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

## Commodity Option Volatility Calculator

A new script `commodity_option_vol_calculator.py` is included for volatility calculations:

- `hist` mode: annualized historical volatility from a price series.
- `iv` mode: implied volatility for futures options using the Black-76 model.

Examples:

```bash
python3 commodity_option_vol_calculator.py hist --prices "100,101,99.5,102" --annualization 252
python3 commodity_option_vol_calculator.py iv --market-price 4.2 --futures-price 100 --strike 102 --time 0.25 --rate 0.03 --type call
```

## iPhone 使用方式（網頁版）

新增 `iphone_option_vol_calculator.html`，可直接在 iPhone Safari 打開使用。

- 方式 1：把檔案上傳到任意靜態空間（GitHub Pages / iCloud Drive）後用 Safari 開啟。
- 方式 2：在電腦執行 `python3 -m http.server 8000`，iPhone 與電腦同網路下打開 `http://<電腦IP>:8000/iphone_option_vol_calculator.html`。

此頁面包含：
- 歷史波動率（價格序列）
- Black-76 隱含波動率（期貨期權）
