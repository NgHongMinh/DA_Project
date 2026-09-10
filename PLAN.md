# QUY TRÌNH THỰC HIỆN ĐỒ ÁN
## Phân tích Năng lượng tái tạo — Việt Nam & Đông Nam Á

---

## Bối cảnh

`note.txt` yêu cầu đồ án gồm 6 nội dung (1.1 → 1.6), thực hiện bằng **ít nhất 2 trong 3 công cụ: SQL, Power BI, Python**. Nguồn dữ liệu: bộ **Renewable Energy World Wide** (Our World in Data — Ember + BP), **17 file CSV / 74 cột / 251 thực thể / 1965–2022**, tại [archive/](archive/).

**Đã chốt với người dùng:**

| Mục | Lựa chọn |
|---|---|
| Công cụ | **Cả 3** — Python (làm sạch, thống kê, biểu đồ) · SQLite + Navicat Premium 17 (truy vấn phân tích) · Power BI (dashboard) |
| Hướng phân tích | **Việt Nam & Đông Nam Á chuyên sâu** |
| Ngôn ngữ | Văn bản / biểu đồ / dashboard = **tiếng Việt** · code & tên cột = **tiếng Anh** |
| Slide (1.5b) | Hoãn sang phiên sau — ⚠️ vẫn là yêu cầu có điểm |

**Mục tiêu tổng thể:** trả lời được *Đông Nam Á đang chuyển dịch sang năng lượng tái tạo đến đâu, và Việt Nam đứng ở đâu trong đó* — với dữ liệu đã được làm sạch có kiểm định, thống kê mô tả đầy đủ, biểu đồ và dashboard.

---

## Phân vai

> **Người dùng tự tay thực hiện toàn bộ đồ án.** Đây là bài học, không phải việc cần giao khoán.
>
> Claude **không** viết code, không tạo file, không chạy script — trừ khi người dùng yêu cầu trực tiếp cho một việc cụ thể.
>
> Vai trò của Claude: giải thích khi được hỏi · gợi ý hướng khi bị tắc · review code hoặc kết quả khi được đưa cho · chỉ ra lỗi logic phân tích · trả lời câu hỏi về công cụ.
>
> Tài liệu này là **bản đồ để người dùng đi theo**, không phải danh sách việc để Claude làm.

---

## Nguyên tắc xuyên suốt

1. **Không sửa file trong `archive/`.** Mọi biến đổi ghi ra `output/`.
2. **Mỗi phase có sản phẩm cụ thể và tiêu chí hoàn thành.** Không sang phase sau khi phase trước chưa đạt tiêu chí.
3. **Phát hiện gì cũng phải kiểm chứng lại bằng số** trước khi viết vào báo cáo.
4. **Kết luận đi sau dữ liệu.** Phase 1–4 không viết sẵn kết luận; kết luận là sản phẩm của Phase 7.
5. Mỗi phase kết thúc bằng việc **ghi lại phát hiện vào `docs/NhatKyPhanTich.md`** để Phase 6–7 có nguyên liệu.
6. **Mọi script import đường dẫn từ `python/config.py`**, không hard-code `d:\DA\Final_Project` rải rác.

## Đặc điểm SQLite cần nhớ

Ba điểm này sẽ gây lỗi ở Phase 2–3 nếu không biết trước:

1. ⚠️ **Navicat giữ file `.db` → Python ghi báo `database is locked`.** Mỗi lần chạy lại script nạp dữ liệu, **đóng connection trong Navicat trước**.
2. ⚠️ **SQLite không có hàm percentile** (`PERCENTILE_CONT` là của SQL Server/Postgres). Các phân vị P10…P99 mà mục 1.3 yêu cầu tính bằng **pandas `.quantile()`** — đúng phân công sẵn có. Nếu cần làm trong SQL thì dùng `PERCENT_RANK()` / `CUME_DIST()`.
3. ⚠️ **Type affinity lỏng** — nạp text vào cột số SQLite vẫn nhận, lỗi sẽ ẩn thay vì báo. Bù bằng: khai báo kiểu tường minh khi `CREATE TABLE` + kiểm tra dtype trong pandas **trước** khi nạp + bộ kiểm định V1–V8.

**Power BI đọc `output/clean/*.csv`, KHÔNG nối vào `.db`** — Power BI không có connector SQLite native, mà cài ODBC driver cần quyền admin (máy này không có). Đây là lựa chọn có chủ ý, không phải hạn chế.

---

## Cấu trúc thư mục sẽ tạo

