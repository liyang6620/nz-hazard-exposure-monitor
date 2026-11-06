"""Generate the source-controlled PBIP model and report from compact specs."""

# ruff: noqa: E501  -- DAX and PBIR strings are clearer when kept intact.

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBIP = ROOT / "reports/powerbi"
MODEL = PBIP / "nzhem.SemanticModel/definition"
REPORT = PBIP / "nzhem.Report/definition"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"


def tag(value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"nzhem-powerbi:{value}"))


def write(path: Path, content: str | dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, dict):
        content = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
    path.write_text(content, encoding="utf-8")


# Display name, source column, type, hidden, format, data category.
TABLES = {
    "dim_event": [
        ("Event ID", "event_id", "string", True, None, None),
        ("Event", "event_name", "string", False, None, None),
        ("Event Date", "event_date", "dateTime", False, "d MMM yyyy", None),
        ("Event Date (NZ)", "event_date_label", "string", False, None, None),
        ("Origin Time", "origin_time", "dateTime", False, "d MMM yyyy HH:mm", None),
        ("Origin Time NZ", "origin_time_label", "string", False, None, None),
        ("Timeline Year", "timeline_year", "double", True, "0.0", None),
        ("Magnitude", "magnitude", "double", False, "0.0", None),
        ("Depth km", "depth_km", "double", False, "#,0.0", None),
        ("Shaking Source", "mmi_source", "string", False, None, None),
        ("Shaking Version", "shaking_version", "string", False, None, None),
        ("Exposure Basis", "exposure_basis", "string", False, None, None),
        ("Event Group", "event_group", "string", False, None, None),
    ],
    "dim_region": [
        ("Region Key", "region_key", "string", True, None, None),
        ("Region", "region_name", "string", False, None, None),
        ("Territorial Authority", "territorial_authority", "string", False, None, None),
        ("Region Buildings", "region_buildings", "int64", True, "#,0", None),
    ],
    "dim_date": [
        ("Date", "date_value", "dateTime", False, "d MMM yyyy", None),
        ("Year", "year", "int64", False, "0", None),
        ("Month Number", "month_number", "int64", True, "0", None),
        ("Month", "month_label", "string", False, None, None),
    ],
    "dim_mmi_band": [
        ("Band Key", "band_key", "int64", True, "0", None),
        ("MMI Band", "band_label", "string", False, None, None),
        ("Minimum MMI", "minimum_mmi", "int64", True, "0", None),
    ],
    "MMI Threshold": [("MMI Threshold", "threshold", "int64", False, "0", None)],
    "fct_event_summary": [
        ("Event ID", "event_id", "string", True, None, None),
        ("Event Date", "event_date", "dateTime", True, None, None),
        ("Maximum MMI", "max_mmi", "double", True, "0.0", None),
        ("Buildings MMI 6+", "buildings_mmi_ge_6", "int64", True, "#,0", None),
        ("People MMI 6+", "population_mmi_ge_6", "double", True, "#,0", None),
        ("Footprint m2 MMI 6+", "footprint_m2_mmi_ge_6", "double", True, "#,0", None),
        ("Validation Stations", "validation_station_count", "int64", True, "#,0", None),
        ("Validation MAE", "validation_mae", "double", True, "0.000", None),
    ],
    "fct_exposure": [
        ("Event ID", "event_id", "string", True, None, None),
        ("Region Key", "region_key", "string", True, None, None),
        ("Band Key", "band_key", "int64", True, None, None),
        ("Buildings", "buildings", "int64", True, "#,0", None),
        ("Footprint m2", "footprint_m2", "double", True, "#,0", None),
        ("People", "people", "double", True, "#,0", None),
    ],
    "fct_map": [
        ("Event ID", "event_id", "string", True, None, None),
        ("H3 Cell", "h3_cell", "string", True, None, None),
        ("Band Key", "band_key", "int64", True, None, None),
        ("MMI", "mmi", "double", True, "0.0", None),
        ("Buildings", "buildings", "int64", True, "#,0", None),
        ("People", "people", "double", True, "#,0", None),
        ("Latitude", "latitude", "double", True, "0.000", "Latitude"),
        ("Longitude", "longitude", "double", True, "0.000", "Longitude"),
    ],
    "fct_accumulation": [
        ("Region Key", "region_key", "string", True, None, None),
        ("Accumulation Score", "accumulation_score", "int64", True, "#,0", None),
        ("Buildings in Strong Cells", "buildings_in_strong_cells", "int64", True, "#,0", None),
        ("Maximum Strong Events", "maximum_strong_events", "int64", True, "0", None),
        ("Latitude", "latitude", "double", True, "0.000", "Latitude"),
        ("Longitude", "longitude", "double", True, "0.000", "Longitude"),
    ],
    "fct_validation": [
        ("Event ID", "event_id", "string", True, None, None),
        ("Station ID", "station_id", "string", True, None, None),
        ("Observed MMI", "observed_mmi", "double", True, "0.0", None),
        ("Estimated MMI", "estimated_mmi", "double", True, "0.0", None),
        ("Absolute Error", "absolute_error", "double", True, "0.000", None),
    ],
    "fct_health": [
        ("Snapshot At", "snapshot_at", "dateTime", True, "d MMM yyyy HH:mm", None),
        ("Last Run", "last_successful_run", "dateTime", True, "d MMM yyyy HH:mm", None),
        ("Failed Runs", "failed_runs", "int64", True, "#,0", None),
        ("Recorded Runs", "recorded_runs", "int64", True, "#,0", None),
        ("Poison Messages", "poison_messages", "int64", True, "#,0", None),
        ("Scope", "scope", "string", False, None, None),
    ],
    "fct_status": [
        ("Assessment Status", "assessment_status", "string", False, None, None),
        ("Event Count", "event_count", "int64", True, "#,0", None),
    ],
    "fct_source": [
        ("Shaking Source", "shaking_source", "string", False, None, None),
        ("Event Count", "event_count", "int64", True, "#,0", None),
    ],
}

