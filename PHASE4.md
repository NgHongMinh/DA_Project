# Hợp đồng triển khai Phase 4 (Giai đoạn 4) — Trực quan hóa

Tài liệu này là hợp đồng thực thi cho **PHASE 4 — Trực quan hóa** trong `PLAN.md`. Mục tiêu là chuyển kết quả đã kiểm chứng của Phase 3 thành đúng 13 biểu đồ tĩnh, đồng thời lưu dữ liệu biểu đồ và bằng chứng kiểm định để mọi con số có thể truy ngược về nguồn.

Trạng thái hiện tại: **ĐÃ HOÀN THÀNH** ngày 2026-09-08. Bản phát hành có 13 PNG, 16 sheet và 38/38 kiểm định tự động `PASS`; 13/13 biểu đồ đạt nghiệm thu trực quan và được Nguyễn Hồng Minh ký nhận trong `docs/Phase4_Review.md`.

## 1. Mục tiêu, phạm vi và điều kiện đầu vào

### 1.1. Mục tiêu

Phase 4 phải tạo một bản phát hành nhất quán gồm:

- đúng 13 PNG (tệp ảnh nén không mất dữ liệu) trong `output/charts/`, mỗi hình chỉ có một thông điệp chính;
- `output/stats/04_chart_data.xlsx`, một workbook (tệp Excel nhiều trang tính) chứa đúng dữ liệu đã dùng để vẽ và thông tin truy vết;
- `output/stats/04_validation_results.csv`, chứa bằng chứng cho các kiểm định tự động;
- mục 1.4 trong `docs/BaoCao.md`, phần Phase 4 trong `docs/NhatKyPhanTich.md` và bảng nghiệm thu `docs/Phase4_Review.md`;
- bốn chương trình `python/04_charts.py`, `python/04_test_contract.py`, `python/04_test_publish.py`, `python/04_verify_release.py` cùng hợp đồng `python/phase4_contract.py`.

Mục tiêu của bộ bằng chứng đi kèm là ngăn một PNG đúng hình thức nhưng dùng sai phiên bản dữ liệu, sai công thức hoặc không thể truy lại số đã trình bày.

### 1.2. Trong và ngoài phạm vi

Trong phạm vi:

- biểu đồ tĩnh bằng Python, Matplotlib và Seaborn;
- ASEAN-10 và bối cảnh thế giới trong giai đoạn 2000–2021;
- sáu câu hỏi Q1–Q6 đã khóa ở Phase 3;
- một chỉ số mới duy nhất: hệ số sử dụng công suất xấp xỉ cho C13;
- dữ liệu biểu đồ, kiểm định, tài liệu giải thích và nghiệm thu trực quan.

Ngoài phạm vi:

- Power BI, slide (trang trình chiếu), kết luận cuối cùng và đề xuất chính sách;
- nội suy, điền giá trị thiếu, đưa năm 2022 trở lại hoặc sửa dữ liệu Phase 2–3;
- tính lại các công thức Phase 3 trong tầng trực quan hóa;
- dùng C13 để kết luận về hiệu quả kỹ thuật hoặc quan hệ nhân quả.

### 1.3. Mốc đầu vào bắt buộc

Pipeline (chuỗi xử lý) phải dừng trước khi dựng dữ liệu nếu một mốc sau không còn đúng:

| Hạng mục | Mốc khóa |
|---|---:|
| Kiểm tra môi trường Phase 0 | 26/26 đạt |
| Số dòng `fact_energy` Phase 2 | 89.075 |
| SHA-256 của `fact_energy.csv` | `dfaca2c46efde54b506f317497d458ed864f88ab4a8d74de9665afaa467a4374` |
| Kiểm định Phase 2 | 864 dòng; 560 `PASS`, 268 `WARN`, 36 `SKIP`; không có kiểm định `BLOCKING` khác `PASS` |
| Số dòng `fact_metrics` Phase 3 | 18.926 |
| Đối chiếu Python–SQL Phase 3 | 18.926/18.926 `PASS` |
| Kiểm định Phase 3 | 92/92 `PASS` |
| Phân bố Q1–Q6 | Q1=5.544; Q2=3.608; Q3=1.980; Q4=1.382; Q5=5.950; Q6=462 |
| Dấu vân tay Phase 2 | `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10` |
| Phạm vi chính | ASEAN-10, 2000–2021; không nội suy; không dùng năm 2022 |

