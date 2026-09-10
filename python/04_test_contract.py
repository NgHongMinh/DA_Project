"""Regression tests for Phase 4 input locking and percentage labels."""
from __future__ import annotations

import copy
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

from config import CLEAN
from phase4_contract import (
    EXPECTED_PHASE2_FACT_ENERGY_SHA256,
    EXPECTED_PHASE2_FACT_ROWS,
    EXPECTED_PHASE2_FINGERPRINT,
)


PYTHON_DIR = Path(__file__).resolve().parent
MODULE_PATH = PYTHON_DIR / "04_charts.py"


def load_phase4_module():
    spec = importlib.util.spec_from_file_location("phase4_contract_test_target", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load Phase 4 module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


phase4 = load_phase4_module()


def test_fact_energy_lock() -> None:
    inputs, input_checks = phase4.load_inputs()
    if not phase4.phase2_fact_energy_lock_ok(input_checks):
        raise AssertionError(f"Canonical fact_energy.csv failed its lock: {input_checks}")
    if len(inputs.fact_energy) != EXPECTED_PHASE2_FACT_ROWS:
        raise AssertionError("Canonical fact_energy.csv row count differs from the contract")
    if inputs.fact_energy_sha256 != EXPECTED_PHASE2_FACT_ENERGY_SHA256:
        raise AssertionError("Canonical fact_energy.csv SHA-256 differs from the contract")
    if input_checks["phase2_db_fingerprint"] != EXPECTED_PHASE2_FINGERPRINT:
        raise AssertionError("Current Phase 2 database fingerprint differs from the contract")

    with tempfile.TemporaryDirectory(prefix="phase4_fact_lock_test_") as temp_name:
        mutated_path = Path(temp_name) / "fact_energy.csv"
        shutil.copy2(CLEAN / "fact_energy.csv", mutated_path)
        mutated = pd.read_csv(mutated_path, low_memory=False)
        mask = (
            mutated["entity"].eq("Philippines")
            & mutated["year"].eq(2005)
            & mutated["metric_key"].eq("wind_generation_twh")
        )
        if int(mask.sum()) != 1:
            raise AssertionError("Locked C13 mutation fixture is not unique")
        mutated.loc[mask, "value"] = mutated.loc[mask, "value"] * 1.001
        mutated.to_csv(mutated_path, index=False, encoding="utf-8", lineterminator="\n")

        changed_checks = copy.deepcopy(input_checks)
        changed_checks["phase2_fact_rows"] = len(mutated)
        changed_checks["phase2_fact_energy_sha256"] = phase4.file_hash(mutated_path)
        if changed_checks["phase2_fact_rows"] != EXPECTED_PHASE2_FACT_ROWS:
            raise AssertionError("Mutation test unexpectedly changed the row count")
        if phase4.phase2_fact_energy_lock_ok(changed_checks):
            raise AssertionError("A same-shape fact_energy.csv value mutation passed the input lock")
        try:
            phase4.enforce_phase2_fact_energy_lock(changed_checks)
        except phase4.Phase4Error as exc:
            if "before chart build" not in str(exc):
                raise AssertionError(f"Unexpected mutation rejection message: {exc}") from exc
        else:
            raise AssertionError("A same-shape mutation was not stopped before chart-data construction")


def test_c03_share_labels() -> None:
    inputs, _ = phase4.load_inputs()
    data = phase4.build_chart_data(inputs)["country_mix_2021"]
    shares = data[data["metric_name"].eq("technology_share")]
    lookup = shares.set_index(["entity", "series_key"])["metric_value"]
    expected = {
        ("Indonesia", "SOLAR"): "0,3%",
        ("Laos", "SOLAR"): "0,1%",
        ("Vietnam", "OTHER_RENEWABLES"): "0,2%",
    }
    actual = {key: phase4._format_share_label(lookup.loc[key]) for key in expected}
    if actual != expected:
        raise AssertionError(f"C03 small-share labels changed: expected={expected}, actual={actual}")
    positive_labels = shares.loc[shares["metric_value"].gt(0), "metric_value"].map(
        phase4._format_share_label
    )
    if positive_labels.isin({"", "0%", "0,0%"}).any():
        raise AssertionError("At least one positive C03 share is labelled as zero")
    if phase4._format_share_label(0.00001) != "<0,1%":
        raise AssertionError("Ultra-small positive shares do not use the locked fallback label")

    captured_figure = None
    original_save_figure = phase4._save_figure

    def capture_figure(figure, _target) -> None:
        nonlocal captured_figure
        captured_figure = figure

    phase4._save_figure = capture_figure
    try:
        phase4._render_c03(data, Path("unused_c03.png"))
        if captured_figure is None or len(captured_figure.axes) != 3:
            raise AssertionError("C03 render did not expose the expected heatmap colorbar")
        formatter = captured_figure.axes[-1].yaxis.get_major_formatter()
        actual_ticks = [formatter(value, index) for index, value in enumerate((0.0, 0.2, 1.0))]
        expected_ticks = ["0,0%", "20,0%", "100,0%"]
        if actual_ticks != expected_ticks:
            raise AssertionError(
                "C03 colorbar is not using Vietnamese percentage labels: "
                f"expected={expected_ticks}, actual={actual_ticks}"
            )
    finally:
        phase4._save_figure = original_save_figure
        if captured_figure is not None:
            phase4.plt.close(captured_figure)


def test_c06_all_zero_panel() -> None:
    inputs, _ = phase4.load_inputs()
    data = phase4.build_chart_data(inputs)["small_multiples"]
    brunei = data[data["entity"].eq("Brunei")].sort_values("year")
    if len(brunei) != 22 or not brunei["metric_value"].eq(0).all():
        raise AssertionError("C06 all-zero regression fixture for Brunei changed")

    figure, axis = phase4._new_figure(1, 1)
    try:
        phase4._configure_small_multiple_y_axis(
            axis,
            brunei,
            shared=False,
            global_max=float(data["metric_value"].max()) * 1.08,
        )
        if tuple(axis.get_ylim()) != (0.0, 1.0):
            raise AssertionError(f"C06 all-zero y limits changed: {axis.get_ylim()}")
        if axis.get_yticks().tolist() != [0.0]:
            raise AssertionError(f"C06 all-zero panel has repeated y ticks: {axis.get_yticks()}")
        annotations = [item.get_text() for item in axis.texts]
        if annotations != ["Toàn kỳ = 0 TWh"]:
            raise AssertionError(f"C06 all-zero annotation changed: {annotations}")
    finally:
        phase4.plt.close(figure)


def main() -> int:
    test_fact_energy_lock()
    test_c03_share_labels()
    test_c06_all_zero_panel()
    print(
        "PHASE 4 CONTRACT REGRESSION TEST: PASS | "
        "fact_energy_lock=1 | mutation_rejected=1 | c03_labels=1 | "
        "c03_colorbar=1 | c06_zero_panel=1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
