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

## P3-01 — Quy mô tái tạo ASEAN tăng rõ, nhưng tỷ trọng thế giới vẫn nhỏ

- **finding_id:** P3-01; **question_id:** Q1; **scope:** ASEAN/World; **period:** 2000–2021; **metric_name:** `generation_twh`.
- **Bằng chứng số:** tổng sản lượng tái tạo ASEAN tăng từ **72,800904 TWh** lên **289,655745 TWh**; thế giới tăng từ **2.854,49 TWh** lên **7.885,04005 TWh**.
- **Truy vết:** `output/stats/03_global_context.xlsx`, sheet `annual_context`, khóa `ASEAN_10|Y2000/Y2021|RENEWABLE_TOTAL|generation_twh`; `method_version=phase3_v1`; dấu vân tay bắt đầu bằng `64e1cc7d7bcb`.
- **Diễn giải:** quy mô ASEAN gần gấp bốn trong cửa sổ, nhưng cần đọc trong bối cảnh tổng thế giới cũng tăng mạnh.
- **Giới hạn:** dòng World là tổng do nguồn công bố, không phải tổng dựng lại từ các quốc gia; không suy luận nguyên nhân tăng. **Tin cậy:** Cao.

## P3-02 — Gió và mặt trời tăng nhanh từ nền rất thấp

- **finding_id:** P3-02; **question_id:** Q2; **scope:** ASEAN; **period:** 2000–2021; **metric_name:** `generation_twh`.
- **Bằng chứng số:** gió + mặt trời của ASEAN từ **0 TWh** năm 2000 lên **42,73 TWh** năm 2021; riêng CAGR 2000–2021 không xác định vì mẫu số bằng 0. Trong 2010–2021, CAGR là **69,3554%/năm**.
- **Truy vết:** `output/stats/03_global_context.xlsx`, các sheet `annual_context`, `period_growth`, khóa `ASEAN_10|MODERN_WIND_SOLAR`; `method_version=phase3_v1`.
- **Diễn giải:** tốc độ giai đoạn sau rất cao nhưng không được dùng CAGR từ năm 2000, nhờ vậy tránh giá trị vô hạn hoặc phóng đại từ nền 0.
- **Giới hạn:** “hiện đại” là định nghĩa vận hành gió + mặt trời của đồ án. **Tin cậy:** Cao.

## P3-03 — Thủy điện vẫn là thành phần lớn nhất năm 2021

- **finding_id:** P3-03; **question_id:** Q2; **scope:** ASEAN; **period:** 2021; **metric_name:** `generation_twh`.
- **Bằng chứng số:** thủy điện **185,58 TWh**, nguồn tái tạo khác **61,345745 TWh**, mặt trời **34,43 TWh**, gió **8,30 TWh**; tổng **289,655745 TWh**.
- **Truy vết:** `output/stats/03_asean_cross_section.xlsx`, sheet `asean_annual`, năm 2021; `method_version=phase3_v1`.
- **Diễn giải:** tách gió + mặt trời khỏi tổng tái tạo là cần thiết vì xếp hạng tổng có thể phản ánh lợi thế thủy điện sẵn có.
- **Giới hạn:** số liệu là sản lượng điện, không phải công suất hoặc tổng năng lượng sơ cấp. **Tin cậy:** Cao.

## P3-04 — Sản lượng gió + mặt trời tập trung mạnh

- **finding_id:** P3-04; **question_id:** Q6; **scope:** ASEAN; **period:** 2021; **metric_name:** `hhi/gini/top3_share`.
- **Bằng chứng số:** năm 2021, top 3 giữ **92,2537%** gió + mặt trời ASEAN; HHI **0,480404**, Gini **0,771285**. Với tổng tái tạo, các số tương ứng là **67,1023%**, **0,207886**, **0,529218**.
- **Truy vết:** `output/stats/03_global_context.xlsx`, sheet `annual_concentration`, khóa `Y2021|MODERN_WIND_SOLAR` và `Y2021|RENEWABLE_TOTAL`; `method_version=phase3_v1`.
- **Diễn giải:** phân bố gió + mặt trời giữa mười nước không đều hơn đáng kể so với tổng tái tạo.
- **Giới hạn:** tập trung của mức sản lượng không tự chứng minh nước nào tạo ra tăng trưởng; phải đọc riêng sheet `growth_contribution`. **Tin cậy:** Cao.

## P3-05 — Giá trị 0 làm mean và phân vị thấp nhạy với cách lọc

