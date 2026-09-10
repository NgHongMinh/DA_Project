# Phiếu nghiệm thu Phase 5 — Dashboard Power BI

Phiếu này bao phủ **hai lớp** mà `PHASE5.md` §B11 đòi: lớp định lượng (DAX và mẫu
số có đúng không) và lớp tương tác/trực quan (bố cục, bộ lọc, khả năng đọc).
Kiểm định số không thay thế việc mở dashboard ra bấm; ngược lại, bấm thấy đẹp
không chứng minh được mẫu số đúng.

**Trạng thái tổng thể hiện tại:** `CHỜ NGHIỆM THU`.

Trạng thái hợp lệ cho mỗi mục: `CHỜ NGHIỆM THU` · `CẦN SỬA` (ghi rõ lỗi và cách
tái hiện) · `ĐẠT`.

## 0. Ghi chú về Gate B0

`PHASE5.md` viết “Chỉ khi Gate B0 đạt mới được bắt đầu B1”. Chủ đồ án đã quyết
định **ký B0 song song** thay vì chặn, nên Phase 5 khởi động trước khi có chữ ký.
B0 đã được Nguyễn Hồng Minh ký hoàn tất ngày 2026-09-08 trước khi ký Phase 5.

Hiện trạng B0 tính đến 2026-09-08:

- [x] Câu sai “Thái Lan và Philippines đồng hạng 3” đã sửa ở `NhatKyPhanTich.md` và `BaoCao.md`.
- [x] C04 đã đối chiếu ba lớp với `03_fact_metrics.csv` — hình vẽ đúng, chỉ là lỗi văn bản.
- [x] Đã soi đủ 13 PNG ở kích thước gốc; phát hiện và sửa ba lỗi trình bày (L1 dấu thập phân kiểu Anh ở C01/C05/C06/C12, L2 chồng chữ ở C09, L3 thang màu C03 dùng tỷ lệ kiểu Anh thay vì phần trăm kiểu Việt), đã dựng lại Phase 4.
- [x] Ba lệnh kiểm thử Phase 4 trả mã thoát 0; `04_validation_results.csv` có 38 mã duy nhất, 0 dòng chặn khác `PASS`.
- [x] Nguyễn Hồng Minh đã ký nghiệm thu Phase 4 ngày 2026-09-08 trong mục 5 của `docs/Phase4_Review.md`.

## 1. Bảng nghiệm thu theo cổng

| Cổng | Nội dung | Ai làm | Bằng chứng | Trạng thái |
|---|---|---|---|---|
| B0 | Đóng chính thức Phase 4 | Người | `docs/Phase4_Review.md` | ĐẠT |
| B1 | Khóa hợp đồng và đường cơ sở | Máy | `python/phase5_contract.py` tự kiểm khi import | ĐẠT |
| B2 | Nạp dữ liệu, khai kiểu | Tay trong Desktop | 14 mã `P5_B2_*` | CHỜ NGHIỆM THU |
| B3 | Mô hình sao và bảng chọn | Sinh sẵn trong TMDL | `relationships.tmdl`, ba bảng `Sel*` | CHỜ NGHIỆM THU |
| B4 | DAX nền tảng | Sinh sẵn | 73 phép đo trong `DAX_Measures.md` | CHỜ NGHIỆM THU |
| B5 | DAX chẩn đoán | Sinh sẵn | các phép đo nhóm 05–07 và **10 Entry lag** | CHỜ NGHIỆM THU |
| B6 | Khung ba trang và hàng bộ lọc | Tay | `ASEAN_Renewables.Report/` | CHỜ NGHIỆM THU |
| B7 | Trang 1 — V01–V04 | Sinh sẵn + tay | 14 ô · 54 mã `P5_B7_*` | CHỜ NGHIỆM THU |
| B8 | Trang 2 — V05–V09 | Sinh sẵn + tay | 15 ô · 34 mã `P5_B8_*` | CHỜ NGHIỆM THU |
| B9 | Trang 3 — V10–V14 | Sinh sẵn + tay | 18 ô · **67/67 mã `P5_B9_*` PASS** | CHỜ NGHIỆM THU (còn lớp trực quan) |
| B10 | Kiểm thử tích hợp và bằng chứng phát hành | MCP + người | `05_validation_results.csv`, PDF, SHA-256 | CHỜ NGHIỆM THU |
| B11 | Nghiệm thu tổng thể | Người | phiếu này | CHỜ NGHIỆM THU |

## 2. Kiểm định máy chạy được

Ba lệnh dưới đây chạy **không cần** Power BI và là điều kiện cần của B1–B5:

```powershell
python python\05_expected.py
python python\05_build_pbip.py
python python\05_acceptance.py
```

