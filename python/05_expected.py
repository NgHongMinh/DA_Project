"""Phase 5 -- recompute every acceptance target from the Phase 2 clean tables.

This script is the reference side of Gate B10. It never reads Power BI. It
recomputes each locked figure of `PHASE5.md` section 5 straight from
`output/clean/`, checks the result three ways, and writes the full-precision
targets that `05_validate.py` will later compare DAX output against.

Three independent sources have to agree before anything is written:

1. this recomputation, from `output/clean/*.csv`;
2. the hand-transcribed literals in `phase5_contract.py`;
3. `output/stats/03_fact_metrics.csv`, wherever Phase 3 published the same
   quantity.

Source 2 is display-rounded in the document, so it is compared with a relative
tolerance. Sources 1 and 3 must agree to `1e-9` on the storage scale.

Run:  python python\\05_expected.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_contract as K  # noqa: E402
from config import ARCHIVE, CLEAN, STATS  # noqa: E402

EXPECTED_PATH = STATS / "05_expected_values.csv"

MODE_LABELS = {
    "RENEWABLE_TOTAL": "tổng NLTT",
    "MODERN_WIND_SOLAR": "gió + mặt trời",
}
TECHNOLOGY_LABELS = {
    "HYDRO": "thủy điện",
    "OTHER_RENEWABLES": "NLTT khác",
    "WIND": "gió",
    "SOLAR": "mặt trời",
}


class ContractViolation(RuntimeError):
    """Raised when a recomputed value disagrees with a locked figure."""


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_tables() -> dict[str, pd.DataFrame]:
    tables = {
        "fact": pd.read_csv(CLEAN / "fact_energy.csv"),
        "entity": pd.read_csv(CLEAN / "dim_entity.csv"),
        "metric": pd.read_csv(CLEAN / "dim_metric.csv"),
        "year": pd.read_csv(CLEAN / "dim_year.csv"),
        "phase3": pd.read_csv(STATS / "03_fact_metrics.csv"),
    }
    if len(tables["fact"]) != K.EXPECTED_FACT_ROWS:
        raise ContractViolation(
            f"fact_energy has {len(tables['fact'])} rows, expected {K.EXPECTED_FACT_ROWS}"
        )
    digest = hashlib.sha256((CLEAN / "fact_energy.csv").read_bytes()).hexdigest()
    if digest != K.EXPECTED_PHASE2_FACT_ENERGY_SHA256:
        raise ContractViolation(f"fact_energy.csv sha256 drifted: {digest}")
    return tables


def build_panel(fact: pd.DataFrame) -> pd.DataFrame:
    """Wide panel indexed by (entity, year), one column per metric_key.

    A missing cell stays NaN. That is what makes the complete-case rule
    expressible: a partial total must go blank rather than silently summing the
    components that happen to be present.
    """
    return fact.pivot_table(
        index=["entity", "year"], columns="metric_key", values="value", aggfunc="first"
    )


# ---------------------------------------------------------------------------
# Core measure semantics -- the same rules the DAX has to reproduce
# ---------------------------------------------------------------------------

def complete_case_total(
    panel: pd.DataFrame, entities: Sequence[str], year: int, mode: str
) -> tuple[float | None, int, int]:
    """Sum generation over entities x mode technologies, complete-case only.

    Returns (value, component_count, required_component_count). The required
    count scales with scope: 4 for one entity on the renewable total, 40 for the
    ten-country aggregate, 2 and 20 for the modern measure. Hard-coding 4 would
    still return a number when a country filter leaves cells missing.
    """
    columns = [K.GENERATION_METRICS[t] for t in K.MODE_TECHNOLOGIES[mode]]
    required = len(entities) * len(columns)
    keys = [(entity, year) for entity in entities]
    present = panel.reindex(keys)[columns]
    component_count = int(present.notna().to_numpy().sum())
    if component_count != required:
        return None, component_count, required
    return float(present.to_numpy().sum()), component_count, required


def entity_totals(
    panel: pd.DataFrame, entities: Sequence[str], year: int, mode: str
) -> dict[str, float]:
    """Per-entity complete-case totals, dropping entities that are incomplete."""
    out: dict[str, float] = {}
    for entity in entities:
        value, _, _ = complete_case_total(panel, [entity], year, mode)
        if value is not None:
            out[entity] = value
    return out


def rank_min_desc(values: dict[str, float]) -> dict[str, int]:
    """Descending rank, ties share the smallest rank and the next rank is skipped.

    This is `rank(method='min', ascending=False)` in pandas and `RANKX(..., Skip)`
    in DAX. Country names order the display only; they never break a published tie.
    """
    ordered = sorted(values.values(), reverse=True)
    return {name: ordered.index(value) + 1 for name, value in values.items()}


def concentration(values: Sequence[float]) -> dict[str, float] | None:
    """Top-1, top-3, HHI and Gini over the full fixed cohort, zeros included.

    Returns None when the cohort total is zero: shares are undefined, not zero,
    and every rank in the slice is NULL / ZERO_DENOMINATOR.
    """
    total = sum(values)
    if total <= 0:
        return None
    n = len(values)
    descending = sorted(values, reverse=True)
    ascending = sorted(values)
    # Take exactly one and exactly three largest values. A "rank <= 3" filter
    # would return more than three rows whenever third place is tied.
    weighted = sum((index + 1) * value for index, value in enumerate(ascending))
    return {
        "top1_share": descending[0] / total,
        "top3_share": sum(descending[:3]) / total,
        "hhi": sum((value / total) ** 2 for value in values),
        "gini": 2 * weighted / (n * total) - (n + 1) / n,
    }


def entry_rows(panel: pd.DataFrame) -> pd.DataFrame:
    """The 40-row entry grid, each row carrying two independent status families.

    A censored series keeps its status and leaves the event year blank. Writing
    2000 or 2021 into the year column would turn "we never saw it start" into a
    fabricated observation.
    """
    records = []
    for country in K.ASEAN_10:
        for technology, column in K.GENERATION_METRICS.items():
            series = {
                year: panel.at[(country, year), column]
                if (country, year) in panel.index
                else float("nan")
                for year in K.YEARS
            }
            row: dict[str, Any] = {"entity": country, "technology": technology}
            for family, threshold, labels in (
                (
                    "entry_status",
                    0.0,
                    ("ACTIVE_AT_WINDOW_START", "OBSERVED_TRANSITION", "NOT_OBSERVED_BY_2021"),
                ),
                (
                    "material_entry_status",
                    K.MATERIAL_THRESHOLD_TWH,
                    (
                        "MATERIAL_AT_WINDOW_START",
                        "OBSERVED_MATERIAL_TRANSITION",
                        "NOT_MATERIAL_BY_2021",
                    ),
                ),
            ):
                active = [
                    year
                    for year in K.YEARS
                    if pd.notna(series[year])
                    and (series[year] > threshold if threshold == 0.0 else series[year] >= threshold)
                ]
                at_start, transition, never = labels
                if active and active[0] == K.YEAR_START:
                    row[family] = at_start
                    row[f"{family}__year"] = None
                    row[f"{family}__lag"] = None
                elif active:
                    row[family] = transition
                    row[f"{family}__year"] = active[0]
                    row[f"{family}__lag"] = active[0] - K.YEAR_START
                else:
                    row[family] = never
                    row[f"{family}__year"] = None
                    row[f"{family}__lag"] = None
            records.append(row)
    return pd.DataFrame(records)


def capacity_factor_pairs(fact: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Generation/capacity pairs kept only where capacity is strictly positive.

    A raw join gives 132 pairs; the 28 with zero capacity are dropped and none of
    them carries positive generation, so nothing observable is lost. Division is
    guarded so a zero denominator yields blank rather than an infinity.
    """
    window = fact[fact.entity.isin(K.ASEAN_10) & fact.year.between(K.YEAR_START, K.YEAR_END)]
    out: dict[str, pd.DataFrame] = {}
    for technology, prefix in (("WIND", "wind"), ("SOLAR", "solar")):
        capacity = window[window.metric_key == f"{prefix}_capacity_gw"][
            ["entity", "year", "value"]
        ].rename(columns={"value": "capacity_gw"})
        generation = window[window.metric_key == f"{prefix}_generation_twh"][
            ["entity", "year", "value"]
        ].rename(columns={"value": "generation_twh"})
        joined = capacity.merge(generation, on=["entity", "year"], how="inner")
        joined["kept"] = (joined.capacity_gw > 0) & joined.generation_twh.notna()
        joined["capacity_factor"] = [
            row.generation_twh / (row.capacity_gw * K.CAPACITY_FACTOR_DIVISOR)
            if row.kept
            else float("nan")
            for row in joined.itertuples()
        ]
        out[technology] = joined
    return out