- **finding_id:** P3-05; **question_id:** Q1; **scope:** GLOBAL/ASEAN; **period:** 2000, 2010, 2021; **metric_name:** bộ thống kê phân phối.
- **Bằng chứng số:** gió ASEAN năm 2021 trên đủ 10 nước có mean **0,83 TWh**, median **0 TWh**, CV **1,655283**, gồm `zero_n=6`, `trace_n=0`, `material_n=4`. Khi chỉ giữ bốn nước `MATERIAL` từ **0,05 TWh**, mean tăng lên **2,075 TWh**, median **1,78 TWh**, CV giảm còn **0,704262**. Với mặt trời toàn cầu năm 2021 trên 210 quốc gia/vùng lãnh thổ quan sát được, mean là **4,954571 TWh**, median chỉ **0,06 TWh** và skewness **9,757789**.
- **Truy vết:** `output/stats/03_global_cross_section.xlsx` và `03_asean_cross_section.xlsx`, sheet `generation_stats`; `method_version=phase3_v1`.
- **Diễn giải:** median và các phân vị phù hợp hơn mean đơn độc khi phân phối lệch; ASEAN chỉ có n=10 nên các phân vị chỉ mang tính mô tả.
- **Giới hạn:** không suy rộng thống kê ASEAN như ước lượng cho một tổng thể ngẫu nhiên. **Tin cậy:** Cao.

## P3-06 — Hai cách đo làm thay đổi đáng kể vị trí của một số nước

- **finding_id:** P3-06; **question_id:** Q3; **scope:** ASEAN-10; **period:** 2021; **metric_name:** `asean_rank/modern_rank_gain`.
- **Bằng chứng số:** Việt Nam đứng hạng 1 theo cả tổng tái tạo và gió + mặt trời. Singapore tăng 4 bậc khi đổi cách đo; Indonesia giảm 4 bậc và Lào giảm 5 bậc. Thái Lan lên hạng 2 và Philippines lên hạng 3 theo gió + mặt trời, mỗi nước tăng 3 bậc so với xếp hạng tổng tái tạo (Thái Lan 5 → 2, Philippines 6 → 3).
- **Truy vết:** `output/stats/03_ranking_comparison.xlsx`, sheet `annual_ranks`, khóa `entity|Y2021`; `method_version=phase3_v1`.
- **Diễn giải:** xếp hạng tổng tái tạo có thể phản ánh lợi thế thủy điện lịch sử, nên công tắc gió + mặt trời ở các phase sau có ý nghĩa phân tích thực.
- **Giới hạn:** đây là xếp hạng sản lượng tuyệt đối, chưa điều chỉnh theo dân số, GDP hoặc nhu cầu điện. **Tin cậy:** Cao.

## P3-07 — Việt Nam chiếm tỷ trọng lớn trong gió + mặt trời ASEAN năm 2021

- **finding_id:** P3-07; **question_id:** Q4; **scope:** Vietnam/ASEAN-10/Global; **period:** 2021; **metric_name:** `generation_twh/country_share_asean/global_rank`.
- **Bằng chứng số:** Việt Nam tạo **104,2180361 TWh** tái tạo, bằng **35,9800%** ASEAN và đứng **16/205** toàn cầu; gió + mặt trời đạt **28,16 TWh**, bằng **65,9022%** ASEAN và đứng **17/209** toàn cầu.
- **Truy vết:** `output/stats/03_vietnam_time_series.xlsx`, sheet `annual`, các khóa `Vietnam|Y2021|RENEWABLE_TOTAL/MODERN_WIND_SOLAR`; `method_version=phase3_v1`.
- **Diễn giải:** vị thế của Việt Nam trong phần gió + mặt trời nổi bật hơn tỷ trọng trong tổng tái tạo của khu vực.
- **Giới hạn:** `ranked_n` thay đổi theo độ phủ toàn cầu nên không dùng hạng toàn cầu để kết luận thay đổi vị trí qua thời gian. **Tin cậy:** Cao.

## P3-08 — TWh và tỷ trọng điện của Việt Nam không phải lúc nào cũng cùng hướng

