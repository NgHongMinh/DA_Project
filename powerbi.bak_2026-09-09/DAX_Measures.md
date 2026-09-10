# Danh mục phép đo DAX — Phase 5

Tệp này được **sinh tự động** từ `python/05_measures.py`. Không sửa tay: sửa ở nguồn rồi
chạy lại `python python\05_build_pbip.py`.

Phiên bản phương pháp: `phase5_v1` · Power BI Desktop: `2.157.1354.0` ·
Dấu vân tay Phase 2: `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10`

## Cách đọc hai cột đơn vị

`unit_stored` là thang **lưu trữ** — thứ B10 đối chiếu với `03_fact_metrics.csv`.
`format_string` là thang **hiển thị**. Việc ×100 chỉ được nằm ở `format_string`,
không bao giờ nằm trong biểu thức. Trong toàn bộ mô hình chỉ `Share Electricity Pct`
mang `unit_stored = pct` (thang 0–100); mọi tỷ lệ còn lại là `ratio` (thang 0–1).
So một measure ratio `0,671023268910` với đích hiển thị `67,102326891` sẽ lệch `66,43`,
không phải sai số làm tròn.

## Bảng danh mục

| measure_id | name | format_string | unit | unit_stored | numerator | denominator | filter_behavior | blank_rule | source_metric_keys | question_ids | page_ids |
|---|---|---|---|---|---|---|---|---|---|---|---|
| M001 | Selected Year | #,0 | year | year | — | — | reads the disconnected SelReportYear table, never filters DimYear | never blank -- it has a default | — | — | P1, P2, P3 |
| M002 | Selected Mode | — | STATUS_CODE | STATUS_CODE | — | — | reads the disconnected SelMode table, never filters raw metric_key | defaults to RENEWABLE_TOTAL | — | — | P1, P2, P3 |
| M003 | Selected Base Year | #,0 | year | year | — | — | — | defaults to 2010 | — | — | P3 |
| M004 | Mode Tech Count | #,0 | count | count | — | — | — | — | — | — | P1, P2, P3 |
| M010 | Gen TWh Raw | #,0.0### | TWh | TWh | SUM(FactEnergy[value]) over metric = generation | — | follows the ambient filter context | blank when no rows match | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1, Q2 | — |
| M011 | Component Count | #,0 | count | count | — | — | — | returns 0 rather than blank so it stays comparable | — | — | — |
| M012 | Required Component Count | #,0 | count | count | — | — | counts entities and metrics in context, never hard-codes 4 | — | — | — | — |
| M013 | Gen TWh | #,0.0### | TWh | TWh | sum of 4 or 2 technologies | -- | complete-case within the scope being filtered | BLANK when component_count < required_component_count | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1, Q2 | P1, P2, P3 |
| M014 | Gen TWh @Year | #,0.0### | TWh | TWh | — | — | overrides DimYear to the selected year | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1, Q2 | P1, P2, P3 |
| M015 | Gen TWh ToDate | #,0.0### | TWh | TWh | — | — | keeps the year axis, only suppresses years past the selection | BLANK for every year later than the selected one | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1, Q4 | P1, P2, P3 |
| M020 | ASEAN Gen TWh | #,0.0### | TWh | TWh | sum over 10 countries x the mode's technologies | — | ignores the country filter -- label the scope on the visual title | BLANK when any of the 40 (or 20) cells is missing | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1, Q2 | P1, P3 |
| M021 | ASEAN Gen TWh ToDate | #,0.0### | TWh | TWh | — | — | ignores the country filter | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1 | P1 |
| M022 | World Gen TWh | #,0.0### | TWh | TWh | — | — | ignores the country filter, pins entity = World | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1 | P1 |
| M023 | World Gen TWh ToDate | #,0.0### | TWh | TWh | — | — | — | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1 | P1 |
| M030 | ASEAN Share World | 0.0000% | ratio | ratio | ASEAN Gen TWh | World Gen TWh (REPORTED_WORLD) | both numerator and denominator ignore the country filter | DIVIDE returns BLANK when the denominator is zero or blank | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1 | P1 |
| M031 | Country Share ASEAN | 0.0000% | ratio | ratio | Gen TWh @Year for the country | ASEAN_SUM_10 | numerator follows the country filter, denominator keeps all ten | BLANK when either side is blank | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q2 | P1, P2, P3 |
| M032 | Technology Share | 0.0000% | ratio | ratio | generation for the technology | TOTAL_RENEWABLE_GENERATION | — | BLANK when the denominator is zero | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q2 | P1 |
| M033 | Share Electricity Pct | #,0.0####"%" | pct | pct | source column (1/1) or wind + solar (2/2) | -- | follows the ambient year filter | BLANK when modern mode is missing either component | renewables_share_electricity_pct, wind_share_electricity_pct, solar_share_electricity_pct | Q5 | P2 |
| M034 | Share Electricity Pct @Year | #,0.0####"%" | pct | pct | — | — | pins DimYear to the selected year | — | — | Q5 | P2 |
| M035 | Share Electricity Pct ToDate | #,0.0####"%" | pct | pct | — | — | — | — | — | Q5 | P2 |
| M036 | Direction Relation | — | STATUS_CODE | STATUS_CODE | — | — | reads the year from the chart axis, not from the slicer | BLANK in 2000: the prior year lies outside the window, so there is nothing inside the window to compare against | — | Q5 | P2 |
| M037 | Country Share ASEAN ToDate | 0.0000% | ratio | ratio | Gen TWh ToDate for the country | ASEAN_SUM_10 at the same year | numerator follows the country filter, denominator keeps all ten | BLANK outside 2000..selected year, and when either side is blank | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q2 | P2, P3 |
| M040 | ASEAN Rank | #,0 | rank | rank | — | population_n = 10 | fixed is_asean = 1 cohort, unaffected by the country filter | BLANK / ZERO_SCOPE_TOTAL when the scope total is zero | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q3 | P1, P2 |
| M041 | Global Rank | #,0 | rank | rank | — | ranked_n (dynamic), population_n = 215 | fixed cohort, ignores the country filter | BLANK when the country is incomplete that year | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q4 | P2 |
| M042 | Global Ranked N | #,0 | count | count | — | — | fixed 215-country cohort, counts the eligible ones | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q4 | P2 |
| M043 | Global Population N | #,0 | count | count | — | — | — | — | — | — | P2 |
| M044 | Modern Rank Gain | +#,0;-#,0;0 | rank_change | rank_change | — | — | overrides SelMode per side, independent of the current switch | BLANK when either rank is undefined | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q3 | P1 |
| M045 | ASEAN Rank ToDate | #,0 | rank | rank | — | population_n = 10, the fixed ASEAN-10 cohort | fixed cohort, reads the year from the axis | BLANK outside the window and when the scope total is zero | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q3 | P2, P3 |
| M046 | Global Rank ToDate | #,0 | rank | rank | — | ranked_n at that year (dynamic), population_n = 215 | fixed cohort, ignores the country filter, reads the axis year | BLANK outside the window and when the country is incomplete | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q4 | P2, P3 |
| M047 | Global Ranked N ToDate | #,0 | count | count | — | — | fixed 215-country cohort, counts the eligible ones per axis year | BLANK outside the window, where no country is eligible | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q4 | P2, P3 |
| M050 | YoY | 0.0000% | ratio | ratio | value at year t | value at year t-1, inside the window and greater than zero | — | BLANK when the prior year is zero, blank, or outside the window (which is the case in 2000) | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1, Q4 | P2, P3 |
| M051 | CAGR From Base | 0.0000% | ratio | ratio | end-of-period value | start-of-period value (floor 0.05 TWh) | — | BLANK when the start is under the floor or the span is not positive | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1 | P3 |
| M052 | Indexed 100 | #,0.0 | count | count | value at year t | value at the base year (must be > 0) | — | BLANK when the base is zero or falls after the report year | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q1 | P3 |
| M053 | Positive Addition TWh | #,0.0### | TWh | TWh | — | — | — | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q6 | P3 |
| M054 | Gross Positive Addition TWh | #,0.0### | TWh | TWh | — | — | always all ten countries, ignores the country filter | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q6 | P3 |
| M055 | Positive Growth Share | 0.0000% | ratio | ratio | Positive Addition TWh for the country | GROSS_POSITIVE_ADDITION | — | BLANK when there is no positive addition at all | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q6 | P3 |
| M060 | Above 0.05 TWh N | #,0 | count | count | — | — | fixed ten-country cohort | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q6 | P1 |
| M061 | Top1 Share | 0.0000% | ratio | ratio | largest value | ASEAN_SUM_10 | — | BLANK / ZERO_DENOMINATOR when the ASEAN total is zero | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q6 | P3 |
| M062 | Top3 Share | 0.0000% | ratio | ratio | sum of the three largest values | ASEAN_SUM_10 | — | BLANK / ZERO_DENOMINATOR when the ASEAN total is zero | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q6 | P3 |
| M063 | HHI | 0.000000 | ratio | ratio | sum of squared shares | ASEAN_SUM_10 | — | BLANK / ZERO_DENOMINATOR when the ASEAN total is zero | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q6 | P3 |
| M064 | Gini | 0.000000 | ratio | ratio | empirical Gini formula | ASEAN_SUM_10 | — | BLANK / ZERO_DENOMINATOR when the ASEAN total is zero | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q6 | P3 |
| M070 | Capacity GW | #,0.000 | GW | GW | — | — | — | — | wind_capacity_gw, solar_capacity_gw | Q4 | P3 |
| M071 | Capacity Factor | 0.0000% | ratio | ratio | generation TWh | capacity GW x 8.76 | ASEAN-10 within the 2000-2021 window only | BLANK when capacity is zero or blank | wind_capacity_gw, solar_capacity_gw, wind_generation_twh, solar_generation_twh | Q4 | P3 |
| M072 | Capacity Factor Country N | #,0 | count | count | — | — | — | — | — | Q4 | P3 |
| M090 | VN Gen TWh @Year | #,0.0### | TWh | TWh | — | — | overrides any country filter to Vietnam | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q4 | P2 |
| M091 | VN Gen TWh ToDate | #,0.0### | TWh | TWh | — | — | overrides any country filter to Vietnam | — | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q4 | P2 |
| M092 | VN Share Electricity Pct @Year | #,0.0####"%" | pct | pct | — | — | overrides any country filter to Vietnam | — | — | Q5 | P2 |
| M093 | VN Share Electricity Pct ToDate | #,0.0####"%" | pct | pct | — | — | — | — | — | Q5 | P2 |
| M094 | VN Country Share ASEAN | 0.0000% | ratio | ratio | Vietnam generation | ASEAN_SUM_10 | — | — | — | Q2 | P2 |
| M095 | VN Global Rank | #,0 | rank | rank | — | ranked_n (dynamic) | — | — | — | Q4 | P2 |
| M096 | VN YoY | 0.0000% | ratio | ratio | value at t | value at t-1 (must be > 0) | — | — | — | Q4 | P2 |
| M097 | VN Direction Relation | — | STATUS_CODE | STATUS_CODE | — | — | — | — | — | Q5 | P2 |
| M098 | VN Country Share ASEAN ToDate | 0.0000% | ratio | ratio | Vietnam Gen TWh ToDate | ASEAN_SUM_10 at the same year | — | — | — | Q2 | P2 |
| M099 | VN ASEAN Rank ToDate | #,0 | rank | rank | — | population_n = 10 | — | BLANK when the ASEAN total for that year and mode is zero | — | Q3 | P2 |
| M100 | VN Global Rank ToDate | #,0 | rank | rank | — | ranked_n at that year (dynamic) | — | — | — | Q4 | P2 |
| M101 | VN Rank Label | — | STATUS_CODE | STATUS_CODE | — | population_n = 10 for ASEAN, ranked_n for the world | locked to Vietnam, ignores the country slicer | the ASEAN half falls back to Rank Status; the world half drops out when the rank is undefined | hydro_generation_twh, other_renewables_generation_twh, wind_generation_twh, solar_generation_twh | Q3, Q4 | P2 |
| M102 | VN Direction Color | — | STATUS_CODE | STATUS_CODE | — | — | follows the row of the year table | BLANK on every year that is not OPPOSITE_DIRECTION, by design | — | Q5 | P2 |
| M080 | Rank Status | — | STATUS_CODE | STATUS_CODE | — | — | — | only appears when the rank is undefined | — | Q3 | P1, P2 |
| M081 | Concentration Status | — | STATUS_CODE | STATUS_CODE | — | — | — | — | — | Q6 | P3 |
| M082 | Completeness Label | — | STATUS_CODE | STATUS_CODE | — | — | — | — | — | — | P1, P2, P3 |
| M083 | Footer Note | — | STATUS_CODE | STATUS_CODE | — | — | — | — | — | — | P1, P2, P3 |