- [x] `05_expected.py` tính lại **169 đích** từ `output/clean/` và đối chiếu **ba
  chiều**: recompute ↔ hằng số khóa trong `phase5_contract.py` ↔ `03_fact_metrics.csv`.
  Không đích nào lệch. → đo được: `targets=169 | gates={'B2': 14, 'B7': 54, 'B8': 34, 'B9': 67}`.
- [x] `05_build_pbip.py` sinh mô hình 8 bảng, 3 quan hệ, 61 phép đo và
  `DAX_Measures.md` từ **một** nguồn `05_measures.py`.
- [x] `05_acceptance.py` ánh xạ **169/169** đích sang truy vấn DAX; đích không có
  truy vấn thì script báo lỗi chứ không bỏ qua âm thầm.
- [x] `05_validate.py` đã được kiểm thử bằng bộ kết quả giả có gieo lỗi và bắt
  đúng cả bảy kiểu: `Fixed Decimal` cắt chữ số · mẫu số `ranked_n` viết cứng ·
  sai năm ngược hướng · trả `0` thay vì trống kèm lý do · **lệch thang ×100** ·
  thiếu kết quả · mã kiểm thử lạ.

### 2a. Bản dựng trang 3 ngày 2026-09-09

Trang 3 trước đó là một trang trắng: `05_visuals.py` không khai báo ô nào cho
`PAGE3`. Lượt này catalogue dựng lại cả ba trang. Bốn thay đổi cần biết khi đọc
`git diff`:

1. **Thêm 10 phép đo (M110–M119), tổng còn 71.** Họ gia nhập (M113–M119) trước
   đây **không tồn tại trong model** — `05_acceptance.dax` tính nó inline nên
   B10 vẫn chạy được, nhưng không có gì để một ô trực quan bám vào. Hai phép đo
   M113/M114 ẩn, năm phép đo còn lại hiện trong thư mục `10 Entry lag`.
2. **M070 và M071 đổi `ALL( DimMetric )` → `KEEPFILTERS( FILTER( ALL(...) ) )`.**
   Dạng cũ xoá sạch bộ lọc công nghệ nên gió và mặt trời **luôn bị cộng chung**,
   và không cách nào đọc được "2 nước cho gió, 4 nước cho mặt trời" mà Gate B9
   đòi. Không phép đo nào trong nhóm này bị `05_acceptance.dax` gọi, nên không
   đích khoá nào đổi.
3. **M055 `Positive Growth Share` thêm chốt `is_asean`.** Hai truy vấn nghiệm
   thu gọi nó đều kèm `DimEntity[entity] = "Vietnam"` nên giá trị không đổi.
4. **Bộ lọc `metric = "generation"` của slicer Technology nay do catalogue sinh
   ra** (`05_build_report.py :: visual_filters`), sao đúng hình dạng Desktop đã
   lưu. Mục 6 của danh sách dưới đây vì thế **không còn là việc tay**.

Tổng cộng **73 phép đo** sau khi kiểm chứng bổ sung hai lần (xem ba lỗi dưới).

### Ba lỗi phát hiện và sửa trong lượt này

Không lỗi nào trong ba lỗi này thuộc về trang 3 nói riêng — cả ba đều đã nằm sẵn
trong dự án và chỉ lộ ra khi có ô trực quan thật đi qua chúng.

1. **`05_acceptance.py` lấy tên trường sai.** Dùng `test_id.rsplit("_", 1)[-1]`
   nên với `..._LAG_FROM_2000` nó trả về `"2000"`, và nhánh trừ mốc năm **không
   bao giờ chạy**. Hai truy vấn độ trễ xuất ra *năm gia nhập* (2006 và 2010)
   trong khi đích là *độ trễ* (6 và 10). Đã đổi sang so khớp cả hậu tố.
2. **Bảng gia nhập ra 70 dòng thay vì 40.** `technology_label` có bảy nhãn;
   `Renewables total`, `Biofuel` và `Geothermal` không có chỉ số sản lượng nào,
   nhưng các phép đo gia nhập vẫn trả `NOT_OBSERVED_BY_2021` cho chúng — một
   khẳng định **sai**: không có gì được đo ở đó thì cũng không có gì "không quan
   sát được". Thêm `Entry Metric Count` (M120) làm chốt, năm phép đo công khai
   trả trống khi số chỉ số sản lượng trong phạm vi bằng 0. Đo lại: **40 dòng**.
3. **Chuỗi trạng thái sai dấu cách.** `Rank Status` và `Concentration Status`
   trả `NOT_DEFINED / ZERO_SCOPE_TOTAL` (có dấu cách) trong khi `05_expected.py`
   ghép từ hai cột của Phase 3 thành `NOT_DEFINED/ZERO_SCOPE_TOTAL` (không dấu
   cách). Lỗi này **không chỉ ảnh hưởng trang 3**: `[Rank Status]` là thứ truy
   vấn B8 gọi, nên trang 2 sẽ trượt y hệt. Đã đổi cả hai phép đo về dạng của
   Phase 3; `VN Rank Label` thừa hưởng tự động và nay đọc
   `NOT_DEFINED/ZERO_SCOPE_TOTAL | World 40/212`.

