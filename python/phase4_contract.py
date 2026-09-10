"""Locked release contract shared by the Phase 4 build and verification.

This module intentionally contains data and lightweight import-time checks only.
Keeping the visual, provenance, and acceptance constants in one place prevents
the chart builder and the independent release verifier from drifting apart.
"""
from __future__ import annotations

from typing import Final


# ---------------------------------------------------------------------------
# Release baseline and numerical conventions
# ---------------------------------------------------------------------------

METHOD_VERSION: Final = "phase4_v1"
PHASE4_METHOD_VERSION: Final = METHOD_VERSION

EXPECTED_PHASE2_INPUT_FINGERPRINT: Final = (
    "64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10"
)
EXPECTED_PHASE2_FINGERPRINT: Final = EXPECTED_PHASE2_INPUT_FINGERPRINT
EXPECTED_ARCHIVE_CSV_COUNT: Final = 17
EXPECTED_PHASE2_FACT_ROWS: Final = 89_075
EXPECTED_PHASE2_FACT_ENERGY_SHA256: Final = (
    "dfaca2c46efde54b506f317497d458ed864f88ab4a8d74de9665afaa467a4374"
)
EXPECTED_PHASE2_VALIDATION_ROWS: Final = 864
EXPECTED_PHASE2_VALIDATION_STATUS_COUNTS: Final = {
    "PASS": 560,
    "WARN": 268,
    "SKIP": 36,
}
EXPECTED_PHASE2_STATUS_COUNTS: Final = EXPECTED_PHASE2_VALIDATION_STATUS_COUNTS
EXPECTED_PHASE2_BLOCKING_FAILURES: Final = 0

EXPECTED_PHASE3_FACT_ROWS: Final = 18_926
EXPECTED_PHASE3_CROSSCHECK_ROWS: Final = 18_926
EXPECTED_PHASE3_VALIDATION_ROWS: Final = 92
EXPECTED_FACT_ROWS: Final = EXPECTED_PHASE3_FACT_ROWS
EXPECTED_CROSSCHECK_ROWS: Final = EXPECTED_PHASE3_CROSSCHECK_ROWS
EXPECTED_PHASE3_QUESTION_ROWS: Final = {
    "Q1": 5_544,
    "Q2": 3_608,
    "Q3": 1_980,
    "Q4": 1_382,
    "Q5": 5_950,
    "Q6": 462,
}
EXPECTED_QUESTION_ROWS: Final = EXPECTED_PHASE3_QUESTION_ROWS

YEAR_START: Final = 2000
YEAR_END: Final = 2021
YEARS: Final = tuple(range(YEAR_START, YEAR_END + 1))
EXPECTED_YEAR_COUNT: Final = len(YEARS)
MATERIAL_THRESHOLD_TWH: Final = 0.05
NUMERIC_TOLERANCE: Final = 1e-9
CAPACITY_FACTOR_DIVISOR: Final = 8.76
CAPACITY_FACTOR_TOLERANCE: Final = 1e-9
HASH_ALGORITHM: Final = "sha256"


# ---------------------------------------------------------------------------
# Rendering contract
# ---------------------------------------------------------------------------

CHART_WIDTH_PX: Final = 2_400
CHART_HEIGHT_PX: Final = 1_350
CHART_SIZE_PX: Final = (CHART_WIDTH_PX, CHART_HEIGHT_PX)
DIMENSIONS_PX: Final = CHART_SIZE_PX
CHART_DPI: Final = 200
DPI: Final = CHART_DPI
FIGURE_SIZE_INCHES: Final = (
    CHART_WIDTH_PX / CHART_DPI,
    CHART_HEIGHT_PX / CHART_DPI,
)
FIGSIZE: Final = FIGURE_SIZE_INCHES
FIGSIZE_INCHES: Final = FIGURE_SIZE_INCHES
FONT_FAMILY: Final = "DejaVu Sans"
BACKGROUND_COLOR: Final = "#FFFFFF"
FORBIDDEN_PLOTTING_TOKENS: Final = ("pie(", "twinx(", "twiny(")

TECHNOLOGY_SERIES: Final = (
    "HYDRO",
    "OTHER_RENEWABLES",
    "WIND",
    "SOLAR",
)
ANALYSIS_SERIES: Final = (
    "HYDRO",
    "WIND",
    "SOLAR",
    "OTHER_RENEWABLES",
    "RENEWABLE_TOTAL",
    "MODERN_WIND_SOLAR",
)
TECHNOLOGY_COLORS: Final = {
    "HYDRO": "#0072B2",
    "WIND": "#009E73",
    "SOLAR": "#E69F00",
    "OTHER_RENEWABLES": "#CC79A7",
    "RENEWABLE_TOTAL": "#374151",
    "MODERN_WIND_SOLAR": "#D55E00",
}
SERIES_COLORS: Final = TECHNOLOGY_COLORS