- **finding_id:** P3-08; **question_id:** Q5; **scope:** Vietnam; **period:** 2001–2021; **metric_name:** `direction_relation`.
- **Bằng chứng số:** tổng tái tạo có 19 năm cùng hướng và 2 năm ngược hướng; gió + mặt trời có 9 năm cùng hướng, 1 năm ngược hướng và 11 năm một hoặc cả hai thước đo không đổi.
- **Truy vết:** `output/stats/03_vietnam_time_series.xlsx`, sheet `annual_changes`, khóa `Y2001:Y2021|series_key|direction_relation`; `method_version=phase3_v1`.
- **Diễn giải:** tăng sản lượng TWh không đủ để suy ra tỷ trọng tái tạo trong tổng điện cũng tăng.
- **Giới hạn:** dữ liệu không có tổng nhu cầu điện, biến chính sách hay giá thành nên không quy nguyên nhân cho các năm ngược hướng. **Tin cậy:** Cao.

## P3-09 — Đóng góp tăng dương giai đoạn 2010–2021 tập trung ở Việt Nam

- **finding_id:** P3-09; **question_id:** Q6; **scope:** ASEAN-10; **period:** 2010–2021; **metric_name:** `positive_growth_share`.
- **Bằng chứng số:** Việt Nam đóng góp **65,9859%** tổng phần tăng dương gió + mặt trời và **42,3781%** tổng phần tăng dương của toàn bộ sản lượng tái tạo ASEAN.
- **Truy vết:** `output/stats/03_global_context.xlsx`, sheet `growth_contribution`, khóa `Vietnam|I2010_2021|MODERN_WIND_SOLAR/RENEWABLE_TOTAL`; `method_version=phase3_v1`.
- **Diễn giải:** kết quả đóng góp tăng dương, không chỉ HHI/Gini của mức sản lượng, cho thấy phần tăng giai đoạn này tập trung mạnh ở Việt Nam.
- **Giới hạn:** chỉ số loại phần giảm khỏi mẫu số và phải gọi đúng là tỷ trọng trong tổng phần tăng dương, không phải tỷ trọng trong tăng trưởng ròng. **Tin cậy:** Cao.

## P3-10 — Bộ kiểm định Phase 3 bao phủ đầy đủ Q1–Q6

- **finding_id:** P3-10; **question_id:** Q1–Q6; **scope:** Phase 3 release; **period:** 2000–2021; **metric_name:** `fact_metrics`.
- **Bằng chứng số:** `fact_metrics` có **18.926** dòng: Q1=5.544, Q2=3.608, Q3=1.980, Q4=1.382, Q5=5.950, Q6=462; **18.926/18.926** đối chiếu Python–SQL và **92/92** kiểm định có mã duy nhất đều `PASS`.
- **Truy vết:** `output/stats/03_fact_metrics.csv`, `03_crosscheck_results.csv`, `03_validation_results.csv`; dấu vân tay `64e1cc7d7bcb…`.
- **Diễn giải:** phạm vi kiểm chứng gồm giá trị, chữ, trạng thái, lý do, số đếm, thành phần, mẫu số và định dạng tỷ lệ trong workbook. Các mốc 18.926 dòng, phân bố Q1–Q6, 18.926 đối chiếu và chính xác tập 92 mã được khóa trực tiếp; CV đủ quan sát nhưng mean bằng 0 dùng `NOT_DEFINED / ZERO_MEAN`.
- **Giới hạn:** kiểm định chứng minh hai cách triển khai và các bất biến đã khóa nhất quán; nó không thay thế việc thẩm định định nghĩa nghiệp vụ bên ngoài đồ án. **Tin cậy:** Cao.

# Phase 4 — Trực quan hoá

## Trạng thái bản phát hành kỹ thuật

- Đã tạo đúng 13 PNG kích thước 2.400 × 1.350 điểm ảnh, 16 sheet trong
  `output/stats/04_chart_data.xlsx` và 38/38 kiểm định `BLOCKING` đều
  `PASS`. Toàn bộ sản phẩm mang `method_version=phase4_v1` và dấu vân tay
  `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10`.
- `python/04_test_contract.py` đã xác nhận `fact_energy.csv` đúng 89.075 dòng,
  đúng SHA-256 và bị chặn khi một giá trị C13 bị sửa mà khóa/số dòng không đổi.
  `python/04_test_publish.py` đã xác nhận hoàn tác đủ bản cũ khi có thể và giữ
  bản sao kèm đường dẫn khi phục hồi không đầy đủ. `python/04_verify_release.py`
  đã tự chạy 3/3 tiền điều kiện B1, dựng Phase 4 hai lần và xác nhận cùng nội
  dung workbook/CSV, cùng mã băm mảng điểm ảnh đã giải mã; 17 CSV nguồn,
  `fact_energy.csv` và 16 đầu ra được bảo vệ của Phase 3 không đổi trong hai
  lần dựng Phase 4.
