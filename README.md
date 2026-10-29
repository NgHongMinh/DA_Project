# Phân tích năng lượng tái tạo — Việt Nam và Đông Nam Á (2000–2021)

Đồ án cuối môn Phân tích dữ liệu. Dự án trả lời câu hỏi:

> **Đông Nam Á đã chuyển dịch sang năng lượng tái tạo đến đâu trong giai đoạn 2000–2021, và Việt Nam đứng ở vị trí nào trong quá trình đó?**

- **Nguồn dữ liệu:** bộ *Renewable Energy World Wide* của Our World in Data (tổng hợp từ Ember và BP Statistical Review) — 17 file CSV trong [`archive/`](archive/), 256 thực thể, khoảng năm 1965–2022.
- **Phạm vi phân tích:** 10 nước ASEAN × 22 năm (2000–2021), bốn công nghệ (thuỷ điện, gió, mặt trời, nguồn tái tạo khác). Năm 2022 bị loại vì không nước ASEAN nào có dữ liệu.
- **Công cụ:** Python · SQLite (SQL) · Power BI.

Báo cáo đầy đủ: [`docs/BaoCao.md`](docs/BaoCao.md).

---

## Câu hỏi phân tích

"Chuyển dịch" được đo theo hai nghĩa và so sánh với nhau: **tổng năng lượng tái tạo** (gồm thuỷ điện) và **năng lượng tái tạo hiện đại** (chỉ gió + mặt trời). Sự khác biệt giữa hai cách đo là một phần của câu trả lời.

| # | Câu hỏi con |
|---|---|
| Q1 | Quy mô và tốc độ: khu vực đã đi được bao xa? |
| Q2 | Cơ cấu: tăng trưởng đến từ công nghệ nào? |
| Q3 | Xếp hạng: thứ tự các nước thay đổi thế nào khi đổi cách đo? |
| Q4 | Việt Nam: quỹ đạo riêng khác gì phần còn lại của khu vực? |
| Q5 | Sản lượng (TWh) hay tỷ trọng (%): hai thước đo có kể cùng một câu chuyện không? |
| Q6 | Mức tập trung: tăng trưởng do vài nước hay đến từ số đông? |

## Kết quả chính

1. **Quy mô tăng gần 4 lần, vị thế gần như không đổi.** Sản lượng tái tạo ASEAN-10 tăng từ 72,801 lên 289,656 TWh (gấp 3,98 lần), nhưng tỷ trọng trong tổng thế giới chỉ từ 2,5504% lên 3,6735% (+1,12 điểm phần trăm).
2. **Cơ cấu năm 2021 vẫn là thuỷ điện.** Thuỷ điện chiếm 64,07%; gió + mặt trời chỉ 14,75%, xuất phát từ đúng 0 TWh năm 2000.
3. **Đà chuyển dịch tập trung vào rất ít nước.** Ba nước dẫn đầu giữ 92,25% lượng gió và mặt trời của khối; HHI (chỉ số tập trung Herfindahl–Hirschman) tăng từ 0,2079 lên 0,4804, Gini từ 0,5292 lên 0,7713.
4. **Việt Nam là động lực chính ở nhóm nguồn hiện đại.** Năm 2021 Việt Nam chiếm 65,90% gió + mặt trời của ASEAN và đóng góp 65,99% mức tăng giai đoạn 2010–2021.
5. **Xếp hạng phụ thuộc định nghĩa.** Đổi thước đo trong cùng năm 2021: Singapore tăng 4 bậc, Indonesia giảm 4, Lào giảm 5; Việt Nam giữ hạng 1 ở cả hai cách đo.

![Bối cảnh ASEAN trong thế giới](output/charts/04_01_global_asean_context.png)
![Cơ cấu công nghệ theo nước, 2021](output/charts/04_03_asean_country_mix_2021.png)

Đề xuất cho Việt Nam và khu vực, cùng các giới hạn của dữ liệu, nằm ở mục 1.6 của [báo cáo](docs/BaoCao.md).

## Đối chiếu yêu cầu đề bài

Đề bài yêu cầu sáu nội dung (1.1–1.6) và dùng ít nhất 2 trong 3 công cụ SQL, Power BI, Python. Dự án dùng cả 3.