## Công thức và định nghĩa nghiệp vụ

### 00 Selection

#### `Selected Year` — M001

Report year currently chosen. Defaults to 2021 when the viewer has not picked one.

```dax
Selected Year =
SELECTEDVALUE( SelReportYear[year], 2021 )
```

- **Hành vi bộ lọc:** reads the disconnected SelReportYear table, never filters DimYear
- **Quy tắc trống:** never blank -- it has a default
- **Đơn vị:** lưu `year` · hiển thị `#,0`

#### `Selected Mode` — M002

Measurement mode currently chosen: RENEWABLE_TOTAL or MODERN_WIND_SOLAR.

```dax
Selected Mode =
SELECTEDVALUE( SelMode[mode_key], "RENEWABLE_TOTAL" )
```

- **Hành vi bộ lọc:** reads the disconnected SelMode table, never filters raw metric_key
- **Quy tắc trống:** defaults to RENEWABLE_TOTAL
- **Đơn vị:** lưu `STATUS_CODE` · hiển thị `mặc định`

#### `Selected Base Year` — M003

Base year for indexation and for the positive-growth contribution period.

```dax
Selected Base Year =
SELECTEDVALUE( SelBaseYear[year], 2010 )
```

- **Quy tắc trống:** defaults to 2010
- **Đơn vị:** lưu `year` · hiển thị `#,0`

#### `Mode Tech Count` — M004

How many technologies the current mode covers: 4 for the renewable total, 2 for wind plus solar.

```dax
Mode Tech Count =
IF( [Selected Mode] = "MODERN_WIND_SOLAR", 2, 4 )
```

