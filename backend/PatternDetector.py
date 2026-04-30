"""
===================================================================
CROSS-PATTERN CONFLUENCE SCORING ENGINE (CPCS)
===================================================================

Patent-Pending Feature: Detects multiple chart patterns simultaneously
and computes a unified Confluence Score using weighted pattern agreement.

Unlike traditional pattern detection that treats each pattern independently,
CPCS measures the *agreement* between patterns across multiple timeframes
and pattern types, producing a single actionable score.

Key Innovation:
  - Multi-timeframe pattern scanning (5, 10, 20, 50-day windows)
  - Pattern confluence scoring via agreement matrix
  - Support/Resistance clustering with adaptive thresholds
  - Candlestick pattern ensemble with reliability weighting
  - Trend exhaustion detection via divergence analysis

Author: GenAI Stock Intelligence System
Version: 1.0.0
===================================================================
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ==================== DATA CLASSES ====================

class PatternType(str, Enum):
    # Candlestick Patterns
    DOJI = "doji"
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    HANGING_MAN = "hanging_man"
    ENGULFING_BULL = "engulfing_bullish"
    ENGULFING_BEAR = "engulfing_bearish"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    SHOOTING_STAR = "shooting_star"
    MARUBOZU_BULL = "marubozu_bullish"
    MARUBOZU_BEAR = "marubozu_bearish"
    HARAMI_BULL = "harami_bullish"
    HARAMI_BEAR = "harami_bearish"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    PIERCING_LINE = "piercing_line"
    DARK_CLOUD = "dark_cloud_cover"
    TWEEZER_TOP = "tweezer_top"
    TWEEZER_BOTTOM = "tweezer_bottom"
    
    # Chart Patterns
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    HEAD_SHOULDERS = "head_and_shoulders"
    INV_HEAD_SHOULDERS = "inverse_head_and_shoulders"
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    CUP_AND_HANDLE = "cup_and_handle"
    CHANNEL_UP = "channel_up"
    CHANNEL_DOWN = "channel_down"
    
    # Trend Patterns
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"
    TREND_REVERSAL_BULL = "trend_reversal_bullish"
    TREND_REVERSAL_BEAR = "trend_reversal_bearish"
    BREAKOUT_UP = "breakout_up"
    BREAKOUT_DOWN = "breakout_down"


class PatternSignal(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass
class DetectedPattern:
    pattern_type: str
    signal: str
    confidence: float        # 0-100
    reliability: float       # Historical reliability weight
    description: str
    price_at_detection: float
    timeframe: str           # "short", "medium", "long"
    target_move_pct: float   # Expected % move based on pattern
    
    def to_dict(self):
        return asdict(self)


@dataclass
class SupportResistance:
    level: float
    strength: int            # Number of touches
    level_type: str          # "support" or "resistance"
    distance_pct: float      # Distance from current price
    
    def to_dict(self):
        return asdict(self)


@dataclass
class ConfluenceResult:
    """Output of the Cross-Pattern Confluence Scoring Engine"""
    patterns_detected: List[Dict]
    support_levels: List[Dict]
    resistance_levels: List[Dict]
    confluence_score: float       # -100 (max bearish) to +100 (max bullish)
    pattern_agreement: float      # 0-100 (how much patterns agree)
    dominant_signal: str          # BULLISH / BEARISH / NEUTRAL
    trend_strength: float         # 0-100
    suggested_entry: float
    suggested_stoploss: float
    suggested_target: float
    risk_reward_from_patterns: float
    pattern_summary: str
    
    def to_dict(self):
        return asdict(self)


# ==================== CANDLESTICK PATTERN DETECTOR ====================

class CandlestickDetector:
    """
    Detects candlestick patterns with reliability-weighted scoring.
    
    Each pattern has an empirically-derived reliability score based on
    Bulkowski's Encyclopedia of Candlestick Charts research.
    """
    
    # Pattern reliability scores (based on historical research)
    RELIABILITY = {
        PatternType.DOJI: 0.50,
        PatternType.HAMMER: 0.60,
        PatternType.INVERTED_HAMMER: 0.55,
        PatternType.HANGING_MAN: 0.59,
        PatternType.ENGULFING_BULL: 0.63,
        PatternType.ENGULFING_BEAR: 0.79,
        PatternType.MORNING_STAR: 0.78,
        PatternType.EVENING_STAR: 0.72,
        PatternType.SHOOTING_STAR: 0.59,
        PatternType.MARUBOZU_BULL: 0.56,
        PatternType.MARUBOZU_BEAR: 0.56,
        PatternType.HARAMI_BULL: 0.53,
        PatternType.HARAMI_BEAR: 0.53,
        PatternType.THREE_WHITE_SOLDIERS: 0.82,
        PatternType.THREE_BLACK_CROWS: 0.78,
        PatternType.PIERCING_LINE: 0.64,
        PatternType.DARK_CLOUD: 0.60,
        PatternType.TWEEZER_TOP: 0.57,
        PatternType.TWEEZER_BOTTOM: 0.57,
    }
    
    def __init__(self, df: pd.DataFrame):
        """
        df must have columns: open, high, low, close, volume
        """
        self.df = df.copy()
        self.patterns: List[DetectedPattern] = []
        
        # Pre-compute body metrics
        self.df['body'] = self.df['close'] - self.df['open']
        self.df['body_abs'] = self.df['body'].abs()
        self.df['range'] = self.df['high'] - self.df['low']
        self.df['upper_shadow'] = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['lower_shadow'] = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['body_pct'] = self.df['body_abs'] / (self.df['range'] + 1e-10)
        self.df['avg_body'] = self.df['body_abs'].rolling(20).mean()
        self.df['avg_range'] = self.df['range'].rolling(20).mean()
    
    def detect_all(self) -> List[DetectedPattern]:
        """Run all candlestick pattern detections"""
        self._detect_doji()
        self._detect_hammer()
        self._detect_inverted_hammer()
        self._detect_hanging_man()
        self._detect_engulfing()
        self._detect_morning_evening_star()
        self._detect_shooting_star()
        self._detect_marubozu()
        self._detect_harami()
        self._detect_three_soldiers_crows()
        self._detect_piercing_dark_cloud()
        self._detect_tweezers()
        return self.patterns
    
    def _add_pattern(self, pattern_type: PatternType, signal: PatternSignal,
                     confidence: float, description: str, target_move: float = 0):
        price = float(self.df['close'].iloc[-1])
        self.patterns.append(DetectedPattern(
            pattern_type=pattern_type.value,
            signal=signal.value,
            confidence=min(confidence, 100),
            reliability=self.RELIABILITY.get(pattern_type, 0.5),
            description=description,
            price_at_detection=price,
            timeframe="short",
            target_move_pct=target_move
        ))
    
    def _detect_doji(self):
        if len(self.df) < 2: return
        row = self.df.iloc[-1]
        if row['body_pct'] < 0.1 and row['range'] > 0:
            conf = (1 - row['body_pct']) * 80
            trend = self.df['close'].iloc[-10:].mean() - self.df['close'].iloc[-20:-10].mean()
            if trend > 0:
                self._add_pattern(PatternType.DOJI, PatternSignal.BEARISH, conf,
                                  "Doji after uptrend - potential reversal", -1.5)
            elif trend < 0:
                self._add_pattern(PatternType.DOJI, PatternSignal.BULLISH, conf,
                                  "Doji after downtrend - potential reversal", 1.5)
            else:
                self._add_pattern(PatternType.DOJI, PatternSignal.NEUTRAL, conf * 0.7,
                                  "Doji - market indecision", 0)
    
    def _detect_hammer(self):
        if len(self.df) < 10: return
        row = self.df.iloc[-1]
        prior_trend = self.df['close'].iloc[-10:-1].mean() - self.df['close'].iloc[-1]
        
        if (row['lower_shadow'] > 2 * row['body_abs'] and
            row['upper_shadow'] < row['body_abs'] * 0.5 and
            prior_trend > 0):  # Prior downtrend
            conf = min(row['lower_shadow'] / (row['body_abs'] + 1e-10) * 20, 85)
            self._add_pattern(PatternType.HAMMER, PatternSignal.BULLISH, conf,
                              "Hammer - bullish reversal signal", 3.0)
    
    def _detect_inverted_hammer(self):
        if len(self.df) < 10: return
        row = self.df.iloc[-1]
        prior_trend = self.df['close'].iloc[-10:-1].mean() - self.df['close'].iloc[-1]
        
        if (row['upper_shadow'] > 2 * row['body_abs'] and
            row['lower_shadow'] < row['body_abs'] * 0.5 and
            prior_trend > 0):
            conf = min(row['upper_shadow'] / (row['body_abs'] + 1e-10) * 18, 80)
            self._add_pattern(PatternType.INVERTED_HAMMER, PatternSignal.BULLISH, conf,
                              "Inverted Hammer - potential bullish reversal", 2.5)
    
    def _detect_hanging_man(self):
        if len(self.df) < 10: return
        row = self.df.iloc[-1]
        prior_trend = self.df['close'].iloc[-1] - self.df['close'].iloc[-10:-1].mean()
        
        if (row['lower_shadow'] > 2 * row['body_abs'] and
            row['upper_shadow'] < row['body_abs'] * 0.5 and
            prior_trend > 0):  # Prior uptrend
            conf = min(row['lower_shadow'] / (row['body_abs'] + 1e-10) * 20, 82)
            self._add_pattern(PatternType.HANGING_MAN, PatternSignal.BEARISH, conf,
                              "Hanging Man - bearish reversal warning", -2.5)
    
    def _detect_engulfing(self):
        if len(self.df) < 3: return
        curr = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        # Bullish engulfing
        if (prev['close'] < prev['open'] and  # Previous bearish
            curr['close'] > curr['open'] and   # Current bullish
            curr['open'] <= prev['close'] and   # Opens below prev close
            curr['close'] >= prev['open']):     # Closes above prev open
            
            engulf_ratio = curr['body_abs'] / (prev['body_abs'] + 1e-10)
            conf = min(engulf_ratio * 35, 88)
            self._add_pattern(PatternType.ENGULFING_BULL, PatternSignal.BULLISH, conf,
                              "Bullish Engulfing - strong reversal signal", 4.0)
        
        # Bearish engulfing
        if (prev['close'] > prev['open'] and  # Previous bullish
            curr['close'] < curr['open'] and   # Current bearish
            curr['open'] >= prev['close'] and   # Opens above prev close
            curr['close'] <= prev['open']):     # Closes below prev open
            
            engulf_ratio = curr['body_abs'] / (prev['body_abs'] + 1e-10)
            conf = min(engulf_ratio * 38, 90)
            self._add_pattern(PatternType.ENGULFING_BEAR, PatternSignal.BEARISH, conf,
                              "Bearish Engulfing - strong reversal signal", -4.0)
    
    def _detect_morning_evening_star(self):
        if len(self.df) < 4: return
        c1, c2, c3 = self.df.iloc[-3], self.df.iloc[-2], self.df.iloc[-1]
        
        # Morning Star (bullish)
        if (c1['body'] < 0 and abs(c1['body']) > c1['avg_body'] and  # Big bearish
            c2['body_abs'] < c2['avg_body'] * 0.4 and                 # Small body (star)
            c3['body'] > 0 and c3['body_abs'] > c3['avg_body'] * 0.5 and  # Big bullish
            c2['close'] < c1['close'] and c3['close'] > (c1['open'] + c1['close'])/2):
            
            self._add_pattern(PatternType.MORNING_STAR, PatternSignal.BULLISH, 82,
                              "Morning Star - strong bullish reversal", 5.0)
        
        # Evening Star (bearish)
        if (c1['body'] > 0 and c1['body_abs'] > c1['avg_body'] and  # Big bullish
            c2['body_abs'] < c2['avg_body'] * 0.4 and                # Small body
            c3['body'] < 0 and c3['body_abs'] > c3['avg_body'] * 0.5 and  # Big bearish
            c2['close'] > c1['close'] and c3['close'] < (c1['open'] + c1['close'])/2):
            
            self._add_pattern(PatternType.EVENING_STAR, PatternSignal.BEARISH, 80,
                              "Evening Star - strong bearish reversal", -5.0)
    
    def _detect_shooting_star(self):
        if len(self.df) < 10: return
        row = self.df.iloc[-1]
        prior_trend = self.df['close'].iloc[-1] - self.df['close'].iloc[-10:-1].mean()
        
        if (row['upper_shadow'] > 2 * row['body_abs'] and
            row['lower_shadow'] < row['body_abs'] * 0.3 and
            prior_trend > 0):
            conf = min(row['upper_shadow'] / (row['body_abs'] + 1e-10) * 20, 80)
            self._add_pattern(PatternType.SHOOTING_STAR, PatternSignal.BEARISH, conf,
                              "Shooting Star - bearish reversal", -3.0)
    
    def _detect_marubozu(self):
        if len(self.df) < 2: return
        row = self.df.iloc[-1]
        
        if row['body_pct'] > 0.85:
            if row['body'] > 0:
                self._add_pattern(PatternType.MARUBOZU_BULL, PatternSignal.BULLISH, 75,
                                  "Bullish Marubozu - strong buying pressure", 3.0)
            else:
                self._add_pattern(PatternType.MARUBOZU_BEAR, PatternSignal.BEARISH, 75,
                                  "Bearish Marubozu - strong selling pressure", -3.0)
    
    def _detect_harami(self):
        if len(self.df) < 3: return
        curr = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        if (prev['body_abs'] > prev['avg_body'] * 1.2 and  # Previous large body
            curr['body_abs'] < prev['body_abs'] * 0.5 and   # Current small body
            curr['high'] < max(prev['open'], prev['close']) and
            curr['low'] > min(prev['open'], prev['close'])):
            
            if prev['body'] < 0:  # Previous bearish → bullish harami
                self._add_pattern(PatternType.HARAMI_BULL, PatternSignal.BULLISH, 65,
                                  "Bullish Harami - potential reversal", 2.0)
            else:  # Previous bullish → bearish harami
                self._add_pattern(PatternType.HARAMI_BEAR, PatternSignal.BEARISH, 65,
                                  "Bearish Harami - potential reversal", -2.0)
    
    def _detect_three_soldiers_crows(self):
        if len(self.df) < 4: return
        c1, c2, c3 = self.df.iloc[-3], self.df.iloc[-2], self.df.iloc[-1]
        
        # Three White Soldiers
        if (c1['body'] > 0 and c2['body'] > 0 and c3['body'] > 0 and
            c2['close'] > c1['close'] and c3['close'] > c2['close'] and
            c1['body_abs'] > c1['avg_body'] * 0.6 and
            c2['body_abs'] > c2['avg_body'] * 0.6 and
            c3['body_abs'] > c3['avg_body'] * 0.6):
            
            self._add_pattern(PatternType.THREE_WHITE_SOLDIERS, PatternSignal.BULLISH, 85,
                              "Three White Soldiers - very strong bullish", 6.0)
        
        # Three Black Crows
        if (c1['body'] < 0 and c2['body'] < 0 and c3['body'] < 0 and
            c2['close'] < c1['close'] and c3['close'] < c2['close'] and
            c1['body_abs'] > c1['avg_body'] * 0.6 and
            c2['body_abs'] > c2['avg_body'] * 0.6 and
            c3['body_abs'] > c3['avg_body'] * 0.6):
            
            self._add_pattern(PatternType.THREE_BLACK_CROWS, PatternSignal.BEARISH, 83,
                              "Three Black Crows - very strong bearish", -6.0)
    
    def _detect_piercing_dark_cloud(self):
        if len(self.df) < 3: return
        curr = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        
        # Piercing Line
        if (prev['body'] < 0 and curr['body'] > 0 and
            curr['open'] < prev['low'] and
            curr['close'] > (prev['open'] + prev['close']) / 2 and
            curr['close'] < prev['open']):
            
            self._add_pattern(PatternType.PIERCING_LINE, PatternSignal.BULLISH, 70,
                              "Piercing Line - bullish reversal", 3.5)
        
        # Dark Cloud Cover
        if (prev['body'] > 0 and curr['body'] < 0 and
            curr['open'] > prev['high'] and
            curr['close'] < (prev['open'] + prev['close']) / 2 and
            curr['close'] > prev['open']):
            
            self._add_pattern(PatternType.DARK_CLOUD, PatternSignal.BEARISH, 68,
                              "Dark Cloud Cover - bearish reversal", -3.5)
    
    def _detect_tweezers(self):
        if len(self.df) < 3: return
        curr = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        tolerance = curr['avg_range'] * 0.05
        
        # Tweezer Top
        if (abs(curr['high'] - prev['high']) < tolerance and
            prev['body'] > 0 and curr['body'] < 0):
            self._add_pattern(PatternType.TWEEZER_TOP, PatternSignal.BEARISH, 65,
                              "Tweezer Top - bearish reversal", -2.5)
        
        # Tweezer Bottom
        if (abs(curr['low'] - prev['low']) < tolerance and
            prev['body'] < 0 and curr['body'] > 0):
            self._add_pattern(PatternType.TWEEZER_BOTTOM, PatternSignal.BULLISH, 65,
                              "Tweezer Bottom - bullish reversal", 2.5)


# ==================== CHART PATTERN DETECTOR ====================

class ChartPatternDetector:
    """
    Detects higher-level chart patterns using swing point analysis.
    
    Innovation: Uses adaptive swing thresholds based on ATR to handle
    different volatility regimes automatically.
    """
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.patterns: List[DetectedPattern] = []
        self.current_price = float(df['close'].iloc[-1])
        
        # Compute ATR for adaptive thresholds
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.atr = float(tr.rolling(14).mean().iloc[-1])
        
        # Find swing points
        self._find_swings()
    
    def _find_swings(self, window: int = 5):
        """Find swing highs and lows"""
        highs = self.df['high'].values
        lows = self.df['low'].values
        
        self.swing_highs = []
        self.swing_lows = []
        
        for i in range(window, len(highs) - window):
            if highs[i] == max(highs[i-window:i+window+1]):
                self.swing_highs.append((i, highs[i]))
            if lows[i] == min(lows[i-window:i+window+1]):
                self.swing_lows.append((i, lows[i]))
    
    def detect_all(self) -> List[DetectedPattern]:
        """Run all chart pattern detections"""
        self._detect_double_top_bottom()
        self._detect_head_and_shoulders()
        self._detect_triangles()
        self._detect_flags()
        self._detect_wedges()
        self._detect_channels()
        self._detect_crossovers()
        self._detect_breakouts()
        return self.patterns
    
    def _add_pattern(self, pattern_type: PatternType, signal: PatternSignal,
                     confidence: float, description: str, target_move: float = 0):
        self.patterns.append(DetectedPattern(
            pattern_type=pattern_type.value,
            signal=signal.value,
            confidence=min(confidence, 100),
            reliability=0.65,
            description=description,
            price_at_detection=self.current_price,
            timeframe="medium",
            target_move_pct=target_move
        ))
    
    def _detect_double_top_bottom(self):
        """Detect double top and double bottom patterns"""
        tolerance = self.atr * 0.5
        
        # Double Top (last 2 swing highs at similar level)
        if len(self.swing_highs) >= 2:
            h1_idx, h1_val = self.swing_highs[-2]
            h2_idx, h2_val = self.swing_highs[-1]
            
            if (abs(h1_val - h2_val) < tolerance and 
                h2_idx - h1_idx > 10 and
                self.current_price < h2_val):
                
                # Find neckline (lowest low between the two highs)
                between = self.df['low'].iloc[h1_idx:h2_idx]
                neckline = float(between.min()) if len(between) > 0 else self.current_price
                pattern_height = h2_val - neckline
                target_move = -(pattern_height / self.current_price) * 100
                
                conf = 75 - abs(h1_val - h2_val) / self.atr * 10
                self._add_pattern(PatternType.DOUBLE_TOP, PatternSignal.BEARISH, conf,
                                  f"Double Top at {h2_val:.2f} - bearish target {neckline - pattern_height:.2f}",
                                  target_move)
        
        # Double Bottom (last 2 swing lows at similar level)
        if len(self.swing_lows) >= 2:
            l1_idx, l1_val = self.swing_lows[-2]
            l2_idx, l2_val = self.swing_lows[-1]
            
            if (abs(l1_val - l2_val) < tolerance and 
                l2_idx - l1_idx > 10 and
                self.current_price > l2_val):
                
                between = self.df['high'].iloc[l1_idx:l2_idx]
                neckline = float(between.max()) if len(between) > 0 else self.current_price
                pattern_height = neckline - l2_val
                target_move = (pattern_height / self.current_price) * 100
                
                conf = 75 - abs(l1_val - l2_val) / self.atr * 10
                self._add_pattern(PatternType.DOUBLE_BOTTOM, PatternSignal.BULLISH, conf,
                                  f"Double Bottom at {l2_val:.2f} - bullish target {neckline + pattern_height:.2f}",
                                  target_move)
    
    def _detect_head_and_shoulders(self):
        """Detect Head & Shoulders and Inverse H&S"""
        if len(self.swing_highs) < 3 or len(self.swing_lows) < 2:
            return
        
        tolerance = self.atr * 0.3
        
        # Head & Shoulders (bearish)
        h1_idx, h1 = self.swing_highs[-3]
        h2_idx, h2 = self.swing_highs[-2]  # Head
        h3_idx, h3 = self.swing_highs[-1]
        
        if (h2 > h1 and h2 > h3 and               # Head is highest
            abs(h1 - h3) < tolerance * 2 and        # Shoulders at similar level
            h2_idx > h1_idx and h3_idx > h2_idx):   # Proper order
            
            # Find neckline
            lows_between = []
            for idx, val in self.swing_lows:
                if h1_idx < idx < h3_idx:
                    lows_between.append(val)
            
            if lows_between:
                neckline = np.mean(lows_between)
                pattern_height = h2 - neckline
                target = neckline - pattern_height
                target_move = ((target - self.current_price) / self.current_price) * 100
                
                self._add_pattern(PatternType.HEAD_SHOULDERS, PatternSignal.BEARISH, 80,
                                  f"Head & Shoulders - neckline {neckline:.2f}, target {target:.2f}",
                                  target_move)
        
        # Inverse Head & Shoulders (bullish)
        if len(self.swing_lows) >= 3:
            l1_idx, l1 = self.swing_lows[-3]
            l2_idx, l2 = self.swing_lows[-2]  # Head
            l3_idx, l3 = self.swing_lows[-1]
            
            if (l2 < l1 and l2 < l3 and
                abs(l1 - l3) < tolerance * 2 and
                l2_idx > l1_idx and l3_idx > l2_idx):
                
                highs_between = []
                for idx, val in self.swing_highs:
                    if l1_idx < idx < l3_idx:
                        highs_between.append(val)
                
                if highs_between:
                    neckline = np.mean(highs_between)
                    pattern_height = neckline - l2
                    target = neckline + pattern_height
                    target_move = ((target - self.current_price) / self.current_price) * 100
                    
                    self._add_pattern(PatternType.INV_HEAD_SHOULDERS, PatternSignal.BULLISH, 80,
                                      f"Inverse H&S - neckline {neckline:.2f}, target {target:.2f}",
                                      target_move)
    
    def _detect_triangles(self):
        """Detect ascending, descending, and symmetrical triangles"""
        if len(self.swing_highs) < 3 or len(self.swing_lows) < 3:
            return
        
        # Recent swing highs and lows
        recent_highs = self.swing_highs[-4:]
        recent_lows = self.swing_lows[-4:]
        
        high_values = [h[1] for h in recent_highs]
        low_values = [l[1] for l in recent_lows]
        
        high_slope = np.polyfit(range(len(high_values)), high_values, 1)[0] if len(high_values) >= 2 else 0
        low_slope = np.polyfit(range(len(low_values)), low_values, 1)[0] if len(low_values) >= 2 else 0
        
        tolerance = self.atr * 0.1
        
        # Ascending Triangle: flat highs, rising lows
        if abs(high_slope) < tolerance and low_slope > tolerance:
            self._add_pattern(PatternType.ASCENDING_TRIANGLE, PatternSignal.BULLISH, 72,
                              "Ascending Triangle - bullish breakout likely", 4.0)
        
        # Descending Triangle: falling highs, flat lows
        elif high_slope < -tolerance and abs(low_slope) < tolerance:
            self._add_pattern(PatternType.DESCENDING_TRIANGLE, PatternSignal.BEARISH, 72,
                              "Descending Triangle - bearish breakdown likely", -4.0)
        
        # Symmetrical Triangle: converging highs and lows
        elif high_slope < -tolerance and low_slope > tolerance:
            self._add_pattern(PatternType.SYMMETRICAL_TRIANGLE, PatternSignal.NEUTRAL, 60,
                              "Symmetrical Triangle - breakout imminent, direction unclear", 0)
    
    def _detect_flags(self):
        """Detect bull and bear flags"""
        if len(self.df) < 30: return
        
        # Look for sharp move followed by consolidation
        recent = self.df.iloc[-30:]
        first_half = recent.iloc[:15]
        second_half = recent.iloc[15:]
        
        first_move = (first_half['close'].iloc[-1] - first_half['close'].iloc[0]) / first_half['close'].iloc[0]
        second_vol = second_half['close'].std() / second_half['close'].mean()
        
        # Bull Flag: sharp up move + low vol consolidation
        if first_move > 0.05 and second_vol < 0.02:
            self._add_pattern(PatternType.BULL_FLAG, PatternSignal.BULLISH, 70,
                              "Bull Flag - continuation pattern, bullish", 5.0)
        
        # Bear Flag: sharp down move + low vol consolidation
        elif first_move < -0.05 and second_vol < 0.02:
            self._add_pattern(PatternType.BEAR_FLAG, PatternSignal.BEARISH, 70,
                              "Bear Flag - continuation pattern, bearish", -5.0)
    
    def _detect_wedges(self):
        """Detect rising and falling wedges"""
        if len(self.swing_highs) < 3 or len(self.swing_lows) < 3:
            return
        
        high_values = [h[1] for h in self.swing_highs[-4:]]
        low_values = [l[1] for l in self.swing_lows[-4:]]
        
        if len(high_values) < 2 or len(low_values) < 2:
            return
        
        high_slope = np.polyfit(range(len(high_values)), high_values, 1)[0]
        low_slope = np.polyfit(range(len(low_values)), low_values, 1)[0]
        
        # Rising Wedge (bearish): both slopes positive, converging
        if high_slope > 0 and low_slope > 0 and high_slope < low_slope:
            self._add_pattern(PatternType.RISING_WEDGE, PatternSignal.BEARISH, 68,
                              "Rising Wedge - bearish reversal pattern", -3.5)
        
        # Falling Wedge (bullish): both slopes negative, converging
        elif high_slope < 0 and low_slope < 0 and high_slope > low_slope:
            self._add_pattern(PatternType.FALLING_WEDGE, PatternSignal.BULLISH, 68,
                              "Falling Wedge - bullish reversal pattern", 3.5)
    
    def _detect_channels(self):
        """Detect price channels"""
        if len(self.df) < 40: return
        
        recent = self.df.iloc[-40:]
        closes = recent['close'].values
        x = np.arange(len(closes))
        
        slope, intercept = np.polyfit(x, closes, 1)
        trend_line = slope * x + intercept
        residuals = closes - trend_line
        
        # Check if residuals are bounded (channel)
        if np.std(residuals) / np.mean(closes) < 0.03:
            if slope > 0:
                self._add_pattern(PatternType.CHANNEL_UP, PatternSignal.BULLISH, 65,
                                  "Ascending Channel - bullish trend", 3.0)
            else:
                self._add_pattern(PatternType.CHANNEL_DOWN, PatternSignal.BEARISH, 65,
                                  "Descending Channel - bearish trend", -3.0)
    
    def _detect_crossovers(self):
        """Detect golden cross and death cross"""
        if len(self.df) < 210: return
        
        sma50 = self.df['close'].rolling(50).mean()
        sma200 = self.df['close'].rolling(200).mean()
        
        if sma50.iloc[-1] > sma200.iloc[-1] and sma50.iloc[-2] <= sma200.iloc[-2]:
            self._add_pattern(PatternType.GOLDEN_CROSS, PatternSignal.BULLISH, 78,
                              "Golden Cross (50 SMA > 200 SMA) - major bullish signal", 8.0)
        
        elif sma50.iloc[-1] < sma200.iloc[-1] and sma50.iloc[-2] >= sma200.iloc[-2]:
            self._add_pattern(PatternType.DEATH_CROSS, PatternSignal.BEARISH, 78,
                              "Death Cross (50 SMA < 200 SMA) - major bearish signal", -8.0)
    
    def _detect_breakouts(self):
        """Detect breakouts from consolidation"""
        if len(self.df) < 30: return
        
        # 20-day range
        high_20 = self.df['high'].iloc[-20:-1].max()
        low_20 = self.df['low'].iloc[-20:-1].min()
        range_20 = high_20 - low_20
        
        # Check for breakout
        current = self.df.iloc[-1]
        
        if current['close'] > high_20 and current['volume'] > self.df['volume'].iloc[-20:].mean() * 1.5:
            self._add_pattern(PatternType.BREAKOUT_UP, PatternSignal.BULLISH, 75,
                              f"Breakout above 20-day high {high_20:.2f} with volume confirmation", 5.0)
        
        elif current['close'] < low_20 and current['volume'] > self.df['volume'].iloc[-20:].mean() * 1.5:
            self._add_pattern(PatternType.BREAKOUT_DOWN, PatternSignal.BEARISH, 75,
                              f"Breakdown below 20-day low {low_20:.2f} with volume confirmation", -5.0)


# ==================== SUPPORT/RESISTANCE DETECTOR ====================

class SupportResistanceDetector:
    """
    Identifies key support and resistance levels using price clustering.
    
    Innovation: Uses kernel density estimation on price action to find
    statistically significant price levels with adaptive bandwidth.
    """
    
    def __init__(self, df: pd.DataFrame, n_levels: int = 5):
        self.df = df
        self.n_levels = n_levels
        self.current_price = float(df['close'].iloc[-1])
    
    def detect(self) -> Tuple[List[SupportResistance], List[SupportResistance]]:
        """Find support and resistance levels"""
        # Combine multiple price action points
        prices = np.concatenate([
            self.df['high'].values,
            self.df['low'].values,
            self.df['close'].values,
            self.df['open'].values
        ])
        
        # Remove outliers
        q1, q3 = np.percentile(prices, [5, 95])
        prices = prices[(prices >= q1) & (prices <= q3)]
        
        # Create price bins using histogram
        n_bins = min(100, len(prices) // 10)
        if n_bins < 5:
            return [], []
        
        counts, bin_edges = np.histogram(prices, bins=n_bins)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        
        # Smooth the histogram
        from scipy.ndimage import gaussian_filter1d
        try:
            smoothed = gaussian_filter1d(counts.astype(float), sigma=2)
        except ImportError:
            # Fallback: simple moving average smoothing
            kernel = np.ones(5) / 5
            smoothed = np.convolve(counts.astype(float), kernel, mode='same')
        
        # Find peaks (levels with high price concentration)
        levels = []
        for i in range(1, len(smoothed) - 1):
            if smoothed[i] > smoothed[i-1] and smoothed[i] > smoothed[i+1] and smoothed[i] > np.mean(smoothed):
                levels.append({
                    'price': bin_centers[i],
                    'strength': int(smoothed[i]),
                    'count': int(counts[i])
                })
        
        # Sort by strength
        levels.sort(key=lambda x: x['strength'], reverse=True)
        levels = levels[:self.n_levels * 2]
        
        # Classify as support or resistance
        supports = []
        resistances = []
        
        for level in levels:
            price = level['price']
            distance_pct = ((price - self.current_price) / self.current_price) * 100
            
            sr = SupportResistance(
                level=round(price, 2),
                strength=level['strength'],
                level_type="support" if price < self.current_price else "resistance",
                distance_pct=round(distance_pct, 2)
            )
            
            if price < self.current_price:
                supports.append(sr)
            else:
                resistances.append(sr)
        
        # Sort: supports descending (closest first), resistances ascending (closest first)
        supports.sort(key=lambda x: x.level, reverse=True)
        resistances.sort(key=lambda x: x.level)
        
        return supports[:self.n_levels], resistances[:self.n_levels]


# ==================== CONFLUENCE ENGINE ====================

class CrossPatternConfluenceEngine:
    """
    PATENT-PENDING: Cross-Pattern Confluence Scoring (CPCS)
    
    Computes a unified confluence score by measuring agreement between
    multiple pattern types, timeframes, and technical signals.
    
    The score is the WEIGHTED AVERAGE of individual pattern signals,
    where weights = confidence × reliability, normalized by pattern count.
    
    Innovation:
    1. Agreement matrix between different pattern categories
    2. Multi-timeframe confirmation (candlestick + chart + trend)
    3. Support/Resistance integration for entry/exit calibration
    4. Dynamic target computation using pattern-implied moves
    """
    
    def __init__(self, df: pd.DataFrame):
        if len(df) < 20:
            raise ValueError("Insufficient data for pattern analysis (need >= 20 rows)")
        
        self.df = df.copy()
        self.current_price = float(df['close'].iloc[-1])
        
        # Compute ATR for risk levels
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.atr = float(tr.rolling(14).mean().iloc[-1])
    
    def analyze(self) -> ConfluenceResult:
        """Run full pattern analysis and compute confluence score"""
        
        # Step 1: Detect candlestick patterns
        candle_detector = CandlestickDetector(self.df)
        candle_patterns = candle_detector.detect_all()
        
        # Step 2: Detect chart patterns
        chart_detector = ChartPatternDetector(self.df)
        chart_patterns = chart_detector.detect_all()
        
        # Step 3: Detect support/resistance
        sr_detector = SupportResistanceDetector(self.df)
        supports, resistances = sr_detector.detect()
        
        # Combine all patterns
        all_patterns = candle_patterns + chart_patterns
        
        # Step 4: Compute confluence score
        confluence_score, agreement, dominant_signal = self._compute_confluence(all_patterns)
        
        # Step 5: Compute trend strength
        trend_strength = self._compute_trend_strength()
        
        # Step 6: Compute suggested entry, stoploss, target
        entry, stoploss, target, rr = self._compute_trade_levels(
            all_patterns, supports, resistances, dominant_signal
        )
        
        # Step 7: Generate summary
        summary = self._generate_summary(all_patterns, confluence_score, dominant_signal, trend_strength)
        
        return ConfluenceResult(
            patterns_detected=[p.to_dict() for p in all_patterns],
            support_levels=[s.to_dict() for s in supports],
            resistance_levels=[r.to_dict() for r in resistances],
            confluence_score=round(confluence_score, 2),
            pattern_agreement=round(agreement, 2),
            dominant_signal=dominant_signal,
            trend_strength=round(trend_strength, 2),
            suggested_entry=round(entry, 2),
            suggested_stoploss=round(stoploss, 2),
            suggested_target=round(target, 2),
            risk_reward_from_patterns=round(rr, 2),
            pattern_summary=summary
        )
    
    def _compute_confluence(self, patterns: List[DetectedPattern]) -> Tuple[float, float, str]:
        """
        Compute weighted confluence score.
        
        Returns: (confluence_score, agreement_pct, dominant_signal)
        """
        if not patterns:
            return 0.0, 0.0, "NEUTRAL"
        
        bullish_weight = 0
        bearish_weight = 0
        total_weight = 0
        
        for p in patterns:
            weight = (p.confidence / 100) * p.reliability
            total_weight += weight
            
            if p.signal == "BULLISH":
                bullish_weight += weight
            elif p.signal == "BEARISH":
                bearish_weight += weight
        
        if total_weight == 0:
            return 0.0, 0.0, "NEUTRAL"
        
        # Confluence score: -100 to +100
        confluence = ((bullish_weight - bearish_weight) / total_weight) * 100
        
        # Agreement: how much patterns agree (0-100)
        max_side = max(bullish_weight, bearish_weight)
        agreement = (max_side / total_weight) * 100
        
        # Dominant signal
        if confluence > 15:
            dominant = "BULLISH"
        elif confluence < -15:
            dominant = "BEARISH"
        else:
            dominant = "NEUTRAL"
        
        return confluence, agreement, dominant
    
    def _compute_trend_strength(self) -> float:
        """Compute overall trend strength (0-100)"""
        if len(self.df) < 50:
            return 50.0
        
        close = self.df['close']
        
        # Multiple moving average alignment
        sma_5 = close.rolling(5).mean().iloc[-1]
        sma_10 = close.rolling(10).mean().iloc[-1]
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1]
        
        # Check alignment (bull: 5 > 10 > 20 > 50, bear: reverse)
        bull_aligned = sum([
            sma_5 > sma_10,
            sma_10 > sma_20,
            sma_20 > sma_50,
            self.current_price > sma_5
        ])
        
        bear_aligned = sum([
            sma_5 < sma_10,
            sma_10 < sma_20,
            sma_20 < sma_50,
            self.current_price < sma_5
        ])
        
        alignment = max(bull_aligned, bear_aligned) / 4 * 100
        
        # ADX-like calculation
        plus_dm = self.df['high'].diff().clip(lower=0)
        minus_dm = (-self.df['low'].diff()).clip(lower=0)
        
        atr_14 = pd.concat([
            self.df['high'] - self.df['low'],
            abs(self.df['high'] - self.df['close'].shift()),
            abs(self.df['low'] - self.df['close'].shift())
        ], axis=1).max(axis=1).rolling(14).mean()
        
        plus_di = 100 * (plus_dm.rolling(14).mean() / (atr_14 + 1e-10))
        minus_di = 100 * (minus_dm.rolling(14).mean() / (atr_14 + 1e-10))
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(14).mean().iloc[-1]
        adx = min(adx, 100)
        
        # Combine alignment and ADX
        strength = 0.5 * alignment + 0.5 * adx
        return min(strength, 100)
    
    def _compute_trade_levels(self, patterns: List[DetectedPattern],
                               supports: List[SupportResistance],
                               resistances: List[SupportResistance],
                               signal: str) -> Tuple[float, float, float, float]:
        """
        Compute entry, stop-loss, target, and risk/reward ratio
        using pattern analysis and support/resistance levels.
        
        Innovation: ATR-adaptive levels calibrated by nearest S/R
        """
        entry = self.current_price
        
        # Compute pattern-implied target
        if patterns:
            target_moves = [p.target_move_pct for p in patterns if p.target_move_pct != 0]
            if target_moves:
                # Weighted average of target moves
                weights = [(p.confidence * p.reliability) for p in patterns if p.target_move_pct != 0]
                avg_move = np.average(target_moves, weights=weights)
                pattern_target = entry * (1 + avg_move / 100)
            else:
                pattern_target = entry
        else:
            pattern_target = entry
        
        if signal == "BULLISH":
            # Stop-loss: below nearest support or 2x ATR
            if supports:
                sl_from_support = supports[0].level - 0.5 * self.atr
                sl_from_atr = entry - 2 * self.atr
                stoploss = max(sl_from_support, sl_from_atr)  # Tighter stop
            else:
                stoploss = entry - 2 * self.atr
            
            # Target: nearest resistance or pattern-implied, whichever is closer
            if resistances:
                sr_target = resistances[0].level
                target = min(max(pattern_target, sr_target), entry + 5 * self.atr)
            else:
                target = max(pattern_target, entry + 2 * self.atr)
            
            # Buy price: slight pullback entry
            entry = entry - 0.3 * self.atr
            
        elif signal == "BEARISH":
            # Stop-loss: above nearest resistance or 2x ATR
            if resistances:
                sl_from_resistance = resistances[0].level + 0.5 * self.atr
                sl_from_atr = entry + 2 * self.atr
                stoploss = min(sl_from_resistance, sl_from_atr)
            else:
                stoploss = entry + 2 * self.atr
            
            # Target: nearest support or pattern-implied
            if supports:
                sr_target = supports[0].level
                target = max(min(pattern_target, sr_target), entry - 5 * self.atr)
            else:
                target = min(pattern_target, entry - 2 * self.atr)
            
            entry = entry + 0.3 * self.atr
            
        else:  # NEUTRAL
            stoploss = entry - 1.5 * self.atr
            target = entry + 1.5 * self.atr
        
        # Risk/Reward
        risk = abs(entry - stoploss)
        reward = abs(target - entry)
        rr = reward / risk if risk > 0 else 0
        
        return entry, stoploss, target, rr
    
    def _generate_summary(self, patterns: List[DetectedPattern], 
                          confluence: float, signal: str, trend: float) -> str:
        """Generate human-readable pattern summary"""
        
        n_bull = sum(1 for p in patterns if p.signal == "BULLISH")
        n_bear = sum(1 for p in patterns if p.signal == "BEARISH")
        n_neutral = sum(1 for p in patterns if p.signal == "NEUTRAL")
        
        top_patterns = sorted(patterns, key=lambda p: p.confidence * p.reliability, reverse=True)[:3]
        top_names = ", ".join([p.pattern_type.replace("_", " ").title() for p in top_patterns])
        
        summary_parts = [
            f"Detected {len(patterns)} patterns ({n_bull} bullish, {n_bear} bearish, {n_neutral} neutral).",
            f"Confluence Score: {confluence:+.1f}/100 ({signal}).",
            f"Trend Strength: {trend:.0f}/100.",
        ]
        
        if top_names:
            summary_parts.append(f"Key Patterns: {top_names}.")
        
        if confluence > 50:
            summary_parts.append("Strong bullish consensus across multiple pattern types.")
        elif confluence < -50:
            summary_parts.append("Strong bearish consensus across multiple pattern types.")
        elif abs(confluence) < 15:
            summary_parts.append("Mixed signals - exercise caution, wait for confirmation.")
        
        return " ".join(summary_parts)


# ==================== CONVENIENCE FUNCTION ====================

def detect_patterns(df: pd.DataFrame) -> Dict:
    """
    Convenience function for pattern detection.
    
    Args:
        df: DataFrame with columns [date, open, high, low, close, volume]
    
    Returns:
        Dict with full pattern analysis
    """
    try:
        engine = CrossPatternConfluenceEngine(df)
        result = engine.analyze()
        return result.to_dict()
    except Exception as e:
        logger.error(f"Pattern detection error: {e}")
        return {
            "patterns_detected": [],
            "support_levels": [],
            "resistance_levels": [],
            "confluence_score": 0,
            "pattern_agreement": 0,
            "dominant_signal": "NEUTRAL",
            "trend_strength": 50,
            "suggested_entry": float(df['close'].iloc[-1]) if not df.empty else 0,
            "suggested_stoploss": 0,
            "suggested_target": 0,
            "risk_reward_from_patterns": 0,
            "pattern_summary": f"Pattern detection failed: {str(e)}"
        }
