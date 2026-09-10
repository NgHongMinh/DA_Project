"""Run the Phase 4 release twice and prove deterministic, read-only inputs."""
from __future__ import annotations

import hashlib
import math
import struct
import subprocess
import sys
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from openpyxl import load_workbook
from PIL import Image

from config import ARCHIVE, BASE, CHARTS, DB_PATH, DOCS, STATS
from phase3_contract import PHASE3_WORKBOOKS
from phase4_contract import (
    CHARTS as CHART_SPECS,
    CHART_DATA_SHEETS,
    CHART_FILES,
    DIMENSIONS_PX,
    EXPECTED_PHASE2_INPUT_FINGERPRINT,
    EXPECTED_VALIDATION_IDS,
    EXPECTED_VALIDATION_ROWS,
    MANIFEST_COLUMNS,
    VALIDATION_COLUMNS,
    VALIDATION_GATE_BY_ID,
    VALIDATION_SEVERITY,
    manifest_rows,
)


WORKBOOK_PATH = STATS / "04_chart_data.xlsx"
VALIDATION_PATH = STATS / "04_validation_results.csv"
FACT_ENERGY_PATH = BASE / "output" / "clean" / "fact_energy.csv"
EXPECTED_WORKBOOK_SHEETS = (
    "manifest",
    "global_context",
    "asean_technology",
    "country_mix_2021",
    "rank_shift_2021",
    "small_multiples",
    "vietnam_technology",
    "vietnam_q5",
    "vietnam_position",
    "global_distribution",
    "entry_lag",
    "concentration",
    "growth_contribution",
    "capacity_factor",
    "metadata",
    "method_notes",
)
PHASE3_CSV = (
    "03_fact_metrics.csv",
    "03_metric_definitions.csv",
    "03_crosscheck_results.csv",
    "03_validation_results.csv",
)
PHASE3_PUBLIC_FILES = (
    BASE / "python" / "03_descriptive.py",
    BASE / "sql" / "03_analysis.sql",
    DB_PATH,
    *(STATS / name for name in PHASE3_WORKBOOKS),
    *(STATS / name for name in PHASE3_CSV),
    DOCS / "NhatKyPhanTich.md",
    DOCS / "BaoCao.md",
    BASE / "PLAN.md",
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_name(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def file_hashes(paths: Iterable[Path]) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in paths:
        if not path.is_file():
            raise AssertionError(f"Required protected file is missing: {relative_name(path)}")
        result[relative_name(path)] = digest_bytes(path.read_bytes())
    return result


def run_command(arguments: list[str]) -> None:
    completed = subprocess.run(
        arguments,
        cwd=BASE,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.returncode:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(arguments)}"
        )


def run_release() -> None:
    run_command([sys.executable, str(BASE / "python" / "04_charts.py")])


def run_preflight() -> None:
    """Run every Phase 4 prerequisite in the same auditable verifier process."""
    commands = (
        [sys.executable, str(BASE / "python" / "00_check_env.py")],
        [sys.executable, str(BASE / "python" / "03_test_publish.py")],
        [sys.executable, str(BASE / "python" / "03_verify_release.py")],
    )
    for index, arguments in enumerate(commands, start=1):
        print(f"PHASE 4 PREFLIGHT {index}/{len(commands)}: {Path(arguments[1]).name}")
        run_command(arguments)
    print(f"PHASE 4 PREFLIGHT: PASS | checks={len(commands)}/{len(commands)}")


def expected_chart_files() -> tuple[str, ...]:
    contract_files = tuple(str(name) for name in CHART_FILES)
    spec_files = tuple(str(spec["file_name"]) for spec in CHART_SPECS)
    if len(contract_files) != 13 or len(set(contract_files)) != 13:
        raise AssertionError(
            f"Phase 4 contract must expose 13 unique chart files, found {len(set(contract_files))}"
        )
    if spec_files != contract_files:
        raise AssertionError("CHART_FILES order differs from the CHARTS specification order")
    return contract_files


def png_pixel_snapshot(path: Path) -> dict[str, Any]:
    """Hash decoded RGBA pixels so volatile PNG metadata cannot affect comparison."""
    with Image.open(path) as source:
        if source.format != "PNG":
            raise AssertionError(f"Not a PNG image: {relative_name(path)}")
        source.load()
        expected_width, expected_height = DIMENSIONS_PX
        if source.size != (expected_width, expected_height):
            raise AssertionError(
                f"Wrong dimensions for {path.name}: expected="
                f"{expected_width}x{expected_height}, actual={source.width}x{source.height}"
            )
        rgba = source.convert("RGBA")
        extrema = rgba.convert("RGB").getextrema()
        if all(low == high for low, high in extrema):
            raise AssertionError(f"Decoded image is blank: {path.name}")
        pixels = rgba.tobytes()
        return {
            "dimensions": rgba.size,
            "mode": rgba.mode,
            "pixel_sha256": digest_bytes(pixels),
            "decoded_bytes": len(pixels),
        }


def encode_cell_value(value: Any) -> bytes:
    """Serialize an openpyxl value without locale- or display-dependent formatting."""
    if value is None:
        return b"N"
    if isinstance(value, bool):
        return b"B1" if value else b"B0"
    if isinstance(value, int):
        return b"I" + str(value).encode("ascii")
    if isinstance(value, float):
        if math.isnan(value):
            return b"Fnan"
        if math.isinf(value):
            return b"F+inf" if value > 0 else b"F-inf"
        return b"F" + value.hex().encode("ascii")
    if isinstance(value, Decimal):
        return b"D" + str(value).encode("ascii")
    if isinstance(value, (datetime, date, time)):
        return b"T" + value.isoformat().encode("ascii")
    if isinstance(value, bytes):
        return b"Y" + value
    return b"S" + str(value).encode("utf-8")


def add_framed(digest: Any, payload: bytes) -> None:
    digest.update(struct.pack(">Q", len(payload)))
    digest.update(payload)


def workbook_content_snapshot(path: Path) -> dict[str, Any]:
    """Snapshot ordered sheets, column schemas, formats, types, and cell values."""
    if not path.is_file():
        raise AssertionError(f"Phase 4 workbook is missing: {relative_name(path)}")
    workbook = load_workbook(path, read_only=True, data_only=False)
    try:
        if tuple(CHART_DATA_SHEETS) != EXPECTED_WORKBOOK_SHEETS:
            raise AssertionError("Contract sheet allow-list differs from the locked Phase 4 plan")
        sheet_order = tuple(workbook.sheetnames)
        if sheet_order != EXPECTED_WORKBOOK_SHEETS:
            raise AssertionError(
                "Phase 4 workbook sheet contract changed: "
                f"expected={EXPECTED_WORKBOOK_SHEETS!r}, actual={sheet_order!r}"
            )
        digest = hashlib.sha256()
        schemas: dict[str, tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]] = {}
        row_counts: dict[str, int] = {}
        for sheet_name in sheet_order:
            worksheet = workbook[sheet_name]
            rows = worksheet.iter_rows()
            try:
                header_cells = next(rows)
            except StopIteration as exc:
                raise AssertionError(f"Workbook sheet is empty: {sheet_name}") from exc
            headers = tuple(cell.value for cell in header_cells)
            if not headers or any(not isinstance(value, str) or not value for value in headers):
                raise AssertionError(f"Workbook sheet has an invalid header row: {sheet_name}")
            if len(set(headers)) != len(headers):
                raise AssertionError(f"Workbook sheet has duplicate headers: {sheet_name}")

            type_sets = [set() for _ in headers]
            format_sets = [set() for _ in headers]
            add_framed(digest, sheet_name.encode("utf-8"))
            for column_index, cell in enumerate(header_cells):
                add_framed(digest, str(column_index).encode("ascii"))
                add_framed(digest, encode_cell_value(cell.value))
                add_framed(digest, str(cell.data_type).encode("ascii"))
                add_framed(digest, str(cell.number_format).encode("utf-8"))

            data_rows = 0
            for row_index, row in enumerate(rows, start=2):
                if len(row) != len(headers):
                    raise AssertionError(
                        f"Workbook row width changed at {sheet_name}!{row_index}"
                    )
                data_rows += 1
                for column_index, cell in enumerate(row):
                    cell_type = str(cell.data_type)
                    number_format = str(cell.number_format)
                    type_sets[column_index].add(cell_type)
                    format_sets[column_index].add(number_format)
                    add_framed(digest, f"{row_index}:{column_index}".encode("ascii"))
                    add_framed(digest, encode_cell_value(cell.value))
                    add_framed(digest, cell_type.encode("ascii"))
                    add_framed(digest, number_format.encode("utf-8"))
            row_counts[sheet_name] = data_rows
            schemas[sheet_name] = tuple(
                (
                    str(header),
                    tuple(sorted(type_sets[index])),
                    tuple(sorted(format_sets[index])),
                )
                for index, header in enumerate(headers)
            )
        return {
            "sheet_order": sheet_order,
            "schemas": schemas,
            "row_counts": row_counts,
            "cell_value_schema_sha256": digest.hexdigest(),
        }
    finally:
        workbook.close()


