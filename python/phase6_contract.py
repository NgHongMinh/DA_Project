"""Locked contract for the Phase 6 findings that reach the report and the slides.

Why this file exists
--------------------
`docs/NhatKyPhanTich.md` line 13 binds the project to one rule: *every number that
reaches `BaoCao.md` must be recomputed from source, never copied from the journal*.
A journal entry is a note taken at the time; by the time it reaches a slide, three
phases of rebuilds have happened underneath it.

So the numbers below are NOT the authority. They are one of three voices that must
agree before a number is allowed onto a slide:

1. the literals here, transcribed by hand from the findings that were selected;
2. `output/stats/03_fact_metrics.csv`, the Phase 3 metric interface, looked up by key;
3. an independent recomputation from `output/clean/*.csv`, which never reads either
   of the other two.

`06_verify_findings.py` runs all three and refuses to publish when any pair
disagrees. Two sources echoing each other would prove nothing, which is why the
third path re-derives the aggregation from the fact table rather than reading a
precomputed row.

Scale trap, inherited from `05_acceptance.dax`
----------------------------------------------
Reconciliation always happens on the STORAGE scale of `03_fact_metrics.csv`. Only
`share_electricity_pct` is held on 0-100; every other ratio is on 0-1. Comparing a
stored 0.671023268910 against a displayed 67.102326891 is off by 66.43 -- that is a
unit error wearing the costume of a rounding difference.

Column-name trap
----------------
In `03_fact_metrics.csv` the unit column is `unit`. The name `unit_stored` belongs
to `03_metric_definitions.csv` and to the PHASE5 prose. Mixing them raises KeyError
rather than failing silently, but knowing costs less than finding out.
"""
from __future__ import annotations

from typing import Final, NamedTuple


# ---------------------------------------------------------------------------
# Release baseline -- inherited, not re-decided
# ---------------------------------------------------------------------------

METHOD_VERSION: Final = "phase6_v1"

EXPECTED_PHASE2_INPUT_FINGERPRINT: Final = (
    "64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10"
)
EXPECTED_PHASE3_FACT_METRIC_ROWS: Final = 18_926
EXPECTED_ARCHIVE_CSV_COUNT: Final = 17

YEAR_START: Final = 2000
YEAR_END: Final = 2021

# Absolute tolerance between the three voices. `03_fact_metrics.csv` stores twelve
# significant figures, and the recomputation runs the same float64 arithmetic in a
# different order, so the gap is float-association noise rather than method drift.
NUMERIC_TOLERANCE: Final = 1e-9

ASEAN_10: Final = (
    "Brunei", "Cambodia", "Indonesia", "Laos", "Malaysia",
    "Myanmar", "Philippines", "Singapore", "Thailand", "Vietnam",
)

# The four generation metrics that make up RENEWABLE_TOTAL, and the two that make
# up MODERN_WIND_SOLAR. Phase 2 produced sixteen metric keys; only these carry
# generation in TWh, and the other twelve are shares or capacity.
GENERATION_KEYS: Final[dict[str, str]] = {
    "hydro": "hydro_generation_twh",
    "other_renewables": "other_renewables_generation_twh",
    "solar": "solar_generation_twh",
    "wind": "wind_generation_twh",
}
RENEWABLE_TOTAL_KEYS: Final = tuple(GENERATION_KEYS.values())
MODERN_KEYS: Final = (GENERATION_KEYS["wind"], GENERATION_KEYS["solar"])

# Share of electricity is NOT a sum of the four technologies: Phase 2 carries it as
# its own reported metric per technology. It is also the one metric held on a 0-100
# scale while every other ratio in this contract is on 0-1 -- see the module
# docstring. Reading it as a ratio understates it by a factor of a hundred.
SHARE_ELECTRICITY_KEYS: Final[dict[str, str]] = {
    "RENEWABLE_TOTAL": "renewables_share_electricity_pct",
    "HYDRO": "hydro_share_electricity_pct",
    "SOLAR": "solar_share_electricity_pct",
    "WIND": "wind_share_electricity_pct",
}

# The six ASEAN countries with no wind generation at all in 2021. Locked one row
# per country rather than as a single count, because `03_fact_metrics.csv` carries
# `positive_n` only for RENEWABLE_TOTAL and MODERN_WIND_SOLAR -- there is no
# per-technology count row to look a "6 of 10" claim up against, and a claim with
# no lookup would have two voices instead of three.
WIND_ZERO_COUNTRIES_2021: Final = (
    "Brunei", "Cambodia", "Laos", "Malaysia", "Myanmar", "Singapore",
)


