"""Phase 5 -- the single source of truth for every DAX measure in the dashboard.

`05_build_pbip.py` renders this catalogue into the TMDL model and into
`powerbi/DAX_Measures.md`. Keeping one source is what makes section 8.5 of
`PHASE5.md` enforceable: after any MCP write, `ExportTMDL` is diffed against the
generated markdown, and a difference that is not in the change log has to be
explained.

Every entry carries the columns Gate B4 demands:
    measure_id, name, dax_expression, description, format_string, unit,
    unit_stored, numerator, denominator, filter_behavior, blank_rule,
    source_metric_keys, question_ids, page_ids

`unit_stored` is the scale the value is HELD at and is what B10 reconciles
against `03_fact_metrics.csv`; `format_string` is only the scale it is SHOWN at.
Multiplying by 100 belongs in `format_string` and never in the expression.

Everything here is ASCII on purpose. Power BI Desktop reads TMDL as UTF-8 and
rejects a byte order mark outright, and an earlier build with Vietnamese folder
names came back mojibaked with one folder split in two. Vietnamese wording for
the dashboard is typed into the visuals in Desktop, where it lives in the binary
.pbix and never passes through a text file.
"""
from __future__ import annotations

from typing import Any, Final

# Display formats. The model culture is vi-VN, so "#,0.0" renders as 289,7 --
# matching the thirteen Phase 4 charts. The format string itself stays ASCII.
FMT_TWH: Final = "#,0.0###"
FMT_RATIO_PCT: Final = "0.0000%"
# A pct-stored measure already holds 0-100, so the percent sign has to be a
# LITERAL in the format string -- Power BI's "%" token multiplies by 100 and
# would turn 42,578747 into 4.257,8747%. The literal is what keeps this card
# readable next to a ratio card: without it the pair showed "42,5787" beside
# "35,9800%" and nothing on screen said the two were not the same scale.
FMT_PCT_STORED: Final = '#,0.0####"%"'
FMT_INT: Final = "#,0"
FMT_SIGNED_INT: Final = "+#,0;-#,0;0"
FMT_INDEX: Final = "#,0.0"
FMT_RATIO_PLAIN: Final = "0.000000"

GEN_KEYS: Final = (
    "hydro_generation_twh",
    "other_renewables_generation_twh",
    "wind_generation_twh",
    "solar_generation_twh",
)

FOLDER_SELECTION: Final = "00 Selection"
FOLDER_BASE: Final = "01 Base"
FOLDER_SCOPE: Final = "02 Scope"
FOLDER_SHARES: Final = "03 Shares"
FOLDER_RANKING: Final = "04 Ranking"
FOLDER_GROWTH: Final = "05 Growth"
FOLDER_CONCENTRATION: Final = "06 Concentration"
FOLDER_CAPACITY: Final = "07 Capacity factor"
FOLDER_STATUS: Final = "08 Status"
FOLDER_VIETNAM: Final = "09 Vietnam page"
# Numbered 10 rather than squeezed in beside "07 Capacity factor": the folder
# list is ordered by name, and renumbering an existing folder would move every
# measure already sitting in it.
FOLDER_ENTRY: Final = "10 Entry lag"


def _m(
    measure_id: str,
    name: str,
    dax: str,
    description: str,
    *,
    format_string: str = "",
    unit: str = "",
    unit_stored: str = "",
    numerator: str = "",
    denominator: str = "",
    filter_behavior: str = "",
    blank_rule: str = "",
    source_metric_keys: tuple[str, ...] = (),
    question_ids: tuple[str, ...] = (),
    page_ids: tuple[str, ...] = (),
    display_folder: str = "",
    hidden: bool = False,
) -> dict[str, Any]:
    return {
        "measure_id": measure_id,
        "name": name,
        "dax_expression": dax.strip("\n"),
        "description": description,
        "format_string": format_string,
        "unit": unit,
        "unit_stored": unit_stored,
        "numerator": numerator,
        "denominator": denominator,
        "filter_behavior": filter_behavior,
        "blank_rule": blank_rule,
        "source_metric_keys": source_metric_keys,
        "question_ids": question_ids,
        "page_ids": page_ids,
        "display_folder": display_folder,
        "hidden": hidden,
    }


# ---------------------------------------------------------------------------
# Reusable DAX fragments
# ---------------------------------------------------------------------------

# The mode switch never filters metric_key directly. Filtering raw keys would
# leave the completeness rule and the ranking denominator to chance; selecting
# the technologies keeps both derivable from DimMetric.
_MODE_METRIC_FILTER = (
    'FILTER( ALL( DimMetric ), DimMetric[metric] = "generation" '
    '&& ( [Selected Mode] = "RENEWABLE_TOTAL" '
    '|| DimMetric[technology] IN { "wind", "solar" } ) )'
)

_ASEAN_COHORT = (
    "CALCULATETABLE( VALUES( DimEntity[entity] ), "
    "ALL( DimEntity ), DimEntity[is_asean] = 1 )"
)

_GLOBAL_COHORT = (
    "CALCULATETABLE( VALUES( DimEntity[entity] ), "
    "ALL( DimEntity ), DimEntity[is_current_country_or_territory] = 1 )"
)

# Ranking a cohort has one trap, and it costs a whole column of wrong numbers.
#
# RANKX walks VALUES(DimEntity[entity]) and calls CALCULATE, whose context
# transition adds `DimEntity[entity] = <row being walked>`. If the visual puts a
# DIFFERENT DimEntity column on its axis -- entity_label, say -- that filter is
# still live, and the two INTERSECT rather than replace each other. Every cohort
# member except the visual's own row resolves to an empty set and comes back
# blank, so the rank list holds one real value and nine blanks and every country
# ranks first.
#
# ALLEXCEPT clears the other DimEntity filters while keeping the one the row
# context just supplied, which restores all ten values during the walk.
#
# It must NOT be applied to the current-value argument as well. At the outer
# level there is no `entity` filter to keep -- only entity_label -- so ALLEXCEPT
# there strips everything and hands back the whole ASEAN total, which puts every
# country last instead of first. The walk is filtered; the current value is not.
_COHORT_VALUE = (
    "CALCULATE( [Gen TWh @Year], ALLEXCEPT( DimEntity, DimEntity[entity] ) )"
)

# The same cohort walk for a visual that puts YEAR on its axis. It reads the
# ambient year through `Gen TWh ToDate` instead of pinning the slicer year, and
# it needs the identical ALLEXCEPT treatment for the identical reason.
#
# Why a second fragment exists at all: `Gen TWh @Year` opens with ALL( DimYear ),
# which WIPES the year the axis supplied and replaces it with the slicer's. Any
# measure built on it therefore returns one constant for every point on a time
# axis -- a rank column that reads 16 on all twenty-two rows, or a share line
# that comes out perfectly flat. Every measure below that is meant to be plotted
# over time is built on the ToDate side instead.
_COHORT_VALUE_TODATE = (
    "CALCULATE( [Gen TWh ToDate], ALLEXCEPT( DimEntity, DimEntity[entity] ) )"
)

# Page 2 is locked to Vietnam in the measure, not by a page filter. ALL() clears
# whatever country a slicer on another page left behind before pinning the one
# entity this page is about.
_VIETNAM_SCOPE = 'ALL( DimEntity ), DimEntity[entity] = "Vietnam"'

# A sequential 1..n position over the fixed cohort, ordered by value with the
# entity name only as a tiebreak. A plain RANKX shares positions on ties, which
# both breaks the Gini formula's 1..n requirement and lets "rank <= 3" return
# more than three countries. Tied values contribute the same product either way,
# so the name never changes a published figure -- it only makes the walk stable.
_RANKED_COHORT = """ADDCOLUMNS(
            _Values,
            "@AscPos",
                VAR CurV = [@Value]
                VAR CurE = [@Entity]
                RETURN
                    COUNTROWS(
                        FILTER( _Values, [@Value] < CurV || ( [@Value] = CurV && [@Entity] <= CurE ) )
                    ),
            "@DescPos",
                VAR CurV = [@Value]
                VAR CurE = [@Entity]
                RETURN
                    COUNTROWS(
                        FILTER( _Values, [@Value] > CurV || ( [@Value] = CurV && [@Entity] <= CurE ) )
                    )
        )"""


def _asean_values() -> str:
    """Cohort table with one complete-case total per ASEAN country."""
    return f"""VAR _Cohort = {_ASEAN_COHORT}
    VAR _Values =
        ADDCOLUMNS(
            _Cohort,
            "@Entity", DimEntity[entity],
            "@Value", CALCULATE( [Gen TWh @Year] ) + 0
        )"""


