# PATENT CLAIMS — Artha Drishti v5.0: AI-Powered Stock Intelligence Platform

**Application Title:** System and Method for Multi-Modal Autonomous Stock Intelligence Using Neural Committee Screening, Portfolio-Aware Risk Decomposition, and Generative Report Synthesis

**Filing Date:** *(To be determined)*
**Inventor(s):** *(To be determined)*
**Classification:** G06Q 40/04 (Financial data processing – Stock trading)

---

## ABSTRACT

A computer-implemented system for autonomous multi-modal stock market intelligence, comprising:
(a) a Multi-Target Neural Network with Sinusoidal Positional Encoding and Multi-Scale Temporal Convolutional Networks, outputting five simultaneously predicted targets (price direction, volatility regime, risk level, trend strength, optimal action) through independent decoder heads gated by learned confidence weights;
(b) a Committee-of-Experts Strategy Screening Engine that evaluates each security against 18+ heterogeneous quantitative strategies spanning 7 categories, producing a unified consensus signal only when a configurable threshold of independent strategies agree — thereby eliminating single-strategy bias;
(c) a Portfolio-Aware Risk Decomposition module computing Component Value-at-Risk (CVaR), Diversification Ratio, and Monte Carlo Efficient Frontier with Dirichlet-weighted sampling to identify statistically optimal portfolios;
(d) a Fundamental Scoring Engine implementing Piotroski F-Score alongside a proprietary 5-category weighted composite score (Valuation 25%, Profitability 25%, Growth 20%, Health 20%, Dividends 10%);
(e) a Generative Report Synthesis module that autonomously assembles HTML intelligence dossiers combining AI predictions, fundamental assessments, risk metrics, and technical analysis into a single investor-ready document.

---

## CLAIM 1 — Multi-Target Neural Network Architecture

A computer-implemented method for predicting multiple interdependent stock market targets simultaneously, comprising:

**1.1** Receiving preprocessed OHLCV candlestick data and 150+ engineered features including multi-timeframe technical indicators, statistical moments (skew, kurtosis), regime detection signals, and volume profile metrics;

**1.2** Encoding temporal position information via **Sinusoidal Positional Encoding** defined as:
$$PE_{(pos, 2i)} = \sin\left(\frac{pos}{10000^{2i/d_{model}}}\right)$$
$$PE_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d_{model}}}\right)$$
to preserve inter-day temporal relationships across variable-length lookback windows;

**1.3** Processing the encoded sequence through a **Multi-Scale Temporal Convolutional Network (TCN)** with parallel branches having dilation rates of $\{1, 2, 4, 8\}$, each capturing different temporal granularities, followed by concatenation and projection;

**1.4** Passing the multi-scale representation through a **Bidirectional LSTM** layer to capture both forward and backward temporal dependencies;

**1.5** Applying **Self-Attention** mechanism to weight the importance of different time steps, with learned query, key, and value projections;

**1.6** Simultaneously predicting **five independent targets** through dedicated decoder heads:
- **Direction Prediction** (3-class: Bullish / Bearish / Neutral)
- **Volatility Regime** (3-class: Low / Medium / High)
- **Risk Level** (3-class: Low / Medium / High)
- **Trend Strength** (regression: 0.0–1.0)
- **Optimal Action** (5-class: Strong Buy / Buy / Hold / Sell / Strong Sell)

**1.7** Computing a **Confidence Score** as a learned weighted combination of individual head confidences, gated through a soft-attention mechanism over the target predictions;

**1.8** Training with a **multi-task loss function**:
$$\mathcal{L}_{total} = \sum_{i=1}^{5} \lambda_i \mathcal{L}_i$$
where $\lambda_i$ are learnable task weights and $\mathcal{L}_i$ are individual task losses (cross-entropy for classification heads, MSE for regression head).

**Novelty:** The simultaneous prediction of five interdependent financial targets through independent decoder heads with confidence gating. Prior art systems predict single targets (price direction OR volatility OR risk), whereas this system jointly models all dimensions in a single forward pass, enabling coherent multi-dimensional analysis.

---

## CLAIM 2 — Committee-of-Experts Strategy Screening Engine

A method for evaluating stock securities against a heterogeneous committee of independent quantitative strategies, comprising:

**2.1** Maintaining a registry of **18+ strategies** organized into 7 categories:
| Category | Strategies |
|----------|-----------|
| Trend Following | Trend Rider, Golden Cross, Ichimoku Cloud Breakout, Supertrend Bullish |
| Momentum | Momentum Hunter, Breakout Scanner, 52-Week High Momentum |
| Swing Trading | Swing Trader |
| Value Investing | Value Bounce, GARP (Growth at Reasonable Price) |
| Mean Reversion | RSI Divergence, Bollinger Squeeze, Contrarian Recovery |
| Pattern Recognition | Double Bottom |
| Multi-Factor | Volume Surge, Smart Money, Triple MACD Alignment |

