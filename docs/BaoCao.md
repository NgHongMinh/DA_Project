# Phân tích năng lượng tái tạo — Việt Nam và Đông Nam Á

Đồ án phân tích dữ liệu · Nguồn: bộ **Renewable Energy World Wide** (Our World in Data, tổng hợp từ Ember và BP) · Công cụ: Python · SQLite · Power BI

---

# 1.1. Xác định và định nghĩa vấn đề, mục tiêu phân tích

## Bối cảnh và nguồn dữ liệu

Bộ dữ liệu gồm **17 file CSV**, **23 cột chỉ số**, **256 thực thể** và khoảng năm **1965–2022**. Ba nhóm chỉ số:

| Nhóm | Đơn vị | File | Nội dung |
|---|---|---|---|
| Sản lượng điện | TWh | `02`, `03`, `05`, `08`, `12` | Điện sản xuất từ thuỷ điện, gió, mặt trời, nguồn tái tạo khác |
| Tỷ trọng | % | `01`, `04`, `06`, `07`, `10`, `11`, `14`, `15` | Trên tổng điện năng, hoặc trên năng lượng sơ cấp quy đổi |
| Công suất lắp đặt | GW | `09`, `13`, `17` | Gió, mặt trời, địa nhiệt |
| Sản lượng nhiên liệu sinh học | TWh | `16` | Biofuel |

Dữ liệu đến từ **hai nhà cung cấp** được OWID tổng hợp lại: Ember (chuyên về điện, phủ rộng) và BP Statistical Review (phủ hẹp hơn, chuỗi dài hơn). Sự tồn tại song song của hai nguồn là nguyên nhân của phần lớn các vấn đề dữ liệu được mô tả ở mục 1.2.

### Vì sao chọn hướng Việt Nam và Đông Nam Á

Ba lý do, tất cả đều xuất phát từ đặc điểm dữ liệu chứ không từ sở thích chủ đề:

1. **Khu vực đủ nhỏ để phân tích sâu, đủ lớn để có bối cảnh so sánh.** Mười nước ASEAN cho phép so từng nước một mà vẫn giữ được một mẫu số khu vực có nghĩa.
2. **Dữ liệu đủ cho cả 10 nước ở nhóm chỉ số quan trọng nhất.** Khảo sát Phase 1 cho thấy tám file phủ đủ ASEAN-10, trong đó có toàn bộ nhóm sản lượng điện theo công nghệ và tỷ trọng điện.
3. **Việt Nam là trường hợp có biến động rõ trong cửa sổ phân tích**, nên đặt được câu hỏi so sánh có ý nghĩa thay vì chỉ mô tả một chuỗi phẳng.

## Câu hỏi trung tâm

> **Đông Nam Á đã chuyển dịch sang năng lượng tái tạo đến đâu trong giai đoạn 2000–2021, và Việt Nam đứng ở vị trí nào trong quá trình đó?**

Câu hỏi này chọn được vì dữ liệu trả lời được nó một cách trọn vẹn: panel **10 nước × 22 năm = 220 quan sát**, bốn công nghệ, **không ô trống nào** trong file `03`.

Một chữ trong câu hỏi cần định nghĩa trước, vì nó quyết định toàn bộ phần còn lại: **"chuyển dịch"**. Bộ dữ liệu cho phép đo theo hai nghĩa khác nhau, và hai nghĩa này có thể cho kết quả trái ngược:

- **Nghĩa rộng — tổng năng lượng tái tạo:** gồm cả thuỷ điện. Một nước có nhiều sông lớn sẽ có chỉ số cao mà không cần đầu tư mới gì.
- **Nghĩa hẹp — năng lượng tái tạo hiện đại:** chỉ gió và mặt trời. Đây là phần phản ánh quyết định đầu tư trong hai thập kỷ gần đây.

Báo cáo này **đo cả hai và so sánh chúng với nhau**. Sự khác biệt giữa hai cách đo chính là một phần của câu trả lời, không phải một chi tiết kỹ thuật.

## Sáu câu hỏi con

Mỗi câu gắn với chỉ số cụ thể sẽ tính, file nguồn và cửa sổ năm đã được Phase 1 xác nhận là khả thi.

### Q1. Quy mô và tốc độ: khu vực đã đi được bao xa?

| | |
|---|---|
| **Chỉ số** | Tổng TWh tái tạo theo năm; CAGR từng giai đoạn; tỷ trọng ASEAN trong tổng thế giới |
| **Nguồn** | `03 modern-renewable-prod.csv` |
| **Cửa sổ** | 2000–2021, đủ 10 nước |
| **Trả lời ở** | Phase 3 (bảng cắt ngang), Phase 4 (biểu đồ bối cảnh) |

