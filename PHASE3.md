# Kế hoạch triển khai Phase 3 — Phân tích mô tả

Kế hoạch này cụ thể hóa mục **PHASE 3 — Phân tích mô tả** trong `PLAN.md`, sáu câu hỏi Q1–Q6 trong `docs/BaoCao.md` và các giới hạn đã được xác nhận ở Phase 1–2.

Đây chỉ là kế hoạch thực hiện. Trong giai đoạn lập kế hoạch chưa viết mã Python, SQL, chưa tạo kết quả thống kê và chưa thay đổi dữ liệu hay sản phẩm của Phase 1–2.

Phạm vi của lần điều chỉnh tài liệu hiện tại chỉ là `PHASE3.md`. Những chỗ bên dưới nói đến việc tạo mã, cập nhật báo cáo, nhật ký hoặc trạng thái trong `PLAN.md` đều là công việc tương lai khi triển khai Phase 3, không phải thay đổi được thực hiện trong lần chỉnh kế hoạch này.

## 1. Mục tiêu và phạm vi

### Mục tiêu

Phase 3 phải:

1. Mô tả phân phối sản lượng điện tái tạo ở hai tầng toàn cầu và ASEAN-10.
2. Tính các chỉ số dẫn xuất cần để trả lời đủ Q1–Q6.
3. Giải thích thống kê nào có ý nghĩa, thống kê nào dễ bị giá trị 0, độ lệch phân phối hoặc độ phủ làm méo.
4. Tạo một nguồn số liệu đã kiểm chứng cho Phase 4, chuẩn đối chiếu cho Power BI ở Phase 5 và bằng chứng cho Phase 6–7.

### Trong phạm vi

- Bốn chỉ số sản lượng điện từ file `03`:
  - `hydro_generation_twh`;
  - `wind_generation_twh`;
  - `solar_generation_twh`;
  - `other_renewables_generation_twh`.
- Bốn chỉ số tỷ trọng trong tổng điện năng:
  - `renewables_share_electricity_pct`;
  - `hydro_share_electricity_pct`;
  - `wind_share_electricity_pct`;
  - `solar_share_electricity_pct`.
- Thống kê mô tả, `YoY` (thay đổi so với năm liền trước), `CAGR` (tốc độ tăng trưởng kép hằng năm), cơ cấu công nghệ, tỷ trọng, xếp hạng, thời điểm xuất hiện, mức tập trung và đóng góp tăng trưởng.
- Phạm vi chính ASEAN-10, giai đoạn 2000–2021.
- Bối cảnh toàn cầu chỉ gồm các thực thể có `is_current_country_or_territory = 1`.
- Dòng `World` do nguồn công bố, chỉ dùng ở đúng vai trò tổng thế giới.

### Ngoài phạm vi

- Không cộng `biofuel_production_twh` vào tổng sản lượng điện tái tạo. Đây là sản lượng nhiên liệu sinh học, không cùng khái niệm với bốn cột phát điện của file `03`.
- Không cộng các chỉ số công suất GW vào sản lượng TWh.
- Không dùng các tỷ trọng trên năng lượng sơ cấp của nhóm ASEAN-6 cho phân tích chính ASEAN-10.
- Không tính hệ số công suất; đây là phân tích phụ của Phase 4 với độ phủ hạn chế đã được ghi trong `PLAN.md`.
- Không vẽ biểu đồ, viết DAX (công thức đo lường trong Power BI), chọn kết luận chính hay đưa ra đề xuất chính sách.
- Không làm sạch lại hoặc sửa dữ liệu Phase 2.

## 2. Căn cứ kế thừa từ Phase 1–2

Kế hoạch Phase 3 khóa các mốc sau làm hợp đồng đầu vào:

- 17 CSV nguồn không bị sửa.
- `fact_energy` có 89.075 quan sát, gồm 36.153 giá trị 0 và 52.922 giá trị dương.
- Có 256 thực thể, trong đó 215 quốc gia/vùng lãnh thổ hiện tại và đúng 10 nước ASEAN.
- Có 16 chỉ số chuẩn; tám chỉ số nêu ở phần phạm vi có `scope = main_asean10`.
- `Panel` (bảng dữ liệu theo thực thể–thời gian) ASEAN chính đủ 1.760/1.760 ô:

  `10 nước × 22 năm × (4 chỉ số TWh + 4 chỉ số tỷ trọng điện)`.

- Riêng bốn chỉ số TWh, ASEAN đủ 880/880 ô.
- Trên `spine` (khung đầy đủ các tổ hợp khóa) toàn cầu `215 × 22 = 4.730 entity-year` có 4.601 dòng đủ 4/4 thành phần, 67 dòng có 3 thành phần, 10 dòng có 1 thành phần và 52 dòng không có thành phần nào. Như vậy có 77 dòng quan sát một phần và tổng cộng 129 dòng không thể tạo tổng 4/4; Phase 3 không được bỏ qua các trường hợp này.
- Dòng `World` đủ bốn thành phần TWh trong toàn bộ 2000–2021.
- V1 có 23 `WARN` vì tổng các quốc gia hiện tại không luôn bằng dòng `World`; V1–V5 là đối soát nguồn, không phải kiểm tra chặn.
- 31 kiểm tra cấu trúc và V6–V8 phải `PASS`; không có khóa trùng, giá trị âm hay tỷ lệ ngoài miền `[0,100]`.
- Năm 2022 bị loại khỏi tầng phân tích; không được đưa lại vào Phase 3.
- Không có ô thiếu trong panel ASEAN chính; không nội suy, điền tiến, điền lùi hoặc đổi `NULL` thành 0.

Những mốc này vừa là căn cứ chọn phương pháp, vừa là kiểm chứng hồi quy. Nếu chúng thay đổi, Phase 3 phải dừng trước khi tính chỉ số.

## 3. Các quyết định phương pháp đã khóa

### 3.1. Nguồn chuẩn và tính độc lập của hai công cụ

`sql/renewables.db` là `canonical input` (đầu vào chuẩn) duy nhất của Phase 3.

- Python đọc các bảng Phase 2 từ `database` (cơ sở dữ liệu) bằng `sqlite3` rồi tính bằng pandas/SciPy.
- SQL tính độc lập từ `fact_energy` và các bảng chiều.
- `sql/03_analysis.sql` không được đọc `fact_metrics` do Python tạo. Quy tắc này ngăn kiểm tra vòng tròn, trong đó kết quả được so với chính nó.
- CSV trong `output/clean/` vẫn là đầu vào của Power BI theo `PLAN.md`, nhưng không phải nguồn tính của Phase 3.
- Trước khi tính, tạo `phase2_input_fingerprint` (dấu vân tay đầu vào Phase 2) bằng SHA-256 trên phép tuần tự hóa chuẩn, sắp theo khóa của `dim_entity`, `dim_metric`, `dim_year`, `fact_energy` và `missingness_audit`. Giá trị số dùng biểu diễn ổn định, tên cột và dấu phân cách nằm trong dữ liệu băm.
- `sql/02_validate.sql` tạo cột `phase2_input_fingerprint` với trạng thái ban đầu `UNBOUND`; `python/run_sql.py` chỉ gắn dấu vân tay hiện tại sau khi đủ 864 dòng, đủ 39 mã `S01–S31`/`V1–V8`, đúng 34 mã chặn duy nhất và toàn bộ mã chặn `PASS`. Phase 3 tính lại dấu vân tay và dừng nếu bất kỳ dòng kiểm định nào chưa được gắn hoặc thuộc dữ liệu khác.
- Ghi cùng dấu vân tay vào `fact_metrics`, `03_metric_definitions.csv` và trang tính `metadata` của cả sáu `workbook` (tệp Excel nhiều trang tính). Mục tiêu là phát hiện trường hợp Phase 2 đã được dựng lại nhưng chuẩn đối chiếu Phase 3 vẫn thuộc bản dữ liệu cũ.

### 3.2. Cửa sổ và lát cắt

- Cửa sổ thường niên chính: 2000–2021, đủ 22 năm.
- Năm cắt ngang: 2000, 2010, 2021.
- Giai đoạn tăng trưởng:
  - 2000–2010;
  - 2010–2021;
  - 2000–2021.
- Toàn cầu:
  - `population_n = 215`;
  - thống kê từng năm dùng các quốc gia/vùng lãnh thổ hiện tại có quan sát ở lát cắt đó;
  - luôn công bố `observed_n` và `missing_n`.
- ASEAN:
  - `population_n = 10`;
  - dùng đủ ASEAN-10 trong mọi năm 2000–2021.

Không dùng số dòng quan sát từng năm làm mẫu số cho chỉ số “tỷ lệ số nước”. Điều này trực tiếp xử lý rủi ro về độ phủ tại năm 2000 đã phát hiện ở Phase 1.

### 3.3. Hai định nghĩa sản lượng

Tên chỉ số phải thể hiện đây là **sản lượng điện**, không phải tổng cung hay tiêu thụ năng lượng:

`renewable_generation_twh
= hydro_generation_twh
+ wind_generation_twh
+ solar_generation_twh
+ other_renewables_generation_twh`