def validation_bytes() -> bytes:
    if not VALIDATION_PATH.is_file():
        raise AssertionError(
            f"Phase 4 validation CSV is missing: {relative_name(VALIDATION_PATH)}"
        )
    raw = VALIDATION_PATH.read_bytes()
    frame = pd.read_csv(VALIDATION_PATH)
    if list(frame.columns) != list(VALIDATION_COLUMNS):
        raise AssertionError(
            "Phase 4 validation columns changed: "
            f"expected={list(VALIDATION_COLUMNS)!r}, actual={list(frame.columns)!r}"
        )
    if len(frame) != EXPECTED_VALIDATION_ROWS:
        raise AssertionError(
            f"Phase 4 validation row count changed: expected={EXPECTED_VALIDATION_ROWS}, "
            f"actual={len(frame)}"
        )
    if not frame.validation_id.is_unique:
        raise AssertionError("Phase 4 validation IDs are not unique")
    actual_ids = set(frame.validation_id.astype(str))
    if actual_ids != set(EXPECTED_VALIDATION_IDS):
        raise AssertionError(
            "Phase 4 validation ID set changed: "
            f"missing={sorted(set(EXPECTED_VALIDATION_IDS) - actual_ids)}, "
            f"unexpected={sorted(actual_ids - set(EXPECTED_VALIDATION_IDS))}"
        )
    if not frame.status.astype(str).eq("PASS").all():
        failed = frame.loc[frame.status.astype(str).ne("PASS"), "validation_id"].tolist()
        raise AssertionError(f"Phase 4 validation contains non-PASS rows: {failed}")
    if not frame.severity.astype(str).eq(VALIDATION_SEVERITY).all():
        raise AssertionError("Phase 4 validation rows must all be blocking release checks")
    actual_gate_map = dict(
        zip(frame.validation_id.astype(str), frame.gate_id.astype(str), strict=True)
    )
    if actual_gate_map != VALIDATION_GATE_BY_ID:
        raise AssertionError("Phase 4 validation IDs do not map to the locked gates")
    if not frame.method_version.astype(str).eq("phase4_v1").all():
        raise AssertionError("Phase 4 validation method_version must be phase4_v1")
    if not frame.phase2_input_fingerprint.astype(str).eq(
        EXPECTED_PHASE2_INPUT_FINGERPRINT
    ).all():
        raise AssertionError("Phase 4 validation rows use a stale Phase 2 fingerprint")
    return raw


