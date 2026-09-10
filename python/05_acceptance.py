"""Phase 5 -- generate `powerbi/05_acceptance.dax` from the expected-value set.

Every target produced by `05_expected.py` gets exactly one DAX scalar here, so
the reference side and the query side cannot drift apart: an unmapped target
raises rather than silently going untested.

Queries are grouped so that a whole gate comes back in one round trip through
`dax_query_operations`. Numeric and textual results are split into separate
blocks because a DAX UNION needs one type per column.

Run:  python python\\05_acceptance.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_contract as K  # noqa: E402
from config import POWERBI, STATS  # noqa: E402

EXPECTED_PATH = STATS / "05_expected_values.csv"
DAX_PATH = POWERBI / "05_acceptance.dax"

TECH_COLUMN = {
    "HYDRO": "hydro",
    "OTHER_RENEWABLES": "other_renewables",
    "WIND": "wind",
    "SOLAR": "solar",
}


class UnmappedTarget(RuntimeError):
    """Raised when a target has no acceptance query -- coverage must be total."""


def context(filters: dict, *, base_year: int | None = None) -> list[str]:
    """Turn a target's filter descriptor into CALCULATE arguments.

    The year and mode go onto the disconnected selector tables rather than onto
    DimYear or metric_key: that is exactly how a viewer drives the report, so the
    query exercises the same path the dashboard does.
    """
    parts: list[str] = []
    if "year" in filters:
        parts.append(f'SelReportYear[year] = {filters["year"]}')
    if "mode" in filters:
        parts.append(f'SelMode[mode_key] = "{filters["mode"]}"')
    if base_year is not None:
        parts.append(f"SelBaseYear[year] = {base_year}")
    if "entity" in filters:
        parts.append(f'DimEntity[entity] = "{filters["entity"]}"')
    if "technology" in filters and filters["technology"] in TECH_COLUMN:
        parts.append(f'DimMetric[technology] = "{TECH_COLUMN[filters["technology"]]}"')
    return parts


def calculate(measure: str, filters: dict, *, base_year: int | None = None) -> str:
    parts = context(filters, base_year=base_year)
    if not parts:
        return measure
    return f"CALCULATE( {measure}, " + ", ".join(parts) + " )"


# ---------------------------------------------------------------------------
# Structural checks that read the model directly rather than a measure
# ---------------------------------------------------------------------------

STRUCTURAL: dict[str, str] = {
    "P5_B2_FACT_ROWS": "COUNTROWS( FactEnergy )",
    "P5_B2_DIM_ENTITY_ROWS": "COUNTROWS( DimEntity )",
    "P5_B2_DIM_METRIC_ROWS": "COUNTROWS( DimMetric )",
    "P5_B2_DIM_YEAR_ROWS": "COUNTROWS( DimYear )",
    "P5_B2_CURRENT_COUNTRY_N":
        "CALCULATE( COUNTROWS( DimEntity ), DimEntity[is_current_country_or_territory] = 1 )",
    "P5_B2_ASEAN_N": "CALCULATE( COUNTROWS( DimEntity ), DimEntity[is_asean] = 1 )",
    # Documented on purpose: this cohort is 216, not 215, because USSR is
    # historical rather than aggregate. It must never drive a country filter.
    "P5_B2_NON_AGGREGATE_N": "CALCULATE( COUNTROWS( DimEntity ), DimEntity[is_aggregate] = 0 )",
    "P5_B2_MAIN_WINDOW_N": "CALCULATE( COUNTROWS( DimYear ), DimYear[is_main_asean_window] = 1 )",
    "P5_B2_DUPLICATE_KEYS":
        "COUNTROWS( FactEnergy ) - COUNTROWS( SUMMARIZE( FactEnergy, "
        "FactEnergy[entity], FactEnergy[year], FactEnergy[metric_key] ) )",
    "P5_B2_NEGATIVE_VALUES":
        "COUNTROWS( FILTER( FactEnergy, FactEnergy[value] < 0 ) ) + 0",
    "P5_B2_YEAR_2022_ROWS":
        "COUNTROWS( FILTER( FactEnergy, FactEnergy[year] = 2022 ) ) + 0",
    # This is the type test. If value were loaded as Fixed Decimal the engine
    # would have truncated at four places and this count would collapse to 0.
    "P5_B2_VALUES_OVER_4DP":
        "COUNTROWS( FILTER( FactEnergy, "
        "ROUND( FactEnergy[value], 4 ) <> FactEnergy[value] ) ) + 0",
    "P5_B7_AGGREGATE_IN_COUNTRY_LIST":
        "COUNTROWS( FILTER( DimEntity, "
        "DimEntity[is_asean] = 1 && DimEntity[is_aggregate] = 1 ) ) + 0",
    "P5_B9_ENTRY_KEY_ROWS":
        "CALCULATE( COUNTROWS( DimEntity ), DimEntity[is_asean] = 1 ) * 4",
    "P5_B9_ENTRY_STATUS_VALUES":
        "CALCULATE( COUNTROWS( DimEntity ), DimEntity[is_asean] = 1 ) * 4 * 2",
    "P5_B9_SMALL_MULTIPLE_POINTS":
        "CALCULATE( COUNTROWS( DimEntity ), DimEntity[is_asean] = 1 ) * "
        "CALCULATE( COUNTROWS( DimYear ), DimYear[is_main_asean_window] = 1 )",
}


def entry_grid_expression(mode_filter: str, threshold: str, comparison: str) -> str:
    """Count ASEAN countries whose series first clears a threshold in-window."""
    return f"""COUNTROWS(
            FILTER(
                CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 ),
                {comparison}
            )
        ) + 0"""


def target_expression(test_id: str, filters: dict) -> tuple[str, bool]:
    """Return (dax_scalar, is_text) for one target."""
    if test_id in STRUCTURAL:
        return STRUCTURAL[test_id], False

    # -- raw reads before any measure is trusted -----------------------------
    if test_id == "P5_B2_RAW_ASEAN_10_2021":
        return calculate("[ASEAN Gen TWh]", filters), False
    if test_id == "P5_B2_RAW_WORLD_REPORTED_2021":
        return calculate("[World Gen TWh]", filters), False

    # -- page 1 ---------------------------------------------------------------
    if test_id.startswith("P5_B7_ASEAN_TOTAL_") or test_id.startswith("P5_B7_ASEAN_MODERN_"):
        return calculate("[ASEAN Gen TWh]", filters), False
    if test_id.startswith("P5_B7_WORLD_TOTAL_"):
        return calculate("[World Gen TWh]", filters), False
    if test_id.startswith("P5_B7_ASEAN_SHARE_WORLD_"):
        return calculate("[ASEAN Share World]", filters), False
    if test_id.startswith("P5_B7_ABOVE005_"):
        return calculate("[Above 0.05 TWh N]", filters), False
    if test_id.startswith("P5_B7_MIX_") and test_id != "P5_B7_MIX_RESIDUAL_2021":
        # A single technology inside the ASEAN scope: 10 cells needed, not 40.
        return calculate('[ASEAN Gen TWh]', {**filters, "mode": "RENEWABLE_TOTAL"}), False
    if test_id == "P5_B7_MIX_RESIDUAL_2021":
        parts = " + ".join(
            f'CALCULATE( [ASEAN Gen TWh], SelReportYear[year] = 2021, '
            f'SelMode[mode_key] = "RENEWABLE_TOTAL", DimMetric[technology] = "{column}" )'
            for column in TECH_COLUMN.values()
        )
        total = ('CALCULATE( [ASEAN Gen TWh], SelReportYear[year] = 2021, '
                 'SelMode[mode_key] = "RENEWABLE_TOTAL" )')
        return f"( {parts} ) - {total}", False
    if test_id.startswith("P5_B7_ASEAN_RANK_"):
        return calculate("[ASEAN Rank]", filters), False
    if test_id.startswith("P5_B7_RANK_GAIN_"):
        return calculate("[Modern Rank Gain]", filters), False

    # -- page 2 ---------------------------------------------------------------
    if test_id.startswith("P5_B8_VN_TOTAL_") or test_id.startswith("P5_B8_VN_MODERN_"):
        return calculate("[Gen TWh @Year]", filters), False
    if test_id.startswith("P5_B8_VN_SHARE_ELEC_"):
        return calculate("[Share Electricity Pct @Year]", filters), False
    if test_id.startswith("P5_B8_VN_SHARE_ASEAN_"):
        return calculate("[Country Share ASEAN]", filters), False
    if test_id.startswith("P5_B8_VN_ASEAN_RANK_"):
        # 2000 modern must come back blank with a reason, not as a shared rank 1.
        if filters.get("year") == 2000 and filters.get("mode") == "MODERN_WIND_SOLAR":
            return calculate("[Rank Status]", filters), True
        return calculate("[ASEAN Rank]", filters), False
    if test_id.startswith("P5_B8_VN_GLOBAL_RANK_"):
        return calculate("[Global Rank]", filters), False
    if test_id.startswith("P5_B8_VN_RANKED_N_"):
        return calculate("[Global Ranked N]", filters), False
    if test_id.startswith("P5_B8_VN_OPPOSITE_"):
        mode = filters["mode"]
        return (
            f"""CONCATENATEX(
            FILTER(
                CALCULATETABLE(
                    VALUES( DimYear[year] ),
                    ALL( DimYear ),
                    DimYear[is_main_asean_window] = 1
                ),
                CALCULATE(
                    [Direction Relation],
                    DimEntity[entity] = "Vietnam",
                    SelMode[mode_key] = "{mode}"
                ) = "OPPOSITE_DIRECTION"
            ),
            DimYear[year],
            ",",
            DimYear[year],
            ASC
        )""",
            True,
        )

    # -- page 3 ---------------------------------------------------------------
    for name, measure in (
        ("TOP1_SHARE", "[Top1 Share]"),
        ("TOP3_SHARE", "[Top3 Share]"),
        ("HHI", "[HHI]"),
        ("GINI", "[Gini]"),
    ):
        if test_id.startswith(f"P5_B9_{name}_"):
            if filters.get("year") == 2000 and filters.get("mode") == "MODERN_WIND_SOLAR":
                return calculate("[Concentration Status]", filters), True
            return calculate(measure, filters), False
    if test_id.startswith("P5_B9_POSGROWTH_VN_"):
        return calculate("[Positive Growth Share]", {**filters, "year": 2021}, base_year=2010), False
    if test_id.startswith("P5_B9_ENTRY_"):
        family = filters["family"]
        status = test_id.split(f"{family}_", 1)[-1]
        return entry_status_count(filters["technology"], family, status), False
    if test_id.startswith("P5_B9_ENTRYCASE_"):
        return entry_case_expression(test_id, filters)
    if test_id.startswith("P5_B9_CF_PAIRS_") and test_id != "P5_B9_CF_PAIRS_TOTAL":
        return capacity_pair_count(filters["technology"]), False
    if test_id == "P5_B9_CF_PAIRS_TOTAL":
        return " + ".join(capacity_pair_count(t) for t in ("WIND", "SOLAR")), False
    if test_id.startswith("P5_B9_CF_COUNTRIES_"):
        return capacity_country_count(filters["technology"]), False
    if test_id in ("P5_B9_CF_MAX", "P5_B9_CF_MIN"):
        return capacity_extreme("MAXX" if test_id.endswith("MAX") else "MINX"), False

    raise UnmappedTarget(test_id)


def _entry_year_table(technology: str, threshold: float) -> str:
    """First in-window year where a country's series clears a threshold."""
    column = f"{TECH_COLUMN[technology]}_generation_twh"
    operator = ">" if threshold == 0 else ">="
    return f"""ADDCOLUMNS(
                CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 ),
                "@FirstYear",
                    CALCULATE(
                        MIN( FactEnergy[year] ),
                        ALL( DimMetric ),
                        DimMetric[metric_key] = "{column}",
                        ALL( DimYear ),
                        DimYear[is_main_asean_window] = 1,
                        FactEnergy[value] {operator} {threshold}
                    )
            )"""


