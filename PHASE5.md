# Hợp đồng triển khai Phase 5 — Dashboard Power BI

Tài liệu này cụ thể hóa `PHASE 5 — Dashboard` trong `PLAN.md`. Mục tiêu là xây dựng dashboard (bảng điều khiển tương tác) Power BI gồm ba trang, dùng dữ liệu sạch của Phase 2, tuân thủ định nghĩa đã kiểm chứng ở Phase 3 và kế thừa quy ước trực quan của Phase 4.

Mỗi bước dưới đây có một `gate` (cổng điều kiện bắt buộc). Chỉ được bắt đầu bước tiếp theo khi toàn bộ tiêu chí của bước hiện tại đã đạt và có bằng chứng. Nếu một tiêu chí không đạt, phải sửa trong chính bước đó rồi chạy lại toàn bộ cổng. Nếu dữ liệu đầu vào, quan hệ hoặc công thức thay đổi, mọi cổng phía sau có liên quan phải chạy lại.

## 1. Hiện trạng và điều kiện đầu vào

| Phase | Kết quả hiện tại |
|---|---|
| Phase 0 | 26/26 kiểm tra môi trường đạt |
| Phase 1 | Đã khóa cửa sổ 2000–2021, không nội suy và loại năm 2022 khỏi phân tích chính |
| Phase 2 | 89.075 dòng `fact_energy`; 256 thực thể; 215 quốc gia/vùng lãnh thổ hiện tại; 16 chỉ số; panel ASEAN đủ 1.760/1.760 ô |
| Phase 3 | 18.926 dòng `fact_metrics`; 18.926/18.926 đối chiếu Python–SQL; 92/92 kiểm định đạt |
| Phase 4 | **ĐÃ HOÀN THÀNH** ngày 2026-09-08: 13 PNG, 16 sheet, 38/38 kiểm định tự động `PASS` và 13/13 biểu đồ được Nguyễn Hồng Minh ký nghiệm thu |
| Phase 5 | Thư mục `powerbi/` chưa có sản phẩm dashboard |

Các khóa đầu vào bắt buộc:

| Hạng mục | Giá trị khóa |
|---|---:|
| `fact_energy` | 89.075 dòng |
| SHA-256 `fact_energy.csv` | `dfaca2c46efde54b506f317497d458ed864f88ab4a8d74de9665afaa467a4374` |
| Phase 2 validation | 864 dòng = 560 `PASS` + 268 `WARN` + 36 `SKIP`; không có lỗi chặn |
| `fact_metrics` | 18.926 dòng |
| Đối chiếu Python–SQL | 18.926/18.926 `PASS` |
| Phase 3 validation | 92/92 `PASS` |
| `phase2_input_fingerprint` | `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10` |
| Phạm vi chính | ASEAN-10, 2000–2021; không nội suy; loại 2022 |

### 1.1. Sai lệch nội dung phải xử lý trước Phase 5

`docs/NhatKyPhanTich.md` và `docs/BaoCao.md` đang ghi “Thái Lan và Philippines đồng hạng 3” theo gió + mặt trời năm 2021.

Dữ liệu chuẩn trong `output/stats/03_fact_metrics.csv` cho thấy:

- Thái Lan: hạng tổng 5, hạng hiện đại 2;
- Philippines: hạng tổng 6, hạng hiện đại 3;
- hai nước cùng tăng 3 bậc khi đổi cách đo, nhưng không đồng hạng.

Sai lệch này không làm hỏng dữ liệu Phase 3 nhưng làm sai diễn giải bằng chữ. Phải sửa nhật ký và báo cáo, đồng thời kiểm tra lại C04 trước khi ký nghiệm thu Phase 4.

## 2. Quyết định kiến trúc đã khóa

### 2.1. Ba lớp nguồn không được trộn vai trò

1. Dữ liệu vận hành dashboard:
   - `output/clean/fact_energy.csv`;
   - `output/clean/dim_entity.csv`;
   - `output/clean/dim_metric.csv`;
   - `output/clean/dim_year.csv`.
2. Nguồn định nghĩa `measure DAX` (phép đo bằng DAX):
   - `output/stats/03_metric_definitions.csv`;
   - các quy tắc trong `PHASE3.md`.
3. Nguồn chuẩn để đối chiếu kết quả:
   - `output/stats/03_fact_metrics.csv`;
   - sáu workbook Phase 3;
   - `output/stats/04_chart_data.xlsx`;
   - `output/stats/04_validation_results.csv`.

Các đầu ra Phase 3–4 chỉ dùng để kiểm chứng, không được dùng làm nguồn hiển thị thay cho DAX. Power BI không nối vào `sql/renewables.db`.

### 2.2. Mô hình dữ liệu

Mô hình `star schema` (mô hình sao) phải có ba quan hệ chủ động, lọc một chiều từ bảng chiều sang fact:

- `DimEntity[entity] 1 → * FactEnergy[entity]`;
- `DimYear[year] 1 → * FactEnergy[year]`;
- `DimMetric[metric_key] 1 → * FactEnergy[metric_key]`.

Không được có quan hệ nhiều-nhiều, lọc hai chiều hoặc đường lọc mơ hồ.

**Hợp đồng cột cờ.** Ba tập thực thể dùng xuyên suốt Phase 5 được định nghĩa bằng đúng ba cột dưới đây, không được suy ra bằng cách khác:

| Tập | Cột định nghĩa | Số dòng |
|---|---|---:|
| Quốc gia/vùng lãnh thổ hiện tại — mẫu số của `global_rank` | `DimEntity[is_current_country_or_territory] = 1` | 215 |
| ASEAN-10 cố định — mọi mẫu số khu vực, hạng, chỉ số tập trung | `DimEntity[is_asean] = 1` | 10 |
| Cửa sổ phân tích chính | `DimYear[is_main_asean_window] = 1` | 22 |

⚠️ `is_aggregate = 0` **không tương đương** `is_current_country_or_territory = 1`: nó trả về **216** dòng vì còn `USSR` (`entity_type = historical` — không phải thực thể tổng hợp, nhưng cũng không phải quốc gia hiện tại). Dùng nhầm cột này để triển khai tiêu chí B7 "không có thực thể tổng hợp trong danh sách nước" sẽ đưa `USSR` vào bộ lọc quốc gia và làm Gate B2 mâu thuẫn với Gate B7.

### 2.3. Ý nghĩa bộ lọc năm

Bộ lọc năm được hiểu là “đến năm được chọn”:

- KPI và lát cắt dùng đúng năm được chọn;
- biểu đồ chuỗi thời gian hiển thị từ 2000 đến năm được chọn;
- không lọc trực tiếp `DimYear` làm chuỗi thời gian co lại còn một điểm.

### 2.4. Ý nghĩa công tắc hiện đại

Công tắc dùng bảng chọn không có quan hệ với hai giá trị:

- `RENEWABLE_TOTAL`: thủy điện + gió + mặt trời + nguồn tái tạo khác;
- `MODERN_WIND_SOLAR`: gió + mặt trời.

Công tắc không được triển khai bằng cách lọc thô `metric_key`, vì cách đó có thể phá quy tắc đủ thành phần và mẫu số xếp hạng.

