"""Phase 5 -- the single source of truth for every visual on the dashboard.

`05_build_report.py` renders this catalogue into the Power BI report layout.
Same one-source rule the measures follow: the catalogue here and the JSON on disk
cannot drift, because the JSON is generated and never hand-edited.

The shapes below are not guesses. Power BI Desktop 2.157.1354.0 was asked to
build one visual of each archetype against this very model, and the layout it
wrote back was read to learn the exact role names, query structure and type
codes. That sample is what the renderer replicates:

    cardVisual            role "Data"
    lineChart             roles "Category", "Y", "Series", "Rows" (small multiples)
    clusteredBarChart     roles "Category", "Y"
    tableEx               role  "Values" (ordered list)
    advancedSlicerVisual  role  "Values"   -- numeric slicer
    listSlicer            role  "Values"   -- categorical slicer

Only those six types are used. Adding a seventh would mean guessing role names
again, which is exactly what the sampling step existed to avoid. That rule is
why page 3 has no scatter plot: the capacity-factor indicator is drawn as a
small-multiple line chart instead, since `scatterChart` has never been sampled.

`listSlicer` replaced `textSlicer` after Desktop converted the four slicers
itself and saved the result -- the converted form is now the sampled one.

Titles are ASCII English on purpose. Vietnamese wording is typed over them in
Desktop, where it lives in the binary .pbix; the model and report text files stay
ASCII after a Vietnamese build came back mojibaked.

The coordinates are the ones the project owner tuned by hand on page 1 and saved
back through Desktop. They are captured here so a regeneration reproduces that
arrangement instead of resetting it to the script's first-pass grid.
"""
from __future__ import annotations

from typing import Any, Final

# Canvas was raised from the 720 default to 1000 when page 1 was laid out.
CANVAS_W: Final = 1280
CANVAS_H: Final = 1000

PAGE1: Final = "01_TongQuan_ASEAN"
PAGE2: Final = "02_VietNam_ChuyenSau"
PAGE3: Final = "03_SoSanh_ChanDoan"

# Column registry. `underlyingType` and `format` are the codes Desktop wrote for
# these very columns: 1 = text, 260 = whole number, 259 = decimal.
COLUMNS: Final[dict[str, dict[str, Any]]] = {
    "DimYear.year": {"entity": "DimYear", "property": "year", "type": 260, "format": "0"},
    "DimEntity.entity_label": {"entity": "DimEntity", "property": "entity_label", "type": 1},
    "DimMetric.technology_label": {"entity": "DimMetric", "property": "technology_label", "type": 1},
    "SelReportYear.year": {"entity": "SelReportYear", "property": "year", "type": 260, "format": "0"},
    "SelBaseYear.year": {"entity": "SelBaseYear", "property": "year", "type": 260, "format": "0"},
    "SelMode.mode_key": {"entity": "SelMode", "property": "mode_key", "type": 1},
}


def _v(
    visual_id: str,
    page: str,
    visual_type: str,
    box: tuple[float, float, float, float],
    roles: dict[str, list[str]],
    *,
    title: str = "",
    group: str = "",
    note: str = "",
    filters: tuple[tuple[str, str, tuple[str, ...]], ...] = (),
) -> dict[str, Any]:
    x, y, width, height = box
    return {
        "visual_id": visual_id,
        "page": page,
        "visual_type": visual_type,
        "x": float(x),
        "y": float(y),
        "width": float(width),
        "height": float(height),
        "roles": roles,
        "title": title,
        "group": group,
        "note": note,
        # (entity, column, values) -- a visual-level categorical filter.
        "filters": filters,
    }


# ---------------------------------------------------------------------------
# Shared grid, taken from the hand-tuned page 1
# ---------------------------------------------------------------------------
# Every page reuses these boxes so the filter row sits in one place and the eye
# lands in the same spot when the viewer switches tabs -- what B6 asks for.

BOX_FLT_YEAR: Final = (2.5, 7.5, 310.0, 203.75)
BOX_FLT_MODE: Final = (330.0, 7.5, 300.0, 86.25)
BOX_FLT_COUNTRY: Final = (651.25, 0.0, 300.0, 93.75)
BOX_FLT_TECH: Final = (961.25, 0.0, 300.0, 93.75)