- **Đơn vị:** lưu `count` · hiển thị `#,0`

### 01 Base

#### `Gen TWh Raw` — M010

Raw generation total for the technologies in the current mode, BEFORE the completeness rule is applied. Not for direct use on the report.

```dax
Gen TWh Raw =
CALCULATE(
            SUM( FactEnergy[value] ),
            KEEPFILTERS( FILTER( ALL( DimMetric ), DimMetric[metric] = "generation" && ( [Selected Mode] = "RENEWABLE_TOTAL" || DimMetric[technology] IN { "wind", "solar" } ) ) )
        )
```

- **Tử số:** SUM(FactEnergy[value]) over metric = generation
- **Hành vi bộ lọc:** follows the ambient filter context
- **Quy tắc trống:** blank when no rows match
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Component Count` — M011

Observations actually present in the current scope. This is the component_count that B10 reconciles against 03_fact_metrics.csv.

```dax
Component Count =
CALCULATE(
            COUNTROWS( FactEnergy ),
            KEEPFILTERS( FILTER( ALL( DimMetric ), DimMetric[metric] = "generation" && ( [Selected Mode] = "RENEWABLE_TOTAL" || DimMetric[technology] IN { "wind", "solar" } ) ) )
        ) + 0
```

- **Quy tắc trống:** returns 0 rather than blank so it stays comparable
- **Đơn vị:** lưu `count` · hiển thị `#,0`

#### `Required Component Count` — M012

Cells required = entities in scope x metrics REMAINING after intersecting the mode with any technology filter. It scales on both axes: 4/4 for one country, 40/40 for the ASEAN-10 aggregate, 2/2 and 20/20 in modern mode, and 10/10 when the viewer drills to a single technology. Hard-coding the mode's technology count would demand 40 cells where only 10 exist, and the visual would go blank instead of returning a number.

```dax
Required Component Count =
VAR _Entities = COUNTROWS( VALUES( DimEntity[entity] ) )
    VAR _Metrics =
        COUNTROWS(
            CALCULATETABLE(
                VALUES( DimMetric[metric_key] ),
                KEEPFILTERS( FILTER( ALL( DimMetric ), DimMetric[metric] = "generation" && ( [Selected Mode] = "RENEWABLE_TOTAL" || DimMetric[technology] IN { "wind", "solar" } ) ) )
            )
        )
    RETURN
        _Entities * _Metrics
```

- **Hành vi bộ lọc:** counts entities and metrics in context, never hard-codes 4
- **Đơn vị:** lưu `count` · hiển thị `#,0`

#### `Gen TWh` — M013

Generation for the current mode, returned ONLY when every component is present. A missing cell yields blank rather than a partial sum -- hard-coding 4/4 at the regional level would still return a number when a country filter removes cells.

```dax
Gen TWh =
IF(
            [Component Count] = [Required Component Count],
            [Gen TWh Raw]
        )
```

- **Tử số:** sum of 4 or 2 technologies
- **Mẫu số:** --
- **Hành vi bộ lọc:** complete-case within the scope being filtered
- **Quy tắc trống:** BLANK when component_count < required_component_count
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Gen TWh @Year` — M014

Generation at exactly the selected year. Used by the KPI row and every single-year slice.

```dax
Gen TWh @Year =
VAR _Year = [Selected Year]
    RETURN
        CALCULATE(
            [Gen TWh],
            ALL( DimYear ),
            DimYear[year] = _Year
        )
```

- **Hành vi bộ lọc:** overrides DimYear to the selected year
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Gen TWh ToDate` — M015

Generation for time-series visuals: shows 2000 through the selected year. The year filter means "up to the selected year", not "collapse the series to a single point".

```dax
Gen TWh ToDate =
IF(
            SELECTEDVALUE( DimYear[is_main_asean_window] ) = 1
                && MAX( DimYear[year] ) <= [Selected Year],
            [Gen TWh]
        )
```

- **Hành vi bộ lọc:** keeps the year axis, only suppresses years past the selection
- **Quy tắc trống:** BLANK for every year later than the selected one
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

### 02 Scope

#### `ASEAN Gen TWh` — M020

ASEAN-10 total at the selected year. Always uses the fixed is_asean = 1 cohort, so a country selection on Page 1 or Page 3 does NOT change the regional denominator.

```dax
ASEAN Gen TWh =
CALCULATE(
            [Gen TWh @Year],
            ALL( DimEntity ),
            DimEntity[is_asean] = 1
        )
```

- **Tử số:** sum over 10 countries x the mode's technologies
- **Hành vi bộ lọc:** ignores the country filter -- label the scope on the visual title
- **Quy tắc trống:** BLANK when any of the 40 (or 20) cells is missing
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `ASEAN Gen TWh ToDate` — M021

ASEAN-10 total as a series from 2000 to the selected year.

```dax
ASEAN Gen TWh ToDate =
CALCULATE(
            [Gen TWh ToDate],
            ALL( DimEntity ),
            DimEntity[is_asean] = 1
        )
```

- **Hành vi bộ lọc:** ignores the country filter
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `World Gen TWh` — M022

World total taken from the World ROW as published by the source, not from summing the countries present. The two differ, and summing countries would build a wrong denominator.

```dax
World Gen TWh =
CALCULATE(
            [Gen TWh @Year],
            ALL( DimEntity ),
            DimEntity[entity] = "World"
        )
```

- **Hành vi bộ lọc:** ignores the country filter, pins entity = World
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `World Gen TWh ToDate` — M023

The World row as a series from 2000 to the selected year.

```dax
World Gen TWh ToDate =
CALCULATE(
            [Gen TWh ToDate],
            ALL( DimEntity ),
            DimEntity[entity] = "World"
        )
```

- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

### 03 Shares

#### `ASEAN Share World` — M030

ASEAN-10 as a share of the World row. STORED ON THE 0-1 SCALE; the x100 lives only in format_string.

```dax
ASEAN Share World =
DIVIDE( [ASEAN Gen TWh], [World Gen TWh] )
```

- **Tử số:** ASEAN Gen TWh
- **Mẫu số:** World Gen TWh (REPORTED_WORLD)
- **Hành vi bộ lọc:** both numerator and denominator ignore the country filter
- **Quy tắc trống:** DIVIDE returns BLANK when the denominator is zero or blank
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Country Share ASEAN` — M031

One country as a share of the ASEAN-10 total. The denominator is always the fixed ASEAN_SUM_10. STORED ON THE 0-1 SCALE.

```dax
Country Share ASEAN =
IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1,
            DIVIDE( [Gen TWh @Year], [ASEAN Gen TWh] )
        )
```

- **Tử số:** Gen TWh @Year for the country
- **Mẫu số:** ASEAN_SUM_10
- **Hành vi bộ lọc:** numerator follows the country filter, denominator keeps all ten
- **Quy tắc trống:** BLANK when either side is blank
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Technology Share` — M032

One technology as a share of the renewable total for the same scope. STORED ON THE 0-1 SCALE.

```dax
Technology Share =
DIVIDE(
            [Gen TWh @Year],
            CALCULATE(
                [Gen TWh @Year],
                ALL( DimMetric )
            )
        )
```