⚠️ CAGR chỉ tính được khi giá trị gốc dương. Với dữ liệu này phần lớn dòng gió và mặt trời ở đầu giai đoạn bằng 0, nên phải đặt ngưỡng sàn cho giá trị gốc; nếu không, nước xuất phát từ gần 0 sẽ chiếm hết nhóm dẫn đầu với con số vô nghĩa.

### Q2. Cơ cấu: sự tăng trưởng đến từ công nghệ nào?

| | |
|---|---|
| **Chỉ số** | Phân rã TWh theo 4 công nghệ; tỷ trọng từng công nghệ trong tổng tái tạo của mỗi nước |
| **Nguồn** | `03` |
| **Cửa sổ** | 2000–2021, đủ 10 nước |
| **Trả lời ở** | Phase 3, Phase 4 (biểu đồ cơ cấu), Phase 5 (trang 1) |

Đây là câu tách "thuỷ điện sẵn có" khỏi "đầu tư mới", tức là làm rõ định nghĩa "chuyển dịch" đã nêu ở trên.

### Q3. Xếp hạng: thứ tự các nước thay đổi thế nào khi đổi cách đo?

| | |
|---|---|
| **Chỉ số** | Xếp hạng ASEAN theo tổng tái tạo **so với** xếp hạng theo tái tạo hiện đại (gió + mặt trời); độ chênh thứ hạng |
| **Nguồn** | `03` |
| **Cửa sổ** | 2000–2021 |
| **Trả lời ở** | Phase 3, Phase 4, Phase 5 (công tắc "chỉ NLTT hiện đại") |

Câu hỏi này kiểm tra trực tiếp giả thuyết rằng hai cách đo cho kết quả khác nhau. Nếu thứ hạng không đổi thì đó cũng là một phát hiện.

### Q4. Việt Nam: quỹ đạo riêng khác gì phần còn lại của khu vực?

| | |
|---|---|
| **Chỉ số** | Chuỗi thời gian 4 công nghệ; tăng trưởng YoY; năm đầu tiên có sản lượng > 0 theo từng công nghệ (độ trễ gia nhập); tỷ trọng trong tổng ASEAN; thứ hạng toàn cầu theo năm |
| **Nguồn** | `03` (sản lượng), `04`/`07`/`11`/`15` (tỷ trọng điện) |
| **Cửa sổ** | 2000–2021 |
| **Trả lời ở** | Phase 3, Phase 4 (nhóm biểu đồ Việt Nam), Phase 5 (trang 2) |

Phase 1 đã xác nhận Việt Nam có đủ 22 năm dữ liệu liên tục và hai nguồn `02`/`03` chênh nhau tối đa `0,005 TWh` cho Việt Nam, nên kết quả không phụ thuộc vào việc chọn nguồn nào.

### Q5. Sản lượng hay tỷ trọng: hai thước đo có kể cùng một câu chuyện không?

| | |
|---|---|
| **Chỉ số** | TWh tuyệt đối **đối chiếu với** % trong tổng điện năng, cùng nước cùng năm |
| **Nguồn** | `03` (TWh) và `04`, `07`, `11`, `15` (%) |
| **Cửa sổ** | 2000–2021, đủ 10 nước |
| **Trả lời ở** | Phase 3, Phase 4 (hai panel chung trục x) |

Một nước có thể tăng mạnh sản lượng tái tạo mà tỷ trọng vẫn giảm, nếu tổng nhu cầu điện tăng nhanh hơn. Câu hỏi này tách hai hiện tượng đó ra.

⚠️ Không dùng trục kép để so hai đại lượng này — chọn thang trục khác nhau có thể tạo ra gần như bất kỳ tương quan nào. Dùng hai panel chia chung trục thời gian.

### Q6. Mức tập trung: tăng trưởng khu vực do vài nước hay đến từ số đông?

| | |
|---|---|
| **Chỉ số** | Tỷ trọng top-3 trong tổng ASEAN theo năm; HHI; hệ số Gini |
| **Nguồn** | `03` |
| **Cửa sổ** | 2000–2021 |
| **Trả lời ở** | Phase 3, Phase 4 (biểu đồ mức tập trung), Phase 5 (trang 3) |

Phân biệt "cả khu vực chuyển dịch" với "một hai nước kéo con số chung lên".

---

## Những gì bộ dữ liệu này KHÔNG trả lời được

Phần này quan trọng ngang phần trên. Mỗi giới hạn dưới đây đóng lại một loại câu hỏi mà người đọc có thể mong đợi, và nêu rõ cần dữ liệu gì để mở lại.