```
d:\DA\Final_Project\
├── archive\                    17 CSV gốc — KHÔNG SỬA
├── note.txt
├── PLAN.md
├── python\
│   ├── config.py               ✅ đường dẫn + danh sách ASEAN_10 dùng chung
│   ├── requirements.txt         ✅ 6 thư viện
│   ├── 00_check_env.py         ✅ kiểm tra môi trường (Phase 0)
│   ├── run_sql.py              ✅ chạy file .sql không cần CLI
│   ├── 01_profile.py           ✅ Phase 1 hợp nhất
│   ├── 02_clean_build.py       ✅ ETL + mô hình dữ liệu Phase 2
│   ├── 03_descriptive.py       ✅ Phase 3 Q1–Q6 + đối chiếu + công bố
│   ├── 03_test_publish.py      ✅ kiểm thử hoàn tác tệp thường + SQLite fallback Phase 3
│   ├── 03_verify_release.py    ✅ kiểm thử tái lập hai lần Phase 3
│   ├── 04_charts.py            ✅ Phase 4 — 13 PNG + workbook + 38 kiểm định
│   ├── 04_test_contract.py     ✅ kiểm thử hợp đồng Phase 4
│   ├── 04_test_publish.py      ✅ kiểm thử hoàn tác phát hành Phase 4
│   ├── 04_verify_release.py    ✅ kiểm thử tái lập hai lần Phase 4
│   ├── phase4_contract.py      ✅ hằng số khóa Phase 4
│   ├── phase5_contract.py      ✅ hằng số khóa Phase 5 (bộ số §5 của PHASE5.md)
│   ├── 05_measures.py          ✅ nguồn DUY NHẤT của 73 phép đo DAX
│   ├── 05_expected.py          ✅ tính lại 169 đích nghiệm thu, đối chiếu ba chiều
│   ├── 05_build_pbip.py        ✅ sinh PBIP dạng TMDL + DAX_Measures.md
│   ├── 05_acceptance.py        ✅ sinh 05_acceptance.dax từ bộ đích
│   ├── 05_validate.py          ✅ đối chiếu kết quả Power BI → 05_validation_results.csv
│   └── 05_test_artifacts.py    ✅ C1–C9: chặn PBIP đi sau catalogue, không cần Power BI
├── sql\
│   ├── renewables.db           ✅ 89.075 fact rows + validation results
│   ├── 01_schema.sql           ✅ schema STRICT + `vw_wide`
│   ├── 02_validate.sql         ✅ V1–V8
│   └── 03_analysis.sql         ✅ nhánh tính SQL độc lập Q1–Q6
├── output\
│   ├── clean\                  ✅ 7 CSV sạch (nguồn cho Power BI)
│   ├── stats\                  ✅ đầu ra Phase 1–5, gồm 6 workbook + `03_*` + `04_*` + `05_*`
│   └── charts\                 ✅ 13 PNG
├── powerbi\
│   ├── ASEAN_Renewables.pbip           ✅ dự án dạng văn bản — nguồn để dựng .pbix
│   ├── ASEAN_Renewables.SemanticModel\ ✅ TMDL: 8 bảng, 3 quan hệ, 61 phép đo
│   ├── ASEAN_Renewables.Report\        khung ba trang (chặng 2 dựng đủ V01–V14)
│   ├── ASEAN_Renewables.pbix           ⬅ Desktop sinh ra — SẢN PHẨM NỘP
│   ├── README.md                       ✅ cách dựng, mô hình, quy ước, đường dự phòng
│   ├── DAX_Measures.md                 ✅ danh mục phép đo (sinh tự động)
│   ├── ASEAN_Renewables_theme.json     ✅ bảng màu Phase 4 — áp tay một lần trong Desktop
│   └── 05_acceptance.dax               ✅ 169 truy vấn nghiệm thu (sinh tự động)
└── docs\                       Phase1_KhaoSatDuLieu.md · NhatKyPhanTich.md · BaoCao.md
                                Phase4_Review.md · Phase5_Review.md
```
*(✅ = đã tạo và kiểm chứng xong · ⬅ = cần một thao tác tay trong Power BI Desktop)*

---

# ✅ PHASE 0 — Chuẩn bị môi trường *(ĐÃ HOÀN THÀNH)*

**Mục tiêu:** có đủ 3 công cụ chạy được trên máy.

**Đã cài / đã tạo:**

| Thành phần | Phiên bản thực tế | Ghi chú |
|---|---|---|
| Python | **3.12.10** | `winget --scope user` (máy **không có quyền admin**) |
| SQLite trong Python | **3.49.1** | module `sqlite3` built-in — không cần driver |
| sqlite3 CLI | **3.53.4** | portable qua winget, alias `sqlite3` / `sqldiff` / `sqlite3_analyzer` |
| pandas · numpy · matplotlib | 3.0.5 · 2.5.2 · 3.11.1 | |
| seaborn · scipy · openpyxl | 0.13.2 · 1.18.0 · 3.1.5 | |
| Power BI Desktop | 2.156.951.0 | đã có sẵn (Microsoft Store) |
| Navicat Premium | 17.3 | có `sqlite.dll` + `sqlite3.dll` → hỗ trợ SQLite native |

**Cạm bẫy đã xử lý:** `python.exe` trước đó là **stub Microsoft Store 0 byte**. Installer Python đã tự đưa thư mục thật lên **đầu** PATH user nên `python` giờ trỏ đúng chỗ. Nếu về sau lại trỏ vào `WindowsApps` → tắt app execution alias trong *Settings → Apps → Advanced app settings*.

**Đầu ra:** `python/{config.py, requirements.txt, 00_check_env.py, run_sql.py}` · `sql/renewables.db` · cây thư mục 8 mục.

**Tiêu chí hoàn thành — đã đạt 26/26:**
```powershell
python python\00_check_env.py     # => TONG KET PHASE 0: 26/26 tieu chi dat
```
Script kiểm tra thật (không giả định): phiên bản Python và `sys.executable` không nằm trong `WindowsApps` · 6 thư viện import được · SQLite ≥ 3.25 · `ROW_NUMBER() OVER`, `LAG() OVER`, CTE, `CREATE VIEW IF NOT EXISTS` **chạy thật** · ghi/xoá được bảng trên file `.db` · đếm đúng 17 CSV · pandas đọc thử được 1 file.

**Còn 1 việc tự làm bằng tay:** Navicat Premium 17 → *Connection → SQLite* → trỏ tới `d:\DA\Final_Project\sql\renewables.db`.

---

# ✅ PHASE 1 — Khảo sát dữ liệu & xác định vấn đề *(yêu cầu 1.1 — ĐÃ HOÀN THÀNH)*

**Mục tiêu:** hiểu dữ liệu có gì / thiếu gì **trước khi** đặt câu hỏi phân tích, rồi chốt câu hỏi mà dữ liệu thật sự trả lời được.

**Cách chạy duy nhất:**
```powershell
python python\01_profile.py
```

`python/01_profile.py` đọc và kiểm tra 17 CSV một lần, thực hiện tuần tự cả 7 bước trong bộ nhớ, rồi chỉ ghi đầu ra khi toàn bộ phép tính thành công. Script chạy độc lập với mọi đầu ra cũ và chạy lại phải cho kết quả giống nhau.