ASEAN_10: Final = (
    "Vietnam",
    "Thailand",
    "Indonesia",
    "Philippines",
    "Malaysia",
    "Singapore",
    "Myanmar",
    "Cambodia",
    "Laos",
    "Brunei",
)
COUNTRY_COLORS: Final = {
    "Vietnam": "#D55E00",
    "Thailand": "#0072B2",
    "Indonesia": "#009E73",
    "Philippines": "#E69F00",
    "Malaysia": "#CC79A7",
    "Singapore": "#56B4E9",
    "Myanmar": "#6B7280",
    "Cambodia": "#F0E442",
    "Laos": "#332288",
    "Brunei": "#88CCEE",
}
COUNTRY_LABELS_VI: Final = {
    "Vietnam": "Việt Nam",
    "Thailand": "Thái Lan",
    "Indonesia": "Indonesia",
    "Philippines": "Philippines",
    "Malaysia": "Malaysia",
    "Singapore": "Singapore",
    "Myanmar": "Myanmar",
    "Cambodia": "Campuchia",
    "Laos": "Lào",
    "Brunei": "Brunei",
}
SERIES_LABELS_VI: Final = {
    "HYDRO": "Thủy điện",
    "WIND": "Điện gió",
    "SOLAR": "Điện mặt trời",
    "OTHER_RENEWABLES": "NLTT khác",
    "RENEWABLE_TOTAL": "Tổng NLTT",
    "MODERN_WIND_SOLAR": "Gió + mặt trời",
}
VALUE_CLASS_LABELS_VI: Final = {
    "Zero": "Bằng 0",
    "Trace": "Dưới 0,05 TWh",
    "Material": "Từ 0,05 TWh",
    "Not observed": "Không quan sát",
}


# ---------------------------------------------------------------------------
# Phase 3 sources and trace keys
# ---------------------------------------------------------------------------

PHASE3_CSV_FILES: Final = (
    "03_fact_metrics.csv",
    "03_metric_definitions.csv",
    "03_crosscheck_results.csv",
    "03_validation_results.csv",
)
PHASE3_WORKBOOKS: Final = {
    "03_global_cross_section.xlsx": (
        "generation_stats", "country_values", "coverage", "metadata",
    ),
    "03_asean_cross_section.xlsx": (
        "generation_stats", "asean_annual", "country_year_values",
        "twh_vs_pct", "endpoint_change", "metadata",
    ),
    "03_vietnam_time_series.xlsx": (
        "annual", "annual_changes", "asean9_benchmark", "endpoint_change",
        "metadata",
    ),
    "03_ranking_comparison.xlsx": (
        "annual_ranks", "milestone_change", "cagr_ranking", "metadata",
    ),
    "03_entry_lag.xlsx": (
        "entry_status", "entry_summary", "method_notes", "metadata",
    ),
    "03_global_context.xlsx": (
        "annual_context", "period_growth", "annual_concentration",
        "growth_contribution", "world_reconciliation", "metadata",
    ),
}
EXPECTED_PHASE3_WORKBOOK_COUNT: Final = len(PHASE3_WORKBOOKS)

PHASE3_FACT_KEY_COLUMNS: Final = (
    "subject_type",
    "subject_key",
    "period_type",
    "period_key",
    "series_key",
    "metric_name",
    "comparison_scope",
    "filter_variant",
    "method_version",
)
PHASE3_REQUIRED_FACT_COLUMNS: Final = PHASE3_FACT_KEY_COLUMNS + (
    "question_id",
    "period_start_year",
    "period_end_year",
    "metric_value",
    "metric_text_value",
    "unit",
    "value_status",
    "exclusion_reason",
    "source_metric_keys",
    "phase2_input_fingerprint",
)
GENERATION_SOURCE_METRICS: Final = {
    "HYDRO": "hydro_generation_twh",
    "WIND": "wind_generation_twh",
    "SOLAR": "solar_generation_twh",
    "OTHER_RENEWABLES": "other_renewables_generation_twh",
}
CAPACITY_SOURCE_METRICS: Final = {
    "WIND": "wind_capacity_gw",
    "SOLAR": "solar_capacity_gw",
}


# ---------------------------------------------------------------------------
# Exact chart allow-list and manifest metadata
# ---------------------------------------------------------------------------

CHART_SPEC_KEYS: Final = frozenset({
    "chart_id",
    "file_name",
    "question_ids",
    "title_vi",
    "message_vi",
    "data_sheets",
    "source_locator",
    "period",
    "scope",
    "axis_mode",
    "limitation_vi",
})