**2.2** For each stock, computing a **universal indicator set** (20+ technical indicators: RSI, MACD, Bollinger Bands, ADX, Ichimoku, Supertrend, ATR, OBV, stochastic, ROC, Williams %R, CMF, VWAP proxy, etc.) once and sharing across all strategies, thereby:
- Eliminating redundant computation;
- Enabling cross-strategy feature sharing;

**2.3** Evaluating each strategy independently using its own rule set that tests specific conditions on the shared indicator set, producing per-strategy verdicts comprising:
- Pass/Fail boolean
- Confidence score (0–100)
- Signal type (Bullish / Bearish / Neutral)
- Metadata (which specific conditions were met)

**2.4** Aggregating results through a **Committee Consensus** mechanism:
- Computing the number of passing strategies $N_{pass}$
- Computing average confidence $\bar{C}$ across passing strategies
- A stock qualifies for recommendation IF AND ONLY IF:
  $$N_{pass} \geq T_{min} \quad \land \quad \bar{C} \geq C_{min}$$
  where $T_{min}$ (default: 2) and $C_{min}$ (default: 60%) are user-configurable thresholds;

**2.5** Generating an overall committee verdict of {**Strong Consensus**, **Moderate Consensus**, **Weak Consensus**, **No Consensus**} based on the ratio $N_{pass}/N_{total}$;

**2.6** Allowing **dynamic strategy addition/removal** at runtime without retraining or restarting, through a self-describing strategy registry with JSON-serializable strategy definitions.

**Novelty:** Unlike single-strategy screeners (e.g., traditional RSI-based or moving average crossover screeners), this system evaluates every stock simultaneously against ALL strategies and synthesizes consensus. The committee approach eliminates signal-strategy coupling and provides statistically robust screening by requiring agreement across fundamentally different methodologies.

---

## CLAIM 3 — Portfolio-Aware Risk Decomposition

A system for quantifying investment risk through multi-level decomposition, comprising:

**3.1** Computing **30+ individual risk metrics** organized into 7 categories:
- **Volatility Metrics**: annualized volatility, downside deviation, upside volatility, volatility skew ratio
- **Drawdown Metrics**: maximum drawdown, average drawdown, drawdown duration, recovery factor
- **Value at Risk**: Parametric VaR (95%, 99%), Historical VaR, Conditional VaR (CVaR/Expected Shortfall)
- **Tail Risk**: skewness, excess kurtosis, Jarque-Bera statistic, tail ratio
- **Risk-Adjusted Returns**: Sharpe ratio, Sortino ratio, Calmar ratio, Omega ratio, information ratio
- **Market Risk**: Beta, Alpha, Treynor ratio, R-squared, tracking error
- **Advanced**: Hurst exponent (trend persistence), Ulcer index (investor anxiety), pain ratio, gain-loss ratio

**3.2** **Component VaR Decomposition** at the portfolio level:
$$CVaR_i = w_i \cdot \beta_i^{portfolio} \cdot VaR_{portfolio}$$
where $w_i$ is the weight of asset $i$, $\beta_i^{portfolio} = \frac{Cov(r_i, r_p)}{\sigma_p^2}$, and $VaR_{portfolio}$ is the portfolio-level Value at Risk;

**3.3** **Diversification Ratio** computation:
$$DR = \frac{\sum_i w_i \sigma_i}{\sigma_p}$$
where $\sigma_i$ is the individual asset volatility and $\sigma_p$ is the portfolio volatility, measuring the effectiveness of diversification ($DR > 1$ implies diversification benefit);

**3.4** **Monte Carlo Efficient Frontier** generation using Dirichlet-weighted random sampling:
- Generating $N$ random weight vectors $\mathbf{w} \sim Dir(\boldsymbol{\alpha})$ with $\alpha_i = 1$ (uniform Dirichlet);
- Computing expected return and volatility for each portfolio;
- Identifying the **Maximum Sharpe Ratio** portfolio and **Minimum Volatility** portfolio;
- Returning frontier coordinates for visualization;

**3.5** **Hurst Exponent** estimation via Rescaled Range (R/S) analysis to determine whether a stock exhibits:
- Mean-reverting behavior ($H < 0.5$)
- Random walk ($H \approx 0.5$)
- Trending behavior ($H > 0.5$)

**Novelty:** The combination of Component VaR decomposition, diversification ratio, Hurst exponent analysis, and Monte Carlo efficient frontier in a single unified API, specifically designed for retail investor portfolio optimization. Prior systems typically offer VaR OR efficient frontier, but not both in an integrated, real-time web-accessible system.

---

## CLAIM 4 — Piotroski F-Score Enhanced Fundamental Scoring

A method for scoring stock fundamentals through a dual-framework approach, comprising:

**4.1** Computing the classic **Piotroski F-Score** (9-point scale) with decomposition into sub-scores:
- Profitability (4 points): ROA positivity, operating cash flow positivity, ROA improvement, quality of earnings (OCF > Net Income)
- Leverage/Liquidity (3 points): leverage decrease, current ratio improvement, no share dilution
- Operating Efficiency (2 points): gross margin improvement, asset turnover improvement

