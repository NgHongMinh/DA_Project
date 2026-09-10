# Dashboard Power BI — ASEAN Renewables (Phase 5)

Thư mục này chứa dashboard ba trang cho đồ án. Sản phẩm nộp là
`ASEAN_Renewables.pbix`; phần còn lại là dự án dạng văn bản dùng để dựng ra nó và
bộ bằng chứng nghiệm thu.

| Hạng mục | Giá trị |
|---|---|
| Phiên bản phương pháp | `phase5_v1` |
| Power BI Desktop dùng để dựng | `2.157.1354.0` (bản Microsoft Store) |
| Dấu vân tay đầu vào Phase 2 | `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10` |
| SHA-256 `fact_energy.csv` | `dfaca2c46efde54b506f317497d458ed864f88ab4a8d74de9665afaa467a4374` |
| Phạm vi | ASEAN-10, 2000–2021, không nội suy, đã loại 2022 |

> `PLAN.md` §Phase 0 ghi Power BI `2.156.951.0`. Đó là bản cũ trước khi Microsoft
> Store tự cập nhật; bản thực tế đang dùng là `2.157.1354.0`.

## 1. Vì sao có PBIP mà vẫn phải có PBIX

`.pbix` là tệp **nhị phân** và chỉ Power BI Desktop ghi ra được. Không script nào
tạo được nó. Ngược lại, PBIX nhị phân thì `git diff` không đọc được — đúng thứ mà
Gate B1 của `PHASE5.md` phải bù bằng một hợp đồng giấy.

PBIP giải quyết cả hai: mô hình nằm ở dạng TMDL văn bản, xem được diff, sinh lại
được; còn `.pbix` vẫn là sản phẩm nộp theo `PLAN.md`.

```
ASEAN_Renewables.pbip                  điểm vào của dự án
ASEAN_Renewables.SemanticModel/        mô hình: bảng, quan hệ, 61 phép đo (TMDL)
ASEAN_Renewables.Report/               lớp trình bày: ba trang
ASEAN_Renewables.pbix                  ← sinh ra từ Desktop, là sản phẩm nộp
ASEAN_Renewables_theme.json            bảng màu Phase 4 (áp tay một lần trong Desktop)
DAX_Measures.md                        danh mục phép đo (SINH TỰ ĐỘNG)
05_acceptance.dax                      truy vấn nghiệm thu (SINH TỰ ĐỘNG)
review/05_dashboard_default.pdf        bằng chứng bố cục ba trang
```

### Tệp chủ đề — vì sao nó tồn tại

Màu dữ liệu nằm trong khối `objects` của từng ô trực quan, và
`05_build_report.py` không sinh khối đó (chưa lấy mẫu từ Desktop). Tệp chủ đề là
đường vòng hợp lệ: định dạng chủ đề là schema **có tài liệu**, và Desktop **từ
chối kèm thông báo** nếu khoá sai — khác hẳn kiểu lỗi im lặng của `objects` đoán bừa.

Áp một lần: *View → Themes → Browse for themes* → chọn tệp này.

`dataColors` được xếp theo đúng thứ tự `technology_sort`:

| Chỉ số | Màu | Công nghệ |
|---:|---|---|
| 0 | `#0072B2` | Thuỷ điện |
| 1 | `#CC79A7` | Nguồn tái tạo khác |
| 2 | `#009E73` | Gió |
| 3 | `#E69F00` | Mặt trời |
| 4 | `#D55E00` | Nhấn Việt Nam / gió + mặt trời |
| 5 | `#374151` | Tổng tái tạo |

Nhờ vậy hai biểu đồ bốn chuỗi (V02 và V06) nhận đúng màu Phase 4 **không cần
chọn tay từng series**. Ánh xạ này chỉ đúng vì `technology_label` đã có
`sortByColumn: technology_sort` — nếu thứ tự chú giải quay về alphabet thì màu
lệch ngay. Bảng màu gán theo **chỉ số**, không theo tên, nên các biểu đồ một
chuỗi vẫn phải đặt màu tay.


**Không sửa tay `DAX_Measures.md` và `05_acceptance.dax`.** Cả hai sinh ra từ
`python/05_measures.py` và bộ đích ở `output/stats/05_expected_values.csv`. Sửa ở
nguồn rồi chạy lại script.

## 2. Cách dựng `.pbix` lần đầu

1. **Nhấp đúp `ASEAN_Renewables.pbip` trong File Explorer.** Hộp thoại
   `File → Open → Browse this device` lọc theo loại tệp và **không liệt kê
   `.pbip`**, nên mở từ trong Desktop sẽ không thấy gì để chọn. Nếu vẫn muốn đi
   đường đó thì gõ thẳng đường dẫn đầy đủ vào ô *File name* để bỏ qua bộ lọc.
