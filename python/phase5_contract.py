"""Locked release contract shared by the Phase 5 dashboard build and its verifier.

This module holds data and lightweight import-time checks only. The literals in
`LOCKED_*` are transcribed by hand from `PHASE5.md` section 5. `05_expected.py`
recomputes every one of them from `output/clean/` and `output/stats/` and refuses
to publish when a recomputed value disagrees, so the contract and the data act as
two independent sources rather than one echoing the other.

The `PHASE5.md` literals are display-rounded to roughly twelve significant
figures, which is why `LOCKED_REL_TOLERANCE` is looser than the `1e-9` absolute
tolerance that Power BI results are held to. Do not confuse the two: the first
compares a document against the data, the second compares DAX against the data.
"""
from __future__ import annotations

from typing import Final


# ---------------------------------------------------------------------------
# Release baseline
# ---------------------------------------------------------------------------

METHOD_VERSION: Final = "phase5_v1"
POWERBI_DESKTOP_VERSION: Final = "2.157.1354.0"

EXPECTED_PHASE2_INPUT_FINGERPRINT: Final = (
    "64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10"
)
EXPECTED_PHASE2_FACT_ENERGY_SHA256: Final = (
    "dfaca2c46efde54b506f317497d458ed864f88ab4a8d74de9665afaa467a4374"
)
EXPECTED_ARCHIVE_CSV_COUNT: Final = 17
EXPECTED_FACT_ROWS: Final = 89_075
EXPECTED_PHASE2_VALIDATION_ROWS: Final = 864
EXPECTED_PHASE3_FACT_METRIC_ROWS: Final = 18_926
EXPECTED_PHASE3_VALIDATION_ROWS: Final = 92
EXPECTED_PHASE4_VALIDATION_ROWS: Final = 38

YEAR_START: Final = 2000
YEAR_END: Final = 2021
YEARS: Final = tuple(range(YEAR_START, YEAR_END + 1))
PROBE_YEARS: Final = (2000, 2010, 2021)

MATERIAL_THRESHOLD_TWH: Final = 0.05
CAPACITY_FACTOR_DIVISOR: Final = 8.76
HASH_ALGORITHM: Final = "sha256"

# Absolute tolerance every Power BI result is held to, on the STORAGE scale.
NUMERIC_TOLERANCE: Final = 1e-9
# Relative tolerance used only when checking this file against recomputed data.
LOCKED_REL_TOLERANCE: Final = 1e-10


# ---------------------------------------------------------------------------
# Model contract
# ---------------------------------------------------------------------------

MODEL_NAME: Final = "ASEAN_Renewables"

# B2 step 6: a fixed file list, never "load every CSV in the folder".
OPERATIONAL_TABLES: Final = {
    "FactEnergy": "fact_energy.csv",
    "DimEntity": "dim_entity.csv",
    "DimMetric": "dim_metric.csv",
    "DimYear": "dim_year.csv",
}
# B2 step 4: declared but not loaded into the presentation model.
AUDIT_TABLES: Final = (
    "source_metric_catalog.csv",
    "missingness_audit.csv",
    "cleaning_audit.csv",
)
SELECTOR_TABLES: Final = ("SelReportYear", "SelMode", "SelBaseYear")

EXPECTED_DIM_ENTITY_ROWS: Final = 256
EXPECTED_DIM_METRIC_ROWS: Final = 16
EXPECTED_DIM_YEAR_ROWS: Final = 57
EXPECTED_DIM_YEAR_MIN: Final = 1965
EXPECTED_DIM_YEAR_MAX: Final = 2021

# The flag-column contract. These three columns define the three cohorts used
# throughout Phase 5; nothing may be derived another way.
EXPECTED_CURRENT_COUNTRY_ROWS: Final = 215
EXPECTED_ASEAN_ROWS: Final = 10
EXPECTED_MAIN_WINDOW_ROWS: Final = 22
# The trap: is_aggregate = 0 is NOT the same cohort. It returns 216 because USSR
# is entity_type = historical -- not an aggregate, but not a current country
# either. Using it for the "no aggregates in the country list" rule would put
# USSR into the country filter and make Gate B2 contradict Gate B7.
EXPECTED_NON_AGGREGATE_ROWS: Final = 216

