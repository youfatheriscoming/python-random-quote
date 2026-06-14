#!/usr/bin/env python3
"""Generate a volatility smile graph from option parameters.

A volatility smile plots the Black-Scholes *implied volatility* of a set of
options (sharing the same underlying and expiry) against their strike price
(or moneyness). The script can work from two kinds of input:

1. Market prices -- the implied volatility is backed out of each price with a
   Black-Scholes root-finder, then plotted. This is the "real" use case.
2. A parametric smile -- when you only have a handful of anchor points (or
   just want a quick illustration) the script can synthesise a smooth smile
   from an at-the-money vol plus skew/curvature parameters.

Run with no arguments for a self-contained demo:

    python3 volatility_smile.py

Back vols out of market prices:

    python3 volatility_smile.py \
        --spot 100 --rate 0.02 --expiry 0.5 --kind call \
        --quote 80:21.0 --quote 90:12.5 --quote 100:5.8 \
        --quote 110:2.1 --quote 120:0.8 \
        --output smile.png

Only numpy and matplotlib are required (see requirements.txt).
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass


# --------------------------------------------------------------------------- #
# Black-Scholes pricing and implied volatility
# --------------------------------------------------------------------------- #

def _norm_cdf(x: float) -> float:
    """Standard normal CDF using the error function (no scipy dependency)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes_price(
    spot: float,
    strike: float,
    rate: float,
    expiry: float,
    vol: float,
    kind: str = "call",
) -> float:
    """Black-Scholes price of a European call or put.

    spot   : current price of the underlying
    strike : strike price
    rate   : continuously-compounded risk-free rate
    expiry : time to expiry in years
    vol    : volatility (annualised, e.g. 0.20 for 20%)
    kind   : "call" or "put"
    """
    if expiry <= 0 or vol <= 0:
        # Degenerate case: option is worth its intrinsic value.
        forward = spot * math.exp(rate * expiry)
        intrinsic = forward - strike if kind == "call" else strike - forward
        return max(intrinsic, 0.0) * math.exp(-rate * expiry)

    d1 = (math.log(spot / strike) + (rate + 0.5 * vol * vol) * expiry) / (
        vol * math.sqrt(expiry)
    )
    d2 = d1 - vol * math.sqrt(expiry)

    if kind == "call":
        return spot * _norm_cdf(d1) - strike * math.exp(-rate * expiry) * _norm_cdf(d2)
    if kind == "put":
        return strike * math.exp(-rate * expiry) * _norm_cdf(-d2) - spot * _norm_cdf(-d1)
    raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")


def implied_volatility(
    price: float,
    spot: float,
    strike: float,
    rate: float,
    expiry: float,
    kind: str = "call",
    tol: float = 1e-8,
    max_iter: int = 200,
) -> float:
    """Back out the implied volatility from a market price via bisection.

    Bisection is used rather than Newton-Raphson because it is unconditionally
    convergent and cannot blow up when vega is tiny (deep in/out of the money),
    which is exactly where smiles are most interesting.

    Returns ``nan`` if the price is outside the no-arbitrage bounds.
    """
    discount = math.exp(-rate * expiry)
    forward = spot / discount
    intrinsic = max((forward - strike if kind == "call" else strike - forward), 0.0) * discount
    upper_bound = spot if kind == "call" else strike * discount

    # Price must sit strictly inside [intrinsic, upper bound] to be invertible.
    if price <= intrinsic + 1e-12 or price >= upper_bound - 1e-12:
        return float("nan")

    low, high = 1e-6, 5.0  # 0.0001% .. 500% vol brackets essentially any market
    for _ in range(max_iter):
        mid = 0.5 * (low + high)
        diff = black_scholes_price(spot, strike, rate, expiry, mid, kind) - price
        if abs(diff) < tol:
            return mid
        if diff > 0:
            high = mid
        else:
            low = mid
    return 0.5 * (low + high)


# --------------------------------------------------------------------------- #
# Smile construction
# --------------------------------------------------------------------------- #

@dataclass
class SmilePoint:
    strike: float
    moneyness: float          # strike / spot
    implied_vol: float        # as a fraction, e.g. 0.21


def smile_from_quotes(
    quotes: list[tuple[float, float]],
    spot: float,
    rate: float,
    expiry: float,
    kind: str,
) -> list[SmilePoint]:
    """Build smile points from (strike, market_price) quotes."""
    points: list[SmilePoint] = []
    for strike, price in sorted(quotes):
        iv = implied_volatility(price, spot, strike, rate, expiry, kind)
        if not math.isnan(iv):
            points.append(SmilePoint(strike, strike / spot, iv))
    return points


