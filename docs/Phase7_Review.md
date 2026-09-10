# Phiếu nghiệm thu Phase 7 — Kết luận, đề xuất và bộ hồ sơ nộp

Phase 7 gánh hai việc khác nhau. Một là **mục 1.6** — kết luận và đề xuất, phần cuối
của nội dung phân tích. Hai là **hoàn tất bộ ba tệp nộp** theo yêu cầu định dạng,
vốn chỉ được biết sau khi Phase 6 đã xong và đã đổi khá nhiều thứ.

**Trạng thái tổng thể hiện tại:** `CHỜ NGHIỆM THU`.

## 0. Yêu cầu định dạng nộp và trạng thái từng tệp

| Tệp | Yêu cầu | Sản phẩm | Trạng thái |
|---|---|---|---|
| 1. Báo cáo | dạng slide, tối đa **15 slide nội dung**, 16:9 | `output/slides/ASEAN_Renewables.pptx` — **17 slide** = 15 nội dung + mở đầu + kết thúc | ĐẠT |
| 2. Xử lý dữ liệu | **01 file**, có chú thích từng bước | `output/notebook/ASEAN_Renewables_DataProcessing.ipynb` — 42 ô, tự chứa | ĐẠT |
| 3. Dashboard | Power BI `.pbix` | `powerbi/ASEAN_Renewables.pbix` — **vẫn là bản cũ 71 phép đo** | **CẦN SỬA** |

⚠️ Tệp 3 là khuyết điểm nội dung, không phải thủ tục: bản `.pbix` hiện tại mở ra thì
bảng V12 hiện 70 dòng thay vì 40. Xem `docs/Phase5_Review.md` §5.3. Cách sửa mất
khoảng một phút và **chỉ chủ đồ án làm được**: đóng Desktop **không lưu**, mở
`ASEAN_Renewables.pbip`, Save As `.pbix`.

## 1. Bảng nghiệm thu theo cổng

| Cổng | Nội dung | Bằng chứng | Trạng thái |
|---|---|---|---|
| G1 | Mở rộng hợp đồng cho số liệu 1.6 | 77 claim, `_validate_contract()` tự kiểm | ĐẠT |
| G2 | Kiểm chứng ba chiều | **77/77 `MATCH`** | ĐẠT |
| G3 | Viết mục 1.6 | `BaoCao.md` §1.6.1–§1.6.5 | CHỜ NGHIỆM THU |
| G4 | Mở rộng slide lên đủ 1.1–1.6 | 17 slide, 7 hình | CHỜ NGHIỆM THU |
| G5 | Dựng notebook nộp bài | 42 ô, 31/31 ô có kết quả, 0 lỗi | CHỜ NGHIỆM THU |
| G6 | Tệp `.pbix` hợp lệ | — | **CẦN SỬA** |

## 2. Kiểm định máy chạy được

```powershell
python python\06_verify_findings.py     # 77/77 MATCH
python python\06_build_slides.py        # 17 slide, 7 hình, byte-identical
python python\07_build_notebook.py      # 42 ô, 31 ô có kết quả, 5 biểu đồ
```

- [x] **77/77 claim khớp ba chiều.** Ba mươi claim mới của Phase 7 gồm: sáu nước có
  sản lượng gió bằng 0 năm 2021, ba con số Việt Nam cho đề xuất VN-2, và **21 thống
  kê phân phối** cho mục 1.3.
- [x] Hai định nghĩa dễ sai đã được tính lại đúng: `sd` dùng **`ddof=0`** (độ lệch
  chuẩn tổng thể, không phải mẫu) và `skewness` dùng **`bias=False`** (hiệu chỉnh
  chệch). Chọn sai một trong hai cho ra con số hợp lý chứ không ra lỗi.
- [x] Notebook **tự dựng lại đúng** dữ liệu đã công bố: `fact_energy` 89.075 dòng,
  khoá trùng khớp từng dòng, lệch giá trị lớn nhất `1,1 × 10⁻¹³`, `value_class` khớp
  tuyệt đối, cả ba bảng chiều đúng số dòng. Đây là bằng chứng notebook trung thực
  chứ không phải một bản rút gọn kể lại.
- [x] `assert_self_contained()` chặn `%run`, `import` script của dự án, đọc
  `output/`, dùng `__file__`, và mọi lệnh ghi tệp.
- [x] Slide dựng hai lần cho tệp **giống hệt từng byte**.

### 2.1. Lỗi phát hiện và cách xử lý

