"""
Chay mot file .sql tren database SQLite cua do an.

Day la phuong an du phong khi `sqlite3` CLI khong goi duoc tu terminal
(vi du thu muc WinGet\\Links chua vao PATH). Ket qua cua cac cau SELECT
duoc in ra dang bang.

Cach dung:
    python python\\run_sql.py sql\\02_validate.sql
    python python\\run_sql.py sql\\02_validate.sql --fail-on-blocking \\
        --output-csv output\\stats\\02_validation_results.csv
    python python\\run_sql.py sql\\03_analysis.sql --db duong\\dan\\khac.db
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import DB_PATH  # noqa: E402
from phase2_contract import (  # noqa: E402
    Phase2ContractError,
    bind_phase2_validation_fingerprint,
)


def split_statements(sql_text: str):
    """Tach script SQL thanh tung cau lenh hoan chinh.

    Dung sqlite3.complete_statement() thay vi split(';') — cach nay
    khong bi vo khi dau ';' nam trong string literal hoac trong trigger.
    """
    buffer = ""
    for line in sql_text.splitlines(keepends=True):
        stripped = line.strip()
        # Bo qua dong trong va dong chi co comment, tranh tao cau lenh rong.
        if not buffer and (not stripped or stripped.startswith("--")):
            continue
        buffer += line
        if sqlite3.complete_statement(buffer):
            statement = buffer.strip()
            if statement:
                yield statement
            buffer = ""
    if buffer.strip():
        yield buffer.strip()


def print_table(columns: list[str], rows: list[tuple], max_rows: int = 50) -> None:
    """In ket qua truy van dang bang, cac cot thang hang."""
    if not rows:
        print("   (khong co dong nao)")
        return

    shown = rows[:max_rows]
    cells = [[("NULL" if v is None else str(v)) for v in row] for row in shown]
    widths = [
        max(len(col), *(len(r[i]) for r in cells)) for i, col in enumerate(columns)
    ]

    print("   " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(columns)))
    print("   " + "-+-".join("-" * w for w in widths))
    for row in cells:
        print("   " + " | ".join(v.ljust(widths[i]) for i, v in enumerate(row)))

    if len(rows) > max_rows:
        print(f"   ... con {len(rows) - max_rows} dong nua (da gioi han {max_rows})")


def fetch_validation_results(
    conn: sqlite3.Connection,
) -> tuple[list[str], list[tuple]] | None:
    """Doc ``validation_results`` neu script da tao table/view nay.

    Sap xep theo tat ca cot giup output on dinh ma khong rang buoc script
    validation phai dung mot khoa hay thu tu cot cu the.
    """
    exists = conn.execute(
        """
        SELECT 1
        FROM (
            SELECT name FROM sqlite_master WHERE type IN ('table', 'view')
            UNION ALL
            SELECT name FROM sqlite_temp_master WHERE type IN ('table', 'view')
        )
        WHERE name = 'validation_results' COLLATE NOCASE
        LIMIT 1
        """
    ).fetchone()
    if exists is None:
        return None

    cursor = conn.execute('SELECT * FROM "validation_results"')
    columns = [description[0] for description in cursor.description or []]
    if not columns:
        return columns, []

    order_by = ", ".join(str(index) for index in range(1, len(columns) + 1))
    cursor = conn.execute(
        f'SELECT * FROM "validation_results" ORDER BY {order_by}'
    )
    return columns, cursor.fetchall()


def export_csv(path: Path, columns: list[str], rows: list[tuple]) -> None:
    """Xuat CSV UTF-8 voi thu tu dong da duoc on dinh tu truy van."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.writer(csv_file, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def summarize_validation_results(
    columns: list[str], rows: list[tuple]
) -> tuple[int, str | None]:
    """In tong ket va tra so validation blocking khong PASS.

    Ten cot duoc doi chieu khong phan biet hoa-thuong de SQL co the chon
    convention rieng. Gia tri ``is_blocking`` chi duoc bat khi bang 1.
    """
    column_indexes = {name.casefold(): index for index, name in enumerate(columns)}
    status_index = column_indexes.get("status")
    blocking_index = column_indexes.get("is_blocking")

    print("\nVALIDATION_RESULTS")
    print(f"   Tong so dong: {len(rows)}")

    if not rows:
        return 0, "khong co dong nao"

    if status_index is None:
        return 0, "thieu cot status"

    status_counts: dict[str, int] = {}
    for row in rows:
        raw_status = row[status_index]
        status = "NULL" if raw_status is None else str(raw_status).strip().upper()
        status_counts[status] = status_counts.get(status, 0) + 1

    if status_counts:
        counts = ", ".join(
            f"{status}={status_counts[status]}" for status in sorted(status_counts)
        )
        print(f"   Trang thai  : {counts}")
    else:
        print("   Trang thai  : (khong co dong nao)")

    if blocking_index is None:
        return 0, "thieu cot is_blocking"

    blocking_failures = 0
    for row in rows:
        status = "" if row[status_index] is None else str(row[status_index]).strip()
        is_blocking = row[blocking_index]
        if is_blocking == 1 and status.upper() != "PASS":
            blocking_failures += 1

    print(f"   Blocking khong PASS: {blocking_failures}")
    return blocking_failures, None