def opposite_direction_years(panel: pd.DataFrame, mode: str) -> tuple[int, ...]:
    """Years where Vietnam's TWh and its share of electricity move opposite ways.

    Both quantities are reported; the chart marks the divergence and stops there.
    Nothing here licenses a causal reading in either direction.
    """
    share_columns = K.SHARE_ELECTRICITY_METRICS[mode]
    years: list[int] = []
    for year in K.YEARS[1:]:
        current, _, _ = complete_case_total(panel, ["Vietnam"], year, mode)
        previous, _, _ = complete_case_total(panel, ["Vietnam"], year - 1, mode)
        if current is None or previous is None:
            continue
        try:
            share_now = sum(panel.at[("Vietnam", year), c] for c in share_columns)
            share_before = sum(panel.at[("Vietnam", year - 1), c] for c in share_columns)
        except KeyError:
            continue
        delta_twh = current - previous
        delta_share = share_now - share_before
        if delta_twh == 0 or delta_share == 0:
            continue
        if (delta_twh > 0) != (delta_share > 0):
            years.append(year)
    return tuple(years)


def share_electricity(panel: pd.DataFrame, entity: str, year: int, mode: str) -> float | None:
    """Share of electricity on the stored 0-100 scale.

    The renewable total is a 1/1 pass-through of the source column, never a sum
    of components: adding the four parts gives Vietnam 2021 = 42,513379% instead
    of the locked 42,578747%, and the model has no other-renewables share column
    to add in the first place.
    """
    columns = K.SHARE_ELECTRICITY_METRICS[mode]
    if (entity, year) not in panel.index:
        return None
    values = [panel.at[(entity, year), column] for column in columns]
    if any(pd.isna(value) for value in values):
        return None
    return float(sum(values))


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def check_locked(label: str, actual: Any, locked: Any) -> None:
    """Compare a recomputed value against the hand-transcribed contract."""
    if locked is None or actual is None:
        if locked is None and actual is None:
            return
        raise ContractViolation(f"{label}: recomputed {actual!r}, contract {locked!r}")
    if isinstance(locked, str) or isinstance(actual, str):
        if str(actual) != str(locked):
            raise ContractViolation(f"{label}: recomputed {actual!r}, contract {locked!r}")
        return
    if isinstance(locked, int) and not isinstance(locked, bool) and float(locked).is_integer():
        if int(round(float(actual))) != int(locked) or abs(float(actual) - locked) > 1e-9:
            raise ContractViolation(f"{label}: recomputed {actual!r}, contract {locked!r}")
        return
    if not math.isclose(float(actual), float(locked), rel_tol=K.LOCKED_REL_TOLERANCE, abs_tol=1e-12):
        raise ContractViolation(f"{label}: recomputed {actual!r}, contract {locked!r}")