**Các bước bên trong script (theo đúng thứ tự):**
1. **Lập hồ sơ dữ liệu** — với cả 17 file: đọc header, đếm dòng, khoảng năm, số thực thể, số ô rỗng, số giá trị 0, min/max.
2. **Lập bảng tầng độ phủ** — nhóm 17 file theo số thực thể và khoảng năm. Đây là bước quan trọng nhất của Phase 1: các file phủ rất khác nhau (từ 251 xuống 33 thực thể), quyết định toàn bộ chiến lược join ở Phase 2.
3. **Kiểm tra trùng lặp giữa các file** — so từng dòng theo khoá `(Entity, Year)` giữa các file cùng đo một đại lượng. Ghi lại file nào trùng file nào, file nào xung đột giá trị.
4. **Kiểm tra tính thống nhất khoá join** — tên `Entity` ở các file có khớp nhau không, có cần fuzzy matching không.
5. **Lập bảng độ phủ 10 nước ASEAN × 17 file** — nước nào có mặt ở file nào. Bước này quyết định phạm vi phân tích có khả thi hay không.
6. **Kiểm tra tính liên tục theo năm** của từng thực thể — có lỗ hổng ở giữa hay chỉ cắt đầu/cắt cuối. Quyết định có nội suy hay không.
7. **Kiểm tra năm cuối** — đếm số dòng mỗi năm để phát hiện năm bị cắt cụt.
8. Tổng hợp ý nghĩa, phương pháp, cách đọc kết quả, vai trò, hệ quả cho Phase 2 và giới hạn diễn giải của cả 7 bước vào `docs/Phase1_KhaoSatDuLieu.md`.
9. Từ kết quả 1–7, viết mục 1.1 trong `docs/BaoCao.md`:
   - câu hỏi trung tâm + 5–6 câu hỏi con, mỗi câu gắn với chỉ số cụ thể sẽ tính
   - **danh sách những gì dữ liệu KHÔNG trả lời được** (giá thành, dân số, phát thải, chính sách, gió trên bờ/ngoài khơi…) — mục này có điểm, không được bỏ

**Công cụ:** Python

**Đầu ra:**

- `output/stats/00_phase1_summary.txt` (UTF-8, không timestamp): 7 phần kết quả và phần quyết định cuối Phase 1.
- Năm CSV chi tiết, giữ ổn định tên và schema: `01_overlap_conflict_details.csv` (15 cột), `02_join_key_details.csv` (13), `03_asean_coverage_details.csv` (7), `04_year_continuity_details.csv` (22), `05_last_year_check.csv` (14).
- `docs/Phase1_KhaoSatDuLieu.md`, mục 1.1 của `docs/BaoCao.md`, `docs/NhatKyPhanTich.md`.

**Hai quy ước Phase 1 đặt ra, Phase 2–3 phải dùng lại nhất quán:**

1. **Ngưỡng `MATERIAL` = `abs_diff > 0,05 TWh` VÀ `rel_diff > 1%`.** Dùng để tách chênh lệch thật khỏi sai số làm tròn khi so hai nguồn. Phải vượt **cả hai**: chỉ dùng % thì `0` vs `0,005 TWh` thành lệch 100%; chỉ dùng tuyệt đối thì `0,5 TWh` trên `1.200 TWh` cũng bị tính là lệch. Nhãn dưới ngưỡng là `IMMATERIAL`, **không** phải `ROUNDING` — nhóm đó còn chứa chênh lệch tới 39 TWh nằm dưới mốc 1%.
2. **Độ phủ chuỗi đo bằng cột `*_effective`, không dùng cột thô.** `coverage_pattern` đo so với năm lớn nhất có mặt trong file, nên bị năm 2022 cắt cụt chi phối; `coverage_pattern_effective` đo so với `recommended_end_year` của Step 7. Lọc nhầm cột thô sẽ giữ 22 thực thể của file `03` thay vì 89.

Phase 1 không tạo workbook Excel. `00_data_profile.xlsx` và các script Step 2–7 riêng lẻ không còn là đầu vào hay điều kiện chạy của quy trình.

**Tiêu chí hoàn thành — đã đạt.** Năm câu hỏi và nơi trả lời:

| # | Câu hỏi | Trả lời ở |
|---|---|---|
| a | Dùng file nào, bỏ file nào, vì sao | `Phase1_KhaoSatDuLieu.md` §10.1 |
| b | Join theo chiến lược nào | §10.2 |
| c | ASEAN-10 đủ dữ liệu ở chỉ số nào | §10.3 |
| d | Có nội suy hay không | §10.4 |
| e | Cắt cửa sổ phân tích ở năm nào | §10.5 |

> ⚠️ **Các phát hiện Phase 1 phải giữ làm kiểm chứng hồi quy:**
>
> - `INNER JOIN` cả 17 file chỉ giữ **3,125%** thực thể và 1,8673% khoá.
> - Ba file `05`, `08`, `12` chứa chỉ số là **tập con dư thừa** của các cột tương ứng trong file `03` — không có nghĩa toàn bộ file giống nhau.
> - Năm 2022 bị cắt cụt nặng ở **8 file** (~12% đường nền, 0 nước ASEAN).
> - File `02` và `03` lệch ở mức `MATERIAL` chủ yếu về **quy mô** ở thực thể tổng hợp (tối đa 159 TWh), trong khi ở cấp quốc gia phần lớn chỉ là sai số làm tròn. **Việt Nam không có dòng `MATERIAL` nào.**
> - Vực coverage tại **năm 2000**: panel nhảy từ 106 lên 247 thực thể do nguồn thay đổi → mọi chỉ số "% số nước" phải dùng mẫu số cố định.
> - Chỉ **35/2.702** chuỗi có lỗ hổng giữa, và 31 trong đó là nhịp lấy mẫu 5 năm của file `17` chứ không phải dữ liệu bị mất. **Không chuỗi ASEAN nào cần nội suy.**
> - Bốn cặp tên gần giống đều là thực thể **khác nhau** (`South Africa` ↔ `South America`) → cấm fuzzy matching.

---

# ✅ PHASE 2 — Tiền xử lý & dựng mô hình dữ liệu *(yêu cầu 1.2 — ĐÃ HOÀN THÀNH)*

**Mục tiêu:** từ 17 file rời rạc → một mô hình dữ liệu sạch, có kiểm định, dùng chung được cho Python / SQL / Power BI.

