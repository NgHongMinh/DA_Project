# Phase 1 — Khảo sát dữ liệu và xác định vấn đề

## 1. Mục đích của Phase 1

Phase 1 kiểm tra 17 file CSV trong `archive/` trước khi làm sạch, ghép bảng hoặc đặt câu hỏi phân tích. Mục tiêu là trả lời bằng số liệu thực tế:

1. Nguồn nào nên dùng, nguồn nào nên loại hoặc chỉ dùng bổ trợ?
2. Có thể nối dữ liệu bằng khóa nào và theo chiến lược nào?
3. Chỉ số nào đủ độ phủ để so sánh cả 10 nước ASEAN?
4. Có nên nội suy các năm thiếu hay không?
5. Cửa sổ thời gian nào đủ tin cậy cho phân tích chính?

Phase này chỉ đọc dữ liệu gốc. Không sửa file trong `archive/`, không tự động gộp tên gần giống, không nội suy và không thay giá trị thiếu bằng 0.

## 2. Cách chạy và đầu ra

Từ thư mục gốc dự án, chạy duy nhất:

```powershell
python python\01_profile.py
```

Script kiểm tra đủ 17 CSV, thực hiện tuần tự Step 1–7 trong bộ nhớ và chỉ ghi đầu ra sau khi toàn bộ phép tính thành công. Kết quả không phụ thuộc vào đầu ra của lần chạy trước và không chứa timestamp, vì vậy có thể chạy lại để đối chiếu.

### Danh mục đầu ra

| File | Nội dung | Số dòng kiểm chứng |
|---|---|---:|
| `output/stats/00_phase1_summary.txt` | Báo cáo văn bản UTF-8 gồm bảy phần kết quả và năm quyết định cuối Phase 1 | Không cố định theo dòng |
| `output/stats/01_overlap_conflict_details.csv` | Các giá trị xung đột và trạng thái thiếu không khớp của Step 3, kèm `conflict_tier` và `is_aggregate` | 12.180 × 15 cột |
| `output/stats/02_join_key_details.csv` | Thực thể thiếu `Code` và các cặp tên gần giống của Step 4 | 43 × 13 cột |
| `output/stats/03_asean_coverage_details.csv` | Dữ liệu dạng dài cho ma trận 10 nước ASEAN × 17 file | 170 × 7 cột |
| `output/stats/04_year_continuity_details.csv` | Một dòng cho mỗi chuỗi `Entity`–file của Step 6, kèm bốn cột biên hiệu dụng | 2.702 × 22 cột |
| `output/stats/05_last_year_check.csv` | Một dòng cho mỗi file–năm của Step 7 | 780 × 14 cột |
| `docs/Phase1_KhaoSatDuLieu.md` | Tài liệu giải thích ổn định về ý nghĩa, phương pháp và cách diễn giải Phase 1 | — |

Phase 1 không tạo workbook Excel. File `00_data_profile.xlsx` và các script Step 2–7 riêng lẻ không còn là đầu vào hoặc điều kiện chạy của quy trình hợp nhất.

### Thứ tự thực hiện bên trong script

Step 7 (kiểm tra năm cuối) chạy **trước** Step 6 (tính liên tục theo năm). Lý do: Step 6 cần biết năm cuối dùng được của từng file để tính biên hiệu dụng, nếu không thì một năm bị cắt cụt sẽ làm mọi chuỗi kết thúc đúng hạn bị gắn nhãn "kết thúc sớm". Chi tiết ở mục 8. Thứ tự đánh số của các Step trong báo cáo giữ nguyên 1→7 để dễ đọc.

### Giới hạn của bước ghi file

Script ghi từng đầu ra ra file tạm `.<tên>.tmp` rồi mới `replace()` sang tên chính, nên không bao giờ để lại file bị ghi dở. Nhưng đây là **sáu lần replace tuần tự**, không phải một giao dịch nguyên tử: nếu tiến trình bị dừng giữa chừng thì một phần đầu ra là bản mới, một phần là bản cũ. Trên Windows không có cơ chế nguyên tử cho nhiều file cùng lúc. Khi nghi ngờ, chạy lại toàn bộ script — chi phí chỉ khoảng 2 giây và kết quả tái lập byte-identical.

Việc dọn file cũ `00_data_profile.xlsx` nằm **ngoài** khối try chính. Nếu file đó đang mở trong Excel và không xóa được, script in cảnh báo nhưng vẫn báo thành công, vì toàn bộ đầu ra đã ghi xong.

---

## 3. Step 1 — Lập hồ sơ dữ liệu

### Ý nghĩa và vai trò

Step 1 tạo “hồ sơ sức khỏe” cho từng cột chỉ số. Nó cho biết quy mô, phạm vi thời gian, mức thiếu, tỷ lệ số 0 và miền giá trị trước khi quyết định dùng dữ liệu như thế nào.

Bước này đặc biệt cần thiết vì một file có thể chứa nhiều chỉ số với mức thiếu khác nhau. Do đó, mỗi dòng profile đại diện cho **một cột chỉ số trong một file**, không nhất thiết đại diện cho cả file. Ví dụ, file `03` có bốn chỉ số nên tạo bốn dòng profile.

### Phương pháp và cách đọc các cột

Trước khi tính thống kê, script yêu cầu mỗi file có `Entity`, `Code`, `Year` và ít nhất một cột chỉ số. `Entity` không được rỗng; `Year` phải là số nguyên hữu hạn; giá trị không rỗng trong cột chỉ số phải chuyển được thành số hữu hạn.

| Cột | Đại diện cho thông tin gì? | Vì sao cần? |
|---|---|---|
| `file_name` | Tên CSV nguồn | Truy ngược thống kê về đúng dữ liệu gốc |
| `metric_column` | Cột chỉ số đang được khảo sát | Tách riêng chất lượng từng chỉ số trong file nhiều cột |
| `row_count` | Tổng số dòng của file | Cho biết quy mô nguồn; lặp lại giữa các chỉ số cùng file |
| `entity_count` | Số `Entity` khác nhau | Đo bề rộng độ phủ thực thể ban đầu |
| `year_min`, `year_max` | Năm nhỏ nhất và lớn nhất trong file | Xác định hai đầu phạm vi thời gian |
| `year_count` | Số năm khác nhau thực sự xuất hiện | Không đồng nghĩa chuỗi liên tục; chỉ cho biết số năm có mặt |
| `missing_count` | Số ô CSV rỗng hoặc `NaN` trong chỉ số | Đo thiếu dữ liệu trực tiếp |
| `missing_pct` | `missing_count / row_count × 100` | So sánh mức thiếu giữa các file có quy mô khác nhau |
| `valid_numeric_count` | Số giá trị số hữu hạn, gồm cả 0 | Cho biết số quan sát có thể dùng để tính toán |
| `invalid_numeric_count` | Số ô không rỗng nhưng không phải số hữu hạn | Phân biệt dữ liệu lỗi với dữ liệu thiếu; nếu lớn hơn 0 thì script dừng |
| `zero_count` | Số giá trị số bằng đúng 0 | Số 0 là quan sát hợp lệ, không phải dữ liệu thiếu |
| `zero_pct_of_valid` | `zero_count / valid_numeric_count × 100` | Đo mức tập trung tại 0 mà không để ô thiếu làm sai mẫu số |
| `min_value`, `max_value` | Giá trị nhỏ nhất/lớn nhất, bỏ qua ô thiếu nhưng giữ số 0 | Phát hiện giá trị âm, cực trị, sai đơn vị hoặc tỷ lệ vượt miền hợp lệ |