def entry_status_count(technology: str, family: str, status: str) -> str:
    threshold = 0.0 if family == "entry_status" else K.MATERIAL_THRESHOLD_TWH
    table = _entry_year_table(technology, threshold)
    if status.endswith("AT_WINDOW_START"):
        predicate = f"[@FirstYear] = {K.YEAR_START}"
    elif status.startswith("NOT_"):
        predicate = "ISBLANK( [@FirstYear] )"
    else:
        predicate = f"NOT ISBLANK( [@FirstYear] ) && [@FirstYear] > {K.YEAR_START}"
    return f"COUNTROWS( FILTER( {table}, {predicate} ) ) + 0"


def entry_case_expression(test_id: str, filters: dict) -> tuple[str, bool]:
    """One named entry case: a status label, an event year, or a censored blank."""
    technology = filters["technology"]
    entity = filters["entity"]
    material = "MATERIAL" in test_id
    threshold = K.MATERIAL_THRESHOLD_TWH if material else 0.0
    column = f"{TECH_COLUMN[technology]}_generation_twh"
    operator = ">" if threshold == 0 else ">="
    first_year = f"""CALCULATE(
            MIN( FactEnergy[year] ),
            ALL( DimEntity ),
            DimEntity[entity] = "{entity}",
            ALL( DimMetric ),
            DimMetric[metric_key] = "{column}",
            ALL( DimYear ),
            DimYear[is_main_asean_window] = 1,
            FactEnergy[value] {operator} {threshold}
        )"""
    if test_id.endswith("_STATUS"):
        at_start = "MATERIAL_AT_WINDOW_START" if material else "ACTIVE_AT_WINDOW_START"
        transition = "OBSERVED_MATERIAL_TRANSITION" if material else "OBSERVED_TRANSITION"
        never = "NOT_MATERIAL_BY_2021" if material else "NOT_OBSERVED_BY_2021"
        return (
            f"""VAR _First = {first_year}
        RETURN
            SWITCH(
                TRUE(),
                ISBLANK( _First ), "{never}",
                _First = {K.YEAR_START}, "{at_start}",
                "{transition}"
            )""",
            True,
        )
    # Matched on the whole suffix, not on a trailing token: `rsplit("_", 1)` here
    # returned "2000" and the branch never fired, so both lag cases emitted the
    # entry YEAR -- 2006 against an expected 6 -- and would have failed at B10.
    if test_id.endswith("_LAG_FROM_2000"):
        # Left-censored series keep a status and no lag. Writing 0 here would
        # claim we watched it start in 2000.
        return (
            f"""VAR _First = {first_year}
        RETURN
            IF( NOT ISBLANK( _First ) && _First > {K.YEAR_START}, _First - {K.YEAR_START} )""",
            False,
        )
    return (
        f"""VAR _First = {first_year}
        RETURN
            IF( NOT ISBLANK( _First ) && _First > {K.YEAR_START}, _First )""",
        False,
    )