# B2 step 5: values carrying more than four decimal places, which a fixed-point
# column type would silently truncate.
#
# `PHASE5.md` locks this at 36.027. That figure was counted by looking for a "."
# in the CSV text and measuring the digits after it, which silently skips the
# three values written in scientific notation -- Bulgaria 2007 `3e-05`, Russia
# 2010 `1e-05` and Vietnam 2000 `2e-06`, all in `solar_capacity_gw`. They do have
# five or six decimal places, so the correct count is 36.030. Both the reference
# side and the DAX side now use the same predicate the engine uses,
# `ROUND(value, 4) <> value`, so the two cannot diverge on notation again.
EXPECTED_VALUES_OVER_4DP: Final = 36_030
EXPECTED_VALUES_OVER_4DP_DOCUMENT_FIGURE: Final = 36_027

RELATIONSHIPS: Final = (
    ("DimEntity", "entity", "FactEnergy", "entity"),
    ("DimYear", "year", "FactEnergy", "year"),
    ("DimMetric", "metric_key", "FactEnergy", "metric_key"),
)

ASEAN_10: Final = (
    "Brunei",
    "Cambodia",
    "Indonesia",
    "Laos",
    "Malaysia",
    "Myanmar",
    "Philippines",
    "Singapore",
    "Thailand",
    "Vietnam",
)

GENERATION_METRICS: Final = {
    "HYDRO": "hydro_generation_twh",
    "OTHER_RENEWABLES": "other_renewables_generation_twh",
    "WIND": "wind_generation_twh",
    "SOLAR": "solar_generation_twh",
}
MODE_TECHNOLOGIES: Final = {
    "RENEWABLE_TOTAL": ("HYDRO", "OTHER_RENEWABLES", "WIND", "SOLAR"),
    "MODERN_WIND_SOLAR": ("WIND", "SOLAR"),
}
MODES: Final = tuple(MODE_TECHNOLOGIES)
DEFAULT_MODE: Final = "RENEWABLE_TOTAL"
DEFAULT_REPORT_YEAR: Final = 2021
DEFAULT_BASE_YEAR: Final = 2010

# share_electricity_pct does NOT use the total's completeness rule.
# RENEWABLE_TOTAL is a 1/1 pass-through of the source column; summing the four
# components gives Vietnam 2021 = 42,513379% instead of the locked 42,578747%,
# and the model has no other_renewables_share_electricity_pct anyway.
SHARE_ELECTRICITY_METRICS: Final = {
    "RENEWABLE_TOTAL": ("renewables_share_electricity_pct",),
    "MODERN_WIND_SOLAR": ("wind_share_electricity_pct", "solar_share_electricity_pct"),
}

# Storage scale, kept separate from the display scale in format_string.
# The last three were added after auditing 03_fact_metrics.csv; without them
# q5_pct_point_change, modern_rank_gain and the entry statuses have no legal
# unit_stored and cannot be reconciled at B10.
UNIT_STORED_VALUES: Final = (
    "ratio",
    "pct",
    "TWh",
    "GW",
    "count",
    "rank",
    "year",
    "percentage_point",
    "rank_change",
    "STATUS_CODE",
)
# Only share_electricity_pct is stored on the 0-100 scale.
PCT_SCALE_METRICS: Final = ("share_electricity_pct",)


# ---------------------------------------------------------------------------
# Locked acceptance values -- transcribed from PHASE5.md section 5
# ---------------------------------------------------------------------------

# 5.1 Regional KPI by year: ASEAN total, modern, World total, ASEAN/World ratio,
# and the count of countries at or above 0,05 TWh for each mode.
LOCKED_REGIONAL_KPI: Final = {
    2000: {
        "asean_total_twh": 72.800904,
        "asean_modern_twh": 0.0,
        "world_total_twh": 2854.49,
        "asean_share_world": 0.0255039968611,
        "above_0_05_n_total": 8,
        "above_0_05_n_modern": 0,
    },
    2010: {
        "asean_total_twh": 111.2779545,
        "asean_modern_twh": 0.13,
        "world_total_twh": 4182.39,
        "asean_share_world": 0.026606307518,
        "above_0_05_n_total": 8,
        "above_0_05_n_modern": 2,
    },
    2021: {
        "asean_total_twh": 289.6557446,
        "asean_modern_twh": 42.73,
        "world_total_twh": 7885.04005,
        "asean_share_world": 0.0367348476055,
        "above_0_05_n_total": 9,
        "above_0_05_n_modern": 8,
    },
}

# B7: the 2021 four-technology split. The four must add back to the KPI exactly.
LOCKED_ASEAN_MIX_2021: Final = {
    "HYDRO": 185.58,
    "OTHER_RENEWABLES": 61.3457446,
    "SOLAR": 34.43,
    "WIND": 8.30,
}

