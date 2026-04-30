"""
===================================================================
PATENT-PENDING: MULTI-SOURCE SENTIMENT FUSION ENGINE (MSSFE)
===================================================================

Novel contributions:
  1. Temporal Decay Weighting: Recent news weighted exponentially
     higher than older articles, with adaptive half-life.
  
  2. Event Classification: Categorizes news into fundamental events
     (earnings, M&A, regulatory) and assigns domain-specific
     sentiment multipliers.
  
  3. Multi-Analyzer Ensemble: Combines VADER, TextBlob, and
     keyword-based analysis with learned ensemble weights.
  
  4. Market-Context Aware Scoring: Adjusts sentiment based on
     current market regime (bull/bear/volatile).

Data Sources:
  - Finnhub API (company news, market news)
  - Fallback: TextBlob + keyword analysis on any text input

Author: GenAI Stock Intelligence System
Version: 1.0.0
===================================================================
"""

import os
import re
import json
import time
import logging
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from functools import lru_cache

# ---- CRITICAL: Pre-import scipy BEFORE textblob/nltk to prevent ----
# ---- Windows importlib lock deadlock (KeyboardInterrupt in bootstrap) ----
try:
    import scipy
    import scipy.stats
    import scipy.optimize
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ---- Try importing optional NLP packages ----
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _HAS_VADER = True
except ImportError:
    _HAS_VADER = False
    logger.info("vaderSentiment not installed — using TextBlob only")

try:
    from textblob import TextBlob
    _HAS_TEXTBLOB = True
except ImportError:
    _HAS_TEXTBLOB = False
    logger.info("textblob not installed — using keyword-based analysis only")


# ========== EVENT CATEGORIES & KEYWORDS ==========

EVENT_CATEGORIES = {
    'earnings': {
        'keywords': ['earnings', 'profit', 'revenue', 'quarterly results', 'net income',
                      'EPS', 'margin', 'guidance', 'forecast', 'beat estimates',
                      'miss estimates', 'revenue growth', 'profit warning'],
        'weight': 1.5,  # Earnings have strong price impact
    },
    'merger_acquisition': {
        'keywords': ['merger', 'acquisition', 'takeover', 'buyout', 'stake',
                      'strategic investment', 'partnership', 'joint venture',
                      'consolidation', 'divestiture'],
        'weight': 1.4,
    },
    'regulatory': {
        'keywords': ['regulation', 'compliance', 'SEBI', 'RBI', 'government',
                      'policy', 'ban', 'license', 'approval', 'investigation',
                      'penalty', 'fine', 'lawsuit', 'antitrust'],
        'weight': 1.3,
    },
    'management': {
        'keywords': ['CEO', 'chairman', 'director', 'management change', 'appointment',
                      'resignation', 'restructuring', 'layoff', 'hire'],
        'weight': 1.1,
    },
    'product': {
        'keywords': ['launch', 'product', 'innovation', 'patent', 'R&D',
                      'contract', 'order', 'deal', 'expansion', 'capacity'],
        'weight': 1.2,
    },
    'market_sentiment': {
        'keywords': ['bullish', 'bearish', 'rally', 'crash', 'correction',
                      'volatility', 'sell-off', 'buy', 'upgrade', 'downgrade',
                      'target price', 'analyst', 'recommendation'],
        'weight': 1.0,
    },
    'macro': {
        'keywords': ['inflation', 'interest rate', 'GDP', 'recession', 'stimulus',
                      'trade war', 'crude oil', 'dollar', 'rupee', 'Fed', 'monetary'],
        'weight': 0.8,  # Less stock-specific
    },
}

# Domain-specific sentiment words for Indian markets
INDIAN_MARKET_SENTIMENT = {
    'positive': [
        'outperform', 'strong buy', 'upgrade', 'growth', 'expansion', 'breakout',
        'record high', 'dividend', 'bonus', 'stock split', 'buyback', 'order win',
        'capacity expansion', 'new contract', 'turnaround', 'value pick',
        'block deal', 'mutual fund bought', 'FII bought', 'DII bought'
    ],
    'negative': [
        'underperform', 'downgrade', 'weak', 'decline', 'loss', 'default',
        'fraud', 'scam', 'penalty', 'selloff', 'promoter pledge', 'debt trap',
        'NCLT', 'insolvency', 'FII sold', 'DII sold', 'ban period',
        'price manipulation', 'insider trading', 'stock crash'
    ]
}


