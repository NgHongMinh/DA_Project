# Kế hoạch triển khai Phase 3 — Phân tích mô tả

Kế hoạch này được đối chiếu với mục **PHASE 3 — Phân tích mô tả** trong `PLAN.md`, phần kiểm chứng sau Phase 3 và sáu câu hỏi phân tích trong `docs/BaoCao.md`.

Đây chỉ là kế hoạch thực hiện. Trong giai đoạn lập kế hoạch, chưa viết mã Python, SQL, chưa tạo bảng thống kê và chưa thay đổi kết quả của Phase 1–2.

## 1. Phạm vi

Phase 3 thực hiện:

- Thống kê mô tả bằng Python.
- Tính các chỉ số dẫn xuất bằng Python và SQL.
- Tạo bảng `fact_metrics`.
- Xuất sáu bảng thống kê Excel.
- Đối chiếu kết quả giữa Python và SQL.
- Ghi phát hiện vào `docs/NhatKyPhanTich.md`.
- Hoàn thiện mục 1.3 trong `docs/BaoCao.md`.

Phase 3 không thực hiện:

- Vẽ biểu đồ — thuộc Phase 4.
- Xây dựng Power BI — thuộc Phase 5.
- Chọn kết luận hoặc đưa ra đề xuất chính sách — thuộc Phase 6–7.
- Làm sạch lại dữ liệu nguồn — đã thuộc Phase 2.

## 2. Nguyên tắc thực hiện

1. Thực hiện tuần tự từng bước; chỉ chuyển bước khi điều kiện hoàn thành của bước hiện tại đã đạt.
2. Dùng `sql/renewables.db` hoặc các bảng tương ứng trong `output/clean/` làm nguồn phân tích duy nhất; không đọc lại và tự hợp nhất 17 CSV gốc.
3. Không nội suy, không tự điền dữ liệu và không đổi `NULL` thành 0. `NULL` là không có quan sát, còn 0 là một quan sát hợp lệ.
4. Loại thực thể tổng hợp khỏi mọi phân tích cấp quốc gia.
5. Phân tích ASEAN chính chỉ dùng ASEAN-10 trong giai đoạn 2000–2021.
6. Tách rõ hai định nghĩa:
   - Tổng năng lượng tái tạo: thủy điện + gió + mặt trời + nguồn tái tạo khác.
   - Năng lượng tái tạo hiện đại: gió + mặt trời.
7. Mọi công thức, ngưỡng, phạm vi, đơn vị và quy tắc xử lý trường hợp biên phải được ghi rõ trước khi tính.

---

## Bước 1 — Xác nhận đầu vào Phase 3

### Làm gì

Chạy lại quy trình và kiểm định Phase 2:

```powershell
python python\02_clean_build.py
python python\run_sql.py sql\02_validate.sql --fail-on-blocking --output-csv output\stats\02_validation_results.csv
```

Đối chiếu các mốc:

- `fact_energy` có 89.075 dòng.
- Có 215 quốc gia/vùng lãnh thổ hiện tại và đúng 10 nước ASEAN.
- Panel ASEAN chính có đủ 1.760/1.760 quan sát.
- Cửa sổ ASEAN là 2000–2021.
- Không có khóa trùng, giá trị âm hoặc tỷ lệ ngoài `[0,100]`.
- Không có năm vượt thời điểm cắt dữ liệu.

### Vì sao

Phase 3 phụ thuộc hoàn toàn vào kết quả Phase 2. Nếu dữ liệu nền thay đổi hoặc kiểm định không đạt, các phép tính sau có thể đúng về công thức nhưng sai về dữ liệu đầu vào.

### Kết quả hướng tới

Xác nhận `sql/renewables.db` và `output/clean/` đủ điều kiện làm nguồn duy nhất cho Phase 3.

### Điều kiện dừng

Nếu có kiểm tra chặn không đạt, dừng Phase 3 và xử lý nguyên nhân ở Phase 2 trước.

---

## Bước 2 — Lập đặc tả chỉ số và quy tắc tính

### Làm gì

Lập bảng định nghĩa cho:

