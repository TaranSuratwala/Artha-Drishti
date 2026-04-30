# """
# News Provider Service
# ======================
# Multi-source news aggregation for stock market intelligence.
# Supports: NewsAPI, Finnhub, AlphaVantage

# Configure API keys via environment variables:
# - NEWSAPI_KEY
# - FINNHUB_KEY
# - ALPHAVANTAGE_KEY
# """

# import os
# import logging
# import requests
# from abc import ABC, abstractmethod
# from dataclasses import dataclass, field
# from typing import List, Dict, Optional, Any
# from datetime import datetime, timedelta
# from functools import lru_cache
# import time

# logger = logging.getLogger(__name__)

# # Rate limiting settings
# RATE_LIMIT_DELAY = 1.0  # seconds between requests


# @dataclass
# class NewsArticle:
#     """Represents a news article"""
#     title: str
#     description: str
#     url: str
#     source: str
#     published_at: str
#     image_url: Optional[str] = None
#     sentiment: Optional[str] = None  # positive, negative, neutral
#     relevance_score: float = 0.0
#     tickers: List[str] = field(default_factory=list)
    
#     def to_dict(self) -> Dict[str, Any]:
#         return {
#             'title': self.title,
#             'description': self.description,
#             'url': self.url,
#             'source': self.source,
#             'published_at': self.published_at,
#             'image_url': self.image_url,
#             'sentiment': self.sentiment,
#             'relevance_score': self.relevance_score,
#             'tickers': self.tickers
#         }


# class NewsProvider(ABC):
#     """Abstract base class for news providers"""
    
#     @abstractmethod
#     def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news articles for a query"""
#         pass
    
#     @abstractmethod
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news for a specific stock symbol"""
#         pass
    
#     @abstractmethod
#     def is_available(self) -> bool:
#         """Check if the provider is configured and available"""
#         pass


# class NewsAPIProvider(NewsProvider):
#     """NewsAPI.org provider - Great for general market news"""
    
#     BASE_URL = "https://newsapi.org/v2"
    
#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or os.getenv('NEWSAPI_KEY', '')
#         self._last_request = 0
    
#     def is_available(self) -> bool:
#         return bool(self.api_key)
    
#     def _rate_limit(self):
#         """Enforce rate limiting"""
#         elapsed = time.time() - self._last_request
#         if elapsed < RATE_LIMIT_DELAY:
#             time.sleep(RATE_LIMIT_DELAY - elapsed)
#         self._last_request = time.time()
    
#     def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch general news matching query"""
#         if not self.is_available():
#             logger.warning("NewsAPI key not configured")
#             return []
        
#         try:
#             self._rate_limit()
            
#             params = {
#                 'q': query,
#                 'language': 'en',
#                 'sortBy': 'publishedAt',
#                 'pageSize': min(limit, 100),
#                 'apiKey': self.api_key
#             }
            
#             response = requests.get(
#                 f"{self.BASE_URL}/everything",
#                 params=params,
#                 timeout=10
#             )
#             response.raise_for_status()
#             data = response.json()
            
#             articles = []
#             for article in data.get('articles', []):
#                 articles.append(NewsArticle(
#                     title=article.get('title', ''),
#                     description=article.get('description', '') or '',
#                     url=article.get('url', ''),
#                     source=article.get('source', {}).get('name', 'Unknown'),
#                     published_at=article.get('publishedAt', ''),
#                     image_url=article.get('urlToImage')
#                 ))
            
#             return articles[:limit]
            
#         except Exception as e:
#             logger.error(f"NewsAPI error: {e}")
#             return []
    
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news for a specific stock"""
#         # Search for company name or stock symbol
#         query = f"{symbol} stock OR {symbol} shares"
#         articles = self.fetch_news(query, limit)
        
#         # Add ticker to articles
#         for article in articles:
#             article.tickers.append(symbol.upper())
        
#         return articles


# class FinnhubProvider(NewsProvider):
#     """Finnhub.io provider - Excellent for stock-specific news"""
    
#     BASE_URL = "https://finnhub.io/api/v1"
    
#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or os.getenv('FINNHUB_KEY', '')
#         self._last_request = 0
    
#     def is_available(self) -> bool:
#         return bool(self.api_key)
    
#     def _rate_limit(self):
#         elapsed = time.time() - self._last_request
#         if elapsed < RATE_LIMIT_DELAY:
#             time.sleep(RATE_LIMIT_DELAY - elapsed)
#         self._last_request = time.time()
    
#     def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch general market news"""
#         if not self.is_available():
#             logger.warning("Finnhub key not configured")
#             return []
        
#         try:
#             self._rate_limit()
            
#             # Finnhub general news endpoint
#             params = {
#                 'category': 'general',
#                 'token': self.api_key
#             }
            
#             response = requests.get(
#                 f"{self.BASE_URL}/news",
#                 params=params,
#                 timeout=10
#             )
#             response.raise_for_status()
#             data = response.json()
            
#             articles = []
#             for item in data[:limit]:
#                 articles.append(NewsArticle(
#                     title=item.get('headline', ''),
#                     description=item.get('summary', ''),
#                     url=item.get('url', ''),
#                     source=item.get('source', 'Finnhub'),
#                     published_at=datetime.fromtimestamp(
#                         item.get('datetime', 0)
#                     ).isoformat() if item.get('datetime') else '',
#                     image_url=item.get('image')
#                 ))
            
#             return articles
            