Khi không có dữ liệu sai kiểu:

```text
row_count = missing_count + valid_numeric_count
```

`year_count` không kiểm tra được lỗ hổng. Chẳng hạn các năm `2000, 2001, 2003` cho `year_count = 3`, nhưng năm 2002 vẫn thiếu; Step 6 mới xác định vấn đề này.

### Kết quả thực tế

- Đọc đủ 17 CSV và lập hồ sơ cho 23 cột chỉ số.
- Quy mô dao động từ 758 đến 8.851 dòng và từ 33 đến 251 thực thể.
- Phạm vi tổng thể trải từ 1965 đến 2022; từng nguồn kết thúc ở 2020, 2021 hoặc 2022.
- Không phát hiện `Entity` rỗng, `Year` không hợp lệ hoặc giá trị chỉ số sai kiểu số hữu hạn.
- Ô thiếu tập trung ở file `02` và `03`. Các file đơn chỉ số còn lại không có ô thiếu trong chính cột chỉ số.
- Số 0 xuất hiện nhiều, đặc biệt ở điện gió và điện mặt trời: khoảng 66,71% quan sát hợp lệ của gió trong file `03`/`08`, và 68,92% của mặt trời trong file `03`/`12`.
- `min_value` của toàn bộ 23 chỉ số là 0. Đây không phải bằng chứng rằng dữ liệu thiếu đã được điền 0.
- Một số tỷ trọng điện có cực đại hơi vượt 100% (`100.000015` và `100.000010`). Sai lệch rất nhỏ này cần được xử lý bằng quy tắc dung sai/làm tròn ở Phase 2, không nên diễn giải như tỷ trọng thực sự vượt 100%.

### Hệ quả cho Phase 2

- Giữ riêng `NULL` và 0 trong mô hình dữ liệu sạch.
- Chuẩn hóa kiểu và tên cột nhưng không làm mất nguồn gốc `source_file`.
- Thiết lập kiểm tra miền cho tỷ lệ phần trăm với dung sai số thực có giải thích.
- Không chọn nguồn chỉ dựa vào số dòng hoặc min/max; cần Step 2–5 để đánh giá độ phủ và trùng lặp.

### Giới hạn diễn giải

- `entity_count` bao gồm quốc gia, `World`, châu lục, nhóm thu nhập và thực thể tổng hợp/lịch sử; không đồng nghĩa với số quốc gia.
- `missing_count = 0` không chứng minh chuỗi đủ mọi năm hoặc đủ mọi quốc gia.
- Số 0 có thể là giá trị thực, “chưa phát sinh công nghệ” hoặc quy ước của nguồn; chỉ profile không xác định được ngữ nghĩa nghiệp vụ.

---

## 4. Step 2 — Lập tầng độ phủ và đo mức mất dữ liệu khi join

### Ý nghĩa và vai trò

Step 2 nhóm các file có cùng chữ ký độ phủ `(số thực thể, năm đầu, năm cuối)`, sau đó đo giao và hợp thực tế của `Entity`, `Year` và khóa `(Entity, Year)`.

Đây là bằng chứng để lựa chọn chiến lược join. Hai file có cùng số thực thể và cùng khoảng năm vẫn có thể thiếu các cặp thực thể–năm khác nhau, nên không thể suy luận khả năng join chỉ từ header hoặc số dòng.

### Phương pháp và cách đọc các cột

- `entity_union_count`: số thực thể có mặt trong ít nhất một file của tầng.
- `entity_intersection_count`: số thực thể có mặt trong mọi file của tầng.
- `entity_retention_pct = entity_intersection_count / entity_union_count × 100`.
- `common_year_count`: số giá trị năm cùng xuất hiện trong tất cả file của tầng.
- `key_count_min`, `key_count_max`: số khóa `(Entity, Year)` nhỏ nhất/lớn nhất giữa các file.
- `key_union_count`: số khóa có mặt trong ít nhất một file.
- `key_intersection_count`: số khóa có mặt trong tất cả file.
- `key_retention_pct = key_intersection_count / key_union_count × 100`.

`entity_retention_pct` chỉ kiểm tra tên thực thể. `key_retention_pct` chặt hơn vì yêu cầu cùng thực thể và cùng năm.

### Kết quả thực tế

| Tầng | Thành viên | Thực thể | Năm | Giao/hợp khóa | Giữ lại khóa |
|---|---|---:|---:|---:|---:|
| T1 | `03`, `05`, `08`, `12` | 251 | 1965–2022 | 8.663 / 8.851 | 97,8759% |
| T2 | `04`, `07`, `11`, `15` | 246 | 1985–2022 | 6.870 / 6.926 | 99,1915% |
| T3 | `01`, `02`, `06`, `10`, `14` | 104 | 1965–2021 | 5.426 / 5.610 | 96,7201% |
| T4 | `13` | 64 | 1996–2021 | 1.659 / 1.659 | 100% |
| T5 | `09` | 62 | 1995–2021 | 1.540 / 1.540 | 100% |
| T6 | `16` | 35 | 1990–2021 | 1.081 / 1.081 | 100% |
| T7 | `17` | 33 | 1975–2020 | 758 / 758 | 100% |

Trong ba tầng nhiều file, tập tên `Entity` khớp 100%, nhưng khóa `(Entity, Year)` không khớp hoàn toàn. Chênh lệch hợp–giao lần lượt là 188 khóa ở T1, 56 ở T2 và 184 ở T3.

Kết quả của toàn bộ 17 file:

```text
Hợp Entity:               256
Giao Entity:                8  (3,125%)
Hợp khóa Entity–Year:   8.997
Giao khóa Entity–Year:    168  (1,8673%)
Số năm chung:              21
```

Nếu `INNER JOIN` cả 17 nguồn, 248/256 thực thể và 8.829/8.997 khóa sẽ bị loại. Phần giao 168 khóa đúng bằng 8 thực thể × 21 năm, nhưng đây chỉ là một panel rất nhỏ, không đại diện cho toàn bộ nguồn.

### Hệ quả cho Phase 2

- Không `INNER JOIN` toàn bộ 17 file.
- Dựng spine `quốc gia × năm`, sau đó `LEFT JOIN` từng chỉ số để dữ liệu thiếu xuất hiện rõ dưới dạng `NULL`.
- Khi phân tích một cặp chỉ số, chỉ giới hạn trên giao của đúng hai chỉ số đó; không dùng giao của toàn bộ nguồn.
- Các file công suất, biofuel và geothermal phải là bảng/chỉ số bổ trợ, không được dùng làm điều kiện bắt buộc của panel chính.

### Giới hạn diễn giải

- Tỷ lệ 100% của T4–T7 là hệ quả toán học vì mỗi tầng chỉ có một file; nó không có nghĩa độ phủ tốt. Các tầng này chỉ có 33–64 thực thể.
- Độ phủ khóa không cho biết hai file đo cùng khái niệm hoặc có cùng giá trị; Step 3 mới kiểm tra điều đó.

---

## 5. Step 3 — Kiểm tra trùng lặp và xung đột giá trị

### Ý nghĩa và vai trò

Step 2 trả lời “hai nguồn có chung khóa không”; Step 3 trả lời “trên khóa chung, hai nguồn cùng đo một đại lượng có cho cùng giá trị không”.