class Claim(NamedTuple):
    """One number that is allowed to appear in the report or on a slide.

    `lookup` is the key into `03_fact_metrics.csv`; `recompute` names the
    independent derivation in `06_verify_findings.py`. A claim with no recompute
    handler is a claim that only has two voices, and the verifier rejects it.
    """

    claim_id: str
    finding_id: str
    claim_vi: str
    value: float
    unit: str
    lookup: dict[str, str]
    recompute: tuple  # (handler_name, *args)


def _year(metric: str, series: str, subject: str, scope: str, year: int) -> dict[str, str]:
    return {
        "metric_name": metric,
        "subject_key": subject,
        "series_key": series,
        "comparison_scope": scope,
        "period_type": "YEAR",
        "period_key": f"Y{year}",
    }


# ---------------------------------------------------------------------------
# Finding 1 -- P3-01. Scale grew, share of the world barely moved.
# ---------------------------------------------------------------------------

F1: Final = (
    Claim("F1_ASEAN_2000", "P3-01",
          "Tổng sản lượng NLTT của ASEAN-10 năm 2000",
          72.800904, "TWh",
          _year("generation_twh", "RENEWABLE_TOTAL", "ASEAN_10", "ASEAN_10", 2000),
          ("asean_generation", "RENEWABLE_TOTAL", 2000)),
    Claim("F1_ASEAN_2021", "P3-01",
          "Tổng sản lượng NLTT của ASEAN-10 năm 2021",
          289.6557446, "TWh",
          _year("generation_twh", "RENEWABLE_TOTAL", "ASEAN_10", "ASEAN_10", 2021),
          ("asean_generation", "RENEWABLE_TOTAL", 2021)),
    Claim("F1_WORLD_2000", "P3-01",
          "Tổng sản lượng NLTT toàn thế giới năm 2000",
          2854.49, "TWh",
          _year("generation_twh", "RENEWABLE_TOTAL", "WORLD_REPORTED", "WORLD_REPORTED", 2000),
          ("world_generation", "RENEWABLE_TOTAL", 2000)),
    Claim("F1_WORLD_2021", "P3-01",
          "Tổng sản lượng NLTT toàn thế giới năm 2021",
          7885.04005, "TWh",
          _year("generation_twh", "RENEWABLE_TOTAL", "WORLD_REPORTED", "WORLD_REPORTED", 2021),
          ("world_generation", "RENEWABLE_TOTAL", 2021)),
    Claim("F1_SHARE_2000", "P3-01",
          "Tỷ trọng ASEAN-10 trong tổng NLTT thế giới, năm 2000",
          0.0255039968611, "ratio",
          _year("asean_share_world", "RENEWABLE_TOTAL", "ASEAN_10", "WORLD_REPORTED", 2000),
          ("asean_share_world", "RENEWABLE_TOTAL", 2000)),
    Claim("F1_SHARE_2021", "P3-01",
          "Tỷ trọng ASEAN-10 trong tổng NLTT thế giới, năm 2021",
          0.0367348476055, "ratio",
          _year("asean_share_world", "RENEWABLE_TOTAL", "ASEAN_10", "WORLD_REPORTED", 2021),
          ("asean_share_world", "RENEWABLE_TOTAL", 2021)),
)

# ---------------------------------------------------------------------------
# Finding 2 -- P3-02 + P3-03. Wind and solar exploded from a floor of exactly
# zero, and hydro is still the largest single technology in 2021.
# ---------------------------------------------------------------------------

F2: Final = (
    Claim("F2_MODERN_2000", "P3-02",
          "Gió + mặt trời của ASEAN-10 năm 2000",
          0.0, "TWh",
          _year("generation_twh", "MODERN_WIND_SOLAR", "ASEAN_10", "ASEAN_10", 2000),
          ("asean_generation", "MODERN_WIND_SOLAR", 2000)),
    Claim("F2_MODERN_2010", "P3-02",
          "Gió + mặt trời của ASEAN-10 năm 2010",
          0.13, "TWh",
          _year("generation_twh", "MODERN_WIND_SOLAR", "ASEAN_10", "ASEAN_10", 2010),
          ("asean_generation", "MODERN_WIND_SOLAR", 2010)),
    Claim("F2_MODERN_2021", "P3-02",
          "Gió + mặt trời của ASEAN-10 năm 2021",
          42.73, "TWh",
          _year("generation_twh", "MODERN_WIND_SOLAR", "ASEAN_10", "ASEAN_10", 2021),
          ("asean_generation", "MODERN_WIND_SOLAR", 2021)),
    Claim("F2_HYDRO_2021", "P3-03",
          "Thuỷ điện của ASEAN-10 năm 2021",
          185.58, "TWh",
          _year("generation_twh", "HYDRO", "ASEAN_10", "ASEAN_10", 2021),
          ("asean_generation", "HYDRO", 2021)),
    Claim("F2_OTHER_2021", "P3-03",
          "Nguồn tái tạo khác của ASEAN-10 năm 2021",
          61.3457446, "TWh",
          _year("generation_twh", "OTHER_RENEWABLES", "ASEAN_10", "ASEAN_10", 2021),
          ("asean_generation", "OTHER_RENEWABLES", 2021)),
    Claim("F2_SOLAR_2021", "P3-03",
          "Mặt trời của ASEAN-10 năm 2021",
          34.43, "TWh",
          _year("generation_twh", "SOLAR", "ASEAN_10", "ASEAN_10", 2021),
          ("asean_generation", "SOLAR", 2021)),
    Claim("F2_WIND_2021", "P3-03",
          "Gió của ASEAN-10 năm 2021",
          8.3, "TWh",
          _year("generation_twh", "WIND", "ASEAN_10", "ASEAN_10", 2021),
          ("asean_generation", "WIND", 2021)),
)