CHART_SPECS: Final = (
    {
        "chart_id": "C01",
        "file_name": "04_01_global_asean_context.png",
        "question_ids": ("Q1",),
        "title_vi": "Điện tái tạo ASEAN trong bối cảnh thế giới, 2000–2021",
        "message_vi": "ASEAN tăng gần 4 lần nhưng vẫn là một phần nhỏ của thế giới.",
        "data_sheets": ("global_context",),
        "source_locator": "03_fact_metrics.csv | 03_global_context.xlsx:annual_context",
        "period": "2000–2021",
        "scope": "ASEAN-10 và thế giới được báo cáo",
        "axis_mode": "LOG_TWH_AND_LINEAR_RATIO_SEPARATE_PANELS",
        "limitation_vi": "Tổng thế giới là số được nguồn báo cáo; tỷ trọng không chứng minh quan hệ nhân quả.",
    },
    {
        "chart_id": "C02",
        "file_name": "04_02_asean_technology_trend.png",
        "question_ids": ("Q2",),
        "title_vi": "Cơ cấu sản lượng điện tái tạo ASEAN theo công nghệ",
        "message_vi": "Thủy điện vẫn lớn nhất; gió và mặt trời tăng rõ vào cuối kỳ.",
        "data_sheets": ("asean_technology",),
        "source_locator": "03_fact_metrics.csv | 03_asean_cross_section.xlsx:asean_annual",
        "period": "2000–2021",
        "scope": "ASEAN-10",
        "axis_mode": "LINEAR_STACKED_AREA",
        "limitation_vi": "Biểu đồ mô tả sản lượng, không đo công suất hay nguyên nhân tăng trưởng.",
    },
    {
        "chart_id": "C03",
        "file_name": "04_03_asean_country_mix_2021.png",
        "question_ids": ("Q2",),
        "title_vi": "Quy mô và cơ cấu điện tái tạo theo nước ASEAN năm 2021",
        "message_vi": "Quy mô và cơ cấu năm 2021 khác nhau rõ giữa các nước.",
        "data_sheets": ("country_mix_2021",),
        "source_locator": "03_fact_metrics.csv | 03_asean_cross_section.xlsx:country_year_values",
        "period": "2021",
        "scope": "ASEAN-10",
        "axis_mode": "LINEAR_STACKED_BAR_AND_SHARE_HEATMAP",
        "limitation_vi": "Một năm cắt ngang không thể hiện quỹ đạo hay nguyên nhân khác biệt.",
    },
    {
        "chart_id": "C04",
        "file_name": "04_04_asean_rank_shift_2021.png",
        "question_ids": ("Q3",),
        "title_vi": "Thay đổi thứ hạng ASEAN khi đổi cách đo, năm 2021",
        "message_vi": "Singapore tăng 4 bậc, Indonesia giảm 4 bậc và Lào giảm 5 bậc.",
        "data_sheets": ("rank_shift_2021",),
        "source_locator": "03_fact_metrics.csv | 03_ranking_comparison.xlsx:annual_ranks",
        "period": "2021",
        "scope": "ASEAN-10",
        "axis_mode": "REVERSED_LINEAR_RANK_DUMBBELL",
        "limitation_vi": "Thứ hạng chỉ so sánh hai thước đo trong cùng tập ASEAN-10 và giữ nguyên đồng hạng.",
    },
    {
        "chart_id": "C05",
        "file_name": "04_05_asean_small_multiples_shared.png",
        "question_ids": ("Q1",),
        "title_vi": "Tổng điện tái tạo ASEAN theo nước — chung thang đo",
        "message_vi": "Trục chung cho thấy chênh lệch quy mô tuyệt đối giữa các nước.",
        "data_sheets": ("small_multiples",),
        "source_locator": "03_fact_metrics.csv | 03_asean_cross_section.xlsx:country_year_values",
        "period": "2000–2021",
        "scope": "ASEAN-10",
        "axis_mode": "LINEAR_SMALL_MULTIPLES_SHARED_Y",
        "limitation_vi": "Trục chung có thể làm biến động của các nước quy mô nhỏ khó quan sát.",
    },
    {
        "chart_id": "C06",
        "file_name": "04_06_asean_small_multiples_free.png",
        "question_ids": ("Q1",),
        "title_vi": "Tổng điện tái tạo ASEAN theo nước — thang đo riêng",
        "message_vi": "Trục riêng cho thấy quỹ đạo nội tại của các nước quy mô nhỏ.",
        "data_sheets": ("small_multiples",),
        "source_locator": "03_fact_metrics.csv | 03_asean_cross_section.xlsx:country_year_values",
        "period": "2000–2021",
        "scope": "ASEAN-10",
        "axis_mode": "LINEAR_SMALL_MULTIPLES_FREE_Y",
        "limitation_vi": "Không dùng chiều cao giữa các panel để so sánh quy mô vì mỗi trục tung khác nhau.",
    },
    {
        "chart_id": "C07",
        "file_name": "04_07_vietnam_technology_trend.png",
        "question_ids": ("Q4",),
        "title_vi": "Sản lượng điện tái tạo Việt Nam theo công nghệ",
        "message_vi": "Gió và mặt trời tăng mạnh cuối kỳ nhưng thủy điện vẫn quan trọng.",
        "data_sheets": ("vietnam_technology",),
        "source_locator": "03_fact_metrics.csv | 03_vietnam_time_series.xlsx:annual",
        "period": "2000–2021",
        "scope": "Việt Nam",
        "axis_mode": "LINEAR_MULTI_SERIES",
        "limitation_vi": "Xu hướng mô tả không đủ để kết luận nguyên nhân hay tác động chính sách.",
    },
    {
        "chart_id": "C08",
        "file_name": "04_08_vietnam_twh_vs_share.png",
        "question_ids": ("Q5",),
        "title_vi": "Sản lượng và tỷ trọng điện của Việt Nam không luôn cùng hướng",
        "message_vi": "TWh và tỷ trọng điện không luôn đi cùng hướng.",
        "data_sheets": ("vietnam_q5",),
        "source_locator": "03_fact_metrics.csv | 03_asean_cross_section.xlsx:twh_vs_pct | 03_vietnam_time_series.xlsx:annual_changes",
        "period": "2000–2021",
        "scope": "Việt Nam",
        "axis_mode": "LINEAR_FOUR_PANELS_SHARED_X",
        "limitation_vi": "TWh và phần trăm nằm ở panel riêng; không suy diễn một đại lượng từ đại lượng còn lại.",
    },
    {
        "chart_id": "C09",
        "file_name": "04_09_vietnam_regional_global_position.png",
        "question_ids": ("Q4",),
        "title_vi": "Vị thế điện tái tạo của Việt Nam trong khu vực và thế giới",
        "message_vi": "Việt Nam nổi bật hơn ở gió + mặt trời so với tổng điện tái tạo.",
        "data_sheets": ("vietnam_position",),
        "source_locator": "03_fact_metrics.csv | 03_vietnam_time_series.xlsx:annual,asean9_benchmark",
        "period": "2000–2021; hạng toàn cầu tại 2021",
        "scope": "Việt Nam, tổng ASEAN-9 và các quốc gia/vùng lãnh thổ hiện tại",
        "axis_mode": "LINEAR_TWO_PANELS_WITH_POINT_RANK_ANNOTATIONS",
        "limitation_vi": "ASEAN-9 là tổng chín nước còn lại; hạng toàn cầu chỉ được chú thích tại năm 2021.",
    },
    {
        "chart_id": "C10",
        "file_name": "04_10_global_distribution_2021.png",
        "question_ids": ("Q1",),
        "title_vi": "Phân phối sản lượng điện tái tạo toàn cầu năm 2021",
        "message_vi": "Phân phối toàn cầu có nhiều giá trị 0 và lệch phải mạnh.",
        "data_sheets": ("global_distribution",),
        "source_locator": "03_fact_metrics.csv | 03_global_cross_section.xlsx:country_values,generation_stats",
        "period": "2021",
        "scope": "215 quốc gia/vùng lãnh thổ hiện tại",
        "axis_mode": "VALUE_CLASS_COUNTS_AND_POSITIVE_LOG_DISTRIBUTION",
        "limitation_vi": "Giá trị 0 được đếm riêng và tuyệt đối không được biến đổi để đưa lên trục logarit.",
    },
    {
        "chart_id": "C11",
        "file_name": "04_11_asean_entry_lag.png",
        "question_ids": ("Q4",),
        "title_vi": "Độ trễ đạt ngưỡng 0,05 TWh tại ASEAN",
        "message_vi": "Thời điểm gia nhập từng công nghệ rất không đồng đều.",
        "data_sheets": ("entry_lag",),
        "source_locator": "03_fact_metrics.csv | 03_entry_lag.xlsx:entry_status",
        "period": "Cửa sổ 2000–2021",
        "scope": "ASEAN-10",
        "axis_mode": "LINEAR_YEAR_WITH_LEFT_RIGHT_CENSOR_MARKERS",
        "limitation_vi": "Kiểm duyệt trái/phải là trạng thái, không phải năm 2000 hoặc 2021 giả định.",
    },
    {
        "chart_id": "C12",
        "file_name": "04_12_asean_concentration_growth.png",
        "question_ids": ("Q6",),
        "title_vi": "Mức tập trung và đóng góp tăng trưởng điện tái tạo ASEAN",
        "message_vi": "Gió + mặt trời và phần tăng của nó tập trung mạnh ở Việt Nam.",
        "data_sheets": ("concentration", "growth_contribution"),
        "source_locator": "03_fact_metrics.csv | 03_global_context.xlsx:annual_concentration,growth_contribution",
        "period": "2000–2021; đóng góp tăng dương 2010–2021",
        "scope": "ASEAN-10",
        "axis_mode": "LINEAR_RATIO_AND_POSITIVE_GROWTH_SHARE_PANELS",
        "limitation_vi": "Đóng góp dùng tổng phần tăng dương, không phải HHI/Gini hay thay đổi ròng toàn khu vực.",
    },
    {
        "chart_id": "C13",
        "file_name": "04_13_capacity_factor_proxy.png",
        "question_ids": ("Q4",),
        "title_vi": "Hệ số sử dụng công suất xấp xỉ cho gió và mặt trời",
        "message_vi": "Chỉ số phụ có độ phủ hạn chế: 2 nước cho gió, 4 nước cho mặt trời.",
        "data_sheets": ("capacity_factor",),
        "source_locator": "fact_energy.csv",
        "period": "2000–2021 theo quan sát khả dụng",
        "scope": "ASEAN-10 có cả sản lượng và công suất dương",
        "axis_mode": "LINEAR_TWO_TECHNOLOGY_PANELS",
        "limitation_vi": "Công suất là số cuối năm nên đây chỉ là chỉ báo xấp xỉ, không phải thước đo hiệu quả kỹ thuật.",
    },
)
CHARTS: Final = CHART_SPECS
CHART_FILES: Final = tuple(spec["file_name"] for spec in CHART_SPECS)
CHART_BY_ID: Final = {spec["chart_id"]: spec for spec in CHART_SPECS}
QUESTION_IDS_BY_CHART: Final = {
    spec["chart_id"]: spec["question_ids"] for spec in CHART_SPECS
}
GATE_BY_CHART_ID: Final = {
    "C01": "B4",
    "C02": "B4",
    "C03": "B5",
    "C04": "B5",
    "C05": "B5",
    "C06": "B5",
    "C07": "B6",
    "C08": "B6",
    "C09": "B6",
    "C10": "B7",
    "C11": "B7",
    "C12": "B7",
    "C13": "B8",
}
TRACE_KEYS_BY_CHART: Final = {
    **{f"C{number:02d}": ("fact_key",) for number in range(1, 13)},
    "C13": ("generation_source_key", "capacity_source_key"),
}