Bước này ngăn việc nạp cùng một chỉ số hai lần, phát hiện nguồn riêng chỉ là tập con của nguồn tổng hợp, tách thiếu dữ liệu khỏi xung đột và cung cấp bằng chứng để chọn nguồn chính ở Phase 2.

### Phạm vi kiểm tra

Chỉ 10 cặp đã xác định là cùng khái niệm và cùng đơn vị TWh được so sánh, thuộc **5 file** (`02`, `03`, `05`, `08`, `12`):

- hydro: mọi cặp giữa file `02`, `03`, `05`;
- wind: mọi cặp giữa `02`, `03`, `08`;
- solar: mọi cặp giữa `02`, `03`, `12`;
- other renewables: file `02` với `03`.

**Mười hai file còn lại không được so sánh với bất kỳ file nào** (`01`, `04`, `06`, `07`, `09`, `10`, `11`, `13`, `14`, `15`, `16`, `17`), vì mỗi file đo một đại lượng mà không file nào khác trong bộ đo cùng đại lượng và cùng đơn vị. Cụ thể: nhóm `04`/`07`/`11`/`15` là tỷ trọng trên tổng **điện năng**, nhóm `01`/`06`/`10`/`14` là tỷ trọng trên **năng lượng sơ cấp quy đổi** — hai mẫu số khác nhau nên không phải bản trùng của nhau; `09`, `13`, `17` là công suất (GW), `16` là sản lượng biofuel.

Hệ quả: **Step 3 không kết luận gì về khả năng trùng lặp của 12 file này.** Nếu Phase 2 cần biết, phải kiểm tra riêng bằng cách khác (ví dụ đối chiếu tỷ trọng tính lại từ TWh với tỷ trọng có sẵn).

### Phương pháp và cách đọc kết quả

Mỗi cặp được outer join one-to-one theo `(Entity, Year)`. Các cột tổng hợp chính gồm:

- `left_only_count`, `right_only_count`, `shared_key_count`: phân rã phạm vi khóa;
- `both_missing_count`, `left_missing_only_count`, `right_missing_only_count`: phân rã trạng thái thiếu trên khóa chung;
- `comparable_count`: số khóa chung mà cả hai phía đều có giá trị;
- `exact_match_count`: số giá trị bằng chính xác;
- `approximate_match_count`: số giá trị không bằng chính xác nhưng nằm trong `numpy.isclose(rtol=1e-9, atol=1e-12)`;
- `value_conflict_count`: số giá trị khác ngoài dung sai;
- `match_pct`, `mean_abs_diff`, `max_abs_diff`: mức khớp và quy mô sai lệch;
- `classification`, `recommendation`: phân loại và khuyến nghị sử dụng.

#### Phân tầng độ lớn: vì sao `value_conflict_count` một mình là không đủ

Dung sai `rtol=1e-9` rất chặt, nên **mọi** khác biệt độ chính xác giữa hai nguồn đều rơi vào `value_conflict_count`. File `03` làm tròn phần lớn giá trị tới 2 chữ số thập phân, file `02` giữ đủ độ chính xác; kết quả là `0.00` so với `0.004` bị đếm là "xung đột". Nếu chỉ đọc `match_pct`, người đọc sẽ kết luận hai nguồn mâu thuẫn ở hơn một phần ba số dòng — điều không đúng về mặt nội dung.

Vì vậy mỗi dòng xung đột được gắn thêm `conflict_tier`:

```text
MATERIAL     khi  abs_diff > 0,05 TWh  VÀ  relative_diff_pct > 1%
IMMATERIAL   khi ngược lại
```

**Phải vượt cả hai ngưỡng.** Chỉ dùng tỷ lệ thì `0` so với `0,005 TWh` thành lệch 100%; chỉ dùng tuyệt đối thì `0,5 TWh` trên nền `1.200 TWh` của một nước lớn cũng bị gọi là lệch. Chỉ khi vừa lớn về lượng vừa lớn về tỷ lệ thì mới đúng nghĩa "khác nhau đáng kể".

Chọn `0,05 TWh` vì làm tròn 2 chữ số chỉ dịch chuyển giá trị tối đa `0,005 TWh`, nên đây là biên an toàn gấp mười lần. Chọn `1%` làm mức quy ước cho "không phải khác biệt do phiên bản hoặc quy tắc làm tròn".

⚠️ Nhãn là `IMMATERIAL` chứ không phải `ROUNDING`. Phần lớn nhóm này thật sự là sai số làm tròn (trung vị `0,0031 TWh` ở cấp quốc gia), nhưng nó **còn chứa các chênh lệch tuyệt đối lớn nằm trên nền giá trị rất lớn** — cao nhất tới `39,48 TWh` mà vẫn dưới 1%. Gọi nhóm này là "làm tròn" sẽ là mô tả sai.

Dòng chi tiết còn có cột `is_aggregate`: `True` khi `Entity` không có `Code` ở bất kỳ file nào trong 17 file. Đây là chỉ báo sơ bộ cho thực thể tổng hợp (châu lục, nhóm thu nhập, khối chính trị); phân loại chính thức là việc của Phase 2.

#### Các lớp kết quả

| Phân loại | Ý nghĩa |
|---|---|
| `exact_duplicate` | Khóa, trạng thái thiếu và giá trị giống hoàn toàn |
| `redundant_subset` | Tập quan sát không rỗng của một nguồn là tập con và khớp hoàn toàn với nguồn kia |
| `approximate_duplicate` | Chỉ khác trong dung sai số thực |
| `immaterial_variant` | Có khác biệt nhưng **không dòng nào** vượt ngưỡng `MATERIAL` |
| `conflicting_overlap` | Có ít nhất một dòng vượt ngưỡng `MATERIAL` |
| `insufficient_overlap` | Không đủ phần giao để kết luận |

CSV chi tiết chỉ ghi `VALUE_CONFLICT` và `MISSING_MISMATCH`, kèm `conflict_tier`, `is_aggregate`, hai nguồn/cột, `Entity`, `Year`, hai giá trị, sai lệch tuyệt đối và sai lệch tương đối.

### Kết quả thực tế

| Cặp | So sánh được | Xung đột | `IMMATERIAL` | `MATERIAL` | Khớp thô | Khớp sau lọc | Phân loại |
|---|---:|---:|---:|---:|---:|---:|---|
| Hydro `02–03` | 5.603 | 2.010 | 1.469 | 541 | 64,13% | **90,34%** | `conflicting_overlap` |
| Hydro `02–05` | 5.603 | 2.010 | 1.469 | 541 | 64,13% | **90,34%** | `conflicting_overlap` |
| Hydro `03–05` | 8.840 | 0 | 0 | 0 | 100% | 100% | `redundant_subset` |
| Wind `02–03` | 5.445 | 1.676 | 1.458 | 218 | 69,22% | **96,00%** | `conflicting_overlap` |
| Wind `02–08` | 5.445 | 1.676 | 1.458 | 218 | 69,22% | **96,00%** | `conflicting_overlap` |
| Wind `03–08` | 8.676 | 0 | 0 | 0 | 100% | 100% | `redundant_subset` |
| Solar `02–03` | 5.442 | 1.564 | 1.248 | 316 | 71,26% | **94,19%** | `conflicting_overlap` |
| Solar `02–12` | 5.442 | 1.564 | 1.248 | 316 | 71,26% | **94,19%** | `conflicting_overlap` |
| Solar `03–12` | 8.683 | 0 | 0 | 0 | 100% | 100% | `redundant_subset` |
| Other renewables `02–03` | 5.466 | 1.668 | 960 | 708 | 69,48% | **87,05%** | `conflicting_overlap` |

