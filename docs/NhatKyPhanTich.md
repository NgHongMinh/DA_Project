# Nhật ký phân tích

Kho phát hiện tích luỹ qua các phase, làm nguyên liệu cho Phase 6 (diễn giải) và Phase 7 (kết luận). Đây **không phải** bản tóm tắt báo cáo — nó ghi cả những thứ chưa dùng đến và những thứ chưa kết luận được.

Mỗi mục có cùng cấu trúc:

- **Phát hiện** — phát biểu thành một câu
- **Số** — con số cụ thể
- **Truy vết** — file và cột để kiểm chứng lại
- **Ý nghĩa** — dùng được ở phase nào
- **Mức tin cậy** — Cao / Trung bình / Cần kiểm chứng thêm

> ⚠️ Quy tắc: mọi con số đưa vào `BaoCao.md` phải **tính lại từ nguồn**, không chép từ đây. File này ghi lại thời điểm phát hiện, không phải nguồn chân lý.

---

# Phase 1 — Khảo sát dữ liệu

Chạy: `python python\01_profile.py` · Nguồn: 17 CSV trong `archive/` · Kết quả tái lập byte-identical.

## P1-01. Ghép toàn bộ 17 file bằng INNER JOIN sẽ mất gần hết dữ liệu

- **Phát hiện:** không tồn tại một tập thực thể chung đủ lớn giữa 17 file; chúng phủ ở bảy mức rất khác nhau.
- **Số:** giao của cả 17 file chỉ còn **8 trên 256** thực thể (**3,125%**) và **168 trên 8.997** khoá `(Entity, Year)` (**1,8673%**).
- **Truy vết:** `00_phase1_summary.txt` → STEP 2, dòng `ALL_FILES`.
- **Ý nghĩa:** Phase 2 phải dùng tidy long + spine `LEFT JOIN`, tuyệt đối không `INNER JOIN` nhiều tầng. Đây là rủi ro nguy hiểm nhất của bộ dữ liệu vì mất 97% dữ liệu mà **không có lỗi nào báo**.
- **Mức tin cậy:** Cao — phép đếm tập hợp trực tiếp.

Bảy tầng độ phủ:

| Tầng | File | Thực thể | Năm |
|---|---|---:|---|
| T1 | `03`, `05`, `08`, `12` | 251 | 1965–2022 |
| T2 | `04`, `07`, `11`, `15` | 246 | 1985–2022 |
| T3 | `01`, `02`, `06`, `10`, `14` | 104 | 1965–2021 |
| T4 | `13` | 64 | 1996–2021 |
| T5 | `09` | 62 | 1995–2021 |
| T6 | `16` | 35 | 1990–2021 |
| T7 | `17` | 33 | 1975–2020 |

## P1-02. Ba file là bản dư thừa của file 03

- **Phát hiện:** cột hydro/wind/solar của `05`, `08`, `12` khớp **tuyệt đối** với cột tương ứng trong `03` trên toàn bộ quan sát không rỗng.
- **Số:** 8.840 / 8.676 / 8.683 giá trị khớp chính xác, 0 xung đột, `match_pct = 100%`.
- **Truy vết:** `00_phase1_summary.txt` → STEP 3, các cặp `hydro_twh__03_05`, `wind_twh__03_08`, `solar_twh__03_12`.
- **Ý nghĩa:** Phase 2 chỉ nạp `03`; nạp thêm ba file kia sẽ đếm trùng và làm tổng sai gấp bội.
- **Mức tin cậy:** Cao.
- **⚠️ Không được nói quá:** kết luận chỉ áp cho **cột được so sánh**, không phải "ba file giống hệt file 03". Ba file này có số dòng và schema khác `03`.

## P1-03. File 02 và 03 khớp ở cấp quốc gia, lệch ở cấp thực thể tổng hợp

Đây là phát hiện có giá trị nhất của Phase 1.

