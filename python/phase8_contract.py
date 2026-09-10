"""Locked, data-only contract for the sequential Phase 8 SQL verification.

The verifier and its fault-injection tests import this module so gate order,
release baselines, and the public CSV interface cannot drift independently.
"""
from __future__ import annotations

from typing import Final


METHOD_VERSION: Final = "phase8_v1"
PHASE8_METHOD_VERSION: Final = METHOD_VERSION

EXPECTED_PHASE2_INPUT_FINGERPRINT: Final = (
    "64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10"
)
EXPECTED_ARCHIVE_CSV_COUNT: Final = 17
EXPECTED_PHASE2_FACT_ROWS: Final = 89_075
EXPECTED_PHASE2_VALIDATION_ROWS: Final = 864
EXPECTED_PHASE2_VALIDATION_STATUS_COUNTS: Final = {
    "PASS": 560,
    "WARN": 268,
    "SKIP": 36,
}
EXPECTED_PHASE2_BLOCKING_ROWS: Final = 34

EXPECTED_PHASE3_FACT_ROWS: Final = 18_926
EXPECTED_PHASE3_CROSSCHECK_ROWS: Final = 18_926
EXPECTED_PHASE3_VALIDATION_ROWS: Final = 92
EXPECTED_PHASE3_QUESTION_ROWS: Final = {
    "Q1": 5_544,
    "Q2": 3_608,
    "Q3": 1_980,
    "Q4": 1_382,
    "Q5": 5_950,
    "Q6": 462,
}
EXPECTED_PHASE4_VALIDATION_ROWS: Final = 38

YEAR_START: Final = 2000
YEAR_END: Final = 2021
YEAR_COUNT: Final = YEAR_END - YEAR_START + 1
ASEAN_ENTITY_COUNT: Final = 10
TECHNOLOGY_COUNT: Final = 4
MATERIAL_THRESHOLD_TWH: Final = 0.05
NUMERIC_TOLERANCE: Final = 1e-9

GATE_IDS: Final = tuple(f"P8-{number:02d}" for number in range(9))
FINAL_GATE_ID: Final = "P8-FINAL"
ALL_GATE_IDS: Final = (*GATE_IDS, FINAL_GATE_ID)
GATE_STEP_NAMES: Final = {
    "P8-00": "Tien dieu kien lien phase",
    "P8-01": "Kiem dinh V1-V8",
    "P8-02": "Xep hang theo nam",
    "P8-03": "Tang truong YoY",
    "P8-04": "Nam dau tien duong",
    "P8-05": "Tich luy va trung binh truot",
    "P8-06": "Thay doi thu hang",
    "P8-07": "Muc tap trung",
    "P8-08": "Doi chieu tong va tai lap",
    "P8-FINAL": "Quyet dinh hoan thanh Phase 8",
}

EXPECTED_METRIC_ROWS: Final = {
    "asean_rank": 440,
    "global_rank": 132,
    "modern_rank_gain": 220,
    "yoy": 396,
    "q5_yoy": 1_100,
    "first_positive_in_window": 40,
    "first_material_in_window": 40,
    "cumulative_generation_twh": 264,
    "rolling_mean_3y_twh": 264,
    "rank_gain_over_time": 60,
    "top1_share": 44,
    "top3_share": 44,
    "hhi": 44,
    "gini": 44,
    "positive_n": 44,
    "above_0_05_n": 44,
}

ENTRY_STATUS_VALUES: Final = frozenset({
    "ACTIVE_AT_WINDOW_START",
    "OBSERVED_TRANSITION",
    "NOT_OBSERVED_BY_2021",
    "UNKNOWN_INCOMPLETE_SERIES",
})
MATERIAL_ENTRY_STATUS_VALUES: Final = frozenset({
    "MATERIAL_AT_WINDOW_START",
    "OBSERVED_MATERIAL_TRANSITION",
    "NOT_MATERIAL_BY_2021",
    "UNKNOWN_INCOMPLETE_SERIES",
})

VALIDATION_COLUMNS: Final = (
    "gate_id",
    "step_name",
    "status",
    "expected",
    "observed",
    "details",
    "method_version",
    "phase2_input_fingerprint",
)
VALIDATION_STATUS_VALUES: Final = frozenset({"PASS", "FAIL"})
OUTPUT_FILE_NAME: Final = "08_validation_results.csv"


def _validate_contract() -> None:
    """Fail on import if the supposedly locked contract is inconsistent."""
    expected_gates = tuple(f"P8-{number:02d}" for number in range(9))
    if GATE_IDS != expected_gates:
        raise RuntimeError("Phase 8 task gates must be the ordered sequence P8-00..P8-08")
    if tuple(GATE_STEP_NAMES) != ALL_GATE_IDS:
        raise RuntimeError("Every Phase 8 gate must have exactly one ordered step name")
    if len(ALL_GATE_IDS) != len(set(ALL_GATE_IDS)):
        raise RuntimeError("Phase 8 gate identifiers must be unique")
    if sum(EXPECTED_PHASE3_QUESTION_ROWS.values()) != EXPECTED_PHASE3_FACT_ROWS:
        raise RuntimeError("Phase 3 question rows must sum to the fact-row baseline")
    if EXPECTED_PHASE2_BLOCKING_ROWS != 34:
        raise RuntimeError("The Phase 2 blocking-check baseline must remain 34")
    if set(EXPECTED_PHASE2_VALIDATION_STATUS_COUNTS) != {"PASS", "WARN", "SKIP"}:
        raise RuntimeError("Phase 2 status baseline must contain PASS/WARN/SKIP only")
    if len(VALIDATION_COLUMNS) != len(set(VALIDATION_COLUMNS)):
        raise RuntimeError("Phase 8 validation CSV columns must be unique")


_validate_contract()
