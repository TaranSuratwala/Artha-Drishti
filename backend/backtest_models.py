"""
Backtest Models
===============
Shared data classes, enums, and configuration for the universal backtesting framework.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


# ==================== ENUMS ====================

class MarketRegime(Enum):
    """Market regime classification"""
    BULL = "bull"
    BEAR = "bear"
    HIGH_VOL = "high_volatility"
    LOW_VOL = "low_volatility"
    CHOPPY = "choppy"
    UNKNOWN = "unknown"


class PositionSizingMode(Enum):
    """Position sizing methods"""
    RISK_BASED = "risk_based"              # Fixed % of equity risked per trade
    VOLATILITY_ADJUSTED = "volatility_adjusted"  # Scale inversely with ATR
    FIXED_DOLLAR = "fixed_dollar"          # Fixed rupee amount per trade
    PORTFOLIO_HEAT = "portfolio_heat"      # Max total risk across all positions


class OrderType(Enum):
    """Order fill types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class PositionType(Enum):
    """Trade direction"""
    LONG = "long"
    SHORT = "short"


class ExitReason(Enum):
    """Why a trade was closed"""
    SIGNAL = "signal_exit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    TIME_EXIT = "time_exit"
    END_OF_BACKTEST = "end_of_backtest"
    GAP_STOP = "gap_stop"  # Gapped through stop


# ==================== CONFIGURATION ====================

@dataclass
class BacktestConfig:
    """
    Comprehensive configuration for the universal backtesting engine.
    """

    # --- Capital ---
    initial_capital: float = 100000.0

    # --- Transaction Costs (percentage, e.g. 0.1 = 0.1%) ---
    transaction_cost_pct: float = 0.1
    min_commission: float = 20.0       # Minimum commission per trade (₹)
    commission_per_share: float = 0.0  # Per-share commission (0 = use percentage)

    # --- Slippage ---
    base_slippage_pct: float = 0.05    # Base slippage percentage
    volume_impact_factor: float = 0.1  # Extra slippage per (order_size / avg_volume)
    volatility_slippage_factor: float = 0.5  # Multiply slippage by current ATR ratio

    # --- Position Sizing ---
    sizing_mode: PositionSizingMode = PositionSizingMode.RISK_BASED
    risk_per_trade_pct: float = 2.0    # For RISK_BASED mode
    max_position_pct: float = 20.0     # Max % of capital in a single position
    fixed_trade_amount: float = 20000.0  # For FIXED_DOLLAR mode
    max_portfolio_heat_pct: float = 6.0  # For PORTFOLIO_HEAT: max total risk
    volatility_target_pct: float = 1.0   # For VOLATILITY_ADJUSTED: daily vol target

    # --- Stop Loss & Targets ---
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 15.0
    use_trailing_stop: bool = False
    trailing_stop_pct: float = 3.0
    max_holding_days: int = 0          # 0 = no time limit
    use_atr_stops: bool = True         # Use ATR-based stops instead of fixed %
    atr_stop_multiplier: float = 2.5   # Stop = entry - (ATR * multiplier)
    atr_target_multiplier: float = 4.0 # Target = entry + (ATR * multiplier)

    # --- Order Fill Logic ---
    default_order_type: OrderType = OrderType.MARKET
    use_next_bar_open: bool = True     # Fill at next bar's open (realistic)
    fill_limit_only_if_touched: bool = True  # Limit orders need price to reach

    # --- Data Filters ---
    min_price: float = 10.0            # Skip stocks below this price
    min_avg_volume: int = 10000        # Skip illiquid stocks
    max_single_day_move_pct: float = 50.0  # Cap / flag anomalous moves
    skip_zero_volume_bars: bool = True

    # --- Risk-Free Rate ---
    risk_free_rate: float = 0.065      # Annual (Indian govt bond ~6.5%)

    # --- Market Regime ---
    regime_sma_period: int = 50        # SMA period for trend detection
    regime_vol_period: int = 20        # Rolling window for volatility regime
    regime_vol_high_threshold: float = 0.02  # Daily vol above this = high vol
    regime_vol_low_threshold: float = 0.008  # Daily vol below this = low vol

    # --- Walk-Forward ---
    walk_forward_splits: int = 5
    in_sample_pct: float = 0.7        # 70% in-sample, 30% out-of-sample

    # --- include dividends ---
    include_dividends: bool = True


@dataclass
class WalkForwardConfig:
    """Configuration for walk-forward validation"""
    n_splits: int = 5
    in_sample_ratio: float = 0.7
    min_in_sample_bars: int = 200
    min_out_sample_bars: int = 50
    parameter_variations: Dict[str, List[float]] = field(default_factory=dict)
    # e.g. {'stop_loss_pct': [3.0, 5.0, 7.0], 'take_profit_pct': [10.0, 15.0, 20.0]}


# ==================== TRADE ====================

