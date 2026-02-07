#!/usr/bin/env python3
"""Generate an FX volatility smile from standard market quotes.

Inputs: ATM, 10/25-delta risk reversals and butterflies, forward, maturity,
        rates, and delta convention.
Outputs: 10Δ/25Δ strikes and vols plus a plotted smile.
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Iterable, List, Tuple

import matplotlib.pyplot as plt


@dataclass(frozen=True)
class MarketQuotes:
    atm: float
    rr_10: float
    rr_25: float
    bf_10: float
    bf_25: float


@dataclass(frozen=True)
class MarketParams:
    forward: float
    maturity: float
    rd: float
    rf: float
    delta_convention: str
    premium_adjusted: bool


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# Acklam's approximation for inverse normal CDF.
# Source: http://home.online.no/~pjacklam/notes/invnorm/
# This is a standard, fast, and accurate approximation for most practical use.

def norm_ppf(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
        )
    q = p - 0.5
    r = q * q
    return (
        (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    )


def strike_from_delta(
    delta: float,
    is_call: bool,
    vol: float,
    params: MarketParams,
) -> float:
    sqrt_t = math.sqrt(params.maturity)
    if params.delta_convention == "forward":
        delta_adj = delta
    elif params.delta_convention == "spot":
        delta_adj = delta / math.exp(-params.rf * params.maturity)
    else:
        raise ValueError("delta_convention must be 'spot' or 'forward'")

    if params.premium_adjusted:
        # Premium-adjusted delta requires numerical solve; use simple iteration.
        return solve_strike_premium_adjusted(delta, is_call, vol, params)

    p = delta_adj if is_call else -delta_adj
    if not 0.0 < p < 1.0:
        raise ValueError("delta outside (0,1) after adjustment")
    d1 = norm_ppf(p)
    return params.forward * math.exp(-(d1 * vol * sqrt_t - 0.5 * vol * vol * params.maturity))


def solve_strike_premium_adjusted(
    delta: float,
    is_call: bool,
    vol: float,
    params: MarketParams,
) -> float:
    sqrt_t = math.sqrt(params.maturity)
    fwd = params.forward
    discount_f = math.exp(-params.rf * params.maturity)

    def delta_pa(k: float) -> float:
        if k <= 0:
            return 0.0
        d1 = (math.log(fwd / k) + 0.5 * vol * vol * params.maturity) / (vol * sqrt_t)
        d2 = d1 - vol * sqrt_t
        if is_call:
            return discount_f * (norm_cdf(d1) - (k / fwd) * norm_cdf(d2))
        return -discount_f * (norm_cdf(-d1) - (k / fwd) * norm_cdf(-d2))

    target = delta
    # Use a bracket around forward for solve.
    low, high = fwd * 0.2, fwd * 5.0
    for _ in range(80):
        mid = 0.5 * (low + high)
        val = delta_pa(mid)
        if is_call:
            if val > target:
                low = mid
            else:
                high = mid
        else:
            if val < -target:
                low = mid
            else:
                high = mid
    return 0.5 * (low + high)


def build_vols(quotes: MarketQuotes) -> Tuple[float, float, float, float, float]:
    vol_25c = quotes.atm + quotes.bf_25 + 0.5 * quotes.rr_25
    vol_25p = quotes.atm + quotes.bf_25 - 0.5 * quotes.rr_25
    vol_10c = quotes.atm + quotes.bf_10 + 0.5 * quotes.rr_10
    vol_10p = quotes.atm + quotes.bf_10 - 0.5 * quotes.rr_10
    return vol_10p, vol_25p, quotes.atm, vol_25c, vol_10c


def build_strikes(
    vols: Tuple[float, float, float, float, float],
    params: MarketParams,
) -> Tuple[float, float, float, float, float]:
    vol_10p, vol_25p, atm, vol_25c, vol_10c = vols
    k_10p = strike_from_delta(0.10, False, vol_10p, params)
    k_25p = strike_from_delta(0.25, False, vol_25p, params)
    k_atm = params.forward
    k_25c = strike_from_delta(0.25, True, vol_25c, params)
    k_10c = strike_from_delta(0.10, True, vol_10c, params)
    return k_10p, k_25p, k_atm, k_25c, k_10c


def interpolate_smile(strikes: Iterable[float], vols: Iterable[float]) -> Tuple[List[float], List[float]]:
    points = sorted(zip(strikes, vols), key=lambda x: x[0])
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    grid = []
    grid_vols = []
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        y0, y1 = ys[i], ys[i + 1]
        steps = 20
        for j in range(steps):
            t = j / steps
            grid.append(x0 + (x1 - x0) * t)
            grid_vols.append(y0 + (y1 - y0) * t)
    grid.append(xs[-1])
    grid_vols.append(ys[-1])
    return grid, grid_vols


def plot_smile(strikes: Iterable[float], vols: Iterable[float], output: str) -> None:
    grid_x, grid_y = interpolate_smile(strikes, vols)
    plt.figure(figsize=(7, 4))
    plt.plot(grid_x, grid_y, label="Interpolated smile")
    plt.scatter(list(strikes), list(vols), color="red", label="Market quotes")
    plt.xlabel("Strike")
    plt.ylabel("Implied volatility")
    plt.title("FX Volatility Smile")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=200)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an FX vol smile from RR/BF quotes.")
    parser.add_argument("--atm", type=float, required=True, help="ATM volatility (decimal)")
    parser.add_argument("--rr-10", type=float, required=True, help="10-delta risk reversal")
    parser.add_argument("--rr-25", type=float, required=True, help="25-delta risk reversal")
    parser.add_argument("--bf-10", type=float, required=True, help="10-delta butterfly")
    parser.add_argument("--bf-25", type=float, required=True, help="25-delta butterfly")
    parser.add_argument("--forward", type=float, required=True, help="Forward FX rate")
    parser.add_argument("--maturity", type=float, required=True, help="Maturity in years")
    parser.add_argument("--rd", type=float, required=True, help="Domestic rate")
    parser.add_argument("--rf", type=float, required=True, help="Foreign rate")
    parser.add_argument(
        "--delta-convention",
        choices=["spot", "forward"],
        default="spot",
        help="Delta convention",
    )
    parser.add_argument(
        "--premium-adjusted",
        action="store_true",
        help="Use premium-adjusted delta",
    )
    parser.add_argument("--output", default="smile.png", help="Output image path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    quotes = MarketQuotes(
        atm=args.atm,
        rr_10=args.rr_10,
        rr_25=args.rr_25,
        bf_10=args.bf_10,
        bf_25=args.bf_25,
    )
    params = MarketParams(
        forward=args.forward,
        maturity=args.maturity,
        rd=args.rd,
        rf=args.rf,
        delta_convention=args.delta_convention,
        premium_adjusted=args.premium_adjusted,
    )
    vols = build_vols(quotes)
    strikes = build_strikes(vols, params)

    labels = ["10Δ Put", "25Δ Put", "ATM", "25Δ Call", "10Δ Call"]
    for label, strike, vol in zip(labels, strikes, vols):
        print(f"{label}: strike={strike:.6f}, vol={vol:.4%}")

    plot_smile(strikes, vols, args.output)
    print(f"Saved smile plot to {args.output}")


if __name__ == "__main__":
    main()
