"""Kiểm tra dấu vết soạn thảo trong nội dung hai tài liệu bàn giao."""
from __future__ import annotations
import ast
import io
import re
import tokenize


INTERNAL = re.compile(
    r"\b(?:Phase\s*\d+|Gate\s*[A-Z]\d+|Q[1-6]|V[1-8]|P[1-8]-\d+|F[1-7](?:_\w+)?|TODO|FIXME|PASS|WARN|FAIL)\b"
    r"|method_version|phase\d+_v\d+|\[\s*ảnh chụp|[A-Za-z]:[\\/]"
    r"|(?:output|python)[/\\](?:stats|clean|\d)|(?:03_fact_metrics|04_chart_data)"
    r"|gần như toàn bộ|nói sai câu chuyện|khó bác hơn|không câu nào.*bỏ ngỏ"
    r"|đúng số không|chứng minh đã làm đúng|cú sụt giả|mẫu số động",
    re.IGNORECASE,
)


def assert_reader_text(chunks):
    problems = []
    for where, text in chunks:
        for match in INTERNAL.finditer(text):
            problems.append(f"{where}: {match.group(0)}")
    if problems:
        raise AssertionError("Nội dung còn dấu vết soạn thảo:\n" + "\n".join(problems))


def notebook_chunks(notebook):
    for i, cell in enumerate(notebook["cells"], 1):
        source = cell["source"]
        if not isinstance(source, str):
            source = "".join(source)
        if cell["cell_type"] == "markdown":
            yield f"Ô {i}, văn bản", source
        else:
            # Tên biến/hàm và giá trị phân lớp cần cho dữ liệu là ngoại lệ kỹ thuật.
            # Chuỗi lời đọc, truy vấn và chú thích vẫn phải qua kiểm tra.
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type in (tokenize.COMMENT, tokenize.STRING):
                    yield f"Ô {i}, dòng {token.start[0]}", token.string
            for output in cell.get("outputs", []):
                for key, value in output.get("data", {}).items():
                    if key in {"text/plain", "text/html", "image/svg+xml"}:
                        yield f"Ô {i}, kết quả", value if isinstance(value, str) else "".join(value)
                if "text" in output:
                    value = output["text"]
                    yield f"Ô {i}, thông báo", value if isinstance(value, str) else "".join(value)


def assert_notebook_clean(notebook):
    assert_reader_text(notebook_chunks(notebook))


def assert_slides_clean(prs, figure_labels):
    chunks = []
    for i, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if shape.has_text_frame:
                chunks.append((f"Trang {i}", shape.text))
            for properties in shape._element.xpath(".//p:cNvPr"):
                chunks.append((f"Trang {i}, mô tả", properties.get("descr", "")))
        chunks.append((f"Trang {i}, ghi chú", slide.notes_slide.notes_text_frame.text))
    for name, labels in figure_labels.items():
        chunks.append((f"Hình {name}", "\n".join(labels)))
    assert_reader_text(chunks)