MEASURES: Final[list[dict[str, Any]]] = [

    # -- Selection helpers ---------------------------------------------------
    _m(
        "M001", "Selected Year",
        'SELECTEDVALUE( SelReportYear[year], 2021 )',
        "Report year currently chosen. Defaults to 2021 when the viewer has not picked one.",
        format_string=FMT_INT, unit="year", unit_stored="year",
        filter_behavior="reads the disconnected SelReportYear table, never filters DimYear",
        blank_rule="never blank -- it has a default",
        page_ids=("P1", "P2", "P3"), display_folder=FOLDER_SELECTION,
    ),
    _m(
        "M002", "Selected Mode",
        'SELECTEDVALUE( SelMode[mode_key], "RENEWABLE_TOTAL" )',
        "Measurement mode currently chosen: RENEWABLE_TOTAL or MODERN_WIND_SOLAR.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        filter_behavior="reads the disconnected SelMode table, never filters raw metric_key",
        blank_rule="defaults to RENEWABLE_TOTAL",
        page_ids=("P1", "P2", "P3"), display_folder=FOLDER_SELECTION,
    ),
    _m(
        "M003", "Selected Base Year",
        'SELECTEDVALUE( SelBaseYear[year], 2010 )',
        "Base year for indexation and for the positive-growth contribution period.",
        format_string=FMT_INT, unit="year", unit_stored="year",
        blank_rule="defaults to 2010", page_ids=("P3",), display_folder=FOLDER_SELECTION,
    ),
    _m(
        "M004", "Mode Tech Count",
        'IF( [Selected Mode] = "MODERN_WIND_SOLAR", 2, 4 )',
        "How many technologies the current mode covers: 4 for the renewable total, "
        "2 for wind plus solar.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        page_ids=("P1", "P2", "P3"), display_folder=FOLDER_SELECTION, hidden=True,
    ),

    # -- Raw reads and the completeness rule ---------------------------------
    _m(
        "M010", "Gen TWh Raw",
        f"""CALCULATE(
            SUM( FactEnergy[value] ),
            KEEPFILTERS( {_MODE_METRIC_FILTER} )
        )""",
        "Raw generation total for the technologies in the current mode, BEFORE the "
        "completeness rule is applied. Not for direct use on the report.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        numerator="SUM(FactEnergy[value]) over metric = generation",
        filter_behavior="follows the ambient filter context",
        blank_rule="blank when no rows match",
        source_metric_keys=GEN_KEYS, question_ids=("Q1", "Q2"),
        display_folder=FOLDER_BASE, hidden=True,
    ),
    _m(
        "M011", "Component Count",
        f"""CALCULATE(
            COUNTROWS( FactEnergy ),
            KEEPFILTERS( {_MODE_METRIC_FILTER} )
        ) + 0""",
        "Observations actually present in the current scope. This is the "
        "component_count that B10 reconciles against 03_fact_metrics.csv.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        blank_rule="returns 0 rather than blank so it stays comparable",
        display_folder=FOLDER_BASE, hidden=True,
    ),
    _m(
        "M012", "Required Component Count",
        f"""VAR _Entities = COUNTROWS( VALUES( DimEntity[entity] ) )
    VAR _Metrics =
        COUNTROWS(
            CALCULATETABLE(
                VALUES( DimMetric[metric_key] ),
                KEEPFILTERS( {_MODE_METRIC_FILTER} )
            )
        )
    RETURN
        _Entities * _Metrics""",
        "Cells required = entities in scope x metrics REMAINING after intersecting the "
        "mode with any technology filter. It scales on both axes: 4/4 for one country, "
        "40/40 for the ASEAN-10 aggregate, 2/2 and 20/20 in modern mode, and 10/10 when "
        "the viewer drills to a single technology. Hard-coding the mode's technology "
        "count would demand 40 cells where only 10 exist, and the visual would go blank "
        "instead of returning a number.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        filter_behavior="counts entities and metrics in context, never hard-codes 4",
        display_folder=FOLDER_BASE, hidden=True,
    ),
    _m(
        "M013", "Gen TWh",
        """IF(
            [Component Count] = [Required Component Count],
            [Gen TWh Raw]
        )""",
        "Generation for the current mode, returned ONLY when every component is present. "
        "A missing cell yields blank rather than a partial sum -- hard-coding 4/4 at the "
        "regional level would still return a number when a country filter removes cells.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        numerator="sum of 4 or 2 technologies", denominator="--",
        filter_behavior="complete-case within the scope being filtered",
        blank_rule="BLANK when component_count < required_component_count",
        source_metric_keys=GEN_KEYS, question_ids=("Q1", "Q2"),
        page_ids=("P1", "P2", "P3"), display_folder=FOLDER_BASE,
    ),
    _m(
        "M014", "Gen TWh @Year",
        """VAR _Year = [Selected Year]
    RETURN
        CALCULATE(
            [Gen TWh],
            ALL( DimYear ),
            DimYear[year] = _Year
        )""",
        "Generation at exactly the selected year. Used by the KPI row and every "
        "single-year slice.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        filter_behavior="overrides DimYear to the selected year",
        source_metric_keys=GEN_KEYS, question_ids=("Q1", "Q2"),
        page_ids=("P1", "P2", "P3"), display_folder=FOLDER_BASE,
    ),
    _m(
        "M015", "Gen TWh ToDate",
        """IF(
            SELECTEDVALUE( DimYear[is_main_asean_window] ) = 1
                && MAX( DimYear[year] ) <= [Selected Year],
            [Gen TWh]
        )""",
        "Generation for time-series visuals: shows 2000 through the selected year. "
        "The year filter means \"up to the selected year\", not \"collapse the series to "
        "a single point\".",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        filter_behavior="keeps the year axis, only suppresses years past the selection",
        blank_rule="BLANK for every year later than the selected one",
        source_metric_keys=GEN_KEYS, question_ids=("Q1", "Q4"),
        page_ids=("P1", "P2", "P3"), display_folder=FOLDER_BASE,
    ),

    # -- Scoped aggregates ---------------------------------------------------
    _m(
        "M020", "ASEAN Gen TWh",
        """CALCULATE(
            [Gen TWh @Year],
            ALL( DimEntity ),
            DimEntity[is_asean] = 1
        )""",
        "ASEAN-10 total at the selected year. Always uses the fixed is_asean = 1 cohort, "
        "so a country selection on Page 1 or Page 3 does NOT change the regional "
        "denominator.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        numerator="sum over 10 countries x the mode's technologies",
        filter_behavior="ignores the country filter -- label the scope on the visual title",
        blank_rule="BLANK when any of the 40 (or 20) cells is missing",
        source_metric_keys=GEN_KEYS, question_ids=("Q1", "Q2"),
        page_ids=("P1", "P3"), display_folder=FOLDER_SCOPE,
    ),
    _m(
        "M021", "ASEAN Gen TWh ToDate",
        """CALCULATE(
            [Gen TWh ToDate],
            ALL( DimEntity ),
            DimEntity[is_asean] = 1
        )""",
        "ASEAN-10 total as a series from 2000 to the selected year.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        filter_behavior="ignores the country filter",
        source_metric_keys=GEN_KEYS, question_ids=("Q1",),
        page_ids=("P1",), display_folder=FOLDER_SCOPE,
    ),
    _m(
        "M022", "World Gen TWh",
        """CALCULATE(
            [Gen TWh @Year],
            ALL( DimEntity ),
            DimEntity[entity] = "World"
        )""",
        "World total taken from the World ROW as published by the source, not from "
        "summing the countries present. The two differ, and summing countries would "
        "build a wrong denominator.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        filter_behavior="ignores the country filter, pins entity = World",
        source_metric_keys=GEN_KEYS, question_ids=("Q1",),
        page_ids=("P1",), display_folder=FOLDER_SCOPE,
    ),
    _m(
        "M023", "World Gen TWh ToDate",
        """CALCULATE(
            [Gen TWh ToDate],
            ALL( DimEntity ),
            DimEntity[entity] = "World"
        )""",
        "The World row as a series from 2000 to the selected year.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        source_metric_keys=GEN_KEYS, question_ids=("Q1",),
        page_ids=("P1",), display_folder=FOLDER_SCOPE,
    ),

    # -- Shares --------------------------------------------------------------
    _m(
        "M030", "ASEAN Share World",
        'DIVIDE( [ASEAN Gen TWh], [World Gen TWh] )',
        "ASEAN-10 as a share of the World row. STORED ON THE 0-1 SCALE; the x100 lives "
        "only in format_string.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="ASEAN Gen TWh", denominator="World Gen TWh (REPORTED_WORLD)",
        filter_behavior="both numerator and denominator ignore the country filter",
        blank_rule="DIVIDE returns BLANK when the denominator is zero or blank",
        source_metric_keys=GEN_KEYS, question_ids=("Q1",),
        page_ids=("P1",), display_folder=FOLDER_SHARES,
    ),
    _m(
        "M031", "Country Share ASEAN",
        """IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1,
            DIVIDE( [Gen TWh @Year], [ASEAN Gen TWh] )
        )""",
        "One country as a share of the ASEAN-10 total. The denominator is always the "
        "fixed ASEAN_SUM_10. STORED ON THE 0-1 SCALE.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="Gen TWh @Year for the country", denominator="ASEAN_SUM_10",
        filter_behavior="numerator follows the country filter, denominator keeps all ten",
        blank_rule="BLANK when either side is blank",
        source_metric_keys=GEN_KEYS, question_ids=("Q2",),
        page_ids=("P1", "P2", "P3"), display_folder=FOLDER_SHARES,
    ),
    _m(
        "M032", "Technology Share",
        """DIVIDE(
            [Gen TWh @Year],
            CALCULATE(
                [Gen TWh @Year],
                ALL( DimMetric )
            )
        )""",
        "One technology as a share of the renewable total for the same scope. "
        "STORED ON THE 0-1 SCALE.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="generation for the technology", denominator="TOTAL_RENEWABLE_GENERATION",
        blank_rule="BLANK when the denominator is zero",
        source_metric_keys=GEN_KEYS, question_ids=("Q2",),
        page_ids=("P1",), display_folder=FOLDER_SHARES,
    ),
    _m(
        "M033", "Share Electricity Pct",
        """VAR _Total =
        CALCULATE(
            SUM( FactEnergy[value] ),
            ALL( DimMetric ),
            DimMetric[metric_key] = "renewables_share_electricity_pct"
        )
    VAR _Parts =
        CALCULATE(
            SUM( FactEnergy[value] ),
            ALL( DimMetric ),
            DimMetric[metric_key]
                IN { "wind_share_electricity_pct", "solar_share_electricity_pct" }
        )
    VAR _PartCount =
        CALCULATE(
            COUNTROWS( FactEnergy ),
            ALL( DimMetric ),
            DimMetric[metric_key]
                IN { "wind_share_electricity_pct", "solar_share_electricity_pct" }
        )
    RETURN
        IF(
            [Selected Mode] = "RENEWABLE_TOTAL",
            _Total,
            IF( _PartCount = 2, _Parts )
        )""",
        "Share of total electricity, in the ambient year context. RENEWABLE_TOTAL takes "
        "the source column renewables_share_electricity_pct AS IS (1/1 pass-through) -- "
        "never sum the four components: summing them gives Vietnam 2021 = 42.513379% "
        "instead of 42.578747%, and the model has no other-renewables share column to "
        "add anyway. MODERN_WIND_SOLAR is wind plus solar and needs both (2/2). "
        "ALREADY STORED ON THE 0-100 SCALE -- do not multiply.",
        format_string=FMT_PCT_STORED, unit="pct", unit_stored="pct",
        numerator="source column (1/1) or wind + solar (2/2)", denominator="--",
        filter_behavior="follows the ambient year filter",
        blank_rule="BLANK when modern mode is missing either component",
        source_metric_keys=(
            "renewables_share_electricity_pct",
            "wind_share_electricity_pct",
            "solar_share_electricity_pct",
        ),
        question_ids=("Q5",), page_ids=("P2",), display_folder=FOLDER_SHARES,
    ),
    _m(
        "M034", "Share Electricity Pct @Year",
        """VAR _Year = [Selected Year]
    RETURN
        CALCULATE(
            [Share Electricity Pct],
            ALL( DimYear ),
            DimYear[year] = _Year
        )""",
        "Share of electricity at exactly the selected year -- used by the Vietnam KPI row.",
        format_string=FMT_PCT_STORED, unit="pct", unit_stored="pct",
        filter_behavior="pins DimYear to the selected year",
        question_ids=("Q5",), page_ids=("P2",), display_folder=FOLDER_SHARES,
    ),
    _m(
        "M035", "Share Electricity Pct ToDate",
        """IF(
            SELECTEDVALUE( DimYear[is_main_asean_window] ) = 1
                && MAX( DimYear[year] ) <= [Selected Year],
            [Share Electricity Pct]
        )""",
        "Share of electricity for the time-series panel, 2000 through the selected year. "
        "This panel must NOT share an axis with the TWh panel.",
        format_string=FMT_PCT_STORED, unit="pct", unit_stored="pct",
        question_ids=("Q5",), page_ids=("P2",), display_folder=FOLDER_SHARES,
    ),
    _m(
        "M036", "Direction Relation",
        """VAR _Year = MAX( DimYear[year] )
    VAR _CurrentTwh = [Gen TWh]
    VAR _PreviousTwh =
        CALCULATE(
            [Gen TWh],
            ALL( DimYear ),
            DimYear[year] = _Year - 1,
            DimYear[is_main_asean_window] = 1
        )
    VAR _CurrentShare = [Share Electricity Pct]
    VAR _PreviousShare =
        CALCULATE(
            [Share Electricity Pct],
            ALL( DimYear ),
            DimYear[year] = _Year - 1,
            DimYear[is_main_asean_window] = 1
        )
    VAR _DeltaTwh = _CurrentTwh - _PreviousTwh
    VAR _DeltaShare = _CurrentShare - _PreviousShare
    RETURN
        SWITCH(
            TRUE(),
            ISBLANK( _PreviousTwh ) || ISBLANK( _PreviousShare ), BLANK(),
            _DeltaTwh = 0 || _DeltaShare = 0, "ONE_OR_BOTH_UNCHANGED",
            ( _DeltaTwh > 0 ) <> ( _DeltaShare > 0 ), "OPPOSITE_DIRECTION",
            "SAME_DIRECTION"
        )""",
        "Compares the direction of the TWh move against the direction of the "
        "share-of-electricity move in the same year. Vietnam: the renewable total moves "
        "opposite ways in 2003 and 2014, the modern measure in 2016. This only FLAGS the "
        "divergence -- it licenses no causal reading between the two quantities.\n"
        "The prior year must ALSO be inside the window. Without that condition the "
        "ALL( DimYear ) reaches back to 1999, where Vietnam went 13,774 -> 14,550 TWh "
        "while its share went 58,46598 -> 54,781628 percent, and the year 2000 comes "
        "back OPPOSITE_DIRECTION. The reference walks K.YEARS[1:] and so never asks "
        "about 2000; the two sides would then disagree by one year.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        filter_behavior="reads the year from the chart axis, not from the slicer",
        blank_rule="BLANK in 2000: the prior year lies outside the window, so there is "
                   "nothing inside the window to compare against",
        question_ids=("Q5",), page_ids=("P2",), display_folder=FOLDER_SHARES,
    ),
    _m(
        "M037", "Country Share ASEAN ToDate",
        """IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1,
            DIVIDE( [Gen TWh ToDate], [ASEAN Gen TWh ToDate] )
        )""",
        "M031 as a SERIES: the same share, read at the year the axis supplies instead of "
        "the year the slicer holds. M031 cannot be plotted over time -- it is built on "
        "Gen TWh @Year, whose ALL( DimYear ) replaces the axis year with the slicer's, so "
        "every point returns the same number and the line comes out flat across all "
        "fifty-seven rows of DimYear. Both sides carry the window guard from Gen TWh "
        "ToDate, so the pre-2000 years fall away on their own. STORED ON THE 0-1 SCALE.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="Gen TWh ToDate for the country",
        denominator="ASEAN_SUM_10 at the same year",
        filter_behavior="numerator follows the country filter, denominator keeps all ten",
        blank_rule="BLANK outside 2000..selected year, and when either side is blank",
        source_metric_keys=GEN_KEYS, question_ids=("Q2",),
        page_ids=("P2", "P3"), display_folder=FOLDER_SHARES,
    ),

    # -- Ranking -------------------------------------------------------------
    _m(
        "M040", "ASEAN Rank",
        f"""VAR _ScopeTotal = [ASEAN Gen TWh]
    VAR _Cohort = {_ASEAN_COHORT}
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", {_COHORT_VALUE} )
    VAR _Current = [Gen TWh @Year]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && NOT ISBLANK( _ScopeTotal ) && _ScopeTotal > 0,
            RANKX( _Values, [@Value], _Current, DESC, Skip )
        )""",
        "Rank within the fixed ASEAN-10 cohort (population_n = 10). Ties take the "
        "smallest rank and the next rank is skipped. Zeros are still ranked. If the "
        "whole scope totals zero the rank is BLANK with reason ZERO_SCOPE_TOTAL -- not "
        "every country tied at rank 1.",
        format_string=FMT_INT, unit="rank", unit_stored="rank",
        denominator="population_n = 10",
        filter_behavior="fixed is_asean = 1 cohort, unaffected by the country filter",
        blank_rule="BLANK / ZERO_SCOPE_TOTAL when the scope total is zero",
        source_metric_keys=GEN_KEYS, question_ids=("Q3",),
        page_ids=("P1", "P2"), display_folder=FOLDER_RANKING,
    ),
    _m(
        "M041", "Global Rank",
        f"""VAR _Cohort = {_GLOBAL_COHORT}
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", {_COHORT_VALUE} )
    VAR _Current = [Gen TWh @Year]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_current_country_or_territory] ) = 1
                && NOT ISBLANK( _Current ),
            RANKX( _Values, [@Value], _Current, DESC, Skip )
        )""",
        "Rank within the current countries and territories cohort (population_n = 215), "
        "counting only countries complete in that year. Uses is_current_country_or_"
        "territory = 1: is_aggregate = 0 returns 216 rows because USSR is still in it.",
        format_string=FMT_INT, unit="rank", unit_stored="rank",
        denominator="ranked_n (dynamic), population_n = 215",
        filter_behavior="fixed cohort, ignores the country filter",
        blank_rule="BLANK when the country is incomplete that year",
        source_metric_keys=GEN_KEYS, question_ids=("Q4",),
        page_ids=("P2",), display_folder=FOLDER_RANKING,
    ),
    _m(
        "M042", "Global Ranked N",
        f"""VAR _Cohort = {_GLOBAL_COHORT}
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", {_COHORT_VALUE} )
    RETURN
        COUNTROWS( FILTER( _Values, NOT ISBLANK( [@Value] ) ) )""",
        "The denominator shown next to a global rank: how many countries are complete "
        "that year. IT MOVES WITH BOTH YEAR AND MODE -- 2021 is 205 for the total and "
        "209 for modern, 2000 is 209 and 212, 2010 is 211 and 214. Never hard-code it.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        filter_behavior="fixed 215-country cohort, counts the eligible ones",
        source_metric_keys=GEN_KEYS, question_ids=("Q4",),
        page_ids=("P2",), display_folder=FOLDER_RANKING,
    ),
    _m(
        "M043", "Global Population N",
        f"""COUNTROWS( {_GLOBAL_COHORT} )""",
        "Size of the global cohort -- always 215, independent of year and mode. Kept "
        "separate from ranked_n so the two denominators are never confused.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        page_ids=("P2",), display_folder=FOLDER_RANKING,
    ),
    _m(
        "M044", "Modern Rank Gain",
        """VAR _Total =
        CALCULATE( [ASEAN Rank], SelMode[mode_key] = "RENEWABLE_TOTAL" )
    VAR _Modern =
        CALCULATE( [ASEAN Rank], SelMode[mode_key] = "MODERN_WIND_SOLAR" )
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && NOT ISBLANK( _Total ) && NOT ISBLANK( _Modern ),
            _Total - _Modern
        )""",
        "Rank change when the measure switches: modern_rank_gain = total_rank - "
        "modern_rank. A POSITIVE number means a BETTER rank on wind plus solar alone. "
        "In 2021: Singapore +4, Indonesia -4, Laos -5.",
        format_string=FMT_SIGNED_INT, unit="rank_change", unit_stored="rank_change",
        filter_behavior="overrides SelMode per side, independent of the current switch",
        blank_rule="BLANK when either rank is undefined",
        source_metric_keys=GEN_KEYS, question_ids=("Q3",),
        page_ids=("P1",), display_folder=FOLDER_RANKING,
    ),

    # The three ToDate ranks below exist for one reason: a rank belongs on a time
    # axis as often as it belongs on a card, and the @Year versions cannot go
    # there. Built on Gen TWh @Year, they answer with the slicer's year no matter
    # what year the row asks about, so a per-year table shows one rank repeated
    # down every row -- 16 and 205 on all twenty-two lines -- which reads as a
    # country that never moved.
    _m(
        "M045", "ASEAN Rank ToDate",
        f"""VAR _ScopeTotal = [ASEAN Gen TWh ToDate]
    VAR _Cohort = {_ASEAN_COHORT}
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", {_COHORT_VALUE_TODATE} )
    VAR _Current = [Gen TWh ToDate]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && NOT ISBLANK( _ScopeTotal ) && _ScopeTotal > 0,
            RANKX( _Values, [@Value], _Current, DESC, Skip )
        )""",
        "M040 read at the year the axis supplies, for a per-year table or a rank line. "
        "Same fixed ASEAN-10 cohort (population_n = 10), same tie handling: smallest "
        "rank shared, next rank skipped, zeros still ranked. If the whole scope totals "
        "zero the rank is BLANK -- read Rank Status beside it for the reason.",
        format_string=FMT_INT, unit="rank", unit_stored="rank",
        denominator="population_n = 10, the fixed ASEAN-10 cohort",
        filter_behavior="fixed cohort, reads the year from the axis",
        blank_rule="BLANK outside the window and when the scope total is zero",
        source_metric_keys=GEN_KEYS, question_ids=("Q3",),
        page_ids=("P2", "P3"), display_folder=FOLDER_RANKING,
    ),
    _m(
        "M046", "Global Rank ToDate",
        f"""VAR _Cohort = {_GLOBAL_COHORT}
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", {_COHORT_VALUE_TODATE} )
    VAR _Current = [Gen TWh ToDate]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_current_country_or_territory] ) = 1
                && NOT ISBLANK( _Current ),
            RANKX( _Values, [@Value], _Current, DESC, Skip )
        )""",
        "M041 read at the year the axis supplies. Same 215-country cohort, counting only "
        "the countries complete in that year. A rank line drawn from this needs its axis "
        "INVERTED in Desktop so rank 1 sits at the top; the invertAxis property lives in "
        "the visual `objects` block, which this project does not generate.",
        format_string=FMT_INT, unit="rank", unit_stored="rank",
        denominator="ranked_n at that year (dynamic), population_n = 215",
        filter_behavior="fixed cohort, ignores the country filter, reads the axis year",
        blank_rule="BLANK outside the window and when the country is incomplete",
        source_metric_keys=GEN_KEYS, question_ids=("Q4",),
        page_ids=("P2", "P3"), display_folder=FOLDER_RANKING,
    ),
    _m(
        "M047", "Global Ranked N ToDate",
        f"""VAR _Cohort = {_GLOBAL_COHORT}
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", {_COHORT_VALUE_TODATE} )
    RETURN
        COUNTROWS( FILTER( _Values, NOT ISBLANK( [@Value] ) ) )""",
        "M042 read at the year the axis supplies -- the denominator that belongs beside "
        "Global Rank ToDate in a per-year table. Entity-independent by construction, so "
        "it needs no Vietnam-locked twin.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        filter_behavior="fixed 215-country cohort, counts the eligible ones per axis year",
        blank_rule="BLANK outside the window, where no country is eligible",
        source_metric_keys=GEN_KEYS, question_ids=("Q4",),
        page_ids=("P2", "P3"), display_folder=FOLDER_RANKING,
    ),

    # -- Growth --------------------------------------------------------------
    _m(
        "M050", "YoY",
        """VAR _Year = MAX( DimYear[year] )
    VAR _Current = [Gen TWh]
    VAR _Previous =
        CALCULATE(
            [Gen TWh],
            ALL( DimYear ),
            DimYear[year] = _Year - 1,
            DimYear[is_main_asean_window] = 1
        )
    RETURN
        IF(
            NOT ISBLANK( _Previous ) && _Previous > 0,
            DIVIDE( _Current, _Previous ) - 1
        )""",
        "Growth against the prior year. DEFINED ONLY when the denominator is > 0 -- with "
        "a dataset this full of zeros that is the number one source of Inf/NaN. An end "
        "value of zero giving -1 is still valid. STORED ON THE 0-1 SCALE.\n"
        "The prior year is required to be inside the window too. Vietnam has data back "
        "to 1965, so without that condition the year 2000 returns +5,63 percent while "
        "`03_fact_metrics.csv` holds yoy Y2000 as NOT_DEFINED.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="value at year t", denominator="value at year t-1, inside the window "
                                                "and greater than zero",
        blank_rule="BLANK when the prior year is zero, blank, or outside the window "
                   "(which is the case in 2000)",
        source_metric_keys=GEN_KEYS, question_ids=("Q1", "Q4"),
        page_ids=("P2", "P3"), display_folder=FOLDER_GROWTH,
    ),
    _m(
        "M051", "CAGR From Base",
        """VAR _StartYear = [Selected Base Year]
    VAR _EndYear = [Selected Year]
    VAR _Years = _EndYear - _StartYear
    VAR _Start =
        CALCULATE( [Gen TWh], ALL( DimYear ), DimYear[year] = _StartYear )
    VAR _End =
        CALCULATE( [Gen TWh], ALL( DimYear ), DimYear[year] = _EndYear )
    RETURN
        IF(
            _Years > 0 && NOT ISBLANK( _Start ) && _Start >= 0.05
                && NOT ISBLANK( _End ),
            ( DIVIDE( _End, _Start ) ^ DIVIDE( 1, _Years ) ) - 1
        )""",
        "CAGR from the base year to the report year. Applies a 0.05 TWh START FLOOR: "
        "without it, countries starting from near zero take over the top of the ranking "
        "with meaningless figures. STORED ON THE 0-1 SCALE.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="end-of-period value", denominator="start-of-period value (floor 0.05 TWh)",
        blank_rule="BLANK when the start is under the floor or the span is not positive",
        source_metric_keys=GEN_KEYS, question_ids=("Q1",),
        page_ids=("P3",), display_folder=FOLDER_GROWTH,
    ),
    _m(
        "M052", "Indexed 100",
        """VAR _BaseYear = [Selected Base Year]
    VAR _Base =
        CALCULATE(
            [Gen TWh],
            ALL( DimYear ),
            DimYear[year] = _BaseYear
        )
    RETURN
        IF(
            _BaseYear <= [Selected Year]
                && NOT ISBLANK( _Base ) && _Base > 0,
            DIVIDE( [Gen TWh ToDate], _Base ) * 100
        )""",
        "Indexed to 100 at the base year. A zero base, or a base later than the report "
        "year, returns BLANK -- it never produces an infinity.",
        format_string=FMT_INDEX, unit="count", unit_stored="count",
        numerator="value at year t", denominator="value at the base year (must be > 0)",
        blank_rule="BLANK when the base is zero or falls after the report year",
        source_metric_keys=GEN_KEYS, question_ids=("Q1",),
        page_ids=("P3",), display_folder=FOLDER_GROWTH,
    ),
    _m(
        "M053", "Positive Addition TWh",
        """VAR _StartYear = [Selected Base Year]
    VAR _EndYear = [Selected Year]
    VAR _Start =
        CALCULATE( [Gen TWh], ALL( DimYear ), DimYear[year] = _StartYear )
    VAR _End =
        CALCULATE( [Gen TWh], ALL( DimYear ), DimYear[year] = _EndYear )
    RETURN
        IF(
            NOT ISBLANK( _Start ) && NOT ISBLANK( _End ),
            MAX( _End - _Start, 0 )
        )""",
        "A country's POSITIVE addition between the base year and the report year. "
        "Declines are clipped to zero and reported separately, never netted off the total.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        source_metric_keys=GEN_KEYS, question_ids=("Q6",),
        page_ids=("P3",), display_folder=FOLDER_GROWTH,
    ),
    _m(
        "M054", "Gross Positive Addition TWh",
        f"""VAR _Cohort = {_ASEAN_COHORT}
    RETURN
        SUMX( _Cohort, CALCULATE( [Positive Addition TWh] ) )""",
        "Sum of the positive additions across all of ASEAN-10 -- the "
        "GROSS_POSITIVE_ADDITION denominator.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        filter_behavior="always all ten countries, ignores the country filter",
        source_metric_keys=GEN_KEYS, question_ids=("Q6",),
        page_ids=("P3",), display_folder=FOLDER_GROWTH,
    ),
    _m(
        "M055", "Positive Growth Share",
        """IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1,
            DIVIDE( [Positive Addition TWh], [Gross Positive Addition TWh] )
        )""",
        "A country's share OF THE GROSS POSITIVE ADDITION -- not its share of the "
        "region's net growth. Vietnam 2010-2021: modern 65.985915493%, total "
        "42.3780539369% (held on the ratio scale). STORED ON THE 0-1 SCALE. The "
        "is_asean guard is what keeps the page 3 bar chart to ten bars: the "
        "denominator is ASEAN-only, so the ratio is meaningless for any other entity, "
        "and without the guard entity_label on an axis returns all 256 of them.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="Positive Addition TWh for the country",
        denominator="GROSS_POSITIVE_ADDITION",
        filter_behavior="ASEAN-10 only; BLANK for any entity outside the cohort",
        blank_rule="BLANK outside ASEAN-10, or when there is no positive addition at all",
        source_metric_keys=GEN_KEYS, question_ids=("Q6",),
        page_ids=("P3",), display_folder=FOLDER_GROWTH,
    ),

    # -- Concentration -------------------------------------------------------
    _m(
        "M060", "Above 0.05 TWh N",
        f"""VAR _Cohort = {_ASEAN_COHORT}
    RETURN
        COUNTROWS(
            FILTER( _Cohort, CALCULATE( [Gen TWh @Year] ) >= 0.05 )
        ) + 0""",
        "How many ASEAN countries clear the 0.05 TWh threshold in the current mode. The "
        "threshold applies to the DERIVED TOTAL (PHASE3_DERIVED_FLOOR); a component's "
        "value_class is never assigned back to the total.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        filter_behavior="fixed ten-country cohort",
        source_metric_keys=GEN_KEYS, question_ids=("Q6",),
        page_ids=("P1",), display_folder=FOLDER_CONCENTRATION,
    ),
    _m(
        "M061", "Top1 Share",
        f"""VAR _Total = [ASEAN Gen TWh]
    {_asean_values()}
    RETURN
        IF(
            NOT ISBLANK( _Total ) && _Total > 0,
            DIVIDE( MAXX( _Values, [@Value] ), _Total )
        )""",
        "Share held by the largest country in the ASEAN-10 total. In 2021 this equals "
        "Vietnam's share EXACTLY, because both use the ASEAN_SUM_10 denominator and "
        "Vietnam leads in both modes -- it is ONE quantity, not two measures. "
        "STORED ON THE 0-1 SCALE.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="largest value", denominator="ASEAN_SUM_10",
        blank_rule="BLANK / ZERO_DENOMINATOR when the ASEAN total is zero",
        source_metric_keys=GEN_KEYS, question_ids=("Q6",),
        page_ids=("P3",), display_folder=FOLDER_CONCENTRATION,
    ),
    _m(
        "M062", "Top3 Share",
        f"""VAR _Total = [ASEAN Gen TWh]
    {_asean_values()}
    VAR _Ranked = {_RANKED_COHORT}
    RETURN
        IF(
            NOT ISBLANK( _Total ) && _Total > 0,
            DIVIDE(
                SUMX( FILTER( _Ranked, [@DescPos] <= 3 ), [@Value] ),
                _Total
            )
        )""",
        "Share held by EXACTLY the three largest values. Uses a sequential position "
        "rather than \"rank <= 3\": on a tie for third place a rank condition returns "
        "more than three countries. Tied values are equal, so the top-3 total is the "
        "same whichever is picked. STORED ON THE 0-1 SCALE.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="sum of the three largest values", denominator="ASEAN_SUM_10",
        blank_rule="BLANK / ZERO_DENOMINATOR when the ASEAN total is zero",
        source_metric_keys=GEN_KEYS, question_ids=("Q6",),
        page_ids=("P3",), display_folder=FOLDER_CONCENTRATION,
    ),
    _m(
        "M063", "HHI",
        f"""VAR _Total = [ASEAN Gen TWh]
    {_asean_values()}
    RETURN
        IF(
            NOT ISBLANK( _Total ) && _Total > 0,
            SUMX( _Values, DIVIDE( [@Value], _Total ) ^ 2 )
        )""",
        "Herfindahl-Hirschman concentration index over all ten countries, KEEPING the "
        "countries whose value is zero. STORED ON THE 0-1 SCALE, with no percent sign.",
        format_string=FMT_RATIO_PLAIN, unit="ratio", unit_stored="ratio",
        numerator="sum of squared shares", denominator="ASEAN_SUM_10",
        blank_rule="BLANK / ZERO_DENOMINATOR when the ASEAN total is zero",
        source_metric_keys=GEN_KEYS, question_ids=("Q6",),
        page_ids=("P3",), display_folder=FOLDER_CONCENTRATION,
    ),
    _m(
        "M064", "Gini",
        f"""VAR _Total = [ASEAN Gen TWh]
    {_asean_values()}
    VAR _N = COUNTROWS( _Values )
    VAR _Ranked = {_RANKED_COHORT}
    RETURN
        IF(
            NOT ISBLANK( _Total ) && _Total > 0,
            DIVIDE( 2 * SUMX( _Ranked, [@AscPos] * [@Value] ), _N * _Total )
                - DIVIDE( _N + 1, _N )
        )""",
        "Gini inequality coefficient by the empirical formula over all ten values sorted "
        "ascending: 2*SUM(i*x_i)/(n*SUM x) - (n+1)/n. Position i must be a distinct "
        "1..10; tied values contribute the same product wherever they sit, so the country "
        "name only makes the walk stable. STORED ON THE 0-1 SCALE.",
        format_string=FMT_RATIO_PLAIN, unit="ratio", unit_stored="ratio",
        numerator="empirical Gini formula", denominator="ASEAN_SUM_10",
        blank_rule="BLANK / ZERO_DENOMINATOR when the ASEAN total is zero",
        source_metric_keys=GEN_KEYS, question_ids=("Q6",),
        page_ids=("P3",), display_folder=FOLDER_CONCENTRATION,
    ),

    # -- Capacity factor -----------------------------------------------------
    _m(
        "M070", "Capacity GW",
        """CALCULATE(
            SUM( FactEnergy[value] ),
            KEEPFILTERS(
                FILTER(
                    ALL( DimMetric ),
                    DimMetric[metric] = "installed_capacity"
                        && DimMetric[technology] IN { "wind", "solar" }
                )
            )
        )""",
        "End-of-year installed capacity, wind and solar only. KEEPFILTERS rather than "
        "a bare ALL( DimMetric ): the bare form WIPES the technology the slicer or the "
        "small-multiple row supplied, so wind and solar were always summed together and "
        "the B9 reading of 2 countries for wind against 4 for solar could not be made.",
        format_string="#,0.000", unit="GW", unit_stored="GW",
        source_metric_keys=("wind_capacity_gw", "solar_capacity_gw"),
        question_ids=("Q4",), page_ids=("P3",), display_folder=FOLDER_CAPACITY,
    ),
    _m(
        "M071", "Capacity Factor",
        """VAR _Capacity = [Capacity GW]
    VAR _Generation =
        CALCULATE(
            SUM( FactEnergy[value] ),
            KEEPFILTERS(
                FILTER(
                    ALL( DimMetric ),
                    DimMetric[metric] = "generation"
                        && DimMetric[technology] IN { "wind", "solar" }
                )
            )
        )
    RETURN
        IF(
            NOT ISBLANK( _Capacity ) && _Capacity > 0
                && NOT ISBLANK( _Generation ),
            DIVIDE( _Generation, _Capacity * 8.76 )
        )""",
        "APPROXIMATE capacity factor = TWh / (GW x 8.76). Keeps only pairs with "
        "capacity_gw > 0 and non-blank generation: a raw join over the window gives 132 "
        "pairs, the 28 with zero capacity are dropped, and none of those carries positive "
        "generation, so the filter loses no observation. 104 pairs remain -- wind 33, "
        "solar 71. Uses DIVIDE() to return BLANK, NOT the / operator. This is an "
        "indicator built on end-of-year capacity, NOT a measure of technical efficiency.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="generation TWh", denominator="capacity GW x 8.76",
        filter_behavior="ASEAN-10 within the 2000-2021 window only",
        blank_rule="BLANK when capacity is zero or blank",
        source_metric_keys=("wind_capacity_gw", "solar_capacity_gw",
                            "wind_generation_twh", "solar_generation_twh"),
        question_ids=("Q4",), page_ids=("P3",), display_folder=FOLDER_CAPACITY,
    ),
    _m(
        "M072", "Capacity Factor Country N",
        """COUNTROWS(
            FILTER(
                CALCULATETABLE(
                    VALUES( DimEntity[entity] ),
                    ALL( DimEntity ),
                    DimEntity[is_asean] = 1
                ),
                NOT ISBLANK( CALCULATE( [Capacity Factor] ) )
            )
        ) + 0""",
        "How many ASEAN countries actually have capacity-factor data: 2 for wind, 4 for "
        "solar. Show this next to the chart so nobody reads it as covering all ten. It "
        "reads 4 with no technology picked, because the union of the two sets is "
        "Malaysia, the Philippines, Thailand and Vietnam.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        question_ids=("Q4",), page_ids=("P3",), display_folder=FOLDER_CAPACITY,
    ),

    # -- Page 3: cohort-guarded twins ----------------------------------------
    # Page 3 is the first page to put DimEntity[entity_label] on an axis while
    # asking for a country-level figure. Page 1 gets away without a guard because
    # ASEAN Rank and Country Share ASEAN already refuse to answer outside the
    # cohort; the measures below did not, and an unguarded axis lists all 256
    # entities -- World and the continents included -- rather than the ten.
    #
    # The guard is SELECTEDVALUE( is_asean ) = 1 and not a filter on entity: a
    # filter would intersect with whatever the axis column already put in context,
    # which is the trap documented at _COHORT_VALUE.
    _m(
        "M110", "ASEAN Country Gen TWh ToDate",
        """IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1,
            [Gen TWh ToDate]
        )""",
        "One ASEAN country's generation as a series, 2000 through the selected year. "
        "This is what the ten-panel grid plots. TWh rather than a share, to stay with "
        "the Phase 4 convention: C05 and C06 drew output, and a grid of shares would "
        "answer a different question.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        filter_behavior="BLANK for any entity outside ASEAN-10",
        blank_rule="BLANK outside the cohort and outside the 2000-2021 window",
        source_metric_keys=GEN_KEYS, question_ids=("Q1",),
        page_ids=("P3",), display_folder=FOLDER_SCOPE,
    ),
    _m(
        "M111", "ASEAN Indexed 100",
        """IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1,
            [Indexed 100]
        )""",
        "M052 restricted to the ASEAN-10 cohort, for the indexed trajectory chart. "
        "M052 itself is left unguarded on purpose so the same index can be read for "
        "World or a region when a later question asks for it.",
        format_string=FMT_INDEX, unit="count", unit_stored="count",
        numerator="value at year t", denominator="value at the base year (must be > 0)",
        filter_behavior="BLANK for any entity outside ASEAN-10",
        blank_rule="inherits M052: BLANK on a zero base or a base after the report year",
        source_metric_keys=GEN_KEYS, question_ids=("Q1",),
        page_ids=("P3",), display_folder=FOLDER_GROWTH,
    ),
    _m(
        "M112", "ASEAN Capacity Factor",
        """IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1,
            [Capacity Factor]
        )""",
        "M071 restricted to the ASEAN-10 cohort. Wind and solar capacity exist for many "
        "countries outside the region, so an unguarded series would quietly widen a "
        "chart whose caption says ASEAN. Still an APPROXIMATE indicator on end-of-year "
        "capacity, never a measure of technical efficiency.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="generation TWh", denominator="capacity GW x 8.76",
        filter_behavior="BLANK for any entity outside ASEAN-10",
        blank_rule="BLANK outside the cohort, or when capacity is zero or blank",
        source_metric_keys=("wind_capacity_gw", "solar_capacity_gw",
                            "wind_generation_twh", "solar_generation_twh"),
        question_ids=("Q4",), page_ids=("P3",), display_folder=FOLDER_CAPACITY,
    ),

    # -- Technology entry and censoring (V12) --------------------------------
    # The entry family had no measure at all: `05_acceptance.dax` computes it
    # inline, which satisfies B10 but leaves nothing for a visual to bind to.
    #
    # Two rules this family does NOT share with the rest of the model:
    #   * it never touches [Gen TWh], because that applies the mode switch and the
    #     entry table must show all four technologies in BOTH modes;
    #   * it never narrows to the report year -- the statuses are defined against
    #     the whole 2000-2021 window, which is what NOT_OBSERVED_BY_2021 means.
    # KEEPFILTERS lets the technology arrive from the row instead of being written
    # into the expression, so one pair of helpers serves all forty rows.
    _m(
        "M113", "Entry First Year",
        """CALCULATE(
            MIN( FactEnergy[year] ),
            KEEPFILTERS(
                FILTER( ALL( DimMetric ), DimMetric[metric] = "generation" )
            ),
            ALL( DimYear ),
            DimYear[is_main_asean_window] = 1,
            FactEnergy[value] > 0.0
        )""",
        "First year inside the window with generation above zero, for whichever "
        "technology the row supplies. Helper only -- read Entry Status and Entry Year "
        "Label, which say what a blank means.",
        format_string=FMT_INT, unit="year", unit_stored="year",
        blank_rule="BLANK when the technology is never observed inside the window",
        source_metric_keys=GEN_KEYS, question_ids=("Q5",),
        page_ids=("P3",), display_folder=FOLDER_ENTRY, hidden=True,
    ),
    _m(
        "M114", "Material First Year",
        """CALCULATE(
            MIN( FactEnergy[year] ),
            KEEPFILTERS(
                FILTER( ALL( DimMetric ), DimMetric[metric] = "generation" )
            ),
            ALL( DimYear ),
            DimYear[is_main_asean_window] = 1,
            FactEnergy[value] >= 0.05
        )""",
        "M113 at the 0.05 TWh material threshold instead of at any positive value. The "
        "two families answer different questions -- Vietnam's solar turns positive in "
        "2010 and only reaches 0.05 TWh in 2018 -- so both are carried, which is why "
        "forty key rows hold eighty status values.",
        format_string=FMT_INT, unit="year", unit_stored="year",
        blank_rule="BLANK when the technology never reaches 0.05 TWh inside the window",
        source_metric_keys=GEN_KEYS, question_ids=("Q5",),
        page_ids=("P3",), display_folder=FOLDER_ENTRY, hidden=True,
    ),
    _m(
        "M120", "Entry Metric Count",
        """COUNTROWS(
            CALCULATETABLE(
                VALUES( DimMetric[metric_key] ),
                KEEPFILTERS(
                    FILTER( ALL( DimMetric ), DimMetric[metric] = "generation" )
                )
            )
        ) + 0""",
        "How many generation metrics survive the current technology filter. Numbered "
        "out of sequence because it was added after the first pass, when the entry "
        "table came back with SEVENTY rows instead of forty: technology_label resolves "
        "seven labels, and Renewables total, Biofuel and Geothermal have no generation "
        "metric at all. Those three returned NOT_OBSERVED_BY_2021, which is a false "
        "claim -- nothing was ever measured there, so nothing failed to be observed. "
        "Every public measure in this folder is blank when this count is zero.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        page_ids=("P3",), display_folder=FOLDER_ENTRY, hidden=True,
    ),
    _m(
        "M115", "Entry Status",
        """VAR _First = [Entry First Year]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && [Entry Metric Count] >= 1,
            SWITCH(
                TRUE(),
                ISBLANK( _First ), "NOT_OBSERVED_BY_2021",
                _First = 2000, "ACTIVE_AT_WINDOW_START",
                "OBSERVED_TRANSITION"
            )
        )""",
        "Censoring status on the positive threshold. ACTIVE_AT_WINDOW_START is "
        "LEFT-CENSORED: the series was already running in 2000 and the real entry year "
        "is before the window, so it must not be reported as an entry in 2000. "
        "NOT_OBSERVED_BY_2021 is right-censored the same way.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        filter_behavior="BLANK for any entity outside ASEAN-10",
        source_metric_keys=GEN_KEYS, question_ids=("Q5",),
        page_ids=("P3",), display_folder=FOLDER_ENTRY,
    ),
    _m(
        "M116", "Entry Year Label",
        """VAR _First = [Entry First Year]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && [Entry Metric Count] >= 1,
            IF(
                NOT ISBLANK( _First ) && _First > 2000,
                FORMAT( _First, "0" ),
                "CENSORED/EVENT_NOT_EXACTLY_OBSERVED"
            )
        )""",
        "The observed entry year, or the censoring code when the event was not seen "
        "inside the window. Text rather than a number so a censored row shows the "
        "reason instead of an empty cell that reads like a data gap. FORMAT uses '0' "
        "and not '#,0': the model culture is vi-VN, where a thousands separator turns "
        "2010 into 2.010.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        filter_behavior="BLANK for any entity outside ASEAN-10",
        source_metric_keys=GEN_KEYS, question_ids=("Q5",),
        page_ids=("P3",), display_folder=FOLDER_ENTRY,
    ),
    _m(
        "M117", "Material Entry Status",
        """VAR _First = [Material First Year]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && [Entry Metric Count] >= 1,
            SWITCH(
                TRUE(),
                ISBLANK( _First ), "NOT_MATERIAL_BY_2021",
                _First = 2000, "MATERIAL_AT_WINDOW_START",
                "OBSERVED_MATERIAL_TRANSITION"
            )
        )""",
        "M115 on the 0.05 TWh threshold. Brunei's solar holds NOT_MATERIAL_BY_2021 "
        "through 2021 and must keep it: substituting 2021 as an event year would "
        "invent an entry that was never observed.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        filter_behavior="BLANK for any entity outside ASEAN-10",
        source_metric_keys=GEN_KEYS, question_ids=("Q5",),
        page_ids=("P3",), display_folder=FOLDER_ENTRY,
    ),
    _m(
        "M118", "Material Entry Year Label",
        """VAR _First = [Material First Year]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && [Entry Metric Count] >= 1,
            IF(
                NOT ISBLANK( _First ) && _First > 2000,
                FORMAT( _First, "0" ),
                "CENSORED/EVENT_NOT_EXACTLY_OBSERVED"
            )
        )""",
        "M116 on the 0.05 TWh threshold. Vietnam's solar reads 2018 here against 2010 "
        "on the positive threshold; the series never takes the value 0.05 exactly, it "
        "reaches 0.10 TWh in 2018.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        filter_behavior="BLANK for any entity outside ASEAN-10",
        source_metric_keys=GEN_KEYS, question_ids=("Q5",),
        page_ids=("P3",), display_folder=FOLDER_ENTRY,
    ),
    _m(
        "M121", "ASEAN Completeness Label",
        """VAR _Year = [Selected Year]
    VAR _Need =
        CALCULATE(
            [Required Component Count],
            ALL( DimYear ),
            DimYear[year] = _Year,
            KEEPFILTERS( FILTER( ALL( DimEntity ), DimEntity[is_asean] = 1 ) )
        )
    VAR _Label =
        CALCULATE(
            [Completeness Label],
            ALL( DimYear ),
            DimYear[year] = _Year,
            KEEPFILTERS( FILTER( ALL( DimEntity ), DimEntity[is_asean] = 1 ) )
        )
    RETURN
        IF( NOT ISBLANK( _Need ), _Label )""",
        "M082 given the two scopes it needs to mean anything. Read bare on a card it "
        "returned 34.714/1.024 -- every entity in the model across every year, which "
        "is true and useless. Pinning the report year and intersecting with ASEAN-10 "
        "produces the three readings Phase5_Review 3.4 asks for: 40/40 with nothing "
        "selected, 4/4 with one country, 10/10 with one technology. KEEPFILTERS rather "
        "than a replacement, so a country picked on this page still narrows it. Blank "
        "rather than the bare string '0/' when the selection lands outside ASEAN-10 "
        "entirely -- an empty card reads as no data, which is the truth, where '0/' "
        "reads as a broken measure.",
        blank_rule="BLANK when the country selection has no ASEAN-10 member in it",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        filter_behavior="ASEAN-10 intersected with the current country selection, at "
                        "the selected year",
        page_ids=("P3",), display_folder=FOLDER_STATUS,
    ),
    _m(
        "M119", "Entry Lag From 2000",
        """VAR _First = [Entry First Year]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && [Entry Metric Count] >= 1
                && NOT ISBLANK( _First ) && _First > 2000,
            _First - 2000
        )""",
        "Years from the start of the window to the observed entry. Numeric and BLANK "
        "for a censored series -- Entry Status beside it carries the reason. Writing 0 "
        "for a left-censored series would claim the start was watched in 2000; writing "
        "21 for a right-censored one would claim an entry that never happened.",
        format_string=FMT_INT, unit="count", unit_stored="count",
        filter_behavior="BLANK for any entity outside ASEAN-10",
        blank_rule="BLANK on both censoring directions, never zero and never 21",
        source_metric_keys=GEN_KEYS, question_ids=("Q5",),
        page_ids=("P3",), display_folder=FOLDER_ENTRY,
    ),

    # -- Page 2: Vietnam, scope-locked ---------------------------------------
    # B6 requires page 2 to stay on Vietnam no matter what a country slicer on
    # another page is set to. The lock lives in the measure rather than in a
    # page-level filter: same pattern as ASEAN Gen TWh and World Gen TWh, and it
    # needs no report JSON shape that has not been sampled from Desktop.
    #
    # Wrapping does not defeat the guards inside the wrapped measures --
    # SELECTEDVALUE(DimEntity[is_asean]) and its global twin both still resolve,
    # because the wrapper leaves exactly one entity in context.
    _m(
        "M090", "VN Gen TWh @Year",
        f"""CALCULATE( [Gen TWh @Year], {_VIETNAM_SCOPE} )""",
        "Vietnam generation at the selected year. Locked to Vietnam, so a country "
        "selection made on another page cannot move this page off its subject.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        filter_behavior="overrides any country filter to Vietnam",
        source_metric_keys=GEN_KEYS, question_ids=("Q4",),
        page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M091", "VN Gen TWh ToDate",
        f"""CALCULATE( [Gen TWh ToDate], {_VIETNAM_SCOPE} )""",
        "Vietnam generation as a series, 2000 through the selected year.",
        format_string=FMT_TWH, unit="TWh", unit_stored="TWh",
        filter_behavior="overrides any country filter to Vietnam",
        source_metric_keys=GEN_KEYS, question_ids=("Q4",),
        page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M092", "VN Share Electricity Pct @Year",
        f"""CALCULATE( [Share Electricity Pct @Year], {_VIETNAM_SCOPE} )""",
        "Vietnam share of total electricity at the selected year. Stored on the "
        "0-100 scale already -- do not multiply.",
        format_string=FMT_PCT_STORED, unit="pct", unit_stored="pct",
        filter_behavior="overrides any country filter to Vietnam",
        question_ids=("Q5",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M093", "VN Share Electricity Pct ToDate",
        f"""CALCULATE( [Share Electricity Pct ToDate], {_VIETNAM_SCOPE} )""",
        "Vietnam share of electricity as a series. Goes on its OWN panel, never "
        "on a second axis beside the TWh series.",
        format_string=FMT_PCT_STORED, unit="pct", unit_stored="pct",
        question_ids=("Q5",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M094", "VN Country Share ASEAN",
        f"""CALCULATE( [Country Share ASEAN], {_VIETNAM_SCOPE} )""",
        "Vietnam as a share of the ASEAN-10 total. STORED ON THE 0-1 SCALE. "
        "In 2021 this equals Top1 Share, because Vietnam leads in both modes and "
        "both use the ASEAN_SUM_10 denominator.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="Vietnam generation", denominator="ASEAN_SUM_10",
        question_ids=("Q2",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M095", "VN Global Rank",
        f"""CALCULATE( [Global Rank], {_VIETNAM_SCOPE} )""",
        "Vietnam's rank among the 215 current countries and territories. Read it "
        "beside Global Ranked N, which moves with both year and mode: 16/205 for "
        "the renewable total in 2021 and 17/209 for the modern measure.",
        format_string=FMT_INT, unit="rank", unit_stored="rank",
        denominator="ranked_n (dynamic)",
        question_ids=("Q4",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M096", "VN YoY",
        f"""CALCULATE( [YoY], {_VIETNAM_SCOPE} )""",
        "Vietnam year-on-year growth. Blank when the prior year is zero, which is "
        "common early in the window for wind and solar.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="value at t", denominator="value at t-1 (must be > 0)",
        question_ids=("Q4",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M097", "VN Direction Relation",
        f"""CALCULATE( [Direction Relation], {_VIETNAM_SCOPE} )""",
        "Whether Vietnam's TWh and its share of electricity moved the same way "
        "that year. Opposite in 2003 and 2014 on the renewable total, and in 2016 "
        "on the modern measure. A flag only -- it explains nothing about cause.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        question_ids=("Q5",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M098", "VN Country Share ASEAN ToDate",
        f"""CALCULATE( [Country Share ASEAN ToDate], {_VIETNAM_SCOPE} )""",
        "Vietnam's share of the ASEAN-10 total as a SERIES. This is what the position "
        "chart plots; M094 is the single-year card and produces a flat line if it is "
        "put on a time axis. STORED ON THE 0-1 SCALE.",
        format_string=FMT_RATIO_PCT, unit="ratio", unit_stored="ratio",
        numerator="Vietnam Gen TWh ToDate",
        denominator="ASEAN_SUM_10 at the same year",
        question_ids=("Q2",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M099", "VN ASEAN Rank ToDate",
        f"""CALCULATE( [ASEAN Rank ToDate], {_VIETNAM_SCOPE} )""",
        "Vietnam's rank inside ASEAN-10 at the year the axis supplies. The year table "
        "carries this so the rank can be read as a trajectory rather than as one number "
        "repeated down the column.",
        format_string=FMT_INT, unit="rank", unit_stored="rank",
        denominator="population_n = 10",
        blank_rule="BLANK when the ASEAN total for that year and mode is zero",
        question_ids=("Q3",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M100", "VN Global Rank ToDate",
        f"""CALCULATE( [Global Rank ToDate], {_VIETNAM_SCOPE} )""",
        "Vietnam's rank among the 215 current countries and territories at the year the "
        "axis supplies. Read it beside Global Ranked N ToDate, which moves with both "
        "year and mode.",
        format_string=FMT_INT, unit="rank", unit_stored="rank",
        denominator="ranked_n at that year (dynamic)",
        question_ids=("Q4",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M101", "VN Rank Label",
        f"""VAR _AseanRank = CALCULATE( [ASEAN Rank], {_VIETNAM_SCOPE} )
    VAR _AseanN = COUNTROWS( {_ASEAN_COHORT} )
    VAR _GlobalRank = [VN Global Rank]
    VAR _GlobalN = [Global Ranked N]
    VAR _AseanText =
        IF(
            ISBLANK( _AseanRank ),
            [Rank Status],
            "ASEAN " & FORMAT( _AseanRank, "#,0" ) & "/" & FORMAT( _AseanN, "#,0" )
        )
    VAR _GlobalText =
        IF(
            ISBLANK( _GlobalRank ),
            "",
            " | World " & FORMAT( _GlobalRank, "#,0" ) & "/" & FORMAT( _GlobalN, "#,0" )
        )
    RETURN
        _AseanText & _GlobalText""",
        "Both of Vietnam's ranks with both denominators, on one card: 2021 on the "
        "renewable total reads `ASEAN 1/10 | World 16/205`. A bare rank is unreadable -- "
        "16 means nothing until the reader knows whether it is out of 205 or out of 215 "
        "-- and ranked_n moves with year AND mode, so it cannot be typed into a title. "
        "When the ASEAN rank is undefined the reason takes its place: 2000 in modern "
        "mode reads `NOT_DEFINED/ZERO_SCOPE_TOTAL | World 40/212`, which shows the "
        "reason without hiding the global rank that IS defined. The ASEAN denominator "
        "is counted, not typed, for the same reason ranked_n is.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        denominator="population_n = 10 for ASEAN, ranked_n for the world",
        filter_behavior="locked to Vietnam, ignores the country slicer",
        blank_rule="the ASEAN half falls back to Rank Status; the world half drops out "
                   "when the rank is undefined",
        source_metric_keys=GEN_KEYS, question_ids=("Q3", "Q4"),
        page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),
    _m(
        "M102", "VN Direction Color",
        """IF(
            [VN Direction Relation] = "OPPOSITE_DIRECTION",
            "#D55E00"
        )""",
        "Font colour for the direction column of the year table, so the two divergent "
        "years stand out instead of hiding among twenty-two rows of SAME_DIRECTION. "
        "Returns the Phase 4 Vietnam accent on an opposing year and BLANK everywhere "
        "else, which leaves the other rows in the default colour rather than painting "
        "the whole column. Exists because a TEXT column can only be conditionally "
        "formatted through `Format by: Field value` -- the Rules option needs a numeric "
        "field -- so the colour has to come from a measure. Wire it up in Desktop: "
        "the column's dropdown in the Values well -> Conditional formatting -> Font "
        "colour -> Format by `Field value` -> this measure.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        filter_behavior="follows the row of the year table",
        blank_rule="BLANK on every year that is not OPPOSITE_DIRECTION, by design",
        question_ids=("Q5",), page_ids=("P2",), display_folder=FOLDER_VIETNAM,
    ),

    # -- Status labels -------------------------------------------------------
    _m(
        "M080", "Rank Status",
        """VAR _ScopeTotal = [ASEAN Gen TWh]
    RETURN
        IF(
            ISBLANK( _ScopeTotal ) || _ScopeTotal = 0,
            "NOT_DEFINED/ZERO_SCOPE_TOTAL"
        )""",
        "Reason label shown when a rank is undefined. Placed next to the rank so the "
        "viewer sees WHY it is empty instead of assuming a bug.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        blank_rule="only appears when the rank is undefined",
        question_ids=("Q3",), page_ids=("P1", "P2"), display_folder=FOLDER_STATUS,
    ),
    _m(
        "M081", "Concentration Status",
        """VAR _Total = [ASEAN Gen TWh]
    RETURN
        IF(
            ISBLANK( _Total ) || _Total = 0,
            "NOT_DEFINED/ZERO_DENOMINATOR"
        )""",
        "Reason label when top-1, top-3, HHI and Gini are undefined -- the mandatory edge "
        "case is the year 2000 in modern mode, where the ASEAN total is zero.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        question_ids=("Q6",), page_ids=("P3",), display_folder=FOLDER_STATUS,
    ),
    _m(
        "M082", "Completeness Label",
        """VAR _Have = [Component Count]
    VAR _Need = [Required Component Count]
    RETURN
        FORMAT( _Have, "#,0" ) & "/" & FORMAT( _Need, "#,0" )""",
        "A have/need label so the viewer can see which level the completeness rule is "
        "operating at: 4/4 for one country, 40/40 for the ASEAN-10 aggregate.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        page_ids=("P1", "P2", "P3"), display_folder=FOLDER_STATUS,
    ),
    _m(
        "M083", "Footer Note",
        '''"Source: Our World in Data (Ember + BP) via output/clean | "
        & "Analysis window 2000-2021 | "
        & "2022 excluded: severely truncated in 8 source files, 0 ASEAN countries | "
        & "Aggregate entities excluded from every country list | "
        & "No interpolation"''',
        "Fixed footer for all three pages: source, year window, why 2022 was dropped and "
        "the note that aggregate entities were excluded. Retype in Vietnamese inside "
        "Desktop if the report should read in Vietnamese -- that text lives in the .pbix, "
        "not in TMDL.",
        unit="STATUS_CODE", unit_stored="STATUS_CODE",
        page_ids=("P1", "P2", "P3"), display_folder=FOLDER_STATUS,
    ),
]


def measure_by_name(name: str) -> dict[str, Any]:
    for measure in MEASURES:
        if measure["name"] == name:
            return measure
    raise KeyError(name)


def validate() -> None:
    names = [m["name"] for m in MEASURES]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate measure name")
    ids = [m["measure_id"] for m in MEASURES]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate measure_id")
    for measure in MEASURES:
        if not measure["description"]:
            raise RuntimeError(f"{measure['name']}: missing description")
        # Every ratio must say what it divides by, so no KPI is left undefined.
        if measure["unit_stored"] == "ratio" and not measure["denominator"]:
            raise RuntimeError(f"{measure['name']}: ratio without a denominator")
        if measure["unit_stored"] == "ratio" and "* 100" in measure["dax_expression"]:
            raise RuntimeError(
                f"{measure['name']}: ratio measures must not scale by 100 in the expression"
            )
        # TMDL must stay ASCII; Desktop rejects a BOM and an earlier Vietnamese
        # build came back mojibaked. Catch it at the source, not at write time.
        for field in ("name", "description", "format_string", "dax_expression",
                      "display_folder", "numerator", "denominator",
                      "filter_behavior", "blank_rule"):
            if not str(measure[field]).isascii():
                raise RuntimeError(
                    f"{measure['name']}.{field}: must be ASCII, model text cannot "
                    "carry Vietnamese"
                )


validate()
