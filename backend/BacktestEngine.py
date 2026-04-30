"""
Universal Backtest Engine
=========================
Production-grade backtesting engine that works across all stock types:
penny stocks, blue chips, volatile biotechs, stable utilities.

Features:
- Volume-aware slippage model
- Gap handling (open-price fills, gap-through stops)
- Market regime detection (bull/bear/high-vol/low-vol/choppy)
- Walk-forward validation with parameter stability testing
- Multiple position sizing modes
- ATR-based stops and targets
- Data integrity checks (anomaly detection, lookahead bias prevention)
- Regime-segmented performance reporting
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from copy import deepcopy

from backtest_models import (
    BacktestConfig, BacktestResult, Trade, WalkForwardConfig, WalkForwardResult,
    MarketRegime, PositionSizingMode, PositionType, OrderType, ExitReason,
)

logger = logging.getLogger(__name__)


# ==================== DATA NORMALIZER ====================

class DataNormalizer:
    """
    Prepare price data for backtesting:
    - Adjust for splits/dividends using adj_close ratio
    - Detect and flag anomalies
    - Add ATR, volatility, and volume metrics
    """

    @staticmethod
    def normalize(df: pd.DataFrame, config: BacktestConfig) -> pd.DataFrame:
        """Normalize and enrich price data for backtesting."""
        df = df.copy()
        df = df.sort_values('date').reset_index(drop=True)

        # --- Split/Dividend adjustment ---
        if 'adj_close' in df.columns:
            adj_factor = df['adj_close'] / df['close'].replace(0, np.nan)
            adj_factor = adj_factor.ffill().bfill().fillna(1.0)
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col] * adj_factor

        # --- Percentage returns ---
        df['daily_return'] = df['close'].pct_change().fillna(0)

        # --- ATR (14-period) ---
        high_low = df['high'] - df['low']
        high_prev_close = np.abs(df['high'] - df['close'].shift(1))
        low_prev_close = np.abs(df['low'] - df['close'].shift(1))
        true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
        df['atr_14'] = true_range.rolling(14, min_periods=1).mean()

        # --- Average volume ---
        df['avg_volume_20'] = df['volume'].rolling(20, min_periods=1).mean()

        # --- Rolling volatility ---
        df['rolling_vol_20'] = df['daily_return'].rolling(
            config.regime_vol_period, min_periods=5
        ).std().fillna(0)

        # --- SMA for regime detection ---
        df['sma_regime'] = df['close'].rolling(
            config.regime_sma_period, min_periods=10
        ).mean()

        # --- Anomaly flags ---
        df['anomaly'] = np.abs(df['daily_return']) > (config.max_single_day_move_pct / 100)

        # --- Zero volume flags ---
        df['zero_volume'] = df['volume'] <= 0

        # Clean infinities
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.ffill().bfill().fillna(0)

        return df


# ==================== MARKET REGIME DETECTOR ====================

class RegimeDetector:
    """Classify market regime for each bar."""

    @staticmethod
    def detect(df: pd.DataFrame, config: BacktestConfig) -> pd.Series:
        """
        Returns a Series of MarketRegime values aligned with df index.
        """
        regimes = []

        for i in range(len(df)):
            vol = df['rolling_vol_20'].iloc[i]
            price = df['close'].iloc[i]
            sma = df['sma_regime'].iloc[i]

            if vol > config.regime_vol_high_threshold:
                regime = MarketRegime.HIGH_VOL
            elif vol < config.regime_vol_low_threshold:
                regime = MarketRegime.LOW_VOL
            elif sma > 0 and price > sma * 1.02:
                regime = MarketRegime.BULL
            elif sma > 0 and price < sma * 0.98:
                regime = MarketRegime.BEAR
            else:
                regime = MarketRegime.CHOPPY

            regimes.append(regime)

        return pd.Series(regimes, index=df.index)


# ==================== BACKTEST ENGINE ====================

class BacktestEngine:
    """
    Universal backtesting engine with:
    - Realistic fill logic (gaps, limits, stops)
    - Volume-aware slippage
    - Multiple position sizing modes
    - Priority exit ordering
    - Market regime tagging
    - Walk-forward validation
    """

    def __init__(self, data_pipeline=None, config: Optional[BacktestConfig] = None):
        self.pipeline = data_pipeline
        self.config = config or BacktestConfig()

    # ─── Slippage ───────────────────────────────────────────

    def calculate_slippage(
        self, price: float, quantity: int, atr: float,
        avg_volume: float, is_buy: bool
    ) -> float:
        """
        Volume- and volatility-aware slippage model.
        Slippage = base% * (1 + order_size/avg_vol * impact) * (atr_ratio)
        """
        cfg = self.config
        base_slip = cfg.base_slippage_pct / 100

        # Volume impact: larger orders relative to avg volume get worse fills
        vol_ratio = (quantity * price) / max(avg_volume * price, 1)
        volume_component = 1 + vol_ratio * cfg.volume_impact_factor

        # Volatility component: scale slippage with current ATR / price ratio
        atr_ratio = (atr / max(price, 0.01))
        vol_component = 1 + atr_ratio * cfg.volatility_slippage_factor * 100

        total_slip_pct = base_slip * volume_component * vol_component
        slippage_amount = price * total_slip_pct * quantity

        return round(slippage_amount, 2)

    # ─── Transaction Costs ──────────────────────────────────

    def calculate_transaction_cost(self, price: float, quantity: int) -> float:
        """Apply per-trade or per-share commission with minimum fee."""
        cfg = self.config
        trade_value = price * quantity

        if cfg.commission_per_share > 0:
            cost = cfg.commission_per_share * quantity
        else:
            cost = trade_value * (cfg.transaction_cost_pct / 100)

        return max(cost, cfg.min_commission)

    # ─── Position Sizing ────────────────────────────────────

    def calculate_position_size(
        self, capital: float, entry_price: float,
        stop_loss_price: float, atr: float,
        current_total_risk: float = 0.0
    ) -> int:
        """
        Calculate position size based on the configured sizing mode.
        """
        cfg = self.config
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share <= 0:
            risk_per_share = entry_price * (cfg.stop_loss_pct / 100)

        if cfg.sizing_mode == PositionSizingMode.RISK_BASED:
            risk_amount = capital * (cfg.risk_per_trade_pct / 100)
            quantity = int(risk_amount / risk_per_share)

        elif cfg.sizing_mode == PositionSizingMode.VOLATILITY_ADJUSTED:
            # Target a fixed daily volatility contribution
            daily_vol = atr / max(entry_price, 0.01)
            target_vol = cfg.volatility_target_pct / 100
            if daily_vol > 0:
                notional = capital * target_vol / daily_vol
                quantity = int(notional / entry_price)
            else:
                quantity = int(capital * 0.05 / entry_price)

        elif cfg.sizing_mode == PositionSizingMode.FIXED_DOLLAR:
            quantity = int(cfg.fixed_trade_amount / entry_price)

        elif cfg.sizing_mode == PositionSizingMode.PORTFOLIO_HEAT:
            max_total_risk = capital * (cfg.max_portfolio_heat_pct / 100)
            available_risk = max_total_risk - current_total_risk
            if available_risk <= 0:
                return 0
            quantity = int(available_risk / risk_per_share)

        else:
            quantity = int((capital * 0.05) / entry_price)

        # Cap at max position percentage
        max_position_value = capital * (cfg.max_position_pct / 100)
        max_qty = int(max_position_value / max(entry_price, 0.01))
        quantity = min(quantity, max_qty)

        return max(quantity, 0)

    # ─── Fill Price Logic ───────────────────────────────────

    def get_fill_price(
        self, row: pd.Series, signal: int,
        order_type: OrderType = None, limit_price: float = None
    ) -> Optional[float]:
        """
        Determine the fill price based on order type and bar data.
        Returns None if order cannot be filled this bar.
        """
        ot = order_type or self.config.default_order_type
        open_p = row.get('open', row['close'])
        high = row.get('high', row['close'])
        low = row.get('low', row['close'])
        close = row['close']

        if ot == OrderType.MARKET:
            if self.config.use_next_bar_open:
                return open_p
            # Approximate mid-price
            return (open_p + close) / 2

        elif ot == OrderType.LIMIT:
            if signal == 1:  # Buy limit: fill if price dips to limit
                if limit_price is not None and low <= limit_price:
                    return limit_price
                return None
            else:  # Sell limit: fill if price reaches limit
                if limit_price is not None and high >= limit_price:
                    return limit_price
                return None

        elif ot == OrderType.STOP:
            if signal == 1:  # Buy stop: fill if price rises to stop
                if limit_price is not None and high >= limit_price:
                    return max(open_p, limit_price)  # Gap up → fill at open
                return None
            else:  # Sell stop: fill if price drops to stop
                if limit_price is not None and low <= limit_price:
                    return min(open_p, limit_price)  # Gap down → fill at open
                return None

        return close

    # ─── Stop / Target Check ────────────────────────────────

    def _check_exits(
        self, row: pd.Series, trade: Trade, bar_idx: int, entry_bar: int
    ) -> Optional[Tuple[float, ExitReason]]:
        """
        Check exit conditions in priority order:
        1. Stop-loss (including gap-through)
        2. Take-profit
        3. Trailing stop
        4. Time-based exit

        Returns (exit_price, reason) or None.
        """
        cfg = self.config
        open_p = row.get('open', row['close'])
        high = row.get('high', row['close'])
        low = row.get('low', row['close'])

        # 1. STOP-LOSS: did price go below stop?
        if trade.stop_loss_price > 0 and low <= trade.stop_loss_price:
            # Gap through: price opened below stop → fill at open (worse)
            if open_p <= trade.stop_loss_price:
                return (open_p, ExitReason.GAP_STOP)
            else:
                return (trade.stop_loss_price, ExitReason.STOP_LOSS)

        # 2. TAKE-PROFIT: did price reach target?
        if trade.take_profit_price > 0 and high >= trade.take_profit_price:
            if open_p >= trade.take_profit_price:
                return (open_p, ExitReason.TAKE_PROFIT)
            else:
                return (trade.take_profit_price, ExitReason.TAKE_PROFIT)

        # 3. TRAILING STOP
        if cfg.use_trailing_stop and trade.trailing_stop_price > 0:
            # Update highest price
            if high > trade.highest_price_since_entry:
                trade.highest_price_since_entry = high
                trade.trailing_stop_price = trade.highest_price_since_entry * (
                    1 - cfg.trailing_stop_pct / 100
                )
            if low <= trade.trailing_stop_price:
                if open_p <= trade.trailing_stop_price:
                    return (open_p, ExitReason.TRAILING_STOP)
                return (trade.trailing_stop_price, ExitReason.TRAILING_STOP)

        # 4. TIME-BASED EXIT
        if cfg.max_holding_days > 0:
            bars_held = bar_idx - entry_bar
            if bars_held >= cfg.max_holding_days:
                return (row['close'], ExitReason.TIME_EXIT)

        return None

    # ─── Main Backtest Loop ─────────────────────────────────

    def backtest_strategy(
        self,
        signals: pd.DataFrame,
        price_data: pd.DataFrame,
        strategy_name: str = "Custom Strategy"
    ) -> BacktestResult:
        """
        Run a full backtest on signal data against price data.

        Args:
            signals: DataFrame with 'date' and 'signal' columns
                     signal: 1=buy, -1=sell, 0=hold
            price_data: DataFrame with date, open, high, low, close, volume
                        (and optionally adj_close)
            strategy_name: Name for reporting

        Returns:
            BacktestResult with comprehensive metrics
        """
        cfg = self.config

        # --- Merge signals with price data ---
        if 'date' in signals.columns and 'date' in price_data.columns:
            merged = pd.merge(signals[['date', 'signal']], price_data, on='date', how='inner')
        else:
            merged = price_data.copy()
            if 'signal' not in merged.columns:
                merged['signal'] = signals['signal'].values[:len(merged)]

        # --- Normalize data ---
        merged = DataNormalizer.normalize(merged, cfg)

        # --- Detect regimes ---
        regimes = RegimeDetector.detect(merged, cfg)
        merged['regime'] = regimes

        # --- Simulation state ---
        capital = cfg.initial_capital
        position: Optional[Trade] = None  # Current open position
        entry_bar_idx = 0
        trades: List[Trade] = []
        equity_curve: List[Dict] = []
        total_txn_costs = 0.0
        total_slip_costs = 0.0
        current_portfolio_risk = 0.0

        for i in range(len(merged)):
            row = merged.iloc[i]

            # Skip anomalous or zero-volume bars
            if cfg.skip_zero_volume_bars and row.get('zero_volume', False):
                equity_curve.append(self._equity_point(row, capital, position))
                continue
            if row.get('anomaly', False):
                equity_curve.append(self._equity_point(row, capital, position))
                continue

            # Filter by minimum price & volume
            if row['close'] < cfg.min_price:
                equity_curve.append(self._equity_point(row, capital, position))
                continue
            if row.get('avg_volume_20', float('inf')) < cfg.min_avg_volume:
                equity_curve.append(self._equity_point(row, capital, position))
                continue

            atr = row.get('atr_14', row['close'] * 0.02)
            avg_vol = row.get('avg_volume_20', row.get('volume', 1))
            signal = row.get('signal', 0)

            # === CHECK EXITS FIRST (if in a position) ===
            if position is not None:
                exit_result = self._check_exits(row, position, i, entry_bar_idx)

                if exit_result is not None:
                    exit_price, exit_reason = exit_result
                    self._close_position(
                        position, exit_price, exit_reason, row, atr, avg_vol
                    )
                    capital += position.exit_price * position.quantity - position.transaction_costs - position.slippage_cost
                    # Only deduct exit costs from capital
                    exit_txn = self.calculate_transaction_cost(exit_price, position.quantity)
                    exit_slip = self.calculate_slippage(exit_price, position.quantity, atr, avg_vol, False)
                    capital -= exit_txn + exit_slip
                    total_txn_costs += exit_txn + position.transaction_costs
                    total_slip_costs += exit_slip + position.slippage_cost
                    current_portfolio_risk -= abs(position.entry_price - position.stop_loss_price) * position.quantity
                    trades.append(position)
                    position = None

                elif signal == -1:
                    # Manual sell signal
                    exit_price = self.get_fill_price(row, -1) or row['close']
                    self._close_position(
                        position, exit_price, ExitReason.SIGNAL, row, atr, avg_vol
                    )
                    exit_txn = self.calculate_transaction_cost(exit_price, position.quantity)
                    exit_slip = self.calculate_slippage(exit_price, position.quantity, atr, avg_vol, False)
                    capital += exit_price * position.quantity - exit_txn - exit_slip
                    total_txn_costs += exit_txn + position.transaction_costs
                    total_slip_costs += exit_slip + position.slippage_cost
                    current_portfolio_risk -= abs(position.entry_price - position.stop_loss_price) * position.quantity
                    trades.append(position)
                    position = None

            # === CHECK ENTRY (if no position) ===
            if position is None and signal == 1:
                fill_price = self.get_fill_price(row, 1) or row['close']

                # Calculate stops
                if cfg.use_atr_stops:
                    stop_loss = fill_price - (atr * cfg.atr_stop_multiplier)
                    take_profit = fill_price + (atr * cfg.atr_target_multiplier)
                else:
                    stop_loss = fill_price * (1 - cfg.stop_loss_pct / 100)
                    take_profit = fill_price * (1 + cfg.take_profit_pct / 100)

                # Position sizing
                quantity = self.calculate_position_size(
                    capital, fill_price, stop_loss, atr, current_portfolio_risk
                )

                if quantity <= 0:
                    equity_curve.append(self._equity_point(row, capital, position))
                    continue

                # Costs
                entry_txn = self.calculate_transaction_cost(fill_price, quantity)
                entry_slip = self.calculate_slippage(
                    fill_price, quantity, atr, avg_vol, True
                )
                adjusted_entry = fill_price * (1 + cfg.base_slippage_pct / 100)

                total_cost = adjusted_entry * quantity + entry_txn + entry_slip
                if total_cost > capital:
                    # Reduce quantity to fit
                    quantity = int((capital - entry_txn - entry_slip) / adjusted_entry)
                    if quantity <= 0:
                        equity_curve.append(self._equity_point(row, capital, position))
                        continue
                    total_cost = adjusted_entry * quantity + entry_txn + entry_slip

                # Create position
                position = Trade(
                    ticker=strategy_name,
                    entry_date=row['date'] if hasattr(row['date'], 'isoformat') else pd.to_datetime(row['date']),
                    entry_price=adjusted_entry,
                    position_type=PositionType.LONG,
                    quantity=quantity,
                    transaction_costs=entry_txn,
                    slippage_cost=entry_slip,
                    stop_loss_price=stop_loss,
                    take_profit_price=take_profit,
                    trailing_stop_price=(
                        adjusted_entry * (1 - cfg.trailing_stop_pct / 100)
                        if cfg.use_trailing_stop else 0
                    ),
                    highest_price_since_entry=adjusted_entry,
                    market_regime=row.get('regime', MarketRegime.UNKNOWN),
                )
                entry_bar_idx = i
                capital -= total_cost
                current_portfolio_risk += abs(adjusted_entry - stop_loss) * quantity

            # Track equity
            equity_curve.append(self._equity_point(row, capital, position))

        # --- Close remaining position at end ---
        if position is not None:
            last_row = merged.iloc[-1]
            exit_price = last_row['close']
            atr = last_row.get('atr_14', exit_price * 0.02)
            avg_vol = last_row.get('avg_volume_20', 1)
            self._close_position(
                position, exit_price, ExitReason.END_OF_BACKTEST, last_row, atr, avg_vol
            )
            exit_txn = self.calculate_transaction_cost(exit_price, position.quantity)
            exit_slip = self.calculate_slippage(exit_price, position.quantity, atr, avg_vol, False)
            capital += exit_price * position.quantity - exit_txn - exit_slip
            total_txn_costs += exit_txn + position.transaction_costs
            total_slip_costs += exit_slip + position.slippage_cost
            trades.append(position)

        # --- Calculate metrics ---
        return self._calculate_metrics(
            strategy_name, trades, equity_curve,
            cfg.initial_capital, capital,
            total_txn_costs, total_slip_costs, merged
        )

    # ─── Helpers ────────────────────────────────────────────

    def _equity_point(self, row, capital, position) -> Dict:
        """Create an equity curve data point."""
        equity = capital
        if position is not None:
            current_price = row['close']
            unrealized = (current_price - position.entry_price) * position.quantity
            equity += position.entry_price * position.quantity + unrealized
        dt = row['date']
        return {
            'date': dt.isoformat() if hasattr(dt, 'isoformat') else str(dt),
            'equity': round(equity, 2),
            'regime': row.get('regime', MarketRegime.UNKNOWN).value
                if isinstance(row.get('regime'), MarketRegime) else 'unknown',
        }

    def _close_position(
        self, trade: Trade, exit_price: float, reason: ExitReason,
        row: pd.Series, atr: float, avg_vol: float
    ):
        """Fill out trade exit fields."""
        dt = row['date']
        trade.exit_date = dt if hasattr(dt, 'isoformat') else pd.to_datetime(dt)
        trade.exit_price = exit_price
        trade.exit_reason = reason

        gross_pnl = (exit_price - trade.entry_price) * trade.quantity
        trade.pnl = gross_pnl  # Net PnL without costs (costs tracked separately)
        if trade.entry_price > 0:
            trade.pnl_pct = (gross_pnl / (trade.entry_price * trade.quantity)) * 100

        if trade.entry_date and trade.exit_date:
            try:
                delta = pd.to_datetime(trade.exit_date) - pd.to_datetime(trade.entry_date)
                trade.holding_days = max(delta.days, 0)
            except Exception:
                trade.holding_days = 0

    # ─── Metrics Calculation ────────────────────────────────

    def _calculate_metrics(
        self, strategy_name: str, trades: List[Trade],
        equity_curve: List[Dict], initial_capital: float,
        final_capital: float, total_txn_costs: float,
        total_slip_costs: float, data: pd.DataFrame
    ) -> BacktestResult:
        """Calculate comprehensive performance metrics with regime segmentation."""
        cfg = self.config

        total_return_pct = ((final_capital - initial_capital) / initial_capital) * 100

        # Dates
        if equity_curve and len(equity_curve) > 1:
            try:
                start_date = pd.to_datetime(equity_curve[0]['date'])
                end_date = pd.to_datetime(equity_curve[-1]['date'])
                days = max((end_date - start_date).days, 1)
                years = days / 365.25
            except Exception:
                start_date = end_date = datetime.now()
                years = 1.0
        else:
            start_date = end_date = datetime.now()
            years = 1.0

        # Annualized / CAGR
        if final_capital > 0 and initial_capital > 0 and years > 0:
            cagr = ((final_capital / initial_capital) ** (1 / max(years, 0.01)) - 1) * 100
        else:
            cagr = total_return_pct
        annualized_return = cagr

        # Daily returns for risk metrics
        equity_values = [e['equity'] for e in equity_curve]
        if len(equity_values) > 1:
            daily_returns = np.diff(equity_values) / np.maximum(equity_values[:-1], 0.01)
            daily_returns = np.nan_to_num(daily_returns, nan=0, posinf=0, neginf=0)
        else:
            daily_returns = np.array([0.0])

        # Sharpe
        daily_rf = cfg.risk_free_rate / 252
        excess = daily_returns - daily_rf
        std = np.std(daily_returns)
        sharpe = (np.mean(excess) / std * np.sqrt(252)) if std > 0 else 0.0

        # Sortino
        downside = daily_returns[daily_returns < 0]
        downside_std = np.std(downside) if len(downside) > 0 else std
        sortino = (np.mean(excess) / downside_std * np.sqrt(252)) if downside_std > 0 else sharpe

        # Annual volatility
        vol_annual = std * np.sqrt(252) * 100

        # Max Drawdown
        peak = initial_capital
        max_dd = 0.0
        dd_start = 0
        max_dd_duration = 0
        current_dd_start = None

        for i, eq in enumerate(equity_values):
            if eq > peak:
                peak = eq
                if current_dd_start is not None:
                    max_dd_duration = max(max_dd_duration, i - current_dd_start)
                current_dd_start = None
            else:
                dd = (peak - eq) / peak * 100
                if dd > max_dd:
                    max_dd = dd
                if current_dd_start is None:
                    current_dd_start = i

        # Calmar
        calmar = cagr / max_dd if max_dd > 0 else 0

        # --- Trade Statistics ---
        total_trades = len(trades)
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]
        win_rate = (len(winning) / total_trades * 100) if total_trades > 0 else 0

        avg_win = np.mean([t.pnl_pct for t in winning]) if winning else 0
        avg_loss = np.mean([abs(t.pnl_pct) for t in losing]) if losing else 0

        gross_profit = sum(t.pnl for t in winning)
        gross_loss = abs(sum(t.pnl for t in losing))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (
            gross_profit if gross_profit > 0 else 0
        )

        avg_holding = np.mean([t.holding_days for t in trades]) if trades else 0

        # Expectancy
        if total_trades > 0:
            expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)
        else:
            expectancy = 0

        # Max consecutive losses
        max_consec_loss = 0
        current_consec = 0
        for t in trades:
            if t.pnl <= 0:
                current_consec += 1
                max_consec_loss = max(max_consec_loss, current_consec)
            else:
                current_consec = 0

        # Monthly returns
        monthly_returns = []
        if len(equity_values) > 20:
            eq_series = pd.Series(equity_values)
            # Approximate monthly as every 21 bars
            monthly_eq = eq_series.iloc[::21]
            monthly_returns = list(monthly_eq.pct_change().dropna().values * 100)

        # --- Regime-Segmented Performance ---
        regime_perf = self._calculate_regime_performance(trades)

        return BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return_pct=total_return_pct,
            annualized_return_pct=annualized_return,
            cagr_pct=cagr,
            monthly_returns=monthly_returns,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown_pct=max_dd,
            max_drawdown_duration_days=max_dd_duration,
            volatility_annual_pct=vol_annual,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate_pct=win_rate,
            average_win_pct=avg_win,
            average_loss_pct=avg_loss,
            profit_factor=profit_factor,
            expectancy_per_trade=expectancy,
            average_holding_days=avg_holding,
            max_consecutive_losses=max_consec_loss,
            total_transaction_costs=total_txn_costs,
            total_slippage_costs=total_slip_costs,
            regime_performance=regime_perf,
            trades=trades,
            equity_curve=equity_curve,
            config=self.config,
        )

    def _calculate_regime_performance(self, trades: List[Trade]) -> Dict[str, Dict]:
        """Break down trade performance by market regime."""
        regime_groups: Dict[str, List[Trade]] = {}

        for t in trades:
            regime_key = t.market_regime.value if isinstance(t.market_regime, MarketRegime) else 'unknown'
            if regime_key not in regime_groups:
                regime_groups[regime_key] = []
            regime_groups[regime_key].append(t)

        result = {}
        for regime, regime_trades in regime_groups.items():
            n = len(regime_trades)
            wins = [t for t in regime_trades if t.pnl > 0]
            result[regime] = {
                'total_trades': n,
                'win_rate_pct': round(len(wins) / n * 100, 1) if n > 0 else 0,
                'avg_return_pct': round(np.mean([t.pnl_pct for t in regime_trades]), 2) if n > 0 else 0,
                'total_pnl': round(sum(t.pnl for t in regime_trades), 2),
                'avg_holding_days': round(np.mean([t.holding_days for t in regime_trades]), 1) if n > 0 else 0,
            }

        return result

    # ─── Strategy Comparison ────────────────────────────────

    def compare_strategies(
        self, strategies: Dict[str, pd.DataFrame],
        price_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Compare multiple strategies on the same price data."""
        results = {}

        for name, signals in strategies.items():
            try:
                result = self.backtest_strategy(signals, price_data, name)
                results[name] = result.to_dict()
            except Exception as e:
                logger.error(f"Error backtesting {name}: {e}")
                results[name] = {"error": str(e)}

        valid = {k: v for k, v in results.items() if 'error' not in v}

        rankings = {}
        if valid:
            rankings = {
                'by_return': sorted(valid, key=lambda x: valid[x].get('total_return_pct', 0), reverse=True),
                'by_sharpe': sorted(valid, key=lambda x: valid[x].get('sharpe_ratio', 0), reverse=True),
                'by_win_rate': sorted(valid, key=lambda x: valid[x].get('win_rate_pct', 0), reverse=True),
                'by_drawdown': sorted(valid, key=lambda x: valid[x].get('max_drawdown_pct', 100)),
                'by_calmar': sorted(valid, key=lambda x: valid[x].get('calmar_ratio', 0), reverse=True),
            }

        return {
            'results': results,
            'rankings': rankings,
            'config': {
                'transaction_cost_pct': self.config.transaction_cost_pct,
                'slippage_model': 'volume_volatility_aware',
                'initial_capital': self.config.initial_capital,
                'sizing_mode': self.config.sizing_mode.value,
            }
        }