MEASURES = [
    (
        "MMI Threshold Selected",
        "SELECTEDVALUE('MMI Threshold'[MMI Threshold], 6)",
        "0",
        "01 Exposure",
        "Selected minimum intensity; 4–8, default 6.",
    ),
    (
        "Exposed Buildings",
        "VAR threshold = [MMI Threshold Selected] RETURN COALESCE(CALCULATE(SUM(fct_exposure[Buildings]), KEEPFILTERS(fct_exposure[Band Key] >= threshold)), 0)",
        "#,0",
        "01 Exposure",
        "Event-time buildings for live events or current buildings for historical replays in cells at or above the selected MMI threshold.",
    ),
    (
        "Exposed Footprint m2",
        "VAR threshold = [MMI Threshold Selected] RETURN CALCULATE(SUM(fct_exposure[Footprint m2]), KEEPFILTERS(fct_exposure[Band Key] >= threshold))",
        "#,0",
        "01 Exposure",
        "Building footprint area in square metres at or above the selected MMI threshold.",
    ),
    (
        "Exposed Population",
        "VAR threshold = [MMI Threshold Selected] RETURN COALESCE(ROUND(CALCULATE(SUM(fct_exposure[People]), KEEPFILTERS(fct_exposure[Band Key] >= threshold)), 0), 0)",
        "#,0",
        "01 Exposure",
        "2023 allocated population in cells at or above the selected MMI threshold, rounded to people.",
    ),
    (
        "% Region Buildings Exposed",
        "IF(HASONEVALUE(dim_event[Event ID]), DIVIDE([Exposed Buildings], SUM(dim_region[Region Buildings])))",
        "0.0%",
        "02 Regions",
        "Share of current buildings exposed in a selected replay region and event; unavailable for live events because the public live feed lacks a regional stock denominator.",
    ),
    (
        "Accumulated Building Exposures",
        "SUM(fct_accumulation[Accumulation Score])",
        "#,0",
        "02 Regions",
        "Sum of current buildings multiplied by the number of historical MMI 6+ events per cell; repeated exposure, not unique buildings.",
    ),
    (
        "Buildings in Strong Cells",
        "SUM(fct_accumulation[Buildings in Strong Cells])",
        "#,0",
        "02 Regions",
        "Current buildings in cells that experienced MMI 6+ in at least one replay.",
    ),
    (
        "Max MMI",
        "MAX(fct_event_summary[Maximum MMI])",
        "0.0",
        "03 Events",
        "Highest populated-cell MMI in the filtered event set; never summed.",
    ),
    (
        "Magnitude",
        "MAX(dim_event[Magnitude])",
        "0.0",
        "03 Events",
        "Highest GeoNet magnitude in the filtered event set.",
    ),
    (
        "Event Count",
        "DISTINCTCOUNT(dim_event[Event ID])",
        "#,0",
        "03 Events",
        "Number of distinct live and historical events in filter context.",
    ),
    (
        "Timeline Year",
        "MAX(dim_event[Timeline Year])",
        "0.0",
        "03 Events",
        "Fractional calendar year of the earthquake origin, for the timeline X axis.",
    ),
    (
        "Estimated MMI MAE",
        "DIVIDE(SUM(fct_validation[Absolute Error]), COUNTROWS(fct_validation))",
        "0.000",
        "04 Quality",
        "Station-weighted mean absolute error, recomputed from valid stations rather than summed event MAEs.",
    ),
    (
        "Validation Stations",
        "COUNTROWS(fct_validation)",
        "#,0",
        "04 Quality",
        "Valid observed-intensity stations included in the MAE calculation.",
    ),
    (
        "Last Successful Run",
        'FORMAT(MAX(fct_health[Last Run]), "d MMM yyyy HH:mm", "en-NZ")',
        "@",
        "04 Quality",
        "Last successful Azure housekeeping run captured in the read-only snapshot.",
    ),
    (
        "Hours Since Last Run",
        "DATEDIFF(MAX(fct_health[Last Run]), MAX(fct_health[Snapshot At]), HOUR)",
        "#,0",
        "04 Quality",
        "Age of the last Azure housekeeping run at snapshot time, in hours; not live.",
    ),
    (
        "Failed Runs",
        "SUM(fct_health[Failed Runs])",
        "#,0",
        "04 Quality",
        "Failed Azure housekeeping runs in the read-only snapshot.",
    ),
    (
        "Poison Messages",
        "SUM(fct_health[Poison Messages])",
        "#,0",
        "04 Quality",
        "Approximate Azure poison-queue depth at snapshot time, including acceptance-drill messages.",
    ),
    (
        "Live Event Count",
        "SUM(fct_status[Event Count])",
        "#,0",
        "04 Quality",
        "Recent monitored events by terminal assessment state in the published site index.",
    ),
    (
        "Shaking Source Events",
        "SUM(fct_source[Event Count])",
        "#,0",
        "04 Quality",
        "Recent monitored events by published shaking source.",
    ),
    (
        "Largest Event Exposure",
        "MAXX(VALUES(dim_event[Event ID]), [Exposed Buildings])",
        "#,0",
        "03 Events",
        "Largest building exposure in a single replay at the selected MMI threshold.",
    ),
    (
        "Largest Exposure Event",
        'VAR ranked = TOPN(1, VALUES(dim_event[Event ID]), [Exposed Buildings], DESC, dim_event[Event ID], ASC) RETURN CONCATENATEX(ranked, CALCULATE(SELECTEDVALUE(dim_event[Event])), ", ")',
        "@",
        "03 Events",
        "Event name associated with the largest single-event building exposure.",
    ),
    (
        "Events with Damaging Shaking",
        "COUNTROWS(FILTER(VALUES(dim_event[Event ID]), CALCULATE([Max MMI]) >= 6))",
        "#,0",
        "03 Events",
        "Number of replay events reaching MMI 6 in a populated cell.",
    ),
    (
        "Share of Stock Title",
        'IF(HASONEVALUE(dim_region[Region]), "Share of region stock", "Share of national stock")',
        "@",
        "02 Regions",
        "Describes whether the denominator covers a selected region or the national stock.",
    ),
    (
        "Map Buildings",
        "SUM(fct_map[Buildings])",
        "#,0",
        "05 Map",
        "Buildings at the event's stated exposure basis for map bubble size.",
    ),
    (
        "Map Longitude",
        "AVERAGE(fct_map[Longitude])",
        "0.000",
        "05 Map",
        "Longitude of the H3 resolution 6 map point.",
    ),
    (
        "Map Latitude",
        "AVERAGE(fct_map[Latitude])",
        "0.000",
        "05 Map",
        "Latitude of the H3 resolution 6 map point.",
    ),
    (
        "Regional Map Longitude",
        "AVERAGE(fct_accumulation[Longitude])",
        "0.000",
        "05 Map",
        "Longitude of the regional accumulation centroid.",
    ),
    (
        "Regional Map Latitude",
        "AVERAGE(fct_accumulation[Latitude])",
        "0.000",
        "05 Map",
        "Latitude of the regional accumulation centroid.",
    ),
    (
        "Exposure Status",
        'IF(HASONEVALUE(dim_event[Event ID]) && [Max MMI] < 6, "No damaging shaking", "Exposure assessed")',
        "@",
        "03 Events",
        "Explicit no-damaging-shaking status for a single assessed event.",
    ),
    (
        "Buildings Threshold Title",
        '"Buildings at MMI " & FORMAT([MMI Threshold Selected], "0") & "+"',
        "@",
        "01 Exposure",
        "Building KPI label that follows the selected MMI threshold.",
    ),
    (
        "People Threshold Title",
        '"People at MMI " & FORMAT([MMI Threshold Selected], "0") & "+"',
        "@",
        "01 Exposure",
        "Population KPI label that follows the selected MMI threshold.",
    ),
    (
        "Snapshot Time",
        '"Snapshot " & FORMAT(MAX(fct_health[Snapshot At]), "d MMM yyyy HH:mm", "en-NZ") & " UTC"',
        "@",
        "04 Quality",
        "UTC time at which the read-only Power BI import snapshot was created.",
    ),
]