# 5.2 ASEAN ranking in 2021, rank -> country, for both modes.
LOCKED_ASEAN_RANK_2021: Final = {
    "RENEWABLE_TOTAL": {
        1: "Vietnam",
        2: "Indonesia",
        3: "Malaysia",
        4: "Laos",
        5: "Thailand",
        6: "Philippines",
        7: "Myanmar",
        8: "Cambodia",
        9: "Singapore",
        10: "Brunei",
    },
    "MODERN_WIND_SOLAR": {
        1: "Vietnam",
        2: "Thailand",
        3: "Philippines",
        4: "Malaysia",
        5: "Singapore",
        6: "Indonesia",
        7: "Cambodia",
        8: "Myanmar",
        9: "Laos",
        10: "Brunei",
    },
}

# B7: switching to the modern measure moves these three the most.
LOCKED_MODERN_RANK_GAIN_2021: Final = {
    "Singapore": 4,
    "Indonesia": -4,
    "Laos": -5,
}

# 5.3 Vietnam. share_electricity_pct is already on the 0-100 scale; the two
# country_share_asean figures below are ratios on 0-1. They sit next to each
# other but are not on the same scale.
LOCKED_VIETNAM: Final = {
    2000: {
        "total_twh": 14.55,
        "modern_twh": 0.0,
        "share_electricity_total_pct": 54.781628,
        "share_electricity_modern_pct": 0.0,
        "asean_rank_total": 3,
        "asean_rank_modern": None,  # ZERO_SCOPE_TOTAL
    },
    2010: {
        "total_twh": 28.625,
        "modern_twh": 0.05,
        "share_electricity_total_pct": 31.203663,
        "share_electricity_modern_pct": 0.0545137375,
        "asean_rank_total": 2,
        "asean_rank_modern": 2,
    },
    2021: {
        "total_twh": 104.2180361,
        "modern_twh": 28.16,
        "share_electricity_total_pct": 42.578747,
        "share_electricity_modern_pct": 11.5046779,
        "asean_rank_total": 1,
        "asean_rank_modern": 1,
    },
}

LOCKED_VIETNAM_SHARE_ASEAN_2021: Final = {
    "RENEWABLE_TOTAL": 0.359799651976,
    "MODERN_WIND_SOLAR": 0.659021764568,
}

# 5.3: population_n is 215 everywhere, but the displayed denominator is
# ranked_n, which moves with both year and mode. Never hard-code 205/209.
LOCKED_VIETNAM_GLOBAL_RANK: Final = {
    (2000, "RENEWABLE_TOTAL"): (31, 209),
    (2000, "MODERN_WIND_SOLAR"): (40, 212),
    (2010, "RENEWABLE_TOTAL"): (25, 211),
    (2010, "MODERN_WIND_SOLAR"): (53, 214),
    (2021, "RENEWABLE_TOTAL"): (16, 205),
    (2021, "MODERN_WIND_SOLAR"): (17, 209),
}
LOCKED_GLOBAL_RANK_POPULATION_N: Final = 215

# 5.4 Concentration, all four stored on the ratio scale.
# 2000 modern is the mandatory edge case: NOT_DEFINED / ZERO_DENOMINATOR.
LOCKED_CONCENTRATION: Final = {
    (2000, "RENEWABLE_TOTAL"): {
        "top1_share": 0.269227426077,
        "top3_share": 0.735155720044,
        "hhi": 0.204478848183,
        "gini": 0.555271560914,
    },
    (2000, "MODERN_WIND_SOLAR"): {
        "top1_share": None,
        "top3_share": None,
        "hhi": None,
        "gini": None,
    },
    (2010, "RENEWABLE_TOTAL"): {
        "top1_share": 0.311202700981,
        "top3_share": 0.7315465167,
        "hhi": 0.208080520146,
        "gini": 0.550964517864,
    },
    (2010, "MODERN_WIND_SOLAR"): {
        "top1_share": 0.461538461538,
        "top3_share": 1.0,
        "hhi": 0.384615384615,
        "gini": 0.761538461538,
    },
    (2021, "RENEWABLE_TOTAL"): {
        "top1_share": 0.359799651976,
        "top3_share": 0.67102326891,
        "hhi": 0.207886216029,
        "gini": 0.529218182611,
    },
    (2021, "MODERN_WIND_SOLAR"): {
        "top1_share": 0.659021764568,
        "top3_share": 0.922536859349,
        "hhi": 0.480403925201,
        "gini": 0.771284811608,
    },
}
ZERO_DENOMINATOR_REASON: Final = "ZERO_DENOMINATOR"
ZERO_SCOPE_TOTAL_REASON: Final = "ZERO_SCOPE_TOTAL"