def validate_manifest() -> None:
    manifest = pd.read_excel(WORKBOOK_PATH, sheet_name="manifest", dtype=object)
    if tuple(manifest.columns) != tuple(MANIFEST_COLUMNS):
        raise AssertionError(
            "Manifest column order/schema differs from the Phase 4 contract: "
            f"expected={tuple(MANIFEST_COLUMNS)!r}, actual={tuple(manifest.columns)!r}"
        )
    if len(manifest) != 13 or not manifest.chart_id.is_unique or not manifest.file_name.is_unique:
        raise AssertionError("Manifest must contain 13 rows with unique chart IDs and filenames")
    expected_ids = [str(spec["chart_id"]) for spec in CHART_SPECS]
    if manifest.chart_id.astype(str).tolist() != expected_ids:
        raise AssertionError("Manifest chart order/IDs differ from the Phase 4 contract")
    if manifest.file_name.astype(str).tolist() != list(expected_chart_files()):
        raise AssertionError("Manifest filenames differ from the Phase 4 contract")
    if not manifest.method_version.astype(str).eq("phase4_v1").all():
        raise AssertionError("Manifest method_version must be phase4_v1")
    fingerprints = manifest.phase2_input_fingerprint.dropna().astype(str).unique()
    if tuple(fingerprints) != (EXPECTED_PHASE2_INPUT_FINGERPRINT,):
        raise AssertionError("Manifest is not bound to the locked Phase 2 fingerprint")
    expected = pd.DataFrame(manifest_rows(), columns=MANIFEST_COLUMNS).astype(str)
    actual = manifest.astype(str)
    if not actual.equals(expected):
        raise AssertionError("Manifest values differ from the locked chart specifications")


