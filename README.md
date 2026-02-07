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

## FX volatility smile helper

`vol_smile.py` generates a visual volatility smile curve from standard 10Δ/25Δ risk reversals and butterflies, plus an ATM volatility. It outputs the 10Δ/25Δ strikes and vols, and saves a plot to an image file.

Example:

```bash
python vol_smile.py \
  --atm 0.12 \
  --rr-10 -0.02 \
  --rr-25 -0.01 \
  --bf-10 0.002 \
  --bf-25 0.001 \
  --forward 1.085 \
  --maturity 0.5 \
  --rd 0.03 \
  --rf 0.01 \
  --delta-convention spot \
  --output smile.png
```

Use `--premium-adjusted` to switch to premium-adjusted delta.

## FX volatility surface helper

`vol_surface.py` generates a 3D volatility surface from spot and delta-based call/put vols (50Δ/25Δ/10Δ). It interpolates vols across deltas, derives strikes from the chosen delta convention, and renders a single-maturity surface.

Example:

```bash
python vol_surface.py \
  --spot 1.085 \
  --maturity 0.5 \
  --rd 0.03 \
  --rf 0.01 \
  --vol-50c 0.12 \
  --vol-50p 0.12 \
  --vol-25c 0.125 \
  --vol-25p 0.118 \
  --vol-10c 0.135 \
  --vol-10p 0.115 \
  --delta-convention spot \
  --output surface.png
```

Use `--premium-adjusted` to switch to premium-adjusted delta.

Both helpers save PNG images to the local filesystem. You can transfer the generated image (for example, `smile.png` or `surface.png`) to your phone via AirDrop, email, or cloud storage.