@dataclass
class Trade:
    """Represents a single completed trade"""
    ticker: str
    entry_date: datetime
    entry_price: float
    position_type: PositionType
    quantity: int
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    transaction_costs: float = 0.0
    slippage_cost: float = 0.0
    holding_days: int = 0
    exit_reason: ExitReason = ExitReason.SIGNAL
    market_regime: MarketRegime = MarketRegime.UNKNOWN
    # Stop tracking
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    trailing_stop_price: float = 0.0
    highest_price_since_entry: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker': self.ticker,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'entry_price': round(self.entry_price, 2),
            'exit_date': self.exit_date.isoformat() if self.exit_date else None,
            'exit_price': round(self.exit_price, 2) if self.exit_price else None,
            'position_type': self.position_type.value,
            'quantity': self.quantity,
            'pnl': round(self.pnl, 2),
            'pnl_pct': round(self.pnl_pct, 2),
            'transaction_costs': round(self.transaction_costs, 2),
            'slippage_cost': round(self.slippage_cost, 2),
            'holding_days': self.holding_days,
            'exit_reason': self.exit_reason.value,
            'market_regime': self.market_regime.value,
            'stop_loss_price': round(self.stop_loss_price, 2),
            'take_profit_price': round(self.take_profit_price, 2),
        }


# ==================== BACKTEST RESULT ====================

@dataclass
class BacktestResult:
    """Complete backtest results with regime-segmented metrics"""
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float

    # Return metrics
    total_return_pct: float
    annualized_return_pct: float
    cagr_pct: float = 0.0
    monthly_returns: List[float] = field(default_factory=list)

    # Risk metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0
    volatility_annual_pct: float = 0.0

    # Trade metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0
    average_win_pct: float = 0.0
    average_loss_pct: float = 0.0
    profit_factor: float = 0.0
    expectancy_per_trade: float = 0.0
    average_holding_days: float = 0.0
    max_consecutive_losses: int = 0

    # Cost metrics
    total_transaction_costs: float = 0.0
    total_slippage_costs: float = 0.0

    # Regime-segmented performance
    regime_performance: Dict[str, Dict] = field(default_factory=dict)

    # Raw data
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict] = field(default_factory=list)
    config: Optional[BacktestConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'strategy_name': self.strategy_name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'initial_capital': round(self.initial_capital, 2),
            'final_capital': round(self.final_capital, 2),
            'total_return_pct': round(self.total_return_pct, 2),
            'annualized_return_pct': round(self.annualized_return_pct, 2),
            'cagr_pct': round(self.cagr_pct, 2),
            'sharpe_ratio': round(self.sharpe_ratio, 3),
            'sortino_ratio': round(self.sortino_ratio, 3),
            'calmar_ratio': round(self.calmar_ratio, 3),
            'max_drawdown_pct': round(self.max_drawdown_pct, 2),
            'max_drawdown_duration_days': self.max_drawdown_duration_days,
            'volatility_annual_pct': round(self.volatility_annual_pct, 2),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_pct': round(self.win_rate_pct, 2),
            'average_win_pct': round(self.average_win_pct, 2),
            'average_loss_pct': round(self.average_loss_pct, 2),
            'profit_factor': round(self.profit_factor, 2),
            'expectancy_per_trade': round(self.expectancy_per_trade, 2),
            'average_holding_days': round(self.average_holding_days, 1),
            'max_consecutive_losses': self.max_consecutive_losses,
            'total_transaction_costs': round(self.total_transaction_costs, 2),
            'total_slippage_costs': round(self.total_slippage_costs, 2),
            'regime_performance': self.regime_performance,
            'trades': [t.to_dict() for t in self.trades],
            'equity_curve': self.equity_curve[-500:] if len(self.equity_curve) > 500 else self.equity_curve,
        }


# ==================== WALK-FORWARD RESULT ====================

@dataclass
class WalkForwardResult:
    """Results from walk-forward validation"""
    strategy_name: str
    n_folds: int
    in_sample_results: List[BacktestResult] = field(default_factory=list)
    out_sample_results: List[BacktestResult] = field(default_factory=list)
    aggregate_oos_return: float = 0.0
    aggregate_oos_sharpe: float = 0.0
    parameter_stability: Dict[str, float] = field(default_factory=dict)
    is_robust: bool = False  # True if OOS performance > 50% of IS performance

    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy_name': self.strategy_name,
            'n_folds': self.n_folds,
            'in_sample_summary': [
                {
                    'fold': i + 1,
                    'return_pct': round(r.total_return_pct, 2),
                    'sharpe': round(r.sharpe_ratio, 3),
                    'trades': r.total_trades,
                }
                for i, r in enumerate(self.in_sample_results)
            ],
            'out_sample_summary': [
                {
                    'fold': i + 1,
                    'return_pct': round(r.total_return_pct, 2),
                    'sharpe': round(r.sharpe_ratio, 3),
                    'trades': r.total_trades,
                }
                for i, r in enumerate(self.out_sample_results)
            ],
            'aggregate_oos_return': round(self.aggregate_oos_return, 2),
            'aggregate_oos_sharpe': round(self.aggregate_oos_sharpe, 3),
            'parameter_stability': {
                k: round(v, 4) for k, v in self.parameter_stability.items()
            },
            'is_robust': self.is_robust,
        }
