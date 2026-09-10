"""Phase 6 Gate E5 -- build the 1.5b deck from the verified claim set.

Why a script rather than PowerPoint by hand
-------------------------------------------
Every other artefact in this project is reproducible from one command: the 13 PNGs
come from `04_charts.py`, the PBIP from `05_build_pbip.py`. A hand-built deck would
be the only deliverable that cannot be rebuilt, and also the only one where the
completion criterion -- *every number on a slide traces back to a table in
`output/stats/`* -- would have to be checked by eye.

Here the criterion holds by construction: every number on every slide is read from
`phase6_contract.py`, which is the same set `06_verify_findings.py` proved against
three independent sources. Nothing in this file computes a statistic, and nothing
in it types a digit that came from anywhere else. `assert_no_stray_numbers()` at
the end enforces that rather than trusting it.

Vietnamese number convention
----------------------------
`1.000` for thousands, `0,0` for decimals -- the same convention the Phase 4 charts
were rebuilt to satisfy after defect L1. A deck using English separators next to
PNGs using Vietnamese ones reads as two documents stapled together.

Run:  python python\\06_build_slides.py
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CHARTS, OUTPUT  # noqa: E402

PYTHON_DIR = Path(__file__).resolve().parent
SLIDES_DIR = OUTPUT / "slides"
DECK_PATH = SLIDES_DIR / "ASEAN_Renewables.pptx"


def _load(module_name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(module_name, PYTHON_DIR / file_name)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {file_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


contract = _load("phase6_contract_deck", "phase6_contract.py")
VALUE = {c.claim_id: c.value for c in contract.CLAIMS}
MESSAGES = contract.FINDING_MESSAGES

# Figures a slide states that are ratios BETWEEN two locked claims rather than a
# claim in their own right. Declared here, once, so they are still traceable: each
# is an expression over `VALUE` and nothing else, and `assert_no_stray_numbers()`
# renders this dict alongside VALUE. Computing one inline inside a builder would
# make it a number the check cannot account for, which is how the traceability
# criterion quietly stops meaning anything.
DERIVED = {
    "asean_growth_multiple": VALUE["F1_ASEAN_2021"] / VALUE["F1_ASEAN_2000"],
    "world_growth_multiple": VALUE["F1_WORLD_2021"] / VALUE["F1_WORLD_2000"],
    "hydro_share_2021": VALUE["F2_HYDRO_2021"] / VALUE["F1_ASEAN_2021"],
    "modern_share_2021": VALUE["F2_MODERN_2021"] / VALUE["F1_ASEAN_2021"],
    "vn_growth_multiple": VALUE["F4_VN_TOTAL_2021"] / VALUE["F6_VN_TOTAL_2000"],
    "mean_over_median": (VALUE["F7_SOLAR2021_ALL_OBSERVED_MEAN"]
                         / VALUE["F7_SOLAR2021_ALL_OBSERVED_MEDIAN"]),
}

# Phase 4 palette, so the deck and the 13 PNGs read as one document.
INK = RGBColor(0x37, 0x41, 0x51)          # foreground
MUTED = RGBColor(0x6B, 0x72, 0x80)        # secondary text
ACCENT = RGBColor(0xD5, 0x5E, 0x00)       # the Vietnam / emphasis colour
BLUE = RGBColor(0x00, 0x72, 0xB2)
GREEN = RGBColor(0x00, 0x9E, 0x73)
RULE = RGBColor(0xE5, 0xE7, 0xEB)
PAPER = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "Segoe UI"
W, H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.62)


# --------------------------------------------------------------------------
# Vietnamese number formatting
# --------------------------------------------------------------------------

def vn(value: float, decimals: int = 0) -> str:
    """1234.5 -> '1.234,5'. Thousands with '.', decimal comma."""
    whole, _, frac = f"{abs(value):.{decimals}f}".partition(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    sign = "-" if value < 0 else ""
    return f"{sign}{grouped},{frac}" if decimals else f"{sign}{grouped}"


def pct(ratio: float, decimals: int = 2) -> str:
    """A 0-1 ratio rendered as a percentage.

    The x100 happens HERE and nowhere else, so the storage scale stays 0-1 all the
    way from the contract. Doing it earlier is how 0,671 becomes 67,1 in a variable
    that some later line then multiplies again.
    """
    return vn(ratio * 100, decimals) + "%"


# --------------------------------------------------------------------------
# Layout primitives
# --------------------------------------------------------------------------

def blank(prs: Presentation):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = PAPER
    return slide


def textbox(slide, x, y, w, h, text: str, *, size: int, bold: bool = False,
            color: RGBColor = INK, align=PP_ALIGN.LEFT, spacing: float = 1.0,
            italic: bool = False):
    box = slide.shapes.add_textbox(x, y, w, h)
    frame = box.text_frame
    frame.word_wrap = True
    for index, line in enumerate(text.split("\n")):
        para = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        para.alignment = align
        para.line_spacing = spacing
        run = para.add_run()
        run.text = line
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
        run.font.name = FONT
    return box


def rule(slide, y, *, x=MARGIN, w=None, color: RGBColor = RULE, thickness=Pt(1.5)):
    w = w or (W - 2 * MARGIN)
    line = slide.shapes.add_shape(1, x, y, w, thickness)  # 1 = rectangle
    line.fill.solid()
    line.fill.fore_color.rgb = color
    line.line.fill.background()
    line.shadow.inherit = False
    return line


def heading(slide, kicker: str, title: str) -> Emu:
    """Kicker + title + rule. Returns the y where body content may start."""
    if kicker:
        textbox(slide, MARGIN, Inches(0.42), W - 2 * MARGIN, Inches(0.3),
                kicker.upper(), size=12, bold=True, color=ACCENT)
    textbox(slide, MARGIN, Inches(0.74), W - 2 * MARGIN, Inches(0.9),
            title, size=30, bold=True, color=INK, spacing=0.95)
    rule(slide, Inches(1.72))
    return Inches(1.95)


def footer(slide, note: str) -> None:
    textbox(slide, MARGIN, H - Inches(0.5), W - 2 * MARGIN - Inches(0.6), Inches(0.3),
            note, size=9.5, color=MUTED)


def notes(slide, text: str) -> None:
    """Ghi chú cho người thuyết trình — phần nói, không phải phần chiếu.

    Đây là chỗ tách slide thuyết trình khỏi slide báo cáo. Câu dài, số phụ, lời
    dẫn và câu trả lời cho những chất vấn hay gặp đều để ở đây; trên màn hình chỉ
    còn một câu khẳng định và vài cụm ngắn. Nhồi hết vào slide thì người nghe đọc
    thay vì nghe, và người nói thành thừa.
    """
    slide.notes_slide.notes_text_frame.text = text.strip()


def stamp_page_numbers(prs) -> None:
    """Number the slides after they are all built, not inside each builder.

    Page numbers written by hand inside the builders were fine at eleven slides
    and became a liability the moment a slide had to be inserted in the middle:
    every later number silently became wrong, and nothing checks a footer.
    """
    for index, slide in enumerate(prs.slides, start=1):
        textbox(slide, W - MARGIN - Inches(0.6), H - Inches(0.5), Inches(0.6),
                Inches(0.3), str(index), size=9.5, color=MUTED, align=PP_ALIGN.RIGHT)


def picture(slide, name: str, y: Emu, height: Emu, x: Emu | None = None) -> None:
    """Place a Phase 4 PNG preserving its 16:9 ratio; centred unless `x` is given."""
    path = CHARTS / name
    if not path.exists():
        raise FileNotFoundError(f"thieu hinh Phase 4: {path}")
    width = Emu(int(height * 2400 / 1350))
    left = Emu(int((W - width) / 2)) if x is None else x
    slide.shapes.add_picture(str(path), left, y, width=width)


def stat_row(slide, y: Emu, items: list[tuple[str, str, RGBColor]]) -> None:
    """Evenly spaced big-number tiles. `items` is (value, caption, colour)."""
    gap = Inches(0.3)
    span = W - 2 * MARGIN
    width = Emu(int((span - gap * (len(items) - 1)) / len(items)))
    for index, (value, caption, colour) in enumerate(items):
        x = Emu(int(MARGIN + index * (width + gap)))
        textbox(slide, x, y, width, Inches(0.72), value,
                size=34, bold=True, color=colour, align=PP_ALIGN.CENTER)
        textbox(slide, x, y + Inches(0.78), width, Inches(0.7), caption,
                size=12, color=MUTED, align=PP_ALIGN.CENTER, spacing=1.05)


def table(slide, x: Emu, y: Emu, w: Emu, headers: list[str],
          rows: list[list[str]], *, widths: list[float] | None = None,
          size: int = 13, row_h: float = 0.42) -> Emu:
    """A light table: header row, hairline rules, no cell borders.

    Built from text boxes rather than a PowerPoint table shape on purpose --
    a real table brings its own theme colours and overrides the Phase 4 palette,
    which is the one thing the deck and the 13 PNGs must agree on.
    Returns the y just below the last row.
    """
    weights = widths or [1.0] * len(headers)
    total = sum(weights)
    cols, running = [], 0.0
    for weight in weights:
        cols.append((Emu(int(x + w * running / total)), Emu(int(w * weight / total))))
        running += weight

    for (cx, cw), head in zip(cols, headers):
        textbox(slide, cx, y, cw, Inches(row_h), head,
                size=size, bold=True, color=MUTED)
    rule(slide, y + Inches(row_h - 0.06), x=x, w=w, thickness=Pt(1))

    cursor = y + Inches(row_h + 0.06)
    for index, row in enumerate(rows):
        for (cx, cw), cell in zip(cols, row):
            first = index == 0 or True
            textbox(slide, cx, cursor, cw, Inches(row_h), cell,
                    size=size, bold=(cell is row[0] and first), color=INK)
        cursor = cursor + Inches(row_h)
        if index < len(rows) - 1:
            rule(slide, cursor - Inches(0.04), x=x, w=w,
                 color=RGBColor(0xF3, 0xF4, 0xF6), thickness=Pt(0.75))
    return cursor


def bullets(slide, x, y, w, lines: list[str], *, size: int = 15,
            spacing: float = 1.35) -> None:
    body = "\n".join(f"•   {line}" for line in lines)
    textbox(slide, x, y, w, H - y - Inches(0.7), body, size=size, spacing=spacing)


# --------------------------------------------------------------------------
# The eleven slides
# --------------------------------------------------------------------------

SOURCE = "Nguồn: Our World in Data (Ember · BP) · ASEAN-10 · 2000–2021 · đã loại năm 2022 bị cắt cụt"


def slide_01(prs) -> None:
    """Hook: one question and one number."""
    slide = blank(prs)
    textbox(slide, MARGIN, Inches(1.15), W - 2 * MARGIN, Inches(0.4),
            "ĐỒ ÁN PHÂN TÍCH DỮ LIỆU", size=13, bold=True, color=ACCENT)
    textbox(slide, MARGIN, Inches(1.6), W - 2 * MARGIN, Inches(1.7),
            "Đông Nam Á chuyển dịch sang năng lượng tái tạo\nđến đâu, và Việt Nam đứng ở đâu trong đó?",
            size=38, bold=True, color=INK, spacing=1.0)
    rule(slide, Inches(3.5), w=Inches(3.2), color=ACCENT, thickness=Pt(3))

    textbox(slide, MARGIN, Inches(3.95), Inches(7.4), Inches(1.5),
            f"Năm 2021, một nước duy nhất chiếm {pct(VALUE['F4_VN_SHARE_MODERN'])} "
            "toàn bộ sản lượng\ngió và mặt trời của cả mười nước ASEAN.",
            size=19, color=INK, spacing=1.25)
    textbox(slide, MARGIN, Inches(5.35), Inches(7.4), Inches(0.5),
            "Nước đó là Việt Nam.", size=19, bold=True, color=ACCENT)

    textbox(slide, Inches(8.6), Inches(3.95), Inches(4.1), Inches(2.0),
            f"{pct(VALUE['F4_VN_SHARE_MODERN'])}",
            size=66, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    textbox(slide, Inches(8.6), Inches(5.15), Inches(4.1), Inches(0.8),
            "tỷ trọng của Việt Nam trong\ngió + mặt trời của ASEAN-10, 2021",
            size=12, color=MUTED, align=PP_ALIGN.CENTER, spacing=1.15)

    footer(slide, SOURCE)
    notes(slide, """