Quy ước trạng thái kiểm định: `PASS` (đạt), `WARN` (cảnh báo cần xem xét), `SKIP` (bỏ qua có chủ đích) và `FAIL` (không đạt).

Sáu workbook Phase 3 phải đúng tên, đúng sheet (trang tính) và mang cùng dấu vân tay. Mã băm của 17 CSV nguồn cùng `fact_energy.csv` phải được ghi trước và sau quá trình chạy để chứng minh Phase 4 không sửa dữ liệu nguồn trực tiếp.
Danh sách 17 mã SHA-256 được lưu bền vững tại dòng `archive_csv_sha256`; mã băm riêng của `fact_energy.csv` nằm tại `phase2_fact_energy_sha256` trong sheet `metadata` của `04_chart_data.xlsx`. Kiểm định `P4_B1_PHASE2_FACT_ENERGY` khóa đúng nội dung đầu vào C13, còn `P4_B9_SOURCE_IMMUTABILITY` đối chiếu lại tệp trước khi cho phép công bố.

## 2. Nguồn chuẩn, dữ liệu đầu ra và truy vết

### 2.1. Nguồn số

- `output/stats/03_fact_metrics.csv` và `output/stats/03_metric_definitions.csv` là nguồn số chính của C01–C12.
- Các workbook Phase 3 là bảng trình bày để chọn lát cắt và đối chiếu; chúng không được trở thành nơi định nghĩa lại công thức. Mọi dòng lấy từ workbook phải phân giải được về đúng một `fact_key` trong `03_fact_metrics.csv` và khớp giá trị, đơn vị, trạng thái, phiên bản phương pháp cùng dấu vân tay.
- Chỉ C13 được đọc trực tiếp `output/clean/fact_energy.csv`, vì hệ số sử dụng công suất xấp xỉ chưa thuộc `fact_metrics` Phase 3. Dữ liệu C13 phải giữ cả khóa nguồn của tử số sản lượng và mẫu số công suất.

Hệ số sử dụng công suất xấp xỉ được khóa bởi công thức:

```text
capacity_factor = generation_twh / (capacity_gw × 8,76)
```

Chỉ tính khi sản lượng được quan sát và `capacity_gw > 0`. Công suất là giá trị cuối năm nên kết quả chỉ là chỉ báo xấp xỉ, không phải phép đo hiệu quả kỹ thuật thực tế.

### 2.2. Hợp đồng workbook Phase 4

`output/stats/04_chart_data.xlsx` phải có đúng thứ tự sheet sau:

1. `manifest`
2. `global_context`
3. `asean_technology`
4. `country_mix_2021`
5. `rank_shift_2021`
6. `small_multiples`
7. `vietnam_technology`
8. `vietnam_q5`
9. `vietnam_position`
10. `global_distribution`
11. `entry_lag`
12. `concentration`
13. `growth_contribution`
14. `capacity_factor`
15. `metadata`
16. `method_notes`

Sheet `manifest` (bảng kê) phải có tối thiểu các trường:

`chart_id`, `file_name`, `question_ids`, `title_vi`, `message_vi`, `data_sheets`, `source_locator`, `trace_key`, `scope`, `period`, `axis_mode`, `limitation_vi`, `method_version`, `phase2_input_fingerprint`.

Các điều kiện chung của workbook:

- `method_version = phase4_v1` và dấu vân tay phải giống nhau trên toàn bộ sản phẩm;
- khóa của từng sheet là duy nhất và thứ tự hàng/cột ổn định;
- không có năm ngoài 2000–2021, `Inf` hoặc chuỗi `NaN`;
- giá trị không xác định phải để trống và có trạng thái/lý do, không được đổi thành 0;
- dữ liệu cấp quốc gia chỉ chứa 10 nước ASEAN hoặc 215 quốc gia/vùng lãnh thổ hiện tại theo đúng phạm vi của biểu đồ, không lẫn thực thể tổng hợp;
- mọi giá trị hiển thị trên hình, kể cả số trong chú thích, phải có dòng bằng chứng trong workbook.

