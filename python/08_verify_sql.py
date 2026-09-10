"""Sequential, fail-fast acceptance verifier for Phase 8 SQL.

The source database is always opened with ``mode=ro`` and copied to an
in-memory SQLite database.  Both SQL programs may rebuild working tables only
inside that isolated copy.  The sole published artifact is the locked Phase 8
validation CSV.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sqlite3
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import pandas as pd

from config import ARCHIVE, CHARTS, DB_PATH, OUTPUT, SQL_DIR, STATS
from phase2_contract import Phase2ContractError, phase2_input_fingerprint, validate_phase2_gate
from phase3_contract import EXPECTED_PHASE3_VALIDATION_IDS
from phase4_contract import EXPECTED_VALIDATION_IDS as EXPECTED_PHASE4_VALIDATION_IDS
from phase8_contract import (
    ALL_GATE_IDS,
    ENTRY_STATUS_VALUES,
    EXPECTED_ARCHIVE_CSV_COUNT,
    EXPECTED_METRIC_ROWS,
    EXPECTED_PHASE2_BLOCKING_ROWS,
    EXPECTED_PHASE2_FACT_ROWS,
    EXPECTED_PHASE2_INPUT_FINGERPRINT,
    EXPECTED_PHASE2_VALIDATION_ROWS,
    EXPECTED_PHASE2_VALIDATION_STATUS_COUNTS,
    EXPECTED_PHASE3_CROSSCHECK_ROWS,
    EXPECTED_PHASE3_FACT_ROWS,
    EXPECTED_PHASE3_QUESTION_ROWS,
    EXPECTED_PHASE3_VALIDATION_ROWS,
    EXPECTED_PHASE4_VALIDATION_ROWS,
    FINAL_GATE_ID,
    GATE_IDS,
    GATE_STEP_NAMES,
    MATERIAL_ENTRY_STATUS_VALUES,
    MATERIAL_THRESHOLD_TWH,
    METHOD_VERSION,
    NUMERIC_TOLERANCE,
    OUTPUT_FILE_NAME,
    VALIDATION_COLUMNS,
    YEAR_END,
    YEAR_START,
)


SQL02_PATH = SQL_DIR / "02_validate.sql"
SQL03_PATH = SQL_DIR / "03_analysis.sql"
OUTPUT_PATH = STATS / OUTPUT_FILE_NAME
PHASE3_FACT_PATH = STATS / "03_fact_metrics.csv"
PHASE3_CROSSCHECK_PATH = STATS / "03_crosscheck_results.csv"
PHASE3_VALIDATION_PATH = STATS / "03_validation_results.csv"
PHASE4_VALIDATION_PATH = STATS / "04_validation_results.csv"


class Phase8Error(RuntimeError):
    """Base error for an invalid gate or an unusable verifier environment."""


class GateFailure(Phase8Error):
    """A blocking gate failure with CSV-ready evidence."""

    def __init__(self, expected: Any, observed: Any, details: Any):
        super().__init__(str(details))
        self.expected = expected
        self.observed = observed
        self.details = details


@dataclass(frozen=True)
class GateEvidence:
    expected: Any
    observed: Any
    details: Any


@dataclass
class VerificationContext:
    conn: sqlite3.Connection
    sql02_text: str
    sql03_text: str
    fingerprint: str = "UNAVAILABLE"
    protected_before: dict[str, str] = field(default_factory=dict)
    sql_facts: pd.DataFrame | None = None
    python_facts: pd.DataFrame | None = None
    crosscheck: pd.DataFrame | None = None
    phase3_module: ModuleType | None = None

    def close(self) -> None:
        self.conn.close()


class GateAudit:
    """Collect all assertions inside one gate and report them together."""

    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def check(self, name: str, ok: Any, expected: Any, observed: Any) -> None:
        self.checks.append({
            "name": name,
            "status": "PASS" if bool(ok) else "FAIL",
            "expected": _jsonable(expected),
            "observed": _jsonable(observed),
        })

    def finish(self, expected: Any, observed: Any, summary: str) -> GateEvidence:
        failed = [item for item in self.checks if item["status"] == "FAIL"]
        details = {
            "summary": summary,
            "check_count": len(self.checks),
            "failed_count": len(failed),
            "checks": self.checks,
        }
        if failed:
            raise GateFailure(expected, observed, details)
        return GateEvidence(expected, observed, details)


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def _encode(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalise_sql(sql_text: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", " ", sql_text, flags=re.DOTALL)
    without_lines = re.sub(r"--[^\r\n]*", " ", without_blocks)
    return re.sub(r"\s+", " ", without_lines).strip().lower()


def _sql_statement_for_literal(sql_text: str, literal: str) -> str:
    wanted = f"'{literal.lower()}'"
    candidates = [statement.strip() for statement in _normalise_sql(sql_text).split(";")]
    matches = [statement for statement in candidates if wanted in statement]
    if len(matches) != 1:
        raise GateFailure(
            f"one SQL statement containing {literal}",
            len(matches),
            f"Could not identify exactly one {literal} validation statement",
        )
    return matches[0]


def validate_v7_v8_cte_structure(sql_text: str) -> None:
    """Raise when either V7 or V8 is not expressed through a CTE."""
    audit = GateAudit()
    for check_id in ("V7", "V8"):
        statement = _sql_statement_for_literal(sql_text, check_id)
        audit.check(
            f"{check_id}_CTE",
            statement.startswith("with ") and "insert into validation_results" in statement,
            "statement starts with WITH and inserts validation_results",
            statement[:120],
        )
    audit.finish("V7 and V8 use CTE", "static SQL structure checked", "V7/V8 CTE contract")


def validate_entry_window_structure(sql_text: str) -> None:
    """Raise unless both entry thresholds use the locked MIN window syntax."""
    sql = _normalise_sql(sql_text)
    positive = re.search(
        r"min\s*\(\s*case\s+when\s+value\s*>\s*0(?:\.0+)?\s+then\s+year\s+end\s*\)"
        r"\s+over\s*\(\s*partition\s+by\s+entity\s*,\s*series_key\s*\)",
        sql,
    )
    material = re.search(
        r"min\s*\(\s*case\s+when\s+value\s*>=\s*(?:0?\.05|0\.050*)\s+then\s+year\s+end\s*\)"
        r"\s+over\s*\(\s*partition\s+by\s+entity\s*,\s*series_key\s*\)",
        sql,
    )
    audit = GateAudit()
    audit.check("FIRST_POSITIVE_MIN_OVER", positive is not None, "MIN(CASE value>0) OVER entity,series_key", positive is not None)
    audit.check("FIRST_MATERIAL_MIN_OVER", material is not None, "MIN(CASE value>=0.05) OVER entity,series_key", material is not None)
    audit.finish("two locked MIN window expressions", int(positive is not None) + int(material is not None), "entry-window SQL structure")


def _open_readonly_memory(db_path: Path = DB_PATH) -> sqlite3.Connection:
    resolved = db_path.resolve()
    if not resolved.is_file():
        raise Phase8Error(f"SQLite source is missing: {resolved}")
    source = sqlite3.connect(resolved.as_uri() + "?mode=ro", uri=True, timeout=5)
    memory = sqlite3.connect(":memory:")
    try:
        source.backup(memory)
    except Exception:
        memory.close()
        raise
    finally:
        source.close()
    memory.execute("PRAGMA foreign_keys=ON")
    return memory


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _protected_files() -> list[Path]:
    paths: set[Path] = set(ARCHIVE.glob("*.csv"))
    paths.update(path for path in (OUTPUT / "clean").glob("*") if path.is_file())
    paths.update(path for path in CHARTS.glob("*") if path.is_file())
    for prefix in ("00_", "01_", "02_", "03_", "04_", "05_"):
        paths.update(path for path in STATS.glob(f"{prefix}*") if path.is_file())
    if DB_PATH.is_file():
        paths.add(DB_PATH)
    return sorted(paths, key=lambda path: str(path.relative_to(OUTPUT.parent)).lower())


def _snapshot_protected() -> dict[str, str]:
    base = OUTPUT.parent.resolve()
    return {
        path.resolve().relative_to(base).as_posix(): _sha256_file(path)
        for path in _protected_files()
    }


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise GateFailure("existing readable CSV", "missing", str(path))
    try:
        return pd.read_csv(path, low_memory=False)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise GateFailure("existing readable CSV", type(exc).__name__, str(path)) from exc


def _load_phase3_module() -> ModuleType:
    module_name = "_phase3_descriptive_for_phase8"
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    path = Path(__file__).resolve().parent / "03_descriptive.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise Phase8Error(f"Cannot load Phase 3 implementation from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _build_python_facts(conn: sqlite3.Connection, fingerprint: str) -> tuple[pd.DataFrame, ModuleType]:
    module = _load_phase3_module()
    _, fact, current, asean = module.load_input(conn)
    facts, _, _, _ = module.build_python_facts(fact, current, asean, fingerprint)
    return facts, module


def _run_sql_analysis(conn: sqlite3.Connection, sql_text: str) -> pd.DataFrame:
    conn.executescript(sql_text)
    return pd.read_sql_query("SELECT * FROM phase3_sql_results", conn)


def _ensure_analysis(ctx: VerificationContext) -> None:
    if ctx.sql_facts is not None:
        return
    ctx.sql_facts = _run_sql_analysis(ctx.conn, ctx.sql03_text)
    ctx.python_facts, ctx.phase3_module = _build_python_facts(ctx.conn, ctx.fingerprint)
    ctx.crosscheck = ctx.phase3_module.crosscheck(ctx.python_facts, ctx.sql_facts, ctx.fingerprint)


def _metric_counts(facts: pd.DataFrame, names: Iterable[str]) -> dict[str, int]:
    wanted = list(names)
    counts = facts[facts.metric_name.isin(wanted)].groupby("metric_name").size().to_dict()
    return {name: int(counts.get(name, 0)) for name in wanted}


def _crosscheck_subset(crosscheck: pd.DataFrame, metric_names: Iterable[str]) -> tuple[int, int]:
    selected = crosscheck[crosscheck.metric_name.isin(set(metric_names))]
    return len(selected), int(selected.status.ne("PASS").sum())


def _finite_or_null(series: pd.Series) -> bool:
    numeric = pd.to_numeric(series, errors="coerce")
    return bool(np.isfinite(numeric.dropna().to_numpy(dtype=float)).all())


def _close(left: Any, right: Any, tolerance: float = NUMERIC_TOLERANCE) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    if pd.isna(left) or pd.isna(right):
        return False
    return math.isclose(float(left), float(right), abs_tol=tolerance, rel_tol=tolerance)


def validate_rank_gate(facts: pd.DataFrame, crosscheck: pd.DataFrame) -> GateEvidence:
    names = ("asean_rank", "global_rank", "modern_rank_gain")
    counts = _metric_counts(facts, names)
    expected_counts = {name: EXPECTED_METRIC_ROWS[name] for name in names}
    ranks = facts[facts.metric_name.isin(("asean_rank", "global_rank"))]
    calculated = ranks[ranks.value_status.eq("CALCULATED")]
    numeric = pd.to_numeric(calculated.metric_value, errors="coerce")
    ranked_n = pd.to_numeric(calculated.ranked_n, errors="coerce")
    rank_domain = bool((numeric.ge(1) & numeric.le(ranked_n) & numeric.mod(1).eq(0)).all())
    null_ranks = ranks[ranks.metric_value.isna()]
    null_rules = bool(
        null_ranks.value_status.ne("CALCULATED").all()
        and null_ranks.exclusion_reason.isin({"ZERO_SCOPE_TOTAL", "NOT_OBSERVED"}).all()
    )
    subset_n, cross_failures = _crosscheck_subset(crosscheck, names)
    audit = GateAudit()
    audit.check("METRIC_ROWS", counts == expected_counts, expected_counts, counts)
    audit.check("RANK_DOMAIN", rank_domain, "integer 1..ranked_n", int((~(numeric.ge(1) & numeric.le(ranked_n) & numeric.mod(1).eq(0))).sum()))
    audit.check("ZERO_TOTAL_NULL_RULE", null_rules, "NULL rank with explicit reason", len(null_ranks))
    audit.check("PYTHON_SQL_MATCH", cross_failures == 0, "0 failures", cross_failures)
    return audit.finish(expected_counts, {"counts": counts, "crosscheck_rows": subset_n}, "RANK() results, domains, and independent Python agreement")


def validate_yoy_gate(facts: pd.DataFrame, crosscheck: pd.DataFrame) -> GateEvidence:
    names = ("yoy", "q5_yoy")
    counts = _metric_counts(facts, names)
    expected_counts = {name: EXPECTED_METRIC_ROWS[name] for name in names}
    yoy = facts[facts.metric_name.isin(names)].copy()
    group_columns = [
        "subject_type", "subject_key", "series_key", "metric_name",
        "comparison_scope", "filter_variant",
    ]
    first_indices = yoy.groupby(group_columns, dropna=False).period_start_year.idxmin()
    first = yoy.loc[first_indices]
    first_rule = bool(
        first.period_start_year.eq(YEAR_START).all()
        and first.metric_value.isna().all()
        and first.value_status.eq("NOT_DEFINED").all()
        and first.exclusion_reason.eq("MISSING_PREVIOUS").all()
    )
    zero_base = yoy[yoy.exclusion_reason.eq("ZERO_BASE")]
    zero_rule = bool(zero_base.metric_value.isna().all() and zero_base.value_status.eq("NOT_DEFINED").all())
    finite = _finite_or_null(yoy.metric_value)
    subset_n, cross_failures = _crosscheck_subset(crosscheck, names)
    audit = GateAudit()
    audit.check("METRIC_ROWS", counts == expected_counts, expected_counts, counts)
    audit.check("FIRST_YEAR", first_rule, "2000=NULL/MISSING_PREVIOUS per sequence", int(first_rule))
    audit.check("ZERO_BASE", zero_rule, "NULL/NOT_DEFINED/ZERO_BASE", len(zero_base))
    audit.check("FINITE", finite, "no NaN or infinity among calculated values", finite)
    audit.check("PYTHON_SQL_MATCH", cross_failures == 0, "0 failures", cross_failures)
    return audit.finish(expected_counts, {"counts": counts, "crosscheck_rows": subset_n}, "LAG partitions, zero bases, and numerical agreement")


def validate_entry_gate(facts: pd.DataFrame, crosscheck: pd.DataFrame, sql_text: str) -> GateEvidence:
    validate_entry_window_structure(sql_text)
    numeric_names = (
        "first_positive_in_window", "first_material_in_window",
        "observed_entry_year", "observed_material_entry_year",
    )
    status_names = ("entry_status", "material_entry_status")
    counts = _metric_counts(facts, (*numeric_names, *status_names))
    expected_counts = {name: 40 for name in (*numeric_names, *status_names)}
    entry_status = facts[facts.metric_name.eq("entry_status")]
    material_status = facts[facts.metric_name.eq("material_entry_status")]
    allowed_status = bool(
        set(entry_status.metric_text_value.dropna()) <= ENTRY_STATUS_VALUES
        and set(material_status.metric_text_value.dropna()) <= MATERIAL_ENTRY_STATUS_VALUES
    )
    keys = ["subject_key", "series_key"]
    status_wide = entry_status[keys + ["metric_text_value"]].rename(columns={"metric_text_value": "entry_status"})
    observed = facts[facts.metric_name.eq("observed_entry_year")][keys + ["metric_value"]]
    joined = status_wide.merge(observed, on=keys, validate="one_to_one")
    exact_mask = joined.entry_status.eq("OBSERVED_TRANSITION")
    censor_rule = bool(joined.loc[exact_mask, "metric_value"].notna().all() and joined.loc[~exact_mask, "metric_value"].isna().all())
    material_status_wide = material_status[keys + ["metric_text_value"]].rename(columns={"metric_text_value": "material_status"})
    observed_material = facts[facts.metric_name.eq("observed_material_entry_year")][keys + ["metric_value"]]
    material_joined = material_status_wide.merge(observed_material, on=keys, validate="one_to_one")
    material_exact = material_joined.material_status.eq("OBSERVED_MATERIAL_TRANSITION")
    material_censor_rule = bool(
        material_joined.loc[material_exact, "metric_value"].notna().all()
        and material_joined.loc[~material_exact, "metric_value"].isna().all()
    )
    vietnam_solar = facts[
        facts.subject_key.eq("Vietnam")
        & facts.series_key.eq("SOLAR")
        & facts.metric_name.eq("first_positive_in_window")
    ]
    vietnam_year = None if len(vietnam_solar) != 1 else vietnam_solar.iloc[0].metric_value
    names_for_crosscheck = (*numeric_names, *status_names, "is_entry_year_exact", "is_material_entry_year_exact")
    subset_n, cross_failures = _crosscheck_subset(crosscheck, names_for_crosscheck)
    audit = GateAudit()
    audit.check("METRIC_ROWS", counts == expected_counts, expected_counts, counts)
    audit.check("STATUS_ALLOWLIST", allowed_status, "locked entry and material status sets", {"entry": sorted(entry_status.metric_text_value.dropna().unique()), "material": sorted(material_status.metric_text_value.dropna().unique())})
    audit.check("ENTRY_CENSORING", censor_rule, "only exact transitions expose observed entry year", censor_rule)
    audit.check("MATERIAL_CENSORING", material_censor_rule, "only exact material transitions expose observed entry year", material_censor_rule)
    audit.check("VIETNAM_SOLAR", _close(vietnam_year, 2010), 2010, vietnam_year)
    audit.check("PYTHON_SQL_MATCH", cross_failures == 0, "0 failures", cross_failures)
    return audit.finish(expected_counts, {"counts": counts, "Vietnam-SOLAR": vietnam_year, "crosscheck_rows": subset_n}, "MIN OVER entry dates, censoring, threshold, and Python agreement")


def validate_window_gate(facts: pd.DataFrame, crosscheck: pd.DataFrame, sql_text: str) -> GateEvidence:
    names = ("cumulative_generation_twh", "rolling_mean_3y_twh")
    counts = _metric_counts(facts, names)
    expected_counts = {name: EXPECTED_METRIC_ROWS[name] for name in names}
    sql = _normalise_sql(sql_text)
    static_rule = "rows unbounded preceding" in sql and "rows between 2 preceding and current row" in sql
    dimensions = ["subject_type", "subject_key", "series_key", "comparison_scope"]
    generated = facts[facts.metric_name.eq("generation_twh")][dimensions + ["period_start_year", "metric_value"]].rename(columns={"metric_value": "generation"})
    cumulative = facts[facts.metric_name.eq(names[0])][dimensions + ["period_start_year", "metric_value", "value_status"]].rename(columns={"metric_value": "cumulative"})
    cumulative = cumulative.merge(generated, on=[*dimensions, "period_start_year"], validate="one_to_one")
    cumulative = cumulative.sort_values([*dimensions, "period_start_year"], kind="mergesort")
    previous = cumulative.groupby(dimensions, dropna=False).cumulative.shift(1).fillna(0.0)
    recurrence_mask = cumulative.value_status.eq("CALCULATED")
    recurrence_error = (cumulative.loc[recurrence_mask, "cumulative"] - previous[recurrence_mask] - cumulative.loc[recurrence_mask, "generation"]).abs()
    recurrence_ok = bool(recurrence_error.le(NUMERIC_TOLERANCE).all())
    rolling = facts[facts.metric_name.eq(names[1])]
    early = rolling[rolling.period_start_year.isin((YEAR_START, YEAR_START + 1))]
    early_rule = bool(
        len(early) == 24
        and early.metric_value.isna().all()
        and early.value_status.eq("INSUFFICIENT_N").all()
        and early.exclusion_reason.eq("INSUFFICIENT_WINDOW").all()
    )
    rolling_calc = rolling[rolling.period_start_year.ge(YEAR_START + 2)][dimensions + ["period_start_year", "metric_value"]].rename(columns={"metric_value": "rolling"})
    generated_sorted = generated.sort_values([*dimensions, "period_start_year"], kind="mergesort")
    generated_sorted["expected_rolling"] = generated_sorted.groupby(dimensions, dropna=False).generation.transform(lambda series: series.rolling(3, min_periods=3).mean())
    rolling_joined = rolling_calc.merge(generated_sorted[[*dimensions, "period_start_year", "expected_rolling"]], on=[*dimensions, "period_start_year"], validate="one_to_one")
    rolling_error = (rolling_joined.rolling - rolling_joined.expected_rolling).abs()
    rolling_ok = bool(rolling_error.le(NUMERIC_TOLERANCE).all())
    subset_n, cross_failures = _crosscheck_subset(crosscheck, names)
    audit = GateAudit()
    audit.check("METRIC_ROWS", counts == expected_counts, expected_counts, counts)
    audit.check("STATIC_ROWS_FRAME", static_rule, "UNBOUNDED cumulative and 2 PRECEDING rolling frames", static_rule)
    audit.check("CUMULATIVE_RECURRENCE", recurrence_ok, "C(t)=C(t-1)+value(t)", float(recurrence_error.max()) if len(recurrence_error) else None)
    audit.check("EARLY_WINDOW", early_rule, "24 rows for 2000-2001 are NULL/INSUFFICIENT_WINDOW", {"rows": len(early), "rule": early_rule})
    audit.check("ROLLING_3Y", rolling_ok, "exact three-year mean", float(rolling_error.max()) if len(rolling_error) else None)
    audit.check("PYTHON_SQL_MATCH", cross_failures == 0, "0 failures", cross_failures)
    return audit.finish(expected_counts, {"counts": counts, "crosscheck_rows": subset_n}, "ROWS frame semantics and direct recurrences")


def validate_rank_change_gate(facts: pd.DataFrame, crosscheck: pd.DataFrame) -> GateEvidence:
    metric = "rank_gain_over_time"
    changes = facts[facts.metric_name.eq(metric)].copy()
    ranks = facts[facts.metric_name.eq("asean_rank")][["subject_key", "series_key", "period_start_year", "metric_value"]]
    start_ranks = ranks.rename(columns={"period_start_year": "period_start_year", "metric_value": "start_rank"})
    end_ranks = ranks.rename(columns={"period_start_year": "period_end_year", "metric_value": "end_rank"})
    joined = changes.merge(start_ranks, on=["subject_key", "series_key", "period_start_year"], how="left", validate="many_to_one")
    joined = joined.merge(end_ranks, on=["subject_key", "series_key", "period_end_year"], how="left", validate="many_to_one")
    expected_value = joined.start_rank - joined.end_rank
    calculated = joined.metric_value.notna() & expected_value.notna()
    errors = (joined.loc[calculated, "metric_value"] - expected_value[calculated]).abs()
    formula_ok = bool(errors.le(NUMERIC_TOLERANCE).all())
    undefined = expected_value.isna()
    undefined_ok = bool(
        joined.loc[undefined, "metric_value"].isna().all()
        and joined.loc[undefined, "exclusion_reason"].eq("RANK_NOT_DEFINED").all()
    )
    subset_n, cross_failures = _crosscheck_subset(crosscheck, (metric,))
    audit = GateAudit()
    audit.check("METRIC_ROWS", len(changes) == EXPECTED_METRIC_ROWS[metric], EXPECTED_METRIC_ROWS[metric], len(changes))
    audit.check("START_MINUS_END", formula_ok, "rank_start-rank_end", float(errors.max()) if len(errors) else None)
    audit.check("UNDEFINED_ENDPOINT", undefined_ok, "NULL/RANK_NOT_DEFINED", int(undefined.sum()))
    audit.check("SIGN_CONVENTION", formula_ok, "positive means improved rank", formula_ok)
    audit.check("PYTHON_SQL_MATCH", cross_failures == 0, "0 failures", cross_failures)
    return audit.finish(EXPECTED_METRIC_ROWS[metric], {"rows": len(changes), "crosscheck_rows": subset_n}, "endpoint rank self-join and locked sign")


def _gini(values: Sequence[float]) -> float | None:
    array = np.sort(np.asarray(values, dtype=float))
    total = float(array.sum())
    if total <= 0:
        return None
    n = len(array)
    return float(2 * np.sum(np.arange(1, n + 1) * array) / (n * total) - (n + 1) / n)


def validate_concentration_gate(facts: pd.DataFrame, crosscheck: pd.DataFrame) -> GateEvidence:
    names = ("top1_share", "top3_share", "hhi", "gini", "positive_n", "above_0_05_n")
    counts = _metric_counts(facts, names)
    expected_counts = {name: EXPECTED_METRIC_ROWS[name] for name in names}
    concentration = facts[facts.metric_name.isin(names)].copy()
    ratios = concentration[concentration.metric_name.isin(names[:4])]
    calculated = ratios[ratios.value_status.eq("CALCULATED")]
    domains = {
        "top1_share": (0.0, 1.0), "top3_share": (0.0, 1.0),
        "hhi": (0.0, 1.0), "gini": (0.0, 0.9),
    }
    domain_ok = all(
        calculated.loc[calculated.metric_name.eq(name), "metric_value"].between(low - NUMERIC_TOLERANCE, high + NUMERIC_TOLERANCE).all()
        for name, (low, high) in domains.items()
    )
    pivot = ratios.pivot(index=["period_start_year", "series_key"], columns="metric_name", values="metric_value")
    top_order = bool((pivot.top1_share <= pivot.top3_share + NUMERIC_TOLERANCE).fillna(True).all())
    zero_rows = ratios[ratios.metric_value.isna()]
    zero_rule = bool(zero_rows.value_status.eq("NOT_DEFINED").all() and zero_rows.exclusion_reason.eq("ZERO_DENOMINATOR").all())
    count_rows = concentration[concentration.metric_name.isin(names[4:])]
    count_domain = bool(pd.to_numeric(count_rows.metric_value, errors="coerce").between(0, 10).all())

    country = facts[
        facts.subject_type.eq("COUNTRY")
        & facts.comparison_scope.eq("ASEAN_10")
        & facts.metric_name.eq("generation_twh")
        & facts.series_key.isin(("RENEWABLE_TOTAL", "MODERN_WIND_SOLAR"))
    ][["period_start_year", "series_key", "subject_key", "metric_value"]]
    expected_records: list[dict[str, Any]] = []
    for (year, series), group in country.groupby(["period_start_year", "series_key"], sort=True):
        values = np.sort(group.metric_value.to_numpy(dtype=float))[::-1]
        total = float(values.sum())
        expected_records.extend([
            {"period_start_year": year, "series_key": series, "metric_name": "top1_share", "expected": values[:1].sum() / total if total else None},
            {"period_start_year": year, "series_key": series, "metric_name": "top3_share", "expected": values[:3].sum() / total if total else None},
            {"period_start_year": year, "series_key": series, "metric_name": "hhi", "expected": float(np.square(values / total).sum()) if total else None},
            {"period_start_year": year, "series_key": series, "metric_name": "gini", "expected": _gini(values)},
            {"period_start_year": year, "series_key": series, "metric_name": "positive_n", "expected": int((values > 0).sum())},
            {"period_start_year": year, "series_key": series, "metric_name": "above_0_05_n", "expected": int((values >= MATERIAL_THRESHOLD_TWH).sum())},
        ])
    independently = pd.DataFrame(expected_records)
    compared = concentration.merge(independently, on=["period_start_year", "series_key", "metric_name"], validate="one_to_one")
    formula_ok = bool(all(_close(row.metric_value, row.expected) for row in compared.itertuples(index=False)))
    canonical_ok = bool(
        _close(float(np.square(np.ones(10) / 10).sum()), 0.1)
        and _close(float(np.square(np.array([0] * 9 + [1])).sum()), 1.0)
        and _close(_gini(np.ones(10)), 0.0)
        and _close(_gini([0] * 9 + [1]), 0.9)
        and _gini(np.zeros(10)) is None
    )
    subset_n, cross_failures = _crosscheck_subset(crosscheck, names)
    audit = GateAudit()
    audit.check("METRIC_ROWS", counts == expected_counts and len(concentration) == 264, {**expected_counts, "total": 264}, {**counts, "total": len(concentration)})
    audit.check("RATIO_DOMAINS", domain_ok, domains, domain_ok)
    audit.check("TOP_ORDER", top_order, "top1<=top3", top_order)
    audit.check("ZERO_DENOMINATOR", zero_rule, "NULL/NOT_DEFINED/ZERO_DENOMINATOR", len(zero_rows))
    audit.check("COUNT_DOMAIN", count_domain, "integer count 0..10", count_domain)
    audit.check("DIRECT_FORMULAS", formula_ok, "top-N/HHI/Gini/counts recomputed from ASEAN-10", formula_ok)
    audit.check("CANONICAL_CASES", canonical_ok, "uniform and single-country concentration cases", canonical_ok)
    audit.check("PYTHON_SQL_MATCH", cross_failures == 0, "0 failures", cross_failures)
    return audit.finish({**expected_counts, "total": 264}, {**counts, "total": len(concentration), "crosscheck_rows": subset_n}, "ASEAN-10 denominator, bounds, and canonical cases")


def gate_p8_00(ctx: VerificationContext) -> GateEvidence:
    audit = GateAudit()
    feature = ctx.conn.execute(
        "WITH x(entity,year,value) AS (VALUES('a',2000,1.0),('a',2001,2.0),('b',2000,1.0)) "
        "SELECT COUNT(*), MAX(r), MAX(previous), MIN(first_year), MAX(running), MAX(rolling) FROM ("
        "SELECT RANK() OVER(PARTITION BY year ORDER BY value DESC) r, "
        "LAG(value) OVER(PARTITION BY entity ORDER BY year) previous, "
        "MIN(CASE WHEN value>0 THEN year END) OVER(PARTITION BY entity) first_year, "
        "SUM(value) OVER(PARTITION BY entity ORDER BY year ROWS UNBOUNDED PRECEDING) running, "
        "AVG(value) OVER(PARTITION BY entity ORDER BY year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) rolling FROM x)"
    ).fetchone()
    audit.check("SQLITE_FEATURES", feature is not None and feature[0] == 3, "CTE/RANK/LAG/MIN OVER/ROWS execute", feature)
    archive_count = len(list(ARCHIVE.glob("*.csv")))
    audit.check("ARCHIVE_CSV_COUNT", archive_count == EXPECTED_ARCHIVE_CSV_COUNT, EXPECTED_ARCHIVE_CSV_COUNT, archive_count)
    try:
        ctx.fingerprint = validate_phase2_gate(ctx.conn)
        phase2_gate_error = None
    except Phase2ContractError as exc:
        ctx.fingerprint = phase2_input_fingerprint(ctx.conn)
        phase2_gate_error = str(exc)
    audit.check("PHASE2_GATE", phase2_gate_error is None, "complete current Phase 2 validation", phase2_gate_error or "PASS")
    audit.check("PHASE2_FINGERPRINT", ctx.fingerprint == EXPECTED_PHASE2_INPUT_FINGERPRINT, EXPECTED_PHASE2_INPUT_FINGERPRINT, ctx.fingerprint)
    fact_rows = int(ctx.conn.execute("SELECT COUNT(*) FROM fact_energy").fetchone()[0])
    audit.check("FACT_ENERGY_ROWS", fact_rows == EXPECTED_PHASE2_FACT_ROWS, EXPECTED_PHASE2_FACT_ROWS, fact_rows)
    db_phase3_rows = int(ctx.conn.execute("SELECT COUNT(*) FROM fact_metrics").fetchone()[0])
    csv_phase3_rows = len(_load_csv(PHASE3_FACT_PATH))
    audit.check("PHASE3_FACT_ROWS", db_phase3_rows == csv_phase3_rows == EXPECTED_PHASE3_FACT_ROWS, EXPECTED_PHASE3_FACT_ROWS, {"database": db_phase3_rows, "csv": csv_phase3_rows})
    phase4 = _load_csv(PHASE4_VALIDATION_PATH)
    phase4_ids = set(phase4.validation_id.astype(str)) if "validation_id" in phase4 else set()
    phase4_pass = "status" in phase4 and phase4.status.eq("PASS").all()
    phase4_ok = len(phase4) == EXPECTED_PHASE4_VALIDATION_ROWS and phase4_pass and phase4_ids == set(EXPECTED_PHASE4_VALIDATION_IDS)
    audit.check("PHASE4_VALIDATIONS", phase4_ok, "38/38 exact IDs PASS", {"rows": len(phase4), "pass": int(phase4.status.eq("PASS").sum()) if "status" in phase4 else 0})
    return audit.finish(
        "Phase 0-4 locked baselines",
        {"sqlite": sqlite3.sqlite_version, "archive_csv": archive_count, "fact_energy": fact_rows, "phase3": db_phase3_rows, "phase4": len(phase4)},
        "read-only source backed up to isolated in-memory SQLite",
    )


def gate_p8_01(ctx: VerificationContext) -> GateEvidence:
    validate_v7_v8_cte_structure(ctx.sql02_text)
    ctx.conn.executescript(ctx.sql02_text)
    rows = pd.read_sql_query("SELECT check_id,status,is_blocking FROM validation_results", ctx.conn)
    counts = {key: int(value) for key, value in rows.status.value_counts().to_dict().items()}
    blocking = rows[rows.is_blocking.eq(1)]
    blocking_pass = int(blocking.status.eq("PASS").sum())
    audit = GateAudit()
    audit.check("ROWS", len(rows) == EXPECTED_PHASE2_VALIDATION_ROWS, EXPECTED_PHASE2_VALIDATION_ROWS, len(rows))
    audit.check("STATUS_COUNTS", counts == EXPECTED_PHASE2_VALIDATION_STATUS_COUNTS, EXPECTED_PHASE2_VALIDATION_STATUS_COUNTS, counts)
    audit.check("NO_FAIL", int(rows.status.eq("FAIL").sum()) == 0, 0, int(rows.status.eq("FAIL").sum()))
    audit.check("BLOCKING_PASS", len(blocking) == blocking_pass == EXPECTED_PHASE2_BLOCKING_ROWS, f"{EXPECTED_PHASE2_BLOCKING_ROWS}/{EXPECTED_PHASE2_BLOCKING_ROWS}", f"{blocking_pass}/{len(blocking)}")
    recalculated_fp = phase2_input_fingerprint(ctx.conn)
    audit.check("FINGERPRINT", recalculated_fp == ctx.fingerprint == EXPECTED_PHASE2_INPUT_FINGERPRINT, EXPECTED_PHASE2_INPUT_FINGERPRINT, recalculated_fp)
    return audit.finish(
        {"rows": EXPECTED_PHASE2_VALIDATION_ROWS, "statuses": EXPECTED_PHASE2_VALIDATION_STATUS_COUNTS, "blocking_pass": EXPECTED_PHASE2_BLOCKING_ROWS},
        {"rows": len(rows), "statuses": counts, "blocking_pass": blocking_pass},
        "02_validate.sql recalculated on the in-memory copy; WARN/SKIP remain non-blocking",
    )


def gate_p8_02(ctx: VerificationContext) -> GateEvidence:
    _ensure_analysis(ctx)
    assert ctx.sql_facts is not None and ctx.crosscheck is not None
    return validate_rank_gate(ctx.sql_facts, ctx.crosscheck)


def gate_p8_03(ctx: VerificationContext) -> GateEvidence:
    _ensure_analysis(ctx)
    assert ctx.sql_facts is not None and ctx.crosscheck is not None
    return validate_yoy_gate(ctx.sql_facts, ctx.crosscheck)


def gate_p8_04(ctx: VerificationContext) -> GateEvidence:
    _ensure_analysis(ctx)
    assert ctx.sql_facts is not None and ctx.crosscheck is not None
    return validate_entry_gate(ctx.sql_facts, ctx.crosscheck, ctx.sql03_text)


def gate_p8_05(ctx: VerificationContext) -> GateEvidence:
    _ensure_analysis(ctx)
    assert ctx.sql_facts is not None and ctx.crosscheck is not None
    return validate_window_gate(ctx.sql_facts, ctx.crosscheck, ctx.sql03_text)


def gate_p8_06(ctx: VerificationContext) -> GateEvidence:
    _ensure_analysis(ctx)
    assert ctx.sql_facts is not None and ctx.crosscheck is not None
    return validate_rank_change_gate(ctx.sql_facts, ctx.crosscheck)


def gate_p8_07(ctx: VerificationContext) -> GateEvidence:
    _ensure_analysis(ctx)
    assert ctx.sql_facts is not None and ctx.crosscheck is not None
    return validate_concentration_gate(ctx.sql_facts, ctx.crosscheck)


def _canonical_frame_hash(frame: pd.DataFrame, key_columns: Sequence[str]) -> str:
    ordered = frame.sort_values(list(key_columns), kind="mergesort").reset_index(drop=True)
    digest = hashlib.sha256()
    digest.update("\x1e".join(ordered.columns).encode("utf-8"))
    for row in ordered.itertuples(index=False, name=None):
        fields: list[str] = []
        for value in row:
            if value is None or pd.isna(value):
                fields.append("<NULL>")
            elif isinstance(value, (float, np.floating)):
                fields.append(format(float(value), ".17g"))
            else:
                fields.append(str(value))
        digest.update(("\x1f".join(fields) + "\n").encode("utf-8"))
    return digest.hexdigest()


def _independent_analysis(sql_text: str, fingerprint: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = _open_readonly_memory()
    try:
        sql_facts = _run_sql_analysis(conn, sql_text)
        python_facts, module = _build_python_facts(conn, fingerprint)
        cross = module.crosscheck(python_facts, sql_facts, fingerprint)
        return sql_facts, cross
    finally:
        conn.close()


def gate_p8_08(ctx: VerificationContext) -> GateEvidence:
    normal_sql = _normalise_sql(ctx.sql03_text)
    forbidden_python_table = bool(re.search(r"\b(?:from|join)\s+(?:main\.)?fact_metrics\b", normal_sql))
    run1, cross1 = _independent_analysis(ctx.sql03_text, ctx.fingerprint)
    run2, cross2 = _independent_analysis(ctx.sql03_text, ctx.fingerprint)
    module = _load_phase3_module()
    key_columns = tuple(module.FACT_KEY)
    hash1 = _canonical_frame_hash(run1, key_columns)
    hash2 = _canonical_frame_hash(run2, key_columns)
    question1 = {key: int(value) for key, value in run1.groupby("question_id").size().to_dict().items()}
    question2 = {key: int(value) for key, value in run2.groupby("question_id").size().to_dict().items()}
    validations = _load_csv(PHASE3_VALIDATION_PATH)
    validation_ids = set(validations.validation_id.astype(str)) if "validation_id" in validations else set()
    validation_ok = bool(
        len(validations) == EXPECTED_PHASE3_VALIDATION_ROWS
        and "status" in validations
        and validations.status.eq("PASS").all()
        and validation_ids == set(EXPECTED_PHASE3_VALIDATION_IDS)
    )
    current_protected = _snapshot_protected()
    changed = sorted(
        set(ctx.protected_before) ^ set(current_protected)
        | {path for path in set(ctx.protected_before) & set(current_protected) if ctx.protected_before[path] != current_protected[path]}
    )
    audit = GateAudit()
    audit.check("NO_FACT_METRICS_INPUT", not forbidden_python_table, "03_analysis.sql does not read fact_metrics", forbidden_python_table)
    audit.check("RUN1_ROWS", len(run1) == EXPECTED_PHASE3_FACT_ROWS, EXPECTED_PHASE3_FACT_ROWS, len(run1))
    audit.check("RUN2_ROWS", len(run2) == EXPECTED_PHASE3_FACT_ROWS, EXPECTED_PHASE3_FACT_ROWS, len(run2))
    audit.check("RUN1_QUESTION_ROWS", question1 == EXPECTED_PHASE3_QUESTION_ROWS, EXPECTED_PHASE3_QUESTION_ROWS, question1)
    audit.check("RUN2_QUESTION_ROWS", question2 == EXPECTED_PHASE3_QUESTION_ROWS, EXPECTED_PHASE3_QUESTION_ROWS, question2)
    audit.check("RUN1_CROSSCHECK", len(cross1) == EXPECTED_PHASE3_CROSSCHECK_ROWS and cross1.status.eq("PASS").all(), f"{EXPECTED_PHASE3_CROSSCHECK_ROWS}/{EXPECTED_PHASE3_CROSSCHECK_ROWS}", f"{int(cross1.status.eq('PASS').sum())}/{len(cross1)}")
    audit.check("RUN2_CROSSCHECK", len(cross2) == EXPECTED_PHASE3_CROSSCHECK_ROWS and cross2.status.eq("PASS").all(), f"{EXPECTED_PHASE3_CROSSCHECK_ROWS}/{EXPECTED_PHASE3_CROSSCHECK_ROWS}", f"{int(cross2.status.eq('PASS').sum())}/{len(cross2)}")
    audit.check("PHASE3_VALIDATIONS", validation_ok, "92/92 exact IDs PASS", {"rows": len(validations), "pass": int(validations.status.eq("PASS").sum()) if "status" in validations else 0})
    audit.check("DETERMINISTIC_HASH", hash1 == hash2, hash1, hash2)
    audit.check("SOURCE_IMMUTABILITY", not changed, "no Phase 1-5 product changed", changed)
    return audit.finish(
        {"rows_each": EXPECTED_PHASE3_FACT_ROWS, "question_rows": EXPECTED_PHASE3_QUESTION_ROWS, "crosschecks_each": EXPECTED_PHASE3_CROSSCHECK_ROWS, "validations": EXPECTED_PHASE3_VALIDATION_ROWS, "same_hash": True},
        {"rows": [len(run1), len(run2)], "crosschecks": [len(cross1), len(cross2)], "hashes": [hash1, hash2], "changed_files": changed},
        "two fresh in-memory copies independently reproduce the complete SQL surface",
    )


GATE_FUNCTIONS: dict[str, Callable[[VerificationContext], GateEvidence]] = {
    "P8-00": gate_p8_00,
    "P8-01": gate_p8_01,
    "P8-02": gate_p8_02,
    "P8-03": gate_p8_03,
    "P8-04": gate_p8_04,
    "P8-05": gate_p8_05,
    "P8-06": gate_p8_06,
    "P8-07": gate_p8_07,
    "P8-08": gate_p8_08,
}


def _result_row(gate_id: str, status: str, evidence: GateEvidence | GateFailure, fingerprint: str) -> dict[str, str]:
    return {
        "gate_id": gate_id,
        "step_name": GATE_STEP_NAMES[gate_id],
        "status": status,
        "expected": _encode(evidence.expected),
        "observed": _encode(evidence.observed),
        "details": _encode(evidence.details),
        "method_version": METHOD_VERSION,
        "phase2_input_fingerprint": fingerprint,
    }


def _final_gate(rows: list[dict[str, str]], fingerprint: str) -> GateEvidence:
    observed_ids = tuple(row["gate_id"] for row in rows)
    statuses = tuple(row["status"] for row in rows)
    versions = {row["method_version"] for row in rows}
    fingerprints = {row["phase2_input_fingerprint"] for row in rows}
    audit = GateAudit()
    audit.check("ORDERED_GATES", observed_ids == GATE_IDS, GATE_IDS, observed_ids)
    audit.check("ALL_PASS", statuses == tuple("PASS" for _ in GATE_IDS), "all PASS", statuses)
    audit.check("METHOD_VERSION", versions == {METHOD_VERSION}, [METHOD_VERSION], sorted(versions))
    audit.check("FINGERPRINT", fingerprints == {EXPECTED_PHASE2_INPUT_FINGERPRINT} == {fingerprint}, [EXPECTED_PHASE2_INPUT_FINGERPRINT], sorted(fingerprints))
    return audit.finish("P8-00..P8-08 all PASS with one contract and fingerprint", "DAT", "Phase 8 acceptance decision")


def _publish_atomically(rows: list[dict[str, str]], output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{output_path.stem}_",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=VALIDATION_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def run_verification(
    through: str,
    *,
    final: bool = False,
    db_path: Path = DB_PATH,
    sql02_path: Path = SQL02_PATH,
    sql03_path: Path = SQL03_PATH,
    output_path: Path = OUTPUT_PATH,
    publish: bool = True,
) -> tuple[pd.DataFrame, bool]:
    """Run gates from P8-00 through the target and optionally P8-FINAL.

    This is the testable API.  A failed gate is included as the final row and
    no later gate executes.  ``publish=False`` keeps the run fully read-only.
    """
    if through not in GATE_IDS:
        raise ValueError(f"through must be one of {GATE_IDS}, found {through!r}")
    if final and through != GATE_IDS[-1]:
        raise ValueError("final verification must run through P8-08")
    rows: list[dict[str, str]] = []
    ctx: VerificationContext | None = None
    try:
        sql02_text = sql02_path.read_text(encoding="utf-8")
        sql03_text = sql03_path.read_text(encoding="utf-8")
        ctx = VerificationContext(
            conn=_open_readonly_memory(db_path),
            sql02_text=sql02_text,
            sql03_text=sql03_text,
            protected_before=_snapshot_protected(),
        )
        target_index = GATE_IDS.index(through)
        for gate_id in GATE_IDS[: target_index + 1]:
            try:
                evidence = GATE_FUNCTIONS[gate_id](ctx)
            except GateFailure as exc:
                rows.append(_result_row(gate_id, "FAIL", exc, ctx.fingerprint))
                break
            except (AssertionError, KeyError, ValueError, TypeError, OSError, sqlite3.Error, pd.errors.DatabaseError) as exc:
                failure = GateFailure("gate completes without exception", type(exc).__name__, str(exc))
                rows.append(_result_row(gate_id, "FAIL", failure, ctx.fingerprint))
                break
            rows.append(_result_row(gate_id, "PASS", evidence, ctx.fingerprint))
        if final and len(rows) == len(GATE_IDS) and all(row["status"] == "PASS" for row in rows):
            try:
                evidence = _final_gate(rows, ctx.fingerprint)
            except GateFailure as exc:
                rows.append(_result_row(FINAL_GATE_ID, "FAIL", exc, ctx.fingerprint))
            else:
                rows.append(_result_row(FINAL_GATE_ID, "PASS", evidence, ctx.fingerprint))
    except (OSError, sqlite3.Error, Phase8Error, UnicodeError) as exc:
        if not rows:
            failure = GateFailure("readable locked Phase 8 inputs", type(exc).__name__, str(exc))
            rows.append(_result_row("P8-00", "FAIL", failure, "UNAVAILABLE"))
    finally:
        if ctx is not None:
            ctx.close()
    success = bool(rows) and all(row["status"] == "PASS" for row in rows)
    expected_last = FINAL_GATE_ID if final else through
    success = success and rows[-1]["gate_id"] == expected_last
    if publish:
        _publish_atomically(rows, output_path)
    return pd.DataFrame(rows, columns=VALIDATION_COLUMNS), success


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the sequential Phase 8 SQL acceptance gates on an isolated in-memory database.",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--through", choices=GATE_IDS, help="Run P8-00 through this gate, stopping at the first failure.")
    target.add_argument("--final", action="store_true", help="Run P8-00..P8-08 and the final Phase 8 decision gate.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    through = GATE_IDS[-1] if args.final else args.through
    rows, success = run_verification(through, final=bool(args.final))
    last = rows.iloc[-1]
    print(
        f"PHASE 8: {last.status} | through={last.gate_id} | "
        f"gates={len(rows)} | fingerprint={last.phase2_input_fingerprint[:12]}"
    )
    if not success:
        print(f"FAILED GATE: {last.gate_id} | {last.details}", file=sys.stderr)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