# ---------------------------------------------------------------------------
# Finding 3 -- P3-06. Changing the definition of "renewable" reorders ASEAN.
# ---------------------------------------------------------------------------

def _rank_claims() -> tuple[Claim, ...]:
    """Six countries x two measures, plus the rank change between them.

    Six rather than ten: these are the countries whose position actually moves,
    plus Vietnam, which holds rank 1 on BOTH measures and is the control that
    shows the reordering is not an artefact of the whole board shifting.
    """
    locked = {
        "Vietnam": (1, 1, 0),
        "Indonesia": (2, 6, -4),
        "Laos": (4, 9, -5),
        "Thailand": (5, 2, 3),
        "Philippines": (6, 3, 3),
        "Singapore": (9, 5, 4),
    }
    out: list[Claim] = []
    for country, (total_rank, modern_rank, gain) in locked.items():
        out.append(Claim(
            f"F3_RANK_TOTAL_{country}", "P3-06",
            f"Hạng ASEAN của {country} năm 2021, đo bằng tổng NLTT",
            float(total_rank), "rank",
            _year("asean_rank", "RENEWABLE_TOTAL", country, "ASEAN_10", 2021),
            ("asean_rank", "RENEWABLE_TOTAL", 2021, country)))
        out.append(Claim(
            f"F3_RANK_MODERN_{country}", "P3-06",
            f"Hạng ASEAN của {country} năm 2021, đo bằng gió + mặt trời",
            float(modern_rank), "rank",
            _year("asean_rank", "MODERN_WIND_SOLAR", country, "ASEAN_10", 2021),
            ("asean_rank", "MODERN_WIND_SOLAR", 2021, country)))
        out.append(Claim(
            f"F3_GAIN_{country}", "P3-06",
            f"Số bậc {country} thay đổi khi đổi cách đo",
            float(gain), "rank_change",
            _year("modern_rank_gain", "MODERN_WIND_SOLAR", country, "ASEAN_10", 2021),
            ("rank_gain", 2021, country)))
    return tuple(out)


F3: Final = _rank_claims()

# ---------------------------------------------------------------------------
# Finding 4 -- P3-07 + P3-09. Vietnam holds two thirds of ASEAN wind and solar,
# and two thirds of everything the region added.
# ---------------------------------------------------------------------------