### Kết quả kiểm chứng B9 ngày 2026-09-09

Chạy qua MCP trên model đang mở trong Desktop `2.157.1354.0`:

- **67/67 mã `P5_B9_*` `PASS`** (`output/stats/05_validation_results.csv`).
- Đối chiếu thêm **trực tiếp trên các phép đo mới**, vì `05_acceptance.dax` tính
  họ gia nhập và hệ số công suất **inline** nên nó không chạm vào M110–M121:
  bảng gia nhập đúng 40 dòng khóa và 80 giá trị trạng thái · số đếm bốn công
  nghệ khớp §5.5 tuyệt đối · bốn ca chuẩn khớp từng chữ, `Entry Lag` **để trống**
  ở dòng kiểm duyệt trái thay vì 0 · hệ số công suất gió 2 nước/33 cặp, mặt trời
  4 nước/71 cặp, trần đúng `0,3257639133464354` · lưới 220 điểm · V11 tám nước
  xuất phát đúng 100 còn Brunei và Singapore trả trống thay vì vô hạn · thẻ
  "có/cần" đọc 40/40 · 4/4 · 10/10 · 20/20.
- Kiểm §8.5 sau các lượt ghi MCP: 9/9 phép đo bị sửa có độ dài biểu thức khớp
  catalogue, model 73 phép đo = catalogue 73 → **không lệch**.
- `P5_B2_*`, `P5_B7_*`, `P5_B8_*` đang là `MISSING_RESULT` vì lượt này **chỉ**
  chạy khối B9. Chạy đủ 169 mã là việc của B10.

⚠️ Các ô trên chứng minh **phía tham chiếu** đúng. Chúng chưa nói gì về Power BI —
lớp đó chỉ được xác nhận khi `05_test_results.tsv` có dữ liệu thật.

### Bản PBIP đi sau catalogue — phát hiện 2026-09-10

Ba mục "đã sửa" ở trên được đo trên **model đang sống trong Desktop**, không phải
trên tệp nằm trong `powerbi/`. Hai thứ đó đã tách nhau: Desktop lưu lúc 22:25 từ
bản nó nạp **trước** khi `05_measures.py` (22:16) và `05_visuals.py` (22:20) được
sửa, nên PBIP trên đĩa giữ nguyên trạng thái cũ. Ba sai lệch, đo được bằng văn bản:

| Sai lệch | Catalogue | PBIP trên đĩa |
|---|---|---|
| Số phép đo | 73 | 71 — thiếu `M120 Entry Metric Count`, `M121 ASEAN Completeness Label` |
| Chốt bảng gia nhập | 5/5 phép đo mang `[Entry Metric Count] >= 1` | 0/5 → V12 quay lại 10 × 7 = **70 dòng** |
| Chuỗi trạng thái M080/M081 | `NOT_DEFINED/ZERO_SCOPE_TOTAL` | `NOT_DEFINED / ZERO_SCOPE_TOTAL` (có dấu cách) — **chạm cả trang 2** qua `VN Rank Label` |
| Thẻ "có/cần" của trang 3 | `ASEAN Completeness Label` (M121) | `Completeness Label` (M082), đọc phạm vi toàn 256 thực thể × 57 năm |

Sai lệch thứ ba là thứ soi bằng mắt đã bỏ sót; chỉ phép đối chiếu biểu thức mới
bắt được. Nó cũng cho thấy vì sao §8.5 chưa đủ: điều khoản đó nói *"sau mỗi lượt
MCP ghi, xuất lại danh mục và so với `DAX_Measures.md`"*, và lượt 2026-09-09 đã
làm đúng vậy trên model sống — nhưng **không ai so với tệp trên đĩa**, mà tệp trên
đĩa mới là sản phẩm bàn giao.

**Cách chặn từ nay:** `python/05_test_artifacts.py` — chín tiêu chí C1–C9 đọc
thẳng TMDL, `report.json` và `DAX_Measures.md`, không cần Power BI. C1 bắt lệch số
phép đo, C2 bắt mất chốt gia nhập, C3 là chính phép đối chiếu §8.5 nay đã cơ giới
hoá, C5 bắt `report.json` đi sau catalogue ở bất kỳ ô nào.

Bộ tiêu chí được viết **trước** khi sửa và bắt buộc phải trượt trên bản hỏng: chạy
lần đầu cho `FAIL | failed=C1,C2,C3,C5,C6 | passed=4/9`. Sau khi dựng lại bằng
`python python\05_build_pbip.py` thì `PASS | 9/9`. Dựng hai lần cho `report.json`
và `DAX_Measures.md` giống hệt nhau.