#         except Exception as e:
#             logger.error(f"Finnhub error: {e}")
#             return []
    
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news for a specific stock symbol"""
#         if not self.is_available():
#             return []
        
#         try:
#             self._rate_limit()
            
#             # For Indian stocks, try without suffix first
#             clean_symbol = symbol.replace('.NS', '').replace('.BO', '')
            
#             # Get date range (last 30 days)
#             to_date = datetime.now()
#             from_date = to_date - timedelta(days=30)
            
#             params = {
#                 'symbol': clean_symbol,
#                 'from': from_date.strftime('%Y-%m-%d'),
#                 'to': to_date.strftime('%Y-%m-%d'),
#                 'token': self.api_key
#             }
            
#             response = requests.get(
#                 f"{self.BASE_URL}/company-news",
#                 params=params,
#                 timeout=10
#             )
#             response.raise_for_status()
#             data = response.json()
            
#             articles = []
#             for item in data[:limit]:
#                 articles.append(NewsArticle(
#                     title=item.get('headline', ''),
#                     description=item.get('summary', ''),
#                     url=item.get('url', ''),
#                     source=item.get('source', 'Finnhub'),
#                     published_at=datetime.fromtimestamp(
#                         item.get('datetime', 0)
#                     ).isoformat() if item.get('datetime') else '',
#                     image_url=item.get('image'),
#                     tickers=[symbol.upper()]
#                 ))
            
#             return articles
            
#         except Exception as e:
#             logger.error(f"Finnhub stock news error for {symbol}: {e}")
#             return []


# class AlphaVantageProvider(NewsProvider):
#     """Alpha Vantage provider - Good for sentiment analysis"""
    
#     BASE_URL = "https://www.alphavantage.co/query"
    
#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or os.getenv('ALPHAVANTAGE_KEY', '')
#         self._last_request = 0
    
#     def is_available(self) -> bool:
#         return bool(self.api_key)
    
#     def _rate_limit(self):
#         # Alpha Vantage has stricter limits (5 requests/minute on free tier)
#         elapsed = time.time() - self._last_request
#         delay = 12.0  # 12 seconds between requests for safety
#         if elapsed < delay:
#             time.sleep(delay - elapsed)
#         self._last_request = time.time()
    
#     def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news with sentiment analysis"""
#         if not self.is_available():
#             logger.warning("AlphaVantage key not configured")
#             return []
        
#         try:
#             self._rate_limit()
            
#             params = {
#                 'function': 'NEWS_SENTIMENT',
#                 'topics': query,
#                 'limit': min(limit, 50),
#                 'apikey': self.api_key
#             }
            
#             response = requests.get(
#                 self.BASE_URL,
#                 params=params,
#                 timeout=15
#             )
#             response.raise_for_status()
#             data = response.json()
            
#             articles = []
#             for item in data.get('feed', [])[:limit]:
#                 # Extract sentiment
#                 sentiment_score = float(item.get('overall_sentiment_score', 0))
#                 if sentiment_score > 0.15:
#                     sentiment = 'positive'
#                 elif sentiment_score < -0.15:
#                     sentiment = 'negative'
#                 else:
#                     sentiment = 'neutral'
                
#                 articles.append(NewsArticle(
#                     title=item.get('title', ''),
#                     description=item.get('summary', ''),
#                     url=item.get('url', ''),
#                     source=item.get('source', 'AlphaVantage'),
#                     published_at=item.get('time_published', ''),
#                     image_url=item.get('banner_image'),
#                     sentiment=sentiment,
#                     relevance_score=float(item.get('relevance_score', 0))
#                 ))
            
#             return articles
            
#         except Exception as e:
#             logger.error(f"AlphaVantage error: {e}")
#             return []
    
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news for a specific stock with sentiment"""
#         if not self.is_available():
#             return []
        
#         try:
#             self._rate_limit()
            
#             clean_symbol = symbol.replace('.NS', '').replace('.BO', '')
            
#             params = {
#                 'function': 'NEWS_SENTIMENT',
#                 'tickers': clean_symbol,
#                 'limit': min(limit, 50),
#                 'apikey': self.api_key
#             }
            
#             response = requests.get(
#                 self.BASE_URL,
#                 params=params,
#                 timeout=15
#             )
#             response.raise_for_status()
#             data = response.json()
            
#             articles = []
#             for item in data.get('feed', [])[:limit]:
#                 # Extract sentiment
#                 sentiment_score = float(item.get('overall_sentiment_score', 0))
#                 if sentiment_score > 0.15:
#                     sentiment = 'positive'
#                 elif sentiment_score < -0.15:
#                     sentiment = 'negative'
#                 else:
#                     sentiment = 'neutral'
                
#                 # Extract ticker relevance
#                 tickers = []
#                 for ticker_data in item.get('ticker_sentiment', []):
#                     tickers.append(ticker_data.get('ticker', ''))
                
#                 articles.append(NewsArticle(
#                     title=item.get('title', ''),
#                     description=item.get('summary', ''),
#                     url=item.get('url', ''),
#                     source=item.get('source', 'AlphaVantage'),
#                     published_at=item.get('time_published', ''),
#                     image_url=item.get('banner_image'),
#                     sentiment=sentiment,
#                     relevance_score=float(item.get('relevance_score', 0)),
#                     tickers=tickers
#                 ))
            
#             return articles
            
#         except Exception as e:
#             logger.error(f"AlphaVantage stock news error for {symbol}: {e}")
#             return []


# class NewsAggregator:
#     """
#     Aggregates news from multiple providers.
#     Falls back to available providers if some are not configured.
#     """
    
#     def __init__(self):
#         self.providers: Dict[str, NewsProvider] = {
#             'newsapi': NewsAPIProvider(),
#             'finnhub': FinnhubProvider(),
#             'alphavantage': AlphaVantageProvider()
#         }
    
#     def get_available_providers(self) -> List[str]:
#         """Get list of configured providers"""
#         return [name for name, provider in self.providers.items() 
#                 if provider.is_available()]
    
#     def fetch_market_news(self, limit: int = 20) -> List[Dict]:
#         """Fetch general market news from all available sources"""
#         all_articles = []
        
#         for name, provider in self.providers.items():
#             if provider.is_available():
#                 try:
#                     articles = provider.fetch_news("stock market finance", limit // 2)
#                     for article in articles:
#                         article_dict = article.to_dict()
#                         article_dict['provider'] = name
#                         all_articles.append(article_dict)
#                 except Exception as e:
#                     logger.error(f"Error fetching from {name}: {e}")
        
