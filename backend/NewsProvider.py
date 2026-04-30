"""
News Provider Service
======================
Multi-source news aggregation for stock market intelligence.
Bridges to SentimentEngine for analysis.

Data sources (priority order):
  1. Finnhub API (requires FINNHUB_KEY env var)
  2. yfinance .news attribute (free, no key needed — fallback)
"""

import os
import time
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Import our sentiment engine
try:
    from SentimentEngine import SentimentEngine, FinnhubNewsProvider, get_sentiment_engine
except ImportError:
    logger.warning("SentimentEngine not available — NewsProvider will use stubs")
    SentimentEngine = None
    FinnhubNewsProvider = None

# yfinance fallback
try:
    import yfinance as yf
    _HAS_YFINANCE = True
except ImportError:
    _HAS_YFINANCE = False


# ────────────────────────────────────────────────────────────────
#  yfinance News Fallback
# ────────────────────────────────────────────────────────────────

class YFinanceNewsProvider:
    """
    Free fallback news provider using yfinance Ticker.news.
    Works without any API key.  Rate-limited to 1 req/sec.
    """

    _cache: Dict[str, tuple] = {}
    _cache_ttl = 600  # 10 min
    _last_req = 0.0

    @classmethod
    def _rate_limit(cls):
        elapsed = time.time() - cls._last_req
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        cls._last_req = time.time()

    @classmethod
    def get_company_news(cls, symbol: str, limit: int = 15) -> List[Dict]:
        cache_key = f"yf_{symbol}"
        if cache_key in cls._cache:
            ts, data = cls._cache[cache_key]
            if time.time() - ts < cls._cache_ttl:
                return data[:limit]

        cls._rate_limit()
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            raw = ticker.news or []
            articles = []
            for item in raw:
                content = item.get('content', item)
                articles.append({
                    'headline': content.get('title', item.get('title', '')),
                    'summary': content.get('summary', content.get('description', '')),
                    'datetime': content.get('pubDate',
                                  datetime.fromtimestamp(
                                      item.get('providerPublishTime', 0)
                                  ).isoformat() if item.get('providerPublishTime') else None),
                    'source': content.get('provider', {}).get('displayName', 'Yahoo Finance')
                              if isinstance(content.get('provider'), dict)
                              else str(content.get('provider', 'Yahoo Finance')),
                    'url': content.get('canonicalUrl', {}).get('url', item.get('link', ''))
                           if isinstance(content.get('canonicalUrl'), dict)
                           else str(content.get('canonicalUrl', item.get('link', ''))),
                    'category': 'company_news',
                    'related': symbol,
                })
            cls._cache[cache_key] = (time.time(), articles)
            return articles[:limit]
        except Exception as exc:
            logger.warning(f"yfinance news fetch failed for {symbol}: {exc}")
            return []

    @classmethod
    def get_market_news(cls, limit: int = 20) -> List[Dict]:
        """Fetch market-level news via broad index tickers."""
        seen_titles: set = set()
        articles: List[Dict] = []
        for idx_sym in ['^NSEI', '^BSESN']:
            cache_key = f"yf_mkt_{idx_sym}"
            if cache_key in cls._cache:
                ts, data = cls._cache[cache_key]
                if time.time() - ts < cls._cache_ttl:
                    for a in data:
                        if a['headline'] not in seen_titles:
                            seen_titles.add(a['headline'])
                            articles.append(a)
                    continue
            cls._rate_limit()
            try:
                raw = yf.Ticker(idx_sym).news or []
                batch: List[Dict] = []
                for item in raw:
                    content = item.get('content', item)
                    art = {
                        'headline': content.get('title', item.get('title', '')),
                        'summary': content.get('summary', content.get('description', '')),
                        'datetime': content.get('pubDate',
                                      datetime.fromtimestamp(
                                          item.get('providerPublishTime', 0)
                                      ).isoformat() if item.get('providerPublishTime') else None),
                        'source': content.get('provider', {}).get('displayName', 'Yahoo Finance')
                                  if isinstance(content.get('provider'), dict)
                                  else str(content.get('provider', 'Yahoo Finance')),
                        'url': content.get('canonicalUrl', {}).get('url', item.get('link', ''))
                               if isinstance(content.get('canonicalUrl'), dict)
                               else str(content.get('canonicalUrl', item.get('link', ''))),
                        'category': 'market',
                    }
                    batch.append(art)
                    if art['headline'] not in seen_titles:
                        seen_titles.add(art['headline'])
                        articles.append(art)
                cls._cache[cache_key] = (time.time(), batch)
            except Exception as exc:
                logger.warning(f"yfinance market news failed for {idx_sym}: {exc}")
        return articles[:limit]


