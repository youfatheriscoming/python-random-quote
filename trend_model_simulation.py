"""
trend_model_simulation.py
=========================

根據參數 a, b, c 生成「金融趨勢模型」的報酬序列,對應論文 Eq.(1):

    r_{t+1} = a + b * phi_t + c * phi_t**3 + eps_{t+1}

其中
    phi_t  : 今日趨勢強度 = 回看視窗報酬的 t 統計量
             phi_t = sqrt(N) * mean / std
    a      : 風險溢酬(依資產而定)
    b      : 趨勢延續 (論文: 0.013)
    c      : 趨勢反轉 (論文: -0.006,負值)
    eps    : 雜訊(不必為 i.i.d.)

模型是「自我參照」的:今天的報酬會影響明天的趨勢強度 phi,
phi 又透過 b, c 影響明天的報酬,因此需要逐日(path-dependent)模擬。

只依賴 numpy;若要畫圖則需要 matplotlib。
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# 由參數逐日生成一個市場的報酬序列
# ---------------------------------------------------------------------------
def simulate_market(n_days: int,
                    a: float = 0.0,
                    b: float = 0.013,
                    c: float = -0.006,
                    horizon: int = 60,
                    sigma: float = 1.0,
                    rng: np.random.Generator | None = None) -> np.ndarray:
    """逐日模擬報酬序列。

    參數
    ----
    n_days  : 要產生的交易日數
    a,b,c   : Eq.(1) 的係數
    horizon : 計算趨勢強度 phi 的回看視窗長度 N
    sigma   : 雜訊 eps 的標準差(報酬已標準化時通常設 1)
    rng     : numpy 隨機產生器

    回傳
    ----
    長度 n_days 的日報酬陣列。
    """
    rng = rng or np.random.default_rng()
    r = np.zeros(n_days)

    # 暖機:前 horizon 天用純雜訊,讓 phi 有東西可算
    r[:horizon] = rng.normal(0.0, sigma, size=horizon)

    for t in range(horizon, n_days):
        window = r[t - horizon:t]
        sd = window.std(ddof=1)
        phi_t = np.sqrt(horizon) * window.mean() / sd if sd > 0 else 0.0
        eps = rng.normal(0.0, sigma)
        r[t] = a + b * phi_t + c * phi_t ** 3 + eps

    return r


# ---------------------------------------------------------------------------
# 確定性的期望報酬曲線 E[r | phi](不含雜訊),用來畫 fig.1(左)
# ---------------------------------------------------------------------------
def expected_return_curve(phi_grid: np.ndarray,
                          a: float = 0.0,
                          b: float = 0.013,
                          c: float = -0.006) -> np.ndarray:
    """E[r_{t+1} | phi] = a + b*phi + c*phi**3,對給定的 phi 網格回傳曲線。"""
    phi_grid = np.asarray(phi_grid, dtype=float)
    return a + b * phi_grid + c * phi_grid ** 3


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    rng = np.random.default_rng(0)

    # 用論文參數生成一條報酬路徑與其價格
    a, b, c = 0.0, 0.013, -0.006
    returns = simulate_market(n_days=2520, a=a, b=b, c=c, horizon=60, rng=rng)
    price = 100.0 * np.exp(np.cumsum(returns / 100.0))  # 把報酬當成 % 累積成價格

    print(f"生成 {len(returns)} 天報酬")
    print(f"  平均日報酬 = {returns.mean():.4f}")
    print(f"  日報酬標準差 = {returns.std():.4f}")
    print(f"  期末價格 = {price[-1]:.2f}")

    # E[r|phi] 曲線:展示趨勢延續(中段斜率為正)與趨勢反轉(兩端往回彎)
    phi_grid = np.linspace(-3, 3, 13)
    curve = expected_return_curve(phi_grid, a, b, c)
    print("\nphi ->  E[r|phi]:")
    for p, v in zip(phi_grid, curve):
        print(f"  phi={p:+.1f}  E[r]={v:+.4f}")

    # 若有 matplotlib,畫出 fig.1(左)風格的曲線
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fine = np.linspace(-4, 4, 400)
        plt.figure(figsize=(6, 4))
        plt.plot(fine, expected_return_curve(fine, a, b, c))
        plt.axhline(0, color="gray", lw=0.6)
        plt.axvline(0, color="gray", lw=0.6)
        plt.xlabel(r"trend strength  $\phi_t$  (t-statistic)")
        plt.ylabel(r"$E[r_{t+1}\,|\,\phi_t]$")
        plt.title("Cubic trend model:  a + b·φ + c·φ³")
        plt.tight_layout()
        plt.savefig("trend_model_curve.png", dpi=120)
        print("\n已輸出圖檔: trend_model_curve.png")
    except Exception as e:
        print(f"\n(略過繪圖: {e})")