### Nhóm 1 — Thiếu hoàn toàn khỏi bộ dữ liệu

| # | Không trả lời được | Vì thiếu | Cần bổ sung gì |
|---|---|---|---|
| 1 | **Chi phí và hiệu quả đầu tư.** Không thể nói công nghệ nào "đáng đầu tư hơn", hay một nước chi bao nhiêu cho mỗi TWh. | Không có LCOE, vốn đầu tư, giá điện, trợ giá | Bộ dữ liệu chi phí (IRENA Renewable Power Generation Costs, BNEF) |
| 2 | **Tác động môi trường.** Không thể quy đổi TWh tái tạo thành lượng CO₂ tránh được. | Không có phát thải, cường độ phát thải lưới điện | Dữ liệu phát thải theo ngành điện (Ember carbon intensity, IEA) |
| 3 | **Mức tiêu thụ theo đầu người.** Không so được nước lớn với nước nhỏ một cách công bằng. | Không có dân số, GDP | World Bank WDI, UN Population |
| 4 | **Vai trò của chính sách.** Không thể nói FIT, đấu thầu hay hạn ngạch đã tạo ra bao nhiêu tăng trưởng. | Không có biến chính sách, mốc thời gian ban hành | IEA/IRENA Policies and Measures Database |
| 5 | **Cấu trúc thị trường và sở hữu.** Không biết ai đầu tư, tư nhân hay nhà nước. | Không có dữ liệu doanh nghiệp, dự án | Cơ sở dữ liệu dự án cấp nhà máy |

### Nhóm 2 — Có dữ liệu nhưng không đủ độ phân giải

| # | Không trả lời được | Vì sao |
|---|---|---|
| 6 | **Gió trên bờ so với gió ngoài khơi.** | Cột `Electricity from wind (TWh)` là một số gộp, không tách hai loại. Đây là mất mát đáng kể vì hai loại có chi phí và điều kiện triển khai rất khác nhau. |
| 7 | **Phân rã nhóm "nguồn tái tạo khác".** | `Other renewables including bioenergy` gộp sinh khối, địa nhiệt, thuỷ triều vào một cột. Không tách được. |
| 8 | **Biến động trong năm.** | Dữ liệu chỉ có độ phân giải **năm**. Không nói được gì về tính mùa vụ, giờ cao điểm hay khả năng điều độ — chính là những vấn đề khó nhất của điện tái tạo. |
| 9 | **Vị trí địa lý trong một nước.** | Chỉ có tổng cấp quốc gia. Không phân tích được vùng miền hay đấu nối lưới. |

### Nhóm 3 — Giới hạn phát sinh từ khảo sát Phase 1

| # | Không trả lời được | Bằng chứng |
|---|---|---|
| 10 | **Hệ số công suất cho cả 10 nước.** Chỉ so sánh được với tập rất nhỏ. | File công suất `09` phủ 2/10 nước ASEAN, `13` phủ 4/10, `17` phủ 2/10. Mọi biểu đồ hệ số công suất phải ghi rõ nước nào thiếu. |
| 11 | **So sánh 10 nước bằng tỷ trọng trên năng lượng sơ cấp.** | Nhóm file `01`, `06`, `10`, `14` chỉ phủ 6 nước. Kết quả dùng nhóm này phải gọi đúng là **ASEAN-6**, không được trình bày như ASEAN-10. |
| 12 | **Bất cứ điều gì về năm 2022.** | Tám file có dòng năm 2022 nhưng chỉ với 29 thực thể (~12% đường nền) và **không nước ASEAN nào**. Năm này bị loại khỏi tầng phân tích. |
| 13 | **Xu hướng ASEAN trước năm 2000.** | Bốn nước Myanmar, Cambodia, Laos, Brunei không có dữ liệu trước 2000. Số quốc gia trong panel nhảy từ 106 lên 247 tại đúng năm 2000 do nguồn thay đổi, nên mọi chuỗi bắc qua mốc này đều có một cú nhảy giả. |
| 14 | **Con số tuyệt đối cho các thực thể tổng hợp cấp nhóm thu nhập.** | Hai nguồn trong bộ dữ liệu chênh nhau tới **159 TWh** cho `Lower-middle-income countries`. Chừng nào chưa xác minh được provenance, các con số này chưa dùng để kết luận. |
| 15 | **Trùng lặp giữa 12 file còn lại.** | Step 3 của Phase 1 chỉ đối chiếu 5 file có cùng đại lượng và đơn vị TWh. Mười hai file kia chưa được kiểm tra trùng lặp dưới bất kỳ hình thức nào. |

### Cách xử lý các giới hạn này trong báo cáo