**L1 — Notebook mất toàn bộ dấu tiếng Việt.**
*Tái hiện:* tệp nháp phần 4–5 ghi ra có nội dung `M?c 1.3 ? Th?ng k? m? t?`.
*Nguyên nhân:* ghi qua luồng mã hoá mặc định của Windows (cp1252); ký tự không ánh
xạ được bị thay bằng dấu hỏi. Tệp **vẫn decode được bằng UTF-8**, nên không lỗi nào
báo ra — chỉ đọc bằng mắt mới thấy.
*Cách sửa:* ghi lại với `encoding="utf-8"` tường minh, và thêm chốt chặn trong
`07_build_notebook.py`: đếm ký tự ngoài ASCII trong tệp vừa ghi, bằng 0 thì ném lỗi.
*Ghi nhận:* đây đúng là bẫy đã được liệt kê trước khi làm, và vẫn xảy ra. Điều đáng
rút ra là **danh sách rủi ro không tự chặn được rủi ro** — chỉ một phép kiểm chạy
được mới chặn.

**L2 — `nbclient` ném `AttributeError` giữa chừng.**
*Tái hiện:* `AttributeError: 'list' object has no attribute 'strip'` tại
`async_execute_cell`.
*Nguyên nhân:* trường `source` của ô được ghi dưới dạng **danh sách dòng**. Định
dạng `.ipynb` cho phép cả chuỗi lẫn danh sách, nhưng `nbclient` gọi `.strip()`
thẳng lên nó.
*Cách sửa:* ghi `source` là một chuỗi.

**L3 — Sửa docstring làm mất ô đầu tiên của tệp nội dung.**
*Tái hiện:* `AssertionError: so hieu o khong lien tuc: [2, 3, ..., 42]`.
*Nguyên nhân:* dùng `partition('\"\"\"')` hai lần để bóc docstring; lần thứ hai bắt
trúng dấu nháy ba **mở đầu** của ô markdown số 1 chứ không phải dấu đóng docstring.
*Cách sửa:* dựng lại tệp từ nguồn thay vì vá. Lỗi này bị bắt ngay vì `read_cells()`
kiểm số hiệu ô phải liên tục từ 1 — nếu không có phép kiểm đó, notebook sẽ thiếu
phần giới thiệu mà không ai biết.

## 3. Ca người nghiệm thu phải tự đọc

### 3.1. Mục 1.6 trong `BaoCao.md`

- [ ] Năm kết luận, mỗi kết luận có mã claim dẫn chiếu và không vượt quá dữ liệu.
- [ ] Đề xuất viết dạng *"nên xem xét"*, không phải *"nên làm"*.
- [ ] Có tách riêng đề xuất cho Việt Nam và cho khu vực.
- [ ] Mục "không thể đề xuất" liệt kê đủ lý do thiếu dữ liệu nào.
- [ ] Mục "dữ liệu cần bổ sung" nêu rõ bảng nào, khoá ghép nào.

### 3.2. Slide

- [ ] Mở tệp `.pptx`, đếm đúng **17 slide**, khổ 16:9.
- [ ] Đọc **to** tiêu đề từng slide — mỗi slide một thông điệp, một câu.
- [ ] Slide 7 (thống kê mô tả) đọc được: bảng ba biến thể lọc và dòng phân vị.
- [ ] Slide 13 (dashboard) — **cần thay khung giữ chỗ bằng ảnh chụp thật**.
- [ ] Không câu nào giải thích nguyên nhân, vì dữ liệu không có biến chính sách.

### 3.3. Notebook

- [ ] Mở bằng Jupyter, VS Code hoặc Colab — đọc được, có đủ kết quả và biểu đồ.
- [ ] Chú thích tiếng Việt hiển thị đúng dấu ở mọi ô.
- [ ] *Restart Kernel → Run All* chạy lại sạch từ đầu (chạy tại thư mục gốc dự án).
- [ ] Có cả Python lẫn SQL trong cùng một tệp.

### 3.4. Dashboard

- [ ] Đã tái sinh `.pbix` từ `.pbip`; mã băm khác `597b0a61…`.
- [ ] Bảng V12 hiện **40 dòng**, không phải 70.

## 4. Bằng chứng phát hành

| Hạng mục | Giá trị |
|---|---|
| Số claim đạt / tổng | **77 / 77** |
| Slide | 17 (15 nội dung), 7 hình, 16:9 |
| Notebook | 42 ô · 31 ô có kết quả · 0 lỗi · 5 biểu đồ · 0,55 MB |
| 17 CSV nguồn không đổi | băm gộp `3092712a0f05fb09ee7e47463da69daf1aeba74c0da3f65c7eb35fb9dc602df9` |
| Dấu vân tay đầu vào Phase 2 | `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10` |
| SHA-256 `.pbix` | ⚠️ `597b0a61…` — bản cũ, **chưa hợp lệ** |

## 5. Ký nhận tổng thể

| Trường | Nội dung |
|---|---|
| Kết quả tổng thể | CHỜ NGHIỆM THU |
| Người nghiệm thu | |
| Ngày nghiệm thu | |
| Phiên bản phương pháp | `phase6_v1` |
| Ghi chú cuối | |