- **Phát hiện:** hai nguồn TWh chênh nhau ở cả hai cấp, nhưng **quy mô** chênh lệch ở thực thể tổng hợp lớn hơn khoảng một bậc. Dấu hiệu của việc gộp trên tập quốc gia thành phần khác nhau, không phải mâu thuẫn về số liệu từng nước.
- **Số:**

  | Tầng | Loại thực thể | Dòng | Trung vị | Lớn nhất |
  |---|---|---:|---:|---:|
  | `MATERIAL` | quốc gia | 2.011 | 0,4472 TWh | 18,81 TWh |
  | `MATERIAL` | tổng hợp | 847 | 2,6463 TWh | **159,17 TWh** |

  Năm chênh lệch lớn nhất đều là thực thể tổng hợp: `Lower-middle-income countries` 159,17 · `Upper-middle-income countries` 128,86 · `Europe` 32,18 · `High-income countries` 22,16 · `Asia` 21,81 TWh.
- **Truy vết:** `01_overlap_conflict_details.csv`, lọc `conflict_tier = MATERIAL`, nhóm theo `is_aggregate`.
- **Ý nghĩa:** Phase 2 phải ưu tiên xác minh provenance cho **thực thể tổng hợp trước**, vì chính chúng là mẫu số của mọi chỉ số "tỷ trọng khu vực" ở Phase 3. Chọn nhầm nguồn cho `Lower-middle-income countries` kéo theo sai số hơn 150 TWh.
- **Mức tin cậy:** Cao về số liệu; **Cần kiểm chứng thêm** về nguyên nhân — giả thuyết "gộp trên tập nước khác nhau" là suy luận từ hình thái dữ liệu, chưa đối chiếu tài liệu nguồn của OWID/BP/Ember.

## P1-04. Phần lớn "xung đột" giữa 02 và 03 là nhiễu độ chính xác

- **Phát hiện:** file `03` làm tròn tới 2 chữ số thập phân còn `02` giữ đủ độ chính xác, nên so sánh chặt đếm nhầm sai số làm tròn thành mâu thuẫn nguồn.
- **Số:** trong 12.168 dòng xung đột, **9.310 là `IMMATERIAL`** và chỉ 2.858 là `MATERIAL`. Sau khi lọc, tỷ lệ khớp của wind tăng từ **69,22% lên 96,00%**; hydro từ 64,13% lên 90,34%.
- **Truy vết:** `00_phase1_summary.txt` → STEP 3, so cột `match_pct` với `material_match_pct`.
- **Ý nghĩa:** con số `match_pct` một mình không dùng được để mô tả mức đồng thuận giữa hai nguồn. Đây là ví dụ tốt cho phần "phương pháp" của báo cáo: một ngưỡng so sánh đặt sai làm hỏng cả kết luận.
- **Mức tin cậy:** Cao.

## P1-05. Với Việt Nam, hai nguồn thống nhất hoàn toàn

- **Phát hiện:** không có bất kỳ chênh lệch đáng kể nào giữa `02` và `03` cho Việt Nam.
- **Số:** 90 dòng xung đột, **toàn bộ là `IMMATERIAL`**, chênh lệch lớn nhất `0,005 TWh` — đúng bằng biên độ làm tròn 2 chữ số.
- **Truy vết:** `01_overlap_conflict_details.csv`, lọc `Entity = "Vietnam"`.
- **Ý nghĩa:** phần phân tích Việt Nam có thể tiến hành ngay, không phải chờ giải quyết xong vấn đề provenance ở P1-03.
- **Mức tin cậy:** Cao.

## P1-06. Năm 2022 bị cắt cụt nặng ở tám file

- **Phát hiện:** tám file có dòng năm 2022 nhưng chỉ cho một nhóm rất nhỏ thực thể, và **không có nước ASEAN nào**.
- **Số:** 8 file `TRUNCATED_SEVERE`: chỉ 29 thực thể so với đường nền 241–247 (**11,7–12,0%**), `asean_coverage_pct = 0%`. Thêm 2 file `PARTIAL_REVIEW` (`01`, `06`) ở năm 2021 với 93,2% thực thể và 83,3% ASEAN.
- **Truy vết:** `05_last_year_check.csv`, lọc `is_last_year = True`.
- **Ý nghĩa:** giữ 2022 sẽ tạo một cú sụt giả ở cuối **mọi** chuỗi thời gian. Cắt ở tầng phân tích, giữ ở tầng raw làm bằng chứng minh hoạ cho báo cáo — đây là hình ảnh trực quan tốt cho slide phần "khuyết điểm dữ liệu".
- **Mức tin cậy:** Cao.

