"""
Cau hinh dung chung cho toan bo script cua do an.

Moi script khac import tu day thay vi hard-code duong dan,
de khi doi vi tri project chi phai sua mot cho.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Duong dan
# ---------------------------------------------------------------------------
# Suy ra tu vi tri file nay (python/config.py) -> thu muc goc cua project.
# Cach nay portable hon la ghi cung "d:\DA\Final_Project".
BASE = Path(__file__).resolve().parent.parent

ARCHIVE = BASE / "archive"        # 17 CSV goc — CHI DOC, KHONG SUA
OUTPUT = BASE / "output"
CLEAN = OUTPUT / "clean"          # bang sach — nguon cho Power BI
STATS = OUTPUT / "stats"          # bang thong ke mo ta
CHARTS = OUTPUT / "charts"        # PNG
SQL_DIR = BASE / "sql"
DOCS = BASE / "docs"
POWERBI = BASE / "powerbi"

DB_PATH = SQL_DIR / "renewables.db"

# ---------------------------------------------------------------------------
# Pham vi phan tich
# ---------------------------------------------------------------------------
# 10 nuoc ASEAN — dung o Phase 1 (bang do phu) va cac phase sau.
# Ten phai khop CHINH XAC gia tri cot `Entity` trong file CSV goc.
ASEAN_10 = [
    "Vietnam",
    "Thailand",
    "Indonesia",
    "Philippines",
    "Malaysia",
    "Singapore",
    "Myanmar",
    "Cambodia",
    "Laos",
    "Brunei",
]

# So file CSV mong doi trong archive/ — dung de kiem tra tinh toan ven.
EXPECTED_CSV_COUNT = 17
