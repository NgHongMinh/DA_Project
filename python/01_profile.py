"""Khao sat du lieu Phase 1 - hop nhat Step 1 den Step 7.

Script doc 17 CSV mot lan, chay toan bo kiem tra trong bo nho, sau do ghi
mot bao cao text tong hop va nam CSV chi tiet. Du lieu trong archive/ chi doc.

Cach dung (tu thu muc goc du an):
    python python\01_profile.py
"""

from __future__ import annotations

import re
import sys
import unicodedata
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import ARCHIVE, ASEAN_10, EXPECTED_CSV_COUNT, STATS  # noqa: E402


KEY_COLUMNS = ["Entity", "Code", "Year"]
JOIN_COLUMNS = ["Entity", "Year"]

SUMMARY_FILE = STATS / "00_phase1_summary.txt"
LEGACY_WORKBOOK = STATS / "00_data_profile.xlsx"
OVERLAP_DETAIL_FILE = STATS / "01_overlap_conflict_details.csv"
JOIN_KEY_DETAIL_FILE = STATS / "02_join_key_details.csv"
ASEAN_DETAIL_FILE = STATS / "03_asean_coverage_details.csv"
CONTINUITY_DETAIL_FILE = STATS / "04_year_continuity_details.csv"
LAST_YEAR_DETAIL_FILE = STATS / "05_last_year_check.csv"

RTOL = 1e-9
ATOL = 1e-12
FUZZY_THRESHOLD = 0.88
BASELINE_YEARS = 5
SEVERE_THRESHOLD_PCT = 50.0
FULL_THRESHOLD_PCT = 95.0

# Nguong tach "lech that" khoi nhieu lam tron o Step 3.
# Lam tron 2 chu so thap phan chi dich chuyen gia tri toi da 0.005 TWh, nen
# 0.05 TWh la bien an toan gap 10 lan. Phai vuot CA HAI nguong moi la MATERIAL:
# chi dung % thi 0 vs 0.005 TWh thanh lech 100%; chi dung tuyet doi thi 0.5 TWh
# tren 1200 TWh cua mot nuoc lon cung bi tinh la lech.
MATERIAL_ABS_TWH = 0.05
MATERIAL_REL_PCT = 1.0

PRIMARY_SOURCE_FILE = "03 modern-renewable-prod.csv"

METRIC_GROUPS = {
    "hydro_twh": [
        ("02 modern-renewable-energy-consumption.csv", "Hydro Generation - TWh"),
        (PRIMARY_SOURCE_FILE, "Electricity from hydro (TWh)"),
        ("05 hydropower-consumption.csv", "Electricity from hydro (TWh)"),
    ],
    "wind_twh": [
        ("02 modern-renewable-energy-consumption.csv", "Wind Generation - TWh"),
        (PRIMARY_SOURCE_FILE, "Electricity from wind (TWh)"),
        ("08 wind-generation.csv", "Electricity from wind (TWh)"),
    ],
    "solar_twh": [
        ("02 modern-renewable-energy-consumption.csv", "Solar Generation - TWh"),
        (PRIMARY_SOURCE_FILE, "Electricity from solar (TWh)"),
        ("12 solar-energy-consumption.csv", "Electricity from solar (TWh)"),
    ],
    "other_renewables_twh": [
        ("02 modern-renewable-energy-consumption.csv", "Geo Biomass Other - TWh"),
        (PRIMARY_SOURCE_FILE, "Other renewables including bioenergy (TWh)"),
    ],
}

PROFILE_COLUMNS = [
    "file_name", "metric_column", "row_count", "entity_count", "year_min",
    "year_max", "year_count", "missing_count", "missing_pct",
    "valid_numeric_count", "invalid_numeric_count", "zero_count",
    "zero_pct_of_valid", "min_value", "max_value",
]

COVERAGE_COLUMNS = [
    "tier_id", "file_count", "file_names", "entity_count_min",
    "entity_count_max", "entity_union_count", "entity_intersection_count",
    "entity_retention_pct", "year_min", "year_max", "common_year_count",
    "key_count_min", "key_count_max", "key_union_count",
    "key_intersection_count", "key_retention_pct",
]

OVERLAP_SUMMARY_COLUMNS = [
    "pair_id", "metric_group", "left_file", "left_column", "right_file",
    "right_column", "left_key_count", "right_key_count", "left_only_count",
    "right_only_count", "shared_key_count", "both_missing_count",
    "left_missing_only_count", "right_missing_only_count", "comparable_count",
    "exact_match_count", "approximate_match_count", "value_conflict_count",
    "immaterial_conflict_count", "material_conflict_count",
    "material_conflict_country_count", "material_conflict_aggregate_count",
    "match_pct", "material_match_pct", "mean_abs_diff", "max_abs_diff",
    "max_material_abs_diff", "classification", "recommendation",
]

OVERLAP_DETAIL_COLUMNS = [
    "pair_id", "metric_group", "conflict_type", "conflict_tier", "Entity",
    "is_aggregate", "Year", "left_file", "left_column", "left_value",
    "right_file", "right_column", "right_value", "abs_diff",
    "relative_diff_pct",
]

JOIN_SUMMARY_COLUMNS = [
    "check_id", "check_name", "result_count", "status", "meaning",
    "recommendation",
]

JOIN_DETAIL_COLUMNS = [
    "issue_type", "file_name", "Entity", "Year", "Code", "related_entity",
    "related_code", "normalized_entity", "file_count", "file_names",
    "similarity_score", "reason", "recommendation",
]

ASEAN_DETAIL_COLUMNS = [
    "country", "file_name", "present", "row_count", "year_min", "year_max",
    "year_count",
]

CONTINUITY_COLUMNS = [
    "file_name", "Entity", "is_asean", "file_year_min", "file_year_max",
    "entity_year_min", "entity_year_max", "observed_year_count",
    "expected_span_year_count", "internal_gap_count",
    "internal_gap_range_count", "max_internal_gap_length",
    "internal_gap_ranges", "leading_boundary_year_count",
    "trailing_boundary_year_count", "boundary_side", "coverage_pattern",
    "effective_file_year_max", "effective_trailing_boundary_year_count",
    "effective_boundary_side", "coverage_pattern_effective",
    "interpolation_decision",
]

LAST_YEAR_COLUMNS = [
    "file_name", "year", "row_count", "entity_count", "asean_entity_count",
    "previous_year", "previous_entity_count", "entity_baseline_median_5y",
    "asean_baseline_median_5y", "entity_coverage_pct", "asean_coverage_pct",
    "is_last_year", "last_year_status", "recommended_end_year",
]


class Phase1Error(Exception):
    """Loi dau vao hoac bat bien khien Phase 1 khong the tiep tuc."""


def metric_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in frame.columns if column not in KEY_COLUMNS]


def build_entity_code_index(sources: dict[str, pd.DataFrame]) -> dict[str, set[str]]:
    """Entity -> tap cac Code gan cho no tren toan bo 17 file.

    Tap rong nghia la Entity chua bao gio co Code. Trong bo du lieu nay do la
    dau hieu cua thuc the tong hop (chau luc, nhom thu nhap, khoi chinh tri),
    nhung Phase 2 moi phan loai chinh thuc.
    """
    codes: dict[str, set[str]] = {}
    for frame in sources.values():
        pairs = frame[["Entity", "Code"]].drop_duplicates()
        for entity, code in pairs.itertuples(index=False, name=None):
            bucket = codes.setdefault(entity, set())
            if pd.notna(code):
                bucket.add(str(code))
    return codes


def aggregate_flags(entity_codes: dict[str, set[str]]) -> dict[str, bool]:
    return {entity: not codes for entity, codes in entity_codes.items()}


def discover_csv_files() -> list[Path]:
    if not ARCHIVE.is_dir():
        raise Phase1Error(f"Khong tim thay thu muc du lieu: {ARCHIVE}")
    csv_files = sorted(ARCHIVE.glob("*.csv"), key=lambda path: path.name)
    if len(csv_files) != EXPECTED_CSV_COUNT:
        raise Phase1Error(
            f"Can {EXPECTED_CSV_COUNT} file CSV, nhung tim thay {len(csv_files)}."
        )
    return csv_files