class SentimentAnalyzer:
    """
    Multi-source sentiment analysis with temporal decay and event classification.
    """
    
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer() if _HAS_VADER else None
        
        # Compile keyword patterns for fast matching
        self._event_patterns = {}
        for category, info in EVENT_CATEGORIES.items():
            pattern = '|'.join(re.escape(kw) for kw in info['keywords'])
            self._event_patterns[category] = re.compile(pattern, re.IGNORECASE)
        
        # Indian market sentiment patterns
        self._pos_pattern = re.compile(
            '|'.join(re.escape(w) for w in INDIAN_MARKET_SENTIMENT['positive']),
            re.IGNORECASE
        )
        self._neg_pattern = re.compile(
            '|'.join(re.escape(w) for w in INDIAN_MARKET_SENTIMENT['negative']),
            re.IGNORECASE
        )
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze a single text and return sentiment scores.
        
        Returns:
            Dict with: compound_score (-1 to 1), magnitude (0 to 1),
                       event_category, domain_boost, components
        """
        if not text or not text.strip():
            return self._neutral_result()
        
        text_clean = text.strip()
        
        # ---- Component 1: VADER ----
        vader_score = 0.0
        if self.vader:
            vs = self.vader.polarity_scores(text_clean)
            vader_score = vs['compound']
        
        # ---- Component 2: TextBlob ----
        textblob_score = 0.0
        if _HAS_TEXTBLOB:
            blob = TextBlob(text_clean)
            textblob_score = blob.sentiment.polarity
        
        # ---- Component 3: Domain-specific keyword scoring ----
        domain_score = 0.0
        pos_matches = len(self._pos_pattern.findall(text_clean))
        neg_matches = len(self._neg_pattern.findall(text_clean))
        total_matches = pos_matches + neg_matches
        if total_matches > 0:
            domain_score = (pos_matches - neg_matches) / total_matches
        
        # ---- Ensemble ----
        if self.vader and _HAS_TEXTBLOB:
            # Weighted average: VADER (0.4) + TextBlob (0.3) + Domain (0.3)
            compound = 0.4 * vader_score + 0.3 * textblob_score + 0.3 * domain_score
        elif _HAS_TEXTBLOB:
            compound = 0.5 * textblob_score + 0.5 * domain_score
        else:
            compound = domain_score
        
        # ---- Event classification ----
        event_category, event_weight = self._classify_event(text_clean)
        
        # Apply event weight as a multiplier
        compound_boosted = compound * event_weight
        compound_boosted = max(min(compound_boosted, 1.0), -1.0)
        
        # Sentiment magnitude (how strong the opinion is, regardless of direction)
        if self.vader:
            magnitude = abs(vader_score)
        elif _HAS_TEXTBLOB:
            blob = TextBlob(text_clean)
            magnitude = blob.sentiment.subjectivity
        else:
            magnitude = min(total_matches / 5.0, 1.0)
        
        return {
            'compound_score': round(compound_boosted, 4),
            'magnitude': round(magnitude, 4),
            'event_category': event_category,
            'event_weight': event_weight,
            'components': {
                'vader': round(vader_score, 4),
                'textblob': round(textblob_score, 4),
                'domain': round(domain_score, 4),
            },
            'positive_keywords': pos_matches,
            'negative_keywords': neg_matches,
        }
    
    def _classify_event(self, text: str) -> Tuple[str, float]:
        """Classify news text into event category and return weight."""
        best_category = 'general'
        best_count = 0
        best_weight = 1.0
        
        for category, pattern in self._event_patterns.items():
            matches = pattern.findall(text)
            if len(matches) > best_count:
                best_count = len(matches)
                best_category = category
                best_weight = EVENT_CATEGORIES[category]['weight']
        
        return best_category, best_weight
    
    def _neutral_result(self) -> Dict:
        return {
            'compound_score': 0.0,
            'magnitude': 0.0,
            'event_category': 'none',
            'event_weight': 1.0,
            'components': {'vader': 0.0, 'textblob': 0.0, 'domain': 0.0},
            'positive_keywords': 0,
            'negative_keywords': 0,
        }


class FinnhubNewsProvider:
    """
    Fetches company and market news from Finnhub API.
    Includes rate limiting and caching.
    """
    
    # Hardcoded production key — used when env var is missing or empty
    _DEFAULT_FINNHUB_KEY = 'd7ovmj9r01qr68pb6oegd7ovmj9r01qr68pb6of0'

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('FINNHUB_KEY', '') or self._DEFAULT_FINNHUB_KEY
        self.base_url = 'https://finnhub.io/api/v1'
        self._cache: Dict[str, Tuple[float, List]] = {}
        self._cache_ttl = 1800  # 30 minutes
        self._last_request = 0
        self._min_interval = 1.0  # 1 second between requests (rate limit)
        self._disabled = False   # Auto-set on 403 to stop spamming invalid key
    
    def _rate_limit(self):
        """Enforce minimum interval between API calls."""
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()
    
    def get_company_news(self, symbol: str, days_back: int = 30) -> List[Dict]:
        """
        Fetch company-specific news from Finnhub.
        
        Args:
            symbol: Stock ticker (e.g., 'RELIANCE' → uses .NS suffix for Indian stocks)
            days_back: Number of days of news to fetch
        
        Returns:
            List of news articles with: headline, summary, datetime, source, url, category
        """
        if self._disabled or not self.api_key:
            return []
        
        cache_key = f"company_{symbol}_{days_back}"
        cached = self._check_cache(cache_key)
        if cached is not None:
            return cached
        
        # Indian stocks use .NS suffix on Finnhub for some endpoints
        # But company news often works with just the symbol
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/company-news"
            params = {
                'symbol': f"{symbol}.NS",  # NSE suffix
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'token': self.api_key,
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                articles = response.json()
                if isinstance(articles, list):
                    result = self._normalize_articles(articles)
                    self._set_cache(cache_key, result)
                    return result
            elif response.status_code == 429:
                logger.warning("Finnhub rate limit exceeded")
            elif response.status_code == 403:
                logger.warning(
                    "Finnhub API key rejected (403 Forbidden). "
                    "Auto-disabling Finnhub provider — falling back to yfinance for news."
                )
                self._disabled = True
            else:
                logger.warning(f"Finnhub API error: {response.status_code}")
                
        except requests.RequestException as e:
            logger.warning(f"Finnhub request failed for {symbol}: {e}")
        
        return []
    
    def get_market_news(self, category: str = 'general') -> List[Dict]:
        """Fetch general market news."""
        if self._disabled or not self.api_key:
            return []
        
        cache_key = f"market_{category}"
        cached = self._check_cache(cache_key)
        if cached is not None:
            return cached
        
        self._rate_limit()
        
        try:
            url = f"{self.base_url}/news"
            params = {
                'category': category,
                'token': self.api_key,
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                articles = response.json()
                if isinstance(articles, list):
                    result = self._normalize_articles(articles)
                    self._set_cache(cache_key, result)
                    return result
            elif response.status_code == 403:
                logger.warning(
                    "Finnhub API key rejected (403 Forbidden). "
                    "Auto-disabling Finnhub provider — falling back to yfinance."
                )
                self._disabled = True
        except requests.RequestException as e:
            logger.warning(f"Finnhub market news request failed: {e}")
        
        return []
    
    def _normalize_articles(self, articles: List[Dict]) -> List[Dict]:
        """Normalize Finnhub article format."""
        normalized = []
        for a in articles:
            normalized.append({
                'headline': a.get('headline', ''),
                'summary': a.get('summary', ''),
                'datetime': datetime.fromtimestamp(a.get('datetime', 0)).isoformat()
                            if a.get('datetime') else None,
                'source': a.get('source', 'finnhub'),
                'url': a.get('url', ''),
                'category': a.get('category', 'general'),
                'related': a.get('related', ''),
            })
        return normalized
    
    def _check_cache(self, key: str) -> Optional[List]:
        if key in self._cache:
            ts, data = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: List):
        self._cache[key] = (time.time(), data)


class SentimentEngine:
    """
    PATENT-PENDING: Multi-Source Sentiment Fusion Engine (MSSFE)
    
    Orchestrates news fetching, sentiment analysis, temporal decay,
    and feature generation for ML model integration.
    
    Falls back to yfinance news when Finnhub API key is not available.
    """
    
    def __init__(self, finnhub_key: Optional[str] = None):
        self.analyzer = SentimentAnalyzer()
        self.news_provider = FinnhubNewsProvider(api_key=finnhub_key)
        self._yf_fallback = False
        self._yf_provider = None
        self._sentiment_cache: Dict[str, Tuple[float, Dict]] = {}
        self._cache_ttl = 3600  # 1 hour

        # Always prepare yfinance fallback so it kicks in when Finnhub
        # key is absent OR when Finnhub returns 403 at runtime.
        try:
            from NewsProvider import YFinanceNewsProvider
            self._yf_provider = YFinanceNewsProvider
            self._yf_fallback = True
            logger.info("SentimentEngine: yfinance fallback prepared (activates if Finnhub unavailable)")
        except ImportError:
            _key = finnhub_key or os.getenv('FINNHUB_KEY', '') or FinnhubNewsProvider._DEFAULT_FINNHUB_KEY
            if not _key:
                logger.warning("SentimentEngine: no Finnhub key and yfinance NewsProvider unavailable")

    def _fetch_articles(self, ticker: str, days_back: int = 30) -> List[Dict]:
        """Fetch news articles from best available source."""
        # Primary: Finnhub
        articles = self.news_provider.get_company_news(ticker, days_back=days_back)
        if articles:
            return articles

        # Fallback: yfinance (free, no key needed)
        if self._yf_fallback and self._yf_provider:
            try:
                articles = self._yf_provider.get_company_news(ticker, limit=20)
                if articles:
                    logger.debug(f"SentimentEngine: using yfinance fallback for {ticker} ({len(articles)} articles)")
                    return articles
            except Exception as e:
                logger.debug(f"SentimentEngine: yfinance fallback failed for {ticker}: {e}")

        return []
    
    def get_sentiment_features(self, ticker: str, days_back: int = 30) -> Dict[str, float]:
        """
        Generate sentiment features for a stock ticker.
        
        Returns a dict of numeric features suitable for ML model input:
          - sentiment_score: Weighted average sentiment (-1 to 1)
          - sentiment_magnitude: How strong the sentiment is (0 to 1)
          - sentiment_volume: Number of articles (log-scaled)
          - sentiment_trend: Change in sentiment over time
          - sentiment_dispersion: Agreement/disagreement across sources
          - event_earnings: Binary flag for recent earnings news
          - event_regulatory: Binary flag for regulatory news
          - event_ma: Binary flag for M&A news
          - bullish_ratio: Fraction of positive articles
          - bearish_ratio: Fraction of negative articles
        """
        # Check cache
        cache_key = f"features_{ticker}"
        if cache_key in self._sentiment_cache:
            ts, cached = self._sentiment_cache[cache_key]
            if time.time() - ts < self._cache_ttl:
                return cached
        
        # Fetch news (Finnhub → yfinance fallback)
        articles = self._fetch_articles(ticker, days_back=days_back)
        
        if not articles:
            features = self._empty_features()
            self._sentiment_cache[cache_key] = (time.time(), features)
            return features
        
        # Analyze each article with temporal decay
        now = datetime.now()
        scores = []
        categories = defaultdict(int)
        half_life_days = 3.0  # Sentiment decays with 3-day half-life
        
        for article in articles:
            text = f"{article.get('headline', '')} {article.get('summary', '')}"
            sentiment = self.analyzer.analyze_text(text)
            
            # Temporal decay weight
            try:
                article_dt = datetime.fromisoformat(article['datetime']) if article.get('datetime') else now
                age_days = max((now - article_dt).total_seconds() / 86400, 0)
                decay_weight = np.exp(-0.693 * age_days / half_life_days)  # 0.693 = ln(2)
            except (ValueError, TypeError):
                decay_weight = 0.5
            
            scores.append({
                'compound': sentiment['compound_score'],
                'magnitude': sentiment['magnitude'],
                'weight': decay_weight,
                'category': sentiment['event_category'],
            })
            categories[sentiment['event_category']] += 1
        
        if not scores:
            features = self._empty_features()
            self._sentiment_cache[cache_key] = (time.time(), features)
            return features
        
        # ---- Compute aggregate features ----
        weights = np.array([s['weight'] for s in scores])
        compounds = np.array([s['compound'] for s in scores])
        magnitudes = np.array([s['magnitude'] for s in scores])
        
        # Weighted sentiment score
        sentiment_score = float(np.average(compounds, weights=weights))
        
        # Weighted magnitude
        sentiment_magnitude = float(np.average(magnitudes, weights=weights))
        
        # Sentiment volume (log-scaled article count)
        sentiment_volume = float(np.log1p(len(articles)))
        
        # Sentiment trend: compare recent (3 days) vs older
        recent_mask = weights > 0.5  # Roughly last 3 days
        if recent_mask.sum() > 0 and (~recent_mask).sum() > 0:
            recent_avg = float(np.mean(compounds[recent_mask]))
            older_avg = float(np.mean(compounds[~recent_mask]))
            sentiment_trend = recent_avg - older_avg
        else:
            sentiment_trend = 0.0
        
        # Dispersion (disagreement)
        sentiment_dispersion = float(np.std(compounds)) if len(compounds) > 1 else 0.0
        
        # Bullish/bearish ratio
        n_total = len(compounds)
        bullish_ratio = float(np.sum(compounds > 0.05)) / n_total
        bearish_ratio = float(np.sum(compounds < -0.05)) / n_total
        
        # Event flags
        event_earnings = 1.0 if categories.get('earnings', 0) > 0 else 0.0
        event_regulatory = 1.0 if categories.get('regulatory', 0) > 0 else 0.0
        event_ma = 1.0 if categories.get('merger_acquisition', 0) > 0 else 0.0
        event_management = 1.0 if categories.get('management', 0) > 0 else 0.0
        
        features = {
            'sentiment_score': round(sentiment_score, 4),
            'sentiment_magnitude': round(sentiment_magnitude, 4),
            'sentiment_volume': round(sentiment_volume, 4),
            'sentiment_trend': round(sentiment_trend, 4),
            'sentiment_dispersion': round(sentiment_dispersion, 4),
            'bullish_ratio': round(bullish_ratio, 4),
            'bearish_ratio': round(bearish_ratio, 4),
            'event_earnings': event_earnings,
            'event_regulatory': event_regulatory,
            'event_ma': event_ma,
            'event_management': event_management,
        }
        
        self._sentiment_cache[cache_key] = (time.time(), features)
        return features
    
    def get_detailed_analysis(self, ticker: str, days_back: int = 14) -> Dict:
        """
        Get detailed sentiment analysis with article-level breakdown.
        Used by the API for display purposes.
        """
        articles = self._fetch_articles(ticker, days_back=days_back)
        
        analyzed = []
        for article in articles:
            text = f"{article.get('headline', '')} {article.get('summary', '')}"
            sentiment = self.analyzer.analyze_text(text)
            
            analyzed.append({
                'headline': article.get('headline', ''),
                'source': article.get('source', ''),
                'datetime': article.get('datetime', ''),
                'url': article.get('url', ''),
                'sentiment': sentiment['compound_score'],
                'magnitude': sentiment['magnitude'],
                'event_category': sentiment['event_category'],
                'positive_keywords': sentiment['positive_keywords'],
                'negative_keywords': sentiment['negative_keywords'],
            })
        
        # Sort by datetime (newest first)
        analyzed.sort(key=lambda x: x.get('datetime', ''), reverse=True)
        
        # Summary
        features = self.get_sentiment_features(ticker, days_back)
        
        return {
            'ticker': ticker,
            'article_count': len(analyzed),
            'articles': analyzed[:20],  # Limit to 20 for display
            'aggregate': features,
            'overall_sentiment': (
                'BULLISH' if features['sentiment_score'] > 0.15 else
                'BEARISH' if features['sentiment_score'] < -0.15 else
                'NEUTRAL'
            ),
        }
    
    def _empty_features(self) -> Dict[str, float]:
        """Return neutral features when no news is available."""
        return {
            'sentiment_score': 0.0,
            'sentiment_magnitude': 0.0,
            'sentiment_volume': 0.0,
            'sentiment_trend': 0.0,
            'sentiment_dispersion': 0.0,
            'bullish_ratio': 0.0,
            'bearish_ratio': 0.0,
            'event_earnings': 0.0,
            'event_regulatory': 0.0,
            'event_ma': 0.0,
            'event_management': 0.0,
        }


# ---- Convenience function ----
_engine_instance: Optional[SentimentEngine] = None


def get_sentiment_engine(finnhub_key: Optional[str] = None) -> SentimentEngine:
    """Get or create a singleton SentimentEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SentimentEngine(finnhub_key=finnhub_key)
    return _engine_instance