F4: Final = (
    Claim("F4_VN_TOTAL_2021", "P3-07",
          "Sản lượng NLTT của Việt Nam năm 2021",
          104.2180361, "TWh",
          _year("generation_twh", "RENEWABLE_TOTAL", "Vietnam", "ASEAN_10", 2021),
          ("country_generation", "RENEWABLE_TOTAL", 2021, "Vietnam")),
    Claim("F4_VN_MODERN_2021", "P3-07",
          "Sản lượng gió + mặt trời của Việt Nam năm 2021",
          28.16, "TWh",
          _year("generation_twh", "MODERN_WIND_SOLAR", "Vietnam", "ASEAN_10", 2021),
          ("country_generation", "MODERN_WIND_SOLAR", 2021, "Vietnam")),
    Claim("F4_VN_SHARE_TOTAL", "P3-07",
          "Tỷ trọng Việt Nam trong tổng NLTT của ASEAN-10, năm 2021",
          0.359799651976, "ratio",
          _year("country_share_asean", "RENEWABLE_TOTAL", "Vietnam", "ASEAN_10", 2021),
          ("country_share_asean", "RENEWABLE_TOTAL", 2021, "Vietnam")),
    Claim("F4_VN_SHARE_MODERN", "P3-07",
          "Tỷ trọng Việt Nam trong gió + mặt trời của ASEAN-10, năm 2021",
          0.659021764568, "ratio",
          _year("country_share_asean", "MODERN_WIND_SOLAR", "Vietnam", "ASEAN_10", 2021),
          ("country_share_asean", "MODERN_WIND_SOLAR", 2021, "Vietnam")),
    Claim("F4_VN_GLOBAL_RANK_TOTAL", "P3-07",
          "Hạng toàn cầu của Việt Nam năm 2021 theo tổng NLTT",
          16.0, "rank",
          _year("global_rank", "RENEWABLE_TOTAL", "Vietnam", "GLOBAL_CURRENT_COUNTRIES", 2021),
          ("global_rank", "RENEWABLE_TOTAL", 2021, "Vietnam")),
    Claim("F4_VN_GLOBAL_RANK_MODERN", "P3-07",
          "Hạng toàn cầu của Việt Nam năm 2021 theo gió + mặt trời",
          17.0, "rank",
          _year("global_rank", "MODERN_WIND_SOLAR", "Vietnam", "GLOBAL_CURRENT_COUNTRIES", 2021),
          ("global_rank", "MODERN_WIND_SOLAR", 2021, "Vietnam")),
    Claim("F4_VN_GROWTH_TOTAL", "P3-09",
          "Phần đóng góp của Việt Nam vào toàn bộ mức tăng dương NLTT của ASEAN-10, 2010–2021",
          0.423780539369, "ratio",
          {"metric_name": "positive_growth_share", "subject_key": "Vietnam",
           "series_key": "RENEWABLE_TOTAL", "comparison_scope": "ASEAN_10",
           "period_type": "INTERVAL", "period_key": "I2010_2021"},
          ("positive_growth_share", "RENEWABLE_TOTAL", 2010, 2021, "Vietnam")),
    Claim("F4_VN_GROWTH_MODERN", "P3-09",
          "Phần đóng góp của Việt Nam vào mức tăng dương gió + mặt trời của ASEAN-10, 2010–2021",
          0.65985915493, "ratio",
          {"metric_name": "positive_growth_share", "subject_key": "Vietnam",
           "series_key": "MODERN_WIND_SOLAR", "comparison_scope": "ASEAN_10",
           "period_type": "INTERVAL", "period_key": "I2010_2021"},
          ("positive_growth_share", "MODERN_WIND_SOLAR", 2010, 2021, "Vietnam")),
)

# ---------------------------------------------------------------------------
# Finding 5 -- P3-04. The regional momentum sits in very few countries.
# ---------------------------------------------------------------------------

F5: Final = (
    Claim("F5_TOP1_TOTAL", "P3-04",
          "Tỷ trọng nước dẫn đầu trong tổng NLTT của ASEAN-10, năm 2021",
          0.359799651976, "ratio",
          _year("top1_share", "RENEWABLE_TOTAL", "ASEAN_10", "ASEAN_10", 2021),
          ("top_n_share", "RENEWABLE_TOTAL", 2021, 1)),
    Claim("F5_TOP3_TOTAL", "P3-04",
          "Tỷ trọng ba nước dẫn đầu trong tổng NLTT của ASEAN-10, năm 2021",
          0.67102326891, "ratio",
          _year("top3_share", "RENEWABLE_TOTAL", "ASEAN_10", "ASEAN_10", 2021),
          ("top_n_share", "RENEWABLE_TOTAL", 2021, 3)),
    Claim("F5_TOP1_MODERN", "P3-04",
          "Tỷ trọng nước dẫn đầu trong gió + mặt trời của ASEAN-10, năm 2021",
          0.659021764568, "ratio",
          _year("top1_share", "MODERN_WIND_SOLAR", "ASEAN_10", "ASEAN_10", 2021),
          ("top_n_share", "MODERN_WIND_SOLAR", 2021, 1)),
    Claim("F5_TOP3_MODERN", "P3-04",
          "Tỷ trọng ba nước dẫn đầu trong gió + mặt trời của ASEAN-10, năm 2021",
          0.922536859349, "ratio",
          _year("top3_share", "MODERN_WIND_SOLAR", "ASEAN_10", "ASEAN_10", 2021),
          ("top_n_share", "MODERN_WIND_SOLAR", 2021, 3)),
    Claim("F5_HHI_TOTAL", "P3-04",
          "Chỉ số tập trung HHI của tổng NLTT trong ASEAN-10, năm 2021",
          0.207886216029, "ratio",
          _year("hhi", "RENEWABLE_TOTAL", "ASEAN_10", "ASEAN_10", 2021),
          ("hhi", "RENEWABLE_TOTAL", 2021)),
    Claim("F5_HHI_MODERN", "P3-04",
          "Chỉ số tập trung HHI của gió + mặt trời trong ASEAN-10, năm 2021",
          0.480403925201, "ratio",
          _year("hhi", "MODERN_WIND_SOLAR", "ASEAN_10", "ASEAN_10", 2021),
          ("hhi", "MODERN_WIND_SOLAR", 2021)),
    Claim("F5_GINI_TOTAL", "P3-04",
          "Hệ số Gini của tổng NLTT trong ASEAN-10, năm 2021",
          0.529218182611, "ratio",
          _year("gini", "RENEWABLE_TOTAL", "ASEAN_10", "ASEAN_10", 2021),
          ("gini", "RENEWABLE_TOTAL", 2021)),
    Claim("F5_GINI_MODERN", "P3-04",
          "Hệ số Gini của gió + mặt trời trong ASEAN-10, năm 2021",
          0.771284811608, "ratio",
          _year("gini", "MODERN_WIND_SOLAR", "ASEAN_10", "ASEAN_10", 2021),
          ("gini", "MODERN_WIND_SOLAR", 2021)),
)


