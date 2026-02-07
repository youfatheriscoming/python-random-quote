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

## Volatility Smile Surface

You can generate a volatility smile surface from delta quotes using `vol_surface.py`:

```bash
python vol_surface.py \
  --spot 100 \
  --call-50d 0.18 \
  --put-50d 0.19 \
  --call-25d 0.21 \
  --put-25d 0.23 \
  --call-10d 0.27 \
  --put-10d 0.30 \
  --expiries 7,30,90,180,365 \
  --term-structure flat \
  --output vol_surface.png
```

The script interpolates a smooth smile across deltas, then extends it across expiries using the
chosen term-structure scaling. The output is saved to the specified image file. If you omit any
required quote inputs, the script prompts for them and only raises an error when input is not
available (such as in a non-interactive run).