**Các bước:**
1. **Chốt tập file sử dụng** — loại các file trùng lặp; với file xung đột giá trị, chọn nguồn và ghi rõ lý do chọn.
2. **Thiết kế mô hình dữ liệu** dạng tidy long (17 file có measure khác nhau nên dạng dài là phù hợp):
   - `fact_energy(entity, year, metric_key, value, value_class, source_file)`
   - `dim_entity(entity, iso_code, entity_type, is_aggregate, is_current_country_or_territory, is_asean, is_source_variant, canonical_entity, continent, income_group)`
   - `dim_metric(...)` — định nghĩa 16 metric canonical, đơn vị, nguồn, cutoff và ngưỡng `Trace`
   - `dim_year(year, is_main_asean_window)` — cờ `2000–2021`; cutoff riêng nằm ở `dim_metric`
   - `missingness_audit` và `cleaning_audit` — tách dữ liệu thiếu/quyết định làm sạch khỏi fact quan sát
   - `vw_wide` — view pivot 16 metric để tiện truy vấn SQL; Power BI dùng các CSV star schema dạng long
3. **Đổi tên cột** sang snake_case tiếng Anh (`Electricity from wind (TWh)` → `wind_twh`). Dấu ngoặc và khoảng trắng làm hỏng identifier SQL và tham chiếu DAX.
4. **Phân loại thực thể** — dựng cột `entity_type` với bộ quy tắc có thứ tự (quốc gia / châu lục / nhóm thu nhập / khối chính trị / World / lịch sử / bản trùng nguồn). Đây là phần lõi của công việc làm sạch.
5. **Xử lý các bẫy phân loại** — mã giả `OWID_*` (có cả quốc gia thật lẫn thực thể tổng hợp), các vùng xuất hiện nhiều bản từ nhiều nguồn, thực thể đã giải thể.
6. **Xử lý dữ liệu thiếu** — vì các cột chính không có ô rỗng, phải định nghĩa lại "thiếu" cho đúng:
   - dựng **spine** `current country/territory × metric × năm áp dụng` rồi đối chiếu fact → các khóa không có quan sát chính là dữ liệu thiếu
   - lập bảng quyết định xử lý theo từng vùng thiếu (trước dòng đầu / ở giữa / sau dòng cuối / thực thể giải thể), mỗi vùng một cách xử lý kèm lý do
   - xử lý **vực coverage** (số quốc gia trong panel nhảy vọt tại một năm do nguồn dữ liệu thay đổi) → mọi chỉ số dạng "% số nước" phải dùng mẫu số cố định
7. **Xử lý giá trị 0** — phân loại `value_class ∈ {Zero, Trace, Material}`; không xoá, không impute (0 ở đây là "thật sự không có", là kết quả chứ không phải lỗi).
8. **Cắt cửa sổ phân tích** theo quyết định ở Phase 1, nhưng **giữ năm bị cắt ở tầng raw** để làm bằng chứng minh hoạ trong báo cáo.
9. Ghi ra `output/clean/*.csv` và nạp vào `sql/renewables.db`.
10. **Viết và chạy bộ kiểm định** `sql/02_validate.sql` — tối thiểu 8 kiểm tra:

    | # | Kiểm tra |
    |---|---|
    | V1 | Đối chiếu Σ(country/territory) với World từng năm |
    | V2 | Đối chiếu Σ(6 châu lục chuẩn) với World |
    | V3 | Đối chiếu Σ(4 nhóm thu nhập) với World |
    | V4 | So sáu cặp vùng chuẩn–Ember, không tự động gộp |
    | V5 | `renewables_pct ≥ hydro_pct + wind_pct + solar_pct − epsilon` |
    | V6 | Trùng khoá `(entity, year, metric_key)` = 0 |
    | V7 | Giá trị âm = 0 |
    | V8 | Các cột `%` nằm trong [0, 100] |

    V1–V5 là **reconciliation audit** với `PASS/WARN/SKIP`: khác biệt có thật giữa các aggregate nguồn được giữ và giải thích. V6–V8 cùng kiểm tra cấu trúc là **hard gate** bắt buộc `PASS`.
11. Viết mục 1.2 của `docs/BaoCao.md`: **quy tắc làm sạch + kết quả kiểm định**. Trình bày kiểm định như một phát hiện, không phải phụ lục — nó biến "tôi đã làm sạch dữ liệu" thành "tôi *chứng minh* được việc làm sạch là đúng".

**Công cụ:** Python (biến đổi) + SQL (kiểm định)

**Đầu ra:** `python/02_clean_build.py`, `sql/01_schema.sql`, `sql/02_validate.sql`, 7 CSV trong `output/clean/`, `output/stats/02_validation_results.csv`, `sql/renewables.db`, mục 1.2 của báo cáo và nhật ký Phase 2.

**Kết quả thực tế:** 23 mapping nguồn = 13 file canonical + 1 audit + 3 excluded · 16 metric · 256 Entity = 215 current country/territory + USSR + World + 39 aggregate thiếu Code · 89.075 fact rows = 36.153 zero + 52.922 positive · 85.876 dòng missingness · panel ASEAN chính đủ 1.760/1.760 giá trị · `vw_wide` 8.968 dòng.

**Tiêu chí hoàn thành — đã đạt:** 31/31 kiểm tra cấu trúc và V6–V8 đều `PASS`; V1–V5 khớp đúng baseline nguồn với 0 cảnh báo blocking; 0 duplicate, 0 giá trị âm, 0 tỷ lệ ngoài miền sau làm sạch; không mất Kosovo do bẫy `OWID_*`; fact không có năm vượt cutoff; rerun tạo CSV byte-identical và không sửa 17 CSV nguồn.

---

# ✅ PHASE 3 — Phân tích mô tả *(yêu cầu 1.3 — ĐÃ HOÀN THÀNH)*

**Mục tiêu:** tóm tắt đặc trưng dữ liệu bằng thống kê mô tả, và **giải thích được thống kê nào có ý nghĩa / thống kê nào bị bóp méo** với phân phối này.