- Rà trực quan ở kích thước 100% đã phát hiện và sửa ba lỗi trình bày cuối:
  dấu thập phân kiểu Anh ở C01/C05/C06/C12, chồng chữ ở C09 và thang màu C03
  dùng tỷ lệ kiểu Anh thay vì phần trăm kiểu Việt. Phiếu
  `docs/Phase4_Review.md` có 13/13 biểu đồ `ĐẠT` và được Nguyễn Hồng Minh ký
  ngày 2026-09-08; Phase 4 đã được đánh dấu hoàn tất trong `PLAN.md`.

## Ánh xạ phát hiện Phase 3 sang biểu đồ

Các hình C01–C12 không tạo phiên bản phát hiện mới mà trực quan hóa lại bằng
chứng đã kiểm chứng: C01 dẫn `P3-01`; C02 dẫn `P3-02`/`P3-03`; C04 dẫn
`P3-06`; C07/C09 dẫn `P3-07`; C08 dẫn `P3-08`; C10 dẫn `P3-05`; C12 dẫn
`P3-04`/`P3-09`. C03, C05, C06 và C11 là các lát cắt trình bày từ cùng
`fact_key` (khóa truy vết sự kiện) Phase 3, không thêm giải thích nguyên nhân.

## P4-01 — Chỉ số công suất xấp xỉ bị giới hạn mạnh bởi độ phủ

- **finding_id:** P4-01; **question_id:** Q4; **scope:** ASEAN-10;
  **period:** 2000–2021 theo quan sát khả dụng; **metric_name:**
  `capacity_factor_ratio`.
- **Bằng chứng số:** chỉ có **104** cặp sản lượng–công suất đủ điều kiện.
  Gió có **33** quan sát, gồm Philippines 17 năm (2005–2021) và Thái Lan 16
  năm (2006–2021); giá trị nằm trong **0–32,5764%**. Mặt trời có **71** quan
  sát, gồm Malaysia 15, Philippines 18, Thái Lan 16 và Việt Nam 22; giá trị
  nằm trong **0–25,2668%**. Tám nước thiếu công suất gió và sáu nước thiếu
  công suất mặt trời được liệt kê trực tiếp trên C13.
- **Truy vết:** `output/stats/04_chart_data.xlsx`, sheet `capacity_factor`,
  khóa `entity + year + technology`; mỗi dòng giữ
  `generation_source_key` và `capacity_source_key`. Công thức được tính lại
  độc lập trong `P4_C13_CONTRACT` và khớp trong dung sai `1e-9`.
- **Diễn giải:** độ phủ chỉ đủ để minh họa một chỉ số phụ, không đủ để xếp
  hạng đại diện cho ASEAN-10.
- **Giới hạn:** `capacity_gw` là công suất cuối năm; tỷ số
  `generation_twh / (capacity_gw × 8,76)` là chỉ báo xấp xỉ, không phải hiệu
  quả kỹ thuật và không hỗ trợ kết luận nước nào “tốt hơn”. **Tin cậy:** Cao
  cho phép tính trên 104 cặp đã quan sát; Thấp cho suy rộng ra toàn khu vực.

# Phase 5 — Dashboard Power BI

## P5-01 — Phép đo với tới ngoài cửa sổ tạo ra một năm ngược hướng không tồn tại

- **finding_id:** P5-01; **question_id:** Q5; **scope:** Vietnam;
  **period:** 2000–2021; **metric_name:** `direction_relation`, `yoy`.
- **Bằng chứng số:** hai phép đo DAX `Direction Relation` và `YoY` tra năm
  trước bằng `CALCULATE( …, ALL( DimYear ), DimYear[year] = _Year - 1 )`.
  `ALL( DimYear )` xoá **mọi** bộ lọc năm, kể cả cờ cửa sổ, nên năm 2000 với
  tới được năm 1999 — vốn nằm ngoài cửa sổ phân tích. Việt Nam có dữ liệu từ
  1965, và đoạn 1999 → 2000 đúng là một cặp ngược hướng: sản lượng
  **13,774 → 14,550 TWh** (+0,776) trong khi tỷ trọng điện
  **58,46598 → 54,781628%** (−3,684). Hệ quả: `direction_relation` trả
  **2000, 2003, 2014** thay vì **2003, 2014**, và `yoy` năm 2000 trả
  **+5,63%** thay vì để trống.