- Bốn công nghệ tái tạo.
- Tổng năng lượng tái tạo và năng lượng tái tạo hiện đại.
- Hai phạm vi: toàn cầu và ASEAN-10.
- Ba phiên bản thống kê: toàn bộ, chỉ giá trị lớn hơn 0 và chỉ giá trị đạt mức đáng kể.
- YoY (tăng trưởng so với năm trước).
- CAGR (tốc độ tăng trưởng kép hằng năm).
- Tỷ trọng thế giới và tỷ trọng ASEAN.
- Quy tắc xếp hạng.
- Năm đầu tiên có sản lượng dương.
- Top-N share (tỷ trọng của N quốc gia đứng đầu).
- HHI (chỉ số tập trung Herfindahl–Hirschman).
- Gini (hệ số bất bình đẳng).

Bảng đặc tả dự kiến có các trường:

```text
metric_name
definition
formula
unit
grain
scope
null_rule
zero_rule
eligibility_rule
purpose
```

### Vì sao

Kết quả có thể thay đổi nếu Python và SQL dùng khác phạm vi, mẫu số hoặc quy tắc xử lý giá trị 0. Đặc tả trước giúp toàn bộ sản phẩm dùng chung một định nghĩa.

### Quyết định phải khóa

Kiểm tra độ nhạy trước khi chọn:

- Ngưỡng “sản lượng đáng kể”.
- Ngưỡng sàn của giá trị đầu kỳ khi xếp hạng CAGR.
- Các năm mốc dùng cho bảng cắt ngang.

Có thể thử các ngưỡng `0,01`, `0,1` và `1 TWh`. Chỉ chọn ngưỡng cuối cùng sau khi xem ảnh hưởng lên số quốc gia đủ điều kiện và thứ hạng.

### Kết quả hướng tới

Mọi chỉ số đều có công thức, phạm vi, đơn vị, mục đích và quy tắc xử lý trường hợp biên rõ ràng.

---

## Bước 3 — Tạo cấu trúc chương trình Phase 3

### Làm gì

Chuẩn bị:

- `python/03_descriptive.py`
- `sql/03_analysis.sql`

Python phụ trách:

1. Đọc và kiểm tra dữ liệu đầu vào.
2. Tạo tập dữ liệu phân tích.
3. Tính thống kê mô tả và phân vị.
4. Tính các chỉ số phù hợp với Python.
5. Kiểm tra kết quả.
6. Xuất Excel và ghi `fact_metrics`.

SQL phụ trách khoảng 12 truy vấn cho tổng theo năm, YoY, tỷ trọng, xếp hạng, năm đầu có sản lượng dương, tổng năng lượng tái tạo, năng lượng tái tạo hiện đại, top-3 share, HHI và đối chiếu với Python.

### Vì sao

SQL phù hợp với window function (hàm cửa sổ), còn Python phù hợp với phân vị, độ lệch, độ nhọn và Gini. Phân chia này giúp mỗi công cụ thực hiện phần mạnh nhất và tạo cơ sở kiểm chứng chéo.

### Kết quả hướng tới

Hai file có cấu trúc rõ ràng, các phần tính toán có thể kiểm tra độc lập và không lặp logic không cần thiết.

---

## Bước 4 — Dựng tập dữ liệu phân tích chuẩn

### Làm gì

Tạo tập dữ liệu ở mức chi tiết:

```text
entity × year × technology
```

Các trường tối thiểu:

```text
entity
year
technology
value_twh
entity_type
is_current_country
is_asean
is_zero
is_positive
is_significant
```

Sau đó tạo tập dữ liệu ở mức `entity × year`, gồm:

- Tổng bốn công nghệ.
- Tổng gió + mặt trời.
- Tỷ trọng từng công nghệ trong tổng năng lượng tái tạo.
- Tỷ trọng quốc gia trong tổng ASEAN.
- Tỷ trọng ASEAN trong tổng thế giới.

### Vì sao

Một tập dữ liệu chuẩn ngăn mỗi bảng dùng một bộ lọc hoặc công thức khác nhau. Việc giữ riêng `NULL` và 0 bảo vệ ý nghĩa dữ liệu: `NULL` là không có quan sát, còn 0 cho biết đã quan sát nhưng chưa có sản lượng.

### Rủi ro cần chặn

