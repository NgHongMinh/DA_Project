"""Phase 6 Gate E3 -- prove every number that reaches the report and the slides.

What this does
--------------
`docs/NhatKyPhanTich.md` line 13 forbids copying a number out of the journal into
`BaoCao.md`. This script is how that rule is enforced by machine rather than by
discipline: for each locked claim in `phase6_contract.py` it collects three
independent readings and refuses to publish unless all three agree.

    voice 1  the literal in `phase6_contract.py`, transcribed by hand
    voice 2  `output/stats/03_fact_metrics.csv`, looked up by key
    voice 3  a recomputation that reads ONLY `output/clean/*.csv`

Voice 3 is the point. Voices 1 and 2 could agree because the literal was copied
from the table, which would prove nothing at all. Voice 3 rebuilds the country
panel from the fact table and re-derives the aggregation, so agreement means the
number survives an independent path rather than an echo.

Definitions are taken from `03_descriptive.py`, deliberately: the goal is to check
the arithmetic and the plumbing, not to invent a second definition and then
discover it disagrees. Three that matter, because getting them wrong produces
plausible numbers rather than errors:

  * RENEWABLE_TOTAL sums the four generation technologies with `min_count=4`, so a
    country-year missing any component is NaN, not a partial sum. That is why the
    global ranking denominator is 205 rather than 215.
  * MODERN_WIND_SOLAR does the same over wind and solar with `min_count=2`, giving
    209.
  * Rankings collapse to "not defined" when the whole scope sums to zero -- which
    is exactly the ASEAN modern measure in the year 2000, and the reason a rank
    there must read blank rather than 1.

Run:  python python\\06_verify_findings.py
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy.stats import skew

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CLEAN, STATS  # noqa: E402

PYTHON_DIR = Path(__file__).resolve().parent
FACT_METRICS = STATS / "03_fact_metrics.csv"
EVIDENCE_OUT = STATS / "06_finding_evidence.csv"


def _load(module_name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(module_name, PYTHON_DIR / file_name)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {file_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


contract = _load("phase6_contract_probe", "phase6_contract.py")

CLAIMS = contract.CLAIMS
TOL = contract.NUMERIC_TOLERANCE
ASEAN_10 = list(contract.ASEAN_10)
GEN = contract.GENERATION_KEYS
YEARS = list(range(contract.YEAR_START, contract.YEAR_END + 1))

SERIES_KEYS: dict[str, tuple[str, ...]] = {
    "HYDRO": (GEN["hydro"],),
    "OTHER_RENEWABLES": (GEN["other_renewables"],),
    "SOLAR": (GEN["solar"],),
    "WIND": (GEN["wind"],),
    "RENEWABLE_TOTAL": contract.RENEWABLE_TOTAL_KEYS,
    "MODERN_WIND_SOLAR": contract.MODERN_KEYS,
}

SHARE_KEYS = contract.SHARE_ELECTRICITY_KEYS


# --------------------------------------------------------------------------
# Voice 3 -- rebuild the panels from output/clean only
# --------------------------------------------------------------------------

def build_panel(fact: pd.DataFrame, entities: list[str]) -> pd.DataFrame:
    """entity x year x series, with the min_count rule that decides NaN vs sum.

    `min_count=len(keys)` is not a detail. Summing with the pandas default turns a
    country missing three of four technologies into a confident small number, and
    that number then ranks, averages and appears on a slide.
    """
    index = pd.MultiIndex.from_product([entities, YEARS], names=["entity", "year"])
    wanted = set().union(*SERIES_KEYS.values())
    subset = fact[fact.entity.isin(entities) & fact.metric_key.isin(wanted)]
    wide = (subset.pivot(index=["entity", "year"], columns="metric_key", values="value")
            .reindex(index))
    for key in wanted:
        if key not in wide.columns:
            wide[key] = np.nan
    out = pd.DataFrame(index=index)
    for series, keys in SERIES_KEYS.items():
        out[series] = wide[list(keys)].sum(axis=1, min_count=len(keys))
    return out


def rank_within(values: pd.Series) -> tuple[pd.Series, int]:
    """Descending min-rank, with the zero-scope collapse from `03_descriptive.py`.

    When every value in scope is zero there is no meaningful order, so every rank
    is undefined. Returning 1 for the whole field would be arithmetically true and
    analytically false -- that is what `NOT_DEFINED/ZERO_SCOPE_TOTAL` exists to say.
    """
    valid = values.dropna()
    if len(valid) > 0 and bool(np.isclose(valid.sum(), 0.0, atol=1e-12)):
        return pd.Series(np.nan, index=values.index), len(valid)
    return values.rank(method="min", ascending=False), len(valid)


class Recomputer:
    """Every handler here reads `self.asean` / `self.world` / `self.globe` only."""

    def __init__(self) -> None:
        fact = pd.read_csv(CLEAN / "fact_energy.csv")
        entities = pd.read_csv(CLEAN / "dim_entity.csv")

        current = entities.loc[
            entities.is_current_country_or_territory == 1, "entity"
        ].tolist()
        asean_from_dim = sorted(entities.loc[entities.is_asean == 1, "entity"].tolist())
        if asean_from_dim != sorted(ASEAN_10):
            raise AssertionError(
                f"dim_entity liet ke ASEAN {asean_from_dim} != hop dong {sorted(ASEAN_10)}"
            )

        self.asean = build_panel(fact, sorted(ASEAN_10))
        self.globe = build_panel(fact, sorted(current))
        self.world = build_panel(fact, ["World"])
        # Kept unpivoted: the distribution statistics need `value_class`,
        # which the wide panel drops.
        self.raw = fact
        # Share of electricity is a reported metric, not a derived sum, so it gets
        # its own narrow frame rather than going through `build_panel`.
        self.shares = fact[fact.metric_key.isin(SHARE_KEYS.values())].set_index(
            ["entity", "year", "metric_key"]
        )["value"]

    # -- levels ------------------------------------------------------------
    def asean_generation(self, series: str, year: int) -> float:
        return float(self.asean.xs(year, level="year")[series].sum())

    def country_generation(self, series: str, year: int, country: str) -> float:
        return float(self.asean.loc[(country, year), series])

    def world_generation(self, series: str, year: int) -> float:
        return float(self.world.loc[("World", year), series])

    def distribution_stat(self, stat: str, series: str, year: int, variant: str) -> float:
        """One descriptive statistic for one technology, year and filter variant.

        Matches `03_descriptive.py :: add_distribution` exactly, including the two
        choices that silently change the answer rather than raising:
        `std(ddof=0)` (population, not sample) and `skew(bias=False)`
        (bias-corrected). Percentiles use numpy's default linear interpolation.
        """
        key = SERIES_KEYS[series]
        if len(key) != 1:
            raise ValueError(f"thong ke phan phoi chi dinh nghia cho mot cong nghe, khong phai {series}")
        rows = self.raw[self.raw.metric_key.eq(key[0]) & self.raw.year.eq(year)
                        & self.raw.entity.isin(ASEAN_10)]
        values = rows.value.astype(float)
        if variant == "POSITIVE":
            values = values[values.gt(0)]
        elif variant == "MATERIAL":
            values = values[rows.value_class.eq("Material")]
        elif variant != "ALL_OBSERVED":
            raise ValueError(f"bien the loc la {variant!r}")

        array = values.to_numpy(dtype=float)
        if stat == "n":
            return float(len(array))
        if stat == "mean":
            return float(array.mean())
        if stat == "median":
            return float(np.median(array))
        if stat == "sd":
            return float(array.std(ddof=0))
        if stat == "cv":
            return float(array.std(ddof=0) / array.mean())
        if stat == "skewness":
            return float(skew(array, bias=False))
        if stat.startswith("p"):
            return float(np.percentile(array, int(stat[1:]), method="linear"))
        raise ValueError(f"khong biet thong ke {stat!r}")

    def country_share_electricity(self, series: str, year: int, country: str) -> float:
        """Reported share of electricity, on the 0-100 scale Phase 2 stores it at.

        Deliberately NOT rescaled here. Every other ratio this file returns is on
        0-1, and normalising them all to one scale would hide the very mismatch the
        contract locks -- a `pct` claim that had drifted to 0-1 would then compare
        equal and pass.
        """
        return float(self.shares.loc[(country, year, SHARE_KEYS[series])])

    # -- shares ------------------------------------------------------------
    def asean_share_world(self, series: str, year: int) -> float:
        return self.asean_generation(series, year) / self.world_generation(series, year)

    def country_share_asean(self, series: str, year: int, country: str) -> float:
        return self.country_generation(series, year, country) / self.asean_generation(series, year)

    # -- ranks -------------------------------------------------------------
    def asean_rank(self, series: str, year: int, country: str) -> float:
        ranks, _ = rank_within(self.asean.xs(year, level="year")[series])
        return float(ranks.loc[country])

    def global_rank(self, series: str, year: int, country: str) -> float:
        ranks, _ = rank_within(self.globe.xs(year, level="year")[series])
        return float(ranks.loc[country])

    def rank_gain(self, year: int, country: str) -> float:
        return (self.asean_rank("RENEWABLE_TOTAL", year, country)
                - self.asean_rank("MODERN_WIND_SOLAR", year, country))

    # -- concentration -----------------------------------------------------
    def _sorted_asean(self, series: str, year: int) -> pd.Series:
        return self.asean.xs(year, level="year")[series].sort_values(
            ascending=False, kind="mergesort")

    def top_n_share(self, series: str, year: int, n: int) -> float:
        values = self._sorted_asean(series, year)
        return float(values.iloc[:n].sum() / values.sum())

    def hhi(self, series: str, year: int) -> float:
        values = self._sorted_asean(series, year)
        return float(np.square(values / values.sum()).sum())

    def gini(self, series: str, year: int) -> float:
        array = np.sort(self._sorted_asean(series, year).to_numpy(dtype=float))
        n = len(array)
        return float(2 * np.sum(np.arange(1, n + 1) * array) / (n * array.sum()) - (n + 1) / n)

    # -- growth ------------------------------------------------------------
    def positive_growth_share(self, series: str, base: int, end: int, country: str) -> float:
        """One country's share of the GROSS positive addition across ASEAN-10.

        Gross, not net: countries that fell are floored at zero rather than
        subtracted. Netting them off would let a decline elsewhere inflate the
        share of whoever grew, which is a different claim from the one made.
        """
        start = self.asean.xs(base, level="year")[series]
        finish = self.asean.xs(end, level="year")[series]
        positive = (finish - start).clip(lower=0)
        return float(positive.loc[country] / positive.sum())


# --------------------------------------------------------------------------
# Voice 2 -- look the claim up in the Phase 3 metric interface
# --------------------------------------------------------------------------

def load_fact_metrics() -> list[dict[str, str]]:
    with FACT_METRICS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != contract.EXPECTED_PHASE3_FACT_METRIC_ROWS:
        raise AssertionError(
            f"03_fact_metrics.csv co {len(rows)} dong, hop dong cho "
            f"{contract.EXPECTED_PHASE3_FACT_METRIC_ROWS}"
        )
    fingerprints = {r["phase2_input_fingerprint"] for r in rows}
    if fingerprints != {contract.EXPECTED_PHASE2_INPUT_FINGERPRINT}:
        raise AssertionError(f"dau van tay Phase 2 khong khop: {sorted(fingerprints)}")
    return rows


def lookup(rows: list[dict[str, str]], keys: dict[str, str]) -> tuple[float | None, str]:
    """Return the single matching value plus a human-readable locator.

    A key that matches more than one row is a failure, not a case to resolve by
    taking the first: it means the claim is under-specified and the number on the
    slide would depend on row order.
    """
    hits = [r for r in rows if all(r.get(k) == v for k, v in keys.items())]
    locator = " | ".join(f"{k}={v}" for k, v in sorted(keys.items()))
    if len(hits) != 1:
        raise LookupError(f"{len(hits)} dong khop cho khoa [{locator}]")
    raw = hits[0]["metric_value"]
    return (None if raw == "" else float(raw)), locator


# --------------------------------------------------------------------------

def main() -> int:
    fact_rows = load_fact_metrics()
    recomputer = Recomputer()
    handlers: dict[str, Callable[..., float]] = {
        name: getattr(recomputer, name)
        for name in dir(recomputer)
        if not name.startswith("_") and callable(getattr(recomputer, name))
    }

    evidence: list[dict[str, Any]] = []
    failures: list[str] = []

    for claim in CLAIMS:
        handler_name, *args = claim.recompute
        row: dict[str, Any] = {
            "claim_id": claim.claim_id,
            "finding_id": claim.finding_id,
            "claim_vi": claim.claim_vi,
            "unit": claim.unit,
            "locked_value": repr(claim.value),
            "fact_metrics_value": "",
            "recomputed_value": "",
            "source_file": "output/stats/03_fact_metrics.csv",
            "source_locator": "",
            "recompute_call": f"{handler_name}({', '.join(map(repr, args))})",
            "max_abs_delta": "",
            "status": "",
            "failure_reason": "",
        }

        try:
            table_value, locator = lookup(fact_rows, claim.lookup)
            row["source_locator"] = locator
            if table_value is None:
                raise LookupError("o trong 03_fact_metrics.csv de trong")
            row["fact_metrics_value"] = repr(table_value)

            if handler_name not in handlers:
                raise LookupError(f"khong co nhanh tinh lai ten `{handler_name}`")
            recomputed = handlers[handler_name](*args)
            row["recomputed_value"] = repr(recomputed)

            deltas = [abs(claim.value - table_value),
                      abs(claim.value - recomputed),
                      abs(table_value - recomputed)]
            row["max_abs_delta"] = repr(max(deltas))
            if max(deltas) > TOL:
                raise ValueError(
                    f"ba nguon lech qua dung sai {TOL}: hop dong={claim.value!r} "
                    f"bang={table_value!r} tinh lai={recomputed!r}"
                )
            row["status"] = "MATCH"
        except (LookupError, ValueError, KeyError, AssertionError) as error:
            row["status"] = "MISMATCH"
            row["failure_reason"] = str(error).replace("\n", " ")
            failures.append(f"{claim.claim_id}: {error}")

        evidence.append(row)

    EVIDENCE_OUT.parent.mkdir(parents=True, exist_ok=True)
    with EVIDENCE_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(evidence[0].keys()))
        writer.writeheader()
        writer.writerows(evidence)
    print(f"  -> {EVIDENCE_OUT}")

    matched = sum(1 for r in evidence if r["status"] == "MATCH")
    if failures:
        for line in failures:
            print(f"  MISMATCH {line}")
        print(f"\nPHASE 6 FINDING VERIFY: FAIL | {matched}/{len(evidence)} khop | "
              f"{len(failures)} claim lech")
        return 1

    findings = sorted({r["finding_id"] for r in evidence})
    print(f"\nPHASE 6 FINDING VERIFY: PASS | {matched}/{len(evidence)} claim khop ba chieu | "
          f"{len(findings)} phat hien | method_version={contract.METHOD_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
