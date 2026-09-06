"""Run the full Phase 2->3 release twice and prove reproducibility."""
from __future__ import annotations

import hashlib
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd

from config import ARCHIVE, BASE, DB_PATH, STATS
from phase2_contract import EXPECTED_VALIDATION_ROWS, validate_phase2_gate


PHASE3_CSV = [
    "03_fact_metrics.csv", "03_metric_definitions.csv",
    "03_crosscheck_results.csv", "03_validation_results.csv",
]
PHASE3_XLSX = [
    "03_global_cross_section.xlsx", "03_asean_cross_section.xlsx",
    "03_vietnam_time_series.xlsx", "03_ranking_comparison.xlsx",
    "03_entry_lag.xlsx", "03_global_context.xlsx",
]
FACT_ORDER = (
    "subject_type,subject_key,period_type,period_key,series_key,metric_name,"
    "comparison_scope,filter_variant,method_version"
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hashes(paths: list[Path]) -> dict[str, str]:
    return {path.name: digest_bytes(path.read_bytes()) for path in paths}


def workbook_data_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with pd.ExcelFile(path) as workbook:
        for sheet_name in workbook.sheet_names:
            frame = pd.read_excel(workbook, sheet_name=sheet_name, dtype=object)
            digest.update(sheet_name.encode("utf-8"))
            digest.update(frame.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    return digest.hexdigest()


def database_fact_hash() -> str:
    connection = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        frame = pd.read_sql_query(f"SELECT * FROM fact_metrics ORDER BY {FACT_ORDER}", connection)
    finally:
        connection.close()
    return digest_bytes(frame.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode("utf-8"))


def run_command(arguments: list[str]) -> None:
    completed = subprocess.run(arguments, cwd=BASE, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(arguments)}")


def run_release() -> None:
    run_command([sys.executable, str(BASE / "python" / "02_clean_build.py")])
    run_command([
        sys.executable, str(BASE / "python" / "run_sql.py"),
        str(BASE / "sql" / "02_validate.sql"), "--fail-on-blocking",
        "--output-csv", str(STATS / "02_validation_results.csv"),
    ])
    run_command([sys.executable, str(BASE / "python" / "03_descriptive.py")])


def snapshot() -> dict[str, object]:
    phase2_validations = pd.read_csv(STATS / "02_validation_results.csv")
    cross = pd.read_csv(STATS / "03_crosscheck_results.csv")
    validations = pd.read_csv(STATS / "03_validation_results.csv")
    if len(phase2_validations) != EXPECTED_VALIDATION_ROWS:
        raise AssertionError("Phase 2 validation output is incomplete")
    if phase2_validations.phase2_input_fingerprint.nunique() != 1:
        raise AssertionError("Phase 2 validation output is not bound to one fingerprint")
    if not cross.status.eq("PASS").all():
        raise AssertionError("Cross-check output contains non-PASS rows")
    if not validations.status.eq("PASS").all():
        raise AssertionError("Phase 3 validation output contains non-PASS rows")
    if not validations.validation_id.is_unique:
        raise AssertionError("Phase 3 validation IDs are not unique")

    connection = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        current_fingerprint = validate_phase2_gate(connection)
    finally:
        connection.close()
    if set(phase2_validations.phase2_input_fingerprint) != {current_fingerprint}:
        raise AssertionError("Phase 2 validation CSV fingerprint is stale")

    growth = pd.read_excel(
        STATS / "03_global_context.xlsx", sheet_name="growth_contribution"
    )
    if len(growth) != 66 or growth.entity.eq("ASEAN_10").sum() != 6:
        raise AssertionError("Q6 workbook summary contract is incomplete")
    required_metadata = {
        "method_version", "phase2_input_fingerprint", "analysis_window",
        "workbook_scope", "source_provenance", "unit_conventions",
        "statistical_conventions", "denominator_conventions", "null_rule",
        "zero_rule", "threshold_rules", "fact_key_definition", "q5_pair_mapping",
    }
    for name in PHASE3_XLSX:
        metadata = pd.read_excel(STATS / name, sheet_name="metadata")
        if not metadata.metadata_key.is_unique or set(metadata.metadata_key) != required_metadata:
            raise AssertionError(f"Workbook metadata contract failed: {name}")

    entry_summary = pd.read_excel(STATS / "03_entry_lag.xlsx", sheet_name="entry_summary")
    entry_key = ["series_key", "status_type", "status_value"]
    if len(entry_summary) != 18:
        raise AssertionError(f"entry_summary must have 18 rows, found {len(entry_summary)}")
    if not set(entry_key) <= set(entry_summary.columns):
        raise AssertionError("entry_summary is missing explicit status columns")
    if entry_summary[entry_key].isna().any(axis=None):
        raise AssertionError("entry_summary contract key contains null values")
    if entry_summary.duplicated(entry_key).any():
        raise AssertionError("entry_summary contract key is not unique")
    rebuilt_names = entry_summary["status_type"] + "_count__" + entry_summary["status_value"]
    if not rebuilt_names.eq(entry_summary["metric_name"]).all():
        raise AssertionError("entry_summary status columns do not reconstruct metric_name")
    status_totals = entry_summary.groupby(["series_key", "status_type"]).metric_value.sum()
    if not status_totals.eq(10).all():
        raise AssertionError("entry_summary status counts do not reconcile to ASEAN-10")
    return {
        "phase2_validation": file_hashes([STATS / "02_validation_results.csv"]),
        "csv": file_hashes([STATS / name for name in PHASE3_CSV]),
        "workbooks": {name: workbook_data_hash(STATS / name) for name in PHASE3_XLSX},
        "database": database_fact_hash(),
        "fact_count": len(pd.read_csv(STATS / "03_fact_metrics.csv")),
        "cross_count": len(cross),
        "validation_count": len(validations),
    }


def main() -> int:
    archive_paths = sorted(ARCHIVE.glob("*.csv"))
    if len(archive_paths) != 17:
        raise AssertionError(f"Expected 17 archive CSV files, found {len(archive_paths)}")
    archive_before = file_hashes(archive_paths)
    print("RELEASE RUN 1")
    run_release()
    first = snapshot()
    archive_after_first = file_hashes(archive_paths)
    print("RELEASE RUN 2")
    run_release()
    second = snapshot()
    archive_after_second = file_hashes(archive_paths)
    if archive_before != archive_after_first or archive_before != archive_after_second:
        raise AssertionError("At least one archive CSV changed during the release runs")
    if first != second:
        differing = [key for key in first if first[key] != second[key]]
        raise AssertionError(f"Release outputs are not reproducible: {differing}")
    print(
        "PHASE 3 RELEASE VERIFICATION: PASS | "
        f"archive_files=17 | fact_metrics={second['fact_count']:,} | "
        f"crosschecks={second['cross_count']:,} | validations={second['validation_count']:,}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
