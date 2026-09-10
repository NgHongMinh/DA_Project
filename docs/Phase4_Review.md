# Phiếu nghiệm thu trực quan Phase 4 (Giai đoạn 4)

Phiếu này dành cho review (nghiệm thu) bằng mắt đối với đúng 13 biểu đồ Phase 4. Kiểm định tự động trong `output/stats/04_validation_results.csv` là điều kiện cần nhưng không thay thế việc mở hình ở kích thước 100% và kiểm tra trong ngữ cảnh `docs/BaoCao.md`.

**Trạng thái ban đầu:** `CHỜ NGHIỆM THU`. Không ô nào bên dưới được đánh dấu sẵn và không biểu đồ nào được xem là đạt thủ công cho đến khi người nghiệm thu thực sự kiểm tra.

**Lượt soi trực quan ngày 2026-09-08.** Đủ 13 PNG đã được mở và soi ở kích thước gốc 2.400 × 1.350, kèm phóng to vùng nhãn của C01, C03, C05, C06, C09 và C12. Lượt soi phát hiện **ba lỗi trình bày**, đã sửa tại `python/04_charts.py` và dựng lại Phase 4; chi tiết ghi ở mục 2 và mục 4. Sau khi sửa, 13/13 hình đạt cả sáu mục. Người nghiệm thu đã xác nhận kết quả và ký nhận tại mục 5.

## 1. Quy ước ghi nhận

Mỗi biểu đồ chỉ được đổi sang `ĐẠT` khi đồng thời thỏa cả sáu mục:

1. PNG (tệp ảnh nén không mất dữ liệu) mở được ở kích thước 100%, đúng 2.400 × 1.350 điểm ảnh và không phải ảnh trắng.
2. Chữ tiếng Việt, dấu, đơn vị, nguồn, phạm vi và cửa sổ 2000–2021 đều đọc được; không có chữ chồng, cắt hoặc vượt khung.
3. Màu phân biệt được, Việt Nam dùng màu nhấn khi có mặt và màu không biểu thị thứ hạng.
4. Trục, thang đo, chú giải và nhãn trực tiếp không làm người đọc hiểu sai; không có trục kép, biểu đồ tròn hay số 0 trên trục logarit.
5. Hình truyền đạt đúng một thông điệp ghi trong bảng và không suy diễn nguyên nhân vượt quá dữ liệu.
6. Hình xuất hiện đúng chỗ trong mục 1.4 của `docs/BaoCao.md`, đồng thời khớp dữ liệu và dòng `manifest` (bảng kê) trong `04_chart_data.xlsx`.

Trạng thái hợp lệ:

- `CHỜ NGHIỆM THU`: chưa kiểm đủ sáu mục;
- `CẦN SỬA`: đã kiểm và còn ít nhất một lỗi, phải ghi rõ lỗi cùng cách tái hiện;
- `ĐẠT`: đã kiểm đủ sáu mục, không còn ghi chú phải sửa.

## 2. Bảng nghiệm thu từng biểu đồ