Cột "Khớp thô" (`match_pct`) đếm mọi khác biệt kể cả làm tròn; "Khớp sau lọc" (`material_match_pct`) chỉ trừ đi các dòng `MATERIAL`. Khoảng cách giữa hai cột chính là phần nhiễu độ chính xác. Với wind, hai nguồn thật sự khớp 96% chứ không phải 69%.

Ba cặp `03–05`, `03–08`, `03–12` khớp tuyệt đối trên toàn bộ quan sát không rỗng của file riêng; vì file `03` có độ phủ rộng hơn và chứa cả bốn công nghệ, các file `05`, `08`, `12` là ứng viên loại khỏi bảng canonical.

#### Chênh lệch nằm ở đâu

File chi tiết có 12.180 dòng: 12.168 `VALUE_CONFLICT` (9.310 `IMMATERIAL` + 2.858 `MATERIAL`) và 12 `MISSING_MISMATCH`.

| Tầng | Loại thực thể | Số dòng | Chênh lệch trung vị | Chênh lệch lớn nhất |
|---|---|---:|---:|---:|
| `MATERIAL` | quốc gia | 2.011 | 0,4472 TWh | 18,81 TWh |
| `MATERIAL` | tổng hợp | 847 | **2,6463 TWh** | **159,17 TWh** |
| `IMMATERIAL` | quốc gia | 8.617 | 0,0031 TWh | 39,48 TWh |
| `IMMATERIAL` | tổng hợp | 693 | 0,1766 TWh | 11,07 TWh |

Hai kết luận khác nhau, không được lẫn:

1. **Về số lượng dòng**, lệch đáng kể xuất hiện ở cả hai cấp, và cấp quốc gia còn nhiều dòng hơn (2.011 so với 847).
2. **Về quy mô**, lệch ở cấp tổng hợp lớn hơn một bậc: trung vị gấp gần 6 lần, giá trị lớn nhất gấp hơn 8 lần.

Năm chênh lệch tuyệt đối lớn nhất đều thuộc thực thể tổng hợp: `Lower-middle-income countries` (159,17 TWh), `Upper-middle-income countries` (128,86), `Europe` (32,18), `High-income countries` (22,16), `Asia` (21,81). Đây là dấu hiệu hai nguồn gộp trên **tập quốc gia thành phần khác nhau**, chứ không phải mâu thuẫn về giá trị của từng nước.

#### Mười nước ASEAN

| Nước | `IMMATERIAL` | `MATERIAL` | Chênh lệch lớn nhất |
|---|---:|---:|---:|
| Vietnam | 90 | **0** | 0,0050 TWh |
| Indonesia | 102 | 18 | 11,16 TWh |
| Philippines | 95 | 39 | 2,47 TWh |
| Thailand | 94 | 34 | 0,95 TWh |
| Malaysia | 54 | 2 | 1,57 TWh |
| Singapore | 18 | 32 | 0,64 TWh |

Bốn nước còn lại (Myanmar, Cambodia, Laos, Brunei) không có mặt trong file `02` nên không xuất hiện ở bảng này.

**Việt Nam không có một dòng `MATERIAL` nào**; chênh lệch lớn nhất giữa hai nguồn là `0,005 TWh` — đúng bằng biên độ làm tròn 2 chữ số. Với riêng Việt Nam, hai nguồn thống nhất.

Lưu ý: 12.168 không phải 12.168 sai lệch độc lập. Cùng một giá trị của file `02` được ghi lại khi so với cả file tổng hợp `03` và file riêng `05`, `08` hoặc `12`.

### Hệ quả cho Phase 2

- Ưu tiên file `03` cho hydro, wind, solar và other renewables theo TWh; không nạp lại các chỉ số tương ứng từ `05`, `08`, `12`.
- Không coalesce hoặc lấy trung bình file `02` với `03`. Các cột TWh của `02` phải được giữ tách theo provenance hoặc loại khỏi panel canonical cho đến khi xác minh định nghĩa/phiên bản nguồn.
- **Ưu tiên kiểm tra các thực thể tổng hợp trước.** Chênh lệch lớn nhất tập trung ở đó, và đúng những thực thể này là mẫu số của mọi chỉ số "tỷ trọng khu vực" ở Phase 3. Nếu Phase 2 chọn nhầm nguồn cho `Lower-middle-income countries`, sai số kéo theo là hơn 150 TWh.
- Với Việt Nam, việc chọn `02` hay `03` không làm đổi kết quả quá `0,005 TWh`. Đây là lý do phần phân tích Việt Nam có thể tiến hành mà không cần chờ giải quyết xong provenance.
- Giữ `source_file` trong fact table để có thể truy vết mọi lựa chọn nguồn.

### Giới hạn diễn giải

- `redundant_subset` chỉ nói về **cột chỉ số được so sánh và tập quan sát không rỗng**, không khẳng định toàn bộ hai file giống hệt theo byte, schema hoặc phạm vi khóa.
- Xung đột của file `02` không chứng minh `02` hay `03` sai. Nguyên nhân có thể là phiên bản, nhà cung cấp, phương pháp hoặc định nghĩa chỉ số khác nhau.
- Chỉ các cột cùng đơn vị TWh được so sánh. **12 file khác không được kiểm tra trùng lặp** — xem phần "Phạm vi kiểm tra" ở trên.
- Hai ngưỡng `0,05 TWh` và `1%` là lựa chọn có lý do nhưng vẫn là lựa chọn. Đổi ngưỡng sẽ đổi số dòng `MATERIAL`; đổi kết luận về **thứ tự độ lớn giữa quốc gia và tổng hợp** thì khó hơn nhiều, vì khoảng cách ở đó là gần một bậc.
- `is_aggregate` suy ra từ việc thiếu `Code`, không phải từ một bảng phân loại chính thức. Có thực thể tổng hợp mang mã giả `OWID_*` sẽ **không** bị cờ này bắt. Phase 2 phải phân loại lại đầy đủ.
- `IMMATERIAL` không có nghĩa "giống nhau". Nó có nghĩa "không vượt cả hai ngưỡng đã chọn".

---

## 6. Step 4 — Kiểm tra tính nhất quán của khóa join

### Ý nghĩa và vai trò

Step 4 kiểm tra liệu cùng một thực thể có được viết nhất quán giữa các file, quan hệ `Entity`–`Code` có mâu thuẫn không, và khóa `(Entity, Year)` có duy nhất trong từng file không.

Nếu khóa không đáng tin cậy, join có thể tách một quốc gia thành nhiều thực thể, ghép nhầm hai khu vực hoặc nhân đôi dòng. Kiểm tra fuzzy đặc biệt quan trọng vì tên gần giống về ký tự có thể khác hoàn toàn về địa lý.

### Phương pháp và cách đọc kết quả

Tên được chuẩn hóa **chỉ để audit**, không thay đổi dữ liệu gốc: Unicode NFKC, bỏ/gộp khoảng trắng và `casefold`. Mọi cặp tên có similarity từ 0,88 trở lên được liệt kê để review; script không tự động merge.

Mười kiểm tra `J1`–`J10` bao phủ:

- số tên `Entity` chính xác trong hợp 17 file và số tên có mặt trong mọi file;
- biến thể khoảng trắng và va chạm sau chuẩn hóa;
- một `Code` gắn nhiều `Entity` hoặc một `Entity` gắn nhiều `Code`;
- khóa `(Entity, Year)` trùng trong từng file;
- thực thể thiếu `Code`;
- ứng viên fuzzy và alias được cùng `Code` xác nhận.

### Kết quả thực tế

| Kiểm tra | Kết quả | Trạng thái |
|---|---:|---|
| Tên `Entity` chính xác trong hợp 17 file | 256 | `INFO` |
| `Entity` có mặt trong đủ 17 file | 8 | `INFO` |
| Biến thể khoảng trắng | 0 | `PASS` |
| Va chạm sau NFKC/casefold/strip | 0 | `PASS` |
| Một `Code` → nhiều `Entity` | 0 | `PASS` |
| Một `Entity` → nhiều `Code` | 0 | `PASS` |
| Dòng trùng khóa `(Entity, Year)` | 0 | `PASS` |
| `Entity` thiếu `Code` trong ít nhất một file | 39 | `REVIEW` |
| Cặp tên có similarity ≥ 0,88 | 4 | `REVIEW` |
| Alias fuzzy được cùng `Code` xác nhận | 0 | `INFO` |

Bốn cặp fuzzy là:

| Tên thứ nhất | Tên thứ hai | Similarity | Kết luận |
|---|---|---:|---|
| `Eastern Africa (BP)` | `Western Africa (BP)` | 0,9474 | Khác khu vực; không gộp |
| `Lower-middle-income countries` | `Upper-middle-income countries` | 0,8966 | Khác nhóm thu nhập; không gộp |
| `Other South & Central America` | `South & Central America` | 0,8846 | Khác phạm vi; không tự động gộp |
| `South Africa` | `South America` | 0,8800 | Quốc gia và khu vực khác nhau; không gộp |

CSV chi tiết có 43 dòng: 39 `BLANK_CODE_ENTITY` và 4 `FUZZY_CANDIDATE`.

### Hệ quả cho Phase 2

- Join chính xác theo `(Entity, Year)`; không auto-fuzzy.
- `Code` dùng để kiểm chứng danh tính khi có, không dùng làm khóa duy nhất vì 39 thực thể thiếu mã.
- Dựng `dim_entity` để phân loại quốc gia, vùng, nhóm tổng hợp và thực thể lịch sử trước khi tính thống kê quốc gia.
- Nếu sau này cần alias, chỉ thêm vào bảng ánh xạ sau khi review ngữ nghĩa/provenance, không suy ra từ similarity đơn thuần.

### Giới hạn diễn giải

- Không có va chạm tên hiện tại không bảo đảm mọi `Entity` là quốc gia hoặc mọi tên có cùng chuẩn địa chính trị.
- `Code` trống thường gặp ở thực thể tổng hợp, nhưng Step 4 chưa chính thức phân loại loại thực thể.
- Fuzzy matching cho ra ứng viên ngôn ngữ, không phải bằng chứng hai tên cùng một thực thể; cặp `South Africa`–`South America` minh họa rủi ro ghép sai.

---

## 7. Step 5 — Đánh giá độ phủ 10 nước ASEAN

### Ý nghĩa và vai trò

Step 5 kiểm tra phạm vi nghiên cứu “Việt Nam và ASEAN-10” có thực sự được dữ liệu hỗ trợ hay không. Nếu một chỉ số chỉ có 2–6 nước nhưng vẫn được trình bày như toàn ASEAN, xếp hạng và tổng khu vực sẽ bị thiên lệch.

### Phương pháp và cách đọc kết quả

Script dùng danh sách tên chính xác trong `config.py`:

```text
Vietnam, Thailand, Indonesia, Philippines, Malaysia,
Singapore, Myanmar, Cambodia, Laos, Brunei
```

Ma trận có 10 × 17 = 170 tổ hợp nước–file. CSV chi tiết gồm:

- `country`, `file_name`;
- `present`: nước có ít nhất một dòng trong file;
- `row_count`;
- `year_min`, `year_max`, `year_count`.

Một ô ma trận dạng `YES | 57 rows | 1965-2021` cho biết nước có 57 khóa năm trong khoảng đó; `NO` cho biết tên nước không xuất hiện.

### Kết quả thực tế

Tám file có mặt đủ 10 nước ASEAN:

```text
03, 04, 05, 07, 08, 11, 12, 15
```

Sau khi kết hợp bằng chứng Step 3, tập nguồn không trùng phù hợp cho panel chính là:

- `03` cho sản lượng điện hydro, wind, solar và other renewables (TWh);
- `04` cho tỷ trọng năng lượng tái tạo trong điện;
- `07`, `11`, `15` cho tỷ trọng hydro, wind và solar trong điện.

Năm file chỉ có 6/10 nước:

```text
01, 02, 06, 10, 14
```

Bốn nước thiếu đồng loạt là Myanmar, Cambodia, Laos và Brunei. Các file này chỉ hỗ trợ panel gồm Vietnam, Thailand, Indonesia, Philippines, Malaysia và Singapore.

Các nguồn hẹp:

| File/chỉ số | ASEAN có dữ liệu | Số nước |
|---|---|---:|
| `09` — công suất gió | Thailand, Philippines | 2 |
| `13` — công suất mặt trời | Vietnam, Thailand, Philippines, Malaysia | 4 |
| `16` — biofuel | Thailand, Indonesia | 2 |
| `17` — công suất địa nhiệt | Indonesia, Philippines | 2 |

Số file có mặt theo nước:

| Nước | Số file trên 17 |
|---|---:|
| Vietnam | 14 |
| Thailand | 16 |
| Indonesia | 15 |
| Philippines | 16 |
| Malaysia | 14 |
| Singapore | 13 |
| Myanmar | 8 |
| Cambodia | 8 |
| Laos | 8 |
| Brunei | 8 |

Vietnam có độ phủ tốt ở sản lượng và tỷ trọng; xuất hiện trong file `13` về công suất mặt trời giai đoạn 2000–2021, nhưng không xuất hiện trong `09` (công suất gió), `16` (biofuel) hoặc `17` (địa nhiệt).

Myanmar, Cambodia, Laos và Brunei bắt đầu có mặt từ năm 2000 trong nhóm nguồn rộng. Vì vậy `2000–2021` là cửa sổ ứng viên để so sánh đủ ASEAN-10; Step 6 và Step 7 xác nhận tính liên tục và năm kết thúc.

### Hệ quả cho Phase 2

- Chỉ gọi kết quả là “ASEAN-10” khi đủ 10 nước hoặc công khai rõ nước bị thiếu.
- Dùng `03`, `04`, `07`, `11`, `15` cho phân tích chính toàn khối.
- Dùng `01`, `02`, `06`, `10`, `14` cho phân tích phụ ASEAN-6 và ghi rõ mẫu.
- Dùng `09`, `13`, `16`, `17` làm case study/tập con; không xếp hạng toàn ASEAN từ các nguồn này.
- Không thể tính hệ số công suất gió cho Vietnam từ bộ dữ liệu hiện có vì thiếu công suất gió của Vietnam.

### Giới hạn diễn giải