# B9: Vietnam's share of the gross positive addition, 2010-2021.
LOCKED_POSITIVE_GROWTH_SHARE_VN_2010_2021: Final = {
    "MODERN_WIND_SOLAR": 0.65985915493,
    "RENEWABLE_TOTAL": 0.423780539369,
}
POSITIVE_GROWTH_DENOMINATOR_BASIS: Final = "GROSS_POSITIVE_ADDITION"

# 5.5 Technology entry: 40 key rows (10 countries x 4 technologies), each
# carrying two independent status families, so 80 status values -- not 40.
LOCKED_ENTRY_KEY_ROWS: Final = 40
LOCKED_ENTRY_STATUS_VALUES: Final = 80
LOCKED_ENTRY_COUNTS: Final = {
    ("HYDRO", "entry_status"): {"ACTIVE_AT_WINDOW_START": 8, "NOT_OBSERVED_BY_2021": 2},
    ("HYDRO", "material_entry_status"): {
        "MATERIAL_AT_WINDOW_START": 8,
        "NOT_MATERIAL_BY_2021": 2,
    },
    ("OTHER_RENEWABLES", "entry_status"): {
        "ACTIVE_AT_WINDOW_START": 5,
        "OBSERVED_TRANSITION": 4,
        "NOT_OBSERVED_BY_2021": 1,
    },
    ("OTHER_RENEWABLES", "material_entry_status"): {
        "MATERIAL_AT_WINDOW_START": 5,
        "OBSERVED_MATERIAL_TRANSITION": 4,
        "NOT_MATERIAL_BY_2021": 1,
    },
    ("SOLAR", "entry_status"): {"OBSERVED_TRANSITION": 9, "NOT_OBSERVED_BY_2021": 1},
    ("SOLAR", "material_entry_status"): {
        "OBSERVED_MATERIAL_TRANSITION": 8,
        "NOT_MATERIAL_BY_2021": 2,
    },
    ("WIND", "entry_status"): {"OBSERVED_TRANSITION": 4, "NOT_OBSERVED_BY_2021": 6},
    ("WIND", "material_entry_status"): {
        "OBSERVED_MATERIAL_TRANSITION": 4,
        "NOT_MATERIAL_BY_2021": 6,
    },
}

# 5.5 named cases. Vietnam solar never takes the value 0,05 exactly: it is
# positive from 2010 and first clears the material threshold in 2018 at 0,10 TWh.
LOCKED_ENTRY_CASES: Final = {
    ("Vietnam", "HYDRO"): {
        "entry_status": "ACTIVE_AT_WINDOW_START",
        "observed_entry_year": None,
        "lag_from_2000": None,
    },
    ("Vietnam", "SOLAR"): {
        "entry_status": "OBSERVED_TRANSITION",
        "observed_entry_year": 2010,
        "observed_material_entry_year": 2018,
        "lag_from_2000": 10,
    },
    ("Brunei", "SOLAR"): {
        "entry_status": "NOT_OBSERVED_BY_2021",
        "material_entry_status": "NOT_MATERIAL_BY_2021",
        "observed_entry_year": None,
    },
    ("Cambodia", "OTHER_RENEWABLES"): {
        "entry_status": "OBSERVED_TRANSITION",
        "observed_entry_year": 2006,
        "lag_from_2000": 6,
    },
}

# 5.6 Approximate capacity factor. The 104 comes from the capacity_gw > 0
# filter: a raw join over the window gives 132 pairs, and the 28 dropped pairs
# all have zero capacity. None of the dropped pairs has positive generation, so
# the filter loses no observation.
LOCKED_CAPACITY_FACTOR: Final = {
    "raw_pairs": 132,
    "kept_pairs": 104,
    "dropped_pairs": 28,
    "raw_wind": 44,
    "raw_solar": 88,
    "kept_wind": 33,
    "kept_solar": 71,
    "dropped_wind": 11,
    "dropped_solar": 17,
    "max_value": 0.3257639133464354,
    "min_value": 0.0,
}
LOCKED_CAPACITY_FACTOR_COVERAGE: Final = {
    "WIND": {"Philippines": 17, "Thailand": 16},
    "SOLAR": {"Malaysia": 15, "Philippines": 18, "Thailand": 16, "Vietnam": 22},
}

# B8: the years where Vietnam's TWh and share of electricity move in opposite
# directions. Two for the renewable total, one for the modern measure.
LOCKED_VIETNAM_OPPOSITE_YEARS: Final = {
    "RENEWABLE_TOTAL": (2003, 2014),
    "MODERN_WIND_SOLAR": (2016,),
}

# B9: a full 22-year series across the ten-country grid.
LOCKED_SMALL_MULTIPLE_POINTS: Final = 220