| ID | Tệp | Q | Thông điệp cần thấy | Kiểm ở 100% | Kiểm trong báo cáo | Trạng thái | Ghi chú / lỗi cần sửa |
|---|---|---|---|---|---|---|---|
| C01 | `04_01_global_asean_context.png` | Q1 | ASEAN tăng gần bốn lần nhưng vẫn là phần nhỏ của thế giới | [x] | [x] | ĐẠT | **Đã sửa lỗi L1.** Trục tung panel trên in `1,000` và panel dưới in `5.0%` theo kiểu Anh, ngay cạnh chú thích `7.885,0 TWh` và `2,55%` kiểu Việt — hai quy ước trong cùng một ảnh. Nay là `1.000` và `5,0%`. |
| C02 | `04_02_asean_technology_trend.png` | Q2 | Thủy điện vẫn lớn nhất; gió và mặt trời tăng rõ cuối kỳ | [x] | [x] | ĐẠT | Bảng màu đúng hợp đồng; chú thích 2021 `185,6 · 61,3 · 8,3 · 34,4` khớp dữ liệu đã kiểm. |
| C03 | `04_03_asean_country_mix_2021.png` | Q2 | Quy mô và cơ cấu năm 2021 khác nhau rõ giữa các nước | [x] | [x] | ĐẠT | **Đã sửa lỗi L3.** Thang màu nay hiển thị `0,0%–100,0%` theo quy ước Việt và cùng đơn vị phần trăm với nhãn ô. Sáu ô `0,0%` đều là số 0 thật; Brunei ghi `Không xác định (tổng = 0)`, không bịa `0%`. |
| C04 | `04_04_asean_rank_shift_2021.png` | Q3 | Đổi cách đo làm Singapore tăng 4 bậc, Indonesia giảm 4 và Lào giảm 5 | [x] | [x] | ĐẠT | Cả 10 cặp hạng khớp `03_fact_metrics.csv`; Thái Lan hiện đại hạng 2, Philippines hạng 3 — nhất quán với câu đã sửa trong báo cáo. |
| C05 | `04_05_asean_small_multiples_shared.png` | Q1 | Trục chung cho thấy chênh lệch quy mô tuyệt đối | [x] | [x] | ĐẠT | **Đã sửa lỗi L1.** Trục tung in `0.0` kiểu Anh, nay là `0,0`. |
| C06 | `04_06_asean_small_multiples_free.png` | Q1 | Trục riêng cho thấy quỹ đạo nội tại của các nước nhỏ | [x] | [x] | ĐẠT | **Đã sửa lỗi L1.** Các panel in `5.0 / 1.0 / 0.0`, nay là `5,0 / 1,0 / 0,0`. Panel Brunei giữ nguyên chú thích `Toàn kỳ = 0 TWh`. |
| C07 | `04_07_vietnam_technology_trend.png` | Q4 | Gió và mặt trời tăng mạnh cuối cửa sổ nhưng thủy điện vẫn quan trọng | [x] | [x] | ĐẠT | Dải `NLTT khác` gần như không thấy vì Việt Nam 2021 chỉ có `0,158 TWh` — đúng dữ liệu, không phải lỗi vẽ. |
| C08 | `04_08_vietnam_twh_vs_share.png` | Q5 | TWh và tỷ trọng điện không luôn đi cùng hướng | [x] | [x] | ĐẠT | Bốn panel chung trục hoành, TWh và % tách hẳn. Các năm ngược hướng 2003 · 2014 (tổng) và 2016 (hiện đại) khớp `direction_relation`. |
| C09 | `04_09_vietnam_regional_global_position.png` | Q4 | Việt Nam nổi bật hơn ở gió + mặt trời so với tổng NLTT | [x] | [x] | ĐẠT | **Đã sửa lỗi L2.** Nhãn `Tổng ASEAN-9: 14,6 TWh` ở panel phải bị cả đường ASEAN-9 lẫn đường Việt Nam kẻ xuyên qua chữ. Nay có nền trắng mờ phía sau, chữ đọc rõ, vị trí nhãn giữ nguyên. |
| C10 | `04_10_global_distribution_2021.png` | Q1 | Phân phối toàn cầu có nhiều giá trị 0 và lệch phải mạnh | [x] | [x] | ĐẠT | Bốn dòng đếm đều cộng đúng mẫu số cố định 215 (59/8/141/7 · 92/18/96/9 · 105/16/88/6 · 50/48/112/5). Trục logarit chỉ chứa giá trị dương. |
| C11 | `04_11_asean_entry_lag.png` | Q4 | Thời điểm gia nhập từng công nghệ rất không đồng đều | [x] | [x] | ĐẠT | Số đếm bốn công nghệ khớp họ `material_entry_status` (8/2 · 5/4/1 · 8/2 · 4/6). Kiểm duyệt là ký hiệu tam giác có chú giải riêng, không phải năm giả. |
| C12 | `04_12_asean_concentration_growth.png` | Q6 | Gió + mặt trời và phần tăng của nó tập trung mạnh ở Việt Nam | [x] | [x] | ĐẠT | **Đã sửa lỗi L1.** Toàn bộ nhãn in kiểu Anh (`66.0%`, `20.1%`, `42.6 TWh`, `92.2%`, `92.3%`, `67.1%`), nay là `66,0%`, `20,1%`, `42,6 TWh`, `92,2%`, `92,3%`, `67,1%`. |
| C13 | `04_13_capacity_factor_proxy.png` | Q4 | Chỉ số phụ có độ phủ hạn chế: 2 nước cho gió, 4 nước cho mặt trời | [x] | [x] | ĐẠT | Chân hình liệt kê đủ tên nước thiếu công suất cho cả gió và mặt trời; nêu rõ “công suất cuối năm” và “chỉ báo xấp xỉ”. |