- **Truy vết:** đích khoá `P5_B8_VN_OPPOSITE_RENEWABLE_TOTAL` =
  `2003,2014` trong `output/stats/05_expected_values.csv`; phía tham chiếu
  `opposite_direction_years()` trong `python/05_expected.py` duyệt
  `K.YEARS[1:]` nên không bao giờ hỏi về năm 2000. `03_fact_metrics.csv` ghi
  `yoy · Y2000 · Vietnam` = `NOT_DEFINED`, và [[P3-08]] ghi period
  **2001–2021** với đúng **2** năm ngược hướng.
- **Diễn giải:** đây là phát hiện về **phương pháp**, không phải về năng
  lượng. Một cửa sổ phân tích chỉ có hiệu lực khi mọi phép tính tham chiếu
  chéo thời gian cũng tôn trọng nó; một lệnh `ALL()` đặt để bỏ bộ lọc năm
  cũng bỏ luôn cờ cửa sổ, và dữ liệu ngoài cửa sổ lặng lẽ chảy vào kết quả.
  Lỗi này không tạo ra `NaN`, không tạo ra số âm, không làm ô nào trắng —
  nó tạo ra **một con số trông hoàn toàn hợp lý**, nên chỉ đối chiếu với
  phía tham chiếu độc lập mới bắt được.
- **Cách chặn:** thêm `DimYear[is_main_asean_window] = 1` vào chính lệnh tra
  năm trước, để năm 2000 trả `BLANK` thay vì với ra ngoài cửa sổ. Đã sửa
  ngày 2026-09-09 trong `python/05_measures.py` (M036, M050); mô phỏng lại
  ngữ nghĩa đã sửa trên `output/clean/` cho đúng `2003,2014` và `2016`.
- **Giới hạn:** phát hiện này không đổi bất kỳ con số nào của Phase 1–4;
  `05_expected_values.csv` giữ nguyên 169 đích. **Tin cậy:** Cao — kiểm
  chứng được bằng số mà không cần mở Power BI.

## P5-02 — Phép đo ghim năm không thể đặt lên trục thời gian

- **finding_id:** P5-02; **question_id:** Q2, Q4; **scope:** Vietnam;
  **period:** 2000–2021; **metric_name:** `country_share_asean`,
  `global_rank`, `ranked_n`.
- **Bằng chứng số:** `Gen TWh @Year` mở đầu bằng `ALL( DimYear )` rồi đặt
  lại năm theo slicer. Mọi phép đo dựng trên nó — `Country Share ASEAN`,
  `Global Rank`, `Global Ranked N` — vì thế trả **cùng một giá trị cho mọi
  điểm** trên một trục năm: biểu đồ V08 ra đường phẳng tuyệt đối, và cột
  hạng trong bảng V09 in `16` cùng `205` trên cả 22 dòng. Vì các phép đo này
  không bao giờ trả trống, biểu đồ và bảng còn kéo theo cả **57** dòng
  `DimYear` (1965–2021) chứ không phải 22 dòng trong cửa sổ.
- **Truy vết:** `powerbi/DAX_Measures.md`, các phép đo M014, M031, M041,
  M042; catalogue ô trực quan `python/05_visuals.py`, nhóm V08 và V09.
- **Diễn giải:** một phép đo KPI cho **một năm** và một phép đo cho **một
  chuỗi** là hai vật khác nhau, dù cùng định nghĩa nghiệp vụ. Mô hình đã có
  sẵn quy ước `@Year` / `ToDate` cho cặp này ở nhóm sản lượng nhưng chưa
  trải hết sang nhóm tỷ trọng và nhóm hạng.
- **Cách chặn:** thêm bản `ToDate` cho đúng những phép đo được vẽ theo thời
  gian (M037, M045, M046, M047 và ba bản khoá Việt Nam M098–M100), và gắn
  lại V08/V09 vào bản `ToDate`. Hệ quả phụ: mọi phép đo trên trang 2 giờ đều
  mang cờ cửa sổ, nên các năm trước 2000 tự rụng khỏi trang mà không cần bộ
  lọc mức trang. **Tin cậy:** Cao.

## P5-03 — Tệp bàn giao đi sau catalogue mà không kiểm định nào bắt được

- **finding_id:** P5-03; **question_id:** — (phát hiện phương pháp);
  **scope:** toàn Phase 5; **period:** 2026-09-09 → 2026-09-10;
  **metric_name:** `measure_count`, `entry_key_rows`.