### 2.5. Phạm vi quốc gia theo trang

- Trang 1: chọn quốc gia chỉ dùng để tô sáng hoặc so sánh; KPI khu vực vẫn là ASEAN-10.
- Trang 2: luôn cố định Việt Nam, không bị lựa chọn quốc gia từ trang khác ghi đè.
- Trang 3: lựa chọn quốc gia lọc các biểu đồ cấp nước; mẫu số khu vực, chỉ số tập trung và hạng vẫn giữ tập ASEAN-10.
- Mọi ô trực quan cố ý bỏ qua một bộ lọc phải ghi rõ phạm vi ngay trên tiêu đề hoặc phụ đề.

## 3. Trình tự triển khai và cổng chặn

## B0 — Đóng chính thức Phase 4

### Làm gì

1. Sửa câu sai về thứ hạng Thái Lan và Philippines trong:
   - `docs/NhatKyPhanTich.md`;
   - `docs/BaoCao.md`.
2. Kiểm tra lại C04 để xác định hình đang thể hiện đúng hạng 2/3 hay không.
3. Nếu C04 sai, sửa và dựng lại Phase 4; nếu C04 đúng, ghi nhận đây chỉ là lỗi văn bản.
4. Mở đủ 13 PNG ở kích thước 100% và hoàn thành `docs/Phase4_Review.md`.
5. Chạy lại ba lệnh:

```powershell
python python\04_test_contract.py
python python\04_test_publish.py
python python\04_verify_release.py
```

### Vì sao

Phase 4 khóa quy ước màu, trục, nhãn và thông điệp cho dashboard. Quy tắc dự án không cho phép chuyển phase khi phase trước chưa được nghiệm thu đầy đủ.

### Gate B0

- [x] Câu sai về Thái Lan/Philippines đã được sửa ở cả hai tài liệu.
- [x] C04 đã được đối chiếu với `03_fact_metrics.csv`.
- [x] 13/13 biểu đồ được người nghiệm thu đánh dấu `ĐẠT`.
- [x] Toàn bộ mục kiểm tra rủi ro và kiểm định trong `Phase4_Review.md` đã được đánh dấu.
- [x] Kết quả tổng thể có người nghiệm thu, ngày nghiệm thu và không còn ghi chú cần sửa.
- [x] Ba lệnh kiểm thử trả mã thoát 0.
- [x] `04_validation_results.csv` có đúng 38 mã duy nhất và không có dòng chặn khác `PASS`.

Chỉ khi Gate B0 đạt mới được bắt đầu B1.

## B1 — Khóa hợp đồng Phase 5 và đường cơ sở

### Làm gì

1. Khóa phiên bản phương pháp `phase5_v1`.
2. Ghi phiên bản Power BI Desktop thực tế dùng để dựng.
3. Khóa danh sách nguồn, bảng, quan hệ, phép đo, trang, nhóm trực quan và ma trận tương tác bộ lọc.
4. Khóa bộ số chuẩn tại mục 5 của tài liệu này.
5. Khóa danh sách sản phẩm bàn giao tại mục 6.

### Vì sao

PBIX là tệp nhị phân, khó review thay đổi. Hợp đồng bằng văn bản ngăn công thức, phạm vi hoặc hành vi bộ lọc bị thay đổi âm thầm trong quá trình dựng.

### Gate B1

- [ ] Tất cả mốc đầu vào ở mục 1 khớp kết quả hiện hữu.
- [ ] Ba lớp nguồn ở mục 2.1 được ghi rõ và không trộn vai trò.
- [ ] Có danh sách đủ 14 nhóm trực quan V01–V14.
- [ ] Có ma trận bộ lọc × trực quan với trạng thái `lọc / tô sáng / bỏ qua`.
- [ ] Mọi trường hợp bỏ qua bộ lọc đều có lý do nghiệp vụ.
- [ ] Không còn mục `TBD` hoặc quyết định chưa khóa.

## B2 — Nạp dữ liệu bằng Power Query

### Làm gì

1. Tạo tham số đường dẫn `pCleanFolder`.
2. Dùng `Power Query` (trình nạp và biến đổi dữ liệu) nạp đúng danh sách bảy CSV trong `output/clean/`.
3. Bật tải vào mô hình cho `FactEnergy`, `DimEntity`, `DimMetric`, `DimYear`.
4. Giữ `source_metric_catalog`, `missingness_audit`, `cleaning_audit` trong nhóm audit và tắt tải vào mô hình.
5. Khai báo tường minh kiểu dữ liệu của mọi cột. **`FactEnergy[value]` bắt buộc là `Decimal Number` (dấu phẩy động 64-bit); cấm `Fixed Decimal Number` / `Currency`.** Kiểu cố định cắt còn 4 chữ số thập phân, trong khi **36.030/89.075** giá trị có nhiều hơn 4 chữ số — trong đó 197 ô là ASEAN-10 và `World` nằm đúng trong cửa sổ 2000–2021. `year` là `Whole Number`; các cột cờ `is_*` khai báo nhất quán, không để Power BI tự đoán.
6. Không dùng cách lấy tự động mọi CSV trong thư mục.

### Vì sao

Danh sách tệp cố định ngăn tệp lạ lọt vào mô hình. Khai báo kiểu rõ ràng ngăn Power BI tự đoán sai năm, cờ logic hoặc giá trị số.

### Gate B2

- [ ] Làm mới dữ liệu không có lỗi.
- [ ] `FactEnergy` có đúng 89.075 dòng.
- [ ] `DimEntity` có đúng 256 dòng; `is_current_country_or_territory = 1` cho đúng **215** dòng; `is_asean = 1` cho đúng **10** dòng.
- [ ] `DimMetric` có đúng 16 dòng.
- [ ] `DimYear` có đúng 57 dòng từ 1965–2021; `is_main_asean_window = 1` cho đúng **22** dòng (2000–2021).
- [ ] Khóa `(entity, year, metric_key)` của fact không trùng.
- [ ] Không có năm 2022, giá trị âm hoặc lỗi chuyển kiểu.
- [ ] `FactEnergy[value]` mang kiểu `Decimal Number`, không phải `Fixed Decimal Number`.
- [ ] **Trước khi viết bất kỳ phép đo nào**, đọc thẳng từ bảng vừa nạp: tổng `generation_twh` bốn công nghệ của 10 nước ASEAN năm 2021 = `289,6557446`, của dòng `World` = `7.885,04005`. Lệch ở đây là lỗi kiểu dữ liệu, không phải lỗi DAX.

> **Đính chính con số 36.027.** Bản hợp đồng đầu tiên đếm bằng cách tìm dấu `.` trong văn bản CSV rồi đo số chữ số phía sau, nên bỏ sót ba giá trị ghi ở ký hiệu khoa học — Bulgaria 2007 `3e-05`, Nga 2010 `1e-05` và Việt Nam 2000 `2e-06`, đều thuộc `solar_capacity_gw`. Cả ba thật sự có 5–6 chữ số thập phân, nên con số đúng là **36.030**. Từ nay cả vế tham chiếu lẫn vế DAX đều dùng chung một vị từ `ROUND(value, 4) <> value`, để hai bên không thể lệch nhau vì cách ghi số nữa.
- [ ] Ba bảng audit không tạo quan hệ trong mô hình trình bày.