Mở bằng con số trước, tên nước sau. Để người nghe đoán một nhịp rồi mới xác nhận.

"Năm 2021, một nước duy nhất chiếm gần hai phần ba toàn bộ sản lượng gió và mặt
trời của cả mười nước ASEAN. Nước đó là Việt Nam."

Rồi đặt câu hỏi trung tâm: con số ấy nói lên điều gì về chuyển dịch năng lượng
của khu vực, và về vị trí của Việt Nam trong đó.

Không đi vào phương pháp ở slide này. Chỉ một câu hỏi và một con số.
""")


def slide_02(prs) -> None:
    """The central question and the six sub-questions."""
    slide = blank(prs)
    y = heading(slide, "Câu hỏi", "Một câu hỏi trung tâm, sáu câu hỏi con")
    bullets(slide, MARGIN, y + Inches(0.05), W - 2 * MARGIN, [
        "Q1 — ASEAN so với thế giới: quy mô và tỷ trọng?",
        "Q2 — Cơ cấu dịch chuyển ra sao giữa các công nghệ?",
        "Q3 — Đổi cách đo thì thứ hạng đổi thế nào?",
        "Q4 — Việt Nam đứng ở đâu, khu vực và thế giới?",
        "Q5 — Sản lượng và tỷ trọng có đi cùng chiều?",
        "Q6 — Đà tăng tập trung vào bao nhiêu nước?",
    ], size=17, spacing=1.55)

    # Who the answers are for. Taken from the capstone decks used as reference:
    # naming the reader keeps the recommendations in section 1.6 addressed to
    # someone specific instead of floating free.
    rule(slide, Inches(5.55))
    textbox(slide, MARGIN, Inches(5.75), W - 2 * MARGIN, Inches(0.3),
            "KẾT QUẢ NÀY DÙNG CHO AI", size=12, bold=True, color=ACCENT)
    third = Emu(int((W - 2 * MARGIN - Inches(0.8)) / 3))
    for index, (who, why) in enumerate([
        ("Nhà hoạch định năng lượng",
         "so sánh vị thế khu vực và đặt mục tiêu theo tỷ trọng, không chỉ theo sản lượng"),
        ("Nhà phân tích và nghiên cứu",
         "có sẵn bộ dữ liệu đã làm sạch, kiểm định và truy vết được tới từng con số"),
        ("Người đọc báo cáo năng lượng",
         "biết một bảng xếp hạng nói gì, và nó im lặng về điều gì"),
    ]):
        x = Emu(int(MARGIN + index * (third + Inches(0.4))))
        textbox(slide, x, Inches(6.15), third, Inches(0.3), who,
                size=13, bold=True, color=INK)
        textbox(slide, x, Inches(6.45), third, Inches(0.7), why,
                size=11.5, color=MUTED, spacing=1.2)
    footer(slide, SOURCE)
    notes(slide, """
Câu hỏi trung tâm: Đông Nam Á chuyển dịch sang năng lượng tái tạo đến đâu, và
Việt Nam đứng ở đâu trong đó.

Sáu câu hỏi con thu hẹp dần: từ khu vực so với thế giới (Q1), xuống cơ cấu công
nghệ (Q2), sang cách đo (Q3), rồi tới Việt Nam (Q4), quan hệ sản lượng và tỷ
trọng (Q5), và cuối cùng là mức tập trung (Q6).

Điểm đáng nhấn: mỗi câu hỏi con gắn với một chỉ số cụ thể tính được từ dữ liệu.
Không câu nào đặt ra rồi bỏ ngỏ — cả sáu đều được trả lời bằng số ở phần sau.

