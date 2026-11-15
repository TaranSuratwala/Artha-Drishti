"""
Technical indicators for StockFeatureEngineer, built on fin-primitives.

Replaces the pandas_ta calls in FeatureEngineering.py (pandas_ta==0.3.14b is no
longer installable from PyPI). Every function keeps the pandas_ta column names,
so feature columns written to the database do not change:

  macd     -> MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
  adx      -> ADX_14, DMP_14, DMN_14
  bbands   -> BBL_20_2.0, BBM_20_2.0, BBU_20_2.0, BBB_20_2.0, BBP_20_2.0
  aroon    -> AROOND_25, AROONU_25, AROONOSC_25
  stoch    -> STOCHk_14_3_3, STOCHd_14_3_3

RSI, ATR and ADX use Wilder smoothing seeded with a simple mean (TA-Lib's
definition), so the first ~100 bars can differ slightly from pandas_ta, which
seeds its RMA with an exponentially weighted mean. After warm-up they agree.
"""
import numpy as np
import pandas as pd
import fin_primitives as fp


def _on_valid(func, **cols) -> pd.Series:
    """Run ``func`` on the rows where every input is present; NaN elsewhere."""
    frame = pd.DataFrame(cols)
    valid = frame.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=frame.index, dtype="float64")
    out = func(**{k: valid[k] for k in cols})
    return pd.Series(np.asarray(out, dtype="float64"), index=valid.index).reindex(frame.index)


def sma(close: pd.Series, length: int) -> pd.Series:
    return _on_valid(lambda close: fp.sma(close, length), close=close)


def ema(close: pd.Series, length: int) -> pd.Series:
    return _on_valid(lambda close: fp.ema(close, length), close=close)


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    return _on_valid(lambda close: fp.rsi(close, length), close=close)


def roc(close: pd.Series, length: int = 10) -> pd.Series:
    return _on_valid(lambda close: fp.compute("roc", close, length), close=close)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    return _on_valid(
        lambda high, low, close: fp.compute("wilder_smoothed_range", close, length, high=high, low=low),
        high=high, low=low, close=close,
    )


def cci(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 20) -> pd.Series:
    return _on_valid(
        lambda high, low, close: fp.compute("cci", close, length, high=high, low=low),
        high=high, low=low, close=close,
    )


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    # fin-primitives starts OBV at 0; pandas_ta starts at the first bar's volume.
    return _on_valid(
        lambda close, volume: fp.compute("obv", close, volume=volume) + float(volume.iloc[0]),
        close=close, volume=volume,
    )


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    hist = _on_valid(lambda close: fp.macd(close, fast, slow, signal), close=close)
    suffix = f"_{fast}_{slow}_{signal}"
    return pd.DataFrame({f"MACD{suffix}": line, f"MACDh{suffix}": hist, f"MACDs{suffix}": line - hist})


def adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.DataFrame:
    frame = pd.DataFrame({"high": high, "low": low, "close": close})
    valid = frame.dropna()
    out = pd.DataFrame(np.nan, index=valid.index, columns=[f"ADX_{length}", f"DMP_{length}", f"DMN_{length}"])
    if len(valid) > length:
        h, l, c = valid["high"], valid["low"], valid["close"]
        up, down = h.diff().to_numpy()[1:], -l.diff().to_numpy()[1:]
        plus_dm = np.where((up > down) & (up > 0), up, 0.0)
        minus_dm = np.where((down > up) & (down > 0), down, 0.0)
        rng = fp.compute("wilder_smoothed_range", c, length, high=h, low=l).to_numpy()[1:]
        out.iloc[1:, 1] = 100 * fp.compute("smma", plus_dm, length) / rng
        out.iloc[1:, 2] = 100 * fp.compute("smma", minus_dm, length) / rng
        out.iloc[:, 0] = fp.compute("adx", c, length, high=h, low=l).to_numpy()
    return out.reindex(frame.index)


def bbands(close: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    std = float(std)
    mid = sma(close, length)
    dev = close.rolling(length).std(ddof=0)  # population std, as pandas_ta 0.3.14b and TA-Lib
    lower, upper = mid - std * dev, mid + std * dev
    suffix = f"_{length}_{std}"
    return pd.DataFrame({
        f"BBL{suffix}": lower,
        f"BBM{suffix}": mid,
        f"BBU{suffix}": upper,
        f"BBB{suffix}": 100 * (upper - lower) / mid,
        f"BBP{suffix}": (close - lower) / (upper - lower),
    })


def aroon(high: pd.Series, low: pd.Series, length: int = 25) -> pd.DataFrame:
    since_high = high.rolling(length + 1).apply(lambda x: np.argmax(x[::-1]), raw=True)
    since_low = low.rolling(length + 1).apply(lambda x: np.argmin(x[::-1]), raw=True)
    up = 100 * (length - since_high) / length
    down = 100 * (length - since_low) / length
    return pd.DataFrame({f"AROOND_{length}": down, f"AROONU_{length}": up, f"AROONOSC_{length}": up - down})


def stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int = 14, d: int = 3, smooth_k: int = 3) -> pd.DataFrame:
    raw_k = _on_valid(
        lambda high, low, close: fp.compute("stochastic_k", close, k, high=high, low=low),
        high=high, low=low, close=close,
    )
    stoch_k = raw_k.rolling(smooth_k).mean()
    suffix = f"_{k}_{d}_{smooth_k}"
    return pd.DataFrame({f"STOCHk{suffix}": stoch_k, f"STOCHd{suffix}": stoch_k.rolling(d).mean()})


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """VWAP anchored to each calendar day (pandas_ta's default anchor "D")."""
    typical = (high + low + close) / 3
    if isinstance(close.index, pd.DatetimeIndex):
        groups = close.index.to_period("D")
        return (typical * volume).groupby(groups).cumsum() / volume.groupby(groups).cumsum()
    return (typical * volume).cumsum() / volume.cumsum()


def cdl_doji(open_: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series, length: int = 10) -> pd.Series:
    """1.0 when the body is under 10% of the average high-low range of the last ``length`` bars."""
    body = (close - open_).abs()
    avg_range = sma((high - low).abs(), length)
    return (body < 0.1 * avg_range).astype("float64")