`modern_generation_twh
= wind_generation_twh
+ solar_generation_twh`

“Sản lượng điện tái tạo hiện đại” là định nghĩa vận hành riêng của đồ án để tách gió + mặt trời khỏi lợi thế thủy điện sẵn có. Không diễn giải nó như một chuẩn phân loại phổ quát.

### 3.4. Quy tắc đủ thành phần

Dùng `complete-case` (chỉ tính khi đủ thành phần):

- `renewable_generation_twh` chỉ được tính khi `component_count = 4`.
- `modern_generation_twh` chỉ được tính khi `component_count = 2`.
- Nếu thiếu bất kỳ thành phần bắt buộc nào:
  - `metric_value = NULL`;
  - `value_status = NOT_OBSERVED`;
  - `exclusion_reason = INCOMPLETE_COMPONENTS`.
- Cấm dùng `pandas.sum(skipna=True)` hoặc `COALESCE(component, 0)` để tạo tổng dẫn xuất.

ASEAN không mất quan sát vì quy tắc này; mục tiêu chính là ngăn tổng một phần ở tầng toàn cầu bị trình bày như tổng đầy đủ.

### 3.5. Giá trị 0, giá trị thiếu và ngưỡng

- 0 là quan sát hợp lệ và được giữ trong tổng, thống kê, xếp hạng và Gini.
- `NULL` là không có quan sát hoặc công thức không xác định; không được đổi thành 0.
- Ba biến thể thống kê cho bốn chỉ số sản lượng gốc:
  - `ALL_OBSERVED`: mọi quan sát, gồm 0;
  - `POSITIVE`: `value > 0`;
  - `MATERIAL`: `value_class = 'Material'`.
- Với bốn chỉ số TWh, `MATERIAL` của Phase 2 nghĩa là `value >= 0,05 TWh`.
- Khái niệm trên khác `MATERIAL` ở Phase 1: nhãn Phase 1 dùng để phân loại chênh lệch nguồn và đòi hỏi đồng thời chênh tuyệt đối `> 0,05 TWh` lẫn chênh tương đối `> 1%`.
- Không chọn ngưỡng sau khi xem thứ hạng:
  - kết quả so sánh và xếp hạng CAGR cấp quốc gia **chính** dùng sàn đầu kỳ `0,05 TWh`;
  - CAGR thô khi đầu kỳ chỉ lớn hơn 0 được giữ làm chẩn đoán độ nhạy, không dùng để chọn kết luận chính; CAGR cấp khu vực chỉ cần đầu kỳ lớn hơn 0 vì không tham gia xếp hạng quốc gia;
  - `0,1` và `1 TWh` chỉ là `sensitivity analysis` (kiểm tra độ nhạy) xuất song song;
  - hai ngưỡng phụ không được thay thế kết quả chính.
- Khi cần đếm mức `Material` cho hai tổng dẫn xuất, Phase 3 dùng `derived_value >= 0,05 TWh` và ghi `threshold_rule = PHASE3_DERIVED_FLOOR`; không gán ngược `value_class` của một thành phần cho tổng.

### 3.6. Đơn vị lưu trữ

- Sản lượng và thay đổi tuyệt đối: `TWh`.
- Mức tỷ trọng nguồn `*_share_electricity_pct`: giá trị phần trăm trong miền `[0,100]`.
- Thay đổi tỷ trọng nguồn: điểm phần trăm trong miền `[-100,100]`.
- YoY, CAGR, cơ cấu công nghệ, tỷ trọng ASEAN/thế giới, tỷ trọng quốc gia trong ASEAN và đóng góp tăng trưởng: tỷ lệ thập phân; ví dụ `0,25` nghĩa là 25%.
- Top-1 share và top-3 share: tỷ lệ thập phân.
- `HHI` (chỉ số tập trung Herfindahl–Hirschman) và `Gini` (hệ số bất bình đẳng): tỷ lệ trong miền `[0,1]`, với giới hạn chặt hơn được nêu ở phần tương ứng.
- Excel định dạng mọi giá trị có đơn vị `ratio` bằng `0.0000%`; không nhân 100 và không áp dụng định dạng phần trăm cho đơn vị `pct`, vốn đã lưu ở thang 0–100.
- Không làm tròn trước khi tính tổng, tốc độ, tỷ trọng hoặc xếp hạng. Làm tròn chỉ phục vụ hiển thị.

### 3.7. Quy ước thống kê mô tả

Bộ thống kê:

`n, sum, mean, median, sd, CV, min, max,
P10, P25, P50, P75, P90, P95, P99,
IQR, skewness, kurtosis`.

Trong đó `mean` là trung bình số học, `median` là trung vị, `sd` là độ lệch chuẩn và `CV` là hệ số biến thiên.

Quy tắc:

- `sd` là độ lệch chuẩn tổng thể với `ddof=0` vì mục tiêu là mô tả toàn bộ tập thực thể quan sát trong phạm vi đã định nghĩa, không suy rộng từ mẫu.
- Phân vị dùng nội suy tuyến tính; `P50 = median` và `IQR = P75 - P25`.
- `CV = sd / mean` chỉ tính khi `included_n >= 2` và mean lớn hơn 0.
- `skewness` (độ lệch) dùng hiệu chỉnh độ chệch, tương ứng `bias=False`; chỉ tính khi `included_n >= 3` và phương sai lớn hơn 0.
- `kurtosis` (độ nhọn vượt chuẩn Fisher) dùng `fisher=True, bias=False`; chỉ tính khi `included_n >= 4` và phương sai lớn hơn 0.
- Với `included_n = 1`, sum/mean/median/min/max/phân vị hợp lệ và `sd = 0` theo quy ước tổng thể; CV vẫn `NULL / INSUFFICIENT_N` vì cần ít nhất hai quan sát.
- Với `included_n >= 2` nhưng mean bằng 0, CV là `NULL / NOT_DEFINED / ZERO_MEAN`; nguyên nhân là mẫu số bằng 0, không phải thiếu quan sát.
- Nhóm không có quan sát trả `NULL / EMPTY_GROUP` cho sum và mọi thống kê giá trị; các số đếm vẫn bằng 0.
- Nhóm rỗng hoặc không đủ `n` phải để `NULL` cho đúng thống kê không xác định. Với nhóm hằng, mean/median/min/max/phân vị vẫn xác định, `sd = 0` và `CV = 0` nếu mean dương; chỉ skewness và kurtosis là `NULL / CONSTANT_GROUP`.

Mỗi lát cắt phải kèm:

`population_n
observed_n
missing_n
included_n
zero_n
trace_n
material_n
zero_share_population
zero_share_observed`

Trong đó:

- `population_n`, `observed_n`, `missing_n`, `zero_n`, `trace_n` và `material_n` được tính trên lát cắt gốc trước bộ lọc nên không đổi giữa ba `filter_variant`.
- `included_n` được tính sau bộ lọc và chính là `n` dùng cho các thống kê mô tả.
- `zero_share_population = zero_n / population_n`, với mẫu số cố định 215 hoặc 10.
- `zero_share_observed = zero_n / observed_n`, chỉ là tỷ lệ có điều kiện trên các quan sát thực có.

### 3.8. YoY và CAGR

YoY:

`yoy = value(t) / value(t-1) - 1`

Chỉ tính khi:

- có đúng quan sát năm `t` và `t-1`;
- hai năm liên tiếp;
- giá trị năm trước lớn hơn 0.

Trường hợp biên:

- năm trước bằng 0 → `NULL / ZERO_BASE`;
- thiếu năm hiện tại → `NULL / MISSING_CURRENT`;
- thiếu năm trước → `NULL / MISSING_PREVIOUS`;
- năm trước dương, năm hiện tại bằng 0 → `-1`, là kết quả hợp lệ.

CAGR:

`cagr = (end_value / start_value)^(1 / (end_year - start_year)) - 1`

Chỉ tính khi:

- có đúng hai đầu mốc;
- `start_value > 0`;
- `end_year > start_year`.

Trường hợp biên:

- `end_value = 0` → CAGR bằng `-1`, hợp lệ;
- `start_value = 0` → `NULL / ZERO_BASE`;
- thiếu đầu mốc → `NULL / MISSING_ENDPOINT`.

CAGR cấp khu vực được tính nếu tổng khu vực đầu kỳ dương. CAGR cấp quốc gia được tính thô khi đầu kỳ dương, nhưng kết quả so sánh chính và hạng chỉ hợp lệ khi đầu kỳ đạt sàn `0,05 TWh`; sàn `0,1` và `1 TWh` chỉ tạo hai kết quả độ nhạy song song. Nếu có dưới ba quốc gia đủ điều kiện, giữ giá trị CAGR nhưng không lập hạng và dùng `INSUFFICIENT_ELIGIBLE_ENTITIES`.

Tổng gió + mặt trời ASEAN năm 2000 bằng 0. Vì vậy CAGR hiện đại 2000–2010 và 2000–2021 phải là `NULL / ZERO_BASE`; chỉ giai đoạn có đầu kỳ dương mới được tính.