def _capacity_pairs(technology: str) -> str:
    """The country-year grid where a technology has both capacity and generation.

    Built from CROSSJOIN rather than SUMMARIZECOLUMNS: the latter is rejected
    inside a ROW() the way these acceptance queries are assembled. The grid is
    10 countries x 22 years, so materialising it costs nothing.

    The `capacity > 0` predicate is what turns the raw 132 pairs into 104. No
    dropped pair carries positive generation, so nothing observable is lost.
    """
    column = TECH_COLUMN[technology]
    return f"""FILTER(
                ADDCOLUMNS(
                    CROSSJOIN(
                        CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 ),
                        CALCULATETABLE( VALUES( DimYear[year] ), ALL( DimYear ), DimYear[is_main_asean_window] = 1 )
                    ),
                    "@Capacity",
                        CALCULATE(
                            SUM( FactEnergy[value] ),
                            ALL( DimMetric ),
                            DimMetric[metric_key] = "{column}_capacity_gw"
                        ),
                    "@Generation",
                        CALCULATE(
                            SUM( FactEnergy[value] ),
                            ALL( DimMetric ),
                            DimMetric[metric_key] = "{column}_generation_twh"
                        )
                ),
                [@Capacity] > 0 && NOT ISBLANK( [@Generation] )
            )"""