- **Tử số:** generation for the technology
- **Mẫu số:** TOTAL_RENEWABLE_GENERATION
- **Quy tắc trống:** BLANK when the denominator is zero
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Share Electricity Pct` — M033

Share of total electricity, in the ambient year context. RENEWABLE_TOTAL takes the source column renewables_share_electricity_pct AS IS (1/1 pass-through) -- never sum the four components: summing them gives Vietnam 2021 = 42.513379% instead of 42.578747%, and the model has no other-renewables share column to add anyway. MODERN_WIND_SOLAR is wind plus solar and needs both (2/2). ALREADY STORED ON THE 0-100 SCALE -- do not multiply.

```dax
Share Electricity Pct =
VAR _Total =
        CALCULATE(
            SUM( FactEnergy[value] ),
            ALL( DimMetric ),
            DimMetric[metric_key] = "renewables_share_electricity_pct"
        )
    VAR _Parts =
        CALCULATE(
            SUM( FactEnergy[value] ),
            ALL( DimMetric ),
            DimMetric[metric_key]
                IN { "wind_share_electricity_pct", "solar_share_electricity_pct" }
        )
    VAR _PartCount =
        CALCULATE(
            COUNTROWS( FactEnergy ),
            ALL( DimMetric ),
            DimMetric[metric_key]
                IN { "wind_share_electricity_pct", "solar_share_electricity_pct" }
        )
    RETURN
        IF(
            [Selected Mode] = "RENEWABLE_TOTAL",
            _Total,
            IF( _PartCount = 2, _Parts )
        )
```

- **Tử số:** source column (1/1) or wind + solar (2/2)
- **Mẫu số:** --
- **Hành vi bộ lọc:** follows the ambient year filter
- **Quy tắc trống:** BLANK when modern mode is missing either component
- **Đơn vị:** lưu `pct` · hiển thị `#,0.0####"%"`
- **Chỉ số nguồn:** `renewables_share_electricity_pct`, `wind_share_electricity_pct`, `solar_share_electricity_pct`

#### `Share Electricity Pct @Year` — M034

Share of electricity at exactly the selected year -- used by the Vietnam KPI row.

```dax
Share Electricity Pct @Year =
VAR _Year = [Selected Year]
    RETURN
        CALCULATE(
            [Share Electricity Pct],
            ALL( DimYear ),
            DimYear[year] = _Year
        )
```

- **Hành vi bộ lọc:** pins DimYear to the selected year
- **Đơn vị:** lưu `pct` · hiển thị `#,0.0####"%"`

#### `Share Electricity Pct ToDate` — M035

Share of electricity for the time-series panel, 2000 through the selected year. This panel must NOT share an axis with the TWh panel.

```dax
Share Electricity Pct ToDate =
IF(
            SELECTEDVALUE( DimYear[is_main_asean_window] ) = 1
                && MAX( DimYear[year] ) <= [Selected Year],
            [Share Electricity Pct]
        )
```

- **Đơn vị:** lưu `pct` · hiển thị `#,0.0####"%"`

#### `Direction Relation` — M036

Compares the direction of the TWh move against the direction of the share-of-electricity move in the same year. Vietnam: the renewable total moves opposite ways in 2003 and 2014, the modern measure in 2016. This only FLAGS the divergence -- it licenses no causal reading between the two quantities.
The prior year must ALSO be inside the window. Without that condition the ALL( DimYear ) reaches back to 1999, where Vietnam went 13,774 -> 14,550 TWh while its share went 58,46598 -> 54,781628 percent, and the year 2000 comes back OPPOSITE_DIRECTION. The reference walks K.YEARS[1:] and so never asks about 2000; the two sides would then disagree by one year.

```dax
Direction Relation =
VAR _Year = MAX( DimYear[year] )
    VAR _CurrentTwh = [Gen TWh]
    VAR _PreviousTwh =
        CALCULATE(
            [Gen TWh],
            ALL( DimYear ),
            DimYear[year] = _Year - 1,
            DimYear[is_main_asean_window] = 1
        )
    VAR _CurrentShare = [Share Electricity Pct]
    VAR _PreviousShare =
        CALCULATE(
            [Share Electricity Pct],
            ALL( DimYear ),
            DimYear[year] = _Year - 1,
            DimYear[is_main_asean_window] = 1
        )
    VAR _DeltaTwh = _CurrentTwh - _PreviousTwh
    VAR _DeltaShare = _CurrentShare - _PreviousShare
    RETURN
        SWITCH(
            TRUE(),
            ISBLANK( _PreviousTwh ) || ISBLANK( _PreviousShare ), BLANK(),
            _DeltaTwh = 0 || _DeltaShare = 0, "ONE_OR_BOTH_UNCHANGED",
            ( _DeltaTwh > 0 ) <> ( _DeltaShare > 0 ), "OPPOSITE_DIRECTION",
            "SAME_DIRECTION"
        )
```

- **Hành vi bộ lọc:** reads the year from the chart axis, not from the slicer
- **Quy tắc trống:** BLANK in 2000: the prior year lies outside the window, so there is nothing inside the window to compare against
- **Đơn vị:** lưu `STATUS_CODE` · hiển thị `mặc định`

#### `Country Share ASEAN ToDate` — M037

M031 as a SERIES: the same share, read at the year the axis supplies instead of the year the slicer holds. M031 cannot be plotted over time -- it is built on Gen TWh @Year, whose ALL( DimYear ) replaces the axis year with the slicer's, so every point returns the same number and the line comes out flat across all fifty-seven rows of DimYear. Both sides carry the window guard from Gen TWh ToDate, so the pre-2000 years fall away on their own. STORED ON THE 0-1 SCALE.

```dax
Country Share ASEAN ToDate =
IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1,
            DIVIDE( [Gen TWh ToDate], [ASEAN Gen TWh ToDate] )
        )
```

- **Tử số:** Gen TWh ToDate for the country
- **Mẫu số:** ASEAN_SUM_10 at the same year
- **Hành vi bộ lọc:** numerator follows the country filter, denominator keeps all ten
- **Quy tắc trống:** BLANK outside 2000..selected year, and when either side is blank
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

### 04 Ranking

#### `ASEAN Rank` — M040

Rank within the fixed ASEAN-10 cohort (population_n = 10). Ties take the smallest rank and the next rank is skipped. Zeros are still ranked. If the whole scope totals zero the rank is BLANK with reason ZERO_SCOPE_TOTAL -- not every country tied at rank 1.

```dax
ASEAN Rank =
VAR _ScopeTotal = [ASEAN Gen TWh]
    VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 )
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", CALCULATE( [Gen TWh @Year], ALLEXCEPT( DimEntity, DimEntity[entity] ) ) )
    VAR _Current = [Gen TWh @Year]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && NOT ISBLANK( _ScopeTotal ) && _ScopeTotal > 0,
            RANKX( _Values, [@Value], _Current, DESC, Skip )
        )
```

- **Mẫu số:** population_n = 10
- **Hành vi bộ lọc:** fixed is_asean = 1 cohort, unaffected by the country filter
- **Quy tắc trống:** BLANK / ZERO_SCOPE_TOTAL when the scope total is zero
- **Đơn vị:** lưu `rank` · hiển thị `#,0`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Global Rank` — M041

Rank within the current countries and territories cohort (population_n = 215), counting only countries complete in that year. Uses is_current_country_or_territory = 1: is_aggregate = 0 returns 216 rows because USSR is still in it.

```dax
Global Rank =
VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_current_country_or_territory] = 1 )
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", CALCULATE( [Gen TWh @Year], ALLEXCEPT( DimEntity, DimEntity[entity] ) ) )
    VAR _Current = [Gen TWh @Year]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_current_country_or_territory] ) = 1
                && NOT ISBLANK( _Current ),
            RANKX( _Values, [@Value], _Current, DESC, Skip )
        )