# ---------------------------------------------------------------------------
# Phase 4 workbook contract
# ---------------------------------------------------------------------------

CHART_DATA_WORKBOOK: Final = "04_chart_data.xlsx"
VALIDATION_FILE: Final = "04_validation_results.csv"
CHART_DATA_SHEETS: Final = (
    "manifest",
    "global_context",
    "asean_technology",
    "country_mix_2021",
    "rank_shift_2021",
    "small_multiples",
    "vietnam_technology",
    "vietnam_q5",
    "vietnam_position",
    "global_distribution",
    "entry_lag",
    "concentration",
    "growth_contribution",
    "capacity_factor",
    "metadata",
    "method_notes",
)
WORKBOOK_SHEETS: Final = CHART_DATA_SHEETS

MANIFEST_COLUMNS: Final = (
    "chart_id",
    "file_name",
    "question_ids",
    "title_vi",
    "message_vi",
    "data_sheets",
    "source_locator",
    "trace_key",
    "scope",
    "period",
    "axis_mode",
    "limitation_vi",
    "method_version",
    "phase2_input_fingerprint",
)
PROVENANCE_COLUMNS: Final = ("method_version", "phase2_input_fingerprint")
COMMON_CHART_DATA_COLUMNS: Final = (
    "chart_id",
    "series_key",
    *PROVENANCE_COLUMNS,
)