class NewsAggregator:
    """
    Unified news aggregation interface.
    Used by application.py for news-related API endpoints.

    Priority: Finnhub (if key present) → yfinance (free fallback).
    """
    
    # Hardcoded production key — used when env var is missing or empty
    _DEFAULT_FINNHUB_KEY = 'd7ovmj9r01qr68pb6oegd7ovmj9r01qr68pb6of0'

    def __init__(self, finnhub_key: Optional[str] = None):
        self.finnhub_key = finnhub_key or os.getenv('FINNHUB_KEY', '') or self._DEFAULT_FINNHUB_KEY
        self._news_provider = None
        self._sentiment_engine = None
        self._yf_fallback = _HAS_YFINANCE
        
        if FinnhubNewsProvider and self.finnhub_key:
            self._news_provider = FinnhubNewsProvider(api_key=self.finnhub_key)
        if SentimentEngine:
            self._sentiment_engine = SentimentEngine(finnhub_key=self.finnhub_key)
        
        if not self._news_provider and self._yf_fallback:
            logger.info("NewsAggregator: no Finnhub key — using yfinance fallback")
    
    def get_providers(self) -> List[Dict]:
        """List available news providers and their status."""
        providers = []
        providers.append({
            'name': 'Finnhub',
            'active': bool(self.finnhub_key and self._news_provider),
            'type': 'company_news',
        })
        providers.append({
            'name': 'Yahoo Finance',
            'active': self._yf_fallback,
            'type': 'company_news (fallback)',
        })
        return providers
    
    def get_market_news(self, limit: int = 20) -> Dict:
        """Fetch general market news."""
        articles: List[Dict] = []
        source = 'none'

        # Primary: Finnhub
        if self._news_provider:
            raw = self._news_provider.get_market_news(category='general')
            articles = raw[:limit]
            source = 'finnhub'

        # Fallback: yfinance
        if not articles and self._yf_fallback:
            articles = YFinanceNewsProvider.get_market_news(limit=limit)
            source = 'yfinance'
        
        return {
            'articles': articles,
            'count': len(articles),
            'source': source,
            'timestamp': datetime.now().isoformat(),
        }
    
    def get_stock_news(self, symbol: str, limit: int = 20, days_back: int = 14) -> Dict:
        """Fetch news for a specific stock with sentiment analysis."""
        # Primary: SentimentEngine (uses Finnhub internally)
        if self._sentiment_engine and self.finnhub_key:
            detailed = self._sentiment_engine.get_detailed_analysis(symbol, days_back=days_back)
            if detailed.get('articles'):
                detailed['articles'] = detailed['articles'][:limit]
                return detailed

        # Fallback: yfinance news + local sentiment analysis
        articles_raw: List[Dict] = []
        if self._news_provider:
            articles_raw = self._news_provider.get_company_news(symbol, days_back=days_back)[:limit]
        
        if not articles_raw and self._yf_fallback:
            articles_raw = YFinanceNewsProvider.get_company_news(symbol, limit=limit)

        # Run local sentiment if engine available (even without Finnhub key)
        analyzed: List[Dict] = []
        if self._sentiment_engine and articles_raw:
            analyzer = self._sentiment_engine.analyzer
            for art in articles_raw:
                text = f"{art.get('headline', '')} {art.get('summary', '')}"
                sent = analyzer.analyze_text(text)
                analyzed.append({
                    'headline': art.get('headline', ''),
                    'source': art.get('source', ''),
                    'datetime': art.get('datetime', ''),
                    'url': art.get('url', ''),
                    'sentiment': sent['compound_score'],
                    'magnitude': sent['magnitude'],
                    'event_category': sent['event_category'],
                    'positive_keywords': sent['positive_keywords'],
                    'negative_keywords': sent['negative_keywords'],
                })
        else:
            for art in articles_raw:
                analyzed.append({
                    'headline': art.get('headline', ''),
                    'source': art.get('source', ''),
                    'datetime': art.get('datetime', ''),
                    'url': art.get('url', ''),
                    'sentiment': 0.0,
                    'magnitude': 0.0,
                    'event_category': 'general',
                    'positive_keywords': 0,
                    'negative_keywords': 0,
                })

        # Compute aggregate
        if analyzed:
            scores = [a['sentiment'] for a in analyzed]
            avg_score = sum(scores) / len(scores)
            overall = 'BULLISH' if avg_score > 0.15 else 'BEARISH' if avg_score < -0.15 else 'NEUTRAL'
            bullish_ratio = sum(1 for s in scores if s > 0.05) / len(scores)
            bearish_ratio = sum(1 for s in scores if s < -0.05) / len(scores)
        else:
            avg_score = 0.0
            overall = 'NEUTRAL'
            bullish_ratio = 0.0
            bearish_ratio = 0.0
        
        return {
            'ticker': symbol,
            'articles': analyzed,
            'article_count': len(analyzed),
            'aggregate': {
                'sentiment_score': round(avg_score, 4),
                'bullish_ratio': round(bullish_ratio, 4),
                'bearish_ratio': round(bearish_ratio, 4),
            },
            'overall_sentiment': overall,
        }
    
    def get_portfolio_news(self, symbols: List[str], limit_per_stock: int = 5) -> Dict:
        """Fetch news for a portfolio of stocks."""
        portfolio_news = {}
        for symbol in symbols:
            portfolio_news[symbol] = self.get_stock_news(
                symbol, limit=limit_per_stock, days_back=7
            )
        
        return {
            'portfolio': portfolio_news,
            'stocks_count': len(symbols),
            'timestamp': datetime.now().isoformat(),
        }


# ---- Singleton factory ----
_aggregator: Optional[NewsAggregator] = None


def get_news_aggregator(finnhub_key: Optional[str] = None) -> NewsAggregator:
    """Get or create a singleton NewsAggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = NewsAggregator(finnhub_key=finnhub_key)
    return _aggregator
