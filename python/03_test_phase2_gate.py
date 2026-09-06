"""Isolated regression tests for the Phase 2 validation gate."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path
from typing import Callable

from config import DB_PATH, OUTPUT
from phase2_contract import Phase2ContractError, validate_phase2_gate


Mutation = Callable[[sqlite3.Connection], None]


def copy_database(target: Path) -> None:
    source = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def expect_rejected(root: Path, name: str, mutation: Mutation) -> None:
    path = root / f"{name}.db"
    copy_database(path)
    connection = sqlite3.connect(path)
    try:
        mutation(connection)
        connection.commit()
        try:
            validate_phase2_gate(connection)
        except Phase2ContractError:
            return
        raise AssertionError(f"Gate accepted invalid case: {name}")
    finally:
        connection.close()


def main() -> int:
    connection = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        validate_phase2_gate(connection)
    finally:
        connection.close()

    with tempfile.TemporaryDirectory(prefix=".phase2_gate_test_", dir=OUTPUT) as temp_name:
        root = Path(temp_name)
        expect_rejected(root, "empty", lambda conn: conn.execute("DELETE FROM validation_results"))
        expect_rejected(
            root,
            "missing_required",
            lambda conn: conn.execute(
                "DELETE FROM validation_results WHERE check_id='S31_VALUE_CLASS'"
            ),
        )
        expect_rejected(
            root,
            "blocking_failure",
            lambda conn: conn.execute("UPDATE validation_results SET status='FAIL' WHERE check_id='V8'"),
        )
        expect_rejected(
            root,
            "unbound",
            lambda conn: conn.execute(
                "UPDATE validation_results SET phase2_input_fingerprint='UNBOUND'"
            ),
        )
        expect_rejected(
            root,
            "stale",
            lambda conn: conn.execute(
                "UPDATE validation_results SET phase2_input_fingerprint=?", ("0" * 64,)
            ),
        )
    print("PHASE 2 GATE REGRESSION TESTS: PASS | valid=1 | rejected=5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