⚠️ **`.pbix` chưa đổi.** Dựng lại chỉ ghi PBIP; `ASEAN_Renewables.pbix` giữ nguyên
mã băm `597b0a61…` và vẫn mang model 71 phép đo cho tới khi mở lại `.pbip` trong
Desktop và lưu đè. Mọi phép đo D1–D5 phải làm **sau** bước lưu đè đó.

## 2b. Việc tay bắt buộc trong Desktop — chưa sinh được bằng script

Mười mục dưới đây **không** nằm trong `05_visuals.py` được. Lý do kỹ thuật, không
phải bỏ sót: `05_build_report.py` chỉ ghi những hình dạng JSON đã được **lấy mẫu
thật** từ Power BI Desktop 2.157.1354.0, và các tính năng này chưa có mẫu nào.
Đoán hình dạng thì Desktop vẫn nhận tệp nhưng ô hiển thị sai hoặc trắng mà không
báo lỗi — đúng kiểu lỗi đắt nhất. Phân vai `B6–B9: Tay` của `PHASE5.md` §8.3 đã
lường trước việc này.

Đánh dấu từng mục sau khi làm trong Desktop và lưu lại `.pbix`:

- [ ] **1. Đồng bộ slicer** `Report year` và `Measure mode` trên cả ba trang
  (*View → Sync slicers*). Hiện mỗi trang giữ một bản slicer riêng, không đồng
  bộ — đổi năm ở trang 1 thì trang 2 vẫn giữ năm cũ, tức **rớt ô đầu tiên của
  Gate B10**.
- [ ] **2. Khoá chọn đơn** cho hai slicer đó, đặt mặc định `2021` và
  `RENEWABLE_TOTAL`. Hiện chọn được nhiều giá trị: chọn 2000 + 2010 cùng lúc thì
  `SELECTEDVALUE( …, 2021 )` lặng lẽ rơi về 2021 — slicer hiện hai năm, KPI hiện
  năm thứ ba, không có gì báo.
- [ ] **3. Dấu trang `Reset`** + nút gọi nó, và **thanh điều hướng ba trang**
  (Gate B6).
- [ ] **4. Ma trận tương tác** (*Format → Edit interactions*). Trang 2: slicer
  `Technology` đặt **Không tương tác** với bốn thẻ KPI, hai panel V07, hai panel
  V08 và bảng V09; chỉ giữ tác động lên V06. Không làm thì chọn một công nghệ sẽ
  khiến thẻ “Vietnam total” âm thầm còn một công nghệ trong khi tiêu đề vẫn ghi
  *total*, và panel TWh của V07 lệch khỏi panel % điện — vì
  `Share Electricity Pct` có `ALL( DimMetric )` bên trong nên **không** đổi theo.
  Hai panel khi đó không còn mô tả cùng một đại lượng, đúng cái bẫy suy diễn mà
  Gate B8 cấm.
- [ ] **5. Phụ đề trang 2**: “Trang này cố định Việt Nam — bộ lọc quốc gia không
  tác động”. Mọi ô trang 2 dùng phép đo `VN *` có `ALL( DimEntity )` nên slicer
  `Country` hoàn toàn vô tác dụng ở đây. Đó là khoá đúng theo §2.5, nhưng §2.5
  cũng đòi ghi rõ phạm vi khi một ô cố ý bỏ qua bộ lọc.
- [x] **6a. Giới hạn slicer `Technology`** còn bốn công nghệ có `*_generation_twh`.
  `technology_label` sinh ra bảy nhãn; ba nhãn `Renewables total`, `Biofuel`,
  `Geothermal` không có chỉ số sản lượng nào nên chọn vào là **trắng cả trang,
  không một dòng giải thích**. → **Không còn là việc tay từ 2026-09-09**:
  catalogue sinh thẳng bộ lọc `metric = "generation"` cho slicer này trên cả ba
  trang, dựng lại bao nhiêu lần cũng còn. Tiêu chí C7 chống hồi quy.