```

- **Mẫu số:** ranked_n (dynamic), population_n = 215
- **Hành vi bộ lọc:** fixed cohort, ignores the country filter
- **Quy tắc trống:** BLANK when the country is incomplete that year
- **Đơn vị:** lưu `rank` · hiển thị `#,0`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Global Ranked N` — M042

The denominator shown next to a global rank: how many countries are complete that year. IT MOVES WITH BOTH YEAR AND MODE -- 2021 is 205 for the total and 209 for modern, 2000 is 209 and 212, 2010 is 211 and 214. Never hard-code it.

```dax
Global Ranked N =
VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_current_country_or_territory] = 1 )
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", CALCULATE( [Gen TWh @Year], ALLEXCEPT( DimEntity, DimEntity[entity] ) ) )
    RETURN
        COUNTROWS( FILTER( _Values, NOT ISBLANK( [@Value] ) ) )
```

- **Hành vi bộ lọc:** fixed 215-country cohort, counts the eligible ones
- **Đơn vị:** lưu `count` · hiển thị `#,0`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Global Population N` — M043

Size of the global cohort -- always 215, independent of year and mode. Kept separate from ranked_n so the two denominators are never confused.

```dax
Global Population N =
COUNTROWS( CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_current_country_or_territory] = 1 ) )
```

- **Đơn vị:** lưu `count` · hiển thị `#,0`

#### `Modern Rank Gain` — M044

Rank change when the measure switches: modern_rank_gain = total_rank - modern_rank. A POSITIVE number means a BETTER rank on wind plus solar alone. In 2021: Singapore +4, Indonesia -4, Laos -5.

```dax
Modern Rank Gain =
VAR _Total =
        CALCULATE( [ASEAN Rank], SelMode[mode_key] = "RENEWABLE_TOTAL" )
    VAR _Modern =
        CALCULATE( [ASEAN Rank], SelMode[mode_key] = "MODERN_WIND_SOLAR" )
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && NOT ISBLANK( _Total ) && NOT ISBLANK( _Modern ),
            _Total - _Modern
        )
```

- **Hành vi bộ lọc:** overrides SelMode per side, independent of the current switch
- **Quy tắc trống:** BLANK when either rank is undefined
- **Đơn vị:** lưu `rank_change` · hiển thị `+#,0;-#,0;0`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `ASEAN Rank ToDate` — M045

M040 read at the year the axis supplies, for a per-year table or a rank line. Same fixed ASEAN-10 cohort (population_n = 10), same tie handling: smallest rank shared, next rank skipped, zeros still ranked. If the whole scope totals zero the rank is BLANK -- read Rank Status beside it for the reason.

```dax
ASEAN Rank ToDate =
VAR _ScopeTotal = [ASEAN Gen TWh ToDate]
    VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 )
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", CALCULATE( [Gen TWh ToDate], ALLEXCEPT( DimEntity, DimEntity[entity] ) ) )
    VAR _Current = [Gen TWh ToDate]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_asean] ) = 1
                && NOT ISBLANK( _ScopeTotal ) && _ScopeTotal > 0,
            RANKX( _Values, [@Value], _Current, DESC, Skip )
        )
```

- **Mẫu số:** population_n = 10, the fixed ASEAN-10 cohort
- **Hành vi bộ lọc:** fixed cohort, reads the year from the axis
- **Quy tắc trống:** BLANK outside the window and when the scope total is zero
- **Đơn vị:** lưu `rank` · hiển thị `#,0`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Global Rank ToDate` — M046

M041 read at the year the axis supplies. Same 215-country cohort, counting only the countries complete in that year. A rank line drawn from this needs its axis INVERTED in Desktop so rank 1 sits at the top; the invertAxis property lives in the visual `objects` block, which this project does not generate.

```dax
Global Rank ToDate =
VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_current_country_or_territory] = 1 )
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", CALCULATE( [Gen TWh ToDate], ALLEXCEPT( DimEntity, DimEntity[entity] ) ) )
    VAR _Current = [Gen TWh ToDate]
    RETURN
        IF(
            SELECTEDVALUE( DimEntity[is_current_country_or_territory] ) = 1
                && NOT ISBLANK( _Current ),
            RANKX( _Values, [@Value], _Current, DESC, Skip )
        )
```

- **Mẫu số:** ranked_n at that year (dynamic), population_n = 215
- **Hành vi bộ lọc:** fixed cohort, ignores the country filter, reads the axis year
- **Quy tắc trống:** BLANK outside the window and when the country is incomplete
- **Đơn vị:** lưu `rank` · hiển thị `#,0`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Global Ranked N ToDate` — M047

M042 read at the year the axis supplies -- the denominator that belongs beside Global Rank ToDate in a per-year table. Entity-independent by construction, so it needs no Vietnam-locked twin.

```dax
Global Ranked N ToDate =
VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_current_country_or_territory] = 1 )
    VAR _Values = ADDCOLUMNS( _Cohort, "@Value", CALCULATE( [Gen TWh ToDate], ALLEXCEPT( DimEntity, DimEntity[entity] ) ) )
    RETURN
        COUNTROWS( FILTER( _Values, NOT ISBLANK( [@Value] ) ) )
```

- **Hành vi bộ lọc:** fixed 215-country cohort, counts the eligible ones per axis year
- **Quy tắc trống:** BLANK outside the window, where no country is eligible
- **Đơn vị:** lưu `count` · hiển thị `#,0`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

### 05 Growth

#### `YoY` — M050

Growth against the prior year. DEFINED ONLY when the denominator is > 0 -- with a dataset this full of zeros that is the number one source of Inf/NaN. An end value of zero giving -1 is still valid. STORED ON THE 0-1 SCALE.
The prior year is required to be inside the window too. Vietnam has data back to 1965, so without that condition the year 2000 returns +5,63 percent while `03_fact_metrics.csv` holds yoy Y2000 as NOT_DEFINED.

```dax
YoY =
VAR _Year = MAX( DimYear[year] )
    VAR _Current = [Gen TWh]
    VAR _Previous =
        CALCULATE(
            [Gen TWh],
            ALL( DimYear ),
            DimYear[year] = _Year - 1,
            DimYear[is_main_asean_window] = 1
        )
    RETURN
        IF(
            NOT ISBLANK( _Previous ) && _Previous > 0,
            DIVIDE( _Current, _Previous ) - 1
        )
```

- **Tử số:** value at year t
- **Mẫu số:** value at year t-1, inside the window and greater than zero
- **Quy tắc trống:** BLANK when the prior year is zero, blank, or outside the window (which is the case in 2000)
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `CAGR From Base` — M051

CAGR from the base year to the report year. Applies a 0.05 TWh START FLOOR: without it, countries starting from near zero take over the top of the ranking with meaningless figures. STORED ON THE 0-1 SCALE.