# Data sheets may retain the complete selected Phase 3 fact columns or widen
# related metrics. Therefore only stable identity/provenance columns are locked.
SHEET_REQUIRED_COLUMNS: Final = {
    "manifest": frozenset(MANIFEST_COLUMNS),
    "global_context": frozenset(COMMON_CHART_DATA_COLUMNS + ("year", "fact_key")),
    "asean_technology": frozenset(COMMON_CHART_DATA_COLUMNS + ("year", "fact_key")),
    "country_mix_2021": frozenset(COMMON_CHART_DATA_COLUMNS + ("entity", "year")),
    "rank_shift_2021": frozenset(("chart_id", "entity", *PROVENANCE_COLUMNS)),
    "small_multiples": frozenset(COMMON_CHART_DATA_COLUMNS + ("entity", "year", "fact_key")),
    "vietnam_technology": frozenset(COMMON_CHART_DATA_COLUMNS + ("year", "fact_key")),
    "vietnam_q5": frozenset(COMMON_CHART_DATA_COLUMNS + ("year",)),
    "vietnam_position": frozenset(COMMON_CHART_DATA_COLUMNS + ("year",)),
    "global_distribution": frozenset(COMMON_CHART_DATA_COLUMNS + ("entity", "year", "fact_key")),
    "entry_lag": frozenset(COMMON_CHART_DATA_COLUMNS + ("entity",)),
    "concentration": frozenset(COMMON_CHART_DATA_COLUMNS + ("year", "fact_key")),
    "growth_contribution": frozenset(COMMON_CHART_DATA_COLUMNS + ("entity",)),
    "capacity_factor": frozenset({
        "chart_id", "entity", "year", "technology", "generation_twh",
        "capacity_gw", "capacity_factor_ratio", "generation_source_key",
        "capacity_source_key", *PROVENANCE_COLUMNS,
    }),
    "metadata": frozenset(("metadata_key", "metadata_value", *PROVENANCE_COLUMNS)),
    "method_notes": frozenset(("note_key", "note", *PROVENANCE_COLUMNS)),
}
SHEET_KEY_COLUMNS: Final = {
    "manifest": ("chart_id",),
    "global_context": ("subject_key", "year", "series_key", "metric_name"),
    "asean_technology": ("year", "series_key"),
    "country_mix_2021": ("entity", "year", "series_key", "metric_name"),
    "rank_shift_2021": ("entity",),
    "small_multiples": ("entity", "year", "series_key"),
    "vietnam_technology": ("year", "series_key"),
    "vietnam_q5": ("year", "series_key"),
    "vietnam_position": (
        "record_type", "display_subject", "year", "series_key", "metric_name",
    ),
    "global_distribution": (
        "record_type", "subject_key", "year", "series_key", "metric_name",
    ),
    "entry_lag": ("entity", "series_key"),
    "concentration": ("year", "series_key", "metric_name"),
    "growth_contribution": (
        "subject_type", "subject_key", "series_key", "metric_name",
    ),
    "capacity_factor": ("entity", "year", "technology"),
    "metadata": ("metadata_key",),
    "method_notes": ("note_key",),
}

