"""
Export Manager
==============
Generate CSV, JSON, and HTML report exports for all platform modules.

Supports export of: screener results, backtest results, risk metrics,
fundamental analysis, portfolio holdings, stock comparison reports,
and comprehensive HTML stock reports.

Version: 2.0.0
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import io
from typing import Dict, List, Optional, Any
import logging
import warnings

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


class ExportManager:
    """Manage data exports for screener results, backtests, risk, and reports."""

    @staticmethod
    def screener_to_csv(results: Any) -> str:
        """Export screener results to CSV string."""
        if results is None:
            return ""
        if isinstance(results, pd.DataFrame):
            if results.empty:
                return ""
            return results.to_csv(index=False)
        if isinstance(results, list):
            if not results:
                return ""
            return pd.DataFrame(results).to_csv(index=False)
        return ""

    @staticmethod
    def backtest_to_csv(backtest_result: Dict) -> str:
        """Export backtest results to CSV string."""
        if not backtest_result:
            return ""

        summary = {k: v for k, v in backtest_result.items()
                   if not isinstance(v, (pd.DataFrame, pd.Series, list, dict))}
        summary_df = pd.DataFrame([summary])

        output = io.StringIO()
        output.write("=== BACKTEST SUMMARY ===\n")
        summary_df.to_csv(output, index=False)

        trades = backtest_result.get("trades")
        if trades is not None:
            if isinstance(trades, pd.DataFrame) and not trades.empty:
                output.write("\n=== TRADE LOG ===\n")
                trades.to_csv(output, index=False)
            elif isinstance(trades, list) and trades:
                output.write("\n=== TRADE LOG ===\n")
                pd.DataFrame(trades).to_csv(output, index=False)

        return output.getvalue()

    @staticmethod
    def risk_metrics_to_csv(metrics: Dict) -> str:
        """Export risk metrics to CSV string."""
        if not metrics:
            return ""
        clean = {k: v for k, v in metrics.items()
                 if isinstance(v, (int, float, str, np.floating, np.integer))}
        return pd.DataFrame([clean]).to_csv(index=False)

    @staticmethod
    def fundamentals_to_csv(fundamentals: Dict) -> str:
        """Export fundamental analysis to CSV string."""
        if not fundamentals:
            return ""
        flat = {}
        for category, data in fundamentals.items():
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (int, float, str, type(None))):
                        flat[f"{category}_{k}"] = v
            elif isinstance(data, (int, float, str)):
                flat[category] = data
        return pd.DataFrame([flat]).to_csv(index=False)

    @staticmethod
    def comparison_to_csv(comparison: Any) -> str:
        """Export comparison data to CSV."""
        if comparison is None:
            return ""
        if isinstance(comparison, pd.DataFrame):
            return comparison.to_csv() if not comparison.empty else ""
        if isinstance(comparison, dict):
            return pd.DataFrame(comparison).T.to_csv()
        if isinstance(comparison, list):
            return pd.DataFrame(comparison).to_csv(index=False) if comparison else ""
        return ""

    @staticmethod
    def portfolio_to_csv(portfolio_data: Any) -> str:
        """Export portfolio holdings to CSV."""
        if not portfolio_data:
            return ""
        if isinstance(portfolio_data, list):
            return pd.DataFrame(portfolio_data).to_csv(index=False)
        if isinstance(portfolio_data, dict):
            return pd.DataFrame([portfolio_data]).to_csv(index=False)
        return ""

    @staticmethod
    def to_json(data: Any) -> str:
        """Export any data structure to JSON string."""
        def default_serializer(obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            if isinstance(obj, pd.DataFrame):
                return obj.to_dict(orient="records")
            if isinstance(obj, pd.Series):
                return obj.to_dict()
            if isinstance(obj, (datetime,)):
                return obj.isoformat()
            return str(obj)

        return json.dumps(data, default=default_serializer, indent=2)

    @staticmethod
    def generate_stock_report_html(symbol: str,
                                    analysis_data: Optional[Dict] = None,
                                    fundamentals: Optional[Dict] = None,
                                    technical: Optional[Dict] = None,
                                    risk_metrics: Optional[Dict] = None,
                                    prediction: Optional[Dict] = None) -> str:
        """
        Generate a comprehensive HTML report for a stock.

        Includes: Price overview, fundamental analysis, technical patterns,
        risk metrics, and AI prediction (if available).
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Intelligence Report - {symbol}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; max-width: 960px; margin: 0 auto; padding: 2rem; background: #0e1117; color: #e0e0e0; line-height: 1.6; }}
        h1 {{ color: #667eea; border-bottom: 2px solid #667eea; padding-bottom: 12px; margin-bottom: 1.5rem; font-size: 1.8em; }}
        h2 {{ color: #764ba2; margin-top: 2rem; margin-bottom: 1rem; font-size: 1.3em; }}
        h3 {{ color: #88a0d0; font-size: 1.1em; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #333; padding: 10px 14px; text-align: left; }}
        th {{ background: #1e2130; color: #667eea; font-weight: 600; }}
        tr:nth-child(even) {{ background: #161b22; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin: 1rem 0; }}
        .metric-card {{ background: #1e2130; padding: 1.2rem; border-radius: 10px; text-align: center; border: 1px solid #2a2e3d; }}
        .metric-value {{ font-size: 1.4em; font-weight: bold; color: #667eea; }}
        .metric-label {{ color: #888; font-size: 0.85em; margin-top: 4px; }}
        .bullish {{ color: #2ecc71; }} .bearish {{ color: #e74c3c; }} .neutral {{ color: #f39c12; }}
        .footer {{ text-align: center; margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid #333; color: #666; font-size: 0.85em; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.85em; font-weight: 600; }}
        .badge-buy {{ background: #1a4731; color: #2ecc71; }}
        .badge-sell {{ background: #4a1a1a; color: #e74c3c; }}
        .badge-hold {{ background: #4a3a1a; color: #f39c12; }}
        .section {{ margin-bottom: 2rem; }}
        .disclaimer {{ background: #1a1a2e; border-left: 4px solid #f39c12; padding: 1rem; margin: 1rem 0; border-radius: 4px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Stock Intelligence Report: {symbol}</h1>
    <p><strong>Generated:</strong> {timestamp} | <strong>Platform:</strong> Artha Drishti v5.0 — AI Stock Intelligence</p>
"""

        # ── Price & Technical Overview ──
        if analysis_data:
            price = analysis_data.get('current_price', 'N/A')
            mcap = analysis_data.get('market_cap', 'N/A')
            pe = analysis_data.get('pe_ratio', 'N/A')
            rsi = analysis_data.get('rsi', 'N/A')
            day_range = analysis_data.get('day_range', 'N/A')
            prev_close = analysis_data.get('prev_close', 'N/A')
            range_52w = analysis_data.get('52w_range', 'N/A')
            dividend = analysis_data.get('dividend_yield', 'N/A')
            company = analysis_data.get('company_name', symbol)
            sector = analysis_data.get('sector', 'N/A')
            industry = analysis_data.get('industry', 'N/A')
            html += f"""
    <div class="section">
    <h2>Price &amp; Technical Overview</h2>
    <p style="color: #888; margin-bottom: 1rem;">{company} • {sector} / {industry}</p>
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-label">Current Price</div><div class="metric-value">{price}</div></div>
        <div class="metric-card"><div class="metric-label">Market Cap</div><div class="metric-value">{mcap}</div></div>
        <div class="metric-card"><div class="metric-label">P/E Ratio</div><div class="metric-value">{pe}</div></div>
        <div class="metric-card"><div class="metric-label">RSI (14)</div><div class="metric-value">{rsi}</div></div>
        <div class="metric-card"><div class="metric-label">Prev Close</div><div class="metric-value">{prev_close}</div></div>
        <div class="metric-card"><div class="metric-label">Day Range</div><div class="metric-value" style="font-size:0.9em;">{day_range}</div></div>
        <div class="metric-card"><div class="metric-label">52-Week Range</div><div class="metric-value" style="font-size:0.9em;">{range_52w}</div></div>
        <div class="metric-card"><div class="metric-label">Dividend Yield</div><div class="metric-value">{dividend}</div></div>
    </div>
    </div>
"""

        # ── AI Prediction ──
        if prediction:
            signal = prediction.get('signal', 'N/A')
            confidence = prediction.get('confidence', 'N/A')
            target = prediction.get('target_price', 'N/A')
            stoploss = prediction.get('stoploss', 'N/A')
            predicted_5d = prediction.get('predicted_price_5d', 'N/A')
            expected_return = prediction.get('predicted_return_pct', 'N/A')
            rr_ratio = prediction.get('risk_reward_ratio', 'N/A')
            direction_prob = prediction.get('direction_probability', 'N/A')
            badge_class = ('badge-buy' if signal in ('BUY', 'STRONG_BUY')
                          else ('badge-sell' if signal in ('SELL', 'STRONG_SELL')
                                else 'badge-hold'))
            html += f"""
    <div class="section">
    <h2>AI Prediction</h2>
    <div class="metric-grid">
        <div class="metric-card"><div class="metric-label">Signal</div><div class="metric-value"><span class="badge {badge_class}">{signal}</span></div></div>
        <div class="metric-card"><div class="metric-label">Confidence</div><div class="metric-value">{confidence}{'%' if isinstance(confidence, (int, float)) else ''}</div></div>
        <div class="metric-card"><div class="metric-label">5-Day Target</div><div class="metric-value">{predicted_5d}</div></div>
        <div class="metric-card"><div class="metric-label">Expected Return</div><div class="metric-value">{expected_return}</div></div>
        <div class="metric-card"><div class="metric-label">Target Price</div><div class="metric-value">{target}</div></div>
        <div class="metric-card"><div class="metric-label">Stop Loss</div><div class="metric-value">{stoploss}</div></div>
        <div class="metric-card"><div class="metric-label">Risk/Reward</div><div class="metric-value">{rr_ratio}</div></div>
        <div class="metric-card"><div class="metric-label">Direction Prob.</div><div class="metric-value">{direction_prob}{'%' if isinstance(direction_prob, (int, float)) else ''}</div></div>
    </div>
    </div>
"""

        # ── Fundamental Analysis ──
        if fundamentals:
            val = fundamentals.get("valuation", {})
            prof = fundamentals.get("profitability", {})
            health = fundamentals.get("financial_health", {})
            html += """
    <div class="section">
    <h2>Fundamental Analysis</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Assessment</th></tr>
"""
            metrics_list = [
                ("P/E Ratio", val.get("pe_ratio"), "pe"),
                ("P/B Ratio", val.get("pb_ratio"), "pb"),
                ("EV/EBITDA", val.get("ev_ebitda"), "ev"),
                ("ROE", prof.get("roe"), "roe"),
                ("Profit Margin", prof.get("profit_margin"), "margin"),
                ("Debt/Equity", health.get("debt_to_equity"), "de"),
                ("Current Ratio", health.get("current_ratio"), "cr"),
            ]
            for label, value, metric_type in metrics_list:
                if value is not None:
                    display = f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
                    assessment = ExportManager._assess_metric(metric_type, value)
                    css_class = ("bullish" if "Good" in assessment or "Strong" in assessment
                                else ("bearish" if "Weak" in assessment or "High" in assessment
                                      else "neutral"))
                    html += f'        <tr><td>{label}</td><td>{display}</td><td class="{css_class}">{assessment}</td></tr>\n'
            html += "    </table>\n    </div>\n"

        # ── Technical Patterns ──
        if technical:
            patterns = technical.get("patterns_detected", technical.get("chart_patterns", []))
            if patterns:
                html += '    <div class="section">\n    <h2>Technical Patterns Detected</h2>\n'
                for p in patterns:
                    if isinstance(p, dict):
                        name = p.get("pattern", p.get("name", ""))
                        signal = p.get("signal", p.get("direction", ""))
                        conf = p.get("confidence", "")
                        css = ("bullish" if "Bull" in str(signal)
                               else ("bearish" if "Bear" in str(signal) else "neutral"))
                        html += f'    <p><strong>{name}</strong> — <span class="{css}">{signal}</span>'
                        if conf:
                            html += f' (Confidence: {conf}%)'
                        html += '</p>\n'
                html += "    </div>\n"

        # ── Risk Metrics ──
        if risk_metrics:
            html += '    <div class="section">\n    <h2>Risk Metrics</h2>\n    <div class="metric-grid">\n'
            risk_display = [
                ("Sharpe Ratio", "sharpe_ratio"),
                ("Sortino Ratio", "sortino_ratio"),
                ("Max Drawdown", "max_drawdown"),
                ("VaR 95%", "var_95_historical"),
                ("Beta", "beta"),
                ("Volatility", "annualized_volatility"),
                ("CAGR", "cagr"),
                ("Calmar Ratio", "calmar_ratio"),
            ]
            for label, key in risk_display:
                v = risk_metrics.get(key)
                if v is not None:
                    display = f"{v:.3f}" if isinstance(v, float) else str(v)
                    html += f'        <div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{display}</div></div>\n'
            html += "    </div>\n    </div>\n"

        # ── Disclaimer & Footer ──
        html += f"""
    <div class="disclaimer">
        <strong>Disclaimer:</strong> This report is generated by an AI-powered system for
        informational and educational purposes only. It does not constitute financial advice.
        Always consult a qualified financial advisor before making investment decisions.
        Past performance does not guarantee future results.
    </div>
    <div class="footer">
        <p>Generated by <strong>Artha Drishti v5.0</strong> — AI-Powered Stock Intelligence Platform</p>
        <p>{timestamp} | Patent-Pending Technology</p>
    </div>
</body>
</html>
"""
        return html

    @staticmethod
    def _assess_metric(metric_type: str, value: float) -> str:
        """Generate qualitative assessment for a metric value."""
        if value is None:
            return "N/A"
        try:
            if metric_type == "pe":
                if value < 15: return "Good — Undervalued"
                if value < 25: return "Fair"
                if value < 40: return "High"
                return "Weak — Overvalued"
            elif metric_type == "pb":
                if value < 1.5: return "Good — Undervalued"
                if value < 3: return "Fair"
                return "High"
            elif metric_type == "ev":
                if value < 10: return "Good"
                if value < 15: return "Fair"
                return "High"
            elif metric_type == "roe":
                pct = value * 100 if abs(value) < 1 else value
                if pct > 20: return "Strong"
                if pct > 10: return "Good"
                return "Weak"
            elif metric_type == "margin":
                pct = value * 100 if abs(value) < 1 else value
                if pct > 15: return "Strong"
                if pct > 5: return "Good"
                return "Weak"
            elif metric_type == "de":
                if value < 50: return "Strong — Low Debt"
                if value < 100: return "Fair"
                return "High Risk"
            elif metric_type == "cr":
                if value > 2: return "Strong"
                if value > 1: return "Fair"
                return "Weak"
        except Exception:
            pass
        return "N/A"


# ============================================================================
# MODULE-LEVEL SINGLETON
# ============================================================================

_export_manager: Optional[ExportManager] = None


def get_export_manager() -> ExportManager:
    """Get or create the singleton ExportManager."""
    global _export_manager
    if _export_manager is None:
        _export_manager = ExportManager()
    return _export_manager