**Các bước:**
1. **Xác định các lát cắt cần thống kê** — vì ASEAN chỉ có n=10, phải làm 2 tầng: toàn cầu (n≈200+, để có bối cảnh và để phân vị có ý nghĩa) và ASEAN (n=10, mô tả trực tiếp).
2. **Tính bộ thống kê đầy đủ** cho từng lát cắt × từng công nghệ: `n, sum, mean, median, sd, CV, min, max, P10, P25, P50, P75, P90, P95, P99, IQR, skewness, kurtosis`.
3. **Tính bộ thống kê 3 phiên bản**: toàn bộ / chỉ nước có giá trị > 0 / chỉ nước ở mức đáng kể. So sánh 3 phiên bản để thấy ảnh hưởng của các giá trị 0.
4. **Diễn giải chất lượng phân phối** — dùng skewness, CV, khoảng cách mean↔median để lập luận thống kê nào đáng tin. Đây là chỗ giải thích *vì sao đề bài yêu cầu phân vị*.
5. **Tính các chỉ số dẫn xuất** (đặt trong `fact_metrics`):
   - tăng trưởng YoY, CAGR theo giai đoạn
   - tỷ trọng trong tổng thế giới / khu vực
   - xếp hạng toàn cầu và xếp hạng ASEAN theo năm
   - năm đầu tiên có sản lượng > 0 → độ trễ gia nhập
   - tách "NLTT hiện đại" (gió + mặt trời) khỏi thủy điện — chỉ số then chốt để trả lời câu hỏi trung tâm
   - chỉ số tập trung (top-N share, HHI) và bất bình đẳng (Gini)

   ⚠️ **YoY và CAGR chỉ định nghĩa khi mẫu số > 0.** Với dữ liệu này phần lớn dòng bằng 0 → đây là nguồn lỗi `Inf`/`NaN` số 1. Xếp hạng theo CAGR phải đặt ngưỡng sàn cho giá trị gốc, nếu không nước xuất phát từ gần 0 sẽ có CAGR vô nghĩa lớn.
6. **Lập các bảng thống kê** xuất ra Excel: cắt ngang toàn cầu · cắt ngang ASEAN · chuỗi thời gian Việt Nam · so sánh xếp hạng theo 2 cách đo (tổng NLTT vs NLTT hiện đại) · độ trễ gia nhập · bối cảnh toàn cầu theo mốc năm.
7. Ghi phát hiện vào `docs/NhatKyPhanTich.md`.

**Công cụ:** Python (thống kê) + SQL (chỉ số dẫn xuất bằng window functions — xem Phase 8)

**Đầu ra:** `python/03_descriptive.py`, `sql/03_analysis.sql`, sáu workbook, bốn CSV `03_*`, bảng `fact_metrics` và hai script kiểm thử phát hành/hoàn tác.

**Tiêu chí hoàn thành — đã đạt:** sáu workbook đúng tên, thứ tự sheet, khóa riêng và truy vết `fact_key`; các ô đơn vị `ratio` hiển thị `0.0000%`, còn `pct` giữ thang 0–100. `entry_summary` có hai cột trạng thái tường minh và duy nhất theo `series_key + status_type + status_value`; `fact_metrics` có **18.926 dòng** gồm đủ Q1–Q6, với phân bố Q1=5.544, Q2=3.608, Q3=1.980, Q4=1.382, Q5=5.950 và Q6=462. Các mốc này cùng **18.926/18.926** đối chiếu Python–SQL và chính xác tập **92/92** mã kiểm định được khóa trực tiếp, không chỉ so hai lần chạy với nhau; mọi kiểm định đều `PASS`. CV đủ quan sát nhưng mean bằng 0 dùng `NOT_DEFINED / ZERO_MEAN`. Kiểm định Phase 2 có đúng 864 dòng, 34/34 dòng chặn `PASS` và được gắn dấu vân tay đầu vào hiện tại. Hai lần chạy đầy đủ Phase 2 → validation → Phase 3 cho cùng nội dung SQLite/CSV/XLSX khi đọc lại; 17 CSV nguồn giữ nguyên hàm băm. Kiểm thử hoàn tác bao phủ tệp thường, SQLite fallback, lỗi backup, lỗi xóa staging, phục hồi sau khi database đã công bố và báo đúng khi phục hồi không đầy đủ. Dấu vân tay đầu vào là `64e1cc7d7bcb…`.

---

# ✅ PHASE 4 — Trực quan hoá *(yêu cầu 1.4 — ĐÃ HOÀN THÀNH)*

**Mục tiêu:** biến các phát hiện của Phase 3 thành hình ảnh, và phát hiện thêm mẫu/xu hướng mà bảng số không cho thấy.

**Các bước:**
1. **Gọi skill `dataviz` trước khi viết dòng code biểu đồ đầu tiên** — để chốt bảng màu, quy tắc mã hoá, cách xử lý trục và nhãn thống nhất cho cả bộ biểu đồ và dashboard.
2. **Chốt quy ước chung**, áp cho mọi biểu đồ:
   - loại thực thể tổng hợp khỏi mọi biểu đồ cấp quốc gia
   - ghi chú rõ cửa sổ năm và năm đã bị cắt
   - **không dùng trục kép** — thay bằng 2 panel chia chung trục x, hoặc chỉ số hoá về gốc chung
   - màu gắn theo **thực thể** (không theo thứ hạng); Việt Nam luôn dùng màu nhấn
   - tối đa ~8 series, phần còn lại gộp "Khác"
   - nhãn trực tiếp chỉ đặt ở điểm cuối / điểm cực trị
3. **Vẽ nhóm biểu đồ bối cảnh** — xu hướng toàn cầu theo thời gian; ASEAN so với thế giới.
4. **Vẽ nhóm biểu đồ so sánh trong ASEAN** — cơ cấu NLTT từng nước phân rã theo công nghệ; so sánh xếp hạng theo 2 cách đo; heatmap phân hoá công nghệ; small multiples 10 nước.
5. **Vẽ nhóm biểu đồ Việt Nam** — chuỗi thời gian 4 công nghệ; sản lượng và % điện năng trên 2 panel; vị thế Việt Nam trong bảng xếp hạng toàn cầu; Việt Nam so với phần còn lại của ASEAN.
6. **Vẽ nhóm biểu đồ phân phối & chẩn đoán** — phân phối lệch (thang log, xử lý riêng các giá trị 0), độ trễ gia nhập, mức tập trung theo thời gian.
7. **Vẽ biểu đồ phụ về hiệu quả** (hệ số công suất = TWh / (GW × 8,76)) — chỉ với các nước có cả hai dữ liệu; **phải ghi rõ nước nào thiếu**, tuyệt đối không để người đọc hiểu là đã phủ hết.
8. **Rà soát từng PNG** theo checklist ở phần Kiểm chứng.
9. Ghi phát hiện mới (nếu có) vào `docs/NhatKyPhanTich.md`.

**Công cụ:** Python (matplotlib/seaborn)