Để thực hiện đầy đủ vai trò SQL đã nêu ở Phase 8 của `PLAN.md`, tính thêm cho sáu chuỗi TWh của tổng ASEAN và Việt Nam:

- `cumulative_generation_twh(t) = Σ value(year)` từ 2000 đến `t`; chỉ tính khi mọi năm từ 2000 đến `t` đều có quan sát hợp lệ.
- `rolling_mean_3y_twh(t) = mean(value(t-2), value(t-1), value(t))`; chỉ tính khi có đúng ba năm liên tiếp.
- Năm 2000–2001 của trung bình trượt trả `NULL / INSUFFICIENT_WINDOW`; khoảng trống trong cửa sổ trả `NULL / INCOMPLETE_WINDOW`.
- Sáu chuỗi gồm bốn công nghệ, tổng bốn công nghệ và gió + mặt trời. Không tính tích lũy hoặc trung bình trượt cho tỷ lệ phần trăm.

### 3.9. Tỷ trọng và đối chiếu TWh với tỷ trọng điện

Các tỷ trọng sản lượng:

- Từng công nghệ trong tổng sản lượng điện tái tạo của cùng thực thể–năm.
- Từng nước trong tổng ASEAN theo bốn công nghệ, tổng tái tạo và gió + mặt trời.
- ASEAN trong tổng thế giới theo cùng định nghĩa tử số và mẫu số.

Quy tắc mẫu số:

- Tổng bằng 0 → tỷ trọng `NULL / ZERO_DENOMINATOR`.
- ASEAN/thế giới dùng dòng `World` cùng metric và cùng năm, gắn `denominator_basis = REPORTED_WORLD`.
- Tổng các quốc gia/vùng lãnh thổ hiện tại chỉ mang nhãn `CURRENT_COUNTRY_SUM_AUDIT` và không được dùng làm “tổng thế giới”.
- `CURRENT_COUNTRY_SUM_AUDIT` được tính riêng cho từng metric gốc bằng tổng mọi quan sát quốc gia hiện có, đúng logic V1. Tổng audit bốn công nghệ là tổng của bốn kết quả cấp metric; không dùng tổng dẫn xuất thiếu thành phần ở cấp quốc gia để thay đổi định nghĩa đối soát này.

Q5 dùng năm cặp cùng quốc gia, cùng năm:

1. `renewable_generation_twh` ↔ `renewables_share_electricity_pct`.
2. `modern_generation_twh` ↔ `wind_share_electricity_pct + solar_share_electricity_pct`.
3. `hydro_generation_twh` ↔ `hydro_share_electricity_pct`.
4. `wind_generation_twh` ↔ `wind_share_electricity_pct`.
5. `solar_generation_twh` ↔ `solar_share_electricity_pct`.

`modern_share_electricity_pct = wind_share_electricity_pct + solar_share_electricity_pct` chỉ được tính khi đủ cả 2/2 chỉ số phần trăm. Mỗi cặp Q5 chỉ được tạo khi cả phía TWh và phía phần trăm đều có quan sát hợp lệ; nếu thiếu, giá trị thay đổi/hướng để `NULL` với trạng thái và lý do tương ứng.

Với từng cặp, tính:

- thay đổi TWh giữa hai mốc hoặc hai năm liên tiếp;
- thay đổi điểm phần trăm;
- `direction_relation ∈ {SAME_DIRECTION, OPPOSITE_DIRECTION, ONE_OR_BOTH_UNCHANGED}`.

Khi phân loại hướng, một thay đổi có trị tuyệt đối không quá `1e-12` được xem là không đổi để tránh dấu giả do sai số số thực. Hai thay đổi cùng dấu khác 0 là `SAME_DIRECTION`; trái dấu là `OPPOSITE_DIRECTION`; các trường hợp còn lại là `ONE_OR_BOTH_UNCHANGED`.

Chỉ mô tả hai thước đo cùng hay ngược hướng. Không suy luận rằng nhu cầu điện, chính sách hay một nguyên nhân cụ thể tạo ra chênh lệch vì bộ dữ liệu không có các biến đó.

Tuyệt đối không cộng hoặc lấy trung bình đơn giản phần trăm của các nước để tạo “tỷ trọng ASEAN”. Không có tổng sản lượng điện mọi nguồn theo nước để dựng mẫu số khu vực có trọng số.

### 3.10. Xếp hạng

- Hạng công bố dùng `RANK()` giảm dần trong SQL và `rank(method='min', ascending=False)` trong pandas.
- Giá trị bằng nhau nhận cùng hạng; hạng kế tiếp có thể bị nhảy.
- Tên quốc gia chỉ dùng để sắp xếp hiển thị ổn định, không phá hòa cho hạng công bố.
- Chỉ quốc gia/vùng lãnh thổ có quan sát hợp lệ được xếp hạng; giữ cả giá trị 0.
- Tổng bốn công nghệ và tổng gió + mặt trời chỉ đủ điều kiện khi đạt quy tắc đủ thành phần.
- Nếu tổng toàn phạm vi bằng 0, mọi hạng của lát cắt là `NULL / ZERO_SCOPE_TOTAL` thay vì cùng hạng 1.
- Mỗi dòng hạng phải có `ranked_n` và `population_n`.
- Hạng toàn cầu của Việt Nam được công bố theo năm cùng `ranked_n`; không dùng nó để tính thay đổi hạng chính vì tập đủ điều kiện toàn cầu có thể đổi.
- Thay đổi hạng qua thời gian chỉ tính cho ASEAN-10, là `cohort` (tập đối tượng theo dõi) cố định.

Hai chỉ số dấu đã khóa:

- `modern_rank_gain = total_rank - modern_rank`; số dương nghĩa là hạng tốt hơn khi chỉ xét gió + mặt trời.
- `rank_gain_over_time = rank_start - rank_end`; số dương nghĩa là hạng được cải thiện ở cuối giai đoạn.

### 3.11. Thời điểm xuất hiện và kiểm duyệt

Không gọi mọi `MIN(year WHERE value > 0)` là “năm gia nhập”. Với từng nước ASEAN và từng công nghệ, phân loại trong cửa sổ 2000–2021:

- `ACTIVE_AT_WINDOW_START`: đã dương ngay năm 2000; đây là `left-censored` (kiểm duyệt trái), nên sự kiện thật có thể xảy ra trước cửa sổ.
- `OBSERVED_TRANSITION`: có ít nhất một quan sát 0 trước lần chuyển đầu tiên sang dương.
- `NOT_OBSERVED_BY_2021`: đủ chuỗi nhưng luôn bằng 0; đây là kết quả bị kiểm duyệt phải ở cuối cửa sổ.
- `UNKNOWN_INCOMPLETE_SERIES`: chuỗi không đủ để phân loại an toàn.

Lưu riêng:

`series_start_year
first_positive_in_window
observed_entry_year
is_entry_year_exact
first_material_in_window
observed_material_entry_year
is_material_entry_year_exact
entry_status
material_entry_status
lag_from_2000
relative_lag`

Quy tắc:

- `first_positive_in_window` có thể bằng 2000, nhưng `observed_entry_year = NULL` và `is_entry_year_exact = 0` cho `ACTIVE_AT_WINDOW_START`.
- `is_entry_year_exact = 1` chỉ cho `OBSERVED_TRANSITION`; dùng `NULL` chỉ khi chuỗi thiếu khiến trạng thái là `UNKNOWN_INCOMPLETE_SERIES`.
- `lag_from_2000` chỉ tính cho `OBSERVED_TRANSITION`.
- `relative_lag` chỉ tính khi năm xuất hiện sớm nhất của công nghệ trong ASEAN được quan sát chính xác. Nếu nước sớm nhất đã hoạt động ở năm 2000, để `NULL / EARLIEST_ENTRY_CENSORED`.
- Lần đầu đạt `MATERIAL` dùng các trạng thái riêng `MATERIAL_AT_WINDOW_START`, `OBSERVED_MATERIAL_TRANSITION`, `NOT_MATERIAL_BY_2021` và `UNKNOWN_INCOMPLETE_SERIES`. Chuyển trạng thái được coi là quan sát chính xác khi có ít nhất một giá trị trước đó không phải `Material`, gồm cả `Zero` và `Trace`; không bắt buộc giá trị trước bằng 0.
- `is_material_entry_year_exact` tuân theo cùng quy tắc 1/0/`NULL` như cờ lần đầu dương.

### 3.12. Mức tập trung và đóng góp tăng trưởng

Chỉ tính cho đủ ASEAN-10 và gồm cả nước có giá trị 0, theo:

- tổng sản lượng điện tái tạo;
- tổng gió + mặt trời.

Số nước “đạt mức đáng kể” của hai tổng dẫn xuất được đặt tên `above_0_05_n` và dùng ngưỡng Phase 3 `value >= 0,05 TWh`; không gọi đây là `material_n` của dữ liệu nguồn.

Theo từng năm:

`share_i = country_value_i / asean_total`

`HHI = Σ share_i²`

Gini dùng công thức thực nghiệm trên đủ 10 giá trị đã sắp tăng dần:

`Gini = 2 × Σ(i × x_i) / (n × Σx_i) - (n + 1) / n`

Quy tắc:

- Tỷ trọng dùng miền `[0,1]`.
- Với ASEAN-10, HHI hợp lệ trong `[0,1]` và Gini thỏa `0 ≤ Gini ≤ 0,9`.
- Tổng ASEAN bằng 0 → `top-N share` (tỷ trọng của N giá trị lớn nhất), HHI và Gini đều `NULL / ZERO_DENOMINATOR`.
- Top-1 và top-3 lấy đúng một hoặc ba giá trị lớn nhất.
- Khi hòa ở vị trí thứ ba, dùng tên quốc gia để chọn dòng hiển thị ổn định; vì giá trị hòa bằng nhau nên tổng top-3 không đổi.
- Không dùng `RANK() <= 3` để lấy top-3 vì có thể trả hơn ba quốc gia.

HHI/Gini theo mức sản lượng không đủ để kết luận “tăng trưởng do vài nước”. Vì vậy, với mỗi giai đoạn đã khóa, tính thêm:

`country_delta = end_value - start_value`

`positive_addition = max(country_delta, 0)`

`positive_growth_share = positive_addition / Σ positive_addition`

Xuất riêng các giảm sút, số nước tăng, tổng tăng dương và tỷ trọng top-3 trong tổng tăng dương. Nếu không có tăng dương, tỷ trọng đóng góp là `NULL`. Kết quả phải gọi đúng là “tỷ trọng trong tổng phần tăng dương”, không gọi là tỷ trọng trong tăng trưởng ròng.

## 4. Trình tự triển khai

## Bước 1 — Xác nhận đầu vào Phase 2

### Làm gì

Chạy đúng thứ tự:

```powershell
python python\02_clean_build.py
python python\run_sql.py sql\02_validate.sql --fail-on-blocking --output-csv output\stats\02_validation_results.csv
```

Đối chiếu các mốc ở mục 2 và xác nhận `validation_results` có đúng 864 dòng, đủ `S01–S31` và `V1–V8`, cùng một `phase2_input_fingerprint` khớp dữ liệu hiện tại.

### Vì sao

Chạy lại Phase 2 tái tạo database và loại mọi sản phẩm Phase 3 cũ. Kiểm định ngay sau đó bảo đảm Phase 3 không dùng database mới dựng nhưng chưa có kết quả validation.

### Kết quả và điều kiện dừng

- 31 kiểm tra cấu trúc và V6–V8 `PASS`.
- Đúng 34 dòng chặn, mỗi mã `S01–S31` và `V6–V8` xuất hiện một lần; V1–V5 đều hiện diện làm bằng chứng audit.
- Không có dòng `is_blocking = 1` mang trạng thái khác `PASS`.
- `WARN/SKIP` của V1–V5 được giữ làm bằng chứng đối soát, không làm dừng.
- Nếu bất kỳ kiểm tra chặn nào không đạt, dừng Phase 3 và xử lý ở Phase 2.

## Bước 2 — Lập đặc tả chỉ số có phiên bản

### Làm gì

Định nghĩa từng chỉ số với các trường:

`metric_name
question_id
definition
formula
unit
grain
scope
source_metric_keys
component_rule
denominator_rule
null_rule
zero_rule
eligibility_rule
threshold_rule
method_version
phase2_input_fingerprint
downstream_use
crosscheck_required
q5_pair_mapping`

`crosscheck_required` xác định kết quả phải có bản tính SQL độc lập. Mọi dòng chỉ số phân tích sẽ đi vào `fact_metrics` phải có `crosscheck_required = 1`; chỉ metadata (siêu dữ liệu) và bản thân các dòng kiểm định mới được đặt 0.

Khóa `method_version = phase3_v1` và xuất đặc tả thành `output/stats/03_metric_definitions.csv`.

### Vì sao

Đặc tả là nguồn duy nhất cho Python, SQL, Phase 4 và việc viết DAX ở Phase 5. Nó ngăn cùng một tên chỉ số nhưng dùng khác mẫu số, đơn vị hoặc điều kiện đủ.

### Kết quả hướng tới

Mọi chỉ số trong sáu workbook và `fact_metrics` đều ánh xạ được tới đúng một dòng đặc tả.

## Bước 3 — Chuẩn bị cấu trúc chương trình

### Làm gì

Chuẩn bị:

- `python/03_descriptive.py`;
- `sql/03_analysis.sql`.

Python phụ trách đọc database, dựng panel, thống kê phân phối, sáu workbook, kiểm định và công bố đầu ra. SQL tạo độc lập toàn bộ dòng phân tích có `crosscheck_required = 1`, gồm thống kê mô tả, số đếm độ phủ, tổng hợp, YoY, CAGR, tỷ trọng, Q5, xếp hạng, thời điểm xuất hiện, top-N, HHI, Gini và đóng góp tăng dương. Phân vị tuyến tính, skewness và kurtosis trong SQL phải được triển khai tường minh bằng CTE/hàm cửa sổ theo đặc tả, không dùng hàm `PERCENTILE_CONT` mà SQLite không hỗ trợ. Python không dùng kết quả SQL làm đầu vào tính toán và SQL không đọc `fact_metrics` do Python tạo.

`python/03_descriptive.py` phải thực thi hoặc đọc kết quả từ `sql/03_analysis.sql` trước khi ghi `fact_metrics`, để đối chiếu được thực hiện trước khi công bố.

Giao diện SQL được khóa như sau:

- `03_analysis.sql` tạo lại `TEMP TABLE phase3_sql_results` trong chính kết nối do Python mở.
- Bảng tạm dùng cùng khóa ngữ nghĩa với `fact_metrics` và tối thiểu có `metric_value`, `metric_text_value`, `value_status`, `exclusion_reason`, các số đếm độ phủ/hạng/thành phần và `denominator_basis`.
- Python đọc bảng tạm trong cùng kết nối, thực hiện đối chiếu ngoài với kết quả pandas rồi mới tạo `fact_metrics`.
- Khi chạy `03_analysis.sql` độc lập để kiểm tra thủ công, câu lệnh cuối phải `SELECT` toàn bộ `phase3_sql_results` theo thứ tự khóa. Không phụ thuộc khả năng xuất nhiều tập kết quả của `python/run_sql.py`.

### Vì sao

Phân chia này dùng đúng thế mạnh của pandas/SciPy và hàm cửa sổ SQL, đồng thời giữ được hai cách triển khai độc lập.

### Kết quả hướng tới

Không có công thức SQL nào lấy kết quả Python làm đầu vào và không có công thức Python nào chỉ sao chép kết quả SQL.

## Bước 4 — Dựng panel phân tích chuẩn

### Làm gì

Dựng spine (khung đầy đủ khóa) `entity × year × metric_key` cho tám chỉ số chính, gắn:

`entity
year
metric_key
technology
measure_type
value
unit
value_class
scope
entity_type
is_current_country_or_territory
is_asean
is_observed
missing_region
missing_decision`

Từ đó tạo panel `entity × year` với bốn TWh, bốn tỷ trọng điện và các chỉ số dẫn xuất đã khóa.

### Vì sao

Spine làm lộ rõ ô thiếu thay vì để phép ghép bảng tự loại thực thể. Đây là cách chặn mất nước và nhầm `NULL` với 0.

### Kết quả hướng tới

- ASEAN có đúng 220 `entity-year` và 1.760 ô nguồn.
- Không có năm ngoài 2000–2021 trong panel chính.
- Mọi tổng dẫn xuất có `component_count` và trạng thái đủ thành phần.

## Bước 5 — Tính thống kê mô tả

### Làm gì

Tính bộ thống kê ở mục 3.7 theo:

`scope × milestone_year × generation_metric × filter_variant`

Hai phạm vi là toàn cầu và ASEAN-10; ba năm là 2000, 2010, 2021; bốn metric là bốn công nghệ TWh; ba biến thể là `ALL_OBSERVED`, `POSITIVE` và `MATERIAL`.

### Vì sao

Tầng toàn cầu cho bối cảnh phân phối đủ lớn; ASEAN mô tả trực tiếp mười nước. Ba biến thể cho thấy mean, median và phân vị thay đổi thế nào khi giữ hoặc loại giá trị 0/Trace.

### Kết quả hướng tới

Mỗi dòng có đủ số đếm độ phủ, nguồn, đơn vị, mẫu số và mã lý do cho mọi thống kê không xác định. Biến thể `MATERIAL` ghi trực tiếp `threshold_value = 0,05 TWh` ở cả kết quả Python lẫn SQL.

## Bước 6 — Tính quy mô, tăng trưởng và bối cảnh thế giới

### Làm gì

Tính chuỗi 2000–2021 cho:

- bốn công nghệ;
- tổng bốn công nghệ;
- gió + mặt trời;
- tổng ASEAN;
- dòng `World` công bố;
- tỷ trọng ASEAN/thế giới;
- tổng quốc gia hiện tại chỉ để đối soát.

Tính thay đổi tuyệt đối, YoY, CAGR chính, hai ngưỡng độ nhạy, tích lũy từ 2000 và trung bình trượt ba năm theo quy tắc đã khóa.

