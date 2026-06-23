"""
trend_param_estimation.py
==========================

根據論文 "Trends, Volatility, Correlations, and Critical Phenomena in
Financial Markets" (Safari & Schmidhuber, 2026) 的 Eq.(1):

    r_{t+1} = a + b * phi_t + c * phi_t**3 + eps_{t+1}

從(真實或模擬的)市場日報酬資料,統計估計參數 a, b, c。

估計流程
--------
1. 趨勢強度 phi_t 定義為趨勢的 t 統計量:對長度 N 的回看視窗,
       phi_t = sqrt(N) * mean(window_returns) / std(window_returns)
   (等於 Sharpe ratio * sqrt(N),衡量趨勢是否顯著)。
2. 把明日報酬 r_{t+1} 標準化成變異數 1:(r - mean) / std。
3. 因為模型對參數是線性的(特徵 = phi 與 phi**3),用 OLS 迴歸:
       r_norm ~ 1 + phi + phi**3   ->  截距=a, 斜率=b, 三次項=c
4. 論文指出 eps 不是 i.i.d.,因此回報「Newey-West (HAC) 穩健標準誤」,
   而不是普通 OLS 標準誤,才能得到像 b = 0.013 ± 0.004 這樣的誤差棒。
5. 可跨多個市場 / 多個 horizon 聚合(pool)後一起迴歸,以壓低雜訊;
   論文認為 b, c 對所有資產通用,a(風險溢酬)則依資產而定。

只依賴 numpy。若安裝了 statsmodels,會自動用它算 HAC 標準誤;
否則用內建的純 numpy Newey-West 實作。
"""

from __future__ import annotations

from dataclasses import dataclass
import numpy as np


# ---------------------------------------------------------------------------
# 1. 趨勢強度 phi (t 統計量)
# ---------------------------------------------------------------------------
def trend_strength(returns: np.ndarray, horizon: int) -> np.ndarray:
    """對日報酬序列,計算每一天回看 `horizon` 天的趨勢強度(t 統計量)。

    phi_t = sqrt(N) * mean(r[t-N+1 .. t]) / std(r[t-N+1 .. t])

    回傳長度與 returns 相同的陣列,前 horizon-1 天為 NaN(視窗不足)。
    """
    r = np.asarray(returns, dtype=float)
    n = len(r)
    phi = np.full(n, np.nan)
    if horizon < 2 or n < horizon:
        return phi
    for t in range(horizon - 1, n):
        window = r[t - horizon + 1 : t + 1]
        sd = window.std(ddof=1)
        if sd > 0:
            phi[t] = np.sqrt(horizon) * window.mean() / sd
    return phi


# ---------------------------------------------------------------------------
# 2. 建立 (phi_t, r_{t+1}) 的配對樣本
# ---------------------------------------------------------------------------
def build_samples(returns: np.ndarray, horizon: int, normalize: bool = True):
    """把一個市場的日報酬轉成 (phi_t, r_{t+1}) 配對。

    normalize=True 時,把 r_{t+1} 標準化成變異數 1。
    回傳 (phi, r_next)。
    """
    r = np.asarray(returns, dtype=float)
    phi = trend_strength(r, horizon)

    # phi_t 對到「明天」的報酬 r_{t+1}
    phi_t = phi[:-1]
    r_next = r[1:]

    mask = ~np.isnan(phi_t)
    phi_t, r_next = phi_t[mask], r_next[mask]

    if normalize and r_next.std(ddof=1) > 0:
        r_next = (r_next - r_next.mean()) / r_next.std(ddof=1)
    return phi_t, r_next


# ---------------------------------------------------------------------------
# 3. Newey-West (HAC) 共變異數,給非 i.i.d. 的 eps
# ---------------------------------------------------------------------------
def _newey_west_cov(X: np.ndarray, resid: np.ndarray, lags: int) -> np.ndarray:
    """純 numpy 的 Newey-West HAC 共變異數估計。"""
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    u = resid.reshape(-1, 1)
    Xu = X * u  # n x k

    S = Xu.T @ Xu  # lag 0
    for L in range(1, lags + 1):
        w = 1.0 - L / (lags + 1.0)  # Bartlett kernel
        G = Xu[L:].T @ Xu[:-L]
        S += w * (G + G.T)

    return XtX_inv @ S @ XtX_inv