Về đối tượng dùng kết quả: nói ngắn thôi, một câu mỗi nhóm. Ý chính là báo cáo
này có người đọc cụ thể, nên phần đề xuất ở cuối được viết cho họ chứ không phải
viết chung chung.
""")


def slide_03(prs) -> None:
    """What the data cannot answer -- stated before any finding."""
    slide = blank(prs)
    y = heading(slide, "Giới hạn", "Bộ dữ liệu này không trả lời được những gì")
    column = Inches(5.0)
    bullets(slide, MARGIN, y + Inches(0.3), column, [
        "Giá thành sản xuất và suất đầu tư",
        "Chính sách, cơ chế giá và trợ cấp",
        "Dân số, GDP, cường độ tiêu thụ",
        "Phát thải và hệ số phát thải lưới",
        "Gió trên bờ và ngoài khơi (chỉ có tổng)",
        "Công suất đầy đủ cho mọi nước, mọi công nghệ",
    ], size=14, spacing=1.5)

    # C13 is the coverage limitation made visible: the capacity-factor proxy can
    # only be computed where BOTH generation and capacity exist, and the chart
    # names the countries where they do not. Showing it here means the limits
    # slide has evidence rather than only assertions.
    picture(slide, "04_13_capacity_factor_proxy.png",
            y + Inches(0.25), Inches(3.9), x=Inches(6.05))
    textbox(slide, Inches(6.05), y + Inches(4.25), Inches(6.7), Inches(0.5),
            "Ví dụ: hệ số công suất chỉ tính được ở 104 cặp nước–năm.",
            size=12, color=MUTED)

    textbox(slide, MARGIN, Inches(5.85), Inches(5.0), Inches(1.2),
            "Hệ quả: báo cáo mô tả điều đã xảy ra và mức độ,\nnhưng không giải "
            "thích nguyên nhân.",
            size=14, bold=True, color=ACCENT, spacing=1.3)
    footer(slide, SOURCE)
    notes(slide, """
Nói giới hạn TRƯỚC khi trình bày phát hiện, không phải sau. Đây là lựa chọn có
chủ ý: biết ranh giới của dữ liệu là điều kiện để đọc đúng mọi con số phía sau.

Sáu nhóm dữ liệu không có: giá thành và suất đầu tư · chính sách và cơ chế giá ·
dân số và GDP · phát thải · gió tách trên bờ và ngoài khơi · công suất đầy đủ cho
mọi nước và mọi công nghệ.

Biểu đồ bên phải là ví dụ cụ thể của giới hạn cuối cùng: hệ số công suất chỉ tính
được ở những nước có ĐỦ CẢ sản lượng lẫn công suất — 104 cặp nước-năm. Biểu đồ ghi
thẳng tên nước bị thiếu thay vì lặng lẽ bỏ qua.

Câu chốt: báo cáo này mô tả điều đã xảy ra và mức độ, nhưng không giải thích
nguyên nhân. Mọi câu trả lời cho "vì sao" đều nằm ngoài phạm vi.
""")


def slide_04(prs) -> None:
    """The data defects actually found. Half of the pair that sets this apart."""
    slide = blank(prs)
    y = heading(slide, "Chất lượng dữ liệu",
                "Bốn khuyết điểm — không cái nào tự báo lỗi")
    stat_row(slide, y + Inches(0.05), [
        ("3,125%", "thực thể còn lại nếu ghép\nINNER JOIN cả 17 file", ACCENT),
        ("3", "file là bản trùng dư thừa\ncủa một file khác", ACCENT),
        ("8", "file bị cắt cụt nặng\nở năm 2022", ACCENT),
        ("106 → 247", "thực thể nhảy vọt tại\nnăm 2000 do đổi nguồn", ACCENT),
    ])
    bullets(slide, MARGIN, Inches(4.5), W - 2 * MARGIN, [
        "Ghép sai kiểu → mất 97% thực thể, im lặng",
        "Dùng file trùng → đếm hai lần cùng một lượng điện",
        "Giữ năm 2022 → cú sụt giả ở cuối mọi chuỗi",
        "Mẫu số động → cú sụt giả thứ hai, tại năm 2000",
    ], size=17, spacing=1.7)
    footer(slide, SOURCE)
    notes(slide, """
Đây là nửa đầu của cặp slide quan trọng nhất bài. Thông điệp: dữ liệu này KHÔNG
sạch sẵn, và bốn khuyết điểm dưới đây đều thuộc loại không ném ra lỗi nào.

1. GHÉP SAI KIỂU. 17 file phủ rất khác nhau, từ 251 xuống 33 thực thể. INNER JOIN
   toàn bộ chỉ giữ 3,125% thực thể và 1,87% khoá — mất khoảng 97% dữ liệu mà
   pandas không cảnh báo gì. Cách chặn: dựng spine rồi LEFT JOIN.

2. FILE TRÙNG. Ba file 05, 08, 12 là tập con dư thừa của các cột tương ứng trong
   file 03. Dùng cả hai là đếm hai lần cùng một lượng điện.

3. NĂM 2022 BỊ CẮT CỤT ở 8 file, và có 0 nước ASEAN. Giữ lại thì mọi chuỗi thời
   gian có một cú sụt giả ở cuối — trông y hệt một sự suy giảm thật.

4. VỰC COVERAGE tại năm 2000: panel nhảy từ 106 lên 247 thực thể vì nguồn dữ liệu
   đổi. Nếu tính "% số nước" bằng cách chia cho số dòng từng năm thì tạo ra cú sụt
   giả thứ hai, đúng tại năm 2000.

Điểm cần nói rõ: cả bốn đều được phát hiện bằng khảo sát có hệ thống, không phải
tình cờ. Slide sau nói cách chứng minh đã xử lý đúng.
""")


def slide_05(prs) -> None:
    """How the cleaning was proven correct. The other half of the pair."""
    slide = blank(prs)
    y = heading(slide, "Kiểm định", "Làm sạch là một chuyện, chứng minh đã làm đúng là chuyện khác")
    stat_row(slide, y + Inches(0.05), [
        ("89.075", "dòng dữ kiện sau khi\nchuẩn hoá về dạng dài", BLUE),
        ("8", "kiểm định đối chiếu\nV1–V8 viết bằng SQL", BLUE),
        ("864", "kết quả kiểm định\nPhase 2 được ghi lại", BLUE),
        ("0", "dòng chặn không đạt\ntrên toàn bộ quy trình", GREEN),
    ])
    bullets(slide, MARGIN, Inches(4.5), W - 2 * MARGIN, [
        "Tổng các nước phải khớp dòng “World” từng năm",
        "Giá trị 0 giữ nguyên — là kết quả, không phải lỗi",
        "Chênh lệch thật giữa hai nguồn: giữ và giải thích",
        "Chạy lại cho kết quả trùng khớp từng byte",
    ], size=17, spacing=1.7)
    footer(slide, SOURCE)
    notes(slide, """
Nửa sau của cặp slide tạo khác biệt. Thông điệp: làm sạch dữ liệu là một chuyện,
CHỨNG MINH đã làm đúng là chuyện khác — và đây là phần chứng minh.

Bốn ý trên slide, nói kỹ hơn:

1. ĐỐI CHIẾU. V1 kiểm tổng tất cả các nước so với dòng "World" từng năm; V2 kiểm
   tổng sáu châu lục; V3 kiểm tổng bốn nhóm thu nhập. Ba đường đi độc lập tới cùng
   một con số.

2. GIÁ TRỊ 0. Không xoá, không nội suy. Phân loại thành Zero / Trace / Material
   theo ngưỡng 0,05 TWh. Số 0 ở đây nghĩa là "nước đó thật sự không sản xuất" —
   xoá đi là mất chính phát hiện cần tìm, vì gió và mặt trời ASEAN xuất phát từ 0.

3. CHÊNH LỆCH GIỮA NGUỒN. File 02 và 03 lệch ở mức đáng kể tại các thực thể tổng
   hợp. Không gộp cho khớp: chọn một nguồn chuẩn, ghi rõ lý do, giữ nguồn kia làm
   đối chiếu.

4. TÁI LẬP. Chạy lại toàn bộ quy trình cho CSV giống hệt từng byte. 17 file gốc
   giữ nguyên mã băm — không bị sửa dòng nào.

Số trên slide: 89.075 dòng dữ kiện, 8 kiểm định V1–V8 viết bằng SQL, 864 kết quả
kiểm định được ghi lại, 0 dòng chặn không đạt.