### 2.1. Ba lỗi phát hiện trong lượt soi và cách đã xử lý

**L1 — Dấu thập phân kiểu Anh ở 4/13 hình.** C01, C05, C06 và C12 in số theo quy ước Anh (`1,000` cho hàng nghìn; `0.0` / `66.0%` cho phần thập phân), trong khi 9 hình còn lại và toàn bộ văn bản đồ án dùng quy ước Việt (`1.000`; `0,0`; `66,0%`). Nặng nhất là C01 và C12 vì hai quy ước xuất hiện **trong cùng một ảnh**.

*Tái hiện:* mở C12 ở 100%, đọc nhãn thanh Việt Nam — trước khi sửa là `66.0%`.

*Nguyên nhân:* `python/04_charts.py` đã có sẵn `_vi_number()` và `_format_share_label()`, nhưng sáu chỗ định dạng dựng chuỗi trực tiếp bằng f-string nên không đi qua hai hàm này: trục logarit và trục tỷ lệ của C01, bộ định dạng trục dùng chung của C05/C06, ba nhãn của C12.

*Cách sửa:* nối cả sáu chỗ vào `_vi_number()` / `_format_share_label()`. Không đổi số liệu, chỉ đổi cách in.

**L2 — Chồng chữ ở C09.** Nhãn `Tổng ASEAN-9: 14,6 TWh` nằm đúng chỗ đường ASEAN-9 dựng đứng đi lên và đường Việt Nam cắt qua, nên hai nét kẻ xuyên ngang thân chữ. Vi phạm tiêu chí 2 (“không có chữ chồng”).

*Tái hiện:* mở C09 ở 100%, nhìn panel phải quanh mốc 2019–2021.

*Cách sửa:* thêm nền trắng mờ (`alpha = 0,85`) sau nhãn điểm cuối, giữ nguyên tọa độ nhãn để bố cục không đổi.

**L3 — Thang màu C03 dùng dấu thập phân và đơn vị không nhất quán.** Các ô bản đồ nhiệt đã hiển thị phần trăm kiểu Việt (`72,8%`), nhưng thang màu vẫn dùng tỷ lệ mặc định kiểu Anh (`0.0–1.0`). Điều này làm cùng một đại lượng xuất hiện với hai quy ước trong một ảnh và mâu thuẫn với quy ước đọc số của dự án.

*Tái hiện:* mở C03 ở 100%, đọc các mốc trên thang màu bên phải — trước khi sửa là `0.0`, `0.2`, …, `1.0`.

*Cách sửa:* gắn thang màu vào `_format_share_label()` để hiển thị `0,0%`, `20,0%`, …, `100,0%`; bổ sung ca `c03_colorbar=1` trong `04_test_contract.py` để kiểm trực tiếp bộ định dạng sau khi dựng C03.

**Vì sao bộ 38 kiểm định phát hành không bắt được ba lỗi này:** `04_validation_results.csv` kiểm tên tệp, kích thước, độ không-trắng, dấu vân tay dữ liệu và các bất biến số — không đọc **chuỗi ký tự được vẽ ra ảnh**. Phần soi trực quan ở mục 2–3 đã phát hiện đủ ba lỗi; riêng L3 nay còn có kiểm thử hồi quy ở `04_test_contract.py` để ngăn tái phát.

## 3. Kiểm tra riêng theo rủi ro

Các mục sau xử lý những rủi ro không thể kết luận chỉ bằng việc tệp mở được:

- [x] C01 và C10 không đưa giá trị 0 lên trục logarit; C01 dùng dòng `World` do nguồn công bố. → C01 vẽ hai chuỗi luôn dương (nhỏ nhất là ASEAN năm 2000 = `72,8 TWh`); panel logarit của C10 mang tiêu đề “Phân phối **dương**”, còn số 0 được đếm riêng ở panel trái. Chuỗi thế giới lấy từ dòng `World` nguồn báo cáo, đúng `7.885,04005 TWh` năm 2021.
- [x] C03 dùng cùng thứ tự quốc gia cho thanh chồng và bản đồ nhiệt; TWh không bị trình bày như tỷ trọng; không tỷ trọng dương nào bị ghi thành `0%` hoặc `0,0%`. → Hai panel cùng thứ tự hạng tổng NLTT (Việt Nam → Brunei). Panel trái ghi đơn vị `Sản lượng năm 2021 (TWh)`, panel phải ghi `Tỷ trọng trong tổng NLTT`. Đã đối chiếu **cả sáu** ô hiển thị `0,0%` (Campuchia/Lào/Malaysia/Myanmar–gió, Singapore–thủy điện và gió): tất cả đều có giá trị thô đúng bằng `0`, không ô nào là số dương bị làm tròn xuống.
- [x] C04 đặt hạng 1 ở phía trên, giữ đồng hạng và màu không thay đổi theo vị trí. → Việt Nam (hạng 1) ở dòng trên cùng; màu gắn theo quốc gia và trùng đúng màu quốc gia đó ở C05/C06/C12. **Lưu ý:** năm 2021 không có đồng hạng nào để nhìn thấy — xem cảnh báo ở cuối mục 4.
- [x] C05 và C06 dùng cùng dữ liệu; C05 ghi rõ “chung thang đo”, C06 ghi rõ “thang đo riêng”. → Cả hai đọc từ sheet `small_multiples`; tiêu đề ghi đúng “— chung thang đo” và “— thang đo riêng”; chân hình C06 còn cảnh báo không so chiều cao giữa các panel.
- [x] C08 tách TWh và % điện thành panel (ô biểu đồ) riêng; các năm ngược hướng được đánh dấu nhưng không bị giải thích thành quan hệ nhân quả. → Bốn panel, hàng trên TWh và hàng dưới % điện, không dùng trục kép. Ba mốc đánh dấu 2003 · 2014 · 2016 khớp đúng các dòng `OPPOSITE_DIRECTION` của `direction_relation`; nhãn chỉ ghi “ngược hướng”, không nêu nguyên nhân.
- [x] C09 ghi ASEAN-9 là tổng, không phải trung bình; `16/205` và `17/209` chỉ là hạng năm 2021. → Chú giải ghi `Tổng ASEAN-9`, chân hình ghi “ASEAN-9 là tổng chín nước còn lại; hạng toàn cầu chỉ được chú thích tại năm 2021”. Giá trị `185,4` và `14,6 TWh` đúng bằng ASEAN-10 trừ Việt Nam.
- [x] C11 phân biệt được kiểm duyệt trái/phải; không biến trạng thái thành năm đầu giả. → Ba ký hiệu khác hình dạng (◁ đã đạt từ đầu · ● năm chuyển quan sát được · ▷ chưa đạt đến cuối) có chú giải riêng; chân hình ghi “Kiểm duyệt trái/phải là trạng thái, không phải năm 2000 hoặc 2021 giả định”. Việt Nam–thủy điện hiện ◁ chứ không phải mốc 2000; Brunei–mặt trời hiện ▷ chứ không phải mốc 2021.
- [x] C12 phân biệt top-3 (ba nước có tỷ trọng lớn nhất) của mức sản lượng với đóng góp tăng dương; không dùng HHI (chỉ số tập trung Herfindahl–Hirschman)/Gini (hệ số bất bình đẳng) thay cho đóng góp tăng trưởng. → Panel trái là `top3_share` theo thời gian, panel phải là `positive_growth_share` 2010–2021; hai đại lượng ở hai panel có tiêu đề và đơn vị riêng. Không hình nào vẽ HHI/Gini. Chân hình ghi “Đóng góp dùng tổng phần tăng dương, không phải HHI/Gini hay thay đổi ròng toàn khu vực”.
- [x] C13 ghi “công suất cuối năm”, “chỉ báo xấp xỉ”, đủ danh sách nước thiếu và không kết luận hiệu quả kỹ thuật. → Chân hình nêu công thức `TWh / (GW × 8,76)`, quy tắc chọn cặp `công suất > 0`, và liệt kê **đủ tên** 8 nước thiếu công suất gió cùng 6 nước thiếu công suất mặt trời; kết câu bằng “không phải hiệu quả kỹ thuật”.
- [x] Không biểu đồ cấp quốc gia nào chứa thực thể tổng hợp hoặc năm 2022. → Mọi hình cấp nước chỉ chứa đúng 10 tên ASEAN; C10 dùng mẫu số cố định 215 quốc gia/vùng lãnh thổ hiện tại. Trục thời gian mọi hình dừng ở 2021; `fact_energy` không còn dòng 2022 nào.