def table_tmdl(name: str, columns: list[tuple[str, str, str, bool, str | None, str | None]]) -> str:
    quoted = f"'{name}'" if " " in name else name
    lines = [f"table {quoted}", f"\tlineageTag: {tag('table:' + name)}", ""]
    if name == "dim_date":
        lines.insert(2, "\tdataCategory: Time")
    for display, source, kind, hidden, fmt, category in columns:
        lines += [f"\tcolumn '{display}'", f"\t\tdataType: {kind}"]
        if name == "dim_date" and display == "Date":
            lines.append("\t\tisKey")
        if hidden:
            lines.append("\t\tisHidden")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        if category:
            lines.append(f"\t\tdataCategory: {category}")
        lines += [
            f"\t\tlineageTag: {tag(name + ':' + source)}",
            "\t\tsummarizeBy: none",
            f"\t\tsourceColumn: {source}",
            "",
        ]
        if name == "dim_date" and display == "Date":
            lines.insert(len(lines) - 1, "\t\tannotation UnderlyingDateTimeDataType = Date")
    if name == "dim_region":
        lines += [
            "\thierarchy 'Region to Authority'",
            f"\t\tlineageTag: {tag('hierarchy:region-authority')}",
            "\t\tlevel Region",
            f"\t\t\tlineageTag: {tag('level:region')}",
            "\t\t\tcolumn: Region",
            "\t\tlevel 'Territorial Authority'",
            f"\t\t\tlineageTag: {tag('level:authority')}",
            "\t\t\tcolumn: 'Territorial Authority'",
            "",
        ]
    filename = "mmi_threshold" if name == "MMI Threshold" else name
    lines += [
        f"\tpartition {quoted} = m",
        "\t\tmode: import",
        f'\t\tsource = Parquet.Document(File.Contents(RepoRoot & "\\.local\\data\\powerbi\\{filename}.parquet"))',
        "",
    ]
    return "\n".join(lines)


def measures_tmdl() -> str:
    lines = ["table _Measures", f"\tlineageTag: {tag('table:_Measures')}", ""]
    for name, dax, fmt, folder, description in MEASURES:
        lines += [
            f"\t/// {description}",
            f"\tmeasure '{name}' = {dax}",
            f"\t\tformatString: {fmt}",
            f"\t\tdisplayFolder: {folder}",
            f"\t\tlineageTag: {tag('measure:' + name)}",
            "",
        ]
    lines += [
        "\tcolumn Placeholder",
        "\t\tdataType: string",
        "\t\tisHidden",
        "\t\tsummarizeBy: none",
        "\t\tsourceColumn: [Placeholder]",
        "",
        "\tpartition _Measures = calculated",
        "\t\tmode: import",
        '\t\tsource = ROW("Placeholder", "")',
        "",
    ]
    return "\n".join(lines)


