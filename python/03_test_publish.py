"""Isolated regression tests for Phase 3 all-or-restore publication."""
from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("03_descriptive.py")
spec = importlib.util.spec_from_file_location("phase3_descriptive", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Cannot load Phase 3 module")
phase3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase3)


def create_database(path: Path, marker: str, user_version: int) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE release_marker (value TEXT NOT NULL)")
        connection.execute("INSERT INTO release_marker VALUES (?)", (marker,))
        connection.execute(f"PRAGMA user_version = {user_version}")
        connection.commit()
    finally:
        connection.close()


def database_snapshot(path: Path) -> tuple[str, int, tuple[str, ...]]:
    connection = sqlite3.connect(path)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        dump = tuple(connection.iterdump())
        return integrity, user_version, dump
    finally:
        connection.close()


def test_text_rollback(root: Path) -> None:
    stage = root / "text_stage"
    target = root / "text_target"
    stage.mkdir()
    target.mkdir()
    staged_targets = []
    for index in range(2):
        staged = stage / f"item_{index}.txt"
        published = target / f"item_{index}.txt"
        staged.write_text(f"new-{index}", encoding="utf-8")
        published.write_text(f"old-{index}", encoding="utf-8")
        staged_targets.append((staged, published))

    original_replace = phase3.os.replace
    calls = 0

    def fail_second_replace(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected publication failure")
        original_replace(source, destination)

    phase3.os.replace = fail_second_replace
    try:
        try:
            phase3.replace_outputs_atomically(staged_targets)
        except phase3.Phase3Error:
            pass
        else:
            raise AssertionError("Injected text failure did not abort publication")
    finally:
        phase3.os.replace = original_replace

    for index in range(2):
        actual = (target / f"item_{index}.txt").read_text(encoding="utf-8")
        if actual != f"old-{index}":
            raise AssertionError(f"Text rollback failed for item {index}: {actual}")


def test_sqlite_fallback_success(root: Path) -> None:
    stage = root / "sqlite_success_stage"
    target = root / "sqlite_success_target"
    stage.mkdir()
    target.mkdir()
    staged_database = stage / "renewables.db"
    published_database = target / "renewables.db"
    create_database(staged_database, "new", 2)
    create_database(published_database, "old", 1)
    expected_new = database_snapshot(staged_database)

    original_db_path = phase3.DB_PATH
    original_replace = phase3.os.replace

    def deny_database_replace(source: Path, destination: Path) -> None:
        if Path(destination).resolve() == published_database.resolve():
            raise PermissionError("injected database lock")
        original_replace(source, destination)

    phase3.DB_PATH = published_database
    phase3.os.replace = deny_database_replace
    try:
        phase3.replace_outputs_atomically([(staged_database, published_database)])
    finally:
        phase3.os.replace = original_replace
        phase3.DB_PATH = original_db_path

    if database_snapshot(published_database) != expected_new:
        raise AssertionError("SQLite fallback did not publish the complete new database")
    if staged_database.exists():
        raise AssertionError("SQLite fallback did not remove the staged database")


def test_sqlite_fallback_rollback(root: Path) -> None:
    stage = root / "sqlite_rollback_stage"
    target = root / "sqlite_rollback_target"
    stage.mkdir()
    target.mkdir()
    staged_database = stage / "renewables.db"
    published_database = target / "renewables.db"
    staged_text = stage / "after_database.txt"
    published_text = target / "after_database.txt"
    create_database(staged_database, "new", 2)
    create_database(published_database, "old", 1)
    staged_text.write_text("new-text", encoding="utf-8")
    published_text.write_text("old-text", encoding="utf-8")
    expected_old = database_snapshot(published_database)

    original_db_path = phase3.DB_PATH
    original_replace = phase3.os.replace
    original_backup_replace = phase3.sqlite_backup_replace
    backup_calls: list[tuple[Path, Path]] = []

    def fail_after_database(source: Path, destination: Path) -> None:
        resolved_destination = Path(destination).resolve()
        if resolved_destination == published_database.resolve():
            raise PermissionError("injected database lock")
        if resolved_destination == published_text.resolve():
            raise OSError("injected failure after database publication")
        original_replace(source, destination)

    def traced_backup_replace(source: Path, destination: Path) -> None:
        backup_calls.append((Path(source), Path(destination)))
        original_backup_replace(source, destination)

    phase3.DB_PATH = published_database
    phase3.os.replace = fail_after_database
    phase3.sqlite_backup_replace = traced_backup_replace
    try:
        try:
            phase3.replace_outputs_atomically([
                (staged_database, published_database),
                (staged_text, published_text),
            ])
        except phase3.Phase3Error:
            pass
        else:
            raise AssertionError("Injected post-database failure did not abort publication")
    finally:
        phase3.sqlite_backup_replace = original_backup_replace
        phase3.os.replace = original_replace
        phase3.DB_PATH = original_db_path

    if len(backup_calls) != 2:
        raise AssertionError(
            f"Expected SQLite publication and restoration calls, found {len(backup_calls)}"
        )
    if database_snapshot(published_database) != expected_old:
        raise AssertionError("SQLite rollback did not restore the complete old database")
    if published_text.read_text(encoding="utf-8") != "old-text":
        raise AssertionError("Text output changed despite post-database rollback")


def test_sqlite_fallback_backup_error(root: Path) -> None:
    stage = root / "sqlite_backup_error_stage"
    target = root / "sqlite_backup_error_target"
    stage.mkdir()
    target.mkdir()
    staged_database = stage / "renewables.db"
    published_database = target / "renewables.db"
    create_database(staged_database, "new", 2)
    create_database(published_database, "old", 1)
    expected_old = database_snapshot(published_database)

    original_db_path = phase3.DB_PATH
    original_replace = phase3.os.replace
    original_backup_replace = phase3.sqlite_backup_replace
    backup_calls = 0

    def deny_database_replace(source: Path, destination: Path) -> None:
        raise PermissionError("injected database lock")

    def fail_first_backup(source: Path, destination: Path) -> None:
        nonlocal backup_calls
        backup_calls += 1
        if backup_calls == 1:
            raise sqlite3.OperationalError("injected SQLite backup failure")
        original_backup_replace(source, destination)

    phase3.DB_PATH = published_database
    phase3.os.replace = deny_database_replace
    phase3.sqlite_backup_replace = fail_first_backup
    try:
        try:
            phase3.replace_outputs_atomically([(staged_database, published_database)])
        except phase3.Phase3Error as exc:
            if "previous outputs restored" not in str(exc):
                raise AssertionError(f"Unexpected backup-error message: {exc}") from exc
        else:
            raise AssertionError("Injected SQLite backup failure did not abort publication")
    finally:
        phase3.sqlite_backup_replace = original_backup_replace
        phase3.os.replace = original_replace
        phase3.DB_PATH = original_db_path

    if backup_calls != 2:
        raise AssertionError(f"Expected failed publication plus restoration, found {backup_calls}")
    if database_snapshot(published_database) != expected_old:
        raise AssertionError("SQLite backup error did not preserve the old database")


def test_sqlite_fallback_unlink_error(root: Path) -> None:
    stage = root / "sqlite_unlink_error_stage"
    target = root / "sqlite_unlink_error_target"
    stage.mkdir()
    target.mkdir()
    staged_database = stage / "renewables.db"
    published_database = target / "renewables.db"
    create_database(staged_database, "new", 2)
    create_database(published_database, "old", 1)
    expected_old = database_snapshot(published_database)

    original_db_path = phase3.DB_PATH
    original_replace = phase3.os.replace
    original_unlink = phase3.os.unlink

    def deny_database_replace(source: Path, destination: Path) -> None:
        raise PermissionError("injected database lock")

    def fail_staged_unlink(path: object, *args: object, **kwargs: object) -> None:
        if Path(path).resolve() == staged_database.resolve():
            raise OSError("injected staged database unlink failure")
        original_unlink(path, *args, **kwargs)

    phase3.DB_PATH = published_database
    phase3.os.replace = deny_database_replace
    phase3.os.unlink = fail_staged_unlink
    try:
        try:
            phase3.replace_outputs_atomically([(staged_database, published_database)])
        except phase3.Phase3Error as exc:
            if "previous outputs restored" not in str(exc):
                raise AssertionError(f"Unexpected unlink-error message: {exc}") from exc
        else:
            raise AssertionError("Injected staged unlink failure did not abort publication")
    finally:
        phase3.os.unlink = original_unlink
        phase3.os.replace = original_replace
        phase3.DB_PATH = original_db_path

    if database_snapshot(published_database) != expected_old:
        raise AssertionError("SQLite unlink error did not restore the old database")


def test_sqlite_rollback_failure_is_reported(root: Path) -> None:
    stage = root / "sqlite_restore_error_stage"
    target = root / "sqlite_restore_error_target"
    stage.mkdir()
    target.mkdir()
    staged_database = stage / "renewables.db"
    published_database = target / "renewables.db"
    staged_text = stage / "after_database.txt"
    published_text = target / "after_database.txt"
    create_database(staged_database, "new", 2)
    create_database(published_database, "old", 1)
    staged_text.write_text("new-text", encoding="utf-8")
    published_text.write_text("old-text", encoding="utf-8")

    original_db_path = phase3.DB_PATH
    original_replace = phase3.os.replace
    original_backup_replace = phase3.sqlite_backup_replace
    backup_calls = 0

    def fail_after_database(source: Path, destination: Path) -> None:
        if Path(destination).resolve() == published_database.resolve():
            raise PermissionError("injected database lock")
        raise OSError("injected failure after database publication")

    def fail_restoration(source: Path, destination: Path) -> None:
        nonlocal backup_calls
        backup_calls += 1
        if backup_calls == 2:
            raise sqlite3.OperationalError("injected SQLite restoration failure")
        original_backup_replace(source, destination)

    phase3.DB_PATH = published_database
    phase3.os.replace = fail_after_database
    phase3.sqlite_backup_replace = fail_restoration
    try:
        try:
            phase3.replace_outputs_atomically([
                (staged_database, published_database),
                (staged_text, published_text),
            ])
        except phase3.Phase3Error as exc:
            message = str(exc)
            if "rollback incomplete" not in message:
                raise AssertionError(f"Incomplete rollback was not reported: {message}") from exc
            if "publication error" not in message or "rollback errors" not in message:
                raise AssertionError(f"Error context is incomplete: {message}") from exc
        else:
            raise AssertionError("Injected restoration failure did not abort publication")
    finally:
        phase3.sqlite_backup_replace = original_backup_replace
        phase3.os.replace = original_replace
        phase3.DB_PATH = original_db_path


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="phase3_publish_test_") as temp_name:
        root = Path(temp_name)
        test_text_rollback(root)
        test_sqlite_fallback_success(root)
        test_sqlite_fallback_rollback(root)
        test_sqlite_fallback_backup_error(root)
        test_sqlite_fallback_unlink_error(root)
        test_sqlite_rollback_failure_is_reported(root)
    print(
        "PHASE 3 PUBLICATION ROLLBACK TEST: PASS | "
        "text_restore=1 | sqlite_fallback=1 | sqlite_restore=1 | "
        "sqlite_backup_error=1 | sqlite_unlink_error=1 | rollback_incomplete=1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
