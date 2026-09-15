#!/usr/bin/env python3
"""Rebuild annualized and counterfactual outputs using only the Python standard library."""

from __future__ import annotations

import csv
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "inputs.csv"
OUTPUT = ROOT / "output"
SECONDS = 365 * 24 * 60 * 60


def money(value: float) -> str:
    return f"${value:,.2f}"


def read_inputs() -> list[dict[str, str]]:
    with INPUT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"metric_id", "label", "status", "with_low", "with_high", "without_low", "without_high", "delta_low", "delta_high", "unit"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("inputs.csv is empty or missing required columns")
    for row in rows:
        for field in ("with_low", "with_high", "without_low", "without_high", "delta_low", "delta_high"):
            row[field] = float(row[field])  # type: ignore[assignment]
        if (row["with_low"] > row["with_high"] or row["without_low"] > row["without_high"]
                or row["delta_low"] > row["delta_high"]):
            raise ValueError(f"Invalid range for {row['metric_id']}")
    return rows


def write_annualized(rows: list[dict[str, str]]) -> None:
    fields = [
        "metric_id", "label", "status", "unit", "annual_low", "annual_high",
        "daily_low", "daily_high", "hourly_low", "hourly_high",
        "minute_low", "minute_high", "second_low", "second_high",
    ]
    with (OUTPUT / "annualized_values.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            if row["unit"] != "USD/year":
                continue
            low, high = row["with_low"], row["with_high"]
            writer.writerow({
                "metric_id": row["metric_id"],
                "label": row["label"],
                "status": row["status"],
                "unit": row["unit"],
                "annual_low": f"{low:.2f}",
                "annual_high": f"{high:.2f}",
                "daily_low": f"{low / 365:.2f}",
                "daily_high": f"{high / 365:.2f}",
                "hourly_low": f"{low / 8760:.2f}",
                "hourly_high": f"{high / 8760:.2f}",
                "minute_low": f"{low / 525600:.2f}",
                "minute_high": f"{high / 525600:.2f}",
                "second_low": f"{low / SECONDS:.4f}",
                "second_high": f"{high / SECONDS:.4f}",
            })


def write_counterfactual(rows: list[dict[str, str]]) -> None:
    fields = [
        "metric_id", "label", "status", "with_low", "with_high",
        "without_low", "without_high", "loss_low", "loss_high",
        "with_second_low", "with_second_high", "without_second_low",
        "without_second_high", "loss_second_low", "loss_second_high",
    ]
    with (OUTPUT / "counterfactual.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            if row["unit"] != "USD/year":
                continue
            with_low, with_high = row["with_low"], row["with_high"]
            without_low, without_high = row["without_low"], row["without_high"]
            loss_low = row["delta_low"]
            loss_high = row["delta_high"]
            writer.writerow({
                "metric_id": row["metric_id"],
                "label": row["label"],
                "status": row["status"],
                "with_low": f"{with_low:.2f}",
                "with_high": f"{with_high:.2f}",
                "without_low": f"{without_low:.2f}",
                "without_high": f"{without_high:.2f}",
                "loss_low": f"{loss_low:.2f}",
                "loss_high": f"{loss_high:.2f}",
                "with_second_low": f"{with_low / SECONDS:.4f}",
                "with_second_high": f"{with_high / SECONDS:.4f}",
                "without_second_low": f"{without_low / SECONDS:.4f}",
                "without_second_high": f"{without_high / SECONDS:.4f}",
                "loss_second_low": f"{loss_low / SECONDS:.4f}",
                "loss_second_high": f"{loss_high / SECONDS:.4f}",
            })


def write_svg(rows: list[dict[str, str]]) -> None:
    wanted = ["chiefs_revenue", "chiefs_schedule_media", "licensed_products", "hospitality_food_beverage", "regional_activity"]
    by_id = {row["metric_id"]: row for row in rows}
    chart_rows = [by_id[item] for item in wanted]
    width, height = 1400, 530
    left, top, chart_width = 400, 90, 700
    max_value = max(row["with_high"] for row in chart_rows)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0b1625"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#f6f8fb}.title{font-size:30px;font-weight:700}.sub{font-size:15px;fill:#aebbd0}.label{font-size:16px}.value{font-size:14px;font-weight:700}</style>',
        '<text x="50" y="46" class="title">Mahomes-led vs. replacement-QB scenario</text>',
        '<text x="50" y="72" class="sub">Annual values in USD; modeled categories overlap and must not be summed</text>',
    ]
    for index, row in enumerate(chart_rows):
        y = top + index * 82
        with_mid = (row["with_low"] + row["with_high"]) / 2
        without_mid = (row["without_low"] + row["without_high"]) / 2
        with_width = chart_width * with_mid / max_value
        without_width = chart_width * without_mid / max_value
        label = html.escape(row["label"])
        elements.extend([
            f'<text x="50" y="{y + 18}" class="label">{label}</text>',
            f'<rect x="{left}" y="{y}" width="{with_width:.1f}" height="25" rx="4" fill="#e31837"/>',
            f'<rect x="{left}" y="{y + 31}" width="{without_width:.1f}" height="18" rx="4" fill="#8c98aa"/>',
            f'<text x="{left + with_width + 10:.1f}" y="{y + 18}" class="value">With: {money(with_mid)}</text>',
            f'<text x="{left + without_width + 10:.1f}" y="{y + 45}" class="sub">Without: {money(without_mid)}</text>',
        ])
    elements.extend([
        '<rect x="50" y="492" width="18" height="12" fill="#e31837"/><text x="76" y="503" class="sub">Mahomes-led case</text>',
        '<rect x="230" y="492" width="18" height="12" fill="#8c98aa"/><text x="256" y="503" class="sub">Replacement-QB midpoint</text>',
        '</svg>',
    ])
    (OUTPUT / "comparison.svg").write_text("\n".join(elements), encoding="utf-8")


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    rows = read_inputs()
    write_annualized(rows)
    write_counterfactual(rows)
    write_svg(rows)
    print(f"Validated {len(rows)} inputs and rebuilt 3 outputs.")


if __name__ == "__main__":
    main()