def field(table: str, property_name: str, measure: bool = False) -> dict[str, object]:
    return {
        "field": {
            "Measure" if measure else "Column": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": property_name,
            }
        },
        "queryRef": f"{table}.{property_name}",
        "nativeQueryRef": property_name,
    }


def visual(
    name: str,
    kind: str,
    x: int,
    y: int,
    width: int,
    height: int,
    roles: dict[str, list[tuple[str, str, bool]]] | None = None,
    title: str | None = None,
    text: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "$schema": f"{SCHEMA}/visualContainer/2.10.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": 1, "width": width, "height": height, "tabOrder": 1},
        "visual": {"visualType": kind, "drillFilterOtherVisuals": True},
    }
    inner = result["visual"]
    if kind == "card":
        inner["objects"] = {
            "categoryLabels": [{"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}],
            "labels": [
                {
                    "properties": {
                        "labelDisplayUnits": {"expr": {"Literal": {"Value": "1D"}}},
                        **(
                            {"fontSize": {"expr": {"Literal": {"Value": "18D"}}}}
                            if name == "last-run"
                            else {}
                        ),
                    }
                }
            ],
        }
    elif kind in {"clusteredBarChart", "clusteredColumnChart", "columnChart"} or name in {
        "history-trend",
        "regional-map",
    }:
        inner["objects"] = {
            "dataPoint": [
                {
                    "properties": {
                        "fill": {"solid": {"color": {"expr": {"Literal": {"Value": "'#171815'"}}}}}
                    }
                }
            ]
        }
    if roles:
        inner["query"] = {
            "queryState": {
                role: {"projections": [field(*spec) for spec in specs]}
                for role, specs in roles.items()
            }
        }
    if title:
        inner["visualContainerObjects"] = {
            "title": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {
                            "expr": {
                                "Literal": {
                                    "Value": json.dumps(title, ensure_ascii=False).replace('"', "'")
                                }
                            }
                        },
                    }
                }
            ]
        }
    if text is not None:
        font_size = "26pt" if name == "heading" else "10pt" if name == "rule" else "12pt"
        inner["objects"] = {
            "general": [
                {
                    "properties": {
                        "paragraphs": [
                            {
                                "textRuns": [
                                    {
                                        "value": text,
                                        "textStyle": {
                                            "fontFamily": "Segoe UI",
                                            "fontSize": font_size,
                                            "color": "#171815",
                                        },
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }
    return result


def sort_visual(
    item: dict[str, object], table: str, name: str, *, descending: bool = True, measure: bool = True
) -> dict[str, object]:
    item["visual"]["query"]["sortDefinition"] = {
        "sort": [
            {
                "field": field(table, name, measure)["field"],
                "direction": "Descending" if descending else "Ascending",
            }
        ],
        "isDefaultSort": False,
    }
    return item


def no_totals(item: dict[str, object]) -> dict[str, object]:
    item["visual"].setdefault("objects", {})["total"] = [
        {"properties": {"totals": {"expr": {"Literal": {"Value": "false"}}}}}
    ]
    return item


def hide_unmapped_region(item: dict[str, object]) -> dict[str, object]:
    item["filterConfig"] = {
        "filters": [
            {
                "name": tag(f"filter:unmapped:{item['name']}").replace("-", "")[:20],
                "field": field("dim_region", "Region")["field"],
                "type": "Advanced",
                "filter": {
                    "Version": 2,
                    "From": [{"Name": "r", "Entity": "dim_region", "Type": 0}],
                    "Where": [
                        {
                            "Condition": {
                                "Not": {
                                    "Expression": {
                                        "Comparison": {
                                            "ComparisonKind": 0,
                                            "Left": {
                                                "Column": {
                                                    "Expression": {"SourceRef": {"Source": "r"}},
                                                    "Property": "Region",
                                                }
                                            },
                                            "Right": {
                                                "Literal": {"Value": "'Outside mapped regions'"}
                                            },
                                        }
                                    }
                                }
                            }
                        }
                    ],
                },
            }
        ]
    }
    return item


def historical_only(item: dict[str, object]) -> dict[str, object]:
    item["filterConfig"] = {
        "filters": [
            {
                "name": tag(f"filter:replays:{item['name']}").replace("-", "")[:20],
                "field": field("dim_event", "Event Group")["field"],
                "type": "Categorical",
                "filter": {
                    "Version": 2,
                    "From": [{"Name": "e", "Entity": "dim_event", "Type": 0}],
                    "Where": [
                        {
                            "Condition": {
                                "In": {
                                    "Expressions": [
                                        {
                                            "Column": {
                                                "Expression": {"SourceRef": {"Source": "e"}},
                                                "Property": "Event Group",
                                            }
                                        }
                                    ],
                                    "Values": [[{"Literal": {"Value": "'Historical replays'"}}]],
                                }
                            }
                        }
                    ],
                },
            }
        ]
    }
    return item


def table_widths(item: dict[str, object], widths: dict[str, int]) -> dict[str, object]:
    objects = item["visual"].setdefault("objects", {})
    objects["columnHeaders"] = [{"properties": {}}]
    objects["columnWidth"] = [
        {
            "properties": {"value": {"expr": {"Literal": {"Value": f"{width}D"}}}},
            "selector": {"metadata": column},
        }
        for column, width in widths.items()
    ]
    return item


def map_axes(item: dict[str, object]) -> dict[str, object]:
    axes = item["visual"].setdefault("objects", {})
    for axis, start, end in (("categoryAxis", 160, 185), ("valueAxis", -48.5, -33.5)):
        axes[axis] = [
            {
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "false"}}},
                    "start": {"expr": {"Literal": {"Value": f"{start}D"}}},
                    "end": {"expr": {"Literal": {"Value": f"{end}D"}}},
                    "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}},
                    "gridlineShow": {"expr": {"Literal": {"Value": "false"}}},
                }
            }
        ]
    axes["plotArea"] = [
        {
            "properties": {
                "transparency": {"expr": {"Literal": {"Value": "0D"}}},
                "image": {
                    "image": {
                        "name": {"expr": {"Literal": {"Value": "'nz-coastline.svg'"}}},
                        "url": {
                            "expr": {
                                "ResourcePackageItem": {
                                    "PackageName": "RegisteredResources",
                                    "PackageType": 1,
                                    "ItemName": "nz-coastline.svg",
                                }
                            }
                        },
                        "scaling": {"expr": {"Literal": {"Value": "'Fill'"}}},
                    }
                },
            }
        }
    ]
    return item


def add(page: Path, item: dict[str, object]) -> None:
    write(page / "visuals" / item["name"] / "visual.json", item)


def build_page(
    slug: str,
    title: str,
    subtitle: str,
    items: list[dict[str, object]],
    *,
    header_width: int = 1344,
) -> None:
    page = REPORT / "pages" / slug
    write(
        page / "page.json",
        {
            "$schema": f"{SCHEMA}/page/2.0.0/schema.json",
            "name": slug,
            "displayName": title,
            "displayOption": "FitToPage",
            "height": 900,
            "width": 1440,
            "objects": {
                "background": [
                    {
                        "properties": {
                            "color": {
                                "solid": {"color": {"expr": {"Literal": {"Value": "'#F2EDDF'"}}}}
                            },
                            "transparency": {"expr": {"Literal": {"Value": "0D"}}},
                        }
                    }
                ]
            },
        },
    )
    add(page, visual("heading", "textbox", 48, 24, header_width, 60, text=title.upper()))
    add(page, visual("subtitle", "textbox", 48, 82, header_width, 36, text=subtitle))
    add(
        page,
        visual(
            "rule",
            "textbox",
            48,
            818,
            1344,
            32,
            text="NZ HAZARD EXPOSURE MONITOR  /  stnzhem8495b7ca.z8.web.core.windows.net",
        ),
    )
    add(
        page,
        visual("navigation", "pageNavigator", 48, 852, 670, 36),
    )
    add(
        page,
        visual(
            "snapshot-time",
            "card",
            742,
            852,
            360,
            36,
            {"Values": [("_Measures", "Snapshot Time", True)]},
        ),
    )
    site_button = visual("open-website", "actionButton", 1118, 852, 274, 36, title="OPEN WEBSITE")
    site_button["visual"].setdefault("visualContainerObjects", {})["visualLink"] = [
        {
            "properties": {
                "show": {"expr": {"Literal": {"Value": "true"}}},
                "type": {"expr": {"Literal": {"Value": "'WebUrl'"}}},
                "webUrl": {
                    "expr": {
                        "Literal": {"Value": "'https://stnzhem8495b7ca.z8.web.core.windows.net/'"}
                    }
                },
            }
        }
    ]
    add(page, site_button)
    for item in items:
        add(page, item)


def card(
    name: str, measure: str, title: str, x: int, y: int, width: int = 292
) -> dict[str, object]:
    item = visual(name, "card", x, y, width, 112, {"Values": [("_Measures", measure, True)]}, title)
    dynamic_titles = {
        "region-share": "Share of Stock Title",
        "buildings": "Buildings Threshold Title",
        "people": "People Threshold Title",
        "region-buildings": "Buildings Threshold Title",
    }
    if name in dynamic_titles:
        item["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"] = {
            "expr": {
                "Measure": {
                    "Expression": {"SourceRef": {"Entity": "_Measures"}},
                    "Property": dynamic_titles[name],
                }
            }
        }
    return item


def chart(
    name: str,
    kind: str,
    title: str,
    x: int,
    y: int,
    width: int,
    height: int,
    category: tuple[str, str, bool],
    metrics: list[str],
) -> dict[str, object]:
    role = "Y" if kind == "clusteredBarChart" else "Y"
    return sort_visual(
        visual(
            name,
            kind,
            x,
            y,
            width,
            height,
            {"Category": [category], role: [("_Measures", m, True) for m in metrics]},
            title,
        ),
        "_Measures",
        metrics[0],
    )


def threshold_slicer() -> dict[str, object]:
    item = visual(
        "threshold",
        "slicer",
        1104,
        132,
        288,
        96,
        {"Values": [("MMI Threshold", "MMI Threshold", False)]},
        None,
    )
    item["visual"]["objects"] = {
        "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}],
        "selection": [
            {"properties": {"strictSingleSelect": {"expr": {"Literal": {"Value": "true"}}}}}
        ],
        "general": [
            {
                "properties": {
                    "filter": {
                        "filter": {
                            "Version": 2,
                            "From": [{"Name": "t", "Entity": "MMI Threshold", "Type": 0}],
                            "Where": [
                                {
                                    "Condition": {
                                        "Comparison": {
                                            "ComparisonKind": 0,
                                            "Left": {
                                                "Column": {
                                                    "Expression": {"SourceRef": {"Source": "t"}},
                                                    "Property": "MMI Threshold",
                                                }
                                            },
                                            "Right": {"Literal": {"Value": "6D"}},
                                        }
                                    }
                                }
                            ],
                        }
                    }
                }
            }
        ],
    }
    return item


def event_slicer() -> dict[str, object]:
    item = visual(
        "event-slicer",
        "slicer",
        252,
        132,
        196,
        96,
        {"Values": [("dim_event", "Event", False)]},
        None,
    )
    item["visual"]["objects"] = {
        "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}],
        "selection": [
            {"properties": {"strictSingleSelect": {"expr": {"Literal": {"Value": "true"}}}}}
        ],
        "general": [
            {
                "properties": {
                    "filter": {
                        "filter": {
                            "Version": 2,
                            "From": [{"Name": "e", "Entity": "dim_event", "Type": 0}],
                            "Where": [
                                {
                                    "Condition": {
                                        "Comparison": {
                                            "ComparisonKind": 0,
                                            "Left": {
                                                "Column": {
                                                    "Expression": {"SourceRef": {"Source": "e"}},
                                                    "Property": "Event",
                                                }
                                            },
                                            "Right": {"Literal": {"Value": "'Kaikōura, 2016'"}},
                                        }
                                    }
                                }
                            ],
                        }
                    }
                }
            }
        ],
    }
    return item


def event_group_slicer() -> dict[str, object]:
    item = visual(
        "event-group-slicer",
        "slicer",
        48,
        132,
        190,
        96,
        {"Values": [("dim_event", "Event Group", False)]},
        None,
    )
    item["visual"]["objects"] = {
        "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Dropdown'"}}}}}]
    }
    return item