def phase3_value(
    phase3: pd.DataFrame,
    metric_name: str,
    *,
    subject_key: str | None = None,
    period_key: str | None = None,
    series_key: str | None = None,
    comparison_scope: str | None = None,
) -> pd.Series | None:
    """Fetch the single Phase 3 row for a quantity, or None when absent."""
    frame = phase3[phase3.metric_name == metric_name]
    for column, value in (
        ("subject_key", subject_key),
        ("period_key", period_key),
        ("series_key", series_key),
        ("comparison_scope", comparison_scope),
    ):
        if value is not None:
            frame = frame[frame[column] == value]
    if len(frame) != 1:
        return None
    return frame.iloc[0]


def check_phase3(label: str, actual: float | None, row: pd.Series | None) -> str:
    """Cross-check against Phase 3 on the storage scale. Returns a note."""
    if row is None:
        return "phase3=absent"
    published = row.metric_value
    if actual is None:
        if pd.isna(published):
            return f"phase3={row.value_status}/{row.exclusion_reason}"
        raise ContractViolation(f"{label}: recomputed blank, Phase 3 has {published!r}")
    if pd.isna(published):
        raise ContractViolation(f"{label}: recomputed {actual!r}, Phase 3 blank")
    if abs(float(actual) - float(published)) > K.NUMERIC_TOLERANCE:
        raise ContractViolation(
            f"{label}: recomputed {actual!r}, Phase 3 {published!r} "
            f"(delta {abs(float(actual) - float(published)):.3e} > {K.NUMERIC_TOLERANCE})"
        )
    return "phase3=match"


# ---------------------------------------------------------------------------
# Target registry
# ---------------------------------------------------------------------------