```dax
CAGR From Base =
VAR _StartYear = [Selected Base Year]
    VAR _EndYear = [Selected Year]
    VAR _Years = _EndYear - _StartYear
    VAR _Start =
        CALCULATE( [Gen TWh], ALL( DimYear ), DimYear[year] = _StartYear )
    VAR _End =
        CALCULATE( [Gen TWh], ALL( DimYear ), DimYear[year] = _EndYear )
    RETURN
        IF(
            _Years > 0 && NOT ISBLANK( _Start ) && _Start >= 0.05
                && NOT ISBLANK( _End ),
            ( DIVIDE( _End, _Start ) ^ DIVIDE( 1, _Years ) ) - 1
        )
```

- **Tử số:** end-of-period value
- **Mẫu số:** start-of-period value (floor 0.05 TWh)
- **Quy tắc trống:** BLANK when the start is under the floor or the span is not positive
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Indexed 100` — M052

Indexed to 100 at the base year. A zero base, or a base later than the report year, returns BLANK -- it never produces an infinity.

```dax
Indexed 100 =
VAR _BaseYear = [Selected Base Year]
    VAR _Base =
        CALCULATE(
            [Gen TWh],
            ALL( DimYear ),
            DimYear[year] = _BaseYear
        )
    RETURN
        IF(
            _BaseYear <= [Selected Year]
                && NOT ISBLANK( _Base ) && _Base > 0,
            DIVIDE( [Gen TWh ToDate], _Base ) * 100
        )
```

- **Tử số:** value at year t
- **Mẫu số:** value at the base year (must be > 0)
- **Quy tắc trống:** BLANK when the base is zero or falls after the report year
- **Đơn vị:** lưu `count` · hiển thị `#,0.0`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Positive Addition TWh` — M053

A country's POSITIVE addition between the base year and the report year. Declines are clipped to zero and reported separately, never netted off the total.

```dax
Positive Addition TWh =
VAR _StartYear = [Selected Base Year]
    VAR _EndYear = [Selected Year]
    VAR _Start =
        CALCULATE( [Gen TWh], ALL( DimYear ), DimYear[year] = _StartYear )
    VAR _End =
        CALCULATE( [Gen TWh], ALL( DimYear ), DimYear[year] = _EndYear )
    RETURN
        IF(
            NOT ISBLANK( _Start ) && NOT ISBLANK( _End ),
            MAX( _End - _Start, 0 )
        )
```

- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Gross Positive Addition TWh` — M054

Sum of the positive additions across all of ASEAN-10 -- the GROSS_POSITIVE_ADDITION denominator.

```dax
Gross Positive Addition TWh =
VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 )
    RETURN
        SUMX( _Cohort, CALCULATE( [Positive Addition TWh] ) )
```

- **Hành vi bộ lọc:** always all ten countries, ignores the country filter
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Positive Growth Share` — M055

A country's share OF THE GROSS POSITIVE ADDITION -- not its share of the region's net growth. Vietnam 2010-2021: modern 65.985915493%, total 42.3780539369% (held on the ratio scale). STORED ON THE 0-1 SCALE.

```dax
Positive Growth Share =
DIVIDE( [Positive Addition TWh], [Gross Positive Addition TWh] )
```

- **Tử số:** Positive Addition TWh for the country
- **Mẫu số:** GROSS_POSITIVE_ADDITION
- **Quy tắc trống:** BLANK when there is no positive addition at all
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

### 06 Concentration

#### `Above 0.05 TWh N` — M060

How many ASEAN countries clear the 0.05 TWh threshold in the current mode. The threshold applies to the DERIVED TOTAL (PHASE3_DERIVED_FLOOR); a component's value_class is never assigned back to the total.

```dax
Above 0.05 TWh N =
VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 )
    RETURN
        COUNTROWS(
            FILTER( _Cohort, CALCULATE( [Gen TWh @Year] ) >= 0.05 )
        ) + 0
```

- **Hành vi bộ lọc:** fixed ten-country cohort
- **Đơn vị:** lưu `count` · hiển thị `#,0`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Top1 Share` — M061

Share held by the largest country in the ASEAN-10 total. In 2021 this equals Vietnam's share EXACTLY, because both use the ASEAN_SUM_10 denominator and Vietnam leads in both modes -- it is ONE quantity, not two measures. STORED ON THE 0-1 SCALE.

```dax
Top1 Share =
VAR _Total = [ASEAN Gen TWh]
    VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 )
    VAR _Values =
        ADDCOLUMNS(
            _Cohort,
            "@Entity", DimEntity[entity],
            "@Value", CALCULATE( [Gen TWh @Year] ) + 0
        )
    RETURN
        IF(
            NOT ISBLANK( _Total ) && _Total > 0,
            DIVIDE( MAXX( _Values, [@Value] ), _Total )
        )
```

- **Tử số:** largest value
- **Mẫu số:** ASEAN_SUM_10
- **Quy tắc trống:** BLANK / ZERO_DENOMINATOR when the ASEAN total is zero
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Top3 Share` — M062

Share held by EXACTLY the three largest values. Uses a sequential position rather than "rank <= 3": on a tie for third place a rank condition returns more than three countries. Tied values are equal, so the top-3 total is the same whichever is picked. STORED ON THE 0-1 SCALE.

```dax
Top3 Share =
VAR _Total = [ASEAN Gen TWh]
    VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 )
    VAR _Values =
        ADDCOLUMNS(
            _Cohort,
            "@Entity", DimEntity[entity],
            "@Value", CALCULATE( [Gen TWh @Year] ) + 0
        )
    VAR _Ranked = ADDCOLUMNS(
            _Values,
            "@AscPos",
                VAR CurV = [@Value]
                VAR CurE = [@Entity]
                RETURN
                    COUNTROWS(
                        FILTER( _Values, [@Value] < CurV || ( [@Value] = CurV && [@Entity] <= CurE ) )
                    ),
            "@DescPos",
                VAR CurV = [@Value]
                VAR CurE = [@Entity]
                RETURN
                    COUNTROWS(
                        FILTER( _Values, [@Value] > CurV || ( [@Value] = CurV && [@Entity] <= CurE ) )
                    )
        )
    RETURN
        IF(
            NOT ISBLANK( _Total ) && _Total > 0,
            DIVIDE(
                SUMX( FILTER( _Ranked, [@DescPos] <= 3 ), [@Value] ),
                _Total
            )
        )
```

- **Tử số:** sum of the three largest values
- **Mẫu số:** ASEAN_SUM_10
- **Quy tắc trống:** BLANK / ZERO_DENOMINATOR when the ASEAN total is zero
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `HHI` — M063

Herfindahl-Hirschman concentration index over all ten countries, KEEPING the countries whose value is zero. STORED ON THE 0-1 SCALE, with no percent sign.

```dax
HHI =
VAR _Total = [ASEAN Gen TWh]
    VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 )
    VAR _Values =
        ADDCOLUMNS(
            _Cohort,
            "@Entity", DimEntity[entity],
            "@Value", CALCULATE( [Gen TWh @Year] ) + 0
        )
    RETURN
        IF(
            NOT ISBLANK( _Total ) && _Total > 0,
            SUMX( _Values, DIVIDE( [@Value], _Total ) ^ 2 )
        )
```

