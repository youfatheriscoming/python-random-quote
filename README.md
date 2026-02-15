# Let's Write a Python Quote Bot!

This repository will get you started with building a quote bot in Python. It's meant to be used along with the [Learning Lab](https://lab.github.com) intro to Python.

When complete, you'll be able to grab random quotes from the command line, like this:

> **$** python get-quote.py
> 
> Keep it logically awesome
> 
> **$** python get-quote.py
> 
> Speak like a human

## Start the Tutorial

You can find your next step in [this repo's issues](../../issues/)!

## Volatility smile utility

This repository now also includes a small script (`spx_smile.py`) that calculates smile metrics from quoted SPX options:

- ATM vol (from 50-delta quotes)
- 25-delta risk reversal (`RR25`) and butterfly (`BF25`)
- 10-delta risk reversal (`RR10`) and butterfly (`BF10`)

Example:

```bash
python spx_smile.py \
  --quotes data/spx_example_quotes.csv \
  --spot 6836.17 \
  --rate 0.00 \
  --div 0.00 \
  --valuation-date 2026-01-20
```

The quote CSV format is:

```text
expiry,type,strike,price,delta_label
YYYY-MM-DD,C|P,<strike>,<premium>,0.50|0.25|0.10
```