Ba nguyên tắc áp dụng xuyên suốt:

1. **Mọi kết luận đều nêu rõ phạm vi** — ASEAN-10 hay ASEAN-6, cửa sổ năm nào, gồm hay không gồm thuỷ điện.
2. **Không suy diễn nguyên nhân từ dữ liệu tương quan.** Bộ dữ liệu này mô tả *cái gì đã xảy ra*, không giải thích *vì sao*. Câu hỏi "vì sao" cần các bộ dữ liệu ở Nhóm 1.
3. **Đề xuất ở mục 1.6 chỉ phát biểu dưới dạng "dữ liệu cho thấy X, nên cần xem xét Y"**, không phát biểu như phương án đã tính chi phí.

---

# 1.2. Tiền xử lý dữ liệu

Phase 2 chuyển 17 CSV nguồn thành mô hình **tidy-long** dùng chung cho Python,
SQLite và Power BI. Quy trình có thể chạy lại bằng
`python python\02_clean_build.py`; dữ liệu gốc trong `archive/` chỉ được đọc.

## Chọn nguồn và phạm vi thời gian

| Vai trò | File | Quyết định |
|---|---|---|
| Canonical | `01`, `03`, `04`, `06`, `07`, `09`, `10`, `11`, `13`, `14`, `15`, `16`, `17` | 13 nguồn tạo ra 16 metric chính thức |
| Audit-only | `02` | Giữ để đối chiếu sai khác nguồn, không trộn giá trị với `03` |
| Excluded | `05`, `08`, `12` | Loại khỏi fact vì trùng hoàn toàn các metric hydro, wind và solar của `03` |

Cutoff được áp dụng theo từng nguồn: `01` và `06` kết thúc ở 2020;
`03`, `04`, `07`, `11`, `15` kết thúc ở 2021 và loại năm 2022; `17` kết
thúc ở 2020; các nguồn canonical còn lại kết thúc ở 2021. Toàn bộ lịch sử
hợp lệ trước cutoff được giữ lại, còn cửa sổ phân tích chính ASEAN-10 được
đánh dấu riêng là **2000–2021**.

Không dùng fuzzy matching, nội suy, forward-fill hay backward-fill; không đổi
`NULL` thành 0 và không coalesce các bản vùng từ nguồn khác nhau. File `17`
được chuẩn hoá công suất địa nhiệt từ **MW sang GW** bằng hệ số `0,001`.

## Mô hình dữ liệu sạch

SQLite dùng bảng `STRICT`, khoá chính, khoá ngoại và `CHECK`; bảy bảng sạch
đồng thời được xuất thành CSV trong `output/clean/`:

| Đối tượng | Grain/khoá chính | Kết quả |
|---|---|---:|
| `source_metric_catalog` | `(source_file, source_column)` | 23 mapping nguồn |
| `dim_metric` | `metric_key` | 16 metric canonical |
| `dim_entity` | `entity` | 256 thực thể |
| `dim_year` | `year` | Gắn cờ cửa sổ ASEAN chính |
| `fact_energy` | `(entity, year, metric_key)` | 89.075 quan sát thật |
| `missingness_audit` | `(entity, year, metric_key)` | 85.876 ô thiếu trên spine quốc gia hiện tại |
| `cleaning_audit` | nguồn–cột–thực thể–năm–hành động | 427 thay đổi/loại trừ có truy vết |
| `validation_results` | kết quả kiểm định chi tiết | 864 kết quả sau khi chạy validation |
| `vw_wide` | `(entity, year)` | 8.968 dòng, 16 cột metric tiện dụng |

`fact_energy` có **36.153 giá trị 0** và **52.922 giá trị dương**; 0 vẫn là
quan sát hợp lệ, không phải dữ liệu thiếu. Trong 256 thực thể có **215 quốc
gia/vùng lãnh thổ hiện tại**, gồm đúng 10 nước ASEAN. `continent` và
`income_group` của từng quốc gia để `NULL` vì Phase 2 không bổ sung nguồn
phân loại bên ngoài.

## Dữ liệu thiếu và nhật ký làm sạch

Trong cửa sổ canonical có **574 ô `NULL` từ nguồn**. Spine
`215 quốc gia/vùng lãnh thổ × metric × khoảng năm áp dụng` phân loại các ô
không quan sát thành `NO_SERIES`, `BEFORE_FIRST`, `INTERNAL_GAP`,
`AFTER_LAST` hoặc `SAMPLING_GRID_NOT_MISSING`; không giá trị nào được điền
thay. Phase 1 nhận diện 31 chuỗi địa nhiệt theo nhịp lấy mẫu; do audit chỉ áp
dụng cho quốc gia hiện tại, **23 chuỗi với 184 ô** được gắn
`SAMPLING_GRID_NOT_MISSING`. Panel chính vẫn đủ **1.760/1.760** quan sát
(10 nước × 22 năm × 8 metric).