@dataclass
class FitResult:
    a: float
    b: float
    c: float
    se: np.ndarray          # [se_a, se_b, se_c]
    n_obs: int
    method: str

    def __str__(self) -> str:
        z = 1.959963985  # 95% 信賴區間 (近似論文的 ±)
        names = ["a", "b", "c"]
        vals = [self.a, self.b, self.c]
        lines = [f"估計方法: {self.method}   樣本數: {self.n_obs}"]
        for name, v, s in zip(names, vals, self.se):
            lines.append(f"  {name} = {v:+.4f} ± {z * s:.4f}   (SE={s:.4f})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. 主估計函數:OLS 擬合 r_norm ~ 1 + phi + phi**3
# ---------------------------------------------------------------------------
def estimate_abc(phi: np.ndarray, r_next: np.ndarray,
                 hac_lags: int | None = None) -> FitResult:
    """用最小平方法估計 a, b, c,並回報 HAC 穩健標準誤。

    hac_lags=None 時自動用 Newey-West 經驗法則 floor(4*(n/100)^(2/9))。
    """
    phi = np.asarray(phi, dtype=float)
    y = np.asarray(r_next, dtype=float)
    X = np.column_stack([np.ones_like(phi), phi, phi ** 3])  # [1, phi, phi^3]
    n = len(y)

    if hac_lags is None:
        hac_lags = max(1, int(np.floor(4 * (n / 100.0) ** (2.0 / 9.0))))

    # 先試 statsmodels(可直接拿 HAC 標準誤)
    try:
        import statsmodels.api as sm
        model = sm.OLS(y, X).fit(cov_type="HAC",
                                 cov_kwds={"maxlags": hac_lags})
        a, b, c = model.params
        se = model.bse
        method = f"statsmodels OLS + HAC(maxlags={hac_lags})"
    except Exception:
        # 純 numpy 後備方案
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        cov = _newey_west_cov(X, resid, hac_lags)
        a, b, c = beta
        se = np.sqrt(np.diag(cov))
        method = f"numpy OLS + Newey-West(lags={hac_lags})"

    return FitResult(a=a, b=b, c=c, se=np.asarray(se), n_obs=n, method=method)


# ---------------------------------------------------------------------------
# 5. 跨多市場 / 多 horizon 聚合估計
# ---------------------------------------------------------------------------
def estimate_pooled(returns_by_market: dict[str, np.ndarray],
                    horizons: list[int]) -> FitResult:
    """把多個市場、多個 horizon 的 (phi, r_next) pool 起來一起估計。

    對應論文「跨數十年、多市場、10 個趨勢 horizon 聚合」的做法。
    """
    all_phi, all_r = [], []
    for _, rets in returns_by_market.items():
        for h in horizons:
            phi, r_next = build_samples(rets, h, normalize=True)
            all_phi.append(phi)
            all_r.append(r_next)
    phi = np.concatenate(all_phi)
    r_next = np.concatenate(all_r)
    return estimate_abc(phi, r_next)


# ---------------------------------------------------------------------------
# Demo:用合成資料把已知的 a, b, c 還原出來
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from trend_model_simulation import simulate_market

    rng = np.random.default_rng(42)

    # 用論文參數模擬幾個市場,再回過頭估計,檢查能否還原
    true_a, true_b, true_c = 0.0, 0.013, -0.006
    markets = {
        f"MKT{i}": simulate_market(
            n_days=6000, a=true_a, b=true_b, c=true_c,
            horizon=60, rng=rng)
        for i in range(20)
    }

    print(f"真實參數: a={true_a}, b={true_b}, c={true_c}\n")

    # 單一市場、單一 horizon
    phi, r_next = build_samples(markets["MKT0"], horizon=60)
    print("[單一市場 / horizon=60]")
    print(estimate_abc(phi, r_next), "\n")

    # 跨市場 + 多 horizon 聚合(雜訊更低,最接近論文做法)
    print("[跨 20 市場 + 多 horizon 聚合]")
    res = estimate_pooled(markets, horizons=[20, 40, 60, 120, 250])
    print(res)