def build_report() -> None:
    pages = REPORT / "pages"
    if pages.exists():
        for child in pages.iterdir():
            if child.is_dir():
                if child.resolve().parent != pages.resolve():
                    raise RuntimeError("Unsafe report page deletion target")
                shutil.rmtree(child)
    order = [
        "event-overview",
        "event-comparison",
        "regional-exposure",
        "event-history",
        "data-health",
    ]
    write(
        pages / "pages.json",
        {
            "$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json",
            "pageOrder": order,
            "activePageName": order[0],
        },
    )
    threshold = threshold_slicer()
    selected_event = event_slicer()
    overview = [
        event_group_slicer(),
        selected_event,
        threshold,
        card("magnitude", "Magnitude", "MAGNITUDE", 48, 248, 324),
        card("mmi", "Max MMI", "MAXIMUM MMI", 388, 248, 324),
        card("buildings", "Exposed Buildings", "EXPOSED BUILDINGS", 728, 248, 324),
        card("people", "Exposed Population", "EXPOSED PEOPLE", 1068, 248, 324),
        map_axes(
            visual(
                "h3-map",
                "scatterChart",
                48,
                392,
                708,
                428,
                {
                    "X": [("_Measures", "Map Longitude", True)],
                    "Y": [("_Measures", "Map Latitude", True)],
                    "Size": [("_Measures", "Map Buildings", True)],
                    "Category": [("fct_map", "H3 Cell", False)],
                    "Series": [("dim_mmi_band", "MMI Band", False)],
                },
                "H3 REPLAY CELLS / LIVE EPICENTRE / MMI INTENSITY",
            )
        ),
        no_totals(
            visual(
                "event-source",
                "tableEx",
                460,
                142,
                620,
                86,
                {
                    "Values": [
                        ("dim_event", "Event", False),
                        ("dim_event", "Shaking Source", False),
                        ("dim_event", "Exposure Basis", False),
                    ]
                },
                "SOURCE AND BASIS",
            )
        ),
        card("exposure-status", "Exposure Status", "ASSESSMENT", 1090, 142, 302),
        hide_unmapped_region(
            chart(
                "regions",
                "clusteredBarChart",
                "REGIONS BY EXPOSED BUILDINGS",
                780,
                392,
                612,
                428,
                ("dim_region", "Region", False),
                ["Exposed Buildings"],
            )
        ),
    ]
    build_page(
        "event-overview",
        "Event Overview",
        "Select live event-time exposure or an as-if-today historical replay. Population uses 2023 Census.",
        overview,
    )

    comparison_threshold = threshold_slicer()
    comparison_threshold["position"]["y"] = 40
    comparison = [
        comparison_threshold,
        card("events", "Event Count", "HISTORICAL EVENTS", 48, 146, 324),
        card(
            "largest-buildings", "Largest Event Exposure", "LARGEST EVENT EXPOSURE", 388, 146, 324
        ),
        card(
            "largest-event", "Largest Exposure Event", "EVENT WITH LARGEST EXPOSURE", 728, 146, 324
        ),
        card(
            "damaging-events",
            "Events with Damaging Shaking",
            "EVENTS WITH DAMAGING SHAKING",
            1068,
            146,
            324,
        ),
        chart(
            "event-buildings",
            "clusteredBarChart",
            "BUILDINGS / EVENT",
            48,
            284,
            658,
            240,
            ("dim_event", "Event", False),
            ["Exposed Buildings"],
        ),
        chart(
            "event-people",
            "clusteredBarChart",
            "PEOPLE / EVENT",
            730,
            284,
            662,
            240,
            ("dim_event", "Event", False),
            ["Exposed Population"],
        ),
        table_widths(
            no_totals(
                sort_visual(
                    visual(
                        "event-comparison-table",
                        "tableEx",
                        48,
                        536,
                        1344,
                        278,
                        {
                            "Values": [
                                ("dim_event", "Event", False),
                                ("_Measures", "Magnitude", True),
                                ("_Measures", "Max MMI", True),
                                ("_Measures", "Exposed Buildings", True),
                                ("_Measures", "Exposed Population", True),
                            ]
                        },
                        "EVENT COMPARISON / SELECT ANY ROW TO CROSS-FILTER",
                    ),
                    "_Measures",
                    "Exposed Buildings",
                )
            ),
            {
                "dim_event.Event": 340,
                "_Measures.Magnitude": 180,
                "_Measures.Max MMI": 180,
                "_Measures.Exposed Buildings": 300,
                "_Measures.Exposed Population": 300,
            },
        ),
    ]
    comparison = [
        historical_only(item) if item["name"] != "threshold" else item for item in comparison
    ]
    build_page(
        "event-comparison",
        "Event Comparison",
        "Ten fixed earthquakes replayed against today's buildings and the 2023 population.",
        comparison,
        header_width=1040,
    )

    regional = [
        selected_event,
        threshold,
        card("region-buildings", "Exposed Buildings", "EXPOSED BUILDINGS", 48, 244, 324),
        card(
            "region-share", "% Region Buildings Exposed", "SHARE OF NATIONAL STOCK", 388, 244, 324
        ),
        card(
            "accumulation",
            "Accumulated Building Exposures",
            "REPEAT EXPOSURE ACROSS 10 REPLAYS",
            728,
            244,
            324,
        ),
        card(
            "strong-cells", "Buildings in Strong Cells", "BUILDINGS IN MMI 6+ CELLS", 1068, 244, 324
        ),
        map_axes(
            visual(
                "regional-map",
                "scatterChart",
                48,
                402,
                660,
                412,
                {
                    "X": [("_Measures", "Regional Map Longitude", True)],
                    "Y": [("_Measures", "Regional Map Latitude", True)],
                    "Size": [("_Measures", "Accumulated Building Exposures", True)],
                    "Category": [("dim_region", "Territorial Authority", False)],
                },
                "REPEAT EXPOSURE ACROSS 10 REPLAYS / CENTROIDS",
            )
        ),
        hide_unmapped_region(
            table_widths(
                no_totals(
                    sort_visual(
                        visual(
                            "region-table",
                            "pivotTable",
                            732,
                            402,
                            660,
                            412,
                            {
                                "Rows": [
                                    ("dim_region", "Region", False),
                                    ("dim_region", "Territorial Authority", False),
                                ],
                                "Values": [
                                    ("_Measures", "Exposed Buildings", True),
                                    ("_Measures", "% Region Buildings Exposed", True),
                                    ("_Measures", "Accumulated Building Exposures", True),
                                ],
                            },
                            "REGION / DISTRICT RANKING AND REPEAT EXPOSURE",
                        ),
                        "_Measures",
                        "Exposed Buildings",
                    )
                ),
                {
                    "dim_region.Region": 170,
                    "dim_region.Territorial Authority": 170,
                    "_Measures.Exposed Buildings": 95,
                    "_Measures.% Region Buildings Exposed": 95,
                    "_Measures.Accumulated Building Exposures": 110,
                },
            )
        ),
    ]
    build_page(
        "regional-exposure",
        "Regional Exposure",
        "Cell-to-region attribution follows the majority building location; boundaries are approximate.",
        regional,
    )

    history_group = event_group_slicer()
    history_group["position"].update({"x": 470, "y": 138, "width": 240})
    history = [
        history_group,
        threshold,
        visual(
            "region-filter",
            "slicer",
            48,
            138,
            400,
            96,
            {"Values": [("dim_region", "Region", False)]},
            None,
        ),
        card("history-events", "Event Count", "EVENTS", 48, 260, 324),
        card(
            "history-damaging",
            "Events with Damaging Shaking",
            "EVENTS WITH DAMAGING SHAKING",
            388,
            260,
            324,
        ),
        card("history-mmi", "Largest Exposure Event", "LARGEST EXPOSURE EVENT", 728, 260, 324),
        card("history-largest", "Largest Event Exposure", "LARGEST EVENT EXPOSURE", 1068, 260, 324),
        visual(
            "history-trend",
            "scatterChart",
            48,
            420,
            600,
            394,
            {
                "X": [("_Measures", "Timeline Year", True)],
                "Y": [("_Measures", "Magnitude", True)],
                "Size": [("_Measures", "Exposed Buildings", True)],
                "Category": [("dim_event", "Event", False)],
                "Tooltips": [
                    ("dim_event", "Event Date (NZ)", False),
                    ("_Measures", "Exposed Population", True),
                ],
            },
            "EVENT TIME × MAGNITUDE  /  BUBBLE AREA = EXPOSED BUILDINGS",
        ),
        table_widths(
            no_totals(
                sort_visual(
                    visual(
                        "history-table",
                        "tableEx",
                        672,
                        420,
                        720,
                        394,
                        {
                            "Values": [
                                ("dim_event", "Event", False),
                                ("dim_event", "Origin Time NZ", False),
                                ("_Measures", "Magnitude", True),
                                ("_Measures", "Exposed Buildings", True),
                            ]
                        },
                        "EVENT CHRONOLOGY",
                    ),
                    "dim_event",
                    "Origin Time NZ",
                    descending=False,
                    measure=False,
                )
            ),
            {
                "dim_event.Event": 205,
                "dim_event.Origin Time NZ": 230,
                "_Measures.Magnitude": 85,
                "_Measures.Exposed Buildings": 145,
            },
        ),
    ]
    build_page(
        "event-history",
        "Event History",
        "Event time along the horizontal axis, magnitude vertically, bubble size by thresholded building exposure.",
        history,
    )

    quality = [
        card("last-run", "Last Successful Run", "LAST SUCCESSFUL RUN / UTC", 48, 148, 280),
        card("hours", "Hours Since Last Run", "HOURS SINCE RUN / AT SNAPSHOT", 340, 148, 252),
        card("failures", "Failed Runs", "FAILED RUNS", 604, 148, 252),
        card("poison", "Poison Messages", "POISON MESSAGES / INCL. DRILLS", 868, 148, 252),
        card("mae", "Estimated MMI MAE", "STATION-WEIGHTED MAE", 1132, 148, 260),
        chart(
            "status",
            "clusteredBarChart",
            "RECENT EVENT STATUS",
            48,
            284,
            420,
            410,
            ("fct_status", "Assessment Status", False),
            ["Live Event Count"],
        ),
        chart(
            "source",
            "clusteredBarChart",
            "RECENT SHAKING SOURCE",
            484,
            284,
            420,
            410,
            ("fct_source", "Shaking Source", False),
            ["Shaking Source Events"],
        ),
        no_totals(
            sort_visual(
                visual(
                    "quality-table",
                    "tableEx",
                    920,
                    284,
                    472,
                    410,
                    {
                        "Values": [
                            ("dim_event", "Event", False),
                            ("_Measures", "Validation Stations", True),
                            ("_Measures", "Estimated MMI MAE", True),
                        ]
                    },
                    "MODEL VALIDATION BY EVENT",
                ),
                "_Measures",
                "Estimated MMI MAE",
            )
        ),
        visual(
            "limitations",
            "textbox",
            48,
            710,
            1344,
            104,
            text=(
                "READ-ONLY AZURE SNAPSHOT. Housekeeping failures and poison-queue depth are "
                "captured at refresh time. Recent event status and shaking source come from the "
                "published index. The station-weighted MAE is indicative, not an actuarial loss "
                "estimate. Historical replays use current building outlines and 2023 population. "
                "Water cells and the Chatham Islands are outside the mapped exposure model."
            ),
        ),
    ]
    quality = [
        historical_only(item) if item["name"] == "quality-table" else item for item in quality
    ]
    build_page(
        "data-health",
        "Data Health",
        "Azure gold and runtime, read-only at refresh time; not a live dashboard.",
        quality,
    )