#         # Sort by published date (newest first)
#         all_articles.sort(
#             key=lambda x: x.get('published_at', ''),
#             reverse=True
#         )
        
#         return all_articles[:limit]
    
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
#         """Fetch news for a specific stock from all available sources"""
#         all_articles = []
        
#         for name, provider in self.providers.items():
#             if provider.is_available():
#                 try:
#                     articles = provider.fetch_stock_news(symbol, limit // 2)
#                     for article in articles:
#                         article_dict = article.to_dict()
#                         article_dict['provider'] = name
#                         all_articles.append(article_dict)
#                 except Exception as e:
#                     logger.error(f"Error fetching {symbol} news from {name}: {e}")
        
#         # Sort by relevance then by date
#         all_articles.sort(
#             key=lambda x: (x.get('relevance_score', 0), x.get('published_at', '')),
#             reverse=True
#         )
        
#         return all_articles[:limit]
    
#     def fetch_portfolio_news(self, symbols: List[str], limit: int = 20) -> List[Dict]:
#         """Fetch news for multiple stocks in a portfolio"""
#         all_articles = []
#         per_stock_limit = max(3, limit // len(symbols)) if symbols else limit
        
#         for symbol in symbols:
#             articles = self.fetch_stock_news(symbol, per_stock_limit)
#             all_articles.extend(articles)
        
#         # Remove duplicates based on URL
#         seen_urls = set()
#         unique_articles = []
#         for article in all_articles:
#             if article['url'] not in seen_urls:
#                 seen_urls.add(article['url'])
#                 unique_articles.append(article)
        
#         # Sort by date
#         unique_articles.sort(
#             key=lambda x: x.get('published_at', ''),
#             reverse=True
#         )
        
#         return unique_articles[:limit]


# # Global instance
# _news_aggregator: Optional[NewsAggregator] = None


# def get_news_aggregator() -> NewsAggregator:
#     """Get or create the global news aggregator instance"""
#     global _news_aggregator
#     if _news_aggregator is None:
#         _news_aggregator = NewsAggregator()
#     return _news_aggregator


# if __name__ == "__main__":
#     # Test the news aggregator
#     aggregator = get_news_aggregator()
    
#     print("Available providers:", aggregator.get_available_providers())
    
#     print("\n--- Market News ---")
#     news = aggregator.fetch_market_news(limit=5)
#     for article in news:
#         print(f"- {article['title'][:60]}... ({article['source']})")
    
#     print("\n--- RELIANCE News ---")
#     stock_news = aggregator.fetch_stock_news("RELIANCE", limit=3)
#     for article in stock_news:
#         print(f"- {article['title'][:60]}... (Sentiment: {article.get('sentiment', 'N/A')})")











# """
# News Provider Service - Ready to Run with Finnhub
# ==================================================
# Pre-configured with your Finnhub API key for immediate use.

# For other providers, set environment variables:
# - NEWSAPI_KEY
# - ALPHAVANTAGE_KEY
# - MARKETAUX_KEY
# """

# import os
# import logging
# import requests
# from abc import ABC, abstractmethod
# from dataclasses import dataclass, field
# from typing import List, Dict, Optional, Any
# from datetime import datetime, timedelta
# import time

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Rate limiting settings
# RATE_LIMIT_DELAY = 1.0  # seconds between requests

# # HARDCODED API KEYS (for convenience - environment variables are more secure)
# FINNHUB_API_KEY = "d011btpr01qv3oh23b7gd011btpr01qv3oh23b80"


# @dataclass
# class NewsArticle:
#     """Represents a news article"""
#     title: str
#     description: str
#     url: str
#     source: str
#     published_at: str
#     image_url: Optional[str] = None
#     sentiment: Optional[str] = None  # positive, negative, neutral
#     relevance_score: float = 0.0
#     tickers: List[str] = field(default_factory=list)
    
#     def to_dict(self) -> Dict[str, Any]:
#         return {
#             'title': self.title,
#             'description': self.description,
#             'url': self.url,
#             'source': self.source,
#             'published_at': self.published_at,
#             'image_url': self.image_url,
#             'sentiment': self.sentiment,
#             'relevance_score': self.relevance_score,
#             'tickers': self.tickers
#         }


# class NewsProvider(ABC):
#     """Abstract base class for news providers"""
    
#     @abstractmethod
#     def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news articles for a query"""
#         pass
    
#     @abstractmethod
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news for a specific stock symbol"""
#         pass
    
#     @abstractmethod
#     def is_available(self) -> bool:
#         """Check if the provider is configured and available"""
#         pass


# class NewsAPIProvider(NewsProvider):
#     """NewsAPI.org provider - Great for general market news"""
    
#     BASE_URL = "https://newsapi.org/v2"
    
#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or os.getenv('NEWSAPI_KEY', '')
#         self._last_request = 0
    
#     def is_available(self) -> bool:
#         return bool(self.api_key)
    
#     def _rate_limit(self):
#         """Enforce rate limiting"""
#         elapsed = time.time() - self._last_request
#         if elapsed < RATE_LIMIT_DELAY:
#             time.sleep(RATE_LIMIT_DELAY - elapsed)
#         self._last_request = time.time()
    
#     def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch general news matching query"""
#         if not self.is_available():
#             logger.warning("NewsAPI key not configured")
#             return []
        
#         try:
#             self._rate_limit()
            
#             # Calculate date range (last 30 days for better results)
#             to_date = datetime.now()
#             from_date = to_date - timedelta(days=30)
            
#             params = {
#                 'q': query,
#                 'language': 'en',
#                 'sortBy': 'publishedAt',
#                 'pageSize': min(limit, 100),
#                 'from': from_date.strftime('%Y-%m-%d'),
#                 'to': to_date.strftime('%Y-%m-%d'),
#                 'apiKey': self.api_key
#             }
            