BOX_KPI: Final = (
    (2.5, 220.0, 310.0, 161.25),
    (325.0, 220.0, 310.0, 161.25),
    (651.25, 220.0, 310.0, 161.25),
    (966.25, 220.0, 310.0, 161.25),
)

BOX_MAIN_LEFT: Final = (15.0, 413.75, 628.0, 268.0)
BOX_PANEL_TOP: Final = (651.25, 413.75, 628.0, 130.0)
BOX_PANEL_BOTTOM: Final = (651.25, 551.25, 628.0, 130.0)
BOX_LOWER_LEFT: Final = (15.0, 711.25, 628.0, 250.0)
BOX_LOWER_RIGHT: Final = (652.5, 711.25, 627.5, 265.0)
# 976.25 + 23.75 lands exactly on the 1000pt edge. At the original 24.0 the
# footer ran a quarter point past it, which the +0.5 tolerance in validate()
# let through but a PDF export would clip -- and Gate B10 asks for three pages
# with nothing cut off.
BOX_FOOTER: Final = (2.5, 976.25, 1264.0, 23.75)

# Page 2 splits the lower-left box into two stacked panels, using the same 7.5pt
# gutter as BOX_PANEL_TOP/BOTTOM. The pair ends at 961.25, exactly where the
# single box used to end, so nothing else on the page has to move.
BOX_LOWER_LEFT_TOP: Final = (15.0, 711.25, 628.0, 121.25)
BOX_LOWER_LEFT_BOTTOM: Final = (15.0, 840.0, 628.0, 121.25)

# Page 3 needs a fifth slicer and three status readouts that the other two pages
# do not. They go in the band between the short slicers (which stop at 93.75)
# and the KPI row (which starts at 220), so the shared filter row keeps the exact
# position B6 asks for and nothing has to move on pages 1 and 2.
BOX_FLT_BASEYEAR: Final = (330.0, 100.0, 300.0, 104.0)
BOX_STATUS_LEFT: Final = (651.25, 100.0, 148.0, 93.75)
BOX_STATUS_MIDDLE: Final = (803.25, 100.0, 148.0, 93.75)
BOX_STATUS_RIGHT: Final = (961.25, 100.0, 300.0, 93.75)


def _filter_row(page: str, suffix: str) -> list[dict[str, Any]]:
    """The shared filter row: four slicers, identical position on every page."""
    return [
        _v(f"FLT_YEAR_{suffix}", page, "advancedSlicerVisual", BOX_FLT_YEAR,
           {"Values": ["SelReportYear.year"]}, title="Report year",
           group="Filter row", note="means up to the selected year"),
        _v(f"FLT_MODE_{suffix}", page, "listSlicer", BOX_FLT_MODE,
           {"Values": ["SelMode.mode_key"]}, title="Measure mode",
           group="Filter row", note="renewable total vs wind + solar only"),
        _v(f"FLT_COUNTRY_{suffix}", page, "listSlicer", BOX_FLT_COUNTRY,
           {"Values": ["DimEntity.entity_label"]}, title="Country",
           group="Filter row",
           note="restricted to the ASEAN-10; entity_label otherwise resolves all 256 "
                "entities and offers World, Africa and USSR beside the ten countries. "
                "What each page DOES with a selection still differs -- read the titles",
           filters=(("DimEntity", "is_asean", (1,)),)),
        _v(f"FLT_TECH_{suffix}", page, "listSlicer", BOX_FLT_TECH,
           {"Values": ["DimMetric.technology_label"]}, title="Technology",
           group="Filter row",
           note="restricted to the four technologies that HAVE a generation metric; "
                "the other three labels blank the page with no explanation",
           filters=(("DimMetric", "metric", ("generation",)),)),
    ]


def _footer(page: str, suffix: str) -> dict[str, Any]:
    return _v(f"FOOTER_{suffix}", page, "cardVisual", BOX_FOOTER,
              {"Data": ["KPI_Measures.Footer Note"]}, group="Footer",
              note="source, window, why 2022 was dropped, aggregates excluded")


VISUALS: Final[list[dict[str, Any]]] = []