# ---------------------------------------------------------------------------
# Finding 6 -- P7-01 + P7-02. Two facts the conclusions in section 1.6 rest on
# that no earlier finding needed, so they enter the contract here.
# ---------------------------------------------------------------------------

def _wind_zero_claims() -> tuple[Claim, ...]:
    return tuple(
        Claim(
            f"F6_WIND_ZERO_{country}", "P7-02",
            f"Sản lượng điện gió của {country} năm 2021",
            0.0, "TWh",
            _year("generation_twh", "WIND", country, "ASEAN_10", 2021),
            ("country_generation", "WIND", 2021, country),
        )
        for country in WIND_ZERO_COUNTRIES_2021
    )


F6: Final = _wind_zero_claims() + (
    Claim("F6_VN_TOTAL_2000", "P7-01",
          "Sản lượng NLTT của Việt Nam năm 2000",
          14.55, "TWh",
          _year("generation_twh", "RENEWABLE_TOTAL", "Vietnam", "ASEAN_10", 2000),
          ("country_generation", "RENEWABLE_TOTAL", 2000, "Vietnam")),
    Claim("F6_VN_SHARE_ELEC_2000", "P7-01",
          "Tỷ trọng NLTT trong sản lượng điện của Việt Nam, năm 2000",
          54.781628, "pct",
          _year("share_electricity_pct", "RENEWABLE_TOTAL", "Vietnam", "ASEAN_10", 2000),
          ("country_share_electricity", "RENEWABLE_TOTAL", 2000, "Vietnam")),
    Claim("F6_VN_SHARE_ELEC_2021", "P7-01",
          "Tỷ trọng NLTT trong sản lượng điện của Việt Nam, năm 2021",
          42.578747, "pct",
          _year("share_electricity_pct", "RENEWABLE_TOTAL", "Vietnam", "ASEAN_10", 2021),
          ("country_share_electricity", "RENEWABLE_TOTAL", 2021, "Vietnam")),
)


# ---------------------------------------------------------------------------
# Finding 7 -- P7-03. The descriptive statistics required by section 1.3, and the
# reason the assignment asks for percentiles at all.
# ---------------------------------------------------------------------------
#
# Solar in ASEAN-10, 2021, under the three filter variants Phase 3 defines:
#   ALL_OBSERVED  every observed country-year
#   POSITIVE      value > 0
#   MATERIAL      value_class == "Material", i.e. at or above the 0.05 TWh floor
#
# Two definitions here are easy to get wrong in a way that produces a plausible
# number rather than an error, so the recomputation must match them exactly:
#   * `sd` is the POPULATION standard deviation, numpy `ddof=0`.
#   * `skewness` is the BIAS-CORRECTED third moment, scipy `bias=False`.
#
# Unit label `index` rather than `ratio` is deliberate. Phase 3 stamps CV and
# skewness as `ratio` because they are dimensionless, but this contract uses
# `ratio` to mean a bounded share and validates it into [0, 1]. CV of 2.19 is a
# perfectly good coefficient of variation and a nonsense share; the same word
# carries two meanings across the two files, so this one does not reuse it.
_SOLAR_2021_STATS: Final[dict[str, dict[str, float]]] = {
    "ALL_OBSERVED": {
        "n": 10.0, "mean": 3.443, "median": 0.52, "sd": 7.54379221612,
        "cv": 2.19105205231, "skewness": 3.0145714003,
        "p25": 0.1225, "p75": 1.5, "p90": 6.438,
    },
    "POSITIVE": {
        "n": 9.0, "mean": 3.82555555556, "median": 0.67, "sd": 7.85929472537,
        "cv": 2.05441918467, "skewness": 2.86205120742,
    },
    "MATERIAL": {
        "n": 8.0, "mean": 4.29875, "median": 1.085, "sd": 8.21427787073,
        "cv": 1.91085265966, "skewness": 2.70114107205,
    },
}