## P1-07. Năm cụt làm hỏng cả phép đo độ phủ, không chỉ chuỗi thời gian

- **Phát hiện:** vì `trailing_boundary` đo so với năm lớn nhất **có mặt** trong file, mọi thực thể kết thúc đúng hạn ở 2021 bị gắn nhãn "kết thúc sớm". Ảnh hưởng lan sang phép đo hoàn toàn khác.
- **Số:** **535 trên 2.702** chuỗi đổi nhãn khi đo lại theo năm hiệu dụng. Số chuỗi `FULL_SPAN` tăng từ **682 lên 1.215**. Riêng file `03`: từ 22 lên 89.
- **Truy vết:** `04_year_continuity_details.csv`, so `coverage_pattern` với `coverage_pattern_effective`.
- **Ý nghĩa:** bài học phương pháp — một lỗi dữ liệu ở một chiều (thời gian) có thể lây sang chỉ số ở chiều khác (độ phủ) mà không có dấu hiệu. Phase 2 phải lọc bằng cột `*_effective`.
- **Mức tin cậy:** Cao.

## P1-08. Vực coverage tại năm 2000

- **Phát hiện:** số quốc gia trong panel nhảy vọt tại đúng năm 2000 do nguồn dữ liệu thay đổi, không phải do có thêm nước phát điện.
- **Số:** file `03`: **106 → 247** thực thể giữa 1999 và 2000; ASEAN từ **6 → 10** nước. File `04` và `07`: 106 → 242.
- **Truy vết:** `05_last_year_check.csv`, cột `entity_count` và `asean_entity_count` tại các năm 1999–2000.
- **Ý nghĩa:** mọi chỉ số dạng "% số nước" phải dùng **mẫu số cố định**, nếu không sẽ tạo một cú nhảy giả năm 2000. Đây cũng là lý do cửa sổ phân tích ASEAN-10 bắt đầu từ 2000 — trước đó bốn nước không có dữ liệu.
- **Mức tin cậy:** Cao.

## P1-09. Độ phủ ASEAN chia thành hai nhóm rõ rệt

- **Phát hiện:** sáu nước có mặt ở phần lớn file, bốn nước chỉ có ở nhóm file phủ rộng.
- **Số:**

  | Nhóm | Nước | Số file có mặt |
  |---|---|---:|
  | Đủ dữ liệu | Philippines, Thailand | 16/17 |
  | | Indonesia | 15/17 |
  | | Malaysia, Vietnam | 14/17 |
  | | Singapore | 13/17 |
  | Hạn chế | Myanmar, Cambodia, Laos, Brunei | **8/17** |

  Tám file phủ đủ ASEAN-10: `03`, `04`, `05`, `07`, `08`, `11`, `12`, `15`.
- **Truy vết:** `03_asean_coverage_details.csv`; `00_phase1_summary.txt` → STEP 5.
- **Ý nghĩa:** so sánh 10 nước chỉ khả thi trên sản lượng TWh và tỷ trọng điện. Mọi so sánh dùng tỷ trọng trên năng lượng sơ cấp chỉ là **ASEAN-6** và phải gọi đúng tên. Biểu đồ hệ số công suất chỉ làm được cho tập rất nhỏ.
- **Mức tin cậy:** Cao về sự có mặt của khoá; **Trung bình** về nội dung — `present = Y` chỉ xác nhận có dòng, không đảm bảo metric khác `NaN`.

## P1-10. Lỗ hổng giữa chuỗi hầu như không tồn tại