# ---------------------------------------------------------------------------
# Page 1 -- ASEAN overview (V01-V04)
# ---------------------------------------------------------------------------

VISUALS += _filter_row(PAGE1, "01")

# V01 -- regional KPI row. Each card names its own scope: these deliberately
# ignore the country slicer, and the World card is not an ASEAN figure at all.
for _index, (_measure, _label) in enumerate([
    ("ASEAN Gen TWh", "ASEAN-10 total (TWh) - selected year"),
    ("World Gen TWh", "World total (TWh) - source-published World row"),
    ("ASEAN Share World", "ASEAN-10 share of World - selected year"),
    ("Above 0.05 TWh N", "ASEAN-10 countries at or above 0.05 TWh"),
]):
    VISUALS.append(
        _v(f"V01_{_index + 1}", PAGE1, "cardVisual", BOX_KPI[_index],
           {"Data": [f"KPI_Measures.{_measure}"]}, title=_label,
           group="V01", note="ignores the country slicer on purpose")
    )

VISUALS.append(
    _v("V02", PAGE1, "lineChart", BOX_MAIN_LEFT,
       {"Category": ["DimYear.year"],
        "Y": ["KPI_Measures.ASEAN Gen TWh ToDate"],
        "Series": ["DimMetric.technology_label"]},
       title="ASEAN-10 renewable mix by technology, 2000 to selected year",
       group="V02")
)

# V04 -- ASEAN against World on two separate panels. Never a dual axis: with two
# scales on one frame any correlation can be manufactured by choosing them.
VISUALS.append(
    _v("V04_ASEAN", PAGE1, "lineChart", BOX_PANEL_TOP,
       {"Category": ["DimYear.year"], "Y": ["KPI_Measures.ASEAN Gen TWh ToDate"]},
       title="Panel 1 of 2 - ASEAN-10 total (TWh)", group="V04",
       note="separate panel, shared x axis, no dual axis")
)
VISUALS.append(
    _v("V04_WORLD", PAGE1, "lineChart", BOX_PANEL_BOTTOM,
       {"Category": ["DimYear.year"], "Y": ["KPI_Measures.World Gen TWh ToDate"]},
       title="Panel 2 of 2 - World total (TWh), source-published row", group="V04",
       note="the World row as published, never the sum of countries")
)

# V03 -- rank on both measures. Power BI has no dumbbell, so a clustered bar
# carries the rank and the gain per country and the shift is read as the gap.
VISUALS.append(
    _v("V03", PAGE1, "clusteredBarChart", BOX_LOWER_LEFT,
       {"Category": ["DimEntity.entity_label"],
        "Y": ["KPI_Measures.ASEAN Rank", "KPI_Measures.Modern Rank Gain"]},
       title="ASEAN rank and the gain from switching to wind + solar",
       group="V03", note="positive gain = better rank on the modern measure")
)
VISUALS.append(
    _v("V03_TABLE", PAGE1, "tableEx", BOX_LOWER_RIGHT,
       {"Values": ["DimEntity.entity_label",
                   "KPI_Measures.ASEAN Rank",
                   "KPI_Measures.Modern Rank Gain",
                   "KPI_Measures.Country Share ASEAN"]},
       title="Rank detail - ASEAN-10, selected year and mode", group="V03")
)

VISUALS.append(_footer(PAGE1, "01"))

# ---------------------------------------------------------------------------
# Page 2 -- Vietnam deep dive (V05-V09)
# ---------------------------------------------------------------------------
# Every figure here comes from a VN-prefixed measure, which pins the entity to
# Vietnam inside the DAX. A country picked on page 1 or page 3 therefore cannot
# drag this page onto a different subject -- the lock B6 asks for, without
# needing a page-filter JSON shape that has never been sampled from Desktop.

VISUALS += _filter_row(PAGE2, "02")

