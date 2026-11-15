"""
Checks TechnicalIndicators.py against plain numpy/pandas references of the
standard definitions, and that the pandas_ta column names are kept.
Run: pytest backend/test_technical_indicators.py
"""
import numpy as np
import pandas as pd
import pytest

import TechnicalIndicators as ti


@pytest.fixture
def ohlcv():
    rng = np.random.default_rng(3)
    n = 300
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    open_ = np.r_[100, close[:-1]] + rng.normal(0, 0.3, n)
    idx = pd.date_range("2023-01-02", periods=n, freq="B")
    return pd.DataFrame({
        "open": open_,
        "high": np.maximum(close, open_) + rng.uniform(0.1, 2, n),
        "low": np.minimum(close, open_) - rng.uniform(0.1, 2, n),
        "close": close,
        "volume": rng.uniform(1e5, 1e6, n),
    }, index=idx)


def _wilder(values, length):
    out = np.full(len(values), np.nan)
    out[length - 1] = np.mean(values[:length])
    for i in range(length, len(values)):
        out[i] = (out[i - 1] * (length - 1) + values[i]) / length
    return out


def _ema(values, length):
    out = np.full(len(values), np.nan)
    start = np.flatnonzero(~np.isnan(values))[0]
    out[start + length - 1] = np.mean(values[start:start + length])
    alpha = 2 / (length + 1)
    for i in range(start + length, len(values)):
        out[i] = alpha * values[i] + (1 - alpha) * out[i - 1]
    return out


def _true_range(df):
    prev = df["close"].shift(1)
    return pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1).max(axis=1).to_numpy()


def test_moving_averages_rsi_roc(ohlcv):
    close = ohlcv["close"]
    np.testing.assert_allclose(ti.sma(close, 20), close.rolling(20).mean(), atol=1e-9)
    np.testing.assert_allclose(ti.ema(close, 20), _ema(close.to_numpy(), 20), atol=1e-9)
    delta = np.diff(close.to_numpy())
    gain, loss = _wilder(np.clip(delta, 0, None), 14), _wilder(np.clip(-delta, 0, None), 14)
    np.testing.assert_allclose(ti.rsi(close, 14), np.r_[np.nan, 100 * gain / (gain + loss)], atol=1e-9)
    np.testing.assert_allclose(ti.roc(close, 10), 100 * (close / close.shift(10) - 1), atol=1e-9)


def test_macd(ohlcv):
    out = ti.macd(ohlcv["close"])
    assert list(out.columns) == ["MACD_12_26_9", "MACDh_12_26_9", "MACDs_12_26_9"]
    close = ohlcv["close"].to_numpy()
    line = _ema(close, 12) - _ema(close, 26)
    signal = _ema(line, 9)
    np.testing.assert_allclose(out["MACD_12_26_9"], line, atol=1e-9)
    np.testing.assert_allclose(out["MACDs_12_26_9"], signal, atol=1e-9)
    np.testing.assert_allclose(out["MACDh_12_26_9"], line - signal, atol=1e-9)


def test_atr_and_adx(ohlcv):
    np.testing.assert_allclose(ti.atr(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14), _wilder(_true_range(ohlcv), 14), atol=1e-9)
    out = ti.adx(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14)
    assert list(out.columns) == ["ADX_14", "DMP_14", "DMN_14"]
    last = out.iloc[-1]
    assert 0 <= last["ADX_14"] <= 100 and last["DMP_14"] > 0 and last["DMN_14"] > 0


def test_bbands(ohlcv):
    close = ohlcv["close"]
    out = ti.bbands(close, length=20, std=2)
    assert list(out.columns) == ["BBL_20_2.0", "BBM_20_2.0", "BBU_20_2.0", "BBB_20_2.0", "BBP_20_2.0"]
    mid, dev = close.rolling(20).mean(), close.rolling(20).std(ddof=0)
    np.testing.assert_allclose(out["BBL_20_2.0"], mid - 2 * dev, atol=1e-9)
    np.testing.assert_allclose(out["BBU_20_2.0"], mid + 2 * dev, atol=1e-9)
    np.testing.assert_allclose(out["BBP_20_2.0"], (close - (mid - 2 * dev)) / (4 * dev), atol=1e-9)


def test_oscillators(ohlcv):
    h, l, c = ohlcv["high"], ohlcv["low"], ohlcv["close"]
    stoch = ti.stoch(h, l, c, k=14, d=3, smooth_k=3)
    assert list(stoch.columns) == ["STOCHk_14_3_3", "STOCHd_14_3_3"]
    raw = 100 * (c - l.rolling(14).min()) / (h.rolling(14).max() - l.rolling(14).min())
    np.testing.assert_allclose(stoch["STOCHk_14_3_3"], raw.rolling(3).mean(), atol=1e-9)
    np.testing.assert_allclose(stoch["STOCHd_14_3_3"], raw.rolling(3).mean().rolling(3).mean(), atol=1e-9)

    tp = (h + l + c) / 3
    mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    np.testing.assert_allclose(ti.cci(h, l, c, 20), (tp - tp.rolling(20).mean()) / (0.015 * mad), atol=1e-8)

    aroon = ti.aroon(h, l, 25)
    assert list(aroon.columns) == ["AROOND_25", "AROONU_25", "AROONOSC_25"]
    i = len(h) - 1
    since_high = 25 - int(np.argmax(h.iloc[i - 25:i + 1].to_numpy()))
    assert aroon["AROONU_25"].iloc[-1] == pytest.approx(100 * (25 - since_high) / 25)


def test_volume_and_patterns(ohlcv):
    c, v = ohlcv["close"], ohlcv["volume"]
    expected_obv = (np.sign(c.diff()).fillna(1) * v).cumsum()
    np.testing.assert_allclose(ti.obv(c, v), expected_obv, rtol=1e-12)
    np.testing.assert_allclose(ti.vwap(ohlcv["high"], ohlcv["low"], c, v), (ohlcv["high"] + ohlcv["low"] + c) / 3, atol=1e-9)
    doji = ti.cdl_doji(ohlcv["open"], ohlcv["high"], ohlcv["low"], c)
    body = (c - ohlcv["open"]).abs()
    expected = (body < 0.1 * (ohlcv["high"] - ohlcv["low"]).rolling(10).mean()).astype(float)
    np.testing.assert_array_equal(doji, expected)


def test_missing_bar_is_skipped(ohlcv):
    ohlcv.iloc[150, ohlcv.columns.get_loc("close")] = np.nan
    rsi = ti.rsi(ohlcv["close"], 14)
    adx = ti.adx(ohlcv["high"], ohlcv["low"], ohlcv["close"], 14)
    assert np.isnan(rsi.iloc[150]) and rsi.iloc[151:].notna().all()
    assert adx.iloc[150].isna().all() and adx.iloc[-1].notna().all()