**Đầu ra:** `python/04_charts.py`, ~12–13 PNG trong `output/charts/`

**Tiêu chí hoàn thành — đã đạt ngày 2026-09-08:** 13/13 biểu đồ nói đúng một thông điệp, không lẫn thực thể tổng hợp vào biểu đồ quốc gia, không có năm 2022, trục kép, biểu đồ tròn hoặc giá trị 0 trên trục logarit. Bản phát hành có 16 sheet trong `04_chart_data.xlsx`, đúng 38/38 kiểm định `PASS`, `method_version=phase4_v1` và dấu vân tay `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10`. Ba lệnh kiểm thử cuối trả mã thoát 0; hai lần dựng cho cùng nội dung workbook/CSV và cùng mã băm điểm ảnh. Nguyễn Hồng Minh đã ký nghiệm thu trực quan ngày 2026-09-08.

**13 PNG đã nghiệm thu:** `04_01_global_asean_context.png`, `04_02_asean_technology_trend.png`, `04_03_asean_country_mix_2021.png`, `04_04_asean_rank_shift_2021.png`, `04_05_asean_small_multiples_shared.png`, `04_06_asean_small_multiples_free.png`, `04_07_vietnam_technology_trend.png`, `04_08_vietnam_twh_vs_share.png`, `04_09_vietnam_regional_global_position.png`, `04_10_global_distribution_2021.png`, `04_11_asean_entry_lag.png`, `04_12_asean_concentration_growth.png`, `04_13_capacity_factor_proxy.png`.

---

# ✅ PHASE 5 — Dashboard *(yêu cầu 1.5c — ĐÃ ĐÓNG, phạm vi thu hẹp)*

**Mục tiêu:** dashboard 3 trang cho phép người xem tự khám phá, không chỉ xem hình tĩnh.

**Các bước:**
1. Nạp `output/clean/*.csv` vào Power BI; dựng quan hệ star schema (`fact_energy` ↔ `dim_entity` / `dim_year`).
2. **Viết các measure DAX** với định nghĩa tường minh — đặc biệt là các tỷ lệ. KPI định nghĩa mơ hồ là chỗ dashboard mất tín nhiệm.
3. **Dựng hàng filter dùng chung, đặt trên cùng** (năm, quốc gia, công nghệ, chỉ số, công tắc "chỉ NLTT hiện đại") — không nhét filter vào từng biểu đồ.
4. **Trang 1 — Tổng quan Đông Nam Á**: hàng KPI khu vực + biểu đồ cơ cấu NLTT phân rã theo công nghệ + so sánh xếp hạng 2 cách đo + bối cảnh toàn cầu.
5. **Trang 2 — Việt Nam chuyên sâu**: hàng KPI Việt Nam + chuỗi thời gian 4 công nghệ + sản lượng vs % điện năng + vị thế toàn cầu + bảng chi tiết theo năm.
6. **Trang 3 — So sánh & chẩn đoán**: small multiples + chỉ số hoá + độ trễ gia nhập + mức tập trung + hệ số công suất.
7. **Chân trang cố định mọi trang**: nguồn dữ liệu, cửa sổ năm, năm đã loại và lý do, ghi chú đã loại thực thể tổng hợp.
8. Kiểm tra tính nhất quán khi đổi filter (xem Kiểm chứng).

**Công cụ:** Power BI Desktop

**Đầu ra:** `powerbi/ASEAN_Renewables.pbix`

**Tiêu chí hoàn thành — đạt một phần, ký ngày 2026-09-10 với phạm vi thu hẹp:**

*Đã chứng minh:* mô hình 8 bảng / 3 quan hệ / **73 phép đo** sinh từ một nguồn duy nhất; ba trang với **47 ô** trực quan; **175/175** mã nghiệm thu DAX `PASS`, 0 dòng chặn; **C1–C10** đọc thẳng tệp trên đĩa đều `PASS`, dựng hai lần cho nội dung giống hệt; mọi KPI có định nghĩa DAX viết ra được trong `powerbi/DAX_Measures.md`; công tắc "chỉ NLTT hiện đại" đổi đúng thứ hạng (Singapore +4, Indonesia −4, Lào −5).

*Chấp nhận không đo:* 14 mục việc tay trong Desktop và 32 ca kiểm tương tác — nên tiêu chí "đổi filter năm → cả 3 trang cập nhật nhất quán" **chưa được kiểm**, và bộ lọc thực tế chưa đồng bộ giữa ba trang. `.pbix` còn mang model cũ 71 phép đo; sản phẩm hợp lệ là PBIP + `DAX_Measures.md`.

Ranh giới đầy đủ ở `docs/Phase5_Review.md` §5.1–§5.3.

---

# ✅ PHASE 6 — Diễn giải & slide *(yêu cầu 1.5a, 1.5b — ĐÃ HOÀN THÀNH)*

**Mục tiêu:** chuyển từ "đã phân tích" sang "kể được một mạch lập luận".

**Các bước:**
1. Đọc lại `docs/NhatKyPhanTich.md`, chọn ra 4–5 phát hiện mạnh nhất.
2. **Kiểm chứng lại từng phát hiện bằng số** trước khi đưa vào báo cáo — không dùng lại con số từ bản nháp.
3. Viết mục 1.5a `docs/BaoCao.md`: mỗi phát hiện = một tiêu đề + con số + biểu đồ minh hoạ + diễn giải.
4. **Dựng slide (1.5b)** — hoãn theo yêu cầu, nhưng phải làm trước khi nộp. Mạch ~11 slide: móc mở đầu → câu hỏi & giới hạn dữ liệu → khuyết điểm dữ liệu phát hiện được → cách làm sạch và *chứng minh* làm sạch đúng → 4–5 phát hiện chính → kết luận & đề xuất → dữ liệu cần bổ sung.
   - Slide phải theo **mạch lập luận**, không phải mục lục kỹ thuật ("tôi đã dùng pandas", "tôi đã viết SQL").
   - Cặp slide "khuyết điểm dữ liệu" + "cách làm sạch & kiểm định" là chỗ tạo khác biệt lớn nhất so với bài trung bình.

**Công cụ:** Markdown + PowerPoint

**Đầu ra:** mục 1.5a của `docs/BaoCao.md`, file slide