def capacity_pair_count(technology: str) -> str:
    return f"COUNTROWS( {_capacity_pairs(technology)} ) + 0"


def capacity_country_count(technology: str) -> str:
    # DISTINCT over a projection rather than SUMMARIZE: SUMMARIZE over a derived
    # table is fragile, and the count here is what warns the reader that the
    # capacity chart covers 2 countries for wind and 4 for solar, not all ten.
    return f"""COUNTROWS(
            DISTINCT(
                SELECTCOLUMNS( {_capacity_pairs(technology)}, "@Country", DimEntity[entity] )
            )
        ) + 0"""


def capacity_extreme(aggregator: str) -> str:
    parts = [
        f'{aggregator}( {_capacity_pairs(technology)}, '
        f'DIVIDE( [@Generation], [@Capacity] * {K.CAPACITY_FACTOR_DIVISOR} ) )'
        for technology in ("WIND", "SOLAR")
    ]
    function = "MAX" if aggregator == "MAXX" else "MIN"
    return f"{function}( {parts[0]}, {parts[1]} )"


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

HEADER = f"""// =====================================================================
// Phase 5 -- acceptance queries
// Generated by python\\05_acceptance.py. DO NOT edit by hand.
//
// How to run: through MCP `dax_query_operations`, one EVALUATE block at a time.
// Set maxRows explicitly -- the largest block returns 54 rows and a default row
// cap silently truncates the result, which reads as missing tests.
// Collect every block into output\\stats\\05_test_results.tsv with the three
// columns `test_id`, `actual_value`, `actual_text`, then run:
//     python python\\05_validate.py
//
// Reconciliation ALWAYS happens on the STORAGE scale of 03_fact_metrics.csv.
// Only share_electricity_pct is held on 0-100; every other ratio is on 0-1.
// Comparing a stored ratio of 0.671023268910 against a displayed 67.102326891
// is off by 66.43 -- that is a unit error, not a rounding difference.
//
// Method version: {K.METHOD_VERSION}
// Phase 2 fingerprint: {K.EXPECTED_PHASE2_INPUT_FINGERPRINT}
// =====================================================================
"""


