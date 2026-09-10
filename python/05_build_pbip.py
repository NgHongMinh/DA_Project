"""Phase 5 -- generate the Power BI project (PBIP) and the measure documentation.

A `.pbix` is a binary file only Power BI Desktop can write, so it cannot be
produced here. What can be produced is the text form of the same thing: a PBIP
project whose semantic model is TMDL. The user opens it once in Desktop and
saves it as `powerbi\\ASEAN_Renewables.pbix`.

Generating rather than hand-writing the TMDL matters for section 8.5 of
`PHASE5.md`: the model and `powerbi/DAX_Measures.md` come out of one catalogue
(`05_measures.py`), so a later `ExportTMDL` can be diffed against the markdown
and any difference that is not in the change log stands out.

Run:  python python\\05_build_pbip.py
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_contract as K  # noqa: E402
from config import CLEAN, POWERBI  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "phase5_measures", Path(__file__).resolve().parent / "05_measures.py"
)
_measures_module = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_measures_module)
MEASURES = _measures_module.MEASURES

MODEL = K.MODEL_NAME
SEMANTIC_DIR = POWERBI / f"{MODEL}.SemanticModel"
REPORT_DIR = POWERBI / f"{MODEL}.Report"
NAMESPACE = uuid.UUID("6f1e0d2c-4a3b-5c6d-8e9f-0a1b2c3d4e5f")

# Page tab names ship in ASCII and are renamed to Vietnamese inside Desktop,
# where they live in the binary .pbix. The page IDs themselves are the names
# `PHASE5.md` B6 locks.
PAGES = (
    ("01_TongQuan_ASEAN", "01 ASEAN overview"),
    ("02_VietNam_ChuyenSau", "02 Vietnam deep dive"),
    ("03_SoSanh_ChanDoan", "03 Comparison and diagnostics"),
)


def tag(*parts: str) -> str:
    """Deterministic lineage tag, so regenerating produces an identical tree."""
    return str(uuid.uuid5(NAMESPACE, ":".join(parts)))


# ---------------------------------------------------------------------------
# Column specifications -- declared explicitly, never left to type inference
# ---------------------------------------------------------------------------
# B2 step 5: FactEnergy[value] must be `double`. A fixed-decimal type truncates
# at four places, and 36.027 of 89.075 values carry more than four.

TABLES: dict[str, dict[str, Any]] = {
    "FactEnergy": {
        "source": "fact_energy.csv",
        "columns": [
            ("entity", "string", "type text"),
            ("year", "int64", "Int64.Type"),
            ("metric_key", "string", "type text"),
            ("value", "double", "type number"),
            ("value_class", "string", "type text"),
            ("source_file", "string", "type text"),
        ],
        "hidden_columns": ("source_file",),
    },
    "DimEntity": {
        "source": "dim_entity.csv",
        "columns": [
            ("entity", "string", "type text"),
            ("iso_code", "string", "type text"),
            ("entity_type", "string", "type text"),
            ("is_aggregate", "int64", "Int64.Type"),
            ("is_current_country_or_territory", "int64", "Int64.Type"),
            ("is_asean", "int64", "Int64.Type"),
            ("is_source_variant", "int64", "Int64.Type"),
            ("canonical_entity", "string", "type text"),
            ("continent", "string", "type text"),
            ("income_group", "string", "type text"),
        ],
        "hidden_columns": ("is_source_variant", "canonical_entity", "iso_code"),
    },
    "DimMetric": {
        "source": "dim_metric.csv",
        "columns": [
            ("metric_key", "string", "type text"),
            ("technology", "string", "type text"),
            ("metric", "string", "type text"),
            ("canonical_unit", "string", "type text"),
            ("source_unit", "string", "type text"),
            ("conversion_factor", "double", "type number"),
            ("source_file", "string", "type text"),
            ("source_column", "string", "type text"),
            ("scope", "string", "type text"),
            ("trace_threshold", "double", "type number"),
            ("analysis_start_year", "int64", "Int64.Type"),
            ("analysis_end_year", "int64", "Int64.Type"),
        ],
        "hidden_columns": (
            "source_unit", "conversion_factor", "source_file", "source_column",
        ),
    },
    "DimYear": {
        "source": "dim_year.csv",
        "columns": [
            ("year", "int64", "Int64.Type"),
            ("is_main_asean_window", "int64", "Int64.Type"),
        ],
        "hidden_columns": (),
    },
}

# Display labels stay ASCII. The Vietnamese wording the report needs -- "Thuy
# dien", "Viet Nam" and so on -- is typed into the visuals in Desktop, where it
# lives in the binary .pbix and never passes through a TMDL file. That keeps the
# fragile text layer out of the model entirely.
#
# `entity` and `technology` are already English in the source data; these columns
# only fix the casing so legends read "Hydro" rather than "hydro".
ENTITY_LABEL = {
    "Cambodia": "Cambodia",
    "Laos": "Laos",
    "Thailand": "Thailand",
    "Vietnam": "Vietnam",
    "World": "World",
}
TECHNOLOGY_LABEL = {
    "hydro": "Hydro",
    "other_renewables": "Other renewables",
    "wind": "Wind",
    "solar": "Solar",
    "renewables": "Renewables total",
    "biofuel": "Biofuel",
    "geothermal": "Geothermal",
}
# Stack order inherited from the Phase 4 charts, so the dashboard and the
# thirteen PNGs lay the technologies out the same way.
TECHNOLOGY_SORT = {
    "hydro": 1, "other_renewables": 2, "wind": 3, "solar": 4,
    "renewables": 5, "biofuel": 6, "geothermal": 7,
}


def switch_expression(column: str, mapping: dict[str, Any], *, quote: bool = True) -> str:
    parts = [f"SWITCH(\n            {column},"]
    for key, value in mapping.items():
        rendered = f'"{value}"' if quote else str(value)
        parts.append(f'            "{key}", {rendered},')
    parts.append(f"            {column if quote else '0'}\n        )")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# TMDL rendering
# ---------------------------------------------------------------------------

def block(expression: str, depth: int) -> str:
    """Indent a multi-line DAX/M expression under a TMDL property."""
    pad = "\t" * depth
    return "\n".join(f"{pad}{line}".rstrip() for line in expression.strip("\n").splitlines())


def m_partition(table: str, spec: dict[str, Any]) -> str:
    """Power Query partition reading exactly one named file.

    The file list is fixed on purpose (B2 step 6): pulling every CSV in the
    folder would let a stray file into the model. The culture argument on
    TransformColumnTypes pins parsing to "en-US" so a dot decimal in the CSV is
    read correctly even though the model itself displays in Vietnamese.
    """
    transforms = ", ".join(f'{{"{name}", {m_type}}}' for name, _, m_type in spec["columns"])
    return f'''let
    Source = Csv.Document(
        File.Contents( pCleanFolder & "\\{spec['source']}" ),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders( Source, [PromoteAllScalars = true] ),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {{{transforms}}},
        "en-US"
    )
in
    Typed'''


def render_source_table(name: str, spec: dict[str, Any]) -> str:
    lines = [f"table {name}", f"\tlineageTag: {tag('table', name)}", ""]
    for column, data_type, _ in spec["columns"]:
        lines.append(f"\tcolumn {column}")
        lines.append(f"\t\tdataType: {data_type}")
        if data_type == "int64":
            lines.append("\t\tformatString: 0")
        if column in spec["hidden_columns"]:
            lines.append("\t\tisHidden")
        lines.append(f"\t\tlineageTag: {tag('column', name, column)}")
        lines.append("\t\tsummarizeBy: none")
        lines.append(f"\t\tsourceColumn: {column}")
        lines.append("")

    if name == "DimEntity":
        lines += [
            "\t/// Display label for the entity. Vietnamese wording belongs on the",
            "\t/// report surface, not here: TMDL must stay ASCII.",
            "\tcolumn entity_label =",
            block(switch_expression("DimEntity[entity]", ENTITY_LABEL), 3),
            "\t\tdataType: string",
            f"\t\tlineageTag: {tag('column', name, 'entity_vi')}",
            "\t\tsummarizeBy: none",
            "",
        ]
    if name == "DimMetric":
        lines += [
            "\t/// Display label for the technology, cased for legends. Sorted by",
            "\t/// technology_sort so legends and slicers follow the Phase 4 stack",
            "\t/// order instead of the alphabet, which would open with Biofuel and",
            "\t/// Geothermal -- two technologies this dashboard never charts.",
            "\tcolumn technology_label =",
            block(switch_expression("DimMetric[technology]", TECHNOLOGY_LABEL), 3),
            "\t\tdataType: string",
            f"\t\tlineageTag: {tag('column', name, 'technology_vi')}",
            "\t\tsummarizeBy: none",
            "\t\tsortByColumn: technology_sort",
            "",
            "\t/// Technology display order, matching the Phase 4 chart stack order.",
            "\tcolumn technology_sort =",
            block(switch_expression("DimMetric[technology]", TECHNOLOGY_SORT, quote=False), 3),
            "\t\tdataType: int64",
            "\t\tformatString: 0",
            "\t\tisHidden",
            f"\t\tlineageTag: {tag('column', name, 'technology_sort')}",
            "\t\tsummarizeBy: none",
            "",
        ]

    lines.append(f"\tpartition {name} = m")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    lines.append(block(m_partition(name, spec), 3))
    lines.append("")
    return "\n".join(lines)


def render_calculated_table(name: str, columns: list[tuple[str, str]], expression: str) -> str:
    lines = [f"table {name}", f"\tlineageTag: {tag('table', name)}", ""]
    for column, data_type in columns:
        lines.append(f"\tcolumn {column}")
        lines.append(f"\t\tdataType: {data_type}")
        if data_type == "int64":
            lines.append("\t\tformatString: 0")
        lines.append(f"\t\tlineageTag: {tag('column', name, column)}")
        lines.append("\t\tsummarizeBy: none")
        lines.append(f"\t\tsourceColumn: [{column}]")
        lines.append("")
    lines.append(f"\tpartition {name} = calculated")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    lines.append(block(expression, 3))
    lines.append("")
    return "\n".join(lines)


def render_measures_table() -> str:
    """A measure-only table. Keeping measures off the fact table stops them
    inheriting a home-table filter nobody asked for, and gives one obvious place
    to look for every KPI definition."""
    # Named KPI_Measures to match the model that shipped in the .pbix. "Measures"
    # reads as a generic bucket next to the four real tables; the name is also
    # what ExportTMDL will report, so the text source has to agree with it.
    lines = [
        "table KPI_Measures",
        "\tisHidden",
        f"\tlineageTag: {tag('table', 'Measures')}",
        "",
    ]
    for measure in MEASURES:
        # In TMDL a description is a /// block placed BEFORE the object.
        description = f"[{measure['measure_id']}] {measure["description"]}"
        for line in description.splitlines():
            lines.append(f"\t/// {line}")
        lines.append(f"\tmeasure '{measure['name']}' =")
        lines.append(block(measure["dax_expression"], 3))
        if measure["format_string"]:
            lines.append(f"\t\tformatString: {measure['format_string']}")
        if measure["hidden"]:
            lines.append("\t\tisHidden")
        lines.append(f"\t\tlineageTag: {tag('measure', measure['name'])}")
        if measure["display_folder"]:
            lines.append(f"\t\tdisplayFolder: {measure['display_folder']}")
        lines.append("")
    # A measure table needs one column to exist; it is hidden from the report.
    lines += [
        "\tcolumn _placeholder",
        "\t\tdataType: string",
        "\t\tisHidden",
        f"\t\tlineageTag: {tag('column', 'Measures', '_placeholder')}",
        "\t\tsummarizeBy: none",
        "\t\tsourceColumn: [_placeholder]",
        "",
        "\tpartition KPI_Measures = calculated",
        "\t\tmode: import",
        "\t\tsource =",
        '\t\t\tROW( "_placeholder", "" )',
        "",
    ]
    return "\n".join(lines)


def render_relationships() -> str:
    """Three active one-to-many relationships, filtering dimension -> fact only.

    Nothing bidirectional and nothing many-to-many: an ambiguous filter path
    would make the ranking denominators depend on which visual asked.
    """
    blocks = []
    for from_table, from_column, to_table, to_column in K.RELATIONSHIPS:
        name = tag("rel", from_table, to_table)
        blocks.append(
            f"relationship {name}\n"
            f"\tfromColumn: {to_table}.{to_column}\n"
            f"\ttoColumn: {from_table}.{from_column}\n"
        )
    return "\n".join(blocks)


def render_model() -> str:
    table_names = list(TABLES) + list(K.SELECTOR_TABLES) + ["KPI_Measures"]
    refs = "\n".join(f"ref table {name}" for name in table_names)
    query_order = json.dumps(["pCleanFolder"] + list(TABLES), ensure_ascii=False)
    return f'''model Model
\tculture: vi-VN
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tdiscourageImplicitMeasures
\tsourceQueryCulture: en-US

\tannotation PBI_QueryOrder = {query_order}

\tannotation PBI_ProTooling = ["DevMode"]

{refs}

ref cultureInfo vi-VN
'''


def render_expressions() -> str:
    """The path parameter. Kept as a parameter so moving the project needs one
    edit, matching the `python/config.py` rule the rest of the project follows."""
    default = str(CLEAN).replace("\\", "\\\\")
    # The /// block must PRECEDE the object it describes. Trailing it after the
    # annotations parses as a description with nothing to attach to, and the
    # whole folder is rejected with "an object-description must be followed by
    # the actual object!".
    return f'''/// Folder holding the seven clean Phase 2 CSVs. One edit here moves every source.
expression pCleanFolder = "{default}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]
\tlineageTag: {tag('expression', 'pCleanFolder')}

\tannotation PBI_ResultType = Text
'''


def render_culture() -> str:
    return "cultureInfo vi-VN\n"


# ---------------------------------------------------------------------------
# Report shell (stage 1) -- three named but empty pages
# ---------------------------------------------------------------------------

def render_report() -> dict[str, Any]:
    sections = []
    for ordinal, (page_name, display_name) in enumerate(PAGES):
        sections.append(
            {
                "name": tag("page", page_name),
                "displayName": display_name,
                "ordinal": ordinal,
                "width": 1280,
                "height": 720,
                "displayOption": 1,
                "config": json.dumps(
                    {"visibility": 0, "defaultLayout": {"displayOption": 1}},
                    ensure_ascii=False,
                ),
                "filters": "[]",
                "visualContainers": [],
            }
        )
    # The legacy report layout carries no $schema of its own -- only the
    # `definition.pbir` alongside it does. Inventing one here is a way to get the
    # project rejected for a file that was otherwise fine.
    return {
        "config": json.dumps(
            {
                "version": "5.55",
                "themeCollection": {"baseTheme": {"name": "CY24SU10"}},
                "activeSectionIndex": 0,
                "defaultDrillFilterOtherVisuals": True,
                "settings": {
                    "useStylableVisualContainerHeader": True,
                    "defaultFilterActionIsDataFilter": True,
                },
            },
            ensure_ascii=False,
        ),
        "layoutOptimization": 0,
        "resourcePackages": [
            {
                "resourcePackage": {
                    "disabled": False,
                    "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": 202}],
                    "name": "SharedResources",
                    "type": 2,
                }
            }
        ],
        "sections": sections,
    }


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------

CATALOGUE_COLUMNS = (
    "measure_id", "name", "format_string", "unit", "unit_stored",
    "numerator", "denominator", "filter_behavior", "blank_rule",
    "source_metric_keys", "question_ids", "page_ids",
)


def render_dax_markdown() -> str:
    lines = [
        "# Danh mục phép đo DAX — Phase 5",
        "",
        "Tệp này được **sinh tự động** từ `python/05_measures.py`. Không sửa tay: sửa ở nguồn rồi",
        "chạy lại `python python\\05_build_pbip.py`.",
        "",
        f"Phiên bản phương pháp: `{K.METHOD_VERSION}` · Power BI Desktop: `{K.POWERBI_DESKTOP_VERSION}` ·",
        f"Dấu vân tay Phase 2: `{K.EXPECTED_PHASE2_INPUT_FINGERPRINT}`",
        "",
        "## Cách đọc hai cột đơn vị",
        "",
        "`unit_stored` là thang **lưu trữ** — thứ B10 đối chiếu với `03_fact_metrics.csv`.",
        "`format_string` là thang **hiển thị**. Việc ×100 chỉ được nằm ở `format_string`,",
        "không bao giờ nằm trong biểu thức. Trong toàn bộ mô hình chỉ `Share Electricity Pct`",
        "mang `unit_stored = pct` (thang 0–100); mọi tỷ lệ còn lại là `ratio` (thang 0–1).",
        "So một measure ratio `0,671023268910` với đích hiển thị `67,102326891` sẽ lệch `66,43`,",
        "không phải sai số làm tròn.",
        "",
        "## Bảng danh mục",
        "",
        "| " + " | ".join(CATALOGUE_COLUMNS) + " |",
        "|" + "|".join("---" for _ in CATALOGUE_COLUMNS) + "|",
    ]
    for measure in MEASURES:
        cells = []
        for column in CATALOGUE_COLUMNS:
            value = measure[column]
            if isinstance(value, tuple):
                value = ", ".join(value) if value else "—"
            cells.append(str(value).replace("|", "\\|") or "—")
        lines.append("| " + " | ".join(cells) + " |")

    lines += ["", "## Công thức và định nghĩa nghiệp vụ", ""]
    current_folder = None
    for measure in MEASURES:
        if measure["display_folder"] != current_folder:
            current_folder = measure["display_folder"]
            lines += [f"### {current_folder}", ""]
        lines += [
            f"#### `{measure['name']}` — {measure['measure_id']}",
            "",
            measure["description"],
            "",
            "```dax",
            f"{measure['name']} =",
            measure["dax_expression"],
            "```",
            "",
        ]
        detail = []
        if measure["numerator"]:
            detail.append(f"- **Tử số:** {measure['numerator']}")
        if measure["denominator"]:
            detail.append(f"- **Mẫu số:** {measure['denominator']}")
        if measure["filter_behavior"]:
            detail.append(f"- **Hành vi bộ lọc:** {measure['filter_behavior']}")
        if measure["blank_rule"]:
            detail.append(f"- **Quy tắc trống:** {measure['blank_rule']}")
        detail.append(
            f"- **Đơn vị:** lưu `{measure['unit_stored'] or '—'}` · "
            f"hiển thị `{measure['format_string'] or 'mặc định'}`"
        )
        if measure["source_metric_keys"]:
            detail.append(
                "- **Chỉ số nguồn:** " + ", ".join(f"`{k}`" for k in measure["source_metric_keys"])
            )
        lines += detail + [""]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write(path: Path, content: str) -> None:
    """Write a TMDL file as UTF-8 WITHOUT a byte order mark, ASCII-only.

    Power BI Desktop rejects a BOM outright -- `UTF8EncodingThrowOnBOM` refuses
    the file and the whole project fails to open with "Only text with UTF8
    encoding without BOM (byte order marks) is supported". Note that the MCP
    TMDL reader happily accepts a BOM, so it is NOT a faithful stand-in for
    Desktop on encoding: a folder that loads through MCP can still be unopenable.

    The content is also asserted to be pure ASCII. An earlier build carried
    Vietnamese display folders and descriptions and part of the model came back
    mojibaked ("Vi?t Nam", and one folder split into "03 Tỷ trọng" plus
    "03 T? tr?ng"). The cause was never pinned down, so the model layer is kept
    ASCII and Vietnamese is confined to the report surface, which Desktop stores
    in the binary .pbix and handles natively.
    """
    if not content.isascii():
        offenders = sorted({c for c in content if not c.isascii()})
        raise ValueError(
            f"{path.name}: TMDL must stay ASCII, found {''.join(offenders)!r}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\r\n")


def write_plain(path: Path, content: str) -> None:
    """Write UTF-8 without a BOM, for JSON and Markdown.

    A BOM must NOT go into the project JSON: those files are parsed by a reader
    that already assumes UTF-8, and a leading BOM is at best tolerated. Routing
    `write_json` through the TMDL writer would put a BOM in front of
    `ASEAN_Renewables.pbip` and risk the very open failure just fixed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\r\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_plain(path, json.dumps(payload, indent=2, ensure_ascii=False))


