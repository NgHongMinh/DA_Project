"""Phase 5 -- reconcile Power BI output against the recomputed reference set.

Reads `output/stats/05_test_results.tsv` (exported from the model through MCP
`dax_query_operations`), joins it to `output/stats/05_expected_values.csv` on
`test_id`, and writes `output/stats/05_validation_results.csv`.

Two rules matter more than the rest:

* Comparison happens on the STORAGE scale. Only `share_electricity_pct` is held
  on 0-100; every other ratio is held on 0-1. Comparing a stored ratio against a
  display figure that has already been multiplied by 100 is an off-by-100 unit
  error, not a rounding difference, and the `1e-9` tolerance would hide nothing.
* Counts, ranks, keys and statuses must match exactly. Only raw numbers get a
  tolerance.

A missing result is a failure. Silence is not a pass.

Run:  python python\\05_validate.py
"""
from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_contract as K  # noqa: E402
from config import ARCHIVE, CLEAN, STATS  # noqa: E402

EXPECTED_PATH = STATS / "05_expected_values.csv"
RESULTS_PATH = STATS / "05_test_results.tsv"
VALIDATION_PATH = STATS / "05_validation_results.csv"

BLANK_TOKENS = {"", "blank", "(blank)", "null", "none", "nan"}

RESULT_COLUMNS = (
    "validation_id", "gate_id", "page_id", "severity", "status",
    "comparison", "unit_stored", "expected", "actual", "delta",
    "tolerance", "failure_reason", "description_vi",
    "method_version", "phase2_input_fingerprint",
)


def normalise_header(name: str) -> str:
    """DAX query results often come back with bracketed column names."""
    return name.strip().strip("[]").split(".")[-1].strip().lower()


def read_results() -> dict[str, dict[str, str]]:
    if not RESULTS_PATH.exists():
        return {}
    with RESULTS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = [normalise_header(cell) for cell in next(reader)]
        except StopIteration:
            return {}
        rows: dict[str, dict[str, str]] = {}
        for raw in reader:
            if not any(cell.strip() for cell in raw):
                continue
            record = dict(zip(header, (cell.strip() for cell in raw)))
            test_id = record.get("test_id", "")
            if test_id:
                rows[test_id] = record
    return rows