for _index, (_measure, _label) in enumerate([
    ("VN Gen TWh @Year", "Vietnam total (TWh) - selected year"),
    ("VN Share Electricity Pct @Year", "Vietnam share of its own electricity (%)"),
    ("VN Country Share ASEAN", "Vietnam share of the ASEAN-10 total"),
    # A rank without its denominator is unreadable, and ranked_n moves with both
    # year and mode, so it cannot be typed into the title either. One label
    # measure carries both ranks with both denominators -- and when the ASEAN
    # rank is undefined it shows the reason in place of a blank card.
    ("VN Rank Label", "Vietnam rank - ASEAN and world, selected year"),
]):
    VISUALS.append(
        _v(f"V05_{_index + 1}", PAGE2, "cardVisual", BOX_KPI[_index],
           {"Data": [f"KPI_Measures.{_measure}"]}, title=_label,
           group="V05", note="locked to Vietnam inside the measure")
    )

VISUALS.append(
    _v("V06", PAGE2, "lineChart", BOX_MAIN_LEFT,
       {"Category": ["DimYear.year"],
        "Y": ["KPI_Measures.VN Gen TWh ToDate"],
        "Series": ["DimMetric.technology_label"]},
       title="Vietnam generation by technology, 2000 to selected year",
       group="V06")
)

# V07 -- the pair Gate B8 is most specific about. TWh and share of electricity
# are different quantities on different scales; putting them on one frame invites
# reading a trend in one as a cause of the other. Two panels, two axes, no claim.
VISUALS.append(
    _v("V07_TWH", PAGE2, "lineChart", BOX_PANEL_TOP,
       {"Category": ["DimYear.year"], "Y": ["KPI_Measures.VN Gen TWh ToDate"]},
       title="Panel 1 of 2 - Vietnam output (TWh)", group="V07",
       note="separate panel from the share; no dual axis")
)
VISUALS.append(
    _v("V07_SHARE", PAGE2, "lineChart", BOX_PANEL_BOTTOM,
       {"Category": ["DimYear.year"], "Y": ["KPI_Measures.VN Share Electricity Pct ToDate"]},
       title="Panel 2 of 2 - Vietnam share of electricity (%)", group="V07",
       note="different quantity and scale -- do not infer one from the other")
)

# V08 -- "position in ASEAN AND in the world", so it takes two panels rather than
# one. Both series are ToDate measures: the @Year versions pin the year to the
# slicer, and a line built on them is flat by construction.
VISUALS.append(
    _v("V08_ASEAN", PAGE2, "lineChart", BOX_LOWER_LEFT_TOP,
       {"Category": ["DimYear.year"],
        "Y": ["KPI_Measures.VN Country Share ASEAN ToDate"]},
       title="Panel 1 of 2 - Vietnam share of the ASEAN-10 total",
       group="V08", note="denominator is the fixed ASEAN_SUM_10")
)
VISUALS.append(
    _v("V08_GLOBAL", PAGE2, "lineChart", BOX_LOWER_LEFT_BOTTOM,
       {"Category": ["DimYear.year"], "Y": ["KPI_Measures.VN Global Rank ToDate"]},
       title="Panel 2 of 2 - Vietnam global rank (lower is better)",
       group="V08",
       note="INVERT THE Y AXIS IN DESKTOP so rank 1 sits at the top -- invertAxis "
            "lives in the visual objects block, which this project does not generate, "
            "so the chart reads upside down until that is done by hand")
)

VISUALS.append(
    _v("V09", PAGE2, "tableEx", BOX_LOWER_RIGHT,
       {"Values": ["DimYear.year",
                   "KPI_Measures.VN Gen TWh ToDate",
                   "KPI_Measures.VN Share Electricity Pct ToDate",
                   "KPI_Measures.VN YoY",
                   "KPI_Measures.VN ASEAN Rank ToDate",
                   "KPI_Measures.VN Global Rank ToDate",
                   "KPI_Measures.Global Ranked N ToDate",
                   "KPI_Measures.VN Direction Relation"]},
       title="Vietnam year detail - output, share, growth, rank and direction",
       group="V09",
       note="every column is a ToDate measure, so the rows stop at the selected year "
            "and the pre-2000 years never appear; Ranked N is the denominator for the "
            "global rank in THAT row, not in the slicer year")
)

VISUALS.append(_footer(PAGE2, "02"))

