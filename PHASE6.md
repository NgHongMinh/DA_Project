# PHASE 6 — Diễn giải và trình bày *(yêu cầu 1.5a, 1.5b)*

Phase 1–5 đã trả lời được câu hỏi. Phase 6 làm một việc khác hẳn: **kể lại** câu
trả lời đó thành một mạch lập luận mà người nghe theo được từ đầu đến cuối.

Đây là chỗ dễ mất điểm nhất của một đồ án đã làm tốt phần kỹ thuật, vì cám dỗ tự
nhiên là trình bày theo **trình tự công việc** ("tôi đã dùng pandas, rồi tôi viết
SQL, rồi tôi dựng dashboard"). Người nghe không quan tâm thứ tự ấy. Họ quan tâm:
câu hỏi là gì, dữ liệu có đáng tin không, và rốt cuộc câu trả lời là gì.

## Phạm vi

| Mục | Nội dung | Đầu ra |
|---|---|---|
| 1.5a | Phân tích kết quả để đưa ra kết luận có ý nghĩa | mục 1.5a của `docs/BaoCao.md` |
| 1.5b | Slide trình bày, **bao gồm biểu đồ và đồ thị minh hoạ** | `output/slides/ASEAN_Renewables.pptx` |

Kết luận và đề xuất đầy đủ **không** thuộc Phase 6 — đó là mục 1.6 và Phase 7.
Slide cuối chỉ mở hướng, không chốt.

## Cổng E0 – E6

---

### E0 — Điều kiện vào

**Làm gì.** Xác nhận Phase 5 đã ký trong `docs/Phase5_Review.md` §5.

**Vì sao.** Phase 6 dẫn chiếu tới dashboard ở mục 1.5c. Nếu Phase 5 còn treo thì
không biết được cái gì trong đó đã chứng minh và cái gì chưa, nên không viết được
câu nào về nó mà không đoán.

**Gate E0.**
- [x] `Phase5_Review.md` §5 có người ký và ngày.
- [x] Phạm vi đã ký được ghi rõ — Phase 5 đóng ở mức `ĐẠT — lớp định lượng`, lớp
  tương tác chưa nghiệm thu. Mọi câu trong 1.5a và trên slide nói về dashboard
  phải nằm trong phạm vi đó.

---

### E1 — Khoá hợp đồng

**Làm gì.** Dựng `python/phase6_contract.py`: mỗi con số sắp lên báo cáo hoặc lên
slide là một `Claim` có mã, câu phát biểu tiếng Việt, giá trị, đơn vị, khoá tra cứu
vào `03_fact_metrics.csv`, và tên nhánh tính lại độc lập.

**Vì sao.** Không có hợp đồng thì "con số trên slide" là một khái niệm mờ — không
đếm được, không kiểm được. Có hợp đồng thì nó thành một tập hữu hạn có mã, và câu
hỏi "mọi con số đã truy vết chưa" trở thành một phép so tập hợp.

`_validate_contract()` chạy lúc import và kiểm các **quan hệ** giữa các số, không
lặp lại chính các số đó: bốn công nghệ cộng lại phải bằng tổng khu vực · gió + mặt
trời phải bằng chế độ hiện đại · tỷ trọng Việt Nam phải bằng top-1 share vì Việt Nam
hạng 1 · độ tăng hạng phải bằng hiệu hai hạng · chế độ hiện đại phải tập trung hơn
trên cả ba chỉ số, vì **đó chính là nội dung P3-04**.

**Gate E1.**
- [x] `phase6_contract.py` import được, `_validate_contract()` không ném lỗi.
- [x] Mọi `claim_id` duy nhất; mọi claim có nhánh tính lại.
- [x] Mọi claim đơn vị `ratio` nằm trong `[0, 1]` — chốt chặn bẫy lệch thang ×100.

---

### E2 — Chọn phát hiện

**Làm gì.** Đọc lại `docs/NhatKyPhanTich.md` (34 phát hiện có mã), chọn 4–5 phát
hiện mạnh nhất làm xương sống.

**Vì sao.** Nhật ký ghi mọi thứ tìm được; bài trình bày chỉ chứa được vài thứ. Chọn
là hành vi phân tích, và tiêu chí phải đặt **trước** khi chọn để khỏi chọn theo cảm
tính rồi hợp lý hoá sau.

**Tiêu chí chọn.** Mỗi phát hiện phải:
1. trả lời trực tiếp câu hỏi trung tâm;
2. có con số truy được về một bảng trong `output/stats/`;
3. có ít nhất một PNG đã nghiệm thu ở Phase 4;
4. không trùng thông điệp với phát hiện khác.

**Đã chọn — bộ trả lời câu hỏi trung tâm:**

| # | Mã | Thông điệp | Hình |
|---|---|---|---|
| 1 | P3-01 | Quy mô tăng mạnh, chỗ đứng trên thế giới gần như không đổi | C01 |
| 2 | P3-02 + P3-03 | Gió và mặt trời đi lên từ nền đúng bằng 0; thuỷ điện vẫn lớn nhất | C02 |
| 3 | P3-06 | Đổi cách đo là đổi thứ hạng | C04 |
| 4 | P3-07 + P3-09 | Việt Nam nắm hai phần ba lượng gió + mặt trời và hai phần ba phần tăng | C07, C09 |
| 5 | P3-04 | Đà tăng tập trung vào rất ít nước | C12 |

Mạch của bộ này đi từ **khu vực → công nghệ → cách đo → Việt Nam → mức tập trung**,
tức là thu hẹp dần đúng theo câu hỏi trung tâm: *Đông Nam Á chuyển dịch đến đâu, và
Việt Nam đứng ở đâu trong đó.*

**Gate E2.**
- [x] Đúng 5 phát hiện, mỗi phát hiện có thông điệp phát biểu được thành **một** câu.
- [x] Mỗi phát hiện có ít nhất một PNG.
- [x] Tiêu chí chọn ghi ra được, kiểm lại được.

---

### E3 — Kiểm chứng lại từng con số

**Làm gì.** `python/06_verify_findings.py` thu **ba** cách đọc độc lập cho mỗi claim
rồi từ chối công bố nếu bất kỳ cặp nào lệch quá dung sai:

1. hằng số chép tay trong `phase6_contract.py`;
2. tra `output/stats/03_fact_metrics.csv` theo khoá;
3. **tính lại chỉ từ `output/clean/*.csv`**, không đọc hai nguồn kia.

**Vì sao.** `docs/NhatKyPhanTich.md` dòng 13 tự ràng buộc: *"mọi con số đưa vào
BaoCao.md phải tính lại từ nguồn, không chép từ đây"*. Nhật ký là ghi chép tại thời
điểm phát hiện; đến lúc lên slide thì đã có ba phase dựng lại bên dưới nó.

Nhánh thứ ba mới là điểm mấu chốt. Nhánh 1 và 2 có thể khớp nhau **chỉ vì** hằng số
được chép ra từ bảng — khớp kiểu đó không chứng minh gì. Nhánh 3 dựng lại panel từ
bảng dữ kiện và tính lại phép tổng hợp, nên khớp nghĩa là con số sống sót qua một
đường đi độc lập.

**Ba định nghĩa phải lấy đúng, vì sai thì ra số hợp lý chứ không ra lỗi:**

- `RENEWABLE_TOTAL` cộng bốn công nghệ với `min_count=4` — thiếu một thành phần thì
  là `NaN`, **không** phải tổng một phần. Đây là lý do mẫu số hạng toàn cầu là 205
  chứ không phải 215.
- `MODERN_WIND_SOLAR` làm tương tự trên gió và mặt trời với `min_count=2` → 209.
- Xếp hạng sụp về "không xác định" khi toàn bộ phạm vi cộng lại bằng 0 — đúng trường
  hợp chế độ hiện đại năm 2000, và là lý do ô hạng ở đó phải **để trống** thay vì
  hiện `1`.

**Bẫy thang đo.** Chỉ `share_electricity_pct` ở thang 0–100; mọi tỷ lệ khác ở thang
0–1. So `0,671023268910` với `67,102326891` lệch 66,43 — đó là **lỗi đơn vị** đội lốt
sai số làm tròn.

**Đầu ra.** `output/stats/06_finding_evidence.csv`, mỗi dòng một claim với
`source_locator` là khoá dòng cụ thể — không phải "xem workbook Phase 3".

**Gate E3.**
- [x] **47/47** claim có `status = MATCH`; script trả mã thoát 0.
- [x] Delta lớn nhất giữa ba nguồn là `9,1e-13`, dưới dung sai `1e-9` — đúng dạng
  nhiễu kết hợp dấu phẩy động, xác nhận nhánh 3 thực sự tính chứ không vọng lại.
- [x] `03_fact_metrics.csv` đủ 18.926 dòng và khớp dấu vân tay `64e1cc7d…`.

---

### E4 — Viết mục 1.5a

**Làm gì.** Mỗi phát hiện = **tiêu đề + con số + biểu đồ minh hoạ + diễn giải**.

**Vì sao.** Bốn thành phần này là bốn câu hỏi mà người đọc sẽ hỏi theo đúng thứ tự
đó: *chuyện gì · bao nhiêu · cho tôi xem · thế thì sao*. Thiếu thành phần thứ tư thì
đó là báo cáo số liệu, không phải phân tích.

**Gate E4.**
- [ ] Mục 1.5a có đủ 5 phát hiện, mỗi phát hiện đủ bốn thành phần.
- [ ] Mọi con số trong 1.5a có `claim_id` khớp một dòng `MATCH` của
  `06_finding_evidence.csv`.
- [ ] Phụ lục truy vết được cập nhật.

---

### E5 — Dựng slide

**Làm gì.** `python/06_build_slides.py` → `output/slides/ASEAN_Renewables.pptx`,
khổ 16:9, 11 slide.

**Vì sao dựng bằng script.** Cả đồ án theo một nếp: 13 PNG do `04_charts.py` sinh,
PBIP do `05_build_pbip.py` sinh. Slide làm tay sẽ là sản phẩm duy nhất không tái lập
được, và cũng là sản phẩm duy nhất mà tiêu chí "mỗi con số truy được về một bảng"
phải kiểm bằng mắt. Sinh bằng script thì mỗi con số trên slide lấy trực tiếp từ
`phase6_contract.py`, tức là từ chính tập đã qua Gate E3.

**Mạch 11 slide.**

| # | Slide | Nguyên liệu |
|---|---|---|
| 1 | Móc mở đầu — một câu hỏi, một con số | |
| 2 | Câu hỏi trung tâm và sáu câu hỏi con | `BaoCao.md` §1.1 |
| 3 | Dữ liệu **không** trả lời được những gì | `BaoCao.md` §1.1 |
| 4 | **Khuyết điểm dữ liệu phát hiện được** | P1-01 · P1-02 · P1-06 · P1-08 · P1-12 |
| 5 | **Cách làm sạch và chứng minh làm sạch đúng** | P2-05 · P2-06 |
| 6–10 | Năm phát hiện của E2, mỗi slide một hình | C01 · C02 · C04 · C07 · C12 |
| 11 | Hướng kết luận và dữ liệu cần bổ sung | *(kết luận đầy đủ là Phase 7)* |

**Cặp slide 4 + 5 là chỗ tạo khác biệt lớn nhất.** Bài trung bình trình bày dữ liệu
như thể nó sạch sẵn. Nói được "dữ liệu có bốn khuyết điểm cụ thể, đây là cách tôi
phát hiện, đây là cách tôi chứng minh đã xử lý đúng" là thứ phân biệt người đã làm
với người đã hiểu.

**Ràng buộc từ đề bài.** `note.txt` dòng 10 đòi slide **bao gồm biểu đồ và đồ thị
minh hoạ** — không được toàn chữ. 13 PNG có sẵn ở 2.400 × 1.350 px, đúng 16:9.

**Gate E5.**
- [ ] Đủ 11 slide; ít nhất 6 slide mang hình.
- [ ] Mỗi slide **một** thông điệp phát biểu được thành một câu.
- [ ] Mọi con số trên slide đến từ `phase6_contract.py`, không viết cứng trong mã
  dựng slide.
- [ ] Dựng hai lần cho cùng nội dung.
- [ ] Số theo quy ước Việt: `1.000` hàng nghìn, `0,0` thập phân — đồng bộ với 13 PNG
  sau bản sửa L1 của Phase 4.

---

### E6 — Nghiệm thu

**Làm gì.** `docs/Phase6_Review.md` theo khuôn `Phase4_Review.md`.

**Vì sao.** Kiểm định số chứng minh con số đúng; nó không chứng minh **câu** đúng.
Một slide có thể mang con số đã qua Gate E3 mà vẫn phát biểu quá lời — ví dụ nói
"Việt Nam dẫn đầu chuyển dịch năng lượng ASEAN" trong khi dữ liệu chỉ cho phép nói
"Việt Nam chiếm hai phần ba sản lượng gió và mặt trời của ASEAN".

**Cách kiểm hiệu quả nhất:** đọc **to** từng slide. Slide nào cần hai câu mới nói
hết là slide đang gánh hai thông điệp, và nó phải được tách chứ không phải viết lại
cho gọn.

**Gate E6.**
- [ ] Mọi slide đã đọc to và phát biểu được thành một câu.
- [ ] Không câu nào vượt quá phạm vi dữ liệu.
- [ ] Không slide nào chốt kết luận thuộc Phase 7.
- [ ] Phiếu có người ký và ngày.

---

## Rủi ro riêng của Phase 6

| Rủi ro | Hậu quả | Chặn ở đâu |
|---|---|---|
| Chép số từ `NhatKyPhanTich.md` sang slide | Vi phạm ràng buộc dòng 13 của chính nhật ký; số có thể đã cũ sau ba lần dựng lại | E3, ba nhánh độc lập |
| Nhầm thang `ratio` (0–1) với `pct` (0–100) | Lệch ×100 trông y hệt sai số làm tròn | E1 chốt miền, E3 so trên thang lưu trữ |
| Viết cứng số trong `06_build_slides.py` | Slide và hợp đồng trôi khỏi nhau, Gate E5 mất ý nghĩa | E5, mọi số lấy từ hợp đồng |
| Slide thành mục lục kỹ thuật | Mất đúng chỗ tạo khác biệt | E5, mạch 11 slide |
| Phát biểu quá lời trên một con số đúng | Kiểm định số không bắt được loại lỗi này | E6, đọc to |
| Chốt kết luận ở slide 11 | Lấn sang Phase 7 | E5, E6 |
| Nói về dashboard ngoài phạm vi đã ký | Khẳng định thứ Phase 5 chưa nghiệm thu | E0 |