def platform(display_name: str, item_type: str) -> dict[str, Any]:
    return {
        "$schema": (
            "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/"
            "platformProperties/2.0.0/schema.json"
        ),
        "metadata": {"type": item_type, "displayName": display_name},
        "config": {"version": "2.0", "logicalId": tag("logical", item_type)},
    }


def main() -> int:
    for directory in (SEMANTIC_DIR, REPORT_DIR):
        if directory.exists():
            shutil.rmtree(directory)

    # -- semantic model ------------------------------------------------------
    write_json(SEMANTIC_DIR / ".platform", platform(MODEL, "SemanticModel"))
    write_json(
        SEMANTIC_DIR / "definition.pbism",
        {
            "$schema": (
                "https://developer.microsoft.com/json-schemas/fabric/item/"
                "semanticModel/definitionProperties/1.0.0/schema.json"
            ),
            "version": "4.2",
            "settings": {},
        },
    )

    definition = SEMANTIC_DIR / "definition"
    # Match the compatibility level created by Power BI Desktop 2.157.1354.0.
    # Reusing 1567 against an already-open 1606 Desktop database is rejected as
    # a compatibility-level downgrade.
    write(definition / "database.tmdl", "database\n\tcompatibilityLevel: 1606\n")
    write(definition / "model.tmdl", render_model())
    write(definition / "expressions.tmdl", render_expressions())
    write(definition / "relationships.tmdl", render_relationships())
    write(definition / "cultures" / "vi-VN.tmdl", render_culture())

    for name, spec in TABLES.items():
        write(definition / "tables" / f"{name}.tmdl", render_source_table(name, spec))

    write(
        definition / "tables" / "SelReportYear.tmdl",
        render_calculated_table(
            "SelReportYear",
            [("year", "int64")],
            f'SELECTCOLUMNS(\n'
            f'    GENERATESERIES( {K.YEAR_START}, {K.YEAR_END}, 1 ),\n'
            f'    "year", [Value]\n'
            f')',
        ),
    )
    write(
        definition / "tables" / "SelBaseYear.tmdl",
        render_calculated_table(
            "SelBaseYear",
            [("year", "int64")],
            f'SELECTCOLUMNS(\n'
            f'    GENERATESERIES( {K.YEAR_START}, {K.YEAR_END}, 1 ),\n'
            f'    "year", [Value]\n'
            f')',
        ),
    )
    write(
        definition / "tables" / "SelMode.tmdl",
        render_calculated_table(
            "SelMode",
            [("mode_key", "string"), ("mode_label", "string"), ("sort_order", "int64")],
            'DATATABLE(\n'
            '    "mode_key", STRING,\n'
            '    "mode_label", STRING,\n'
            '    "sort_order", INTEGER,\n'
            '    {\n'
            '        { "RENEWABLE_TOTAL", "Renewable total (hydro + wind + solar + other)", 1 },\n'
            '        { "MODERN_WIND_SOLAR", "Modern only (wind + solar)", 2 }\n'
            '    }\n'
            ')',
        ),
    )
    write(definition / "tables" / "Measures.tmdl", render_measures_table())

    # -- report shell --------------------------------------------------------
    write_json(REPORT_DIR / ".platform", platform(MODEL, "Report"))
    # Report definition version 4.0 is the current Desktop entry-point format.
    # It still supports the existing PBIR-Legacy report.json, so upgrading this
    # metadata pair does not require rewriting the report into a definition tree.
    write_json(
        REPORT_DIR / "definition.pbir",
        {
            "$schema": (
                "https://developer.microsoft.com/json-schemas/fabric/item/"
                "report/definitionProperties/2.0.0/schema.json"
            ),
            "version": "4.0",
            "datasetReference": {"byPath": {"path": f"../{MODEL}.SemanticModel"}},
        },
    )
    # The report layout is owned by 05_build_report.py, which renders the visual
    # catalogue. Writing an empty shell here as well would silently wipe every
    # visual on the next pbip rebuild, since this function clears REPORT_DIR
    # first. Run it as a subprocess rather than importing: the report builder
    # already imports THIS module for the page list.
    report_build = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "05_build_report.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    print(report_build.stdout.rstrip())
    if report_build.returncode != 0:
        print(report_build.stderr.rstrip(), file=sys.stderr)
        raise RuntimeError("report layout build failed")

    # -- project pointer -----------------------------------------------------
    # The .pbip shortcut uses its own schema family -- `fabric/pbip/pbipProperties`,
    # NOT the `fabric/item/.../definitionProperties` family the artifact files use.
    # Desktop validates this string against a regex and refuses to open the whole
    # project if it does not match, so it is spelled out here rather than derived.
    write_json(
        POWERBI / f"{MODEL}.pbip",
        {
            "$schema": (
                "https://developer.microsoft.com/json-schemas/fabric/pbip/"
                "pbipProperties/1.0.0/schema.json"
            ),
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{MODEL}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )

    write_plain(POWERBI / "DAX_Measures.md", render_dax_markdown())

    files = sorted(p for p in POWERBI.rglob("*") if p.is_file())
    print(
        f"PHASE 5 PBIP BUILD: PASS | measures={len(MEASURES)} | "
        f"tables={len(TABLES) + len(K.SELECTOR_TABLES) + 1} | "
        f"relationships={len(K.RELATIONSHIPS)} | pages={len(PAGES)} | files={len(files)}"
    )
    print(f"  -> {POWERBI / (MODEL + '.pbip')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
