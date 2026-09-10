"""Phase 5 -- acceptance criteria for the BUILT artifacts, checked without Power BI.

Why this file exists
--------------------
`PHASE5.md` section 8.5 names the risk directly: MCP can change a measure between
two gate runs and leave no trace in the binary .pbix. The countermeasure written
there is "export the measure catalogue again and diff it against
`powerbi/DAX_Measures.md`". That diff was never mechanised, and on 2026-09-09 it
went wrong in exactly the predicted way -- Desktop saved the model it had loaded
BEFORE `05_measures.py` gained M120/M121, so the PBIP on disk carried 71 measures
against a catalogue of 73, the five public entry measures lost their
`[Entry Metric Count]` guard, and table V12 was back to a 10 x 7 crossjoin of
seventy rows while the review sheet recorded the forty-row fix as done.

Every check below is a criterion written BEFORE the fix and required to FAIL on
the state that prompted it. A check that passes on the broken build proves
nothing, so `main()` prints the per-criterion verdict rather than a single total.

Scope
-----
Only what can be measured from text on disk. Anything that needs the report
rendered -- the forty rows actually appearing in V12, the slicer actually listing
ten countries, ten small-multiple panels visible at once -- is criteria D1..D5 in
`docs/Phase5_Review.md` section 2c and is measured in Desktop or through MCP.

C5 deliberately compares the visual layer only. Desktop rewrites report-level and
page-level chrome on every save -- it bumped `version` to 5.68, moved
`activeSectionIndex` to the page last opened, added `linguisticSchemaSyncVersion`
and dropped `resourcePackages` -- and none of that is drift the catalogue owns.
What the catalogue does own is each visual's type, box, title, wells and filters,
and those must match exactly.

`objects` (the in-plot formatting layer) is NOT compared yet: no small-multiples
grid has ever been sampled from Desktop, so the catalogue cannot express one. Once
that shape is sampled and folded in, add it to the comparison.

Run:  python python\\05_test_artifacts.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import POWERBI  # noqa: E402

PYTHON_DIR = Path(__file__).resolve().parent

SEMANTIC_DIR = POWERBI / "ASEAN_Renewables.SemanticModel"
TABLES_DIR = SEMANTIC_DIR / "definition" / "tables"
REPORT_PATH = POWERBI / "ASEAN_Renewables.Report" / "report.json"
DAX_MARKDOWN = POWERBI / "DAX_Measures.md"

MEASURE_TABLE = "KPI_Measures"


def measure_table_path() -> Path:
    """Find the measure table by the name DECLARED inside it, not by file name.

    The two producers disagree on the file name and both are right: the builder
    writes `Measures.tmdl` while Desktop saves the same table as
    `KPI_Measures.tmdl`. TMDL takes the table name from the first line, so
    matching on the file name made this harness fail with FileNotFoundError the
    moment a build replaced a Desktop save.
    """
    for path in sorted(TABLES_DIR.glob("*.tmdl")):
        if path.read_text(encoding="utf-8").startswith(f"table {MEASURE_TABLE}"):
            return path
    raise AssertionError(f"no tmdl file declares `table {MEASURE_TABLE}` in {TABLES_DIR}")


# --------------------------------------------------------------------------
# Locked decisions. Everything else is derived from the catalogue, so a
# legitimate catalogue change does not need this file edited; these five are
# the choices that must NOT drift silently.
# --------------------------------------------------------------------------

# Agreed 2026-09-10: the country slicer lists the ASEAN-10 and nothing else.
# Every visual on all three pages is either is_asean-guarded or locked to
# Vietnam, and the one non-ASEAN quantity anywhere -- the World row -- is taken
# through ALL(DimEntity) and never sees this slicer. Gate B7's "no aggregate
# entities in the country list" is satisfied a fortiori.
# NOT is_aggregate = 0: that returns 216 rows because USSR is historical rather
# than aggregate, which is the trap PHASE5.md section 2.2 spells out.
LOCKED_COUNTRY_FILTER = ("DimEntity", "is_asean", (1,))

# Regression guard for manual item 6: technology_label resolves seven labels and
# three of them have no generation metric, so picking one blanks the page.
LOCKED_TECH_FILTER = ("DimMetric", "metric", ("generation",))

# The guard that keeps V12 at forty key rows instead of seventy.
ENTRY_GUARD_TOKEN = "[Entry Metric Count]"
ENTRY_GUARDED_MEASURES = (
    "Entry Status",
    "Entry Year Label",
    "Material Entry Status",
    "Material Entry Year Label",
    "Entry Lag From 2000",
)

PAGE3_ID = "03_SoSanh_ChanDoan"
PAGE3_VISUAL_COUNT = 18
V12_COLUMN_COUNT = 7
SMALL_MULTIPLE_VISUALS = ("V10", "V14")


def _load(module_name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(module_name, PYTHON_DIR / file_name)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {file_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


measures_module = _load("phase5_measures_probe", "05_measures.py")
visuals_module = _load("phase5_visuals_probe", "05_visuals.py")
report_module = _load("phase5_report_probe", "05_build_report.py")

CATALOGUE = list(measures_module.MEASURES)
VISUALS = list(visuals_module.VISUALS)


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------

def squash(text: str) -> str:
    """Collapse every run of whitespace, so indentation cannot cause a false diff."""
    return re.sub(r"\s+", " ", text).strip()


def wire_value(value: object) -> str:
    """A filter literal in the form the report layout stores it.

    Text is single-quoted, the way the sampled technology filter carries
    `'generation'`. A whole number takes the `L` suffix instead -- `is_asean` is
    int64, and quoting it would compare a number against a string and match
    nothing. This is the one encoding here not round-tripped through Desktop;
    criterion D3 is what confirms it against a rendered slicer.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return f"'{value}'"
    return f"{value}L"


