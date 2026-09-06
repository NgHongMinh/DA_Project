"""
Kiem tra moi truong cho do an — Phase 0.

Chay script nay de xac nhan Phase 0 da hoan thanh. Script tu tao file
database rong neu chua co, va bao cao PASS/FAIL cho tung tieu chi.

Cach dung:
    python python\\00_check_env.py

Exit code 0 = tat ca dat, 1 = co tieu chi that bai.
"""

from __future__ import annotations

import importlib
import platform
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import ARCHIVE, BASE, DB_PATH, EXPECTED_CSV_COUNT  # noqa: E402

# Phien ban SQLite toi thieu de co window functions.
MIN_SQLITE = (3, 25, 0)

REQUIRED_LIBS = ["pandas", "numpy", "matplotlib", "seaborn", "scipy", "openpyxl"]

REQUIRED_DIRS = [
    "python",
    "sql",
    "output",
    "output/clean",
    "output/stats",
    "output/charts",
    "powerbi",
    "docs",
]

results: list[tuple[bool, str]] = []


def check(passed: bool, label: str, detail: str = "") -> bool:
    """Ghi lai ket qua mot tieu chi va in ra ngay."""
    results.append((passed, label))
    mark = "[ OK ]" if passed else "[FAIL]"
    line = f"{mark}  {label}"
    if detail:
        line += f"  ->  {detail}"
    print(line)
    return passed


def section(title: str) -> None:
    print(f"\n{title}")
    print("-" * 78)


# ---------------------------------------------------------------------------
# 1. Python
# ---------------------------------------------------------------------------
section("1. Python")

version = sys.version_info
check(
    version >= (3, 12),
    "Python >= 3.12",
    f"{platform.python_version()}",
)

# Diem quan trong: stub Microsoft Store la file 0 byte trong WindowsApps.
# Neu sys.executable tro vao do thi khong the cai thu vien duoc.
executable = Path(sys.executable)
check(
    "WindowsApps" not in str(executable),
    "Khong dung stub Microsoft Store",
    str(executable),
)

# ---------------------------------------------------------------------------
# 2. Thu vien
# ---------------------------------------------------------------------------
section("2. Thu vien")

for name in REQUIRED_LIBS:
    try:
        module = importlib.import_module(name)
        check(True, f"import {name}", getattr(module, "__version__", "khong ro version"))
    except ImportError as exc:
        check(False, f"import {name}", str(exc))

# ---------------------------------------------------------------------------
# 3. SQLite — kiem tra bang cach CHAY THAT, khong gia dinh
# ---------------------------------------------------------------------------
section("3. SQLite")

sqlite_tuple = tuple(int(p) for p in sqlite3.sqlite_version.split("."))
check(
    sqlite_tuple >= MIN_SQLITE,
    f"SQLite >= {'.'.join(map(str, MIN_SQLITE))} (dieu kien co window functions)",
    sqlite3.sqlite_version,
)

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

try:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Window function — tinh nang bat buoc cho Phase 8.
        cursor.execute(
            "SELECT ROW_NUMBER() OVER (ORDER BY value) AS rn, value "
            "FROM (SELECT 10 AS value UNION ALL SELECT 20 UNION ALL SELECT 30)"
        )
        rows = cursor.fetchall()
        check(
            rows == [(1, 10), (2, 20), (3, 30)],
            "ROW_NUMBER() OVER (...) chay dung",
            f"{rows}",
        )

        # CTE — dung nhieu o Phase 2 (bo kiem dinh) va Phase 8.
        cursor.execute("WITH t(x) AS (SELECT 1 UNION ALL SELECT 2) SELECT SUM(x) FROM t")
        check(cursor.fetchone()[0] == 3, "CTE (WITH ...) chay dung")

        # LAG — dung cho tang truong YoY o Phase 3.
        cursor.execute(
            "SELECT value - LAG(value) OVER (ORDER BY value) "
            "FROM (SELECT 5 AS value UNION ALL SELECT 8) ORDER BY value DESC LIMIT 1"
        )
        check(cursor.fetchone()[0] == 3, "LAG() OVER (...) chay dung")

        # CREATE VIEW IF NOT EXISTS — dung cho vw_wide o Phase 2.
        cursor.execute("CREATE VIEW IF NOT EXISTS _tmp_view AS SELECT 1 AS one")
        cursor.execute("SELECT one FROM _tmp_view")
        view_ok = cursor.fetchone()[0] == 1
        cursor.execute("DROP VIEW IF EXISTS _tmp_view")
        check(view_ok, "CREATE VIEW IF NOT EXISTS chay dung")

        # Ghi that len o dia — xac nhan quyen ghi tren d:\ khong van de.
        cursor.execute("CREATE TABLE IF NOT EXISTS _tmp_write_test (id INTEGER)")
        cursor.execute("INSERT INTO _tmp_write_test VALUES (1)")
        cursor.execute("SELECT COUNT(*) FROM _tmp_write_test")
        write_ok = cursor.fetchone()[0] >= 1
        cursor.execute("DROP TABLE IF EXISTS _tmp_write_test")
        conn.commit()
        check(write_ok, "Ghi/xoa bang tren file .db thanh cong")

    check(DB_PATH.is_file(), "File database ton tai", str(DB_PATH))

except sqlite3.OperationalError as exc:
    # Loi hay gap nhat: Navicat dang giu file -> "database is locked".
    hint = ""
    if "locked" in str(exc).lower():
        hint = " (dong connection trong Navicat roi chay lai)"
    check(False, "Ket noi / ghi SQLite", f"{exc}{hint}")

# ---------------------------------------------------------------------------
# 4. Cay thu muc
# ---------------------------------------------------------------------------
section("4. Cay thu muc")

for relative in REQUIRED_DIRS:
    path = BASE / relative
    check(path.is_dir(), f"Thu muc {relative}/")

# ---------------------------------------------------------------------------
# 5. Du lieu nguon
# ---------------------------------------------------------------------------
section("5. Du lieu nguon")

check(ARCHIVE.is_dir(), "Thu muc archive/ ton tai", str(ARCHIVE))

csv_files = sorted(ARCHIVE.glob("*.csv"))
check(
    len(csv_files) == EXPECTED_CSV_COUNT,
    f"Dem duoc {EXPECTED_CSV_COUNT} file CSV",
    f"thuc te: {len(csv_files)}",
)

if csv_files:
    try:
        import pandas as pd

        sample = csv_files[0]
        frame = pd.read_csv(sample, nrows=5)
        check(
            len(frame.columns) == 4,
            "pandas doc thu 1 file CSV, ra dung 4 cot",
            f"{sample.name} -> {list(frame.columns)}",
        )
    except Exception as exc:  # noqa: BLE001 — bao cao moi loi doc file
        check(False, "pandas doc thu 1 file CSV", str(exc))

# ---------------------------------------------------------------------------
# Tong ket
# ---------------------------------------------------------------------------
passed = sum(1 for ok, _ in results if ok)
total = len(results)
failed = [label for ok, label in results if not ok]

print("\n" + "=" * 78)
print(f"TONG KET PHASE 0: {passed}/{total} tieu chi dat")
print("=" * 78)

if failed:
    print("\nCac tieu chi CHUA dat:")
    for label in failed:
        print(f"  - {label}")
    print("\n=> Phase 0 CHUA hoan thanh.")
    raise SystemExit(1)

print("\n=> Phase 0 HOAN THANH. Da san sang sang Phase 1.")
print("\nViec con lai phai tu lam bang tay:")
print("  - Navicat Premium 17 -> Connection -> SQLite -> tro toi:")
print(f"      {DB_PATH}")
raise SystemExit(0)
