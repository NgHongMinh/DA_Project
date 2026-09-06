"""Build, cross-check, validate, and publish all Phase 3 products.

Python and SQL calculate the complete analytical surface independently from
the Phase 2 SQLite model. Workbooks are projections of the checked fact table.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from config import DB_PATH, OUTPUT, SQL_DIR, STATS  # noqa: E402
from phase2_contract import (  # noqa: E402
    EXPECTED_VALIDATION_ROWS,
    Phase2ContractError,
    validate_phase2_gate,
)
from phase3_contract import (  # noqa: E402
    EXPECTED_CROSSCHECK_ROWS,
    EXPECTED_FACT_ROWS,
    EXPECTED_PHASE3_VALIDATION_IDS,
    EXPECTED_QUESTION_ROWS,
    PHASE3_WORKBOOKS,
    RATIO_NUMBER_FORMAT,
    workbook_number_format_errors,
)

VERSION = "phase3_v1"
YEARS = list(range(2000, 2022))
MILESTONES = [2000, 2010, 2021]
PERIODS = [(2000, 2010), (2010, 2021), (2000, 2021)]
GEN = {
    "HYDRO": "hydro_generation_twh",
    "WIND": "wind_generation_twh",
    "SOLAR": "solar_generation_twh",
    "OTHER_RENEWABLES": "other_renewables_generation_twh",
}
PCT = {
    "RENEWABLE_TOTAL": "renewables_share_electricity_pct",
    "HYDRO": "hydro_share_electricity_pct",
    "WIND": "wind_share_electricity_pct",
    "SOLAR": "solar_share_electricity_pct",
}
SIX = [*GEN, "RENEWABLE_TOTAL", "MODERN_WIND_SOLAR"]
FOURS = list(GEN)
PAIR_SERIES = ["RENEWABLE_TOTAL", "MODERN_WIND_SOLAR", "HYDRO", "WIND", "SOLAR"]
PAIR_KEYS = {
    "RENEWABLE_TOTAL": "RENEWABLE_TOTAL_VS_RENEWABLE_SHARE",
    "MODERN_WIND_SOLAR": "MODERN_VS_WIND_SOLAR_SHARE",
    "HYDRO": "HYDRO_VS_HYDRO_SHARE",
    "WIND": "WIND_VS_WIND_SHARE",
    "SOLAR": "SOLAR_VS_SOLAR_SHARE",
}
WORKBOOK_SCOPES = {
    "03_global_cross_section.xlsx": "GLOBAL_CURRENT_COUNTRIES milestone distribution",
    "03_asean_cross_section.xlsx": "ASEAN_10 annual and milestone analysis",
    "03_vietnam_time_series.xlsx": "Vietnam with ASEAN_9, ASEAN_10, and global benchmarks",
    "03_ranking_comparison.xlsx": "ASEAN_10 rankings and CAGR eligibility",
    "03_entry_lag.xlsx": "ASEAN_10 technology-entry status",
    "03_global_context.xlsx": "ASEAN_10 and WORLD_REPORTED context and Q6 evidence",
}
FACT_KEY = [
    "subject_type", "subject_key", "period_type", "period_key", "series_key",
    "metric_name", "comparison_scope", "filter_variant", "method_version",
]
FACT_COLUMNS = FACT_KEY + [
    "question_id", "period_start_year", "period_end_year", "metric_value",
    "metric_text_value", "unit", "value_status", "exclusion_reason",
    "population_n", "observed_n", "missing_n", "included_n", "zero_n",
    "trace_n", "material_n", "ranked_n", "component_count",
    "required_component_count", "denominator_basis", "threshold_value",
    "source_metric_keys", "phase2_input_fingerprint",
]
EXACT_CROSSCHECK_COLUMNS = [
    "question_id", "period_start_year", "period_end_year", "metric_text_value",
    "unit", "value_status", "exclusion_reason", "population_n", "observed_n",
    "missing_n", "included_n", "zero_n", "trace_n", "material_n", "ranked_n",
    "component_count", "required_component_count", "denominator_basis",
    "threshold_value", "source_metric_keys",
]
WORKBOOKS = PHASE3_WORKBOOKS


class Phase3Error(RuntimeError):
    pass


def stable_json(values: Iterable[str]) -> str:
    return json.dumps(sorted(set(values)), ensure_ascii=False, separators=(",", ":"))


def generation_sources(series: str) -> list[str]:
    if series in GEN:
        return [GEN[series]]
    if series == "MODERN_WIND_SOLAR":
        return [GEN["WIND"], GEN["SOLAR"]]
    return list(GEN.values())


def percentage_sources(series: str) -> list[str]:
    if series == "MODERN_WIND_SOLAR":
        return [PCT["WIND"], PCT["SOLAR"]]
    return [PCT[series]]


def q5_pair_mapping() -> dict[str, dict[str, Any]]:
    return {
        PAIR_KEYS[series]: {
            "series_key": series,
            "twh_metric_name": "generation_twh",
            "twh_source_metric_keys": generation_sources(series),
            "pct_metric_name": "share_electricity_pct",
            "pct_source_metric_keys": percentage_sources(series),
        }
        for series in PAIR_SERIES
    }


def load_input(conn: sqlite3.Connection) -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    entities = pd.read_sql_query("SELECT * FROM dim_entity", conn)
    fact = pd.read_sql_query(
        "SELECT entity,year,metric_key,value,value_class FROM fact_energy "
        "WHERE year BETWEEN 2000 AND 2021", conn,
    )
    current = entities.loc[entities.is_current_country_or_territory.eq(1), "entity"].tolist()
    asean = entities.loc[entities.is_asean.eq(1), "entity"].tolist()
    if len(current) != 215 or len(asean) != 10:
        raise Phase3Error("Phase 2 entity baseline changed")
    main = set(GEN.values()) | set(PCT.values())
    observed = len(fact[fact.entity.isin(asean) & fact.metric_key.isin(main)])
    if observed != 1760:
        raise Phase3Error(f"ASEAN main panel must be 1,760/1,760, found {observed}")
    return entities, fact, current, asean


def make_panel(fact: pd.DataFrame, entities: list[str]) -> pd.DataFrame:
    index = pd.MultiIndex.from_product([entities, YEARS], names=["entity", "year"])
    wanted = set(GEN.values()) | set(PCT.values())
    subset = fact[fact.entity.isin(entities) & fact.metric_key.isin(wanted)]
    values = subset.pivot(index=["entity", "year"], columns="metric_key", values="value").reindex(index).reset_index()
    classes = subset[subset.metric_key.isin(GEN.values())].pivot(
        index=["entity", "year"], columns="metric_key", values="value_class"
    ).reindex(index).reset_index()
    for series, metric_key in GEN.items():
        values[series] = values[metric_key]
        values[f"{series}_class"] = classes[metric_key]
    for series, metric_key in PCT.items():
        values[f"{series}_PCT"] = values[metric_key]
    values["RENEWABLE_TOTAL"] = values[FOURS].sum(axis=1, min_count=4)
    values["RENEWABLE_TOTAL_components"] = values[FOURS].notna().sum(axis=1)
    values["MODERN_WIND_SOLAR"] = values[["WIND", "SOLAR"]].sum(axis=1, min_count=2)
    values["MODERN_WIND_SOLAR_components"] = values[["WIND", "SOLAR"]].notna().sum(axis=1)
    values["MODERN_WIND_SOLAR_PCT"] = values[["WIND_PCT", "SOLAR_PCT"]].sum(axis=1, min_count=2)
    return values


def component_info(row: pd.Series, series: str) -> tuple[int, int, list[str]]:
    if series in GEN:
        return int(pd.notna(row[series])), 1, [GEN[series]]
    if series == "RENEWABLE_TOTAL":
        return int(row["RENEWABLE_TOTAL_components"]), 4, list(GEN.values())
    return int(row["MODERN_WIND_SOLAR_components"]), 2, [GEN["WIND"], GEN["SOLAR"]]


class FactBuilder:
    def __init__(self, input_fingerprint: str):
        self.input_fingerprint = input_fingerprint
        self.rows: list[dict[str, Any]] = []

    def add(
        self, subject_type: str, subject_key: str, period_type: str,
        start_year: int, end_year: int, series_key: str, metric_name: str,
        question_id: str, *, value: Any = None, text: str | None = None,
        comparison_scope: str = "NONE", filter_variant: str = "NOT_APPLICABLE",
        unit: str = "TWh", status: str | None = None, reason: str | None = None,
        population_n: Any = None, observed_n: Any = None, missing_n: Any = None,
        included_n: Any = None, zero_n: Any = None, trace_n: Any = None,
        material_n: Any = None, ranked_n: Any = None, component_count: Any = None,
        required_component_count: Any = None, denominator_basis: str = "NONE",
        threshold_value: Any = None, sources: Iterable[str] = (),
    ) -> None:
        period_key = f"Y{start_year}" if period_type == "YEAR" else (
            f"I{start_year}_{end_year}" if period_type == "INTERVAL" else f"W{start_year}_{end_year}"
        )
        numeric = None if value is None or pd.isna(value) else float(value)
        if text is not None:
            status, reason, numeric = status or "CALCULATED_TEXT", reason or "NON_NUMERIC_RESULT", None
        elif status is None:
            if numeric is not None and math.isfinite(numeric):
                status, reason = "CALCULATED", "NONE"
            else:
                status, reason, numeric = "NOT_DEFINED", reason or "NOT_DEFINED", None
        elif status != "CALCULATED":
            numeric = None
        if status == "CALCULATED":
            reason = "NONE"
        elif reason in (None, "NONE"):
            raise Phase3Error(f"Missing exclusion reason for {metric_name}/{status}")
        self.rows.append({
            "subject_type": subject_type, "subject_key": subject_key,
            "period_type": period_type, "period_key": period_key,
            "series_key": series_key, "metric_name": metric_name,
            "comparison_scope": comparison_scope, "filter_variant": filter_variant,
            "method_version": VERSION, "question_id": question_id,
            "period_start_year": int(start_year), "period_end_year": int(end_year),
            "metric_value": numeric, "metric_text_value": text, "unit": unit,
            "value_status": status, "exclusion_reason": reason,
            "population_n": population_n, "observed_n": observed_n,
            "missing_n": missing_n, "included_n": included_n, "zero_n": zero_n,
            "trace_n": trace_n, "material_n": material_n, "ranked_n": ranked_n,
            "component_count": component_count,
            "required_component_count": required_component_count,
            "denominator_basis": denominator_basis, "threshold_value": threshold_value,
            "source_metric_keys": stable_json(sources),
            "phase2_input_fingerprint": self.input_fingerprint,
        })

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=FACT_COLUMNS).sort_values(FACT_KEY, kind="mergesort").reset_index(drop=True)


def add_distribution(builder: FactBuilder, fact: pd.DataFrame, entities: list[str], scope: str) -> None:
    for year in MILESTONES:
        for series, metric_key in GEN.items():
            base = fact[fact.entity.isin(entities) & fact.year.eq(year) & fact.metric_key.eq(metric_key)]
            observed_values, classes = base.value.astype(float), base.value_class
            counts = {
                "population_n": len(entities), "observed_n": len(base),
                "missing_n": len(entities) - len(base), "zero_n": int(observed_values.eq(0).sum()),
                "trace_n": int(classes.eq("Trace").sum()), "material_n": int(classes.eq("Material").sum()),
            }
            for variant in ["ALL_OBSERVED", "POSITIVE", "MATERIAL"]:
                values = observed_values if variant == "ALL_OBSERVED" else (
                    observed_values[observed_values.gt(0)] if variant == "POSITIVE" else observed_values[classes.eq("Material")]
                )
                array, n = values.to_numpy(float), len(values)
                mean = float(array.mean()) if n else None
                sd = float(array.std(ddof=0)) if n else None
                metrics: dict[str, Any] = {
                    "n": n, "sum": float(array.sum()) if n else None,
                    "mean": mean, "median": float(np.median(array)) if n else None,
                    "sd": sd, "cv": sd / mean if n >= 2 and mean and mean > 0 else None,
                    "min": float(array.min()) if n else None, "max": float(array.max()) if n else None,
                }
                for quantile in [10, 25, 50, 75, 90, 95, 99]:
                    metrics[f"p{quantile}"] = float(np.percentile(array, quantile, method="linear")) if n else None
                metrics["iqr"] = metrics["p75"] - metrics["p25"] if n else None
                metrics["skewness"] = float(skew(array, bias=False)) if n >= 3 and sd and sd > 0 else None
                metrics["kurtosis"] = float(kurtosis(array, fisher=True, bias=False)) if n >= 4 and sd and sd > 0 else None
                for metric_name, value in metrics.items():
                    status = reason = None
                    if value is None:
                        if n == 0:
                            status, reason = "NOT_DEFINED", "EMPTY_GROUP"
                        elif metric_name == "cv" and n >= 2 and mean == 0:
                            status, reason = "NOT_DEFINED", "ZERO_MEAN"
                        elif metric_name in ("cv", "skewness", "kurtosis"):
                            status = "INSUFFICIENT_N"
                            reason = "CONSTANT_GROUP" if sd == 0 and metric_name in ("skewness", "kurtosis") else "INSUFFICIENT_N"
                    builder.add(
                        "STATISTICAL_SCOPE", scope, "YEAR", year, year, series, metric_name, "Q1",
                        value=value, comparison_scope=scope, filter_variant=variant,
                        unit="count" if metric_name == "n" else "ratio" if metric_name in ("cv", "skewness", "kurtosis") else "TWh",
                        status=status, reason=reason, included_n=n, sources=[metric_key], **counts,
                        threshold_value=0.05 if variant == "MATERIAL" else None,
                    )
                for metric_name, value, denominator in [
                    ("zero_share_population", counts["zero_n"] / counts["population_n"], "POPULATION"),
                    ("zero_share_observed", counts["zero_n"] / counts["observed_n"] if counts["observed_n"] else None, "OBSERVED"),
                ]:
                    builder.add(
                        "STATISTICAL_SCOPE", scope, "YEAR", year, year, series, metric_name, "Q1",
                        value=value, comparison_scope=scope, filter_variant=variant, unit="ratio",
                        status="NOT_DEFINED" if value is None else None,
                        reason="ZERO_DENOMINATOR" if value is None else None,
                        included_n=n, denominator_basis=denominator, sources=[metric_key], **counts,
                        threshold_value=0.05 if variant == "MATERIAL" else None,
                    )


def add_levels(builder: FactBuilder, ap: pd.DataFrame, cp: pd.DataFrame, wp: pd.DataFrame) -> None:
    for _, row in ap.iterrows():
        for series in SIX:
            count, required, sources = component_info(row, series)
            value = row[series]
            builder.add(
                "COUNTRY", row.entity, "YEAR", row.year, row.year, series, "generation_twh", "Q2",
                value=value, comparison_scope="ASEAN_10",
                status="NOT_OBSERVED" if pd.isna(value) else None,
                reason="INCOMPLETE_COMPONENTS" if pd.isna(value) else None,
                population_n=10, observed_n=int(pd.notna(value)), missing_n=int(pd.isna(value)),
                included_n=int(pd.notna(value)), component_count=count,
                required_component_count=required, sources=sources,
            )
        for series in PAIR_SERIES:
            source = [PCT[series]] if series != "MODERN_WIND_SOLAR" else [PCT["WIND"], PCT["SOLAR"]]
            keys = [series] if series != "MODERN_WIND_SOLAR" else ["WIND", "SOLAR"]
            count, value = sum(pd.notna(row[f"{key}_PCT"]) for key in keys), row[f"{series}_PCT"]
            builder.add(
                "COUNTRY", row.entity, "YEAR", row.year, row.year, series, "share_electricity_pct", "Q5",
                value=value, comparison_scope="ASEAN_10", unit="pct",
                status="NOT_OBSERVED" if pd.isna(value) else None,
                reason="INCOMPLETE_COMPONENTS" if pd.isna(value) else None,
                population_n=10, observed_n=int(pd.notna(value)), missing_n=int(pd.isna(value)),
                included_n=int(pd.notna(value)), component_count=count,
                required_component_count=len(source), sources=source,
            )
    for _, row in cp[cp.year.isin(MILESTONES)].iterrows():
        for series in FOURS:
            value = row[series]
            builder.add(
                "COUNTRY", row.entity, "YEAR", row.year, row.year, series, "generation_twh", "Q1",
                value=value, comparison_scope="GLOBAL_CURRENT_COUNTRIES",
                status="NOT_OBSERVED" if pd.isna(value) else None,
                reason="NOT_OBSERVED" if pd.isna(value) else None,
                component_count=int(pd.notna(value)), required_component_count=1, sources=[GEN[series]],
            )
    for subject_type, subject_key, panel, scope in [
        ("REGION", "ASEAN_10", ap, "ASEAN_10"),
        ("WORLD", "WORLD_REPORTED", wp, "WORLD_REPORTED"),
    ]:
        for year, group in panel.groupby("year"):
            row = group.iloc[0] if subject_type == "WORLD" else None
            for series in SIX:
                if subject_type == "WORLD":
                    value = row[series]
                    count, required, sources = component_info(row, series)
                    observed_n, population_n = int(pd.notna(value)), 1
                else:
                    values = group[series]
                    value = float(values.sum()) if values.notna().all() else None
                    per_entity_required = 1 if series in GEN else 4 if series == "RENEWABLE_TOTAL" else 2
                    if series in GEN:
                        count = int(values.notna().sum())
                    else:
                        count = int(group[f"{series}_components"].sum())
                    required = 10 * per_entity_required
                    observed_n, population_n = int(values.notna().sum()), 10
                    sources = [GEN[series]] if series in GEN else (list(GEN.values()) if series == "RENEWABLE_TOTAL" else [GEN["WIND"], GEN["SOLAR"]])
                builder.add(
                    subject_type, subject_key, "YEAR", year, year, series, "generation_twh", "Q1",
                    value=value, comparison_scope=scope,
                    status="NOT_OBSERVED" if value is None or pd.isna(value) else None,
                    reason="INCOMPLETE_COMPONENTS" if value is None or pd.isna(value) else None,
                    population_n=population_n, observed_n=observed_n,
                    missing_n=population_n-observed_n, included_n=observed_n,
                    component_count=count, required_component_count=required,
                    denominator_basis="ASEAN_SUM_10" if subject_type == "REGION" else "NONE", sources=sources,
                )
    for year, group in cp.groupby("year"):
        for series in SIX:
            component_series = [series] if series in GEN else FOURS if series == "RENEWABLE_TOTAL" else ["WIND", "SOLAR"]
            component_values = group[component_series]
            value = float(component_values.sum(axis=0, min_count=1).sum(min_count=1)) if component_values.notna().any().any() else None
            observed_count = int(component_values.notna().sum().sum())
            population_count = 215 * len(component_series)
            builder.add(
                "STATISTICAL_SCOPE", "GLOBAL_CURRENT_COUNTRIES", "YEAR", year, year,
                series, "current_country_sum_twh", "Q1", value=value,
                comparison_scope="WORLD_REPORTED", population_n=population_count,
                observed_n=observed_count, missing_n=population_count-observed_count,
                included_n=observed_count, denominator_basis="CURRENT_COUNTRY_SUM_AUDIT",
                sources=generation_sources(series),
            )


def add_shares(builder: FactBuilder, ap: pd.DataFrame, wp: pd.DataFrame) -> None:
    for year, group in ap.groupby("year"):
        totals = {series: float(group[series].sum()) for series in SIX}
        for _, row in group.iterrows():
            for series in SIX:
                denominator = totals[series]
                value = row[series] / denominator if denominator > 0 else None
                builder.add(
                    "COUNTRY", row.entity, "YEAR", year, year, series, "country_share_asean", "Q2",
                    value=value, comparison_scope="ASEAN_10", unit="ratio",
                    status="NOT_DEFINED" if value is None else None,
                    reason="ZERO_DENOMINATOR" if value is None else None,
                    population_n=10, observed_n=10, included_n=10,
                    denominator_basis="ASEAN_SUM_10",
                    sources=generation_sources(series),
                )
            renewable_total = row["RENEWABLE_TOTAL"]
            for series in FOURS:
                value = row[series] / renewable_total if renewable_total > 0 else None
                builder.add(
                    "COUNTRY", row.entity, "YEAR", year, year, series, "technology_share", "Q2",
                    value=value, comparison_scope="ASEAN_10", unit="ratio",
                    status="NOT_DEFINED" if value is None else None,
                    reason="ZERO_DENOMINATOR" if value is None else None,
                    denominator_basis="TOTAL_RENEWABLE_GENERATION", component_count=4,
                    required_component_count=4, sources=list(GEN.values()),
                )
        asean_total = totals["RENEWABLE_TOTAL"]
        for series in FOURS:
            value = totals[series] / asean_total if asean_total > 0 else None
            builder.add(
                "REGION", "ASEAN_10", "YEAR", year, year, series, "technology_share", "Q2",
                value=value, comparison_scope="ASEAN_10", unit="ratio",
                status="NOT_DEFINED" if value is None else None,
                reason="ZERO_DENOMINATOR" if value is None else None,
                denominator_basis="TOTAL_RENEWABLE_GENERATION", component_count=40,
                required_component_count=40, sources=list(GEN.values()),
            )
        world_row = wp[wp.year.eq(year)].iloc[0]
        for series in SIX:
            denominator = world_row[series]
            value = totals[series] / denominator if pd.notna(denominator) and denominator > 0 else None
            builder.add(
                "REGION", "ASEAN_10", "YEAR", year, year, series, "asean_share_world", "Q1",
                value=value, comparison_scope="WORLD_REPORTED", unit="ratio",
                status="NOT_DEFINED" if value is None else None,
                reason="ZERO_DENOMINATOR" if value is None else None,
                denominator_basis="REPORTED_WORLD",
                sources=generation_sources(series),
            )


def sequence_status(current: Any, previous: Any) -> tuple[Any, str | None, str | None]:
    if pd.isna(current):
        return None, "NOT_OBSERVED", "MISSING_CURRENT"
    if pd.isna(previous):
        return None, "NOT_DEFINED", "MISSING_PREVIOUS"
    if previous == 0:
        return None, "NOT_DEFINED", "ZERO_BASE"
    return current / previous - 1, None, None


def add_time_metrics(builder: FactBuilder, ap: pd.DataFrame, wp: pd.DataFrame) -> None:
    panels = [
        ("REGION", "ASEAN_10", ap.groupby("year")[SIX].sum(), "ASEAN_10", "Q1"),
        ("WORLD", "WORLD_REPORTED", wp.set_index("year")[SIX], "WORLD_REPORTED", "Q1"),
        ("COUNTRY", "Vietnam", ap[ap.entity.eq("Vietnam")].set_index("year")[SIX], "ASEAN_10", "Q4"),
    ]
    for subject_type, subject_key, indexed, scope, question in panels:
        indexed = indexed.reindex(YEARS)
        for series in SIX:
            sources = generation_sources(series)
            for position, year in enumerate(YEARS):
                current = indexed.loc[year, series]
                previous = indexed.loc[year - 1, series] if year > YEARS[0] else np.nan
                absolute = current - previous if pd.notna(current) and pd.notna(previous) else None
                builder.add(subject_type, subject_key, "YEAR", year, year, series, "annual_change_twh", question, value=absolute, comparison_scope=scope, status="NOT_DEFINED" if absolute is None else None, reason="MISSING_PREVIOUS" if absolute is None else None, sources=sources)
                yoy, status, reason = sequence_status(current, previous)
                builder.add(subject_type, subject_key, "YEAR", year, year, series, "yoy", question, value=yoy, comparison_scope=scope, unit="ratio", status=status, reason=reason, sources=sources)
                if subject_key in ("ASEAN_10", "Vietnam"):
                    prefix = indexed.loc[YEARS[0]:year, series]
                    cumulative = float(prefix.sum()) if prefix.notna().all() else None
                    builder.add(subject_type, subject_key, "YEAR", year, year, series, "cumulative_generation_twh", question, value=cumulative, comparison_scope=scope, status="NOT_OBSERVED" if cumulative is None else None, reason="INCOMPLETE_HISTORY" if cumulative is None else None, sources=sources)
                    window = indexed.loc[max(YEARS[0], year - 2):year, series]
                    rolling = float(window.mean()) if len(window) == 3 and window.notna().all() else None
                    window_reason = "INSUFFICIENT_WINDOW" if position < 2 else "INCOMPLETE_WINDOW"
                    builder.add(subject_type, subject_key, "YEAR", year, year, series, "rolling_mean_3y_twh", question, value=rolling, comparison_scope=scope, status="NOT_DEFINED" if rolling is None else None, reason=window_reason if rolling is None else None, sources=sources)
    for subject_type, subject_key, indexed, scope, _ in panels[:2]:
        for start, end in PERIODS:
            for series in SIX:
                start_value, end_value = indexed.loc[start, series], indexed.loc[end, series]
                delta = end_value - start_value if pd.notna(start_value) and pd.notna(end_value) else None
                cagr = (end_value / start_value) ** (1 / (end - start)) - 1 if pd.notna(start_value) and pd.notna(end_value) and start_value > 0 else None
                missing_reason = "MISSING_ENDPOINT" if pd.isna(start_value) or pd.isna(end_value) else "ZERO_BASE"
                sources = generation_sources(series)
                builder.add(subject_type, subject_key, "INTERVAL", start, end, series, "absolute_change_twh", "Q1", value=delta, comparison_scope=scope, status="NOT_DEFINED" if delta is None else None, reason="MISSING_ENDPOINT" if delta is None else None, sources=sources)
                builder.add(subject_type, subject_key, "INTERVAL", start, end, series, "cagr", "Q1", value=cagr, comparison_scope=scope, unit="ratio", status="NOT_DEFINED" if cagr is None else None, reason=missing_reason if cagr is None else None, sources=sources)


def direction(delta_twh: Any, delta_pct: Any) -> str | None:
    if pd.isna(delta_twh) or pd.isna(delta_pct):
        return None
    if abs(delta_twh) <= 1e-12 or abs(delta_pct) <= 1e-12:
        return "ONE_OR_BOTH_UNCHANGED"
    return "SAME_DIRECTION" if delta_twh * delta_pct > 0 else "OPPOSITE_DIRECTION"


def add_q5(builder: FactBuilder, ap: pd.DataFrame) -> None:
    for entity, group in ap.groupby("entity"):
        indexed = group.set_index("year").sort_index()
        for series in PAIR_SERIES:
            sources = generation_sources(series) + (
                [PCT[series]] if series != "MODERN_WIND_SOLAR" else [PCT["WIND"], PCT["SOLAR"]]
            )
            for year in YEARS:
                current_twh = indexed.loc[year, series]
                current_pct = indexed.loc[year, f"{series}_PCT"]
                previous_twh = indexed.loc[year - 1, series] if year > YEARS[0] else np.nan
                previous_pct = indexed.loc[year - 1, f"{series}_PCT"] if year > YEARS[0] else np.nan
                delta_twh = current_twh - previous_twh if pd.notna(current_twh) and pd.notna(previous_twh) else None
                delta_pct = current_pct - previous_pct if pd.notna(current_pct) and pd.notna(previous_pct) else None
                relation = direction(delta_twh, delta_pct)
                common = dict(comparison_scope="ASEAN_10", sources=sources)
                builder.add("COUNTRY", entity, "YEAR", year, year, series, "q5_twh_change", "Q5", value=delta_twh, status="NOT_DEFINED" if delta_twh is None else None, reason="MISSING_PREVIOUS" if delta_twh is None else None, **common)
                yoy, status, reason = sequence_status(current_twh, previous_twh)
                builder.add("COUNTRY", entity, "YEAR", year, year, series, "q5_yoy", "Q5", value=yoy, unit="ratio", status=status, reason=reason, **common)
                builder.add("COUNTRY", entity, "YEAR", year, year, series, "q5_pct_point_change", "Q5", value=delta_pct, unit="percentage_point", status="NOT_DEFINED" if delta_pct is None else None, reason="MISSING_PREVIOUS" if delta_pct is None else None, **common)
                builder.add("COUNTRY", entity, "YEAR", year, year, series, "direction_relation", "Q5", text=relation, unit="STATUS_CODE", status="NOT_DEFINED" if relation is None else None, reason="MISSING_PREVIOUS" if relation is None else None, **common)
            for start, end in PERIODS:
                delta_twh = indexed.loc[end, series] - indexed.loc[start, series]
                delta_pct = indexed.loc[end, f"{series}_PCT"] - indexed.loc[start, f"{series}_PCT"]
                relation = direction(delta_twh, delta_pct)
                common = dict(comparison_scope="ASEAN_10", sources=sources)
                builder.add("COUNTRY", entity, "INTERVAL", start, end, series, "q5_twh_change", "Q5", value=delta_twh, **common)
                builder.add("COUNTRY", entity, "INTERVAL", start, end, series, "q5_pct_point_change", "Q5", value=delta_pct, unit="percentage_point", **common)
                builder.add("COUNTRY", entity, "INTERVAL", start, end, series, "direction_relation", "Q5", text=relation, unit="STATUS_CODE", **common)


def rank_values(values: pd.Series) -> tuple[pd.Series, int, bool]:
    valid = values.dropna()
    total_zero = len(valid) > 0 and bool(np.isclose(valid.sum(), 0.0, atol=1e-12))
    ranks = values.rank(method="min", ascending=False) if not total_zero else pd.Series(np.nan, index=values.index)
    return ranks, len(valid), total_zero


def add_rankings(builder: FactBuilder, ap: pd.DataFrame, cp: pd.DataFrame) -> None:
    annual_rank_rows: list[dict[str, Any]] = []
    for year, group in ap.groupby("year"):
        indexed = group.set_index("entity")
        rank_map: dict[str, pd.Series] = {}
        for series in ["RENEWABLE_TOTAL", "MODERN_WIND_SOLAR"]:
            ranks, ranked_n, total_zero = rank_values(indexed[series])
            rank_map[series] = ranks
            for entity in indexed.index:
                value = ranks.loc[entity]
                builder.add(
                    "COUNTRY", entity, "YEAR", year, year, series, "asean_rank", "Q3",
                    value=value, comparison_scope="ASEAN_10", unit="rank",
                    status="NOT_DEFINED" if pd.isna(value) else None,
                    reason="ZERO_SCOPE_TOTAL" if total_zero else "NOT_OBSERVED" if pd.isna(value) else None,
                    population_n=10, ranked_n=ranked_n, sources=generation_sources(series),
                )
                annual_rank_rows.append({"entity": entity, "year": year, "series": series, "rank": value})
        for entity in indexed.index:
            total_rank = rank_map["RENEWABLE_TOTAL"].loc[entity]
            modern_rank = rank_map["MODERN_WIND_SOLAR"].loc[entity]
            gain = total_rank - modern_rank if pd.notna(total_rank) and pd.notna(modern_rank) else None
            builder.add(
                "COUNTRY", entity, "YEAR", year, year, "MODERN_WIND_SOLAR", "modern_rank_gain", "Q3",
                value=gain, comparison_scope="ASEAN_10", unit="rank_change",
                status="NOT_DEFINED" if gain is None else None,
                reason="RANK_NOT_DEFINED" if gain is None else None,
                population_n=10, ranked_n=10, sources=list(GEN.values()),
            )
    annual_ranks = pd.DataFrame(annual_rank_rows).set_index(["entity", "year", "series"])["rank"]
    for entity in sorted(ap.entity.unique()):
        for start, end in PERIODS:
            for series in ["RENEWABLE_TOTAL", "MODERN_WIND_SOLAR"]:
                start_rank = annual_ranks.loc[(entity, start, series)]
                end_rank = annual_ranks.loc[(entity, end, series)]
                value = start_rank - end_rank if pd.notna(start_rank) and pd.notna(end_rank) else None
                builder.add(
                    "COUNTRY", entity, "INTERVAL", start, end, series, "rank_gain_over_time", "Q3",
                    value=value, comparison_scope="ASEAN_10", unit="rank_change",
                    status="NOT_DEFINED" if value is None else None,
                    reason="RANK_NOT_DEFINED" if value is None else None,
                    population_n=10, ranked_n=10, sources=generation_sources(series),
                )
    for start, end in PERIODS:
        for series in SIX:
            start_values = ap[ap.year.eq(start)].set_index("entity")[series]
            end_values = ap[ap.year.eq(end)].set_index("entity")[series]
            raw = pd.Series(index=start_values.index, dtype=float)
            eligible_raw = start_values.gt(0)
            raw.loc[eligible_raw] = (end_values.loc[eligible_raw] / start_values.loc[eligible_raw]) ** (1 / (end - start)) - 1
            sources = generation_sources(series)
            for entity in start_values.index:
                value = raw.loc[entity]
                builder.add(
                    "COUNTRY", entity, "INTERVAL", start, end, series, "country_cagr", "Q3",
                    value=value, comparison_scope="ASEAN_10", unit="ratio",
                    status="NOT_DEFINED" if pd.isna(value) else None,
                    reason="ZERO_BASE" if pd.isna(value) else None, sources=sources,
                )
            for variant, floor in [("CAGR_FLOOR_0_05", 0.05), ("CAGR_FLOOR_0_1", 0.1), ("CAGR_FLOOR_1_0", 1.0)]:
                eligible = start_values.ge(floor) & raw.notna()
                ranked_n = int(eligible.sum())
                ranks = raw.where(eligible).rank(method="min", ascending=False) if ranked_n >= 3 else pd.Series(np.nan, index=raw.index)
                for entity in start_values.index:
                    cagr_value = raw.loc[entity] if eligible.loc[entity] else None
                    builder.add(
                        "COUNTRY", entity, "INTERVAL", start, end, series, "country_cagr", "Q3",
                        value=cagr_value, comparison_scope="ASEAN_10", filter_variant=variant, unit="ratio",
                        status="NOT_DEFINED" if cagr_value is None or pd.isna(cagr_value) else None,
                        reason="BELOW_START_FLOOR" if not eligible.loc[entity] else None,
                        ranked_n=ranked_n, threshold_value=floor, sources=sources,
                    )
                    rank_value = ranks.loc[entity]
                    if pd.isna(rank_value):
                        rank_status = "INSUFFICIENT_N" if eligible.loc[entity] and ranked_n < 3 else "NOT_DEFINED"
                        rank_reason = "INSUFFICIENT_ELIGIBLE_ENTITIES" if eligible.loc[entity] and ranked_n < 3 else "BELOW_START_FLOOR"
                    else:
                        rank_status = rank_reason = None
                    builder.add(
                        "COUNTRY", entity, "INTERVAL", start, end, series, "cagr_rank", "Q3",
                        value=rank_value, comparison_scope="ASEAN_10", filter_variant=variant, unit="rank",
                        status=rank_status, reason=rank_reason, ranked_n=ranked_n,
                        threshold_value=floor, sources=sources,
                    )
    for year, group in cp.groupby("year"):
        indexed = group.set_index("entity")
        for series in SIX:
            ranks, ranked_n, total_zero = rank_values(indexed[series])
            value = ranks.get("Vietnam", np.nan)
            builder.add(
                "COUNTRY", "Vietnam", "YEAR", year, year, series, "global_rank", "Q4",
                value=value, comparison_scope="GLOBAL_CURRENT_COUNTRIES", unit="rank",
                status="NOT_DEFINED" if pd.isna(value) else None,
                reason="ZERO_SCOPE_TOTAL" if total_zero else "NOT_OBSERVED" if pd.isna(value) else None,
                population_n=215, ranked_n=ranked_n, sources=generation_sources(series),
            )


def classify_entry(values: pd.Series, threshold: float) -> tuple[str, int | None, int | None, int | None]:
    if values.isna().any():
        return "UNKNOWN_INCOMPLETE_SERIES", None, None, None
    qualifying = values[values >= threshold] if threshold > 0 else values[values > 0]
    if qualifying.empty:
        return ("NOT_MATERIAL_BY_2021" if threshold > 0 else "NOT_OBSERVED_BY_2021"), None, None, 0
    first_year = int(qualifying.index[0])
    if first_year == YEARS[0]:
        return ("MATERIAL_AT_WINDOW_START" if threshold > 0 else "ACTIVE_AT_WINDOW_START"), first_year, None, 0
    return ("OBSERVED_MATERIAL_TRANSITION" if threshold > 0 else "OBSERVED_TRANSITION"), first_year, first_year, 1


def add_entry(builder: FactBuilder, ap: pd.DataFrame) -> None:
    records: list[dict[str, Any]] = []
    for entity, group in ap.groupby("entity"):
        indexed = group.set_index("year").sort_index()
        for series in FOURS:
            entry_status, first_positive, observed_entry, entry_exact = classify_entry(indexed[series], 0)
            material_status, first_material, observed_material, material_exact = classify_entry(indexed[series], 0.05)
            records.append({
                "entity": entity, "series": series, "entry_status": entry_status,
                "first_positive": first_positive, "observed_entry": observed_entry, "entry_exact": entry_exact,
                "material_status": material_status, "first_material": first_material,
                "observed_material": observed_material, "material_exact": material_exact,
            })
    record_frame = pd.DataFrame(records)
    earliest: dict[str, int | None] = {}
    for series, group in record_frame.groupby("series"):
        exact_years = group.loc[group.entry_status.eq("OBSERVED_TRANSITION"), "observed_entry"]
        earliest[series] = None if group.entry_status.eq("ACTIVE_AT_WINDOW_START").any() or exact_years.empty else int(exact_years.min())
    for record in records:
        entity, series = record["entity"], record["series"]
        sources = [GEN[series]]
        numeric_metrics = {
            "series_start_year": 2000, "first_positive_in_window": record["first_positive"],
            "observed_entry_year": record["observed_entry"], "is_entry_year_exact": record["entry_exact"],
            "first_material_in_window": record["first_material"],
            "observed_material_entry_year": record["observed_material"],
            "is_material_entry_year_exact": record["material_exact"],
            "lag_from_2000": record["observed_entry"] - 2000 if record["observed_entry"] is not None else None,
        }
        year_metrics = {
            "series_start_year", "first_positive_in_window", "observed_entry_year",
            "first_material_in_window", "observed_material_entry_year", "lag_from_2000",
        }
        for metric_name, value in numeric_metrics.items():
            if value is None:
                incomplete = "UNKNOWN" in record["entry_status"] or ("material" in metric_name and "UNKNOWN" in record["material_status"])
                status = "NOT_OBSERVED" if incomplete else "CENSORED"
                reason = "INCOMPLETE_SERIES" if incomplete else "EVENT_NOT_EXACTLY_OBSERVED"
            else:
                status = reason = None
            builder.add(
                "COUNTRY", entity, "WINDOW", 2000, 2021, series, metric_name, "Q4",
                value=value, comparison_scope="ASEAN_10", unit="year" if metric_name in year_metrics else "count",
                status=status, reason=reason, sources=sources,
            )
        builder.add("COUNTRY", entity, "WINDOW", 2000, 2021, series, "entry_status", "Q4", text=record["entry_status"], comparison_scope="ASEAN_10", unit="STATUS_CODE", sources=sources)
        builder.add("COUNTRY", entity, "WINDOW", 2000, 2021, series, "material_entry_status", "Q4", text=record["material_status"], comparison_scope="ASEAN_10", unit="STATUS_CODE", sources=sources)
        earliest_year = earliest[series]
        relative = record["observed_entry"] - earliest_year if earliest_year is not None and record["observed_entry"] is not None else None
        reason = "EARLIEST_ENTRY_CENSORED" if earliest_year is None else "EVENT_NOT_EXACTLY_OBSERVED"
        builder.add(
            "COUNTRY", entity, "WINDOW", 2000, 2021, series, "relative_lag", "Q4",
            value=relative, comparison_scope="ASEAN_10", unit="year",
            status="CENSORED" if relative is None else None, reason=reason if relative is None else None, sources=sources,
        )
    for series, group in record_frame.groupby("series"):
        for status_type, column in [("entry", "entry_status"), ("material_entry", "material_status")]:
            for status_value, count in group[column].value_counts().sort_index().items():
                builder.add(
                    "REGION", "ASEAN_10", "WINDOW", 2000, 2021, series,
                    f"{status_type}_count__{status_value}", "Q4", value=count,
                    comparison_scope="ASEAN_10", unit="count", population_n=10, sources=[GEN[series]],
                )


def gini(values: Iterable[float]) -> float | None:
    array = np.sort(np.asarray(list(values), dtype=float))
    total = array.sum()
    if total <= 0:
        return None
    n = len(array)
    return float(2 * np.sum(np.arange(1, n + 1) * array) / (n * total) - (n + 1) / n)


def add_concentration(builder: FactBuilder, ap: pd.DataFrame) -> None:
    for year, group in ap.groupby("year"):
        for series in ["RENEWABLE_TOTAL", "MODERN_WIND_SOLAR"]:
            values = group.set_index("entity")[series].sort_values(ascending=False, kind="mergesort")
            total = float(values.sum())
            metrics = {
                "top1_share": float(values.iloc[:1].sum() / total) if total > 0 else None,
                "top3_share": float(values.iloc[:3].sum() / total) if total > 0 else None,
                "hhi": float(np.square(values / total).sum()) if total > 0 else None,
                "gini": gini(values), "positive_n": int(values.gt(0).sum()),
                "above_0_05_n": int(values.ge(0.05).sum()),
            }
            for metric_name, value in metrics.items():
                is_count = metric_name.endswith("_n")
                builder.add(
                    "REGION", "ASEAN_10", "YEAR", year, year, series, metric_name, "Q6",
                    value=value, comparison_scope="ASEAN_10", unit="count" if is_count else "ratio",
                    status="NOT_DEFINED" if value is None else None,
                    reason="ZERO_DENOMINATOR" if value is None else None,
                    population_n=10, observed_n=10, included_n=10,
                    denominator_basis="ASEAN_SUM_10" if not is_count else "NONE",
                    threshold_value=0.05 if metric_name == "above_0_05_n" else None,
                    sources=generation_sources(series),
                )
    for start, end in PERIODS:
        start_frame = ap[ap.year.eq(start)].set_index("entity")
        end_frame = ap[ap.year.eq(end)].set_index("entity")
        for series in ["RENEWABLE_TOTAL", "MODERN_WIND_SOLAR"]:
            delta = end_frame[series] - start_frame[series]
            positive = delta.clip(lower=0)
            denominator = float(positive.sum())
            for entity in delta.index:
                share = positive.loc[entity] / denominator if denominator > 0 else None
                sources = generation_sources(series)
                builder.add("COUNTRY", entity, "INTERVAL", start, end, series, "country_delta_twh", "Q6", value=delta.loc[entity], comparison_scope="ASEAN_10", sources=sources)
                builder.add("COUNTRY", entity, "INTERVAL", start, end, series, "positive_addition_twh", "Q6", value=positive.loc[entity], comparison_scope="ASEAN_10", sources=sources)
                builder.add("COUNTRY", entity, "INTERVAL", start, end, series, "positive_growth_share", "Q6", value=share, comparison_scope="ASEAN_10", unit="ratio", status="NOT_DEFINED" if share is None else None, reason="ZERO_DENOMINATOR" if share is None else None, denominator_basis="GROSS_POSITIVE_ADDITION", sources=sources)
            top3 = positive.sort_values(ascending=False, kind="mergesort").iloc[:3].sum() / denominator if denominator > 0 else None
            for metric_name, value, unit in [
                ("gross_positive_addition_twh", denominator, "TWh"),
                ("growth_positive_n", int(delta.gt(0).sum()), "count"),
                ("top3_positive_growth_share", top3, "ratio"),
            ]:
                builder.add(
                    "REGION", "ASEAN_10", "INTERVAL", start, end, series, metric_name, "Q6",
                    value=value, comparison_scope="ASEAN_10", unit=unit,
                    status="NOT_DEFINED" if value is None else None,
                    reason="ZERO_DENOMINATOR" if value is None else None,
                    denominator_basis="GROSS_POSITIVE_ADDITION" if "share" in metric_name else "NONE",
                    population_n=10, sources=generation_sources(series),
                )


def add_benchmarks(builder: FactBuilder, ap: pd.DataFrame, wp: pd.DataFrame, cp: pd.DataFrame) -> None:
    asean9 = ap[ap.entity.ne("Vietnam")]
    for year, group in asean9.groupby("year"):
        for series in SIX:
            for metric_name, value in [
                ("asean9_sum_twh", float(group[series].sum())),
                ("asean9_median_twh", float(group[series].median())),
            ]:
                builder.add(
                    "COUNTRY", "Vietnam", "YEAR", year, year, series, metric_name, "Q4",
                    value=value, comparison_scope="ASEAN_9", population_n=9,
                    observed_n=9, included_n=9,
                    sources=generation_sources(series),
                )
    for year in YEARS:
        world = wp[wp.year.eq(year)].iloc[0]
        current = cp[cp.year.eq(year)]
        for series in SIX:
            component_series = [series] if series in GEN else FOURS if series == "RENEWABLE_TOTAL" else ["WIND", "SOLAR"]
            component_values = current[component_series]
            current_sum = float(component_values.sum(axis=0, min_count=1).sum(min_count=1)) if component_values.notna().any().any() else None
            observed_count = int(component_values.notna().sum().sum())
            population_count = 215 * len(component_series)
            reported = world[series]
            gap = current_sum - reported if current_sum is not None and pd.notna(reported) else None
            builder.add(
                "STATISTICAL_SCOPE", "GLOBAL_CURRENT_COUNTRIES", "YEAR", year, year,
                series, "world_reconciliation_gap_twh", "Q1", value=gap,
                comparison_scope="WORLD_REPORTED",
                status="NOT_DEFINED" if gap is None else None,
                reason="MISSING_COMPONENT" if gap is None else None,
                population_n=population_count, observed_n=observed_count,
                missing_n=population_count-observed_count, denominator_basis="REPORTED_WORLD",
                sources=generation_sources(series),
            )


def build_python_facts(fact: pd.DataFrame, current: list[str], asean: list[str], fp: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ap, cp, wp = make_panel(fact, asean), make_panel(fact, current), make_panel(fact, ["World"])
    builder = FactBuilder(fp)
    add_distribution(builder, fact, current, "GLOBAL_CURRENT_COUNTRIES")
    add_distribution(builder, fact, asean, "ASEAN_10")
    add_levels(builder, ap, cp, wp)
    add_shares(builder, ap, wp)
    add_time_metrics(builder, ap, wp)
    add_q5(builder, ap)
    add_rankings(builder, ap, cp)
    add_entry(builder, ap)
    add_concentration(builder, ap)
    add_benchmarks(builder, ap, wp, cp)
    return builder.frame(), ap, cp, wp


def metric_spec(metric_name: str, questions: str) -> dict[str, Any]:
    formulas = {
        "generation_twh": "source value; derived totals require all components",
        "share_electricity_pct": "source percentage; modern percentage is wind plus solar when both are observed",
        "technology_share": "technology_generation_twh / renewable_generation_twh",
        "country_share_asean": "country_generation_twh / ASEAN_10_generation_twh",
        "asean_share_world": "ASEAN_10_generation_twh / WORLD_REPORTED_generation_twh",
        "annual_change_twh": "value(t) - value(t-1)",
        "yoy": "value(t) / value(t-1) - 1 when value(t-1) > 0",
        "absolute_change_twh": "end_value - start_value",
        "cagr": "(end_value / start_value)^(1 / years) - 1 when start_value > 0",
        "cumulative_generation_twh": "sum(value) from 2000 through year with complete history",
        "rolling_mean_3y_twh": "mean(value(t-2), value(t-1), value(t)) with a complete window",
        "q5_twh_change": "TWh endpoint or adjacent-year difference",
        "q5_yoy": "TWh value(t) / TWh value(t-1) - 1 when prior value > 0",
        "q5_pct_point_change": "percentage endpoint or adjacent-year difference",
        "direction_relation": "sign comparison of Q5 changes with epsilon 1e-12",
        "asean_rank": "RANK descending within fixed ASEAN_10 cohort",
        "modern_rank_gain": "renewable_total_rank - modern_wind_solar_rank",
        "rank_gain_over_time": "rank_start - rank_end",
        "country_cagr": "country CAGR, optionally gated by a fixed start floor",
        "cagr_rank": "RANK descending among eligible ASEAN country CAGR values",
        "global_rank": "RANK descending among observed current countries, with ranked_n",
        "first_positive_in_window": "first year with value > 0 in 2000-2021",
        "observed_entry_year": "first positive year only for an exactly observed transition",
        "first_material_in_window": "first year with value >= 0.05 TWh",
        "observed_material_entry_year": "first material year only for an exactly observed transition",
        "lag_from_2000": "observed_entry_year - 2000",
        "relative_lag": "observed_entry_year - earliest exact ASEAN entry year",
        "entry_status": "window-censoring classification for first positive production",
        "material_entry_status": "window-censoring classification for first material production",
        "top1_share": "largest country value / ASEAN total",
        "top3_share": "sum of exactly three largest values / ASEAN total",
        "hhi": "sum((country_value / ASEAN_total)^2)",
        "gini": "2*sum(i*x_i)/(n*sum(x))-(n+1)/n on ascending values",
        "positive_n": "count(value > 0)", "above_0_05_n": "count(value >= 0.05 TWh)",
        "country_delta_twh": "country_end_value - country_start_value",
        "positive_addition_twh": "max(country_delta_twh, 0)",
        "positive_growth_share": "positive_addition_twh / gross_positive_addition_twh",
        "gross_positive_addition_twh": "sum(max(country_delta_twh, 0))",
        "growth_positive_n": "count(country_delta_twh > 0)",
        "top3_positive_growth_share": "three largest positive additions / gross positive addition",
        "asean9_sum_twh": "sum across ASEAN_10 excluding Vietnam",
        "asean9_median_twh": "median across ASEAN_10 excluding Vietnam",
        "current_country_sum_twh": "sum of observed current-country values for source reconciliation",
        "world_reconciliation_gap_twh": "current_country_sum_twh - WORLD_REPORTED value",
        "series_start_year": "fixed analysis-window start year",
        "is_entry_year_exact": "1 only for OBSERVED_TRANSITION; otherwise 0 or NULL if incomplete",
        "is_material_entry_year_exact": "1 only for OBSERVED_MATERIAL_TRANSITION; otherwise 0 or NULL if incomplete",
    }
    descriptive = {
        "n": "count after filter", "sum": "sum(values)", "mean": "sum(values)/n",
        "median": "linear percentile P50", "sd": "population standard deviation, ddof=0",
        "cv": "sd/mean when n>=2 and mean>0", "min": "minimum", "max": "maximum",
        "iqr": "P75-P25", "skewness": "bias-corrected sample skewness",
        "kurtosis": "bias-corrected Fisher excess kurtosis",
        "zero_share_population": "zero_n/population_n", "zero_share_observed": "zero_n/observed_n",
    }
    if metric_name in descriptive:
        formulas[metric_name] = descriptive[metric_name]
    if metric_name in {"p10", "p25", "p50", "p75", "p90", "p95", "p99"}:
        formulas[metric_name] = f"linear percentile {metric_name.upper()}"
    if "_count__" in metric_name:
        formulas[metric_name] = "count of ASEAN countries in the encoded status"
    if metric_name in {"n", "positive_n", "above_0_05_n", "growth_positive_n", "is_entry_year_exact", "is_material_entry_year_exact"} or "_count__" in metric_name:
        unit = "count"
    elif metric_name in {"cv", "skewness", "kurtosis", "zero_share_population", "zero_share_observed", "technology_share", "country_share_asean", "asean_share_world", "yoy", "cagr", "q5_yoy", "country_cagr", "positive_growth_share", "top1_share", "top3_share", "hhi", "gini", "top3_positive_growth_share"}:
        unit = "ratio"
    elif metric_name in {"direction_relation", "entry_status", "material_entry_status"}:
        unit = "STATUS_CODE"
    elif metric_name in {"asean_rank", "cagr_rank", "global_rank"}:
        unit = "rank"
    elif "rank_gain" in metric_name:
        unit = "rank_change"
    elif metric_name == "q5_pct_point_change":
        unit = "percentage_point"
    elif metric_name == "share_electricity_pct":
        unit = "pct"
    elif metric_name in {"series_start_year", "first_positive_in_window", "observed_entry_year", "first_material_in_window", "observed_material_entry_year", "lag_from_2000", "relative_lag"}:
        unit = "year"
    else:
        unit = "TWh"
    return {
        "metric_name": metric_name, "question_id": questions,
        "definition": metric_name.replace("_", " "), "formula": formulas[metric_name],
        "unit": unit, "grain": "subject-period-series", "scope": "DEFINED_BY_FACT_ROW",
        "source_metric_keys": stable_json([*GEN.values(), *PCT.values()]),
        "component_rule": "COMPLETE_CASE_WHERE_DERIVED", "denominator_rule": "EXPLICIT_DENOMINATOR_BASIS",
        "null_rule": "NULL_WITH_STATUS_AND_REASON", "zero_rule": "ZERO_IS_VALID",
        "eligibility_rule": "EXPLICIT_BY_METRIC", "threshold_rule": "FIXED_0_05_0_1_1_TWH_WHERE_APPLICABLE",
        "method_version": VERSION, "downstream_use": "PHASE4_PHASE5", "crosscheck_required": 1,
    }


def build_definitions(facts: pd.DataFrame, fp: str) -> pd.DataFrame:
    rows = []
    for metric_name, group in facts.groupby("metric_name", sort=True):
        row = metric_spec(metric_name, ",".join(sorted(group.question_id.unique())))
        source_keys: set[str] = set()
        for encoded in group.source_metric_keys.unique():
            source_keys.update(json.loads(encoded))
        units = sorted(group.unit.unique())
        if len(units) != 1:
            raise Phase3Error(f"Metric {metric_name} has inconsistent units: {units}")
        denominators = sorted(group.denominator_basis.unique())
        thresholds = sorted(group.threshold_value.dropna().unique())
        row["unit"] = units[0]
        row["scope"] = "|".join(sorted(group.comparison_scope.unique()))
        row["source_metric_keys"] = stable_json(source_keys)
        row["component_rule"] = "COMPLETE_CASE" if group.required_component_count.notna().any() else "NOT_APPLICABLE"
        row["denominator_rule"] = "|".join(denominators)
        row["threshold_rule"] = "NONE" if not thresholds else "FIXED_TWH:" + "|".join(format(value, ".12g") for value in thresholds)
        if metric_name in {"country_cagr", "cagr_rank"}:
            row["eligibility_rule"] = "START_VALUE_GT_ZERO_OR_FIXED_FLOOR; RANK_REQUIRES_AT_LEAST_3"
        elif set(group.filter_variant) & {"ALL_OBSERVED", "POSITIVE", "MATERIAL"}:
            row["eligibility_rule"] = "FILTER_VARIANT_DEFINES_INCLUDED_VALUES"
        else:
            row["eligibility_rule"] = "ALL_ROWS_WITH_REQUIRED_INPUTS"
        row["phase2_input_fingerprint"] = fp
        row["q5_pair_mapping"] = (
            json.dumps(q5_pair_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if "Q5" in set(group.question_id)
            else "NONE"
        )
        rows.append(row)
    columns = [
        "metric_name", "question_id", "definition", "formula", "unit", "grain", "scope",
        "source_metric_keys", "component_rule", "denominator_rule", "null_rule", "zero_rule",
        "eligibility_rule", "threshold_rule", "method_version", "phase2_input_fingerprint",
        "downstream_use", "crosscheck_required",
        "q5_pair_mapping",
    ]
    return pd.DataFrame(rows)[columns]


def values_equal(left: Any, right: Any) -> bool:
    return bool(pd.isna(left) and pd.isna(right)) or left == right


def crosscheck(python_facts: pd.DataFrame, sql_facts: pd.DataFrame, fp: str) -> pd.DataFrame:
    merged = python_facts.drop(columns="phase2_input_fingerprint").merge(
        sql_facts, on=FACT_KEY, how="outer", suffixes=("_python", "_sql"), indicator=True,
    )
    rows: list[dict[str, Any]] = []
    for index, row in merged.iterrows():
        present = row["_merge"] == "both"
        py_value, sql_value = row.get("metric_value_python"), row.get("metric_value_sql")
        if present and pd.isna(py_value) and pd.isna(sql_value):
            numeric_ok, difference, relative = True, None, None
        elif present and pd.notna(py_value) and pd.notna(sql_value):
            difference = abs(float(py_value) - float(sql_value))
            scale = max(abs(float(py_value)), abs(float(sql_value)))
            relative = difference / scale if scale else 0.0
            numeric_ok = math.isclose(float(py_value), float(sql_value), abs_tol=1e-9, rel_tol=1e-9)
        else:
            numeric_ok, difference, relative = False, None, None
        mismatches = []
        if not present:
            mismatches.append("PRESENCE")
        if present:
            for column in EXACT_CROSSCHECK_COLUMNS:
                if not values_equal(row.get(f"{column}_python"), row.get(f"{column}_sql")):
                    mismatches.append(column.upper())
            if not numeric_ok:
                mismatches.append("METRIC_VALUE")
        ok = present and not mismatches
        rows.append({
            "check_id": f"X{index + 1:06d}",
            "question_id": row.get("question_id_python") if row["_merge"] != "right_only" else row.get("question_id_sql"),
            "comparison_type": "PYTHON_SQL_FULL_FACT_SURFACE", "metric_name": row.metric_name,
            "subject_type": row.subject_type, "subject_key": row.subject_key,
            "period_type": row.period_type, "period_key": row.period_key,
            "series_key": row.series_key, "comparison_scope": row.comparison_scope,
            "filter_variant": row.filter_variant, "method_version": VERSION,
            "phase2_input_fingerprint": fp, "python_present": int(row["_merge"] != "right_only"),
            "sql_present": int(row["_merge"] != "left_only"),
            "python_status": row.get("value_status_python"), "sql_status": row.get("value_status_sql"),
            "python_exclusion_reason": row.get("exclusion_reason_python"), "sql_exclusion_reason": row.get("exclusion_reason_sql"),
            "python_value": py_value, "sql_value": sql_value,
            "python_text_value": row.get("metric_text_value_python"), "sql_text_value": row.get("metric_text_value_sql"),
            "absolute_difference": difference, "relative_difference": relative,
            "absolute_tolerance": 1e-9, "relative_tolerance": 1e-9,
            "status": "PASS" if ok else "FAIL", "failure_reason": "" if ok else "MISMATCH:" + ",".join(mismatches),
        })
    return pd.DataFrame(rows)


def fact_key(frame: pd.DataFrame) -> pd.Series:
    return frame[FACT_KEY].apply(
        lambda row: json.dumps(row.tolist(), ensure_ascii=False, separators=(",", ":")), axis=1
    )


def select_facts(facts: pd.DataFrame, **conditions: Any) -> pd.DataFrame:
    selected = facts
    for column, accepted in conditions.items():
        values = accepted if isinstance(accepted, (list, tuple, set, np.ndarray)) else [accepted]
        selected = selected[selected[column].isin(values)]
    result = selected.copy()
    result["fact_key"] = fact_key(result)
    return result


def wide_values(frame: pd.DataFrame, index: list[str], value_names: list[str]) -> pd.DataFrame:
    pieces = []
    for metric_name in value_names:
        part = frame[frame.metric_name.eq(metric_name)].copy()
        keep = index + [
            "metric_value", "metric_text_value", "unit", "value_status",
            "exclusion_reason", "denominator_basis", "threshold_value",
            "source_metric_keys", "fact_key",
        ]
        part = part[keep].rename(columns={
            "metric_value": metric_name, "metric_text_value": f"{metric_name}_text",
            "unit": f"{metric_name}_unit",
            "value_status": f"{metric_name}_status", "exclusion_reason": f"{metric_name}_exclusion_reason",
            "denominator_basis": f"{metric_name}_denominator_basis",
            "threshold_value": f"{metric_name}_threshold_value",
            "source_metric_keys": f"{metric_name}_source_metric_keys",
            "fact_key": f"{metric_name}_fact_key",
        })
        pieces.append(part)
    result = pieces[0]
    for piece in pieces[1:]:
        result = result.merge(piece, on=index, how="outer", validate="one_to_one")
    return result.sort_values(index, kind="mergesort").reset_index(drop=True)


def metadata_frame(
    fp: str,
    workbook_name: str,
    definitions: pd.DataFrame,
    source_catalog: pd.DataFrame,
) -> pd.DataFrame:
    main_sources = source_catalog[
        source_catalog.metric_key.isin(set(GEN.values()) | set(PCT.values()))
        & source_catalog.source_role.eq("canonical")
    ][["metric_key", "source_file", "source_column", "canonical_unit"]]
    source_provenance = {
        row.metric_key: {
            "source_file": row.source_file,
            "source_column": row.source_column,
            "canonical_unit": row.canonical_unit,
        }
        for row in main_sources.sort_values("metric_key").itertuples(index=False)
    }
    unit_conventions = definitions.set_index("metric_name").unit.to_dict()
    denominator_conventions = definitions.set_index("metric_name").denominator_rule.to_dict()
    threshold_rules = definitions.set_index("metric_name").threshold_rule.to_dict()
    metadata = {
        "method_version": VERSION,
        "phase2_input_fingerprint": fp,
        "analysis_window": "2000-2021 inclusive",
        "workbook_scope": WORKBOOK_SCOPES[workbook_name],
        "source_provenance": source_provenance,
        "unit_conventions": unit_conventions,
        "statistical_conventions": {
            "sd": "population standard deviation; ddof=0",
            "percentiles": "linear interpolation",
            "skewness": "SciPy bias=False",
            "kurtosis": "SciPy Fisher excess; bias=False",
        },
        "denominator_conventions": denominator_conventions,
        "null_rule": "NULL is never converted to zero; status and exclusion_reason are required",
        "zero_rule": "Observed zero is valid; POSITIVE means value > 0",
        "threshold_rules": threshold_rules,
        "fact_key_definition": FACT_KEY,
        "q5_pair_mapping": q5_pair_mapping(),
    }
    rows = [
        {
            "metadata_key": key,
            "metadata_value": (
                value if isinstance(value, str) else json.dumps(
                    value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
            ),
            "method_version": VERSION,
            "phase2_input_fingerprint": fp,
            "value_status": "CALCULATED_TEXT",
            "exclusion_reason": "NON_NUMERIC_RESULT",
        }
        for key, value in metadata.items()
    ]
    return pd.DataFrame(rows)


def build_workbook_frames(
    facts: pd.DataFrame,
    definitions: pd.DataFrame,
    source_catalog: pd.DataFrame,
    fp: str,
) -> dict[str, dict[str, pd.DataFrame]]:
    descriptive_names = [
        "n", "sum", "mean", "median", "sd", "cv", "min", "max", "p10", "p25",
        "p50", "p75", "p90", "p95", "p99", "iqr", "skewness", "kurtosis",
        "zero_share_population", "zero_share_observed",
    ]
    distribution = select_facts(facts, subject_type="STATISTICAL_SCOPE", metric_name=descriptive_names)
    generation_stats = wide_values(
        distribution,
        ["subject_key", "period_start_year", "series_key", "filter_variant"],
        descriptive_names,
    ).rename(columns={"subject_key": "scope", "period_start_year": "year", "series_key": "metric_key"})
    distribution_counts = distribution[distribution.metric_name.eq("n")][[
        "subject_key", "period_start_year", "series_key", "filter_variant",
        "population_n", "observed_n", "missing_n", "included_n", "zero_n",
        "trace_n", "material_n", "source_metric_keys", "threshold_value",
    ]].rename(columns={
        "subject_key": "scope", "period_start_year": "year",
        "series_key": "metric_key", "threshold_value": "filter_threshold_twh",
    })
    distribution_counts["generation_unit"] = "TWh"
    generation_stats = generation_stats.merge(
        distribution_counts,
        on=["scope", "year", "metric_key", "filter_variant"],
        how="left",
        validate="one_to_one",
    )
    coverage_source = distribution[distribution.metric_name.eq("n") & distribution.filter_variant.eq("ALL_OBSERVED")].copy()
    coverage = coverage_source[[
        "subject_key", "period_start_year", "series_key", "population_n", "observed_n",
        "missing_n", "zero_n", "trace_n", "material_n", "fact_key", "method_version",
        "value_status", "exclusion_reason", "source_metric_keys",
    ]].rename(columns={"subject_key": "scope", "period_start_year": "year", "series_key": "metric_key", "fact_key": "coverage_fact_key"})
    coverage["generation_unit"] = "TWh"
    countries = select_facts(facts, subject_type="COUNTRY", comparison_scope="GLOBAL_CURRENT_COUNTRIES", metric_name="generation_twh", period_start_year=MILESTONES)
    asean_annual = select_facts(facts, subject_type="REGION", subject_key="ASEAN_10", metric_name=["generation_twh", "technology_share"])
    country_year = select_facts(facts, subject_type="COUNTRY", comparison_scope="ASEAN_10", metric_name=["generation_twh", "technology_share"])

    q5_year = select_facts(
        facts, subject_type="COUNTRY", comparison_scope="ASEAN_10", period_type="YEAR",
        metric_name=["generation_twh", "share_electricity_pct", "q5_twh_change", "q5_yoy", "q5_pct_point_change", "direction_relation"],
    )
    q5_year = q5_year[q5_year.series_key.isin(PAIR_SERIES)]
    q5_wide = wide_values(
        q5_year, ["subject_key", "period_start_year", "series_key"],
        ["generation_twh", "share_electricity_pct", "q5_twh_change", "q5_yoy", "q5_pct_point_change", "direction_relation"],
    ).rename(columns={"subject_key": "entity", "period_start_year": "year"})
    q5_wide["pair_key"] = q5_wide.series_key.map(PAIR_KEYS)
    q5_interval = select_facts(
        facts, subject_type="COUNTRY", comparison_scope="ASEAN_10", period_type="INTERVAL",
        metric_name=["q5_twh_change", "q5_pct_point_change", "direction_relation"],
    )
    endpoint = wide_values(
        q5_interval, ["subject_key", "period_key", "series_key"],
        ["q5_twh_change", "q5_pct_point_change", "direction_relation"],
    ).rename(columns={"subject_key": "entity"})
    endpoint["pair_key"] = endpoint.series_key.map(PAIR_KEYS)

    vietnam_annual = pd.concat([
        select_facts(
            facts, subject_key="Vietnam", period_type="YEAR", comparison_scope="ASEAN_10",
            metric_name=["generation_twh", "share_electricity_pct", "country_share_asean", "cumulative_generation_twh", "rolling_mean_3y_twh"],
        ),
        select_facts(
            facts, subject_key="Vietnam", period_type="YEAR", comparison_scope="GLOBAL_CURRENT_COUNTRIES",
            metric_name="global_rank",
        ),
    ], ignore_index=True).sort_values(["period_start_year", "series_key", "metric_name"], kind="mergesort")
    vietnam_changes = select_facts(
        facts, subject_key="Vietnam", period_type="YEAR",
        metric_name=["q5_twh_change", "q5_yoy", "q5_pct_point_change", "direction_relation"],
    )
    asean9 = select_facts(facts, subject_key="Vietnam", comparison_scope="ASEAN_9", metric_name=["asean9_sum_twh", "asean9_median_twh"])

    ranks = select_facts(facts, comparison_scope="ASEAN_10", period_type="YEAR", metric_name=["asean_rank", "modern_rank_gain"])
    rank_totals = ranks[ranks.metric_name.eq("asean_rank") & ranks.series_key.eq("RENEWABLE_TOTAL")].copy()
    rank_totals["metric_name"] = "total_rank"
    rank_modern = ranks[ranks.metric_name.eq("asean_rank") & ranks.series_key.eq("MODERN_WIND_SOLAR")].copy()
    rank_modern["metric_name"] = "modern_rank"
    rank_gain = ranks[ranks.metric_name.eq("modern_rank_gain")].copy()
    rank_gain["metric_name"] = "modern_rank_gain"
    rank_wide_source = pd.concat([rank_totals, rank_modern, rank_gain], ignore_index=True)
    annual_ranks = wide_values(
        rank_wide_source, ["subject_key", "period_start_year"],
        ["total_rank", "modern_rank", "modern_rank_gain"],
    ).rename(columns={"subject_key": "entity", "period_start_year": "year"})
    rank_change = select_facts(facts, metric_name="rank_gain_over_time")
    cagr = select_facts(facts, metric_name=["country_cagr", "cagr_rank"])
    cagr_ranking = wide_values(
        cagr, ["subject_key", "period_key", "series_key", "filter_variant"],
        ["country_cagr", "cagr_rank"],
    ).rename(columns={"subject_key": "entity"})

    entry_names = [
        "series_start_year", "first_positive_in_window", "observed_entry_year",
        "is_entry_year_exact", "first_material_in_window", "observed_material_entry_year",
        "is_material_entry_year_exact", "entry_status", "material_entry_status",
        "lag_from_2000", "relative_lag",
    ]
    entry = select_facts(facts, subject_type="COUNTRY", period_type="WINDOW", metric_name=entry_names)
    entry_status = wide_values(entry, ["subject_key", "series_key"], entry_names).rename(columns={"subject_key": "entity"})
    summary_names = [name for name in facts.metric_name.unique() if "_count__" in name]
    entry_summary = select_facts(
        facts, subject_type="REGION", period_type="WINDOW", metric_name=summary_names,
    ).copy()
    status_parts = entry_summary["metric_name"].str.extract(
        r"^(entry|material_entry)_count__(.+)$"
    )
    status_parts.columns = ["status_type", "status_value"]
    allowed_status_values = {
        "entry": {
            "ACTIVE_AT_WINDOW_START", "OBSERVED_TRANSITION",
            "NOT_OBSERVED_BY_2021", "UNKNOWN_INCOMPLETE_SERIES",
        },
        "material_entry": {
            "MATERIAL_AT_WINDOW_START", "OBSERVED_MATERIAL_TRANSITION",
            "NOT_MATERIAL_BY_2021", "UNKNOWN_INCOMPLETE_SERIES",
        },
    }
    invalid_status = status_parts.isna().any(axis=1)
    for status_type, allowed_values in allowed_status_values.items():
        invalid_status |= status_parts["status_type"].eq(status_type) & ~status_parts["status_value"].isin(allowed_values)
    if invalid_status.any():
        invalid_names = entry_summary.loc[invalid_status, "metric_name"].tolist()
        raise Phase3Error(f"Invalid entry_summary status encoding: {invalid_names}")
    metric_position = entry_summary.columns.get_loc("metric_name")
    entry_summary.insert(metric_position, "status_type", status_parts["status_type"])
    entry_summary.insert(metric_position + 1, "status_value", status_parts["status_value"])
    notes = pd.DataFrame({
        "note_key": ["left_censoring", "right_censoring", "relative_lag"],
        "note": [
            "ACTIVE_AT_WINDOW_START means actual entry may predate 2000",
            "NOT_OBSERVED_BY_2021 means no transition was observed by 2021",
            "relative_lag is NULL when the earliest ASEAN event is left-censored",
        ],
        "method_version": VERSION, "value_status": "CALCULATED_TEXT", "exclusion_reason": "NON_NUMERIC_RESULT",
    })

    annual_context = select_facts(
        facts, subject_key=["ASEAN_10", "WORLD_REPORTED"], period_type="YEAR",
        metric_name=["generation_twh", "annual_change_twh", "yoy", "cumulative_generation_twh", "rolling_mean_3y_twh", "asean_share_world"],
    )
    period_growth = select_facts(facts, subject_key=["ASEAN_10", "WORLD_REPORTED"], period_type="INTERVAL", metric_name=["absolute_change_twh", "cagr"])
    concentration = select_facts(facts, subject_type="REGION", period_type="YEAR", metric_name=["top1_share", "top3_share", "hhi", "gini", "positive_n", "above_0_05_n"])
    contribution = select_facts(
        facts,
        period_type="INTERVAL",
        metric_name=[
            "country_delta_twh", "positive_addition_twh", "positive_growth_share",
            "gross_positive_addition_twh", "growth_positive_n",
            "top3_positive_growth_share",
        ],
    )
    growth_contribution = wide_values(
        contribution, ["subject_key", "period_key", "series_key"],
        [
            "country_delta_twh", "positive_addition_twh", "positive_growth_share",
            "gross_positive_addition_twh", "growth_positive_n",
            "top3_positive_growth_share",
        ],
    ).rename(columns={"subject_key": "entity"})
    reconciliation = select_facts(facts, subject_type="STATISTICAL_SCOPE", metric_name=["current_country_sum_twh", "world_reconciliation_gap_twh"])
    world_reconciliation = wide_values(
        reconciliation, ["period_start_year", "series_key"],
        ["current_country_sum_twh", "world_reconciliation_gap_twh"],
    ).rename(columns={"period_start_year": "year"})

    books = {
        "03_global_cross_section.xlsx": {
            "generation_stats": generation_stats[generation_stats.scope.eq("GLOBAL_CURRENT_COUNTRIES")],
            "country_values": countries,
            "coverage": coverage[coverage.scope.eq("GLOBAL_CURRENT_COUNTRIES")],
            "metadata": metadata_frame(fp, "03_global_cross_section.xlsx", definitions, source_catalog),
        },
        "03_asean_cross_section.xlsx": {
            "generation_stats": generation_stats[generation_stats.scope.eq("ASEAN_10")],
            "asean_annual": asean_annual, "country_year_values": country_year,
            "twh_vs_pct": q5_wide, "endpoint_change": endpoint,
            "metadata": metadata_frame(fp, "03_asean_cross_section.xlsx", definitions, source_catalog),
        },
        "03_vietnam_time_series.xlsx": {
            "annual": vietnam_annual, "annual_changes": vietnam_changes,
            "asean9_benchmark": asean9, "endpoint_change": endpoint[endpoint.entity.eq("Vietnam")],
            "metadata": metadata_frame(fp, "03_vietnam_time_series.xlsx", definitions, source_catalog),
        },
        "03_ranking_comparison.xlsx": {
            "annual_ranks": annual_ranks, "milestone_change": rank_change,
            "cagr_ranking": cagr_ranking,
            "metadata": metadata_frame(fp, "03_ranking_comparison.xlsx", definitions, source_catalog),
        },
        "03_entry_lag.xlsx": {
            "entry_status": entry_status, "entry_summary": entry_summary,
            "method_notes": notes,
            "metadata": metadata_frame(fp, "03_entry_lag.xlsx", definitions, source_catalog),
        },
        "03_global_context.xlsx": {
            "annual_context": annual_context, "period_growth": period_growth,
            "annual_concentration": concentration, "growth_contribution": growth_contribution,
            "world_reconciliation": world_reconciliation,
            "metadata": metadata_frame(fp, "03_global_context.xlsx", definitions, source_catalog),
        },
    }
    for sheets in books.values():
        for frame in sheets.values():
            if "method_version" not in frame.columns:
                frame["method_version"] = VERSION
            if "phase2_input_fingerprint" not in frame.columns:
                frame["phase2_input_fingerprint"] = fp
    return books


def validate_facts(
    facts: pd.DataFrame, cross: pd.DataFrame, definitions: pd.DataFrame,
    books: dict[str, dict[str, pd.DataFrame]], fp: str,
    phase2_validation_rows: int,
) -> pd.DataFrame:
    results: list[dict[str, Any]] = []
    def add(identifier: str, group: str, question: str, ok: bool, expected: Any, actual: Any, details: str) -> None:
        results.append({
            "validation_id": identifier, "validation_group": group, "question_id": question,
            "severity": "BLOCKING", "status": "PASS" if ok else "FAIL",
            "expected_value": expected, "actual_value": actual,
            "failure_reason": "" if ok else details, "details": details,
            "method_version": VERSION, "phase2_input_fingerprint": fp,
        })
    add(
        "P3_PHASE2_VALIDATION_GATE", "INPUT", "NOT_APPLICABLE",
        phase2_validation_rows == EXPECTED_VALIDATION_ROWS,
        EXPECTED_VALIDATION_ROWS, phase2_validation_rows,
        "Phase 2 validation is complete, passing, and bound to the current fingerprint",
    )
    add("P3_INPUT", "INPUT", "NOT_APPLICABLE", len(facts) > 0, ">0", len(facts), "fact_metrics is non-empty")
    duplicates = int(facts.duplicated(FACT_KEY).sum())
    add("P3_KEYS", "FACT_SCHEMA", "NOT_APPLICABLE", duplicates == 0, 0, duplicates, "nine-column semantic key is unique")
    finite = np.isfinite(pd.to_numeric(facts.metric_value, errors="coerce").dropna()).all()
    add("P3_FINITE", "FACT_SCHEMA", "NOT_APPLICABLE", bool(finite), True, bool(finite), "numeric values are finite")
    valid_codes = (
        set(facts.subject_type) <= {"COUNTRY", "REGION", "WORLD", "STATISTICAL_SCOPE"}
        and set(facts.comparison_scope) <= {"NONE", "ASEAN_10", "ASEAN_9", "GLOBAL_CURRENT_COUNTRIES", "WORLD_REPORTED"}
        and set(facts.value_status) <= {"CALCULATED", "CALCULATED_TEXT", "NOT_DEFINED", "NOT_OBSERVED", "CENSORED", "INSUFFICIENT_N"}
    )
    add("P3_CODES", "FACT_SCHEMA", "NOT_APPLICABLE", valid_codes, "locked code sets", "valid" if valid_codes else "invalid", "canonical codes")
    calculated_ok = facts[facts.value_status.eq("CALCULATED")].metric_value.notna().all()
    text_ok = facts[facts.value_status.eq("CALCULATED_TEXT")].metric_text_value.notna().all()
    null_ok = facts[~facts.value_status.isin(["CALCULATED", "CALCULATED_TEXT"])].metric_value.isna().all()
    add("P3_STATUS", "FACT_SCHEMA", "NOT_APPLICABLE", bool(calculated_ok and text_ok and null_ok), True, bool(calculated_ok and text_ok and null_ok), "status/value contract")
    add("P3_CROSS", "CROSSCHECK", "Q1-Q6", bool(cross.status.eq("PASS").all()), "all PASS", int(cross.status.ne("PASS").sum()), "complete Python-SQL surface")
    definition_ok = set(facts.metric_name) == set(definitions.metric_name) and definitions.metric_name.is_unique and definitions.formula.notna().all()
    add("P3_DEFINITIONS", "DEFINITIONS", "Q1-Q6", bool(definition_ok), "exact metric coverage", f"facts={facts.metric_name.nunique()}, definitions={len(definitions)}", "metric definitions cover every fact metric")
    expected_pair_mapping = json.dumps(
        q5_pair_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    q5_definitions = definitions[definitions.question_id.str.contains("Q5", regex=False)]
    q5_mapping_ok = (
        not q5_definitions.empty
        and q5_definitions.q5_pair_mapping.eq(expected_pair_mapping).all()
        and definitions[~definitions.index.isin(q5_definitions.index)].q5_pair_mapping.eq("NONE").all()
    )
    add(
        "P3_Q5_PAIR_MAPPING", "DEFINITIONS", "Q5", bool(q5_mapping_ok),
        "five complete pair mappings", int(q5_definitions.q5_pair_mapping.nunique()),
        "Q5 definitions map each pair to series, TWh sources, and percentage sources",
    )
    unit_map = facts.groupby("metric_name").unit.nunique()
    definition_units = definitions.set_index("metric_name").unit
    fact_units = facts.groupby("metric_name").unit.first()
    unit_ok = unit_map.eq(1).all() and definition_units.equals(fact_units.reindex(definition_units.index))
    add("P3_DEFINITION_UNITS", "DEFINITIONS", "Q1-Q6", bool(unit_ok), "one exact unit per metric", int((unit_map != 1).sum()), "definition units match fact_metrics")
    fingerprint_ok = facts.phase2_input_fingerprint.eq(fp).all()
    add("P3_FINGERPRINT", "FACT_SCHEMA", "NOT_APPLICABLE", bool(fingerprint_ok), fp, facts.phase2_input_fingerprint.nunique(), "all fact rows use the current Phase 2 fingerprint")
    period_ok = (
        facts.period_start_year.le(facts.period_end_year).all()
        and facts[facts.period_type.eq("YEAR")].period_key.eq("Y" + facts[facts.period_type.eq("YEAR")].period_start_year.astype(str)).all()
        and facts[facts.period_type.eq("INTERVAL")].period_key.eq("I" + facts[facts.period_type.eq("INTERVAL")].period_start_year.astype(str) + "_" + facts[facts.period_type.eq("INTERVAL")].period_end_year.astype(str)).all()
        and facts[facts.period_type.eq("WINDOW")].period_key.eq("W" + facts[facts.period_type.eq("WINDOW")].period_start_year.astype(str) + "_" + facts[facts.period_type.eq("WINDOW")].period_end_year.astype(str)).all()
    )
    add("P3_PERIOD_KEYS", "FACT_SCHEMA", "NOT_APPLICABLE", bool(period_ok), True, bool(period_ok), "period type, key, and endpoints agree")
    component_rows = facts[facts.required_component_count.notna()]
    component_ok = component_rows.component_count.notna().all() and component_rows.component_count.le(component_rows.required_component_count).all()
    add("P3_COMPONENT_COUNTS", "COMPONENTS", "Q1-Q6", bool(component_ok), "0 <= component_count <= required", int((component_rows.component_count > component_rows.required_component_count).sum()), "component completeness fields are coherent")
    country_generation = facts[(facts.subject_type == "COUNTRY") & (facts.comparison_scope == "ASEAN_10") & (facts.metric_name == "generation_twh")]
    add("P3_ASEAN_PANEL", "COVERAGE", "Q2", len(country_generation) == 1320, 1320, len(country_generation), "10 countries x 22 years x 6 series")
    technology = facts[(facts.subject_type == "COUNTRY") & (facts.metric_name == "technology_share")]
    add("P3_TECH_ROWS", "COVERAGE", "Q2", len(technology) == 880, 880, len(technology), "10 countries x 22 years x 4 technology shares")
    tech_sums = technology.groupby(["subject_key", "period_key"]).metric_value.sum(min_count=1)
    defined_tech_sums = tech_sums.dropna()
    add("P3_TECH_SHARE", "FORMULA", "Q2", bool(np.allclose(defined_tech_sums, 1, atol=1e-9)), "all defined 1", float((defined_tech_sums - 1).abs().max()), "country technology shares sum to one when the denominator is positive")
    country_shares = facts[(facts.metric_name == "country_share_asean") & facts.value_status.eq("CALCULATED")]
    share_sums = country_shares.groupby(["period_key", "series_key"]).metric_value.sum()
    add("P3_COUNTRY_SHARE", "FORMULA", "Q2", bool(np.allclose(share_sums, 1, atol=1e-9)), "all 1", float((share_sums - 1).abs().max()), "ASEAN country shares sum to one")
    percentage_rows = facts[facts.metric_name.eq("share_electricity_pct") & facts.value_status.eq("CALCULATED")]
    percentage_ok = percentage_rows.metric_value.between(0, 100).all()
    point_rows = facts[facts.metric_name.eq("q5_pct_point_change") & facts.value_status.eq("CALCULATED")]
    point_ok = point_rows.metric_value.between(-100, 100).all()
    add("P3_PERCENT_DOMAINS", "FORMULA", "Q5", bool(percentage_ok and point_ok), "pct [0,100], point change [-100,100]", "checked", "percentage domains")
    q5_counts = facts[facts.metric_name.isin(["q5_twh_change", "q5_yoy", "q5_pct_point_change", "direction_relation"]) & facts.period_type.eq("YEAR")].groupby("metric_name").size()
    q5_ok = set(q5_counts.index) == {"q5_twh_change", "q5_yoy", "q5_pct_point_change", "direction_relation"} and q5_counts.eq(1100).all()
    add("P3_Q5_COVERAGE", "COVERAGE", "Q5", bool(q5_ok), "1,100 rows per annual Q5 metric", q5_counts.to_dict(), "10 countries x 22 years x 5 pairs")
    generation_lookup = country_generation.set_index(
        ["subject_key", "period_start_year", "series_key"]
    )["metric_value"].to_dict()
    yoy_failures = 0
    q5_yoy_rows = facts[
        facts.metric_name.eq("q5_yoy") & facts.period_type.eq("YEAR")
    ]
    for row in q5_yoy_rows.itertuples(index=False):
        current = generation_lookup.get((row.subject_key, row.period_start_year, row.series_key))
        previous = generation_lookup.get((row.subject_key, row.period_start_year - 1, row.series_key))
        expected_value, expected_status, expected_reason = sequence_status(current, previous)
        expected_status = expected_status or "CALCULATED"
        expected_reason = expected_reason or "NONE"
        numeric_ok = (
            pd.isna(expected_value) and pd.isna(row.metric_value)
        ) or (
            pd.notna(expected_value) and pd.notna(row.metric_value)
            and math.isclose(float(expected_value), float(row.metric_value), abs_tol=1e-9, rel_tol=1e-9)
        )
        yoy_failures += int(
            not numeric_ok
            or row.value_status != expected_status
            or row.exclusion_reason != expected_reason
        )
    add("P3_YOY_RULE", "FORMULA", "Q5", yoy_failures == 0, 0, yoy_failures, "YoY values, zero bases, and missing-prior statuses follow the contract")
    raw_cagr = facts[
        facts.metric_name.eq("country_cagr")
        & facts.filter_variant.eq("NOT_APPLICABLE")
    ]
    cagr_failures = 0
    for row in raw_cagr.itertuples(index=False):
        start_value = generation_lookup.get((row.subject_key, row.period_start_year, row.series_key))
        end_value = generation_lookup.get((row.subject_key, row.period_end_year, row.series_key))
        expected_value = (
            (end_value / start_value) ** (1 / (row.period_end_year - row.period_start_year)) - 1
            if pd.notna(start_value) and pd.notna(end_value) and start_value > 0 else None
        )
        expected_status = "CALCULATED" if expected_value is not None else "NOT_DEFINED"
        expected_reason = "NONE" if expected_value is not None else (
            "MISSING_ENDPOINT" if pd.isna(start_value) or pd.isna(end_value) else "ZERO_BASE"
        )
        numeric_ok = (
            expected_value is None and pd.isna(row.metric_value)
        ) or (
            expected_value is not None and pd.notna(row.metric_value)
            and math.isclose(float(expected_value), float(row.metric_value), abs_tol=1e-9, rel_tol=1e-9)
        )
        cagr_failures += int(
            not numeric_ok
            or row.value_status != expected_status
            or row.exclusion_reason != expected_reason
        )
    add("P3_CAGR_RULE", "FORMULA", "Q3", cagr_failures == 0, 0, cagr_failures, "country CAGR values and denominator statuses follow endpoint rules")
    annual_rank_counts = facts[facts.metric_name.eq("asean_rank")].groupby("series_key").size()
    rank_coverage_ok = set(annual_rank_counts.index) == {"RENEWABLE_TOTAL", "MODERN_WIND_SOLAR"} and annual_rank_counts.eq(220).all()
    add("P3_RANK_COVERAGE", "COVERAGE", "Q3", bool(rank_coverage_ok), "220 per rank concept", annual_rank_counts.to_dict(), "fixed ASEAN rank cohort")
    rank_rows = facts[facts.metric_name.eq("asean_rank")]
    rank_lookup = rank_rows.set_index(
        ["subject_key", "period_start_year", "series_key"]
    )["metric_value"].to_dict()
    rank_failures = 0
    for (year, series), group in country_generation[
        country_generation.series_key.isin(["RENEWABLE_TOTAL", "MODERN_WIND_SOLAR"])
    ].groupby(["period_start_year", "series_key"]):
        values = group.set_index("subject_key")["metric_value"]
        expected_ranks, expected_n, total_zero = rank_values(values)
        for entity, expected_rank in expected_ranks.items():
            actual_row = rank_rows[
                rank_rows.subject_key.eq(entity)
                & rank_rows.period_start_year.eq(year)
                & rank_rows.series_key.eq(series)
            ].iloc[0]
            numeric_ok = (
                pd.isna(expected_rank) and pd.isna(actual_row.metric_value)
            ) or (
                pd.notna(expected_rank) and pd.notna(actual_row.metric_value)
                and math.isclose(float(expected_rank), float(actual_row.metric_value), abs_tol=1e-9, rel_tol=1e-9)
            )
            expected_status = "NOT_DEFINED" if pd.isna(expected_rank) else "CALCULATED"
            expected_reason = "ZERO_SCOPE_TOTAL" if total_zero else "NOT_OBSERVED" if pd.isna(expected_rank) else "NONE"
            rank_failures += int(
                not numeric_ok
                or actual_row.value_status != expected_status
                or actual_row.exclusion_reason != expected_reason
                or actual_row.ranked_n != expected_n
            )
        if series == "MODERN_WIND_SOLAR":
            gains = facts[
                facts.metric_name.eq("modern_rank_gain")
                & facts.period_start_year.eq(year)
            ]
            for gain in gains.itertuples(index=False):
                expected_gain = (
                    rank_lookup[(gain.subject_key, year, "RENEWABLE_TOTAL")]
                    - rank_lookup[(gain.subject_key, year, "MODERN_WIND_SOLAR")]
                )
                gain_ok = (
                    pd.isna(expected_gain) and pd.isna(gain.metric_value)
                ) or (
                    pd.notna(expected_gain) and pd.notna(gain.metric_value)
                    and math.isclose(float(expected_gain), float(gain.metric_value), abs_tol=1e-9, rel_tol=1e-9)
                )
                rank_failures += int(not gain_ok)
    add("P3_ANNUAL_RANK_RULE", "FORMULA", "Q3", rank_failures == 0, 0, rank_failures, "ASEAN ranks, ranked_n, and modern rank gains are recomputed from generation")
    rank_change_failures = 0
    rank_changes = facts[facts.metric_name.eq("rank_gain_over_time")]
    for row in rank_changes.itertuples(index=False):
        expected = (
            rank_lookup[(row.subject_key, row.period_start_year, row.series_key)]
            - rank_lookup[(row.subject_key, row.period_end_year, row.series_key)]
        )
        change_ok = (
            pd.isna(expected) and pd.isna(row.metric_value)
        ) or (
            pd.notna(expected) and pd.notna(row.metric_value)
            and math.isclose(float(expected), float(row.metric_value), abs_tol=1e-9, rel_tol=1e-9)
        )
        rank_change_failures += int(not change_ok)
    add("P3_RANK_CHANGE_RULE", "FORMULA", "Q3", rank_change_failures == 0, 0, rank_change_failures, "rank change uses start rank minus end rank, so positive means improvement")
    concentration = facts[facts.metric_name.isin(["hhi", "gini"]) & facts.value_status.eq("CALCULATED")]
    domains = ((concentration.metric_name.ne("hhi") | concentration.metric_value.between(0, 1)) & (concentration.metric_name.ne("gini") | concentration.metric_value.between(0, 0.9))).all()
    add("P3_CONCENTRATION_DOMAIN", "FORMULA", "Q6", bool(domains), "HHI [0,1], Gini [0,.9]", "checked", "concentration domains")
    contribution_sums = facts[facts.metric_name.eq("positive_growth_share")].groupby(["period_key", "series_key"]).metric_value.sum(min_count=1)
    add("P3_CONTRIBUTION", "FORMULA", "Q6", bool(np.allclose(contribution_sums.dropna(), 1, atol=1e-9)), "all 1", float((contribution_sums.dropna() - 1).abs().max()), "positive growth shares sum to one")
    delta_rows = facts[facts.metric_name.eq("country_delta_twh")]
    delta_counts = delta_rows.groupby(["period_key", "series_key"]).size()
    add("P3_CONTRIBUTION_COHORT", "COVERAGE", "Q6", bool(delta_counts.eq(10).all() and len(delta_counts) == 6), "10 countries in 6 slices", delta_counts.to_dict(), "every contribution slice contains ASEAN_10")
    region_delta = facts[(facts.metric_name.eq("absolute_change_twh")) & facts.subject_key.eq("ASEAN_10")].set_index(["period_key", "series_key"]).metric_value
    country_delta = delta_rows.groupby(["period_key", "series_key"]).metric_value.sum()
    delta_ok = np.allclose(country_delta.sort_index(), region_delta.reindex(country_delta.index).sort_index(), atol=1e-9)
    add("P3_DELTA_RECONCILIATION", "FORMULA", "Q6", bool(delta_ok), "country delta sum = ASEAN delta", float((country_delta - region_delta.reindex(country_delta.index)).abs().max()), "growth contributions reconcile to regional change")
    relative = facts[facts.metric_name.eq("relative_lag")]
    relative_ok = relative[relative.value_status.eq("CALCULATED")].metric_value.ge(0).all() and relative[relative.metric_value.isna()].exclusion_reason.isin(["EARLIEST_ENTRY_CENSORED", "EVENT_NOT_EXACTLY_OBSERVED"]).all()
    add("P3_RELATIVE_LAG", "FORMULA", "Q4", bool(relative_ok), True, bool(relative_ok), "relative lag obeys censoring rule")
    gini_ok = abs(gini(np.ones(10)) or 0) < 1e-12 and abs((gini([0] * 9 + [1]) or 0) - 0.9) < 1e-12 and gini(np.zeros(10)) is None
    hhi_ok = abs(np.square(np.ones(10) / 10).sum() - 0.1) < 1e-12 and abs(np.square(np.array([0] * 9 + [1])).sum() - 1) < 1e-12
    add("P3_CANONICAL_CONCENTRATION", "FORMULA", "Q6", bool(gini_ok and hhi_ok), "canonical cases", "checked", "HHI/Gini reference tests")
    expected_questions = {"Q1", "Q2", "Q3", "Q4", "Q5", "Q6"}
    add("P3_QUESTION_COVERAGE", "QUESTION_MAPPING", "Q1-Q6", set(facts.question_id) == expected_questions, sorted(expected_questions), sorted(set(facts.question_id)), "all questions represented in fact_metrics")
    vietnam_annual = books["03_vietnam_time_series.xlsx"]["annual"]
    vietnam_key_ok = len(vietnam_annual) == 770 and not vietnam_annual.duplicated(["period_start_year", "series_key", "metric_name"]).any()
    add("P3_VIETNAM_ANNUAL", "COVERAGE", "Q4", bool(vietnam_key_ok), "770 unique rows", len(vietnam_annual), "22 years x 35 Vietnam annual metrics")
    workbook_keys = {
        ("03_global_cross_section.xlsx", "generation_stats"): ["scope", "year", "metric_key", "filter_variant"],
        ("03_global_cross_section.xlsx", "country_values"): ["subject_key", "period_start_year", "series_key", "metric_name"],
        ("03_global_cross_section.xlsx", "coverage"): ["scope", "year", "metric_key"],
        ("03_asean_cross_section.xlsx", "generation_stats"): ["scope", "year", "metric_key", "filter_variant"],
        ("03_asean_cross_section.xlsx", "asean_annual"): ["period_start_year", "series_key", "metric_name"],
        ("03_asean_cross_section.xlsx", "country_year_values"): ["subject_key", "period_start_year", "series_key", "metric_name"],
        ("03_asean_cross_section.xlsx", "twh_vs_pct"): ["entity", "year", "pair_key"],
        ("03_asean_cross_section.xlsx", "endpoint_change"): ["entity", "period_key", "pair_key"],
        ("03_vietnam_time_series.xlsx", "annual"): ["period_start_year", "series_key", "metric_name"],
        ("03_vietnam_time_series.xlsx", "annual_changes"): ["period_start_year", "series_key", "metric_name"],
        ("03_vietnam_time_series.xlsx", "asean9_benchmark"): ["period_start_year", "series_key", "metric_name"],
        ("03_vietnam_time_series.xlsx", "endpoint_change"): ["period_key", "pair_key"],
        ("03_ranking_comparison.xlsx", "annual_ranks"): ["entity", "year"],
        ("03_ranking_comparison.xlsx", "milestone_change"): ["subject_key", "period_key", "series_key"],
        ("03_ranking_comparison.xlsx", "cagr_ranking"): ["entity", "period_key", "series_key", "filter_variant"],
        ("03_entry_lag.xlsx", "entry_status"): ["entity", "series_key"],
        ("03_entry_lag.xlsx", "entry_summary"): ["series_key", "status_type", "status_value"],
        ("03_global_context.xlsx", "annual_context"): ["subject_key", "period_start_year", "series_key", "metric_name"],
        ("03_global_context.xlsx", "period_growth"): ["subject_key", "period_key", "series_key", "metric_name", "filter_variant"],
        ("03_global_context.xlsx", "annual_concentration"): ["period_start_year", "series_key", "metric_name"],
        ("03_global_context.xlsx", "growth_contribution"): ["entity", "period_key", "series_key"],
        ("03_global_context.xlsx", "world_reconciliation"): ["year", "series_key"],
    }
    for name, sheets in WORKBOOKS.items():
        actual = list(books[name])
        workbook_id = Path(name).stem.upper()
        add(f"WB_{workbook_id}", "WORKBOOK", "NOT_APPLICABLE", actual == sheets, sheets, actual, "workbook sheet allow-list and order")
        for sheet_name, frame in books[name].items():
            if sheet_name in {"metadata", "method_notes"}:
                continue
            has_trace = any(column == "fact_key" or column.endswith("_fact_key") for column in frame.columns)
            sheet_id = sheet_name.upper()
            add(f"TRACE_{workbook_id}_{sheet_id}", "WORKBOOK", "NOT_APPLICABLE", has_trace, True, has_trace, "sheet values trace to fact_metrics")
            key_columns = workbook_keys[(name, sheet_name)]
            missing_key_columns = [column for column in key_columns if column not in frame.columns]
            if missing_key_columns:
                key_ok = False
                key_actual: Any = f"missing columns: {missing_key_columns}"
            else:
                null_key_rows = int(frame[key_columns].isna().any(axis=1).sum())
                duplicate_key_rows = int(frame.duplicated(key_columns).sum())
                key_ok = null_key_rows == 0 and duplicate_key_rows == 0
                key_actual = f"null rows={null_key_rows}; duplicate rows={duplicate_key_rows}"
            add(
                f"KEY_{workbook_id}_{sheet_id}", "WORKBOOK", "NOT_APPLICABLE",
                key_ok, "all key columns present; 0 null rows; 0 duplicate rows",
                key_actual, "workbook semantic key is complete and unique",
            )

    required_metadata_keys = {
        "method_version", "phase2_input_fingerprint", "analysis_window",
        "workbook_scope", "source_provenance", "unit_conventions",
        "statistical_conventions", "denominator_conventions", "null_rule",
        "zero_rule", "threshold_rules", "fact_key_definition",
        "q5_pair_mapping",
    }
    for name in WORKBOOKS:
        metadata = books[name]["metadata"]
        metadata_map = metadata.set_index("metadata_key").metadata_value.to_dict()
        metadata_ok = (
            metadata.metadata_key.is_unique
            and set(metadata.metadata_key) == required_metadata_keys
            and metadata.method_version.eq(VERSION).all()
            and metadata.phase2_input_fingerprint.eq(fp).all()
            and json.loads(metadata_map.get("q5_pair_mapping", "{}")) == q5_pair_mapping()
        )
        add(
            f"META_{Path(name).stem.upper()}", "WORKBOOK", "Q1-Q6",
            bool(metadata_ok), sorted(required_metadata_keys),
            sorted(set(metadata.metadata_key)),
            "workbook metadata contains the complete, versioned contract",
        )

    distribution_columns = {
        "population_n", "observed_n", "missing_n", "included_n", "zero_n",
        "trace_n", "material_n", "source_metric_keys", "generation_unit",
        "filter_threshold_twh",
    }
    distribution_contract_ok = True
    for name in ["03_global_cross_section.xlsx", "03_asean_cross_section.xlsx"]:
        frame = books[name]["generation_stats"]
        material = frame[frame.filter_variant.eq("MATERIAL")]
        distribution_contract_ok = distribution_contract_ok and (
            distribution_columns <= set(frame.columns)
            and material.filter_threshold_twh.eq(0.05).all()
            and frame.generation_unit.eq("TWh").all()
            and frame.source_metric_keys.notna().all()
        )
    add(
        "P3_DISTRIBUTION_WORKBOOK_CONTRACT", "WORKBOOK", "Q1",
        bool(distribution_contract_ok), True, bool(distribution_contract_ok),
        "distribution sheets carry coverage, source, unit, and MATERIAL threshold",
    )

    growth = books["03_global_context.xlsx"]["growth_contribution"]
    aggregate_names = [
        "gross_positive_addition_twh", "growth_positive_n",
        "top3_positive_growth_share",
    ]
    growth_summary = growth[growth.entity.eq("ASEAN_10")]
    growth_countries = growth[~growth.entity.eq("ASEAN_10")]
    growth_contract_ok = (
        len(growth) == 66
        and len(growth_countries) == 60
        and len(growth_summary) == 6
        and all(growth_summary[name].notna().all() for name in aggregate_names)
        and all(growth_summary[f"{name}_fact_key"].notna().all() for name in aggregate_names)
    )
    add(
        "P3_Q6_WORKBOOK_SUMMARY", "WORKBOOK", "Q6", bool(growth_contract_ok),
        "60 country rows + 6 ASEAN summary rows", len(growth),
        "growth_contribution exposes gross growth, positive country count, and top-three share",
    )
    workbook_provenance_ok = all(
        "method_version" in frame.columns
        and frame.method_version.eq(VERSION).all()
        and "phase2_input_fingerprint" in frame.columns
        and frame.phase2_input_fingerprint.eq(fp).all()
        for sheets in books.values() for frame in sheets.values()
    )
    add("P3_WORKBOOK_PROVENANCE", "WORKBOOK", "Q1-Q6", workbook_provenance_ok, True, workbook_provenance_ok, "every workbook sheet carries method version and Phase 2 fingerprint")
    prospective_ids = [row["validation_id"] for row in results] + ["P3_VALIDATION_IDS_UNIQUE"]
    ids_unique = len(prospective_ids) == len(set(prospective_ids))
    add(
        "P3_VALIDATION_IDS_UNIQUE", "VALIDATION_SCHEMA", "NOT_APPLICABLE",
        ids_unique, "all validation_id values unique",
        len(prospective_ids) - len(set(prospective_ids)),
        "validation identifiers are stable and unique",
    )
    validations = pd.DataFrame(results)
    if not validations.validation_id.is_unique:
        raise Phase3Error("Phase 3 validation_id values are not unique")
    return validations


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n", float_format="%.12g")


def write_workbooks(books: dict[str, dict[str, pd.DataFrame]], stage: Path) -> None:
    for name, sheets in books.items():
        with pd.ExcelWriter(stage / name, engine="openpyxl") as writer:
            for sheet_name in WORKBOOKS[name]:
                sheets[sheet_name].replace([np.inf, -np.inf], np.nan).to_excel(writer, sheet_name=sheet_name, index=False)


def sqlite_backup_replace(source: Path, target: Path) -> None:
    source_conn = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
    target_conn = sqlite3.connect(target, timeout=5)
    try:
        source_conn.backup(target_conn)
        target_conn.commit()
    finally:
        target_conn.close()
        source_conn.close()


def replace_outputs_atomically(staged_targets: list[tuple[Path, Path]]) -> None:
    backup_dir = staged_targets[0][0].parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backups: dict[Path, Path | None] = {}
    committed: list[Path] = []
    try:
        for index, (staged, target) in enumerate(staged_targets):
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                backup = backup_dir / f"{index:02d}_{target.name}.bak"
                shutil.copy2(target, backup)
                backups[target] = backup
            else:
                backups[target] = None
            try:
                os.replace(staged, target)
            except PermissionError:
                if target.resolve() != DB_PATH.resolve() or not target.exists():
                    raise
                sqlite_backup_replace(staged, target)
                staged.unlink()
            committed.append(target)
    except OSError as exc:
        for target in reversed(committed):
            backup = backups[target]
            if backup is None:
                if target.exists():
                    target.unlink()
            elif target.resolve() == DB_PATH.resolve():
                sqlite_backup_replace(backup, target)
            else:
                shutil.copy2(backup, target)
        raise Phase3Error(f"Phase 3 publication failed; previous outputs restored: {exc}") from exc


def clean_orphan_stages(active: Path) -> None:
    output_root = OUTPUT.resolve()
    for path in OUTPUT.glob(".phase3_stage_*"):
        try:
            resolved = path.resolve()
            if resolved == active.resolve() or resolved.parent != output_root or not resolved.name.startswith(".phase3_stage_"):
                continue
            shutil.rmtree(resolved)
        except OSError:
            print(f"WARNING: could not remove orphan staging directory: {path}", file=sys.stderr)


def build_and_stage() -> tuple[Path, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    STATS.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(DB_PATH)
    try:
        try:
            fp = validate_phase2_gate(source)
        except Phase2ContractError as exc:
            raise Phase3Error(str(exc)) from exc
        phase2_validation_rows = source.execute(
            "SELECT COUNT(*) FROM validation_results"
        ).fetchone()[0]
        source_catalog = pd.read_sql_query(
            "SELECT * FROM source_metric_catalog ORDER BY source_file,source_column",
            source,
        )
        _, fact, current, asean = load_input(source)
    finally:
        source.close()
    python_facts, _, _, _ = build_python_facts(fact, current, asean, fp)
    stage = Path(tempfile.mkdtemp(prefix=".phase3_stage_", dir=OUTPUT))
    staged_db = stage / DB_PATH.name
    source_db, stage_db = sqlite3.connect(DB_PATH), sqlite3.connect(staged_db)
    try:
        source_db.backup(stage_db)
    finally:
        stage_db.close()
        source_db.close()
    connection = sqlite3.connect(staged_db)
    try:
        connection.executescript((SQL_DIR / "03_analysis.sql").read_text(encoding="utf-8"))
        sql_facts = pd.read_sql_query("SELECT * FROM phase3_sql_results", connection)
        cross = crosscheck(python_facts, sql_facts, fp)
        if cross.status.ne("PASS").any():
            failed = cross[cross.status.ne("PASS")]
            print(failed.groupby(["failure_reason", "metric_name"]).size().sort_values(ascending=False).head(30).to_string(), file=sys.stderr)
            print(failed[["metric_name", "subject_key", "period_key", "series_key", "filter_variant", "python_value", "sql_value", "failure_reason"]].head(30).to_string(index=False), file=sys.stderr)
            raise Phase3Error(f"Python-SQL crosscheck failed: {len(failed)}/{len(cross)} rows")
        python_facts.to_sql("fact_metrics", connection, if_exists="replace", index=False)
        connection.execute("CREATE UNIQUE INDEX uq_fact_metrics_semantic ON fact_metrics(subject_type,subject_key,period_type,period_key,series_key,metric_name,comparison_scope,filter_variant,method_version)")
        connection.commit()
    finally:
        connection.close()
    definitions = build_definitions(python_facts, fp)
    books = build_workbook_frames(python_facts, definitions, source_catalog, fp)
    validations = validate_facts(
        python_facts, cross, definitions, books, fp, phase2_validation_rows
    )
    if validations.status.eq("FAIL").any():
        print(validations[validations.status.eq("FAIL")][["validation_id", "actual_value", "failure_reason"]].to_string(index=False), file=sys.stderr)
        raise Phase3Error("Phase 3 validation failed")
    write_workbooks(books, stage)
    write_csv(python_facts, stage / "03_fact_metrics.csv")
    write_csv(definitions, stage / "03_metric_definitions.csv")
    write_csv(cross, stage / "03_crosscheck_results.csv")
    write_csv(validations, stage / "03_validation_results.csv")
    return stage, python_facts, cross, validations, fp


def main() -> int:
    stage: Path | None = None
    try:
        stage, facts, cross, validations, fp = build_and_stage()
        targets = [(stage / DB_PATH.name, DB_PATH)] + [
            (stage / name, STATS / name)
            for name in [*WORKBOOKS, "03_fact_metrics.csv", "03_metric_definitions.csv", "03_crosscheck_results.csv", "03_validation_results.csv"]
        ]
        replace_outputs_atomically(targets)
        clean_orphan_stages(stage)
        print(f"PHASE 3: PASS | fact_metrics={len(facts):,} | crosschecks={len(cross):,} | validations={len(validations):,} | fingerprint={fp[:12]}")
        return 0
    except (Phase3Error, OSError, sqlite3.Error, ValueError, KeyError, pd.errors.DatabaseError) as exc:
        print(f"PHASE 3 FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        if stage is not None and stage.exists():
            try:
                shutil.rmtree(stage)
            except OSError:
                print(f"WARNING: staging cleanup failed: {stage}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