2. Nếu Desktop hỏi bật *Power BI Project (.pbip) save option*, bật rồi mở lại.
3. Kiểm tham số `pCleanFolder`. Mặc định trỏ tới `output\clean` của máy này. Nếu
   chuyển máy: *Transform data → Manage parameters → pCleanFolder*.
4. `Refresh` toàn bộ.
5. **Trước khi tin bất kỳ phép đo nào**, đọc thẳng hai số của Gate B2:
   - tổng bốn công nghệ của 10 nước ASEAN năm 2021 = `289,6557446`
   - dòng `World` năm 2021 = `7.885,04005`

   Lệch ở đây là **lỗi kiểu dữ liệu, không phải lỗi DAX**: `FactEnergy[value]`
   phải là `Decimal Number` (dấu phẩy động 64-bit). `Fixed Decimal Number` cắt
   còn 4 chữ số thập phân, mà **36.027/89.075** giá trị có nhiều hơn 4 chữ số.
6. `File → Save as` → `powerbi\ASEAN_Renewables.pbix`.
7. **Giữ Desktop mở** nếu bước tiếp theo cần MCP.

### Quy tắc mã hóa TMDL — hai lần vấp

**1. Cấm BOM.** Power BI Desktop từ chối thẳng tệp TMDL có byte order mark:

```
Only text with UTF8 encoding without BOM (byte order marks) is supported.
Detected BOM: 'UTF-8'
   at Microsoft.PowerBI.Packaging.UTF8EncodingThrowOnBOM.CheckBom(...)
```

⚠️ **`ConnectFolder` của MCP lại CHẤP NHẬN BOM.** Hai trình phân tích khác nhau,
nên MCP nạp được không có nghĩa Desktop mở được. Đừng dùng MCP làm bằng chứng về
mã hóa — chỉ dùng nó để kiểm **cú pháp** TMDL.

**2. TMDL giữ nguyên ASCII.** Một bản dựng trước có tên thư mục và mô tả tiếng
Việt, và một phần model quay về dạng hỏng dấu (`Vi?t Nam`, `Th?y di?n`), thậm chí
tách một thư mục thành hai: `03 Tỷ trọng` và `03 T? tr?ng` cùng tồn tại. Nguyên
nhân chưa xác định được, nên lớp model giữ ASCII và **tiếng Việt chỉ nằm ở lớp
trình bày** — gõ thẳng vào ô trực quan trong Desktop, nơi nó được lưu trong
`.pbix` nhị phân và không bao giờ đi qua tệp văn bản.

`05_build_pbip.py` chặn cả hai ngay lúc ghi: BOM bị loại bỏ, và ký tự ngoài ASCII
trong TMDL làm dừng bản dựng kèm thông báo chỉ đúng ký tự vi phạm.

### Cạm bẫy `$schema` — đã gặp một lần

Desktop **kiểm tra chuỗi `$schema` bằng biểu thức chính quy** và từ chối mở
**toàn bộ** dự án nếu không khớp, kể cả khi mọi thứ khác đúng. Hai họ schema khác
nhau và rất dễ nhầm:

| Tệp | Chuỗi đúng |
|---|---|
| `ASEAN_Renewables.pbip` | `…/fabric/pbip/pbipProperties/1.x.x/schema.json` |
| `.platform` | `…/fabric/gitIntegration/platformProperties/2.0.0/schema.json` |

Chú ý `.pbip` dùng họ `fabric/pbip/pbipProperties`, **không** phải
`fabric/item/…/definitionProperties` như các tệp artifact. Dùng nhầm sẽ báo:

```
Expected '$schema' property in '…\ASEAN_Renewables.pbip' to follow patterns:
^https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.[0-9]+.[0-9]+/schema.json$
```

`definition.pbir` và `definition.pbism` cũng phải có `$schema` đúng họ của từng
loại tệp. Riêng `report.json` là định dạng PBIR-Legacy do Desktop quản lý và
không có khai báo `$schema` ở cấp gốc.

### Nếu Desktop không mở được `.pbip`

Đây là đường dự phòng, luôn chạy được, đúng `PHASE5.md` §8.3:

1. **Kiểm TMDL trước khi mở Desktop.** Đây là bước rẻ nhất và bắt được gần hết
   lỗi cấu trúc mà không phải nạp lại dữ liệu: cho MCP đọc thẳng thư mục bằng
   `connection_operations → ConnectFolder` với đường dẫn
   `powerbi\ASEAN_Renewables.SemanticModel`. Nó dùng cùng bộ phân tích TMDL của
   Power BI và trả về lỗi cụ thể, ví dụ *“an object-description must be followed
   by the actual object!”* khi một khối `///` bị đặt sau đối tượng thay vì trước.
   Đạt thì phải thấy `tablesLoaded 8 · measuresLoaded 61 · relationshipsLoaded 3`.