def as_float(text: str) -> float | None:
    cleaned = text.strip().replace(" ", "")
    if cleaned.lower() in BLANK_TOKENS:
        return None
    # Accept a Vietnamese-formatted number in case a result was pasted from the
    # report surface rather than taken from the query.
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def compare(expected: dict[str, str], actual: dict[str, str] | None) -> dict[str, Any]:
    comparison = expected["comparison"]
    tolerance = float(expected["tolerance"] or 0.0)
    expected_value = expected["expected_value"]
    expected_text = expected["expected_text"]

    if actual is None:
        return {
            "status": "FAIL",
            "actual": "",
            "delta": "",
            "failure_reason": "MISSING_RESULT — không có dòng nào cho mã kiểm thử này",
        }

    actual_value_text = actual.get("actual_value", "")
    actual_text = actual.get("actual_text", "")

    if comparison == "blank":
        blank_value = as_float(actual_value_text) is None
        reported = actual_text.strip()
        if blank_value and (not reported or reported.upper() == expected_text.upper()):
            return {"status": "PASS", "actual": reported or "BLANK", "delta": "",
                    "failure_reason": ""}
        return {
            "status": "FAIL",
            "actual": reported or actual_value_text,
            "delta": "",
            "failure_reason": (
                "EXPECTED_BLANK_WITH_REASON — ô này phải trống kèm lý do "
                f"{expected_text}, không được trả số"
            ),
        }

    if comparison == "text":
        if actual_text.strip() == expected_text.strip():
            return {"status": "PASS", "actual": actual_text, "delta": "", "failure_reason": ""}
        return {
            "status": "FAIL", "actual": actual_text, "delta": "",
            "failure_reason": f"TEXT_MISMATCH — chờ {expected_text!r}",
        }

    target = as_float(expected_value)
    observed = as_float(actual_value_text)
    if target is None:
        return {"status": "FAIL", "actual": actual_value_text, "delta": "",
                "failure_reason": "EXPECTED_VALUE_UNREADABLE"}
    if observed is None:
        return {
            "status": "FAIL", "actual": actual_value_text or "BLANK", "delta": "",
            "failure_reason": "BLANK_RESULT — chờ một con số nhưng nhận về trống",
        }

    delta = abs(observed - target)
    if comparison == "exact":
        if observed == target:
            return {"status": "PASS", "actual": repr(observed), "delta": "0",
                    "failure_reason": ""}
        return {
            "status": "FAIL", "actual": repr(observed), "delta": repr(delta),
            "failure_reason": "EXACT_MISMATCH — số đếm, hạng và trạng thái phải khớp tuyệt đối",
        }

    if delta <= tolerance:
        return {"status": "PASS", "actual": repr(observed), "delta": repr(delta),
                "failure_reason": ""}

    # An off-by-100 gap is almost always a stored-versus-displayed scale mix-up,
    # so name it rather than reporting a large meaningless delta.
    hint = ""
    if target != 0 and abs(observed / target - 100) < 1e-6:
        hint = " — lệch đúng 100 lần: đang so thang hiển thị với thang lưu trữ"
    elif observed != 0 and abs(target / observed - 100) < 1e-6:
        hint = " — lệch đúng 100 lần: đang so thang lưu trữ với thang hiển thị"
    return {
        "status": "FAIL", "actual": repr(observed), "delta": repr(delta),
        "failure_reason": f"TOLERANCE_EXCEEDED (>{tolerance:g}){hint}",
    }


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_lock_rows() -> list[dict[str, Any]]:
    """Gate B10 also requires that nothing upstream moved while Phase 5 was built."""
    rows: list[dict[str, Any]] = []

    def record(validation_id: str, description: str, expected: Any, actual: Any) -> None:
        ok = str(expected) == str(actual)
        rows.append(
            {
                "validation_id": validation_id,
                "gate_id": "B10",
                "page_id": "INPUT_LOCK",
                "severity": "BLOCKING",
                "status": "PASS" if ok else "FAIL",
                "comparison": "exact",
                "unit_stored": "count",
                "expected": str(expected),
                "actual": str(actual),
                "delta": "",
                "tolerance": 0.0,
                "failure_reason": "" if ok else "INPUT_DRIFT — đầu vào Phase 1–4 đã đổi",
                "description_vi": description,
                "method_version": K.METHOD_VERSION,
                "phase2_input_fingerprint": K.EXPECTED_PHASE2_INPUT_FINGERPRINT,
            }
        )

    record("P5_LOCK_ARCHIVE_CSV_COUNT", "17 CSV nguồn còn nguyên",
           K.EXPECTED_ARCHIVE_CSV_COUNT, len(list(ARCHIVE.glob("*.csv"))))
    record("P5_LOCK_FACT_ENERGY_SHA256", "fact_energy.csv giữ nguyên mã băm",
           K.EXPECTED_PHASE2_FACT_ENERGY_SHA256, digest(CLEAN / "fact_energy.csv"))
    for validation_id, description, path, expected_rows in (
        ("P5_LOCK_PHASE2_VALIDATION", "Kiểm định Phase 2 đủ 864 dòng",
         STATS / "02_validation_results.csv", K.EXPECTED_PHASE2_VALIDATION_ROWS),
        ("P5_LOCK_PHASE3_FACT_METRICS", "fact_metrics Phase 3 đủ 18.926 dòng",
         STATS / "03_fact_metrics.csv", K.EXPECTED_PHASE3_FACT_METRIC_ROWS),
        ("P5_LOCK_PHASE3_VALIDATION", "Kiểm định Phase 3 đủ 92 dòng",
         STATS / "03_validation_results.csv", K.EXPECTED_PHASE3_VALIDATION_ROWS),
        ("P5_LOCK_PHASE4_VALIDATION", "Kiểm định Phase 4 đủ 38 dòng",
         STATS / "04_validation_results.csv", K.EXPECTED_PHASE4_VALIDATION_ROWS),
    ):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            actual_rows = sum(1 for _ in csv.DictReader(handle))
        record(validation_id, description, expected_rows, actual_rows)
    return rows


