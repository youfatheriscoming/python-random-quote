#!/usr/bin/env python3
"""Commodity option volatility calculator.

Supports:
1) Historical volatility from price series (log returns, annualized)
2) Implied volatility from Black-76 option pricing (common for commodity futures options)
"""

from __future__ import annotations

import argparse
import math
from statistics import stdev


def normal_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black76_price(
    futures_price: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    option_type: str,
) -> float:
    """Black-76 price for options on futures."""
    if volatility <= 0 or time_to_expiry <= 0:
        intrinsic = max(futures_price - strike, 0.0) if option_type == "call" else max(strike - futures_price, 0.0)
        return math.exp(-risk_free_rate * time_to_expiry) * intrinsic

    sigma_sqrt_t = volatility * math.sqrt(time_to_expiry)
    d1 = (math.log(futures_price / strike) + 0.5 * volatility * volatility * time_to_expiry) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    discount = math.exp(-risk_free_rate * time_to_expiry)

    if option_type == "call":
        return discount * (futures_price * normal_cdf(d1) - strike * normal_cdf(d2))
    return discount * (strike * normal_cdf(-d2) - futures_price * normal_cdf(-d1))


def implied_volatility_black76(
    market_price: float,
    futures_price: float,
    strike: float,
    time_to_expiry: float,
    risk_free_rate: float,
    option_type: str,
    tolerance: float = 1e-8,
    max_iterations: int = 200,
) -> float:
    """Solve implied volatility with bisection."""
    low, high = 1e-6, 5.0
    low_price = black76_price(futures_price, strike, time_to_expiry, risk_free_rate, low, option_type)
    high_price = black76_price(futures_price, strike, time_to_expiry, risk_free_rate, high, option_type)

    if not (low_price <= market_price <= high_price):
        raise ValueError(
            "Market price is outside model price bounds; check inputs."
        )

    for _ in range(max_iterations):
        mid = 0.5 * (low + high)
        mid_price = black76_price(futures_price, strike, time_to_expiry, risk_free_rate, mid, option_type)

        if abs(mid_price - market_price) < tolerance:
            return mid

        if mid_price < market_price:
            low = mid
        else:
            high = mid

    return 0.5 * (low + high)


def historical_volatility(prices: list[float], annualization_factor: int = 252) -> float:
    """Annualized historical volatility from price series."""
    if len(prices) < 2:
        raise ValueError("Need at least two prices to compute volatility.")

    returns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
    if len(returns) < 2:
        raise ValueError("Need at least three prices for sample standard deviation.")

    return stdev(returns) * math.sqrt(annualization_factor)


def parse_prices(prices_text: str) -> list[float]:
    return [float(item.strip()) for item in prices_text.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Commodity option volatility calculator")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    hist = subparsers.add_parser("hist", help="Calculate historical volatility from prices")
    hist.add_argument("--prices", required=True, help="Comma-separated prices, e.g. 102,101.5,103")
    hist.add_argument("--annualization", type=int, default=252, help="Annualization factor, default 252")

    iv = subparsers.add_parser("iv", help="Calculate implied volatility using Black-76")
    iv.add_argument("--market-price", type=float, required=True, help="Observed option market price")
    iv.add_argument("--futures-price", type=float, required=True, help="Current futures price")
    iv.add_argument("--strike", type=float, required=True, help="Option strike")
    iv.add_argument("--time", type=float, required=True, help="Time to expiry in years")
    iv.add_argument("--rate", type=float, default=0.0, help="Risk-free rate (annualized, decimal)")
    iv.add_argument("--type", choices=["call", "put"], required=True, help="Option type")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.mode == "hist":
        prices = parse_prices(args.prices)
        vol = historical_volatility(prices, args.annualization)
        print(f"Historical Volatility: {vol:.6f} ({vol * 100:.2f}%)")
        return

    implied_vol = implied_volatility_black76(
        market_price=args.market_price,
        futures_price=args.futures_price,
        strike=args.strike,
        time_to_expiry=args.time,
        risk_free_rate=args.rate,
        option_type=args.type,
    )
    print(f"Implied Volatility (Black-76): {implied_vol:.6f} ({implied_vol * 100:.2f}%)")


if __name__ == "__main__":
    main()
