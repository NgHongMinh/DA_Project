"""Build the validated Phase 2 renewable-energy data model.

The script reads the 17 immutable CSV files in archive/, applies the source and
metric decisions made in Phase 1, builds tidy dimensions/facts/audit tables,
and atomically publishes deterministic CSV files plus a SQLite database.

Usage from the project root:
    python python\02_clean_build.py
    python python\02_clean_build.py --check-only
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import (  # noqa: E402
    ARCHIVE,
    ASEAN_10,
    CLEAN,
    DB_PATH,
    EXPECTED_CSV_COUNT,
    OUTPUT,
    SQL_DIR,
    STATS,
)


KEY_COLUMNS = ["Entity", "Code", "Year"]
PERCENT_EPSILON = 0.0001
MAIN_WINDOW_START = 2000
MAIN_WINDOW_END = 2021

CONTINUITY_FILE = STATS / "04_year_continuity_details.csv"
SCHEMA_FILE = SQL_DIR / "01_schema.sql"

EXPECTED_FACT_ROWS = 89_075
EXPECTED_ZERO_ROWS = 36_153
EXPECTED_POSITIVE_ROWS = 52_922
EXPECTED_ENTITY_YEAR_KEYS = 8_968
EXPECTED_ENTITY_COUNT = 256
EXPECTED_CURRENT_ENTITY_COUNT = 215
EXPECTED_MAIN_PANEL_ROWS = 1_760
EXPECTED_SOURCE_NULL_CELLS = 574
EXPECTED_PERCENT_SNAPS = 3
EXPECTED_CURRENT_SAMPLING_SERIES = 23
EXPECTED_CURRENT_SAMPLING_MISSING_CELLS = 184

OUTPUT_TABLES = {
    "source_metric_catalog": "source_metric_catalog.csv",
    "dim_metric": "dim_metric.csv",
    "dim_entity": "dim_entity.csv",
    "dim_year": "dim_year.csv",
    "fact_energy": "fact_energy.csv",
    "missingness_audit": "missingness_audit.csv",
    "cleaning_audit": "cleaning_audit.csv",
}


class Phase2Error(Exception):
    """Raised when an input or Phase 2 invariant is invalid."""


def metric_spec(
    source_file: str,
    source_column: str,
    source_role: str,
    metric_key: str,
    technology: str,
    metric: str,
    source_unit: str,
    canonical_unit: str,
    conversion_factor: float,
    scope: str,
    trace_threshold: float,
    analysis_start_year: int,
    analysis_end_year: int,
    decision_reason: str,
) -> dict[str, object]:
    return {
        "source_file": source_file,
        "source_column": source_column,
        "source_role": source_role,
        "metric_key": metric_key,
        "technology": technology,
        "metric": metric,
        "source_unit": source_unit,
        "canonical_unit": canonical_unit,
        "conversion_factor": conversion_factor,
        "scope": scope,
        "trace_threshold": trace_threshold,
        "analysis_start_year": analysis_start_year,
        "analysis_end_year": analysis_end_year,
        "decision_reason": decision_reason,
    }


F01 = "01 renewable-share-energy.csv"
F02 = "02 modern-renewable-energy-consumption.csv"
F03 = "03 modern-renewable-prod.csv"
F04 = "04 share-electricity-renewables.csv"
F05 = "05 hydropower-consumption.csv"
F06 = "06 hydro-share-energy.csv"
F07 = "07 share-electricity-hydro.csv"
F08 = "08 wind-generation.csv"
F09 = "09 cumulative-installed-wind-energy-capacity-gigawatts.csv"
F10 = "10 wind-share-energy.csv"
F11 = "11 share-electricity-wind.csv"
F12 = "12 solar-energy-consumption.csv"
F13 = "13 installed-solar-PV-capacity.csv"
F14 = "14 solar-share-energy.csv"
F15 = "15 share-electricity-solar.csv"
F16 = "16 biofuel-production.csv"
F17 = "17 installed-geothermal-capacity.csv"


METRIC_SPECS = [
    metric_spec(F01, "Renewables (% equivalent primary energy)", "canonical", "renewables_share_primary_energy_pct", "renewables", "share_primary_energy", "pct", "pct", 1.0, "auxiliary_asean6", 0.01, 1965, 2020, "Unique primary-energy share; fixed ASEAN-6 panel ends in 2020."),
    metric_spec(F02, "Geo Biomass Other - TWh", "audit", "other_renewables_generation_twh", "other_renewables", "generation", "TWh", "TWh", 1.0, "audit_source_conflict", 0.05, 1965, 2021, "Conflicts materially with file 03; retained only in immutable raw/audit source."),
    metric_spec(F02, "Solar Generation - TWh", "audit", "solar_generation_twh", "solar", "generation", "TWh", "TWh", 1.0, "audit_source_conflict", 0.05, 1965, 2021, "Conflicts materially with file 03; retained only in immutable raw/audit source."),
    metric_spec(F02, "Wind Generation - TWh", "audit", "wind_generation_twh", "wind", "generation", "TWh", "TWh", 1.0, "audit_source_conflict", 0.05, 1965, 2021, "Conflicts materially with file 03; retained only in immutable raw/audit source."),
    metric_spec(F02, "Hydro Generation - TWh", "audit", "hydro_generation_twh", "hydro", "generation", "TWh", "TWh", 1.0, "audit_source_conflict", 0.05, 1965, 2021, "Conflicts materially with file 03; retained only in immutable raw/audit source."),
    metric_spec(F03, "Electricity from wind (TWh)", "canonical", "wind_generation_twh", "wind", "generation", "TWh", "TWh", 1.0, "main_asean10", 0.05, 1965, 2021, "Preferred broad source; 2022 is severely truncated."),
    metric_spec(F03, "Electricity from hydro (TWh)", "canonical", "hydro_generation_twh", "hydro", "generation", "TWh", "TWh", 1.0, "main_asean10", 0.05, 1965, 2021, "Preferred broad source; 2022 is severely truncated."),
    metric_spec(F03, "Electricity from solar (TWh)", "canonical", "solar_generation_twh", "solar", "generation", "TWh", "TWh", 1.0, "main_asean10", 0.05, 1965, 2021, "Preferred broad source; 2022 is severely truncated."),
    metric_spec(F03, "Other renewables including bioenergy (TWh)", "canonical", "other_renewables_generation_twh", "other_renewables", "generation", "TWh", "TWh", 1.0, "main_asean10", 0.05, 1965, 2021, "Preferred broad source; 2022 is severely truncated."),
    metric_spec(F04, "Renewables (% electricity)", "canonical", "renewables_share_electricity_pct", "renewables", "share_electricity", "pct", "pct", 1.0, "main_asean10", 0.01, 1985, 2021, "Unique ASEAN-10 electricity-share metric; 2022 is severely truncated."),
    metric_spec(F05, "Electricity from hydro (TWh)", "excluded", "hydro_generation_twh", "hydro", "generation", "TWh", "TWh", 1.0, "excluded_redundant", 0.05, 1965, 2021, "Redundant subset of the hydro column in file 03."),
    metric_spec(F06, "Hydro (% equivalent primary energy)", "canonical", "hydro_share_primary_energy_pct", "hydro", "share_primary_energy", "pct", "pct", 1.0, "auxiliary_asean6", 0.01, 1965, 2020, "Unique primary-energy share; fixed ASEAN-6 panel ends in 2020."),
    metric_spec(F07, "Hydro (% electricity)", "canonical", "hydro_share_electricity_pct", "hydro", "share_electricity", "pct", "pct", 1.0, "main_asean10", 0.01, 1985, 2021, "Unique ASEAN-10 electricity-share metric; 2022 is severely truncated."),
    metric_spec(F08, "Electricity from wind (TWh)", "excluded", "wind_generation_twh", "wind", "generation", "TWh", "TWh", 1.0, "excluded_redundant", 0.05, 1965, 2021, "Redundant subset of the wind column in file 03."),
    metric_spec(F09, "Wind Capacity", "canonical", "wind_capacity_gw", "wind", "installed_capacity", "GW", "GW", 1.0, "subset_case_study", 0.01, 1995, 2021, "Unique capacity metric with limited ASEAN coverage."),
    metric_spec(F10, "Wind (% equivalent primary energy)", "canonical", "wind_share_primary_energy_pct", "wind", "share_primary_energy", "pct", "pct", 1.0, "auxiliary_asean6", 0.01, 1965, 2021, "Unique primary-energy share with ASEAN-6 coverage."),
    metric_spec(F11, "Wind (% electricity)", "canonical", "wind_share_electricity_pct", "wind", "share_electricity", "pct", "pct", 1.0, "main_asean10", 0.01, 1985, 2021, "Unique ASEAN-10 electricity-share metric; 2022 is severely truncated."),
    metric_spec(F12, "Electricity from solar (TWh)", "excluded", "solar_generation_twh", "solar", "generation", "TWh", "TWh", 1.0, "excluded_redundant", 0.05, 1965, 2021, "Redundant subset of the solar column in file 03."),
    metric_spec(F13, "Solar Capacity", "canonical", "solar_capacity_gw", "solar", "installed_capacity", "GW", "GW", 1.0, "subset_case_study", 0.01, 1996, 2021, "Unique capacity metric with limited ASEAN coverage."),
    metric_spec(F14, "Solar (% equivalent primary energy)", "canonical", "solar_share_primary_energy_pct", "solar", "share_primary_energy", "pct", "pct", 1.0, "auxiliary_asean6", 0.01, 1965, 2021, "Unique primary-energy share with ASEAN-6 coverage."),
    metric_spec(F15, "Solar (% electricity)", "canonical", "solar_share_electricity_pct", "solar", "share_electricity", "pct", "pct", 1.0, "main_asean10", 0.01, 1985, 2021, "Unique ASEAN-10 electricity-share metric; 2022 is severely truncated."),
    metric_spec(F16, "Biofuels Production - TWh - Total", "canonical", "biofuel_production_twh", "biofuel", "production", "TWh", "TWh", 1.0, "subset_case_study", 0.05, 1990, 2021, "Unique biofuel production metric with limited ASEAN coverage."),
    metric_spec(F17, "Geothermal Capacity", "canonical", "geothermal_capacity_gw", "geothermal", "installed_capacity", "MW", "GW", 0.001, "subset_case_study", 0.01, 1975, 2020, "Source is measured in MW; converted to GW. Sampling grid is not interpolated."),
]


CANONICAL_METRIC_KEYS = [
    "renewables_share_primary_energy_pct",
    "wind_generation_twh",
    "hydro_generation_twh",
    "solar_generation_twh",
    "other_renewables_generation_twh",
    "renewables_share_electricity_pct",
    "hydro_share_primary_energy_pct",
    "hydro_share_electricity_pct",
    "wind_capacity_gw",
    "wind_share_primary_energy_pct",
    "wind_share_electricity_pct",
    "solar_capacity_gw",
    "solar_share_primary_energy_pct",
    "solar_share_electricity_pct",
    "biofuel_production_twh",
    "geothermal_capacity_gw",
]

MAIN_METRIC_KEYS = {
    spec["metric_key"]
    for spec in METRIC_SPECS
    if spec["source_role"] == "canonical" and spec["scope"] == "main_asean10"
}

CANONICAL_CONTINENTS = {
    "Africa",
    "Asia",
    "Europe",
    "North America",
    "Oceania",
    "South America",
}

CONTINENT_VARIANTS = {
    "Africa (BP)": "Africa",
    "Africa (Ember)": "Africa",
    "Asia (Ember)": "Asia",
    "Europe (BP)": "Europe",
    "Europe (Ember)": "Europe",
    "North America (BP)": "North America",
    "North America (Ember)": "North America",
    "Oceania (Ember)": "Oceania",
}

SAFE_CANONICAL_VARIANTS = {
    "Africa (Ember)": "Africa",
    "Asia (Ember)": "Asia",
    "Europe (Ember)": "Europe",
    "European Union (27) (Ember)": "European Union (27)",
    "North America (Ember)": "North America",
    "Oceania (Ember)": "Oceania",
}

INCOME_GROUPS = {
    "High-income countries",
    "Low-income countries",
    "Lower-middle-income countries",
    "Upper-middle-income countries",
}

POLITICAL_BLOCS = {
    "European Union (27)",
    "European Union (27) (Ember)",
    "G20 (Ember)",
    "G7 (Ember)",
    "Non-OECD (BP)",
    "OECD (BP)",
    "OECD (Ember)",
}


def catalog_frame() -> pd.DataFrame:
    columns = [
        "source_file",
        "source_column",
        "source_role",
        "metric_key",
        "technology",
        "metric",
        "source_unit",
        "canonical_unit",
        "conversion_factor",
        "scope",
        "trace_threshold",
        "analysis_start_year",
        "analysis_end_year",
        "decision_reason",
    ]
    return pd.DataFrame(METRIC_SPECS, columns=columns).sort_values(
        ["source_file", "source_column"], kind="stable"
    ).reset_index(drop=True)


def discover_and_load_sources(
    catalog: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    csv_files = sorted(ARCHIVE.glob("*.csv"), key=lambda path: path.name)
    if len(csv_files) != EXPECTED_CSV_COUNT:
        raise Phase2Error(
            f"Expected {EXPECTED_CSV_COUNT} CSV files, found {len(csv_files)}."
        )

    expected_files = set(catalog["source_file"])
    actual_files = {path.name for path in csv_files}
    if actual_files != expected_files:
        raise Phase2Error(
            "Archive/catalog file mismatch: "
            f"missing={sorted(expected_files - actual_files)}, "
            f"unexpected={sorted(actual_files - expected_files)}"
        )

    sources: dict[str, pd.DataFrame] = {}
    for csv_path in csv_files:
        frame = pd.read_csv(csv_path)
        missing_keys = [column for column in KEY_COLUMNS if column not in frame.columns]
        if missing_keys:
            raise Phase2Error(f"{csv_path.name}: missing key columns {missing_keys}.")

        expected_metrics = set(
            catalog.loc[
                catalog["source_file"].eq(csv_path.name), "source_column"
            ]
        )
        actual_metrics = set(frame.columns) - set(KEY_COLUMNS)
        if actual_metrics != expected_metrics:
            raise Phase2Error(
                f"{csv_path.name}: metric header mismatch; "
                f"missing={sorted(expected_metrics - actual_metrics)}, "
                f"unexpected={sorted(actual_metrics - expected_metrics)}"
            )

        if frame["Entity"].isna().any() or frame["Entity"].astype(str).str.strip().eq("").any():
            raise Phase2Error(f"{csv_path.name}: Entity contains blank values.")
        if not frame["Entity"].astype(str).eq(frame["Entity"].astype(str).str.strip()).all():
            raise Phase2Error(f"{csv_path.name}: Entity contains surrounding whitespace.")

        numeric_year = pd.to_numeric(frame["Year"], errors="coerce")
        if numeric_year.isna().any() or not np.equal(numeric_year, np.floor(numeric_year)).all():
            raise Phase2Error(f"{csv_path.name}: Year must contain integers only.")
        frame["Year"] = numeric_year.astype("int64")

        if frame.duplicated(["Entity", "Year"]).any():
            raise Phase2Error(f"{csv_path.name}: duplicate (Entity, Year) keys.")

        for column in actual_metrics:
            original = frame[column]
            numeric = pd.to_numeric(original, errors="coerce")
            invalid = original.notna() & numeric.isna()
            if invalid.any():
                examples = frame.loc[invalid, ["Entity", "Year", column]].head(5)
                raise Phase2Error(
                    f"{csv_path.name}/{column}: non-numeric values found:\n{examples}"
                )
            frame[column] = numeric.astype("float64")

        sources[csv_path.name] = frame

    return sources


def validate_catalog(catalog: pd.DataFrame, sources: dict[str, pd.DataFrame]) -> None:
    if len(catalog) != 23:
        raise Phase2Error(f"Metric catalog must have 23 rows, found {len(catalog)}.")
    if catalog.duplicated(["source_file", "source_column"]).any():
        raise Phase2Error("Metric catalog contains duplicate source column mappings.")
    if (catalog["conversion_factor"] <= 0).any():
        raise Phase2Error("All conversion factors must be positive.")
    if (catalog["trace_threshold"] <= 0).any():
        raise Phase2Error("All trace thresholds must be positive.")
    if (catalog["analysis_start_year"] > catalog["analysis_end_year"]).any():
        raise Phase2Error("A metric analysis start year is after its end year.")

    file_roles = catalog.groupby("source_file")["source_role"].nunique()
    if not file_roles.eq(1).all():
        raise Phase2Error("Every source file must have exactly one source role.")
    role_counts = (
        catalog[["source_file", "source_role"]]
        .drop_duplicates()["source_role"]
        .value_counts()
        .to_dict()
    )
    if role_counts != {"canonical": 13, "excluded": 3, "audit": 1}:
        raise Phase2Error(f"Unexpected source role counts: {role_counts}")

    canonical = catalog.loc[catalog["source_role"].eq("canonical")]
    if len(canonical) != 16 or canonical["metric_key"].nunique() != 16:
        raise Phase2Error("Canonical catalog must contain 16 unique metrics.")
    if set(canonical["metric_key"]) != set(CANONICAL_METRIC_KEYS):
        raise Phase2Error(
            "Canonical metric keys differ from the locked Phase 2 contract."
        )

    for row in catalog.itertuples(index=False):
        frame = sources[row.source_file]
        observed_min = int(frame["Year"].min())
        observed_max = int(frame["Year"].max())
        if row.analysis_start_year < observed_min or row.analysis_end_year > observed_max:
            raise Phase2Error(
                f"{row.source_file}/{row.source_column}: analysis window "
                f"{row.analysis_start_year}-{row.analysis_end_year} lies outside "
                f"source range {observed_min}-{observed_max}."
            )


def build_dim_metric(catalog: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "metric_key",
        "technology",
        "metric",
        "canonical_unit",
        "source_unit",
        "conversion_factor",
        "source_file",
        "source_column",
        "scope",
        "trace_threshold",
        "analysis_start_year",
        "analysis_end_year",
    ]
    dim_metric = (
        catalog.loc[catalog["source_role"].eq("canonical"), columns]
        .copy()
        .sort_values("metric_key", kind="stable")
        .reset_index(drop=True)
    )
    if dim_metric["metric_key"].duplicated().any():
        raise Phase2Error("dim_metric contains duplicate metric_key values.")
    return dim_metric


def build_entity_code_map(
    sources: dict[str, pd.DataFrame],
) -> dict[str, str | None]:
    entity_codes: dict[str, set[str]] = defaultdict(set)
    for frame in sources.values():
        for entity, code in frame[["Entity", "Code"]].itertuples(index=False):
            if pd.notna(code) and str(code).strip():
                entity_codes[str(entity)].add(str(code).strip())
            else:
                entity_codes[str(entity)]

    conflicts = {entity: codes for entity, codes in entity_codes.items() if len(codes) > 1}
    if conflicts:
        raise Phase2Error(f"Entity-to-code conflicts found: {conflicts}")
    return {
        entity: (next(iter(codes)) if codes else None)
        for entity, codes in entity_codes.items()
    }


def classify_entity(entity: str, iso_code: str | None) -> str:
    if iso_code == "OWID_KOS":
        return "country_or_territory"
    if iso_code == "OWID_USS":
        return "historical"
    if iso_code == "OWID_WRL":
        return "world"
    if entity in CANONICAL_CONTINENTS or entity in CONTINENT_VARIANTS:
        return "continent"
    if entity in INCOME_GROUPS:
        return "income_group"
    if entity in POLITICAL_BLOCS:
        return "political_bloc"
    if iso_code is None:
        return "region"
    if iso_code:
        return "country_or_territory"
    raise Phase2Error(f"Unable to classify entity: {entity!r}")


def build_dim_entity(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    entity_codes = build_entity_code_map(sources)
    records: list[dict[str, object]] = []
    aggregate_types = {"continent", "income_group", "political_bloc", "region", "world"}

    for entity in sorted(entity_codes):
        iso_code = entity_codes[entity]
        entity_type = classify_entity(entity, iso_code)
        is_source_variant = entity.endswith("(BP)") or entity.endswith("(Ember)")
        if not is_source_variant:
            canonical_entity: str | None = entity
        else:
            canonical_entity = SAFE_CANONICAL_VARIANTS.get(entity)

        continent = None
        if entity_type == "continent":
            continent = CONTINENT_VARIANTS.get(entity, entity)
        income_group = entity if entity_type == "income_group" else None

        records.append(
            {
                "entity": entity,
                "iso_code": iso_code,
                "entity_type": entity_type,
                "is_aggregate": int(entity_type in aggregate_types),
                "is_current_country_or_territory": int(
                    entity_type == "country_or_territory"
                ),
                "is_asean": int(entity in ASEAN_10),
                "is_source_variant": int(is_source_variant),
                "canonical_entity": canonical_entity,
                "continent": continent,
                "income_group": income_group,
            }
        )

    dim_entity = pd.DataFrame(records).sort_values("entity", kind="stable").reset_index(drop=True)
    duplicate_iso = dim_entity.loc[
        dim_entity["iso_code"].notna()
        & dim_entity["iso_code"].duplicated(keep=False),
        ["entity", "iso_code"],
    ]
    if not duplicate_iso.empty:
        raise Phase2Error(
            "An ISO/pseudo code maps to multiple entities:\n"
            + duplicate_iso.to_string(index=False)
        )
    valid_targets = set(dim_entity["entity"])
    invalid_targets = set(dim_entity["canonical_entity"].dropna()) - valid_targets
    if invalid_targets:
        raise Phase2Error(f"Unknown canonical_entity targets: {sorted(invalid_targets)}")

    checks = [
        (len(dim_entity) == EXPECTED_ENTITY_COUNT, "dim_entity must contain 256 entities."),
        (
            int(dim_entity["is_current_country_or_territory"].sum())
            == EXPECTED_CURRENT_ENTITY_COUNT,
            "Expected 215 current country/territory entities.",
        ),
        (int(dim_entity["is_asean"].sum()) == 10, "Expected exactly 10 ASEAN entities."),
        (int(dim_entity["is_aggregate"].sum()) == 40, "Expected 40 aggregate entities."),
        (
            dim_entity.loc[dim_entity["entity"].eq("Kosovo"), "entity_type"].iat[0]
            == "country_or_territory",
            "Kosovo must be a current country/territory.",
        ),
        (
            dim_entity.loc[dim_entity["entity"].eq("USSR"), "entity_type"].iat[0]
            == "historical",
            "USSR must be historical.",
        ),
        (
            dim_entity.loc[dim_entity["entity"].eq("World"), "entity_type"].iat[0]
            == "world",
            "World must be classified as world.",
        ),
    ]
    for passed, message in checks:
        if not passed:
            raise Phase2Error(message)
    return dim_entity


def audit_record(
    source_file: str,
    source_column: str,
    entity: str,
    year: int,
    old_value: float | None,
    new_value: float | None,
    action: str,
    reason: str,
) -> dict[str, object]:
    return {
        "source_file": source_file,
        "source_column": source_column,
        "entity": entity,
        "year": int(year),
        "old_value": old_value,
        "new_value": new_value,
        "action": action,
        "reason": reason,
    }


def build_fact_energy(
    catalog: pd.DataFrame, sources: dict[str, pd.DataFrame]
) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    fact_parts: list[pd.DataFrame] = []
    audit_rows: list[dict[str, object]] = []
    source_null_cells = 0

    canonical = catalog.loc[catalog["source_role"].eq("canonical")]
    for spec in canonical.itertuples(index=False):
        frame = sources[spec.source_file]
        source_values = frame[spec.source_column]
        in_window = frame["Year"].between(
            spec.analysis_start_year, spec.analysis_end_year
        )

        excluded = frame.loc[~in_window & source_values.notna(), ["Entity", "Year", spec.source_column]]
        for entity, year, old_value in excluded.itertuples(index=False, name=None):
            audit_rows.append(
                audit_record(
                    spec.source_file,
                    spec.source_column,
                    str(entity),
                    int(year),
                    float(old_value),
                    None,
                    "EXCLUDE_OUTSIDE_ANALYSIS_WINDOW",
                    f"Canonical window is {spec.analysis_start_year}-{spec.analysis_end_year}.",
                )
            )

        working = frame.loc[in_window, ["Entity", "Year", spec.source_column]].copy()
        source_null_cells += int(working[spec.source_column].isna().sum())
        working = working.loc[working[spec.source_column].notna()].copy()
        values = working[spec.source_column].astype("float64") * float(spec.conversion_factor)

        if spec.canonical_unit == "pct":
            invalid = values.lt(-PERCENT_EPSILON) | values.gt(100.0 + PERCENT_EPSILON)
            if invalid.any():
                bad = working.loc[invalid, ["Entity", "Year", spec.source_column]].head(10)
                raise Phase2Error(
                    f"{spec.metric_key}: percentage outside epsilon-adjustable range:\n{bad}"
                )

            snap_low = values.lt(0.0)
            snap_high = values.gt(100.0)
            for index in values.index[snap_low | snap_high]:
                old_value = float(values.loc[index])
                new_value = 0.0 if old_value < 0.0 else 100.0
                audit_rows.append(
                    audit_record(
                        spec.source_file,
                        spec.source_column,
                        str(working.loc[index, "Entity"]),
                        int(working.loc[index, "Year"]),
                        old_value,
                        new_value,
                        "SNAP_PERCENT_BOUNDARY",
                        f"Within {PERCENT_EPSILON} percentage points of the valid boundary.",
                    )
                )
            values = values.clip(lower=0.0, upper=100.0)

        if values.lt(0.0).any():
            bad = working.loc[values.lt(0.0), ["Entity", "Year", spec.source_column]].head(10)
            raise Phase2Error(f"{spec.metric_key}: negative values found:\n{bad}")

        threshold = float(spec.trace_threshold)
        value_class = np.select(
            [values.eq(0.0), values.lt(threshold)],
            ["Zero", "Trace"],
            default="Material",
        )
        fact_parts.append(
            pd.DataFrame(
                {
                    "entity": working["Entity"].astype(str),
                    "year": working["Year"].astype("int64"),
                    "metric_key": spec.metric_key,
                    "value": values.astype("float64"),
                    "value_class": value_class,
                    "source_file": spec.source_file,
                }
            )
        )

    fact = pd.concat(fact_parts, ignore_index=True).sort_values(
        ["entity", "year", "metric_key"], kind="stable"
    ).reset_index(drop=True)
    cleaning_audit = pd.DataFrame(
        audit_rows,
        columns=[
            "source_file",
            "source_column",
            "entity",
            "year",
            "old_value",
            "new_value",
            "action",
            "reason",
        ],
    ).sort_values(
        ["source_file", "source_column", "entity", "year", "action"],
        kind="stable",
    ).reset_index(drop=True)

    duplicates = fact.duplicated(["entity", "year", "metric_key"])
    if duplicates.any():
        raise Phase2Error(
            "Canonical fact contains duplicate semantic keys:\n"
            + fact.loc[duplicates, ["entity", "year", "metric_key", "source_file"]]
            .head(20)
            .to_string(index=False)
        )
    if not np.isfinite(fact["value"].to_numpy(dtype="float64")).all():
        raise Phase2Error("Canonical fact contains NaN or infinite values.")

    checks = [
        (len(fact) == EXPECTED_FACT_ROWS, f"Expected {EXPECTED_FACT_ROWS} fact rows, found {len(fact)}."),
        (source_null_cells == EXPECTED_SOURCE_NULL_CELLS, f"Expected {EXPECTED_SOURCE_NULL_CELLS} canonical source NULL cells, found {source_null_cells}."),
        (fact["metric_key"].nunique() == 16, "Expected 16 canonical metrics in fact."),
        (fact["entity"].nunique() == EXPECTED_ENTITY_COUNT, "Expected 256 entities in fact."),
        (int(fact["value"].eq(0.0).sum()) == EXPECTED_ZERO_ROWS, "Unexpected zero-value count."),
        (int(fact["value"].gt(0.0).sum()) == EXPECTED_POSITIVE_ROWS, "Unexpected positive-value count."),
        (len(fact[["entity", "year"]].drop_duplicates()) == EXPECTED_ENTITY_YEAR_KEYS, "Unexpected entity-year key count."),
        (not fact["year"].eq(2022).any(), "Canonical fact must not contain 2022."),
        (int(cleaning_audit["action"].eq("SNAP_PERCENT_BOUNDARY").sum()) == EXPECTED_PERCENT_SNAPS, "Expected exactly three percentage boundary snaps."),
    ]
    for passed, message in checks:
        if not passed:
            raise Phase2Error(message)
    return fact, cleaning_audit, source_null_cells


def validate_main_panel(fact: pd.DataFrame, dim_entity: pd.DataFrame) -> None:
    asean = set(dim_entity.loc[dim_entity["is_asean"].eq(1), "entity"])
    panel = fact.loc[
        fact["entity"].isin(asean)
        & fact["year"].between(MAIN_WINDOW_START, MAIN_WINDOW_END)
        & fact["metric_key"].isin(MAIN_METRIC_KEYS)
    ]
    expected_keys = {
        (entity, year, metric_key)
        for entity in asean
        for year in range(MAIN_WINDOW_START, MAIN_WINDOW_END + 1)
        for metric_key in MAIN_METRIC_KEYS
    }
    actual_keys = set(panel[["entity", "year", "metric_key"]].itertuples(index=False, name=None))
    if len(panel) != EXPECTED_MAIN_PANEL_ROWS or actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)[:20]
        extra = sorted(actual_keys - expected_keys)[:20]
        raise Phase2Error(
            f"Main ASEAN panel mismatch: rows={len(panel)}, missing={missing}, extra={extra}"
        )


def build_dim_year(fact: pd.DataFrame) -> pd.DataFrame:
    year_min = int(fact["year"].min())
    year_max = int(fact["year"].max())
    years = pd.Series(range(year_min, year_max + 1), name="year", dtype="int64")
    return pd.DataFrame(
        {
            "year": years,
            "is_main_asean_window": years.between(
                MAIN_WINDOW_START, MAIN_WINDOW_END
            ).astype("int64"),
        }
    )


def load_continuity_decisions() -> tuple[dict[tuple[str, str], str], int]:
    if not CONTINUITY_FILE.is_file():
        raise Phase2Error(
            f"Missing Phase 1 dependency: {CONTINUITY_FILE}. Run 01_profile.py first."
        )
    continuity = pd.read_csv(CONTINUITY_FILE)
    required = {"file_name", "Entity", "interpolation_decision", "coverage_pattern_effective"}
    missing = required - set(continuity.columns)
    if missing:
        raise Phase2Error(f"Continuity audit is missing columns: {sorted(missing)}")

    decisions = {
        (str(row.file_name), str(row.Entity)): str(row.interpolation_decision)
        for row in continuity.itertuples(index=False)
    }
    sampling_count = int(
        continuity["interpolation_decision"].eq("SAMPLING_GRID_NOT_MISSING").sum()
    )
    if sampling_count != 31:
        raise Phase2Error(
            f"Expected 31 sampling-grid series from Phase 1, found {sampling_count}."
        )
    return decisions, sampling_count


def build_missingness_audit(
    fact: pd.DataFrame,
    dim_entity: pd.DataFrame,
    dim_metric: pd.DataFrame,
) -> tuple[pd.DataFrame, int]:
    continuity_decisions, sampling_series_count = load_continuity_decisions()
    current_entities = dim_entity.loc[
        dim_entity["is_current_country_or_territory"].eq(1), "entity"
    ].tolist()
    current_set = set(current_entities)
    current_fact = fact.loc[fact["entity"].isin(current_set)]
    observed_by_metric_entity = {
        (metric_key, entity): set(group["year"].astype(int))
        for (metric_key, entity), group in current_fact.groupby(
            ["metric_key", "entity"], sort=False
        )
    }

    records: list[dict[str, object]] = []
    for metric in dim_metric.itertuples(index=False):
        applicable_years = range(metric.analysis_start_year, metric.analysis_end_year + 1)
        for entity in current_entities:
            observed = observed_by_metric_entity.get((metric.metric_key, entity), set())
            if observed:
                first_year = min(observed)
                last_year = max(observed)
            else:
                first_year = None
                last_year = None
            continuity_decision = continuity_decisions.get(
                (metric.source_file, entity), ""
            )

            for year in applicable_years:
                if year in observed:
                    continue
                if not observed:
                    missing_region = "NO_SERIES"
                    decision = "KEEP_NULL_NO_IMPUTE"
                elif year < first_year:
                    missing_region = "BEFORE_FIRST"
                    decision = "KEEP_NULL_NO_IMPUTE"
                elif year > last_year:
                    missing_region = "AFTER_LAST"
                    decision = "KEEP_NULL_NO_IMPUTE"
                elif continuity_decision == "SAMPLING_GRID_NOT_MISSING":
                    missing_region = "SAMPLING_GRID_NOT_MISSING"
                    decision = "KEEP_NULL_NOT_ANNUAL"
                else:
                    missing_region = "INTERNAL_GAP"
                    decision = "KEEP_NULL_EXCLUDE_FROM_YOY"
                records.append(
                    {
                        "entity": entity,
                        "year": year,
                        "metric_key": metric.metric_key,
                        "missing_region": missing_region,
                        "decision": decision,
                        "source_file": metric.source_file,
                    }
                )

    audit = pd.DataFrame(
        records,
        columns=[
            "entity",
            "year",
            "metric_key",
            "missing_region",
            "decision",
            "source_file",
        ],
    ).sort_values(["entity", "year", "metric_key"], kind="stable").reset_index(drop=True)

    if audit.duplicated(["entity", "year", "metric_key"]).any():
        raise Phase2Error("missingness_audit contains duplicate keys.")
    fact_keys = set(
        current_fact[["entity", "year", "metric_key"]].itertuples(
            index=False, name=None
        )
    )
    audit_keys = set(
        audit[["entity", "year", "metric_key"]].itertuples(index=False, name=None)
    )
    if fact_keys & audit_keys:
        raise Phase2Error("Observed fact keys also appear in missingness_audit.")

    asean = set(dim_entity.loc[dim_entity["is_asean"].eq(1), "entity"])
    main_missing = audit.loc[
        audit["entity"].isin(asean)
        & audit["year"].between(MAIN_WINDOW_START, MAIN_WINDOW_END)
        & audit["metric_key"].isin(MAIN_METRIC_KEYS)
    ]
    if not main_missing.empty:
        raise Phase2Error(
            "Main ASEAN panel unexpectedly contains missing cells:\n"
            + main_missing.head(20).to_string(index=False)
        )
    sampling_audit = audit.loc[
        audit["missing_region"].eq("SAMPLING_GRID_NOT_MISSING")
    ]
    audited_sampling_series = sampling_audit[["entity", "metric_key"]].drop_duplicates()
    if len(audited_sampling_series) != EXPECTED_CURRENT_SAMPLING_SERIES:
        raise Phase2Error(
            "Expected 23 current-country geothermal sampling-grid series in "
            f"missingness_audit, found {len(audited_sampling_series)}."
        )
    if len(sampling_audit) != EXPECTED_CURRENT_SAMPLING_MISSING_CELLS:
        raise Phase2Error(
            "Expected 184 current-country sampling-grid missing cells, "
            f"found {len(sampling_audit)}."
        )
    return audit, sampling_series_count


def build_tables() -> tuple[dict[str, pd.DataFrame], dict[str, int]]:
    catalog = catalog_frame()
    sources = discover_and_load_sources(catalog)
    validate_catalog(catalog, sources)
    dim_metric = build_dim_metric(catalog)
    dim_entity = build_dim_entity(sources)
    fact, cleaning_audit, source_null_cells = build_fact_energy(catalog, sources)
    validate_main_panel(fact, dim_entity)
    dim_year = build_dim_year(fact)
    missingness_audit, sampling_series_count = build_missingness_audit(
        fact, dim_entity, dim_metric
    )

    tables = {
        "source_metric_catalog": catalog,
        "dim_metric": dim_metric,
        "dim_entity": dim_entity,
        "dim_year": dim_year,
        "fact_energy": fact,
        "missingness_audit": missingness_audit,
        "cleaning_audit": cleaning_audit,
    }
    summary = {
        "source_files": len(sources),
        "catalog_rows": len(catalog),
        "canonical_metrics": len(dim_metric),
        "entities": len(dim_entity),
        "current_entities": int(dim_entity["is_current_country_or_territory"].sum()),
        "fact_rows": len(fact),
        "zero_rows": int(fact["value"].eq(0).sum()),
        "positive_rows": int(fact["value"].gt(0).sum()),
        "entity_year_keys": len(fact[["entity", "year"]].drop_duplicates()),
        "source_null_cells": source_null_cells,
        "missingness_rows": len(missingness_audit),
        "sampling_grid_series": sampling_series_count,
        "audited_sampling_series": EXPECTED_CURRENT_SAMPLING_SERIES,
        "audited_sampling_cells": EXPECTED_CURRENT_SAMPLING_MISSING_CELLS,
        "cleaning_audit_rows": len(cleaning_audit),
        "percent_snaps": int(cleaning_audit["action"].eq("SNAP_PERCENT_BOUNDARY").sum()),
    }
    return tables, summary


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(
        path,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
        float_format="%.12g",
    )


def build_sqlite_database(tables: dict[str, pd.DataFrame], db_path: Path) -> None:
    if not SCHEMA_FILE.is_file():
        raise Phase2Error(f"Missing SQLite schema: {SCHEMA_FILE}")
    if db_path.exists():
        db_path.unlink()

    schema_sql = SCHEMA_FILE.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.executescript(schema_sql)
        for table_name in [
            "source_metric_catalog",
            "dim_entity",
            "dim_year",
            "dim_metric",
            "fact_energy",
            "missingness_audit",
            "cleaning_audit",
        ]:
            tables[table_name].to_sql(
                table_name, conn, if_exists="append", index=False
            )
        conn.commit()

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = conn.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_keys:
            raise Phase2Error(
                f"SQLite integrity failure: integrity={integrity}, foreign_keys={foreign_keys[:10]}"
            )
        for table_name, frame in tables.items():
            observed = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
            if observed != len(frame):
                raise Phase2Error(
                    f"SQLite/CSV row mismatch for {table_name}: {observed} != {len(frame)}"
                )
        wide_rows = conn.execute("SELECT COUNT(*) FROM vw_wide").fetchone()[0]
        if wide_rows != EXPECTED_ENTITY_YEAR_KEYS:
            raise Phase2Error(
                f"vw_wide must contain {EXPECTED_ENTITY_YEAR_KEYS} rows, found {wide_rows}."
            )
    finally:
        # sqlite3.Connection's context manager commits/rolls back but does not
        # close the handle. Explicit close is required before os.replace on
        # Windows, otherwise the staged database remains locked.
        conn.close()


def ensure_database_replaceable(path: Path) -> None:
    if not path.exists():
        return
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(path, timeout=0.2)
        conn.execute("BEGIN EXCLUSIVE")
        conn.rollback()
    except sqlite3.Error as exc:
        raise Phase2Error(
            "The SQLite database is locked. Close the Navicat connection before rerunning Phase 2."
        ) from exc
    finally:
        if conn is not None:
            conn.close()


def sqlite_backup_replace(source_path: Path, target_path: Path) -> None:
    """Replace SQLite contents transactionally without renaming the target.

    Navicat can keep a Windows file handle open even when it holds no SQLite
    transaction. In that state os.replace is denied although SQLite writes are
    safe. The backup API replaces database contents through SQLite's locking
    protocol and therefore provides a safe Windows fallback.
    """
    source_uri = source_path.resolve().as_uri() + "?mode=ro"
    source_conn = sqlite3.connect(source_uri, uri=True)
    target_conn = sqlite3.connect(target_path, timeout=5.0)
    try:
        source_conn.backup(target_conn)
        target_conn.commit()
    finally:
        target_conn.close()
        source_conn.close()


def replace_outputs_atomically(staged_targets: list[tuple[Path, Path]]) -> None:
    if not staged_targets:
        return
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
            else:
                if target.resolve() == DB_PATH.resolve():
                    sqlite_backup_replace(backup, target)
                else:
                    shutil.copy2(backup, target)
        raise Phase2Error(
            "Could not atomically publish Phase 2 outputs; previous outputs were restored. "
            "If renewables.db is open in Navicat, close the connection and retry. "
            f"System error: {exc}"
        ) from exc


def publish_outputs(tables: dict[str, pd.DataFrame]) -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    ensure_database_replaceable(DB_PATH)

    with tempfile.TemporaryDirectory(prefix=".phase2_stage_", dir=OUTPUT) as temp_name:
        stage_dir = Path(temp_name)
        staged_targets: list[tuple[Path, Path]] = []
        for table_name, file_name in OUTPUT_TABLES.items():
            staged_path = stage_dir / file_name
            write_csv(tables[table_name], staged_path)
            staged_targets.append((staged_path, CLEAN / file_name))

        staged_db = stage_dir / DB_PATH.name
        build_sqlite_database(tables, staged_db)
        # Replace the database first: a late Navicat lock then leaves CSV untouched.
        staged_targets.insert(0, (staged_db, DB_PATH))
        replace_outputs_atomically(staged_targets)


def print_summary(summary: dict[str, int], check_only: bool) -> None:
    print("=" * 78)
    print("PHASE 2 - CLEAN BUILD")
    print("=" * 78)
    for key, value in summary.items():
        print(f"{key:26s}: {value:,}")
    print("mode                      : " + ("CHECK ONLY" if check_only else "PUBLISHED"))
    print("RESULT                    : PASS")
    print("=" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build clean Phase 2 CSV tables and SQLite data model."
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Build and validate all tables in memory without writing outputs.",
    )
    args = parser.parse_args()

    try:
        tables, summary = build_tables()
        if not args.check_only:
            publish_outputs(tables)
        print_summary(summary, args.check_only)
        return 0
    except (
        Phase2Error,
        OSError,
        sqlite3.Error,
        pd.errors.DatabaseError,
        pd.errors.ParserError,
    ) as exc:
        print(f"PHASE 2 FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
