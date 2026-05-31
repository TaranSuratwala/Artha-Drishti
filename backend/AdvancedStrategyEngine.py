"""
Advanced Multi-Strategy Screening Engine (AMSE)
===============================================
Patent-Pending Component: Multi-Strategy Committee Screening with
Weighted Ensemble Scoring and Sector Rotation Detection.

Core Innovation:
- Evaluates stocks against 18+ independent strategies simultaneously
- Each strategy uses weighted rule-based scoring with domain-specific thresholds
- "Committee of Experts" approach: a stock qualifies only when N+ strategies agree
- Sector Rotation detection across Indian & global markets

Version: 2.0.0
Integrated from: BTP SEM-5 AdvancedStrategyEngine + Project sem-6 architecture
"""

import pandas as pd
import numpy as np
import ta
import yfinance as yf
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import warnings

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


# ============================================================================
# COMPREHENSIVE INDICATOR LIBRARY
# ============================================================================

def compute_full_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute 30+ technical indicators across momentum, trend, volatility,
    volume, and oscillator categories.

    Returns enriched DataFrame with all indicators as new columns.
    """
    if df is None or len(df) < 50:
        return df

    try:
        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close, window=20)
        df["BB_upper"] = bb.bollinger_hband()
        df["BB_lower"] = bb.bollinger_lband()
        df["BB_mid"] = bb.bollinger_mavg()
        df["BB_width"] = (df["BB_upper"] - df["BB_lower"]) / df["BB_mid"]
        df["BB_pct"] = (close - df["BB_lower"]) / (df["BB_upper"] - df["BB_lower"])

        # RSI
        df["RSI"] = ta.momentum.RSIIndicator(close, window=14).rsi()
        df["RSI_SMA"] = df["RSI"].rolling(10).mean()

        # MACD
        macd = ta.trend.MACD(close)
        df["MACD"] = macd.macd()
        df["MACD_Signal"] = macd.macd_signal()
        df["MACD_Hist"] = macd.macd_diff()

        # ADX / DMI
        adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
        df["+DMI"] = adx_ind.adx_pos()
        df["-DMI"] = adx_ind.adx_neg()
        df["ADX"] = adx_ind.adx()

        # Stochastic
        stoch = ta.momentum.StochasticOscillator(high, low, close)
        df["Stoch_K"] = stoch.stoch()
        df["Stoch_D"] = stoch.stoch_signal()

        # CCI
        df["CCI"] = ta.trend.CCIIndicator(high, low, close, window=20).cci()

        # Williams %R
        df["Williams_R"] = ta.momentum.WilliamsRIndicator(high, low, close).williams_r()

        # ATR
        df["ATR"] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
        df["ATR_pct"] = df["ATR"] / close * 100

        # OBV
        df["OBV"] = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
        df["OBV_SMA"] = df["OBV"].rolling(20).mean()

        # MFI
        df["MFI"] = ta.volume.MFIIndicator(high, low, close, volume, window=14).money_flow_index()

        # VWAP approximation
        df["VWAP"] = (volume * (high + low + close) / 3).cumsum() / volume.cumsum()

        # Moving Averages (5 periods × 2 types = 10 columns)
        for period in [10, 20, 50, 100, 200]:
            df[f"SMA_{period}"] = close.rolling(period).mean()
            df[f"EMA_{period}"] = close.ewm(span=period).mean()

        # Volume analytics
        df["Vol_MA"] = volume.rolling(20).mean()
        df["Vol_Ratio"] = volume / df["Vol_MA"]

        # Rate of Change
        df["ROC_12"] = ta.momentum.ROCIndicator(close, window=12).roc()
        df["ROC_26"] = ta.momentum.ROCIndicator(close, window=26).roc()

        # Ichimoku Cloud
        ichi = ta.trend.IchimokuIndicator(high, low)
        df["Ichimoku_A"] = ichi.ichimoku_a()
        df["Ichimoku_B"] = ichi.ichimoku_b()
        df["Ichimoku_Base"] = ichi.ichimoku_base_line()
        df["Ichimoku_Conv"] = ichi.ichimoku_conversion_line()

        # Parabolic SAR
        df["PSAR"] = ta.trend.PSARIndicator(high, low, close).psar()

        # Proper Supertrend indicator with band-flipping logic
        atr_mult = 3
        hl2 = (high + low) / 2
        basic_upper = hl2 + (atr_mult * df["ATR"])
        basic_lower = hl2 - (atr_mult * df["ATR"])

        # Build final upper/lower bands with memory (band sticks until broken)
        final_upper = basic_upper.copy()
        final_lower = basic_lower.copy()
        supertrend = pd.Series(index=df.index, dtype=float)
        supertrend_dir = pd.Series(index=df.index, dtype=float)  # 1=bullish, -1=bearish

        for i in range(1, len(df)):
            # Final upper band: can only decrease (tighten) while close stays below
            if basic_upper.iloc[i] < final_upper.iloc[i - 1] or close.iloc[i - 1] > final_upper.iloc[i - 1]:
                final_upper.iloc[i] = basic_upper.iloc[i]
            else:
                final_upper.iloc[i] = final_upper.iloc[i - 1]

            # Final lower band: can only increase (tighten) while close stays above
            if basic_lower.iloc[i] > final_lower.iloc[i - 1] or close.iloc[i - 1] < final_lower.iloc[i - 1]:
                final_lower.iloc[i] = basic_lower.iloc[i]
            else:
                final_lower.iloc[i] = final_lower.iloc[i - 1]

        # Determine direction: flip between upper and lower bands
        supertrend_dir.iloc[0] = 1  # start bullish
        for i in range(1, len(df)):
            prev_dir = supertrend_dir.iloc[i - 1]
            if prev_dir == 1:  # was bullish
                if close.iloc[i] < final_lower.iloc[i]:
                    supertrend_dir.iloc[i] = -1  # flip bearish
                else:
                    supertrend_dir.iloc[i] = 1
            else:  # was bearish
                if close.iloc[i] > final_upper.iloc[i]:
                    supertrend_dir.iloc[i] = 1  # flip bullish
                else:
                    supertrend_dir.iloc[i] = -1

            # Set supertrend value
            if supertrend_dir.iloc[i] == 1:
                supertrend.iloc[i] = final_lower.iloc[i]
            else:
                supertrend.iloc[i] = final_upper.iloc[i]

        df["Supertrend"] = supertrend
        df["Supertrend_Dir"] = supertrend_dir
        df["Supertrend_Upper"] = final_upper
        df["Supertrend_Lower"] = final_lower

    except Exception as e:
        logger.warning(f"Error computing indicators: {e}")

    return df


# ============================================================================
# 18 ADVANCED STRATEGY DEFINITIONS (Patent-Pending)
# ============================================================================

ADVANCED_STRATEGIES = {
    # ──── Trend Following (5 strategies) ────
    "Swing Trader": {
        "category": "Trend Following",
        "description": "Medium-term momentum with trend confirmation",
        "risk_level": "Moderate",
        "timeframe": "1-4 weeks",
        "rules": [
            {"indicator": "MACD", "condition": "bullish_cross", "weight": 2.0},
            {"indicator": "RSI", "condition": "between", "min": 50, "max": 70, "weight": 1.5},
            {"indicator": "ADX", "condition": "above", "threshold": 25, "weight": 1.5},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.2, "weight": 1.0},
        ],
    },
    "Trend Rider": {
        "category": "Trend Following",
        "description": "Strong trending stocks with directional bias",
        "risk_level": "Moderate",
        "timeframe": "2-8 weeks",
        "rules": [
            {"indicator": "ADX", "condition": "above", "threshold": 30, "weight": 2.5},
            {"indicator": "EMA_Cross", "condition": "bullish", "fast": 12, "slow": 26, "weight": 2.0},
            {"indicator": "RSI", "condition": "above", "threshold": 55, "weight": 1.5},
            {"indicator": "Volume", "condition": "trending_up", "weight": 1.0},
            {"indicator": "+DMI", "condition": "above_minus", "weight": 1.5},
        ],
    },
    "Golden Cross": {
        "category": "Trend Following",
        "description": "50-day SMA crossing above 200-day SMA",
        "risk_level": "Low",
        "timeframe": "3-12 months",
        "rules": [
            {"indicator": "SMA_Cross", "condition": "golden", "fast": 50, "slow": 200, "weight": 3.0},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.5, "weight": 1.5},
            {"indicator": "ADX", "condition": "above", "threshold": 20, "weight": 1.0},
            {"indicator": "RSI", "condition": "above", "threshold": 50, "weight": 1.0},
        ],
    },
    "Ichimoku Cloud Breakout": {
        "category": "Trend Following",
        "description": "Price breaking above Ichimoku cloud",
        "risk_level": "Moderate",
        "timeframe": "2-8 weeks",
        "rules": [
            {"indicator": "Ichimoku", "condition": "above_cloud", "weight": 3.0},
            {"indicator": "Ichimoku", "condition": "bullish_tk_cross", "weight": 2.0},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.2, "weight": 1.0},
            {"indicator": "RSI", "condition": "above", "threshold": 50, "weight": 1.0},
        ],
    },
    "Supertrend Bullish": {
        "category": "Trend Following",
        "description": "Price above supertrend with confirming momentum",
        "risk_level": "Moderate",
        "timeframe": "1-6 weeks",
        "rules": [
            {"indicator": "Supertrend", "condition": "bullish", "weight": 2.5},
            {"indicator": "MACD", "condition": "bullish", "weight": 1.5},
            {"indicator": "RSI", "condition": "above", "threshold": 50, "weight": 1.0},
            {"indicator": "ADX", "condition": "above", "threshold": 20, "weight": 1.0},
        ],
    },

    # ──── Momentum (3 strategies) ────
    "Momentum Hunter": {
        "category": "Momentum",
        "description": "High momentum stocks breaking out",
        "risk_level": "High",
        "timeframe": "1-3 weeks",
        "rules": [
            {"indicator": "RSI", "condition": "above", "threshold": 60, "weight": 2.0},
            {"indicator": "MACD", "condition": "bullish", "weight": 1.5},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.5, "weight": 2.0},
            {"indicator": "SMA_Cross", "condition": "golden", "fast": 20, "slow": 50, "weight": 1.5},
            {"indicator": "ROC", "condition": "above", "threshold": 5, "weight": 1.5},
        ],
    },
    "Breakout Scanner": {
        "category": "Momentum",
        "description": "Stocks breaking out of consolidation with volume",
        "risk_level": "High",
        "timeframe": "1-2 weeks",
        "rules": [
            {"indicator": "Bollinger", "condition": "upper_break", "weight": 2.5},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 2.0, "weight": 2.5},
            {"indicator": "RSI", "condition": "above", "threshold": 60, "weight": 1.5},
            {"indicator": "ADX", "condition": "above", "threshold": 25, "weight": 1.5},
        ],
    },
    "52-Week High Momentum": {
        "category": "Momentum",
        "description": "Stocks near 52-week highs with strong momentum",
        "risk_level": "High",
        "timeframe": "1-4 weeks",
        "rules": [
            {"indicator": "Price", "condition": "near_52w_high", "threshold": 0.95, "weight": 3.0},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.3, "weight": 1.5},
            {"indicator": "RSI", "condition": "between", "min": 60, "max": 80, "weight": 1.5},
            {"indicator": "MACD", "condition": "bullish", "weight": 1.0},
        ],
    },

    # ──── Mean Reversion (3 strategies) ────
    "Value Bounce": {
        "category": "Mean Reversion",
        "description": "Oversold stocks with reversal potential",
        "risk_level": "Moderate-High",
        "timeframe": "1-3 weeks",
        "rules": [
            {"indicator": "RSI", "condition": "below", "threshold": 40, "weight": 2.0},
            {"indicator": "Bollinger", "condition": "near_lower", "weight": 1.5},
            {"indicator": "MACD", "condition": "turning_up", "weight": 1.5},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.0, "weight": 1.0},
        ],
    },
    "RSI Divergence": {
        "category": "Mean Reversion",
        "description": "Bullish RSI divergence with price making new low",
        "risk_level": "Moderate",
        "timeframe": "1-4 weeks",
        "rules": [
            {"indicator": "RSI", "condition": "bullish_divergence", "weight": 3.0},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.0, "weight": 1.0},
            {"indicator": "Stochastic", "condition": "oversold_cross", "weight": 2.0},
            {"indicator": "MACD", "condition": "turning_up", "weight": 1.5},
        ],
    },
    "Double Bottom": {
        "category": "Mean Reversion",
        "description": "Double bottom pattern with bullish confirmations",
        "risk_level": "Moderate",
        "timeframe": "2-6 weeks",
        "rules": [
            {"indicator": "Pattern", "condition": "double_bottom", "weight": 3.0},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.2, "weight": 1.5},
            {"indicator": "RSI", "condition": "above", "threshold": 40, "weight": 1.0},
            {"indicator": "MACD", "condition": "turning_up", "weight": 1.5},
        ],
    },

    # ──── Volatility (1 strategy) ────
    "Bollinger Squeeze": {
        "category": "Volatility",
        "description": "Narrow Bollinger Bands about to expand",
        "risk_level": "High",
        "timeframe": "1-2 weeks",
        "rules": [
            {"indicator": "Bollinger", "condition": "squeeze", "weight": 3.0},
            {"indicator": "Volume", "condition": "decreasing", "weight": 1.5},
            {"indicator": "ADX", "condition": "below", "threshold": 20, "weight": 1.5},
            {"indicator": "ATR", "condition": "low", "weight": 1.5},
        ],
    },

    # ──── Volume-Based (2 strategies) ────
    "Volume Surge": {
        "category": "Volume",
        "description": "Unusual volume spikes with bullish price action",
        "risk_level": "Moderate-High",
        "timeframe": "1-2 weeks",
        "rules": [
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 2.5, "weight": 3.0},
            {"indicator": "OBV", "condition": "rising", "weight": 2.0},
            {"indicator": "MFI", "condition": "above", "threshold": 50, "weight": 1.5},
            {"indicator": "RSI", "condition": "above", "threshold": 50, "weight": 1.0},
        ],
    },
    "Smart Money": {
        "category": "Volume",
        "description": "Institutional accumulation signals via OBV divergence",
        "risk_level": "Moderate",
        "timeframe": "2-8 weeks",
        "rules": [
            {"indicator": "OBV", "condition": "rising_divergence", "weight": 3.0},
            {"indicator": "MFI", "condition": "above", "threshold": 60, "weight": 2.0},
            {"indicator": "Volume", "condition": "trending_up", "weight": 1.5},
            {"indicator": "ADX", "condition": "above", "threshold": 20, "weight": 1.0},
        ],
    },

    # ──── Multi-Timeframe (1 strategy) ────
    "Triple MACD Alignment": {
        "category": "Multi-Timeframe",
        "description": "MACD bullish on daily, weekly, and monthly timeframes",
        "risk_level": "Low-Moderate",
        "timeframe": "4-12 weeks",
        "rules": [
            {"indicator": "MACD", "condition": "bullish", "weight": 1.0},
            {"indicator": "MACD_Weekly", "condition": "bullish", "weight": 2.0},
            {"indicator": "MACD_Monthly", "condition": "bullish", "weight": 3.0},
            {"indicator": "+DMI", "condition": "above_minus", "weight": 1.5},
            {"indicator": "RSI", "condition": "above", "threshold": 50, "weight": 1.0},
        ],
    },

    # ──── Additional Hybrid Strategies (2 strategies) ────
    "GARP (Growth at Reasonable Price)": {
        "category": "Hybrid",
        "description": "Growth stocks with fair valuation and momentum",
        "risk_level": "Moderate",
        "timeframe": "4-12 weeks",
        "rules": [
            {"indicator": "RSI", "condition": "between", "min": 45, "max": 70, "weight": 1.5},
            {"indicator": "MACD", "condition": "bullish", "weight": 2.0},
            {"indicator": "SMA_Cross", "condition": "golden", "fast": 50, "slow": 200, "weight": 2.5},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.1, "weight": 1.0},
            {"indicator": "ADX", "condition": "above", "threshold": 20, "weight": 1.0},
        ],
    },
    "Contrarian Recovery": {
        "category": "Mean Reversion",
        "description": "Heavily sold-off stocks showing recovery signals",
        "risk_level": "High",
        "timeframe": "2-8 weeks",
        "rules": [
            {"indicator": "RSI", "condition": "below", "threshold": 35, "weight": 2.5},
            {"indicator": "Bollinger", "condition": "near_lower", "weight": 2.0},
            {"indicator": "MACD", "condition": "turning_up", "weight": 2.0},
            {"indicator": "Volume", "condition": "above_avg", "multiplier": 1.5, "weight": 1.5},
            {"indicator": "Stochastic", "condition": "oversold_cross", "weight": 2.0},
        ],
    },
}


# ============================================================================
# ADVANCED STRATEGY ENGINE (Patent-Pending)
# ============================================================================

class AdvancedStrategyEngine:
    """
    Multi-Strategy Committee Screening Engine.

    Patent Innovation: Instead of evaluating stocks against a single strategy,
    this engine evaluates each stock against ALL 18+ strategies simultaneously
    using weighted rule scoring. A stock is flagged only when multiple
    independent strategies agree — the "committee of experts" approach.
    """

    def __init__(self):
        self.strategies = dict(ADVANCED_STRATEGIES)
        self.custom_strategies = {}
        logger.info(f"AdvancedStrategyEngine initialized with {len(self.strategies)} strategies")

    # ── Strategy Catalog ──

    def get_strategy_catalog(self) -> List[Dict[str, Any]]:
        """Return full strategy catalog with metadata."""
        catalog = []
        for name, config in self.strategies.items():
            catalog.append({
                "name": name,
                "category": config.get("category", "Other"),
                "description": config.get("description", ""),
                "risk_level": config.get("risk_level", "Unknown"),
                "timeframe": config.get("timeframe", "Unknown"),
                "num_rules": len(config.get("rules", [])),
            })
        return catalog

    def get_categories(self) -> List[str]:
        """Get unique strategy categories."""
        return sorted({s.get("category", "Other") for s in self.strategies.values()})

    def get_strategies_by_category(self, category: Optional[str] = None) -> Dict:
        """Get strategies filtered by category."""
        if category is None:
            return self.strategies
        return {k: v for k, v in self.strategies.items() if v.get("category") == category}

    # ── Single Strategy Evaluation ──

    def evaluate_strategy(self, df: pd.DataFrame, strategy_name: str) -> Optional[Dict]:
        """Evaluate a single strategy on stock data."""
        if strategy_name not in self.strategies:
            return None

        strategy = self.strategies[strategy_name]
        df = compute_full_indicators(df.copy())

        if df is None or len(df) < 50:
            return None

        total_score = 0
        total_weight = 0
        conditions_met = []
        conditions_failed = []

        for rule in strategy["rules"]:
            weight = rule.get("weight", 1.0)
            met = self._evaluate_rule(df, rule)

            if met:
                total_score += weight
                conditions_met.append(f"{rule['indicator']}:{rule['condition']}")
            else:
                conditions_failed.append(f"{rule['indicator']}:{rule['condition']}")
            total_weight += weight

        confidence = (total_score / total_weight * 100) if total_weight > 0 else 0

        return {
            "strategy": strategy_name,
            "category": strategy.get("category", "Other"),
            "risk_level": strategy.get("risk_level", "Unknown"),
            "timeframe": strategy.get("timeframe", "Unknown"),
            "confidence": round(confidence, 1),
            "conditions_met": len(conditions_met),
            "total_conditions": len(strategy["rules"]),
            "met_details": conditions_met,
            "failed_details": conditions_failed,
            "score": total_score,
            "max_score": total_weight,
        }

    # ── Multi-Strategy Evaluation (Patent-Pending) ──

    def evaluate_multiple_strategies(self, df: pd.DataFrame,
                                      strategy_names: Optional[List[str]] = None) -> List[Dict]:
        """Evaluate multiple strategies on the same stock data using parallel execution."""
        if strategy_names is None:
            strategy_names = list(self.strategies.keys())

        df_with_indicators = compute_full_indicators(df.copy())
        if df_with_indicators is None or len(df_with_indicators) < 50:
            return []

        def eval_strategy(name):
            if name not in self.strategies:
                return None
            strategy = self.strategies[name]
            total_score = 0
            total_weight = 0
            conditions_met = []

            for rule in strategy["rules"]:
                weight = rule.get("weight", 1.0)
                met = self._evaluate_rule(df_with_indicators, rule)

                if met:
                    total_score += weight
                    conditions_met.append(f"{rule['indicator']}:{rule['condition']}")
                total_weight += weight

            confidence = (total_score / total_weight * 100) if total_weight > 0 else 0

            return {
                "strategy": name,
                "category": strategy.get("category", "Other"),
                "description": strategy.get("description", ""),
                "confidence": round(confidence, 1),
                "conditions_met": len(conditions_met),
                "total_conditions": len(strategy["rules"]),
                "rules_passing": len(conditions_met),
                "rules_total": len(strategy["rules"]),
                "score": round(total_score, 2),
                "max_score": round(total_weight, 2),
                "risk_level": strategy.get("risk_level", "Unknown"),
                "timeframe": strategy.get("timeframe", "Unknown"),
            }

        results = []
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(10, max(1, len(strategy_names)))) as executor:
            futures = [executor.submit(eval_strategy, name) for name in strategy_names]
            for future in futures:
                res = future.result()
                if res:
                    results.append(res)

        return sorted(results, key=lambda x: x["confidence"], reverse=True)

    def multi_strategy_screen(self, df: pd.DataFrame,
                               min_strategies_passing: int = 2,
                               min_confidence: float = 60.0) -> Dict:
        """
        Patent-Pending: Committee-of-Experts screening.

        Screen a stock against ALL strategies and determine if enough
        independent strategies agree on a bullish signal.
        """
        all_results = self.evaluate_multiple_strategies(df)
        if not all_results:
            return {
                "strategies_passing": 0, "strategies_evaluated": 0,
                "passing_strategies": [], "avg_confidence": 0,
                "max_confidence": 0, "best_strategy": "None",
                "all_results": [], "qualifies": False,
            }

        passing = [r for r in all_results if r["confidence"] >= min_confidence]
        avg_confidence = float(np.mean([r["confidence"] for r in passing])) if passing else 0
        max_confidence = max([r["confidence"] for r in all_results])
        best_strategy = all_results[0]["strategy"]

        return {
            "strategies_passing": len(passing),
            "strategies_evaluated": len(all_results),
            "passing_strategies": [r["strategy"] for r in passing],
            "avg_confidence": round(avg_confidence, 1),
            "max_confidence": round(max_confidence, 1),
            "best_strategy": best_strategy,
            "all_results": all_results,
            "qualifies": len(passing) >= min_strategies_passing,
        }

    # ── Custom Strategy Support ──

    def add_custom_strategy(self, name: str, description: str, category: str,
                             risk_level: str, timeframe: str, rules: List[Dict]):
        """Add a user-defined strategy at runtime."""
        self.strategies[name] = {
            "category": category,
            "description": description,
            "risk_level": risk_level,
            "timeframe": timeframe,
            "rules": rules,
        }
        self.custom_strategies[name] = self.strategies[name]
        logger.info(f"Custom strategy '{name}' added with {len(rules)} rules")

    def remove_custom_strategy(self, name: str) -> bool:
        """Remove a custom strategy."""
        if name in self.custom_strategies:
            del self.custom_strategies[name]
            del self.strategies[name]
            return True
        return False

    # ══════════════════════════════════════════════════════════
    # RULE EVALUATION ENGINE (Patent-Pending)
    # ══════════════════════════════════════════════════════════

    def _evaluate_rule(self, df: pd.DataFrame, rule: Dict) -> bool:
        """Evaluate a single technical rule against price data."""
        try:
            indicator = rule["indicator"]
            condition = rule["condition"]
            latest = df.iloc[-1]

            if indicator == "MACD":
                return self._eval_macd(df, condition)
            elif indicator == "MACD_Weekly":
                return self._eval_macd_resampled(df, condition, "W")
            elif indicator == "MACD_Monthly":
                return self._eval_macd_resampled(df, condition, "ME")
            elif indicator == "RSI":
                return self._eval_rsi(df, rule)
            elif indicator == "ADX":
                return self._eval_threshold(latest.get("ADX", 0), rule)
            elif indicator == "+DMI":
                if condition == "above_minus":
                    return latest.get("+DMI", 0) > latest.get("-DMI", 0)
                return False
            elif indicator == "Bollinger":
                return self._eval_bollinger(df, condition)
            elif indicator == "Volume":
                return self._eval_volume(df, rule)
            elif indicator in ("SMA_Cross", "EMA_Cross"):
                return self._eval_ma_cross(df, rule)
            elif indicator == "Stochastic":
                return self._eval_stochastic(df, condition)
            elif indicator == "ROC":
                return self._eval_threshold(latest.get("ROC_12", 0), rule)
            elif indicator == "OBV":
                return self._eval_obv(df, condition)
            elif indicator == "MFI":
                return self._eval_threshold(latest.get("MFI", 0), rule)
            elif indicator == "ATR":
                return self._eval_atr(df, condition)
            elif indicator == "Ichimoku":
                return self._eval_ichimoku(df, condition)
            elif indicator == "Supertrend":
                return self._eval_supertrend(df, condition)
            elif indicator == "Price":
                return self._eval_price(df, rule)
            elif indicator == "Pattern":
                return self._eval_pattern(df, condition)
            return False
        except Exception:
            return False

    # ── Individual Rule Evaluators ──

    def _eval_macd(self, df, condition):
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        if condition == "bullish_cross":
            return (latest.get("MACD", 0) > latest.get("MACD_Signal", 0) and
                    prev.get("MACD", 0) <= prev.get("MACD_Signal", 0))
        elif condition == "bullish":
            return latest.get("MACD", 0) > 0
        elif condition == "turning_up":
            return latest.get("MACD", 0) > prev.get("MACD", 0)
        return False

    def _eval_macd_resampled(self, df, condition, freq):
        try:
            resampled = df.resample(freq).agg({
                "Open": "first", "High": "max", "Low": "min",
                "Close": "last", "Volume": "sum"
            }).dropna()
            if len(resampled) < 30:
                return False
            macd = ta.trend.MACD(resampled["Close"])
            m_val = macd.macd().iloc[-1]
            return m_val > 0 if condition == "bullish" else False
        except Exception:
            return False

    def _eval_rsi(self, df, rule):
        latest = df.iloc[-1]
        rsi = latest.get("RSI", 50)
        condition = rule["condition"]
        if condition == "above":
            return rsi > rule.get("threshold", 50)
        elif condition == "below":
            return rsi < rule.get("threshold", 50)
        elif condition == "between":
            return rule.get("min", 0) < rsi < rule.get("max", 100)
        elif condition == "bullish_divergence":
            return self._detect_rsi_divergence(df)
        return False

    def _detect_rsi_divergence(self, df, lookback=20):
        """Detect bullish RSI divergence (price lower low, RSI higher low)."""
        try:
            prices = df["Close"].iloc[-lookback:]
            rsi = df["RSI"].iloc[-lookback:]
            mid = lookback // 2
            price_low1 = prices.iloc[:mid].min()
            price_low2 = prices.iloc[mid:].min()
            rsi_low1 = rsi.iloc[:mid].min()
            rsi_low2 = rsi.iloc[mid:].min()
            return price_low2 < price_low1 and rsi_low2 > rsi_low1
        except Exception:
            return False

    def _eval_threshold(self, value, rule):
        condition = rule.get("condition", "above")
        threshold = rule.get("threshold", 0)
        if condition == "above":
            return value > threshold
        elif condition == "below":
            return value < threshold
        return False

    def _eval_bollinger(self, df, condition):
        latest = df.iloc[-1]
        if condition == "near_lower":
            return latest.get("BB_pct", 0.5) < 0.2
        elif condition == "upper_break":
            return latest.get("Close", 0) > latest.get("BB_upper", float("inf"))
        elif condition == "squeeze":
            if "BB_width" not in df.columns:
                return False
            bb_width = df["BB_width"].iloc[-5:].mean()
            bb_width_avg = df["BB_width"].iloc[-60:].mean()
            return bb_width < bb_width_avg * 0.5
        return False

    def _eval_volume(self, df, rule):
        latest = df.iloc[-1]
        condition = rule["condition"]
        if condition == "above_avg":
            multiplier = rule.get("multiplier", 1.0)
            vol_ma = latest.get("Vol_MA", 1)
            return latest.get("Volume", 0) > vol_ma * multiplier
        elif condition == "trending_up":
            vol_5 = df["Volume"].iloc[-5:].mean()
            vol_20 = df["Volume"].iloc[-20:].mean()
            return vol_5 > vol_20 * 1.1
        elif condition == "decreasing":
            vol_5 = df["Volume"].iloc[-5:].mean()
            vol_20 = df["Volume"].iloc[-20:].mean()
            return vol_5 < vol_20 * 0.8
        return False

    def _eval_ma_cross(self, df, rule):
        condition = rule.get("condition", "golden")
        fast = rule.get("fast", 20)
        slow = rule.get("slow", 50)
        indicator = rule["indicator"]

        prefix = "SMA" if indicator == "SMA_Cross" else "EMA"
        fast_col = f"{prefix}_{fast}" if f"{prefix}_{fast}" in df.columns else None
        slow_col = f"{prefix}_{slow}" if f"{prefix}_{slow}" in df.columns else None

        if fast_col and slow_col:
            if condition in ("golden", "bullish"):
                return (df[fast_col].iloc[-1] > df[slow_col].iloc[-1] and
                        df[fast_col].iloc[-2] <= df[slow_col].iloc[-2])
        else:
            close = df["Close"]
            if indicator == "SMA_Cross":
                fast_ma = close.rolling(fast).mean()
                slow_ma = close.rolling(slow).mean()
            else:
                fast_ma = close.ewm(span=fast).mean()
                slow_ma = close.ewm(span=slow).mean()
            if condition in ("golden", "bullish"):
                return fast_ma.iloc[-1] > slow_ma.iloc[-1]
        return False

    def _eval_stochastic(self, df, condition):
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        if condition == "oversold_cross":
            return (latest.get("Stoch_K", 50) > latest.get("Stoch_D", 50) and
                    prev.get("Stoch_K", 50) <= prev.get("Stoch_D", 50) and
                    latest.get("Stoch_K", 50) < 30)
        return False

    def _eval_obv(self, df, condition):
        if "OBV" not in df.columns:
            return False
        if condition == "rising":
            return df["OBV"].iloc[-1] > df["OBV"].iloc[-5]
        elif condition == "rising_divergence":
            obv_rising = df["OBV"].iloc[-1] > df["OBV"].iloc[-10]
            price_flat = abs(df["Close"].iloc[-1] / df["Close"].iloc[-10] - 1) < 0.02
            return obv_rising and price_flat
        return False

    def _eval_atr(self, df, condition):
        if "ATR_pct" not in df.columns:
            return False
        if condition == "low":
            current_atr = df["ATR_pct"].iloc[-1]
            avg_atr = df["ATR_pct"].iloc[-60:].mean()
            return current_atr < avg_atr * 0.7
        return False

    def _eval_ichimoku(self, df, condition):
        latest = df.iloc[-1]
        if condition == "above_cloud":
            cloud_top = max(latest.get("Ichimoku_A", 0), latest.get("Ichimoku_B", 0))
            return latest.get("Close", 0) > cloud_top
        elif condition == "bullish_tk_cross":
            return latest.get("Ichimoku_Conv", 0) > latest.get("Ichimoku_Base", 0)
        return False

    def _eval_supertrend(self, df, condition):
        latest = df.iloc[-1]
        if condition == "bullish":
            # Use the proper Supertrend direction indicator
            st_dir = latest.get("Supertrend_Dir", None)
            if st_dir is not None and not pd.isna(st_dir):
                return float(st_dir) == 1.0
            # Fallback: Close must be above Supertrend value AND recently flipped
            st_val = latest.get("Supertrend", None)
            if st_val is not None and not pd.isna(st_val):
                return latest.get("Close", 0) > st_val
            return False
        elif condition == "bearish":
            st_dir = latest.get("Supertrend_Dir", None)
            if st_dir is not None and not pd.isna(st_dir):
                return float(st_dir) == -1.0
            return False
        return False

    def _eval_price(self, df, rule):
        condition = rule.get("condition", "")
        if condition == "near_52w_high":
            threshold = rule.get("threshold", 0.95)
            high_252 = df["High"].iloc[-252:].max() if len(df) >= 252 else df["High"].max()
            return df["Close"].iloc[-1] >= high_252 * threshold
        return False

    def _eval_pattern(self, df, condition):
        if condition == "double_bottom":
            return self._detect_double_bottom(df)
        return False

    def _detect_double_bottom(self, df, lookback=40):
        """Simple double bottom detection."""
        try:
            lows = df["Low"].iloc[-lookback:]
            mid = lookback // 2
            low1 = lows.iloc[:mid].min()
            low2 = lows.iloc[mid:].min()
            current = df["Close"].iloc[-1]
            low1_idx = lows.iloc[:mid].idxmin()
            low2_idx = lows.iloc[mid:].idxmin()
            mid_high = df["High"].loc[low1_idx:low2_idx].max()
            tolerance = 0.03
            return (abs(low1 - low2) / low1 < tolerance and current > mid_high * 0.98)
        except Exception:
            return False


# ============================================================================
# SECTOR ROTATION DETECTOR (Patent-Pending)
# ============================================================================

class SectorRotationDetector:
    """
    Detect sector rotation patterns across Indian & global markets.

    Classifies each sector into rotation phases:
    Strong Uptrend → Topping Out → Downtrend → Recovery → Early Uptrend
    """

    SECTOR_SYMBOLS = {
        "NSE": {
            "IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"],
            "Banking": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK"],
            "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB"],
            "Auto": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO"],
            "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA"],
            "Metals": ["TATASTEEL", "JSWSTEEL", "HINDALCO"],
            "Energy": ["RELIANCE", "ONGC", "NTPC", "POWERGRID"],
            "Realty": ["DLF", "GODREJPROP", "OBEROIRLTY"],
        },
        "NYSE": {
            "Technology": ["AAPL", "MSFT", "NVDA"],
            "Healthcare": ["JNJ", "UNH", "PFE"],
            "Financials": ["JPM", "BAC", "GS"],
            "Energy": ["XOM", "CVX"],
            "Consumer": ["WMT", "PG", "KO"],
        },
    }

    def analyze_rotation(self, exchange: str = "NSE",
                          periods: Optional[Dict[str, str]] = None) -> Dict:
        """Analyze sector rotation over multiple periods."""
        if periods is None:
            periods = {"1W": "5d", "1M": "1mo", "3M": "3mo", "6M": "6mo"}

        sectors = self.SECTOR_SYMBOLS.get(exchange, {})
        rotation_data = {}

        suffix = {"NSE": ".NS", "BSE": ".BO", "NYSE": "", "NASDAQ": "", "LSE": ".L"}
        sfx = suffix.get(exchange, "")

        for sector, symbols in sectors.items():
            sector_returns = {}
            for period_label, period_val in periods.items():
                returns = []
                for symbol in symbols:
                    try:
                        df = yf.download(f"{symbol}{sfx}", period=period_val,
                                          progress=False, auto_adjust=True)
                        if df is not None and len(df) > 1:
                            close = df["Close"]
                            if isinstance(close, pd.DataFrame):
                                close = close.iloc[:, 0]
                            ret = (close.iloc[-1] / close.iloc[0] - 1) * 100
                            returns.append(float(ret))
                    except Exception:
                        pass
                sector_returns[period_label] = float(np.mean(returns)) if returns else 0.0

            rotation_data[sector] = sector_returns

        # Classify rotation phases
        analysis = {}
        for sector, returns in rotation_data.items():
            short_term = returns.get("1W", 0)
            medium_term = returns.get("1M", 0)
            long_term = returns.get("3M", 0)

            if short_term > 0 and medium_term > 0 and long_term > 0:
                phase = "Strong Uptrend"
            elif short_term > 0 and medium_term > 0:
                phase = "Early Uptrend"
            elif short_term > 0 and medium_term < 0:
                phase = "Recovery"
            elif short_term < 0 and medium_term > 0:
                phase = "Topping Out"
            elif short_term < 0 and medium_term < 0:
                phase = "Downtrend"
            else:
                phase = "Consolidation"

            analysis[sector] = {
                "returns": returns,
                "phase": phase,
                "momentum_score": round(short_term * 0.5 + medium_term * 0.3 + long_term * 0.2, 2),
            }

        return analysis


# ============================================================================
# MODULE-LEVEL SINGLETON
# ============================================================================

_strategy_engine: Optional[AdvancedStrategyEngine] = None

def get_strategy_engine() -> AdvancedStrategyEngine:
    """Get or create the singleton AdvancedStrategyEngine."""
    global _strategy_engine
    if _strategy_engine is None:
        _strategy_engine = AdvancedStrategyEngine()
    return _strategy_engine