def build_model() -> None:
    tables = MODEL / "tables"
    for old in tables.glob("*.tmdl"):
        old.unlink()
    for name, columns in TABLES.items():
        write(tables / f"{name}.tmdl", table_tmdl(name, columns))
    write(tables / "_Measures.tmdl", measures_tmdl())
    refs = "\n".join(
        f"ref table '{name}'" if " " in name else f"ref table {name}"
        for name in [*TABLES, "_Measures"]
    )
    write(
        MODEL / "model.tmdl",
        "model Model\n\tculture: en-NZ\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n"
        "\tsourceQueryCulture: en-NZ\n\tdataAccessOptions\n\t\treturnErrorValuesAsNull\n\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n"
        'annotation PBI_ProTooling = ["DevMode"]\n\n' + refs + "\nref role 'Canterbury Analyst'\n",
    )
    write(
        MODEL / "roles/Canterbury Analyst.tmdl",
        "role 'Canterbury Analyst'\n"
        "\tmodelPermission: read\n\n"
        '\ttablePermission dim_region = [Region] = "Canterbury Region"\n',
    )
    relationships = [
        ("fct_event_summary", "Event ID", "dim_event", "Event ID"),
        ("fct_event_summary", "Event Date", "dim_date", "Date"),
        ("fct_exposure", "Event ID", "dim_event", "Event ID"),
        ("fct_exposure", "Region Key", "dim_region", "Region Key"),
        ("fct_exposure", "Band Key", "dim_mmi_band", "Band Key"),
        ("fct_map", "Event ID", "dim_event", "Event ID"),
        ("fct_map", "Band Key", "dim_mmi_band", "Band Key"),
        ("fct_accumulation", "Region Key", "dim_region", "Region Key"),
        ("fct_validation", "Event ID", "dim_event", "Event ID"),
    ]
    write(
        MODEL / "relationships.tmdl",
        "\n".join(
            f"relationship '{tag('relation:' + child + parent)}'\n"
            "\tcrossFilteringBehavior: oneDirection\n"
            f"\tfromColumn: {child}.'{child_col}'\n\ttoColumn: {parent}.'{parent_col}'\n"
            for child, child_col, parent, parent_col in relationships
        ),
    )