- Lẫn `World`, châu lục, nhóm thu nhập hoặc vùng tổng hợp vào phân tích quốc gia.
- Phép ghép bảng làm mất quốc gia.
- Cộng `NULL` như một giá trị 0.
- Dùng năm 2022 cho ASEAN.
- Dùng tổng thế giới không cùng định nghĩa với tử số.

### Kết quả hướng tới

Có một tập dữ liệu chuẩn làm nguồn duy nhất cho toàn bộ phép tính phía sau.

---

## Bước 5 — Tính bộ thống kê mô tả đầy đủ

### Làm gì

Tính theo từng tổ hợp:

```text
phạm vi × năm mốc × công nghệ × phiên bản lọc
```

Hai phạm vi:

- Toàn cầu: các quốc gia/vùng lãnh thổ hiện tại.
- ASEAN-10.

Ba phiên bản:

- Toàn bộ quan sát.
- Chỉ giá trị `> 0`.
- Chỉ giá trị đạt mức đáng kể.

Bộ thống kê:

```text
n, sum, mean, median, sd, CV, min, max,
P10, P25, P50, P75, P90, P95, P99,
IQR, skewness, kurtosis, zero_count, zero_share
```

Trong đó `CV` là hệ số biến thiên, `IQR` là khoảng tứ phân vị, `skewness` là độ lệch phân phối và `kurtosis` là độ nhọn của phân phối.

### Vì sao

Mẫu toàn cầu đủ lớn để các phân vị tạo bối cảnh có ý nghĩa. ASEAN chỉ có 10 nước nên các phân vị ở phạm vi này chỉ dùng để mô tả trực tiếp, không dùng để suy rộng thống kê. Ba phiên bản giúp đo tác động của giá trị 0 lên mean, median và phân vị.

### Quy tắc xử lý

- Chỉ tính `CV = sd / mean` khi mean lớn hơn 0.
- Nhóm không đủ quan sát phải để `NULL` cho thống kê không ổn định.
- Không đổi kết quả không xác định thành 0.
- Luôn ghi số lượng quan sát của từng nhóm.

### Kết quả hướng tới

Có bộ thống kê đầy đủ đúng yêu cầu Bước 2–3 của Phase 3 trong `PLAN.md`.

---

## Bước 6 — Diễn giải chất lượng phân phối

### Làm gì

Đánh giá theo từng phạm vi và công nghệ:

- Chênh lệch giữa mean và median.
- Mức CV.
- Dấu và độ lớn của skewness.
- Khoảng cách giữa các phân vị.
- Ảnh hưởng khi loại giá trị 0.
- Ảnh hưởng của ngưỡng “đáng kể”.

### Vì sao

Mục tiêu của Phase 3 không phải liệt kê thống kê cho đủ. Cần giải thích khi nào mean bị một số quốc gia có sản lượng lớn kéo lên, khi nào median đại diện tốt hơn và vì sao phân vị cần thiết với phân phối lệch.

### Kết quả hướng tới

Mỗi thống kê được dùng trong báo cáo đều có lý do xuất hiện, cách đọc và giới hạn rõ ràng.

---

## Bước 7 — Tính YoY và CAGR

### Làm gì

Tính YoY:

```text
YoY(t) = value(t) / value(t-1) - 1
```

Chỉ tính khi có quan sát của năm trước, hai năm liên tiếp và giá trị năm trước lớn hơn 0.

Tính CAGR:

```text
CAGR = (end_value / start_value)^(1 / number_of_years) - 1
```

Dự kiến cho các giai đoạn:

- 2000–2010.
- 2010–2021.
- 2000–2021.

Chỉ đưa CAGR vào xếp hạng khi giá trị đầu kỳ đạt ngưỡng sàn đã chốt ở Bước 2.

### Vì sao

Nếu mẫu số bằng 0, YoY và CAGR không được định nghĩa. Nếu giá trị đầu kỳ gần 0, CAGR có thể rất lớn nhưng không phản ánh mức tăng có quy mô đáng kể.

### Rủi ro cần chặn

- `Inf` do chia cho 0.
- `NaN` do thiếu dữ liệu.
- CAGR vô nghĩa từ nền gần 0.
- Tính YoY qua khoảng trống nhiều năm.
- So sánh các nước có độ dài giai đoạn khác nhau.

