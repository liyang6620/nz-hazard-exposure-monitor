from __future__ import annotations

import json
import shutil
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import shapely
from shapely.geometry import mapping

from nzhem.ports import TableStore

MMI_BANDS = ("<4", "4", "5", "6", "7", "8+")


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _mmi_band(value: float) -> str:
    if value >= 8:
        return "8+"
    if value < 4:
        return "<4"
    return str(int(value))


def _event_label(value: str) -> str:
    return value.replace("_", " ").strip().title()


class LocalSiteDataPublisher:
    """Publish a versioned static-site contract from local gold Parquet."""

    def __init__(
        self,
        *,
        event_root: Path,
        reference_root: Path,
        web_root: Path,
        tables: TableStore,
        memory_limit_mb: int = 512,
    ) -> None:
        self._event_root = event_root.resolve()
        self._reference_root = reference_root.resolve()
        self._web_root = web_root.resolve()
        self._tables = tables
        self._memory_limit_mb = memory_limit_mb

    def publish(self, generated_at: datetime) -> dict[str, Any]:
        generated_at = generated_at.astimezone(UTC)
        generation_id = generated_at.strftime("%Y%m%dT%H%M%S%fZ")
        data_root = self._web_root / "data"
        generation_root = data_root / "generations" / generation_id
        generation_root.mkdir(parents=True, exist_ok=False)

        connection = duckdb.connect()
        connection.execute(f"set memory_limit = '{self._memory_limit_mb}MB'")
        connection.execute("set threads = 1")
        connection.execute("load h3")
        try:
            events = self._gold_events(connection)
            regions = self._region_lookup(connection)
            exposure = self._exposure_rows(connection)
            map_exposure = self._map_exposure_rows(connection)
            briefings = self._briefing_states()
            payloads = self._build_event_payloads(
                events,
                exposure,
                regions,
                briefings,
                map_exposure=map_exposure,
            )
            merged_events = self._merge_recent_events(payloads, generated_at)
            self._write_generation(connection, generation_root, merged_events, payloads)
        except Exception:
            shutil.rmtree(generation_root, ignore_errors=True)
            raise
        finally:
            connection.close()

        latest_event_id = merged_events[0]["event_id"] if merged_events else None
        manifest = {
            "schema_version": 1,
            "generation_id": generation_id,
            "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
            "latest_event_id": latest_event_id,
            "base_path": f"/data/generations/{generation_id}",
        }
        self._write_json(data_root / f"manifest-{generation_id}.json", manifest)
        temporary_manifest = data_root / ".manifest.json.tmp"
        self._write_json(temporary_manifest, manifest)
        temporary_manifest.replace(data_root / "manifest.json")
        self._remove_old_generations(data_root / "generations", keep=2)
        return {
            "generation_id": generation_id,
            "events": len(merged_events),
            "ready_events": len(payloads),
            "latest_event_id": latest_event_id,
        }

    def _gold_events(self, connection: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
        summary = _sql_path(self._event_root / "mart_event_summary.parquet")
        events = _sql_path(self._event_root / "dim_event.parquet")
        return self._rows(
            connection,
            f"""
            select
                summary.*,
                events.shaking_type
            from read_parquet('{summary}') summary
            join read_parquet('{events}') events using (event_id)
            order by summary.origin_time desc
            """,
        )

    def _region_lookup(self, connection: duckdb.DuckDBPyConnection) -> dict[int, tuple[str, str]]:
        buildings = _sql_path(self._reference_root / "int_buildings_h3" / "region=*" / "*.parquet")
        rows = self._rows(
            connection,
            f"""
            select
                h3_res8,
                arg_max(region_code, building_count) as region_code,
                arg_max(region_name, building_count) as region_name
            from (
                select h3_res8, region_code, region_name, count(*) as building_count
                from read_parquet('{buildings}', hive_partitioning=true)
                where lifecycle = 'Current'
                group by h3_res8, region_code, region_name
            ) grouped
            group by h3_res8
            """,
        )
        return {
            int(row["h3_res8"]): (
                str(row["region_code"] or "unknown"),
                str(row["region_name"] or "Unknown region"),
            )
            for row in rows
        }

    def _exposure_rows(self, connection: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
        exposure = _sql_path(self._event_root / "fct_event_exposure_cell.parquet")
        return self._rows(
            connection,
            f"""
            select *
            from read_parquet('{exposure}')
            order by event_id, h3_res8
            """,
        )

    def _map_exposure_rows(self, connection: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
        exposure = _sql_path(self._event_root / "mart_event_exposure_h3r6.parquet")
        return self._rows(
            connection,
            f"""
            select *, h3_cell_to_boundary_wkt(h3_res6) as geometry_wkt
            from read_parquet('{exposure}')
            order by event_id, h3_res6
            """,
        )

    def _briefing_states(self) -> dict[str, dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self._tables.list_entities("briefings", "briefing"):
            grouped[str(row.get("event_id", ""))].append(row)
        result: dict[str, dict[str, Any]] = {}
        for event_id, rows in grouped.items():
            latest = max(
                rows,
                key=lambda row: str(row.get("reviewed_at") or row.get("created_at", "")),
            )
            status = str(latest.get("status", "pending"))
            result[event_id] = {
                "status": status,
                "title": latest.get("title") if status == "approved" else None,
                "public_path": f"/briefings/{event_id}.html" if status == "approved" else None,
            }
        return result

    def _build_event_payloads(
        self,
        events: list[dict[str, Any]],
        exposure: list[dict[str, Any]],
        regions: dict[int, tuple[str, str]],
        briefings: dict[str, dict[str, Any]],
        *,
        map_exposure: list[dict[str, Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        exposure_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in exposure:
            exposure_by_event[str(row["event_id"])].append(row)
        map_exposure_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in map_exposure if map_exposure is not None else exposure:
            map_exposure_by_event[str(row["event_id"])].append(row)

        payloads: dict[str, dict[str, Any]] = {}
        for event in events:
            event_id = str(event["event_id"])
            event_exposure = exposure_by_event[event_id]
            bands = {
                band: {"mmi_band": band, "buildings": 0, "population": 0.0} for band in MMI_BANDS
            }
            regional: dict[tuple[str, str], dict[str, Any]] = {}
            features = []
            for row in event_exposure:
                band = _mmi_band(float(row["mmi"]))
                bands[band]["buildings"] += int(row["as_if_today_building_count"] or 0)
                bands[band]["population"] += float(row["population_2023"] or 0)
                if float(row["mmi"]) >= 6:
                    region = regions.get(int(row["h3_res8"]), ("unknown", "Unknown region"))
                    region_row = regional.setdefault(
                        region,
                        {
                            "region_code": region[0],
                            "region_name": region[1],
                            "buildings": 0,
                            "population": 0.0,
                        },
                    )
                    region_row["buildings"] += int(row["as_if_today_building_count"] or 0)
                    region_row["population"] += float(row["population_2023"] or 0)
            for row in map_exposure_by_event[event_id]:
                if float(row["mmi"]) >= 5 and int(row["current_building_count"] or 0) > 0:
                    geometry = shapely.from_wkt(str(row["geometry_wkt"]))
                    features.append(
                        {
                            "type": "Feature",
                            "properties": {
                                "h3_res6": str(row["h3_res6"]),
                                "mmi": float(row["mmi"]),
                                "mmi_band": _mmi_band(float(row["mmi"])),
                                "mmi_source": row["mmi_source"],
                                "source_version": row["source_version"],
                                "buildings": int(row["as_if_today_building_count"] or 0),
                                "population": float(row["population_2023"] or 0),
                            },
                            "geometry": mapping(geometry),
                        }
                    )
            region_rows = sorted(
                (row for row in regional.values() if row["buildings"] > 0 or row["population"] > 0),
                key=lambda row: (-row["buildings"], row["region_code"]),
            )
            no_damage = float(event["max_mmi"] or 0) < 6
            top_region = region_rows[0]["region_name"] if region_rows else None
            if no_damage:
                map_summary = (
                    f"No damaging shaking (MMI < 6). The highest populated intensity was "
                    f"MMI {float(event['max_mmi'] or 0):.1f}."
                )
            else:
                map_summary = (
                    f"{top_region or 'The mapped area'} was most affected. The highest populated "
                    f"intensity was MMI {float(event['max_mmi']):.1f}. MMI 6 or greater exposed "
                    f"{int(event['buildings_mmi_ge_6'] or 0):,} buildings and "
                    f"{round(float(event['population_mmi_ge_6'] or 0)):,} people."
                )
            source_kind = "official" if event["mmi_source"] == "official" else "preliminary"
            summary = {
                "event_id": event_id,
                "name": _event_label(str(event["event_name"])),
                "origin_time": _json_value(event["origin_time"]),
                "magnitude": float(event["magnitude"]),
                "depth_km": float(event["depth_km"]),
                "latitude": float(event["latitude"]),
                "longitude": float(event["longitude"]),
                "assessment_status": "ready",
                "max_mmi": float(event["max_mmi"] or 0),
                "buildings_mmi_ge_6": int(event["buildings_mmi_ge_6"] or 0),
                "population_mmi_ge_6": float(event["population_mmi_ge_6"] or 0),
                "no_damaging_shaking": no_damage,
                "mmi_source": str(event["mmi_source"]),
                "source_kind": source_kind,
                "source_version": str(event["shaking_version"]),
                "shaking_type": str(event["shaking_type"]),
                "event_time_status": str(event["event_time_status"]),
                "as_if_today": True,
                "map_summary": map_summary,
                "mmi_bands": list(bands.values()),
                "regions": region_rows,
                "briefing": briefings.get(
                    event_id,
                    {"status": "pending", "title": None, "public_path": None},
                ),
            }
            payloads[event_id] = {
                "summary": summary,
                "features": {"type": "FeatureCollection", "features": features},
            }
        return payloads

    def _merge_recent_events(
        self,
        payloads: dict[str, dict[str, Any]],
        generated_at: datetime,
    ) -> list[dict[str, Any]]:
        events = {event_id: dict(payload["summary"]) for event_id, payload in payloads.items()}
        cutoff = generated_at - timedelta(days=30)
        for row in self._tables.list_entities("eventsstate", "recent"):
            if float(row.get("magnitude", 0)) < 4:
                continue
            try:
                event_time = datetime.fromisoformat(str(row["event_time"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if event_time.astimezone(UTC) < cutoff:
                continue
            event_id = str(row["event_id"])
            if event_id in events:
                events[event_id].update(
                    {
                        "origin_time": event_time.astimezone(UTC).isoformat(),
                        "magnitude": float(row["magnitude"]),
                        "depth_km": float(row.get("depth_km", events[event_id]["depth_km"])),
                        "latitude": float(row.get("latitude", events[event_id]["latitude"])),
                        "longitude": float(row.get("longitude", events[event_id]["longitude"])),
                    }
                )
                continue
            events[event_id] = {
                "event_id": event_id,
                "name": str(row.get("event_name") or "New Zealand earthquake"),
                "origin_time": event_time.astimezone(UTC).isoformat(),
                "magnitude": float(row["magnitude"]),
                "depth_km": float(row.get("depth_km", 0)),
                "latitude": float(row.get("latitude", 0)),
                "longitude": float(row.get("longitude", 0)),
                "assessment_status": "processing",
                "max_mmi": None,
                "buildings_mmi_ge_6": None,
                "population_mmi_ge_6": None,
                "no_damaging_shaking": False,
                "mmi_source": None,
                "source_kind": "preliminary",
                "source_version": None,
                "shaking_type": "preliminary",
                "event_time_status": "pending",
                "as_if_today": True,
                "map_summary": "Exposure assessment pending.",
                "mmi_bands": [],
                "regions": [],
                "briefing": {"status": "pending", "title": None, "public_path": None},
            }
        return sorted(events.values(), key=lambda event: str(event["origin_time"]), reverse=True)

    def _write_generation(
        self,
        connection: duckdb.DuckDBPyConnection,
        generation_root: Path,
        events: list[dict[str, Any]],
        payloads: dict[str, dict[str, Any]],
    ) -> None:
        index_rows = [
            {key: value for key, value in event.items() if key not in {"mmi_bands", "regions"}}
            for event in events
        ]
        self._write_json(generation_root / "events.json", index_rows)
        for event in events:
            event_id = str(event["event_id"])
            event_root = generation_root / "events" / event_id
            if event_id in payloads:
                self._write_json(event_root / "summary.json", payloads[event_id]["summary"])
                self._write_json(event_root / "exposure.geojson", payloads[event_id]["features"])
            else:
                self._write_json(event_root / "summary.json", event)
                self._write_json(
                    event_root / "exposure.geojson",
                    {"type": "FeatureCollection", "features": []},
                )
        cells = _sql_path(self._reference_root / "dim_h3_cell.parquet")
        rows = connection.execute(
            f"select distinct h3_cell_to_boundary_wkt(h3_res6) from read_parquet('{cells}') "
            "where h3_res6 is not null"
        ).fetchall()
        outline = shapely.unary_union([shapely.from_wkt(row[0]) for row in rows]).simplify(
            0.03, preserve_topology=True
        )
        self._write_json(
            generation_root / "nz-outline.geojson",
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "New Zealand exposure coverage"},
                        "geometry": mapping(outline),
                    }
                ],
            },
        )

    @staticmethod
    def _rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
        cursor = connection.execute(sql)
        columns = [item[0] for item in cursor.description]
        return [
            {column: _json_value(value) for column, value in zip(columns, row, strict=True)}
            for row in cursor.fetchall()
        ]

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _remove_old_generations(root: Path, *, keep: int) -> None:
        generations = sorted(path for path in root.iterdir() if path.is_dir())
        for path in generations[:-keep]:
            shutil.rmtree(path)