- **Tử số:** sum of squared shares
- **Mẫu số:** ASEAN_SUM_10
- **Quy tắc trống:** BLANK / ZERO_DENOMINATOR when the ASEAN total is zero
- **Đơn vị:** lưu `ratio` · hiển thị `0.000000`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `Gini` — M064

Gini inequality coefficient by the empirical formula over all ten values sorted ascending: 2*SUM(i*x_i)/(n*SUM x) - (n+1)/n. Position i must be a distinct 1..10; tied values contribute the same product wherever they sit, so the country name only makes the walk stable. STORED ON THE 0-1 SCALE.

```dax
Gini =
VAR _Total = [ASEAN Gen TWh]
    VAR _Cohort = CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 )
    VAR _Values =
        ADDCOLUMNS(
            _Cohort,
            "@Entity", DimEntity[entity],
            "@Value", CALCULATE( [Gen TWh @Year] ) + 0
        )
    VAR _N = COUNTROWS( _Values )
    VAR _Ranked = ADDCOLUMNS(
            _Values,
            "@AscPos",
                VAR CurV = [@Value]
                VAR CurE = [@Entity]
                RETURN
                    COUNTROWS(
                        FILTER( _Values, [@Value] < CurV || ( [@Value] = CurV && [@Entity] <= CurE ) )
                    ),
            "@DescPos",
                VAR CurV = [@Value]
                VAR CurE = [@Entity]
                RETURN
                    COUNTROWS(
                        FILTER( _Values, [@Value] > CurV || ( [@Value] = CurV && [@Entity] <= CurE ) )
                    )
        )
    RETURN
        IF(
            NOT ISBLANK( _Total ) && _Total > 0,
            DIVIDE( 2 * SUMX( _Ranked, [@AscPos] * [@Value] ), _N * _Total )
                - DIVIDE( _N + 1, _N )
        )
```

- **Tử số:** empirical Gini formula
- **Mẫu số:** ASEAN_SUM_10
- **Quy tắc trống:** BLANK / ZERO_DENOMINATOR when the ASEAN total is zero
- **Đơn vị:** lưu `ratio` · hiển thị `0.000000`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

### 07 Capacity factor

#### `Capacity GW` — M070

End-of-year installed capacity, wind and solar only.

```dax
Capacity GW =
CALCULATE(
            SUM( FactEnergy[value] ),
            ALL( DimMetric ),
            DimMetric[metric] = "installed_capacity",
            DimMetric[technology] IN { "wind", "solar" }
        )
```

- **Đơn vị:** lưu `GW` · hiển thị `#,0.000`
- **Chỉ số nguồn:** `wind_capacity_gw`, `solar_capacity_gw`

#### `Capacity Factor` — M071

APPROXIMATE capacity factor = TWh / (GW x 8.76). Keeps only pairs with capacity_gw > 0 and non-blank generation: a raw join over the window gives 132 pairs, the 28 with zero capacity are dropped, and none of those carries positive generation, so the filter loses no observation. 104 pairs remain -- wind 33, solar 71. Uses DIVIDE() to return BLANK, NOT the / operator. This is an indicator built on end-of-year capacity, NOT a measure of technical efficiency.

```dax
Capacity Factor =
VAR _Capacity = [Capacity GW]
    VAR _Generation =
        CALCULATE(
            SUM( FactEnergy[value] ),
            ALL( DimMetric ),
            DimMetric[metric] = "generation",
            DimMetric[technology] IN { "wind", "solar" }
        )
    RETURN
        IF(
            NOT ISBLANK( _Capacity ) && _Capacity > 0
                && NOT ISBLANK( _Generation ),
            DIVIDE( _Generation, _Capacity * 8.76 )
        )
```

- **Tử số:** generation TWh
- **Mẫu số:** capacity GW x 8.76
- **Hành vi bộ lọc:** ASEAN-10 within the 2000-2021 window only
- **Quy tắc trống:** BLANK when capacity is zero or blank
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`
- **Chỉ số nguồn:** `wind_capacity_gw`, `solar_capacity_gw`, `wind_generation_twh`, `solar_generation_twh`

#### `Capacity Factor Country N` — M072

How many ASEAN countries actually have capacity-factor data: 2 for wind, 4 for solar. Show this next to the chart so nobody reads it as covering all ten.

```dax
Capacity Factor Country N =
COUNTROWS(
            FILTER(
                CALCULATETABLE(
                    VALUES( DimEntity[entity] ),
                    ALL( DimEntity ),
                    DimEntity[is_asean] = 1
                ),
                NOT ISBLANK( CALCULATE( [Capacity Factor] ) )
            )
        ) + 0
```

- **Đơn vị:** lưu `count` · hiển thị `#,0`

### 09 Vietnam page

#### `VN Gen TWh @Year` — M090

Vietnam generation at the selected year. Locked to Vietnam, so a country selection made on another page cannot move this page off its subject.

