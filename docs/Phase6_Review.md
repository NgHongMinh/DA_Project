# Phiếu nghiệm thu Phase 6 — Diễn giải và slide

Phiếu này bao phủ hai lớp mà `PHASE6.md` §E6 đòi: lớp **con số** (mỗi số có truy được
về nguồn không) và lớp **câu chữ** (câu phát biểu có nằm trong phạm vi con số cho phép
không). Kiểm định số không thay thế việc đọc câu; ngược lại, một câu nghe xuôi tai
không chứng minh được con số đứng sau nó đúng.

**Trạng thái tổng thể hiện tại:** `CHỜ NGHIỆM THU`.

Trạng thái hợp lệ cho mỗi mục: `CHỜ NGHIỆM THU` · `CẦN SỬA` (ghi rõ lỗi và cách tái
hiện) · `ĐẠT`.

## 0. Ghi chú về cổng vào E0

`PHASE6.md` §E0 đòi Phase 5 đã ký. Phase 5 được ký ngày 2026-09-10 ở mức
**`ĐẠT — lớp định lượng`**, không phải `ĐẠT` toàn phần: 14 mục việc tay trong Desktop
và 32 ca kiểm tương tác được chấp nhận không đo.

Hệ quả trực tiếp lên Phase 6: mọi câu nói về dashboard trong mục 1.5c và trên slide
phải nằm trong phạm vi đã chứng minh. Cụ thể, **không** được phát biểu rằng dashboard
đã kiểm tính nhất quán khi đổi bộ lọc — điều đó thuộc lớp chưa nghiệm thu.

- [x] `Phase5_Review.md` §5 có người ký và ngày.
- [x] Mục 1.5c của `BaoCao.md` ghi rõ giới hạn, không khẳng định quá phạm vi đã ký.

## 1. Bảng nghiệm thu theo cổng

| Cổng | Nội dung | Ai làm | Bằng chứng | Trạng thái |
|---|---|---|---|---|
| E0 | Phase 5 đã đóng | Người | `Phase5_Review.md` §5 | ĐẠT |
| E1 | Khoá hợp đồng | Máy | `phase6_contract.py` tự kiểm khi import | ĐẠT |
| E2 | Chọn 5 phát hiện | Người | `PHASE6.md` §E2, tiêu chí đặt trước | ĐẠT |
| E3 | Kiểm chứng lại từng con số | Máy | **47/47 `MATCH`** ba chiều | ĐẠT |
| E4 | Viết mục 1.5a | Người | `BaoCao.md` §1.5a | CHỜ NGHIỆM THU |
| E5 | Dựng slide | Máy | 11 slide, 6 hình, byte-identical | CHỜ NGHIỆM THU |
| E6 | Nghiệm thu tổng thể | Người | phiếu này | CHỜ NGHIỆM THU |

## 2. Kiểm định máy chạy được

Hai lệnh dưới đây chạy độc lập, không cần Power BI, và là điều kiện cần của E1–E5:

```powershell
python python\06_verify_findings.py
python python\06_build_slides.py
```

- [x] `phase6_contract.py` import được; `_validate_contract()` kiểm **chín nhóm quan
  hệ** giữa các số chứ không lặp lại chính các số: bốn công nghệ cộng lại bằng tổng
  khu vực · gió + mặt trời bằng chế độ hiện đại · tỷ trọng Việt Nam bằng top-1 share ·
  tỷ trọng suy ra được từ hai con số TWh · top-1 ≤ top-3 ≤ 1 · chế độ hiện đại tập
  trung hơn trên cả ba chỉ số · độ tăng hạng bằng hiệu hai hạng · hạng không trùng và
  nằm trong 1–10 · mọi tỷ lệ nằm trong `[0, 1]`.
- [x] `06_verify_findings.py` thu **ba** cách đọc độc lập cho từng claim và trả
  **47/47 `MATCH`**, mã thoát 0.