- **Bằng chứng số:** ngày 2026-09-09, ba lỗi được sửa và đo đạt **trên model
  đang sống trong Power BI Desktop**. Hôm sau, PBIP nằm trong `powerbi/` vẫn
  mang **71** phép đo chống lại catalogue **73** — thiếu `Entry Metric Count`
  (M120) và `ASEAN Completeness Label` (M121). Kéo theo: 0/5 phép đo gia nhập
  còn chốt `[Entry Metric Count]`, nên bảng V12 quay lại **10 × 7 = 70** dòng
  thay vì **40**; và `Rank Status` trả `NOT_DEFINED / ZERO_SCOPE_TOTAL` **có dấu
  cách** trong khi Phase 3 ghép chuỗi **không dấu cách** — sai lệch này chạm cả
  trang 2 qua `VN Rank Label`. Nguyên nhân: Desktop lưu lúc 22:25 từ bản nó nạp
  **trước** khi `05_measures.py` (22:16) và `05_visuals.py` (22:20) được sửa.
- **Truy vết:** `docs/Phase5_Review.md` §"Bản PBIP đi sau catalogue";
  `python/05_test_artifacts.py` tiêu chí C1, C2, C3, C5.
- **Diễn giải:** điều khoản §8.5 của `PHASE5.md` đã lường trước đúng rủi ro này
  và yêu cầu "sau mỗi lượt MCP ghi, xuất lại danh mục và so với
  `DAX_Measures.md`". Lượt 2026-09-09 **đã làm đúng vậy** và vẫn trượt, vì phép
  so được thực hiện trên **model sống**, còn thứ đem nộp là **tệp trên đĩa**.
  Một quy trình đúng chữ vẫn hỏng khi nó so nhầm vật. Sai lệch thứ ba — dấu cách
  trong một chuỗi trạng thái — soi bằng mắt không thể thấy; chỉ phép đối chiếu
  biểu thức mới bắt được.
- **Cách chặn:** cơ giới hoá phép so bằng `python/05_test_artifacts.py`, đọc
  thẳng TMDL, `report.json` và `DAX_Measures.md`, **không cần Power BI**. Bộ tiêu
  chí được viết trước khi sửa và bắt buộc phải trượt trên bản hỏng: lần chạy đầu
  cho `FAIL | failed=C1,C2,C3,C5,C6 | passed=4/9`; sau khi dựng lại thì `PASS`.
  **Tin cậy:** Cao.

## P5-04 — Khối định dạng chỉ vào được catalogue sau khi đi vòng qua Desktop

- **finding_id:** P5-04; **question_id:** — (phát hiện phương pháp);
  **scope:** ô V10 và V08_GLOBAL, trang 2 và trang 3; **period:** 2026-09-10;
  **metric_name:** —.
- **Bằng chứng số:** `05_build_report.py` chỉ ghi những hình dạng JSON đã được
  **lấy mẫu thật** từ Desktop, nên khối `objects` — lớp định dạng bên trong ô —
  trước đây luôn được ghi rỗng. Hệ quả đo được: lưới small multiples của V10 rơi
  về mặc định **2 × 2**, tức **4/10** nước hiện và 6 nước phải cuộn, trong khi
  Gate B9 đòi đủ 10 và Gate B10 đòi PDF không cắt — mà bản xuất tĩnh chỉ in phần
  đang hiện. Cùng lý do, `invertAxis` của V08_GLOBAL không sinh được nên biểu đồ
  hạng đọc **ngược** (hạng 1 nằm dưới).
- **Truy vết:** `python/05_visuals.py` hằng số `SMALL_MULTIPLES_5X2` và
  `INVERTED_RANK_AXIS`; `python/05_build_report.py :: render_visual`;
  `python/05_test_artifacts.py` tiêu chí C10.
- **Diễn giải:** thế bí ở đây có cấu trúc vòng — catalogue không sinh được thứ
  chưa có mẫu, mà mẫu chỉ sinh ra khi đặt tay trong Desktop. Lối ra là chấp nhận
  một vòng lấy mẫu: đặt tay → Desktop ghi JSON → trích khối → đưa vào catalogue →
  thêm tiêu chí chống hồi quy. Một khi mẫu đã có, nó dùng lại được cho ô khác:
  đúng thuộc tính `valueAxis.invertAxis` lấy từ mẫu lưới V10 đã giải phóng luôn
  mục 7, biến một việc tay thành việc catalogue.
- **Cách chặn:** thứ tự là bắt buộc, vì `05_build_pbip.py :: main()` gọi
  `shutil.rmtree` lên cả `.SemanticModel/` và `.Report/` trước khi dựng — trích
  mẫu **trước**, dựng lại **sau**. C10 khoá **văn bản literal** chứ không khoá
  giá trị đã phân giải: Desktop viết số nguyên có hậu tố `L` còn boolean thì
  không, và một boolean viết thành `1L` vẫn được định dạng tệp chấp nhận rồi đọc
  lại như chưa đặt gì — cùng lớp bẫy kiểu với `is_asean = 1L`. **Tin cậy:** Cao.