def main() -> None:
    build_model()
    build_report()
    theme = {
        "name": "NZHEM Earthquake Record",
        "dataColors": ["#E8DFAF", "#FFF200", "#FFB300", "#FF6800", "#D7191C"],
        "background": "#F2EDDF",
        "foreground": "#171815",
        "tableAccent": "#171815",
        "textClasses": {
            "title": {"fontFace": "Segoe UI", "color": "#171815", "fontSize": 18},
            "header": {"fontFace": "Segoe UI", "color": "#171815", "fontSize": 12},
            "label": {"fontFace": "Segoe UI", "color": "#171815", "fontSize": 10},
            "callout": {"fontFace": "Consolas", "color": "#171815", "fontSize": 28},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"color": {"solid": {"color": "#F2EDDF"}}}],
                    "border": [{"show": True, "color": {"solid": {"color": "#D5D2C9"}}}],
                    "title": [
                        {
                            "fontFace": "Segoe UI",
                            "fontSize": 11,
                            "fontColor": {"solid": {"color": "#171815"}},
                        }
                    ],
                }
            }
        },
    }
    write(PBIP / "nzhem-theme.json", theme)
    write(PBIP / "nzhem.Report/StaticResources/RegisteredResources/nzhem-theme.json", theme)
    report_path = REPORT / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["themeCollection"]["customTheme"] = {
        "name": "nzhem-theme.json",
        "reportVersionAtImport": {"visual": "2.10.0", "report": "3.1.0", "page": "2.0.0"},
        "type": "RegisteredResources",
    }
    report["resourcePackages"] = [
        {
            "name": "RegisteredResources",
            "type": "RegisteredResources",
            "items": [
                {"name": "nzhem-theme.json", "path": "nzhem-theme.json", "type": "CustomTheme"},
                {"name": "nz-coastline.svg", "path": "nz-coastline.svg", "type": "Image"},
            ],
        }
    ]
    write(report_path, report)
    print("Generated Power BI semantic model and five report pages")


if __name__ == "__main__":
    main()