### Vì sao

Đây là bằng chứng cho Q1 và cung cấp chuỗi đầy đủ cho Phase 4. Tách `World` công bố khỏi tổng quốc gia xử lý trực tiếp 23 `WARN` ở V1.

### Kết quả hướng tới

Không có CAGR được tạo từ mẫu số 0; riêng hai giai đoạn hiện đại bắt đầu năm 2000 có trạng thái `ZERO_BASE`.

## Bước 7 — Tính cơ cấu và Q5

### Làm gì

Tính cơ cấu bốn công nghệ trong tổng sản lượng điện tái tạo, năm cặp TWh–tỷ trọng điện và thay đổi hướng theo mục 3.9 cho toàn bộ ASEAN-10 × 22 năm.

Tạo `benchmark` (mốc đối chiếu) Việt Nam:

- tổng của ASEAN-9, tức ASEAN loại Việt Nam;
- median quốc gia trong ASEAN-9;
- tỷ trọng Việt Nam trong tổng ASEAN.

### Vì sao

Bước này trả lời Q2, Q4 và phần Q5 bị thiếu trong kế hoạch cũ. Benchmark loại Việt Nam khỏi nhóm so sánh để tránh một quan sát xuất hiện đồng thời ở cả tử số và nhóm tham chiếu.

### Kết quả hướng tới

Không có tỷ trọng ASEAN nào được tạo bằng cách cộng/trung bình phần trăm quốc gia; dữ liệu Q5 giữ đúng cặp cùng nước, cùng năm.

## Bước 8 — Tính xếp hạng

### Làm gì

Tính:

- hạng ASEAN theo tổng bốn công nghệ và gió + mặt trời cho đủ 22 năm;
- `modern_rank_gain`;
- `rank_gain_over_time` cho các mốc ASEAN;
- hạng toàn cầu của Việt Nam theo từng công nghệ, tổng tái tạo và gió + mặt trời, kèm `ranked_n`;
- CAGR cấp khu vực cho ASEAN và `World` trên sáu chuỗi TWh, không xếp hạng hai khu vực này;
- CAGR cấp quốc gia và hạng CAGR chỉ trong ASEAN-10, trên sáu chuỗi TWh × ba giai đoạn × ba sàn đã khóa; không tạo bảng xếp hạng CAGR toàn cầu.

### Vì sao

Q3 cần so hai định nghĩa trên cùng cohort ASEAN-10. Hạng toàn cầu biến động theo độ phủ nên phải công bố `ranked_n` và không dùng làm thước đo thay đổi hạng chính.

### Kết quả hướng tới

Python và SQL cho cùng tập khóa, cùng hạng và cùng trạng thái không xác định.

## Bước 9 — Tính trạng thái xuất hiện công nghệ

### Làm gì

Phân loại lần đầu dương và lần đầu `MATERIAL` theo mục 3.11 cho 10 nước × 4 công nghệ.

### Vì sao

Nhiều chuỗi thủy điện và nguồn khác đã dương ở năm 2000. Nếu coi 2000 là năm gia nhập thật, độ trễ sẽ bị sai do kiểm duyệt trái.

### Kết quả hướng tới

Chỉ `OBSERVED_TRANSITION` có năm gia nhập chính xác và độ trễ số; các trạng thái bị kiểm duyệt có mô tả đúng giới hạn.

## Bước 10 — Tính mức tập trung và đóng góp tăng trưởng

### Làm gì

Tính top-1, top-3, HHI và Gini thường niên cho tổng tái tạo và gió + mặt trời. Theo ba giai đoạn, tính đóng góp tăng dương của từng nước và tỷ trọng top-3.

### Vì sao

Chỉ số theo mức sản lượng trả lời “sản lượng tập trung đến đâu”; đóng góp theo chênh lệch mới trả lời “phần tăng do bao nhiêu nước tạo ra”. Tách hai khái niệm ngăn kết luận quá mức cho Q6.

### Kết quả hướng tới

Có đủ bằng chứng riêng cho mức sản lượng và phần tăng; mọi trường hợp tổng bằng 0 trả `NULL` có lý do.

## Bước 11 — Đối chiếu Python và SQL

### Làm gì

Đối chiếu toàn bộ khóa có `crosscheck_required = 1`; không lấy mẫu và không giới hạn ở một số nhóm thuận tiện. Phạm vi gồm:

- toàn bộ thống kê mô tả, phân vị, số đếm độ phủ và ba biến thể lọc;
- tổng theo năm;
- YoY và CAGR;
- tích lũy và trung bình trượt ba năm;
- tỷ trọng, thay đổi và trạng thái cùng/ngược hướng của năm cặp Q5;
- xếp hạng;
- năm đầu dương, năm đầu `MATERIAL` và các trạng thái xuất hiện tương ứng;
- top-1, top-3, HHI, Gini và đóng góp tăng dương;
- số đếm đủ điều kiện.

Dùng `outer join` (phép ghép ngoài) trên đủ chín trường khóa ngữ nghĩa của `fact_metrics` để bắt cả dòng chỉ xuất hiện ở một công cụ. Nếu Python hoặc SQL thiếu bất kỳ khóa bắt buộc nào thì dòng đó phải `FAIL`; không được thu hẹp tập so sánh về phần giao của hai kết quả.

Xuất `output/stats/03_crosscheck_results.csv` với `schema` (lược đồ cột):

`check_id
question_id
comparison_type
metric_name
subject_type
subject_key
period_type
period_key
series_key
comparison_scope
filter_variant
method_version
phase2_input_fingerprint
python_present
sql_present
python_status
sql_status
python_exclusion_reason
sql_exclusion_reason
python_value
sql_value
python_text_value
sql_text_value
absolute_difference
relative_difference
absolute_tolerance
relative_tolerance
status
failure_reason`

### Vì sao

So vài số mẫu không phát hiện được dòng thiếu, khác cohort hoặc khác quy tắc `NULL`. Ghép ngoài trên toàn bộ khóa kiểm tra cả tập kết quả lẫn giá trị.

### Quy tắc đạt

- So trạng thái hiện diện, `value_status` và `exclusion_reason` trước; bất kỳ khác biệt nào đều `FAIL` trước khi xét giá trị.
- Với hai số: `absolute_difference = abs(python_value - sql_value)`. Nếu cả hai bằng 0 thì `relative_difference = 0`; nếu không, `relative_difference = absolute_difference / max(abs(python_value), abs(sql_value))`.
- Số thực đạt theo `isclose(atol=1e-9, rtol=1e-9)`.
- Khóa, hạng, năm, số đếm, giá trị chữ và trạng thái: khớp tuyệt đối.
- Mọi dòng bắt buộc phải `PASS`.

## Bước 12 — Dựng `fact_metrics`

### Làm gì

Tạo bảng dạng dọc; mỗi dòng là một giá trị chỉ số hoặc một trường hợp không tính được đã giải thích. Bảng phải chứa các mức nguồn của tám chỉ số trong phạm vi khi chúng được dùng cho Q1–Q6/Phase 4, cùng toàn bộ chỉ số dẫn xuất, để Phase 4 không phải quay lại tính công thức Phase 3 từ dữ liệu sạch.

Các trường nhận diện bắt buộc, không được `NULL`:

`subject_type
subject_key
period_type
period_key
series_key
metric_name
comparison_scope
filter_variant
method_version`

Các trường dữ liệu:

`period_start_year
period_end_year
metric_value
metric_text_value
unit
value_status
exclusion_reason
population_n
observed_n
missing_n
included_n
zero_n
trace_n
material_n
ranked_n
component_count
required_component_count
denominator_basis
threshold_value
source_metric_keys
phase2_input_fingerprint`

Quy ước:

- `subject_type ∈ {COUNTRY, REGION, WORLD, STATISTICAL_SCOPE}`; `subject_key` dùng tên thực thể chuẩn hoặc một trong `ASEAN_10`, `WORLD_REPORTED`, `GLOBAL_CURRENT_COUNTRIES`.
- `series_key ∈ {HYDRO, WIND, SOLAR, OTHER_RENEWABLES, RENEWABLE_TOTAL, MODERN_WIND_SOLAR}`.
- `comparison_scope ∈ {NONE, ASEAN_10, ASEAN_9, GLOBAL_CURRENT_COUNTRIES, WORLD_REPORTED}`.
- Ngoài ba mã CAGR, `filter_variant ∈ {NOT_APPLICABLE, ALL_OBSERVED, POSITIVE, MATERIAL}`; CAGR thô dùng `NOT_APPLICABLE` và không được gắn nhãn kết quả chính.
- `period_start_year` và `period_end_year` bắt buộc có giá trị; chỉ số theo năm dùng cùng một năm cho cả hai trường.
- `period_start_year <= period_end_year` và phải khớp với `period_type`/`period_key`.
- `period_type ∈ {YEAR, INTERVAL, WINDOW}`.
- `period_key` có dạng ổn định như `Y2021`, `I2000_2010` hoặc `W2000_2021`.
- `comparison_scope` và `filter_variant` dùng giá trị `NONE` hoặc `NOT_APPLICABLE` khi không áp dụng, không dùng `NULL` trong khóa.
- Ba kết quả xếp hạng CAGR dùng đúng `filter_variant ∈ {CAGR_FLOOR_0_05, CAGR_FLOOR_0_1, CAGR_FLOOR_1_0}` và `threshold_value` lần lượt bằng `0,05`, `0,1`, `1` TWh. Vì `filter_variant` nằm trong khóa ngữ nghĩa, các ngưỡng không thể ghi đè nhau.
- `value_status ∈ {CALCULATED, CALCULATED_TEXT, NOT_DEFINED, NOT_OBSERVED, CENSORED, INSUFFICIENT_N}`.
- `unit`, `value_status`, `exclusion_reason`, `denominator_basis`, `source_metric_keys` và `phase2_input_fingerprint` bắt buộc có giá trị.
- Với `value_status = CALCULATED`, `metric_value` phải là số hữu hạn, `metric_text_value = NULL` và `exclusion_reason = NONE`.
- Với trạng thái phân loại như `entry_status` và `direction_relation`, dùng `value_status = CALCULATED_TEXT`, `metric_value = NULL`, `metric_text_value` có giá trị, `unit = STATUS_CODE` và `exclusion_reason = NON_NUMERIC_RESULT`. Cặp trạng thái/lý do này giải thích tường minh vì sao trường số để trống.
- Với các `value_status` còn lại, cả hai trường giá trị phải `NULL` và `exclusion_reason != NONE`.
- `population_n`, `observed_n`, `missing_n`, `included_n`, `zero_n`, `trace_n`, `material_n`, `ranked_n`, `component_count` và `required_component_count` là số nguyên không âm khi áp dụng; để `NULL` khi trường không có ý nghĩa với loại dòng đó. Với lát cắt thống kê, phải có `population_n = observed_n + missing_n`; các số đếm `zero_n`, `trace_n`, `material_n` mô tả lát cắt nguồn trước bộ lọc, còn `included_n` mô tả tập sau bộ lọc.
- `component_count` không được lớn hơn `required_component_count` khi chỉ số có yêu cầu thành phần.
- `denominator_basis` dùng các mã đã khóa như `NONE`, `ASEAN_SUM_10`, `REPORTED_WORLD`, `TOTAL_RENEWABLE_GENERATION` hoặc `GROSS_POSITIVE_ADDITION`.
- `source_metric_keys` là mảng JSON đã sắp xếp; dùng mảng rỗng `[]` khi chỉ số không phụ thuộc trực tiếp metric nguồn, không dùng `NULL`.
- Ràng buộc duy nhất:

  `(subject_type, subject_key, period_type, period_key, series_key,
  metric_name, comparison_scope, filter_variant, method_version)`.

- Mỗi lần chạy xóa và dựng lại trong transaction (giao dịch dữ liệu), không `append` (nối thêm).
- Xuất bản sao sắp xếp ổn định tại `output/stats/03_fact_metrics.csv`.

### Vì sao

Khóa cũ chứa nhiều cột có thể `NULL` nên SQLite có thể cho phép trùng ngữ nghĩa. Khóa mới biểu diễn thống nhất chỉ số theo năm, theo giai đoạn và theo cửa sổ.

### Kết quả hướng tới

Mọi số trong workbook truy được về một khóa `fact_metrics` hoặc một truy vấn SQL được gắn mã.

## Bước 13 — Xuất sáu workbook

`Workbook` và `sheet` (trang tính) phải có đúng hợp đồng sau. Workbook phục vụ đọc, rà soát và trích dẫn; giao diện máy chuẩn cho Phase 4 là `03_fact_metrics.csv`, nên workbook có thể trình bày dạng rộng để dễ đọc.

Quy tắc truy vết chung:

- Nếu một dòng chỉ có một giá trị phân tích, dòng đó phải có `fact_key`, là chuỗi JSON theo đúng thứ tự chín trường khóa ngữ nghĩa của `fact_metrics`.
- Nếu một dòng rộng có nhiều cột giá trị, mỗi cột phải có cột khóa ghép đôi dạng `<value_column>_fact_key`. Không được dùng riêng `entity + year`, `pair_key` hay tên cột hiển thị làm khóa thay thế.
- Với dòng rộng, mỗi giá trị còn phải mang các cột ghép đôi `<value_column>_unit`, `<value_column>_source_metric_keys`, `<value_column>_denominator_basis` và `<value_column>_threshold_value`; mục tiêu là giữ đơn vị, nguồn, mẫu số và ngưỡng ngay cạnh giá trị thay vì chỉ dựa vào tài liệu ngoài workbook.
- Mọi sheet dữ liệu phải có `method_version`, `value_status` và `exclusion_reason` tương ứng với từng giá trị; sheet `metadata` ghi `phase2_input_fingerprint` và định nghĩa phép tuần tự hóa `fact_key`.
- `pair_key` của Q5 được khóa thành năm mã `RENEWABLE_TOTAL_VS_RENEWABLE_SHARE`, `MODERN_VS_WIND_SOLAR_SHARE`, `HYDRO_VS_HYDRO_SHARE`, `WIND_VS_WIND_SHARE`, `SOLAR_VS_SOLAR_SHARE`. Sheet `metadata` và `03_metric_definitions.csv` phải ánh xạ từng mã tới đúng `series_key`, chỉ số TWh và chỉ số phần trăm nguồn; `pair_key` không thay thế khóa `fact_metrics`.

### 1. `03_global_cross_section.xlsx`

- `generation_stats`, khóa `scope + year + metric_key + filter_variant`: thống kê toàn cầu theo 2000/2010/2021 × 4 công nghệ × 3 biến thể.
- `country_values`, khóa `entity + year + metric_key`: giá trị từng quốc gia/vùng lãnh thổ ở ba năm mốc.
- `coverage`, khóa `scope + year + metric_key`: population, observed, missing, zero, Trace, Material.
- `metadata`, khóa `metadata_key`: đúng 13 nội dung gồm phiên bản, fingerprint, cửa sổ, phạm vi workbook, nguồn, đơn vị, quy tắc thống kê, mẫu số, quy tắc `NULL`, quy tắc 0, ngưỡng, định nghĩa `fact_key` và ánh xạ Q5.

### 2. `03_asean_cross_section.xlsx`

- `generation_stats`, khóa `scope + year + metric_key + filter_variant`: thống kê ASEAN theo ba năm mốc.
- `asean_annual`, khóa `year + series_key + metric_name`: chuỗi tổng ASEAN, tổng bốn công nghệ, gió + mặt trời và cơ cấu.
- `country_year_values`, khóa `entity + year + series_key + metric_name`: 10 nước × 22 năm phục vụ đọc và kiểm tra.
- `twh_vs_pct`, khóa `entity + year + pair_key`: mức TWh, mức phần trăm, thay đổi thường niên TWh, thay đổi điểm phần trăm và `direction_relation` của năm cặp Q5; năm 2000 để các thay đổi là `NULL / MISSING_PREVIOUS`.
- `endpoint_change`, khóa `entity + period_key + pair_key`: thay đổi TWh, điểm phần trăm và hướng theo ba giai đoạn.
- `metadata`.

### 3. `03_vietnam_time_series.xlsx`

- `annual`, khóa `year + series_key + metric_name`: 22 năm, bốn TWh, tổng tái tạo, gió + mặt trời, bốn tỷ trọng điện nguồn, `modern_share_electricity_pct`, tỷ trọng Việt Nam trong ASEAN cho sáu chuỗi TWh, hạng toàn cầu, tích lũy và trung bình trượt ba năm.
- `annual_changes`, khóa `year + series_key + metric_name`: thay đổi tuyệt đối, YoY, thay đổi điểm phần trăm và trạng thái hướng của năm cặp Q5.
- `asean9_benchmark`, khóa `year + series_key + metric_name`: tổng ASEAN-9 và median quốc gia ASEAN-9 cho bốn công nghệ, tổng tái tạo và gió + mặt trời.
- `endpoint_change`, khóa `period_key + pair_key`: đủ năm cặp Q5 × ba giai đoạn.
- `metadata`.

### 4. `03_ranking_comparison.xlsx`

- `annual_ranks`, khóa `entity + year`: 10 nước × 22 năm, hai cách xếp hạng và `modern_rank_gain`.
- `milestone_change`, khóa `entity + period_key + series_key`: 2000/2010/2021 và `rank_gain_over_time`.
- `cagr_ranking`, khóa `entity + period_key + series_key + filter_variant`: CAGR thô, hạng chính sàn 0,05 TWh và hai kiểm tra độ nhạy.
- `metadata`.

### 5. `03_entry_lag.xlsx`

- `entry_status`, khóa `entity + series_key`: trạng thái, năm đầu dương, năm đầu Material, cờ chính xác và độ trễ.
- `entry_summary`, khóa `series_key + status_type + status_value`: số nước theo trạng thái và công nghệ. `status_type` và `status_value` là hai cột vật lý bắt buộc; `metric_name` vẫn được giữ để tương thích và truy vết về `fact_metrics`, nhưng không thay thế hai cột trạng thái trong khóa công khai.
- `method_notes`: giải thích kiểm duyệt trái/phải.
- `metadata`.

