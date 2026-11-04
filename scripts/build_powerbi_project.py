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
        ("Origin Time", "origin_time", "dateTime", False, "d MMM yyyy HH:mm", None),
        ("Timeline Year", "timeline_year", "double", True, "0.0", None),
        ("Magnitude", "magnitude", "double", False, "0.0", None),
        ("Depth km", "depth_km", "double", False, "#,0.0", None),
        ("Shaking Source", "mmi_source", "string", False, None, None),
        ("Shaking Version", "shaking_version", "string", False, None, None),
        ("Exposure Basis", "exposure_basis", "string", False, None, None),
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
        ("Scope", "scope", "string", False, None, None),
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
        "VAR threshold = [MMI Threshold Selected] RETURN CALCULATE(SUM(fct_exposure[Buildings]), KEEPFILTERS(fct_exposure[Band Key] >= threshold))",
        "#,0",
        "01 Exposure",
        "Current building outlines in cells at or above the selected MMI threshold.",
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
        "VAR threshold = [MMI Threshold Selected] RETURN ROUND(CALCULATE(SUM(fct_exposure[People]), KEEPFILTERS(fct_exposure[Band Key] >= threshold)), 0)",
        "#,0",
        "01 Exposure",
        "2023 allocated population in cells at or above the selected MMI threshold, rounded to people.",
    ),
    (
        "% Region Buildings Exposed",
        "IF(HASONEVALUE(dim_event[Event ID]), DIVIDE([Exposed Buildings], SUM(dim_region[Region Buildings])))",
        "0.0%",
        "02 Regions",
        "Share of current buildings exposed in the selected region and event; blank for multiple events.",
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
        "Number of distinct historical replay events in filter context.",
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
        "MAX(fct_health[Last Run])",
        "d MMM yyyy HH:mm",
        "04 Quality",
        "Last successful local SQLite housekeeping run captured by the snapshot; not Azure live status.",
    ),
    (
        "Hours Since Last Run",
        "DATEDIFF(MAX(fct_health[Last Run]), NOW(), HOUR)",
        "#,0",
        "04 Quality",
        "Age of the last local run at report viewing time, in hours.",
    ),
    (
        "Failed Runs",
        "SUM(fct_health[Failed Runs])",
        "#,0",
        "04 Quality",
        "Recorded failed local housekeeping runs in the snapshot.",
    ),
    (
        "Map Buildings",
        "SUM(fct_map[Buildings])",
        "#,0",
        "05 Map",
        "Current buildings at H3 resolution 6 for map bubble size.",
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
        "\t\tsource =",
        "\t\t\t\tlet",
        f'\t\t\t\t\tSource = Parquet.Document(File.Contents(RepoRoot & "\\.local\\data\\powerbi\\{filename}.parquet"))',
        "\t\t\t\tin",
        "\t\t\t\t\tSource",
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
                                            "fontFamily": "IBM Plex Sans",
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


def add(page: Path, item: dict[str, object]) -> None:
    write(page / "visuals" / item["name"] / "visual.json", item)


def build_page(slug: str, title: str, subtitle: str, items: list[dict[str, object]]) -> None:
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
    add(page, visual("heading", "textbox", 48, 24, 1344, 60, text=title.upper()))
    add(page, visual("subtitle", "textbox", 48, 82, 1344, 36, text=subtitle))
    add(
        page,
        visual(
            "rule",
            "textbox",
            48,
            824,
            1344,
            24,
            text="NZ HAZARD EXPOSURE MONITOR  /  AS-IF-TODAY REPLAY  /  2023 POPULATION",
        ),
    )
    add(
        page,
        visual("navigation", "pageNavigator", 48, 852, 1040, 36),
    )
    for item in items:
        add(page, item)


def card(
    name: str, measure: str, title: str, x: int, y: int, width: int = 292
) -> dict[str, object]:
    return visual(name, "card", x, y, width, 122, {"Values": [("_Measures", measure, True)]}, title)


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
    return visual(
        name,
        kind,
        x,
        y,
        width,
        height,
        {"Category": [category], role: [("_Measures", m, True) for m in metrics]},
        title,
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
        "MMI THRESHOLD",
    )
    item["visual"]["objects"] = {
        "data": [{"properties": {"mode": {"expr": {"Literal": {"Value": "'Single'"}}}}}],
        "slider": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}],
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
        48,
        132,
        400,
        96,
        {"Values": [("dim_event", "Event", False)]},
        "EVENT",
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
        selected_event,
        threshold,
        card("magnitude", "Magnitude", "PEAK MAGNITUDE", 48, 248),
        card("mmi", "Max MMI", "MAXIMUM MMI", 348, 248),
        card("buildings", "Exposed Buildings", "EXPOSED BUILDINGS", 648, 248),
        card("people", "Exposed Population", "EXPOSED PEOPLE", 948, 248),
        visual(
            "h3-map",
            "scatterChart",
            48,
            392,
            760,
            428,
            {
                "X": [("_Measures", "Map Longitude", True)],
                "Y": [("_Measures", "Map Latitude", True)],
                "Size": [("_Measures", "Map Buildings", True)],
                "Category": [("fct_map", "H3 Cell", False)],
                "Series": [("dim_mmi_band", "MMI Band", False)],
            },
            "H3 EXPOSURE POINTS  /  LONGITUDE × LATITUDE",
        ),
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
        ),
        chart(
            "regions",
            "clusteredBarChart",
            "REGIONS BY EXPOSED BUILDINGS",
            832,
            392,
            560,
            428,
            ("dim_region", "Region", False),
            ["Exposed Buildings"],
        ),
    ]
    build_page(
        "event-overview",
        "Event Overview",
        "Select one earthquake. Counts use the current building stock and 2023 population (as-if-today).",
        overview,
    )

    comparison = [
        threshold,
        card("events", "Event Count", "HISTORICAL EVENTS", 48, 146),
        card("total-buildings", "Exposed Buildings", "EVENT-BUILDING EXPOSURES", 348, 146),
        card("total-people", "Exposed Population", "EVENT-PEOPLE EXPOSURES", 648, 146),
        card("peak-mmi", "Max MMI", "HIGHEST MMI", 948, 146),
        chart(
            "event-buildings",
            "clusteredBarChart",
            "BUILDINGS / EVENT",
            48,
            310,
            658,
            340,
            ("dim_event", "Event", False),
            ["Exposed Buildings"],
        ),
        chart(
            "event-people",
            "clusteredBarChart",
            "PEOPLE / EVENT",
            730,
            310,
            662,
            340,
            ("dim_event", "Event", False),
            ["Exposed Population"],
        ),
        visual(
            "event-comparison-table",
            "tableEx",
            48,
            670,
            1344,
            144,
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
    ]
    build_page(
        "event-comparison",
        "Event Comparison",
        "Ten fixed earthquakes replayed against today's buildings and the 2023 population; totals count repeat exposure.",
        comparison,
    )

    regional = [
        selected_event,
        threshold,
        card("region-buildings", "Exposed Buildings", "EXPOSED BUILDINGS", 48, 244),
        card("region-share", "% Region Buildings Exposed", "SHARE OF REGION STOCK", 348, 244),
        card("accumulation", "Accumulated Building Exposures", "ACCUMULATED EXPOSURES", 648, 244),
        card("strong-cells", "Buildings in Strong Cells", "BUILDINGS IN MMI 6+ CELLS", 948, 244),
        chart(
            "region-ranking",
            "clusteredBarChart",
            "REGION / TERRITORIAL AUTHORITY RANKING",
            48,
            402,
            660,
            220,
            ("dim_region", "Territorial Authority", False),
            ["Exposed Buildings"],
        ),
        visual(
            "regional-map",
            "scatterChart",
            732,
            402,
            660,
            220,
            {
                "X": [("_Measures", "Regional Map Longitude", True)],
                "Y": [("_Measures", "Regional Map Latitude", True)],
                "Size": [("_Measures", "Accumulated Building Exposures", True)],
                "Category": [("dim_region", "Territorial Authority", False)],
            },
            "ACCUMULATION CENTROIDS  /  LONGITUDE × LATITUDE",
        ),
        visual(
            "region-table",
            "pivotTable",
            48,
            640,
            1344,
            174,
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
            "REGIONAL DETAIL",
        ),
    ]
    build_page(
        "regional-exposure",
        "Regional Exposure",
        "Cell-to-region attribution follows the majority building location; boundaries are approximate.",
        regional,
    )

    history = [
        threshold,
        visual(
            "region-filter",
            "slicer",
            48,
            138,
            400,
            96,
            {"Values": [("dim_region", "Region", False)]},
            "REGION",
        ),
        card("history-events", "Event Count", "EVENTS", 48, 260),
        card("history-buildings", "Exposed Buildings", "EVENT-BUILDING EXPOSURES", 348, 260),
        card("history-mmi", "Max MMI", "HIGHEST MMI", 648, 260),
        visual(
            "history-trend",
            "scatterChart",
            48,
            420,
            860,
            394,
            {
                "X": [("_Measures", "Timeline Year", True)],
                "Y": [("_Measures", "Magnitude", True)],
                "Size": [("_Measures", "Exposed Buildings", True)],
                "Category": [("dim_event", "Event", False)],
                "Tooltips": [
                    ("dim_event", "Event Date", False),
                    ("_Measures", "Exposed Population", True),
                ],
            },
            "EVENT TIME × MAGNITUDE  /  BUBBLE AREA = EXPOSED BUILDINGS",
        ),
        visual(
            "history-table",
            "tableEx",
            932,
            420,
            460,
            394,
            {
                "Values": [
                    ("dim_event", "Event", False),
                    ("dim_event", "Event Date", False),
                    ("_Measures", "Magnitude", True),
                    ("_Measures", "Exposed Buildings", True),
                    ("_Measures", "Exposed Population", True),
                ]
            },
            "EVENT CHRONOLOGY",
        ),
    ]
    build_page(
        "event-history",
        "Event History",
        "Event time along the horizontal axis, magnitude vertically, bubble size by thresholded building exposure.",
        history,
    )

    quality = [
        card("last-run", "Last Successful Run", "LAST LOCAL RUN", 48, 150, 360),
        card("hours", "Hours Since Last Run", "AGE OF LOCAL RUN / HOURS", 420, 150, 292),
        card("failures", "Failed Runs", "RECORDED FAILURES", 724, 150, 292),
        card("stations", "Validation Stations", "VALID STATIONS", 1028, 150, 364),
        card("mae", "Estimated MMI MAE", "STATION-WEIGHTED MAE", 48, 310, 360),
        chart(
            "source",
            "columnChart",
            "SHAKING SOURCE / EVENT COUNT",
            420,
            310,
            480,
            236,
            ("dim_event", "Shaking Source", False),
            ["Event Count"],
        ),
        visual(
            "quality-table",
            "tableEx",
            920,
            310,
            472,
            504,
            {
                "Values": [
                    ("dim_event", "Event", False),
                    ("dim_event", "Shaking Source", False),
                    ("_Measures", "Validation Stations", True),
                    ("_Measures", "Estimated MMI MAE", True),
                ]
            },
            "MODEL VALIDATION BY EVENT",
        ),
        visual(
            "limitations",
            "textbox",
            48,
            582,
            820,
            232,
            text=(
                "LOCAL SNAPSHOT ONLY. No policy or insured-value data are used. "
                "MAE is station-weighted and indicative, not an actuarial loss estimate. "
                "Building lifecycle dates are approximate; all ten historical replays use current outlines. "
                "Water cells and the Chatham Islands are outside the mapped exposure model."
            ),
        ),
    ]
    build_page(
        "data-health",
        "Data Health",
        "Local gold and SQLite snapshot; this page does not claim live Azure health.",
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
        'annotation PBI_ProTooling = ["DevMode"]\n\n' + refs + "\n",
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
        "dataColors": ["#F7D34D", "#FFF200", "#FFB300", "#FF6800", "#D7191C"],
        "background": "#F2EDDF",
        "foreground": "#171815",
        "tableAccent": "#171815",
        "textClasses": {
            "title": {"fontFace": "IBM Plex Sans", "color": "#171815", "fontSize": 18},
            "header": {"fontFace": "IBM Plex Sans", "color": "#171815", "fontSize": 12},
            "label": {"fontFace": "IBM Plex Sans", "color": "#171815", "fontSize": 10},
            "callout": {"fontFace": "IBM Plex Mono", "color": "#171815", "fontSize": 28},
        },
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"color": {"solid": {"color": "#F2EDDF"}}}],
                    "border": [{"show": True, "color": {"solid": {"color": "#D5D2C9"}}}],
                    "title": [
                        {
                            "fontFace": "IBM Plex Sans",
                            "fontSize": 11,
                            "fontColor": {"solid": {"color": "#171815"}},
                        }
                    ],
                }
            }
        },
    }
    write(PBIP / "nzhem-theme.json", theme)
    write(REPORT / "StaticResources/RegisteredResources/nzhem-theme.json", theme)
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
                {"name": "nzhem-theme.json", "path": "nzhem-theme.json", "type": "CustomTheme"}
            ],
        }
    ]
    write(report_path, report)
    print("Generated Power BI semantic model and five report pages")


if __name__ == "__main__":
    main()