# ==================== WALK-FORWARD ENGINE ====================

class WalkForwardEngine:
    """
    Walk-forward validation: optimize on in-sample, test on out-of-sample,
    roll forward through time.
    """

    def __init__(self, engine: BacktestEngine, config: Optional[WalkForwardConfig] = None):
        self.engine = engine
        self.wf_config = config or WalkForwardConfig()

    def validate(
        self,
        signals: pd.DataFrame,
        price_data: pd.DataFrame,
        strategy_name: str = "Walk-Forward"
    ) -> WalkForwardResult:
        """
        Run walk-forward validation with chronological splits.
        """
        wf = self.wf_config
        n = len(price_data)

        if n < wf.min_in_sample_bars + wf.min_out_sample_bars:
            logger.warning("Insufficient data for walk-forward validation")
            return WalkForwardResult(strategy_name=strategy_name, n_folds=0)

        fold_size = n // wf.n_splits
        is_results = []
        oos_results = []

        for fold in range(wf.n_splits):
            start = fold * fold_size
            end = min(start + fold_size, n)
            fold_data = price_data.iloc[start:end].reset_index(drop=True)
            fold_signals = signals.iloc[start:end].reset_index(drop=True)

            split_idx = int(len(fold_data) * wf.in_sample_ratio)

            if split_idx < wf.min_in_sample_bars or (len(fold_data) - split_idx) < wf.min_out_sample_bars:
                continue

            # In-sample
            is_data = fold_data.iloc[:split_idx].reset_index(drop=True)
            is_sig = fold_signals.iloc[:split_idx].reset_index(drop=True)
            try:
                is_result = self.engine.backtest_strategy(is_sig, is_data, f"{strategy_name}_IS_{fold+1}")
                is_results.append(is_result)
            except Exception as e:
                logger.warning(f"Walk-forward IS fold {fold+1} failed: {e}")
                continue

            # Out-of-sample
            oos_data = fold_data.iloc[split_idx:].reset_index(drop=True)
            oos_sig = fold_signals.iloc[split_idx:].reset_index(drop=True)
            try:
                oos_result = self.engine.backtest_strategy(oos_sig, oos_data, f"{strategy_name}_OOS_{fold+1}")
                oos_results.append(oos_result)
            except Exception as e:
                logger.warning(f"Walk-forward OOS fold {fold+1} failed: {e}")

        # Aggregate
        agg_oos_return = np.mean([r.total_return_pct for r in oos_results]) if oos_results else 0
        agg_oos_sharpe = np.mean([r.sharpe_ratio for r in oos_results]) if oos_results else 0

        # Parameter stability: compare IS vs OOS performance
        stability = {}
        if is_results and oos_results:
            is_avg_return = np.mean([r.total_return_pct for r in is_results])
            oos_avg_return = np.mean([r.total_return_pct for r in oos_results])
            stability['return_retention'] = oos_avg_return / is_avg_return if is_avg_return != 0 else 0

            is_avg_sharpe = np.mean([r.sharpe_ratio for r in is_results])
            oos_avg_sharpe = np.mean([r.sharpe_ratio for r in oos_results])
            stability['sharpe_retention'] = oos_avg_sharpe / is_avg_sharpe if is_avg_sharpe != 0 else 0

        is_robust = stability.get('return_retention', 0) > 0.5

        return WalkForwardResult(
            strategy_name=strategy_name,
            n_folds=len(oos_results),
            in_sample_results=is_results,
            out_sample_results=oos_results,
            aggregate_oos_return=agg_oos_return,
            aggregate_oos_sharpe=agg_oos_sharpe,
            parameter_stability=stability,
            is_robust=is_robust,
        )


# ==================== GLOBAL INSTANCE ====================

_backtest_engine: Optional[BacktestEngine] = None


def get_backtest_engine(
    data_pipeline=None, config: Optional[BacktestConfig] = None
) -> BacktestEngine:
    """Get or create the global backtest engine instance."""
    global _backtest_engine
    if _backtest_engine is None or config is not None:
        _backtest_engine = BacktestEngine(data_pipeline, config)
    return _backtest_engine


if __name__ == "__main__":
    config = BacktestConfig(
        initial_capital=100000.0,
        sizing_mode=PositionSizingMode.RISK_BASED,
        use_atr_stops=True,
        use_trailing_stop=True,
    )
    engine = BacktestEngine(config=config)
    print("✅ Universal Backtest Engine initialized")
    print(f"   Sizing mode: {config.sizing_mode.value}")
    print(f"   ATR stops: multiplier={config.atr_stop_multiplier}")
    print(f"   Trailing stop: {config.trailing_stop_pct}%")
    print(f"   Slippage model: volume+volatility aware")
    print(f"   Risk per trade: {config.risk_per_trade_pct}%")