def phase4_snapshot() -> dict[str, Any]:
    expected_files = expected_chart_files()
    actual_paths = sorted(CHARTS.glob("*.png"), key=lambda path: path.name)
    actual_names = tuple(path.name for path in actual_paths)
    if set(actual_names) != set(expected_files) or len(actual_names) != 13:
        raise AssertionError(
            "Phase 4 chart allow-list failed: "
            f"missing={sorted(set(expected_files) - set(actual_names))}, "
            f"unexpected={sorted(set(actual_names) - set(expected_files))}"
        )
    workbook = workbook_content_snapshot(WORKBOOK_PATH)
    validate_manifest()
    return {
        "png_pixels": {
            name: png_pixel_snapshot(CHARTS / name) for name in expected_files
        },
        "workbook": workbook,
        # Keep the exact bytes, rather than only their digest, in the in-memory snapshot.
        "validation_csv_bytes": validation_bytes(),
    }


def assert_protected_files_unchanged(
    label: str,
    baseline: dict[str, str],
    current: dict[str, str],
) -> None:
    if baseline != current:
        changed = sorted(
            name
            for name in set(baseline) | set(current)
            if baseline.get(name) != current.get(name)
        )
        raise AssertionError(f"{label} changed during Phase 4 release: {changed}")


def main() -> int:
    run_preflight()
    archive_paths = sorted(ARCHIVE.glob("*.csv"), key=lambda path: path.name)
    if len(archive_paths) != 17:
        raise AssertionError(f"Expected 17 archive CSV files, found {len(archive_paths)}")
    archive_before = file_hashes(archive_paths)
    fact_energy_before = file_hashes([FACT_ENERGY_PATH])
    phase3_before = file_hashes(PHASE3_PUBLIC_FILES)

    print("PHASE 4 RELEASE RUN 1")
    run_release()
    first = phase4_snapshot()
    assert_protected_files_unchanged(
        "Archive CSV files", archive_before, file_hashes(archive_paths)
    )
    assert_protected_files_unchanged(
        "Phase 2 fact_energy.csv", fact_energy_before, file_hashes([FACT_ENERGY_PATH])
    )
    assert_protected_files_unchanged(
        "Phase 3 public outputs", phase3_before, file_hashes(PHASE3_PUBLIC_FILES)
    )

    print("PHASE 4 RELEASE RUN 2")
    run_release()
    second = phase4_snapshot()
    assert_protected_files_unchanged(
        "Archive CSV files", archive_before, file_hashes(archive_paths)
    )
    assert_protected_files_unchanged(
        "Phase 2 fact_energy.csv", fact_energy_before, file_hashes([FACT_ENERGY_PATH])
    )
    assert_protected_files_unchanged(
        "Phase 3 public outputs", phase3_before, file_hashes(PHASE3_PUBLIC_FILES)
    )

    if first != second:
        differing = [key for key in first if first[key] != second[key]]
        raise AssertionError(f"Phase 4 release outputs are not reproducible: {differing}")
    print(
        "PHASE 4 RELEASE VERIFICATION: PASS | "
        "preflight=3/3 PASS | archive_files=17 | fact_energy=1 | "
        f"phase3_outputs={len(PHASE3_PUBLIC_FILES)} | "
        f"charts={len(second['png_pixels'])} | "
        f"workbook_sheets={len(second['workbook']['sheet_order'])} | "
        f"validations={EXPECTED_VALIDATION_ROWS}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