**Tiêu chí hoàn thành:** mỗi slide có **một** thông điệp phát biểu được thành một câu; mỗi con số trên slide truy được về một bảng trong `output/stats/`.

---

# ✅ PHASE 7 — Kết luận & đề xuất *(yêu cầu 1.6 — ĐÃ HOÀN THÀNH)*

**Mục tiêu:** kết luận có căn cứ và đề xuất **không vượt quá phạm vi dữ liệu**.

**Các bước:**
1. Viết 4–5 kết luận, **mỗi kết luận truy được về một con số cụ thể** đã kiểm chứng.
2. Viết đề xuất theo công thức *"dữ liệu cho thấy X, nên cần xem xét / ưu tiên Y"* — **không** phát biểu như phương án đã tính chi phí.
3. Phân tách đối tượng đề xuất: cho Việt Nam / cho khu vực.
4. **Viết mục "những gì không thể đề xuất"** kèm lý do (thiếu dữ liệu giá thành, công suất đầy đủ, dân số, phát thải, biến chính sách). Mục này là **điểm mạnh**, không phải điểm yếu — nó cho thấy hiểu giới hạn của dữ liệu.
5. **Nêu yêu cầu dữ liệu cho bước tiếp theo** — chính xác cần ghép thêm bảng nào để trả lời được câu hỏi hiện chưa trả lời được.

**Công cụ:** Markdown

**Đầu ra:** mục 1.6 của `docs/BaoCao.md`

**Tiêu chí hoàn thành — đã đạt:** năm kết luận, mỗi kết luận neo vào một `claim_id` đã qua kiểm chứng ba chiều; đề xuất tách riêng cho Việt Nam và cho khu vực, viết dạng "nên xem xét" chứ không phải "nên làm"; có mục "không thể đề xuất" và mục "dữ liệu cần bổ sung". **77/77** claim khớp cả ba nguồn.

**Phase 7 gánh thêm việc hoàn tất bộ hồ sơ nộp**, sau khi yêu cầu định dạng được biết:

| Tệp nộp | Sản phẩm | Trạng thái |
|---|---|---|
| 1. Báo cáo dạng slide | `output/slides/ASEAN_Renewables.pptx` — 17 slide (15 nội dung + mở đầu + kết thúc), 16:9 | ĐẠT |
| 2. File xử lý dữ liệu | `output/notebook/ASEAN_Renewables_DataProcessing.ipynb` — 42 ô tự chứa, 31 ô có kết quả, 5 biểu đồ | ĐẠT |
| 3. Dashboard | `powerbi/ASEAN_Renewables.pbix` | **CẦN SỬA** — còn là bản cũ 71 phép đo |

Notebook chỉ đọc `archive/`, không `import` script nào của dự án, không đọc `output/`. Bảng `fact_energy` nó tự dựng khớp **từng dòng** với dữ liệu đã công bố: 89.075 dòng, lệch lớn nhất `1,1e-13`, `value_class` khớp tuyệt đối.

Chi tiết ở `docs/Phase7_Review.md`.

---

# PHASE 8 — SQL đóng vai gì (chạy song song Phase 2–3)

**Mục tiêu:** SQL phải làm việc thật, không chỉ có mặt cho đủ 3 công cụ.

Giao cho SQL đúng phần nó mạnh nhất — **window functions**:

| Nhiệm vụ | Cấu trúc |
|---|---|
| Xếp hạng theo năm | `RANK() OVER (PARTITION BY year, technology ORDER BY value DESC)` |
| Tăng trưởng YoY | `LAG(value) OVER (PARTITION BY entity, technology ORDER BY year)` |
| Năm đầu tiên có sản lượng > 0 | `MIN(CASE WHEN value > 0 THEN year END) OVER (PARTITION BY entity, technology)` |
| Tích luỹ & trung bình trượt | `SUM(...) OVER (... ROWS UNBOUNDED PRECEDING)`, `AVG(...) OVER (... ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)` |
| Thay đổi thứ hạng giữa 2 mốc | self-join / pivot |
| Mức tập trung theo năm | top-N share, HHI |
| Toàn bộ 8 kiểm định V1–V8 | CTE đối chiếu |

✅ Đã xác minh ở Phase 0: `ROW_NUMBER()`, `LAG()`, CTE đều chạy được trên SQLite 3.49.1.
⚠️ **Không dùng `PERCENTILE_CONT`** — SQLite không có. Phân vị để pandas làm (Phase 3), hoặc dùng `PERCENT_RANK()` / `CUME_DIST()` nếu bắt buộc phải ở trong SQL.

**Hai cách chạy file `.sql`** (cả hai đã test xong ở Phase 0):
```powershell
sqlite3 sql\renewables.db ".read sql/02_validate.sql"   # CLI
python python\run_sql.py sql\02_validate.sql            # dự phòng, in kết quả dạng bảng
```

**Đầu ra:** `sql/02_validate.sql`, `sql/03_analysis.sql` (~12 truy vấn), kết quả lưu ra `output/stats/`

---

## Bảng tổng hợp: Phase × Công cụ × Yêu cầu note.txt

| Phase | Nội dung | Công cụ chính | Yêu cầu |
|---|---|---|---|
| 0 | Chuẩn bị môi trường | winget / pip | — |
| 1 | Khảo sát & xác định vấn đề | Python | **1.1** |
| 2 | Tiền xử lý & mô hình dữ liệu | Python + SQL | **1.2** |
| 3 | Phân tích mô tả | Python + SQL | **1.3** |
| 4 | Trực quan hoá | Python | **1.4** |
| 5 | Dashboard | Power BI | **1.5c** |
| 6 | Diễn giải & slide | Markdown + PPT | **1.5a, 1.5b** |
| 7 | Kết luận & đề xuất | Markdown | **1.6** |
| 8 | Truy vấn phân tích *(song song 2–3)* | SQL | hỗ trợ 1.2, 1.3 |

---

## Rủi ro cần chặn ngay từ Phase 1–2

