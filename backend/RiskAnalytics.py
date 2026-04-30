"""
Advanced Risk Analytics Engine (ARAE)
======================================
Patent-Pending Component: Comprehensive Risk Quantification Framework
with Portfolio Optimization via Monte Carlo Efficient Frontier.

Core Innovations:
- 30+ risk metrics across 7 categories (returns, volatility, risk-adjusted,
  drawdown, VaR, tail risk, benchmark-relative)
- Portfolio-level risk decomposition with Component VaR and Diversification Ratio
- Monte Carlo Efficient Frontier with max-Sharpe and min-volatility portfolio identification
  using Dirichlet-distributed random weights
- Multi-criteria stock ranking with composite scoring

Version: 2.0.0
Integrated from: BTP SEM-5 RiskAnalytics into Project sem-6 architecture
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Optional, Any
import logging
import warnings

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


def _strip_tz(series_or_df):
    """Remove timezone info from DatetimeIndex to avoid tz-naive vs tz-aware join errors."""
    if series_or_df is None:
        return series_or_df
    if hasattr(series_or_df, 'index') and hasattr(series_or_df.index, 'tz') and series_or_df.index.tz is not None:
        series_or_df = series_or_df.copy()
        series_or_df.index = series_or_df.index.tz_localize(None)
    return series_or_df


# ============================================================================
# RISK METRICS CALCULATOR (Patent-Pending)
# ============================================================================

class RiskAnalytics:
    """
    Calculate 30+ risk metrics for stocks and portfolios across 7 categories:
    Returns, Volatility, Risk-Adjusted, Drawdown, VaR, Tail Risk, and
    Benchmark-Relative metrics.
    """

    def __init__(self, risk_free_rate: float = 0.06):
        """
        Args:
            risk_free_rate: Annual risk-free rate (default 6% for India/RBI rate).
        """
        self.risk_free_rate = risk_free_rate

    @staticmethod
    def _ensure_series(df_or_series, col: str = "Close") -> Optional[pd.Series]:
        """Ensure data is a 1-D pandas Series (handles multi-level columns from yf.download)."""
        if df_or_series is None:
            return None
        if isinstance(df_or_series, pd.Series):
            return _strip_tz(df_or_series)
        if isinstance(df_or_series, pd.DataFrame):
            if isinstance(df_or_series.columns, pd.MultiIndex):
                df_or_series = df_or_series.copy()
                df_or_series.columns = df_or_series.columns.get_level_values(0)
            if col in df_or_series.columns:
                s = df_or_series[col]
                if isinstance(s, pd.DataFrame):
                    return _strip_tz(s.iloc[:, 0])
                return _strip_tz(s)
            return _strip_tz(df_or_series.iloc[:, 0])
        return _strip_tz(pd.Series(df_or_series))

    def compute_all_metrics(self, df, benchmark_df=None) -> Optional[Dict]:
        """Compute all 30+ risk metrics for a stock."""
        if df is None or len(df) < 30:
            return None

        close = self._ensure_series(df, "Close")
        if close is None or len(close) < 30:
            return None

        returns = close.pct_change().dropna()

        metrics = {}
        metrics.update(self._return_metrics(returns))
        metrics.update(self._volatility_metrics(returns))
        metrics.update(self._risk_adjusted_metrics(returns))
        metrics.update(self._drawdown_metrics(close))
        metrics.update(self._var_metrics(returns))
        metrics.update(self._tail_risk_metrics(returns))

        if benchmark_df is not None and len(benchmark_df) > 30:
            bench_close = self._ensure_series(benchmark_df, "Close")
            if bench_close is not None and len(bench_close) > 30:
                bench_returns = bench_close.pct_change().dropna()
                metrics.update(self._relative_metrics(returns, bench_returns))

        return metrics

    # ── Return Metrics ──

    def _return_metrics(self, returns: pd.Series) -> Dict:
        """Calculate return-based metrics."""
        ann_return = returns.mean() * 252
        total_return = (1 + returns).prod() - 1
        cagr = (1 + total_return) ** (252 / max(len(returns), 1)) - 1

        monthly_returns = returns.groupby(pd.Grouper(freq="ME")).sum()
        positive_months = int((monthly_returns > 0).sum())
        negative_months = int((monthly_returns < 0).sum())
        total_months = len(monthly_returns)

        return {
            "annualized_return": round(ann_return * 100, 2),
            "total_return": round(total_return * 100, 2),
            "cagr": round(cagr * 100, 2),
            "best_day": round(float(returns.max()) * 100, 2),
            "worst_day": round(float(returns.min()) * 100, 2),
            "avg_daily_return": round(returns.mean() * 100, 4),
            "positive_days_pct": round((returns > 0).mean() * 100, 1),
            "positive_months": positive_months,
            "negative_months": negative_months,
            "win_rate": round(positive_months / max(total_months, 1) * 100, 1),
        }

    # ── Volatility Metrics ──

    def _volatility_metrics(self, returns: pd.Series) -> Dict:
        """Calculate volatility-based metrics."""
        daily_vol = returns.std()
        ann_vol = daily_vol * np.sqrt(252)

        vol_20d = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
        vol_60d = (returns.rolling(60).std().iloc[-1] * np.sqrt(252)
                   if len(returns) > 60 else ann_vol)

        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        upside_returns = returns[returns > 0]
        upside_vol = upside_returns.std() * np.sqrt(252) if len(upside_returns) > 0 else 0

        return {
            "daily_volatility": round(daily_vol * 100, 2),
            "annualized_volatility": round(ann_vol * 100, 2),
            "volatility_20d": round(float(vol_20d) * 100, 2),
            "volatility_60d": round(float(vol_60d) * 100, 2),
            "downside_volatility": round(downside_vol * 100, 2),
            "upside_volatility": round(upside_vol * 100, 2),
            "upside_downside_ratio": round(
                upside_vol / downside_vol if downside_vol > 0 else float("inf"), 2
            ),
        }

    # ── Risk-Adjusted Metrics ──

    def _risk_adjusted_metrics(self, returns: pd.Series) -> Dict:
        """Calculate risk-adjusted performance metrics."""
        excess = returns.mean() * 252 - self.risk_free_rate
        vol = returns.std() * np.sqrt(252)

        sharpe = excess / vol if vol > 0 else 0

        downside = returns[returns < 0]
        downside_std = downside.std() * np.sqrt(252) if len(downside) > 0 else 0.001
        sortino = excess / downside_std if downside_std > 0 else 0

        prices = (1 + returns).cumprod()
        peak = prices.expanding(min_periods=1).max()
        drawdown = (prices - peak) / peak
        max_dd = abs(drawdown.min())
        ann_return = returns.mean() * 252
        calmar = ann_return / max_dd if max_dd > 0 else 0

        return {
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "calmar_ratio": round(calmar, 3),
        }

    # ── Drawdown Metrics ──

    def _drawdown_metrics(self, prices: pd.Series) -> Dict:
        """Calculate drawdown-related metrics."""
        peak = prices.expanding(min_periods=1).max()
        drawdown = (prices - peak) / peak
        max_dd = drawdown.min()
        current_dd = drawdown.iloc[-1]

        in_drawdown = drawdown < 0
        dd_groups = (~in_drawdown).cumsum()
        if in_drawdown.any():
            dd_durations = in_drawdown.groupby(dd_groups).sum()
            max_dd_duration = int(dd_durations.max())
            dd_nonzero = dd_durations[dd_durations > 0]
            avg_dd_duration = float(dd_nonzero.mean()) if len(dd_nonzero) > 0 else 0
        else:
            max_dd_duration = 0
            avg_dd_duration = 0

        max_dd_idx = drawdown.idxmin()
        recovery_data = drawdown.loc[max_dd_idx:]
        recovered = recovery_data[recovery_data >= 0]
        recovery_days = (recovered.index[0] - max_dd_idx).days if len(recovered) > 0 else None

        return {
            "max_drawdown": round(float(max_dd) * 100, 2),
            "current_drawdown": round(float(current_dd) * 100, 2),
            "max_drawdown_duration": max_dd_duration,
            "avg_drawdown_duration": round(avg_dd_duration, 1),
            "recovery_days": recovery_days,
        }

    # ── Value at Risk ──

    def _var_metrics(self, returns: pd.Series,
                      confidence_levels: Optional[List[float]] = None) -> Dict:
        """Calculate VaR (Historical, Parametric) and CVaR / Expected Shortfall."""
        if confidence_levels is None:
            confidence_levels = [0.95, 0.99]

        var_results = {}
        for cl in confidence_levels:
            cln = int(cl * 100)

            # Historical VaR
            var_hist = np.percentile(returns, (1 - cl) * 100)
            var_results[f"var_{cln}_historical"] = round(float(var_hist) * 100, 3)

            # Parametric VaR (normal distribution assumption)
            z_score = stats.norm.ppf(1 - cl)
            var_param = (returns.mean() + z_score * returns.std())
            var_results[f"var_{cln}_parametric"] = round(float(var_param) * 100, 3)

            # Conditional VaR (Expected Shortfall)
            threshold = np.percentile(returns, (1 - cl) * 100)
            tail = returns[returns <= threshold]
            cvar = tail.mean() if len(tail) > 0 else threshold
            var_results[f"cvar_{cln}"] = round(float(cvar) * 100, 3)

        return var_results

    # ── Tail Risk ──

    def _tail_risk_metrics(self, returns: pd.Series) -> Dict:
        """Calculate tail risk metrics (skewness, kurtosis, tail ratio)."""
        skewness = returns.skew()
        kurtosis = returns.kurtosis()

        pct_95 = np.percentile(returns, 95)
        pct_5 = abs(np.percentile(returns, 5))
        tail_ratio = abs(pct_95 / pct_5) if pct_5 > 0 else 0

        return {
            "skewness": round(float(skewness), 3),
            "kurtosis": round(float(kurtosis), 3),
            "tail_ratio": round(float(tail_ratio), 3),
        }

    # ── Benchmark-Relative Metrics ──

    def _relative_metrics(self, returns: pd.Series,
                           benchmark_returns: pd.Series) -> Dict:
        """Calculate benchmark-relative metrics (Beta, Alpha, Treynor, etc.)."""
        returns = _strip_tz(returns)
        benchmark_returns = _strip_tz(benchmark_returns)

        combined = pd.DataFrame({
            "stock": returns, "benchmark": benchmark_returns
        }).dropna()

        if len(combined) < 30:
            return {}

        stock_ret = combined["stock"]
        bench_ret = combined["benchmark"]

        # Beta
        covariance = np.cov(stock_ret, bench_ret)[0][1]
        bench_var = bench_ret.var()
        beta = covariance / bench_var if bench_var > 0 else 1

        # Alpha (Jensen's)
        stock_ann = stock_ret.mean() * 252
        bench_ann = bench_ret.mean() * 252
        alpha = stock_ann - (self.risk_free_rate + beta * (bench_ann - self.risk_free_rate))

        # Treynor
        excess = stock_ann - self.risk_free_rate
        treynor = excess / beta if beta != 0 else 0

        # Information Ratio
        active_returns = stock_ret - bench_ret
        tracking_error = active_returns.std() * np.sqrt(252)
        information_ratio = (active_returns.mean() * 252 / tracking_error
                             if tracking_error > 0 else 0)

        # Up/Down Capture
        up_market = bench_ret > 0
        down_market = bench_ret < 0
        up_capture = (stock_ret[up_market].mean() / bench_ret[up_market].mean() * 100
                      if bench_ret[up_market].mean() != 0 else 0)
        down_capture = (stock_ret[down_market].mean() / bench_ret[down_market].mean() * 100
                        if bench_ret[down_market].mean() != 0 else 0)

        # R-squared
        correlation = stock_ret.corr(bench_ret)
        r_squared = correlation ** 2

        return {
            "beta": round(float(beta), 3),
            "alpha": round(float(alpha) * 100, 2),
            "treynor_ratio": round(float(treynor), 3),
            "information_ratio": round(float(information_ratio), 3),
            "tracking_error": round(float(tracking_error) * 100, 2),
            "up_capture": round(float(up_capture), 1),
            "down_capture": round(float(down_capture), 1),
            "r_squared": round(float(r_squared) * 100, 1),
            "correlation_with_benchmark": round(float(correlation), 3),
        }


# ============================================================================
# PORTFOLIO RISK ANALYZER (Patent-Pending)
# ============================================================================

class PortfolioRiskAnalyzer:
    """
    Portfolio-level risk analysis with:
    - Weighted portfolio return/volatility/Sharpe
    - Diversification Ratio
    - Component VaR decomposition
    - Marginal risk contribution
    - Correlation & covariance matrices
    - Monte Carlo Efficient Frontier
    """

    def __init__(self, risk_free_rate: float = 0.06):
        self.risk_analytics = RiskAnalytics(risk_free_rate)

    def analyze_portfolio_risk(self, stock_data_dict: Dict[str, pd.DataFrame],
                                weights: Optional[Dict[str, float]] = None) -> Optional[Dict]:
        """
        Analyze portfolio risk.

        Args:
            stock_data_dict: {symbol: DataFrame with 'Close' column}
            weights: {symbol: weight} summing to 1. Defaults to equal weight.
        """
        if not stock_data_dict:
            return None

        symbols = list(stock_data_dict.keys())

        if weights is None:
            equal_weight = 1.0 / len(symbols)
            weights = {s: equal_weight for s in symbols}

        # Build returns matrix
        returns_dict = {}
        for symbol, df in stock_data_dict.items():
            if df is not None and len(df) > 30:
                close = RiskAnalytics._ensure_series(df, "Close")
                if close is not None:
                    returns_dict[symbol] = _strip_tz(close.pct_change().dropna())

        if len(returns_dict) < 2:
            return None

        returns_df = pd.DataFrame(returns_dict).dropna()
        w = np.array([weights.get(s, 0) for s in returns_df.columns])

        # Portfolio returns
        portfolio_returns = (returns_df * w).sum(axis=1)

        # Correlation & covariance
        corr_matrix = returns_df.corr()
        cov_matrix = returns_df.cov() * 252

        # Portfolio variance and volatility
        portfolio_var = np.dot(w, np.dot(cov_matrix, w))
        portfolio_vol = np.sqrt(portfolio_var)

        # Portfolio Sharpe
        portfolio_ann_return = portfolio_returns.mean() * 252
        portfolio_sharpe = ((portfolio_ann_return - self.risk_analytics.risk_free_rate) /
                            portfolio_vol if portfolio_vol > 0 else 0)

        # Diversification ratio
        weighted_vol = sum(w[i] * returns_df.iloc[:, i].std() * np.sqrt(252)
                          for i in range(len(w)))
        diversification_ratio = weighted_vol / portfolio_vol if portfolio_vol > 0 else 1

        # Marginal contribution to risk
        marginal_contrib = (np.dot(cov_matrix, w) / portfolio_vol
                           if portfolio_vol > 0 else np.zeros(len(w)))

        # Component VaR
        z_95 = stats.norm.ppf(0.05)
        portfolio_var_95 = -(portfolio_returns.mean() + z_95 * portfolio_returns.std())
        component_var = {
            s: round(float(w[i] * marginal_contrib[i] * z_95), 6)
            for i, s in enumerate(returns_df.columns)
        }

        # Individual metrics (without series data for JSON serialization)
        individual_metrics = {}
        for s in symbols:
            if s in stock_data_dict and stock_data_dict[s] is not None:
                m = self.risk_analytics.compute_all_metrics(stock_data_dict[s])
                if m:
                    individual_metrics[s] = {k: v for k, v in m.items()
                                              if not isinstance(v, (pd.Series, pd.DataFrame))}

        return {
            "portfolio_return": round(float(portfolio_ann_return) * 100, 2),
            "portfolio_volatility": round(float(portfolio_vol) * 100, 2),
            "portfolio_sharpe": round(float(portfolio_sharpe), 3),
            "diversification_ratio": round(float(diversification_ratio), 3),
            "correlation_matrix": corr_matrix.round(3).to_dict(),
            "marginal_risk_contribution": {
                s: round(float(marginal_contrib[i]), 6)
                for i, s in enumerate(returns_df.columns)
            },
            "portfolio_var_95": round(float(portfolio_var_95) * 100, 3),
            "component_var": component_var,
            "individual_metrics": individual_metrics,
        }

    def efficient_frontier(self, stock_data_dict: Dict[str, pd.DataFrame],
                            n_portfolios: int = 5000) -> Optional[Dict]:
        """
        Generate Monte Carlo Efficient Frontier.

        Uses Dirichlet-distributed random weights to generate n_portfolios
        random portfolios and identify max-Sharpe and min-volatility portfolios.
        """
        returns_dict = {}
        for s, df in stock_data_dict.items():
            if df is not None and len(df) > 30:
                close = RiskAnalytics._ensure_series(df, "Close")
                if close is not None:
                    returns_dict[s] = _strip_tz(close.pct_change().dropna())

        returns_df = pd.DataFrame(returns_dict).dropna()
        n = len(returns_df.columns)
        if n < 2:
            return None

        mean_returns = returns_df.mean() * 252
        cov_matrix = returns_df.cov() * 252

        results = []
        for _ in range(n_portfolios):
            w = np.random.dirichlet(np.ones(n))
            ret = np.dot(w, mean_returns)
            vol = np.sqrt(np.dot(w, np.dot(cov_matrix, w)))
            sharpe = ((ret - self.risk_analytics.risk_free_rate) / vol) if vol > 0 else 0
            results.append({
                "return": round(float(ret) * 100, 2),
                "volatility": round(float(vol) * 100, 2),
                "sharpe": round(float(sharpe), 3),
                "weights": {s: round(float(w[i]), 4)
                           for i, s in enumerate(returns_df.columns)},
            })

        results_df = pd.DataFrame(results)

        # Optimal portfolios
        max_sharpe_idx = results_df["sharpe"].idxmax()
        min_vol_idx = results_df["volatility"].idxmin()

        return {
            "portfolios": results_df.to_dict(orient="records"),
            "max_sharpe_portfolio": results_df.iloc[max_sharpe_idx].to_dict(),
            "min_volatility_portfolio": results_df.iloc[min_vol_idx].to_dict(),
            "num_assets": n,
            "asset_names": list(returns_df.columns),
        }


# ============================================================================
# STOCK COMPARATOR
# ============================================================================

class StockComparator:
    """Compare and rank multiple stocks by composite risk-adjusted metrics."""

    def __init__(self, risk_free_rate: float = 0.06):
        self.risk_analytics = RiskAnalytics(risk_free_rate)

    def compare(self, stock_data_dict: Dict[str, pd.DataFrame],
                benchmark_df=None) -> Dict:
        """Compare multiple stocks on risk metrics."""
        comparison = {}
        for symbol, df in stock_data_dict.items():
            if df is None or len(df) < 30:
                continue
            try:
                metrics = self.risk_analytics.compute_all_metrics(df, benchmark_df)
                if metrics:
                    clean = {k: v for k, v in metrics.items()
                             if not isinstance(v, (pd.Series, pd.DataFrame))}
                    comparison[symbol] = clean
            except Exception:
                pass
        return comparison

    def rank_stocks(self, comparison: Dict,
                     criteria: Optional[Dict] = None) -> List[Dict]:
        """
        Rank stocks by multiple weighted criteria.

        Default criteria weights:
        - Sharpe Ratio: 30%, higher is better
        - Sortino Ratio: 20%, higher is better
        - Max Drawdown: 20%, less negative is better
        - Annualized Return: 15%, higher is better
        - Volatility: 15%, lower is better
        """
        if not comparison:
            return []

        if criteria is None:
            criteria = {
                "sharpe_ratio": {"weight": 0.3, "ascending": False},
                "sortino_ratio": {"weight": 0.2, "ascending": False},
                "max_drawdown": {"weight": 0.2, "ascending": True},
                "annualized_return": {"weight": 0.15, "ascending": False},
                "annualized_volatility": {"weight": 0.15, "ascending": True},
            }

        df = pd.DataFrame(comparison).T
        if df.empty:
            return []

        rank_scores = pd.Series(0.0, index=df.index)
        for metric, params in criteria.items():
            if metric in df.columns:
                ranked = df[metric].rank(ascending=params["ascending"])
                rank_scores += ranked * params["weight"]

        df["composite_rank_score"] = rank_scores
        df = df.sort_values("composite_rank_score", ascending=False)

        result = []
        for symbol, row in df.iterrows():
            entry = {"symbol": symbol}
            entry.update({k: (round(v, 3) if isinstance(v, float) else v)
                         for k, v in row.items()})
            result.append(entry)
        return result


# ============================================================================
# MODULE-LEVEL SINGLETONS
# ============================================================================

_risk_analytics: Optional[RiskAnalytics] = None
_portfolio_analyzer: Optional[PortfolioRiskAnalyzer] = None
_comparator: Optional[StockComparator] = None


def get_risk_analytics() -> RiskAnalytics:
    global _risk_analytics
    if _risk_analytics is None:
        _risk_analytics = RiskAnalytics()
    return _risk_analytics


def get_portfolio_analyzer() -> PortfolioRiskAnalyzer:
    global _portfolio_analyzer
    if _portfolio_analyzer is None:
        _portfolio_analyzer = PortfolioRiskAnalyzer()
    return _portfolio_analyzer


def get_stock_comparator() -> StockComparator:
    global _comparator
    if _comparator is None:
        _comparator = StockComparator()
    return _comparator