### 2.3. Hợp đồng kiểm định

`output/stats/04_validation_results.csv` phải có mã kiểm định duy nhất, mức độ `BLOCKING` (chặn phát hành) hoặc `AUDIT` (kiểm toán), trạng thái rõ ràng và cùng `method_version`/dấu vân tay. Không được công bố nếu có dòng `BLOCKING` khác `PASS`.

Kiểm định tự động chỉ xác nhận dữ liệu, hợp đồng tệp và thuộc tính kỹ thuật của PNG. Việc chữ có chồng/cắt, màu có dễ phân biệt và hình có gây diễn giải sai hay không vẫn phải được người nghiệm thu xác nhận trong `docs/Phase4_Review.md`.

## 3. Quy ước thiết kế bắt buộc

### 3.1. Trạng thái skill trực quan hóa

Skill `dataviz` (bộ hướng dẫn trực quan hóa) không khả dụng trong môi trường triển khai hiện tại. Không được ghi nhận giả rằng skill đã được gọi. Hợp đồng tại tài liệu này và `python/phase4_contract.py` là phương án thay thế bắt buộc để khóa bảng màu, cách mã hóa, trục, nhãn và tiêu chí kiểm tra trước khi vẽ.

### 3.2. Kích thước, chữ và bố cục

- Mọi PNG có kích thước 2.400 × 1.350 điểm ảnh, 200 DPI (mật độ điểm ảnh), tỷ lệ 16:9 và nền trắng.
- Font (phông chữ) duy nhất là `DejaVu Sans`; toàn bộ nội dung hiển thị bằng tiếng Việt.
- Nguồn, phạm vi, cửa sổ 2000–2021 và giới hạn diễn giải phải hiện trên từng hình.
- Nhãn trực tiếp chỉ đặt tại điểm cuối hoặc cực trị có ý nghĩa; không phủ dữ liệu và không vượt khung.
- Không dùng `twinx`, `twiny`, trục kép, biểu đồ tròn hoặc đưa giá trị 0 lên trục logarit.
- Khi cần hai thang đo, dùng các panel (ô biểu đồ) riêng và chia sẻ trục thời gian.
- Màu không được gắn theo vị trí xếp hạng; Việt Nam luôn là màu nhấn.

### 3.3. Bảng màu công nghệ và chuỗi phân tích

| Chuỗi | Màu |
|---|---|
| Thủy điện | `#0072B2` |
| Gió | `#009E73` |
| Mặt trời | `#E69F00` |
| NLTT khác | `#CC79A7` |
| Tổng NLTT | `#374151` |
| Gió + mặt trời | `#D55E00` |

Biểu đồ công nghệ dùng màu công nghệ. Biểu đồ so sánh quốc gia dùng ánh xạ thực thể cố định sau; `python/phase4_contract.py` phải chứa đúng cùng ánh xạ để màu không đổi giữa các hình:

| Quốc gia | Màu | Quốc gia | Màu |
|---|---|---|---|
| Việt Nam | `#D55E00` | Thái Lan | `#0072B2` |
| Indonesia | `#009E73` | Philippines | `#E69F00` |
| Malaysia | `#CC79A7` | Singapore | `#56B4E9` |
| Myanmar | `#6B7280` | Campuchia | `#F0E442` |
| Lào | `#332288` | Brunei | `#88CCEE` |

## 4. Danh mục 13 biểu đồ đã khóa