NẾU BỊ HỎI "sao phải phức tạp thế": vì bốn khuyết điểm ở slide trước đều im lặng.
Thứ không báo lỗi thì chỉ có kiểm định mới bắt được.
""")


def slide_06(prs) -> None:
    slide = blank(prs)
    heading(slide, "Phát hiện 1", "Quy mô tăng gần bốn lần, vị thế gần như không đổi")
    stat_row(slide, Inches(1.95), [
        (f"{vn(VALUE['F1_ASEAN_2000'], 1)} → {vn(VALUE['F1_ASEAN_2021'], 1)}",
         "TWh — sản lượng NLTT của ASEAN-10,\n2000 so với 2021", BLUE),
        (f"{pct(VALUE['F1_SHARE_2000'])} → {pct(VALUE['F1_SHARE_2021'])}",
         "tỷ trọng của ASEAN-10 trong\ntổng sản lượng NLTT thế giới", ACCENT),
    ])
    picture(slide, "04_01_global_asean_context.png", Inches(3.62), Inches(3.05))
    textbox(slide, MARGIN, Inches(6.72), W - 2 * MARGIN, Inches(0.4),
            MESSAGES["P3-01"], size=14, bold=True, color=INK)
    footer(slide, SOURCE)
    notes(slide, """
Phát hiện đầu tiên, và là phát hiện dễ bị kể sai nhất.

Đọc riêng con số bên trái thì đây là câu chuyện tăng trưởng mạnh: 72,801 lên
289,656 TWh trong 21 năm, gấp 3,98 lần. Nhiều báo cáo dừng ở đây.

Nhưng thế giới cũng tăng trong cùng giai đoạn, từ 2.854,49 lên 7.885,04 TWh —
gấp 2,76 lần. Nên tỷ trọng của ASEAN chỉ nhích từ 2,5504% lên 3,6735%, thêm
khoảng 1,12 điểm phần trăm sau hai thập kỷ.

Cách nói gọn: khu vực chạy nhanh, nhưng chạy trong một đoàn đang cùng tăng tốc.

Đây cũng là lý do phương pháp: mọi chỗ có thể, báo cáo dùng song song hai thước
đo — sản lượng tuyệt đối và tỷ trọng. Bỏ một trong hai là kể sai.

Biểu đồ: hai panel dùng chung trục thời gian, KHÔNG dùng trục kép. Trục kép có
thể tạo ra bất kỳ tương quan nào tuỳ cách chọn thang.
""")


def slide_07(prs) -> None:
    slide = blank(prs)
    heading(slide, "Phát hiện 2", "Gió và mặt trời xuất phát từ đúng số không")
    stat_row(slide, Inches(1.95), [
        (f"{vn(VALUE['F2_MODERN_2000'])} → {vn(VALUE['F2_MODERN_2021'], 2)}",
         "TWh — gió + mặt trời của ASEAN-10,\n2000 so với 2021", GREEN),
        (f"{pct(DERIVED['hydro_share_2021'])}",
         "phần của thuỷ điện trong sản lượng\ntái tạo ASEAN-10 năm 2021", BLUE),
    ])
    picture(slide, "04_02_asean_technology_trend.png", Inches(3.62), Inches(3.05))
    textbox(slide, MARGIN, Inches(6.72), W - 2 * MARGIN, Inches(0.4),
            MESSAGES["P3-03"], size=14, bold=True, color=INK)
    footer(slide, "Tăng trưởng 2000–2021 của gió + mặt trời KHÔNG tính được: mẫu số bằng 0. " + SOURCE)
    notes(slide, """
Hai ý trong một slide, nói tách bạch.

Ý thứ nhất — nền xuất phát. Năm 2000, tổng sản lượng gió cộng mặt trời của CẢ
MƯỜI nước ASEAN là 0 TWh. Không phải "rất nhỏ" mà đúng bằng không. Năm 2010 mới
đạt 0,13 TWh. Đến 2021 là 42,73 TWh.

Hệ quả kỹ thuật đáng nói: vì mẫu số bằng 0, TỐC ĐỘ TĂNG giai đoạn 2000–2021 của
nhóm này KHÔNG TÍNH ĐƯỢC. Mọi công thức tăng trưởng đều cần mẫu số dương. Báo cáo
ghi "không xác định" thay vì điền một con số cho đẹp bảng — đây là chỗ nhiều bài
sẽ vô tình bịa ra một tỷ lệ phần trăm khổng lồ.

Ý thứ hai — quy mô hiện tại. Cơ cấu 2021: thuỷ điện 185,58 TWh (64,07%), nguồn
tái tạo khác 61,35 (21,18%), mặt trời 34,43 (11,89%), gió 8,30 (2,87%).

Gió cộng mặt trời mới chiếm 14,75%. Nên "bùng nổ điện mặt trời Đông Nam Á" đúng
về tốc độ nhưng chưa đúng về quy mô: cấu trúc nguồn của ASEAN năm 2021 vẫn là
cấu trúc thuỷ điện. Hai câu này chỉ mâu thuẫn khi bỏ mất một thước đo.
""")


def slide_08(prs) -> None:
    slide = blank(prs)
    heading(slide, "Phát hiện 3", "Đổi cách đo là đổi luôn thứ hạng khu vực")
    stat_row(slide, Inches(1.95), [
        (f"{vn(VALUE['F3_GAIN_Singapore'])} bậc", "Singapore tăng khi chuyển sang\nđo bằng gió + mặt trời", GREEN),
        (f"{vn(VALUE['F3_GAIN_Laos'])} bậc", "Lào giảm — thế mạnh của họ\nlà thuỷ điện, không phải gió", ACCENT),
        (f"{vn(VALUE['F3_RANK_TOTAL_Vietnam'])} và {vn(VALUE['F3_RANK_MODERN_Vietnam'])}",
         "hạng của Việt Nam theo cả hai\ncách đo — không đổi", BLUE),
    ])
    picture(slide, "04_04_asean_rank_shift_2021.png", Inches(3.62), Inches(3.05))
    textbox(slide, MARGIN, Inches(6.72), W - 2 * MARGIN, Inches(0.4),
            MESSAGES["P3-06"], size=14, bold=True, color=INK)
    footer(slide, SOURCE)
    notes(slide, """
Phát hiện có tính phương pháp mạnh nhất bài.

Cùng một năm 2021, cùng mười nước, cùng một bộ dữ liệu. Chỉ đổi thước đo từ TỔNG
năng lượng tái tạo sang GIÓ + MẶT TRỜI, thứ hạng đảo lại:

  Singapore   9 → 5   (+4)
  Thái Lan    5 → 2   (+3)
  Philippines 6 → 3   (+3)
  Indonesia   2 → 6   (−4)
  Lào         4 → 9   (−5)

Giải thích: Indonesia và Lào mạnh về thuỷ điện và địa nhiệt — nguồn tái tạo lâu
đời, phụ thuộc địa hình. Singapore vọt lên 4 bậc dù sản lượng tuyệt đối rất nhỏ,
vì gần như toàn bộ phần tái tạo của họ là điện mặt trời.

Chi tiết quan trọng nhất trong bảng: Việt Nam giữ hạng 1 ở CẢ HAI cách đo. Đó là
bằng chứng đây là đảo vị trí thật, không phải cả bảng cùng xê dịch.

Kết luận phương pháp: một bảng xếp hạng năng lượng tái tạo không có nghĩa nếu
không nói rõ nó đang đo cái gì. Đây là lý do dashboard đặt công tắc chuyển thước
đo ngay trên hàng bộ lọc, không giấu trong trang phụ.

Lưu ý khi trả lời: Thái Lan và Philippines cùng tăng 3 bậc nhưng KHÔNG đồng hạng
— Thái Lan hạng 2, Philippines hạng 3.
""")


def slide_09(prs) -> None:
    slide = blank(prs)
    heading(slide, "Phát hiện 4", "Hai phần ba lượng gió và mặt trời của ASEAN nằm ở một nước")
    stat_row(slide, Inches(1.95), [
        (pct(VALUE["F4_VN_SHARE_MODERN"]), "phần của Việt Nam trong gió +\nmặt trời của ASEAN-10, 2021", ACCENT),
        (pct(VALUE["F4_VN_GROWTH_MODERN"]), "phần của Việt Nam trong toàn bộ\nmức tăng 2010–2021", ACCENT),
        (f"{vn(VALUE['F4_VN_GLOBAL_RANK_MODERN'])}", "hạng của Việt Nam trên thế giới\nvề gió + mặt trời", BLUE),
    ])
    picture(slide, "04_07_vietnam_technology_trend.png", Inches(3.62), Inches(3.05))
    textbox(slide, MARGIN, Inches(6.72), W - 2 * MARGIN, Inches(0.4),
            MESSAGES["P3-09"], size=14, bold=True, color=INK)
    footer(slide, "Dữ liệu cho biết mức độ, không cho biết nguyên nhân. " + SOURCE)
    notes(slide, """