def parse_tmdl_measures(path: Path) -> dict[str, dict[str, str]]:
    """Measure name -> {doc_code, expression}.

    TMDL indentation carries the structure: a measure opens at one tab, its
    properties sit at two, and a wrapped expression at three or more. Splitting on
    that is what keeps a multi-line CALCULATE from swallowing `formatString`.

    A `///` block runs to several lines and only the first carries the [M###]
    code, so a continuation line must not clear the pending code -- doing that
    dropped M036 and M050 and reported two measures missing that were there all
    along. Only a new declaration clears it.
    """
    measures: dict[str, dict[str, str]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    pending_code = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("\t///"):
            doc = re.match(r"^\t/// \[(M\d{3})\]", line)
            if doc:
                pending_code = doc.group(1)
            index += 1
            continue
        opened = re.match(r"^\tmeasure ('(?P<quoted>[^']+)'|(?P<bare>[\w@]+))\s*=(?P<inline>.*)$", line)
        if not opened:
            if re.match(r"^\t(column|partition|hierarchy) ", line):
                pending_code = ""
            index += 1
            continue
        name = opened.group("quoted") or opened.group("bare")
        body = [opened.group("inline")]
        index += 1
        while index < len(lines):
            nxt = lines[index]
            if nxt.startswith("\t\t\t") or not nxt.strip():
                body.append(nxt)
                index += 1
                continue
            break
        measures[name] = {"doc_code": pending_code, "expression": squash("\n".join(body))}
        pending_code = ""
    return measures


def parse_tmdl_columns() -> set[str]:
    """`Table.column` for every column declared in the model, for reference resolution."""
    columns: set[str] = set()
    for path in sorted(TABLES_DIR.glob("*.tmdl")):
        table = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            table_match = re.match(r"^table (?P<name>.+)$", line)
            if table_match:
                table = table_match.group("name").strip().strip("'")
                continue
            column_match = re.match(r"^\tcolumn ('(?P<quoted>[^']+)'|(?P<bare>[\w@]+))", line)
            if column_match and table:
                columns.add(f"{table}.{column_match.group('quoted') or column_match.group('bare')}")
    return columns


def load_report() -> dict[str, Any]:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def disk_visuals() -> dict[str, dict[str, Any]]:
    """Visual name -> the fields the catalogue owns, read back off report.json."""
    found: dict[str, dict[str, Any]] = {}
    for section in load_report()["sections"]:
        for container in section["visualContainers"]:
            config = json.loads(container["config"])
            single = config.get("singleVisual", {})
            title = ""
            title_block = single.get("vcObjects", {}).get("title")
            if title_block:
                raw = title_block[0]["properties"]["text"]["expr"]["Literal"]["Value"]
                title = raw[1:-1].replace("''", "'")
            found[config["name"]] = {
                "page": section["displayName"],
                "visual_type": single.get("visualType"),
                "box": (
                    container.get("x"),
                    container.get("y"),
                    container.get("width"),
                    container.get("height"),
                ),
                "title": title,
                "roles": {
                    role: [item.get("queryRef") for item in items]
                    for role, items in single.get("projections", {}).items()
                },
                "filters": json.loads(container.get("filters") or "[]"),
            }
    return found


def catalogue_visuals() -> dict[str, dict[str, Any]]:
    """The same fields, rendered from the catalogue rather than read from disk."""
    expected: dict[str, dict[str, Any]] = {}
    pages = dict(report_module.PAGES)
    for visual in VISUALS:
        expected[report_module.visual_name(visual["visual_id"])] = {
            "visual_id": visual["visual_id"],
            "page": pages[visual["page"]],
            "visual_type": visual["visual_type"],
            "box": (visual["x"], visual["y"], visual["width"], visual["height"]),
            "title": visual["title"],
            "roles": {role: list(refs) for role, refs in visual["roles"].items()},
            "filters": report_module.visual_filters(visual),
        }
    return expected


def filter_triples(filters: list[dict[str, Any]]) -> set[tuple[str, str, tuple[str, ...]]]:
    """(entity, property, values) for each visual-level filter, as written on disk."""
    triples = set()
    for item in filters:
        column = item["expression"]["Column"]
        entity = column["Expression"]["SourceRef"]["Entity"]
        prop = column["Property"]
        values = tuple(
            group[0]["Literal"]["Value"]
            for group in item["filter"]["Where"][0]["Condition"]["In"]["Values"]
        )
        triples.add((entity, prop, values))
    return triples


# --------------------------------------------------------------------------
# Criteria
# --------------------------------------------------------------------------

def c1_model_carries_every_catalogue_measure() -> str:
    """C1 -- every M### in the catalogue reaches the TMDL, and no measure is orphaned."""
    tmdl = parse_tmdl_measures(measure_table_path())
    catalogue_names = {m["name"] for m in CATALOGUE}
    catalogue_codes = {m["measure_id"] for m in CATALOGUE}
    tmdl_codes = {m["doc_code"] for m in tmdl.values() if m["doc_code"]}

    missing_codes = sorted(catalogue_codes - tmdl_codes)
    missing_names = sorted(catalogue_names - set(tmdl))
    extra_names = sorted(set(tmdl) - catalogue_names)
    if missing_codes or missing_names or extra_names:
        raise AssertionError(
            f"TMDL {len(tmdl)} measures vs catalogue {len(CATALOGUE)}; "
            f"missing codes {missing_codes}; missing names {missing_names}; "
            f"orphaned in TMDL {extra_names}"
        )
    return f"{len(tmdl)}/{len(CATALOGUE)} measures present"


def c2_entry_measures_carry_the_guard() -> str:
    """C2 -- the five public entry measures refuse a technology with no generation metric.

    Without this guard the V12 crossjoin returns Renewables total, Biofuel and
    Geothermal rows stamped NOT_OBSERVED_BY_2021, which asserts something false:
    nothing is measured there, so nothing failed to be observed either.
    """
    tmdl = parse_tmdl_measures(measure_table_path())
    unguarded = [
        name
        for name in ENTRY_GUARDED_MEASURES
        if ENTRY_GUARD_TOKEN not in tmdl.get(name, {}).get("expression", "")
    ]
    if unguarded:
        raise AssertionError(
            f"entry measures without {ENTRY_GUARD_TOKEN}: {unguarded} "
            "-- V12 renders 10 x 7 = 70 rows instead of 40"
        )
    return f"{len(ENTRY_GUARDED_MEASURES)}/{len(ENTRY_GUARDED_MEASURES)} entry measures guarded"


def c3_markdown_matches_the_catalogue() -> str:
    """C3 -- the section 8.5 diff: DAX_Measures.md must be the catalogue, not an older one."""
    text = DAX_MARKDOWN.read_text(encoding="utf-8")
    squashed = squash(text)
    listed = set(re.findall(r"^\| (M\d{3}) \|", text, flags=re.MULTILINE))
    catalogue_codes = {m["measure_id"] for m in CATALOGUE}

    missing_rows = sorted(catalogue_codes - listed)
    stale_rows = sorted(listed - catalogue_codes)
    missing_dax = sorted(
        m["measure_id"] for m in CATALOGUE if squash(m["dax_expression"]) not in squashed
    )
    if missing_rows or stale_rows or missing_dax:
        raise AssertionError(
            f"DAX_Measures.md rows {len(listed)} vs catalogue {len(catalogue_codes)}; "
            f"missing rows {missing_rows}; stale rows {stale_rows}; "
            f"expressions not found {missing_dax}"
        )
    return f"{len(listed)} rows and {len(CATALOGUE)} expressions match"


def c4_every_reference_resolves() -> str:
    """C4 -- each queryRef on disk names a real measure or column, in BOTH catalogue and model.

    A reference that survives in the model but has left the catalogue renders a
    visual that looks right and answers a superseded definition.
    """
    tmdl = parse_tmdl_measures(measure_table_path())
    columns = parse_tmdl_columns()
    catalogue_names = {m["name"] for m in CATALOGUE}
    known_columns = set(visuals_module.COLUMNS)

    unresolved: list[str] = []
    for name, visual in disk_visuals().items():
        for role, refs in visual["roles"].items():
            for ref in refs:
                entity, _, member = ref.partition(".")
                if entity == "KPI_Measures":
                    if member not in tmdl or member not in catalogue_names:
                        unresolved.append(f"{visual['page']}/{role}/{ref}")
                elif ref not in known_columns or ref not in columns:
                    unresolved.append(f"{visual['page']}/{role}/{ref}")
    if unresolved:
        raise AssertionError(f"references that do not resolve: {unresolved}")
    return "all queryRefs resolve in catalogue and model"


def c5_report_matches_the_catalogue() -> str:
    """C5 -- report.json is the catalogue rendered, visual for visual.

    This is the check that catches a Desktop save made from a stale load: the
    catalogue moves, Desktop writes the shape it had, and nothing complains.
    """
    expected = catalogue_visuals()
    actual = disk_visuals()

    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    if missing or extra:
        raise AssertionError(
            f"visual set differs -- missing from report.json {len(missing)}, "
            f"not in catalogue {len(extra)}"
        )

    drift: list[str] = []
    for name, want in expected.items():
        got = actual[name]
        for field in ("page", "visual_type", "box", "title", "roles"):
            if want[field] != got[field]:
                drift.append(f"{want['visual_id']}.{field}: catalogue={want[field]!r} disk={got[field]!r}")
        if filter_triples(want["filters"]) != filter_triples(got["filters"]):
            drift.append(
                f"{want['visual_id']}.filters: catalogue={sorted(filter_triples(want['filters']))} "
                f"disk={sorted(filter_triples(got['filters']))}"
            )
    if drift:
        raise AssertionError("report.json is behind the catalogue:\n  " + "\n  ".join(drift))
    return f"{len(expected)} visuals match the catalogue"


def c6_country_slicer_is_scoped() -> str:
    """C6 -- the country slicer is restricted, on every page, with a whole-number literal.

    `is_asean` is int64, so the literal is `1L`. The technology filter's sampled
    shape only ever carried text, so this encoding is the one detail here that has
    not been round-tripped through Desktop -- criterion D3 is what confirms it, and
    a slicer still listing 256 entities is the symptom if it is wrong.
    """
    entity, prop, values = LOCKED_COUNTRY_FILTER
    wire = tuple(wire_value(value) for value in values)

    declared = [v for v in VISUALS if v["visual_id"].startswith("FLT_COUNTRY_")]
    if len(declared) != 3:
        raise AssertionError(f"expected a country slicer on all three pages, found {len(declared)}")
    for visual in declared:
        if (entity, prop, values) not in {
            (e, p, tuple(vals)) for e, p, vals in visual.get("filters", ())
        }:
            raise AssertionError(
                f"{visual['visual_id']}: catalogue declares no {entity}[{prop}] = {values} filter "
                "-- the slicer lists all 256 entities including World, Africa and USSR"
            )

    on_disk = [v for v in disk_visuals().values() if v["visual_type"] == "listSlicer"
               and v["roles"].get("Values") == ["DimEntity.entity_label"]]
    if len(on_disk) != 3:
        raise AssertionError(f"report.json holds {len(on_disk)} country slicers, expected 3")
    for visual in on_disk:
        if (entity, prop, wire) not in filter_triples(visual["filters"]):
            raise AssertionError(
                f"{visual['page']}: country slicer on disk carries "
                f"{sorted(filter_triples(visual['filters']))}, expected {(entity, prop, wire)}"
            )
    return f"3/3 country slicers scoped to {entity}[{prop}] = {values[0]}"


def c7_technology_slicer_keeps_its_filter() -> str:
    """C7 -- regression guard for manual item 6, which the catalogue took over."""
    entity, prop, values = LOCKED_TECH_FILTER
    wire = tuple(wire_value(value) for value in values)
    on_disk = [v for v in disk_visuals().values() if v["visual_type"] == "listSlicer"
               and v["roles"].get("Values") == ["DimMetric.technology_label"]]
    if len(on_disk) != 3:
        raise AssertionError(f"report.json holds {len(on_disk)} technology slicers, expected 3")
    for visual in on_disk:
        if (entity, prop, wire) not in filter_triples(visual["filters"]):
            raise AssertionError(
                f"{visual['page']}: technology slicer lost its {entity}[{prop}] filter"
            )
    return f"3/3 technology slicers restricted to {values[0]}"


def c8_page3_layout_holds() -> str:
    """C8 -- page 3 keeps eighteen visuals inside the canvas, and the filter row does not move."""
    report = load_report()
    pages = dict(report_module.PAGES)
    section = next(s for s in report["sections"] if s["displayName"] == pages[PAGE3_ID])

    boxes = []
    for container in section["visualContainers"]:
        name = json.loads(container["config"])["name"]
        boxes.append((name, container["x"], container["y"],
                      container["x"] + container["width"],
                      container["y"] + container["height"]))
    if len(boxes) != PAGE3_VISUAL_COUNT:
        raise AssertionError(f"page 3 holds {len(boxes)} visuals, expected {PAGE3_VISUAL_COUNT}")

    off_canvas = [b[0] for b in boxes
                  if b[3] > visuals_module.CANVAS_W + 0.5 or b[4] > visuals_module.CANVAS_H + 0.5]
    if off_canvas:
        raise AssertionError(f"visuals running off the canvas: {off_canvas}")

    overlaps = [
        (a[0], b[0])
        for i, a in enumerate(boxes)
        for b in boxes[i + 1:]
        if a[1] < b[3] and b[1] < a[3] and a[2] < b[4] and b[2] < a[4]
    ]
    if overlaps:
        raise AssertionError(f"overlapping visuals on page 3: {overlaps}")

    rows: dict[str, set[tuple[float, float]]] = {}
    for visual in VISUALS:
        if visual["group"] == "Filter row":
            rows.setdefault(visual["visual_id"].rsplit("_", 1)[0], set()).add(
                (visual["x"], visual["y"])
            )
    moved = {stem: coords for stem, coords in rows.items() if len(coords) != 1}
    if len(rows) != 4 or moved:
        raise AssertionError(f"filter row is not identical across pages: {rows}")
    return f"{len(boxes)} visuals, 0 overlaps, filter row fixed on all three pages"


def c9_diagnostic_wells_intact() -> str:
    """C9 -- the wells Gate B9 reads: small multiples on V10/V14, seven columns on V12."""
    by_id = {v["visual_id"]: v for v in VISUALS}
    for visual_id in SMALL_MULTIPLE_VISUALS:
        if "Rows" not in by_id[visual_id]["roles"]:
            raise AssertionError(f"{visual_id} lost its small-multiples well")
    columns = by_id["V12"]["roles"]["Values"]
    if len(columns) != V12_COLUMN_COUNT:
        raise AssertionError(f"V12 has {len(columns)} columns, expected {V12_COLUMN_COUNT}")
    return f"V10/V14 keep the Rows well, V12 keeps {V12_COLUMN_COUNT} columns"


CRITERIA = (
    ("C1", c1_model_carries_every_catalogue_measure),
    ("C2", c2_entry_measures_carry_the_guard),
    ("C3", c3_markdown_matches_the_catalogue),
    ("C4", c4_every_reference_resolves),
    ("C5", c5_report_matches_the_catalogue),
    ("C6", c6_country_slicer_is_scoped),
    ("C7", c7_technology_slicer_keeps_its_filter),
    ("C8", c8_page3_layout_holds),
    ("C9", c9_diagnostic_wells_intact),
)


def main() -> int:
    failures: list[str] = []
    for code, check in CRITERIA:
        try:
            detail = check()
        except AssertionError as error:
            failures.append(code)
            print(f"{code} FAIL {check.__doc__.splitlines()[0].split('--', 1)[-1].strip()}")
            for line in str(error).splitlines():
                print(f"       {line}")
        else:
            print(f"{code} PASS {detail}")

    if failures:
        print(f"\nPHASE 5 ARTIFACT TEST: FAIL | failed={','.join(failures)} "
              f"| passed={len(CRITERIA) - len(failures)}/{len(CRITERIA)}")
        return 1
    print(f"\nPHASE 5 ARTIFACT TEST: PASS | {len(CRITERIA)}/{len(CRITERIA)} criteria "
          f"| measures={len(CATALOGUE)} | visuals={len(VISUALS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
