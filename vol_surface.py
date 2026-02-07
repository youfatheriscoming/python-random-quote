#!/usr/bin/env python3
"""Generate a 3D volatility surface from delta-based quotes."""
from __future__ import annotations

import argparse
import math
from typing import Iterable, List, Tuple

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from vol_smile import MarketParams, strike_from_delta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a 3D FX vol surface from delta quotes.")
    parser.add_argument("--spot", type=float, required=True, help="Spot FX rate")
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
    parser.add_argument("--vol-50c", type=float, required=True, help="50-delta call vol")
    parser.add_argument("--vol-50p", type=float, required=True, help="50-delta put vol")
    parser.add_argument("--vol-25c", type=float, required=True, help="25-delta call vol")
    parser.add_argument("--vol-25p", type=float, required=True, help="25-delta put vol")
    parser.add_argument("--vol-10c", type=float, required=True, help="10-delta call vol")
    parser.add_argument("--vol-10p", type=float, required=True, help="10-delta put vol")
    parser.add_argument("--points", type=int, default=60, help="Number of delta points per wing")
    parser.add_argument("--output", default="surface.png", help="Output image path")
    return parser.parse_args()


def linear_interpolate(x: float, xs: List[float], ys: List[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= x <= xs[i + 1]:
            t = (x - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return ys[-1]


def build_grid(
    deltas: Iterable[float],
    vols: Iterable[float],
    params: MarketParams,
) -> Tuple[List[float], List[float], List[float]]:
    strike_grid: List[float] = []
    delta_grid: List[float] = []
    vol_grid: List[float] = []

    for delta, vol in zip(deltas, vols):
        is_call = delta > 0
        strike = strike_from_delta(abs(delta), is_call, vol, params)
        strike_grid.append(strike)
        delta_grid.append(delta)
        vol_grid.append(vol)
    return delta_grid, strike_grid, vol_grid


def plot_surface(
    delta_grid: List[float],
    strike_grid: List[float],
    vol_grid: List[float],
    output: str,
) -> None:
    fig = plt.figure(figsize=(8, 5))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_trisurf(delta_grid, strike_grid, vol_grid, cmap="viridis", linewidth=0.2)
    ax.set_xlabel("Delta")
    ax.set_ylabel("Strike")
    ax.set_zlabel("Implied volatility")
    ax.set_title("FX Volatility Surface (single maturity)")
    plt.tight_layout()
    plt.savefig(output, dpi=200)


def main() -> None:
    args = parse_args()
    forward = args.spot * math.exp((args.rd - args.rf) * args.maturity)
    params = MarketParams(
        forward=forward,
        maturity=args.maturity,
        rd=args.rd,
        rf=args.rf,
        delta_convention=args.delta_convention,
        premium_adjusted=args.premium_adjusted,
    )

    put_deltas = [-0.5, -0.25, -0.1]
    put_vols = [args.vol_50p, args.vol_25p, args.vol_10p]
    call_deltas = [0.1, 0.25, 0.5]
    call_vols = [args.vol_10c, args.vol_25c, args.vol_50c]

    print("Input quotes (delta, vol):")
    for delta, vol in zip(put_deltas, put_vols):
        print(f"{delta:+.2f}: {vol:.4%}")
    for delta, vol in zip(call_deltas, call_vols):
        print(f"{delta:+.2f}: {vol:.4%}")

    puts = [
        -0.5 + (0.4 * i / (args.points - 1))
        for i in range(args.points)
    ]
    calls = [
        0.1 + (0.4 * i / (args.points - 1))
        for i in range(args.points)
    ]

    delta_values = puts + calls
    vol_values = [
        linear_interpolate(delta, put_deltas, put_vols) if delta < 0 else linear_interpolate(delta, call_deltas, call_vols)
        for delta in delta_values
    ]

    delta_grid, strike_grid, vol_grid = build_grid(delta_values, vol_values, params)

    print("\nComputed strikes (sample):")
    for delta, strike, vol in zip(delta_grid[:: max(1, args.points // 5)], strike_grid[:: max(1, args.points // 5)], vol_grid[:: max(1, args.points // 5)]):
        print(f"{delta:+.3f}: strike={strike:.6f}, vol={vol:.4%}")

    plot_surface(delta_grid, strike_grid, vol_grid, args.output)
    print(f"Saved surface plot to {args.output}")


if __name__ == "__main__":
    main()