class Targets:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []
        self._seen: set[str] = set()

    def add(
        self,
        test_id: str,
        gate_id: str,
        page_id: str,
        description_vi: str,
        filters: dict[str, Any],
        *,
        value: float | int | None = None,
        text: str | None = None,
        unit_stored: str,
        comparison: str,
        note: str = "",
    ) -> None:
        if test_id in self._seen:
            raise ContractViolation(f"duplicate test_id {test_id}")
        if unit_stored not in K.UNIT_STORED_VALUES:
            raise ContractViolation(f"{test_id}: illegal unit_stored {unit_stored!r}")
        if comparison not in {"numeric", "exact", "text", "blank"}:
            raise ContractViolation(f"{test_id}: illegal comparison {comparison!r}")
        self._seen.add(test_id)
        self.rows.append(
            {
                "test_id": test_id,
                "gate_id": gate_id,
                "page_id": page_id,
                "description_vi": description_vi,
                "filter_json": json.dumps(filters, ensure_ascii=False, sort_keys=True),
                "expected_value": "" if value is None else repr(float(value)),
                "expected_text": "" if text is None else text,
                "unit_stored": unit_stored,
                "comparison": comparison,
                "tolerance": 0.0 if comparison in {"exact", "text", "blank"} else K.NUMERIC_TOLERANCE,
                "method_version": K.METHOD_VERSION,
                "phase2_input_fingerprint": K.EXPECTED_PHASE2_INPUT_FINGERPRINT,
                "note": note,
            }
        )


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_targets(tables: dict[str, pd.DataFrame]) -> Targets:
    fact, entity, metric, year_dim, phase3 = (
        tables["fact"],
        tables["entity"],
        tables["metric"],
        tables["year"],
        tables["phase3"],
    )
    panel = build_panel(fact)
    current_countries = sorted(entity.loc[entity.is_current_country_or_territory == 1, "entity"])
    asean = sorted(entity.loc[entity.is_asean == 1, "entity"])
    targets = Targets()

    # ---- B2: the model as loaded, before any measure is written -------------
    structural = [
        ("P5_B2_FACT_ROWS", "FactEnergy có đúng 89.075 dòng", len(fact), K.EXPECTED_FACT_ROWS),
        ("P5_B2_DIM_ENTITY_ROWS", "DimEntity có đúng 256 dòng", len(entity), K.EXPECTED_DIM_ENTITY_ROWS),
        ("P5_B2_CURRENT_COUNTRY_N", "is_current_country_or_territory = 1 cho 215 dòng",
         len(current_countries), K.EXPECTED_CURRENT_COUNTRY_ROWS),
        ("P5_B2_ASEAN_N", "is_asean = 1 cho 10 dòng", len(asean), K.EXPECTED_ASEAN_ROWS),
        ("P5_B2_NON_AGGREGATE_N", "is_aggregate = 0 cho 216 dòng — KHÔNG dùng làm bộ lọc quốc gia",
         int((entity.is_aggregate == 0).sum()), K.EXPECTED_NON_AGGREGATE_ROWS),
        ("P5_B2_DIM_METRIC_ROWS", "DimMetric có đúng 16 dòng", len(metric), K.EXPECTED_DIM_METRIC_ROWS),
        ("P5_B2_DIM_YEAR_ROWS", "DimYear có đúng 57 dòng 1965–2021", len(year_dim), K.EXPECTED_DIM_YEAR_ROWS),
        ("P5_B2_MAIN_WINDOW_N", "is_main_asean_window = 1 cho 22 dòng",
         int((year_dim.is_main_asean_window == 1).sum()), K.EXPECTED_MAIN_WINDOW_ROWS),
        ("P5_B2_DUPLICATE_KEYS", "Khóa (entity, year, metric_key) không trùng",
         int(fact.duplicated(["entity", "year", "metric_key"]).sum()), 0),
        ("P5_B2_NEGATIVE_VALUES", "Không có giá trị âm", int((fact.value < 0).sum()), 0),
        ("P5_B2_YEAR_2022_ROWS", "Không còn dòng năm 2022", int((fact.year == 2022).sum()), 0),
    ]
    for test_id, description, actual, locked in structural:
        check_locked(test_id, actual, locked)
        targets.add(test_id, "B2", "MODEL", description, {}, value=actual,
                    unit_stored="count", comparison="exact")

    # Deliberately the same predicate the DAX side uses. Counting decimal digits
    # in the CSV text instead would skip the three values written in scientific
    # notation and undercount by three -- see EXPECTED_VALUES_OVER_4DP.
    over_4dp = int((fact.value.round(4) != fact.value).sum())
    check_locked("P5_B2_VALUES_OVER_4DP", over_4dp, K.EXPECTED_VALUES_OVER_4DP)
    targets.add(
        "P5_B2_VALUES_OVER_4DP", "B2", "MODEL",
        f"{over_4dp}/{len(fact)} giá trị có hơn 4 chữ số thập phân — vì sao cấm Fixed Decimal",
        {}, value=over_4dp, unit_stored="count", comparison="exact",
        note="FactEnergy[value] phải là Decimal Number (double); "
             "Fixed Decimal cắt còn 4 chữ số và con số này sẽ tụt về 0",
    )

    # The two raw reads Gate B2 demands before any measure exists.
    for scope, entities in (("ASEAN_10", asean), ("WORLD_REPORTED", ["World"])):
        value, _, _ = complete_case_total(panel, entities, 2021, "RENEWABLE_TOTAL")
        targets.add(
            f"P5_B2_RAW_{scope}_2021", "B2", "MODEL",
            f"Đọc thẳng từ bảng vừa nạp: tổng 4 công nghệ {scope} năm 2021",
            {"year": 2021, "scope": scope, "mode": "RENEWABLE_TOTAL"},
            value=value, unit_stored="TWh", comparison="numeric",
            note="Lệch ở đây là lỗi kiểu dữ liệu, không phải lỗi DAX",
        )

    # ---- B7: page 1, regional overview --------------------------------------
    for probe_year in K.PROBE_YEARS:
        locked = K.LOCKED_REGIONAL_KPI[probe_year]
        asean_total, components, required = complete_case_total(panel, asean, probe_year, "RENEWABLE_TOTAL")
        asean_modern, _, _ = complete_case_total(panel, asean, probe_year, "MODERN_WIND_SOLAR")
        world_total, _, _ = complete_case_total(panel, ["World"], probe_year, "RENEWABLE_TOTAL")
        check_locked(f"asean_total {probe_year}", asean_total, locked["asean_total_twh"])
        check_locked(f"asean_modern {probe_year}", asean_modern, locked["asean_modern_twh"])
        check_locked(f"world_total {probe_year}", world_total, locked["world_total_twh"])
        if (components, required) != (40, 40):
            raise ContractViolation(f"ASEAN {probe_year} components {components}/{required}, expected 40/40")

        note = check_phase3(
            f"asean_share_world {probe_year}",
            asean_total / world_total,
            phase3_value(phase3, "asean_share_world", period_key=f"Y{probe_year}",
                         series_key="RENEWABLE_TOTAL", comparison_scope="WORLD_REPORTED"),
        )
        check_locked(f"asean_share_world {probe_year}", asean_total / world_total, locked["asean_share_world"])

        targets.add(f"P5_B7_ASEAN_TOTAL_{probe_year}", "B7", "V01",
                    f"KPI khu vực: ASEAN-10 tổng NLTT năm {probe_year}",
                    {"year": probe_year, "scope": "ASEAN_10", "mode": "RENEWABLE_TOTAL"},
                    value=asean_total, unit_stored="TWh", comparison="numeric",
                    note=f"complete-case {components}/{required}")
        targets.add(f"P5_B7_ASEAN_MODERN_{probe_year}", "B7", "V01",
                    f"KPI khu vực: ASEAN-10 gió + mặt trời năm {probe_year}",
                    {"year": probe_year, "scope": "ASEAN_10", "mode": "MODERN_WIND_SOLAR"},
                    value=asean_modern, unit_stored="TWh", comparison="numeric")
        targets.add(f"P5_B7_WORLD_TOTAL_{probe_year}", "B7", "V04",
                    f"Bối cảnh: dòng World tổng NLTT năm {probe_year}",
                    {"year": probe_year, "scope": "WORLD_REPORTED", "mode": "RENEWABLE_TOTAL"},
                    value=world_total, unit_stored="TWh", comparison="numeric",
                    note="dùng dòng World do nguồn báo cáo, không cộng các quốc gia")
        targets.add(f"P5_B7_ASEAN_SHARE_WORLD_{probe_year}", "B7", "V04",
                    f"Tỷ trọng ASEAN trong thế giới năm {probe_year}",
                    {"year": probe_year, "scope": "ASEAN_10", "mode": "RENEWABLE_TOTAL"},
                    value=asean_total / world_total, unit_stored="ratio", comparison="numeric",
                    note=note + "; lưu thang 0–1, ×100 chỉ ở format_string")

        for mode in K.MODES:
            totals = entity_totals(panel, asean, probe_year, mode)
            above = sum(1 for value in totals.values() if value >= K.MATERIAL_THRESHOLD_TWH)
            key = "above_0_05_n_total" if mode == "RENEWABLE_TOTAL" else "above_0_05_n_modern"
            check_locked(f"above_0_05_n {mode} {probe_year}", above, locked[key])
            targets.add(f"P5_B7_ABOVE005_{mode}_{probe_year}", "B7", "V01",
                        f"Số nước đạt ≥0,05 TWh, {MODE_LABELS[mode]}, năm {probe_year}",
                        {"year": probe_year, "scope": "ASEAN_10", "mode": mode},
                        value=above, unit_stored="count", comparison="exact")

    # 2021 technology mix, and the residual against the KPI.
    mix_total = 0.0
    for technology, column in K.GENERATION_METRICS.items():
        value = float(sum(panel.at[(country, 2021), column] for country in asean))
        mix_total += value
        check_locked(f"mix {technology}", value, K.LOCKED_ASEAN_MIX_2021[technology])
        targets.add(f"P5_B7_MIX_{technology}_2021", "B7", "V02",
                    f"Cơ cấu ASEAN 2021 — {TECHNOLOGY_LABELS[technology]}",
                    {"year": 2021, "scope": "ASEAN_10", "technology": technology},
                    value=value, unit_stored="TWh", comparison="numeric")
    residual = mix_total - K.LOCKED_REGIONAL_KPI[2021]["asean_total_twh"]
    if abs(residual) > K.NUMERIC_TOLERANCE:
        raise ContractViolation(f"2021 mix residual {residual!r} exceeds tolerance")
    targets.add("P5_B7_MIX_RESIDUAL_2021", "B7", "V02",
                "Tổng bốn thành phần trừ KPI khu vực — phần dư phải bằng 0",
                {"year": 2021, "scope": "ASEAN_10"}, value=0.0,
                unit_stored="TWh", comparison="numeric")

    # ASEAN ranking, both modes, 2021.
    for mode in K.MODES:
        totals = entity_totals(panel, asean, 2021, mode)
        ranks = rank_min_desc(totals)
        for rank, country in K.LOCKED_ASEAN_RANK_2021[mode].items():
            if ranks[country] != rank:
                raise ContractViolation(
                    f"{mode} 2021: {country} recomputed rank {ranks[country]}, contract {rank}"
                )
            targets.add(f"P5_B7_ASEAN_RANK_{mode}_{country}_2021", "B7", "V03",
                        f"Hạng ASEAN 2021 của {country}, {MODE_LABELS[mode]}",
                        {"year": 2021, "entity": country, "scope": "ASEAN_10", "mode": mode},
                        value=rank, unit_stored="rank", comparison="exact")

    total_ranks = rank_min_desc(entity_totals(panel, asean, 2021, "RENEWABLE_TOTAL"))
    modern_ranks = rank_min_desc(entity_totals(panel, asean, 2021, "MODERN_WIND_SOLAR"))
    for country in asean:
        gain = total_ranks[country] - modern_ranks[country]
        if country in K.LOCKED_MODERN_RANK_GAIN_2021:
            check_locked(f"modern_rank_gain {country}", gain, K.LOCKED_MODERN_RANK_GAIN_2021[country])
        targets.add(f"P5_B7_RANK_GAIN_{country}_2021", "B7", "V03",
                    f"Thay đổi hạng khi đổi cách đo, 2021 — {country}",
                    {"year": 2021, "entity": country, "scope": "ASEAN_10"},
                    value=gain, unit_stored="rank_change", comparison="exact",
                    note="modern_rank_gain = total_rank − modern_rank; dương là hạng tốt hơn")

    # Gate B7 also asserts no aggregate entity may appear in a country list.
    targets.add("P5_B7_AGGREGATE_IN_COUNTRY_LIST", "B7", "V02",
                "Không có thực thể tổng hợp trong danh sách nước", {"scope": "ASEAN_10"},
                value=0, unit_stored="count", comparison="exact",
                note="dùng is_asean = 1, không dùng is_aggregate = 0 (216 dòng, còn USSR)")

    # ---- B8: page 2, Vietnam ------------------------------------------------
    for probe_year in K.PROBE_YEARS:
        locked = K.LOCKED_VIETNAM[probe_year]
        for mode, suffix, locked_key in (
            ("RENEWABLE_TOTAL", "TOTAL", "total_twh"),
            ("MODERN_WIND_SOLAR", "MODERN", "modern_twh"),
        ):
            value, components, required = complete_case_total(panel, ["Vietnam"], probe_year, mode)
            check_locked(f"VN {suffix} {probe_year}", value, locked[locked_key])
            expected_components = 4 if mode == "RENEWABLE_TOTAL" else 2
            if (components, required) != (expected_components, expected_components):
                raise ContractViolation(
                    f"Vietnam {mode} {probe_year} components {components}/{required}"
                )
            targets.add(f"P5_B8_VN_{suffix}_{probe_year}", "B8", "V05",
                        f"KPI Việt Nam {MODE_LABELS[mode]} năm {probe_year}",
                        {"year": probe_year, "entity": "Vietnam", "mode": mode},
                        value=value, unit_stored="TWh", comparison="numeric",
                        note=f"complete-case {components}/{required}")

            share = share_electricity(panel, "Vietnam", probe_year, mode)
            share_key = (
                "share_electricity_total_pct" if mode == "RENEWABLE_TOTAL"
                else "share_electricity_modern_pct"
            )
            check_locked(f"VN share {suffix} {probe_year}", share, locked[share_key])
            targets.add(f"P5_B8_VN_SHARE_ELEC_{suffix}_{probe_year}", "B8", "V07",
                        f"Tỷ trọng điện Việt Nam {MODE_LABELS[mode]} năm {probe_year}",
                        {"year": probe_year, "entity": "Vietnam", "mode": mode},
                        value=share, unit_stored="pct", comparison="numeric",
                        note="lưu sẵn thang 0–100; RENEWABLE_TOTAL là pass-through 1/1")

            # ASEAN rank, including the 2000 zero-scope edge case.
            totals = entity_totals(panel, asean, probe_year, mode)
            rank_key = "asean_rank_total" if mode == "RENEWABLE_TOTAL" else "asean_rank_modern"
            if sum(totals.values()) <= 0:
                check_locked(f"VN asean_rank {suffix} {probe_year}", None, locked[rank_key])
                targets.add(f"P5_B8_VN_ASEAN_RANK_{suffix}_{probe_year}", "B8", "V08",
                            f"Hạng ASEAN Việt Nam {MODE_LABELS[mode]} năm {probe_year}",
                            {"year": probe_year, "entity": "Vietnam", "scope": "ASEAN_10", "mode": mode},
                            text=f"NOT_DEFINED/{K.ZERO_SCOPE_TOTAL_REASON}",
                            unit_stored="STATUS_CODE", comparison="blank",
                            note="tổng toàn phạm vi bằng 0 → hạng trống, không phải cùng hạng 1")
            else:
                rank = rank_min_desc(totals)["Vietnam"]
                check_locked(f"VN asean_rank {suffix} {probe_year}", rank, locked[rank_key])
                targets.add(f"P5_B8_VN_ASEAN_RANK_{suffix}_{probe_year}", "B8", "V08",
                            f"Hạng ASEAN Việt Nam {MODE_LABELS[mode]} năm {probe_year}",
                            {"year": probe_year, "entity": "Vietnam", "scope": "ASEAN_10", "mode": mode},
                            value=rank, unit_stored="rank", comparison="exact")

            # Global rank: a different cohort, with a denominator that moves.
            global_totals = entity_totals(panel, current_countries, probe_year, mode)
            ranked_n = len(global_totals)
            global_rank = rank_min_desc(global_totals)["Vietnam"]
            locked_rank, locked_ranked_n = K.LOCKED_VIETNAM_GLOBAL_RANK[(probe_year, mode)]
            check_locked(f"VN global_rank {suffix} {probe_year}", global_rank, locked_rank)
            check_locked(f"VN ranked_n {suffix} {probe_year}", ranked_n, locked_ranked_n)
            targets.add(f"P5_B8_VN_GLOBAL_RANK_{suffix}_{probe_year}", "B8", "V08",
                        f"Hạng toàn cầu Việt Nam {MODE_LABELS[mode]} năm {probe_year}",
                        {"year": probe_year, "entity": "Vietnam",
                         "scope": "GLOBAL_CURRENT_COUNTRIES", "mode": mode},
                        value=global_rank, unit_stored="rank", comparison="exact")
            targets.add(f"P5_B8_VN_RANKED_N_{suffix}_{probe_year}", "B8", "V08",
                        f"Mẫu số ranked_n {MODE_LABELS[mode]} năm {probe_year}",
                        {"year": probe_year, "scope": "GLOBAL_CURRENT_COUNTRIES", "mode": mode},
                        value=ranked_n, unit_stored="count", comparison="exact",
                        note=f"population_n = {K.LOCKED_GLOBAL_RANK_POPULATION_N}; "
                             "ranked_n đổi theo năm và theo chế độ, cấm viết cứng")

    for mode in K.MODES:
        country_value, _, _ = complete_case_total(panel, ["Vietnam"], 2021, mode)
        region_value, _, _ = complete_case_total(panel, asean, 2021, mode)
        share = country_value / region_value
        check_locked(f"VN share_asean {mode}", share, K.LOCKED_VIETNAM_SHARE_ASEAN_2021[mode])
        note = check_phase3(
            f"country_share_asean {mode}",
            share,
            phase3_value(phase3, "country_share_asean", subject_key="Vietnam",
                         period_key="Y2021", series_key=mode),
        )
        targets.add(f"P5_B8_VN_SHARE_ASEAN_{mode}_2021", "B8", "V08",
                    f"Tỷ trọng Việt Nam trong ASEAN 2021, {MODE_LABELS[mode]}",
                    {"year": 2021, "entity": "Vietnam", "scope": "ASEAN_10", "mode": mode},
                    value=share, unit_stored="ratio", comparison="numeric",
                    note=note + "; mẫu số ASEAN_SUM_10, lưu thang 0–1")

    for mode, locked_years in K.LOCKED_VIETNAM_OPPOSITE_YEARS.items():
        years = opposite_direction_years(panel, mode)
        if years != locked_years:
            raise ContractViolation(
                f"Vietnam opposite-direction years for {mode}: recomputed {years}, contract {locked_years}"
            )
        targets.add(f"P5_B8_VN_OPPOSITE_{mode}", "B8", "V07",
                    f"Năm TWh và tỷ trọng điện ngược hướng, {MODE_LABELS[mode]}",
                    {"entity": "Vietnam", "mode": mode, "window": "2000-2021"},
                    text=",".join(str(y) for y in years),
                    unit_stored="STATUS_CODE", comparison="text",
                    note="chỉ đánh dấu, không suy diễn nhân quả")

    # ---- B9: page 3, comparison and diagnostics -----------------------------
    for probe_year in K.PROBE_YEARS:
        for mode in K.MODES:
            totals = entity_totals(panel, asean, probe_year, mode)
            if len(totals) != len(asean):
                raise ContractViolation(f"concentration {mode} {probe_year} lost a country")
            result = concentration([totals[country] for country in asean])
            locked = K.LOCKED_CONCENTRATION[(probe_year, mode)]
            for name in ("top1_share", "top3_share", "hhi", "gini"):
                actual = None if result is None else result[name]
                check_locked(f"{name} {mode} {probe_year}", actual, locked[name])
                test_id = f"P5_B9_{name.upper()}_{mode}_{probe_year}"
                description = f"{name} ASEAN-10 {MODE_LABELS[mode]} năm {probe_year}"
                filters = {"year": probe_year, "scope": "ASEAN_10", "mode": mode}
                if actual is None:
                    targets.add(test_id, "B9", "V13", description, filters,
                                text=f"NOT_DEFINED/{K.ZERO_DENOMINATOR_REASON}",
                                unit_stored="STATUS_CODE", comparison="blank",
                                note="tổng ASEAN bằng 0 → không xác định, không phải 0")
                else:
                    note = check_phase3(
                        f"{name} {mode} {probe_year}",
                        actual,
                        phase3_value(phase3, name, period_key=f"Y{probe_year}", series_key=mode),
                    )
                    targets.add(test_id, "B9", "V13", description, filters,
                                value=actual, unit_stored="ratio", comparison="numeric",
                                note=note + "; lưu thang 0–1")

    for mode, locked_share in K.LOCKED_POSITIVE_GROWTH_SHARE_VN_2010_2021.items():
        deltas = {}
        for country in asean:
            start, _, _ = complete_case_total(panel, [country], 2010, mode)
            end, _, _ = complete_case_total(panel, [country], 2021, mode)
            deltas[country] = (end or 0.0) - (start or 0.0)
        gross = sum(max(delta, 0.0) for delta in deltas.values())
        share = max(deltas["Vietnam"], 0.0) / gross
        check_locked(f"positive_growth_share {mode}", share, locked_share)
        note = check_phase3(
            f"positive_growth_share {mode}",
            share,
            phase3_value(phase3, "positive_growth_share", subject_key="Vietnam",
                         period_key="I2010_2021", series_key=mode),
        )
        targets.add(f"P5_B9_POSGROWTH_VN_{mode}_I2010_2021", "B9", "V13",
                    f"Đóng góp của Việt Nam trong tổng phần tăng dương 2010–2021, {MODE_LABELS[mode]}",
                    {"entity": "Vietnam", "period": "I2010_2021", "scope": "ASEAN_10", "mode": mode},
                    value=share, unit_stored="ratio", comparison="numeric",
                    note=note + f"; mẫu số {K.POSITIVE_GROWTH_DENOMINATOR_BASIS}, "
                                "gọi là tỷ trọng trong tổng tăng dương, không phải tăng ròng")

    entries = entry_rows(panel)
    if len(entries) != K.LOCKED_ENTRY_KEY_ROWS:
        raise ContractViolation(f"entry grid has {len(entries)} rows, expected 40")
    targets.add("P5_B9_ENTRY_KEY_ROWS", "B9", "V12",
                "Bảng gia nhập có đúng 40 dòng khóa (10 nước × 4 công nghệ)",
                {"scope": "ASEAN_10"}, value=len(entries), unit_stored="count", comparison="exact")
    targets.add("P5_B9_ENTRY_STATUS_VALUES", "B9", "V12",
                "40 dòng × 2 họ ngưỡng = 80 giá trị trạng thái, không phải 40",
                {"scope": "ASEAN_10"}, value=len(entries) * 2,
                unit_stored="count", comparison="exact")

    for (technology, family), locked_counts in K.LOCKED_ENTRY_COUNTS.items():
        subset = entries[entries.technology == technology]
        actual_counts = subset[family].value_counts().to_dict()
        if actual_counts != locked_counts:
            raise ContractViolation(
                f"entry counts {technology}/{family}: recomputed {actual_counts}, contract {locked_counts}"
            )
        for status, count in sorted(locked_counts.items()):
            targets.add(f"P5_B9_ENTRY_{technology}_{family}_{status}", "B9", "V12",
                        f"Số nước {TECHNOLOGY_LABELS[technology]} ở trạng thái {status}",
                        {"scope": "ASEAN_10", "technology": technology, "family": family},
                        value=count, unit_stored="count", comparison="exact")

    for (country, technology), expectations in K.LOCKED_ENTRY_CASES.items():
        row = entries[(entries.entity == country) & (entries.technology == technology)].iloc[0]
        for field, locked_value in expectations.items():
            if field.endswith("_status"):
                actual: Any = row[field]
            elif field == "observed_entry_year":
                actual = row["entry_status__year"]
            elif field == "observed_material_entry_year":
                actual = row["material_entry_status__year"]
            elif field == "lag_from_2000":
                actual = row["entry_status__lag"]
            else:
                raise ContractViolation(f"unknown entry field {field}")
            if actual is not None and not isinstance(actual, str) and pd.isna(actual):
                actual = None
            check_locked(f"entry {country}/{technology}/{field}", actual, locked_value)
            test_id = f"P5_B9_ENTRYCASE_{country}_{technology}_{field.upper()}"
            if actual is None:
                targets.add(test_id, "B9", "V12",
                            f"Ca chuẩn gia nhập: {country} — {TECHNOLOGY_LABELS[technology]} — {field}",
                            {"entity": country, "technology": technology},
                            text="CENSORED/EVENT_NOT_EXACTLY_OBSERVED",
                            unit_stored="STATUS_CODE", comparison="blank",
                            note="kiểm duyệt là trạng thái, không thay bằng năm 2000 hoặc 2021")
            elif isinstance(actual, str):
                targets.add(test_id, "B9", "V12",
                            f"Ca chuẩn gia nhập: {country} — {TECHNOLOGY_LABELS[technology]} — {field}",
                            {"entity": country, "technology": technology},
                            text=actual, unit_stored="STATUS_CODE", comparison="text")
            else:
                targets.add(test_id, "B9", "V12",
                            f"Ca chuẩn gia nhập: {country} — {TECHNOLOGY_LABELS[technology]} — {field}",
                            {"entity": country, "technology": technology},
                            value=float(actual),
                            unit_stored="year" if "year" in field else "count",
                            comparison="exact")

    pairs = capacity_factor_pairs(fact)
    raw_total = sum(len(frame) for frame in pairs.values())
    kept_total = sum(int(frame.kept.sum()) for frame in pairs.values())
    check_locked("cf raw", raw_total, K.LOCKED_CAPACITY_FACTOR["raw_pairs"])
    check_locked("cf kept", kept_total, K.LOCKED_CAPACITY_FACTOR["kept_pairs"])
    for technology, frame in pairs.items():
        kept = int(frame.kept.sum())
        dropped = len(frame) - kept
        suffix = technology.lower()
        check_locked(f"cf raw {technology}", len(frame), K.LOCKED_CAPACITY_FACTOR[f"raw_{suffix}"])
        check_locked(f"cf kept {technology}", kept, K.LOCKED_CAPACITY_FACTOR[f"kept_{suffix}"])
        check_locked(f"cf dropped {technology}", dropped, K.LOCKED_CAPACITY_FACTOR[f"dropped_{suffix}"])
        if int((frame[~frame.kept].generation_twh > 0).sum()) != 0:
            raise ContractViolation(
                f"{technology}: a dropped capacity pair carries positive generation"
            )
        coverage = frame[frame.kept].groupby("entity").size().to_dict()
        if coverage != K.LOCKED_CAPACITY_FACTOR_COVERAGE[technology]:
            raise ContractViolation(f"cf coverage {technology}: {coverage}")
        targets.add(f"P5_B9_CF_PAIRS_{technology}", "B9", "V14",
                    f"Số cặp hệ số công suất {TECHNOLOGY_LABELS[technology]} sau lọc capacity_gw > 0",
                    {"scope": "ASEAN_10", "technology": technology, "window": "2000-2021"},
                    value=kept, unit_stored="count", comparison="exact",
                    note=f"join thô {len(frame)} cặp, loại {dropped} cặp công suất bằng 0; "
                         "không cặp nào bị loại có sản lượng > 0")
        targets.add(f"P5_B9_CF_COUNTRIES_{technology}", "B9", "V14",
                    f"Số nước có dữ liệu hệ số công suất {TECHNOLOGY_LABELS[technology]}",
                    {"scope": "ASEAN_10", "technology": technology},
                    value=len(coverage), unit_stored="count", comparison="exact",
                    note="phải ghi rõ nước nào thiếu, không để hiểu là đã phủ hết")

    all_values = pd.concat([frame[frame.kept].capacity_factor for frame in pairs.values()])
    check_locked("cf max", float(all_values.max()), K.LOCKED_CAPACITY_FACTOR["max_value"])
    check_locked("cf min", float(all_values.min()), K.LOCKED_CAPACITY_FACTOR["min_value"])
    targets.add("P5_B9_CF_PAIRS_TOTAL", "B9", "V14",
                "Tổng số cặp hệ số công suất sau lọc", {"scope": "ASEAN_10", "window": "2000-2021"},
                value=kept_total, unit_stored="count", comparison="exact",
                note="đếm trên số điểm có giá trị, không đếm 132 dòng bảng join")
    targets.add("P5_B9_CF_MAX", "B9", "V14",
                "Biên trên hệ số công suất xấp xỉ", {"scope": "ASEAN_10", "window": "2000-2021"},
                value=float(all_values.max()), unit_stored="ratio", comparison="numeric",
                note="chỉ báo dùng công suất cuối năm, không phải hiệu quả kỹ thuật")
    targets.add("P5_B9_CF_MIN", "B9", "V14",
                "Biên dưới hệ số công suất xấp xỉ", {"scope": "ASEAN_10", "window": "2000-2021"},
                value=float(all_values.min()), unit_stored="ratio", comparison="numeric")

    grid_points = sum(
        1
        for country in asean
        for probe_year in K.YEARS
        if complete_case_total(panel, [country], probe_year, "RENEWABLE_TOTAL")[0] is not None
    )
    check_locked("small multiple points", grid_points, K.LOCKED_SMALL_MULTIPLE_POINTS)
    targets.add("P5_B9_SMALL_MULTIPLE_POINTS", "B9", "V10",
                "Lưới 10 nước × 22 năm cho đủ 220 điểm", {"scope": "ASEAN_10", "window": "2000-2021"},
                value=grid_points, unit_stored="count", comparison="exact")

    return targets


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    archive_count = len(list(ARCHIVE.glob("*.csv")))
    if archive_count != K.EXPECTED_ARCHIVE_CSV_COUNT:
        raise ContractViolation(f"archive holds {archive_count} CSV files, expected 17")

    tables = load_tables()
    targets = build_targets(tables)
    frame = pd.DataFrame(targets.rows)
    STATS.mkdir(parents=True, exist_ok=True)
    frame.to_csv(EXPECTED_PATH, index=False, encoding="utf-8")

    by_gate = frame.gate_id.value_counts().sort_index().to_dict()
    print(
        f"PHASE 5 EXPECTED VALUES: PASS | targets={len(frame)} | "
        f"gates={by_gate} | fingerprint={K.EXPECTED_PHASE2_INPUT_FINGERPRINT[:12]}…"
    )
    print(f"  -> {EXPECTED_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractViolation as error:
        print(f"PHASE 5 EXPECTED VALUES: FAIL | {error}", file=sys.stderr)
        raise SystemExit(1)