```dax
VN Gen TWh @Year =
CALCULATE( [Gen TWh @Year], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Hành vi bộ lọc:** overrides any country filter to Vietnam
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `VN Gen TWh ToDate` — M091

Vietnam generation as a series, 2000 through the selected year.

```dax
VN Gen TWh ToDate =
CALCULATE( [Gen TWh ToDate], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Hành vi bộ lọc:** overrides any country filter to Vietnam
- **Đơn vị:** lưu `TWh` · hiển thị `#,0.0###`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `VN Share Electricity Pct @Year` — M092

Vietnam share of total electricity at the selected year. Stored on the 0-100 scale already -- do not multiply.

```dax
VN Share Electricity Pct @Year =
CALCULATE( [Share Electricity Pct @Year], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Hành vi bộ lọc:** overrides any country filter to Vietnam
- **Đơn vị:** lưu `pct` · hiển thị `#,0.0####"%"`

#### `VN Share Electricity Pct ToDate` — M093

Vietnam share of electricity as a series. Goes on its OWN panel, never on a second axis beside the TWh series.

```dax
VN Share Electricity Pct ToDate =
CALCULATE( [Share Electricity Pct ToDate], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Đơn vị:** lưu `pct` · hiển thị `#,0.0####"%"`

#### `VN Country Share ASEAN` — M094

Vietnam as a share of the ASEAN-10 total. STORED ON THE 0-1 SCALE. In 2021 this equals Top1 Share, because Vietnam leads in both modes and both use the ASEAN_SUM_10 denominator.

```dax
VN Country Share ASEAN =
CALCULATE( [Country Share ASEAN], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Tử số:** Vietnam generation
- **Mẫu số:** ASEAN_SUM_10
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`

#### `VN Global Rank` — M095

Vietnam's rank among the 215 current countries and territories. Read it beside Global Ranked N, which moves with both year and mode: 16/205 for the renewable total in 2021 and 17/209 for the modern measure.

```dax
VN Global Rank =
CALCULATE( [Global Rank], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Mẫu số:** ranked_n (dynamic)
- **Đơn vị:** lưu `rank` · hiển thị `#,0`

#### `VN YoY` — M096

Vietnam year-on-year growth. Blank when the prior year is zero, which is common early in the window for wind and solar.

```dax
VN YoY =
CALCULATE( [YoY], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Tử số:** value at t
- **Mẫu số:** value at t-1 (must be > 0)
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`

#### `VN Direction Relation` — M097

Whether Vietnam's TWh and its share of electricity moved the same way that year. Opposite in 2003 and 2014 on the renewable total, and in 2016 on the modern measure. A flag only -- it explains nothing about cause.

```dax
VN Direction Relation =
CALCULATE( [Direction Relation], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Đơn vị:** lưu `STATUS_CODE` · hiển thị `mặc định`

#### `VN Country Share ASEAN ToDate` — M098

Vietnam's share of the ASEAN-10 total as a SERIES. This is what the position chart plots; M094 is the single-year card and produces a flat line if it is put on a time axis. STORED ON THE 0-1 SCALE.

```dax
VN Country Share ASEAN ToDate =
CALCULATE( [Country Share ASEAN ToDate], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Tử số:** Vietnam Gen TWh ToDate
- **Mẫu số:** ASEAN_SUM_10 at the same year
- **Đơn vị:** lưu `ratio` · hiển thị `0.0000%`

#### `VN ASEAN Rank ToDate` — M099

Vietnam's rank inside ASEAN-10 at the year the axis supplies. The year table carries this so the rank can be read as a trajectory rather than as one number repeated down the column.

```dax
VN ASEAN Rank ToDate =
CALCULATE( [ASEAN Rank ToDate], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Mẫu số:** population_n = 10
- **Quy tắc trống:** BLANK when the ASEAN total for that year and mode is zero
- **Đơn vị:** lưu `rank` · hiển thị `#,0`

#### `VN Global Rank ToDate` — M100

Vietnam's rank among the 215 current countries and territories at the year the axis supplies. Read it beside Global Ranked N ToDate, which moves with both year and mode.

```dax
VN Global Rank ToDate =
CALCULATE( [Global Rank ToDate], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
```

- **Mẫu số:** ranked_n at that year (dynamic)
- **Đơn vị:** lưu `rank` · hiển thị `#,0`

#### `VN Rank Label` — M101

Both of Vietnam's ranks with both denominators, on one card: 2021 on the renewable total reads `ASEAN 1/10 | World 16/205`. A bare rank is unreadable -- 16 means nothing until the reader knows whether it is out of 205 or out of 215 -- and ranked_n moves with year AND mode, so it cannot be typed into a title. When the ASEAN rank is undefined the reason takes its place: 2000 in modern mode reads `NOT_DEFINED / ZERO_SCOPE_TOTAL | World 40/212`, which shows the reason without hiding the global rank that IS defined. The ASEAN denominator is counted, not typed, for the same reason ranked_n is.

```dax
VN Rank Label =
VAR _AseanRank = CALCULATE( [ASEAN Rank], ALL( DimEntity ), DimEntity[entity] = "Vietnam" )
    VAR _AseanN = COUNTROWS( CALCULATETABLE( VALUES( DimEntity[entity] ), ALL( DimEntity ), DimEntity[is_asean] = 1 ) )
    VAR _GlobalRank = [VN Global Rank]
    VAR _GlobalN = [Global Ranked N]
    VAR _AseanText =
        IF(
            ISBLANK( _AseanRank ),
            [Rank Status],
            "ASEAN " & FORMAT( _AseanRank, "#,0" ) & "/" & FORMAT( _AseanN, "#,0" )
        )
    VAR _GlobalText =
        IF(
            ISBLANK( _GlobalRank ),
            "",
            " | World " & FORMAT( _GlobalRank, "#,0" ) & "/" & FORMAT( _GlobalN, "#,0" )
        )
    RETURN
        _AseanText & _GlobalText
```

- **Mẫu số:** population_n = 10 for ASEAN, ranked_n for the world
- **Hành vi bộ lọc:** locked to Vietnam, ignores the country slicer
- **Quy tắc trống:** the ASEAN half falls back to Rank Status; the world half drops out when the rank is undefined
- **Đơn vị:** lưu `STATUS_CODE` · hiển thị `mặc định`
- **Chỉ số nguồn:** `hydro_generation_twh`, `other_renewables_generation_twh`, `wind_generation_twh`, `solar_generation_twh`

#### `VN Direction Color` — M102

Font colour for the direction column of the year table, so the two divergent years stand out instead of hiding among twenty-two rows of SAME_DIRECTION. Returns the Phase 4 Vietnam accent on an opposing year and BLANK everywhere else, which leaves the other rows in the default colour rather than painting the whole column. Exists because a TEXT column can only be conditionally formatted through `Format by: Field value` -- the Rules option needs a numeric field -- so the colour has to come from a measure. Wire it up in Desktop: the column's dropdown in the Values well -> Conditional formatting -> Font colour -> Format by `Field value` -> this measure.

```dax
VN Direction Color =
IF(
            [VN Direction Relation] = "OPPOSITE_DIRECTION",
            "#D55E00"
        )
```

- **Hành vi bộ lọc:** follows the row of the year table
- **Quy tắc trống:** BLANK on every year that is not OPPOSITE_DIRECTION, by design
- **Đơn vị:** lưu `STATUS_CODE` · hiển thị `mặc định`

### 08 Status

#### `Rank Status` — M080

Reason label shown when a rank is undefined. Placed next to the rank so the viewer sees WHY it is empty instead of assuming a bug.

```dax
Rank Status =
VAR _ScopeTotal = [ASEAN Gen TWh]
    RETURN
        IF(
            ISBLANK( _ScopeTotal ) || _ScopeTotal = 0,
            "NOT_DEFINED / ZERO_SCOPE_TOTAL"
        )
```

- **Quy tắc trống:** only appears when the rank is undefined
- **Đơn vị:** lưu `STATUS_CODE` · hiển thị `mặc định`

#### `Concentration Status` — M081

Reason label when top-1, top-3, HHI and Gini are undefined -- the mandatory edge case is the year 2000 in modern mode, where the ASEAN total is zero.

```dax
Concentration Status =
VAR _Total = [ASEAN Gen TWh]
    RETURN
        IF(
            ISBLANK( _Total ) || _Total = 0,
            "NOT_DEFINED / ZERO_DENOMINATOR"
        )
```

- **Đơn vị:** lưu `STATUS_CODE` · hiển thị `mặc định`

#### `Completeness Label` — M082

A have/need label so the viewer can see which level the completeness rule is operating at: 4/4 for one country, 40/40 for the ASEAN-10 aggregate.

```dax
Completeness Label =
VAR _Have = [Component Count]
    VAR _Need = [Required Component Count]
    RETURN
        FORMAT( _Have, "#,0" ) & "/" & FORMAT( _Need, "#,0" )
```

- **Đơn vị:** lưu `STATUS_CODE` · hiển thị `mặc định`

#### `Footer Note` — M083

Fixed footer for all three pages: source, year window, why 2022 was dropped and the note that aggregate entities were excluded. Retype in Vietnamese inside Desktop if the report should read in Vietnamese -- that text lives in the .pbix, not in TMDL.

```dax
Footer Note =
"Source: Our World in Data (Ember + BP) via output/clean | "
        & "Analysis window 2000-2021 | "
        & "2022 excluded: severely truncated in 8 source files, 0 ASEAN countries | "
        & "Aggregate entities excluded from every country list | "
        & "No interpolation"
```

- **Đơn vị:** lưu `STATUS_CODE` · hiển thị `mặc định`