- **Phát hiện:** vấn đề thời gian của bộ dữ liệu nằm ở **biên chuỗi** và **năm cuối**, không nằm ở lỗ hổng giữa. Và trong số ít lỗ hổng có thật, phần lớn là nhịp lấy mẫu chứ không phải dữ liệu bị mất.
- **Số:** chỉ **35 / 2.702** chuỗi có lỗ hổng giữa. Trong đó **31 là `SAMPLING_GRID_NOT_MISSING`** (toàn bộ file `17`, lịch báo cáo 5 năm rồi chuyển sang hàng năm từ 2000) và chỉ **4 là thiếu thật** — đều là `CIS (BP)` thiếu liên tục 1966–1989 trong file `08`, `10`, `12`, `14`.
- **Truy vết:** `04_year_continuity_details.csv`, cột `interpolation_decision`.
- **Ý nghĩa:** **không chuỗi ASEAN nào có lỗ hổng thật cần nội suy.** Quyết định "không nội suy" ở Phase 1 vì thế gần như không mất mát gì — điểm đáng nói trong báo cáo, vì nó biến một nguyên tắc thận trọng thành một lựa chọn không tốn kém.
- **Mức tin cậy:** Cao về hình dạng khoảng trống; **Trung bình** về diễn giải "nhịp báo cáo" của file `17` — suy ra từ tính đều đặn, chưa đối chiếu tài liệu nguồn.

## P1-11. Khoá join sạch, không cần chuẩn hoá tên

- **Phát hiện:** exact match trên `(Entity, Year)` là an toàn; không có biến thể khoảng trắng, không có va chạm tên sau chuẩn hoá, quan hệ `Entity`–`Code` nhất quán.
- **Số:** J3–J7 đều **PASS với 0**. 256 tên `Entity` duy nhất; chỉ **8** thực thể có mặt ở đủ 17 file.
- **Truy vết:** `00_phase1_summary.txt` → STEP 4; `02_join_key_details.csv`.
- **Ý nghĩa:** Phase 2 không cần bước chuẩn hoá tên. Tiết kiệm một nguồn lỗi lớn.
- **Mức tin cậy:** Cao.

## P1-12. Bốn cặp tên gần giống — không cặp nào được phép gộp

- **Phát hiện:** có tên gần giống nhau nhưng đều là **thực thể khác nhau**, không phải alias.
- **Số:** 4 cặp vượt ngưỡng similarity 0,88:

  | Cặp | Similarity |
  |---|---:|
  | `Eastern Africa (BP)` ↔ `Western Africa (BP)` | 0,9474 |
  | `Lower-middle-income countries` ↔ `Upper-middle-income countries` | 0,8966 |
  | `Other South & Central America` ↔ `South & Central America` | 0,8846 |
  | `South Africa` ↔ `South America` | 0,8800 |

- **Truy vết:** `02_join_key_details.csv`, lọc `issue_type = FUZZY_CANDIDATE`.
- **Ý nghĩa:** bằng chứng cụ thể cho việc **cấm fuzzy matching**. Cặp `South Africa` ↔ `South America` là ví dụ mạnh nhất: một quốc gia và một châu lục, giống nhau 88% về chuỗi ký tự. Gộp tự động sẽ phá huỷ dữ liệu.
- **Mức tin cậy:** Cao.

## P1-13. 39 thực thể thiếu `Code` — nhưng đó chưa phải toàn bộ thực thể tổng hợp

- **Phát hiện:** thiếu `Code` là chỉ báo sơ bộ cho thực thể tổng hợp, không phải quy tắc phân loại đầy đủ.
- **Số:** 39 `Entity` thiếu `Code` ở ít nhất một file: `Africa`, `Africa (BP)`, `Africa (Ember)`, `Asia`, `Asia (Ember)`, `Asia Pacific`, `Asia Pacific (BP)`, `CIS`, `CIS (BP)`, `Central America (BP)`, `Eastern Africa (BP)`, `Europe`, …
- **Truy vết:** `02_join_key_details.csv`, lọc `issue_type = BLANK_CODE_ENTITY`.
- **Ý nghĩa cho Phase 2:** hai bẫy nhìn thấy ngay từ danh sách này —
  1. **Nhiều bản của cùng một vùng từ các nguồn khác nhau** (`Africa` / `Africa (BP)` / `Africa (Ember)`). Giữ cả ba sẽ nhân tổng lên ba lần.
  2. Thực thể tổng hợp mang **mã giả `OWID_*`** sẽ không bị cờ thiếu `Code` bắt được. Lọc thực thể tổng hợp bằng điều kiện "thiếu Code" là **chưa đủ**; lọc bằng "có `OWID_`" thì lại **xoá nhầm quốc gia thật**.
- **Mức tin cậy:** Cao về danh sách; **Cần kiểm chứng thêm** — Phase 2 phải liệt kê đầy đủ các mã `OWID_*` và phân loại từng cái.