| ID / tệp | Q | Thiết kế và dữ liệu | Thông điệp duy nhất | Giới hạn bắt buộc |
|---|---|---|---|---|
| C01 `04_01_global_asean_context.png` | Q1 | Hai panel từ `annual_context`: tổng NLTT ASEAN và `World` trên trục logarit; tỷ trọng ASEAN/World | ASEAN tăng gần bốn lần nhưng vẫn là phần nhỏ của thế giới | Tổng thế giới là dòng `World` được nguồn công bố; không đưa 0 lên trục logarit |
| C02 `04_02_asean_technology_trend.png` | Q2 | Diện tích chồng bốn công nghệ, 2000–2021, từ `asean_annual` | Thủy điện vẫn lớn nhất; gió và mặt trời tăng rõ cuối kỳ | Thành phần chỉ được cộng khi dữ liệu đủ; không suy diễn nguyên nhân |
| C03 `04_03_asean_country_mix_2021.png` | Q2 | Thanh chồng TWh và heatmap (bản đồ nhiệt) tỷ trọng công nghệ, cùng thứ tự 10 nước, từ `country_year_values` | Quy mô và cơ cấu năm 2021 khác nhau rõ giữa các nước | TWh và tỷ trọng là hai cách mã hóa riêng; không lẫn thực thể tổng hợp |
| C04 `04_04_asean_rank_shift_2021.png` | Q3 | Dumbbell chart (biểu đồ nối hai vị trí) từ `annual_ranks`, so hạng tổng NLTT với hạng gió + mặt trời | Đổi cách đo làm Singapore tăng 4 bậc, Indonesia giảm 4 và Lào giảm 5 | Hạng 1 ở phía trên; giữ nguyên đồng hạng; màu theo quốc gia, không theo hạng |
| C05 `04_05_asean_small_multiples_shared.png` | Q1 | Small multiples (lưới biểu đồ nhỏ đồng dạng) tổng NLTT của 10 nước từ `country_year_values`, dùng chung trục y | Trục chung cho thấy chênh lệch quy mô tuyệt đối | Cùng đúng 220 quan sát với C06; tiêu đề nêu “chung thang đo” |
| C06 `04_06_asean_small_multiples_free.png` | Q1 | Cùng dữ liệu và thứ tự C05, nhưng mỗi nước dùng giới hạn trục y riêng | Trục riêng cho thấy quỹ đạo nội tại của các nước nhỏ | Không dùng để so trực tiếp độ cao giữa các panel; tiêu đề nêu “thang đo riêng” |
| C07 `04_07_vietnam_technology_trend.png` | Q4 | Bốn công nghệ của Việt Nam, 2000–2021, từ `annual`/`country_year_values` | Gió và mặt trời tăng mạnh cuối cửa sổ nhưng thủy điện vẫn quan trọng | Không suy diễn nguyên nhân; tổng phải khớp tổng bốn thành phần |
| C08 `04_08_vietnam_twh_vs_share.png` | Q5 | Lưới 2×2 từ `twh_vs_pct` và `annual_changes`: TWh và % điện cho tổng NLTT và gió + mặt trời | TWh và tỷ trọng điện không luôn đi cùng hướng | Hai thang đo ở panel riêng; chỉ mô tả hướng, không suy diễn quan hệ nhân quả |
| C09 `04_09_vietnam_regional_global_position.png` | Q4 | Việt Nam so với tổng ASEAN-9 cho hai cách đo từ `annual`/`asean9_benchmark`; chú thích hạng toàn cầu 2021 | Việt Nam nổi bật hơn ở gió + mặt trời so với tổng NLTT | ASEAN-9 là tổng, không phải trung bình; hạng toàn cầu chỉ là lát cắt 2021 |
| C10 `04_10_global_distribution_2021.png` | Q1 | Đếm riêng `Zero` (bằng 0), `Trace` (dương dưới ngưỡng) và `Material` (đạt ngưỡng 0,05 TWh); phân phối giá trị dương trên trục logarit từ `country_values`/`generation_stats` | Phân phối toàn cầu có nhiều giá trị 0 và lệch phải mạnh | Giữ 0 thành một khối riêng; không cộng số giả để đưa 0 lên trục logarit |
| C11 `04_11_asean_entry_lag.png` | Q4 | Năm đầu đạt 0,05 TWh từ `entry_status`; ký hiệu riêng cho kiểm duyệt trái/phải | Thời điểm gia nhập từng công nghệ rất không đồng đều | Không đổi trạng thái trái thành năm 2000 hoặc trạng thái phải thành năm 2021 |
| C12 `04_12_asean_concentration_growth.png` | Q6 | Top-3 share (tỷ trọng của ba nước lớn nhất) theo thời gian và đóng góp tăng dương 2010–2021 từ `annual_concentration`/`growth_contribution` | Gió + mặt trời và phần tăng của nó tập trung mạnh ở Việt Nam | Đóng góp tăng trưởng không được thay bằng HHI (chỉ số tập trung Herfindahl–Hirschman)/Gini (hệ số bất bình đẳng) của mức sản lượng |
| C13 `04_13_capacity_factor_proxy.png` | Q4 | Hai panel gió/mặt trời từ `fact_energy.csv`, chỉ giữ cặp sản lượng–công suất hợp lệ | Chỉ số phụ có độ phủ hạn chế: 2 nước cho gió, 4 nước cho mặt trời | Ghi rõ công suất cuối năm, tập nước thiếu và đây là chỉ báo xấp xỉ |