def run_file(
    sql_path: Path,
    db_path: Path,
    *,
    fail_on_blocking: bool = False,
    output_csv: Path | None = None,
) -> int:
    if not sql_path.is_file():
        print(f"LOI: khong tim thay file SQL: {sql_path}")
        return 1

    sql_text = sql_path.read_text(encoding="utf-8")
    statements = list(split_statements(sql_text))

    print("=" * 78)
    print(f"File SQL   : {sql_path}")
    print(f"Database   : {db_path}")
    print(f"So cau lenh: {len(statements)}")
    print("=" * 78)

    failed = 0
    blocking_failures = 0
    validation_schema_error: str | None = None
    contract_failed = False
    # isolation_level=None -> autocommit, moi cau lenh co hieu luc ngay.
    with sqlite3.connect(db_path, isolation_level=None) as conn:
        cursor = conn.cursor()
        for index, statement in enumerate(statements, start=1):
            preview = " ".join(statement.split())
            if len(preview) > 90:
                preview = preview[:87] + "..."
            print(f"\n[{index}/{len(statements)}] {preview}")
            try:
                cursor.execute(statement)
                if cursor.description is not None:
                    columns = [d[0] for d in cursor.description]
                    print_table(columns, cursor.fetchall())
                elif cursor.rowcount >= 0:
                    print(f"   OK ({cursor.rowcount} dong bi anh huong)")
                else:
                    # DDL (CREATE/DROP/...) tra rowcount = -1, khong co y nghia.
                    print("   OK")
            except sqlite3.Error as exc:
                failed += 1
                print(f"   LOI SQL: {exc}")

        if sql_path.name.casefold() == "02_validate.sql" and failed == 0:
            try:
                bound_fingerprint = bind_phase2_validation_fingerprint(conn)
                print(
                    "\nPHASE 2 VALIDATION BINDING"
                    f"\n   Fingerprint : {bound_fingerprint}"
                )
            except (Phase2ContractError, sqlite3.Error) as exc:
                contract_failed = True
                validation_schema_error = str(exc)

        validation_results = fetch_validation_results(conn)
        if validation_results is not None:
            columns, rows = validation_results
            blocking_failures, summary_error = summarize_validation_results(
                columns, rows
            )
            if validation_schema_error is None:
                validation_schema_error = summary_error
            if output_csv is not None:
                export_csv(output_csv, columns, rows)
                print(f"   Da xuat CSV : {output_csv}")
        elif output_csv is not None:
            print("\nCHU Y: khong co validation_results; khong xuat CSV.")

    print("\n" + "=" * 78)
    if failed:
        print(f"KET QUA: {failed}/{len(statements)} cau lenh LOI")
    else:
        print(f"KET QUA: tat ca {len(statements)} cau lenh chay thanh cong")
    if validation_schema_error is not None:
        print(f"CHU Y: validation_results {validation_schema_error}")
    if fail_on_blocking and blocking_failures:
        print(f"GATE: FAIL ({blocking_failures} validation blocking khong PASS)")
    elif fail_on_blocking and validation_schema_error is not None:
        print("GATE: LOI (khong the danh gia validation blocking)")
    elif fail_on_blocking:
        print("GATE: PASS")
    print("=" * 78)
    gate_failed = fail_on_blocking and (
        blocking_failures > 0 or validation_schema_error is not None
    )
    return 1 if failed or contract_failed or gate_failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Chay file .sql tren database SQLite cua do an."
    )
    parser.add_argument("sql_file", help="Duong dan toi file .sql")
    parser.add_argument(
        "--db",
        default=str(DB_PATH),
        help=f"Duong dan database (mac dinh: {DB_PATH})",
    )
    parser.add_argument(
        "--fail-on-blocking",
        action="store_true",
        help=(
            "Tra exit code khac 0 neu validation_results co dong "
            "is_blocking=1 va status khac PASS"
        ),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        help="Xuat validation_results ra file CSV UTF-8",
    )
    args = parser.parse_args()
    output_csv = args.output_csv.resolve() if args.output_csv is not None else None
    return run_file(
        Path(args.sql_file).resolve(),
        Path(args.db).resolve(),
        fail_on_blocking=args.fail_on_blocking,
        output_csv=output_csv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