**4.2** Computing a **proprietary 5-category weighted composite score** (0–100):
- **Valuation** (25%): P/E percentile, P/B percentile, forward P/E vs trailing P/E, PEG ratio assessment
- **Profitability** (25%): ROE tier ranking, profit margin tier ranking, ROA tier ranking
- **Growth** (20%): Revenue and earnings growth rate assessment
- **Financial Health** (20%): Current ratio adequacy, D/E ratio safety, interest coverage
- **Dividends** (10%): Dividend yield competitiveness, payout ratio sustainability

**4.3** Mapping the composite score to a **5-tier rating**: Strong Buy (80+), Buy (60–80), Hold (40–60), Sell (20–40), Strong Sell (<20);

**4.4** Enabling **side-by-side comparison** of multiple stocks across all fundamental dimensions, normalizing metrics to comparable scales.

**Novelty:** The dual-framework approach combining traditional Piotroski F-Score with a modern weighted composite score provides both academic rigor and practical utility. The 5-category weighted system with percentile-based normalization addresses limitations of absolute thresholds used in prior art.

---

## CLAIM 5 — Autonomous Intelligence Report Synthesis

A method for generating comprehensive, investor-ready intelligence reports, comprising:

**5.1** Autonomously aggregating outputs from all system modules:
- AI neural network predictions (direction, volatility, confidence)
- Fundamental analysis scores (Piotroski + composite)
- Risk metrics (VaR, Sharpe, etc.)
- Technical indicator snapshots

**5.2** Synthesizing the aggregated data into a **self-contained HTML document** with:
- Professional dark-theme styling
- Color-coded risk indicators (green/yellow/red)
- Tabular metric displays
- AI prediction confidence visualization
- Regulatory disclaimer

**5.3** Providing export in multiple formats: HTML (complete document), JSON (machine-readable), CSV (spreadsheet-compatible).

---

## CLAIM 6 — Multi-Exchange Real-Time Architecture

A system providing unified stock intelligence across multiple exchanges:

**6.1** Supporting NSE, BSE, NYSE, NASDAQ, and LSE through a configurable exchange management layer;

**6.2** Automatic symbol suffix mapping (`.NS`, `.BO`, etc.) for seamless multi-exchange queries;

**6.3** Scheduled automated data pipeline running at market close (4:00 PM IST for Indian markets) via APScheduler;

**6.4** JWT + Google OAuth authentication for secure, production-grade access control;

**6.5** PostgreSQL persistence for user data, portfolio history, and watchlist management.

---

## CLAIM 7 — Walk-Forward Backtesting with Regime Detection

**7.1** Walk-forward cross-validation that splits data into expanding training windows and fixed test windows, preventing look-ahead bias;

**7.2** Automatic market regime detection using volatility clustering and trend strength to contextualize backtest results;

**7.3** Per-regime performance decomposition showing how strategies and AI models perform differently in bull, bear, and sideways markets.

---

## SYSTEM ARCHITECTURE CLAIM

A full-stack computer system for stock market intelligence comprising:

1. A **Flask REST API backend** exposing 60+ endpoints for all modules described in Claims 1–7;
2. A **React + Vite frontend** providing interactive dashboards, charts, and real-time data visualization;
3. A **PyTorch deep learning inference engine** for multi-target neural network prediction;
4. A **PostgreSQL database** for persistent storage of user data, portfolios, and historical analysis;
5. A **Caching layer** for market data to reduce API calls and improve response times;
6. A **Modular plugin architecture** allowing new strategies, risk metrics, and analysis modules to be added without system restart.

---

## PRIOR ART DIFFERENTIATION

| Feature | Prior Art (Bloomberg/TradingView) | Artha Drishti v5.0 |
|---------|-----------------------------------|---------------------|
| Strategy evaluation | Single strategy at a time | 18+ strategies simultaneously (Committee) |
| Risk analysis | VaR only or limited metrics | 30+ metrics with Component VaR decomposition |
| AI prediction | Single target (price/direction) | Five simultaneous targets with confidence gating |
| Fundamental scoring | P/E-based simple filters | Dual framework (Piotroski + 5-category weighted) |
| Portfolio optimization | Mean-variance only | Monte Carlo + Dirichlet sampling efficient frontier |
| Report generation | Manual/template-based | Autonomous multi-modal synthesis |
| Accessibility | Enterprise-only (expensive) | Open, web-accessible platform |

---

## PATENT-WORTHY INNOVATIONS SUMMARY

1. **Multi-Target Neural Architecture** with 5 decoder heads and confidence gating (Claim 1)
2. **Committee-of-Experts Screening** with 18+ strategies and consensus mechanism (Claim 2)
3. **Component VaR Portfolio Decomposition** with Diversification Ratio computation (Claim 3)
4. **Dual Fundamental Scoring Framework** combining Piotroski + proprietary composite (Claim 4)
5. **Autonomous Report Synthesis** across all analytical dimensions (Claim 5)
6. **Multi-Exchange Unified Architecture** with scheduled data pipeline (Claim 6)
7. **Walk-Forward Regime-Aware Backtesting** (Claim 7)

---

*This document is for internal patent preparation purposes. Consult a registered patent attorney before filing.*