# ---------------------------------------------------------------------------
# Page 3 -- comparison and diagnostics (V10-V14)
# ---------------------------------------------------------------------------
# This page is the first to put DimEntity[entity_label] on an axis and ask for a
# country-level number, so every measure it uses carries an is_asean guard inside
# the DAX (M110-M119). Without one the axis resolves all 256 entities and World
# lands in a chart captioned ASEAN. Same reasoning as the Vietnam lock on page 2:
# scope belongs in the measure, not in a page-filter shape nobody has sampled.

VISUALS += _filter_row(PAGE3, "03")

# The base year drives indexation and the growth-contribution period, so it sits
# with V11 rather than in the shared filter row -- the row must stay at exactly
# four slicers on all three pages, which validate() checks.
VISUALS.append(
    _v("FLT_BASEYEAR_03", PAGE3, "advancedSlicerVisual", BOX_FLT_BASEYEAR,
       {"Values": ["SelBaseYear.year"]}, title="Base year - index and growth period",
       group="V11", note="default 2010; a base later than the report year returns blank")
)

# V13 part one -- the concentration row. All four are held on the 0-1 scale;
# top-1 and top-3 are shown as percentages and HHI/Gini are not, which is the
# split PHASE5.md 5.4 locks.
for _index, (_measure, _label) in enumerate([
    ("Top1 Share", "Top-1 share of the ASEAN-10 total"),
    ("Top3 Share", "Top-3 share of the ASEAN-10 total"),
    ("HHI", "HHI concentration (0-1, zeros kept)"),
    ("Gini", "Gini inequality (0-1, ten countries)"),
]):
    VISUALS.append(
        _v(f"V13_{_index + 1}", PAGE3, "cardVisual", BOX_KPI[_index],
           {"Data": [f"KPI_Measures.{_measure}"]}, title=_label,
           group="V13", note="denominator is always the fixed ASEAN_SUM_10")
    )

# The four cards above go blank together in the year 2000 on the modern measure,
# because the regional total is zero. A blank card reads as a bug, so the reason
# sits beside them rather than nowhere -- the same argument that produced the
# rank label on page 2.
VISUALS.append(
    _v("V13_STATUS", PAGE3, "cardVisual", BOX_STATUS_LEFT,
       {"Data": ["KPI_Measures.Concentration Status"]},
       title="Why the four cards are blank", group="V13",
       note="reads NOT_DEFINED/ZERO_DENOMINATOR in 2000 on the modern measure, "
            "and stays empty whenever the four cards do have values")
)
VISUALS.append(
    _v("V14_COVERAGE", PAGE3, "cardVisual", BOX_STATUS_MIDDLE,
       {"Data": ["KPI_Measures.Capacity Factor Country N"]},
       title="Countries with capacity data", group="V14",
       note="2 for wind, 4 for solar, 4 with no technology picked -- never all ten")
)
VISUALS.append(
    _v("V_COMPLETE", PAGE3, "cardVisual", BOX_STATUS_RIGHT,
       {"Data": ["KPI_Measures.ASEAN Completeness Label"]},
       title="Components have / need - ASEAN-10 at the selected year", group="V13",
       note="4/4 for one country, 40/40 for the ASEAN-10 aggregate, 10/10 on a single "
            "technology -- the check Phase5_Review 3.4 asks for and no page carried. "
            "The scoped M121, not the bare M082: read unscoped on a card the label "
            "answers for all 256 entities across all 57 years")
)

# V10 -- the ten-country grid. `Rows` is the small-multiples well; the visual is
# still a lineChart, so no new archetype is introduced. 10 countries x 22 years
# is the 220 points Gate B9 counts.
VISUALS.append(
    _v("V10", PAGE3, "lineChart", BOX_MAIN_LEFT,
       {"Category": ["DimYear.year"],
        "Y": ["KPI_Measures.ASEAN Country Gen TWh ToDate"],
        "Rows": ["DimEntity.entity_label"]},
       title="Small multiples - ASEAN-10 output by country, 2000 to selected year",
       group="V10",
       note="set the Y axis to shared or independent in Desktop; Phase 4 published "
            "both (C05 shared, C06 free) and the reading changes between them")
)

VISUALS.append(
    _v("V11", PAGE3, "lineChart", BOX_PANEL_TOP,
       {"Category": ["DimYear.year"],
        "Y": ["KPI_Measures.ASEAN Indexed 100"],
        "Series": ["DimEntity.entity_label"]},
       title="Indexed trajectory, base year = 100", group="V11",
       note="a zero base returns blank rather than an infinity")
)