_STAT_UNITS: Final[dict[str, str]] = {
    "n": "count", "mean": "TWh", "median": "TWh", "sd": "TWh",
    "p25": "TWh", "p75": "TWh", "p90": "TWh",
    "cv": "index", "skewness": "index",
}

_STAT_LABELS: Final[dict[str, str]] = {
    "n": "Số nước quan sát được", "mean": "Trung bình", "median": "Trung vị",
    "sd": "Độ lệch chuẩn", "cv": "Hệ số biến thiên", "skewness": "Độ lệch phân phối",
    "p25": "Phân vị 25", "p75": "Phân vị 75", "p90": "Phân vị 90",
}


def _distribution_claims() -> tuple[Claim, ...]:
    out: list[Claim] = []
    for variant, stats in _SOLAR_2021_STATS.items():
        for stat, value in stats.items():
            out.append(Claim(
                f"F7_SOLAR2021_{variant}_{stat.upper()}", "P7-03",
                f"{_STAT_LABELS[stat]} — mặt trời ASEAN-10 năm 2021, tập {variant}",
                value, _STAT_UNITS[stat],
                {
                    "metric_name": stat,
                    "subject_key": "ASEAN_10",
                    "series_key": "SOLAR",
                    "comparison_scope": "ASEAN_10",
                    "filter_variant": variant,
                    "period_type": "YEAR",
                    "period_key": "Y2021",
                },
                ("distribution_stat", stat, "SOLAR", 2021, variant),
            ))
    return tuple(out)


F7: Final = _distribution_claims()


CLAIMS: Final[tuple[Claim, ...]] = F1 + F2 + F3 + F4 + F5 + F6 + F7


# The one-sentence message each finding must carry. Gate E5 holds every slide to
# exactly one of these; a slide needing two sentences is a slide carrying two
# messages, and it gets split rather than reworded.
FINDING_MESSAGES: Final[dict[str, str]] = {
    "P3-01": "ASEAN tăng gần bốn lần về quy mô năng lượng tái tạo, nhưng chỗ đứng "
             "của khu vực trên bản đồ thế giới gần như không đổi.",
    "P3-02": "Gió và mặt trời của ASEAN đi lên từ mức đúng bằng không, nên tốc độ "
             "tăng ấn tượng đang nói về một nền xuất phát rất thấp.",
    "P3-03": "Dù gió và mặt trời tăng nhanh, thuỷ điện vẫn là nguồn lớn nhất của "
             "ASEAN năm 2021.",
    "P3-06": "Đổi định nghĩa 'năng lượng tái tạo' là đổi luôn thứ hạng khu vực, "
             "nên mọi bảng xếp hạng phải nói rõ nó đang đo cái gì.",
    "P3-07": "Việt Nam nắm khoảng hai phần ba lượng gió và mặt trời của cả ASEAN.",
    "P3-09": "Gần như toàn bộ mức tăng gió và mặt trời của ASEAN giai đoạn "
             "2010–2021 đến từ một nước duy nhất.",
    "P3-04": "Đà tăng của khu vực tập trung vào rất ít nước, nên một con số trung "
             "bình cho ASEAN sẽ che mất bức tranh thật.",
    "P7-01": "Sản lượng tái tạo của Việt Nam tăng hơn bảy lần nhưng tỷ trọng của nó "
             "trong tổng điện năng lại giảm, vì tổng cầu điện tăng còn nhanh hơn.",
    "P7-02": "Sáu trong mười nước ASEAN không sản xuất một kWh điện gió nào trong "
             "năm 2021.",
    "P7-03": "Phân phối sản lượng giữa các nước lệch mạnh đến mức trung bình gấp "
             "hơn sáu lần trung vị, nên phân vị mới là thống kê đọc được.",
}