## B3 — Dựng mô hình sao và các bảng chọn

### Làm gì

1. Tạo đúng ba quan hệ ở mục 2.2.
2. Tạo `SelReportYear` gồm 2000–2021, mặc định 2021.
3. Tạo `SelMode` gồm `RENEWABLE_TOTAL` và `MODERN_WIND_SOLAR`, mặc định tổng tái tạo.
4. Tạo `SelBaseYear`, mặc định 2010, dùng cho chỉ số hóa.
5. Ẩn các cột kỹ thuật không dành cho người dùng báo cáo.
6. Tạo nhãn tiếng Việt và cột sắp xếp cho công nghệ, chỉ số và quốc gia khi cần.

### Vì sao

`DimMetric` là điều kiện bắt buộc để lọc công nghệ và chỉ số đúng. Các bảng chọn tách rời giúp điều khiển logic DAX mà không phá quan hệ mô hình hoặc làm chuỗi thời gian co lại.

### Gate B3

- [ ] Có đúng ba quan hệ chủ động `1 → *`.
- [ ] Cả ba quan hệ lọc một chiều từ dimension (bảng chiều) sang fact.
- [ ] Không có quan hệ nhiều-nhiều, lọc hai chiều hoặc đường lọc mơ hồ.
- [ ] Phía “1” không có khóa trùng hoặc khóa rỗng.
- [ ] `SelReportYear` có 22 giá trị và chỉ chọn một.
- [ ] `SelMode` có đúng hai giá trị và chỉ chọn một.
- [ ] Năm và chế độ mặc định lần lượt là 2021 và `RENEWABLE_TOTAL`.

## B4 — Viết và kiểm thử DAX nền tảng

### Làm gì

Viết các nhóm phép đo:

1. Sản lượng thủy điện, gió, mặt trời và nguồn tái tạo khác.
2. Tổng sản lượng điện tái tạo.
3. Tổng gió + mặt trời.
4. Tổng theo chế độ người dùng chọn.
5. Tỷ trọng quốc gia trong ASEAN.
6. Tỷ trọng ASEAN trong dòng `World` do nguồn báo cáo.
7. Thay đổi năm, YoY và CAGR.
8. Hạng ASEAN, hạng toàn cầu, số nước được xếp hạng và thay đổi hạng.
9. Các cặp TWh với tỷ trọng điện cho Việt Nam.

Mỗi phép đo phải được ghi vào danh mục với tối thiểu:

`measure_id, name, dax_expression, description_vi, format_string, unit, unit_stored, numerator, denominator, filter_behavior, blank_rule, source_metric_keys, question_ids, page_ids`.

Trong đó `unit_stored ∈ {ratio, pct, TWh, GW, count, rank, year, percentage_point, rank_change, STATUS_CODE}` ghi thang **lưu trữ** trong `03_fact_metrics.csv`, tách khỏi `format_string` là thang **hiển thị**. Đây là cột dùng để đối chiếu ở B10.

⚠️ Ba giá trị cuối được bổ sung sau khi rà `03_fact_metrics.csv`: `percentage_point` cho `q5_pct_point_change` (dùng ở V09), `rank_change` cho `modern_rank_gain` và `rank_gain_over_time` (dùng ở V03), `STATUS_CODE` cho `entry_status`, `material_entry_status` và `direction_relation` (dùng ở V12). Thiếu ba giá trị này thì các phép đo tương ứng không có `unit_stored` hợp lệ và không đối chiếu được ở B10.

### Quy tắc công thức bắt buộc

- **Quy tắc đủ thành phần chỉ áp cho `generation_twh`, và số thành phần co giãn theo phạm vi:**
  - một thực thể đơn lẻ (kể cả dòng `World`): tổng tái tạo cần đủ **4/4**, tổng hiện đại cần đủ **2/2**;
  - tổng hợp ASEAN-10: tổng tái tạo cần đủ **40/40** (10 nước × 4 công nghệ), tổng hiện đại cần đủ **20/20**, một công nghệ đơn lẻ cần đủ **10/10**.

  Đây chính là `component_count` / `required_component_count` mà B10 bắt đối chiếu với `03_fact_metrics.csv`. Viết cứng "4/4" cho mức khu vực sẽ vẫn trả ra số khi bộ lọc quốc gia làm thiếu ô, thay vì để trống.
- **`share_electricity_pct` KHÔNG dùng quy tắc đủ thành phần của tổng.** `RENEWABLE_TOTAL` lấy nguyên cột nguồn `renewables_share_electricity_pct` (**1/1, pass-through**), tuyệt đối không cộng bốn thành phần; `MODERN_WIND_SOLAR` = `wind_share_electricity_pct` + `solar_share_electricity_pct` (**2/2**). Cộng bốn thành phần cho Việt Nam 2021 ra `42,513379%` thay vì `42,578747%` đã khóa ở §5.3. Mô hình 16 chỉ số **không có** `other_renewables_share_electricity_pct`, nên bản bốn thành phần cũng không dựng được.
- Dùng `complete-case` (chỉ tính khi đủ thành phần), không cộng bỏ qua ô thiếu.
- Số 0 là quan sát hợp lệ; `BLANK` (giá trị trống có chủ đích) không được đổi thành 0.
- YoY/CAGR để trống khi mẫu số bằng 0; cuối kỳ bằng 0 thì `-1` vẫn hợp lệ.
- **Thang lưu trữ — bắt buộc khai báo cho từng phép đo.** `pct` lưu ở thang 0–100; `ratio` lưu ở thang 0–1. Trong `03_fact_metrics.csv` **chỉ `share_electricity_pct` mang `unit = pct`**; toàn bộ `country_share_asean`, `asean_share_world`, `technology_share`, `top1_share`, `top3_share`, `top3_positive_growth_share`, `positive_growth_share`, `hhi`, `gini`, `yoy`, `cagr` đều mang `unit = ratio`. Việc ×100 chỉ được nằm ở `format_string`, không nằm trong biểu thức. Đối chiếu dung sai `1e-9` phải thực hiện **trên thang lưu trữ** — so một measure ratio `0,671023268910` với đích hiển thị `67,102326891` sẽ lệch `66,43`, không phải sai số nhỏ.
- Tỷ trọng ASEAN/thế giới dùng dòng `World`, không dùng tổng các quốc gia hiện có.
- **Hạng — hai cohort khác nhau, không dùng chung một quy tắc:**
  - `asean_rank`: xếp trên tập ASEAN-10 cố định `DimEntity[is_asean] = 1` (`population_n = 10`);
  - `global_rank`: xếp trên tập `DimEntity[is_current_country_or_territory] = 1` (`population_n = 215`), chỉ gồm nước đủ thành phần trong năm đó. Mẫu số hiển thị là `ranked_n` và **thay đổi theo năm lẫn theo chế độ** — không được viết cứng 205/209, xem lưới ở §5.3;
  - cả hai: giữ đồng hạng theo hạng nhỏ nhất và bỏ qua hạng kế tiếp (tương đương `RANKX(…, , , Skip)`, mặc định của DAX), giữ số 0, loại giá trị trống.
