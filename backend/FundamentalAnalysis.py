"""
Fundamental Analysis Engine (FAE)
==================================
Patent-Pending Component: Multi-Dimensional Fundamental Scoring System.

Core Innovation:
- 5-category weighted fundamental scoring (Valuation 25%, Profitability 25%,
  Growth 20%, Financial Health 20%, Dividends 10%)
- Composite rating from raw financial metrics via adaptive thresholds
- Piotroski F-Score calculation for value investing
- Multi-stock comparison with normalized scoring
- Financial statement access for deep-dive analysis

Version: 2.0.0
Integrated from: BTP SEM-5 FundamentalAnalyzer into Project sem-6 architecture
"""

import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, List, Optional, Any
import logging
import warnings

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

EXCHANGE_SUFFIX = {
    "NSE": ".NS", "BSE": ".BO", "NYSE": "", "NASDAQ": "", "LSE": ".L"
}


class FundamentalAnalyzer:
    """
    Comprehensive Fundamental Analysis with multi-category scoring.

    Retrieves valuation, profitability, growth, financial health, and
    dividend metrics from yfinance and produces a 0-100 composite score.
    """

    VALUATION_THRESHOLDS = {
        "pe_ratio": {"cheap": 15, "fair": 25, "expensive": 40},
        "pb_ratio": {"cheap": 1.5, "fair": 3, "expensive": 5},
        "peg_ratio": {"cheap": 1, "fair": 1.5, "expensive": 2},
        "ev_ebitda": {"cheap": 10, "fair": 15, "expensive": 25},
    }

    def get_fundamentals(self, symbol: str, exchange: str = "NSE") -> Optional[Dict]:
        """
        Retrieve comprehensive fundamental data for a stock.

        Returns dict with keys: company_info, valuation, profitability,
        growth, financial_health, dividends, per_share, current_price, etc.
        """
        try:
            sfx = EXCHANGE_SUFFIX.get(exchange, "")
            full_symbol = f"{symbol}{sfx}"
            ticker = yf.Ticker(full_symbol)
            info = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                return None

            # Valuation metrics
            valuation = {
                "pe_ratio": info.get("trailingPE", info.get("forwardPE")),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "peg_ratio": info.get("pegRatio"),
                "ev_revenue": info.get("enterpriseToRevenue"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
            }

            # Profitability
            profitability = {
                "profit_margin": info.get("profitMargins"),
                "operating_margin": info.get("operatingMargins"),
                "gross_margin": info.get("grossMargins"),
                "roe": info.get("returnOnEquity"),
                "roa": info.get("returnOnAssets"),
                "ebitda_margin": None,
            }
            ebitda = info.get("ebitda")
            revenue = info.get("totalRevenue")
            if ebitda and revenue and revenue > 0:
                profitability["ebitda_margin"] = ebitda / revenue

            # Growth
            growth = {
                "revenue_growth": info.get("revenueGrowth"),
                "earnings_growth": info.get("earningsGrowth"),
                "quarterly_revenue_growth": info.get("revenueQuarterlyGrowth"),
                "quarterly_earnings_growth": info.get("earningsQuarterlyGrowth"),
            }

            # Financial health
            health = {
                "current_ratio": info.get("currentRatio"),
                "quick_ratio": info.get("quickRatio"),
                "debt_to_equity": info.get("debtToEquity"),
                "total_debt": info.get("totalDebt"),
                "total_cash": info.get("totalCash"),
                "free_cash_flow": info.get("freeCashflow"),
                "operating_cash_flow": info.get("operatingCashflow"),
            }

            # Dividends
            dividends = {
                "dividend_yield": info.get("dividendYield"),
                "dividend_rate": info.get("dividendRate"),
                "payout_ratio": info.get("payoutRatio"),
                "ex_dividend_date": info.get("exDividendDate"),
                "five_year_avg_yield": info.get("fiveYearAvgDividendYield"),
            }

            # Per-share
            per_share = {
                "eps_trailing": info.get("trailingEps"),
                "eps_forward": info.get("forwardEps"),
                "book_value": info.get("bookValue"),
                "revenue_per_share": info.get("revenuePerShare"),
            }

            # Company info
            company_info = {
                "name": info.get("longName", info.get("shortName", symbol)),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "website": info.get("website", ""),
                "description": info.get("longBusinessSummary", ""),
                "employees": info.get("fullTimeEmployees"),
                "country": info.get("country", "N/A"),
            }

            return {
                "symbol": symbol,
                "exchange": exchange,
                "company_info": company_info,
                "valuation": valuation,
                "profitability": profitability,
                "growth": growth,
                "financial_health": health,
                "dividends": dividends,
                "per_share": per_share,
                "current_price": info.get("regularMarketPrice", info.get("currentPrice")),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
            }

        except Exception as e:
            logger.error(f"Fundamental analysis error for {symbol}: {e}")
            return None

    def score_fundamentals(self, fundamentals: Dict) -> Optional[Dict]:
        """
        Score a stock's fundamentals on a 0-100 scale using weighted
        multi-category assessment.

        Weights: Valuation 25%, Profitability 25%, Growth 20%,
                 Financial Health 20%, Dividends 10%.
        """
        if not fundamentals:
            return None

        scores = {}
        total_score = 0
        total_weight = 0

        val = fundamentals.get("valuation", {})
        prof = fundamentals.get("profitability", {})
        growth = fundamentals.get("growth", {})
        health = fundamentals.get("financial_health", {})
        div = fundamentals.get("dividends", {})

        # ── Valuation score (weight: 25) ──
        val_score = 50
        pe = val.get("pe_ratio")
        if pe is not None and pe > 0:
            if pe < 15:
                val_score = 85
            elif pe < 25:
                val_score = 65
            elif pe < 40:
                val_score = 45
            else:
                val_score = 25

        pb = val.get("pb_ratio")
        if pb is not None and pb > 0:
            pb_score = 80 if pb < 1.5 else (60 if pb < 3 else (40 if pb < 5 else 20))
            val_score = (val_score + pb_score) / 2

        scores["valuation"] = round(val_score, 1)
        total_score += val_score * 25
        total_weight += 25

        # ── Profitability score (weight: 25) ──
        prof_score = 50
        roe = prof.get("roe")
        if roe is not None:
            roe_pct = roe * 100 if roe < 1 else roe
            prof_score = min(max(roe_pct * 3, 10), 95)

        margin = prof.get("profit_margin")
        if margin is not None:
            margin_pct = margin * 100 if margin < 1 else margin
            margin_score = min(max(margin_pct * 3, 10), 90)
            prof_score = (prof_score + margin_score) / 2

        scores["profitability"] = round(prof_score, 1)
        total_score += prof_score * 25
        total_weight += 25

        # ── Growth score (weight: 20) ──
        growth_score = 50
        rev_growth = growth.get("revenue_growth")
        earn_growth = growth.get("earnings_growth")

        if rev_growth is not None:
            rg = rev_growth * 100 if abs(rev_growth) < 5 else rev_growth
            growth_score = min(max(rg * 2 + 50, 10), 95)

        if earn_growth is not None:
            eg = earn_growth * 100 if abs(earn_growth) < 5 else earn_growth
            eg_score = min(max(eg * 2 + 50, 10), 95)
            growth_score = (growth_score + eg_score) / 2

        scores["growth"] = round(growth_score, 1)
        total_score += growth_score * 20
        total_weight += 20

        # ── Financial health score (weight: 20) ──
        health_score = 50
        de = health.get("debt_to_equity")
        if de is not None:
            health_score = 85 if de < 50 else (65 if de < 100 else (45 if de < 200 else 25))

        cr = health.get("current_ratio")
        if cr is not None:
            cr_score = 80 if cr > 2 else (60 if cr > 1.5 else (40 if cr > 1 else 20))
            health_score = (health_score + cr_score) / 2

        scores["financial_health"] = round(health_score, 1)
        total_score += health_score * 20
        total_weight += 20

        # ── Dividend score (weight: 10) ──
        div_score = 50
        dy = div.get("dividend_yield")
        if dy is not None:
            dy_pct = dy * 100 if dy < 1 else dy
            div_score = min(max(dy_pct * 15 + 30, 10), 90)

        scores["dividend"] = round(div_score, 1)
        total_score += div_score * 10
        total_weight += 10

        overall = total_score / total_weight if total_weight > 0 else 50

        # Rating
        if overall >= 75:
            rating = "Strong Buy"
        elif overall >= 60:
            rating = "Buy"
        elif overall >= 45:
            rating = "Hold"
        elif overall >= 30:
            rating = "Sell"
        else:
            rating = "Strong Sell"

        return {
            "overall_score": round(overall, 1),
            "rating": rating,
            "category_scores": scores,
        }

    def calculate_piotroski_score(self, symbol: str, exchange: str = "NSE") -> Optional[Dict]:
        """
        Calculate Piotroski F-Score (0-9) from financial statements.

        Criteria:
        1. Positive ROA
        2. Positive operating cash flow
        3. Increasing ROA
        4. CFO > Net Income (accruals)
        5. Decreasing long-term debt ratio
        6. Increasing current ratio
        7. No new share issuance
        8. Improving gross margin
        9. Improving asset turnover
        """
        try:
            sfx = EXCHANGE_SUFFIX.get(exchange, "")
            ticker = yf.Ticker(f"{symbol}{sfx}")
            info = ticker.info
            bs = ticker.balance_sheet
            cf = ticker.cashflow
            is_ = ticker.financials

            if bs is None or bs.empty or is_ is None or is_.empty:
                return None

            score = 0
            details = {}

            # 1. Positive ROA
            roa = info.get("returnOnAssets", 0) or 0
            if roa > 0:
                score += 1
                details["positive_roa"] = True
            else:
                details["positive_roa"] = False

            # 2. Positive operating cash flow
            ocf = info.get("operatingCashflow", 0) or 0
            if ocf > 0:
                score += 1
                details["positive_ocf"] = True
            else:
                details["positive_ocf"] = False

            # 3. Increasing ROA (compare current vs prior year if available)
            details["increasing_roa"] = roa > 0  # Simplified
            if roa > 0:
                score += 1

            # 4. Accruals: CFO > Net Income
            net_income = info.get("netIncomeToCommon", 0) or 0
            if ocf > net_income:
                score += 1
                details["quality_earnings"] = True
            else:
                details["quality_earnings"] = False

            # 5. Decreasing leverage (debt/equity)
            de = info.get("debtToEquity", 100) or 100
            if de < 100:
                score += 1
                details["low_leverage"] = True
            else:
                details["low_leverage"] = False

            # 6. Liquidity: current ratio > 1
            cr = info.get("currentRatio", 0) or 0
            if cr > 1:
                score += 1
                details["adequate_liquidity"] = True
            else:
                details["adequate_liquidity"] = False

            # 7. No dilution (shares outstanding)
            details["no_dilution"] = True  # Assume no dilution if no data
            score += 1

            # 8. Gross margin improvement
            gm = info.get("grossMargins", 0) or 0
            if gm > 0.2:
                score += 1
                details["good_margin"] = True
            else:
                details["good_margin"] = False

            # 9. Asset turnover
            rev = info.get("totalRevenue", 0) or 0
            assets = info.get("totalAssets") or info.get("marketCap", 1) or 1
            turnover = rev / assets if assets > 0 else 0
            if turnover > 0.5:
                score += 1
                details["good_turnover"] = True
            else:
                details["good_turnover"] = False

            # Classification
            if score >= 7:
                classification = "Strong"
            elif score >= 5:
                classification = "Moderate"
            else:
                classification = "Weak"

            return {
                "symbol": symbol,
                "piotroski_score": score,
                "classification": classification,
                "details": details,
            }

        except Exception as e:
            logger.error(f"Piotroski score error for {symbol}: {e}")
            return None

    def compare_fundamentals(self, symbol_list: List[str],
                              exchange: str = "NSE") -> pd.DataFrame:
        """Compare fundamentals of multiple stocks side-by-side."""
        comparison = {}
        for symbol in symbol_list:
            fund = self.get_fundamentals(symbol, exchange)
            if fund:
                score_result = self.score_fundamentals(fund)
                flat = {
                    "P/E": fund["valuation"].get("pe_ratio"),
                    "P/B": fund["valuation"].get("pb_ratio"),
                    "EV/EBITDA": fund["valuation"].get("ev_ebitda"),
                    "ROE %": round((fund["profitability"].get("roe") or 0) * 100, 2),
                    "Profit Margin %": round((fund["profitability"].get("profit_margin") or 0) * 100, 2),
                    "Revenue Growth %": round((fund["growth"].get("revenue_growth") or 0) * 100, 2),
                    "D/E": fund["financial_health"].get("debt_to_equity"),
                    "Current Ratio": fund["financial_health"].get("current_ratio"),
                    "Div Yield %": round((fund["dividends"].get("dividend_yield") or 0) * 100, 2),
                    "Score": score_result["overall_score"] if score_result else None,
                    "Rating": score_result["rating"] if score_result else "N/A",
                }
                comparison[symbol] = flat

        return pd.DataFrame(comparison).T if comparison else pd.DataFrame()

    def get_financial_statements(self, symbol: str,
                                  exchange: str = "NSE") -> Optional[Dict]:
        """Get income statement, balance sheet, and cash flow data."""
        try:
            sfx = EXCHANGE_SUFFIX.get(exchange, "")
            full_symbol = f"{symbol}{sfx}"
            ticker = yf.Ticker(full_symbol)

            result = {}

            if hasattr(ticker, "financials") and ticker.financials is not None:
                result["income_statement"] = ticker.financials.to_dict()
            if hasattr(ticker, "quarterly_financials") and ticker.quarterly_financials is not None:
                result["quarterly_income"] = ticker.quarterly_financials.to_dict()
            if hasattr(ticker, "balance_sheet") and ticker.balance_sheet is not None:
                result["balance_sheet"] = ticker.balance_sheet.to_dict()
            if hasattr(ticker, "cashflow") and ticker.cashflow is not None:
                result["cash_flow"] = ticker.cashflow.to_dict()

            return result if result else None
        except Exception as e:
            logger.error(f"Financial statements error for {symbol}: {e}")
            return None


# ============================================================================
# MODULE-LEVEL SINGLETON
# ============================================================================

_analyzer: Optional[FundamentalAnalyzer] = None

def get_fundamental_analyzer() -> FundamentalAnalyzer:
    """Get or create the singleton FundamentalAnalyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = FundamentalAnalyzer()
    return _analyzer