- [x] **6b. Giới hạn slicer `Country`** còn ASEAN-10 — cùng lớp lỗi với 6a nhưng ở
  phía ngược lại. `entity_label` phân giải đủ **256** thực thể nên danh sách chào
  cả `World`, `Africa`, `USSR` bên cạnh mười nước mà bất kỳ ô nào cũng vẽ được;
  chọn phải một trong số đó là trắng trang, không một dòng giải thích. Gate B7
  cấm thực thể tổng hợp trong danh sách nước, và ở trang 3 slicer này **lọc thật**
  V10, V11, V12, V13_GROWTH và V14.
  → Chốt ngày 2026-09-10: `DimEntity[is_asean] = 1`, **áp cả ba trang**. Chọn cột
  này thay vì `is_current_country_or_territory = 1` (215 dòng) vì mọi ô của cả ba
  trang đều chốt `is_asean` hoặc khoá Việt Nam trong DAX, còn đại lượng ngoài
  ASEAN duy nhất — dòng `World` — đi qua `ALL( DimEntity )` nên không bao giờ thấy
  slicer này; 205 nước kia có mặt trong danh sách cũng không đổi được ô nào.
  **Không** dùng `is_aggregate = 0`: nó trả 216 dòng vì `USSR` là `historical` chứ
  không phải tổng hợp — đúng bẫy §2.2 đã ghi. Từ 2026-09-10 do catalogue sinh;
  tiêu chí C6 chống hồi quy.

  ⚠️ Một chi tiết chưa lấy mẫu: `is_asean` là `int64` nên literal phải là `1L`,
  trong khi mẫu duy nhất đã có từ Desktop (`'generation'`) là cột chữ. Nếu sai,
  triệu chứng là slicer vẫn liệt kê 256 mục — đó chính là thứ tiêu chí **D3** đo.
- [ ] **7. Đảo trục Y** của `V08_GLOBAL` để hạng 1 nằm trên. `invertAxis` nằm
  trong khối `objects` của ô trực quan — chưa có mẫu — nên biểu đồ hạng đọc
  ngược cho tới khi làm bước này.
- [ ] **8. Màu theo Phase 4** — phần lớn đã tự động. Áp tệp chủ đề:
  *View → Themes → Browse for themes* → `powerbi\ASEAN_Renewables_theme.json`.
  `dataColors` xếp theo đúng thứ tự `technology_sort` (thuỷ điện `#0072B2` →
  nguồn khác `#CC79A7` → gió `#009E73` → mặt trời `#E69F00`), nên hai biểu đồ
  bốn chuỗi (V02 trang 1 và V06 trang 2) nhận đúng màu mà **không phải chọn tay
  từng series** — ánh xạ này chỉ tin được vì `technology_label` đã có
  `sortByColumn`, tức thứ tự chú giải là xác định thay vì theo alphabet.
  Còn lại phải đặt tay vì bảng màu gán theo **chỉ số**, không theo tên: 4 biểu đồ
  một chuỗi ở trang 2 (V07 ×2, V08 ×2) đổi sang màu nhấn Việt Nam `#D55E00`, và
  2 panel V04 của trang 1 đổi sang `#374151`. Đường dẫn: Format visual →
  **Lines** → **Colors** → Custom color.
- [ ] **9. Tiếng Việt** cho tiêu đề ô, tên trang và chân trang; số theo quy ước
  Việt (`1.000` hàng nghìn, `0,0` thập phân). **Không** đưa vào TMDL — đã có
  tiền lệ hỏng dấu, xem `powerbi/README.md` §“Quy tắc mã hoá TMDL”.
- [ ] **10a. Bề rộng cột** bảng V09 — 8 cột trong 627,5pt nên phải kéo tay mép
  tiêu đề: `year` ~45pt, `VN Direction Relation` rộng nhất (~130pt) vì chứa chuỗi
  `ONE_OR_BOTH_UNCHANGED`, phần còn lại chia đều.
- [ ] **10b. Tô màu hai năm ngược hướng** — phép đo đã dựng sẵn, chỉ còn nối dây.
  Cột chữ chỉ tô được qua `Format by: Field value` (nhánh `Rules` đòi trường số),
  nên màu phải đến từ một phép đo: `VN Direction Color` (M102) trả
  `#D55E00` ở năm `OPPOSITE_DIRECTION` và **trống** ở mọi năm khác, để các dòng
  còn lại giữ màu mặc định thay vì tô kín cả cột. Trong Desktop: dropdown của cột
  `VN Direction Relation` trong giếng **Values** → **Conditional formatting** →
  **Font color** → **Format by** = `Field value` → **Based on field** =
  `VN Direction Color`.

### Thêm sau bản dựng trang 3 (2026-09-09)

- [ ] **11. Làm lại hai thứ bản dựng đã xoá.** (a) Kích thước bốn slicer từng
  kéo tay lên 204–212pt, nay về lại 86,25–93,75pt của lưới; kéo lại nếu thấy
  chật, nhưng **cùng một kích thước trên cả ba trang**. (b) Ma trận tương tác
  trang 2 — lần này làm cho đúng: slicer `Technology` giữ **Filter** với V06 và
  đặt **None** với 13 ô còn lại. Bản cũ đặt cùng một giá trị cho **cả 14** ô,
  tức V06 cũng bị ngắt, nên slicer đó không tác động được vào đâu.
- [ ] **12a. Trục Y của V10 và V14** (*Format → Y axis → Scale*): chọn **Shared**
  hay **Independent** cho lưới small multiples. Phase 4 công bố cả hai bản
  (C05 chung trục, C06 tự do trục) vì hai cách đọc khác nhau — chọn xong phải
  ghi rõ đang là bản nào trong phụ đề, đúng như checklist Phase 4 đòi.
