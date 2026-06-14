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

## Volatility Smile Graph

`volatility_smile.py` generates a volatility smile graph from option
parameters. Install the dependencies first:

```
pip install -r requirements.txt
```

Generate an illustrative (parametric) smile:

```
python3 volatility_smile.py
```

Back implied volatilities out of real market prices and plot them — supply one
`--quote STRIKE:PRICE` per option, all sharing the same spot/rate/expiry:

```
python3 volatility_smile.py \
    --spot 100 --rate 0.02 --expiry 0.5 --kind call \
    --quote 80:21.0 --quote 90:12.5 --quote 100:5.8 \
    --quote 110:2.1 --quote 120:0.8 \
    --x-axis moneyness --output smile.png
```

The image is written to `--output` (default `volatility_smile.png`). Run
`python3 volatility_smile.py --help` for the full list of options, including the
synthetic-smile controls (`--atm-vol`, `--skew`, `--curvature`).
