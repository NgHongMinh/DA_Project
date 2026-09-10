# Hợp đồng triển khai và nghiệm thu Phase 8 — Vai trò SQL

## 1. Mục tiêu, phạm vi và trạng thái đầu vào

Phase 8 chứng minh SQL thực hiện phần việc phân tích thật cho yêu cầu 1.2 và 1.3,
không chỉ xuất hiện để đủ số công cụ. SQL phải tính độc lập từ các bảng Phase 2,
sau đó được đối chiếu toàn bộ với nhánh Python của Phase 3.

Phase 8 chạy song song với Phase 2–3 theo thiết kế của `PLAN.md`; Phase 5 không
phải đầu vào hoặc điều kiện nghiệm thu. Vì Phase 5 đang được triển khai song song,
Phase 8 không được sửa `powerbi/`, `PHASE5.md`, `docs/Phase5_Review.md`, các script
`05_*` hoặc trạng thái Phase 5.

Đường cơ sở trước khi bắt đầu nghiệm thu:

| Hạng mục | Giá trị khóa |
|---|---:|
| CSV nguồn trong `archive/` | 17 |
| Dấu vân tay đầu vào Phase 2 | `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10` |
| Dòng `fact_energy` | 89.075 |
| Dòng kiểm định Phase 2 | 864 |
| Dòng chặn Phase 2 | 34/34 `PASS` |
| Dòng `fact_metrics` Phase 3 | 18.926 |
| Đối chiếu Python–SQL Phase 3 | 18.926/18.926 `PASS` |
| Kiểm định Phase 3 | 92/92 `PASS` |
| Kiểm định Phase 4 | 38/38 `PASS` |

Hai sai khác cấu trúc phải được phát hiện và xử lý tại đúng cổng, không sửa trước:

1. V7–V8 hiện là truy vấn tổng hợp trực tiếp, chưa dùng CTE (biểu thức bảng chung)
   như cấu trúc đã khóa trong `PLAN.md`.
2. Năm đầu tiên dương hiện dùng `MIN(...)` kết hợp `GROUP BY` (gom nhóm), chưa
   dùng `MIN(...) OVER (...)`, tức `window function` (hàm cửa sổ), như yêu cầu.

## 2. Kiến trúc kiểm định cách ly

`python/08_verify_sql.py` mở `sql/renewables.db` bằng `mode=ro`, tức `read-only`
(chỉ đọc), rồi sao lưu vào SQLite `:memory:`, tức `in-memory` (trong bộ nhớ).
`sql/02_validate.sql` và `sql/03_analysis.sql` chỉ được thực thi trên bản sao đó.

Quy tắc bắt buộc:

- Không chạy `02_clean_build.py`, `03_descriptive.py` hoặc
  `03_verify_release.py` trực tiếp lên sản phẩm đã công bố trong quá trình nghiệm
  thu Phase 8.
- Không ghi vào `renewables.db`, `output/clean/` hoặc đầu ra Phase 1–5.
- Tệp duy nhất trình kiểm định được phép công bố là
  `output/stats/08_validation_results.csv`.
- Kết quả được ghi atomically (thay thế nguyên khối an toàn): lỗi giữa chừng không
  được để lại CSV bị cắt dở.
- Mọi giá trị số khi đối chiếu dùng đồng thời dung sai tuyệt đối và tương đối
  `1e-9`; các trường chữ, trạng thái, lý do và khóa phải khớp chính xác.

Schema (lược đồ cột) công khai của CSV kiểm định:

```text
gate_id,step_name,status,expected,observed,details,method_version,phase2_input_fingerprint
```

`method_version` được khóa là `phase8_v1`. CSV hoàn chỉnh có đúng mười dòng:
`P8-00` đến `P8-08` và `P8-FINAL`.

## 3. Quy tắc chạy tuần tự

Mỗi lần chỉ tăng phạm vi kiểm định thêm một cổng:

```powershell
python python\08_verify_sql.py --through P8-00
python python\08_verify_sql.py --through P8-01
# Chỉ chạy dòng tiếp theo sau khi dòng trước trả mã thoát 0.
python python\08_verify_sql.py --through P8-02
```

Trình kiểm định luôn chạy lại từ `P8-00` đến cổng yêu cầu. Nếu một cổng `FAIL`:

1. dừng ngay và trả mã thoát khác 0;
2. CSV chỉ chứa các cổng đã chạy đến cổng lỗi;
3. không chạy hoặc công bố bằng chứng của cổng sau;
4. chỉ sửa nguyên nhân thuộc cổng lỗi, rồi chạy lại chính cổng đó.

Sau khi `P8-08` đạt, lệnh cuối là:

```powershell
python python\08_verify_sql.py --final
```

## 4. P8-00 — Tiền điều kiện liên phase

### Làm gì và vì sao

Đối chiếu Phase 0–4 trước khi chạy phân tích SQL để loại khả năng dùng sai phiên
bản SQLite, sai dữ liệu, sai cửa sổ năm hoặc bằng chứng Phase 3–4 đã lỗi thời.