- [ ] **12b. Lưới small multiples của V10** (*Format → Small multiples → Grid
  layout*): đặt **5 cột × 2 dòng**. Khối `objects` của ô đang **rỗng hoàn toàn**,
  nghĩa là chưa ai đặt gì và Desktop dùng mặc định 2×2 — bốn nước hiện, sáu nước
  phải cuộn. Gate B9 đòi lưới có đúng 10 nước và Gate B10 đòi PDF không cắt, mà
  bản xuất tĩnh chỉ in phần đang hiện.
  Không sinh được bằng script: `05_build_report.py` chỉ ghi hình dạng JSON **đã
  lấy mẫu thật** từ Desktop, và `smallMultiplesLayout` chưa có mẫu nào trong dự
  án — đoán thì Desktop vẫn mở được tệp nhưng ô render sai hoặc trắng mà không
  báo lỗi. Vì vậy đi vòng lấy mẫu: đặt tay ở đây → lưu → trích khối JSON Desktop
  vừa ghi → đưa vào catalogue (mục 12c) để nó sống sót qua các lần dựng lại.
- [ ] **12c. Gói mẫu lưới vào catalogue** — sau 12b. Không làm bước này thì lần
  chạy `05_build_pbip.py` kế tiếp xoá mất cài đặt lưới, vì `main()` gọi
  `shutil.rmtree` lên cả `.SemanticModel/` và `.Report/` trước khi dựng. Xong thì
  bổ sung tiêu chí **C10**: ô V10 mang khối lưới đúng số cột/dòng đã chốt.
- [ ] **13. Ma trận tương tác trang 3.** Slicer `Country` **lọc** V10, V11,
  V13_GROWTH, V14 và bảng V12; nhưng bốn thẻ tập trung (Top-1, Top-3, HHI, Gini)
  phải đặt **Không tương tác** — mẫu số của chúng là `ASEAN_SUM_10` cố định, và
  §2.5 đòi mẫu số khu vực không đổi theo lựa chọn quốc gia. Bốn thẻ này chốt
  `is_asean` bên trong DAX nên số vẫn đúng, nhưng để mặc định thì lọc một nước
  sẽ khiến bốn thẻ trống trơn mà không nói vì sao.
- [ ] **14. Khoá chọn đơn cho slicer `Base year`**, mặc định **2010**. Cùng bẫy
  như mục 2: chọn hai năm thì `SELECTEDVALUE( …, 2010 )` lặng lẽ rơi về 2010.
- [ ] **15. Bề rộng cột bảng V12** — 7 cột trong 627,5pt. Cột rộng nhất là
  `Material Entry Status` (`OBSERVED_MATERIAL_TRANSITION`, 28 ký tự); hai cột
  nhãn năm chỉ cần ~45pt khi có năm, nhưng phải đủ cho
  `CENSORED/EVENT_NOT_EXACTLY_OBSERVED` ở dòng bị kiểm duyệt.
- [ ] **16. Tiếng Việt cho trang 3** — tiêu đề 18 ô, tên trang, và **tiêu đề cột
  bảng V12** (mặc định lấy nguyên tên phép đo tiếng Anh). Không đưa vào TMDL,
  xem §"Quy tắc mã hoá TMDL" của `powerbi/README.md`.

## 2c. Tiêu chí D1–D5 — chỉ đo được khi báo cáo đã render

`05_test_artifacts.py` chứng minh **tệp** đúng; nó không chứng minh gì về thứ hiện
lên màn hình. Năm tiêu chí dưới đây bù đúng khoảng trống đó và phải đo **sau** khi
mở lại `.pbip` trong Desktop và lưu đè `.pbix` — trước bước đó `.pbix` vẫn mang
model 71 phép đo cũ.

| Mã | Tiêu chí | Cách đo | Chặn cổng |
|---|---|---|---|
| D1 | Bảng V12 đúng **40 dòng khóa** và **80 giá trị trạng thái**; không dòng nào mang nhãn `Renewables total`, `Biofuel` hay `Geothermal` | đếm trên bảng, hoặc `dax_query_operations` | B5, B9 |
| D2 | Thẻ *Components have / need* đọc `40/40` ở trạng thái mặc định (ASEAN-10 · 2021 · `RENEWABLE_TOTAL`); đọc `4/4` khi chọn một nước, `10/10` khi chọn một công nghệ | đọc thẻ | B9 |
| D3 | Slicer `Country` liệt kê **đúng 10 mục**, không có `World`, `Africa`, `USSR`. Nếu vẫn thấy 256 mục thì literal `1L` sai kiểu — xem cảnh báo ở mục 6b | mở slicer, đếm | B7 |
| D4 | V10 hiện **đủ 10 panel cùng lúc**, không thanh cuộn; PDF trang 3 in đủ 10 panel | nhìn ô, rồi *Export to PDF* | B9, B10 |
| D5 | 67/67 mã `P5_B9_*` vẫn `PASS` trên model vừa lưu | chạy khối B9 của `05_acceptance.dax` qua MCP | B9 |