## 4. Đối chiếu kiểm định tự động trước khi ký

Các ô trong mục này là kiểm định **máy chạy được**, đã thực thi thật ngày **2026-09-08** và ghi lại giá trị đo được. Chúng là điều kiện cần, không thay thế mục 2 và mục 3.

> **Đã chạy lại toàn bộ sau khi sửa L1, L2 và L3.** `python python\04_charts.py` dựng lại 13 PNG, rồi cả ba lệnh kiểm thử chạy lại và đều trả mã thoát 0. Kết quả sau khi sửa giữ nguyên mọi mốc: 38 mã kiểm định duy nhất `PASS`, 0 dòng chặn khác `PASS`, `phase2_input_fingerprint = 64e1cc7d7bcb…`, `fact_energy.csv` giữ nguyên `sha256 = dfaca2c4…`, 13 PNG đúng 2.400 × 1.350 và không có tệp lạ. Hai lượt dựng liên tiếp vẫn cho đầu ra giống hệt. `04_test_contract.py` còn xác nhận thang màu C03 dùng phần trăm kiểu Việt. Vì vậy mọi ô đã đánh dấu bên dưới vẫn đúng với bộ hình hiện có trên đĩa.

- [x] `output/stats/04_validation_results.csv` có đúng 38 mã duy nhất và không có dòng `BLOCKING` (chặn phát hành) khác `PASS` (đạt). → đo được: 38 dòng, 38 `validation_id` duy nhất, `PASS=38`, blocking khác PASS = 0.
- [x] `output/charts/` có đúng 13 PNG trong danh sách cho phép và không có tệp `04_*.png` lạ. → đo được: 13 tệp, 0 tệp lạ.
- [x] `output/stats/04_chart_data.xlsx` có đủ 16 sheet (trang tính), đủ 13 dòng `manifest` và cùng dấu vân tay Phase 2. → đo được: 16 sheet, 13 dòng manifest, `phase2_input_fingerprint = 64e1cc7d7bcb…`.
- [x] `python python\04_test_contract.py` trả mã thoát 0; thay một giá trị C13 nhưng giữ số dòng/khóa bị chặn. → `PASS | fact_energy_lock=1 | mutation_rejected=1 | c03_labels=1 | c03_colorbar=1 | c06_zero_panel=1`, exit 0.
- [x] `python python\04_test_publish.py` trả mã thoát 0. → `PASS | existing_restore=1 | new_target_cleanup=1 | rollback_backup_retained=1 | successful_publish=1`, exit 0.
- [x] `python python\04_verify_release.py` trả mã thoát 0 và cùng tiến trình báo tiền điều kiện B1 đạt 3/3. → `PASS | preflight=3/3 PASS`, exit 0; tiền điều kiện gồm Phase 0 `26/26`, Phase 2 gate `PASS`, Phase 3 `92/92`.
- [x] Mã băm 17 CSV nguồn, `fact_energy.csv` và toàn bộ sản phẩm Phase 3 không đổi trong hai lần dựng Phase 4. → `archive_files=17 | fact_energy=1 | phase3_outputs=16` giữ nguyên hàm băm qua cả hai lượt dựng; hai lượt cho đầu ra giống hệt.
- [x] Mục 1.4 của `docs/BaoCao.md` nhúng đủ 13 hình theo năm nhóm. → đo được: 13 tham chiếu PNG, khớp tuyệt đối danh sách trên đĩa, chia đúng 5 nhóm.
- [x] Phần Phase 4 trong `docs/NhatKyPhanTich.md` chỉ có phát hiện mới kèm số và định vị bằng chứng, hoặc dẫn lại đúng mã `P3-xx`. → đo được: đúng một phát hiện mới `P4-01`, có số (104 cặp · gió 33 · mặt trời 71 · biên 0–32,5764%) và truy vết tới `04_chart_data.xlsx` sheet `capacity_factor`.

