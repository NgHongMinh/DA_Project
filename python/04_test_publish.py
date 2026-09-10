"""Isolated regression tests for Phase 4 all-or-restore publication."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Callable


PYTHON_DIR = Path(__file__).resolve().parent
MODULE_PATH = PYTHON_DIR / "04_charts.py"


def load_phase4_module() -> ModuleType:
    """Load a numerically named script without executing its CLI entry point."""
    if str(PYTHON_DIR) not in sys.path:
        sys.path.insert(0, str(PYTHON_DIR))
    spec = importlib.util.spec_from_file_location("phase4_charts", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load Phase 4 module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    if not callable(getattr(module, "replace_outputs_atomically", None)):
        raise RuntimeError(
            "Phase 4 module does not expose replace_outputs_atomically(staged_targets)"
        )
    return module


phase4 = load_phase4_module()


def expect_publication_failure(action: Callable[[], None], context: str) -> Exception:
    """Require an injected publication error to escape after rollback finishes."""
    try:
        action()
    except Exception as exc:  # The public contract guarantees behavior, not an error class.
        return exc
    raise AssertionError(f"Injected {context} failure did not abort publication")


def write_pairs(
    stage: Path,
    target: Path,
    count: int,
    *,
    create_targets: bool,
) -> list[tuple[Path, Path]]:
    """Create deterministic staged/target pairs entirely below a temporary root."""
    stage.mkdir()
    target.mkdir()
    pairs: list[tuple[Path, Path]] = []
    for index in range(count):
        staged_path = stage / f"item_{index}.bin"
        target_path = target / f"item_{index}.bin"
        staged_path.write_bytes(f"new-{index}".encode("ascii"))
        if create_targets:
            target_path.write_bytes(f"old-{index}".encode("ascii"))
        pairs.append((staged_path, target_path))
    return pairs


def inject_failure_on_target(
    pairs: list[tuple[Path, Path]],
    failure_index: int,
) -> tuple[Callable[..., None], Callable[..., None]]:
    """Return the original and a replacement for the module's os.replace."""
    original_replace = phase4.os.replace
    target_paths = {target.resolve(): index for index, (_, target) in enumerate(pairs)}
    injected = False

    def failing_replace(source: object, destination: object, *args: object, **kwargs: object) -> None:
        nonlocal injected
        destination_path = Path(destination).resolve()
        if target_paths.get(destination_path) == failure_index and not injected:
            injected = True
            raise OSError("injected Phase 4 publication failure")
        original_replace(source, destination, *args, **kwargs)

    return original_replace, failing_replace


def test_existing_outputs_rollback(root: Path) -> None:
    """A mid-publication error must restore every pre-existing target byte-for-byte."""
    pairs = write_pairs(
        root / "existing_stage", root / "existing_target", 3, create_targets=True
    )
    before = {target: target.read_bytes() for _, target in pairs}
    original_replace, failing_replace = inject_failure_on_target(pairs, failure_index=1)

    phase4.os.replace = failing_replace
    try:
        expect_publication_failure(
            lambda: phase4.replace_outputs_atomically(pairs),
            "mid-publication existing-output",
        )
    finally:
        phase4.os.replace = original_replace

    after = {target: target.read_bytes() for _, target in pairs}
    if after != before:
        changed = [target.name for target in before if before[target] != after[target]]
        raise AssertionError(f"Existing-output rollback changed targets: {changed}")


def test_new_output_rollback(root: Path) -> None:
    """Rollback must remove a newly introduced target published before failure."""
    pairs = write_pairs(root / "new_stage", root / "new_target", 3, create_targets=False)
    # The failing target and the untouched tail simulate old release members.
    pairs[1][1].write_bytes(b"old-1")
    pairs[2][1].write_bytes(b"old-2")
    original_replace, failing_replace = inject_failure_on_target(pairs, failure_index=1)

    phase4.os.replace = failing_replace
    try:
        expect_publication_failure(
            lambda: phase4.replace_outputs_atomically(pairs),
            "mid-publication new-output",
        )
    finally:
        phase4.os.replace = original_replace

    if pairs[0][1].exists():
        raise AssertionError("Rollback retained a target that did not exist before publication")
    if pairs[1][1].read_bytes() != b"old-1":
        raise AssertionError("Rollback changed the target at the injected failure point")
    if pairs[2][1].read_bytes() != b"old-2":
        raise AssertionError("Rollback changed a target that publication had not reached")


def test_rollback_failure_retains_backup(root: Path) -> None:
    """An incomplete rollback must preserve the last recoverable old copy."""
    pairs = write_pairs(
        root / "rollback_error_stage",
        root / "rollback_error_target",
        2,
        create_targets=True,
    )
    original_replace = phase4.os.replace

    def failing_replace(source: object, destination: object, *args: object, **kwargs: object) -> None:
        source_path = Path(source)
        destination_path = Path(destination).resolve()
        if source_path == pairs[1][0] and destination_path == pairs[1][1].resolve():
            raise OSError("injected Phase 4 publication failure")
        if (
            source_path.name.endswith(f"_{pairs[0][1].name}.bak")
            and destination_path == pairs[0][1].resolve()
        ):
            raise OSError("injected Phase 4 rollback failure")
        original_replace(source, destination, *args, **kwargs)

    phase4.os.replace = failing_replace
    try:
        error = expect_publication_failure(
            lambda: phase4.replace_outputs_atomically(pairs),
            "rollback-restore",
        )
    finally:
        phase4.os.replace = original_replace

    message = str(error)
    if "rollback incomplete" not in message or "backup retained at" not in message:
        raise AssertionError(f"Incomplete rollback did not report retained backup: {message}")
    backup_dirs = list(pairs[0][1].parent.glob(".phase4_backup_*"))
    if len(backup_dirs) != 1:
        raise AssertionError(f"Expected one retained backup directory, found {backup_dirs}")
    retained = list(backup_dirs[0].glob(f"*_{pairs[0][1].name}.bak"))
    if len(retained) != 1 or retained[0].read_bytes() != b"old-0":
        raise AssertionError("Retained backup does not contain the original target bytes")
    if pairs[0][1].read_bytes() != b"new-0":
        raise AssertionError("Injected rollback failure did not leave the failed target unrestored")


def test_successful_publication(root: Path) -> None:
    """The same primitive must publish both replacements and newly created targets."""
    pairs = write_pairs(root / "success_stage", root / "success_target", 3, create_targets=True)
    pairs[2][1].unlink()
    phase4.replace_outputs_atomically(pairs)
    for index, (staged, target) in enumerate(pairs):
        if target.read_bytes() != f"new-{index}".encode("ascii"):
            raise AssertionError(f"Successful publication produced wrong bytes for item {index}")
        if staged.exists():
            raise AssertionError(f"Staged item {index} still exists after publication")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="phase4_publish_test_") as temp_name:
        root = Path(temp_name).resolve()
        test_existing_outputs_rollback(root)
        test_new_output_rollback(root)
        test_rollback_failure_retains_backup(root)
        test_successful_publication(root)
    print(
        "PHASE 4 PUBLICATION ROLLBACK TEST: PASS | "
        "existing_restore=1 | new_target_cleanup=1 | "
        "rollback_backup_retained=1 | successful_publish=1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