#             response = requests.get(
#                 f"{self.BASE_URL}/everything",
#                 params=params,
#                 timeout=10
#             )
            
#             # Check for API errors
#             if response.status_code == 429:
#                 logger.error("NewsAPI rate limit exceeded")
#                 return []
#             elif response.status_code == 401:
#                 logger.error("NewsAPI authentication failed - check API key")
#                 return []
            
#             response.raise_for_status()
#             data = response.json()
            
#             # Check for error in response
#             if data.get('status') == 'error':
#                 logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
#                 return []
            
#             articles = []
#             for article in data.get('articles', []):
#                 # Skip removed articles
#                 if article.get('title') == '[Removed]':
#                     continue
                    
#                 articles.append(NewsArticle(
#                     title=article.get('title', '') or 'No title',
#                     description=article.get('description', '') or article.get('content', '')[:200] if article.get('content') else '',
#                     url=article.get('url', ''),
#                     source=article.get('source', {}).get('name', 'Unknown'),
#                     published_at=article.get('publishedAt', ''),
#                     image_url=article.get('urlToImage')
#                 ))
            
#             logger.info(f"NewsAPI fetched {len(articles)} articles for query: {query}")
#             return articles[:limit]
            
#         except requests.exceptions.Timeout:
#             logger.error("NewsAPI request timeout")
#             return []
#         except requests.exceptions.RequestException as e:
#             logger.error(f"NewsAPI request error: {e}")
#             return []
#         except Exception as e:
#             logger.error(f"NewsAPI unexpected error: {e}")
#             return []
    
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news for a specific stock"""
#         # Search for company name or stock symbol
#         query = f"{symbol} stock"
#         articles = self.fetch_news(query, limit)
        
#         # Add ticker to articles
#         for article in articles:
#             if symbol.upper() not in article.tickers:
#                 article.tickers.append(symbol.upper())
        
#         return articles


# class FinnhubProvider(NewsProvider):
#     """Finnhub.io provider - Excellent for stock-specific news"""
    
#     BASE_URL = "https://finnhub.io/api/v1"
    
#     def __init__(self, api_key: Optional[str] = None):
#         # Use hardcoded key if no key provided
#         self.api_key = api_key or os.getenv('FINNHUB_KEY', '') or FINNHUB_API_KEY
#         self._last_request = 0
    
#     def is_available(self) -> bool:
#         return bool(self.api_key)
    
#     def _rate_limit(self):
#         elapsed = time.time() - self._last_request
#         if elapsed < RATE_LIMIT_DELAY:
#             time.sleep(RATE_LIMIT_DELAY - elapsed)
#         self._last_request = time.time()
    
#     def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch general market news"""
#         if not self.is_available():
#             logger.warning("Finnhub key not configured")
#             return []
        
#         try:
#             self._rate_limit()
            
#             # Finnhub general news endpoint
#             params = {
#                 'category': 'general',
#                 'token': self.api_key
#             }
            
#             response = requests.get(
#                 f"{self.BASE_URL}/news",
#                 params=params,
#                 timeout=10
#             )
            
#             if response.status_code == 429:
#                 logger.error("Finnhub rate limit exceeded")
#                 return []
#             elif response.status_code == 401:
#                 logger.error("Finnhub authentication failed - check API key")
#                 return []
            
#             response.raise_for_status()
#             data = response.json()
            
#             # Finnhub returns a list directly
#             if not isinstance(data, list):
#                 logger.error(f"Finnhub unexpected response format: {type(data)}")
#                 return []
            
#             articles = []
#             for item in data[:limit]:
#                 articles.append(NewsArticle(
#                     title=item.get('headline', 'No title'),
#                     description=item.get('summary', ''),
#                     url=item.get('url', ''),
#                     source=item.get('source', 'Finnhub'),
#                     published_at=datetime.fromtimestamp(
#                         item.get('datetime', 0)
#                     ).isoformat() if item.get('datetime') else '',
#                     image_url=item.get('image')
#                 ))
            
#             logger.info(f"Finnhub fetched {len(articles)} general news articles")
#             return articles
            
#         except requests.exceptions.Timeout:
#             logger.error("Finnhub request timeout")
#             return []
#         except Exception as e:
#             logger.error(f"Finnhub error: {e}")
#             return []
    
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news for a specific stock symbol"""
#         if not self.is_available():
#             return []
        
#         try:
#             self._rate_limit()
            
#             # Clean symbol - remove exchange suffixes
#             clean_symbol = symbol.replace('.NS', '').replace('.BO', '').upper()
            
#             # Get date range (last 30 days)
#             to_date = datetime.now()
#             from_date = to_date - timedelta(days=30)
            
#             params = {
#                 'symbol': clean_symbol,
#                 'from': from_date.strftime('%Y-%m-%d'),
#                 'to': to_date.strftime('%Y-%m-%d'),
#                 'token': self.api_key
#             }
            
#             response = requests.get(
#                 f"{self.BASE_URL}/company-news",
#                 params=params,
#                 timeout=10
#             )
            
#             if response.status_code == 404:
#                 logger.warning(f"Finnhub: Symbol {clean_symbol} not found")
#                 return []
            
#             response.raise_for_status()
#             data = response.json()
            
#             if not isinstance(data, list):
#                 logger.error(f"Finnhub unexpected response for {clean_symbol}")
#                 return []
            
#             articles = []
#             for item in data[:limit]:
#                 articles.append(NewsArticle(
#                     title=item.get('headline', 'No title'),
#                     description=item.get('summary', ''),
#                     url=item.get('url', ''),
#                     source=item.get('source', 'Finnhub'),
#                     published_at=datetime.fromtimestamp(
#                         item.get('datetime', 0)
#                     ).isoformat() if item.get('datetime') else '',
#                     image_url=item.get('image'),
#                     tickers=[symbol.upper()]
#                 ))
            
#             logger.info(f"Finnhub fetched {len(articles)} articles for {symbol}")
#             return articles
            
#         except Exception as e:
#             logger.error(f"Finnhub stock news error for {symbol}: {e}")
#             return []


# class AlphaVantageProvider(NewsProvider):
#     """Alpha Vantage provider - Good for sentiment analysis"""
    
#     BASE_URL = "https://www.alphavantage.co/query"
    
#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or os.getenv('ALPHAVANTAGE_KEY', '')
#         self._last_request = 0
    
#     def is_available(self) -> bool:
#         return bool(self.api_key)
    
#     def _rate_limit(self):
#         # Alpha Vantage has stricter limits (5 requests/minute on free tier)
#         elapsed = time.time() - self._last_request
#         delay = 12.0  # 12 seconds between requests for safety
#         if elapsed < delay:
#             time.sleep(delay - elapsed)
#         self._last_request = time.time()
    
#     def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news with sentiment analysis"""
#         if not self.is_available():
#             logger.warning("AlphaVantage key not configured")
#             return []
        