- `present = YES` chỉ có nghĩa `Entity` xuất hiện trong file; không bảo đảm mọi cột chỉ số ở mọi năm đều khác `NaN`.
- `year_min`–`year_max` không bảo đảm chuỗi liên tục; Step 6 mới kiểm tra năm thiếu ở giữa.
- Tổng hoặc trung bình khu vực trên tập nước thay đổi theo năm không thể so sánh trực tiếp với panel cố định mà không ghi rõ mẫu.

---

## 8. Step 6 — Kiểm tra tính liên tục theo năm

### Ý nghĩa và vai trò

Step 6 phân biệt hai loại thiếu thời gian có ý nghĩa khác nhau:

- chuỗi bắt đầu muộn/kết thúc sớm so với phạm vi file;
- lỗ hổng nằm giữa năm đầu và năm cuối của chính thực thể.

Sự phân biệt này quyết định cách tính YoY, CAGR, rolling average và quyết định có nội suy hay không. Không nên tạo lịch sử giả cho những năm trước khi một quốc gia bắt đầu được ghi nhận.

### Phương pháp và cách đọc các cột

Mỗi dòng CSV đại diện cho một chuỗi `Entity`–file. Kiểm tra này dựa trên sự tồn tại của khóa `(Entity, Year)`, chưa xét `NaN` trong từng chỉ số.

- `file_year_min`, `file_year_max`: biên năm của toàn file.
- `entity_year_min`, `entity_year_max`: biên năm của thực thể.
- `observed_year_count`: số năm thực tế có khóa.
- `expected_span_year_count`: số năm từ `entity_year_min` đến `entity_year_max`, tính cả hai đầu.
- `internal_gap_count`, `internal_gap_ranges`: số năm và các khoảng thiếu nằm giữa chuỗi.
- `leading_boundary_year_count`, `trailing_boundary_year_count`: số năm bị cắt ở đầu/cuối so với biên của file.
- `boundary_side`: `NONE`, `LEADING`, `TRAILING` hoặc `BOTH`.
- `coverage_pattern`: hình dạng chuỗi.
- `interpolation_decision`: quyết định tự động từ audit.

Bốn dạng chuỗi:

| Dạng | Ý nghĩa |
|---|---|
| `FULL_SPAN` | Có mặt suốt phạm vi năm của file |
| `BOUNDARY_ONLY` | Liên tục trong phạm vi riêng nhưng bắt đầu muộn hoặc kết thúc sớm |
| `INTERNAL_GAPS` | Có năm thiếu giữa chuỗi, không bị cắt biên |
| `INTERNAL_AND_BOUNDARY` | Vừa có lỗ hổng giữa, vừa bị cắt ở biên |

Với mọi chuỗi:

```text
observed_year_count + internal_gap_count = expected_span_year_count
```

#### Hai cách đo biên cuối: vì sao cần cả hai

`trailing_boundary_year_count` đo so với `file_year_max`, tức là năm lớn nhất **có mặt** trong file. Nhưng Step 7 cho thấy tám file có năm 2022 chỉ chứa 29 trên hơn 240 thực thể. Với các file đó, mọi thực thể có dữ liệu đầy đủ đến 2021 vẫn bị tính `trailing = 1` và gắn nhãn `BOUNDARY_ONLY`, nghĩa là "kết thúc sớm".

Chúng không kết thúc sớm. File có một năm cụt.

Vì vậy mỗi chuỗi được đo thêm một lần nữa, lấy mốc là năm cuối **dùng được** theo Step 7:

| Cột | Đo so với |
|---|---|
| `file_year_max`, `trailing_boundary_year_count`, `boundary_side`, `coverage_pattern` | Năm lớn nhất có mặt trong file — bằng chứng thô |
| `effective_file_year_max`, `effective_trailing_boundary_year_count`, `effective_boundary_side`, `coverage_pattern_effective` | `recommended_end_year` của Step 7 — độ phủ thật |

Ví dụ một quốc gia trong file `03` có dữ liệu liên tục 1965–2021:

```text
file_year_max                = 2022      effective_file_year_max      = 2021
trailing_boundary            = 1         effective_trailing_boundary  = 0
coverage_pattern             = BOUNDARY_ONLY                          = FULL_SPAN
```

**Dùng cột `*_effective` khi cần biết độ phủ thật; giữ cột thô làm bằng chứng cho quyết định cắt năm 2022.** Đây cũng là lý do Step 7 chạy trước Step 6 trong script (xem mục 2).

Cùng lỗi này từng tạo ra một mâu thuẫn nhìn thấy được: `CIS (BP)` có cùng khoảng năm 1965–2021 nhưng ở file `08` bị gắn `INTERNAL_AND_BOUNDARY` còn ở file `10` là `INTERNAL_GAPS` — chỉ vì file `08` có năm 2022 còn file `10` thì không.

#### Ba giá trị của `interpolation_decision`

| Giá trị | Nghĩa |
|---|---|
| `NOT_NEEDED` | Không có lỗ hổng ở giữa |
| `SAMPLING_GRID_NOT_MISSING` | Các khoảng trống dài bằng nhau và cách đều nhau → nhịp báo cáo theo mốc, không phải dữ liệu bị mất |
| `DO_NOT_INTERPOLATE_REVIEW_SOURCE` | Lỗ hổng không theo quy luật → phải kiểm tra nguồn |

Cả hai nhãn sau đều **chặn nội suy**, nhưng nghĩa khác nhau: một bên là dữ liệu vốn chỉ được thu thập 5 năm một lần, bên kia là dữ liệu đáng lẽ phải có mà không có. Quy tắc nhận diện đòi hỏi **ít nhất hai khoảng trống**, vì một khoảng đơn lẻ không đủ cơ sở kết luận là nhịp lấy mẫu.

### Kết quả thực tế

Đã kiểm tra 2.702 chuỗi `Entity`–file:

| Dạng chuỗi | Đo thô | Đo hiệu dụng |
|---|---:|---:|
| `FULL_SPAN` | 682 | **1.215** |
| `BOUNDARY_ONLY` | 1.985 | 1.452 |
| `INTERNAL_GAPS` | 3 | 5 |
| `INTERNAL_AND_BOUNDARY` | 32 | 30 |

**535 chuỗi đổi nhãn** giữa hai cách đo. Số chuỗi phủ đủ tăng gần gấp đôi khi loại bỏ ảnh hưởng của năm cụt — đó là quy mô của hiện tượng nhiễu mô tả ở trên.

Chênh lệch theo file:

| File | Số thực thể | `FULL_SPAN` thô | `FULL_SPAN` hiệu dụng | Chênh |
|---|---:|---:|---:|---:|
| `03 modern-renewable-prod` | 251 | 22 | 89 | +67 |
| `04 share-electricity-renewables` | 246 | 22 | 89 | +67 |
| `05 hydropower-consumption` | 251 | 22 | 88 | +66 |
| `07 share-electricity-hydro` | 246 | 25 | 99 | +74 |
| `08 wind-generation` | 251 | 22 | 78 | +56 |
| `11 share-electricity-wind` | 246 | 22 | 89 | +67 |
| `12 solar-energy-consumption` | 251 | 22 | 77 | +55 |
| `15 share-electricity-solar` | 246 | 22 | 89 | +67 |
| `01`, `06` | 104 | 82 | 89 | +7 |
| Chín file còn lại | — | — | — | 0 |