`cleaning_audit` có **427 dòng**: 424 quan sát bị loại vì nằm ngoài cutoff và
3 tỷ lệ phần trăm lệch biên không quá `0,0001` điểm phần trăm được snap về
0/100. Mọi dòng fact vẫn truy ngược được tới file, cột nguồn, đơn vị và hệ số
chuyển đổi qua `dim_metric` và `source_metric_catalog`.

## Kiểm định và reconciliation

| Kiểm định | Kết quả | Cách hiểu |
|---|---|---|
| Structural | **31 PASS** | Schema, số dòng, khoá, lineage, cutoff, dtype và panel đúng contract |
| V1 — 215 quốc gia so với World | **65 PASS / 23 WARN / 12 SKIP** | Chỉ cộng bốn metric generation TWh |
| V2 — sáu châu lục so với World | **86 PASS / 2 WARN / 12 SKIP** | `SKIP` cho metric không cộng được/coverage hẹp |
| V3 — bốn nhóm thu nhập so với World | **39 PASS / 49 WARN / 12 SKIP** | Sai khác tổng hợp được giữ nguyên để audit |
| V4 — vùng chuẩn so với Ember | **334 PASS / 194 WARN** | 248 exact, 86 immaterial, 194 material difference |
| V5 — bound thành phần | **5.336/5.336**, ASEAN **220/220** | Renewable share không thấp hơn hydro + wind + solar ngoài epsilon |
| V6–V8 — hard gate | **PASS cả 3** | Không trùng khoá, không âm, tỷ lệ nằm trong `[0,100]` |

Toàn bộ `validation_results` gồm **560 PASS, 268 WARN và 36 SKIP**; không có
dòng blocking nào khác `PASS`. Các `WARN` của V1–V4 là **sai khác giữa số
tổng hợp do nguồn công bố**, không phải lỗi ETL, nên được định lượng và giữ
nguyên thay vì sửa dữ liệu để ép đẳng thức.

Kết quả có **mức tin cậy cao** đối với số dòng, phép biến đổi, tính toàn vẹn
và hard gate vì được kiểm lại bằng Python lẫn SQLite. Mức tin cậy của việc
diễn giải nguyên nhân các sai khác V1–V4 là **trung bình**: phép đo là tái lập
được, nhưng provenance và boundary của từng nhà cung cấp vẫn cần tài liệu
nguồn nếu muốn kết luận nguyên nhân.

# 1.3. Phân tích mô tả

*(Phase 3 — chưa thực hiện)*

# 1.4. Trực quan hoá dữ liệu

*(Phase 4 — chưa thực hiện)*

# 1.5. Diễn giải và trình bày kết quả

## 1.5a. Phân tích kết quả và kết luận có ý nghĩa

*(Phase 6 — chưa thực hiện)*

## 1.5b. Slide trình bày

*(Phase 6 — chưa thực hiện)*

## 1.5c. Dashboard

*(Phase 5 — chưa thực hiện)*

# 1.6. Kết luận và đề xuất

*(Phase 7 — chưa thực hiện)*

---

## Phụ lục — truy vết số liệu

| Nguồn | Nội dung |
|---|---|
| `output/stats/00_phase1_summary.txt` | Báo cáo khảo sát dữ liệu, bảy phần |
| `output/stats/01_overlap_conflict_details.csv` | Chi tiết chênh lệch giữa các nguồn |
| `output/stats/03_asean_coverage_details.csv` | Độ phủ 10 nước ASEAN × 17 file |
| `output/stats/05_last_year_check.csv` | Kiểm tra năm cuối từng file |
| `output/clean/*.csv` | Bảy bảng sạch của mô hình star/tidy-long Phase 2 |
| `output/stats/02_validation_results.csv` | 864 kết quả structural và V1–V8 |
| `sql/renewables.db` | SQLite sạch gồm dimensions, fact, audit và `vw_wide` |
| `python/02_clean_build.py` | Quy tắc chọn nguồn, làm sạch và dựng mô hình |
| `sql/01_schema.sql`, `sql/02_validate.sql` | Schema `STRICT` và logic kiểm định Phase 2 |
| `docs/Phase1_KhaoSatDuLieu.md` | Giải thích phương pháp và giới hạn diễn giải |
| `docs/NhatKyPhanTich.md` | Nhật ký phát hiện, có mức tin cậy từng mục |
