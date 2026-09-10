"""Sinh và chạy notebook nộp bài — sản phẩm 1.2 của bộ hồ sơ.

Vì sao có tệp này
-----------------
Yêu cầu nộp bài đòi **01 file** truy vấn và xử lý dữ liệu, kèm chú thích từng
bước; đi đường Python thì nộp một notebook. Dự án lại có 31 script, nên phải gộp
lại — nhưng gộp bằng tay một lần rồi sửa tay mãi về sau là cách chắc chắn nhất để
notebook trôi khỏi phần còn lại của đồ án.

Nội dung các ô nằm ở `07_notebook_cells.py`; tệp này chỉ làm ba việc: đọc các ô,
dựng JSON `.ipynb`, rồi **chạy thật** để nhúng kết quả vào tệp. Người chấm mở ra
là thấy đủ số liệu và biểu đồ mà không phải chạy lại, cũng không cần dữ liệu.

Notebook tự chứa
----------------
Ô trong notebook chỉ đọc `archive/*.csv`. Không `import` script nào của dự án,
không đọc `output/`, không ghi tệp. Đó là điều kiện để nó thật sự là "một file":
một notebook gọi lại `02_clean_build.py` thì hồ sơ nộp là ba mươi hai file chứ
không phải một.

Tính trung thực của nội dung đã được kiểm riêng: bảng `fact_energy` do notebook
tự dựng khớp **từng dòng** với `output/clean/fact_energy.csv` đã công bố —
89.075 dòng, cùng khoá, lệch giá trị lớn nhất 1,1e-13, `value_class` khớp tuyệt đối.

Chạy:  python python\\07_build_notebook.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import BASE, OUTPUT  # noqa: E402

PYTHON_DIR = Path(__file__).resolve().parent
CELLS_PATH = PYTHON_DIR / "07_notebook_cells.py"
NOTEBOOK_PATH = OUTPUT / "notebook" / "ASEAN_Renewables_DataProcessing.ipynb"

# Mọi lần đọc và ghi đều nói rõ utf-8. Trên Windows mã hoá mặc định là cp1252 và
# dấu tiếng Việt biến thành dấu hỏi mà không ném lỗi nào — bản hỏng vẫn decode
# được, nên chỉ đọc bằng mắt mới phát hiện.
ENCODING = "utf-8"

CELL_MARKER = re.compile(
    r"^# === CELL (?P<num>\d+) \| (?P<kind>code|markdown) \| (?P<title>.*?) ===$",
    re.MULTILINE,
)


def read_cells() -> list[tuple[int, str, str, str]]:
    """(số, loại, tiêu đề, nội dung) cho từng ô, theo đúng thứ tự trong tệp."""
    source = CELLS_PATH.read_text(encoding=ENCODING)
    parts = CELL_MARKER.split(source)
    if len(parts) < 5:
        raise AssertionError(f"khong tim thay o nao trong {CELLS_PATH}")

    cells: list[tuple[int, str, str, str]] = []
    for index in range(1, len(parts), 4):
        number = int(parts[index])
        kind = parts[index + 1]
        title = parts[index + 2].strip()
        body = parts[index + 3]
        cells.append((number, kind, title, body))

    numbers = [c[0] for c in cells]
    if numbers != list(range(1, len(numbers) + 1)):
        raise AssertionError(f"so hieu o khong lien tuc: {numbers}")
    return cells


def markdown_body(body: str, number: int) -> str:
    """Bóc phần văn bản khỏi `MD = \"\"\"...\"\"\"` của một ô markdown."""
    match = re.search(r'MD\s*=\s*"""(.*?)"""', body, re.DOTALL)
    if match is None:
        raise AssertionError(f"o markdown {number} khong co bien MD")
    return match.group(1).strip("\n")


def build_notebook(cells: list[tuple[int, str, str, str]]) -> dict:
    """`source` là một chuỗi, không phải danh sách dòng.

    Định dạng .ipynb cho phép cả hai, nhưng `nbclient` gọi `.strip()` thẳng lên
    `cell.source` khi chạy, nên danh sách dòng làm nó ném AttributeError giữa
    chừng thay vì báo tệp sai định dạng.
    """
    out: list[dict] = []
    for number, kind, _title, body in cells:
        # Id ổn định theo số thứ tự ô, không sinh ngẫu nhiên: dựng lại hai lần
        # phải cho cùng một tệp, và id ngẫu nhiên làm mọi lần dựng khác nhau.
        cell_id = f"cell-{number:02d}"
        if kind == "markdown":
            out.append({
                "id": cell_id,
                "cell_type": "markdown",
                "metadata": {},
                "source": markdown_body(body, number),
            })
        else:
            out.append({
                "id": cell_id,
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": body.strip("\n"),
            })
    return {
        "cells": out,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": sys.version.split()[0]},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


# Dấu hiệu cho thấy notebook đã với ra ngoài `archive/`. Bắt trên mã nguồn trước
# khi chạy, vì một notebook đọc `output/` vẫn chạy trơn tru và vẫn cho số đúng —
# nó chỉ thôi là "một file", và không có lỗi nào báo điều đó.
FORBIDDEN = (
    ("%run", "gọi script khác"),
    ("output/clean", "đọc dữ liệu đã làm sạch sẵn thay vì tự làm sạch"),
    ("output/stats", "đọc kết quả thống kê có sẵn"),
    ("output\\\\clean", "đọc dữ liệu đã làm sạch sẵn"),
    ("__file__", "không tồn tại ổn định trong Jupyter"),
    (".to_csv(", "ghi tệp"),
    (".savefig(", "ghi tệp"),
)


def assert_self_contained(cells: list[tuple[int, str, str, str]]) -> None:
    problems: list[str] = []
    for number, kind, title, body in cells:
        if kind != "code":
            continue
        for token, why in FORBIDDEN:
            if token in body:
                problems.append(f"ô {number} ({title}): {token!r} — {why}")
        # `import` một script của dự án cũng phá tính tự chứa, nhưng chỉ khi nó
        # trỏ vào `python/`; import thư viện chuẩn thì bình thường.
        for match in re.finditer(r"^\s*(?:from|import)\s+(\w+)", body, re.MULTILINE):
            module = match.group(1)
            if (PYTHON_DIR / f"{module}.py").exists():
                problems.append(f"ô {number} ({title}): import `{module}` của dự án")
    if problems:
        raise AssertionError(
            "notebook khong con tu chua:\n  " + "\n  ".join(problems)
        )


def main() -> int:
    cells = read_cells()
    assert_self_contained(cells)
    code_count = sum(1 for c in cells if c[1] == "code")

    import nbformat
    from nbclient import NotebookClient

    notebook = nbformat.from_dict(build_notebook(cells))

    # Chạy từ thư mục gốc của dự án: ô đầu tiên dò ngược từ `Path.cwd()` để tìm
    # thư mục chứa `archive`, nên thư mục làm việc quyết định notebook có chạy
    # được hay không.
    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name="python3",
        resources={"metadata": {"path": str(BASE)}},
        allow_errors=False,
    )
    print(f"dang chay {code_count} o ma ...")
    client.execute()

    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with NOTEBOOK_PATH.open("w", encoding=ENCODING) as handle:
        nbformat.write(notebook, handle)

    # Kiểm lại tệp vừa ghi thay vì tin vào đối tượng còn trong bộ nhớ: cái được
    # nộp là tệp trên đĩa.
    saved = nbformat.read(NOTEBOOK_PATH.open(encoding=ENCODING), as_version=4)
    executed = [c for c in saved.cells if c.cell_type == "code"]
    with_output = [c for c in executed if c.get("outputs")]
    images = sum(
        1
        for c in executed
        for o in c.get("outputs", [])
        if "image/png" in o.get("data", {})
    )
    text = NOTEBOOK_PATH.read_text(encoding=ENCODING)
    diacritics = sum(1 for ch in text if ord(ch) > 127)

    if diacritics == 0:
        raise AssertionError(
            "notebook khong con ky tu ngoai ASCII — dau tieng Viet da bi mat khi ghi"
        )

    size_mb = NOTEBOOK_PATH.stat().st_size / 1024 / 1024
    print(f"  -> {NOTEBOOK_PATH}")
    print(
        f"\nNOTEBOOK BUILD (san pham 1.2): PASS | {len(saved.cells)} o "
        f"({len(executed)} ma, {len(saved.cells) - len(executed)} van ban) | "
        f"{len(with_output)} o co ket qua | {images} bieu do | {size_mb:.2f} MB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