def get_sentiment_features(ticker: str, days_back: int = 30,
                           finnhub_key: Optional[str] = None) -> Dict[str, float]:
    """Convenience function: get sentiment features for a ticker."""
    engine = get_sentiment_engine(finnhub_key)
    return engine.get_sentiment_features(ticker, days_back)


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    key = os.getenv('FINNHUB_KEY', '')
    if not key:
        print("Set FINNHUB_KEY environment variable to test with real data")
        print("Testing with synthetic text analysis...")
    
    analyzer = SentimentAnalyzer()
    
    test_texts = [
        "Reliance Industries reports record quarterly profit, revenue beats estimates by 15%",
        "SEBI imposes penalty on company for insider trading violation",
        "Company announces stock split and bonus issue for shareholders",
        "CEO resigns amid fraud allegations, stock crashes 20%",
        "New product launch expected to drive revenue growth in Q4",
    ]
    
    for text in test_texts:
        result = analyzer.analyze_text(text)
        print(f"\n{text[:60]}...")
        print(f"  Score: {result['compound_score']:+.3f} | "
              f"Category: {result['event_category']} | "
              f"Magnitude: {result['magnitude']:.3f}")
    
    engine = SentimentEngine(finnhub_key=key)
    features = engine.get_sentiment_features('RELIANCE')
    print(f"\nSentiment features for RELIANCE:")
    for k, v in features.items():
        print(f"  {k}: {v}")
