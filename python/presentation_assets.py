"""Dựng hình cho bản trình chiếu từ các bảng số liệu đã đối chiếu."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from config import CLEAN, STATS


def build_assets(target: Path, values: dict[str, float]) -> None:
    spec = importlib.util.spec_from_file_location("presentation_chart_renderer", Path(__file__).with_name("04_charts.py"))
    renderer = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = renderer
    spec.loader.exec_module(renderer)
    renderer._configure_plotting()
    renderer.SERIES_LABELS.update({"OTHER_RENEWABLES": "Tái tạo khác", "RENEWABLE_TOTAL": "Tổng điện tái tạo", "MODERN_WIND_SOLAR": "Gió và mặt trời"})
    target.mkdir(parents=True, exist_ok=True)
    data = pd.read_excel(STATS / "04_chart_data.xlsx", sheet_name=None)
    labels: dict[str, list[str]] = {}

    def decorate(fig, chart_id, footer=None):
        # Nguồn gốc chi tiết vẫn ở bảng đối chiếu; hình chỉ mang thông tin đọc báo cáo.
        fig.text(0.06, 0.965, renderer.CHART_BY_ID[chart_id]["title_vi"],
                 ha="left", va="top", fontsize=19, fontweight="bold")
        note = "Nguồn: Our World in Data, tổng hợp từ Ember và BP."
        if chart_id == "C13":
            note += " Công suất ghi tại cuối năm; hệ số sử dụng công suất là chỉ báo xấp xỉ."
        fig.text(0.06, 0.025, note, fontsize=10, color="#64748B")

    def save(fig, path):
        # Kiểm chữ ngay trên đối tượng hình, kể cả chữ đã trở thành điểm ảnh khi nhúng.
        from matplotlib.text import Text
        for artist in fig.findobj(Text):
            text = artist.get_text().replace("NLTT", "điện tái tạo").replace("gió + mặt trời", "gió và mặt trời").replace("Gió + mặt trời", "Gió và mặt trời").replace("ở cuối cửa sổ", "vào cuối giai đoạn")
            artist.set_text(text)
        fig.canvas.draw()
        labels[path.name] = [a.get_text() for a in fig.findobj(Text) if a.get_text()]
        fig.savefig(path, dpi=renderer.DPI, facecolor="white", edgecolor="white", metadata={"Software": ""})
        plt.close(fig)

    renderer._decorate_figure = decorate
    renderer._save_figure = save
    tasks = [
        ("global_context.png", renderer._render_c01, [data["global_context"]]),
        ("technology_mix.png", renderer._render_c02, [data["asean_technology"]]),
        ("country_ranks.png", renderer._render_c04, [data["rank_shift_2021"]]),
        ("vietnam_generation.png", renderer._render_c07, [data["vietnam_technology"]]),
        ("concentration.png", renderer._render_c12, [data["concentration"], data["growth_contribution"]]),
        ("capacity_coverage.png", renderer._render_c13, [data["capacity_factor"]]),
    ]
    for name, render, inputs in tasks:
        render(*inputs, target / name)

    facts = pd.read_csv(CLEAN / "fact_energy.csv")
    solar = facts.loc[facts.entity.isin(renderer.ASEAN) & facts.year.eq(2021)
                      & facts.metric_key.eq("solar_generation_twh")].sort_values("value")
    assert len(solar) == 10 and solar.entity.nunique() == 10
    mean = values["F7_SOLAR2021_ALL_OBSERVED_MEAN"]
    median = values["F7_SOLAR2021_ALL_OBSERVED_MEDIAN"]
    assert abs(solar.value.mean() - mean) < 1e-9
    assert abs(solar.value.median() - median) < 1e-9
    fig, ax = plt.subplots(figsize=(7.1, 4.5), dpi=180)
    colors = ["#D55E00" if entity == "Vietnam" else "#0072B2" for entity in solar.entity]
    ax.scatter(solar.value, range(10), c=colors, s=52, zorder=3)
    ax.set_yticks(range(10), [renderer.ENTITY_LABELS[e] for e in solar.entity])
    ax.axvline(mean, color="#0072B2", linestyle="--", label="Trung bình")
    ax.axvline(median, color="#009E73", linestyle=":", label="Trung vị")
    for i, value in enumerate(solar.value):
        ax.annotate(renderer._vi_number(value, 2), (value, i), xytext=(6, 2),
                    textcoords="offset points", fontsize=9)
    ax.set_xlim(-0.5, float(solar.value.max()) * 1.18)
    ax.set_xlabel("Sản lượng điện mặt trời (TWh)")
    ax.set_title("Mười nước ASEAN, năm 2021", fontsize=13)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda value, _: renderer._vi_number(value, 0)))
    renderer._style_axis(ax, y_grid=False)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    # Tỷ lệ của hình này khác các hình chung; giữ nguyên tỷ lệ khi đặt trên trang.
    fig.canvas.draw()
    from matplotlib.text import Text
    labels["solar_distribution.png"] = [a.get_text() for a in fig.findobj(Text) if a.get_text()]
    fig.savefig(target / "solar_distribution.png", dpi=180, metadata={"Software": ""})
    plt.close(fig)
    (target / "figure_text.json").write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