Các khóa truy vết chi tiết của từng biểu đồ nằm trong sheet `manifest`; tên nguồn trong bảng trên là tên sheet Phase 3 tương ứng, không phải nguồn công thức thay thế cho `03_fact_metrics.csv`.

## 5. Trình tự triển khai và cổng chặn

Một bước chỉ hoàn tất khi toàn bộ tiêu chí của bước đó đạt. Nếu có `FAIL` hoặc cảnh báo chưa giải quyết, phải sửa và chạy lại trong chính bước hiện tại; không được tạo hoặc công bố sản phẩm của bước sau.

### B1 — Khóa đầu vào Phase 3

Làm gì: đóng mọi kết nối Navicat có thể giữ khóa database (cơ sở dữ liệu), sau đó chạy lệnh kiểm chứng Phase 4 chính thức. Lệnh này tự động chạy kiểm tra môi trường, kiểm thử công bố Phase 3 và kiểm chứng phát hành Phase 3 trước khi chụp mốc đầu vào Phase 4.

```powershell
python python\04_verify_release.py
```

Vì sao: mọi biểu đồ phía sau phụ thuộc vào cùng một phiên bản đầu vào; khóa này phát hiện dữ liệu cũ, dữ liệu bị thay hoặc đầu ra Phase 3 không đồng bộ.

Đạt khi: cùng một tiến trình báo `PHASE 4 PREFLIGHT: PASS | checks=3/3`, đủ các mốc ở mục 1.3, sáu workbook đúng hợp đồng, hai lần dựng Phase 4 không sửa 17 CSV nguồn hoặc `fact_energy.csv`, và không có kiểm định chặn Phase 2–3 thất bại. Riêng 38 dòng trong CSV kiểm định xác nhận hợp đồng dữ liệu/tệp; bằng chứng ba lệnh tiền điều kiện vừa chạy đến từ mã thoát của `04_verify_release.py`.

### B2 — Khóa hợp đồng thiết kế

Làm gì: kiểm tra `PHASE4.md` và `python/phase4_contract.py` trước khi gọi hàm vẽ.

Vì sao: khóa thiết kế trước dữ liệu hình ảnh giúp tránh đổi thông điệp hoặc cách mã hóa sau khi nhìn thấy kết quả.

Đạt khi: đúng 13 ID/tệp duy nhất; mỗi ID có đúng một mã Q, thông điệp, nguồn, kiểu trục và giới hạn; bảng màu phủ đủ sáu chuỗi và 10 nước; rà mã tĩnh không có lời gọi bị cấm như trục kép hoặc biểu đồ tròn.

### B3 — Dựng dữ liệu biểu đồ và truy vết

Làm gì: dựng toàn bộ sheet của `04_chart_data.xlsx`, đối chiếu từng dòng với `fact_key`; riêng C13 giữ khóa nguồn của tử số và mẫu số.

Vì sao: workbook phải là bằng chứng chính xác của những gì đã vẽ, không phải bản tổng hợp thủ công sau khi vẽ.