| Yêu cầu | Sản phẩm |
|---|---|
| 1.1 Xác định vấn đề, mục tiêu | [`docs/BaoCao.md`](docs/BaoCao.md) §1.1 · kết quả khảo sát dữ liệu [`output/stats/00_phase1_summary.txt`](output/stats/00_phase1_summary.txt) |
| 1.2 Tiền xử lý dữ liệu | Notebook [`output/notebook/ASEAN_Renewables_DataProcessing.ipynb`](output/notebook/ASEAN_Renewables_DataProcessing.ipynb) · bảng sạch [`output/clean/`](output/clean/) · CSDL [`sql/renewables.db`](sql/) |
| 1.3 Phân tích mô tả | [`output/stats/`](output/stats/) · truy vấn SQL [`sql/03_analysis.sql`](sql/03_analysis.sql) |
| 1.4 Trực quan hoá | 13 biểu đồ trong [`output/charts/`](output/charts/) |
| 1.5a Diễn giải kết quả | [`docs/BaoCao.md`](docs/BaoCao.md) §1.5a |
| 1.5b Slide | [`output/slides/ASEAN_Renewables.pptx`](output/slides/ASEAN_Renewables.pptx) (17 slide) |
| 1.5c Dashboard | [`powerbi/ASEAN_Renewables.pbix`](powerbi/) (3 trang) · dự án dạng văn bản PBIP · danh mục phép đo [`powerbi/DAX_Measures.md`](powerbi/DAX_Measures.md) |
| 1.6 Kết luận và đề xuất | [`docs/BaoCao.md`](docs/BaoCao.md) §1.6 |

## Vai trò từng công cụ

| Công cụ | Dùng để |
|---|---|
| **Python** (pandas, matplotlib, seaborn, scipy) | Khảo sát và làm sạch dữ liệu, dựng mô hình tidy-long (dạng dài, mỗi dòng một quan sát), thống kê mô tả, 13 biểu đồ, sinh slide và notebook |
| **SQLite** | Lưu mô hình dữ liệu sạch có khoá chính/khoá ngoại; truy vấn kiểm định và phân tích bằng window functions (hàm cửa sổ — tính xếp hạng, tăng trưởng theo năm) |
| **Power BI** | Dashboard 3 trang trên mô hình sao (star schema) đọc từ `output/clean/*.csv`, phép đo viết bằng DAX |

## Cấu trúc thư mục

```
archive/            17 CSV gốc (chỉ đọc, không sửa)
python/             Toàn bộ script xử lý, đánh số theo phase (00–08)
sql/                Schema, kiểm định, truy vấn phân tích và renewables.db
output/
  clean/            7 bảng sạch (dim_*, fact_energy, audit)
  stats/            Bảng thống kê, kết quả kiểm định, bằng chứng cho từng phát hiện
  charts/           13 biểu đồ PNG
  notebook/         Notebook tiền xử lý (đã chạy sẵn, kèm kết quả)
  slides/           Bản trình chiếu .pptx
powerbi/            Dashboard .pbix + dự án PBIP (TMDL) + README riêng
docs/               Báo cáo phân tích đầy đủ (BaoCao.md)
```

## Chạy lại dự án

Yêu cầu: Python 3 (có sẵn module `sqlite3`), Power BI Desktop (chỉ cần nếu muốn mở dashboard).

```powershell
python -m pip install -r python\requirements.txt
```

> `lxml` được ghim ở `5.3.0` vì bản 6.x bị chính sách Application Control của Windows chặn nạp DLL trên máy thực hiện.

Chạy từ thư mục gốc của repo, theo thứ tự:

| Bước | Lệnh | Kết quả |
|---|---|---|
| 0 | `python python\00_check_env.py` | Kiểm tra môi trường, thư viện, phiên bản SQLite |
| 1 | `python python\01_profile.py` | Khảo sát dữ liệu gốc → `output/stats/00_*`, `01_*` |
| 2 | `python python\02_clean_build.py` | Làm sạch, dựng `output/clean/` và `sql/renewables.db` |
| 3 | `python python\03_descriptive.py` | Thống kê mô tả → `output/stats/03_*` |
| 4 | `python python\04_charts.py` | 13 biểu đồ → `output/charts/` |
| 5 | `python python\05_build_pbip.py`, `05_build_report.py`, `05_validate.py` | Dựng và nghiệm thu dự án Power BI — xem [`powerbi/README.md`](powerbi/README.md) |
| 6 | `python python\06_verify_findings.py`, `06_build_slides.py` | Đối chiếu số liệu các phát hiện, sinh slide |
| 7 | `python python\07_build_notebook.py` | Dựng và chạy notebook |
| 8 | `python python\08_verify_sql.py --final` | Nghiệm thu các truy vấn SQL |
| — | `python python\verify_deliverables.py` | Đối chiếu lần cuối nội dung các sản phẩm bàn giao |

Chạy riêng một file SQL: `python python\run_sql.py sql\03_analysis.sql`.

Mọi con số trên slide và trong notebook đều đọc từ tập số đã kiểm chứng (`python/phase6_contract.py`); script từ chối ghi file nếu xuất hiện con số không truy được nguồn.

## Giới hạn

Bộ dữ liệu mô tả *điều gì đã xảy ra*, không giải thích *vì sao*. Không có dữ liệu về chi phí (LCOE), chính sách, phát thải, dân số/GDP; gió không tách trên bờ/ngoài khơi; công suất lắp đặt chỉ phủ 2–4/10 nước ASEAN. Danh sách đầy đủ ở [báo cáo §1.1](docs/BaoCao.md) và §1.6.3.

---

**Tác giả:** NgHongMinh