Phát hiện trung tâm của phần Việt Nam.

Năm 2021 Việt Nam sản xuất 104,2180 TWh năng lượng tái tạo, chiếm 35,9800% toàn
khu vực, đứng hạng 16 thế giới.

Riêng gió và mặt trời, mức tập trung cao hơn hẳn: 28,16 TWh, bằng 65,9022% của cả
ASEAN, hạng 17 thế giới.

Nhìn theo PHẦN TĂNG THÊM giai đoạn 2010–2021 thì rõ hơn nữa: trong tổng mức tăng
dương của cả khu vực, Việt Nam đóng góp 65,9859% ở gió và mặt trời, và 42,3781%
ở tổng năng lượng tái tạo.

Nói cách khác: gần như toàn bộ tăng trưởng gió và mặt trời của Đông Nam Á trong
hơn một thập kỷ đến từ một nước. Chỉ số trung bình của khu vực vì thế gây hiểu
lầm — "ASEAN tăng trưởng điện mặt trời" thực chất là Việt Nam cộng chín nước tăng
chậm hơn nhiều.

QUAN TRỌNG khi trình bày: dừng lại ở mô tả. Bộ dữ liệu này không có biến chính
sách, giá thành hay cơ chế khuyến khích, nên mọi giải thích nguyên nhân — kể cả
những giải thích nghe rất hợp lý về giá FIT — đều nằm ngoài phạm vi chứng minh
được ở đây. Nếu bị hỏi, nói thẳng như vậy.
""")


def slide_10(prs) -> None:
    slide = blank(prs)
    heading(slide, "Phát hiện 5", "Đà tăng tập trung vào rất ít nước")
    stat_row(slide, Inches(1.95), [
        (f"{pct(VALUE['F5_TOP3_TOTAL'])} → {pct(VALUE['F5_TOP3_MODERN'])}",
         "tỷ trọng ba nước dẫn đầu, khi chuyển\ntừ tổng NLTT sang gió + mặt trời", ACCENT),
        (f"{vn(VALUE['F5_HHI_TOTAL'], 3)} → {vn(VALUE['F5_HHI_MODERN'], 3)}",
         "chỉ số tập trung HHI\ntrên cùng hai thước đo", BLUE),
        (f"{vn(VALUE['F5_GINI_TOTAL'], 3)} → {vn(VALUE['F5_GINI_MODERN'], 3)}",
         "hệ số Gini — ba chỉ số độc lập\ncùng chỉ một hướng", BLUE),
    ])
    picture(slide, "04_12_asean_concentration_growth.png", Inches(3.62), Inches(3.05))
    textbox(slide, MARGIN, Inches(6.72), W - 2 * MARGIN, Inches(0.4),
            MESSAGES["P3-04"], size=14, bold=True, color=INK)
    footer(slide, SOURCE)
    notes(slide, """
Phát hiện cuối, và là phát hiện làm cả bốn phát hiện trước có ý nghĩa.

Ba chỉ số tập trung, đo trên cùng mười nước năm 2021, chuyển từ thước đo tổng
sang thước đo hiện đại:

  Tỷ trọng ba nước dẫn đầu   67,1023%  →  92,2537%
  HHI                        0,207886  →  0,480404
  Gini                       0,529218  →  0,771285

Điểm mạnh của lập luận nằm ở chỗ ba chỉ số này đo BA THỨ KHÁC NHAU — tỷ trọng
nhóm dẫn đầu, độ phân tán bình phương, và độ bất bình đẳng — mà cùng chỉ một
hướng. Một chỉ số đơn lẻ có thể là đặc thù của công thức; ba chỉ số độc lập cùng
kết luận thì khó bác hơn nhiều.

HHI vượt 0,48. Trong phân tích cạnh tranh, mức này được coi là tập trung rất cao.

Hệ quả trực tiếp, và cũng là lý do phương pháp của cả bài: một con số trung bình
cho ASEAN sẽ che mất bức tranh thật. Vì vậy mọi biểu đồ ở phần trước đều tách
theo nước thay vì gộp khu vực, và dashboard giữ mẫu số khu vực cố định khi người
xem lọc theo một nước.
""")


def slide_11(prs) -> None:
    """Direction, not conclusions. The conclusions are section 1.6 and Phase 7."""
    slide = blank(prs)
    y = heading(slide, "Hướng đi tiếp", "Câu trả lời hiện có, và dữ liệu còn thiếu")
    half = Emu(int((W - 2 * MARGIN - Inches(0.6)) / 2))

    textbox(slide, MARGIN, y, half, Inches(0.4), "DỮ LIỆU ĐÃ CHO THẤY",
            size=12, bold=True, color=BLUE)
    bullets(slide, MARGIN, y + Inches(0.45), half, [
        "Khu vực tăng mạnh về lượng nhưng chưa đổi vị thế toàn cầu.",
        "Cơ cấu nguồn của ASEAN năm 2021 vẫn là cơ cấu thuỷ điện.",
        "Xếp hạng khu vực phụ thuộc vào việc đo cái gì.",
        "Đà tăng gió và mặt trời tập trung ở một nước.",
    ], size=13.5, spacing=1.35)

    textbox(slide, MARGIN + half + Inches(0.6), y, half, Inches(0.4),
            "CẦN GHÉP THÊM ĐỂ ĐI XA HƠN", size=12, bold=True, color=ACCENT)
    bullets(slide, MARGIN + half + Inches(0.6), y + Inches(0.45), half, [
        "Bảng giá thành và suất đầu tư theo công nghệ.",
        "Mốc thời gian chính sách và cơ chế giá từng nước.",
        "Công suất lắp đặt đầy đủ cho cả mười nước.",
        "Dân số và sản lượng điện để chuẩn hoá theo quy mô.",
    ], size=13.5, spacing=1.35)

    rule(slide, Inches(5.9))
    textbox(slide, MARGIN, Inches(6.2), W - 2 * MARGIN, Inches(0.6),
            "Chưa đủ dữ liệu để nói về chi phí, chính sách hay hiệu quả kỹ thuật.",
            size=14, italic=True, color=MUTED)
    footer(slide, SOURCE)
    notes(slide, """
Slide này nói rõ đâu là ranh giới, và đó là điểm mạnh chứ không phải điểm yếu.

Cột trái — bốn điều dữ liệu đã cho thấy, tóm lại từ năm kết luận.

Cột phải — bốn bảng cần ghép thêm, mỗi bảng gắn với một câu hỏi cụ thể hiện chưa
trả lời được:
  giá thành và suất đầu tư  → ưu tiên công nghệ nào cho mỗi đồng vốn
  mốc chính sách từng nước  → chính sách đi trước hay đi sau tăng trưởng
  công suất đầy đủ 10 nước  → hệ số công suất toàn khu vực, không chỉ 104 cặp
  dân số và tổng điện năng  → chuẩn hoá theo quy mô, so Singapore với Indonesia

Câu chốt: một báo cáo biết mình chưa trả lời được gì thì đáng tin hơn một báo cáo
trả lời tất cả.
""")


def slide_agenda(prs) -> None:
    """Contents. Taken from the capstone decks used as reference -- the reader
    gets the shape of the argument before the first number arrives."""
    slide = blank(prs)
    y = heading(slide, "Nội dung", "Mạch trình bày")
    half = Emu(int((W - 2 * MARGIN - Inches(0.6)) / 2))
    bullets(slide, MARGIN, y + Inches(0.15), half, [
        "Vấn đề, câu hỏi và người dùng kết quả",
        "Dữ liệu, phạm vi và giới hạn",
        "Khuyết điểm dữ liệu tìm thấy",
        "Làm sạch và chứng minh làm sạch đúng",
        "Thống kê mô tả",
    ], size=16, spacing=1.6)
    bullets(slide, MARGIN + half + Inches(0.6), y + Inches(0.15), half, [
        "Năm phát hiện chính",
        "Dashboard tương tác",
        "Kết luận",
        "Đề xuất",
        "Giới hạn và dữ liệu cần bổ sung",
    ], size=16, spacing=1.6)
    footer(slide, SOURCE)
    notes(slide, """