2. Nếu vẫn lỗi, mở trực tiếp
   `ASEAN_Renewables.Report\definition.pbir`; Microsoft hỗ trợ `.pbir` làm điểm
   vào và tham chiếu `byPath` sẽ mở luôn semantic model (mô hình ngữ nghĩa).
3. Nếu cả hai điểm vào đều không mở, Power BI Desktop → `Get Data → Text/CSV`,
   nạp đúng bốn tệp từ `output\clean`:
   `fact_energy.csv`, `dim_entity.csv`, `dim_metric.csv`, `dim_year.csv`.
   **Không** dùng cách lấy tự động cả thư mục — danh sách cố định là thứ ngăn tệp
   lạ lọt vào mô hình.
4. Khai kiểu tường minh: `value` là `Decimal Number`, `year` là `Whole Number`,
   các cột cờ `is_*` là `Whole Number`.
5. `Save as` → `ASEAN_Renewables.pbix`, giữ Desktop mở.
6. Báo lại để MCP dựng quan hệ và toàn bộ phép đo từ `DAX_Measures.md`.

## 3. Mô hình dữ liệu

Ba quan hệ chủ động, lọc **một chiều** từ bảng chiều sang fact:

```
DimEntity[entity]      1 → *  FactEnergy[entity]
DimYear[year]          1 → *  FactEnergy[year]
DimMetric[metric_key]  1 → *  FactEnergy[metric_key]
```

Không quan hệ nhiều-nhiều, không lọc hai chiều, không đường lọc mơ hồ — đường lọc
mơ hồ sẽ làm mẫu số xếp hạng phụ thuộc vào việc ô trực quan nào hỏi trước.

Ba bảng chọn **không có quan hệ**: `SelReportYear` (2000–2021, mặc định 2021),
`SelMode` (`RENEWABLE_TOTAL` / `MODERN_WIND_SOLAR`, mặc định tổng tái tạo),
`SelBaseYear` (mặc định 2010). Tách rời là để điều khiển logic DAX mà không phá
quan hệ mô hình và không làm chuỗi thời gian co lại còn một điểm.

### Hợp đồng cột cờ

Ba tập thực thể dùng xuyên suốt được định nghĩa bằng **đúng** ba cột này:

| Tập | Cột | Số dòng |
|---|---|---:|
| Quốc gia/vùng lãnh thổ hiện tại — mẫu số `global_rank` | `DimEntity[is_current_country_or_territory] = 1` | 215 |
| ASEAN-10 cố định — mọi mẫu số khu vực, hạng, tập trung | `DimEntity[is_asean] = 1` | 10 |
| Cửa sổ phân tích chính | `DimYear[is_main_asean_window] = 1` | 22 |

⚠️ `is_aggregate = 0` **không tương đương** `is_current_country_or_territory = 1`.
Nó trả **216** dòng vì còn `USSR` (`entity_type = historical` — không phải thực
thể tổng hợp, nhưng cũng không phải quốc gia hiện tại). Dùng nhầm cột này cho
tiêu chí “không có thực thể tổng hợp trong danh sách nước” sẽ đưa `USSR` vào bộ
lọc quốc gia và làm Gate B2 mâu thuẫn Gate B7.

## 4. Ba quy ước dễ hiểu sai nhất

**Bộ lọc năm nghĩa là “đến năm được chọn”.** KPI và lát cắt dùng đúng năm chọn
(`… @Year`); biểu đồ chuỗi thời gian hiển thị từ 2000 đến năm chọn
(`… ToDate`). Không lọc trực tiếp `DimYear` — làm thế thì chuỗi co lại còn một
điểm.

**Thang lưu trữ khác thang hiển thị.** Trong toàn mô hình chỉ
`Share Electricity Pct` lưu ở thang 0–100. Mọi tỷ lệ còn lại
(`Country Share ASEAN`, `ASEAN Share World`, `Technology Share`, `Top1/Top3
Share`, `HHI`, `Gini`, `YoY`, `CAGR`, `Positive Growth Share`) lưu ở thang 0–1.
Việc ×100 chỉ nằm ở `format_string`. So một measure ratio `0,671023268910` với
đích hiển thị `67,102326891` sẽ lệch `66,43` — đó là sai đơn vị, không phải sai
số làm tròn.

**Quy tắc đủ thành phần co giãn theo phạm vi.** `Required Component Count` =
số thực thể × số chỉ số còn lại sau khi giao chế độ với bộ lọc công nghệ. Nên nó
tự ra 4/4 cho một nước, 40/40 cho tổng hợp ASEAN-10, 2/2 và 20/20 ở chế độ hiện
đại, và 10/10 khi lọc xuống một công nghệ. Viết cứng “4” sẽ làm ô trực quan trả
trống ngay khi người xem lọc một công nghệ.

