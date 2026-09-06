"""Shared Phase 2 fingerprint and validation-gate contract."""
from __future__ import annotations

import hashlib
import sqlite3

import pandas as pd


EXPECTED_VALIDATION_ROWS = 864
REQUIRED_BLOCKING_CHECK_IDS = (
    "S01_CATALOG_ROWS",
    "S02_SOURCE_FILES",
    "S03_CANONICAL_FILES",
    "S04_AUDIT_FILES",
    "S05_EXCLUDED_FILES",
    "S06_CANONICAL_METRICS",
    "S07_DIM_METRIC_ROWS",
    "S08_DIM_ENTITY_ROWS",
    "S09_CURRENT_ENTITIES",
    "S10_ASEAN_ENTITIES",
    "S11_FACT_ROWS",
    "S12_ZERO_ROWS",
    "S13_POSITIVE_ROWS",
    "S14_ENTITY_YEAR_KEYS",
    "S15_MAIN_WINDOW_YEARS",
    "S16_ASEAN_MAIN_PANEL",
    "S17_PERCENT_BOUNDARY_SNAPS",
    "S18_NO_IMPUTATION",
    "S19_GEOTHERMAL_SAMPLING_SERIES",
    "S20_CATALOG_UNIQUE_MAPPING",
    "S21_CATALOG_VALID_ROLES",
    "S22_DIM_METRIC_CATALOG_MATCH",
    "S23_FACT_ENTITY_FK",
    "S24_FACT_YEAR_FK",
    "S25_FACT_METRIC_FK",
    "S26_FACT_CANONICAL_SOURCE",
    "S27_FACT_DIM_SOURCE_MATCH",
    "S28_FACT_VALUE_DTYPE",
    "S29_FACT_NO_NULL_VALUE",
    "S30_METRIC_CUTOFF",
    "S31_VALUE_CLASS",
    "V6",
    "V7",
    "V8",
)
REQUIRED_AUDIT_CHECK_IDS = ("V1", "V2", "V3", "V4", "V5")
REQUIRED_CHECK_IDS = frozenset(
    [*REQUIRED_BLOCKING_CHECK_IDS, *REQUIRED_AUDIT_CHECK_IDS]
)
FINGERPRINT_TABLES = (
    ("dim_entity", "entity"),
    ("dim_metric", "metric_key"),
    ("dim_year", "year"),
    ("fact_energy", "entity,year,metric_key"),
    ("missingness_audit", "entity,year,metric_key"),
)


class Phase2ContractError(RuntimeError):
    """Raised when Phase 2 validation is absent, incomplete, stale, or failed."""


def phase2_input_fingerprint(conn: sqlite3.Connection) -> str:
    """Return a deterministic SHA-256 digest of the canonical Phase 2 input."""
    digest = hashlib.sha256()
    for table, order in FINGERPRINT_TABLES:
        frame = pd.read_sql_query(f"SELECT * FROM {table} ORDER BY {order}", conn)
        digest.update(table.encode())
        digest.update("\x1e".join(frame.columns).encode())
        for row in frame.itertuples(index=False, name=None):
            serial = "\x1f".join(
                "<NULL>"
                if value is None
                else format(value, ".17g")
                if isinstance(value, float)
                else str(value)
                for value in row
            )
            digest.update((serial + "\n").encode())
    return digest.hexdigest()


def _validation_table_columns(conn: sqlite3.Connection) -> set[str]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='validation_results' COLLATE NOCASE"
    ).fetchone()
    if exists is None:
        raise Phase2ContractError("Phase 2 validation_results table is missing")
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(validation_results)")}


def validate_phase2_gate(
    conn: sqlite3.Connection,
    *,
    require_fingerprint: bool = True,
) -> str:
    """Validate the complete Phase 2 gate and return the current fingerprint."""
    columns = _validation_table_columns(conn)
    required_columns = {"check_id", "status", "is_blocking"}
    if require_fingerprint:
        required_columns.add("phase2_input_fingerprint")
    missing_columns = required_columns - columns
    if missing_columns:
        raise Phase2ContractError(
            f"Phase 2 validation_results is missing columns: {sorted(missing_columns)}"
        )

    selected = "check_id,status,is_blocking"
    if "phase2_input_fingerprint" in columns:
        selected += ",phase2_input_fingerprint"
    rows = conn.execute(f"SELECT {selected} FROM validation_results").fetchall()
    if not rows:
        raise Phase2ContractError("Phase 2 validation_results is empty")
    if len(rows) != EXPECTED_VALIDATION_ROWS:
        raise Phase2ContractError(
            "Phase 2 validation_results row count changed: "
            f"expected {EXPECTED_VALIDATION_ROWS}, found {len(rows)}"
        )

    observed_ids = {str(row[0]) for row in rows}
    missing_ids = REQUIRED_CHECK_IDS - observed_ids
    unexpected_ids = observed_ids - REQUIRED_CHECK_IDS
    if missing_ids or unexpected_ids:
        raise Phase2ContractError(
            "Phase 2 validation check list mismatch: "
            f"missing={sorted(missing_ids)}, unexpected={sorted(unexpected_ids)}"
        )

    blocking_rows = [row for row in rows if row[2] == 1]
    blocking_ids = [str(row[0]) for row in blocking_rows]
    expected_blocking = set(REQUIRED_BLOCKING_CHECK_IDS)
    if len(blocking_rows) != len(REQUIRED_BLOCKING_CHECK_IDS):
        raise Phase2ContractError(
            "Phase 2 blocking validation row count changed: "
            f"expected {len(REQUIRED_BLOCKING_CHECK_IDS)}, found {len(blocking_rows)}"
        )
    if set(blocking_ids) != expected_blocking or len(set(blocking_ids)) != len(blocking_ids):
        raise Phase2ContractError(
            "Phase 2 blocking validation IDs are missing, unexpected, or duplicated"
        )
    failed = [str(row[0]) for row in blocking_rows if str(row[1]).upper() != "PASS"]
    if failed:
        raise Phase2ContractError(
            f"Phase 2 has blocking validation failures: {sorted(failed)}"
        )

    current_fingerprint = phase2_input_fingerprint(conn)
    if require_fingerprint:
        fingerprints = {str(row[3]) for row in rows}
        if fingerprints != {current_fingerprint}:
            raise Phase2ContractError(
                "Phase 2 validation fingerprint does not match the current input"
            )
    return current_fingerprint


def bind_phase2_validation_fingerprint(conn: sqlite3.Connection) -> str:
    """Bind a complete, passing Phase 2 validation set to its current input."""
    fingerprint = validate_phase2_gate(conn, require_fingerprint=False)
    columns = _validation_table_columns(conn)
    if "phase2_input_fingerprint" not in columns:
        raise Phase2ContractError(
            "Phase 2 validation_results cannot be bound without the fingerprint column"
        )
    conn.execute(
        "UPDATE validation_results SET phase2_input_fingerprint = ?",
        (fingerprint,),
    )
    validate_phase2_gate(conn, require_fingerprint=True)
    return fingerprint