- Nếu tổng toàn phạm vi bằng 0, hạng phải trống với trạng thái `ZERO_SCOPE_TOTAL`.

### Vì sao

Đây là nhóm công thức quyết định tính đúng của toàn dashboard. Sai quy tắc thành phần, mẫu số, số 0 hoặc đơn vị có thể tạo kết quả trông hợp lý nhưng sai nghiệp vụ.

### Gate B4

- [ ] Mọi phép đo dùng trong Trang 1–2 có một dòng đầy đủ trong danh mục.
- [ ] Không có tên phép đo trùng.
- [ ] Mọi tỷ lệ ghi rõ tử số, mẫu số và đơn vị lưu trữ.
- [ ] Năm 2000, hiện đại ASEAN bằng 0 nhưng hạng là `NOT_DEFINED / ZERO_SCOPE_TOTAL`.
- [ ] Không có `NaN`, vô hạn hoặc số 0 được tạo từ dữ liệu thiếu.
- [ ] Mọi ca chuẩn của Trang 1–2 tại mục 5 khớp trong dung sai quy định.

## B5 — Viết và kiểm thử DAX chẩn đoán nâng cao

### Làm gì

1. Tạo chỉ số hóa gốc 100, mặc định năm gốc 2010.
2. Tính năm đầu dương, năm đầu đạt 0,05 TWh và trạng thái kiểm duyệt.
3. Tính top-1, top-3, HHI và Gini.
4. Tính đóng góp trong tổng phần tăng dương.
5. Tính hệ số công suất xấp xỉ:

   `DIVIDE(generation_twh, capacity_gw × 8,76)`

   Phạm vi: ASEAN-10, 2000–2021, và **chỉ giữ cặp có `capacity_gw > 0` cùng `generation_twh` không rỗng**. Chính bộ lọc này tạo ra con số 104: join thô trong cửa sổ cho **132** cặp (gió 44, mặt trời 88), trong đó 28 cặp có công suất bằng 0 (gió 11, mặt trời 17) bị loại. Đã kiểm: không cặp nào bị loại có sản lượng > 0, nên bộ lọc không làm mất quan sát nào. Bắt buộc dùng `DIVIDE()` trả `BLANK`, không dùng toán tử `/`.

### Vì sao

Các chỉ số này có nhiều trường hợp biên: năm gốc bằng 0, đồng hạng ở vị trí thứ ba, kiểm duyệt trái/phải và độ phủ công suất hạn chế. Cần kiểm thử riêng trước khi đưa vào trang chẩn đoán.

### Gate B5

- [ ] Năm gốc lớn hơn năm báo cáo hoặc giá trị gốc bằng 0 trả trống kèm lý do.
- [ ] Top-3 luôn lấy đúng ba nước; không dùng điều kiện “hạng ≤ 3”.
- [ ] Năm 2000 hiện đại: top-1, top-3, HHI và Gini đều `NOT_DEFINED / ZERO_DENOMINATOR`.
- [ ] Bảng gia nhập có đúng **40 dòng khóa** (10 nước × 4 công nghệ); mỗi dòng mang **2 trạng thái** — `entry_status` (ngưỡng dương) và `material_entry_status` (ngưỡng 0,05 TWh) — tức **80 giá trị trạng thái**, không phải 40.
- [ ] Việt Nam–thủy điện không bị ghi giả là gia nhập năm 2000.
- [ ] Việt Nam–mặt trời dương lần đầu năm 2010 và vượt ngưỡng vật chất 0,05 TWh lần đầu năm 2018 (giá trị năm 2018 là `0,10 TWh`; chuỗi không bao giờ nhận đúng giá trị 0,05).
- [ ] Brunei–mặt trời giữ trạng thái chưa quan sát đến 2021; không thay năm sự kiện bằng 2021.
- [ ] Hệ số công suất có đúng 104 cặp sau bộ lọc `capacity_gw > 0`: gió 33 và mặt trời 71. Đếm trên số điểm có giá trị, không đếm số dòng bảng join (132).
- [ ] Các giá trị hệ số công suất nằm trong `0–0,3257639133464354`.

## B6 — Dựng khung ba trang và hàng bộ lọc

### Làm gì

Tạo đúng ba trang:

1. `01_TongQuan_ASEAN`;
2. `02_VietNam_ChuyenSau`;
3. `03_SoSanh_ChanDoan`.

Hàng bộ lọc trên cùng gồm:

- năm báo cáo;
- quốc gia;
- công nghệ;
- chỉ số;
- công tắc “chỉ NLTT hiện đại”.

Thêm nút đặt lại và thanh điều hướng ba trang.

### Ma trận hành vi bắt buộc

- Năm và chế độ được đồng bộ trên cả ba trang.
- KPI/lát cắt dùng đúng năm chọn; chuỗi thời gian dùng 2000 đến năm chọn.
- Trang 1: quốc gia chỉ tô sáng/so sánh; KPI khu vực bỏ qua lựa chọn này.
- Trang 2: quốc gia bị khóa ở Việt Nam.
- Trang 3: quốc gia lọc biểu đồ cấp nước; các mẫu số khu vực vẫn giữ ASEAN-10.
- Công nghệ chỉ tác động các biểu đồ công nghệ; không phá tổng 4/4 hoặc 2/2.
- Chỉ số không được tạo “tỷ trọng điện ASEAN” bằng cách cộng hoặc lấy trung bình tỷ trọng các nước.

### Quy ước trực quan kế thừa Phase 4

- Thủy điện: `#0072B2`.
- Gió: `#009E73`.
- Mặt trời: `#E69F00`.
- Nguồn tái tạo khác: `#CC79A7`.
- Tổng tái tạo: `#374151`.
- Gió + mặt trời và màu nhấn Việt Nam: `#D55E00`.
- Không dùng trục kép hoặc biểu đồ tròn.
- Màu quốc gia không thay đổi theo thứ hạng.
- Nhãn trực tiếp chỉ dùng ở điểm cuối hoặc điểm cần nhấn mạnh.

### Gate B6

- [ ] Có đúng ba trang và thanh điều hướng hoạt động.
- [ ] Hàng bộ lọc nằm cùng vị trí trên cả ba trang.
- [ ] Ma trận tương tác ghi rõ `lọc / tô sáng / bỏ qua` cho từng nhóm trực quan.
- [ ] Mọi trường hợp bỏ qua bộ lọc có nhãn phạm vi rõ ràng.
- [ ] Nút đặt lại đưa báo cáo về năm 2021, tổng NLTT và lựa chọn mặc định.
- [ ] Chân trang mẫu có nguồn, cửa sổ 2000–2021, lý do loại 2022 và ghi chú loại thực thể tổng hợp.

## B7 — Dựng Trang 1: Tổng quan Đông Nam Á

### Làm gì

- V01: hàng KPI khu vực.
- V02: cơ cấu sản lượng điện tái tạo theo bốn công nghệ.
- V03: so sánh hạng tổng tái tạo với gió + mặt trời.
- V04: ASEAN và thế giới trên hai panel (ô biểu đồ) riêng, không dùng trục kép.

### Vì sao

Trang 1 phải trả lời đồng thời quy mô, cơ cấu, xếp hạng và bối cảnh thế giới mà không trộn các mẫu số hoặc đơn vị khác nhau.