# V13 part two -- contribution to the region's GROSS positive addition. Declines
# are clipped, not netted, so the shares describe who added capacity to the
# region rather than who grew fastest in percentage terms.
VISUALS.append(
    _v("V13_GROWTH", PAGE3, "clusteredBarChart", BOX_PANEL_BOTTOM,
       {"Category": ["DimEntity.entity_label"],
        "Y": ["KPI_Measures.Positive Growth Share"]},
       title="Share of the ASEAN-10 gross positive addition, base year to selected year",
       group="V13", note="denominator is GROSS_POSITIVE_ADDITION, never net growth")
)

# V14 -- two panels, wind and solar, through the small-multiples well again.
# The measures behind it now follow the technology filter (M070/M071 moved from
# ALL to KEEPFILTERS), which is what makes the 2-against-4 coverage readable.
VISUALS.append(
    _v("V14", PAGE3, "lineChart", BOX_LOWER_LEFT,
       {"Category": ["DimYear.year"],
        "Y": ["KPI_Measures.ASEAN Capacity Factor"],
        "Series": ["DimEntity.entity_label"],
        "Rows": ["DimMetric.technology_label"]},
       title="Approximate capacity factor - end-of-year capacity, indicator only",
       group="V14",
       note="TWh / (GW x 8.76) on end-of-year capacity. Coverage is partial: wind has "
            "Philippines and Thailand only, solar adds Malaysia and Vietnam. It is NOT "
            "a measure of technical efficiency and ranks nothing")
)

# V12 -- forty key rows, and eighty status values because both threshold families
# are carried. Deliberately NOT narrowed by the report year: the statuses are
# defined against the whole window, which is what NOT_OBSERVED_BY_2021 asserts.
VISUALS.append(
    _v("V12", PAGE3, "tableEx", BOX_LOWER_RIGHT,
       {"Values": ["DimEntity.entity_label",
                   "DimMetric.technology_label",
                   "KPI_Measures.Entry Year Label",
                   "KPI_Measures.Entry Status",
                   "KPI_Measures.Entry Lag From 2000",
                   "KPI_Measures.Material Entry Year Label",
                   "KPI_Measures.Material Entry Status"]},
       title="Technology entry and censoring - ASEAN-10, whole 2000-2021 window",
       group="V12",
       note="40 rows, 80 status values. A censored row keeps its status and shows no "
            "year: substituting 2000 or 2021 would invent an entry nobody observed")
)

VISUALS.append(_footer(PAGE3, "03"))


def by_page(page: str) -> list[dict[str, Any]]:
    return [v for v in VISUALS if v["page"] == page]


def validate() -> None:
    ids = [v["visual_id"] for v in VISUALS]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate visual_id")
    for v in VISUALS:
        if not v["roles"]:
            raise RuntimeError(f"{v['visual_id']}: no roles")
        # Report text files stay ASCII for the same reason TMDL does.
        for field in ("title", "note", "group"):
            if not str(v[field]).isascii():
                raise RuntimeError(f"{v['visual_id']}.{field}: must be ASCII")
        if v["x"] < 0 or v["y"] < 0:
            raise RuntimeError(f"{v['visual_id']}: negative position")
        if v["x"] + v["width"] > CANVAS_W + 0.5 or v["y"] + v["height"] > CANVAS_H + 0.5:
            raise RuntimeError(
                f"{v['visual_id']}: runs off the {CANVAS_W}x{CANVAS_H} canvas"
            )

    # The filter row is only useful if it does not move between pages.
    for page in (PAGE1, PAGE2, PAGE3):
        row = {v["visual_id"].rsplit("_", 1)[0]: (v["x"], v["y"])
               for v in VISUALS if v["page"] == page and v["group"] == "Filter row"}
        if len(row) != 4:
            raise RuntimeError(f"{page}: filter row must hold four slicers")
    boxes = {v["group"]: None for v in VISUALS}
    if "Filter row" not in boxes:
        raise RuntimeError("no filter row defined")


validate()