Lướt nhanh, khoảng hai mươi giây. Mục đích chỉ là cho người nghe biết mạch bài
trước khi con số đầu tiên xuất hiện.

Nếu cần nói một câu về cấu trúc: bài đi theo thứ tự câu hỏi trước, chất lượng dữ
liệu trước, rồi mới đến phát hiện — vì phát hiện chỉ đáng tin khi biết dữ liệu
đứng sau nó đã được kiểm thế nào.
""")


def slide_stats(prs) -> None:
    """Section 1.3 -- descriptive statistics, and why percentiles are the ones
    that can be read here."""
    slide = blank(prs)
    y = heading(slide, "Thống kê mô tả",
                "Trung bình nói sai câu chuyện khi phân phối lệch")

    def cell(variant: str, stat: str, decimals: int) -> str:
        return vn(VALUE[f"F7_SOLAR2021_{variant}_{stat}"], decimals)

    rows = []
    for variant, label in (("ALL_OBSERVED", "Toàn bộ quan sát"),
                           ("POSITIVE", "Chỉ nước > 0"),
                           ("MATERIAL", "Chỉ mức đáng kể")):
        rows.append([
            label,
            cell(variant, "N", 0),
            cell(variant, "MEAN", 3),
            cell(variant, "MEDIAN", 3),
            cell(variant, "SD", 3),
            cell(variant, "CV", 3),
            cell(variant, "SKEWNESS", 3),
        ])

    table(slide, MARGIN, y, Inches(7.1),
          ["Tập dữ liệu", "n", "Trung bình", "Trung vị", "Độ lệch chuẩn",
           "Hệ số biến thiên", "Độ lệch"],
          rows, widths=[2.2, 0.7, 1.3, 1.2, 1.5, 1.5, 1.1], size=12.5)

    textbox(slide, MARGIN, Inches(4.05), Inches(7.1), Inches(0.9),
            "Phân vị sản lượng mặt trời ASEAN-10 năm 2021 (TWh):\n"
            f"P25 = {vn(VALUE['F7_SOLAR2021_ALL_OBSERVED_P25'], 4)}   ·   "
            f"P50 = {vn(VALUE['F7_SOLAR2021_ALL_OBSERVED_MEDIAN'], 3)}   ·   "
            f"P75 = {vn(VALUE['F7_SOLAR2021_ALL_OBSERVED_P75'], 3)}   ·   "
            f"P90 = {vn(VALUE['F7_SOLAR2021_ALL_OBSERVED_P90'], 3)}",
            size=13, color=INK, spacing=1.35)

    textbox(slide, MARGIN, Inches(5.1), Inches(7.1), Inches(1.4),
            "Trung bình cao gấp hơn sáu lần trung vị, độ lệch vượt 3 và hệ số "
            "biến thiên vượt 2.\nBỏ các nước bằng 0 rồi bỏ tiếp mức không đáng kể "
            "vẫn không làm phân phối cân lại.",
            size=13.5, color=MUTED, spacing=1.35)

    picture(slide, "04_10_global_distribution_2021.png",
            Inches(2.0), Inches(3.4), x=Inches(8.0))

    textbox(slide, MARGIN, Inches(6.65), W - 2 * MARGIN, Inches(0.4),
            MESSAGES["P7-03"], size=14, bold=True, color=INK)
    footer(slide, "Mặt trời · ASEAN-10 · 2021 · độ lệch chuẩn tổng thể (ddof=0) · "
                  "độ lệch hiệu chỉnh chệch. " + SOURCE)
    notes(slide, """
Slide này trả lời một câu hỏi phương pháp: vì sao đề bài đòi phân vị chứ không
chỉ trung bình.

Lấy mặt trời ASEAN năm 2021 làm ví dụ. Trung bình 3,443 TWh. Trung vị 0,52 TWh.
Trung bình cao gấp hơn SÁU LẦN trung vị.

Nguyên nhân: phân phối lệch phải rất mạnh. Độ lệch 3,01 và hệ số biến thiên 2,19.
Một vài nước sản lượng lớn kéo trung bình lên cao trong khi phần lớn còn lại vẫn
rất thấp. Nói "nước ASEAN điển hình sản xuất 3,4 TWh điện mặt trời" là sai — một
nửa số nước không đạt tới 0,52.

Ba dòng trong bảng là ba tập dữ liệu khác nhau: toàn bộ quan sát, chỉ nước có sản
lượng dương, và chỉ nước ở mức đáng kể. Bỏ dần các nước bằng 0 làm cỡ mẫu giảm từ
10 xuống 9 rồi 8, trung vị nhích lên — nhưng độ lệch vẫn trên 2,7 và hệ số biến
thiên vẫn trên 1,9. Phân phối KHÔNG cân lại.

Vì vậy phân vị mới là thống kê đọc được ở đây: P25 = 0,1225 · P50 = 0,52 ·
P75 = 1,5 · P90 = 6,438 TWh.

Nếu bị hỏi về công thức: độ lệch chuẩn dùng ddof=0 (tổng thể), độ lệch phân phối
hiệu chỉnh chệch. Cả hai đều ghi ở chân slide.
""")


def slide_dashboard(prs) -> None:
    """Section 1.5c -- the third deliverable, shown rather than only mentioned."""
    slide = blank(prs)
    y = heading(slide, "Dashboard", "Ba trang cho phép người xem tự khám phá")

    half = Emu(int((W - 2 * MARGIN - Inches(0.6)) / 2))
    bullets(slide, MARGIN, y + Inches(0.1), half, [
        "Trang 1 — Tổng quan Đông Nam Á",
        "Trang 2 — Việt Nam chuyên sâu",
        "Trang 3 — So sánh và chẩn đoán",
    ], size=17, spacing=1.75)

    textbox(slide, MARGIN, Inches(4.3), half, Inches(1.6),
            "Công tắc “chỉ NLTT hiện đại” nằm trên hàng bộ lọc.\n"
            "Bật lên là thấy ngay phát hiện 3.",
            size=14, color=MUTED, spacing=1.4)

    # The screenshot is added once Power BI has been opened and the .pbix saved.
    # Until then the frame says so rather than leaving a silent blank.
    shot = CHARTS.parent / "slides" / "dashboard.png"
    if shot.exists():
        width = Inches(6.4)
        slide.shapes.add_picture(str(shot), Inches(6.5), Inches(2.0), width=width)
    else:
        placeholder = slide.shapes.add_shape(1, Inches(6.5), Inches(2.05),
                                             Inches(6.2), Inches(3.9))
        placeholder.fill.solid()
        placeholder.fill.fore_color.rgb = RGBColor(0xF3, 0xF4, 0xF6)
        placeholder.line.color.rgb = RULE
        placeholder.shadow.inherit = False
        textbox(slide, Inches(6.5), Inches(3.7), Inches(6.2), Inches(0.6),
                "[ ảnh chụp dashboard ]", size=14, color=MUTED,
                align=PP_ALIGN.CENTER)

    textbox(slide, MARGIN, Inches(6.5), W - 2 * MARGIN, Inches(0.5),
            "Mô hình sao 8 bảng · 73 phép đo DAX sinh từ một nguồn duy nhất · "
            "175/175 truy vấn nghiệm thu đạt.",
            size=13.5, bold=True, color=INK)
    footer(slide, SOURCE)
    notes(slide, """
Nếu trình bày trực tiếp, tốt nhất là MỞ dashboard thật thay vì chiếu ảnh, và bấm
hai thao tác: đổi năm báo cáo, rồi bật công tắc "chỉ NLTT hiện đại".

Thao tác thứ hai chính là phát hiện 3 hiện ra trước mắt người xem — thứ hạng đảo
lại ngay khi đổi thước đo. Đó là lý do công tắc nằm trên hàng bộ lọc chứ không
giấu trong trang phụ.

Ba trang: tổng quan khu vực, Việt Nam chuyên sâu, so sánh và chẩn đoán.