Đúng tám file có chênh lớn — chính là tám file bị Step 7 xếp `TRUNCATED_SEVERE`. Hai file `01` và `06` chênh nhẹ vì năm cuối của chúng là `PARTIAL_REVIEW`.

Con số `FULL_SPAN` hiệu dụng của file `03` là **89** chứ không phải 238, vì phần lớn thực thể còn lại bắt đầu muộn (từ năm 2000) nên vẫn có biên đầu. 89 là số thực thể có dữ liệu liên tục suốt 1965–2021.

Có 35 chuỗi chứa tổng cộng 356 năm thiếu ở giữa, phân thành hai loại rõ rệt:

| Loại | Số chuỗi | Trường hợp |
|---|---:|---|
| `SAMPLING_GRID_NOT_MISSING` | 31 | Toàn bộ file `17` geothermal |
| `DO_NOT_INTERPOLATE_REVIEW_SOURCE` | 4 | `CIS (BP)` trong file `08`, `10`, `12`, `14` |

Các trường hợp nổi bật:

- `CIS (BP)` thiếu liên tục 1966–1989, tức 24 năm, trong bốn file. Một khoảng trống duy nhất và rất dài — đây là thiếu dữ liệu thật, phải kiểm tra nguồn. Là thực thể tổng hợp/lịch sử, không phải nước ASEAN.
- File `17` geothermal: 30 chuỗi giai đoạn 1990–2020 thiếu đúng `1991–1994` và `1996–1999` — hai khoảng dài bằng nhau, cách nhau đều 5 năm. Chuỗi `World` thiếu năm khoảng theo cùng quy luật từ 1975. Đây là lịch báo cáo 5 năm một lần rồi chuyển sang hàng năm từ năm 2000, **không phải dữ liệu bị mất**.
- Trường hợp ASEAN duy nhất có lỗ hổng ở giữa là Philippines trong file geothermal, và nó thuộc nhóm lưới lấy mẫu.
- Các nguồn sản lượng và tỷ trọng chính cho ASEAN không có lỗ hổng giữa. Myanmar, Cambodia, Laos và Brunei bắt đầu từ năm 2000 nhưng liên tục sau khi bắt đầu; đây là `BOUNDARY_ONLY` ở cả hai cách đo, không phải lỗi cần nội suy.

### Hệ quả cho Phase 2

- Không tự động nội suy bất kỳ chuỗi nào.
- Giữ `NULL` cho lỗ hổng giữa và chỉ tính YoY khi hai năm thực sự liên tiếp.
- Không điền dữ liệu trước năm đầu hoặc sau năm cuối của chuỗi `BOUNDARY_ONLY`.
- **Khi lọc theo độ phủ, dùng `coverage_pattern_effective`, không dùng `coverage_pattern`.** Lọc nhầm cột thô sẽ giữ lại 22 thực thể của file `03` thay vì 89 — mất ba phần tư panel mà không có lỗi nào báo.
- Với geothermal, phân tích theo các mốc có dữ liệu và công khai khoảng thiếu. Không tính YoY hay CAGR liên tiếp cho giai đoạn 1975–1999 của file `17`, vì các năm ở giữa vốn không được thu thập.
- `CIS (BP)` cần được phân loại là thực thể tổng hợp/lịch sử trong `dim_entity`.

### Giới hạn diễn giải

- Step 6 kiểm tra khóa năm, không kiểm tra một metric cụ thể có bị `NaN`; cần kết hợp với Step 1 khi dùng cột chỉ số.
- Một chuỗi liên tục không có nghĩa giá trị chính xác hoặc định nghĩa nhất quán qua thời gian.
- **Cột thô bị năm cuối của file chi phối.** Với tám file có 2022 cắt cụt, `coverage_pattern` nói nhiều về file hơn là về thực thể. Đọc một mình cột này sẽ kết luận sai rằng rất ít thực thể phủ đủ.
- Cột hiệu dụng phụ thuộc vào `recommended_end_year` của Step 7, mà giá trị đó chỉ lùi **đúng một năm** so với năm cuối. Nếu về sau nguồn dữ liệu có hai năm cuối liên tiếp bị cắt, cột hiệu dụng sẽ vẫn còn nhiễu và phải sửa lại quy tắc ở Step 7.
- `SAMPLING_GRID_NOT_MISSING` là suy luận từ hình dạng khoảng trống, không phải từ tài liệu nguồn. Nó nói "các khoảng trống đều đặn", và diễn giải "đó là nhịp báo cáo" là bước suy luận thêm — hợp lý với file `17` nhưng cần xác nhận nếu áp cho nguồn khác.
- Lỗ hổng trong dữ liệu công suất có thể phản ánh lịch báo cáo theo mốc, không mặc nhiên là 0.

---

## 9. Step 7 — Kiểm tra năm cuối bị cắt cụt

### Ý nghĩa và vai trò

Step 7 phát hiện năm cuối chỉ mới có một phần dữ liệu. Nếu giữ năm này trong phân tích, biểu đồ có thể tạo cú giảm giả, tổng khu vực và thứ hạng bị sai, còn YoY/CAGR cuối kỳ trở nên không đáng tin cậy.

### Phương pháp và cách đọc các cột

Với mỗi file–năm, script đếm:

- `row_count`, `entity_count`, `asean_entity_count`;
- số thực thể của năm trước;
- median số thực thể trong tối đa 5 năm trước, cho toàn bộ dữ liệu và riêng ASEAN;
- tỷ lệ độ phủ năm hiện tại so với hai baseline;
- trạng thái và năm kết thúc khuyến nghị nếu đây là năm cuối.

Phân loại dùng tỷ lệ xấu hơn giữa toàn bộ thực thể và ASEAN:

| Trạng thái | Quy tắc |
|---|---|
| `FULL` | Tỷ lệ thấp nhất ≥ 95% |
| `PARTIAL_REVIEW` | Tỷ lệ thấp nhất từ 50% đến dưới 95% |
| `TRUNCATED_SEVERE` | Tỷ lệ thấp nhất < 50% |
| `INSUFFICIENT_BASELINE` | Không có baseline hợp lệ để đánh giá |

### Kết quả thực tế

Tám file bị `TRUNCATED_SEVERE` ở năm 2022:

```text
03, 04, 05, 07, 08, 11, 12, 15
```

Năm 2022 của mỗi file chỉ còn 29 thực thể và 0 nước ASEAN. Baseline toàn bộ khoảng 241–247 thực thể; tỷ lệ còn 11,7409%–12,0332%, còn tỷ lệ ASEAN là 0%. Năm kết thúc được khuyến nghị cho cả tám file là 2021.

Hai file `PARTIAL_REVIEW` ở năm 2021:

| File | Toàn bộ thực thể | ASEAN | Nguyên nhân trực tiếp | Năm khuyến nghị cho panel cố định |
|---|---:|---:|---|---:|
| `01` | 96/103 = 93,2039% | 5/6 = 83,3333% | Singapore dừng ở 2020 | 2020 |
| `06` | 96/103 = 93,2039% | 5/6 = 83,3333% | Singapore dừng ở 2020 | 2020 |

Bảy file được đánh giá `FULL`:

- `02`, `09`, `10`, `13`, `14`, `16`: đầy đủ theo quy tắc đến 2021;
- `17`: đầy đủ theo quy tắc đến 2020.

Kết hợp Step 5–7, cửa sổ phân tích chính cho panel ASEAN-10 là **2000–2021**.

### Hệ quả cho Phase 2