REQUIRED_METADATA_KEYS: Final = frozenset({
    "method_version",
    "phase2_input_fingerprint",
    "year_start",
    "year_end",
    "chart_count",
    "image_width_px",
    "image_height_px",
    "dpi",
    "primary_fact_source",
    "definition_source",
    "capacity_factor_source",
    "phase2_fact_energy_sha256",
    "fact_key_columns",
    "dataviz_skill_status",
    "archive_csv_sha256",
})
REQUIRED_METHOD_NOTE_KEYS: Final = frozenset({
    "NO_PHASE3_RECALCULATION",
    "LOG_ZERO",
    "CAPACITY_FACTOR",
    "ENTRY_CENSORING",
    "RANK_SCOPE",
})


# ---------------------------------------------------------------------------
# Chart-specific acceptance values
# ---------------------------------------------------------------------------

EXPECTED_CHART_COUNTS: Final = {
    "C01": {"years": 22, "numeric_values": 66},
    "C02": {"years": 22, "technologies": 4, "numeric_values": 88},
    "C03": {"countries": 10, "technologies": 4, "representations": 2, "numeric_values": 80},
    "C04": {"countries": 10},
    "C05": {"observations": 220},
    "C06": {"observations": 220},
    "C07": {"years": 22, "technologies": 4, "numeric_values": 88},
    "C08": {"paired_rows": 44, "numeric_values": 88},
    "C09": {"years": 22, "series": 2, "comparison_groups": 2, "time_series_values": 88, "rank_annotations": 2},
    "C10": {"countries": 215, "technologies": 4, "state_rows": 860},
    "C11": {"countries": 10, "technologies": 4, "rows": 40},
    "C12": {"concentration_points": 44, "country_growth_rows": 10},
    "C13": {"wind_rows": 33, "solar_rows": 71, "rows": 104},
}
EXPECTED_C01_ENDPOINTS: Final = {
    "ASEAN_10": {2000: 72.800904, 2021: 289.655745},
    "WORLD_REPORTED": {2000: 2_854.49, 2021: 7_885.04005},
    "ASEAN_SHARE_WORLD": {
        2000: 0.02550399686108552,
        2021: 0.03673484765622719,
    },
}
EXPECTED_C02_2021_TWH: Final = {
    "HYDRO": 185.58,
    "OTHER_RENEWABLES": 61.345745,
    "SOLAR": 34.43,
    "WIND": 8.30,
}
EXPECTED_C04_RANK_SHIFTS: Final = {
    "Singapore": 4,
    "Indonesia": -4,
    "Laos": -5,
}
EXPECTED_C08_OPPOSITE_DIRECTION_YEARS: Final = {
    "RENEWABLE_TOTAL": (2003, 2014),
    "MODERN_WIND_SOLAR": (2016,),
}
EXPECTED_C09_2021_TWH: Final = {
    "RENEWABLE_TOTAL": {"Vietnam": 104.218036, "ASEAN_9": 185.437709},
    "MODERN_WIND_SOLAR": {"Vietnam": 28.16, "ASEAN_9": 14.57},
}
EXPECTED_C09_2021_GLOBAL_RANKS: Final = {
    "RENEWABLE_TOTAL": {"rank": 16, "ranked_n": 205},
    "MODERN_WIND_SOLAR": {"rank": 17, "ranked_n": 209},
}
EXPECTED_C10_OBSERVED_N: Final = {
    "HYDRO": 208,
    "OTHER_RENEWABLES": 206,
    "SOLAR": 210,
    "WIND": 209,
}
EXPECTED_C10_ZERO_N: Final = {
    "HYDRO": 59,
    "OTHER_RENEWABLES": 92,
    "SOLAR": 50,
    "WIND": 105,
}
EXPECTED_C12_2021_TOP3_SHARE: Final = {
    "MODERN_WIND_SOLAR": 0.922537,
    "RENEWABLE_TOTAL": 0.671023,
}
EXPECTED_C12_VIETNAM_POSITIVE_GROWTH_SHARE: Final = 0.659859