### 6. `03_global_context.xlsx`

- `annual_context`, khóa `subject_key + year + series_key + metric_name`: 2000–2021, ASEAN, `World`, bốn công nghệ, tổng tái tạo, gió + mặt trời, YoY, tích lũy/trung bình trượt của ASEAN và tỷ trọng ASEAN/thế giới.
- `period_growth`, khóa `subject_key + period_key + series_key + filter_variant`: thay đổi tuyệt đối và CAGR theo trạng thái; YoY không đặt ở sheet có mức chi tiết giai đoạn.
- `annual_concentration`, khóa `year + series_key + metric_name`: top-1, top-3, HHI, Gini, `positive_n` và `above_0_05_n`.
- `growth_contribution`, khóa `entity + period_key + series_key`: 60 dòng đóng góp của 10 nước và 6 dòng `entity=ASEAN_10` chứa `gross_positive_addition_twh`, `growth_positive_n`, `top3_positive_growth_share` theo ba giai đoạn × hai chuỗi.
- `world_reconciliation`, khóa `year + series_key`: tổng quốc gia quan sát so với dòng `World`, chỉ dùng audit.
- `metadata`.

Mỗi workbook phải:

- dùng đúng tên sheet và thứ tự trên;
- ghi đơn vị, phạm vi, cửa sổ, nguồn, mẫu số, quy tắc `NULL`/0, ngưỡng và `method_version`;
- có đủ 22 năm ở các sheet thường niên;
- không chứa `Inf` hoặc chuỗi chữ `NaN`;
- để ô trống cho giá trị không xác định và có cột trạng thái/lý do tương ứng.

## Bước 14 — Kiểm tra chất lượng và công bố nguyên tử

### Làm gì

Tạo `output/stats/03_validation_results.csv` với lược đồ ổn định:

`validation_id
validation_group
question_id
severity
status
expected_value
actual_value
failure_reason
details
method_version
phase2_input_fingerprint`

`validation_id` là duy nhất; `question_id` dùng `NOT_APPLICABLE` cho kiểm tra hạ tầng; `severity ∈ {BLOCKING, AUDIT}` và `status ∈ {PASS, WARN, SKIP, FAIL}`. Không ghi thời điểm chạy động vào CSV này để nội dung có thể đối chiếu tái lập.

Mã kiểm định workbook dùng toàn bộ tên file và sheet, không cắt ngắn. Trước khi công bố phải có kiểm định tự xác nhận `validation_id.is_unique`, kiểm định đủ 13 khóa metadata, ánh xạ Q5, ngưỡng `MATERIAL`, số đếm phân phối và sáu dòng tổng hợp Q6.

Chạy các nhóm `gate` (điều kiện chặn):

1. Đầu vào và phạm vi.
2. Độ đầy đủ thành phần.
3. Công thức và miền giá trị.
4. Khóa và trạng thái `fact_metrics`.
5. Đối chiếu Python–SQL.
6. Hợp đồng sáu workbook.
7. Ánh xạ Q1–Q6.
8. Tính tái lập.

Sau khi Bước 1 hoàn tất, sao chép toàn bộ database Phase 2 sang database staging (bản tạm) bằng SQLite backup API. Mọi bảng/view Phase 3, đối chiếu và kiểm định được tạo trên bản staging; các CSV/XLSX cũng được ghi vào thư mục staging. Chỉ sau khi tất cả gate đạt mới thay database và đúng danh sách file Phase 3 chính thức. Đích SQLite phải được đưa vào phạm vi hoàn tác trước khi nhánh backup có thể thay đổi nó; lỗi `OSError` và `sqlite3.Error` đều kích hoạt phục hồi từ bản sao lưu.

Phạm vi bảo toàn nguyên tử bắt đầu **sau Bước 1**. Chạy lại Phase 2 ở đầu pipeline chủ động xóa sản phẩm Phase 3 cũ; kế hoạch không cam kết giữ bản Phase 3 cũ qua một lần rebuild Phase 2 đã thành công.

Kiểm thử hoàn tác phải bao phủ cả thay thế tệp thông thường và nhánh SQLite backup khi `os.replace` gặp `PermissionError` do database đang bị khóa. Với nhánh SQLite, phải kiểm tra công bố thành công, lỗi trong backup, lỗi xóa tệp staging sau backup và lỗi ở một tệp công bố sau đó. Nếu chính phục hồi thất bại, thông báo phải ghi rõ `rollback incomplete`, lỗi công bố gốc và lỗi phục hồi; không được khẳng định đầu ra cũ đã được khôi phục.

### Vì sao

Không có lỗi runtime (lỗi khi chạy) chưa chứng minh kết quả đúng. Bản database tạm và thư mục tạm ngăn database, CSV và workbook thuộc hai lần chạy khác nhau.

### Các kiểm tra bắt buộc

- ASEAN đủ 1.760/1.760 ô của tám chỉ số.
- Không có tổng dẫn xuất từ bộ thành phần thiếu.
- Không có `Inf`; `NaN` chỉ tồn tại tạm trong bộ nhớ rồi phải thành `NULL` kèm lý do.
- Mức tỷ trọng điện nguồn và tổng dẫn xuất gió + mặt trời nằm trong `[0,100]`; thay đổi điểm phần trăm nằm trong `[-100,100]`.
- Mẫu số ASEAN/thế giới luôn gắn `REPORTED_WORLD`.
- Không có phép cộng/trung bình phần trăm quốc gia thành phần trăm ASEAN.
- YoY/CAGR tuân thủ điều kiện mẫu số và đầu mốc.
- Các lát cắt tổng bằng 0 không có tỷ trọng, hạng hay chỉ số tập trung giả.
- HHI thuộc `[0,1]`; Gini ASEAN thỏa `0 ≤ Gini ≤ 0,9`.
- Tổng tỷ trọng quốc gia ASEAN và cơ cấu công nghệ xấp xỉ 1 trong dung sai `1e-9` khi mẫu số dương.
- Mỗi lát cắt đóng góp có đúng 10 nước; tổng `country_delta` khớp thay đổi tổng ASEAN; tổng `positive_growth_share` xấp xỉ 1 khi tổng phần tăng dương lớn hơn 0; top-3 lấy đúng ba dòng.
- `fact_metrics` không trùng khóa và mọi giá trị `NULL` có trạng thái/lý do.
- Với mọi lát cắt thống kê, `population_n = observed_n + missing_n`; với bốn chỉ số sản lượng nguồn, `observed_n = zero_n + trace_n + material_n`.
- Mọi sản phẩm Phase 3 mang cùng `phase2_input_fingerprint`.
- Sáu workbook được kiểm theo allow-list (danh sách cho phép) tên file ở Bước 13, không đếm bằng wildcard `03_*.xlsx`; mỗi file đúng tên và đủ sheet quy định.
- Q1–Q6 đều ánh xạ tới ít nhất một sheet.
- Mọi kiểm tra Python–SQL bắt buộc `PASS`.
- Hợp đồng phát hành khóa trực tiếp 18.926 dòng fact, phân bố Q1–Q6, 18.926 dòng đối chiếu và chính xác tập 92 mã kiểm định; hai lần chạy giống nhau không đủ để đạt nếu cùng lệch khỏi các mốc này.
- Đọc lại sáu workbook đã ghi và xác nhận mọi ô `ratio` dùng `0.0000%`, còn ô `pct` không dùng định dạng phần trăm.

### Kiểm thử chuẩn cho HHI và Gini

- Mười giá trị bằng nhau → HHI `0,1`, Gini `0`.
- Một nước giữ toàn bộ sản lượng → HHI `1`, Gini `0,9`.
- Mười giá trị đều 0 → HHI và Gini `NULL / ZERO_DENOMINATOR`.

### Tái lập

- Sau hai lần chạy liên tiếp từ cùng đầu vào, truy vấn `fact_metrics` theo đúng thứ tự chín trường khóa và so toàn bộ schema, khóa, giá trị, trạng thái cùng lý do; nội dung bảng SQLite phải giống nhau.
- CSV phải có thứ tự dòng/cột ổn định và nội dung giống nhau giữa hai lần chạy.
- Workbook phải có cùng sheet, schema và giá trị khi đọc lại.
- Không yêu cầu XLSX giống từng byte vì metadata của tệp ZIP có thể thay đổi giữa các lần ghi.
- Không file nào trong `archive/` bị sửa.

## Bước 15 — Ghi phát hiện vào nhật ký

### Làm gì

Cập nhật phần Phase 3 trong `docs/NhatKyPhanTich.md`. Mỗi phát hiện gồm:

`finding_id
question_id
scope
period
metric_name
numeric_evidence
evidence_file
evidence_sheet
evidence_key_or_query_id
method_version
phase2_input_fingerprint
interpretation
limitation
confidence`

Ghi cả phát hiện có ý nghĩa, kết quả không khác như dự kiến, trường hợp thống kê bị giá trị 0 làm méo và câu hỏi chưa thể trả lời.