Đạt khi: khóa duy nhất, số dòng ổn định, phạm vi đúng, không có thực thể tổng hợp ở cấp quốc gia, không có năm ngoài cửa sổ hoặc số không hữu hạn; mọi phép đối chiếu bằng `fact_key` khớp và C13 tính lại độc lập khớp trong dung sai `1e-9`.

### B4 — C01 và C02: bối cảnh

Đạt khi:

- C01 có 22 năm và 66 giá trị; các đầu mốc khớp ASEAN `72,800904 → 289,655745 TWh`, thế giới `2.854,49 → 7.885,04005 TWh`, tỷ trọng `2,5504% → 3,6735%`;
- C01 chỉ đưa số dương lên trục logarit và không dùng trục kép;
- C02 có 88 điểm; tổng bốn thành phần từng năm khớp `RENEWABLE_TOTAL` trong dung sai `1e-9`;
- C02 năm 2021 khớp thủy điện `185,58`, NLTT khác `61,345745`, mặt trời `34,43`, gió `8,30 TWh`;
- kiểm tra trực quan hai hình không phát hiện chữ chồng/cắt hoặc chú thích vượt khung.

### B5 — C03 đến C06: so sánh ASEAN

Đạt khi:

- C03 có `10 × 4 × 2 = 80` giá trị; tổng thanh chồng khớp tổng NLTT từng nước; tỷ trọng dùng một chữ số thập phân và không giá trị dương nào được ghi thành `0%`/`0,0%`;
- C04 có đúng 10 nước, hạng 1 ở phía trên, giữ đồng hạng và không tô màu theo hạng;
- C05/C06 dùng cùng đúng 220 quan sát và chỉ khác chế độ trục y;
- C05 dùng cùng giới hạn y cho 10 panel; C06 có giới hạn riêng cho từng panel;
- không có năm 2022 hoặc thực thể ngoài ASEAN-10.

### B6 — C07 đến C09: Việt Nam

Đạt khi:

- C07 có 88 giá trị; tổng bốn công nghệ từng năm khớp tổng NLTT;
- C08 có 44 dòng cặp và 88 giá trị số; đánh dấu đúng các năm ngược hướng: tổng NLTT 2003, 2014 và gió + mặt trời 2016;
- C09 dùng tổng ASEAN-9; năm 2021 khớp `104,218036/185,437709 TWh` cho tổng NLTT và `28,16/14,57 TWh` cho gió + mặt trời;
- chú thích hạng toàn cầu 2021 là `16/205` và `17/209`; không vẽ đường hạng qua thời gian;
- nội dung chỉ mô tả xu hướng, không khẳng định nguyên nhân.

### B7 — C10 đến C12: phân phối và chẩn đoán

Đạt khi:

- C10 giữ đủ `215 × 4 = 860` trạng thái; phần logarit chỉ dùng giá trị dương;
- số quan sát bốn công nghệ lần lượt là thủy điện 208, NLTT khác 206, mặt trời 210, gió 209; số 0 tương ứng 59, 92, 50, 105;
- C11 có đúng 40 dòng nước–công nghệ và dùng các trường trạng thái dạng `*_text`, không đổi kiểm duyệt thành năm giả;
- C12 có 44 điểm top-3 share; tổng tỷ trọng đóng góp tăng dương 2010–2021 bằng 1 trong dung sai `1e-9`;
- chú thích 2021 khớp top-3 `92,2537%` so với `67,1023%`; đóng góp tăng dương của Việt Nam là `65,9859%`.

### B8 — C13: hệ số sử dụng công suất xấp xỉ

Đạt khi:

- gió có đúng Philippines và Thái Lan với 33 quan sát có mẫu số dương;
- mặt trời có đúng Malaysia, Philippines, Thái Lan và Việt Nam với 71 quan sát;
- tổng cộng 104 giá trị, tất cả thuộc `[0,1]`;
- hình ghi trực tiếp tám nước thiếu công suất gió và sáu nước thiếu công suất mặt trời;
- hình có cụm từ “công suất cuối năm” và “chỉ báo xấp xỉ”, không kết luận nước nào hiệu quả hơn;
- phép tính độc lập từ hai khóa nguồn khớp trong dung sai `1e-9`.