CAPACITY_FACTOR_COUNTRIES: Final = {
    "WIND": ("Philippines", "Thailand"),
    "SOLAR": ("Malaysia", "Philippines", "Thailand", "Vietnam"),
}
CAPACITY_FACTOR_MISSING_COUNTRIES: Final = {
    series: tuple(country for country in ASEAN_10 if country not in available)
    for series, available in CAPACITY_FACTOR_COUNTRIES.items()
}
EXPECTED_CAPACITY_FACTOR_ROWS: Final = {"WIND": 33, "SOLAR": 71}

ENTRY_STATUS_VALUES: Final = frozenset({
    "ACTIVE_AT_WINDOW_START",
    "OBSERVED_TRANSITION",
    "NOT_OBSERVED_BY_2021",
    "UNKNOWN_INCOMPLETE_SERIES",
})
MATERIAL_ENTRY_STATUS_VALUES: Final = frozenset({
    "MATERIAL_AT_WINDOW_START",
    "OBSERVED_MATERIAL_TRANSITION",
    "NOT_MATERIAL_BY_2021",
    "UNKNOWN_INCOMPLETE_SERIES",
})


# ---------------------------------------------------------------------------
# Validation CSV contract
# ---------------------------------------------------------------------------

VALIDATION_COLUMNS: Final = (
    "validation_id",
    "validation_group",
    "gate_id",
    "chart_id",
    "question_id",
    "severity",
    "status",
    "expected_value",
    "actual_value",
    "failure_reason",
    "details",
    "method_version",
    "phase2_input_fingerprint",
)
VALIDATION_STATUS_VALUES: Final = frozenset({"PASS", "FAIL"})
VALIDATION_SEVERITY: Final = "BLOCKING"