### Gate P8-00

- SQLite chạy thật được CTE, `RANK`, `LAG`, `MIN OVER`, tổng tích lũy và cửa sổ
  trung bình ba dòng.
- Có đúng 17 CSV nguồn.
- Dấu vân tay Phase 2 đúng giá trị khóa; `fact_energy` có 89.075 dòng.
- `fact_metrics` có 18.926 dòng với Q1=5.544, Q2=3.608, Q3=1.980,
  Q4=1.382, Q5=5.950 và Q6=462.
- Tệp kiểm định Phase 3 có đúng 92 mã duy nhất, tất cả `PASS`.
- Tệp kiểm định Phase 4 có đúng 38 mã duy nhất, tất cả `PASS`.

## 5. P8-01 — Tính lại V1–V8

### Làm gì và vì sao

Chạy `sql/02_validate.sql` trên bản SQLite trong bộ nhớ. Cổng dữ liệu phải đạt
trước các công thức phân tích để tránh chứng minh một phép tính đúng trên đầu vào
không hợp lệ.

### Gate P8-01

- V1–V8 đều dùng CTE; riêng V7–V8 phải được chuyển sang CTE mà không đổi kết quả.
- Có đúng 864 dòng: 560 `PASS`, 268 `WARN`, 36 `SKIP`, không có `FAIL`.
- Có đúng 34 dòng `is_blocking=1`, tất cả `PASS`.
- V5 đạt 5.336/5.336 dòng chung và 220/220 dòng ASEAN.
- V6 có 0 khóa trùng; V7 có 0 giá trị âm; V8 có 0 phần trăm ngoài `[0,100]`.
- Mọi dòng cùng dấu vân tay Phase 2 hiện tại.

`WARN` và `SKIP` của V1–V5 là bằng chứng đối soát nguồn hợp lệ, không phải lỗi.
Chỉ dòng chặn khác `PASS` mới làm cổng thất bại.

## 6. P8-02 — Xếp hạng theo năm

### Làm gì và vì sao

Kiểm tra `RANK() OVER` phân vùng đúng theo năm và chuỗi. Mục tiêu là giữ đồng
hạng, dùng đúng mẫu số `ranked_n` và không tạo hạng giả khi tổng phạm vi bằng 0.

### Gate P8-02

- Có 440 dòng `asean_rank`, 132 dòng `global_rank` và 220 dòng
  `modern_rank_gain`.
- Hạng đã xác định là số nguyên trong `[1, ranked_n]`.
- Phạm vi tổng bằng 0 trả `NULL` với `ZERO_SCOPE_TOTAL` hoặc
  `RANK_NOT_DEFINED`, không trả hạng 1.
- Mọi dòng thuộc ba chỉ số khớp nhánh Python trong dung sai đã khóa.

## 7. P8-03 — Tăng trưởng YoY

### Làm gì và vì sao

Kiểm tra `LAG()` phân vùng đúng theo đối tượng và chuỗi, nhằm ngăn rò giá trị năm
trước từ một nước hoặc công nghệ khác và ngăn chia cho 0.

### Gate P8-03

- Có 396 dòng `yoy` và 1.100 dòng `q5_yoy`.
- Năm đầu mỗi chuỗi trả `NULL / MISSING_PREVIOUS`.
- Mẫu số 0 trả `NULL / ZERO_BASE`; chỉ mẫu số dương mới tính YoY.
- Không có `NaN` hoặc vô hạn; mọi dòng khớp nhánh Python.

## 8. P8-04 — Năm đầu tiên dương

### Làm gì và vì sao

Chạy cổng trên cấu trúc hiện tại để ghi nhận sai khác, sau đó dừng. Chuyển cả năm
đầu tiên dương và năm đầu đạt `0,05 TWh` sang
`MIN(CASE ... END) OVER (PARTITION BY entity, series_key)`, loại dòng lặp một
cách tường minh, rồi chạy lại P8-04.

### Gate P8-04

- SQL chứa đúng hai phép `MIN(CASE...) OVER` theo `entity, series_key`.
- Có đúng 40 kết quả cho `first_positive_in_window` và 40 kết quả cho
  `first_material_in_window`.
- Năm kết quả nằm trong 2000–2021; chuỗi đã hoạt động trước cửa sổ hoặc chưa xảy
  ra sự kiện được giữ dưới trạng thái kiểm duyệt, không biến thành năm giả.
- Ngưỡng đáng kể đúng `0,05 TWh`; Việt Nam–mặt trời vẫn có
  `first_positive_in_window=2010`.
- Toàn bộ chỉ số và trạng thái gia nhập khớp nhánh Python.

## 9. P8-05 — Tích lũy và trung bình trượt

### Làm gì và vì sao

Kiểm tra khung `ROWS` theo đúng thứ tự năm để ngăn cộng lẫn chuỗi hoặc tính trung
bình trên cửa sổ chưa đủ ba quan sát.