- Giữ năm 2022 ở raw/audit để chứng minh vấn đề nhưng loại khỏi bảng sạch dùng cho phân tích ASEAN.
- Dùng 2000–2021 cho panel chính ASEAN-10.
- Nếu dùng `01` hoặc `06` với panel ASEAN-6 cố định, kết thúc ở 2020; nếu giữ 2021 phải công khai rằng Singapore bị thiếu.
- Geothermal chỉ có thể phân tích đến 2020.

### Giới hạn diễn giải

- `FULL` chỉ có nghĩa năm cuối không giảm mạnh so với baseline; không có nghĩa file phủ nhiều quốc gia hoặc metric không có `NaN`.
- Quy tắc median 5 năm phát hiện sụt giảm độ phủ đột ngột, không xác nhận tính đúng đắn, độ mới hay phương pháp thu thập của nguồn.
- Số thực thể giảm không tự động là lỗi; vì vậy nhóm 50%–95% được đánh dấu review thay vì tự động loại.

---

## 10. Năm quyết định (5 quyết định) cuối Phase 1

### 10.1. Dùng file nào, bỏ file nào và vì sao?

- **Panel chính ASEAN-10:** dùng `03`, `04`, `07`, `11`, `15`. Nhóm này cung cấp sản lượng điện theo công nghệ và tỷ trọng điện với độ phủ đủ 10 nước trong giai đoạn 2000–2021.
- **Loại khỏi bảng canonical để tránh trùng:** `05`, `08`, `12`, vì các cột hydro, wind, solar tương ứng là `redundant_subset` khớp tuyệt đối với file `03`.
- **Không hòa trộn file `02` với `03`:** các chỉ số TWh có chênh lệch vượt ngưỡng `MATERIAL` ở cả bốn nhóm công nghệ. Cho panel chính, ưu tiên `03` vì phủ 251 thực thể và đủ ASEAN-10; giữ `02` tách biệt để audit/provenance hoặc chỉ sử dụng sau khi xác minh định nghĩa nguồn.
  - Chênh lệch **lớn nhất** nằm ở thực thể tổng hợp (tối đa 159 TWh), nên việc chọn nguồn quan trọng nhất khi tính chỉ số cấp khu vực.
  - Với **Việt Nam**, hai nguồn chênh nhau tối đa `0,005 TWh` và không có dòng `MATERIAL` nào; lựa chọn nguồn không ảnh hưởng đến phần phân tích Việt Nam.
- **Phân tích phụ ASEAN-6:** `01`, `06`, `10`, `14` và, nếu được xác minh riêng, `02`. Không gọi kết quả này là đại diện đầy đủ ASEAN-10.
- **Case study/tập con:** `09`, `13`, `16`, `17`, vì chỉ phủ lần lượt 2, 4, 2 và 2 nước ASEAN.

### 10.2. Join theo chiến lược nào?

- Dùng exact match trên `(Entity, Year)`.
- Dựng spine `quốc gia × năm` rồi `LEFT JOIN` các chỉ số.
- Không `INNER JOIN` cả 17 file, vì chỉ giữ 3,125% thực thể và 1,8673% khóa.
- Không auto-fuzzy; `Code` chỉ dùng để kiểm chứng, không phải khóa duy nhất.
- Giữ provenance (`source_file`, tên metric gốc/chuẩn hóa) để audit các nguồn xung đột.

### 10.3. Chỉ số nào đủ cho ASEAN-10?

Trong 2000–2021, bộ không trùng có thể dùng cho đủ 10 nước gồm:

- sản lượng điện hydro, wind, solar và other renewables theo TWh từ `03`;
- tỷ trọng năng lượng tái tạo trong điện từ `04`;
- tỷ trọng hydro, wind và solar trong điện từ `07`, `11`, `15`.

Các chỉ số tỷ trọng trên năng lượng sơ cấp chỉ phủ sáu nước; công suất, biofuel và geothermal chỉ phù hợp cho tập con đã nêu ở Step 5.

### 10.4. Có nội suy không?

**Không tự động nội suy.** Giữ `NULL`, không điền trước/sau biên chuỗi và không coi năm không có dòng là 0. Chỉ xem xét một phương pháp ước lượng riêng sau khi kiểm tra nguồn và nêu rõ giả định; các kết quả Phase 1 hiện tại chưa tạo căn cứ cho việc đó.

Quy mô thực tế của vấn đề: chỉ **35 trên 2.702** chuỗi có lỗ hổng ở giữa, và 31 trong số đó là nhịp lấy mẫu của file geothermal chứ không phải dữ liệu bị mất. Bốn chuỗi còn lại đều thuộc `CIS (BP)` — một thực thể tổng hợp/lịch sử. **Không chuỗi ASEAN nào có lỗ hổng thật sự cần nội suy.** Vấn đề thời gian của bộ dữ liệu này nằm ở biên chuỗi và ở năm cuối bị cắt, không nằm ở lỗ hổng giữa.

### 10.5. Cắt cửa sổ phân tích ở năm nào?

- Panel chính ASEAN-10: **2000–2021**.
- `01` và `06` nếu yêu cầu panel ASEAN-6 cố định: kết thúc **2020**.
- Geothermal: kết thúc **2020**.
- Năm 2022: giữ trong raw/audit, loại khỏi dữ liệu sạch dùng phân tích ASEAN.

## 11. Các cảnh báo bắt buộc khi sử dụng kết quả

1. `Entity` không đồng nghĩa với quốc gia; phải phân loại thực thể trước khi xếp hạng toàn cầu hoặc đếm quốc gia.
2. Số 0 là giá trị số hợp lệ và khác `NULL`; không đổi qua lại giữa hai trạng thái.
3. `redundant_subset` không có nghĩa toàn bộ file giống nhau; kết luận chỉ áp dụng cho cột và tập quan sát được kiểm tra.
4. Xung đột file `02` với `03` không chứng minh nguồn nào sai; phải kiểm tra provenance và định nghĩa.
5. `present = YES` trong Step 5 không bảo đảm metric khác `NaN`.
6. Không tự động fuzzy-match và không tự động nội suy.
7. Tỷ lệ giữ lại 100% trong tầng một file không phải bằng chứng độ phủ rộng.
8. `FULL` ở Step 7 không đồng nghĩa dữ liệu đầy đủ về mặt nội dung; nó chỉ cho biết năm cuối không bị sụt độ phủ theo ngưỡng đã chọn.
9. **Không đọc `match_pct` mà bỏ qua `material_match_pct`.** Cột đầu đếm cả sai số làm tròn; riêng với wind, hai con số là 69% và 96%.
10. **Không lọc độ phủ bằng `coverage_pattern`.** Với tám file có năm 2022 cắt cụt, cột thô nói về file chứ không nói về thực thể; dùng `coverage_pattern_effective`.
11. `IMMATERIAL` nghĩa là "không vượt hai ngưỡng đã chọn", không nghĩa là "giống nhau". Nhóm này chứa cả chênh lệch tới 39 TWh nằm dưới mốc 1%.
12. `is_aggregate` chỉ phát hiện thực thể tổng hợp **thiếu `Code`**. Thực thể tổng hợp mang mã giả `OWID_*` không bị cờ này bắt; Phase 2 phải phân loại lại.
13. Step 3 chỉ so 5 trên 17 file. Mười hai file còn lại **chưa được kiểm tra trùng lặp** dưới bất kỳ hình thức nào.