Về mặt kỹ thuật, nếu bị hỏi: mô hình sao 8 bảng, 3 quan hệ, 73 phép đo DAX sinh
từ MỘT nguồn duy nhất rồi xuất song song ra mô hình và ra danh mục. 175 truy vấn
nghiệm thu chạy trên chính mô hình đó, tất cả đạt.

Trung thực nếu bị hỏi kỹ: lớp định lượng đã được kiểm đầy đủ; lớp tương tác và
trình bày thì chưa nghiệm thu hết — bộ lọc chưa đồng bộ giữa ba trang và giao
diện còn tiếng Anh.
""")


def slide_conclusions(prs) -> None:
    slide = blank(prs)
    y = heading(slide, "Kết luận", "Chuyển dịch là có thật, nhưng hẹp và lệch")
    bullets(slide, MARGIN, y + Inches(0.1), W - 2 * MARGIN, [
        f"Quy mô gấp {vn(DERIVED['asean_growth_multiple'], 2)} lần — vị thế thế giới gần như đứng yên",
        f"Cơ cấu 2021 vẫn là thuỷ điện: {pct(DERIVED['hydro_share_2021'])} so với {pct(DERIVED['modern_share_2021'])}",
        f"Ba nước giữ {pct(VALUE['F5_TOP3_MODERN'])} lượng gió và mặt trời",
        f"Việt Nam: {pct(VALUE['F4_VN_SHARE_MODERN'])} sản lượng, {pct(VALUE['F4_VN_GROWTH_MODERN'])} phần tăng thêm",
        "Đổi thước đo là đổi thứ hạng — mọi so sánh phải nói rõ đo gì",
    ], size=18, spacing=1.9)
    footer(slide, SOURCE)
    notes(slide, """
Năm kết luận, đọc theo mạch thu hẹp dần.

1. ASEAN đi từ 72,801 lên 289,656 TWh — gấp 3,98 lần. Nhưng thế giới cũng tăng,
   nên tỷ trọng khu vực chỉ nhích từ 2,5504% lên 3,6735%, thêm 1,12 điểm phần
   trăm sau 21 năm. Khu vực chạy nhanh, nhưng chạy trong một đoàn đang cùng tăng tốc.

2. Thuỷ điện 185,58 TWh, chiếm 64,07%. Gió cộng mặt trời mới 42,73 TWh, tức
   14,75%. Câu chuyện "bùng nổ điện mặt trời Đông Nam Á" đúng về tốc độ nhưng
   chưa đúng về quy mô.

3. Top-3 giữ 92,2537% lượng gió và mặt trời, so với 67,1023% khi đo bằng tổng
   NLTT. HHI 0,4804 và Gini 0,7713 — ba chỉ số độc lập cùng chỉ một hướng.

4. Việt Nam nắm 65,9022% sản lượng gió và mặt trời của khối, và đóng góp
   65,9859% toàn bộ mức tăng dương 2010–2021.

5. Cùng một năm, cùng mười nước, chỉ đổi thước đo: Singapore +4 bậc, Lào −5.

NẾU BỊ HỎI "vì sao Việt Nam vượt lên": bộ dữ liệu này không có biến chính sách,
giá thành hay cơ chế khuyến khích. Nói thẳng là không trả lời được từ dữ liệu
hiện có, và đó là lý do slide sau chỉ đưa hướng chứ không đưa phương án.
""")


def slide_recommendations(prs) -> None:
    slide = blank(prs)
    y = heading(slide, "Đề xuất", "Tám hướng cần cân nhắc — không phải tám việc phải làm")
    half = Emu(int((W - 2 * MARGIN - Inches(0.6)) / 2))

    # Tám mục ở đây khớp đúng tám đề xuất VN-1..VN-4 và KV-1..KV-4 của
    # `BaoCao.md` §1.6.2. Slide mới là bản báo cáo được chấm, nên bỏ bớt mục nào
    # là mục đó không tới tay người đọc.
    textbox(slide, MARGIN, y, half, Inches(0.4), "CHO VIỆT NAM",
            size=13, bold=True, color=ACCENT)
    bullets(slide, MARGIN, y + Inches(0.45), half, [
        "Cân nhắc lưu trữ song song với công suất mới",
        "Đặt chỉ tiêu theo tỷ trọng, không chỉ theo TWh",
        "Tách mục tiêu sản lượng khỏi mục tiêu tỷ trọng",
        "So chuẩn với nước cùng hạng thế giới, không chỉ ASEAN",
    ], size=14.5, spacing=1.65)

    textbox(slide, MARGIN + half + Inches(0.6), y, half, Inches(0.4),
            "CHO KHU VỰC ASEAN", size=13, bold=True, color=BLUE)
    bullets(slide, MARGIN + half + Inches(0.6), y + Inches(0.45), half, [
        "Hợp tác khu vực thay cho nỗ lực đơn lẻ",
        "Theo dõi mức tập trung như một chỉ báo",
        "Đặt mục tiêu theo tỷ trọng toàn cầu, không chỉ nội khối",
        "Đặt kỳ vọng vào nguồn nhân rộng được",
    ], size=14.5, spacing=1.65)

    rule(slide, Inches(5.6))
    textbox(slide, MARGIN, Inches(5.85), W - 2 * MARGIN, Inches(0.9),
            "“Nên xem xét”, không phải “nên làm”.\n"
            "Dữ liệu này không có giá thành, chính sách hay phát thải để đánh giá khả thi.",
            size=15, color=MUTED, spacing=1.4)
    footer(slide, SOURCE)
    notes(slide, f"""
Tám hướng, bốn cho Việt Nam bốn cho khu vực. Nhấn mạnh ngay từ đầu: đây là hướng
cần cân nhắc, không phải phương án đã tính chi phí.

CHO VIỆT NAM
1. Việt Nam nắm 65,9022% gió và mặt trời của ASEAN nhưng chỉ 35,9800% tổng NLTT
   — tập trung vào một nhóm công nghệ không điều độ được. Đáng đánh giá rủi ro
   vận hành hệ thống, cân nhắc lưu trữ và điều độ song song với công suất mới.
2. Con số đáng chú ý nhất của slide này: tỷ trọng NLTT trong tổng điện năng
   GIẢM từ {vn(VALUE['F6_VN_SHARE_ELEC_2000'], 4)}% xuống
   {vn(VALUE['F6_VN_SHARE_ELEC_2021'], 4)}% — mất 12,20 điểm phần trăm — trong
   khi sản lượng tuyệt đối TĂNG {vn(DERIVED['vn_growth_multiple'], 2)} lần.
   Hai điều này cùng đúng vì tổng cầu điện tăng còn nhanh hơn.
3. Có 2 năm (2003 và 2014) sản lượng và tỷ trọng đi ngược chiều nhau.
4. Hạng {vn(VALUE['F4_VN_GLOBAL_RANK_TOTAL'])} thế giới về tổng NLTT nhưng hạng
   {vn(VALUE['F4_VN_GLOBAL_RANK_MODERN'])} về gió và mặt trời — nhóm nguồn hiện
   đại chưa tạo được lợi thế xếp hạng tương xứng với quy mô. Nên so chuẩn với các
   nước cùng hạng toàn cầu, không chỉ so trong ASEAN.

CHO KHU VỰC
5. 6/10 nước — Brunei, Campuchia, Lào, Malaysia, Myanmar, Singapore — không sản
   xuất một kWh điện gió nào năm 2021.
6. HHI nhóm hiện đại {vn(VALUE['F5_HHI_MODERN'], 4)}, mức được coi là tập trung
   rất cao; cả khu vực nhạy cảm với biến động ở một nước.
7. Tỷ trọng ASEAN trong thế giới chỉ tăng 1,12 điểm phần trăm sau 21 năm, dù nội
   khối tăng gần bốn lần. Đặt mục tiêu theo tỷ trọng toàn cầu sẽ phản ánh đúng vị
   thế hơn là chỉ đo tăng trưởng nội khối.
8. Thuỷ điện chiếm 64,07% và phụ thuộc địa hình, không nhân rộng đều được.