### Gate B7

- [ ] Năm 2021: ASEAN `289,6557446 TWh`.
- [ ] Năm 2021: World `7.885,04005 TWh`.
- [ ] Năm 2021: ASEAN/World `3,67348476055%`.
- [ ] Cơ cấu 2021 gồm thủy điện `185,58`, nguồn khác `61,3457446`, mặt trời `34,43`, gió `8,30 TWh`.
- [ ] Tổng bốn thành phần khớp KPI khu vực: `185,58 + 61,3457446 + 34,43 + 8,30 = 289,6557446`, phần dư đúng bằng `0`.
- [ ] Đổi sang hiện đại năm 2021 cho đúng thay đổi hạng: Singapore `+4`, Indonesia `-4`, Lào `-5`.
- [ ] Thái Lan hiện đại hạng 2 và Philippines hạng 3.
- [ ] Không có thực thể tổng hợp trong danh sách nước.
- [ ] Mỗi nhóm trực quan truyền đạt đúng một thông điệp.

## B8 — Dựng Trang 2: Việt Nam chuyên sâu

### Làm gì

- V05: hàng KPI Việt Nam.
- V06: chuỗi thời gian bốn công nghệ.
- V07: sản lượng TWh và tỷ trọng điện trên hai panel riêng.
- V08: vị thế Việt Nam trong ASEAN và thế giới.
- V09: bảng chi tiết theo năm.

### Vì sao

Trang 2 phải giữ phạm vi Việt Nam ổn định, đồng thời phân biệt quy mô sản lượng, tỷ trọng điện và hạng để tránh suy diễn một đại lượng từ đại lượng khác.

### Gate B8

- [ ] Việt Nam 2021: tổng `104,2180361 TWh`.
- [ ] Việt Nam 2021: gió + mặt trời `28,16 TWh`.
- [ ] Tỷ trọng trong ASEAN: tổng `35,9799651976%`, hiện đại `65,9021764568%`.
- [ ] Hạng toàn cầu: tổng `16/205`, hiện đại `17/209`.
- [ ] Tỷ trọng điện Việt Nam 2021: tổng `42,578747%`, hiện đại `11,5046779%`.
- [ ] TWh và phần trăm điện không dùng chung trục.
- [ ] Tổng tái tạo đánh dấu đúng hai năm ngược hướng 2003 và 2014; hiện đại đúng năm 2016.
- [ ] Lựa chọn quốc gia ở trang khác không làm Trang 2 rời khỏi Việt Nam.
- [ ] Không suy diễn nguyên nhân từ quan hệ giữa TWh và tỷ trọng điện.

## B9 — Dựng Trang 3: So sánh và chẩn đoán

### Làm gì

- V10: small multiples (lưới biểu đồ nhỏ đồng dạng) cho 10 nước.
- V11: xu hướng chỉ số hóa gốc 100.
- V12: độ trễ gia nhập và trạng thái kiểm duyệt.
- V13: top-3, HHI, Gini và đóng góp tăng dương.
- V14: hệ số công suất xấp xỉ và cảnh báo độ phủ.

Nếu không đủ không gian đọc, dùng bộ điều hướng dấu trang trong chính Trang 3; không tạo thêm trang trình bày thứ tư.

### Vì sao

Trang này phục vụ so sánh quỹ đạo và kiểm tra phân phối. Các chỉ số chẩn đoán phải được tách đúng ý nghĩa để không dùng mức tập trung thay cho đóng góp tăng trưởng hoặc dùng chỉ số công suất hạn chế để xếp hạng khu vực.

### Gate B9

- [ ] Lưới chuỗi có đúng 10 nước và 220 điểm cho một chuỗi đủ 22 năm.
- [ ] Chỉ số hóa không tạo vô hạn khi giá trị năm gốc bằng 0.
- [ ] Có đúng **40 dòng khóa** gia nhập và **80 giá trị trạng thái** (hai họ ngưỡng, xem Gate B5); không biến kiểm duyệt thành năm giả.
- [ ] Năm 2021, top-3 tổng NLTT bằng `67,102326891%`.
- [ ] Năm 2021, top-3 hiện đại bằng `92,2536859349%`.
- [ ] HHI/Gini tổng bằng `0,207886216029 / 0,529218182611`.
- [ ] HHI/Gini hiện đại bằng `0,480403925201 / 0,771284811608`.
- [ ] Đóng góp tăng dương Việt Nam 2010–2021 — metric `positive_growth_share`, `subject_key = Vietnam`, `period_key = I2010_2021`, `denominator_basis = GROSS_POSITIVE_ADDITION`: hiện đại `65,985915493%`, tổng `42,3780539369%` (lưu ở thang ratio: `0,65985915493` và `0,423780539369`).
- [ ] Hệ số công suất chỉ hiển thị 2 nước cho gió và 4 nước cho mặt trời.
- [ ] Chú thích ghi rõ “công suất cuối năm”, “chỉ báo xấp xỉ” và không kết luận hiệu quả kỹ thuật.

## B10 — Kiểm thử tích hợp và tạo bằng chứng phát hành

### Làm gì

1. Thử cả ba trang với các năm 2000, 2010 và 2021.
2. Thử cả hai chế độ tổng tái tạo và gió + mặt trời.
3. Thử các lựa chọn quốc gia, công nghệ và chỉ số theo ma trận tương tác.
4. Chạy truy vấn DAX nghiệm thu và xuất kết quả dạng TSV.
5. Đối chiếu kết quả với `03_fact_metrics.csv` và workbook Phase 3–4.
6. Làm mới hai lần, đóng và mở lại PBIX.
7. Xuất ba trang mặc định thành PDF để kiểm bố cục.
8. Ghi SHA-256 của PBIX phát hành.

### Vì sao

Kiểm đúng từng phép đo riêng lẻ chưa chứng minh các trang và bộ lọc hoạt động đúng khi ghép lại. PBIX cũng cần bằng chứng bên ngoài để người review kiểm tra mà không phụ thuộc hoàn toàn vào thao tác thủ công.

### Gate B10

- [ ] Đổi 2021 → 2010 → 2000 làm cả ba trang đổi tiêu đề, KPI và dữ liệu liên quan; không trang nào giữ năm cũ.
- [ ] Chuỗi thời gian dừng ở năm chọn thay vì co lại còn một điểm.
- [ ] Bật/tắt hiện đại năm 2021 làm thứ tự hạng đổi đúng.
- [ ] Mọi trường hợp không xác định hiển thị trống kèm lý do.
- [ ] Không có `NaN`, vô hạn hoặc số 0 giả.
- [ ] Giá trị thô khớp trong dung sai `1e-9`.
- [ ] Số đếm, hạng và trạng thái khớp tuyệt đối.
- [ ] Giá trị hiển thị được kiểm riêng sau khi áp dụng định dạng và làm tròn.
- [ ] Làm mới hai lần cho cùng kết quả; đóng/mở lại không mất quan hệ hoặc bộ lọc mặc định.
- [ ] 17 CSV nguồn và đầu ra Phase 2–4 giữ nguyên mã băm.
- [ ] Mỗi ô trực quan hoàn thành trong tối đa 2 giây và mỗi trang tối đa 5 giây trên máy hiện tại; kết quả được ghi từ công cụ phân tích hiệu năng của Power BI.
- [ ] PDF đủ ba trang, không có chữ chồng, cắt hoặc vượt khung.
- [ ] PBIX đã được ghi SHA-256.