# ---------------------------------------------------------------------------
# Import-time self checks
# ---------------------------------------------------------------------------

def _validate_contract() -> None:
    if len(ASEAN_10) != EXPECTED_ASEAN_ROWS:
        raise RuntimeError("ASEAN_10 must list exactly ten countries")
    if len(YEARS) != EXPECTED_MAIN_WINDOW_ROWS:
        raise RuntimeError("The main analysis window must span 22 years")
    if EXPECTED_NON_AGGREGATE_ROWS == EXPECTED_CURRENT_COUNTRY_ROWS:
        raise RuntimeError(
            "is_aggregate = 0 and is_current_country_or_territory = 1 must stay "
            "distinct cohorts; collapsing them readmits USSR"
        )
    if len(MODE_TECHNOLOGIES["RENEWABLE_TOTAL"]) != 4:
        raise RuntimeError("RENEWABLE_TOTAL must carry four components")
    if len(MODE_TECHNOLOGIES["MODERN_WIND_SOLAR"]) != 2:
        raise RuntimeError("MODERN_WIND_SOLAR must carry two components")
    if set(MODE_TECHNOLOGIES) != set(MODES):
        raise RuntimeError("Mode table and mode technology map disagree")
    if len(SHARE_ELECTRICITY_METRICS["RENEWABLE_TOTAL"]) != 1:
        raise RuntimeError(
            "share_electricity_pct for the renewable total is a 1/1 pass-through; "
            "summing four components produces 42,513379% for Vietnam 2021"
        )
    if LOCKED_ENTRY_STATUS_VALUES != LOCKED_ENTRY_KEY_ROWS * 2:
        raise RuntimeError("Each entry key row carries exactly two status families")
    if LOCKED_SMALL_MULTIPLE_POINTS != len(ASEAN_10) * len(YEARS):
        raise RuntimeError("Small multiple point count must be 10 countries x 22 years")

    cf = LOCKED_CAPACITY_FACTOR
    if cf["kept_wind"] + cf["kept_solar"] != cf["kept_pairs"]:
        raise RuntimeError("Capacity factor kept pairs must split into wind and solar")
    if cf["raw_pairs"] - cf["dropped_pairs"] != cf["kept_pairs"]:
        raise RuntimeError("Capacity factor raw minus dropped must equal kept")
    for technology, coverage in LOCKED_CAPACITY_FACTOR_COVERAGE.items():
        expected = cf["kept_wind"] if technology == "WIND" else cf["kept_solar"]
        if sum(coverage.values()) != expected:
            raise RuntimeError(f"Capacity factor coverage for {technology} does not sum")

    mix_total = sum(LOCKED_ASEAN_MIX_2021.values())
    if abs(mix_total - LOCKED_REGIONAL_KPI[2021]["asean_total_twh"]) > 1e-9:
        raise RuntimeError("The 2021 four-technology mix must add back to the KPI")

    for mode, ranking in LOCKED_ASEAN_RANK_2021.items():
        if sorted(ranking) != list(range(1, 11)):
            raise RuntimeError(f"{mode} ranking must cover ranks 1..10")
        if set(ranking.values()) != set(ASEAN_10):
            raise RuntimeError(f"{mode} ranking must name each ASEAN country once")

    for country, gain in LOCKED_MODERN_RANK_GAIN_2021.items():
        total_rank = next(
            r for r, name in LOCKED_ASEAN_RANK_2021["RENEWABLE_TOTAL"].items()
            if name == country
        )
        modern_rank = next(
            r for r, name in LOCKED_ASEAN_RANK_2021["MODERN_WIND_SOLAR"].items()
            if name == country
        )
        # modern_rank_gain = total_rank - modern_rank; positive means better.
        if total_rank - modern_rank != gain:
            raise RuntimeError(f"modern_rank_gain for {country} contradicts the tables")

    # Top-1 in 2021 is the same quantity as Vietnam's share of ASEAN, because
    # both use the ASEAN_SUM_10 denominator and Vietnam leads in both modes.
    for mode, share in LOCKED_VIETNAM_SHARE_ASEAN_2021.items():
        if abs(LOCKED_CONCENTRATION[(2021, mode)]["top1_share"] - share) > 1e-12:
            raise RuntimeError(
                f"top1_share and Vietnam's ASEAN share must agree for {mode} in 2021"
            )

    if set(PCT_SCALE_METRICS) - set(UNIT_STORED_VALUES) - {"share_electricity_pct"}:
        raise RuntimeError("Percent-scale metric list is inconsistent")


_validate_contract()
