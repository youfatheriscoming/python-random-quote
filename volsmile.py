#!/usr/bin/env python3
"""Compute smile metrics (ATM, RR, BF) from SPX option quotes.

Runs out-of-the-box with bundled sample data when no CLI args are supplied.
"""

import argparse
import csv
import datetime as dt
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


DEFAULT_QUOTES = "data/spx_example_quotes.csv"
DEFAULT_SPOT = 6836.17
DEFAULT_RATE = 0.0
DEFAULT_DIV = 0.0
DEFAULT_VAL_DATE = dt.date(2026, 1, 20)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass
class OptionQuote:
    expiry: dt.date
    opt_type: str
    strike: float
    price: float
    delta_label: float


def bs_price(spot: float, strike: float, t: float, r: float, q: float, sigma: float, opt_type: str) -> float:
    if t <= 0:
        intrinsic = max(0.0, spot - strike) if opt_type == "C" else max(0.0, strike - spot)
        return intrinsic

    sqrt_t = math.sqrt(t)
    d1 = (math.log(spot / strike) + (r - q + 0.5 * sigma * sigma) * t) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t

    if opt_type == "C":
        return math.exp(-q * t) * spot * norm_cdf(d1) - math.exp(-r * t) * strike * norm_cdf(d2)
    return math.exp(-r * t) * strike * norm_cdf(-d2) - math.exp(-q * t) * spot * norm_cdf(-d1)


def implied_vol(spot: float, strike: float, t: float, r: float, q: float, opt_type: str, target_price: float) -> float:
    low, high = 1e-6, 5.0
    for _ in range(120):
        mid = 0.5 * (low + high)
        model = bs_price(spot, strike, t, r, q, mid, opt_type)
        if model > target_price:
            high = mid
        else:
            low = mid
    return 0.5 * (low + high)


def year_fraction(valuation_date: dt.date, expiry: dt.date) -> float:
    return max((expiry - valuation_date).days / 365.0, 1e-8)


def read_quotes(path: str) -> List[OptionQuote]:
    rows: List[OptionQuote] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                OptionQuote(
                    expiry=dt.date.fromisoformat(row["expiry"]),
                    opt_type=row["type"].strip().upper(),
                    strike=float(row["strike"]),
                    price=float(row["price"]),
                    delta_label=abs(float(row["delta_label"])),
                )
            )
    return rows


def summarize_smile(quotes: List[OptionQuote], valuation_date: dt.date, spot: float, r: float, q: float) -> Dict[dt.date, Dict[str, float]]:
    out: Dict[dt.date, Dict[str, float]] = {}
    grouped: Dict[dt.date, List[OptionQuote]] = {}
    for quote in quotes:
        grouped.setdefault(quote.expiry, []).append(quote)

    for expiry, exp_quotes in sorted(grouped.items()):
        t = year_fraction(valuation_date, expiry)
        vols: Dict[Tuple[str, float], float] = {}
        for quote in exp_quotes:
            vols[(quote.opt_type, quote.delta_label)] = implied_vol(
                spot=spot,
                strike=quote.strike,
                t=t,
                r=r,
                q=q,
                opt_type=quote.opt_type,
                target_price=quote.price,
            )

        summary: Dict[str, float] = {}
        c50 = vols.get(("C", 0.5))
        p50 = vols.get(("P", 0.5))
        if c50 is not None and p50 is not None:
            summary["ATM"] = 0.5 * (c50 + p50)
        elif c50 is not None:
            summary["ATM"] = c50
        elif p50 is not None:
            summary["ATM"] = p50

        if ("C", 0.25) in vols and ("P", 0.25) in vols and "ATM" in summary:
            c25 = vols[("C", 0.25)]
            p25 = vols[("P", 0.25)]
            summary["RR25"] = c25 - p25
            summary["BF25"] = 0.5 * (c25 + p25) - summary["ATM"]

        if ("C", 0.10) in vols and ("P", 0.10) in vols and "ATM" in summary:
            c10 = vols[("C", 0.10)]
            p10 = vols[("P", 0.10)]
            summary["RR10"] = c10 - p10
            summary["BF10"] = 0.5 * (c10 + p10) - summary["ATM"]

        out[expiry] = summary

    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute ATM/RR/BF smile metrics from option quotes")
    parser.add_argument("--quotes", default=DEFAULT_QUOTES, help=f"CSV path with quote rows (default: {DEFAULT_QUOTES})")
    parser.add_argument("--spot", type=float, default=DEFAULT_SPOT, help=f"Spot price (default: {DEFAULT_SPOT})")
    parser.add_argument("--rate", type=float, default=DEFAULT_RATE, help="Risk-free annualized rate, decimal")
    parser.add_argument("--div", type=float, default=DEFAULT_DIV, help="Dividend yield / carry q, decimal")
    parser.add_argument(
        "--valuation-date",
        type=dt.date.fromisoformat,
        default=DEFAULT_VAL_DATE,
        help=f"Valuation date YYYY-MM-DD (default: {DEFAULT_VAL_DATE.isoformat()})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not Path(args.quotes).exists():
        raise SystemExit(f"Quotes file not found: {args.quotes}")

    quotes = read_quotes(args.quotes)
    summary = summarize_smile(quotes, args.valuation_date, args.spot, args.rate, args.div)

    for expiry, metrics in summary.items():
        print(f"{expiry}:")
        for key in ("ATM", "RR25", "BF25", "RR10", "BF10"):
            if key in metrics:
                print(f"  {key:<5} = {metrics[key]:.4%}")


if __name__ == "__main__":
    main()