#         try:
#             self._rate_limit()
            
#             # Use financial_markets as default topic
#             topic = 'financial_markets'
            
#             params = {
#                 'function': 'NEWS_SENTIMENT',
#                 'topics': topic,
#                 'limit': min(limit, 50),
#                 'sort': 'LATEST',
#                 'apikey': self.api_key
#             }
            
#             response = requests.get(
#                 self.BASE_URL,
#                 params=params,
#                 timeout=15
#             )
            
#             if response.status_code == 429:
#                 logger.error("AlphaVantage rate limit exceeded")
#                 return []
            
#             response.raise_for_status()
#             data = response.json()
            
#             # Check for API limit message
#             if 'Note' in data or 'Information' in data:
#                 logger.error(f"AlphaVantage API limit: {data.get('Note') or data.get('Information')}")
#                 return []
            
#             if 'Error Message' in data:
#                 logger.error(f"AlphaVantage error: {data.get('Error Message')}")
#                 return []
            
#             articles = []
#             for item in data.get('feed', [])[:limit]:
#                 # Extract sentiment with proper error handling
#                 try:
#                     sentiment_score = float(item.get('overall_sentiment_score', 0))
#                     if sentiment_score > 0.15:
#                         sentiment = 'positive'
#                     elif sentiment_score < -0.15:
#                         sentiment = 'negative'
#                     else:
#                         sentiment = 'neutral'
#                 except (ValueError, TypeError):
#                     sentiment = 'neutral'
#                     sentiment_score = 0.0
                
#                 # Get tickers mentioned
#                 tickers = []
#                 for ticker_data in item.get('ticker_sentiment', []):
#                     ticker = ticker_data.get('ticker', '')
#                     if ticker:
#                         tickers.append(ticker)
                
#                 articles.append(NewsArticle(
#                     title=item.get('title', 'No title'),
#                     description=item.get('summary', '')[:500] if item.get('summary') else '',
#                     url=item.get('url', ''),
#                     source=item.get('source', 'AlphaVantage'),
#                     published_at=item.get('time_published', ''),
#                     image_url=item.get('banner_image'),
#                     sentiment=sentiment,
#                     relevance_score=sentiment_score,
#                     tickers=tickers
#                 ))
            
#             logger.info(f"AlphaVantage fetched {len(articles)} articles with sentiment")
#             return articles
            
#         except requests.exceptions.Timeout:
#             logger.error("AlphaVantage request timeout")
#             return []
#         except Exception as e:
#             logger.error(f"AlphaVantage error: {e}")
#             return []
    
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news for a specific stock with sentiment"""
#         if not self.is_available():
#             return []
        
#         try:
#             self._rate_limit()
            
#             # Clean symbol
#             clean_symbol = symbol.replace('.NS', '').replace('.BO', '').upper()
            
#             params = {
#                 'function': 'NEWS_SENTIMENT',
#                 'tickers': clean_symbol,
#                 'limit': min(limit, 50),
#                 'sort': 'LATEST',
#                 'apikey': self.api_key
#             }
            
#             response = requests.get(
#                 self.BASE_URL,
#                 params=params,
#                 timeout=15
#             )
            
#             response.raise_for_status()
#             data = response.json()
            
#             # Check for errors
#             if 'Note' in data or 'Information' in data:
#                 logger.error(f"AlphaVantage API limit reached")
#                 return []
            
#             articles = []
#             for item in data.get('feed', [])[:limit]:
#                 # Extract sentiment
#                 try:
#                     sentiment_score = float(item.get('overall_sentiment_score', 0))
#                     if sentiment_score > 0.15:
#                         sentiment = 'positive'
#                     elif sentiment_score < -0.15:
#                         sentiment = 'negative'
#                     else:
#                         sentiment = 'neutral'
#                 except (ValueError, TypeError):
#                     sentiment = 'neutral'
#                     sentiment_score = 0.0
                
#                 # Extract ticker relevance
#                 tickers = []
#                 ticker_relevance = 0.0
#                 for ticker_data in item.get('ticker_sentiment', []):
#                     ticker = ticker_data.get('ticker', '')
#                     if ticker:
#                         tickers.append(ticker)
#                         if ticker.upper() == clean_symbol:
#                             try:
#                                 ticker_relevance = float(ticker_data.get('relevance_score', 0))
#                             except (ValueError, TypeError):
#                                 ticker_relevance = 0.0
                
#                 articles.append(NewsArticle(
#                     title=item.get('title', 'No title'),
#                     description=item.get('summary', '')[:500] if item.get('summary') else '',
#                     url=item.get('url', ''),
#                     source=item.get('source', 'AlphaVantage'),
#                     published_at=item.get('time_published', ''),
#                     image_url=item.get('banner_image'),
#                     sentiment=sentiment,
#                     relevance_score=ticker_relevance,
#                     tickers=tickers if tickers else [symbol.upper()]
#                 ))
            
#             logger.info(f"AlphaVantage fetched {len(articles)} articles for {symbol}")
#             return articles
            
#         except Exception as e:
#             logger.error(f"AlphaVantage stock news error for {symbol}: {e}")
#             return []


# class MarketAuxProvider(NewsProvider):
#     """MarketAux provider - Free tier available, good coverage"""
    
#     BASE_URL = "https://api.marketaux.com/v1"
    
#     def __init__(self, api_key: Optional[str] = None):
#         self.api_key = api_key or os.getenv('MARKETAUX_KEY', '')
#         self._last_request = 0
    
#     def is_available(self) -> bool:
#         return bool(self.api_key)
    
#     def _rate_limit(self):
#         elapsed = time.time() - self._last_request
#         if elapsed < RATE_LIMIT_DELAY:
#             time.sleep(RATE_LIMIT_DELAY - elapsed)
#         self._last_request = time.time()
    
#     def fetch_news(self, query: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch general news"""
#         if not self.is_available():
#             logger.warning("MarketAux key not configured")
#             return []
        