def main() -> int:
    with EXPECTED_PATH.open(encoding="utf-8") as handle:
        expected_rows = list(csv.DictReader(handle))
    results = read_results()

    rows: list[dict[str, Any]] = []
    for expected in expected_rows:
        outcome = compare(expected, results.get(expected["test_id"]))
        rows.append(
            {
                "validation_id": expected["test_id"],
                "gate_id": expected["gate_id"],
                "page_id": expected["page_id"],
                "severity": "BLOCKING",
                "status": outcome["status"],
                "comparison": expected["comparison"],
                "unit_stored": expected["unit_stored"],
                "expected": expected["expected_value"] or expected["expected_text"],
                "actual": outcome["actual"],
                "delta": outcome["delta"],
                "tolerance": expected["tolerance"],
                "failure_reason": outcome["failure_reason"],
                "description_vi": expected["description_vi"],
                "method_version": expected["method_version"],
                "phase2_input_fingerprint": expected["phase2_input_fingerprint"],
            }
        )

    unexpected = sorted(set(results) - {row["validation_id"] for row in rows})
    for test_id in unexpected:
        rows.append(
            {
                "validation_id": test_id, "gate_id": "B10", "page_id": "UNKNOWN",
                "severity": "BLOCKING", "status": "FAIL", "comparison": "exact",
                "unit_stored": "", "expected": "", "actual": "", "delta": "",
                "tolerance": 0.0,
                "failure_reason": "UNKNOWN_TEST_ID — kết quả không thuộc bộ đích đã khóa",
                "description_vi": "Kết quả lạ trong 05_test_results.tsv",
                "method_version": K.METHOD_VERSION,
                "phase2_input_fingerprint": K.EXPECTED_PHASE2_INPUT_FINGERPRINT,
            }
        )

    rows.extend(input_lock_rows())

    VALIDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with VALIDATION_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    passed = sum(1 for row in rows if row["status"] == "PASS")
    failed = [row for row in rows if row["status"] != "PASS"]
    missing = sum(1 for row in failed if row["failure_reason"].startswith("MISSING_RESULT"))

    print(f"  -> {VALIDATION_PATH}")
    if not results:
        print(
            "PHASE 5 VALIDATION: PENDING | chưa có 05_test_results.tsv. "
            "Chạy powerbi\\05_acceptance.dax qua MCP rồi lưu kết quả vào "
            f"{RESULTS_PATH.name} với ba cột test_id, actual_value, actual_text.",
            file=sys.stderr,
        )
        return 2
    if failed:
        print(f"PHASE 5 VALIDATION: FAIL | {passed}/{len(rows)} PASS | "
              f"lỗi={len(failed)} | thiếu kết quả={missing}", file=sys.stderr)
        for row in failed[:15]:
            print(f"  {row['validation_id']}: {row['failure_reason']} "
                  f"(chờ {row['expected']}, nhận {row['actual']})", file=sys.stderr)
        if len(failed) > 15:
            print(f"  … và {len(failed) - 15} lỗi nữa, xem {VALIDATION_PATH.name}", file=sys.stderr)
        return 1
    print(f"PHASE 5 VALIDATION: PASS | {passed}/{len(rows)} mã kiểm thử duy nhất đạt | "
          f"0 dòng chặn khác PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