### Gate P8-05

- Có 264 dòng `cumulative_generation_twh` và 264 dòng
  `rolling_mean_3y_twh`.
- Với chuỗi đầy đủ, `C(t) = C(t-1) + value(t)`.
- Trung bình trượt bằng trung bình đúng ba năm hiện tại và hai năm trước.
- Hai năm đầu của mỗi chuỗi trả `NULL / INSUFFICIENT_WINDOW`; cửa sổ thiếu trả
  `NULL / INCOMPLETE_WINDOW`.
- Mọi dòng khớp nhánh Python.

## 10. P8-06 — Thay đổi thứ hạng

### Làm gì và vì sao

Đối chiếu hạng tại hai đầu mốc bằng phép tự ghép bảng. Khóa quy ước dấu để tránh
diễn giải ngược chiều cải thiện và suy giảm.

### Gate P8-06

- Có đúng 60 dòng: 10 nước × 3 giai đoạn × 2 khái niệm.
- Mọi giá trị bằng `rank_start - rank_end`; số dương nghĩa là cải thiện.
- Đầu mốc không có hạng hợp lệ trả `NULL / RANK_NOT_DEFINED`.
- Mọi dòng khớp nhánh Python.

## 11. P8-07 — Mức tập trung

### Làm gì và vì sao

Kiểm tra top-1, top-3, HHI, Gini và số nước tham gia theo cùng mẫu số ASEAN-10.
Mục tiêu là không trộn mức tập trung với số nước có sản lượng hoặc với đóng góp
tăng trưởng.

### Gate P8-07

- Mỗi chỉ số `top1_share`, `top3_share`, `hhi`, `gini`, `positive_n` và
  `above_0_05_n` có 44 dòng; tổng cộng 264 dòng.
- Khi tổng dương: `0 ≤ top1 ≤ top3 ≤ 1`, `0 ≤ HHI ≤ 1`,
  `0 ≤ Gini ≤ 0,9`; hai số đếm nằm trong `[0,10]`.
- Khi tổng bằng 0, bốn tỷ lệ trả `NULL / ZERO_DENOMINATOR`.
- Trường hợp mười nước bằng nhau cho `HHI=0,1`, `Gini=0`; một nước giữ toàn bộ
  cho `HHI=1`, `Gini=0,9`.
- Mọi dòng khớp nhánh Python.

## 12. P8-08 — Đối chiếu tổng và tái lập

### Làm gì và vì sao

Tạo hai bản SQLite trong bộ nhớ độc lập, tính lại toàn bộ nhánh SQL và nhánh
Python. Đây là `cross-check` (đối chiếu độc lập) cuối để chứng minh SQL không đọc
`fact_metrics` do Python tạo và kết quả không phụ thuộc lần chạy.

### Gate P8-08

- Mỗi lần có đúng 18.926 dòng SQL với phân bố Q1–Q6 đã khóa.
- Ghép ngoài toàn bộ khóa cho đúng 18.926/18.926 dòng `PASS`; số, chữ, trạng thái,
  lý do, số đếm, mẫu số và khóa đều khớp.
- Tệp kiểm định Phase 3 hiện hành có 92/92 mã duy nhất `PASS`.
- Hai lần chạy tạo cùng mã băm nội dung chuẩn hóa.
- 17 CSV nguồn và sản phẩm Phase 1–5 không bị trình Phase 8 ghi sửa.

## 13. P8-FINAL — Quyết định hoàn thành

### Gate P8-FINAL

- Có đúng chín cổng nhiệm vụ `P8-00` đến `P8-08`, đúng thứ tự và không trùng.
- Tất cả chín cổng là `PASS`, cùng `method_version=phase8_v1` và cùng dấu vân tay.
- `08_validation_results.csv` có thêm đúng một dòng `P8-FINAL=PASS`.
- `docs/Phase8_Review.md` ghi kết quả tổng thể `ĐẠT` và không còn ghi chú phải sửa.
- Chỉ sau đó mới cập nhật Phase 8 trong `PLAN.md` thành “ĐÃ HOÀN THÀNH” và ghi
  bằng chứng vào báo cáo cùng nhật ký phân tích.

Nếu bất kỳ điều kiện nào không đạt, kết luận bắt buộc là **Phase 8 chưa hoàn
thành**. Bằng chứng từ cổng sau không được dùng để bù cho cổng trước.

## 14. Sản phẩm bàn giao

- `PHASE8.md` — hợp đồng này.
- `python/phase8_contract.py` — hằng số và danh sách cổng khóa.
- `python/08_verify_sql.py` — trình chạy tuần tự và cách ly.
- `python/08_test_contract.py` — kiểm thử gieo lỗi cho bộ kiểm định.
- `output/stats/08_validation_results.csv` — kết quả máy đọc được.
- `docs/Phase8_Review.md` — phiếu nghiệm thu và quyết định cuối.