## B11 — Nghiệm thu tổng thể Phase 5

### Làm gì

1. Hoàn thiện `docs/Phase5_Review.md` theo ba trạng thái:
   - `CHỜ NGHIỆM THU`;
   - `CẦN SỬA`;
   - `ĐẠT`.
2. Cập nhật mục 1.5c trong `docs/BaoCao.md`.
3. Cập nhật phần Phase 5 trong `docs/NhatKyPhanTich.md`.
4. Người nghiệm thu mở PBIX, làm mới và thực hiện lại các ca bắt buộc.
5. Chỉ sau khi ký nhận mới cập nhật Phase 5 trong `PLAN.md` thành “ĐÃ HOÀN THÀNH”.

### Vì sao

Kiểm định số không thay thế kiểm tra tương tác, bố cục và khả năng đọc. Ngược lại, kiểm tra bằng mắt không chứng minh DAX và mẫu số đúng. Nghiệm thu tổng thể phải bao phủ cả hai lớp.

### Gate B11 — điều kiện ký `ĐẠT`

- [ ] B0–B10 đều `ĐẠT`.
- [ ] Có đúng ba trang và đủ V01–V14.
- [ ] Mọi KPI có DAX và định nghĩa nghiệp vụ truy được.
- [ ] Toàn bộ mã kiểm thử trong danh sách khóa đều `PASS`; không chỉ kiểm tổng số.
- [ ] Bộ lọc năm, quốc gia, công nghệ, chỉ số và hiện đại hoạt động đúng ma trận.
- [ ] Chân trang đủ nguồn, phạm vi, loại năm 2022 và loại thực thể tổng hợp.
- [ ] Người nghiệm thu đã thử các năm 2000, 2010, 2021 và hai chế độ.
- [ ] Người nghiệm thu đã kiểm PDF ở kích thước 100%.
- [ ] Phiếu có tên người nghiệm thu, ngày, phiên bản Power BI, dấu vân tay đầu vào và SHA-256 PBIX.
- [ ] Không còn ghi chú cần sửa.

Chỉ sau khi Gate B11 đạt mới được mở Phase 6.

## 4. Danh mục 14 nhóm trực quan đã khóa

| ID | Trang | Nội dung |
|---|---|---|
| V01 | Trang 1 | Hàng KPI khu vực |
| V02 | Trang 1 | Cơ cấu ASEAN theo bốn công nghệ |
| V03 | Trang 1 | So sánh hạng tổng NLTT và gió + mặt trời |
| V04 | Trang 1 | ASEAN trong bối cảnh World, tách panel |
| V05 | Trang 2 | Hàng KPI Việt Nam |
| V06 | Trang 2 | Chuỗi thời gian bốn công nghệ Việt Nam |
| V07 | Trang 2 | TWh và tỷ trọng điện trên hai panel |
| V08 | Trang 2 | Vị thế Việt Nam trong ASEAN và thế giới |
| V09 | Trang 2 | Bảng chi tiết theo năm |
| V10 | Trang 3 | Small multiples 10 nước |
| V11 | Trang 3 | Chỉ số hóa gốc 100 |
| V12 | Trang 3 | Độ trễ gia nhập và trạng thái kiểm duyệt |
| V13 | Trang 3 | Mức tập trung và đóng góp tăng dương |
| V14 | Trang 3 | Hệ số công suất xấp xỉ và độ phủ |

## 5. Bộ số chuẩn nghiệm thu

### 5.1. KPI khu vực theo năm

Các tỷ lệ trong bảng đã được đổi từ tỷ số 0–1 sang phần trăm hiển thị.

| Năm | ASEAN tổng NLTT | Gió + mặt trời | World tổng NLTT | ASEAN/World | Số nước đạt ≥0,05 TWh: tổng / hiện đại |
|---:|---:|---:|---:|---:|---:|
| 2000 | 72,800904 TWh | 0 TWh | 2.854,49 TWh | 2,55039968611% | 8 / 0 |
| 2010 | 111,2779545 TWh | 0,13 TWh | 4.182,39 TWh | 2,6606307518% | 8 / 2 |
| 2021 | 289,6557446 TWh | 42,73 TWh | 7.885,04005 TWh | 3,67348476055% | 9 / 8 |

Ca biên bắt buộc: năm 2000, chế độ hiện đại có tổng bằng 0; hạng ASEAN, top-1, top-3, HHI và Gini phải không xác định.

### 5.2. Xếp hạng ASEAN năm 2021

| Hạng | Tổng NLTT | Chỉ gió + mặt trời |
|---:|---|---|
| 1 | Việt Nam | Việt Nam |
| 2 | Indonesia | Thái Lan |
| 3 | Malaysia | Philippines |
| 4 | Lào | Malaysia |
| 5 | Thái Lan | Singapore |
| 6 | Philippines | Indonesia |
| 7 | Myanmar | Campuchia |
| 8 | Campuchia | Myanmar |
| 9 | Singapore | Lào |
| 10 | Brunei | Brunei |

### 5.3. Việt Nam

| Năm | Tổng NLTT | Hiện đại | % điện NLTT | % điện hiện đại | Hạng ASEAN tổng / hiện đại |
|---:|---:|---:|---:|---:|---|
| 2000 | 14,55 TWh | 0 TWh | 54,781628% | 0% | 3 / không xác định |
| 2010 | 28,625 TWh | 0,05 TWh | 31,203663% | 0,0545137375% | 2 / 2 |
| 2021 | 104,2180361 TWh | 28,16 TWh | 42,578747% | 11,5046779% | 1 / 1 |

**Thang lưu trữ của bảng trên:** `% điện NLTT` và `% điện hiện đại` là `share_electricity_pct`, **lưu sẵn ở thang 0–100** nên trích nguyên, không nhân thêm. Hai tỷ trọng ASEAN bên dưới là `country_share_asean`, **lưu ở thang ratio 0–1** (`0,359799651976` và `0,659021764568`) và đã ×100 để hiển thị. Hai loại số này đứng cạnh nhau nhưng không cùng thang.

Ô `2010 · Hiện đại = 0,05 TWh` là gió `0,04` + mặt trời `0,01`; nó **không** liên quan tới ngưỡng vật chất 0,05 TWh ở §5.5.

Năm 2021:

- Việt Nam chiếm `35,9799651976%` tổng NLTT ASEAN.
- Việt Nam chiếm `65,9021764568%` gió + mặt trời ASEAN.
- Hạng toàn cầu tổng NLTT: `16/205`.
- Hạng toàn cầu hiện đại: `17/209`.

**Mẫu số hạng toàn cầu đổi theo năm và theo chế độ.** `population_n = 215` ở mọi ô, nhưng mẫu số hiển thị là `ranked_n` — số nước đủ thành phần trong năm đó — nên phải tính động, tuyệt đối không viết cứng 205/209. B10 bắt kiểm đúng ba năm dưới đây:

| Năm | Hạng / `ranked_n` tổng NLTT | Hạng / `ranked_n` hiện đại |
|---:|---|---|
| 2000 | 31 / 209 | 40 / 212 |
| 2010 | 25 / 211 | 53 / 214 |
| 2021 | **16 / 205** | **17 / 209** |

### 5.4. Mức tập trung

| Năm / thước đo | Top-1 | Top-3 | HHI | Gini |
|---|---:|---:|---:|---:|
| 2000 tổng NLTT | 26,9227426077% | 73,5155720044% | 0,204478848183 | 0,555271560914 |
| 2000 hiện đại | Không xác định | Không xác định | Không xác định | Không xác định |
| 2010 tổng NLTT | 31,1202700981% | 73,15465167% | 0,208080520146 | 0,550964517864 |
| 2010 hiện đại | 46,1538461538% | 100% | 0,384615384615 | 0,761538461538 |
| 2021 tổng NLTT | 35,9799651976% | 67,102326891% | 0,207886216029 | 0,529218182611 |
| 2021 hiện đại | 65,9021764568% | 92,2536859349% | 0,480403925201 | 0,771284811608 |

⚠️ **Bảng này trộn hai cách hiển thị trên cùng một dòng.** Cả bốn chỉ số đều mang `unit = ratio` (thang 0–1) trong `03_fact_metrics.csv`; Top-1 và Top-3 đã được ×100 và gắn dấu `%`, còn HHI và Gini để nguyên thang ratio. Khi viết `format_string` phải theo đúng cách chia này, và đối chiếu `1e-9` luôn thực hiện trên thang lưu trữ. Ví dụ 2021 tổng NLTT lưu là `0,359799651976 / 0,67102326891 / 0,207886216029 / 0,529218182611`.

Top-1 năm 2021 trùng đúng với tỷ trọng Việt Nam ở §5.3 (`35,9799651976%` và `65,9021764568%`) vì cùng mẫu số `ASEAN_SUM_10` và Việt Nam đứng hạng 1 ở cả hai chế độ — đây là **một đại lượng**, không dựng thành hai phép đo riêng.

### 5.5. Gia nhập công nghệ

Bảng gia nhập có **40 dòng khóa** (10 nước × 4 công nghệ), mỗi dòng mang **hai họ trạng thái độc lập** — `entry_status` theo ngưỡng dương và `material_entry_status` theo ngưỡng 0,05 TWh — tức **80 giá trị trạng thái**. Các số đếm dưới đây liệt kê cả hai họ. Phase 4 (C11) chỉ dựng họ `material`, nên V12 mở rộng thêm họ dương.

Số đếm toàn ASEAN-10:

- Thủy điện: 8 `ACTIVE_AT_WINDOW_START`, 2 `NOT_OBSERVED_BY_2021`.
- Nguồn khác: 5 đã hoạt động từ đầu, 4 chuyển tiếp quan sát được, 1 chưa xuất hiện.
- Mặt trời: 9 chuyển tiếp dương, 1 chưa xuất hiện; theo ngưỡng 0,05 TWh là 8 chuyển tiếp và 2 chưa đạt.
- Gió: 4 chuyển tiếp, 6 chưa xuất hiện; theo ngưỡng 0,05 TWh cũng là 4/6.

Ca chuẩn:

- Việt Nam–thủy điện: đã hoạt động ở đầu cửa sổ; năm gia nhập và độ trễ phải trống/kiểm duyệt.
- Việt Nam–mặt trời: dương lần đầu 2010, đạt 0,05 TWh năm 2018, `lag_from_2000 = 10`.
- Brunei–mặt trời: `NOT_OBSERVED_BY_2021` và `NOT_MATERIAL_BY_2021`; không thay năm sự kiện bằng 2021.
- Campuchia–nguồn khác: chuyển tiếp chính xác năm 2006, độ trễ 6 năm.

### 5.6. Hệ số công suất xấp xỉ

- Phạm vi và quy tắc chọn cặp: ASEAN-10, 2000–2021, **chỉ giữ cặp có `capacity_gw > 0` và `generation_twh` không rỗng**. Join thô cho 132 cặp; 28 cặp công suất bằng 0 (gió 11, mặt trời 17) bị loại và không cặp nào trong số đó có sản lượng > 0.
- Tổng cộng 104 cặp sản lượng–công suất sau khi áp quy tắc trên.
- Gió: 33 quan sát của Philippines 17 năm và Thái Lan 16 năm.
- Mặt trời: 71 quan sát của Malaysia 15 năm, Philippines 18 năm, Thái Lan 16 năm và Việt Nam 22 năm.
- Giá trị toàn bộ nằm trong `0–0,3257639133464354`, tương đương tối đa `32,5763913346%`.
- Đây là chỉ báo dùng công suất cuối năm, không phải thước đo hiệu quả kỹ thuật.

### 5.7. Quy tắc dung sai

- Số đếm, hạng, khóa và trạng thái: phải khớp tuyệt đối.
- **Đối chiếu luôn thực hiện trên thang lưu trữ của `03_fact_metrics.csv`, không phải thang hiển thị.** Chỉ `share_electricity_pct` mang `unit = pct` (0–100); mọi chỉ số tỷ lệ còn lại mang `unit = ratio` (0–1). Danh mục phép đo ở B4 phải ghi `unit_stored` cho từng dòng. So một measure ratio với đích đã ×100 sẽ lệch hàng chục đơn vị, không phải sai số làm tròn.
- Giá trị số thô: sai khác tuyệt đối không vượt `1e-9` so với `03_fact_metrics.csv`, trừ khi hợp đồng của phép đo khóa dung sai khác.
- Giá trị hiển thị: kiểm riêng sau khi áp dụng đúng quy tắc định dạng và làm tròn.
- Không dùng giá trị đã làm tròn trên hình Phase 4 làm chuẩn thay cho giá trị thô Phase 3.

## 6. Sản phẩm bàn giao Phase 5

Sản phẩm bắt buộc:

```text
PHASE5.md
powerbi/
├── ASEAN_Renewables.pbix
├── ASEAN_Renewables.pbip              (dự án dạng văn bản — nguồn để dựng .pbix)
├── ASEAN_Renewables.SemanticModel/    (TMDL: bảng, quan hệ, phép đo)
├── ASEAN_Renewables.Report/           (PBIR: ba trang, V01–V14)
├── README.md
├── DAX_Measures.md
├── 05_acceptance.dax
└── review/
    └── 05_dashboard_default.pdf
python/
├── phase5_contract.py
├── 05_expected.py
└── 05_validate.py
output/stats/
├── 05_expected_values.csv
├── 05_test_results.tsv
└── 05_validation_results.csv
docs/
├── Phase5_Review.md
├── BaoCao.md
└── NhatKyPhanTich.md
```

Vai trò:

- `ASEAN_Renewables.pbix`: sản phẩm nộp chính.
- `ASEAN_Renewables.pbip` + hai thư mục `.SemanticModel/` và `.Report/`: dự án dạng văn bản dùng để dựng ra `.pbix`. Đây là thứ Gate B1 vốn phải bù bằng hợp đồng giấy vì PBIX là tệp nhị phân — có PBIP thì `git diff` đọc được mọi thay đổi mô hình và phép đo.
- `phase5_contract.py`: hằng số khóa dùng chung cho harness kiểm chứng, theo đúng khuôn `phase4_contract.py`.
- `05_expected.py`: tính lại toàn bộ đích nghiệm thu ở mục 5 từ `output/clean/` và `03_fact_metrics.csv`, ghi ra `05_expected_values.csv`. Chạy được độc lập, không cần Power BI.
- `05_validate.py`: ghép `05_test_results.tsv` với `05_expected_values.csv` theo `test_id`, so trên thang lưu trữ và ghi `05_validation_results.csv`. Không có script này thì dung sai `1e-9` ở B10 phải kiểm bằng mắt trên hàng trăm ô.
- `README.md`: phiên bản Power BI, tham số đường dẫn, cách làm mới và quy ước trang/bộ lọc.
- `DAX_Measures.md`: công thức và định nghĩa nghiệp vụ của mọi phép đo dùng trong dashboard.
- `05_acceptance.dax`: các truy vấn DAX dùng để lấy kết quả nghiệm thu.
- `05_test_results.tsv`: kết quả thô xuất từ Power BI, giữ đủ bộ lọc, giá trị mong đợi, giá trị thực tế và trạng thái.
- `05_validation_results.csv`: kết quả đối chiếu theo mã kiểm thử duy nhất.
- `05_dashboard_default.pdf`: bằng chứng bố cục tĩnh của đủ ba trang.
- `Phase5_Review.md`: phiếu nghiệm thu tương tác, trực quan và tổng thể.

Có thể lưu thêm PBIP (dự án Power BI dạng văn bản) để thuận tiện review mô hình và DAX. Tuy nhiên PBIX vẫn là sản phẩm bắt buộc theo `PLAN.md`; PBIP không được trở thành điều kiện chặn nếu môi trường không hỗ trợ ổn định.

## 7. Điều kiện mở Phase 6

Phase 6 chỉ được mở khi:

1. `docs/Phase5_Review.md` có kết quả tổng thể `ĐẠT`.
2. B0–B11 đều có bằng chứng hoàn thành.
3. PBIX mở và làm mới không lỗi.
4. Toàn bộ mã kiểm thử trong danh sách khóa đều `PASS`.
5. Ba trang qua kiểm tra tương tác và trực quan.
6. Đầu ra Phase 1–4 và 17 CSV nguồn không thay đổi.
7. Mục 1.5c của báo cáo và nhật ký Phase 5 đã được cập nhật.
8. Phase 5 trong `PLAN.md` đã được đánh dấu “ĐÃ HOÀN THÀNH” sau khi ký nhận, không phải trước đó.

## 8. Dùng MCP Power BI

Máy này có sẵn MCP `@microsoft/powerbi-modeling-mcp` phiên bản `0.5.0-beta.12`. Mục này quy định dùng nó ở đâu và **không** dùng ở đâu.

### 8.1. Giới hạn quyết định: MCP chỉ làm mô hình, không làm báo cáo

Bộ tool của MCP là `table_operations`, `column_operations`, `measure_operations`, `relationship_operations`, `database_operations` (ExportTMDL/TMSL), `dax_query_operations`, cùng các nhóm role/hierarchy/refresh/trace. **Không có tool nào cho trang, ô trực quan, slicer, dấu trang, nút hay chân trang.** Toàn bộ lớp trình bày của Phase 5 vẫn phải dựng tay trong Power BI Desktop.

### 8.2. Trình tự bắt buộc: có `.pbix` trước, mới nối MCP

MCP **không tạo được mô hình từ số không** — nó phải bám vào một semantic model đang tồn tại. Trình tự:

1. Mở Power BI Desktop → `Get Data → Text/CSV`.
2. Nạp bốn bảng `fact_energy`, `dim_entity`, `dim_metric`, `dim_year` theo đúng B2.
3. `Save as` → `powerbi\ASEAN_Renewables.pbix`.
4. **Giữ Power BI Desktop mở.**
5. Nối MCP: *"Connect to `ASEAN_Renewables` in Power BI Desktop"*.

Bước 1–3 là B2 và **phải làm tay**. Không đẩy Power Query / M partition qua MCP: lớp mashup do Desktop sở hữu, ghi partition qua XMLA vào Desktop là vùng không đảm bảo.

### 8.3. Chia việc theo bước

| Bước | Ai làm | Ghi chú |
|---|---|---|
| B0, B1 | Người | Sửa tài liệu, khóa hợp đồng |
| **B2** | **Tay trong Desktop** | Nạp CSV, khai kiểu, lưu `.pbix` |
| **B3** | **MCP** | Ba quan hệ, bảng chọn rời, ẩn cột kỹ thuật |
| **B4** | **MCP** | Toàn bộ DAX nền tảng |
| **B5** | **MCP** | DAX chẩn đoán: chỉ số hóa, HHI, Gini, hệ số công suất |
| B6–B9 | Tay | Trang, 14 nhóm trực quan, hàng bộ lọc, chân trang |
| **B10** | **MCP** | Chạy `05_acceptance.dax` qua `dax_query_operations`, xuất `05_test_results.tsv` |
| B11 | Người | Nghiệm thu tương tác và trực quan |

B10 là chỗ tiết kiệm lớn nhất: đối chiếu hàng trăm ô bằng truy vấn DAX thay vì bấm tay.

### 8.4. Cạm bẫy vận hành

- **Lưu `.pbix` trước và sau mỗi lượt MCP ghi.** Không sửa tay song song khi MCP đang mở kết nối. Đây là bản sao của bẫy *Navicat giữ `.db`* mà `PLAN.md` đã ghi cho Phase 2.
- `--authmode=interactive` chỉ cần cho Fabric; nối vào Desktop cục bộ không cần đăng nhập.
- Đăng ký MCP phải nằm ở **scope thư mục đồ án** (`.mcp.json` ở gốc repo). Nếu chỉ đăng ký ở scope người dùng thì phiên chạy từ `d:\DA\Final_Project` sẽ **không thấy tool Power BI nào**.
- Ghi phiên bản Power BI Desktop **thực tế** vào B1 bước 2. Tại thời điểm chốt hợp đồng này là **`2.157.1354.0`** (bản Microsoft Store); `PLAN.md` §Phase 0 ghi `2.156.951.0` là bản cũ trước khi Store tự cập nhật.

### 8.5. Rủi ro mới do MCP tạo ra

MCP có thể sửa phép đo giữa hai lần chạy gate mà không để lại vết trong PBIX nhị phân. Hai biện pháp chặn:

1. Sau mỗi lượt MCP ghi, xuất lại danh mục phép đo (`database_operations → ExportTMDL`) và so với `powerbi/DAX_Measures.md`; chênh lệch nào không có trong nhật ký thay đổi thì phải giải thích.
2. Cân nhắc lưu kèm **PBIP**: mô hình thành TMDL dạng văn bản, `git diff` đọc được, và MCP mở trực tiếp thư mục PBIP. Đây đúng là thứ Gate B1 đang phải bù bằng hợp đồng giấy vì PBIX là tệp nhị phân. Vẫn giữ `.pbix` làm sản phẩm nộp theo `PLAN.md`.