---

## Câu hỏi mở chuyển sang Phase 2

| # | Câu hỏi | Liên quan | Cần làm gì để trả lời |
|---|---|---|---|
| Q1 | `02` hay `03` là nguồn đúng cho thực thể tổng hợp? | P1-03 | Đối chiếu tài liệu OWID/BP/Ember; hoặc tự tính lại tổng từ các quốc gia thành phần và so với cả hai |
| Q2 | Mỗi mã `OWID_*` là quốc gia thật hay thực thể tổng hợp? | P1-13 | Liệt kê toàn bộ mã `OWID_*`, phân loại thủ công từng mã |
| Q3 | Các bản `Africa` / `Africa (BP)` / `Africa (Ember)` có bằng nhau không? | P1-13 | Kiểm định V4 ở Phase 2 |
| Q4 | Bốn file tỷ trọng điện có phải suy ra được từ TWh của `03` không? | Phạm vi Step 3 | Tính lại tỷ trọng từ `03` rồi so với `04`/`07`/`11`/`15` |
| Q5 | Tổng các quốc gia có bằng `World` từng năm không? | P1-01 | Kiểm định V1 ở Phase 2 |
| Q6 | 12 file chưa được kiểm tra trùng lặp có thật sự độc lập? | Phạm vi Step 3 | Kiểm tra riêng, không thuộc phạm vi Step 3 |

---

# Phase 2 — Tiền xử lý & mô hình dữ liệu

Chạy: `python python\02_clean_build.py` và
`python python\run_sql.py sql\02_validate.sql --fail-on-blocking --output-csv output\stats\02_validation_results.csv`.

## P2-01. Một metric chỉ có một nguồn canonical

- **Phát hiện:** Phase 2 khoá nguồn trước khi dựng fact; không trộn các giá trị cạnh tranh để tạo ra một chuỗi “đẹp” hơn.
- **Số:** 17 file/23 cột nguồn được chia thành **13 canonical, 1 audit-only và 3 excluded**, tạo ra **16 metric canonical**. File `02` chỉ để audit; `05`, `08`, `12` bị loại vì trùng metric với `03`.
- **Truy vết:** `output/clean/source_metric_catalog.csv`; `output/clean/dim_metric.csv`; `python/02_clean_build.py` → `METRIC_SPECS`.
- **Ý nghĩa:** mọi quan sát có lineage duy nhất; các sai khác nguồn không bị che bởi coalesce.
- **Mức tin cậy:** Cao — catalog có khoá duy nhất `(source_file, source_column)` và được structural validation kiểm lại.

## P2-02. Tidy-long giữ đủ quan sát thật và tách rõ 0 khỏi thiếu

- **Phát hiện:** mô hình long giữ giá trị 0 như quan sát, còn ô không quan sát chỉ xuất hiện trong audit thiếu.
- **Số:** `fact_energy` có **89.075 dòng**, gồm **36.153 zero** và **52.922 dương**, trên **256 thực thể**, **215 quốc gia/vùng lãnh thổ hiện tại**, 16 metric và **8.968** khoá entity–year. Panel ASEAN chính đủ **1.760/1.760** ô.
- **Truy vết:** `output/clean/fact_energy.csv`; `output/clean/dim_entity.csv`; `sql/renewables.db` → `fact_energy`, `vw_wide`; `output/stats/02_validation_results.csv` → S06–S16.
- **Ý nghĩa:** Power BI và Phase 3 có thể dùng một fact chung mà không đếm trùng hoặc hiểu 0 là `NULL`.
- **Mức tin cậy:** Cao — row count, khoá và panel được kiểm độc lập trong Python và SQLite.

## P2-03. Thiếu dữ liệu được mô tả, không được nội suy