Ngoại lệ: `Share Electricity Pct` **không** dùng quy tắc này.
`RENEWABLE_TOTAL` lấy nguyên cột nguồn `renewables_share_electricity_pct`
(pass-through 1/1); cộng bốn thành phần cho Việt Nam 2021 ra `42,513379%` thay vì
`42,578747%`, và mô hình còn không có cột tỷ trọng cho NLTT khác.

## 5. Ba trang và phạm vi bộ lọc

| Trang | Nội dung | Lựa chọn quốc gia làm gì |
|---|---|---|
| `01_TongQuan_ASEAN` | V01–V04: KPI khu vực, cơ cấu 4 công nghệ, so hạng hai cách đo, ASEAN trong bối cảnh World | chỉ **tô sáng / so sánh**; KPI khu vực vẫn là ASEAN-10 |
| `02_VietNam_ChuyenSau` | V05–V09: KPI Việt Nam, chuỗi 4 công nghệ, TWh vs % điện, vị thế, bảng theo năm | **khóa cứng ở Việt Nam** |
| `03_SoSanh_ChanDoan` | V10–V14: small multiples, chỉ số hóa, độ trễ gia nhập, tập trung, hệ số công suất | **lọc** biểu đồ cấp nước; mẫu số khu vực vẫn giữ ASEAN-10 |

Năm và chế độ đồng bộ trên cả ba trang. Mọi ô cố ý bỏ qua một bộ lọc phải ghi rõ
phạm vi ngay trên tiêu đề hoặc phụ đề.

Chân trang cố định (measure `Footer Note`) ghi nguồn, cửa sổ 2000–2021, lý do
loại 2022 và ghi chú đã loại thực thể tổng hợp.

## 6. Quy ước trực quan kế thừa Phase 4

| Thành phần | Màu |
|---|---|
| Thủy điện | `#0072B2` |
| Gió | `#009E73` |
| Mặt trời | `#E69F00` |
| NLTT khác | `#CC79A7` |
| Tổng tái tạo | `#374151` |
| Gió + mặt trời · màu nhấn Việt Nam | `#D55E00` |

Không trục kép, không biểu đồ tròn. Màu gắn theo **thực thể**, không đổi theo thứ
hạng. Nhãn trực tiếp chỉ đặt ở điểm cuối hoặc điểm cần nhấn.

Số hiển thị theo quy ước Việt (`1.000` cho hàng nghìn, `0,0` cho thập phân) nhờ
`culture: vi-VN` của mô hình. Việc phân tích CSV được ghim `"en-US"` trong Power
Query nên dấu chấm thập phân trong tệp nguồn vẫn đọc đúng.

## 7. Nghiệm thu

```powershell
python python\05_expected.py     # tính lại đích từ output\clean, không cần Power BI
python python\05_build_pbip.py   # sinh lại PBIP và DAX_Measures.md
python python\05_acceptance.py   # sinh lại 05_acceptance.dax
python python\05_validate.py     # đối chiếu kết quả Power BI với đích
```

Trình tự đầy đủ:

1. `05_expected.py` tính 169 đích từ `output\clean` và đối chiếu ba chiều — với
   các hằng số khóa trong `phase5_contract.py` và với `03_fact_metrics.csv`.
2. Mở `.pbix`, chạy `05_acceptance.dax` qua MCP `dax_query_operations`.
3. Gom kết quả vào `output\stats\05_test_results.tsv` với ba cột `test_id`,
   `actual_value`, `actual_text`.
4. `05_validate.py` ghi `output\stats\05_validation_results.csv`.

Quy tắc đối chiếu: số đếm, hạng, khóa và trạng thái khớp **tuyệt đối**; giá trị số
thô lệch không quá `1e-9` **trên thang lưu trữ**. Thiếu kết quả tính là **lỗi** —
im lặng không phải là đạt.

## 8. Cạm bẫy vận hành khi dùng MCP

- **Lưu `.pbix` trước và sau mỗi lượt MCP ghi.** Không sửa tay song song khi MCP
  đang mở kết nối. Đây là bản sao của bẫy *Navicat giữ `.db`* mà `PLAN.md` đã ghi
  cho Phase 2.
- MCP chỉ làm được **mô hình**. Bộ tool của nó không có gì cho trang, ô trực
  quan, slicer, dấu trang, nút hay chân trang — lớp trình bày dựng trong Desktop.
- Sau mỗi lượt MCP ghi, xuất lại `database_operations → ExportTMDL` và so với
  `DAX_Measures.md`. Chênh lệch nào không có trong nhật ký thay đổi phải giải
  thích được — MCP sửa phép đo mà không để lại vết trong PBIX nhị phân.
- Đăng ký MCP phải ở **scope thư mục đồ án** (`.mcp.json` ở gốc repo). Chỉ đăng
  ký ở scope người dùng thì phiên chạy từ thư mục này sẽ không thấy tool nào.