_B1_VALIDATION_IDS = (
    "P4_B1_PHASE2_FACT_ENERGY",
    "P4_B1_PHASE2_VALIDATION_ROWS",
    "P4_B1_PHASE2_STATUS_COUNTS",
    "P4_B1_PHASE2_BLOCKING",
    "P4_B1_PHASE3_FACT_ROWS",
    "P4_B1_PHASE3_QUESTION_ROWS",
    "P4_B1_PHASE3_CROSSCHECK",
    "P4_B1_PHASE3_VALIDATIONS",
    "P4_B1_PHASE3_FINGERPRINT",
)
_B2_VALIDATION_IDS = (
    "P4_B2_CHART_ALLOWLIST",
    "P4_B2_CHART_METADATA",
    "P4_B2_PALETTES",
    "P4_B2_STATIC_RENDER_RULES",
)
_B3_VALIDATION_IDS = (
    "P4_B3_SHEET_ALLOWLIST",
    "P4_B3_TRACEABILITY",
    "P4_B3_YEAR_DOMAIN",
    "P4_B3_FINITE",
    "P4_B3_UNIQUE_KEYS",
    "P4_B3_CAPACITY_SOURCE_KEYS",
)
_CHART_VALIDATION_IDS = tuple(f"P4_C{number:02d}_CONTRACT" for number in range(1, 14))
_B9_VALIDATION_IDS = (
    "P4_B9_PNG_ALLOWLIST",
    "P4_B9_PNG_DIMENSIONS",
    "P4_B9_PNG_NONBLANK",
    "P4_B9_MANIFEST",
    "P4_B9_WORKBOOK_SCHEMA",
    "P4_B9_SOURCE_IMMUTABILITY",
)
VALIDATION_IDS: Final = (
    *_B1_VALIDATION_IDS,
    *_B2_VALIDATION_IDS,
    *_B3_VALIDATION_IDS,
    *_CHART_VALIDATION_IDS,
    *_B9_VALIDATION_IDS,
)
EXPECTED_VALIDATION_IDS: Final = frozenset(VALIDATION_IDS)
EXPECTED_VALIDATION_ROWS: Final = len(VALIDATION_IDS)
VALIDATION_GATE_BY_ID: Final = {
    **{identifier: "B1" for identifier in _B1_VALIDATION_IDS},
    **{identifier: "B2" for identifier in _B2_VALIDATION_IDS},
    **{identifier: "B3" for identifier in _B3_VALIDATION_IDS},
    **{
        f"P4_{chart_id}_CONTRACT": gate_id
        for chart_id, gate_id in GATE_BY_CHART_ID.items()
    },
    **{identifier: "B9" for identifier in _B9_VALIDATION_IDS},
}


def manifest_rows() -> tuple[dict[str, object], ...]:
    """Return deterministic manifest records enriched with release provenance."""
    rows: list[dict[str, object]] = []
    for spec in CHART_SPECS:
        chart_id = str(spec["chart_id"])
        rows.append({
            **spec,
            "question_ids": ",".join(spec["question_ids"]),
            "data_sheets": ",".join(spec["data_sheets"]),
            "trace_key": ",".join(TRACE_KEYS_BY_CHART[chart_id]),
            "method_version": METHOD_VERSION,
            "phase2_input_fingerprint": EXPECTED_PHASE2_INPUT_FINGERPRINT,
        })
    return tuple(rows)


def _validate_contract() -> None:
    """Fail at import when a supposedly locked contract is internally invalid."""
    if len(CHART_SPECS) != 13:
        raise RuntimeError("Phase 4 must define exactly 13 chart specifications")
    if any(set(spec) != CHART_SPEC_KEYS for spec in CHART_SPECS):
        raise RuntimeError("A Phase 4 chart specification has missing or unexpected keys")
    if len(CHART_BY_ID) != 13 or set(CHART_BY_ID) != {
        f"C{number:02d}" for number in range(1, 14)
    }:
        raise RuntimeError("Phase 4 chart IDs must be the unique sequence C01-C13")
    if len(set(CHART_FILES)) != 13 or any(not name.endswith(".png") for name in CHART_FILES):
        raise RuntimeError("Phase 4 chart file names must be 13 unique PNG names")
    if set(COUNTRY_COLORS) != set(ASEAN_10):
        raise RuntimeError("Country palette must cover exactly ASEAN-10")
    if set(TECHNOLOGY_COLORS) != set(ANALYSIS_SERIES):
        raise RuntimeError("Series palette must cover exactly the six analysis series")
    if COUNTRY_COLORS["Vietnam"] != "#D55E00":
        raise RuntimeError("Vietnam must use the locked highlight color #D55E00")
    referenced_sheets = {
        sheet for spec in CHART_SPECS for sheet in spec["data_sheets"]
    }
    data_sheets = set(CHART_DATA_SHEETS) - {"manifest", "metadata", "method_notes"}
    if referenced_sheets != data_sheets:
        raise RuntimeError("Chart specs must reference every chart-data sheet exactly by allow-list")
    if set(SHEET_REQUIRED_COLUMNS) != set(CHART_DATA_SHEETS):
        raise RuntimeError("Every Phase 4 workbook sheet needs a required-column contract")
    if set(SHEET_KEY_COLUMNS) != set(CHART_DATA_SHEETS):
        raise RuntimeError("Every Phase 4 workbook sheet needs a semantic-key contract")
    if len(VALIDATION_IDS) != 38 or len(EXPECTED_VALIDATION_IDS) != 38:
        raise RuntimeError("Phase 4 validation contract must contain exactly 38 unique IDs")
    if set(VALIDATION_GATE_BY_ID) != EXPECTED_VALIDATION_IDS:
        raise RuntimeError("Every Phase 4 validation ID must map to one gate")
    if CHART_SIZE_PX != tuple(round(value * CHART_DPI) for value in FIGURE_SIZE_INCHES):
        raise RuntimeError("Figure dimensions and DPI do not resolve to 2400x1350 pixels")


_validate_contract()