#         try:
#             self._rate_limit()
            
#             params = {
#                 'search': query,
#                 'filter_entities': 'true',
#                 'language': 'en',
#                 'limit': min(limit, 100),
#                 'api_token': self.api_key
#             }
            
#             response = requests.get(
#                 f"{self.BASE_URL}/news/all",
#                 params=params,
#                 timeout=10
#             )
            
#             response.raise_for_status()
#             data = response.json()
            
#             articles = []
#             for item in data.get('data', []):
#                 # Extract tickers
#                 tickers = []
#                 for entity in item.get('entities', []):
#                     if entity.get('type') == 'equity':
#                         symbol = entity.get('symbol', '')
#                         if symbol:
#                             tickers.append(symbol)
                
#                 articles.append(NewsArticle(
#                     title=item.get('title', 'No title'),
#                     description=item.get('description', '') or item.get('snippet', ''),
#                     url=item.get('url', ''),
#                     source=item.get('source', 'MarketAux'),
#                     published_at=item.get('published_at', ''),
#                     image_url=item.get('image_url'),
#                     tickers=tickers
#                 ))
            
#             logger.info(f"MarketAux fetched {len(articles)} articles")
#             return articles[:limit]
            
#         except Exception as e:
#             logger.error(f"MarketAux error: {e}")
#             return []
    
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[NewsArticle]:
#         """Fetch news for specific stock"""
#         if not self.is_available():
#             return []
        
#         try:
#             self._rate_limit()
            
#             clean_symbol = symbol.replace('.NS', '').replace('.BO', '').upper()
            
#             params = {
#                 'symbols': clean_symbol,
#                 'filter_entities': 'true',
#                 'language': 'en',
#                 'limit': min(limit, 100),
#                 'api_token': self.api_key
#             }
            
#             response = requests.get(
#                 f"{self.BASE_URL}/news/all",
#                 params=params,
#                 timeout=10
#             )
            
#             response.raise_for_status()
#             data = response.json()
            
#             articles = []
#             for item in data.get('data', []):
#                 tickers = [symbol.upper()]
                
#                 articles.append(NewsArticle(
#                     title=item.get('title', 'No title'),
#                     description=item.get('description', '') or item.get('snippet', ''),
#                     url=item.get('url', ''),
#                     source=item.get('source', 'MarketAux'),
#                     published_at=item.get('published_at', ''),
#                     image_url=item.get('image_url'),
#                     tickers=tickers
#                 ))
            
#             logger.info(f"MarketAux fetched {len(articles)} articles for {symbol}")
#             return articles[:limit]
            
#         except Exception as e:
#             logger.error(f"MarketAux stock news error for {symbol}: {e}")
#             return []


# class NewsAggregator:
#     """
#     Aggregates news from multiple providers.
#     Falls back to available providers if some are not configured.
#     """
    
#     def __init__(self):
#         self.providers: Dict[str, NewsProvider] = {
#             'newsapi': NewsAPIProvider(),
#             'finnhub': FinnhubProvider(),
#             'alphavantage': AlphaVantageProvider(),
#             'marketaux': MarketAuxProvider()
#         }
    
#     def get_available_providers(self) -> List[str]:
#         """Get list of configured providers"""
#         available = [name for name, provider in self.providers.items() 
#                     if provider.is_available()]
#         logger.info(f"Available providers: {available}")
#         return available
    
#     def fetch_market_news(self, limit: int = 20) -> List[Dict]:
#         """Fetch general market news from all available sources"""
#         all_articles = []
#         available_providers = self.get_available_providers()
        
#         if not available_providers:
#             logger.warning("No news providers configured!")
#             return []
        
#         articles_per_provider = max(5, limit // len(available_providers))
        
#         for name, provider in self.providers.items():
#             if provider.is_available():
#                 try:
#                     logger.info(f"Fetching market news from {name}...")
#                     articles = provider.fetch_news("stock market finance", articles_per_provider)
#                     for article in articles:
#                         article_dict = article.to_dict()
#                         article_dict['provider'] = name
#                         all_articles.append(article_dict)
#                 except Exception as e:
#                     logger.error(f"Error fetching from {name}: {e}")
        
#         # Sort by published date (newest first)
#         all_articles.sort(
#             key=lambda x: x.get('published_at', ''),
#             reverse=True
#         )
        
#         logger.info(f"Total articles fetched: {len(all_articles)}")
#         return all_articles[:limit]
    
#     def fetch_stock_news(self, symbol: str, limit: int = 10) -> List[Dict]:
#         """Fetch news for a specific stock from all available sources"""
#         all_articles = []
#         available_providers = self.get_available_providers()
        
#         if not available_providers:
#             logger.warning("No news providers configured!")
#             return []
        
#         articles_per_provider = max(3, limit // len(available_providers))
        
#         for name, provider in self.providers.items():
#             if provider.is_available():
#                 try:
#                     logger.info(f"Fetching {symbol} news from {name}...")
#                     articles = provider.fetch_stock_news(symbol, articles_per_provider)
#                     for article in articles:
#                         article_dict = article.to_dict()
#                         article_dict['provider'] = name
#                         all_articles.append(article_dict)
#                 except Exception as e:
#                     logger.error(f"Error fetching {symbol} news from {name}: {e}")
        