### Kết quả hướng tới

Mọi trường hợp không tính được được lưu là `NULL` kèm lý do, không được đổi thành 0.

---

## Bước 8 — Tính tỷ trọng và xếp hạng

### Làm gì

Tính:

- Tỷ trọng từng nước trong tổng ASEAN.
- Tỷ trọng ASEAN trong tổng thế giới.
- Xếp hạng toàn cầu theo năm và công nghệ.
- Xếp hạng ASEAN theo tổng năng lượng tái tạo.
- Xếp hạng ASEAN theo năng lượng tái tạo hiện đại.
- Chênh lệch giữa hai cách xếp hạng.
- Thay đổi thứ hạng giữa các năm mốc.

Dùng `RANK()`:

- Giá trị bằng nhau nhận cùng hạng.
- Hạng tiếp theo có thể bị nhảy.
- Tên quốc gia chỉ dùng để sắp xếp hiển thị ổn định, không dùng để phá hòa.

### Vì sao

So sánh hai cách đo trực tiếp kiểm tra việc vị trí của một nước có phụ thuộc vào lợi thế thủy điện sẵn có hay không.

### Rủi ro cần chặn

- Tử số và mẫu số dùng khác định nghĩa.
- Lẫn thực thể tổng hợp vào xếp hạng quốc gia.
- Python và SQL dùng hai kiểu xếp hạng khác nhau.
- Tính tỷ trọng khi mẫu số bằng 0.

### Kết quả hướng tới

Có bảng xếp hạng nhất quán cho hai cách đo và giải thích được độ chênh thứ hạng.

---

## Bước 9 — Tính độ trễ gia nhập và mức tập trung

### Làm gì

Với từng quốc gia và công nghệ, tính:

- Năm đầu tiên có sản lượng `> 0`.
- Năm đầu tiên đạt mức đáng kể.
- Độ trễ so với nước ASEAN xuất hiện sớm nhất.
- Độ trễ tính từ năm 2000.

Theo từng năm, tính cho tổng năng lượng tái tạo và năng lượng tái tạo hiện đại:

- Top-1 share.
- Top-3 share.
- HHI.
- Gini.

### Vì sao

Năm đầu dương cho biết thời điểm công nghệ xuất hiện, nhưng có thể chỉ là giá trị rất nhỏ. Năm đầu đạt ngưỡng đáng kể phân biệt sự xuất hiện kỹ thuật với triển khai có quy mô. Các chỉ số tập trung cho biết tăng trưởng ASEAN đến từ số đông hay chủ yếu từ một vài nước.

### Quy tắc xử lý

- Không kết luận “chưa gia nhập” nếu chuỗi bị thiếu dữ liệu.
- Nếu tổng khu vực bằng 0, chỉ số tập trung phải là `NULL`.
- HHI và Gini phải nằm trong `[0,1]`.
- Tổng tỷ trọng quốc gia phải xấp xỉ 1 trong dung sai làm tròn.

### Kết quả hướng tới

Có đủ dữ liệu trả lời câu hỏi về độ trễ công nghệ và mức tập trung của quá trình chuyển dịch.

---

## Bước 10 — Tạo bảng `fact_metrics`

### Làm gì

Tạo `fact_metrics` theo dạng long (dạng dọc, mỗi dòng là một giá trị chỉ số), dự kiến gồm:

```text
entity
year
technology
metric_name
metric_value
unit
comparison_scope
start_year
end_year
eligibility_flag
exclusion_reason
method_version
```

Lưu các nhóm chỉ số: tổng năng lượng tái tạo, năng lượng tái tạo hiện đại, YoY, CAGR, tỷ trọng, xếp hạng, năm gia nhập, top-N share, HHI và Gini.

### Vì sao

Dạng long giúp Phase 4 và Power BI dùng chung cấu trúc, đồng thời tránh một bảng quá rộng. Các trường điều kiện và lý do loại giúp phân biệt trường hợp “không tính được” với giá trị 0.

### Kết quả hướng tới

- Có khóa duy nhất rõ ràng.
- Không có dòng trùng.
- Chạy lại không cộng dồn dữ liệu cũ.
- Mọi dòng truy được về dữ liệu nguồn và phiên bản phương pháp.