# Phase 6 — Diễn giải và slide

## P6-01 — Hai nguồn khớp nhau không chứng minh gì nếu một nguồn chép từ nguồn kia

- **finding_id:** P6-01; **question_id:** — (phát hiện phương pháp);
  **scope:** 47 con số của mục 1.5a và 1.5b; **period:** 2026-09-10.
- **Bằng chứng số:** bộ kiểm chứng Gate E3 thu **ba** cách đọc cho mỗi con số: hằng
  số chép tay trong `phase6_contract.py`, tra cứu trong `03_fact_metrics.csv`, và một
  phép tính lại **chỉ đọc** `output/clean/*.csv`. Kết quả **47/47 MATCH**. Điểm đáng
  chú ý nằm ở phân bố chênh lệch: **17/47** claim có delta khác 0, lớn nhất
  `9,095 × 10⁻¹³`, dưới dung sai `10⁻⁹`.
- **Truy vết:** `python/06_verify_findings.py`; `output/stats/06_finding_evidence.csv`,
  cột `max_abs_delta`.
- **Diễn giải:** chính những delta khác 0 ấy mới là bằng chứng. Nếu nhánh thứ ba đọc
  lại bảng thay vì tự tính thì **mọi** delta sẽ bằng 0 tuyệt đối — và một bộ kiểm
  chứng trả toàn số 0 hoàn hảo là dấu hiệu nó đang so một thứ với chính nó. Nhiễu kết
  hợp dấu phẩy động ở mức `10⁻¹³` là dấu vân tay của phép cộng chạy theo thứ tự khác,
  tức là đường đi thật sự độc lập.
- **Cách chặn:** ba nhánh phải có ít nhất một nhánh **tính lại từ dữ liệu thô**, không
  phải ba lần đọc ba bảng dẫn xuất. Ràng buộc dòng 13 của chính nhật ký này —
  *"mọi con số đưa vào BaoCao.md phải tính lại từ nguồn"* — nay được cơ giới hoá thay
  vì trông cậy vào kỷ luật. **Tin cậy:** Cao.

## P6-02 — Tiêu chí truy vết chỉ có nghĩa khi máy cưỡng chế được

- **finding_id:** P6-02; **question_id:** — (phát hiện phương pháp);
  **scope:** 11 slide của mục 1.5b; **period:** 2026-09-10.
- **Bằng chứng số:** `PLAN.md` dòng 348 đòi *"mỗi con số trên slide truy được về một
  bảng trong `output/stats/`"*. Phát biểu này không kiểm được bằng mắt trên 11 slide
  mà không bỏ sót. `06_build_slides.py` biến nó thành một phép so tập hợp: quét mọi
  chuỗi số trong chữ trên slide, đối chiếu với tập giá trị sinh từ hợp đồng, và **từ
  chối ghi tệp** nếu còn số lạ. Lần chạy đầu trả `FAIL` với bốn token.
- **Truy vết:** `python/06_build_slides.py`, hàm `assert_no_stray_numbers()` và
  `scannable()`.
- **Diễn giải:** bốn token bị bắt đều là **chữ tài liệu** chứ không phải số liệu —
  `00` và `02` nằm trong tên tệp ở chân trang, `1.6` là số hiệu mục. Cám dỗ tự nhiên
  là thêm cả bốn vào danh sách cho phép. Làm vậy vài lần thì danh sách phình đến mức
  bộ chặn không còn chặn gì; tiêu chí vẫn "đạt" mà không còn ý nghĩa.
- **Cách chặn:** lọc tên tệp và số hiệu mục **trước** khi quét, giữ danh sách cho phép
  nhỏ và ghi rõ lý do từng mục trong đó. Nguyên tắc chung: khi một bộ kiểm định báo
  sai, sửa **phạm vi quét** chứ đừng nới **ngưỡng chấp nhận**. **Tin cậy:** Cao.

# Phase 7 — Kết luận, đề xuất và bộ hồ sơ nộp

## P7-01 — Sản lượng tăng bảy lần mà tỷ trọng vẫn giảm

- **finding_id:** P7-01; **question_id:** Q4, Q5; **scope:** Vietnam;
  **period:** 2000–2021; **metric_name:** `generation_twh`, `share_electricity_pct`.