### B9 — Công bố, kiểm thử và cập nhật tài liệu

Làm gì: dựng tệp trong thư mục tạm, kiểm định đầy đủ rồi mới thay đồng thời bộ tệp chính thức; sau đó cập nhật báo cáo, nhật ký và tạo bảng chờ nghiệm thu.

Vì sao: công bố nguyên tử ngăn PNG, workbook và CSV kiểm định thuộc các lần chạy khác nhau; bảng chờ nghiệm thu tách bằng chứng máy kiểm tra được khỏi đánh giá trực quan của con người.

Đạt tự động khi:

- `04_validation_results.csv` có đúng 38 mã duy nhất và không có dòng `BLOCKING` khác `PASS`;
- `output/charts/` có đúng 13 PNG trong danh sách cho phép; phát hiện tệp `04_*.png` lạ phải dừng, không tự xóa;
- từng PNG mở được, đúng 2.400 × 1.350, không phải ảnh trắng và khớp một dòng `manifest`;
- `04_test_contract.py` chứng minh thay một giá trị C13 nhưng giữ số dòng/khóa vẫn bị chặn và nhãn C03 không che mất tỷ trọng dương;
- `04_test_publish.py` chứng minh lỗi giữa lúc công bố khôi phục đủ bản cũ; nếu hoàn tác không đầy đủ thì giữ bản sao và báo đường dẫn;
- `04_verify_release.py` tự chạy ba tiền điều kiện B1, sau đó chạy Phase 4 hai lần cho cùng nội dung workbook/CSV và cùng mã băm mảng điểm ảnh đã giải mã; không yêu cầu XLSX giống từng byte;
- 17 CSV nguồn, `fact_energy.csv` và toàn bộ đầu ra Phase 3 không đổi trong hai lần dựng Phase 4;
- mục 1.4 nhúng đủ 13 hình; nhật ký chỉ ghi phát hiện mới có số và định vị bằng chứng;
- `PLAN.md` chưa đánh dấu Phase 4 hoàn tất trước khi nghiệm thu thủ công.

Đạt thủ công khi: 13/13 dòng trong `docs/Phase4_Review.md` được người nghiệm thu đánh dấu `ĐẠT`, có tên/ngày xác nhận và không còn ghi chú cần sửa.

## 6. Nghiệm thu tổng thể và điều kiện mở Phase 5

Nghiệm thu tổng thể chỉ được ký khi:

1. Mọi tiêu chí tự động của B1–B9 có bằng chứng đạt, mọi tiêu chí trực quan tương ứng đã được ký trong phiếu nghiệm thu và không còn cảnh báo chưa xử lý.
2. C01–C13 phủ đủ Q1–Q6, đúng một thông điệp chính mỗi hình.
3. Không có thực thể tổng hợp trong biểu đồ quốc gia, năm 2022, trục kép, biểu đồ tròn, giá trị 0 trên trục logarit hoặc tổng dựng từ thành phần thiếu.
4. C05/C06 dùng cùng dữ liệu và khác rõ chế độ trục.
5. C13 công bố công thức, tập nước có/thiếu dữ liệu và giới hạn công suất cuối năm.
6. Mọi số hiển thị truy được về `fact_key` hoặc cặp khóa nguồn của C13.
7. Người nghiệm thu mở từng PNG ở 100% và trong `docs/BaoCao.md`, xác nhận chữ tiếng Việt đúng, không chồng/cắt, màu phân biệt được, chú thích đọc được và hình không tạo diễn giải sai.
8. `docs/Phase4_Review.md` có 13/13 dòng `ĐẠT`, không còn ghi chú phải sửa.
9. Ba lệnh cuối trả mã thoát 0:

   ```powershell
   python python\04_test_contract.py
   python python\04_test_publish.py
   python python\04_verify_release.py
   ```

Sau khi có ký nhận tổng thể, mới được đổi Phase 4 trong `PLAN.md` thành “ĐÃ HOÀN THÀNH”, ghi dấu vân tay, số kiểm định, 13 tên PNG và ngày nghiệm thu, rồi mở Phase 5.