- **Phát hiện:** mọi ô không quan sát trên spine quốc gia hiện tại được giữ `NULL` và phân loại theo vị trí trong chuỗi; không fuzzy matching, interpolation, forward-fill hay backward-fill.
- **Số:** **574 ô `NULL` nguồn** trong cửa sổ canonical tạo thành một phần của **85.876 dòng missingness audit** sau khi mở rộng spine. Phase 1 có **31 chuỗi** sampling-grid; audit current-country biểu diễn **23 chuỗi/184 ô** dưới nhãn `SAMPLING_GRID_NOT_MISSING`. Không ô nào thiếu trong panel ASEAN chính.
- **Truy vết:** `output/clean/missingness_audit.csv`; `output/stats/04_year_continuity_details.csv`; `output/stats/02_validation_results.csv` → S18–S19.
- **Ý nghĩa:** phân tích YoY có thể loại `INTERNAL_GAP` mà không làm sai chuỗi lấy mẫu; 0 vẫn được dùng trong tổng và tỷ trọng.
- **Mức tin cậy:** Cao về phép đếm và phân lớp hiện tại; Trung bình về diễn giải nhịp báo cáo địa nhiệt vì dựa trên pattern nguồn.

## P2-04. Mọi thay đổi giá trị đều nhỏ, hữu hạn và có audit

- **Phát hiện:** ETL không “sửa” khác biệt nguồn; chỉ áp cutoff, đổi đơn vị đã công bố và snap sai số sát biên phần trăm.
- **Số:** **427 dòng cleaning audit = 424 loại ngoài cutoff + 3 snap biên**. Cutoff: `01`, `06`, `17` đến 2020; `03`, `04`, `07`, `11`, `15` đến 2021 và loại 2022; canonical còn lại đến 2021. Địa nhiệt file `17` đổi **MW → GW** với hệ số `0,001`.
- **Truy vết:** `output/clean/cleaning_audit.csv`; `output/clean/source_metric_catalog.csv`; `output/clean/dim_metric.csv`.
- **Ý nghĩa:** năm cụt 2022 không tạo sụt giảm giả, trong khi lịch sử hợp lệ và giá trị gốc vẫn truy vết được.
- **Mức tin cậy:** Cao — conversion/cutoff nằm trong catalog và ba snap được structural validation đếm lại.

## P2-05. Reconciliation phát hiện sai khác nguồn nhưng không phát hiện lỗi ETL

- **Phát hiện:** V1–V4 tạo `WARN` ở các tổng công bố không bằng nhau; đây là chênh lệch coverage/boundary của nguồn, không phải lỗi làm sạch và không được dùng để sửa/coalesce fact.
- **Số:** V1 **65 PASS / 23 WARN / 12 SKIP**; V2 **86/2/12**; V3 **39/49/12**. V4 có **528 phép so sánh = 248 exact + 86 immaterial + 194 material WARN**. V5 đạt **5.336/5.336** entity–year và **220/220** ASEAN.
- **Truy vết:** `output/stats/02_validation_results.csv`, lọc `check_id IN ('V1','V2','V3','V4','V5')`; logic tại `sql/02_validate.sql`.
- **Ý nghĩa:** các phân tích quốc gia/ASEAN dùng canonical fact bình thường; khi dùng aggregate World/châu lục/thu nhập phải giữ chú thích provenance.
- **Mức tin cậy:** Cao về kết quả số học; Trung bình về nguyên nhân các chênh lệch V1–V4 cho tới khi đối chiếu metadata từng nhà cung cấp.

## P2-06. Hard gate và schema đều sạch

- **Phát hiện:** bản phát hành Phase 2 vượt toàn bộ kiểm tra blocking.
- **Số:** **31 structural PASS**; V6 không trùng khoá, V7 không giá trị âm, V8 không tỷ lệ ngoài `[0,100]` — cả ba đều PASS. Tổng cộng **560 PASS / 268 WARN / 36 SKIP**, **0 blocking non-PASS**.
- **Truy vết:** `output/stats/02_validation_results.csv`; `sql/renewables.db`; `sql/01_schema.sql`; `sql/02_validate.sql`.
- **Ý nghĩa:** `fact_energy` và dimensions đủ điều kiện làm nguồn duy nhất cho Phase 3 và Power BI; 268 WARN được giữ như reconciliation audit, không làm fail pipeline.
- **Mức tin cậy:** Cao — SQLite `STRICT`, PK/FK/CHECK, `integrity_check`, `foreign_key_check` và CLI gate cùng xác nhận.

# Phase 3 — Phân tích mô tả

*(chưa thực hiện)*

# Phase 4 — Trực quan hoá

*(chưa thực hiện)*