- [ ] D1 · [ ] D2 · [ ] D3 · [ ] D4 · [ ] D5

## 3. Ca bắt buộc người nghiệm thu phải tự thử

Đánh dấu sau khi thực sự bấm trên dashboard, không suy ra từ kiểm định số.

### 3.1. Bộ lọc năm

- [ ] Đổi 2021 → 2010 → 2000: **cả ba trang** đổi tiêu đề, KPI và dữ liệu; không trang nào giữ số cũ.
- [ ] Chuỗi thời gian **dừng** ở năm chọn, không co lại còn một điểm.
- [ ] Nút đặt lại đưa về năm 2021 và chế độ tổng NLTT.

### 3.2. Công tắc “chỉ NLTT hiện đại”

- [ ] Bật/tắt ở năm 2021 làm **thứ tự hạng đổi đúng**: Singapore +4, Indonesia −4, Lào −5.
- [ ] Thái Lan hiện đại hạng 2, Philippines hạng 3 — hai nước cùng tăng 3 bậc nhưng **không đồng hạng**.
- [ ] Năm 2000 chế độ hiện đại: hạng ASEAN, top-1, top-3, HHI và Gini đều hiện **không xác định kèm lý do**, không hiện `0` và không cùng hạng 1.

### 3.3. Phạm vi quốc gia theo trang

- [ ] Trang 1: chọn một nước chỉ **tô sáng**; hàng KPI khu vực vẫn là ASEAN-10.
- [ ] Trang 2: chọn nước ở trang khác **không** làm Trang 2 rời khỏi Việt Nam.
- [ ] Trang 3: chọn nước lọc biểu đồ cấp nước nhưng **mẫu số khu vực, HHI/Gini và hạng vẫn giữ ASEAN-10**.
- [ ] Mọi ô cố ý bỏ qua bộ lọc đều có nhãn phạm vi đọc được ngay trên tiêu đề.

### 3.4. Bộ lọc công nghệ

- [ ] Lọc xuống **một** công nghệ: ô vẫn trả số (10/10), không trả trống. Đây là bẫy `Required Component Count` viết cứng “4”.
- [ ] Nhãn “có/cần” hiển thị đúng: 4/4 cho một nước, 40/40 cho tổng hợp ASEAN-10.

### 3.5. Đọc số

- [ ] Số hiển thị theo quy ước Việt: `1.000` hàng nghìn, `0,0` thập phân — đồng bộ với 13 PNG Phase 4 sau khi sửa L1.
- [ ] TWh và phần trăm điện **không dùng chung trục** ở V07.
- [ ] Không ô nào hiện `NaN`, vô hạn, hoặc số `0` sinh ra từ dữ liệu thiếu.
- [ ] Chú thích V14 ghi rõ “công suất cuối năm”, “chỉ báo xấp xỉ”, đủ tên nước thiếu dữ liệu, và không kết luận hiệu quả kỹ thuật.

### 3.6. Hiệu năng và bố cục

- [ ] Mỗi ô trực quan xong trong ≤ 2 giây, mỗi trang ≤ 5 giây (đo bằng Performance Analyzer).
- [ ] Làm mới hai lần cho cùng kết quả; đóng/mở lại không mất quan hệ hay bộ lọc mặc định.
- [ ] PDF đủ ba trang, không chữ chồng, không cắt, không vượt khung.

### 3.7. Hồi quy trang 2 sau bản sửa 2026-09-09

Sáu lỗi đã sửa ở phía DAX và catalogue ô trực quan. Mỗi dòng là một ca **phải tự
bấm** để xác nhận, vì đây đúng là loại lỗi trông hợp lý trên màn hình:

| # | Ca | Trước khi sửa | Phải thấy sau khi sửa |
|---|---|---|---|
| A1 | V08 panel 1, năm 2021 | đường **phẳng tuyệt đối**, kéo cả 1965–1999 | dốc lên, đúng 22 điểm 2000–2021 |
| A2 | V09, ba cột hạng | `16` · `205` lặp nguyên trên mọi dòng | đổi theo từng năm |
| A3 | V09, cột hướng, chế độ **tổng** | 2000 · 2003 · 2014 | đúng **2003 · 2014** |
| A3 | V09, cột hướng, chế độ **hiện đại** | 2016 | 2016 (không đổi) |
| A4 | V09, dòng 2000, chế độ tổng | `YoY ≈ +5,63%` | **trống** — khớp `NOT_DEFINED` của Phase 3 |
| A5 | V09 | không có hạng ASEAN | có cột `VN ASEAN Rank ToDate` |
| A6 | Thẻ KPI [4], 2021 tổng | `16` | `ASEAN 1/10 \| World 16/205` |
| A5 | Thẻ KPI [4], 2000 hiện đại | `40` | `NOT_DEFINED/ZERO_SCOPE_TOTAL \| World 40/212` |
| C3 | Thẻ KPI [2] và [3] cạnh nhau | `42,5787` bên `35,9800%` | cả hai đều có dấu `%` |
| — | Chú giải công nghệ V06 | thứ tự alphabet | thứ tự chồng Phase 4 |