def load_sources(csv_files: list[Path]) -> dict[str, pd.DataFrame]:
    """Doc mot lan va kiem tra schema, khoa cung kieu du lieu."""
    sources: dict[str, pd.DataFrame] = {}
    for csv_path in csv_files:
        try:
            frame = pd.read_csv(
                csv_path,
                dtype={"Entity": "string", "Code": "string"},
                low_memory=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise Phase1Error(f"Khong doc duoc {csv_path.name}: {exc}") from exc

        missing_keys = [column for column in KEY_COLUMNS if column not in frame.columns]
        if missing_keys:
            raise Phase1Error(
                f"{csv_path.name}: thieu cot khoa {', '.join(missing_keys)}."
            )
        if not metric_columns(frame):
            raise Phase1Error(f"{csv_path.name}: khong co cot chi so nao.")

        empty_entity = frame["Entity"].isna() | frame["Entity"].str.strip().eq("")
        if empty_entity.any():
            raise Phase1Error(
                f"{csv_path.name}: co {int(empty_entity.sum())} Entity rong."
            )

        numeric_year = pd.to_numeric(frame["Year"], errors="coerce")
        invalid_year = numeric_year.isna() | ~np.isfinite(numeric_year)
        invalid_year |= numeric_year.notna() & numeric_year.mod(1).ne(0)
        if invalid_year.any():
            examples = frame.loc[invalid_year, "Year"].head(5).tolist()
            raise Phase1Error(
                f"{csv_path.name}: co {int(invalid_year.sum())} Year khong hop le; "
                f"vi du: {examples}."
            )
        frame["Year"] = numeric_year.astype("int64")

        duplicate_mask = frame.duplicated(JOIN_COLUMNS, keep=False)
        if duplicate_mask.any():
            raise Phase1Error(
                f"{csv_path.name}: co {int(duplicate_mask.sum())} dong trung "
                "khoa (Entity, Year)."
            )
        if frame.empty:
            raise Phase1Error(f"{csv_path.name}: file khong co dong du lieu.")

        for column in metric_columns(frame):
            source_values = frame[column]
            numeric_values = pd.to_numeric(source_values, errors="coerce")
            invalid_value = source_values.notna() & (
                numeric_values.isna() | ~np.isfinite(numeric_values)
            )
            if invalid_value.any():
                examples = source_values.loc[invalid_value].head(5).tolist()
                raise Phase1Error(
                    f"{csv_path.name} / {column}: co {int(invalid_value.sum())} "
                    f"gia tri khong phai so huu han; vi du: {examples}."
                )
            frame[column] = numeric_values
        sources[csv_path.name] = frame
    return sources


# Step 1 --------------------------------------------------------------------
def build_profile(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for file_name, frame in sources.items():
        row_count = len(frame)
        for column in metric_columns(frame):
            values = frame[column]
            missing_count = int(values.isna().sum())
            valid = values.dropna()
            valid_count = len(valid)
            zero_count = int(valid.eq(0).sum())
            records.append(
                {
                    "file_name": file_name,
                    "metric_column": column,
                    "row_count": row_count,
                    "entity_count": int(frame["Entity"].nunique()),
                    "year_min": int(frame["Year"].min()),
                    "year_max": int(frame["Year"].max()),
                    "year_count": int(frame["Year"].nunique()),
                    "missing_count": missing_count,
                    "missing_pct": round(missing_count / row_count * 100, 4),
                    "valid_numeric_count": valid_count,
                    "invalid_numeric_count": 0,
                    "zero_count": zero_count,
                    "zero_pct_of_valid": (
                        round(zero_count / valid_count * 100, 4)
                        if valid_count else 0.0
                    ),
                    "min_value": valid.min() if valid_count else pd.NA,
                    "max_value": valid.max() if valid_count else pd.NA,
                }
            )
    return pd.DataFrame.from_records(records, columns=PROFILE_COLUMNS)


# Step 2 --------------------------------------------------------------------
def union_all(sets: list[set[object]]) -> set[object]:
    return set().union(*sets)


def intersection_all(sets: list[set[object]]) -> set[object]:
    first, *rest = sets
    return first.intersection(*rest)


def coverage_item(file_name: str, frame: pd.DataFrame) -> dict[str, object]:
    entities = set(frame["Entity"])
    years = set(frame["Year"])
    keys = set(frame[JOIN_COLUMNS].itertuples(index=False, name=None))
    return {
        "file_name": file_name,
        "entity_count": len(entities),
        "year_min": min(years),
        "year_max": max(years),
        "entities": entities,
        "years": years,
        "keys": keys,
    }


def summarize_coverage(
    tier_id: str, items: list[dict[str, object]]
) -> dict[str, object]:
    entity_sets = [item["entities"] for item in items]
    year_sets = [item["years"] for item in items]
    key_sets = [item["keys"] for item in items]
    entity_union = union_all(entity_sets)
    entity_intersection = intersection_all(entity_sets)
    year_intersection = intersection_all(year_sets)
    key_union = union_all(key_sets)
    key_intersection = intersection_all(key_sets)
    entity_counts = [len(values) for values in entity_sets]
    key_counts = [len(values) for values in key_sets]
    return {
        "tier_id": tier_id,
        "file_count": len(items),
        "file_names": " | ".join(item["file_name"] for item in items),
        "entity_count_min": min(entity_counts),
        "entity_count_max": max(entity_counts),
        "entity_union_count": len(entity_union),
        "entity_intersection_count": len(entity_intersection),
        "entity_retention_pct": round(
            len(entity_intersection) / len(entity_union) * 100, 4
        ),
        "year_min": min(item["year_min"] for item in items),
        "year_max": max(item["year_max"] for item in items),
        "common_year_count": len(year_intersection),
        "key_count_min": min(key_counts),
        "key_count_max": max(key_counts),
        "key_union_count": len(key_union),
        "key_intersection_count": len(key_intersection),
        "key_retention_pct": round(
            len(key_intersection) / len(key_union) * 100, 4
        ),
    }


def build_coverage_tiers(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    items = [coverage_item(name, frame) for name, frame in sources.items()]
    grouped: dict[tuple[int, int, int], list[dict[str, object]]] = {}
    for item in items:
        signature = (item["entity_count"], item["year_min"], item["year_max"])
        grouped.setdefault(signature, []).append(item)
    signatures = sorted(
        grouped,
        key=lambda signature: (
            -signature[0], -(signature[2] - signature[1] + 1), signature[1]
        ),
    )
    records = [
        summarize_coverage(f"T{position}", grouped[signature])
        for position, signature in enumerate(signatures, start=1)
    ]
    records.append(summarize_coverage("ALL_FILES", items))
    return pd.DataFrame.from_records(records, columns=COVERAGE_COLUMNS)


# Step 3 --------------------------------------------------------------------
def source_metric(
    sources: dict[str, pd.DataFrame], file_name: str, column: str
) -> dict[str, object]:
    if file_name not in sources or column not in sources[file_name].columns:
        raise Phase1Error(f"Khong tim thay dai luong: {file_name} / {column}")
    return {
        "file_name": file_name,
        "metric_column": column,
        "metric_count": len(metric_columns(sources[file_name])),
        "frame": sources[file_name][[*JOIN_COLUMNS, column]].copy(),
    }


def choose_redundant_source(
    left: dict[str, object], right: dict[str, object], relation: str
) -> tuple[str, str]:
    if relation == "left_subset":
        return right["file_name"], left["file_name"]
    if relation == "right_subset":
        return left["file_name"], right["file_name"]
    if left["metric_count"] > right["metric_count"]:
        return left["file_name"], right["file_name"]
    if right["metric_count"] > left["metric_count"]:
        return right["file_name"], left["file_name"]
    return "", ""


def compare_pair(
    metric_group: str,
    left: dict[str, object],
    right: dict[str, object],
    is_aggregate: dict[str, bool],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    left_file, right_file = left["file_name"], right["file_name"]
    left_column, right_column = left["metric_column"], right["metric_column"]
    pair_id = f"{metric_group}__{left_file[:2]}_{right_file[:2]}"
    left_frame = left["frame"].rename(columns={left_column: "left_value"})
    right_frame = right["frame"].rename(columns={right_column: "right_value"})
    merged = left_frame.merge(
        right_frame, on=JOIN_COLUMNS, how="outer", indicator=True,
        validate="one_to_one",
    )
    left_only = merged["_merge"].eq("left_only")
    right_only = merged["_merge"].eq("right_only")
    shared = merged["_merge"].eq("both")
    left_missing = merged["left_value"].isna()
    right_missing = merged["right_value"].isna()
    both_missing = shared & left_missing & right_missing
    left_missing_only = shared & left_missing & ~right_missing
    right_missing_only = shared & ~left_missing & right_missing
    comparable = shared & ~left_missing & ~right_missing

    exact = pd.Series(False, index=merged.index)
    close = pd.Series(False, index=merged.index)
    exact.loc[comparable] = merged.loc[comparable, "left_value"].eq(
        merged.loc[comparable, "right_value"]
    )
    close.loc[comparable] = np.isclose(
        merged.loc[comparable, "left_value"],
        merged.loc[comparable, "right_value"], rtol=RTOL, atol=ATOL,
    )
    approximate_only = comparable & close & ~exact
    value_conflict = comparable & ~close
    differences = (
        merged.loc[comparable, "left_value"]
        - merged.loc[comparable, "right_value"]
    ).abs()
    comparable_count = int(comparable.sum())
    exact_count = int(exact.sum())
    approximate_count = int(approximate_only.sum())
    conflict_count = int(value_conflict.sum())

    # Phan tang xung dot: tach nhieu lam tron khoi lech that su.
    abs_diff_all = (merged["left_value"] - merged["right_value"]).abs()
    scale = pd.concat(
        [merged["left_value"].abs(), merged["right_value"].abs()], axis=1
    ).max(axis=1)
    rel_diff_all = pd.Series(0.0, index=merged.index)
    nonzero_scale = scale.gt(0) & scale.notna()
    rel_diff_all.loc[nonzero_scale] = (
        abs_diff_all.loc[nonzero_scale] / scale.loc[nonzero_scale] * 100
    )
    material = (
        value_conflict
        & abs_diff_all.gt(MATERIAL_ABS_TWH)
        & rel_diff_all.gt(MATERIAL_REL_PCT)
    )
    immaterial = value_conflict & ~material
    entity_is_aggregate = merged["Entity"].map(is_aggregate).fillna(False)
    material_aggregate = material & entity_is_aggregate
    material_country = material & ~entity_is_aggregate
    material_count = int(material.sum())
    immaterial_count = int(immaterial.sum())

    left_non_null_keys = set(
        left_frame.loc[left_frame["left_value"].notna(), JOIN_COLUMNS].itertuples(
            index=False, name=None
        )
    )
    right_non_null_keys = set(
        right_frame.loc[right_frame["right_value"].notna(), JOIN_COLUMNS].itertuples(
            index=False, name=None
        )
    )
    if left_non_null_keys < right_non_null_keys:
        subset_relation = "left_subset"
    elif right_non_null_keys < left_non_null_keys:
        subset_relation = "right_subset"
    elif left_non_null_keys == right_non_null_keys:
        subset_relation = "equal"
    else:
        subset_relation = "neither"

    same_keys = not left_only.any() and not right_only.any()
    no_missing_mismatch = not left_missing_only.any() and not right_missing_only.any()
    all_exact = comparable_count > 0 and exact_count == comparable_count
    all_close = comparable_count > 0 and exact_count + approximate_count == comparable_count
    if comparable_count == 0:
        classification = "insufficient_overlap"
        recommendation = "Khong du gia tri chung de ket luan; xem lai pham vi nguon."
    elif material_count:
        classification = "conflicting_overlap"
        where = (
            "chu yeu o thuc the tong hop"
            if int(material_aggregate.sum()) >= int(material_country.sum())
            else "co ca o cap quoc gia"
        )
        recommendation = (
            f"Giu tach rieng ({where}); kiem tra dinh nghia/phien ban nguon truoc Phase 2."
        )
    elif conflict_count:
        classification = "immaterial_variant"
        recommendation = (
            "Chenh lech khong vuot nguong material; co the coi la cung mot dai luong, "
            "van chon mot nguon canonical de tranh trung lap."
        )
    elif same_keys and no_missing_mismatch and all_exact:
        classification = "exact_duplicate"
        keep, drop = choose_redundant_source(left, right, "equal")
        recommendation = (
            f"Chi giu {keep}; {drop} la ung vien loai de tranh trung lap."
            if keep else "Hai nguon trung hoan toan; chi giu mot nguon sau review provenance."
        )
    elif all_exact and subset_relation in {"left_subset", "right_subset", "equal"}:
        classification = "redundant_subset"
        keep, drop = choose_redundant_source(left, right, subset_relation)
        recommendation = (
            f"Uu tien {keep}; {drop} la ung vien loai de tranh trung lap."
            if keep else "Do phu khong rong tuong duong; chi giu mot nguon sau review provenance."
        )
    elif all_close:
        classification = "approximate_duplicate"
        recommendation = "Kiem tra quy tac lam tron; chi giu mot nguon neu sai lech chap nhan duoc."
    else:
        classification = "insufficient_overlap"
        recommendation = "Do phu khong long nhau; chua du co so ket luan trung lap."

    summary = {
        "pair_id": pair_id, "metric_group": metric_group,
        "left_file": left_file, "left_column": left_column,
        "right_file": right_file, "right_column": right_column,
        "left_key_count": len(left_frame), "right_key_count": len(right_frame),
        "left_only_count": int(left_only.sum()),
        "right_only_count": int(right_only.sum()),
        "shared_key_count": int(shared.sum()),
        "both_missing_count": int(both_missing.sum()),
        "left_missing_only_count": int(left_missing_only.sum()),
        "right_missing_only_count": int(right_missing_only.sum()),
        "comparable_count": comparable_count, "exact_match_count": exact_count,
        "approximate_match_count": approximate_count,
        "value_conflict_count": conflict_count,
        "immaterial_conflict_count": immaterial_count,
        "material_conflict_count": material_count,
        "material_conflict_country_count": int(material_country.sum()),
        "material_conflict_aggregate_count": int(material_aggregate.sum()),
        "match_pct": round((exact_count + approximate_count) / comparable_count * 100, 4) if comparable_count else 0.0,
        "material_match_pct": round((comparable_count - material_count) / comparable_count * 100, 4) if comparable_count else 0.0,
        "mean_abs_diff": differences.mean() if comparable_count else pd.NA,
        "max_abs_diff": differences.max() if comparable_count else pd.NA,
        "max_material_abs_diff": abs_diff_all.loc[material].max() if material_count else pd.NA,
        "classification": classification, "recommendation": recommendation,
    }

    detail_records: list[dict[str, object]] = []
    for conflict_type, mask in [
        ("VALUE_CONFLICT", value_conflict),
        ("MISSING_MISMATCH", left_missing_only | right_missing_only),
    ]:
        subset = merged.loc[mask]
        tiers = material.loc[mask].map({True: "MATERIAL", False: "IMMATERIAL"})
        for row, tier in zip(subset.itertuples(index=False), tiers):
            if conflict_type == "VALUE_CONFLICT":
                abs_diff = abs(row.left_value - row.right_value)
                scale = max(abs(row.left_value), abs(row.right_value))
                relative_diff_pct = abs_diff / scale * 100 if scale else 0.0
                conflict_tier = tier
            else:
                abs_diff = pd.NA
                relative_diff_pct = pd.NA
                conflict_tier = ""
            detail_records.append(
                {
                    "pair_id": pair_id, "metric_group": metric_group,
                    "conflict_type": conflict_type,
                    "conflict_tier": conflict_tier, "Entity": row.Entity,
                    "is_aggregate": is_aggregate.get(row.Entity, False),
                    "Year": row.Year, "left_file": left_file,
                    "left_column": left_column, "left_value": row.left_value,
                    "right_file": right_file, "right_column": right_column,
                    "right_value": row.right_value, "abs_diff": abs_diff,
                    "relative_diff_pct": relative_diff_pct,
                }
            )
    return summary, detail_records


def build_overlap_comparisons(
    sources: dict[str, pd.DataFrame],
    is_aggregate: dict[str, bool],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    for metric_group, specs in METRIC_GROUPS.items():
        loaded = [source_metric(sources, *spec) for spec in specs]
        for left, right in combinations(loaded, 2):
            summary, pair_details = compare_pair(
                metric_group, left, right, is_aggregate
            )
            summaries.append(summary)
            details.extend(pair_details)
    return (
        pd.DataFrame.from_records(summaries, columns=OVERLAP_SUMMARY_COLUMNS),
        pd.DataFrame.from_records(details, columns=OVERLAP_DETAIL_COLUMNS),
    )


# Step 4 --------------------------------------------------------------------
def normalize_entity(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return re.sub(r"\s+", " ", normalized.strip()).casefold()


def build_join_key_audit(
    sources: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    parts = []
    for file_name, frame in sources.items():
        part = frame[["Entity", "Code", "Year"]].copy()
        part["file_name"] = file_name
        parts.append(part)
    all_rows = pd.concat(parts, ignore_index=True)
    entity_file = all_rows[["Entity", "Code", "file_name"]].drop_duplicates()
    entity_file["normalized_entity"] = entity_file["Entity"].map(normalize_entity)
    details: list[dict[str, object]] = []

    collapsed = entity_file["Entity"].map(lambda value: re.sub(r"\s+", " ", value.strip()))
    whitespace_mask = entity_file["Entity"].ne(collapsed)
    for row in entity_file.loc[whitespace_mask].itertuples(index=False):
        details.append({
            "issue_type": "WHITESPACE_VARIANT", "file_name": row.file_name,
            "Entity": row.Entity, "Code": row.Code,
            "normalized_entity": row.normalized_entity,
            "reason": "Ten thay doi sau khi strip/collapse khoang trang.",
            "recommendation": "Chuan hoa khoang trang truoc khi join.",
        })

    normalized_groups = entity_file.groupby("normalized_entity")["Entity"].agg(
        lambda values: sorted(set(values))
    )
    normalized_collisions = normalized_groups[normalized_groups.map(len).gt(1)]
    for normalized, variants in normalized_collisions.items():
        details.append({
            "issue_type": "NORMALIZED_NAME_COLLISION", "Entity": variants[0],
            "related_entity": " | ".join(variants[1:]),
            "normalized_entity": normalized,
            "reason": "Nhieu ten goc tro thanh mot ten sau chuan hoa.",
            "recommendation": "Review thu cong truoc khi gop ten.",
        })

    with_code = entity_file.dropna(subset=["Code"])
    code_to_entities = with_code.groupby("Code")["Entity"].agg(
        lambda values: sorted(set(values))
    )
    code_collisions = code_to_entities[code_to_entities.map(len).gt(1)]
    for code, entities in code_collisions.items():
        details.append({
            "issue_type": "CODE_TO_MULTIPLE_ENTITIES", "Entity": entities[0],
            "Code": code, "related_entity": " | ".join(entities[1:]),
            "reason": "Mot Code gan cho nhieu ten Entity.",
            "recommendation": "Dung Code de review alias; khong auto-merge.",
        })

    entity_to_codes = with_code.groupby("Entity")["Code"].agg(
        lambda values: sorted(set(values))
    )
    entity_collisions = entity_to_codes[entity_to_codes.map(len).gt(1)]
    for entity, codes in entity_collisions.items():
        details.append({
            "issue_type": "ENTITY_TO_MULTIPLE_CODES", "Entity": entity,
            "Code": codes[0], "related_code": " | ".join(codes[1:]),
            "normalized_entity": normalize_entity(entity),
            "reason": "Mot Entity gan cho nhieu Code.",
            "recommendation": "Review ma quoc gia truoc khi join.",
        })

    blank_code_rows = entity_file[entity_file["Code"].isna()]
    blank_code_groups = blank_code_rows.groupby("Entity")["file_name"].agg(
        lambda values: sorted(set(values))
    )
    for entity, file_names in blank_code_groups.items():
        details.append({
            "issue_type": "BLANK_CODE_ENTITY", "Entity": entity,
            "normalized_entity": normalize_entity(entity),
            "file_count": len(file_names), "file_names": " | ".join(file_names),
            "reason": "Entity khong co Code trong it nhat mot file.",
            "recommendation": "Join bang Entity; Phase 2 phan loai quoc gia/vung tong hop.",
        })

    entity_codes = {
        entity: set(values.dropna())
        for entity, values in entity_file.groupby("Entity")["Code"]
    }
    entities = sorted(entity_file["Entity"].unique())
    normalized = {entity: normalize_entity(entity) for entity in entities}
    fuzzy_count = 0
    safe_alias_count = 0
    for index, left_entity in enumerate(entities):
        for right_entity in entities[index + 1:]:
            score = SequenceMatcher(
                None, normalized[left_entity], normalized[right_entity]
            ).ratio()
            if score < FUZZY_THRESHOLD:
                continue
            fuzzy_count += 1
            left_codes = entity_codes[left_entity]
            right_codes = entity_codes[right_entity]
            same_known_code = bool(left_codes and left_codes == right_codes)
            if same_known_code:
                safe_alias_count += 1
                reason = "Ten gan giong va co cung Code; alias can review."
                recommendation = "Review thu cong; co the tao bang alias neu dung cung thuc the."
            elif left_codes and right_codes and left_codes.isdisjoint(right_codes):
                reason = "Ten gan giong nhung Code khac nhau; day la hai thuc the khac nhau."
                recommendation = "Khong fuzzy-match."
            else:
                reason = "Ten gan giong nhung thieu Code de xac nhan quan he."
                recommendation = "Khong auto-merge; review ngu nghia neu can."
            details.append({
                "issue_type": "FUZZY_CANDIDATE", "Entity": left_entity,
                "Code": " | ".join(sorted(left_codes)),
                "related_entity": right_entity,
                "related_code": " | ".join(sorted(right_codes)),
                "normalized_entity": normalized[left_entity],
                "similarity_score": round(score, 4), "reason": reason,
                "recommendation": recommendation,
            })

    file_counts = entity_file.groupby("Entity")["file_name"].nunique()
    unique_count = int(entity_file["Entity"].nunique())
    all_files_count = int(file_counts.eq(len(sources)).sum())
    # Dem lai that su thay vi tin vao viec load_sources() da raise neu co trung.
    duplicate_key_rows = sum(
        int(frame.duplicated(JOIN_COLUMNS, keep=False).sum())
        for frame in sources.values()
    )
    rows = [
        ("J1", "unique_exact_entities", unique_count, "INFO", "So ten Entity chinh xac trong hop cua 17 file.", "Dung lam tap ten goc; chua dong nghia tat ca la quoc gia."),
        ("J2", "entities_present_in_all_files", all_files_count, "INFO", "So Entity co mat trong du 17 file.", "Khong INNER JOIN tat ca file chi de giu nhom nay."),
        ("J3", "whitespace_variants", int(whitespace_mask.sum()), "PASS" if not whitespace_mask.any() else "REVIEW", "Ten co khoang trang dau/cuoi hoac lap khoang trang.", "Exact match an toan ve khoang trang." if not whitespace_mask.any() else "Chuan hoa khoang trang."),
        ("J4", "normalized_name_collisions", len(normalized_collisions), "PASS" if normalized_collisions.empty else "REVIEW", "So nhom ten xung dot sau NFKC/casefold/strip.", "Khong can chuan hoa ten de join." if normalized_collisions.empty else "Review tung nhom bien the."),
        ("J5", "codes_mapping_multiple_entities", len(code_collisions), "PASS" if code_collisions.empty else "REVIEW", "So Code duoc gan cho nhieu ten Entity.", "Code nhat quan tren cac dong co ma." if code_collisions.empty else "Review alias theo Code."),
        ("J6", "entities_mapping_multiple_codes", len(entity_collisions), "PASS" if entity_collisions.empty else "REVIEW", "So Entity duoc gan cho nhieu Code.", "Quan he Entity-Code nhat quan." if entity_collisions.empty else "Review ma quoc gia."),
        ("J7", "duplicate_entity_year_rows", duplicate_key_rows, "PASS" if duplicate_key_rows == 0 else "FAIL", "So dong thuoc khoa (Entity, Year) trung trong tung file.", "Khoa (Entity, Year) duy nhat trong tung file." if duplicate_key_rows == 0 else "Khu trung khoa truoc khi join."),
        ("J8", "entities_with_blank_code", len(blank_code_groups), "REVIEW", "So Entity thieu Code trong it nhat mot file.", "Khong join chi bang Code; giu Entity lam khoa Phase 1."),
        ("J9", "fuzzy_candidate_pairs", fuzzy_count, "REVIEW" if fuzzy_count else "PASS", f"So cap ten co similarity >= {FUZZY_THRESHOLD}.", "Khong auto-fuzzy; cac cap gan ten phai review ngu nghia."),
        ("J10", "safe_code_supported_aliases", safe_alias_count, "INFO", "Cap ten gan giong duoc cung Code ho tro la alias.", "Exact match duoc uu tien; hien khong co alias can auto-merge." if safe_alias_count == 0 else "Review va lap bang alias thu cong."),
    ]
    return (
        pd.DataFrame(rows, columns=JOIN_SUMMARY_COLUMNS),
        pd.DataFrame.from_records(details, columns=JOIN_DETAIL_COLUMNS),
    )


# Step 5 --------------------------------------------------------------------
def build_asean_coverage(
    sources: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    records: list[dict[str, object]] = []
    for file_name, frame in sources.items():
        for country in ASEAN_10:
            country_rows = frame.loc[frame["Entity"].eq(country)]
            present = not country_rows.empty
            records.append({
                "country": country, "file_name": file_name, "present": present,
                "row_count": len(country_rows),
                "year_min": int(country_rows["Year"].min()) if present else pd.NA,
                "year_max": int(country_rows["Year"].max()) if present else pd.NA,
                "year_count": int(country_rows["Year"].nunique()) if present else 0,
            })
    details = pd.DataFrame.from_records(records, columns=ASEAN_DETAIL_COLUMNS)
    matrix = details.pivot(index="country", columns="file_name", values="present")
    matrix = matrix.reindex(index=ASEAN_10, columns=list(sources))
    compact_matrix = matrix.rename(columns={name: name[:2] for name in sources})
    compact_matrix = compact_matrix.map(lambda value: "Y" if value else "-").reset_index()
    compact_matrix["files_present"] = matrix.sum(axis=1).astype(int).values
    country_summary = (
        details.groupby("country", sort=False)["present"].sum().reindex(ASEAN_10)
        .rename("files_present").reset_index()
    )
    country_summary["coverage_pct"] = (
        country_summary["files_present"] / len(sources) * 100
    ).round(2)
    file_records = []
    for file_name in sources:
        rows = details.loc[details["file_name"].eq(file_name)]
        present_countries = set(rows.loc[rows["present"], "country"])
        file_records.append({
            "file_name": file_name,
            "asean_countries_present": len(present_countries),
            "asean_coverage_pct": round(len(present_countries) / len(ASEAN_10) * 100, 2),
            "countries_missing": " | ".join(
                country for country in ASEAN_10 if country not in present_countries
            ),
        })
    return compact_matrix, details, pd.DataFrame(file_records), country_summary


# Step 6 --------------------------------------------------------------------
def split_consecutive_ranges(years: list[int]) -> list[tuple[int, int]]:
    if not years:
        return []
    ranges: list[tuple[int, int]] = []
    start = previous = years[0]
    for year in years[1:]:
        if year == previous + 1:
            previous = year
            continue
        ranges.append((start, previous))
        start = previous = year
    ranges.append((start, previous))
    return ranges


def format_ranges(ranges: list[tuple[int, int]]) -> str:
    return " | ".join(
        str(start) if start == end else f"{start}-{end}" for start, end in ranges
    )


def boundary_side(leading: int, trailing: int) -> str:
    if leading and trailing:
        return "BOTH"
    if leading:
        return "LEADING"
    if trailing:
        return "TRAILING"
    return "NONE"


def continuity_pattern(internal: int, leading: int, trailing: int) -> str:
    if internal and (leading or trailing):
        return "INTERNAL_AND_BOUNDARY"
    if internal:
        return "INTERNAL_GAPS"
    if leading or trailing:
        return "BOUNDARY_ONLY"
    return "FULL_SPAN"


def is_sampling_grid(ranges: list[tuple[int, int]]) -> bool:
    """Cac khoang trong deu dai bang nhau va cach deu nhau => luoi lay mau.

    Vi du file 17: 1990, 1995, 2000 roi hang nam. Doan dau la lich bao cao 5 nam
    mot lan, khong phai du lieu bi mat. Khong doi hoi ca chuoi deu nhau vi nhieu
    nguon chuyen tu moc 5 nam sang hang nam giua chung.

    Can it nhat 2 khoang: mot khoang don le khong du co so ket luan la nhip lay
    mau (vi du CIS (BP) thieu lien tuc 1966-1989 la thieu that).
    """
    if len(ranges) < 2:
        return False
    lengths = {end - start + 1 for start, end in ranges}
    if len(lengths) != 1:
        return False
    steps = {
        ranges[index + 1][0] - ranges[index][0] for index in range(len(ranges) - 1)
    }
    return len(steps) == 1


def build_year_continuity(
    sources: dict[str, pd.DataFrame],
    effective_year_max: dict[str, int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    records: list[dict[str, object]] = []
    for file_name, frame in sources.items():
        file_year_min, file_year_max = int(frame["Year"].min()), int(frame["Year"].max())
        effective_max = effective_year_max.get(file_name, file_year_max)
        for entity, rows in frame.groupby("Entity", sort=True):
            observed = sorted(set(rows["Year"].astype(int)))
            entity_min, entity_max = observed[0], observed[-1]
            expected = set(range(entity_min, entity_max + 1))
            gaps = sorted(expected.difference(observed))
            ranges = split_consecutive_ranges(gaps)
            lengths = [end - start + 1 for start, end in ranges]
            leading, trailing = entity_min - file_year_min, file_year_max - entity_max
            effective_trailing = max(0, effective_max - entity_max)
            if not gaps:
                decision = "NOT_NEEDED"
            elif is_sampling_grid(ranges):
                decision = "SAMPLING_GRID_NOT_MISSING"
            else:
                decision = "DO_NOT_INTERPOLATE_REVIEW_SOURCE"
            records.append({
                "file_name": file_name, "Entity": entity,
                "is_asean": entity in ASEAN_10,
                "file_year_min": file_year_min, "file_year_max": file_year_max,
                "entity_year_min": entity_min, "entity_year_max": entity_max,
                "observed_year_count": len(observed),
                "expected_span_year_count": len(expected),
                "internal_gap_count": len(gaps),
                "internal_gap_range_count": len(ranges),
                "max_internal_gap_length": max(lengths, default=0),
                "internal_gap_ranges": format_ranges(ranges),
                "leading_boundary_year_count": leading,
                "trailing_boundary_year_count": trailing,
                "boundary_side": boundary_side(leading, trailing),
                "coverage_pattern": continuity_pattern(len(gaps), leading, trailing),
                "effective_file_year_max": effective_max,
                "effective_trailing_boundary_year_count": effective_trailing,
                "effective_boundary_side": boundary_side(leading, effective_trailing),
                "coverage_pattern_effective": continuity_pattern(
                    len(gaps), leading, effective_trailing
                ),
                "interpolation_decision": decision,
            })
    details = pd.DataFrame.from_records(records, columns=CONTINUITY_COLUMNS)
    summaries = []
    for file_name, rows in details.groupby("file_name", sort=False):
        summaries.append({
            "file_name": file_name, "entity_count": len(rows),
            "full_span_entities": int(rows["coverage_pattern"].eq("FULL_SPAN").sum()),
            "full_span_effective_entities": int(
                rows["coverage_pattern_effective"].eq("FULL_SPAN").sum()
            ),
            "boundary_only_entities": int(rows["coverage_pattern"].eq("BOUNDARY_ONLY").sum()),
            "boundary_only_effective_entities": int(
                rows["coverage_pattern_effective"].eq("BOUNDARY_ONLY").sum()
            ),
            "entities_with_internal_gaps": int(rows["internal_gap_count"].gt(0).sum()),
            "internal_gap_years": int(rows["internal_gap_count"].sum()),
            "sampling_grid_entities": int(
                rows["interpolation_decision"].eq("SAMPLING_GRID_NOT_MISSING").sum()
            ),
            "asean_entities_with_internal_gaps": int(
                (rows["is_asean"] & rows["internal_gap_count"].gt(0)).sum()
            ),
        })
    return details, pd.DataFrame(summaries)


# Step 7 --------------------------------------------------------------------
def coverage_pct(current: int, baseline: float) -> float:
    if pd.isna(baseline):
        return np.nan
    if baseline == 0:
        return 100.0 if current == 0 else np.nan
    return round(current / baseline * 100, 4)


def classify_last_year(entity_pct: float, asean_pct: float) -> str:
    values = [value for value in [entity_pct, asean_pct] if not pd.isna(value)]
    if not values:
        return "INSUFFICIENT_BASELINE"
    minimum = min(values)
    if minimum < SEVERE_THRESHOLD_PCT:
        return "TRUNCATED_SEVERE"
    if minimum < FULL_THRESHOLD_PCT:
        return "PARTIAL_REVIEW"
    return "FULL"


def build_last_year_check(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for file_name, frame in sources.items():
        yearly = (
            frame.groupby("Year", sort=True)
            .agg(
                row_count=("Entity", "size"),
                entity_count=("Entity", "nunique"),
                asean_entity_count=("Entity", lambda values: values[values.isin(ASEAN_10)].nunique()),
            ).reset_index()
        )
        entity_counts = yearly["entity_count"].tolist()
        asean_counts = yearly["asean_entity_count"].tolist()
        years = yearly["Year"].astype(int).tolist()
        for index, row in yearly.iterrows():
            start = max(0, index - BASELINE_YEARS)
            prior_entities, prior_asean = entity_counts[start:index], asean_counts[start:index]
            entity_baseline = float(np.median(prior_entities)) if prior_entities else np.nan
            asean_baseline = float(np.median(prior_asean)) if prior_asean else np.nan
            entity_pct = coverage_pct(int(row["entity_count"]), entity_baseline)
            asean_pct = coverage_pct(int(row["asean_entity_count"]), asean_baseline)
            is_last = index == len(yearly) - 1
            status = classify_last_year(entity_pct, asean_pct) if is_last else ""
            recommended: int | object = pd.NA
            if is_last:
                recommended = int(row["Year"]) if status == "FULL" else years[index - 1] if index > 0 else pd.NA
            records.append({
                "file_name": file_name, "year": int(row["Year"]),
                "row_count": int(row["row_count"]),
                "entity_count": int(row["entity_count"]),
                "asean_entity_count": int(row["asean_entity_count"]),
                "previous_year": years[index - 1] if index > 0 else pd.NA,
                "previous_entity_count": entity_counts[index - 1] if index > 0 else pd.NA,
                "entity_baseline_median_5y": entity_baseline,
                "asean_baseline_median_5y": asean_baseline,
                "entity_coverage_pct": entity_pct,
                "asean_coverage_pct": asean_pct,
                "is_last_year": is_last, "last_year_status": status,
                "recommended_end_year": recommended,
            })
    return pd.DataFrame.from_records(records, columns=LAST_YEAR_COLUMNS)


# Report/output -------------------------------------------------------------
def table(
    frame: pd.DataFrame,
    columns: list[str] | None = None,
    max_colwidth: int | None = None,
) -> str:
    selected = frame if columns is None else frame[columns]
    return selected.to_string(index=False, max_colwidth=max_colwidth)


def file_code(file_name: str) -> str:
    """Ma 2 ky tu dau ten file, dung lam nhan ngan trong bao cao."""
    return file_name[:2]


def compact_file_list(file_names: list[str] | pd.Series) -> str:
    return ", ".join(file_code(name) for name in file_names)


def resolve_analysis_window(
    asean_details: pd.DataFrame, last_year: pd.DataFrame
) -> tuple[int, int]:
    """Cua so phan tich chinh cho ASEAN-10, suy ra tu du lieu chu khong hard-code.

    Nam bat dau = nam muon nhat trong 10 nuoc ASEAN o file canonical.
    Nam ket thuc = nam cuoi dung duoc cua chinh file do theo Step 7.
    """
    primary_asean = asean_details.loc[
        asean_details["file_name"].eq(PRIMARY_SOURCE_FILE)
        & asean_details["present"]
    ]
    if primary_asean.empty:
        raise Phase1Error(
            f"{PRIMARY_SOURCE_FILE}: khong co nuoc ASEAN nao de suy cua so phan tich."
        )
    last_rows = last_year.loc[
        last_year["is_last_year"] & last_year["file_name"].eq(PRIMARY_SOURCE_FILE)
    ]
    if last_rows.empty or pd.isna(last_rows["recommended_end_year"].iloc[0]):
        raise Phase1Error(
            f"{PRIMARY_SOURCE_FILE}: khong xac dinh duoc nam ket thuc khuyen nghi."
        )
    return (
        int(primary_asean["year_min"].max()),
        int(last_rows["recommended_end_year"].iloc[0]),
    )


def build_summary_text(
    sources: dict[str, pd.DataFrame], profile: pd.DataFrame,
    tiers: pd.DataFrame, overlap_summary: pd.DataFrame,
    overlap_details: pd.DataFrame, join_summary: pd.DataFrame,
    join_details: pd.DataFrame, asean_matrix: pd.DataFrame,
    asean_details: pd.DataFrame, asean_file_summary: pd.DataFrame,
    asean_country_summary: pd.DataFrame, continuity: pd.DataFrame,
    continuity_summary: pd.DataFrame, last_year: pd.DataFrame,
) -> str:
    internal_gaps = continuity.loc[continuity["internal_gap_count"].gt(0)]
    last_rows = last_year.loc[last_year["is_last_year"]]
    redundant = overlap_summary.loc[overlap_summary["classification"].isin(["exact_duplicate", "redundant_subset"])]
    conflicts = overlap_summary.loc[overlap_summary["classification"].eq("conflicting_overlap")]
    immaterial_variants = overlap_summary.loc[overlap_summary["classification"].eq("immaterial_variant")]
    full_asean = asean_file_summary.loc[
        asean_file_summary["asean_countries_present"].eq(len(ASEAN_10)), "file_name"
    ].tolist()
    severe = last_rows.loc[last_rows["last_year_status"].eq("TRUNCATED_SEVERE")]
    partial = last_rows.loc[last_rows["last_year_status"].eq("PARTIAL_REVIEW")]
    analysis_start, analysis_end = resolve_analysis_window(asean_details, last_year)
    issue_counts = join_details["issue_type"].value_counts().to_dict()
    conflict_counts = overlap_details["conflict_type"].value_counts().to_dict()
    value_rows = overlap_details.loc[overlap_details["conflict_type"].eq("VALUE_CONFLICT")]
    tier_counts = value_rows["conflict_tier"].value_counts().to_dict()
    material_rows = value_rows.loc[value_rows["conflict_tier"].eq("MATERIAL")]
    material_aggregate_rows = int(material_rows["is_aggregate"].sum())
    compared_files = sorted(
        {file_name for specs in METRIC_GROUPS.values() for file_name, _ in specs}
    )
    uncompared_files = [name for name in sources if name not in compared_files]
    pattern_changed = continuity.loc[
        continuity["coverage_pattern"].ne(continuity["coverage_pattern_effective"])
    ]
    sampling_grid = continuity.loc[
        continuity["interpolation_decision"].eq("SAMPLING_GRID_NOT_MISSING")
    ]
    compact_tiers = tiers.assign(file_names=tiers["file_names"].map(
        lambda names: compact_file_list(names.split(" | "))
    ))
    file_legend = "\n".join(f"  {file_code(name)} = {name}" for name in sources)
    lines = [
        "PHASE 1 - KHẢO SÁT DỮ LIỆU VÀ XÁC ĐỊNH VẤN ĐỀ",
        "=" * 120,
        f"Nguồn: {len(sources)} CSV trong {ARCHIVE}",
        "Báo cáo không chứa timestamp để có thể đối chiếu giữa các lần chạy.",
        "",
        "STEP 1 - FILE PROFILE (mỗi dòng là một cột chỉ số)", "-" * 120,
        table(profile),
        f"\nTổng: {len(profile)} cột chỉ số trong {len(sources)} file.",
        "Lưu ý: zero là giá trị hợp lệ, khác missing; Entity gồm cả quốc gia và thực thể tổng hợp.",
        "",
        "STEP 2 - TẦNG ĐỘ PHỦ VÀ GIAO KHÓA", "-" * 120,
        "Cột file_names dùng mã 2 ký tự; xem danh mục file ở STEP 5.",
        "",
        "2a. Độ phủ thực thể và năm:",
        table(compact_tiers, [
            "tier_id", "file_count", "file_names", "entity_count_min",
            "entity_count_max", "entity_union_count",
            "entity_intersection_count", "entity_retention_pct",
            "year_min", "year_max", "common_year_count",
        ]),
        "\n2b. Giao khóa (Entity, Year):",
        table(compact_tiers, [
            "tier_id", "file_names", "key_count_min", "key_count_max",
            "key_union_count", "key_intersection_count", "key_retention_pct",
        ]),
        "Lưu ý: tier một file có retention 100% vì giao một tập với chính nó, không có nghĩa độ phủ rộng.",
        "",
        "STEP 3 - TRÙNG LẶP VÀ XUNG ĐỘT GIÁ TRỊ", "-" * 120,
        f"Phạm vi: chỉ so các cột cùng đại lượng và cùng đơn vị TWh, thuộc "
        f"{len(compared_files)} file ({compact_file_list(compared_files)}).",
        f"Không so {len(uncompared_files)} file còn lại ({compact_file_list(uncompared_files)}) "
        "vì không có file thứ hai đo cùng đại lượng và cùng đơn vị.",
        "",
        table(overlap_summary, [
            "pair_id", "comparable_count", "exact_match_count",
            "value_conflict_count", "immaterial_conflict_count",
            "material_conflict_count", "material_conflict_country_count",
            "material_conflict_aggregate_count", "match_pct",
            "material_match_pct", "classification",
        ]),
        "\nKhuyến nghị theo cặp:",
        table(overlap_summary, ["pair_id", "recommendation"]),
        f"\nChi tiết: {conflict_counts.get('VALUE_CONFLICT', 0)} VALUE_CONFLICT "
        f"({tier_counts.get('IMMATERIAL', 0)} IMMATERIAL + {tier_counts.get('MATERIAL', 0)} MATERIAL); "
        f"{conflict_counts.get('MISSING_MISMATCH', 0)} MISSING_MISMATCH.",
        f"Trong {tier_counts.get('MATERIAL', 0)} dòng MATERIAL có {material_aggregate_rows} dòng "
        f"thuộc thực thể tổng hợp (Entity không có Code).",
        f"Ngưỡng MATERIAL: abs_diff > {MATERIAL_ABS_TWH} TWh VÀ relative_diff_pct > {MATERIAL_REL_PCT}%.",
        "Phải vượt cả hai ngưỡng: chỉ dùng % thì 0 vs 0,005 TWh thành lệch 100%;",
        "chỉ dùng tuyệt đối thì 0,5 TWh trên 1.200 TWh của một nước lớn cũng bị tính là lệch.",
        "IMMATERIAL = không vượt đủ hai ngưỡng. Phần lớn là sai số làm tròn, nhưng nhóm này",
        "còn chứa các chênh lệch tuyệt đối lớn trên nền giá trị rất lớn (dưới 1%);",
        "vì vậy nhãn là IMMATERIAL chứ không phải ROUNDING.",
        "Các dòng conflict là theo cặp so sánh, không phải tất cả là sai lệch độc lập.",
        "",
        "STEP 4 - TÍNH NHẤT QUÁN KHÓA JOIN", "-" * 120, table(join_summary),
        f"\nChi tiết: {issue_counts.get('BLANK_CODE_ENTITY', 0)} Entity thiếu Code; "
        f"{issue_counts.get('FUZZY_CANDIDATE', 0)} cặp fuzzy cần review.",
        "Kết luận: exact match theo (Entity, Year); Code chỉ kiểm chứng; không auto-fuzzy.",
        "",
        "STEP 5 - ĐỘ PHỦ ASEAN-10 X 17 FILE", "-" * 120,
        "Quy ước: Y = có khóa Entity-Year; - = không có.", table(asean_matrix),
        "\nDanh mục file:", file_legend,
        "\nTổng hợp theo file:", table(asean_file_summary),
        "\nTổng hợp theo quốc gia:", table(asean_country_summary),
        "Lưu ý: Y chỉ xác nhận có khóa, không đảm bảo mọi metric đều khác NaN.",
        "",
        "STEP 6 - TÍNH LIÊN TỤC THEO NĂM", "-" * 120,
        "Hai cách đo biên cuối. Cột thô so với file_year_max; cột hiệu dụng so với",
        "năm cuối dùng được theo Step 7. Với 8 file có 2022 cắt cụt, mọi thực thể kết thúc",
        "ở 2021 bị cột thô gắn nhãn BOUNDARY_ONLY dù chuỗi của chúng không hề ngắn.",
        "Đọc cột *_effective để biết độ phủ thật; giữ cột thô làm bằng chứng cắt năm.",
        "",
        table(continuity_summary),
        f"\nSố chuỗi đổi nhãn giữa hai cách đo: {len(pattern_changed)}/{len(continuity)}.",
        f"Số chuỗi là lưới lấy mẫu (SAMPLING_GRID_NOT_MISSING): {len(sampling_grid)}.",
        "\nCác chuỗi có lỗ hổng ở giữa:",
        table(internal_gaps, [
            "file_name", "Entity", "is_asean", "entity_year_min",
            "entity_year_max", "internal_gap_count", "internal_gap_ranges",
            "coverage_pattern", "coverage_pattern_effective",
            "interpolation_decision",
        ]),
        "Kết luận: không tự động nội suy; Step 6 kiểm tra khóa năm, không kiểm tra NaN metric.",
        "SAMPLING_GRID_NOT_MISSING = lịch báo cáo theo mốc, không phải dữ liệu bị mất;",
        "cả hai nhãn đều chặn nội suy nhưng khác nghĩa khi diễn giải ở Phase 2.",
        "",
        "STEP 7 - KIỂM TRA NĂM CUỐI", "-" * 120,
        table(last_rows, [
            "file_name", "year", "entity_count", "asean_entity_count",
            "entity_baseline_median_5y", "asean_baseline_median_5y",
            "entity_coverage_pct", "asean_coverage_pct", "last_year_status",
            "recommended_end_year",
        ]),
        f"\nNgưỡng: <{SEVERE_THRESHOLD_PCT:.0f}% = TRUNCATED_SEVERE; "
        f"<{FULL_THRESHOLD_PCT:.0f}% = PARTIAL_REVIEW; >= {FULL_THRESHOLD_PCT:.0f}% = FULL.",
        "Lấy tỷ lệ xấu hơn giữa toàn bộ Entity và ASEAN.",
        "",
        "KẾT LUẬN - NĂM QUYẾT ĐỊNH CUỐI PHASE 1", "=" * 120,
        "1. FILE DÙNG/BỎ",
        f"   Ưu tiên file {file_code(PRIMARY_SOURCE_FILE)} cho sản lượng điện theo công nghệ. "
        "File 05, 08, 12 là ứng viên loại",
        "   vì các cột tương ứng là redundant_subset; không gọi toàn bộ file là trùng hoàn toàn.",
        "   File 02 lệch với file 03 ở mức MATERIAL, tập trung ở thực thể tổng hợp;",
        "   giữ tách riêng đến khi review provenance/định nghĩa. Ở cấp quốc gia hai nguồn",
        "   chỉ khác nhau ở mức làm tròn.",
        f"   Bằng chứng: {len(redundant)} cặp trùng/dư thừa; {len(conflicts)} cặp xung đột thật; "
        f"{len(immaterial_variants)} cặp chỉ khác dưới ngưỡng material.",
        "2. CHIẾN LƯỢC JOIN",
        "   Không INNER JOIN 17 file. Dùng tidy/union cho fact và spine + LEFT JOIN khi cần bảng rộng.",
        "   Khóa exact (Entity, Year); không fuzzy matching; Code chỉ dùng kiểm chứng.",
        "3. ĐỘ PHỦ ASEAN",
        f"   {len(full_asean)} file phủ đủ ASEAN-10: {compact_file_list(full_asean)}.",
        "   Các file capacity/biofuel/geothermal chỉ dùng cho tập con và phải ghi rõ nước thiếu.",
        "4. NỘI SUY",
        "   Không nội suy tự động, không điền trước năm đầu hay sau năm cuối; giữ NULL và review nguồn.",
        "5. CỬA SỔ PHÂN TÍCH",
        f"   Cửa sổ chính ASEAN-10: {analysis_start}-{analysis_end}. Giữ 2022 ở raw làm bằng chứng,",
        "   loại 2022 khỏi tầng phân tích sạch. File 01/06 với panel cố định kết thúc ở 2020;",
        "   geothermal kết thúc ở 2020.",
        f"   Số file TRUNCATED_SEVERE: {len(severe)}; PARTIAL_REVIEW: {len(partial)}.",
        "",
        "CÁC CSV CHI TIẾT", "=" * 120,
        f"- {OVERLAP_DETAIL_FILE.name}: {len(overlap_details)} dòng",
        f"- {JOIN_KEY_DETAIL_FILE.name}: {len(join_details)} dòng",
        f"- {ASEAN_DETAIL_FILE.name}: {len(asean_details)} dòng",
        f"- {CONTINUITY_DETAIL_FILE.name}: {len(continuity)} dòng",
        f"- {LAST_YEAR_DETAIL_FILE.name}: {len(last_year)} dòng",
    ]
    return "\n".join(lines) + "\n"


def validate_results(
    sources: dict[str, pd.DataFrame], profile: pd.DataFrame,
    tiers: pd.DataFrame, overlap_summary: pd.DataFrame,
    overlap_details: pd.DataFrame, join_summary: pd.DataFrame,
    join_details: pd.DataFrame, asean_details: pd.DataFrame,
    continuity: pd.DataFrame, last_year: pd.DataFrame,
) -> None:
    expected_pairs = sum(len(list(combinations(specs, 2))) for specs in METRIC_GROUPS.values())
    checks = [
        (len(profile) == sum(len(metric_columns(frame)) for frame in sources.values()), "So dong profile khong khop so metric."),
        (len(tiers) >= 2 and tiers.iloc[-1]["tier_id"] == "ALL_FILES", "Thieu dong ALL_FILES."),
        (len(overlap_summary) == expected_pairs, "So cap overlap khong dung."),
        (len(join_summary) == 10, "Join-key summary phai co 10 kiem tra."),
        (len(asean_details) == len(ASEAN_10) * len(sources), "Bang ASEAN khong du 10x17."),
        ((continuity["observed_year_count"] + continuity["internal_gap_count"] == continuity["expected_span_year_count"]).all(), "Phuong trinh continuity khong dung."),
        (last_year.groupby("file_name")["is_last_year"].sum().eq(1).all(), "Moi file phai co dung mot nam cuoi."),
    ]
    overlap_expected = int((
        overlap_summary["value_conflict_count"]
        + overlap_summary["left_missing_only_count"]
        + overlap_summary["right_missing_only_count"]
    ).sum())
    value_rows = overlap_details.loc[overlap_details["conflict_type"].eq("VALUE_CONFLICT")]
    material_rows = value_rows.loc[value_rows["conflict_tier"].eq("MATERIAL")]
    checks.extend([
        (len(overlap_details) == overlap_expected, "So dong overlap detail khong khop summary."),
        (list(join_details.columns) == JOIN_DETAIL_COLUMNS, "Sai schema join-key CSV."),
        (list(overlap_details.columns) == OVERLAP_DETAIL_COLUMNS, "Sai schema overlap CSV."),
        (list(continuity.columns) == CONTINUITY_COLUMNS, "Sai schema continuity CSV."),
        (
            int(overlap_summary["material_conflict_count"].sum()) == len(material_rows),
            "Tong material_conflict_count khong khop so dong MATERIAL trong detail.",
        ),
        (
            (
                overlap_summary["material_conflict_country_count"]
                + overlap_summary["material_conflict_aggregate_count"]
                == overlap_summary["material_conflict_count"]
            ).all(),
            "material country + aggregate khong bang material_conflict_count.",
        ),
        (
            (
                overlap_summary["immaterial_conflict_count"]
                + overlap_summary["material_conflict_count"]
                == overlap_summary["value_conflict_count"]
            ).all(),
            "immaterial + material khong bang value_conflict_count.",
        ),
        (
            value_rows["conflict_tier"].isin(["IMMATERIAL", "MATERIAL"]).all(),
            "Con dong VALUE_CONFLICT chua duoc phan tang.",
        ),
        (
            int(material_rows["is_aggregate"].sum())
            == int(overlap_summary["material_conflict_aggregate_count"].sum()),
            "So dong MATERIAL aggregate khong khop summary.",
        ),
        (
            (
                continuity["effective_trailing_boundary_year_count"]
                <= continuity["trailing_boundary_year_count"]
            ).all(),
            "Trailing hieu dung phai nho hon hoac bang trailing tho.",
        ),
        (
            (continuity["effective_file_year_max"] <= continuity["file_year_max"]).all(),
            "Nam cuoi hieu dung phai nho hon hoac bang file_year_max.",
        ),
    ])
    for passed, message in checks:
        if not passed:
            raise Phase1Error(message)


def write_outputs_transactionally(
    summary_text: str, overlap_details: pd.DataFrame,
    join_details: pd.DataFrame, asean_details: pd.DataFrame,
    continuity: pd.DataFrame, last_year: pd.DataFrame,
) -> None:
    STATS.mkdir(parents=True, exist_ok=True)
    frames = [
        (OVERLAP_DETAIL_FILE, overlap_details),
        (JOIN_KEY_DETAIL_FILE, join_details),
        (ASEAN_DETAIL_FILE, asean_details),
        (CONTINUITY_DETAIL_FILE, continuity),
        (LAST_YEAR_DETAIL_FILE, last_year),
    ]
    temp_pairs: list[tuple[Path, Path]] = []
    try:
        for final_path, frame in frames:
            temp_path = final_path.with_name(f".{final_path.name}.tmp")
            frame.to_csv(temp_path, index=False, encoding="utf-8-sig")
            temp_pairs.append((temp_path, final_path))
        summary_temp = SUMMARY_FILE.with_name(f".{SUMMARY_FILE.name}.tmp")
        with summary_temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(summary_text)
        temp_pairs.append((summary_temp, SUMMARY_FILE))
        for temp_path, final_path in temp_pairs:
            temp_path.replace(final_path)
    finally:
        for temp_path, _ in temp_pairs:
            if temp_path.exists():
                temp_path.unlink()

    # Don file cu nam ngoai giao dich: neu .xlsx dang mo trong Excel thi khong
    # duoc lam ca lan chay bao that bai, vi moi dau ra da ghi xong.
    try:
        if LEGACY_WORKBOOK.exists():
            LEGACY_WORKBOOK.unlink()
    except OSError as exc:
        print(
            f"[CANH BAO] Khong xoa duoc {LEGACY_WORKBOOK.name} ({exc}); "
            "dau ra Phase 1 van day du.",
            file=sys.stderr,
        )


def main() -> int:
    try:
        csv_files = discover_csv_files()
        sources = load_sources(csv_files)
        is_aggregate = aggregate_flags(build_entity_code_index(sources))
        profile = build_profile(sources)
        tiers = build_coverage_tiers(sources)
        overlap_summary, overlap_details = build_overlap_comparisons(sources, is_aggregate)
        join_summary, join_details = build_join_key_audit(sources)
        asean_matrix, asean_details, asean_file_summary, asean_country_summary = build_asean_coverage(sources)
        # Step 7 chay truoc Step 6: Step 6 can nam cuoi dung duoc cua tung file
        # de tinh bien hieu dung, neu khong se bi nam cat cut lam nhieu.
        last_year = build_last_year_check(sources)
        last_rows = last_year.loc[last_year["is_last_year"]]
        effective_year_max = {
            str(row.file_name): int(row.recommended_end_year)
            for row in last_rows.itertuples(index=False)
            if pd.notna(row.recommended_end_year)
        }
        continuity, continuity_summary = build_year_continuity(sources, effective_year_max)
        validate_results(
            sources, profile, tiers, overlap_summary, overlap_details,
            join_summary, join_details, asean_details, continuity, last_year,
        )
        summary_text = build_summary_text(
            sources, profile, tiers, overlap_summary, overlap_details,
            join_summary, join_details, asean_matrix, asean_details,
            asean_file_summary, asean_country_summary, continuity,
            continuity_summary, last_year,
        )
        write_outputs_transactionally(
            summary_text, overlap_details, join_details, asean_details,
            continuity, last_year,
        )
        analysis_start, analysis_end = resolve_analysis_window(asean_details, last_year)
    except (Phase1Error, PermissionError, OSError) as exc:
        print(f"\n[LOI] Phase 1 khong hoan thanh: {exc}", file=sys.stderr)
        return 1

    tier_counts = (
        overlap_details.loc[overlap_details["conflict_type"].eq("VALUE_CONFLICT"),
                            "conflict_tier"].value_counts()
    )
    print("PHASE 1 HOÀN THÀNH")
    print("-" * 78)
    print(f"CSV nguồn: {len(sources)}")
    print(f"Cột chỉ số: {len(profile)}")
    print(f"Tầng độ phủ: {len(tiers) - 1}")
    print(f"Cặp overlap: {len(overlap_summary)}")
    print("Xung đột giá trị: " + ", ".join(
        f"{tier}={count}" for tier, count in tier_counts.items()
    ))
    print(f"Chuỗi Entity-file: {len(continuity)}")
    print(
        "Chuỗi FULL_SPAN: "
        f"{int(continuity['coverage_pattern'].eq('FULL_SPAN').sum())} (thô) -> "
        f"{int(continuity['coverage_pattern_effective'].eq('FULL_SPAN').sum())} (hiệu dụng)"
    )
    print("Năm cuối: " + ", ".join(
        f"{status}={count}"
        for status, count in last_rows["last_year_status"].value_counts().items()
    ))
    print(f"Cửa sổ phân tích ASEAN-10: {analysis_start}-{analysis_end}")
    print(f"Báo cáo tổng hợp: {SUMMARY_FILE}")
    print(f"CSV chi tiết: {STATS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