---

## Bước 11 — Xuất sáu bảng Excel

### Làm gì

Xuất sáu bảng:

1. `output/stats/03_global_cross_section.xlsx` — cắt ngang toàn cầu theo công nghệ, năm mốc và ba phiên bản lọc.
2. `output/stats/03_asean_cross_section.xlsx` — cắt ngang ASEAN-10, thống kê phân phối và cơ cấu công nghệ.
3. `output/stats/03_vietnam_time_series.xlsx` — chuỗi Việt Nam gồm bốn công nghệ, tổng năng lượng tái tạo, năng lượng tái tạo hiện đại, YoY, tỷ trọng ASEAN và hạng toàn cầu.
4. `output/stats/03_ranking_comparison.xlsx` — so sánh hạng tổng năng lượng tái tạo với hạng năng lượng tái tạo hiện đại.
5. `output/stats/03_entry_lag.xlsx` — năm đầu dương, năm đầu đáng kể và độ trễ gia nhập.
6. `output/stats/03_global_context.xlsx` — tổng thế giới, tổng ASEAN, tỷ trọng ASEAN/thế giới và mức tập trung theo các năm mốc.

Mỗi file phải ghi rõ đơn vị, phạm vi quốc gia, cửa sổ năm, định nghĩa chỉ số, ngưỡng, quy tắc `NULL`/0, phiên bản phương pháp và số lượng quan sát.

### Vì sao

Sáu bảng tương ứng trực tiếp với yêu cầu trong `PLAN.md` và cung cấp đầu vào có thể truy vết cho Phase 4–7. Tách thành sáu file giúp kiểm tra từng nhóm kết quả độc lập.

### Kết quả hướng tới

Có đúng sáu bảng Excel; mọi con số truy được về `fact_metrics` hoặc một truy vấn trong `sql/03_analysis.sql`.

---

## Bước 12 — Đối chiếu Python và SQL

### Làm gì

Đối chiếu:

- Tổng theo năm và công nghệ.
- Tổng ASEAN và tổng thế giới.
- YoY.
- Xếp hạng toàn cầu và ASEAN.
- Năm đầu có sản lượng dương.
- Tỷ trọng.
- Top-3 share.
- HHI.

Xuất kết quả vào `output/stats/03_crosscheck_results.csv` với cấu trúc:

```text
check_id
description
python_value
sql_value
absolute_difference
tolerance
status
```

### Vì sao

Đối chiếu chéo phát hiện lỗi công thức, bộ lọc hoặc phạm vi mà kiểm tra một công cụ có thể bỏ sót. Đây cũng là tiêu chí bắt buộc trong `PLAN.md`: xếp hạng Python và SQL phải cho cùng kết quả.

### Kết quả hướng tới

Mọi kiểm tra bắt buộc đều `PASS`, chênh lệch số thực nằm trong dung sai và xếp hạng hai công cụ giống nhau.

---

## Bước 13 — Kiểm tra chất lượng toàn bộ Phase 3

### Làm gì

Kiểm tra tự động:

- Không còn `Inf`.
- Không còn `NaN` chưa xử lý.
- Không có khóa trùng trong `fact_metrics`.
- Không lẫn thực thể tổng hợp vào phân tích quốc gia.
- Không có năm ngoài phạm vi.
- Tỷ trọng nằm trong miền hợp lệ.
- HHI và Gini nằm trong `[0,1]`.
- Tổng tỷ trọng xấp xỉ 1 hoặc 100%.
- YoY không được tính khi mẫu số bằng 0.
- CAGR xếp hạng tuân thủ ngưỡng sàn.
- Có đủ sáu file Excel.
- Chạy lại cho kết quả ổn định.

### Vì sao

Chương trình chạy không báo lỗi chưa chứng minh kết quả đúng. Các kiểm tra này nhắm trực tiếp vào những lỗi dễ xảy ra nhất trong Phase 3.

### Kết quả hướng tới

Tạo báo cáo kiểm tra rõ trạng thái; tất cả kiểm tra chặn phải đạt trước khi viết phát hiện.

---

## Bước 14 — Ghi phát hiện vào nhật ký

### Làm gì