- **Bằng chứng số:** sản lượng NLTT của Việt Nam đi từ **14,55** lên **104,2180 TWh**
  — gấp **7,16 lần**. Cùng kỳ, tỷ trọng NLTT trong tổng sản lượng điện lại **giảm**
  từ **54,7816%** xuống **42,5787%**, mất **12,20 điểm phần trăm**.
- **Truy vết:** `F6_VN_TOTAL_2000`, `F4_VN_TOTAL_2021`, `F6_VN_SHARE_ELEC_2000`,
  `F6_VN_SHARE_ELEC_2021` trong `output/stats/06_finding_evidence.csv`.
- **Diễn giải:** hai con số này cùng đúng và ngược chiều nhau, vì mẫu số — tổng cầu
  điện — tăng còn nhanh hơn tử số. Một báo cáo chỉ trích dẫn "tăng bảy lần" sẽ để
  người đọc hiểu ngược hẳn thực tế về mức độ chuyển dịch của hệ thống điện.
- **Cách chặn:** mọi chỉ tiêu năng lượng tái tạo phải nói rõ đo bằng **sản lượng**
  hay bằng **tỷ trọng**; đây cũng là lý do đề xuất VN-2 khuyến nghị đặt mục tiêu theo
  tỷ trọng thay vì chỉ theo TWh. **Tin cậy:** Cao.

## P7-02 — Một danh sách rủi ro không tự chặn được rủi ro

- **finding_id:** P7-02; **question_id:** — (phát hiện phương pháp);
  **scope:** quy trình dựng notebook; **period:** 2026-09-10.
- **Bằng chứng số:** bảng rủi ro của kế hoạch có sẵn dòng *"Tiếng Việt trên Windows
  → `UnicodeEncodeError` → lưu UTF-8"*. Rủi ro đó **vẫn xảy ra**: tệp nội dung
  notebook phần 4–5 được ghi ra với **toàn bộ dấu tiếng Việt biến thành dấu hỏi**
  (`M?c 1.3 ? Th?ng k? m? t?`), đếm ký tự ngoài ASCII bằng **0**.
- **Truy vết:** `docs/Phase7_Review.md` §2.1 lỗi L1; chốt chặn nay nằm ở
  `python/07_build_notebook.py`, hàm `main()`.
- **Diễn giải:** điều làm lỗi này nguy hiểm không phải độ khó mà là **sự im lặng**:
  tệp hỏng vẫn decode được bằng UTF-8, vẫn chạy đúng, vẫn cho số đúng. Không một
  ngoại lệ nào được ném ra. Chỉ đọc bằng mắt mới thấy — mà tệp dài 39 KB thì không
  ai đọc hết.
- **Cách chặn:** biến dòng cảnh báo thành một phép kiểm chạy được — sau khi ghi tệp,
  đếm ký tự có mã > 127 trong **tệp vừa ghi trên đĩa**; bằng 0 thì ném lỗi. Nguyên
  tắc rút ra: một rủi ro đã biết chỉ thực sự được chặn khi có mã kiểm nó, còn nằm
  trong bảng rủi ro thì mới chỉ là được ghi nhớ. **Tin cậy:** Cao.

## P7-03 — Phép kiểm số hiệu liên tục bắt được lỗi mất nội dung

- **finding_id:** P7-03; **question_id:** — (phát hiện phương pháp);
  **scope:** `07_notebook_cells.py`; **period:** 2026-09-10.
- **Bằng chứng số:** khi sửa docstring đầu tệp nội dung, ô markdown số 1 — phần giới
  thiệu đồ án — bị cắt mất. `read_cells()` báo ngay
  `so hieu o khong lien tuc: [2, 3, ..., 42]`.
- **Truy vết:** `python/07_build_notebook.py :: read_cells`.
- **Diễn giải:** nguyên nhân là dùng `partition` trên dấu nháy ba hai lần; lần thứ
  hai bắt trúng dấu nháy **mở đầu** của ô markdown 1 chứ không phải dấu đóng
  docstring. Nếu `read_cells()` chỉ đếm tổng số ô thay vì kiểm tính liên tục thì
  notebook sẽ được dựng với 41 ô, chạy trơn tru, và thiếu hẳn phần giới thiệu mà
  không ai biết.
- **Cách chặn:** kiểm **tính liên tục** chứ không kiểm số đếm. Số đếm chỉ phát hiện
  được mất mát khi ta biết trước phải có bao nhiêu; tính liên tục phát hiện được cả
  khi không biết. **Tin cậy:** Cao.