| Rủi ro | Hậu quả | Chặn ở đâu |
|---|---|---|
| `INNER JOIN` toàn bộ các tầng độ phủ | Mất ~93% thực thể mà không hề báo lỗi | Phase 1 bước 2, Phase 2 bước 6 (spine + `LEFT JOIN`) |
| Dùng cả các file trùng lặp nhau | Đếm trùng, số liệu sai gấp nhiều lần | Phase 1 bước 3 |
| Lọc thực thể tổng hợp bằng điều kiện quá rộng | Xoá mất quốc gia thật có mã giả | Phase 2 bước 5 |
| Giữ cả nhiều bản của cùng một vùng từ các nguồn khác nhau | Tổng bị nhân lên nhiều lần | Phase 2 bước 4–5 |
| Không cắt năm bị truncate | Mọi chuỗi thời gian có một cú sụt giả | Phase 1 bước 7, Phase 2 bước 8 |
| Nội suy dữ liệu thiếu | Bịa ra lịch sử không tồn tại | Phase 1 bước 6 |
| Chia cho số dòng từng năm khi tính "% số nước" | Tạo ra cú sụt giả tại năm nguồn dữ liệu thay đổi | Phase 2 bước 6 |
| Xoá / impute các giá trị 0 | Mất chính phát hiện cần tìm | Phase 2 bước 7 |
| Xếp hạng CAGR không đặt ngưỡng sàn | Nước xuất phát gần 0 chiếm hết top | Phase 3 bước 5 |
| Trục kép trong biểu đồ | Có thể tạo ra bất kỳ tương quan nào tuỳ cách chọn thang | Phase 4 bước 2 |
| **Type affinity lỏng của SQLite** | Nạp text vào cột số vẫn nhận → số liệu sai mà **không có lỗi nào báo** | Phase 2 bước 2 (khai báo kiểu tường minh) + kiểm dtype trong pandas trước khi nạp |
| **Navicat giữ file `.db`** | `database is locked` khi chạy lại script nạp | Đóng connection trong Navicat trước khi chạy |

---

## Kiểm chứng

**Phase 0 — môi trường** *(đã đạt 26/26)*
```powershell
python python\00_check_env.py
```

**Sau Phase 1 — khảo sát dữ liệu**
```powershell
python python\01_profile.py
```
Đạt khi: chỉ cần một lệnh để tạo `00_phase1_summary.txt` cùng đúng 5 CSV chi tiết · TXT có đủ 7 phần và kết luận cửa sổ ASEAN-10 là `2000–2021` · chạy lại cho kết quả **byte-identical** và không sửa 17 CSV nguồn.

**Mốc hồi quy — cấu trúc:** 17 file · 23 chỉ số · 7 tầng · 10 cặp overlap · 256 `Entity` · 39 thực thể thiếu `Code` · 4 cặp fuzzy · 170 dòng ASEAN · 2.702 chuỗi Entity–file · 780 dòng file–năm.

**Mốc hồi quy — phát hiện:**

| Mốc | Giá trị |
|---|---|
| Cặp `03–05`, `03–08`, `03–12` | `redundant_subset` |
| File năm 2022 `TRUNCATED_SEVERE` | 8 |
| Xung đột giá trị | 12.168 = 9.310 `IMMATERIAL` + 2.858 `MATERIAL` |
| `MATERIAL` theo loại thực thể | 2.011 quốc gia + 847 tổng hợp |
| Chuỗi `FULL_SPAN` | 682 (thô) → 1.215 (hiệu dụng), 535 chuỗi đổi nhãn |
| Chuỗi có lỗ hổng giữa | 35 = 31 `SAMPLING_GRID_NOT_MISSING` + 4 `DO_NOT_INTERPOLATE_REVIEW_SOURCE` |
| Việt Nam, cặp `02`–`03` | 0 dòng `MATERIAL`, chênh lớn nhất 0,005 TWh |

**Sau Phase 2 — tính đúng đắn dữ liệu**
```powershell
python python\01_profile.py
python python\02_clean_build.py
python python\run_sql.py sql\02_validate.sql --fail-on-blocking --output-csv output\stats\02_validation_results.csv
```
Đạt khi: 31 structural checks cùng V6–V8 `PASS` · V1–V5 khớp baseline `PASS/WARN/SKIP` và có **0 blocking non-PASS** · `dim_entity` có đúng 215 current country/territory, không mất Kosovo do bẫy mã giả · `fact_energy` có 89.075 dòng và không còn năm vượt cutoff · các file trùng đã bị loại khỏi canonical · rerun tạo CSV byte-identical.

**Sau Phase 3 — thống kê**
```powershell
python python\03_test_publish.py
python python\03_verify_release.py
```
Đạt khi: 18.926/18.926 dòng Q1–Q6 khớp Python–SQL cả khóa, giá trị, chữ, trạng thái, lý do, số đếm và mẫu số · 92/92 kiểm định Phase 3 có mã duy nhất `PASS` · kiểm định Phase 2 đủ và khớp dấu vân tay đầu vào · `entry_summary` tuân thủ khóa trạng thái công khai · tổng/tỷ trọng/xếp hạng/YoY/CAGR/đóng góp tuân thủ bất biến đã khóa · hai lần phát hành cho cùng nội dung dữ liệu · 17 CSV nguồn không đổi · lỗi công bố giả lập khôi phục đủ tệp thường và phiên bản SQLite cũ sau khi nhánh fallback đã chạy.

**Sau Phase 4 — biểu đồ**
Mở từng PNG, kiểm: không lẫn thực thể tổng hợp · không có cú sụt ở năm bị cắt · thang log không chứa giá trị 0 · biểu đồ small multiples có cả bản chung trục và bản tự do trục (ghi rõ bản nào là bản nào) · biểu đồ hệ số công suất ghi rõ nước bị thiếu dữ liệu.

**Sau Phase 5 — dashboard**
Đổi filter năm về một mốc quá khứ → cả 3 trang cập nhật nhất quán, không trang nào giữ số cũ · KPI tính từ dashboard khớp với bảng trong `output/stats/` · bật/tắt công tắc "chỉ NLTT hiện đại" làm thay đổi thứ tự xếp hạng.

**Sau Phase 7 — báo cáo**
Mỗi con số trong kết luận truy được về một bảng trong `output/stats/` hoặc một truy vấn trong `sql/03_analysis.sql` · có mục giới hạn dữ liệu tường minh · không đề xuất nào cần dữ liệu mà bộ này không có.