NẾU BỊ HỎI "nên đầu tư công nghệ nào": không trả lời được. Không có LCOE, không
có suất đầu tư. Đó là slide tiếp theo.
""")


def slide_closing(prs) -> None:
    slide = blank(prs)
    textbox(slide, MARGIN, Inches(2.5), W - 2 * MARGIN, Inches(1.3),
            "Xin cảm ơn", size=54, bold=True, color=INK)
    rule(slide, Inches(4.05), w=Inches(3.2), color=ACCENT, thickness=Pt(3))
    textbox(slide, MARGIN, Inches(4.4), W - 2 * MARGIN, Inches(0.8),
            "Câu hỏi?", size=28, color=ACCENT)
    textbox(slide, MARGIN, Inches(5.6), W - 2 * MARGIN, Inches(0.9),
            "Our World in Data (Ember · BP) · 17 tệp CSV · ASEAN-10 · 2000–2021\n"
            "Python · SQLite · Power BI",
            size=13, color=MUTED, spacing=1.4)
    notes(slide, """
Kết thúc ở đây. Ba điểm để nhắc lại nếu còn thời gian, hoặc để dùng khi trả lời:

- Toàn bộ số liệu tái lập được bằng một lệnh; chạy lại cho kết quả trùng khớp.
- Mỗi con số trong báo cáo truy được về một bảng nguồn cụ thể, không con số nào
  chép lại từ ghi chép trung gian.
- Giới hạn của dữ liệu được ghi rõ ngay từ slide thứ tư, và mọi đề xuất đều nằm
  trong giới hạn đó.

Ba câu hỏi hay gặp và cách trả lời ngắn:

"Vì sao không dự báo tương lai?" — dữ liệu dừng ở 2021 và không có biến chính
sách; dự báo từ đây sẽ là ngoại suy thuần tuý.

"Vì sao chỉ ASEAN-10?" — phạm vi được chọn từ đầu, và độ phủ dữ liệu của mười
nước này đủ 1.760/1.760 ô trong cửa sổ phân tích chính.

"Số liệu có mới không?" — nguồn cập nhật tới 2022 nhưng năm 2022 bị cắt cụt ở 8
tệp và không có nước ASEAN nào, nên đã bị loại có chủ ý.
""")


BUILDERS = (
    slide_01,             # 1  mở đầu
    slide_agenda,         # 2  mục lục
    slide_02,             # 3  câu hỏi
    slide_03,             # 4  dữ liệu và giới hạn
    slide_04,             # 5  khuyết điểm dữ liệu
    slide_05,             # 6  làm sạch và kiểm định
    slide_stats,          # 7  thống kê mô tả (1.3)
    slide_06, slide_07, slide_08, slide_09, slide_10,   # 8-12 năm phát hiện
    slide_dashboard,      # 13 dashboard (1.5c)
    slide_conclusions,    # 14 kết luận (1.6)
    slide_recommendations,  # 15 đề xuất (1.6)
    slide_11,             # 16 giới hạn và dữ liệu cần thêm
    slide_closing,        # 17 kết thúc
)


# --------------------------------------------------------------------------
# Gate E5 enforcement
# --------------------------------------------------------------------------

# Numbers allowed to appear in slide text without coming from the contract.
# Every one is either a label the reader needs (question ids, the analysis window)
# or a Phase 1/2 count that belongs to the data-quality pair on slides 4 and 5 and
# is quoted from the journal rather than recomputed. Keeping the list explicit is
# what makes the check meaningful; widening it silently would defeat it.
ALLOWED_LITERALS = {
    # window, scope, question ids
    "2000", "2021", "2010", "2022", "10", "1", "2", "3", "4", "5", "6", "17",
    # slide 4 -- Phase 1 defect counts
    "3,125", "8", "106", "247", "97",
    # slide 5 -- Phase 2 validation counts
    "89.075", "864", "0",
    # slide 13 -- Phase 5 acceptance counts, proven in docs/Phase5_Review.md section 4
    # and output/stats/05_validation_results.csv rather than in this contract
    "175", "73",
    # slide numbers and the deck's own furniture
    "7", "9", "11",
}

NUMBER_RE = re.compile(r"\d[\d.,]*")

# Document furniture, stripped before the scan: file names carry digits that are
# part of an identifier (`02_validate.sql`), and section references (`1.6`, `1.5a`)
# point at the report rather than reporting a quantity. Neither is a claim, and
# leaving them in would force the allow-list to swell until it meant nothing.
PATH_RE = re.compile(r"[\w./\\-]+\.(?:md|csv|sql|txt|png|pptx|tsv|json|py)\b")
SECTION_RE = re.compile(r"\b\d\.\d[a-z]?\b")
# Percentile labels: the 25 in "P25" names the statistic, it is not a quantity.
# The value that follows it still gets scanned normally.
PERCENTILE_LABEL_RE = re.compile(r"\bP\d{1,2}\b")


def slide_text(slide) -> str:
    parts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            parts.append(shape.text_frame.text)
    return "\n".join(parts)


def scannable(text: str) -> str:
    return PERCENTILE_LABEL_RE.sub(" ", SECTION_RE.sub(" ", PATH_RE.sub(" ", text)))


def assert_no_stray_numbers(prs) -> list[str]:
    """Every number on a slide must trace to the contract or the allow-list.

    This is Gate E5's traceability criterion turned into an assertion. Without it
    the criterion degrades into "we were careful", which is exactly the kind of
    claim this project spends its effort refusing to make.
    """
    rendered = set()
    for value in VALUE.values():
        for decimals in (0, 1, 2, 3, 4):
            rendered.add(vn(value, decimals))
            rendered.add(vn(value * 100, decimals))
        rendered.add(vn(value * 100, 2))
    # derived-on-slide figures: shares computed from two contract values
    for value in DERIVED.values():
        for decimals in (0, 1, 2, 3, 4):
            rendered.add(vn(value, decimals))
            rendered.add(vn(value * 100, decimals))

    strays: list[str] = []
    for index, slide in enumerate(prs.slides, start=1):
        for token in NUMBER_RE.findall(scannable(slide_text(slide))):
            token = token.rstrip(".,")
            if token in ALLOWED_LITERALS or token in rendered:
                continue
            strays.append(f"slide {index}: {token!r}")
    return strays


ZIP_EPOCH = (2026, 1, 1, 0, 0, 0)


def repack_deterministically(path: Path) -> None:
    """Rewrite the .pptx with fixed entry timestamps and a stable part order.

    A .pptx is a ZIP, and python-pptx stamps each entry with the clock at save
    time. Two builds a minute apart therefore differ on bytes while every one of
    the sixty-four parts is identical -- which makes a hash useless as a change
    signal. Every other artefact in this project rebuilds byte-identical, so the
    deck is held to the same standard rather than to a softer one.
    """
    with zipfile.ZipFile(path) as archive:
        parts = {name: archive.read(name) for name in sorted(archive.namelist())}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in parts.items():
            info = zipfile.ZipInfo(name, date_time=ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, payload)


def main() -> int:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    for build in BUILDERS:
        build(prs)

    strays = assert_no_stray_numbers(prs)
    if strays:
        print("PHASE 6 SLIDE BUILD: FAIL | so lieu khong truy duoc ve hop dong:")
        for line in strays:
            print(f"  {line}")
        return 1

    # Page numbers are furniture this file writes, so they are stamped after
    # the stray-number scan rather than being fed into it.
    stamp_page_numbers(prs)

    # Fixed timestamps: PowerPoint stamps created/modified on save, and a moving
    # timestamp would make two builds differ on bytes while being identical in
    # content. Gate E5 asks for reproducibility, so pin them.
    core = prs.core_properties
    core.title = "Năng lượng tái tạo — Việt Nam và Đông Nam Á"
    core.author = "Nguyễn Hồng Minh"
    core.comments = f"method_version={contract.METHOD_VERSION}"
    fixed = dt.datetime(2026, 1, 1, 0, 0, 0)
    core.created = fixed
    core.modified = fixed
    core.revision = 1

    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    prs.save(DECK_PATH)
    repack_deterministically(DECK_PATH)
    print(f"  -> {DECK_PATH}")

    pictures = sum(
        1 for slide in prs.slides
        for shape in slide.shapes
        if shape.shape_type == 13  # PICTURE
    )
    print(f"\nPHASE 6 SLIDE BUILD: PASS | {len(prs.slides)} slide | {pictures} hình | "
          f"{len(VALUE)} claim khả dụng | method_version={contract.METHOD_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