- [x] Nhánh thứ ba thực sự tính chứ không vọng lại: **17/47** claim có chênh lệch khác
  0 giữa ba nguồn, lớn nhất `9,095 × 10⁻¹³`, dưới dung sai `10⁻⁹`. Đây đúng dạng nhiễu
  kết hợp dấu phẩy động khi cộng theo thứ tự khác — nếu nhánh ba đọc lại bảng thay vì
  tự tính thì mọi delta sẽ bằng 0 tuyệt đối.
- [x] `06_build_slides.py` dựng 11 slide, 6 hình, và **từ chối ghi tệp** nếu còn một
  con số không truy được về hợp đồng.
- [x] Dựng hai lần cho tệp **giống hệt từng byte**: `44568cb72f6bc7919aa3ec4dba1d2d54bc18e8966d3f3524d3a7aa3333781991`.

### 2.1. Lỗi phát hiện và cách xử lý trong lượt này

**L1 — `lxml` 6.1.3 bị chính sách máy chặn nạp DLL.**
*Tái hiện:* `python -m pip install python-pptx` rồi `import pptx` →
`ImportError: DLL load failed while importing etree: An Application Control policy has blocked this file`.
*Nguyên nhân:* máy áp Application Control; DLL biên dịch của `lxml` 6.1.3 không qua
được chính sách. Không liên quan quyền quản trị — gói cài được, chỉ không nạp được.
*Cách sửa:* ghim `lxml==5.3.0`, bản này nạp bình thường. Dòng ghim đặt **trước**
`python-pptx` trong `requirements.txt` vì `python-pptx` kéo `lxml` về như phụ thuộc và
sẽ lấy bản mới nhất nếu không bị chặn trước.

**L2 — Bộ chặn số lạ bắt nhầm tên tệp và số hiệu mục.**
*Tái hiện:* lần dựng đầu trả `FAIL` với `slide 4: '00'`, `slide 5: '02'`, `slide 11: '1.6'`.
*Nguyên nhân:* hàm quét bắt mọi chuỗi số trong chữ trên slide, kể cả số nằm trong tên
tệp ở chân trang (`00_phase1_summary.txt`, `02_validate.sql`) và tham chiếu mục `1.6`.
*Cách sửa:* lọc tên tệp và số hiệu mục **trước** khi quét, thay vì nới danh sách cho
phép. Nới danh sách sẽ làm bộ chặn phình ra đến mức mất tác dụng — đúng cái bẫy khiến
một tiêu chí trở thành hình thức.

**L3 — Khoá tra cứu dòng World sai `subject_key`.**
*Tái hiện:* lần chạy đầu của `06_verify_findings.py` trả `45/47`, hai claim World báo
`0 dòng khớp cho khoá`.
*Nguyên nhân:* hợp đồng ghi `subject_key = "World"`, nhưng `03_fact_metrics.csv` dùng
`WORLD_REPORTED` cho cả `subject_key` lẫn `comparison_scope`.
*Cách sửa:* sửa khoá trong hợp đồng. Đáng chú ý là lỗi này **báo ngay** thay vì âm
thầm trả nhầm dòng, vì `lookup()` từ chối khi số dòng khớp khác đúng 1 — nếu nó lấy
dòng đầu tiên thì con số sai đã lên slide mà không ai biết.

## 3. Ca người nghiệm thu phải tự đọc

Đánh dấu sau khi thực sự mở tệp `.pptx` và đọc, không suy ra từ kiểm định số.

### 3.1. Một slide, một thông điệp

Cách kiểm: đọc **to** tiêu đề từng slide. Slide nào cần hai câu mới nói hết là slide
đang gánh hai thông điệp và phải tách, không phải viết lại cho gọn.