#         # Sort by relevance then by date
#         all_articles.sort(
#             key=lambda x: (x.get('relevance_score', 0), x.get('published_at', '')),
#             reverse=True
#         )
        
#         logger.info(f"Total articles fetched for {symbol}: {len(all_articles)}")
#         return all_articles[:limit]
    
#     def fetch_portfolio_news(self, symbols: List[str], limit: int = 20) -> List[Dict]:
#         """Fetch news for multiple stocks in a portfolio"""
#         if not symbols:
#             logger.warning("No symbols provided for portfolio news")
#             return []
        
#         all_articles = []
#         per_stock_limit = max(3, limit // len(symbols))
        
#         for symbol in symbols:
#             logger.info(f"Fetching news for {symbol}...")
#             articles = self.fetch_stock_news(symbol, per_stock_limit)
#             all_articles.extend(articles)
        
#         # Remove duplicates based on URL
#         seen_urls = set()
#         unique_articles = []
#         for article in all_articles:
#             url = article.get('url', '')
#             if url and url not in seen_urls:
#                 seen_urls.add(url)
#                 unique_articles.append(article)
        
#         # Sort by date
#         unique_articles.sort(
#             key=lambda x: x.get('published_at', ''),
#             reverse=True
#         )
        
#         logger.info(f"Total unique articles for portfolio: {len(unique_articles)}")
#         return unique_articles[:limit]


# # Global instance
# _news_aggregator: Optional[NewsAggregator] = None


# def get_news_aggregator() -> NewsAggregator:
#     """Get or create the global news aggregator instance"""
#     global _news_aggregator
#     if _news_aggregator is None:
#         _news_aggregator = NewsAggregator()
#     return _news_aggregator


# if __name__ == "__main__":
#     # Test the news aggregator with Finnhub
#     print("="*70)
#     print("NEWS AGGREGATOR TEST - FINNHUB CONFIGURED")
#     print("="*70)
    
#     aggregator = get_news_aggregator()
    
#     print("\n📡 Available providers:", aggregator.get_available_providers())
    
#     print("\n" + "="*70)
#     print("📰 GENERAL MARKET NEWS (Latest)")
#     print("="*70)
#     market_news = aggregator.fetch_market_news(limit=5)
#     for i, article in enumerate(market_news, 1):
#         print(f"\n{i}. {article['title'][:70]}...")
#         print(f"   Source: {article['source']} | Provider: {article['provider']}")
#         print(f"   Published: {article.get('published_at', 'N/A')[:10]}")
#         if article.get('sentiment'):
#             print(f"   Sentiment: {article['sentiment']}")
    
#     print("\n" + "="*70)
#     print("📈 STOCK NEWS - AAPL (Apple Inc.)")
#     print("="*70)
#     stock_news = aggregator.fetch_stock_news("AAPL", limit=5)
#     for i, article in enumerate(stock_news, 1):
#         print(f"\n{i}. {article['title'][:70]}...")
#         print(f"   Source: {article['source']} | Provider: {article['provider']}")
#         print(f"   Published: {article.get('published_at', 'N/A')[:10]}")
#         print(f"   URL: {article['url'][:60]}...")
    
#     print("\n" + "="*70)
#     print("🚀 TEST COMPLETE - Finnhub is working!")
#     print("="*70)
#     print("\nℹ️  To add more providers, set these environment variables:")
#     print("   - NEWSAPI_KEY")
#     print("   - ALPHAVANTAGE_KEY (for sentiment analysis)")
#     print("   - MARKETAUX_KEY")



