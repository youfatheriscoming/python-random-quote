"""Generate a volatility smile surface visualization from delta quotes."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class SmileQuotes:
    spot: float
    call_50d: float
    put_50d: float
    call_25d: float
    put_25d: float
    call_10d: float
    put_10d: float

    def delta_points(self) -> np.ndarray:
        return np.array([-0.5, -0.25, -0.1, 0.1, 0.25, 0.5], dtype=float)

    def vol_points(self) -> np.ndarray:
        return np.array(
            [self.put_50d, self.put_25d, self.put_10d, self.call_10d, self.call_25d, self.call_50d],
            dtype=float,
        )


def parse_expiries(expiries: str) -> list[float]:
    return [float(part.strip()) for part in expiries.split(",") if part.strip()]


def build_surface(
    deltas: np.ndarray,
    vols: np.ndarray,
    expiries: Sequence[float],
    term_structure: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    delta_grid = np.linspace(deltas.min(), deltas.max(), 101)
    base_vols = np.interp(delta_grid, deltas, vols)

    base_expiry = expiries[0]
    expiry_grid = np.array(expiries, dtype=float)
    if term_structure == "flat":
        scale = np.ones_like(expiry_grid)
    elif term_structure == "sqrt":
        scale = np.sqrt(expiry_grid / base_expiry)
    elif term_structure == "linear":
        scale = expiry_grid / base_expiry
    else:
        raise ValueError(f"Unknown term structure: {term_structure}")

    vol_surface = np.outer(scale, base_vols)
    return delta_grid, expiry_grid, vol_surface


def plot_surface(
    delta_grid: np.ndarray,
    expiry_grid: np.ndarray,
    vol_surface: np.ndarray,
    spot: float,
    output: str,
    show: bool,
) -> None:
    delta_mesh, expiry_mesh = np.meshgrid(delta_grid, expiry_grid)

    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111, projection="3d")
    surface = ax.plot_surface(delta_mesh, expiry_mesh, vol_surface, cmap="viridis", linewidth=0)
    fig.colorbar(surface, shrink=0.5, aspect=10, label="Implied Volatility")

    ax.set_title(f"Volatility Smile Surface (Spot {spot:.2f})")
    ax.set_xlabel("Delta")
    ax.set_ylabel("Expiry (days)")
    ax.set_zlabel("Implied Volatility")
    ax.view_init(elev=25, azim=-135)

    fig.tight_layout()
    fig.savefig(output, dpi=200)
    if show:
        plt.show()
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a volatility smile surface from delta quotes.")
    parser.add_argument("--spot", type=float, help="Spot price.")
    parser.add_argument("--call-50d", type=float, help="0.5 delta call implied vol.")
    parser.add_argument("--put-50d", type=float, help="-0.5 delta put implied vol.")
    parser.add_argument("--call-25d", type=float, help="0.25 delta call implied vol.")
    parser.add_argument("--put-25d", type=float, help="-0.25 delta put implied vol.")
    parser.add_argument("--call-10d", type=float, help="0.1 delta call implied vol.")
    parser.add_argument("--put-10d", type=float, help="-0.1 delta put implied vol.")
    parser.add_argument(
        "--expiries",
        type=parse_expiries,
        default=parse_expiries("7,30,90,180,365"),
        help="Comma-separated expiries in days (default: 7,30,90,180,365).",
    )
    parser.add_argument(
        "--term-structure",
        choices=("flat", "sqrt", "linear"),
        default="flat",
        help="Scaling applied across expiries.",
    )
    parser.add_argument("--output", default="vol_surface.png", help="Output image filename.")
    parser.add_argument("--show", action="store_true", help="Display the plot after saving.")
    return parser


def prompt_float(label: str, current: float | None) -> float:
    if current is not None:
        return float(current)
    if not sys.stdin.isatty():
        raise ValueError(f"Missing required input: {label}. Provide --{label} when running non-interactively.")
    while True:
        raw = input(f"Enter {label.replace('-', ' ')}: ").strip()
        try:
            return float(raw)
        except ValueError:
            print("Please enter a numeric value.")


def main(args: Iterable[str] | None = None) -> None:
    parser = build_parser()
    options = parser.parse_args(args=args)

    quotes = SmileQuotes(
        spot=prompt_float("spot", options.spot),
        call_50d=prompt_float("call-50d", options.call_50d),
        put_50d=prompt_float("put-50d", options.put_50d),
        call_25d=prompt_float("call-25d", options.call_25d),
        put_25d=prompt_float("put-25d", options.put_25d),
        call_10d=prompt_float("call-10d", options.call_10d),
        put_10d=prompt_float("put-10d", options.put_10d),
    )

    deltas = quotes.delta_points()
    vols = quotes.vol_points()

    delta_grid, expiry_grid, vol_surface = build_surface(
        deltas=deltas,
        vols=vols,
        expiries=options.expiries,
        term_structure=options.term_structure,
    )

    plot_surface(
        delta_grid=delta_grid,
        expiry_grid=expiry_grid,
        vol_surface=vol_surface,
        spot=quotes.spot,
        output=options.output,
        show=options.show,
    )

    print(f"Saved volatility surface to {options.output}")


if __name__ == "__main__":
    main()