- [ ] Slide 1 — móc mở đầu nêu được một câu hỏi và một con số, không nhồi thêm.
- [ ] Slide 2 — câu hỏi trung tâm đọc lên là hiểu, sáu câu hỏi con không trùng nhau.
- [ ] Slide 3 — nói về **giới hạn**, không lẫn sang phát hiện.
- [ ] Slide 4 — bốn khuyết điểm là khuyết điểm của **dữ liệu gốc**, không phải của cách làm.
- [ ] Slide 5 — nói về **chứng minh**, không chỉ liệt kê việc đã làm.
- [ ] Slide 6–10 — mỗi slide đúng một phát hiện, tiêu đề phát biểu được thành một câu.
- [ ] Slide 11 — chỉ mở hướng, **không** chốt kết luận.

### 3.2. Không phát biểu quá phạm vi dữ liệu

Đây là loại lỗi mà Gate E3 **không** bắt được: con số đúng, câu sai.

- [ ] Không câu nào giải thích **nguyên nhân** — bộ dữ liệu không có biến chính sách,
  giá thành hay cơ chế khuyến khích.
- [ ] Không câu nào nói Việt Nam "dẫn đầu chuyển dịch năng lượng" — dữ liệu chỉ cho
  phép nói về **tỷ trọng sản lượng**.
- [ ] Không câu nào suy rộng hệ số công suất thành kết luận về **hiệu quả kỹ thuật**.
- [ ] Không câu nào về dashboard vượt quá phạm vi Phase 5 đã ký.
- [ ] Slide 7 ghi rõ tăng trưởng 2000–2021 của gió + mặt trời **không tính được** vì
  mẫu số bằng 0, thay vì bỏ trống không giải thích.

### 3.3. Đọc số

- [ ] Mọi số theo quy ước Việt: `1.000` hàng nghìn, `0,0` thập phân — đồng bộ với 13
  PNG sau bản sửa L1 của Phase 4.
- [ ] Không ô nào hiện `NaN`, vô hạn, hay số `0` sinh ra từ dữ liệu thiếu.
- [ ] Tỷ lệ hiển thị dạng phần trăm có dấu `%`; HHI và Gini **không** có dấu `%` —
  hai nhóm này ở hai thang khác nhau.

### 3.4. Bố cục và hình

- [ ] Sáu hình đều hiện đủ, không bị cắt, không tràn khung.
- [ ] Chữ không chồng lên hình ở bất kỳ slide nào.
- [ ] Chân trang có nguồn, phạm vi ASEAN-10, cửa sổ 2000–2021 và ghi chú loại năm 2022.
- [ ] Mở được trên máy khác mà không báo thiếu phông; nếu thiếu `Segoe UI` thì phông
  thay thế vẫn đọc được.

## 4. Đối chiếu kiểm định tự động

Điều kiện cần, **không** thay thế mục 3.

- [x] `06_verify_findings.py` → `PASS | 47/47 claim khớp ba chiều | 7 phát hiện`.
- [x] `06_build_slides.py` → `PASS | 11 slide | 6 hình | 47 claim khả dụng`.
- [x] `03_fact_metrics.csv` đủ **18.926** dòng và mọi dòng mang dấu vân tay
  `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10`.
- [x] `method_version = phase6_v1` nhất quán giữa hợp đồng, bảng chứng cứ và siêu dữ
  liệu của tệp `.pptx`.

## 5. Ký nhận tổng thể

Chỉ điền khi E0–E5 đều `ĐẠT` và mọi ô mục 3 đã được đọc.

| Trường | Nội dung |
|---|---|
| Kết quả tổng thể | CHỜ NGHIỆM THU |
| Người nghiệm thu | |
| Ngày nghiệm thu | |
| Phiên bản phương pháp | `phase6_v1` |
| SHA-256 `ASEAN_Renewables.pptx` | `44568cb72f6bc7919aa3ec4dba1d2d54bc18e8966d3f3524d3a7aa3333781991` |
| Số claim đạt / tổng | 47 / 47 |
| Ghi chú cuối | |

Sau khi ký mới được cập nhật Phase 6 trong `PLAN.md` thành “ĐÃ HOÀN THÀNH” và mở
Phase 7 — không phải trước đó.