"""
News Display Service with Finnhub
==================================
Fetches and displays news articles as text using your Finnhub API key.
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict
import time

# Your Finnhub API Key
FINNHUB_API_KEY = "d011btpr01qv3oh23b7gd011btpr01qv3oh23b80"
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

def fetch_and_display_market_news(limit: int = 10):
    """
    Fetch and display general market news
    """
    print("="*80)
    print("📰 GENERAL MARKET NEWS")
    print("="*80)
    
    try:
        params = {
            'category': 'general',
            'token': FINNHUB_API_KEY
        }
        
        response = requests.get(
            f"{FINNHUB_BASE_URL}/news",
            params=params,
            timeout=10
        )
        
        if response.status_code == 401:
            print("❌ Authentication failed. Please check your API key.")
            return
        elif response.status_code == 429:
            print("❌ Rate limit exceeded. Please wait a moment.")
            return
        
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list):
            print("❌ Unexpected response format")
            return
        
        articles = data[:limit]
        
        if not articles:
            print("No news articles found.")
            return
        
        print(f"\nFound {len(articles)} news articles\n")
        
        for i, article in enumerate(articles, 1):
            print(f"\n{'─'*80}")
            print(f"📌 Article {i}/{len(articles)}")
            print(f"{'─'*80}")
            
            # Title
            title = article.get('headline', 'No title')
            print(f"\n🔸 TITLE:")
            print(f"   {title}")
            
            # Source and Date
            source = article.get('source', 'Unknown')
            timestamp = article.get('datetime', 0)
            if timestamp:
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            else:
                date_str = 'Unknown date'
            
            print(f"\n🔸 SOURCE: {source}")
            print(f"🔸 DATE: {date_str}")
            
            # Summary/Content
            summary = article.get('summary', '')
            if summary:
                print(f"\n🔸 NEWS CONTENT:")
                print(f"   {summary}")
            else:
                print(f"\n🔸 NEWS CONTENT:")
                print(f"   [No summary available]")
            
            # URL (for reference)
            url = article.get('url', '')
            if url:
                print(f"\n🔸 FULL ARTICLE: {url}")
        
        print(f"\n{'='*80}")
        print(f"✓ Displayed {len(articles)} articles")
        print(f"{'='*80}\n")
        
    except requests.exceptions.Timeout:
        print("❌ Request timeout. Please try again.")
    except Exception as e:
        print(f"❌ Error: {e}")


def fetch_and_display_stock_news(symbol: str, limit: int = 10):
    """
    Fetch and display news for a specific stock
    """
    print("="*80)
    print(f"📈 NEWS FOR {symbol.upper()}")
    print("="*80)
    
    try:
        # Clean symbol
        clean_symbol = symbol.replace('.NS', '').replace('.BO', '').upper()
        
        # Get date range (last 30 days)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=30)
        
        params = {
            'symbol': clean_symbol,
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d'),
            'token': FINNHUB_API_KEY
        }
        
        response = requests.get(
            f"{FINNHUB_BASE_URL}/company-news",
            params=params,
            timeout=10
        )
        
        if response.status_code == 404:
            print(f"❌ Symbol {clean_symbol} not found.")
            print(f"💡 Try a US stock symbol like AAPL, MSFT, GOOGL, TSLA")
            return
        elif response.status_code == 401:
            print("❌ Authentication failed. Please check your API key.")
            return
        elif response.status_code == 429:
            print("❌ Rate limit exceeded. Please wait a moment.")
            return
        
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list):
            print("❌ Unexpected response format")
            return
        
        articles = data[:limit]
        
        if not articles:
            print(f"No news articles found for {clean_symbol}.")
            print(f"💡 Try a popular US stock like AAPL, MSFT, or TSLA")
            return
        
        print(f"\nFound {len(articles)} news articles for {clean_symbol}\n")
        
        for i, article in enumerate(articles, 1):
            print(f"\n{'─'*80}")
            print(f"📌 Article {i}/{len(articles)}")
            print(f"{'─'*80}")
            
            # Title
            title = article.get('headline', 'No title')
            print(f"\n🔸 TITLE:")
            print(f"   {title}")
            
            # Source and Date
            source = article.get('source', 'Unknown')
            timestamp = article.get('datetime', 0)
            if timestamp:
                date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            else:
                date_str = 'Unknown date'
            
            print(f"\n🔸 SOURCE: {source}")
            print(f"🔸 DATE: {date_str}")
            
            # Summary/Content
            summary = article.get('summary', '')
            if summary:
                print(f"\n🔸 NEWS CONTENT:")
                # Wrap text for better readability
                words = summary.split()
                line = "   "
                for word in words:
                    if len(line) + len(word) + 1 > 80:
                        print(line)
                        line = "   " + word
                    else:
                        line += (" " + word) if line != "   " else word
                if line.strip():
                    print(line)
            else:
                print(f"\n🔸 NEWS CONTENT:")
                print(f"   [No summary available]")
            
            # Image
            image_url = article.get('image', '')
            if image_url:
                print(f"\n🔸 IMAGE: {image_url}")
            
            # URL (for reference)
            url = article.get('url', '')
            if url:
                print(f"\n🔸 FULL ARTICLE: {url}")
        
        print(f"\n{'='*80}")
        print(f"✓ Displayed {len(articles)} articles for {clean_symbol}")
        print(f"{'='*80}\n")
        
    except requests.exceptions.Timeout:
        print("❌ Request timeout. Please try again.")
    except Exception as e:
        print(f"❌ Error: {e}")


def fetch_and_display_multiple_stocks(symbols: List[str], articles_per_stock: int = 5):
    """
    Fetch and display news for multiple stocks
    """
    print("="*80)
    print(f"📊 NEWS FOR MULTIPLE STOCKS: {', '.join(symbols)}")
    print("="*80)
    
    for symbol in symbols:
        fetch_and_display_stock_news(symbol, limit=articles_per_stock)
        print("\n")
        time.sleep(1)  # Small delay between stocks


def interactive_menu():
    """
    Interactive menu for news browsing
    """
    while True:
        print("\n" + "="*80)
        print("📰 FINNHUB NEWS READER")
        print("="*80)
        print("\nChoose an option:")
        print("  1. General Market News")
        print("  2. Stock-Specific News (single stock)")
        print("  3. Multiple Stocks News")
        print("  4. Exit")
        print("\n" + "─"*80)
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            limit = input("How many articles? (default 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            fetch_and_display_market_news(limit=limit)
            
        elif choice == '2':
            symbol = input("Enter stock symbol (e.g., AAPL, MSFT, TSLA): ").strip()
            if symbol:
                limit = input("How many articles? (default 10): ").strip()
                limit = int(limit) if limit.isdigit() else 10
                fetch_and_display_stock_news(symbol, limit=limit)
            else:
                print("❌ Please enter a valid symbol")
                
        elif choice == '3':
            symbols_input = input("Enter stock symbols separated by commas (e.g., AAPL,MSFT,TSLA): ").strip()
            if symbols_input:
                symbols = [s.strip() for s in symbols_input.split(',')]
                articles_per_stock = input("Articles per stock? (default 5): ").strip()
                articles_per_stock = int(articles_per_stock) if articles_per_stock.isdigit() else 5
                fetch_and_display_multiple_stocks(symbols, articles_per_stock)
            else:
                print("❌ Please enter valid symbols")
                
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
            
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🚀 FINNHUB NEWS DISPLAY SERVICE")
    print("="*80)
    print(f"API Key: {FINNHUB_API_KEY[:20]}...")
    print(f"Base URL: {FINNHUB_BASE_URL}")
    
    # Quick demo
    print("\n📋 DEMO: Fetching latest market news...")
    fetch_and_display_market_news(limit=5)
    
    print("\n📋 DEMO: Fetching news for AAPL (Apple Inc.)...")
    fetch_and_display_stock_news("AAPL", limit=3)
    
    # Interactive menu
    print("\n" + "─"*80)
    start_interactive = input("\nWould you like to use the interactive menu? (y/n): ").strip().lower()
    if start_interactive == 'y':
        interactive_menu()
    else:
        print("\n✓ Done! Run this script again to see more news.\n")