**Đã sửa trước khi ký (thuộc Gate B0 của Phase 5):** câu “Thái Lan và Philippines đồng hạng 3 theo gió + mặt trời” là **sai** — dữ liệu cho Thái Lan hạng 2 và Philippines hạng 3, mỗi nước tăng 3 bậc, và năm 2021 không có đồng hạng nào. Đã sửa ở `docs/NhatKyPhanTich.md` (P3-06) và `docs/BaoCao.md` (Q3), trong đó bản báo cáo còn phải bỏ mệnh đề “đúng quy tắc không phá hòa bằng tên quốc gia” vì nó biện minh cho một trường hợp hòa không tồn tại. Đã đối chiếu C04 trên cả ba lớp — `04_chart_data.xlsx` sheet `rank_shift_2021`, ảnh PNG, và `P4_C04_CONTRACT = PASS` — **hình vẽ đúng**, đây chỉ là lỗi văn bản, không cần dựng lại Phase 4.

> ⚠️ Lưu ý cho người nghiệm thu ở mục 3: dòng “C04 … giữ đồng hạng” là **quy tắc dựng hình**, không phải thứ phải nhìn thấy trên C04 — năm 2021 không có đồng hạng. Các ca đồng hạng thật nằm ở 2000 và 2010 (Brunei và Singapore cùng hạng 9).

## 5. Ký nhận tổng thể

Chỉ điền phần này khi bảng ở mục 2 có 13/13 trạng thái `ĐẠT`, toàn bộ ô mục 3–4 đã được kiểm và không còn ghi chú phải sửa.

| Trường | Nội dung |
|---|---|
| Kết quả tổng thể | **ĐẠT — ĐÃ KÝ** |
| Người nghiệm thu | **Nguyễn Hồng Minh** |
| Ngày nghiệm thu | **2026-09-08** |
| Dấu vân tay Phase 2 | `64e1cc7d7bcbbde9f2378eaa81e5a42f4a1322d356a5a0b73f4cd944b95a8b10` |
| Phiên bản phương pháp | `phase4_v1` |
| Số kiểm định tự động đạt / tổng | **38 / 38** (0 dòng chặn khác `PASS`) |
| Ghi chú cuối | Lượt soi trực quan ngày 2026-09-08 phát hiện ba lỗi trình bày — L1 dấu thập phân kiểu Anh ở C01/C05/C06/C12, L2 chồng chữ ở C09, L3 thang màu C03 dùng `0.0–1.0` thay vì phần trăm kiểu Việt — đã sửa tại `python/04_charts.py`, dựng lại Phase 4 và chạy lại đủ ba lệnh kiểm thử với mã thoát 0. Không còn ghi chú phải sửa. Bảng mục 2 hiện là 13/13 `ĐẠT`. Câu sai về thứ hạng Thái Lan/Philippines đã sửa trước đó ở cả nhật ký và báo cáo, C04 đã đối chiếu ba lớp và hình vẽ đúng. |

**Kết luận:** Phase 4 đã đủ bằng chứng tự động, 13/13 biểu đồ đạt nghiệm thu trực quan và được Nguyễn Hồng Minh ký ngày 2026-09-08. `PLAN.md` đã được cập nhật thành “ĐÃ HOÀN THÀNH”; Gate B0 của Phase 5 được mở.
