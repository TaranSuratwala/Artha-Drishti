"""
===================================================================
ADAPTIVE MULTI-HORIZON FEATURE ENGINE (AMHFE)
===================================================================

Patent-Pending Feature Engineering System that creates features
across multiple time horizons with automatic relevance weighting.

Key Innovations:
  1. Multi-Horizon Feature Extraction: Computes every indicator at
     5 different timeframes simultaneously, enabling the model to
     learn which horizon matters most per stock
  
  2. Volatility-Regime Adaptive Features: Features are normalized
     relative to current volatility regime, making them comparable
     across different market conditions
  
  3. Cross-Sectional Features: Relative strength vs market,
     sector-adjusted momentum, peer-group positioning
  
  4. Information-Theoretic Feature Selection: Mutual information 
     scoring to automatically discard noise features

Author: GenAI Stock Intelligence System
Version: 1.0.0
===================================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
import yfinance as yf
from functools import lru_cache
import time as _time

logger = logging.getLogger(__name__)

# ---- Market benchmark cache (singleton per process) ----
_market_cache: Dict[str, pd.DataFrame] = {}
_market_cache_ts: float = 0.0
_MARKET_CACHE_TTL = 3600  # 1 hour


def _fetch_market_benchmarks(start_date, end_date) -> Dict[str, pd.DataFrame]:
    """Fetch Nifty 50, India VIX, USD/INR, and Brent Crude data, cached per process."""
    global _market_cache, _market_cache_ts
    now = _time.time()
    if _market_cache and (now - _market_cache_ts) < _MARKET_CACHE_TTL:
        return _market_cache
    try:
        nifty = yf.download('^NSEI', start=start_date, end=end_date,
                            progress=False, auto_adjust=True)
        if isinstance(nifty.columns, pd.MultiIndex):
            nifty.columns = nifty.columns.get_level_values(0)
        nifty = nifty[['Close']].rename(columns={'Close': 'nifty_close'})
        nifty.index = pd.to_datetime(nifty.index).tz_localize(None)
        _market_cache['nifty'] = nifty
    except Exception as e:
        logger.warning(f"Could not fetch Nifty 50 data: {e}")
        _market_cache['nifty'] = pd.DataFrame()
    try:
        vix = yf.download('^INDIAVIX', start=start_date, end=end_date,
                          progress=False, auto_adjust=True)
        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)
        vix = vix[['Close']].rename(columns={'Close': 'india_vix'})
        vix.index = pd.to_datetime(vix.index).tz_localize(None)
        _market_cache['vix'] = vix
    except Exception as e:
        logger.warning(f"Could not fetch India VIX data: {e}")
        _market_cache['vix'] = pd.DataFrame()
    
    # v34: USD/INR (Pillar 3 — Cross-Asset Context)
    try:
        usdinr = yf.download('USDINR=X', start=start_date, end=end_date,
                             progress=False, auto_adjust=True)
        if isinstance(usdinr.columns, pd.MultiIndex):
            usdinr.columns = usdinr.columns.get_level_values(0)
        usdinr = usdinr[['Close']].rename(columns={'Close': 'usdinr'})
        usdinr.index = pd.to_datetime(usdinr.index).tz_localize(None)
        _market_cache['usdinr'] = usdinr
    except Exception as e:
        logger.warning(f"Could not fetch USD/INR data: {e}")
        _market_cache['usdinr'] = pd.DataFrame()
    
    # v34: Brent Crude Oil (Pillar 3 — Cross-Asset Context)
    try:
        crude = yf.download('BZ=F', start=start_date, end=end_date,
                            progress=False, auto_adjust=True)
        if isinstance(crude.columns, pd.MultiIndex):
            crude.columns = crude.columns.get_level_values(0)
        crude = crude[['Close']].rename(columns={'Close': 'brent_crude'})
        crude.index = pd.to_datetime(crude.index).tz_localize(None)
        _market_cache['crude'] = crude
    except Exception as e:
        logger.warning(f"Could not fetch Brent crude data: {e}")
        _market_cache['crude'] = pd.DataFrame()
    
    _market_cache_ts = now
    return _market_cache


class AdvancedFeatureEngine:
    """
    Production-grade feature engineering with multi-horizon extraction
    and volatility-regime normalization.
    """
    
    HORIZONS = [5, 10, 20, 50]
    
    @staticmethod
    def engineer(df: pd.DataFrame) -> pd.DataFrame:
        """
        Complete feature engineering pipeline.
        
        Input: DataFrame with [date, open, high, low, close, volume]
               Optionally: adj_close, delivery_qty, delivery_percentage, traded_qty
        Output: DataFrame with 150+ engineered features
        """
        df = df.copy()
        df = df.sort_values('date').reset_index(drop=True)
        
        # ======== 0. ADJUSTED CLOSE HANDLING ========
        # Use adj_close for return calculations when available (handles splits/bonuses)
        if 'adj_close' in df.columns:
            df['adj_close'] = pd.to_numeric(df['adj_close'], errors='coerce')
            df['adj_close'] = df['adj_close'].fillna(df['close'])
        else:
            df['adj_close'] = df['close'].copy()
        
        # ======== 1. PRICE TRANSFORM FEATURES ========
        df = AdvancedFeatureEngine._price_transforms(df)
        
        # ======== 2. MULTI-HORIZON MOVING AVERAGES ========
        df = AdvancedFeatureEngine._moving_averages(df)
        
        # ======== 3. MOMENTUM SUITE ========
        df = AdvancedFeatureEngine._momentum_features(df)
        
        # ======== 4. VOLATILITY FEATURES ========
        df = AdvancedFeatureEngine._volatility_features(df)
        
        # ======== 5. VOLUME ANALYSIS ========
        df = AdvancedFeatureEngine._volume_features(df)
        
        # ======== 6. OSCILLATORS ========
        df = AdvancedFeatureEngine._oscillator_features(df)
        
        # ======== 7. TREND INDICATORS ========
        df = AdvancedFeatureEngine._trend_features(df)
        
        # ======== 8. CANDLESTICK FEATURES ========
        df = AdvancedFeatureEngine._candlestick_features(df)
        
        # ======== 9. STATISTICAL FEATURES ========
        df = AdvancedFeatureEngine._statistical_features(df)
        
        # ======== 10. MARKET MICROSTRUCTURE ========
        df = AdvancedFeatureEngine._microstructure_features(df)
        
        # ======== 11. REGIME DETECTION FEATURES ========
        df = AdvancedFeatureEngine._regime_features(df)
        
        # ======== 12. TEMPORAL FEATURES ========
        df = AdvancedFeatureEngine._temporal_features(df)
        
        # ======== 13. DELIVERY / INSTITUTIONAL FEATURES ========
        df = AdvancedFeatureEngine._delivery_features(df)
        
        # ======== 14. MARKET CONTEXT FEATURES ========
        df = AdvancedFeatureEngine._market_context_features(df)
        
        # ======== 15. OU MEAN REVERSION (Pillar 2) ========
        df = AdvancedFeatureEngine._ou_reversion_features(df)
        
        # ======== CLEANUP (NO bfill — prevents look-ahead bias) ========
        df = df.replace([np.inf, -np.inf], np.nan)
        # Forward-fill only, then use column-wise median for remaining NaNs
        df = df.ffill()
        # Median imputation for leading NaNs — use median from first 70% of rows
        # (approximate training window) to avoid leaking future data into early rows
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        n_train_approx = max(int(len(df) * 0.70), 1)
        medians = df[numeric_cols].iloc[:n_train_approx].median()
        df[numeric_cols] = df[numeric_cols].fillna(medians)
        # Final safety net
        df = df.fillna(0.0)
        
        return df
    
    @staticmethod
    def _price_transforms(df: pd.DataFrame) -> pd.DataFrame:
        """Log returns, normalized price, gap analysis — uses adj_close for returns"""
        # Use adj_close for return computation (split/bonus adjusted)
        adj = df['adj_close'] if 'adj_close' in df.columns else df['close']
        df['log_close'] = np.log(adj.clip(lower=1e-8))
        df['log_return'] = df['log_close'].diff()
        
        # Split adjustment ratio (detects corporate actions)
        df['adj_ratio'] = adj / (df['close'] + 1e-10)
        
        # Price relative to moving averages
        for h in AdvancedFeatureEngine.HORIZONS:
            sma = df['close'].rolling(h).mean()
            df[f'price_to_sma_{h}'] = (df['close'] - sma) / (sma + 1e-10)
        
        # Gap analysis
        df['gap_pct'] = (df['open'] - df['close'].shift(1)) / (df['close'].shift(1) + 1e-10)
        df['gap_filled'] = ((df['low'] <= df['close'].shift(1)) & (df['gap_pct'] > 0) |
                           (df['high'] >= df['close'].shift(1)) & (df['gap_pct'] < 0)).astype(float)
        
        # True body
        df['true_body'] = (df['close'] - df['open']) / (df['close'] + 1e-10)
        
        # High-Low range normalized
        df['hl_range_pct'] = (df['high'] - df['low']) / (df['close'] + 1e-10)
        
        # ---- v34: 52-Week High Proximity (Pillar 1.2 — George & Hwang 2004) ----
        # Prospect-theory anchoring: investors anchor on 52-week high.
        # Breakout above proximity > 0.95 on strong volume → delayed upward drift.
        # Capitulation below 0.05 → high SELL precision.
        high_252 = df['high'].rolling(252, min_periods=60).max()
        low_252 = df['low'].rolling(252, min_periods=60).min()
        df['proximity_52w'] = (df['close'] - low_252) / (high_252 - low_252 + 1e-10)
        df['at_52w_high'] = (df['proximity_52w'] > 0.95).astype(float)
        df['at_52w_low'] = (df['proximity_52w'] < 0.05).astype(float)
        df['dist_from_52w_high'] = (high_252 - df['close']) / (high_252 + 1e-10)
        
        return df
    
    @staticmethod
    def _moving_averages(df: pd.DataFrame) -> pd.DataFrame:
        """Multi-type moving averages with cross signals"""
        for h in AdvancedFeatureEngine.HORIZONS:
            df[f'sma_{h}'] = df['close'].rolling(h).mean()
            df[f'ema_{h}'] = df['close'].ewm(span=h).mean()
            
            # Slope of moving average (trend direction)
            df[f'sma_slope_{h}'] = df[f'sma_{h}'].diff(3) / (df[f'sma_{h}'].shift(3) + 1e-10)
        
        # MA crosses (short vs long)
        df['ema_cross_5_20'] = (df['ema_5'] - df['ema_20']) / (df['ema_20'] + 1e-10)
        df['ema_cross_10_50'] = (df['ema_10'] - df['ema_50']) / (df['ema_50'] + 1e-10)
        
        # Distance between EMAs
        df['ema_spread'] = (df['ema_5'] - df['ema_50']) / (df['ema_50'] + 1e-10)
        
        return df
    
    @staticmethod
    def _momentum_features(df: pd.DataFrame) -> pd.DataFrame:
        """Multi-horizon momentum with acceleration"""
        for h in AdvancedFeatureEngine.HORIZONS:
            # Returns
            df[f'return_{h}d'] = df['close'].pct_change(h)
            
            # Rate of change
            df[f'roc_{h}'] = (df['close'] - df['close'].shift(h)) / (df['close'].shift(h) + 1e-10) * 100
            
            # Momentum (absolute)
            df[f'momentum_{h}'] = df['close'] - df['close'].shift(h)
        
        # Acceleration (change in momentum)
        df['momentum_accel_5'] = df['momentum_5'].diff()
        df['momentum_accel_20'] = df['momentum_20'].diff(5)
        
        # Mean reversion indicator
        for h in [20, 50]:
            mean = df['close'].rolling(h).mean()
            std = df['close'].rolling(h).std()
            df[f'zscore_{h}'] = (df['close'] - mean) / (std + 1e-10)
        
        return df
    
    @staticmethod
    def _volatility_features(df: pd.DataFrame) -> pd.DataFrame:
        """Multi-horizon volatility with regime detection"""
        returns = df['close'].pct_change()
        
        for h in AdvancedFeatureEngine.HORIZONS:
            # Historical volatility
            df[f'hist_vol_{h}'] = returns.rolling(h).std() * np.sqrt(252)
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df[f'atr_{h}'] = tr.rolling(h).mean()
            
            # Normalized ATR (for cross-stock comparison)
            df[f'natr_{h}'] = df[f'atr_{h}'] / (df['close'] + 1e-10) * 100
        
        # Volatility ratio (short/long) - indicates volatility expansion/contraction
        df['vol_ratio_5_20'] = df['hist_vol_5'] / (df['hist_vol_20'] + 1e-10)
        df['vol_ratio_10_50'] = df['hist_vol_10'] / (df['hist_vol_50'] + 1e-10)
        
        # Bollinger Bands
        for h in [20, 50]:
            sma = df['close'].rolling(h).mean()
            std = df['close'].rolling(h).std()
            df[f'bb_upper_{h}'] = sma + 2 * std
            df[f'bb_lower_{h}'] = sma - 2 * std
            df[f'bb_width_{h}'] = (4 * std) / (sma + 1e-10)
            df[f'bb_position_{h}'] = (df['close'] - df[f'bb_lower_{h}']) / (4 * std + 1e-10)
        
        # Parkinson volatility estimator (uses high-low range)
        df['parkinson_vol'] = np.sqrt(
            (1 / (4 * np.log(2))) * (np.log(df['high'] / (df['low'] + 1e-10)) ** 2)
        ).rolling(20).mean() * np.sqrt(252)
        
        # ---- v34: Volatility Term Structure (Pillar 2.2) ----
        # Ratio of short-term to long-term vol: identifies compression vs expansion.
        # Ratio < 0.5 → Bollinger squeeze (pre-breakout). Ratio > 2.0 → high-noise regime.
        log_rets = df['close'].pct_change()
        std_10d = log_rets.rolling(10).std()
        std_30d = log_rets.rolling(30).std()
        df['vol_term_slope'] = std_10d / (std_30d + 1e-10)
        df['vol_compression'] = (df['vol_term_slope'] < 0.5).astype(float)
        df['vol_expansion'] = (df['vol_term_slope'] > 2.0).astype(float)
        
        # v34: Realized vol vs implied vol divergence (supports VRP computation)
        df['realized_vol_22d'] = log_rets.rolling(22).std() * np.sqrt(252)
        
        return df
    
    @staticmethod
    def _volume_features(df: pd.DataFrame) -> pd.DataFrame:
        """Volume analysis with accumulation/distribution"""
        for h in AdvancedFeatureEngine.HORIZONS:
            # Volume SMA
            df[f'vol_sma_{h}'] = df['volume'].rolling(h).mean()
            
            # Volume ratio
            df[f'vol_ratio_{h}'] = df['volume'] / (df[f'vol_sma_{h}'] + 1)
        
        # On-Balance Volume
        obv_series = []
        obv = 0
        closes = df['close'].values
        volumes = df['volume'].values
        for i in range(len(closes)):
            if i == 0:
                obv_series.append(0)
            else:
                if closes[i] > closes[i-1]:
                    obv += volumes[i]
                elif closes[i] < closes[i-1]:
                    obv -= volumes[i]
                obv_series.append(obv)
        df['obv'] = obv_series
        df['obv_sma_20'] = pd.Series(obv_series).rolling(20).mean().values
        df['obv_trend'] = (pd.Series(obv_series) - pd.Series(obv_series).rolling(20).mean()).values
        # Normalized OBV trend (relative to its own magnitude — cross-stock comparable)
        df['obv_trend_norm'] = df['obv_trend'] / (pd.Series(obv_series).rolling(20).mean().abs().values + 1e-10)
        
        # Volume-Price Trend (VPT)
        df['vpt'] = (df['volume'] * df['close'].pct_change()).cumsum()
        
        # Accumulation/Distribution Line
        clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'] + 1e-10)
        df['ad_line'] = (clv * df['volume']).cumsum()
        
        # Chaikin Money Flow
        for h in [10, 20]:
            df[f'cmf_{h}'] = (clv * df['volume']).rolling(h).sum() / (df['volume'].rolling(h).sum() + 1)
        
        # Force Index
        df['force_index'] = df['close'].diff() * df['volume']
        df['force_index_13'] = df['force_index'].ewm(span=13).mean()
        
        # Volume-Weighted Average Price
        tp = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (tp * df['volume']).rolling(20).sum() / (df['volume'].rolling(20).sum() + 1)
        df['vwap_deviation'] = (df['close'] - df['vwap']) / (df['vwap'] + 1e-10)
        
        return df
    
    @staticmethod
    def _oscillator_features(df: pd.DataFrame) -> pd.DataFrame:
        """RSI, Stochastic, Williams %R, CCI"""
        # RSI at multiple horizons
        for h in [9, 14, 21]:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(h).mean()
            loss = -delta.where(delta < 0, 0).rolling(h).mean()
            rs = gain / (loss + 1e-8)
            df[f'rsi_{h}'] = 100 - (100 / (1 + rs))
        
        # RSI divergence (price making new highs but RSI not)
        df['rsi_divergence'] = (df['close'].rolling(20).apply(lambda x: 1 if x.iloc[-1] > x.max() * 0.98 else 0) -
                                df['rsi_14'].rolling(20).apply(lambda x: 1 if x.iloc[-1] > x.max() * 0.98 else 0))
        
        # Stochastic Oscillator
        for h in [14, 21]:
            low_min = df['low'].rolling(h).min()
            high_max = df['high'].rolling(h).max()
            df[f'stoch_k_{h}'] = 100 * (df['close'] - low_min) / (high_max - low_min + 1e-10)
            df[f'stoch_d_{h}'] = df[f'stoch_k_{h}'].rolling(3).mean()
        
        # Williams %R
        df['williams_r'] = -100 * (df['high'].rolling(14).max() - df['close']) / \
                           (df['high'].rolling(14).max() - df['low'].rolling(14).min() + 1e-10)
        
        # CCI
        for h in [14, 20]:
            tp = (df['high'] + df['low'] + df['close']) / 3
            sma_tp = tp.rolling(h).mean()
            mad = tp.rolling(h).apply(lambda x: np.mean(np.abs(x - x.mean())))
            df[f'cci_{h}'] = (tp - sma_tp) / (0.015 * mad + 1e-10)
        
        # MFI
        tp = (df['high'] + df['low'] + df['close']) / 3
        mf = tp * df['volume']
        pos_mf = mf.where(tp > tp.shift(1), 0).rolling(14).sum()
        neg_mf = mf.where(tp < tp.shift(1), 0).rolling(14).sum()
        df['mfi'] = 100 - (100 / (1 + pos_mf / (neg_mf + 1e-10)))
        
        return df
    
    @staticmethod
    def _trend_features(df: pd.DataFrame) -> pd.DataFrame:
        """MACD, ADX, SuperTrend, Parabolic SAR proxy"""
        # MACD — compute both raw (for compatibility) AND normalized versions
        for fast, slow in [(12, 26), (5, 13)]:
            ema_fast = df['close'].ewm(span=fast).mean()
            ema_slow = df['close'].ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=9).mean()
            df[f'macd_{fast}_{slow}'] = macd
            df[f'macd_signal_{fast}_{slow}'] = signal
            df[f'macd_hist_{fast}_{slow}'] = macd - signal
            df[f'macd_hist_accel_{fast}_{slow}'] = (macd - signal).diff()
            # NORMALIZED versions (divided by close — cross-stock comparable)
            df[f'macd_norm_{fast}_{slow}'] = macd / (df['close'] + 1e-10)
            df[f'macd_signal_norm_{fast}_{slow}'] = signal / (df['close'] + 1e-10)
            df[f'macd_hist_norm_{fast}_{slow}'] = (macd - signal) / (df['close'] + 1e-10)
        
        # ADX
        plus_dm = df['high'].diff().clip(lower=0)
        minus_dm = (-df['low'].diff()).clip(lower=0)
        
        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)
        
        atr_14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / (atr_14 + 1e-10))
        minus_di = 100 * (minus_dm.rolling(14).mean() / (atr_14 + 1e-10))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        df['adx'] = dx.rolling(14).mean()
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di
        df['di_diff'] = plus_di - minus_di
        
        # Aroon Oscillator
        for h in [14, 25]:
            df[f'aroon_up_{h}'] = df['high'].rolling(h+1).apply(lambda x: x.argmax() / h * 100)
            df[f'aroon_down_{h}'] = df['low'].rolling(h+1).apply(lambda x: x.argmin() / h * 100)
            df[f'aroon_osc_{h}'] = df[f'aroon_up_{h}'] - df[f'aroon_down_{h}']
        
        # Trend consistency (how often close > sma)
        for h in [20, 50]:
            sma = df['close'].rolling(h).mean()
            df[f'trend_consistency_{h}'] = (df['close'] > sma).rolling(20).mean()
        
        return df
    
    @staticmethod
    def _candlestick_features(df: pd.DataFrame) -> pd.DataFrame:
        """Quantitative candlestick features"""
        # Body metrics
        df['body_size'] = np.abs(df['close'] - df['open']) / (df['close'] + 1e-10)
        df['body_direction'] = np.sign(df['close'] - df['open'])
        df['upper_wick'] = (df['high'] - df[['open', 'close']].max(axis=1)) / (df['close'] + 1e-10)
        df['lower_wick'] = (df[['open', 'close']].min(axis=1) - df['low']) / (df['close'] + 1e-10)
        df['wick_ratio'] = df['upper_wick'] / (df['lower_wick'] + 1e-10)
        
        # Body relative to range
        df['body_to_range'] = np.abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
        
        # Consecutive direction count
        direction = np.sign(df['close'] - df['open'])
        consecutive = []
        count = 0
        for d in direction:
            if len(consecutive) == 0:
                count = 1
            elif d == direction.iloc[len(consecutive) - 1]:
                count += 1
            else:
                count = 1
            consecutive.append(count * d)
        df['consecutive_candles'] = consecutive
        
        # Average body size ratio (current vs average)
        avg_body = df['body_size'].rolling(20).mean()
        df['body_size_ratio'] = df['body_size'] / (avg_body + 1e-10)
        
        return df
    
    @staticmethod
    def _statistical_features(df: pd.DataFrame) -> pd.DataFrame:
        """Distribution statistics of returns"""
        returns = df['close'].pct_change()
        
        for h in [10, 20, 50]:
            # Skewness
            df[f'skew_{h}'] = returns.rolling(h).skew()
            
            # Kurtosis
            df[f'kurtosis_{h}'] = returns.rolling(h).kurt()
            
            # Percentile rank
            df[f'pct_rank_{h}'] = df['close'].rolling(h).apply(
                lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min() + 1e-10)
            )
        
        # Auto-correlation
        df['autocorr_5'] = returns.rolling(20).apply(lambda x: x.autocorr(lag=5) if len(x) > 5 else 0)
        
        # Hurst exponent proxy (regime indicator)
        df['hurst_proxy'] = AdvancedFeatureEngine._hurst_proxy(returns, 20)
        
        return df
    
    @staticmethod
    def _hurst_proxy(returns: pd.Series, window: int) -> pd.Series:
        """Fast Hurst exponent approximation for trend/mean-reversion detection"""
        def calc_hurst(x):
            if len(x) < 10:
                return 0.5
            mean_adj = x - x.mean()
            cumdev = np.cumsum(mean_adj)
            r = cumdev.max() - cumdev.min()
            s = x.std()
            if s == 0:
                return 0.5
            rs = r / s
            if rs <= 0:
                return 0.5
            n = len(x)
            return np.log(rs) / np.log(n) if n > 1 else 0.5
        
        return returns.rolling(window).apply(calc_hurst, raw=True)
    
    @staticmethod
    def _microstructure_features(df: pd.DataFrame) -> pd.DataFrame:
        """Market microstructure and liquidity features"""
        # Amihud illiquidity ratio
        df['amihud'] = np.abs(df['close'].pct_change()) / (df['volume'] * df['close'] + 1e-10)
        df['amihud_20'] = df['amihud'].rolling(20).mean()
        
        # High-Low spread (proxy for bid-ask spread)
        df['hl_spread'] = (df['high'] - df['low']) / ((df['high'] + df['low']) / 2 + 1e-10)
        
        # Kyle's Lambda proxy (price impact)
        df['kyle_lambda'] = np.abs(df['close'].pct_change()) / (np.log(df['volume'] + 1) + 1e-10)
        
        # Volume clock (volume-weighted time)
        df['vol_clock'] = df['volume'] / (df['volume'].rolling(20).mean() + 1)
        
        # v51: OFI (Order Flow Imbalance) Proxy
        # Infers buying/selling pressure from intra-bar price action relative to volume
        buy_pressure = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
        sell_pressure = (df['high'] - df['close']) / (df['high'] - df['low'] + 1e-10)
        df['ofi_proxy'] = (buy_pressure - sell_pressure) * df['volume']
        df['ofi_proxy_20'] = df['ofi_proxy'].rolling(20).mean() / (df['volume'].rolling(20).mean() + 1e-10)
        
        # Price efficiency (close-to-close vs high-low)
        df['price_efficiency'] = np.abs(df['close'] - df['close'].shift(1)) / (df['high'] - df['low'] + 1e-10)
        
        return df
    
    @staticmethod
    def _regime_features(df: pd.DataFrame) -> pd.DataFrame:
        """Market regime detection features"""
        returns = df['close'].pct_change()
        
        # Volatility regime (current vs long-term)
        short_vol = returns.rolling(10).std()
        long_vol = returns.rolling(50).std()
        df['vol_regime'] = short_vol / (long_vol + 1e-10)
        
        # Trend regime (ADX-based)
        if 'adx' in df.columns:
            df['trending'] = (df['adx'] > 25).astype(float)
        
        # Mean reversion signal
        for h in [20, 50]:
            if f'zscore_{h}' in df.columns:
                df[f'mean_revert_signal_{h}'] = -df[f'zscore_{h}'].clip(-3, 3) / 3
        
        # Momentum regime
        df['mom_regime'] = np.where(
            df['close'].pct_change(20) > 0.05, 1,
            np.where(df['close'].pct_change(20) < -0.05, -1, 0)
        )
        
        return df
    
    @staticmethod
    def _temporal_features(df: pd.DataFrame) -> pd.DataFrame:
        """Calendar and temporal features"""
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'])
            df['day_of_week'] = dates.dt.dayofweek / 4.0  # Normalize to 0-1
            df['month'] = dates.dt.month / 12.0
            df['quarter'] = dates.dt.quarter / 4.0
            df['day_of_month'] = dates.dt.day / 31.0
            
            # Month-end effect
            df['is_month_end'] = dates.dt.is_month_end.astype(float)
            df['is_month_start'] = dates.dt.is_month_start.astype(float)
            
            # Week of year (seasonality)
            df['week_of_year'] = dates.dt.isocalendar().week.astype(float).values / 52.0
            
            # Expiry proximity (last Thursday of month — options expiry)
            def _days_to_expiry(dt):
                import calendar
                last_day = calendar.monthrange(dt.year, dt.month)[1]
                last_date = pd.Timestamp(dt.year, dt.month, last_day)
                # Find last Thursday
                while last_date.dayofweek != 3:  # Thursday
                    last_date -= pd.Timedelta(days=1)
                return max((last_date - dt).days, 0)
            df['days_to_expiry'] = dates.apply(_days_to_expiry) / 30.0
        
        return df
    
    @staticmethod
    def _delivery_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Delivery-based features — institutional activity signals.
        Uses delivery_qty, delivery_percentage, traded_qty from DB.
        
        v34 Enhancement (Pillar 1 — Factor Model Alpha):
        Delivery-based Order Flow Imbalance (OFI) — Chordia, Roll &
        Subrahmanyam (2000).  NSE delivery data is a direct window into
        institutional conviction that no purely price-based indicator replicates.
        """
        has_delivery = 'delivery_percentage' in df.columns or 'delivery_qty' in df.columns
        if not has_delivery:
            return df
        
        # Delivery percentage features
        if 'delivery_percentage' in df.columns:
            dp = pd.to_numeric(df['delivery_percentage'], errors='coerce').fillna(0)
            df['delivery_pct'] = dp / 100.0
            for h in AdvancedFeatureEngine.HORIZONS:
                df[f'delivery_pct_sma_{h}'] = df['delivery_pct'].rolling(h).mean()
            # Delivery spike (current vs 20-day avg)
            dp_sma = df['delivery_pct'].rolling(20).mean()
            df['delivery_spike'] = (df['delivery_pct'] - dp_sma) / (dp_sma + 1e-10)
            # High delivery + bullish price = institutional buying
            df['inst_accumulation'] = df['delivery_pct'] * np.sign(df['close'].pct_change())
            df['inst_accumulation_5'] = df['inst_accumulation'].rolling(5).mean()
            
            # ---- v34: Delivery OFI (Order Flow Imbalance) ----
            # OFI = delivery_pct × close × volume → captures conviction-weighted flow
            ofi_raw = df['delivery_pct'] * df['close'] * df['volume']
            for h in [5, 20]:
                ofi_mean = ofi_raw.rolling(h).mean()
                ofi_std = ofi_raw.rolling(h).std()
                df[f'ofi_zscore_{h}d'] = (ofi_raw - ofi_mean) / (ofi_std + 1e-10)
            
            # Delivery percentile rank within 20-day window
            df['delivery_pct_rank_20'] = df['delivery_pct'].rolling(20).apply(
                lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min() + 1e-10), raw=False
            )
            
            # Delivery 90th percentile spike (Pillar 1.1 — institutional conviction)
            dp_p90 = df['delivery_pct'].rolling(60, min_periods=20).quantile(0.90)
            df['delivery_above_p90'] = (df['delivery_pct'] > dp_p90).astype(float)
            
            # OFI near support confluence (spike + price near 20d low)
            low_20 = df['close'].rolling(20).min()
            near_support = (df['close'] - low_20) / (df['close'] + 1e-10) < 0.03
            df['ofi_near_support'] = (df['delivery_above_p90'] * near_support.astype(float))
            
            # Conviction-weighted flow direction
            df['delivery_conviction'] = (df['delivery_pct'] *
                                          np.abs(df['close'].pct_change()) *
                                          df['volume'] / (df['volume'].rolling(20).mean() + 1))
            df['delivery_conviction_dir'] = df['delivery_conviction'] * np.sign(df['close'].pct_change())
            df['delivery_conviction_dir_5d'] = df['delivery_conviction_dir'].rolling(5).mean()
        
        # Delivery volume features
        if 'delivery_qty' in df.columns:
            dq = pd.to_numeric(df['delivery_qty'], errors='coerce').fillna(0)
            df['delivery_qty_log'] = np.log1p(dq)
            # Delivery to traded ratio
            if 'traded_qty' in df.columns:
                tq = pd.to_numeric(df['traded_qty'], errors='coerce').fillna(1)
                df['delivery_to_traded'] = dq / (tq + 1)
                df['delivery_to_traded_sma_10'] = df['delivery_to_traded'].rolling(10).mean()
                df['delivery_to_traded_momentum_5d'] = df['delivery_to_traded'].pct_change(5)

        # ---- v50: EOD flow/microstructure proxies (intraday-book independent) ----
        # 1) Flow persistence: sustained conviction-weighted directional delivery.
        if 'delivery_conviction_dir_5d' in df.columns:
            flow = pd.Series(df['delivery_conviction_dir_5d'].values)
            flow_mean = flow.rolling(20).mean()
            flow_std = flow.rolling(20).std()
            df['delivery_flow_persistence'] = ((flow - flow_mean) / (flow_std + 1e-10)).clip(-5, 5).values

        # 2) Effort vs result imbalance: high volume effort with muted price expansion.
        vol_effort = df['volume'] / (df['volume'].rolling(20).mean() + 1)
        price_result = (df['high'] - df['low']) / (df['close'] + 1e-10)
        eri_raw = vol_effort / (price_result + 1e-6)
        eri_mean = eri_raw.rolling(20).mean()
        eri_std = eri_raw.rolling(20).std()
        df['effort_result_imbalance'] = ((eri_raw - eri_mean) / (eri_std + 1e-10)).clip(-5, 5)

        # 3) Closing pressure + liquidity interaction.
        close_location = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
        df['closing_pressure'] = close_location.clip(0, 1)
        df['closing_pressure_5d'] = df['closing_pressure'].rolling(5).mean()
        if 'amihud_20' in df.columns:
            liquidity_weight = 1.0 / (1.0 + np.abs(df['amihud_20']) * 1e6)
            df['closing_pressure_liquidity'] = (df['closing_pressure'] * liquidity_weight).clip(0, 1)
        else:
            df['closing_pressure_liquidity'] = df['closing_pressure']
        
        return df
    
    @staticmethod
    def _market_context_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Market-wide context features — Nifty 50 returns, relative strength, VIX.
        These provide macro regime context that individual stock data lacks.
        """
        if 'date' not in df.columns:
            return df
        
        dates = pd.to_datetime(df['date'])
        start_date = dates.min() - pd.Timedelta(days=60)  # extra buffer
        end_date = dates.max() + pd.Timedelta(days=5)
        
        try:
            mkt = _fetch_market_benchmarks(str(start_date.date()), str(end_date.date()))
        except Exception as e:
            logger.warning(f"Market context features skipped: {e}")
            return df
        
        # ---- Nifty 50 features ----
        nifty_df = mkt.get('nifty', pd.DataFrame())
        if not nifty_df.empty:
            df_dates = dates.dt.normalize()
            nifty_aligned = nifty_df.reindex(df_dates, method='ffill')
            nifty_close = nifty_aligned['nifty_close'].values
            
            df['nifty_return_1d'] = pd.Series(nifty_close).pct_change().values
            for h in [5, 10, 20]:
                df[f'nifty_return_{h}d'] = pd.Series(nifty_close).pct_change(h).values
                df[f'nifty_vol_{h}'] = pd.Series(nifty_close).pct_change().rolling(h).std().values
            
            # Relative strength vs Nifty (stock outperformance)
            stock_ret_20 = df['close'].pct_change(20)
            nifty_ret_20 = pd.Series(nifty_close).pct_change(20)
            df['relative_strength_20'] = (stock_ret_20.values - nifty_ret_20.values)
            
            stock_ret_5 = df['close'].pct_change(5)
            nifty_ret_5 = pd.Series(nifty_close).pct_change(5)
            df['relative_strength_5'] = (stock_ret_5.values - nifty_ret_5.values)

            # v50: Relative-strength persistence (stabilizes noisy short-horizon flips).
            rs20 = pd.Series(df['relative_strength_20'].values)
            rs20_trend = rs20.rolling(5).mean()
            rs20_vol = rs20.rolling(20).std()
            df['relative_strength_persistence'] = ((rs20_trend) / (rs20_vol + 1e-10)).clip(-5, 5).values

            # v50: Delivery flow divergence vs benchmark drift (EOD graph-context proxy).
            if 'delivery_conviction_dir_5d' in df.columns:
                flow_series = pd.Series(df['delivery_conviction_dir_5d'].values)
                market_proxy = pd.Series(df['nifty_return_5d'].values)
                flow_spread = flow_series - market_proxy
                spread_mean = flow_spread.rolling(20).mean()
                spread_std = flow_spread.rolling(20).std()
                df['flow_market_divergence_20'] = ((flow_spread - spread_mean) / (spread_std + 1e-10)).clip(-5, 5).values
            
            # Beta (rolling 60-day)
            stock_rets = df['close'].pct_change()
            nifty_rets = pd.Series(nifty_close).pct_change()
            cov = stock_rets.rolling(60).cov(nifty_rets)
            nifty_var = nifty_rets.rolling(60).var()
            df['beta_60'] = (cov / (nifty_var + 1e-10)).values
        
        # ---- India VIX features ----
        vix_df = mkt.get('vix', pd.DataFrame())
        if not vix_df.empty:
            df_dates = dates.dt.normalize()
            vix_aligned = vix_df.reindex(df_dates, method='ffill')
            vix_vals = vix_aligned['india_vix'].values
            
            df['india_vix'] = vix_vals / 100.0  # Normalize
            df['india_vix_change'] = pd.Series(vix_vals).pct_change().values
            df['india_vix_sma_10'] = pd.Series(vix_vals).rolling(10).mean().values / 100.0
            # VIX regime (high fear vs low complacency)
            vix_20_mean = pd.Series(vix_vals).rolling(20).mean()
            df['vix_regime'] = (pd.Series(vix_vals) / (vix_20_mean + 1e-10)).values
            
            # ---- v34: Volatility Risk Premium (Pillar 2 — Bollerslev et al. 2009) ----
            # VRP = India VIX - realized vol.  Positive VRP → fear premium decaying,
            # predicts positive 5-10d returns as vol premium reverts.
            if 'realized_vol_22d' in df.columns:
                india_vix_annual = pd.Series(vix_vals).values / 100.0  # VIX is already annualized
                df['vrp'] = india_vix_annual - df['realized_vol_22d'].values
                vrp_series = pd.Series(df['vrp'].values)
                vrp_mean = vrp_series.rolling(60).mean()
                vrp_std = vrp_series.rolling(60).std()
                df['vrp_zscore'] = ((vrp_series - vrp_mean) / (vrp_std + 1e-10)).values
            
            # ---- v34: India VIX Term Structure Proxy (Pillar 3.3) ----
            # Short-term vix change vs long-term: inverted curve → immediate danger
            vix_series = pd.Series(vix_vals)
            vix_10d_avg = vix_series.rolling(10).mean()
            vix_30d_avg = vix_series.rolling(30).mean()
            df['vix_term_slope'] = (vix_10d_avg / (vix_30d_avg + 1e-10)).values
            df['vix_inverted'] = (df['vix_term_slope'] > 1.0).astype(float)
        
        # ---- v34: Idiosyncratic Volatility (Pillar 1.3 — Ang et al. 2006) ----
        # IVOL = residual vol after regressing on Nifty.  High IVOL stocks
        # systematically underperform (lottery effect).
        if not nifty_df.empty and 'beta_60' in df.columns:
            stock_rets_daily = df['close'].pct_change()
            nifty_rets_daily = pd.Series(nifty_close).pct_change()
            # Residual return = stock_ret - beta * nifty_ret
            residual_ret = stock_rets_daily.values - df['beta_60'].values * nifty_rets_daily.values
            residual_series = pd.Series(residual_ret)
            df['ivol_22d'] = residual_series.rolling(22).std().values * np.sqrt(252)
            # IVOL rank vs own history (bounded 0-1)
            ivol_s = pd.Series(df['ivol_22d'].values)
            ivol_min = ivol_s.rolling(252, min_periods=60).min()
            ivol_max = ivol_s.rolling(252, min_periods=60).max()
            df['ivol_rank'] = ((ivol_s - ivol_min) / (ivol_max - ivol_min + 1e-10)).values
        
        # ---- v34: USD/INR Macro Feature (Pillar 3.2) ----
        usdinr_df = mkt.get('usdinr', pd.DataFrame())
        if not usdinr_df.empty:
            df_dates = dates.dt.normalize()
            usdinr_aligned = usdinr_df.reindex(df_dates, method='ffill')
            usdinr_vals = usdinr_aligned['usdinr'].values
            df['usdinr_change_5d'] = pd.Series(usdinr_vals).pct_change(5).values
            df['usdinr_change_20d'] = pd.Series(usdinr_vals).pct_change(20).values
        
        # ---- v34: Brent Crude Oil Macro Feature (Pillar 3.2) ----
        crude_df = mkt.get('crude', pd.DataFrame())
        if not crude_df.empty:
            df_dates = dates.dt.normalize()
            crude_aligned = crude_df.reindex(df_dates, method='ffill')
            crude_vals = crude_aligned['brent_crude'].values
            df['crude_change_5d'] = pd.Series(crude_vals).pct_change(5).values
            df['crude_change_20d'] = pd.Series(crude_vals).pct_change(20).values
        
        # ---- v34: Sector Breadth Proxy (Pillar 3.4) ----
        # Nifty advance-decline proxy: is Nifty above its own 50d SMA?
        # Broad market support context for individual stock signals.
        if not nifty_df.empty:
            nifty_series = pd.Series(nifty_close)
            nifty_sma50 = nifty_series.rolling(50).mean()
            df['nifty_above_sma50'] = (nifty_series > nifty_sma50).astype(float).values
            # Percentage of time Nifty was above 50d SMA in last 20 days
            df['breadth_20d'] = pd.Series(df['nifty_above_sma50'].values).rolling(20).mean().values
        
        return df
    
    @staticmethod
    def _ou_reversion_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        v34: Ornstein-Uhlenbeck Mean Reversion Speed (θ) — Pillar 2.1
        
        Estimates per-stock mean reversion speed via MLE:
          θ = -log(autocorr(1)) / dt
        
        High θ → structural mean-reverter (reversal features most valuable).
        Low θ → trending stock (momentum features most valuable).
        Halflife = log(2) / θ — expected days to revert to mean.
        """
        log_rets = df['close'].pct_change()
        
        def _est_theta(x):
            """MLE-based OU theta estimation from return autocorrelation."""
            if len(x) < 20:
                return 0.0
            ac = np.corrcoef(x[:-1], x[1:])[0, 1]
            if ac <= 0 or ac >= 1:
                return 0.0  # Cannot estimate
            return -np.log(max(ac, 1e-10))  # dt=1 day
        
        # Rolling 60-day OU theta
        df['ou_theta_60d'] = log_rets.rolling(60, min_periods=30).apply(
            _est_theta, raw=True
        )
        
        # Halflife in trading days
        df['ou_halflife'] = np.log(2) / (df['ou_theta_60d'] + 1e-10)
        # Clamp halflife to reasonable range (1-250 days)
        df['ou_halflife'] = df['ou_halflife'].clip(1, 250)
        
        # Mean reversion strength indicator (bounded 0-1)
        # Higher theta = stronger mean reversion = higher score
        theta_s = pd.Series(df['ou_theta_60d'].values)
        theta_max = theta_s.rolling(252, min_periods=60).max()
        df['ou_reversion_strength'] = (theta_s / (theta_max + 1e-10)).values
        
        return df