def parametric_smile(
    spot: float,
    expiry: float,
    atm_vol: float,
    skew: float,
    curvature: float,
    strikes: list[float],
) -> list[SmilePoint]:
    """Synthesise a smile from a simple quadratic-in-log-moneyness model.

    sigma(K) = atm_vol + skew * x + curvature * x^2,   x = ln(K / forward)

    This is a common, well-behaved parameterisation for illustration: ``skew``
    tilts the smile (equity markets are typically negative) and ``curvature``
    controls how pronounced the wings are.
    """
    points: list[SmilePoint] = []
    for strike in sorted(strikes):
        x = math.log(strike / spot)
        vol = atm_vol + skew * x + curvature * x * x
        vol = max(vol, 1e-4)
        points.append(SmilePoint(strike, strike / spot, vol))
    return points


# --------------------------------------------------------------------------- #
# Plotting
# --------------------------------------------------------------------------- #

def plot_smile(
    points: list[SmilePoint],
    output: str,
    title: str,
    x_axis: str = "strike",
    spot: float | None = None,
) -> None:
    """Render the smile to an image file."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless / no display needed
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit(
            "matplotlib is required to draw the graph.\n"
            "Install it with:  pip install -r requirements.txt"
        )

    if not points:
        raise SystemExit("No valid smile points to plot (check your inputs).")

    if x_axis == "moneyness":
        xs = [p.moneyness for p in points]
        x_label = "Moneyness (strike / spot)"
        atm_x = 1.0
    else:
        xs = [p.strike for p in points]
        x_label = "Strike"
        atm_x = spot
    ys = [p.implied_vol * 100.0 for p in points]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(xs, ys, "-o", color="#1f77b4", linewidth=2, markersize=6, label="Implied vol")

    if atm_x is not None:
        ax.axvline(atm_x, color="grey", linestyle="--", linewidth=1, alpha=0.7,
                   label="At-the-money")

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel(x_label)
    ax.set_ylabel("Implied volatility (%)")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(output, dpi=130)
    plt.close(fig)
    print(f"Saved volatility smile to {output} ({len(points)} points).")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _parse_quote(value: str) -> tuple[float, float]:
    try:
        strike_s, price_s = value.split(":")
        return float(strike_s), float(price_s)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"quote must look like STRIKE:PRICE, got {value!r}"
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate a volatility smile graph from option parameters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--spot", type=float, default=100.0, help="Underlying spot price.")
    p.add_argument("--rate", type=float, default=0.02, help="Risk-free rate (e.g. 0.02).")
    p.add_argument("--expiry", type=float, default=0.5, help="Time to expiry in years.")
    p.add_argument("--kind", choices=["call", "put"], default="call",
                   help="Option type used to invert prices.")
    p.add_argument("--quote", type=_parse_quote, action="append", metavar="STRIKE:PRICE",
                   help="A market quote; repeat for each strike. Enables price inversion.")
    p.add_argument("--output", default="volatility_smile.png", help="Output image path.")
    p.add_argument("--x-axis", choices=["strike", "moneyness"], default="strike",
                   help="Quantity on the x-axis.")
    p.add_argument("--title", default=None, help="Custom plot title.")

    # Parametric-smile options (used when no --quote is supplied).
    p.add_argument("--atm-vol", type=float, default=0.20,
                   help="At-the-money vol for the synthetic smile (default 0.20).")
    p.add_argument("--skew", type=float, default=-0.35,
                   help="Skew term for the synthetic smile (default -0.35).")
    p.add_argument("--curvature", type=float, default=1.2,
                   help="Curvature term for the synthetic smile (default 1.2).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.quote:
        points = smile_from_quotes(args.quote, args.spot, args.rate, args.expiry, args.kind)
        source = "market quotes"
        if not points:
            print(
                "None of the supplied quotes are invertible (prices may be outside "
                "no-arbitrage bounds). Check spot/rate/expiry/kind.",
                file=sys.stderr,
            )
            return 1
    else:
        strikes = [args.spot * m for m in
                   (0.70, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.30)]
        points = parametric_smile(
            args.spot, args.expiry, args.atm_vol, args.skew, args.curvature, strikes
        )
        source = "parametric model"
        print("No --quote given; generating an illustrative parametric smile.")

    title = args.title or (
        f"Volatility Smile ({source})\n"
        f"spot={args.spot:g}, expiry={args.expiry:g}y, rate={args.rate:g}"
    )
    plot_smile(points, args.output, title, x_axis=args.x_axis, spot=args.spot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