def main() -> int:
    with EXPECTED_PATH.open(encoding="utf-8") as handle:
        targets = list(csv.DictReader(handle))

    numeric: dict[str, list[tuple[str, str]]] = {}
    textual: dict[str, list[tuple[str, str]]] = {}
    for target in targets:
        filters = json.loads(target["filter_json"])
        expression, is_text = target_expression(target["test_id"], filters)
        bucket = textual if is_text else numeric
        bucket.setdefault(target["gate_id"], []).append((target["test_id"], expression))

    chunks = [HEADER]
    for gate in sorted(set(numeric) | set(textual)):
        for label, bucket, column, wrapper in (
            ("numeric", numeric, "actual_value", "{expr}"),
            ("text", textual, "actual_text", '{expr} & ""'),
        ):
            rows = bucket.get(gate, [])
            if not rows:
                continue
            chunks.append(f"\n// ---- Gate {gate} -- {label} results ({len(rows)} cells) ----")
            body = ",\n".join(
                f'    ROW( "test_id", "{test_id}", "{column}", '
                f'{wrapper.format(expr=expression)} )'
                for test_id, expression in rows
            )
            chunks.append(f"EVALUATE\nUNION(\n{body}\n)\n")

    DAX_PATH.parent.mkdir(parents=True, exist_ok=True)
    DAX_PATH.write_text("\n".join(chunks), encoding="utf-8", newline="\r\n")

    total = sum(len(v) for v in numeric.values()) + sum(len(v) for v in textual.values())
    if total != len(targets):
        raise UnmappedTarget(f"mapped {total} of {len(targets)} targets")
    blocks = sum(1 for chunk in chunks if chunk.startswith("EVALUATE"))
    print(
        f"PHASE 5 ACCEPTANCE DAX: PASS | targets={total} | blocks={blocks} | "
        f"numeric={sum(len(v) for v in numeric.values())} | "
        f"text={sum(len(v) for v in textual.values())}"
    )
    print(f"  -> {DAX_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UnmappedTarget as error:
        print(f"PHASE 5 ACCEPTANCE DAX: FAIL | target không có truy vấn: {error}", file=sys.stderr)
        raise SystemExit(1)