Cập nhật phần Phase 3 trong `docs/NhatKyPhanTich.md`. Mỗi phát hiện gồm:

- Mã phát hiện.
- Câu hỏi phân tích liên quan.
- Phạm vi và thời gian.
- Chỉ số và con số cụ thể.
- Nguồn truy vết.
- Cách diễn giải và căn cứ diễn giải.
- Giới hạn.
- Mức tin cậy.

Ghi cả phát hiện có ý nghĩa, kết quả không khác biệt như dự kiến, thống kê bị bóp méo và câu hỏi chưa thể trả lời.

### Vì sao

Nhật ký là kho bằng chứng cho Phase 6–7. Ghi cả nguồn và giới hạn giúp kết quả có thể kiểm chứng và ngăn việc diễn giải vượt quá dữ liệu.

### Kết quả hướng tới

Mọi phát hiện Phase 3 đều có bằng chứng số và đường dẫn truy vết.

---

## Bước 15 — Hoàn thiện mục 1.3 của báo cáo

### Làm gì

Thay phần “Phase 3 — chưa thực hiện” trong `docs/BaoCao.md` bằng:

1. Phạm vi và phương pháp.
2. Lý do phân tích hai tầng toàn cầu và ASEAN.
3. Tác động của giá trị 0.
4. Đặc điểm phân phối.
5. Tổng năng lượng tái tạo và năng lượng tái tạo hiện đại.
6. Tăng trưởng và điều kiện tính CAGR.
7. So sánh thứ hạng.
8. Độ trễ gia nhập.
9. Mức tập trung.
10. Giới hạn diễn giải.
11. Dẫn chiếu tới sáu bảng Excel.

### Vì sao

Yêu cầu 1.3 không chỉ cần bảng số mà còn phải chứng minh thống kê nào phù hợp với phân phối và thống kê nào có thể gây hiểu sai.

### Kết quả hướng tới

Mỗi con số trong mục 1.3 truy được về một bảng Excel, `fact_metrics` hoặc truy vấn SQL cụ thể.

---

## Bước 16 — Đóng Phase 3

### Làm gì

Chỉ sau khi tất cả bước đã đạt:

- Chạy lại toàn bộ Phase 3 từ đầu vào Phase 2.
- Xác nhận kết quả có thể tái lập và không sửa 17 file nguồn.
- Ghi lại lệnh chạy chuẩn.
- Đánh dấu Phase 3 hoàn thành trong `PLAN.md`.

### Vì sao

Đóng Phase 3 quá sớm có thể khiến Phase 4 sử dụng kết quả chưa được kiểm chứng.

### Kết quả hướng tới

Phase 3 trở thành đầu vào ổn định và có thể truy vết cho trực quan hóa, dashboard, báo cáo và kết luận.

## 3. Thứ tự sản phẩm dự kiến

1. `python/03_descriptive.py`
2. `sql/03_analysis.sql`
3. Bảng `fact_metrics` trong `sql/renewables.db`
4. Sáu file `output/stats/03_*.xlsx`
5. `output/stats/03_crosscheck_results.csv`
6. Phần Phase 3 trong `docs/NhatKyPhanTich.md`
7. Mục 1.3 trong `docs/BaoCao.md`
8. Trạng thái Phase 3 trong `PLAN.md`

## 4. Tiêu chí hoàn thành cuối cùng

Phase 3 chỉ được coi là hoàn thành khi:

- Có `python/03_descriptive.py` và `sql/03_analysis.sql`.
- Có bảng `fact_metrics` với khóa và mức chi tiết rõ ràng.
- Có đủ sáu bảng Excel.
- Không còn `Inf` hoặc `NaN` chưa xử lý.
- Tổng theo từng lát cắt khớp với tổng kiểm chứng.
- Xếp hạng Python và SQL cho cùng kết quả.
- YoY và CAGR không vi phạm điều kiện mẫu số.
- Không lẫn thực thể tổng hợp vào phân tích quốc gia.
- Mỗi thống kê có lý do sử dụng và giới hạn diễn giải.
- Phát hiện đã được ghi vào nhật ký.
- Mục 1.3 của báo cáo đã hoàn thiện.
- Chạy lại cho kết quả ổn định và không sửa dữ liệu nguồn.