def _validate_contract() -> None:
    """Cross-checks that must hold before anything downstream reads this file.

    These are relationships between the locked numbers, not restatements of them.
    A transcription slip that keeps a value self-consistent is rare; one that
    breaks an identity below is what this catches.
    """
    ids = [c.claim_id for c in CLAIMS]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise AssertionError(f"trung claim_id: {dupes}")

    by_id = {c.claim_id: c.value for c in CLAIMS}

    # The four technologies must reconstitute the regional total exactly. This is
    # the identity that P3-03 rests on, and the one Gate B7 also checks in DAX.
    mix = sum(by_id[k] for k in
              ("F2_HYDRO_2021", "F2_OTHER_2021", "F2_SOLAR_2021", "F2_WIND_2021"))
    if abs(mix - by_id["F1_ASEAN_2021"]) > NUMERIC_TOLERANCE:
        raise AssertionError(
            f"bon cong nghe cong lai {mix!r} != tong khu vuc {by_id['F1_ASEAN_2021']!r}"
        )

    # Wind + solar must equal the modern measure, or the two findings disagree
    # about what "modern" means.
    modern = by_id["F2_WIND_2021"] + by_id["F2_SOLAR_2021"]
    if abs(modern - by_id["F2_MODERN_2021"]) > NUMERIC_TOLERANCE:
        raise AssertionError(f"gio+mat troi {modern!r} != modern {by_id['F2_MODERN_2021']!r}")

    # Vietnam is rank 1 on both measures, so its country share IS the top-1 share.
    # If these ever diverge, either the ranking or the share is wrong.
    for share_id, top1_id in (("F4_VN_SHARE_TOTAL", "F5_TOP1_TOTAL"),
                              ("F4_VN_SHARE_MODERN", "F5_TOP1_MODERN")):
        if abs(by_id[share_id] - by_id[top1_id]) > NUMERIC_TOLERANCE:
            raise AssertionError(f"{share_id} != {top1_id}")

    # Vietnam's share of the region must be reproducible from the two TWh figures.
    for gen_id, region_id, share_id in (
        ("F4_VN_TOTAL_2021", "F1_ASEAN_2021", "F4_VN_SHARE_TOTAL"),
        ("F4_VN_MODERN_2021", "F2_MODERN_2021", "F4_VN_SHARE_MODERN"),
    ):
        implied = by_id[gen_id] / by_id[region_id]
        if abs(implied - by_id[share_id]) > 1e-9:
            raise AssertionError(f"{gen_id}/{region_id} = {implied!r} != {share_id}")

    # Top-3 cannot be below top-1, and neither can exceed the whole.
    for top1, top3 in (("F5_TOP1_TOTAL", "F5_TOP3_TOTAL"),
                       ("F5_TOP1_MODERN", "F5_TOP3_MODERN")):
        if not (by_id[top1] <= by_id[top3] <= 1.0):
            raise AssertionError(f"{top1} <= {top3} <= 1 khong thoa")

    # The modern measure must be the more concentrated one on all three indices --
    # that IS finding P3-04, so if it fails the finding is not what we think.
    for total, modern_id in (("F5_TOP3_TOTAL", "F5_TOP3_MODERN"),
                             ("F5_HHI_TOTAL", "F5_HHI_MODERN"),
                             ("F5_GINI_TOTAL", "F5_GINI_MODERN")):
        if not by_id[modern_id] > by_id[total]:
            raise AssertionError(f"{modern_id} phai lon hon {total} -- do la noi dung P3-04")

    # Rank gain must be the arithmetic difference of the two ranks, per country.
    for claim in F3:
        if not claim.claim_id.startswith("F3_GAIN_"):
            continue
        country = claim.claim_id[len("F3_GAIN_"):]
        total = by_id[f"F3_RANK_TOTAL_{country}"]
        modern_rank = by_id[f"F3_RANK_MODERN_{country}"]
        if claim.value != total - modern_rank:
            raise AssertionError(
                f"{country}: gain {claim.value} != {total} - {modern_rank}"
            )

    # Ranks must be a partial permutation of 1..10 on each measure -- no ties, no
    # duplicates. Six of ten countries are locked, so uniqueness is the test that
    # is available; a duplicate here means a transcription slip.
    for suffix in ("TOTAL", "MODERN"):
        ranks = [by_id[c.claim_id] for c in F3
                 if c.claim_id.startswith(f"F3_RANK_{suffix}_")]
        if len(ranks) != len(set(ranks)):
            raise AssertionError(f"hang {suffix} bi trung: {sorted(ranks)}")
        if not all(1 <= r <= 10 for r in ranks):
            raise AssertionError(f"hang {suffix} ngoai mien 1..10: {sorted(ranks)}")

    # Shares live on 0-1. This is the guard against the x100 scale trap the module
    # docstring warns about: a ratio that slipped to 0-100 fails here, loudly.
    for claim in CLAIMS:
        if claim.unit == "ratio" and not (0.0 <= claim.value <= 1.0):
            raise AssertionError(
                f"{claim.claim_id} don vi ratio nhung gia tri {claim.value} ngoai [0,1] "
                "-- nghi ngo lech thang x100"
            )

    # P7-01 is a decline: the 2021 share must be BELOW the 2000 share while output
    # rose. If either half flips, the finding says the opposite of what it claims.
    if not by_id["F6_VN_SHARE_ELEC_2021"] < by_id["F6_VN_SHARE_ELEC_2000"]:
        raise AssertionError("P7-01 doi ty trong GIAM, nhung 2021 khong nho hon 2000")
    if not by_id["F4_VN_TOTAL_2021"] > by_id["F6_VN_TOTAL_2000"]:
        raise AssertionError("P7-01 doi san luong TANG, nhung 2021 khong lon hon 2000")

    # Both share figures live on 0-100, not 0-1. A value that slipped to the ratio
    # scale would sit under 1 and pass every other check in this file silently.
    for claim in CLAIMS:
        if claim.unit == "pct" and not (1.0 < claim.value <= 100.0):
            raise AssertionError(
                f"{claim.claim_id} don vi pct nhung gia tri {claim.value} "
                "-- nghi ngo bi doc nham sang thang 0-1"
            )

    # The wind-zero claims must all actually be zero; a non-zero one means the
    # country list is stale and the "six of ten" sentence is wrong.
    for country in WIND_ZERO_COUNTRIES_2021:
        if by_id[f"F6_WIND_ZERO_{country}"] != 0.0:
            raise AssertionError(f"{country} duoc khoa la 0 nhung gia tri khac 0")
    if len(WIND_ZERO_COUNTRIES_2021) >= len(ASEAN_10):
        raise AssertionError("so nuoc gio bang 0 khong the bang hoac vuot ca khoi")

    # P7-03 is the skew argument. Three things must hold or the slide says
    # something the numbers do not support.
    for variant in _SOLAR_2021_STATS:
        mean = by_id[f"F7_SOLAR2021_{variant}_MEAN"]
        median = by_id[f"F7_SOLAR2021_{variant}_MEDIAN"]
        if not mean > median:
            raise AssertionError(f"{variant}: trung binh phai lon hon trung vi khi lech phai")
        if not by_id[f"F7_SOLAR2021_{variant}_SKEWNESS"] > 1.0:
            raise AssertionError(f"{variant}: skew <= 1 thi khong con la lech manh")
        if not by_id[f"F7_SOLAR2021_{variant}_CV"] > 1.0:
            raise AssertionError(f"{variant}: CV <= 1 thi phan tan khong con cao")

    # Dropping zeros then dropping trace values can only shrink the group.
    n_all = by_id["F7_SOLAR2021_ALL_OBSERVED_N"]
    n_pos = by_id["F7_SOLAR2021_POSITIVE_N"]
    n_mat = by_id["F7_SOLAR2021_MATERIAL_N"]
    if not n_all >= n_pos >= n_mat:
        raise AssertionError(f"co mau phai thu hep dan: {n_all} >= {n_pos} >= {n_mat}")
    if n_all != float(len(ASEAN_10)):
        raise AssertionError(f"ALL_OBSERVED phai phu het {len(ASEAN_10)} nuoc, dang la {n_all}")

    # Percentiles must be ordered. An unordered triple means a wrong method= or a
    # transcription slip, and both look reasonable in isolation.
    p25 = by_id["F7_SOLAR2021_ALL_OBSERVED_P25"]
    p50 = by_id["F7_SOLAR2021_ALL_OBSERVED_MEDIAN"]
    p75 = by_id["F7_SOLAR2021_ALL_OBSERVED_P75"]
    p90 = by_id["F7_SOLAR2021_ALL_OBSERVED_P90"]
    if not p25 <= p50 <= p75 <= p90:
        raise AssertionError(f"phan vi khong tang dan: {p25} {p50} {p75} {p90}")

    # Every finding that has claims must have a message, and vice versa.
    finding_ids = {c.finding_id for c in CLAIMS}
    if finding_ids != set(FINDING_MESSAGES):
        raise AssertionError(
            f"lech giua phat hien co claim {sorted(finding_ids)} "
            f"va phat hien co thong diep {sorted(FINDING_MESSAGES)}"
        )

    # Every claim must name a recompute handler; two voices are not three.
    without = [c.claim_id for c in CLAIMS if not c.recompute]
    if without:
        raise AssertionError(f"claim khong co nhanh tinh lai: {without}")


_validate_contract()