- [ ] Toàn bộ mười ca trên đã tự bấm và đúng.
- [ ] Không dòng nào trước năm 2000 xuất hiện ở V08, V09 (mọi phép đo trang 2
  giờ đều mang cờ cửa sổ, nên không cần bộ lọc mức trang).

### 3.8. Trang 3 — đọc bằng mắt theo Gate B9

Kiểm định số nói các phép đo trả đúng; mấy ô dưới đây nói cái **hình** đọc đúng.

- [ ] V10 hiện đúng **10 nước**, không nước thứ 11 và không dòng `World`; một
  chuỗi đủ cửa sổ có 22 điểm (10 × 22 = 220).
- [ ] V11 ở năm gốc 2010: mọi đường xuất phát từ **100**. Đổi năm gốc sang một
  năm mà nước nào đó bằng 0 → đường đó **biến mất**, không nhảy lên vô hạn.
- [ ] V12 đúng **40 dòng**; Brunei–mặt trời giữ `NOT_OBSERVED_BY_2021` và
  `NOT_MATERIAL_BY_2021`, **cột năm để trống chứ không điền 2021**.
- [ ] V12, Việt Nam–mặt trời: cột dương ghi **2010**, cột vật chất ghi **2018**,
  độ trễ **10**. Việt Nam–thuỷ điện: `ACTIVE_AT_WINDOW_START`, hai cột năm đều
  là `CENSORED/EVENT_NOT_EXACTLY_OBSERVED` và độ trễ **để trống**, không phải 0.
- [ ] V12 **không đổi theo bộ lọc năm** — trạng thái định nghĩa trên cả cửa sổ
  2000–2021, đó chính là nghĩa của `NOT_OBSERVED_BY_2021`.
- [ ] V13, năm 2021 tổng NLTT: top-3 `67,102326891%`, HHI `0,207886216029`,
  Gini `0,529218182611`. Chuyển sang hiện đại: `92,2536859349%` /
  `0,480403925201` / `0,771284811608`.
- [ ] V13, năm 2000 chế độ hiện đại: bốn thẻ **trống** và thẻ lý do hiện
  `NOT_DEFINED/ZERO_DENOMINATOR`. Không thẻ nào hiện `0`.
- [ ] V13_GROWTH với năm gốc 2010, năm báo cáo 2021: Việt Nam `42,3780539369%`
  ở chế độ tổng và `65,985915493%` ở chế độ hiện đại.
- [ ] V14: chọn `Wind` → thẻ độ phủ hiện **2**, chỉ Philippines và Thái Lan;
  chọn `Solar` → **4**, thêm Malaysia và Việt Nam. Bỏ chọn → **4**.
- [ ] V14 không có điểm nào vượt `0,3257639133464354`, và chú thích nói rõ
  "công suất cuối năm" + "chỉ báo xấp xỉ", không kết luận hiệu quả kỹ thuật.
- [ ] Thẻ "có/cần": một nước `4/4`, bỏ hết bộ lọc quốc gia `40/40`, lọc một công
  nghệ `10/10`.

## 4. Bằng chứng phát hành

| Hạng mục | Giá trị | Ghi lúc |
|---|---|---|
| SHA-256 `ASEAN_Renewables.pbix` | | B10 |
| Số mã kiểm thử đạt / tổng | | B10 |
| Số dòng chặn khác `PASS` | | B10 |
| Phiên bản Power BI Desktop | `2.157.1354.0` | B1 |
| Dấu vân tay đầu vào Phase 2 | `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10` | B1 |
| 17 CSV nguồn và đầu ra Phase 1–4 không đổi | | B10 |

## 5. Ký nhận tổng thể

Chỉ điền khi B0–B10 đều `ĐẠT`, mọi ô mục 3 đã được kiểm và không còn ghi chú phải sửa.

| Trường | Nội dung |
|---|---|
| Kết quả tổng thể | CHỜ NGHIỆM THU |
| Người nghiệm thu | |
| Ngày nghiệm thu | |
| Phiên bản phương pháp | `phase5_v1` |
| Ghi chú cuối | |

Sau khi ký mới được cập nhật Phase 5 trong `PLAN.md` thành “ĐÃ HOÀN THÀNH” và mở
Phase 6 — không phải trước đó.