### Vì sao

Định vị bằng file + sheet + khóa giúp Phase 6–7 dùng lại số đã kiểm chứng thay vì tính hoặc chép lại thủ công.

### Kết quả hướng tới

Mọi phát hiện Phase 3 có bằng chứng số và giới hạn diễn giải; chưa chọn 4–5 kết luận chính hay đề xuất chính sách.

## Bước 16 — Hoàn thiện mục 1.3 của báo cáo

### Làm gì

Thay phần “Phase 3 — chưa thực hiện” trong `docs/BaoCao.md` bằng cấu trúc theo sáu câu hỏi:

1. Q1 — quy mô, tốc độ và bối cảnh thế giới.
2. Q2 — cơ cấu bốn công nghệ.
3. Q3 — xếp hạng theo tổng tái tạo và gió + mặt trời.
4. Q4 — quỹ đạo Việt Nam so với ASEAN-9 và vị thế toàn cầu.
5. Q5 — sản lượng TWh đối chiếu tỷ trọng trong tổng điện.
6. Q6 — mức tập trung sản lượng và đóng góp tăng trưởng.
7. Quy ước thống kê và tác động của giá trị 0.
8. Giới hạn dữ liệu và diễn giải.
9. Dẫn chiếu tới sáu workbook.

### Vì sao

Cấu trúc theo Q1–Q6 ngăn Q5 bị bỏ sót và giữ mạch phân tích bám đúng câu hỏi đã khóa từ Phase 1.

### Kết quả hướng tới

Mỗi con số trong mục 1.3 truy được về `fact_metrics`, một workbook hoặc truy vấn SQL cụ thể.

## Bước 17 — Đóng Phase 3

### Làm gì

Chạy lại toàn bộ chuỗi:

```powershell
python python\02_clean_build.py
python python\run_sql.py sql\02_validate.sql --fail-on-blocking --output-csv output\stats\02_validation_results.csv
python python\03_descriptive.py
```

Chỉ khi tất cả gate đạt:

- ghi lệnh chạy chuẩn;
- xác nhận kết quả tái lập;
- xác nhận không sửa dữ liệu nguồn;
- đánh dấu Phase 3 hoàn thành trong `PLAN.md`.

### Vì sao

Chạy Phase 2 sẽ tái tạo database và xóa sản phẩm Phase 3 cũ. Vì vậy thứ tự Phase 2 → validation → Phase 3 là một phần của hợp đồng tái lập, không chỉ là hướng dẫn vận hành.

### Kết quả hướng tới

Phase 3 trở thành đầu vào ổn định cho trực quan hóa, chuẩn số liệu cho dashboard và kho bằng chứng cho báo cáo/kết luận.

## 5. Ma trận câu hỏi và sản phẩm

| Câu hỏi | Nội dung phải trả lời | File và sheet bằng chứng chính |
|---|---|---|
| Q1 | Quy mô, CAGR hợp lệ, ASEAN trong thế giới | `03_global_context.xlsx`: `annual_context`, `period_growth` |
| Q2 | Cơ cấu bốn công nghệ | `03_asean_cross_section.xlsx`: `asean_annual`, `country_year_values` |
| Q3 | Hai cách xếp hạng và độ chênh | `03_ranking_comparison.xlsx`: `annual_ranks`, `milestone_change`, `cagr_ranking` |
| Q4 | Việt Nam so với ASEAN-9 và vị thế toàn cầu | `03_vietnam_time_series.xlsx`: `annual`, `asean9_benchmark`; `03_entry_lag.xlsx`: `entry_status` |
| Q5 | TWh so với tỷ trọng trong tổng điện | `03_asean_cross_section.xlsx`: `twh_vs_pct`, `endpoint_change`; `03_vietnam_time_series.xlsx`: `annual_changes`, `endpoint_change` |
| Q6 | Tập trung sản lượng và đóng góp tăng trưởng | `03_global_context.xlsx`: `annual_concentration`, `growth_contribution` |

`03_global_cross_section.xlsx` cung cấp bối cảnh phân phối bắt buộc của yêu cầu 1.3, dù không thuộc riêng một câu hỏi.

## 6. Hợp đồng với các phase sau

### Phase 4

- Luồng biểu đồ chính của Phase 4 đọc `output/stats/03_fact_metrics.csv`, `output/stats/03_metric_definitions.csv` và các sheet chuỗi `asean_annual`, `country_year_values`, `annual`, `annual_changes`, `asean9_benchmark`, `annual_ranks`, `annual_context`. `fact_metrics` chứa cả mức nguồn cần vẽ và chỉ số dẫn xuất; các sheet chuỗi là bảng trình bày sẵn, phải đối chiếu được về cùng khóa và không phải nơi định nghĩa công thức mới.
- Không định nghĩa hoặc tính lại công thức Phase 3 trong Phase 4.
- `output/clean/fact_energy.csv` chỉ được Phase 4 đọc trực tiếp cho hệ số công suất phụ hoặc kiểm tra truy nguyên giá trị nguồn. Hệ số công suất là ngoại lệ ngoài `fact_metrics` Phase 3 và phải công bố quốc gia thiếu.
- Nếu Phase 4 tạo một chỉ số/phát hiện mới sẽ đi vào nhật ký, slide hoặc kết luận, Phase 4 phải xuất dữ liệu biểu đồ tại `output/stats/04_chart_data.xlsx`, tạo kiểm định tương ứng và ghi evidence locator (định vị bằng chứng). PNG đơn độc không đủ làm nguồn số liệu.

### Phase 5

- Tiếp tục nạp `output/clean/*.csv` theo `PLAN.md`.
- Dùng `03_metric_definitions.csv` để viết DAX.
- Dùng `fact_metrics` và sáu workbook làm chuẩn kiểm tra `KPI` (chỉ số hiệu suất chính)/hạng, không âm thầm thay đổi mô hình Power BI để đọc SQLite.
- DAX không được `SUM` hoặc `AVERAGE` bốn tỷ trọng quốc gia để tạo KPI “tỷ trọng điện ASEAN”. KPI khu vực chỉ dùng TWh, tỷ trọng ASEAN/thế giới theo TWh hoặc thống kê quốc gia được đặt tên rõ là mean/median không trọng số.

### Phase 6–7

- Không tính số mới hoặc định nghĩa chỉ số mới cho slide, kết luận hay đề xuất; chỉ được chạy lại kiểm định Phase 3–4 để xác nhận bằng chứng đã có.
- Chỉ sử dụng phát hiện có gate `PASS`. Mỗi phát hiện phải ghi trực tiếp `question_id`, `evidence_file`, `evidence_sheet`, khóa lọc hoặc mã truy vấn, `method_version` và `limitation`; không dựa vào thông tin nằm rải ở phần khác để suy ra các trường này.
- Q5 không được suy diễn nguyên nhân; Q6 chỉ được nói “tăng trưởng tập trung” khi dùng bảng đóng góp tăng trưởng, không suy từ HHI/Gini của mức sản lượng.

## 7. Danh sách sản phẩm

1. `python/03_descriptive.py`.
2. `sql/03_analysis.sql`.
3. Bảng `fact_metrics` trong `sql/renewables.db`.
4. `output/stats/03_fact_metrics.csv`.
5. `output/stats/03_metric_definitions.csv`.
6. Sáu workbook đúng tên ở Bước 13 đã được tạo và có đủ sheet quy định; không dùng wildcard (mẫu tên đại diện) để chấp nhận file thừa hoặc file cũ.
7. `output/stats/03_crosscheck_results.csv`.
8. `output/stats/03_validation_results.csv`.
9. Phần Phase 3 trong `docs/NhatKyPhanTich.md`.
10. Mục 1.3 trong `docs/BaoCao.md`.
11. Trạng thái Phase 3 trong `PLAN.md`.

## 8. Tiêu chí hoàn thành cuối cùng

Phase 3 chỉ hoàn thành khi:

- Đầu vào Phase 2 đạt toàn bộ hard gate (kiểm tra chặn).
- Có đủ hai file Python/SQL và SQL không phụ thuộc `fact_metrics` của Python.
- Có bảng `fact_metrics` với khóa ngữ nghĩa không rỗng, không trùng và phiên bản `phase3_v1`.
- Có đúng sáu workbook, đúng sheet và đủ chuỗi 2000–2021.
- Có đủ hai CSV giao diện `03_fact_metrics.csv`, `03_metric_definitions.csv` cùng hai CSV kiểm tra.
- Q1–Q6 đều có dữ liệu và dẫn chiếu rõ.
- Không có tổng một phần, `Inf` hoặc `NaN` chưa xử lý.
- Mọi `NULL` có trạng thái và lý do.
- Mẫu số thế giới, đơn vị tỷ lệ và dấu của thay đổi hạng nhất quán.
- Python và SQL khớp toàn bộ kết quả bắt buộc.
- Kiểm thử HHI/Gini chuẩn đạt.
- Phát hiện và mục 1.3 đã được cập nhật nhưng chưa vượt sang kết luận chính sách.
- Chạy lại cho nội dung ổn định và không sửa 17 CSV nguồn.
