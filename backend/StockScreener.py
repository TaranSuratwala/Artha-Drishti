# import pandas as pd
# import numpy as np
# from FeatureEngineering import StockFeatureEngineer
# import yfinance as yf
# from typing import Dict, List, Optional, Tuple, Any, Callable
# from dataclasses import dataclass, field, asdict
# from datetime import datetime, timedelta
# from functools import lru_cache
# import logging
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from collections import defaultdict
# import time
# import random
# import warnings
# import json
# import pickle
# from pathlib import Path
# from threading import Lock

# warnings.filterwarnings('ignore')

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# )
# logger = logging.getLogger(__name__)


# @dataclass
# class ScreenerConfig:
#     """Configuration for screener performance and behavior"""
#     max_workers: int = 1  # Changed to 1 to avoid rate limiting
#     cache_ttl_seconds: int = 3600
#     timeout_seconds: int = 60
#     retry_attempts: int = 3
#     batch_size: int = 10  # Process in smaller batches
#     enable_caching: bool = True
#     min_data_points: int = 50
#     rate_limit_delay: float = 0.5  # Delay between requests
#     max_retries_before_pause: int = 5  # Pause after this many retries
#     pause_duration: int = 60  # Seconds to pause


# @dataclass
# class StrategyDefinition:
#     """Definition of a trading strategy"""
#     name: str
#     description: str
#     strategy_type: str  # 'fundamental', 'technical', 'hybrid', 'custom'
#     conditions: Dict[str, Any]
#     created_at: datetime = field(default_factory=datetime.now)
#     updated_at: datetime = field(default_factory=datetime.now)
#     metadata: Dict[str, Any] = field(default_factory=dict)
    
#     def to_dict(self) -> Dict:
#         """Convert to dictionary for JSON serialization"""
#         data = asdict(self)
#         data['created_at'] = self.created_at.isoformat()
#         data['updated_at'] = self.updated_at.isoformat()
#         return data
    
#     @classmethod
#     def from_dict(cls, data: Dict) -> 'StrategyDefinition':
#         """Create from dictionary"""
#         data['created_at'] = datetime.fromisoformat(data['created_at'])
#         data['updated_at'] = datetime.fromisoformat(data['updated_at'])
#         return cls(**data)


# @dataclass
# class ScreenResult:
#     """Standardized screening result"""
#     ticker: str
#     signal: str
#     score: float
#     current_price: float
#     metadata: Dict[str, Any] = field(default_factory=dict)
#     timestamp: datetime = field(default_factory=datetime.now)
#     strategy_name: str = ""


# class RateLimiter:
#     """Rate limiter to prevent API throttling"""
    
#     def __init__(self, delay: float = 0.5):
#         self.delay = delay
#         self.last_request = 0
#         self.lock = Lock()
#         self.consecutive_fails = 0
#         self.max_fails = 5
    
#     def wait(self):
#         """Wait before making next request"""
#         with self.lock:
#             now = time.time()
#             elapsed = now - self.last_request
            
#             if elapsed < self.delay:
#                 sleep_time = self.delay - elapsed
#                 time.sleep(sleep_time)
            
#             self.last_request = time.time()
    
#     def report_failure(self):
#         """Report a failed request"""
#         with self.lock:
#             self.consecutive_fails += 1
#             if self.consecutive_fails >= self.max_fails:
#                 logger.warning(f"Too many consecutive failures. Pausing for 60 seconds...")
#                 time.sleep(60)
#                 self.consecutive_fails = 0
    
#     def report_success(self):
#         """Report a successful request"""
#         with self.lock:
#             self.consecutive_fails = 0


# class CacheManager:
#     """Enhanced cache manager with TTL support"""
    
#     def __init__(self, ttl_seconds: int = 3600):
#         self.cache = {}
#         self.timestamps = {}
#         self.ttl = ttl_seconds
#         self.lock = Lock()
    
#     def get(self, key: str) -> Optional[Any]:
#         """Get cached value if not expired"""
#         with self.lock:
#             if key not in self.cache:
#                 return None
            
#             if time.time() - self.timestamps[key] > self.ttl:
#                 self.invalidate(key)
#                 return None
            
#             return self.cache[key]
    
#     def set(self, key: str, value: Any):
#         """Set cache value with timestamp"""
#         with self.lock:
#             self.cache[key] = value
#             self.timestamps[key] = time.time()
    
#     def invalidate(self, key: str):
#         """Remove key from cache"""
#         with self.lock:
#             self.cache.pop(key, None)
#             self.timestamps.pop(key, None)
    
#     def clear(self):
#         """Clear entire cache"""
#         with self.lock:
#             self.cache.clear()
#             self.timestamps.clear()


# class StockDataFetcher:
#     """Optimized data fetching with rate limiting and error handling"""
    
#     def __init__(self, config: ScreenerConfig):
#         self.config = config
#         self.cache = CacheManager(config.cache_ttl_seconds)
#         self.failed_tickers = set()
#         self.rate_limiter = RateLimiter(config.rate_limit_delay)
    
#     def fetch_ticker_info(self, ticker: str, use_cache: bool = True) -> Optional[Dict]:
#         """Fetch ticker info with caching and error handling"""
#         cache_key = f"info_{ticker}"
        
#         if use_cache and self.config.enable_caching:
#             cached = self.cache.get(cache_key)
#             if cached is not None:
#                 return cached
        
#         if ticker in self.failed_tickers:
#             return None
        
#         for attempt in range(self.config.retry_attempts):
#             try:
#                 self.rate_limiter.wait()
#                 stock = yf.Ticker(ticker + ".NS")
#                 info = stock.info
                
#                 if info and len(info) > 5:
#                     if self.config.enable_caching:
#                         self.cache.set(cache_key, info)
#                     self.rate_limiter.report_success()
#                     return info
                
#             except Exception as e:
#                 err_msg = str(e)
#                 if "Too Many Requests" in err_msg or "429" in err_msg:
#                     logger.debug(f"Rate limited on {ticker}, attempt {attempt + 1}")
#                     self.rate_limiter.report_failure()
#                 else:
#                     logger.debug(f"Error on {ticker}: {err_msg}")
                
#                 if attempt == self.config.retry_attempts - 1:
#                     self.failed_tickers.add(ticker)
                
#                 sleep_time = (2 ** (attempt + 1)) + random.uniform(0, 2)
#                 time.sleep(sleep_time)
        
#         return None
    
#     def fetch_ticker_history(self, ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
#         """Fetch historical data with caching"""
#         cache_key = f"history_{ticker}_{period}"
        
#         if self.config.enable_caching:
#             cached = self.cache.get(cache_key)
#             if cached is not None:
#                 return cached
        
#         try:
#             self.rate_limiter.wait()
#             stock = yf.Ticker(ticker + ".NS")
#             history = stock.history(period=period)
            
#             if len(history) < self.config.min_data_points:
#                 return None
            
#             history = history.reset_index()
#             history.columns = [c.lower() for c in history.columns]
            
#             if self.config.enable_caching:
#                 self.cache.set(cache_key, history)
            
#             self.rate_limiter.report_success()
#             return history
            
#         except Exception as e:
#             logger.debug(f"Error fetching history for {ticker}: {str(e)}")
#             self.rate_limiter.report_failure()
#             return None


# class StrategyManager:
#     """Manage custom and predefined trading strategies"""
    
#     def __init__(self, storage_path: str = "./strategies"):
#         self.storage_path = Path(storage_path)
#         self.storage_path.mkdir(exist_ok=True)
#         self.strategies: Dict[str, StrategyDefinition] = {}
#         self._load_predefined_strategies()
#         self._load_custom_strategies()
    
#     def _load_predefined_strategies(self):
#         """Load predefined popular strategies"""
        
#         # Piotroski F-Score Strategy
#         self.strategies['piotroski'] = StrategyDefinition(
#             name='piotroski',
#             description='Fundamental strength based on Piotroski F-Score (9-point scale)',
#             strategy_type='fundamental',
#             conditions={
#                 'min_score': 7,
#                 'scoring_criteria': [
#                     'profitability', 'leverage', 'liquidity', 'operating_efficiency'
#                 ]
#             },
#             metadata={
#                 'typical_holding_period': '6-12 months',
#                 'risk_level': 'low-medium',
#                 'recommended_rebalance': 'quarterly'
#             }
#         )
        
#         # Momentum Strategy
#         self.strategies['momentum'] = StrategyDefinition(
#             name='momentum',
#             description='Price momentum with volume confirmation',
#             strategy_type='technical',
#             conditions={
#                 'lookback_days': 20,
#                 'min_return': 5.0,
#                 'min_rsi': 30,
#                 'max_rsi': 70,
#                 'volume_surge_min': 1.2
#             },
#             metadata={
#                 'typical_holding_period': '1-3 months',
#                 'risk_level': 'medium-high',
#                 'recommended_rebalance': 'monthly'
#             }
#         )
        
#         # Value Investing Strategy
#         self.strategies['value'] = StrategyDefinition(
#             name='value',
#             description='Value investing with quality metrics',
#             strategy_type='fundamental',
#             conditions={
#                 'min_value_score': 3,
#                 'max_pe': 15,
#                 'max_pb': 2.5,
#                 'min_dividend_yield': 2,
#                 'min_roe': 15,
#                 'max_debt_equity': 80
#             },
#             metadata={
#                 'typical_holding_period': '12-24 months',
#                 'risk_level': 'low',
#                 'recommended_rebalance': 'semi-annually'
#             }
#         )
        
#         # Swing Trading Strategy
#         self.strategies['swing'] = StrategyDefinition(
#             name='swing',
#             description='Swing trading opportunities using MACD and RSI',
#             strategy_type='technical',
#             conditions={
#                 'rsi_range': (30, 70),
#                 'macd_crossover': True,
#                 'bollinger_bands': True,
#                 'volume_confirmation': True
#             },
#             metadata={
#                 'typical_holding_period': '1-4 weeks',
#                 'risk_level': 'medium',
#                 'recommended_rebalance': 'weekly'
#             }
#         )
        
#         # Breakout Strategy
#         self.strategies['breakout'] = StrategyDefinition(
#             name='breakout',
#             description='52-week high breakouts with volume surge',
#             strategy_type='technical',
#             conditions={
#                 'volume_threshold': 1.5,
#                 'lookback_period': 252,
#                 'max_distance_from_high': 3,
#                 'consolidation_max': 10
#             },
#             metadata={
#                 'typical_holding_period': '2-8 weeks',
#                 'risk_level': 'high',
#                 'recommended_rebalance': 'weekly'
#             }
#         )
        
#         # GARP (Growth at Reasonable Price)
#         self.strategies['garp'] = StrategyDefinition(
#             name='garp',
#             description='Growth at Reasonable Price - combines growth and value',
#             strategy_type='hybrid',
#             conditions={
#                 'max_peg_ratio': 1.5,
#                 'min_earnings_growth': 15,
#                 'max_pe': 25,
#                 'min_roe': 15,
#                 'min_revenue_growth': 10
#             },
#             metadata={
#                 'typical_holding_period': '6-18 months',
#                 'risk_level': 'medium',
#                 'recommended_rebalance': 'quarterly'
#             }
#         )
        
#         # Mean Reversion Strategy
#         self.strategies['mean_reversion'] = StrategyDefinition(
#             name='mean_reversion',
#             description='Oversold stocks likely to bounce back',
#             strategy_type='technical',
#             conditions={
#                 'max_rsi': 30,
#                 'bollinger_position': 'lower',
#                 'volume_increase': True,
#                 'above_200_sma': True
#             },
#             metadata={
#                 'typical_holding_period': '1-3 weeks',
#                 'risk_level': 'medium-high',
#                 'recommended_rebalance': 'weekly'
#             }
#         )
        
#         # Quality Dividend Strategy
#         self.strategies['dividend_quality'] = StrategyDefinition(
#             name='dividend_quality',
#             description='High-quality dividend stocks with sustainable payouts',
#             strategy_type='fundamental',
#             conditions={
#                 'min_dividend_yield': 3,
#                 'max_payout_ratio': 70,
#                 'min_dividend_growth_years': 5,
#                 'min_roe': 12,
#                 'max_debt_equity': 100,
#                 'min_free_cashflow': 0
#             },
#             metadata={
#                 'typical_holding_period': '24+ months',
#                 'risk_level': 'low',
#                 'recommended_rebalance': 'annually'
#             }
#         )
    
#     def _load_custom_strategies(self):
#         """Load custom strategies from storage"""
#         strategy_files = list(self.storage_path.glob("*.json"))
        
#         for file_path in strategy_files:
#             try:
#                 with open(file_path, 'r') as f:
#                     data = json.load(f)
#                     strategy = StrategyDefinition.from_dict(data)
#                     self.strategies[strategy.name] = strategy
#                     logger.info(f"Loaded custom strategy: {strategy.name}")
#             except Exception as e:
#                 logger.error(f"Error loading strategy from {file_path}: {e}")
    
#     def create_strategy(self, name: str, description: str, strategy_type: str,
#                        conditions: Dict[str, Any], metadata: Optional[Dict] = None) -> StrategyDefinition:
#         """Create a new custom strategy"""
        
#         if name in self.strategies:
#             raise ValueError(f"Strategy '{name}' already exists. Use update_strategy() to modify.")
        
#         strategy = StrategyDefinition(
#             name=name,
#             description=description,
#             strategy_type=strategy_type,
#             conditions=conditions,
#             metadata=metadata or {}
#         )
        
#         self.strategies[name] = strategy
#         self.save_strategy(name)
#         logger.info(f"Created new strategy: {name}")
        
#         return strategy
    
#     def update_strategy(self, name: str, **updates) -> StrategyDefinition:
#         """Update an existing strategy"""
        
#         if name not in self.strategies:
#             raise ValueError(f"Strategy '{name}' not found")
        
#         strategy = self.strategies[name]
        
#         for key, value in updates.items():
#             if hasattr(strategy, key):
#                 setattr(strategy, key, value)
        
#         strategy.updated_at = datetime.now()
#         self.save_strategy(name)
#         logger.info(f"Updated strategy: {name}")
        
#         return strategy
    
#     def save_strategy(self, name: str):
#         """Save strategy to disk"""
        
#         if name not in self.strategies:
#             raise ValueError(f"Strategy '{name}' not found")
        
#         strategy = self.strategies[name]
#         file_path = self.storage_path / f"{name}.json"
        
#         with open(file_path, 'w') as f:
#             json.dump(strategy.to_dict(), f, indent=2)
        
#         logger.info(f"Saved strategy to {file_path}")
    
#     def delete_strategy(self, name: str):
#         """Delete a strategy"""
        
#         if name not in self.strategies:
#             raise ValueError(f"Strategy '{name}' not found")
        
#         # Don't delete predefined strategies
#         predefined = ['piotroski', 'momentum', 'value', 'swing', 'breakout', 
#                      'garp', 'mean_reversion', 'dividend_quality']
        
#         if name in predefined:
#             raise ValueError(f"Cannot delete predefined strategy: {name}")
        
#         del self.strategies[name]
        
#         file_path = self.storage_path / f"{name}.json"
#         if file_path.exists():
#             file_path.unlink()
        
#         logger.info(f"Deleted strategy: {name}")
    
#     def get_strategy(self, name: str) -> StrategyDefinition:
#         """Get a strategy by name"""
        
#         if name not in self.strategies:
#             raise ValueError(f"Strategy '{name}' not found")
        
#         return self.strategies[name]
    
#     def list_strategies(self, strategy_type: Optional[str] = None) -> List[StrategyDefinition]:
#         """List all strategies, optionally filtered by type"""
        
#         strategies = list(self.strategies.values())
        
#         if strategy_type:
#             strategies = [s for s in strategies if s.strategy_type == strategy_type]
        
#         return sorted(strategies, key=lambda x: x.name)
    
#     def export_strategy(self, name: str, export_path: str):
#         """Export strategy to a file"""
        
#         if name not in self.strategies:
#             raise ValueError(f"Strategy '{name}' not found")
        
#         strategy = self.strategies[name]
#         export_file = Path(export_path)
        
#         with open(export_file, 'w') as f:
#             json.dump(strategy.to_dict(), f, indent=2)
        
#         logger.info(f"Exported strategy '{name}' to {export_path}")
    
#     def import_strategy(self, import_path: str) -> StrategyDefinition:
#         """Import strategy from a file"""
        
#         import_file = Path(import_path)
        
#         if not import_file.exists():
#             raise FileNotFoundError(f"File not found: {import_path}")
        
#         with open(import_file, 'r') as f:
#             data = json.load(f)
#             strategy = StrategyDefinition.from_dict(data)
        
#         if strategy.name in self.strategies:
#             logger.warning(f"Strategy '{strategy.name}' already exists, creating copy")
#             strategy.name = f"{strategy.name}_imported_{int(time.time())}"
        
#         self.strategies[strategy.name] = strategy
#         self.save_strategy(strategy.name)
#         logger.info(f"Imported strategy: {strategy.name}")
        
#         return strategy


# class AdvancedStockScreener:
#     """Production-ready stock screener with strategy support"""
    
#     def __init__(self, pipeline, config: Optional[ScreenerConfig] = None):
#         self.pipeline = pipeline
#         self.config = config or ScreenerConfig()
#         self.data_fetcher = StockDataFetcher(self.config)
#         self.strategy_manager = StrategyManager()
#         self.performance_stats = defaultdict(list)
    
#     def get_all_tickers_data(self) -> pd.DataFrame:
#         """Fetch latest data for all tickers from database"""
#         try:
#             raw_data = self.pipeline.get_latest_data(limit=None)
#             df = pd.DataFrame(raw_data)
            
#             if df.empty:
#                 logger.warning("No data retrieved from pipeline")
#                 return pd.DataFrame()
            
#             required_cols = ['ticker', 'close', 'volume']
#             if not all(col in df.columns for col in required_cols):
#                 logger.error(f"Missing required columns. Got: {df.columns.tolist()}")
#                 return pd.DataFrame()
            
#             df = df.drop_duplicates(subset=['ticker'])
#             df = df[df['close'] > 0]
#             df = df[df['volume'] > 0]
            
#             logger.info(f"Loaded {len(df)} tickers from database")
#             return df
            
#         except Exception as e:
#             logger.error(f"Error loading ticker data: {str(e)}")
#             return pd.DataFrame()
    
#     def calculate_piotroski_score(self, ticker: str, info: Optional[Dict] = None) -> Tuple[int, Dict]:
#         """Enhanced Piotroski F-Score calculation"""
#         try:
#             if info is None:
#                 info = self.data_fetcher.fetch_ticker_info(ticker)
#                 if info is None:
#                     return 0, {}
            
#             score = 0
#             details = {}
            
#             # Profitability (4 points)
#             profit_margin = info.get('profitMargins', 0)
#             if profit_margin > 0:
#                 score += 1
#                 details['positive_roa'] = True
            
#             op_cashflow = info.get('operatingCashflow', 0)
#             if op_cashflow > 0:
#                 score += 1
#                 details['positive_cashflow'] = True
            
#             roe = info.get('returnOnEquity', 0)
#             if roe > 0:
#                 score += 1
#                 details['positive_roe'] = True
            
#             net_income = info.get('netIncomeToCommon', 0)
#             if op_cashflow > net_income and net_income > 0:
#                 score += 1
#                 details['quality_earnings'] = True
            
#             # Leverage & Liquidity (3 points)
#             current_ratio = info.get('currentRatio', 0)
#             if current_ratio > 1.5:
#                 score += 1
#                 details['good_liquidity'] = True
            
#             debt_equity = info.get('debtToEquity', 100)
#             if debt_equity < 50:
#                 score += 1
#                 details['low_leverage'] = True
            
#             shares_outstanding = info.get('sharesOutstanding', 0)
#             if shares_outstanding > 0:
#                 score += 1
#                 details['no_dilution'] = True
            
#             # Operating Efficiency (2 points)
#             gross_margin = info.get('grossMargins', 0)
#             if gross_margin > 0.3:
#                 score += 1
#                 details['good_gross_margin'] = True
            
#             asset_turnover = info.get('assetTurnover', 0)
#             if asset_turnover > 0.5:
#                 score += 1
#                 details['good_asset_turnover'] = True
            
#             details['metrics'] = {
#                 'profit_margin': round(profit_margin * 100, 2) if profit_margin else 0,
#                 'roe': round(roe * 100, 2) if roe else 0,
#                 'current_ratio': round(current_ratio, 2),
#                 'debt_equity': round(debt_equity, 2),
#                 'gross_margin': round(gross_margin * 100, 2) if gross_margin else 0
#             }
            
#             return min(score, 9), details
            
#         except Exception as e:
#             logger.debug(f"Error calculating Piotroski for {ticker}: {str(e)}")
#             return 0, {}
    
#     def calculate_technical_indicators(self, history: pd.DataFrame) -> Optional[pd.DataFrame]:
#         """Calculate technical indicators"""
#         try:
#             engineer = StockFeatureEngineer(history)
#             df = engineer.add_technical_indicators()
#             return df.dropna()
#         except Exception as e:
#             logger.debug(f"Error calculating indicators: {str(e)}")
#             return None
    
#     def run_strategy(self, strategy_name: str, **overrides) -> pd.DataFrame:
#         """
#         Run a strategy by name with optional parameter overrides
        
#         Args:
#             strategy_name: Name of the strategy to run
#             **overrides: Parameters to override strategy defaults
#         """
        
#         strategy = self.strategy_manager.get_strategy(strategy_name)
        
#         # Merge strategy conditions with overrides
#         params = {**strategy.conditions, **overrides}
        
#         logger.info(f"Running strategy: {strategy_name}")
#         logger.info(f"Description: {strategy.description}")
        
#         start_time = time.time()
        
#         # Route to appropriate screener based on strategy type
#         if strategy_name == 'piotroski':
#             results = self._piotroski_scan(params)
#         elif strategy_name == 'momentum':
#             results = self._momentum_scan(params)
#         elif strategy_name == 'value':
#             results = self._value_scan(params)
#         elif strategy_name == 'swing':
#             results = self._swing_scan(params)
#         elif strategy_name == 'breakout':
#             results = self._breakout_scan(params)
#         elif strategy_name == 'garp':
#             results = self._garp_scan(params)
#         elif strategy_name == 'mean_reversion':
#             results = self._mean_reversion_scan(params)
#         elif strategy_name == 'dividend_quality':
#             results = self._dividend_quality_scan(params)
#         else:
#             # Custom strategy
#             results = self._custom_strategy_scan(strategy, params)
        
#         elapsed = time.time() - start_time
#         self.performance_stats[strategy_name].append(elapsed)
        
#         if not results.empty:
#             results['strategy_name'] = strategy_name
#             results['scan_timestamp'] = datetime.now()
        
#         logger.info(f"Strategy '{strategy_name}' completed in {elapsed:.2f}s. Found {len(results)} stocks.")
        
#         return results
    
#     def _piotroski_scan(self, params: Dict) -> pd.DataFrame:
#         """Piotroski screening logic"""
#         min_score = params.get('min_score', 7)
#         df = self.get_all_tickers_data()
        
#         if df.empty:
#             return pd.DataFrame()
        
#         results = []
        
#         # Process in batches to avoid overwhelming the API
#         for i in range(0, len(df), self.config.batch_size):
#             batch = df.iloc[i:i+self.config.batch_size]
            
#             for _, row in batch.iterrows():
#                 ticker = row['ticker']
#                 score, details = self.calculate_piotroski_score(ticker)
                
#                 if score >= min_score:
#                     results.append({
#                         'ticker': ticker,
#                         'piotroski_score': score,
#                         'current_price': row['close'],
#                         'volume': row['volume'],
#                         **details.get('metrics', {})
#                     })
            
#             # Small pause between batches
#             if i + self.config.batch_size < len(df):
#                 time.sleep(2)
        
#         if not results:
#             return pd.DataFrame()
        
#         return pd.DataFrame(results).sort_values('piotroski_score', ascending=False)
    
#     def _momentum_scan(self, params: Dict) -> pd.DataFrame:
#         """Momentum screening logic"""
#         lookback_days = params.get('lookback_days', 20)
#         min_return = params.get('min_return', 5.0)
#         min_rsi = params.get('min_rsi', 30)
#         max_rsi = params.get('max_rsi', 70)
        
#         results = []
#         tickers = self.get_all_tickers_data()['ticker'].unique()
        
#         for ticker in tickers[:100]:  # Limit for testing
#             try:
#                 history = pd.DataFrame(self.pipeline.get_ticker_history(ticker))
#                 if len(history) < lookback_days + 20:
#                     continue
                
#                 history = history.sort_values('date').tail(lookback_days + 20)
                
#                 start_price = history['close'].iloc[-(lookback_days+1)]
#                 end_price = history['close'].iloc[-1]
#                 momentum_return = ((end_price - start_price) / start_price) * 100
                
#                 avg_volume = history['volume'].iloc[:-5].mean()
#                 recent_volume = history['volume'].tail(5).mean()
#                 volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 0
                
#                 # RSI
#                 delta = history['close'].diff()
#                 gain = delta.where(delta > 0, 0).rolling(window=14).mean()
#                 loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
#                 rs = gain / loss
#                 rsi = 100 - (100 / (1 + rs))
#                 current_rsi = rsi.iloc[-1]
                
#                 if (momentum_return >= min_return and 
#                     volume_ratio > 1.2 and 
#                     min_rsi <= current_rsi <= max_rsi):
                    
#                     results.append({
#                         'ticker': ticker,
#                         'momentum_return_%': round(momentum_return, 2),
#                         'current_price': round(end_price, 2),
#                         'volume_surge': round(volume_ratio, 2),
#                         'rsi': round(current_rsi, 2),
#                         'signal': 'BUY' if current_rsi < 60 else 'WATCH'
#                     })
#             except Exception as e:
#                 logger.debug(f"Error in momentum scan for {ticker}: {e}")
#                 continue
        
#         if not results:
#             return pd.DataFrame()
        
#         return pd.DataFrame(results).sort_values('momentum_return_%', ascending=False)
    
#     def _value_scan(self, params: Dict) -> pd.DataFrame:
#         """Value investing screening logic"""
#         min_value_score = params.get('min_value_score', 3)
        
#         results = []
#         df = self.get_all_tickers_data()
        
#         for i in range(0, min(len(df), 100), self.config.batch_size):  # Limit for testing
#             batch = df.iloc[i:i+self.config.batch_size]
            
#             for _, row in batch.iterrows():
#                 try:
#                     ticker = row['ticker']
#                     info = self.data_fetcher.fetch_ticker_info(ticker)
                    
#                     if info is None:
#                         continue
                    
#                     pe = info.get('trailingPE', 999)
#                     pb = info.get('priceToBook', 999)
#                     dividend_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
#                     roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
#                     debt_equity = info.get('debtToEquity', 999)
                    
#                     criteria = {
#                         'undervalued_pe': 0 < pe < params.get('max_pe', 15),
#                         'undervalued_pb': 0 < pb < params.get('max_pb', 2.5),
#                         'good_dividend': dividend_yield > params.get('min_dividend_yield', 2),
#                         'strong_roe': roe > params.get('min_roe', 15),
#                         'low_debt': debt_equity < params.get('max_debt_equity', 80)
#                     }
                    
#                     value_score = sum(criteria.values())
                    
#                     if value_score >= min_value_score:
#                         results.append({
#                             'ticker': ticker,
#                             'value_score': value_score,
#                             'pe_ratio': round(pe, 2) if pe < 999 else None,
#                             'pb_ratio': round(pb, 2) if pb < 999 else None,
#                             'dividend_yield_%': round(dividend_yield, 2),
#                             'roe_%': round(roe, 2),
#                             'current_price': round(row['close'], 2)
#                         })
#                 except Exception as e:
#                     logger.debug(f"Error in value scan for {ticker}: {e}")
#                     continue
            
#             if i + self.config.batch_size < len(df):
#                 time.sleep(2)
        
#         if not results:
#             return pd.DataFrame()
        
#         return pd.DataFrame(results).sort_values('value_score', ascending=False)
    
#     def _swing_scan(self, params: Dict) -> pd.DataFrame:
#         """Swing trading screening logic"""
#         results = []
#         tickers = self.get_all_tickers_data()['ticker'].unique()
        
#         for ticker in tickers[:50]:  # Limit for testing
#             try:
#                 history = pd.DataFrame(self.pipeline.get_ticker_history(ticker))
#                 if len(history) < 100:
#                     continue
                
#                 history = history.sort_values('date').tail(100)
#                 df = self.calculate_technical_indicators(history)
                
#                 if df is None or len(df) < 20:
#                     continue
                
#                 current = df.iloc[-1]
#                 prev = df.iloc[-2]
                
#                 macd_hist = current.get('MACDh_12_26_9', 0)
#                 prev_macd_hist = prev.get('MACDh_12_26_9', 0)
#                 rsi = current.get('RSI_14', 50)
                
#                 # Bullish swing setup
#                 if macd_hist > 0 and prev_macd_hist <= 0 and 30 < rsi < 55:
#                     results.append({
#                         'ticker': ticker,
#                         'signal': 'BULLISH_SWING',
#                         'current_price': round(current['close'], 2),
#                         'rsi': round(rsi, 2),
#                         'macd_hist': round(macd_hist, 4)
#                     })
#             except Exception as e:
#                 logger.debug(f"Error in swing scan for {ticker}: {e}")
#                 continue
        
#         if not results:
#             return pd.DataFrame()
        
#         return pd.DataFrame(results)
    
#     def _breakout_scan(self, params: Dict) -> pd.DataFrame:
#         """Breakout screening logic"""
#         volume_threshold = params.get('volume_threshold', 1.5)
#         lookback_period = params.get('lookback_period', 252)
        
#         results = []
#         tickers = self.get_all_tickers_data()['ticker'].unique()
        
#         for ticker in tickers[:50]:  # Limit for testing
#             try:
#                 history = self.data_fetcher.fetch_ticker_history(ticker, period="1y")
#                 if history is None or len(history) < lookback_period:
#                     continue
                
#                 high_52w = history.tail(lookback_period)['high'].max()
#                 current_price = history['close'].iloc[-1]
#                 distance_from_high = ((high_52w - current_price) / high_52w) * 100
                
#                 avg_volume_50 = history.tail(50)['volume'].mean()
#                 recent_volume_5 = history.tail(5)['volume'].mean()
#                 volume_ratio = recent_volume_5 / avg_volume_50 if avg_volume_50 > 0 else 0
                
#                 if distance_from_high < 3 and volume_ratio > volume_threshold:
#                     results.append({
#                         'ticker': ticker,
#                         'signal': 'BREAKOUT',
#                         'current_price': round(current_price, 2),
#                         '52w_high': round(high_52w, 2),
#                         'distance_from_high_%': round(distance_from_high, 2),
#                         'volume_surge': round(volume_ratio, 2)
#                     })
#             except Exception as e:
#                 logger.debug(f"Error in breakout scan for {ticker}: {e}")
#                 continue
        
#         if not results:
#             return pd.DataFrame()
        
#         return pd.DataFrame(results).sort_values('volume_surge', ascending=False)
    
#     def _garp_scan(self, params: Dict) -> pd.DataFrame:
#         """GARP (Growth at Reasonable Price) screening"""
#         results = []
#         df = self.get_all_tickers_data()
        
#         for i in range(0, min(len(df), 50), self.config.batch_size):
#             batch = df.iloc[i:i+self.config.batch_size]
            
#             for _, row in batch.iterrows():
#                 try:
#                     ticker = row['ticker']
#                     info = self.data_fetcher.fetch_ticker_info(ticker)
                    
#                     if info is None:
#                         continue
                    
#                     peg = info.get('pegRatio', 999)
#                     pe = info.get('trailingPE', 999)
#                     roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
                    
#                     if (peg < params.get('max_peg_ratio', 1.5) and 
#                         pe < params.get('max_pe', 25) and 
#                         roe > params.get('min_roe', 15)):
                        
#                         results.append({
#                             'ticker': ticker,
#                             'peg_ratio': round(peg, 2),
#                             'pe_ratio': round(pe, 2),
#                             'roe_%': round(roe, 2),
#                             'current_price': round(row['close'], 2)
#                         })
#                 except Exception as e:
#                     logger.debug(f"Error in GARP scan for {ticker}: {e}")
#                     continue
            
#             if i + self.config.batch_size < len(df):
#                 time.sleep(2)
        
#         if not results:
#             return pd.DataFrame()
        
#         return pd.DataFrame(results).sort_values('peg_ratio')
    
#     def _mean_reversion_scan(self, params: Dict) -> pd.DataFrame:
#         """Mean reversion screening"""
#         results = []
#         tickers = self.get_all_tickers_data()['ticker'].unique()
        
#         for ticker in tickers[:50]:
#             try:
#                 history = pd.DataFrame(self.pipeline.get_ticker_history(ticker))
#                 if len(history) < 200:
#                     continue
                
#                 history = history.sort_values('date').tail(200)
#                 df = self.calculate_technical_indicators(history)
                
#                 if df is None or len(df) < 20:
#                     continue
                
#                 current = df.iloc[-1]
#                 rsi = current.get('RSI_14', 50)
#                 sma_200 = current.get('SMA_200', current['close'])
                
#                 if rsi < params.get('max_rsi', 30) and current['close'] > sma_200:
#                     results.append({
#                         'ticker': ticker,
#                         'signal': 'OVERSOLD',
#                         'current_price': round(current['close'], 2),
#                         'rsi': round(rsi, 2)
#                     })
#             except Exception as e:
#                 logger.debug(f"Error in mean reversion scan for {ticker}: {e}")
#                 continue
        
#         if not results:
#             return pd.DataFrame()
        
#         return pd.DataFrame(results).sort_values('rsi')
    
#     def _dividend_quality_scan(self, params: Dict) -> pd.DataFrame:
#         """Dividend quality screening"""
#         results = []
#         df = self.get_all_tickers_data()
        
#         for i in range(0, min(len(df), 50), self.config.batch_size):
#             batch = df.iloc[i:i+self.config.batch_size]
            
#             for _, row in batch.iterrows():
#                 try:
#                     ticker = row['ticker']
#                     info = self.data_fetcher.fetch_ticker_info(ticker)
                    
#                     if info is None:
#                         continue
                    
#                     div_yield = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
#                     payout = info.get('payoutRatio', 1) * 100 if info.get('payoutRatio') else 100
#                     roe = info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0
#                     debt_equity = info.get('debtToEquity', 999)
                    
#                     if (div_yield > params.get('min_dividend_yield', 3) and 
#                         payout < params.get('max_payout_ratio', 70) and 
#                         roe > params.get('min_roe', 12) and 
#                         debt_equity < params.get('max_debt_equity', 100)):
                        
#                         results.append({
#                             'ticker': ticker,
#                             'dividend_yield_%': round(div_yield, 2),
#                             'payout_ratio_%': round(payout, 2),
#                             'roe_%': round(roe, 2),
#                             'current_price': round(row['close'], 2)
#                         })
#                 except Exception as e:
#                     logger.debug(f"Error in dividend scan for {ticker}: {e}")
#                     continue
            
#             if i + self.config.batch_size < len(df):
#                 time.sleep(2)
        
#         if not results:
#             return pd.DataFrame()
        
#         return pd.DataFrame(results).sort_values('dividend_yield_%', ascending=False)
    
#     def _custom_strategy_scan(self, strategy: StrategyDefinition, params: Dict) -> pd.DataFrame:
#         """Execute custom strategy logic"""
#         logger.info(f"Executing custom strategy: {strategy.name}")
        
#         # This is a flexible custom scanner
#         # Users can define their own logic here
#         results = []
#         df = self.get_all_tickers_data()
        
#         for i in range(0, min(len(df), 50), self.config.batch_size):
#             batch = df.iloc[i:i+self.config.batch_size]
            
#             for _, row in batch.iterrows():
#                 try:
#                     ticker = row['ticker']
                    
#                     # Get data based on strategy type
#                     if strategy.strategy_type in ['fundamental', 'hybrid']:
#                         info = self.data_fetcher.fetch_ticker_info(ticker)
#                         if info is None:
#                             continue
                    
#                     if strategy.strategy_type in ['technical', 'hybrid']:
#                         history = pd.DataFrame(self.pipeline.get_ticker_history(ticker))
#                         if len(history) < 50:
#                             continue
                    
#                     # Example: Apply custom conditions
#                     passed = True
#                     metrics = {'ticker': ticker, 'current_price': row['close']}
                    
#                     # Add your custom logic here based on params
                    
#                     if passed:
#                         results.append(metrics)
                        
#                 except Exception as e:
#                     logger.debug(f"Error in custom scan for {ticker}: {e}")
#                     continue
            
#             if i + self.config.batch_size < len(df):
#                 time.sleep(2)
        
#         if not results:
#             return pd.DataFrame()
        
#         return pd.DataFrame(results)
    
#     def export_results(self, df: pd.DataFrame, filename: str, format: str = 'csv') -> bool:
#         """Export results to file"""
#         try:
#             if df.empty:
#                 logger.warning("No data to export")
#                 return False
            
#             df['scan_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
#             if format == 'csv':
#                 df.to_csv(filename, index=False)
#             elif format == 'excel':
#                 df.to_excel(filename, index=False, engine='openpyxl')
#             elif format == 'json':
#                 df.to_json(filename, orient='records', indent=2)
#             else:
#                 logger.error(f"Unsupported format: {format}")
#                 return False
            
#             logger.info(f"Results exported to {filename}")
#             return True
            
#         except Exception as e:
#             logger.error(f"Error exporting results: {str(e)}")
#             return False
    
#     def get_performance_stats(self) -> Dict[str, Any]:
#         """Get screener performance statistics"""
#         stats = {}
        
#         for strategy, times in self.performance_stats.items():
#             if times:
#                 stats[strategy] = {
#                     'avg_time': round(np.mean(times), 2),
#                     'min_time': round(min(times), 2),
#                     'max_time': round(max(times), 2),
#                     'total_runs': len(times)
#                 }
        
#         stats['cache'] = {
#             'size': len(self.data_fetcher.cache.cache),
#             'failed_tickers': len(self.data_fetcher.failed_tickers)
#         }
        
#         return stats


# # Example Usage
# if __name__ == "__main__":
#     from IntegratedPostGreSQL import NSEDataPipeline
    
#     # Database connection
#     DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"
    
#     # Initialize pipeline and screener
#     pipeline = NSEDataPipeline(DB_URL)
#     config = ScreenerConfig(
#         max_workers=1,
#         cache_ttl_seconds=1800,
#         rate_limit_delay=0.8,
#         batch_size=5,
#         enable_caching=True
#     )
    
#     screener = AdvancedStockScreener(pipeline, config)
    
#     # ===== EXAMPLE 1: List all available strategies =====
#     print("\n" + "="*70)
#     print("AVAILABLE STRATEGIES")
#     print("="*70)
    
#     strategies = screener.strategy_manager.list_strategies()
#     for strategy in strategies:
#         print(f"\n{strategy.name.upper()}")
#         print(f"  Type: {strategy.strategy_type}")
#         print(f"  Description: {strategy.description}")
#         print(f"  Risk Level: {strategy.metadata.get('risk_level', 'N/A')}")
#         print(f"  Holding Period: {strategy.metadata.get('typical_holding_period', 'N/A')}")
    
#     # ===== EXAMPLE 2: Run a predefined strategy =====
#     print("\n" + "="*70)
#     print("RUNNING MOMENTUM STRATEGY")
#     print("="*70)
    
#     results = screener.run_strategy('momentum', lookback_days=30, min_return=10.0)
#     if not results.empty:
#         print(f"\nFound {len(results)} stocks:")
#         print(results.head(10))
#         screener.export_results(results, 'momentum_results.csv')
    
#     # ===== EXAMPLE 3: Create a custom strategy =====
#     print("\n" + "="*70)
#     print("CREATING CUSTOM STRATEGY")
#     print("="*70)
    
#     custom_strategy = screener.strategy_manager.create_strategy(
#         name='my_quality_growth',
#         description='Quality stocks with growth potential',
#         strategy_type='hybrid',
#         conditions={
#             'min_roe': 18,
#             'max_pe': 20,
#             'min_revenue_growth': 15,
#             'max_debt_equity': 60,
#             'min_profit_margin': 12
#         },
#         metadata={
#             'typical_holding_period': '9-15 months',
#             'risk_level': 'medium',
#             'recommended_rebalance': 'quarterly'
#         }
#     )
    
#     print(f"Created strategy: {custom_strategy.name}")
#     print(f"Saved to: ./strategies/{custom_strategy.name}.json")
    
#     # ===== EXAMPLE 4: Run custom strategy =====
#     print("\n" + "="*70)
#     print("RUNNING CUSTOM STRATEGY")
#     print("="*70)
    
#     custom_results = screener.run_strategy('my_quality_growth')
#     if not custom_results.empty:
#         print(f"\nFound {len(custom_results)} stocks:")
#         print(custom_results.head())
    
#     # ===== EXAMPLE 5: Export and import strategies =====
#     print("\n" + "="*70)
#     print("EXPORTING STRATEGY")
#     print("="*70)
    
#     screener.strategy_manager.export_strategy('my_quality_growth', 'exported_strategy.json')
#     print("Strategy exported to: exported_strategy.json")
    
#     # ===== EXAMPLE 6: Compare multiple strategies =====
#     print("\n" + "="*70)
#     print("RUNNING MULTIPLE STRATEGIES FOR COMPARISON")
#     print("="*70)
    
#     strategy_comparison = []
    
#     for strategy_name in ['value', 'momentum', 'piotroski']:
#         print(f"\nRunning {strategy_name}...")
#         results = screener.run_strategy(strategy_name)
        
#         strategy_comparison.append({
#             'strategy': strategy_name,
#             'stocks_found': len(results),
#             'top_ticker': results['ticker'].iloc[0] if len(results) > 0 else None
#         })
    
#     comparison_df = pd.DataFrame(strategy_comparison)
#     print("\nStrategy Comparison:")
#     print(comparison_df)
    
#     # ===== EXAMPLE 7: Performance statistics =====
#     print("\n" + "="*70)
#     print("PERFORMANCE STATISTICS")
#     print("="*70)
    
#     stats = screener.get_performance_stats()
#     print(json.dumps(stats, indent=2))
    
#     # ===== EXAMPLE 8: Update existing strategy =====
#     print("\n" + "="*70)
#     print("UPDATING STRATEGY")
#     print("="*70)
    
#     updated = screener.strategy_manager.update_strategy(
#         'my_quality_growth',
#         conditions={
#             'min_roe': 20,  # Increased from 18
#             'max_pe': 18,   # Decreased from 20
#             'min_revenue_growth': 20,  # Increased from 15
#             'max_debt_equity': 50,  # Decreased from 60
#             'min_profit_margin': 15  # Increased from 12
#         }
#     )
    
#     print(f"Updated strategy: {updated.name}")
#     print(f"New conditions: {updated.conditions}")
    
#     print("\n" + "="*70)
#     print("SCREENER READY FOR USE")
#     print("="*70)
#     print("\nYou can now:")
#     print("1. Run any predefined strategy: screener.run_strategy('strategy_name')")
#     print("2. Create custom strategies: screener.strategy_manager.create_strategy(...)")
#     print("3. Export results for backtesting: screener.export_results(df, 'filename.csv')")
#     print("4. Save strategies for later use (auto-saved in ./strategies/)")
#     print("5. Import shared strategies: screener.strategy_manager.import_strategy('file.json')")










"""
Interactive Advanced Stock Screener - API Ready for React Frontend
===================================================================
Comprehensive stock screening with interactive strategy builder and
full API integration support.

Features:
- 60+ Technical Indicators (organized by category)
- 20+ Fundamental Metrics
- 15+ Candlestick Patterns
- Interactive Strategy Builder
- Predefined Strategy Library
- Export/Import Strategies
- API-Ready Endpoints
- React Frontend Integration

Author: GenAI Stock Intelligence System
Version: 3.0
"""

import pandas as pd
import numpy as np

# Optional dependency: pandas_ta is not yet compatible with Python 3.14.
# We fall back to a lightweight shim so the rest of the code keeps working
# even when pandas_ta cannot be installed.
try:
    import pandas_ta as ta  # type: ignore
except Exception:  # pragma: no cover - environment compatibility shim
    ta = None

    class _DummyTaAccessor:
        """Minimal .ta accessor providing no-op indicator methods.

        This prevents import-time crashes on Python versions where pandas_ta
        is unavailable. All callers already wrap ta-usage in try/except, so
        returning None is safe and simply disables those extra indicators.
        """

        def __init__(self, df: pd.DataFrame):
            self._df = df

        def macd(self, *args, **kwargs):
            return None

        def adx(self, *args, **kwargs):
            return None

        def rsi(self, *args, **kwargs):
            return None

        def willr(self, *args, **kwargs):
            return None

        def atr(self, *args, **kwargs):
            return None

        def bbands(self, *args, **kwargs):
            return None

        def obv(self, *args, **kwargs):
            return None

    # Attach a .ta accessor on DataFrame instances if pandas_ta is missing.
    if not hasattr(pd.DataFrame, "ta"):
        pd.DataFrame.ta = property(lambda self: _DummyTaAccessor(self))

import yfinance as yf
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import logging
import sys
import json
import time
from pathlib import Path
import warnings
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from threading import Lock, Event
from functools import lru_cache

warnings.filterwarnings('ignore')

# Windows console fix
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('interactive_screener.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ==================== INDICATOR CATALOG ====================

class IndicatorCatalog:
    """
    Comprehensive catalog of all available indicators, patterns, and fundamentals
    Organized for easy frontend display and selection
    """
    
    @staticmethod
    def get_technical_indicators() -> Dict[str, List[Dict]]:
        """Get all technical indicators organized by category"""
        return {
            "Trend Indicators": [
                {"id": "sma_5", "name": "SMA 5", "description": "5-day Simple Moving Average"},
                {"id": "sma_10", "name": "SMA 10", "description": "10-day Simple Moving Average"},
                {"id": "sma_20", "name": "SMA 20", "description": "20-day Simple Moving Average"},
                {"id": "sma_50", "name": "SMA 50", "description": "50-day Simple Moving Average"},
                {"id": "sma_100", "name": "SMA 100", "description": "100-day Simple Moving Average"},
                {"id": "sma_200", "name": "SMA 200", "description": "200-day Simple Moving Average"},
                {"id": "ema_5", "name": "EMA 5", "description": "5-day Exponential Moving Average"},
                {"id": "ema_10", "name": "EMA 10", "description": "10-day Exponential Moving Average"},
                {"id": "ema_20", "name": "EMA 20", "description": "20-day Exponential Moving Average"},
                {"id": "ema_50", "name": "EMA 50", "description": "50-day Exponential Moving Average"},
                {"id": "ema_100", "name": "EMA 100", "description": "100-day Exponential Moving Average"},
                {"id": "ema_200", "name": "EMA 200", "description": "200-day Exponential Moving Average"},
                {"id": "wma_20", "name": "WMA 20", "description": "20-day Weighted Moving Average"},
                {"id": "hma_9", "name": "HMA 9", "description": "9-day Hull Moving Average"},
                {"id": "vwma_20", "name": "VWMA 20", "description": "20-day Volume Weighted Moving Average"},
                {"id": "adx_14", "name": "ADX 14", "description": "14-day Average Directional Index", "typical_range": "0-100"},
                {"id": "adx_20", "name": "ADX 20", "description": "20-day Average Directional Index", "typical_range": "0-100"},
            ],
            
            "Momentum Indicators": [
                {"id": "rsi_9", "name": "RSI 9", "description": "9-day Relative Strength Index", "typical_range": "0-100"},
                {"id": "rsi_14", "name": "RSI 14", "description": "14-day Relative Strength Index", "typical_range": "0-100"},
                {"id": "rsi_21", "name": "RSI 21", "description": "21-day Relative Strength Index", "typical_range": "0-100"},
                {"id": "macd_hist", "name": "MACD Histogram", "description": "MACD Histogram (12,26,9)"},
                {"id": "willr_14", "name": "Williams %R 14", "description": "14-day Williams %R", "typical_range": "-100 to 0"},
                {"id": "willr_20", "name": "Williams %R 20", "description": "20-day Williams %R", "typical_range": "-100 to 0"},
                {"id": "price_change_1d", "name": "1-Day % Change", "description": "1-day price change percentage"},
                {"id": "price_change_3d", "name": "3-Day % Change", "description": "3-day price change percentage"},
                {"id": "price_change_5d", "name": "5-Day % Change", "description": "5-day price change percentage"},
                {"id": "price_change_10d", "name": "10-Day % Change", "description": "10-day price change percentage"},
                {"id": "price_change_20d", "name": "20-Day % Change", "description": "20-day price change percentage"},
                {"id": "price_change_50d", "name": "50-Day % Change", "description": "50-day price change percentage"},
            ],
            
            "Volatility Indicators": [
                {"id": "atr_7", "name": "ATR 7", "description": "7-day Average True Range"},
                {"id": "atr_14", "name": "ATR 14", "description": "14-day Average True Range"},
                {"id": "atr_21", "name": "ATR 21", "description": "21-day Average True Range"},
                {"id": "bb_width_20_2", "name": "BB Width (20,2)", "description": "Bollinger Bands Width"},
                {"id": "bb_percent_20_2", "name": "BB %B (20,2)", "description": "Bollinger Bands Percent B", "typical_range": "0-1"},
                {"id": "bb_width_20_3", "name": "BB Width (20,3)", "description": "Bollinger Bands Width (3 std)"},
                {"id": "bb_percent_20_3", "name": "BB %B (20,3)", "description": "Bollinger Bands Percent B (3 std)"},
            ],
            
            "Volume Indicators": [
                {"id": "volume_ratio_10", "name": "Volume Ratio 10", "description": "Volume vs 10-day average"},
                {"id": "volume_ratio_20", "name": "Volume Ratio 20", "description": "Volume vs 20-day average"},
                {"id": "volume_ratio_50", "name": "Volume Ratio 50", "description": "Volume vs 50-day average"},
                {"id": "obv", "name": "OBV", "description": "On-Balance Volume"},
            ],
            
            "Support & Resistance": [
                {"id": "distance_from_high_5d", "name": "Distance from 5D High", "description": "% distance from 5-day high"},
                {"id": "distance_from_high_10d", "name": "Distance from 10D High", "description": "% distance from 10-day high"},
                {"id": "distance_from_high_20d", "name": "Distance from 20D High", "description": "% distance from 20-day high"},
                {"id": "distance_from_high_52d", "name": "Distance from 52D High", "description": "% distance from 52-day high"},
                {"id": "distance_from_high_252d", "name": "Distance from 52W High", "description": "% distance from 52-week high"},
                {"id": "distance_from_low_5d", "name": "Distance from 5D Low", "description": "% distance from 5-day low"},
                {"id": "distance_from_low_10d", "name": "Distance from 10D Low", "description": "% distance from 10-day low"},
                {"id": "distance_from_low_20d", "name": "Distance from 20D Low", "description": "% distance from 20-day low"},
                {"id": "distance_from_low_52d", "name": "Distance from 52D Low", "description": "% distance from 52-day low"},
                {"id": "distance_from_low_252d", "name": "Distance from 52W Low", "description": "% distance from 52-week low"},
            ],
        }
    
    @staticmethod
    def get_fundamental_indicators() -> Dict[str, List[Dict]]:
        """Get all fundamental indicators organized by category"""
        return {
            "Valuation Metrics": [
                {"id": "trailing_pe", "name": "P/E Ratio (Trailing)", "description": "Price to Earnings Ratio"},
                {"id": "forward_pe", "name": "P/E Ratio (Forward)", "description": "Forward Price to Earnings Ratio"},
                {"id": "peg_ratio", "name": "PEG Ratio", "description": "Price/Earnings to Growth Ratio"},
                {"id": "price_to_book", "name": "P/B Ratio", "description": "Price to Book Ratio"},
                {"id": "market_cap", "name": "Market Cap", "description": "Market Capitalization"},
            ],
            
            "Profitability Metrics": [
                {"id": "profit_margin", "name": "Profit Margin", "description": "Net Profit Margin (%)"},
                {"id": "roe", "name": "ROE", "description": "Return on Equity (%)"},
                {"id": "roa", "name": "ROA", "description": "Return on Assets (%)"},
            ],
            
            "Growth Metrics": [
                {"id": "revenue_growth", "name": "Revenue Growth", "description": "Year-over-Year Revenue Growth (%)"},
                {"id": "earnings_growth", "name": "Earnings Growth", "description": "Year-over-Year Earnings Growth (%)"},
            ],
            
            "Financial Health": [
                {"id": "current_ratio", "name": "Current Ratio", "description": "Current Assets / Current Liabilities"},
                {"id": "debt_to_equity", "name": "Debt to Equity", "description": "Total Debt / Shareholders' Equity"},
                {"id": "free_cashflow", "name": "Free Cash Flow", "description": "Operating Cash Flow - Capital Expenditures"},
            ],
            
            "Dividend Metrics": [
                {"id": "dividend_yield", "name": "Dividend Yield", "description": "Annual Dividend / Stock Price (%)"},
                {"id": "payout_ratio", "name": "Payout Ratio", "description": "Dividends / Net Income (%)"},
            ],
            
            "Risk Metrics": [
                {"id": "beta", "name": "Beta", "description": "Stock volatility vs market"},
            ],
        }
    
    @staticmethod
    def get_candlestick_patterns() -> List[Dict]:
        """Get all available candlestick patterns"""
        return [
            {"id": "doji", "name": "Doji", "description": "Indecision pattern - small body", "type": "indecision"},
            {"id": "hammer", "name": "Hammer", "description": "Bullish reversal - long lower wick", "type": "bullish_reversal"},
            {"id": "bullish_engulfing", "name": "Bullish Engulfing", "description": "Bullish reversal - large bullish candle engulfs previous bearish", "type": "bullish_reversal"},
            {"id": "bearish_engulfing", "name": "Bearish Engulfing", "description": "Bearish reversal - large bearish candle engulfs previous bullish", "type": "bearish_reversal"},
            {"id": "morning_star", "name": "Morning Star", "description": "Bullish reversal - three candle pattern", "type": "bullish_reversal"},
        ]
    
    @staticmethod
    def get_operators() -> List[Dict]:
        """Get all available comparison operators"""
        return [
            {"id": ">", "name": "Greater Than", "symbol": ">"},
            {"id": ">=", "name": "Greater Than or Equal", "symbol": "≥"},
            {"id": "<", "name": "Less Than", "symbol": "<"},
            {"id": "<=", "name": "Less Than or Equal", "symbol": "≤"},
            {"id": "==", "name": "Equal To", "symbol": "="},
            {"id": "!=", "name": "Not Equal To", "symbol": "≠"},
            {"id": "between", "name": "Between", "symbol": "⟷"},
        ]
    
    @staticmethod
    def get_all_indicators_flat() -> List[str]:
        """Get flat list of all indicator IDs for quick lookup"""
        indicators = []
        
        # Technical indicators
        tech = IndicatorCatalog.get_technical_indicators()
        for category, items in tech.items():
            indicators.extend([item['id'] for item in items])
        
        # Fundamental indicators
        fund = IndicatorCatalog.get_fundamental_indicators()
        for category, items in fund.items():
            indicators.extend([item['id'] for item in items])
        
        return indicators


# ==================== DATA CLASSES ====================

@dataclass
class StrategyCondition:
    """Single condition in a strategy"""
    indicator: str
    operator: str
    value: Union[float, Tuple[float, float], str]
    weight: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            'indicator': self.indicator,
            'operator': self.operator,
            'value': self.value,
            'weight': self.weight
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StrategyCondition':
        return cls(**data)
    
    def __str__(self):
        if isinstance(self.value, tuple):
            return f"{self.indicator} {self.operator} [{self.value[0]}, {self.value[1]}]"
        return f"{self.indicator} {self.operator} {self.value}"


@dataclass
class TradingStrategy:
    """Complete trading strategy definition"""
    name: str
    description: str
    strategy_type: str  # 'technical', 'fundamental', 'hybrid'
    conditions: List[StrategyCondition] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'strategy_type': self.strategy_type,
            'conditions': [c.to_dict() for c in self.conditions],
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradingStrategy':
        """Create from dictionary"""
        conditions = [StrategyCondition.from_dict(c) for c in data.get('conditions', [])]
        return cls(
            name=data['name'],
            description=data['description'],
            strategy_type=data['strategy_type'],
            conditions=conditions,
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )


# ==================== STRATEGY LIBRARY ====================

class StrategyLibrary:
    """
    Comprehensive library of predefined trading strategies
    Organized for easy frontend display and selection
    """
    
    @staticmethod
    def get_predefined_strategies() -> Dict[str, Dict]:
        """Get all predefined strategies with full details"""
        return {
            "momentum": {
                "name": "Momentum Trading",
                "description": "High momentum stocks with strong price action and volume surge",
                "strategy_type": "technical",
                "category": "Growth",
                "risk_level": "Medium-High",
                "holding_period": "1-3 months",
                "conditions": [
                    {"indicator": "rsi_14", "operator": ">", "value": 50, "weight": 1.0},
                    {"indicator": "rsi_14", "operator": "<", "value": 70, "weight": 1.0},
                    {"indicator": "price_change_20d", "operator": ">", "value": 10, "weight": 1.5},
                    {"indicator": "volume_ratio_20", "operator": ">", "value": 1.3, "weight": 1.2},
                    {"indicator": "macd_hist", "operator": ">", "value": 0, "weight": 1.0},
                ],
                "rationale": "Identifies stocks with strong upward momentum, healthy RSI, and volume confirmation"
            },
            
            "mean_reversion": {
                "name": "Mean Reversion",
                "description": "Oversold stocks likely to bounce back to their mean",
                "strategy_type": "technical",
                "category": "Reversal",
                "risk_level": "Medium",
                "holding_period": "1-4 weeks",
                "conditions": [
                    {"indicator": "rsi_14", "operator": "<", "value": 30, "weight": 2.0},
                    {"indicator": "bb_percent_20_2", "operator": "<", "value": 0.2, "weight": 1.5},
                    {"indicator": "close", "operator": ">", "value": "sma_200", "weight": 1.0},
                ],
                "rationale": "Finds oversold stocks in uptrends, trading near lower Bollinger Band"
            },
            
            "breakout": {
                "name": "Breakout Trading",
                "description": "52-week high breakouts with volume confirmation and trend strength",
                "strategy_type": "technical",
                "category": "Momentum",
                "risk_level": "High",
                "holding_period": "2-8 weeks",
                "conditions": [
                    {"indicator": "distance_from_high_252d", "operator": "<", "value": 3, "weight": 2.0},
                    {"indicator": "volume_ratio_20", "operator": ">", "value": 1.5, "weight": 1.5},
                    {"indicator": "rsi_14", "operator": ">", "value": 60, "weight": 1.0},
                    {"indicator": "adx_14", "operator": ">", "value": 25, "weight": 1.0},
                ],
                "rationale": "Captures strong breakout moves with high volume and trend strength"
            },
            
            "value_investing": {
                "name": "Value Investing",
                "description": "Undervalued quality companies with strong fundamentals",
                "strategy_type": "fundamental",
                "category": "Value",
                "risk_level": "Low",
                "holding_period": "12-24 months",
                "conditions": [
                    {"indicator": "trailing_pe", "operator": "<", "value": 15, "weight": 1.5},
                    {"indicator": "price_to_book", "operator": "<", "value": 2.5, "weight": 1.0},
                    {"indicator": "roe", "operator": ">", "value": 0.15, "weight": 2.0},
                    {"indicator": "debt_to_equity", "operator": "<", "value": 80, "weight": 1.0},
                    {"indicator": "dividend_yield", "operator": ">", "value": 0.02, "weight": 0.5},
                ],
                "rationale": "Classic value investing - low P/E, strong ROE, manageable debt"
            },
            
            "garp": {
                "name": "GARP (Growth at Reasonable Price)",
                "description": "Growing companies at reasonable valuations",
                "strategy_type": "hybrid",
                "category": "Growth & Value",
                "risk_level": "Medium",
                "holding_period": "6-18 months",
                "conditions": [
                    {"indicator": "peg_ratio", "operator": "<", "value": 1.5, "weight": 2.0},
                    {"indicator": "trailing_pe", "operator": "<", "value": 25, "weight": 1.0},
                    {"indicator": "revenue_growth", "operator": ">", "value": 0.15, "weight": 1.5},
                    {"indicator": "roe", "operator": ">", "value": 0.15, "weight": 1.5},
                    {"indicator": "earnings_growth", "operator": ">", "value": 0.10, "weight": 1.0},
                ],
                "rationale": "Combines growth and value - PEG < 1.5, strong growth metrics"
            },
            
            "quality_dividend": {
                "name": "Quality Dividend",
                "description": "High-quality dividend payers with sustainable payouts",
                "strategy_type": "fundamental",
                "category": "Income",
                "risk_level": "Low",
                "holding_period": "24+ months",
                "conditions": [
                    {"indicator": "dividend_yield", "operator": ">", "value": 0.03, "weight": 2.0},
                    {"indicator": "payout_ratio", "operator": "<", "value": 0.70, "weight": 1.5},
                    {"indicator": "roe", "operator": ">", "value": 0.12, "weight": 1.0},
                    {"indicator": "debt_to_equity", "operator": "<", "value": 100, "weight": 1.0},
                    {"indicator": "free_cashflow", "operator": ">", "value": 0, "weight": 1.5},
                ],
                "rationale": "Sustainable dividend payers with strong balance sheets"
            },
            
            "swing_trading": {
                "name": "Swing Trading",
                "description": "Short-term swing trades using MACD and RSI",
                "strategy_type": "technical",
                "category": "Short-term",
                "risk_level": "Medium",
                "holding_period": "1-4 weeks",
                "conditions": [
                    {"indicator": "rsi_14", "operator": "between", "value": (40, 60), "weight": 1.0},
                    {"indicator": "macd_hist", "operator": ">", "value": 0, "weight": 2.0},
                    {"indicator": "close", "operator": ">", "value": "sma_20", "weight": 1.0},
                ],
                "rationale": "Neutral RSI with bullish MACD crossover above 20-day average"
            },
            
            "trend_following": {
                "name": "Trend Following",
                "description": "Strong uptrends with multiple timeframe confirmation",
                "strategy_type": "technical",
                "category": "Trend",
                "risk_level": "Medium",
                "holding_period": "3-6 months",
                "conditions": [
                    {"indicator": "close", "operator": ">", "value": "sma_50", "weight": 1.5},
                    {"indicator": "sma_50", "operator": ">", "value": "sma_200", "weight": 2.0},
                    {"indicator": "adx_14", "operator": ">", "value": 25, "weight": 1.5},
                    {"indicator": "price_change_20d", "operator": ">", "value": 0, "weight": 1.0},
                ],
                "rationale": "Golden cross (SMA 50 > SMA 200) with strong trend strength"
            },
            
            "contrarian": {
                "name": "Contrarian",
                "description": "Extremely oversold stocks with reversal potential",
                "strategy_type": "technical",
                "category": "Reversal",
                "risk_level": "High",
                "holding_period": "1-2 weeks",
                "conditions": [
                    {"indicator": "rsi_14", "operator": "<", "value": 25, "weight": 2.0},
                    {"indicator": "willr_14", "operator": "<", "value": -85, "weight": 1.5},
                    {"indicator": "close", "operator": ">", "value": "sma_200", "weight": 1.0},
                ],
                "rationale": "Extreme oversold conditions in stocks with long-term uptrend"
            },
            
            "quality_growth": {
                "name": "Quality Growth",
                "description": "High-quality companies with consistent growth",
                "strategy_type": "hybrid",
                "category": "Quality",
                "risk_level": "Low-Medium",
                "holding_period": "12-24 months",
                "conditions": [
                    {"indicator": "roe", "operator": ">", "value": 0.20, "weight": 2.0},
                    {"indicator": "revenue_growth", "operator": ">", "value": 0.15, "weight": 1.5},
                    {"indicator": "profit_margin", "operator": ">", "value": 0.12, "weight": 1.5},
                    {"indicator": "debt_to_equity", "operator": "<", "value": 60, "weight": 1.0},
                    {"indicator": "trailing_pe", "operator": "<", "value": 30, "weight": 0.5},
                ],
                "rationale": "Premium quality metrics with reasonable valuations"
            },
            
            # ==================== STRATEGY ALIASES ====================
            # These match the names expected by StockScreener wrapper
            
            "piotroski": {
                "name": "Piotroski F-Score",
                "description": "High quality value stocks based on Piotroski's 9-point scoring system",
                "strategy_type": "fundamental",
                "category": "Value",
                "risk_level": "Low-Medium",
                "holding_period": "12-24 months",
                "conditions": [
                    {"indicator": "roe", "operator": ">", "value": 0.05, "weight": 2.0},
                    {"indicator": "roa", "operator": ">", "value": 0.03, "weight": 1.5},
                    {"indicator": "current_ratio", "operator": ">", "value": 1.0, "weight": 1.0},
                    {"indicator": "debt_to_equity", "operator": "<", "value": 50, "weight": 1.5},
                    {"indicator": "profit_margin", "operator": ">", "value": 0.05, "weight": 1.0},
                    {"indicator": "revenue_growth", "operator": ">", "value": 0, "weight": 1.0},
                ],
                "rationale": "Combines profitability, leverage, and operating efficiency signals"
            },
            
            "swing": {
                "name": "Swing Trading",
                "description": "Short-term swing trades using MACD and RSI signals",
                "strategy_type": "technical",
                "category": "Short-term",
                "risk_level": "Medium",
                "holding_period": "1-4 weeks",
                "conditions": [
                    {"indicator": "rsi_14", "operator": "between", "value": (40, 60), "weight": 1.0},
                    {"indicator": "macd_hist", "operator": ">", "value": 0, "weight": 2.0},
                    {"indicator": "close", "operator": ">", "value": "sma_20", "weight": 1.0},
                ],
                "rationale": "Neutral RSI with bullish MACD crossover above 20-day average"
            },
            
            "value": {
                "name": "Value Investing",
                "description": "Undervalued quality companies with strong fundamentals",
                "strategy_type": "fundamental",
                "category": "Value",
                "risk_level": "Low",
                "holding_period": "12-24 months",
                "conditions": [
                    {"indicator": "trailing_pe", "operator": "<", "value": 15, "weight": 1.5},
                    {"indicator": "price_to_book", "operator": "<", "value": 2.5, "weight": 1.0},
                    {"indicator": "roe", "operator": ">", "value": 0.15, "weight": 2.0},
                    {"indicator": "debt_to_equity", "operator": "<", "value": 80, "weight": 1.0},
                ],
                "rationale": "Classic value investing - low P/E, strong ROE, manageable debt"
            },
        }
    
    @staticmethod
    def get_strategy_categories() -> List[str]:
        """Get unique strategy categories"""
        strategies = StrategyLibrary.get_predefined_strategies()
        categories = set(s['category'] for s in strategies.values())
        return sorted(list(categories))
    
    @staticmethod
    def get_strategies_by_category(category: str) -> Dict[str, Dict]:
        """Get strategies filtered by category"""
        all_strategies = StrategyLibrary.get_predefined_strategies()
        return {
            name: strategy for name, strategy in all_strategies.items()
            if strategy['category'] == category
        }
    
    @staticmethod
    def get_strategies_by_risk(risk_level: str) -> Dict[str, Dict]:
        """Get strategies filtered by risk level"""
        all_strategies = StrategyLibrary.get_predefined_strategies()
        return {
            name: strategy for name, strategy in all_strategies.items()
            if strategy['risk_level'] == risk_level
        }


# ==================== UTILITIES ====================

class RateLimiter:
    """Rate limiter to prevent API throttling"""
    
    def __init__(self, delay: float = 0.5):
        self.delay = delay
        self.last_request = 0
        self.lock = Lock()
    
    def wait(self):
        """Wait before making next request"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request
            
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            
            self.last_request = time.time()


class CacheManager:
    """Enhanced cache manager with TTL support"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.timestamps = {}
        self.ttl = ttl_seconds
        self.lock = Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        with self.lock:
            if key not in self.cache:
                return None
            
            if time.time() - self.timestamps[key] > self.ttl:
                del self.cache[key]
                del self.timestamps[key]
                return None
            
            return self.cache[key]
    
    def set(self, key: str, value: Any):
        """Set cache value with timestamp"""
        with self.lock:
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def clear(self):
        """Clear entire cache"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()


# ==================== TECHNICAL INDICATOR ENGINE ====================

class TechnicalIndicatorEngine:
    """Comprehensive technical indicator calculation engine"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        
        required = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in self.df.columns for col in required):
            raise ValueError(f"Missing required columns. Need: {required}")
    
    def calculate_all_indicators(self) -> pd.DataFrame:
        """Calculate all technical indicators"""
        try:
            self._add_moving_averages()
            self._add_macd()
            self._add_adx()
            self._add_oscillators()
            self._add_price_momentum()
            self._add_volatility()
            self._add_volume()
            self._add_support_resistance()
        except Exception as e:
            logger.debug(f"Error calculating indicators: {e}")
        
        return self.df
    
    def _add_moving_averages(self):
        """Add moving averages"""
        for period in [5, 10, 20, 50, 100, 200]:
            self.df[f'sma_{period}'] = self.df['close'].rolling(window=period).mean()
            self.df[f'ema_{period}'] = self.df['close'].ewm(span=period, adjust=False).mean()
            
            if period <= 50:
                weights = np.arange(1, period + 1)
                self.df[f'wma_{period}'] = self.df['close'].rolling(window=period).apply(
                    lambda prices: np.dot(prices, weights) / weights.sum(), raw=True
                )
        
        # Hull Moving Average
        for period in [9, 16, 20]:
            try:
                wma_half = self.df['close'].rolling(window=period//2).apply(
                    lambda x: np.dot(x, np.arange(1, len(x)+1)) / np.arange(1, len(x)+1).sum(), raw=True
                )
                wma_full = self.df['close'].rolling(window=period).apply(
                    lambda x: np.dot(x, np.arange(1, len(x)+1)) / np.arange(1, len(x)+1).sum(), raw=True
                )
                raw_hma = 2 * wma_half - wma_full
                sqrt_period = int(np.sqrt(period))
                self.df[f'hma_{period}'] = raw_hma.rolling(window=sqrt_period).apply(
                    lambda x: np.dot(x, np.arange(1, len(x)+1)) / np.arange(1, len(x)+1).sum() if len(x) == sqrt_period else np.nan,
                    raw=True
                )
            except:
                pass
        
        # VWMA
        for period in [20, 50]:
            self.df[f'vwma_{period}'] = (
                (self.df['close'] * self.df['volume']).rolling(window=period).sum() /
                self.df['volume'].rolling(window=period).sum()
            )
    
    def _add_macd(self):
        """Add MACD indicators"""
        try:
            macd = self.df.ta.macd(fast=12, slow=26, signal=9)
            if macd is not None:
                self.df = pd.concat([self.df, macd], axis=1)
                if 'MACDh_12_26_9' in self.df.columns:
                    self.df['macd_hist'] = self.df['MACDh_12_26_9']
        except:
            pass
    
    def _add_adx(self):
        """Add ADX indicators"""
        try:
            for period in [14, 20]:
                adx = self.df.ta.adx(length=period)
                if adx is not None:
                    self.df = pd.concat([self.df, adx], axis=1)
                    if f'ADX_{period}' in self.df.columns:
                        self.df[f'adx_{period}'] = self.df[f'ADX_{period}']
        except:
            pass
    
    def _add_oscillators(self):
        """Add momentum oscillators"""
        for period in [9, 14, 21, 25]:
            try:
                self.df[f'rsi_{period}'] = self.df.ta.rsi(length=period)
            except:
                pass
        
        for period in [14, 20]:
            try:
                self.df[f'willr_{period}'] = self.df.ta.willr(length=period)
            except:
                pass
    
    def _add_price_momentum(self):
        """Add price-based momentum"""
        for period in [1, 3, 5, 10, 20, 50]:
            self.df[f'price_change_{period}d'] = self.df['close'].pct_change(period) * 100
            self.df[f'log_return_{period}d'] = np.log(self.df['close'] / self.df['close'].shift(period))
    
    def _add_volatility(self):
        """Add volatility indicators"""
        for period in [7, 14, 21]:
            try:
                self.df[f'atr_{period}'] = self.df.ta.atr(length=period)
            except:
                pass
        
        try:
            for period, std in [(20, 2), (20, 3)]:
                bb = self.df.ta.bbands(length=period, std=std)
                if bb is not None:
                    self.df = pd.concat([self.df, bb], axis=1)
                    if f'BBU_{period}_{std}.0' in self.df.columns:
                        self.df[f'bb_width_{period}_{std}'] = (
                            (self.df[f'BBU_{period}_{std}.0'] - self.df[f'BBL_{period}_{std}.0']) /
                            self.df[f'BBM_{period}_{std}.0']
                        )
                        self.df[f'bb_percent_{period}_{std}'] = (
                            (self.df['close'] - self.df[f'BBL_{period}_{std}.0']) /
                            (self.df[f'BBU_{period}_{std}.0'] - self.df[f'BBL_{period}_{std}.0'])
                        )
        except:
            pass
    
    def _add_volume(self):
        """Add volume indicators"""
        for period in [10, 20, 50]:
            self.df[f'volume_sma_{period}'] = self.df['volume'].rolling(window=period).mean()
            self.df[f'volume_ratio_{period}'] = self.df['volume'] / (self.df[f'volume_sma_{period}'] + 1)
        
        try:
            self.df['obv'] = self.df.ta.obv()
        except:
            pass
    
    def _add_support_resistance(self):
        """Add support and resistance levels"""
        for period in [5, 10, 20, 52, 252]:
            self.df[f'high_{period}d'] = self.df['high'].rolling(window=period).max()
            self.df[f'low_{period}d'] = self.df['low'].rolling(window=period).min()
            self.df[f'distance_from_high_{period}d'] = (
                (self.df[f'high_{period}d'] - self.df['close']) / self.df[f'high_{period}d']
            ) * 100
            self.df[f'distance_from_low_{period}d'] = (
                (self.df['close'] - self.df[f'low_{period}d']) / self.df[f'low_{period}d']
            ) * 100


# ==================== PATTERN RECOGNITION ====================

class PatternRecognitionEngine:
    """Candlestick pattern detection"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
    
    def detect_all_patterns(self) -> Dict[str, bool]:
        """Detect all patterns"""
        patterns = {}
        
        try:
            patterns.update(self._detect_doji())
            patterns.update(self._detect_hammer())
            patterns.update(self._detect_engulfing())
            patterns.update(self._detect_morning_star())
        except Exception as e:
            logger.debug(f"Pattern detection error: {e}")
        
        return patterns
    
    def _detect_doji(self) -> Dict[str, bool]:
        if len(self.df) == 0:
            return {'doji': False}
        
        body = abs(self.df['close'] - self.df['open'])
        avg_body = body.rolling(20).mean()
        
        return {'doji': (body < avg_body * 0.1).iloc[-1] if len(self.df) > 0 else False}
    
    def _detect_hammer(self) -> Dict[str, bool]:
        if len(self.df) == 0:
            return {'hammer': False}
        
        body = abs(self.df['close'] - self.df['open'])
        lower_wick = np.minimum(self.df['close'], self.df['open']) - self.df['low']
        upper_wick = self.df['high'] - np.maximum(self.df['close'], self.df['open'])
        
        hammer = (lower_wick > 2 * body) & (upper_wick < 0.3 * body)
        
        return {'hammer': hammer.iloc[-1] if len(self.df) > 0 else False}
    
    def _detect_engulfing(self) -> Dict[str, bool]:
        if len(self.df) < 2:
            return {'bullish_engulfing': False, 'bearish_engulfing': False}
        
        bullish_engulfing = (
            (self.df['close'].iloc[-2] < self.df['open'].iloc[-2]) &
            (self.df['close'].iloc[-1] > self.df['open'].iloc[-1]) &
            (self.df['open'].iloc[-1] < self.df['close'].iloc[-2]) &
            (self.df['close'].iloc[-1] > self.df['open'].iloc[-2])
        )
        
        bearish_engulfing = (
            (self.df['close'].iloc[-2] > self.df['open'].iloc[-2]) &
            (self.df['close'].iloc[-1] < self.df['open'].iloc[-1]) &
            (self.df['open'].iloc[-1] > self.df['close'].iloc[-2]) &
            (self.df['close'].iloc[-1] < self.df['open'].iloc[-2])
        )
        
        return {
            'bullish_engulfing': bullish_engulfing,
            'bearish_engulfing': bearish_engulfing
        }
    
    def _detect_morning_star(self) -> Dict[str, bool]:
        if len(self.df) < 3:
            return {'morning_star': False}
        
        morning_star = (
            (self.df['close'].iloc[-3] < self.df['open'].iloc[-3]) &
            (abs(self.df['close'].iloc[-2] - self.df['open'].iloc[-2]) <
             abs(self.df['close'].iloc[-3] - self.df['open'].iloc[-3]) * 0.3) &
            (self.df['close'].iloc[-1] > self.df['open'].iloc[-1]) &
            (self.df['close'].iloc[-1] > (self.df['open'].iloc[-3] + self.df['close'].iloc[-3]) / 2)
        )
        
        return {'morning_star': morning_star}


# ==================== FUNDAMENTAL ANALYSIS ====================

class FundamentalAnalysisEngine:
    """Fundamental data fetcher"""
    
    def __init__(self, ticker: str):
        self.ticker = ticker
    
    @lru_cache(maxsize=128)
    def fetch_fundamentals(self) -> Dict[str, Any]:
        """Fetch fundamental data from Yahoo Finance"""
        try:
            search_ticker = self.ticker
            if not search_ticker.endswith('.NS') and not search_ticker.endswith('.BO'):
                search_ticker = f"{self.ticker}.NS"
            
            stock = yf.Ticker(search_ticker)
            info = stock.info
            
            return {
                'market_cap': info.get('marketCap', 0),
                'trailing_pe': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'peg_ratio': info.get('pegRatio', 0),
                'price_to_book': info.get('priceToBook', 0),
                'profit_margin': info.get('profitMargins', 0),
                'roe': info.get('returnOnEquity', 0),
                'roa': info.get('returnOnAssets', 0),
                'revenue_growth': info.get('revenueGrowth', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                'current_ratio': info.get('currentRatio', 0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'free_cashflow': info.get('freeCashflow', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'payout_ratio': info.get('payoutRatio', 0),
                'beta': info.get('beta', 1.0),
            }
        except Exception as e:
            logger.debug(f"Error fetching fundamentals for {self.ticker}: {e}")
            return {}


# ==================== STRATEGY MANAGER ====================

class StrategyManager:
    """Manage predefined and custom strategies"""
    
    def __init__(self, storage_path: str = "./strategies"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.strategies: Dict[str, TradingStrategy] = {}
        self._load_predefined_strategies()
        self._load_custom_strategies()
    
    def _load_predefined_strategies(self):
        """Load predefined strategies from library"""
        predefined = StrategyLibrary.get_predefined_strategies()
        
        for name, strategy_data in predefined.items():
            conditions = [
                StrategyCondition(**c) for c in strategy_data['conditions']
            ]
            
            self.strategies[name] = TradingStrategy(
                name=name,
                description=strategy_data['description'],
                strategy_type=strategy_data['strategy_type'],
                conditions=conditions,
                metadata={
                    'category': strategy_data['category'],
                    'risk_level': strategy_data['risk_level'],
                    'holding_period': strategy_data['holding_period'],
                    'rationale': strategy_data['rationale']
                }
            )
    
    def _load_custom_strategies(self):
        """Load custom strategies from storage"""
        strategy_files = list(self.storage_path.glob("*.json"))
        
        for file_path in strategy_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    strategy = TradingStrategy.from_dict(data)
                    self.strategies[strategy.name] = strategy
                    logger.info(f"Loaded custom strategy: {strategy.name}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
    
    def create_strategy(self, strategy_data: Dict) -> TradingStrategy:
        """Create a new custom strategy"""
        name = strategy_data['name']
        
        if name in self.strategies:
            raise ValueError(f"Strategy '{name}' already exists")
        
        conditions = [StrategyCondition(**c) for c in strategy_data['conditions']]
        
        strategy = TradingStrategy(
            name=name,
            description=strategy_data['description'],
            strategy_type=strategy_data['strategy_type'],
            conditions=conditions,
            metadata=strategy_data.get('metadata', {})
        )
        
        self.strategies[name] = strategy
        self.save_strategy(name)
        
        return strategy
    
    def save_strategy(self, name: str):
        """Save strategy to disk"""
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not found")
        
        strategy = self.strategies[name]
        file_path = self.storage_path / f"{name}.json"
        
        with open(file_path, 'w') as f:
            json.dump(strategy.to_dict(), f, indent=2)
    
    def get_strategy(self, name: str) -> TradingStrategy:
        """Get strategy by name"""
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not found")
        return self.strategies[name]
    
    def list_strategies(self) -> List[Dict]:
        """List all strategies with metadata"""
        return [
            {
                'name': s.name,
                'description': s.description,
                'strategy_type': s.strategy_type,
                'num_conditions': len(s.conditions),
                'metadata': s.metadata
            }
            for s in self.strategies.values()
        ]
    
    def delete_strategy(self, name: str):
        """Delete a custom strategy"""
        if name not in self.strategies:
            raise ValueError(f"Strategy '{name}' not found")
        
        # Don't delete predefined strategies
        predefined = StrategyLibrary.get_predefined_strategies()
        if name in predefined:
            raise ValueError(f"Cannot delete predefined strategy: {name}")
        
        del self.strategies[name]
        
        file_path = self.storage_path / f"{name}.json"
        if file_path.exists():
            file_path.unlink()


# ==================== INTERACTIVE STOCK SCREENER ====================

class InteractiveStockScreener:
    """
    Main screener class with methods designed for React frontend integration
    All methods return JSON-serializable data for API responses
    """
    
    def __init__(self, pipeline, cache_ttl: int = 3600, max_workers: int = 10, max_tickers: int = 2500):
        self.pipeline = pipeline
        self.cache = CacheManager(cache_ttl)
        self.rate_limiter = RateLimiter(0.5)
        self.strategy_manager = StrategyManager()
        self.max_workers = max_workers
        self.max_tickers = max_tickers
    
    # ==================== API METHODS FOR FRONTEND ====================
    
    def get_indicator_catalog(self) -> Dict:
        """
        Get complete indicator catalog for frontend display
        Returns organized structure for building UI
        """
        return {
            'technical_indicators': IndicatorCatalog.get_technical_indicators(),
            'fundamental_indicators': IndicatorCatalog.get_fundamental_indicators(),
            'candlestick_patterns': IndicatorCatalog.get_candlestick_patterns(),
            'operators': IndicatorCatalog.get_operators()
        }
    
    def get_predefined_strategies(self, category: Optional[str] = None) -> Dict:
        """
        Get predefined strategies for frontend display
        Optionally filter by category
        """
        if category:
            strategies = StrategyLibrary.get_strategies_by_category(category)
        else:
            strategies = StrategyLibrary.get_predefined_strategies()
        
        return {
            'strategies': strategies,
            'categories': StrategyLibrary.get_strategy_categories()
        }
    
    def get_custom_strategies(self) -> List[Dict]:
        """Get all custom strategies"""
        return self.strategy_manager.list_strategies()
    
    def create_custom_strategy(self, strategy_data: Dict) -> Dict:
        """
        Create a new custom strategy from frontend data
        
        Expected format:
        {
            'name': 'my_strategy',
            'description': 'Strategy description',
            'strategy_type': 'technical',
            'conditions': [
                {'indicator': 'rsi_14', 'operator': '>', 'value': 50, 'weight': 1.0},
                ...
            ],
            'metadata': {...}
        }
        """
        try:
            strategy = self.strategy_manager.create_strategy(strategy_data)
            return {
                'status': 'success',
                'message': f"Strategy '{strategy.name}' created successfully",
                'strategy': strategy.to_dict()
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def validate_strategy(self, strategy_data: Dict) -> Dict:
        """
        Validate strategy conditions before creation
        Check if indicators exist and values are valid
        """
        errors = []
        warnings = []
        
        # Check name
        if not strategy_data.get('name'):
            errors.append("Strategy name is required")
        
        # Check conditions
        conditions = strategy_data.get('conditions', [])
        if not conditions:
            errors.append("At least one condition is required")
        
        all_indicators = IndicatorCatalog.get_all_indicators_flat()
        
        for i, condition in enumerate(conditions):
            indicator = condition.get('indicator')
            operator = condition.get('operator')
            value = condition.get('value')
            
            # Validate indicator exists
            if indicator not in all_indicators and not indicator.startswith('sma_') and not indicator.startswith('ema_'):
                errors.append(f"Condition {i+1}: Invalid indicator '{indicator}'")
            
            # Validate operator
            valid_operators = ['>', '>=', '<', '<=', '==', '!=', 'between']
            if operator not in valid_operators:
                errors.append(f"Condition {i+1}: Invalid operator '{operator}'")
            
            # Validate value
            if operator == 'between':
                if not isinstance(value, (list, tuple)) or len(value) != 2:
                    errors.append(f"Condition {i+1}: 'between' operator requires [min, max] values")
            elif value is None:
                errors.append(f"Condition {i+1}: Value is required")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def run_screening(self, strategy_name: str, max_results: int = 50) -> Dict:
        """
        Run screening for a strategy
        Returns JSON-serializable results for frontend
        """
        try:
            logger.info(f"Running screening for: {strategy_name}")
            start_time = time.time()
            
            strategy = self.strategy_manager.get_strategy(strategy_name)
            tickers = self._get_tickers()
            
            if not tickers:
                return {
                    'status': 'error',
                    'message': 'No tickers found'
                }
            
            results = []
            
            # Screen stocks in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_ticker = {
                    executor.submit(self._screen_stock, ticker, strategy): ticker
                    for ticker in tickers[:self.max_tickers]
                }
                
                for future in as_completed(future_to_ticker):
                    try:
                        result = future.result(timeout=30)
                        if result and result['score'] > 0:
                            results.append(result)
                    except Exception as e:
                        logger.debug(f"Error screening: {e}")
            
            # Sort by score
            results = sorted(results, key=lambda x: x['score'], reverse=True)[:max_results]
            
            elapsed = time.time() - start_time
            
            return {
                'status': 'success',
                'strategy_name': strategy_name,
                'count': len(results),
                'execution_time': round(elapsed, 2),
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Screening error: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def run_screening_multi(self, strategy_names: List[str], max_results: int = 50,
                            max_tickers: Optional[int] = None,
                            time_budget_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Run multiple strategies efficiently by sharing data.
        Returns a dictionary with results for each strategy.
        """
        try:
            logger.info(f"Running multi-strategy screening for: {strategy_names}")
            start_time = time.time()
            deadline = None
            if time_budget_seconds is not None:
                try:
                    parsed_budget = float(time_budget_seconds)
                    if parsed_budget > 0:
                        deadline = start_time + parsed_budget
                except (TypeError, ValueError):
                    deadline = None

            def _time_budget_exceeded() -> bool:
                return deadline is not None and time.time() >= deadline
            
            strategies = []
            for name in strategy_names:
                try:
                    strategies.append(self.strategy_manager.get_strategy(name))
                except Exception as e:
                    logger.error(f"Strategy {name} not found: {e}")
            
            if not strategies:
                return {'status': 'error', 'message': 'No valid strategies found'}

            tickers = self._get_tickers()
            if not tickers:
                return {'status': 'error', 'message': 'No tickers found'}

            requested_ticker_limit = self.max_tickers
            if max_tickers is not None:
                try:
                    requested_ticker_limit = max(50, int(max_tickers))
                except (TypeError, ValueError):
                    requested_ticker_limit = self.max_tickers

            ticker_limit = min(self.max_tickers, requested_ticker_limit)
            needs_fundamentals = any(s.strategy_type in ['fundamental', 'hybrid'] for s in strategies)
            # Fundamental lookups are network-bound; cap universe to keep API responses interactive.
            if needs_fundamentals:
                ticker_limit = min(ticker_limit, 900)

            tickers_to_process = tickers[:ticker_limit]
            if not tickers_to_process:
                return {'status': 'error', 'message': 'No eligible tickers found'}
            
            # Initialize results containers
            strategy_results = {s.name: [] for s in strategies}
            timed_out = False
            submitted_tickers = 0
            processed_tickers = 0
            stop_event = Event()
            
            # Helper to screen one ticker against ALL strategies
            def screen_ticker_multi(ticker):
                try:
                    if stop_event.is_set() or _time_budget_exceeded():
                        return None

                    # 1. Fetch Data & Calculate Indicators ONCE
                    df = self._fetch_stock_data(ticker)
                    if df is None: return None
                    if stop_event.is_set() or _time_budget_exceeded():
                        return None
                    
                    tech_engine = TechnicalIndicatorEngine(df)
                    df_indicators = tech_engine.calculate_all_indicators()
                    latest = df_indicators.iloc[-1]
                    indicators = latest.to_dict()
                    
                    pattern_engine = PatternRecognitionEngine(df_indicators)
                    patterns = pattern_engine.detect_all_patterns()
                    if stop_event.is_set() or _time_budget_exceeded():
                        return None
                    
                    # Fundamentals - fetch once per ticker and share across all strategy evaluations.
                    fundamentals = {}
                    if needs_fundamentals:
                        if stop_event.is_set() or _time_budget_exceeded():
                            return None
                        fundamentals = self._fetch_fundamentals_cached(ticker)

                    ticker_results = {}
                    
                    # 2. Evaluate ALL strategies
                    for strategy in strategies:
                        if stop_event.is_set() or _time_budget_exceeded():
                            return None
                        total_score = 0.0
                        max_score = 0.0
                        conditions_passed = 0
                        
                        for condition in strategy.conditions:
                            max_score += condition.weight
                            passed, score = self._evaluate_condition(condition, indicators, fundamentals)
                            if passed:
                                total_score += score
                                conditions_passed += 1
                        
                        final_score = (total_score / max_score * 100) if max_score > 0 else 0
                        
                        if final_score >= 40: # Filter
                            ticker_results[strategy.name] = {
                                'ticker': ticker,
                                'score': round(final_score, 2),
                                'current_price': round(float(latest['close']), 2),
                                'conditions_passed': conditions_passed,
                                'total_conditions': len(strategy.conditions),
                                'confidence': round((conditions_passed / len(strategy.conditions)) * 100, 1),
                                'key_indicators': {
                                    'rsi_14': round(float(indicators.get('rsi_14', 0)), 2),
                                    'price_change_20d': round(float(indicators.get('price_change_20d', 0)), 2),
                                    'volume_ratio_20': round(float(indicators.get('volume_ratio_20', 0)), 2),
                                },
                                'patterns': [k for k, v in patterns.items() if v]
                            }
                    return ticker_results

                except Exception as e:
                    # logger.debug(f"Error screening {ticker}: {e}")
                    return None

            # Parallel execution with cooperative time-budget enforcement.
            executor = ThreadPoolExecutor(max_workers=self.max_workers)
            pending = {}
            ticker_iter = iter(tickers_to_process)

            def _submit_next() -> bool:
                nonlocal submitted_tickers, timed_out
                if stop_event.is_set() or _time_budget_exceeded():
                    timed_out = True
                    stop_event.set()
                    return False
                try:
                    next_ticker = next(ticker_iter)
                except StopIteration:
                    return False
                pending[executor.submit(screen_ticker_multi, next_ticker)] = next_ticker
                submitted_tickers += 1
                return True

            try:
                for _ in range(max(1, self.max_workers)):
                    if not _submit_next():
                        break

                while pending:
                    if _time_budget_exceeded():
                        timed_out = True
                        stop_event.set()
                        break

                    wait_timeout = None
                    if deadline is not None:
                        remaining = deadline - time.time()
                        if remaining <= 0:
                            timed_out = True
                            stop_event.set()
                            break
                        wait_timeout = min(0.5, max(0.0, remaining))

                    done, _ = wait(
                        list(pending.keys()),
                        timeout=wait_timeout,
                        return_when=FIRST_COMPLETED,
                    )

                    if not done:
                        continue

                    for future in done:
                        pending.pop(future, None)
                        processed_tickers += 1
                        try:
                            t_res = future.result()
                            if t_res:
                                for s_name, res in t_res.items():
                                    strategy_results[s_name].append(res)
                        except Exception:
                            pass

                        _submit_next()
            finally:
                if pending:
                    for future in list(pending.keys()):
                        future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
            
            # Sort and limit
            final_output = {}
            for s_name, res_list in strategy_results.items():
                final_output[s_name] = sorted(res_list, key=lambda x: x['score'], reverse=True)[:max_results]
                
            elapsed = time.time() - start_time
            if timed_out:
                logger.warning(
                    f"Multi-screening hit time budget after processing {processed_tickers}/{submitted_tickers} submitted tickers"
                )
            logger.info(f"Multi-screening finished in {elapsed:.2f}s")
            
            return {
                'status': 'success',
                'execution_time': round(elapsed, 2),
                'processed_tickers': processed_tickers,
                'submitted_tickers': submitted_tickers,
                'requested_tickers': ticker_limit,
                'timed_out': timed_out,
                'results': final_output,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Multi-screening error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_stock_analysis(self, ticker: str) -> Dict:
        """
        Get complete analysis for a single stock
        Including all indicators, patterns, and fundamentals
        """
        try:
            # Fetch data
            df = self._fetch_stock_data(ticker)
            if df is None or df.empty:
                return {
                    'status': 'error',
                    'message': f'No data available for {ticker}'
                }
            
            # Calculate indicators
            tech_engine = TechnicalIndicatorEngine(df)
            df_indicators = tech_engine.calculate_all_indicators()
            
            latest = df_indicators.iloc[-1]
            indicators = latest.to_dict()
            
            # Detect patterns
            pattern_engine = PatternRecognitionEngine(df_indicators)
            patterns = pattern_engine.detect_all_patterns()
            
            # Fetch fundamentals
            fund_engine = FundamentalAnalysisEngine(ticker)
            fundamentals = fund_engine.fetch_fundamentals()
            
            return {
                'status': 'success',
                'ticker': ticker,
                'current_price': float(latest['close']),
                'indicators': {k: float(v) if isinstance(v, (int, float, np.number)) else v 
                              for k, v in indicators.items()},
                'patterns': {k: bool(v) for k, v in patterns.items()},
                'fundamentals': fundamentals,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Analysis error for {ticker}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def export_strategy(self, strategy_name: str) -> Dict:
        """Export strategy as JSON for download"""
        try:
            strategy = self.strategy_manager.get_strategy(strategy_name)
            return {
                'status': 'success',
                'data': strategy.to_dict()
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def import_strategy(self, strategy_data: Dict) -> Dict:
        """Import strategy from JSON"""
        try:
            # Validate first
            validation = self.validate_strategy(strategy_data)
            if not validation['valid']:
                return {
                    'status': 'error',
                    'message': 'Validation failed',
                    'errors': validation['errors']
                }
            
            # Create strategy
            return self.create_custom_strategy(strategy_data)
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def delete_strategy(self, strategy_name: str) -> Dict:
        """Delete a custom strategy"""
        try:
            self.strategy_manager.delete_strategy(strategy_name)
            return {
                'status': 'success',
                'message': f"Strategy '{strategy_name}' deleted successfully"
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    # ==================== INTERNAL METHODS ====================
    
    def _get_tickers(self) -> List[str]:
        """Get all available tickers from database"""
        try:
            raw_data = self.pipeline.get_latest_data(limit=None)
            df = pd.DataFrame(raw_data)
            
            if df.empty:
                return []
            
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0)

            df = df[df['close'] >= 10]
            df = df[df['volume'] >= 100000]
            if df.empty:
                return []

            # Process liquid tickers first so bounded scans still return actionable names.
            df = df.sort_values('volume', ascending=False)
            df = df.drop_duplicates(subset=['ticker'])

            return df['ticker'].tolist()
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return []

    def _fetch_fundamentals_cached(self, ticker: str) -> Dict[str, Any]:
        """Fetch fundamentals with screener-level cache to avoid repeated network calls."""
        cache_key = f"fund_{ticker}"

        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            self.rate_limiter.wait()
            fund_engine = FundamentalAnalysisEngine(ticker)
            fundamentals = fund_engine.fetch_fundamentals() or {}
            self.cache.set(cache_key, fundamentals)
            return fundamentals
        except Exception as e:
            logger.debug(f"Error fetching fundamentals for {ticker}: {e}")
            return {}
    
    def _fetch_stock_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Fetch stock data with caching"""
        cache_key = f"data_{ticker}"
        
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            raw_data = self.pipeline.get_ticker_history(ticker)
            df = pd.DataFrame(raw_data)
            
            if df.empty or len(df) < 100:
                return None
            
            df = df.sort_values('date')
            df.columns = [c.lower() for c in df.columns]
            
            self.cache.set(cache_key, df)
            return df
            
        except Exception as e:
            logger.debug(f"Error fetching data for {ticker}: {e}")
            return None
    
    def _screen_stock(self, ticker: str, strategy: TradingStrategy) -> Optional[Dict]:
        """Screen a single stock against strategy"""
        try:
            # Fetch data
            df = self._fetch_stock_data(ticker)
            if df is None:
                return None
            
            # Calculate indicators
            tech_engine = TechnicalIndicatorEngine(df)
            df_indicators = tech_engine.calculate_all_indicators()
            
            latest = df_indicators.iloc[-1]
            indicators = latest.to_dict()
            
            # Fetch fundamentals if needed
            fundamentals = {}
            if strategy.strategy_type in ['fundamental', 'hybrid']:
                fundamentals = self._fetch_fundamentals_cached(ticker)
            
            # Detect patterns
            pattern_engine = PatternRecognitionEngine(df_indicators)
            patterns = pattern_engine.detect_all_patterns()
            
            # Evaluate conditions
            total_score = 0.0
            max_score = 0.0
            conditions_passed = 0
            
            for condition in strategy.conditions:
                max_score += condition.weight
                passed, score = self._evaluate_condition(condition, indicators, fundamentals)
                if passed:
                    total_score += score
                    conditions_passed += 1
            
            final_score = (total_score / max_score * 100) if max_score > 0 else 0
            
            if final_score < 40:  # Filter out low scores
                return None
            
            return {
                'ticker': ticker,
                'score': round(final_score, 2),
                'current_price': round(float(latest['close']), 2),
                'conditions_passed': conditions_passed,
                'total_conditions': len(strategy.conditions),
                'confidence': round((conditions_passed / len(strategy.conditions)) * 100, 1),
                'key_indicators': {
                    'rsi_14': round(float(indicators.get('rsi_14', 0)), 2),
                    'price_change_20d': round(float(indicators.get('price_change_20d', 0)), 2),
                    'volume_ratio_20': round(float(indicators.get('volume_ratio_20', 0)), 2),
                },
                'patterns': [k for k, v in patterns.items() if v]
            }
            
        except Exception as e:
            logger.debug(f"Error screening {ticker}: {e}")
            return None
    
    def _evaluate_condition(self, condition: StrategyCondition,
                           indicators: Dict, fundamentals: Dict) -> Tuple[bool, float]:
        """Evaluate a single condition"""
        
        # Get indicator value
        indicator_value = None
        
        if condition.indicator in indicators:
            indicator_value = indicators[condition.indicator]
        elif condition.indicator in fundamentals:
            indicator_value = fundamentals[condition.indicator]
        elif isinstance(condition.value, str) and condition.value in indicators:
            # Comparing two indicators (e.g., close > sma_50)
            indicator_value = indicators.get(condition.indicator)
            comparison_value = indicators.get(condition.value)
            
            if indicator_value is None or comparison_value is None:
                return False, 0.0
            
            if condition.operator == '>':
                passed = indicator_value > comparison_value
            elif condition.operator == '>=':
                passed = indicator_value >= comparison_value
            elif condition.operator == '<':
                passed = indicator_value < comparison_value
            elif condition.operator == '<=':
                passed = indicator_value <= comparison_value
            else:
                passed = False
            
            return passed, condition.weight if passed else 0.0
        
        if indicator_value is None:
            return False, 0.0
        
        # Evaluate condition
        try:
            if condition.operator == '>':
                passed = float(indicator_value) > float(condition.value)
            elif condition.operator == '>=':
                passed = float(indicator_value) >= float(condition.value)
            elif condition.operator == '<':
                passed = float(indicator_value) < float(condition.value)
            elif condition.operator == '<=':
                passed = float(indicator_value) <= float(condition.value)
            elif condition.operator == '==':
                passed = float(indicator_value) == float(condition.value)
            elif condition.operator == '!=':
                passed = float(indicator_value) != float(condition.value)
            elif condition.operator == 'between':
                if isinstance(condition.value, (list, tuple)) and len(condition.value) == 2:
                    passed = condition.value[0] <= float(indicator_value) <= condition.value[1]
                else:
                    passed = False
            else:
                passed = False
            
            return passed, condition.weight if passed else 0.0
            
        except (ValueError, TypeError):
            return False, 0.0


# ==================== LEGACY WRAPPER FOR APPLICATION.PY ====================

class StockScreener:
    """
    Backwards-compatible wrapper used by `application.py`.

    The newer implementation in this file is `InteractiveStockScreener`,
    which powers the rich strategy engine and indicator catalog.

    This thin adapter exposes the older method names expected by the
    Flask backend (`piotroski_scan`, `momentum_scan`, etc.) by delegating
    to `InteractiveStockScreener.run_screening`.
    """

    def __init__(self, pipeline, cache_ttl: int = 3600, max_workers: int = 10, max_tickers: int = 2500):
        self._interactive = InteractiveStockScreener(pipeline, cache_ttl=cache_ttl, max_workers=max_workers, max_tickers=max_tickers)

    def _run(self, strategy_name: str, max_results: int = 50):
        """Helper to run a strategy and always return a DataFrame."""
        result = self._interactive.run_screening(strategy_name, max_results=max_results)
        if not isinstance(result, dict):
            return pd.DataFrame()
        if result.get('status') != 'success':
            return pd.DataFrame()
        rows = result.get('results') or []
        try:
            return pd.DataFrame(rows)
        except Exception:
            return pd.DataFrame()

    def piotroski_scan(self, min_score: int = 7):
        df = self._run('piotroski', max_results=200)
        if 'piotroski_score' in df.columns:
            df = df[df['piotroski_score'] >= min_score]
        return df

    def momentum_scan(self, lookback_days: int = 20, min_return: float = 5.0):
        # Strategy parameters are encoded inside the strategy definition; we
        # simply run the named strategy and optionally filter by min_return.
        df = self._run('momentum', max_results=200)
        # Try to respect caller's min_return if the column exists
        for col in ['price_change_20d', 'expected_return_pct', 'momentum_return']:
            if col in df.columns:
                df = df[df[col] >= min_return]
                break
        return df

    def value_investing_scan(self):
        return self._run('value', max_results=200)

    def swing_trading_scan(self):
        return self._run('swing', max_results=200)

    def breakout_scan(self, volume_threshold: float = 1.5):
        df = self._run('breakout', max_results=200)
        # Best-effort volume filter if we have a suitable column
        for col in ['volume_ratio', 'volume_score']:
            if col in df.columns:
                df = df[df[col] >= volume_threshold]
                break
        return df

    def custom_scan(self, conditions: dict):
        """
        Basic custom scan for the legacy `/api/screen/custom` endpoint.

        To keep behaviour predictable across environments, this implementation
        returns an empty DataFrame when no dedicated custom strategy is
        configured in the advanced engine. The React UI handles the "no
        results" case gracefully.
        """
        return pd.DataFrame()
    
    def execute_custom_strategy(self, conditions: list):
        """
        Execute a custom strategy based on a list of conditions.
        Each condition should have: indicator, operator, value, weight
        """
        try:
            # Get latest stock data
            df = self.get_latest_screening_data()
            
            if df.empty:
                return pd.DataFrame()
            
            # Track scores for each stock
            scores = {}
            
            for ticker in df['ticker'].unique():
                stock_data = df[df['ticker'] == ticker].iloc[-1].to_dict()
                score = 0
                conditions_met = 0
                
                for condition in conditions:
                    try:
                        indicator = condition.get('indicator')
                        operator = condition.get('operator')
                        value = condition.get('value')
                        weight = float(condition.get('weight', 1.0))
                        
                        # Get the indicator value from stock data
                        indicator_value = float(stock_data.get(indicator, 0))
                        condition_value = float(value) if value else 0
                        
                        # Evaluate condition
                        result = False
                        if operator == '>':
                            result = indicator_value > condition_value
                        elif operator == '<':
                            result = indicator_value < condition_value
                        elif operator == '>=':
                            result = indicator_value >= condition_value
                        elif operator == '<=':
                            result = indicator_value <= condition_value
                        elif operator == '==':
                            result = indicator_value == condition_value
                        elif operator == 'between':
                            lower = condition.get('lower', 0)
                            upper = condition.get('upper', 100)
                            result = lower <= indicator_value <= upper
                        
                        if result:
                            score += weight
                            conditions_met += 1
                    except (ValueError, KeyError, TypeError) as e:
                        logger.debug(f"Error evaluating condition for {ticker}: {e}")
                        continue
                
                if conditions_met > 0:
                    scores[ticker] = {
                        'score': score,
                        'conditions_met': conditions_met,
                        'total_conditions': len(conditions)
                    }
            
            if not scores:
                return pd.DataFrame()
            
            # Filter stocks that meet at least half the conditions
            min_conditions = max(1, len(conditions) // 2)
            qualified_tickers = [t for t, s in scores.items() if s['conditions_met'] >= min_conditions]
            
            if not qualified_tickers:
                return pd.DataFrame()
            
            # Return filtered results sorted by score
            results = df[df['ticker'].isin(qualified_tickers)].copy()
            results['custom_score'] = results['ticker'].map(lambda t: scores.get(t, {}).get('score', 0))
            results = results.sort_values('custom_score', ascending=False)
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing custom strategy: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def run_strategy(self, strategy_name: str, max_results: int = 50):
        """
        Generic method to run any strategy by name.
        """
        return self._run(strategy_name, max_results=max_results)

    def run_multiple_strategies(self, strategy_names: List[str], max_results: int = 50,
                                max_tickers: Optional[int] = None,
                                time_budget_seconds: Optional[float] = None) -> Dict[str, Any]:
        """
        Run multiple strategies efficiently.
        """
        return self._interactive.run_screening_multi(
            strategy_names,
            max_results=max_results,
            max_tickers=max_tickers,
            time_budget_seconds=time_budget_seconds,
        )
    



# ==================== EXAMPLE USAGE ====================

def interactive_demo():
    """Interactive demonstration of the screener"""
    
    print("\n" + "="*80)
    print("INTERACTIVE ADVANCED STOCK SCREENER")
    print("API-Ready for React Frontend Integration")
    print("="*80 + "\n")
    
    from IntegratedPostGreSQL import NSEDataPipeline
    DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"
    
    pipeline = NSEDataPipeline(DB_URL)
    screener = InteractiveStockScreener(pipeline)
    
    # 1. Get indicator catalog (for frontend UI)
    print("\n[1] GETTING INDICATOR CATALOG")
    print("-" * 80)
    catalog = screener.get_indicator_catalog()
    print(f"Technical Indicator Categories: {len(catalog['technical_indicators'])}")
    print(f"Fundamental Indicator Categories: {len(catalog['fundamental_indicators'])}")
    print(f"Candlestick Patterns: {len(catalog['candlestick_patterns'])}")
    print(f"Available Operators: {len(catalog['operators'])}")
    
    # Show sample technical indicators
    print("\nSample Technical Indicators:")
    for category, indicators in list(catalog['technical_indicators'].items())[:2]:
        print(f"\n  {category}:")
        for ind in indicators[:3]:
            print(f"    - {ind['name']}: {ind['description']}")
    
    # 2. Get predefined strategies
    print("\n[2] GETTING PREDEFINED STRATEGIES")
    print("-" * 80)
    strategies = screener.get_predefined_strategies()
    print(f"Total Strategies: {len(strategies['strategies'])}")
    print(f"Categories: {', '.join(strategies['categories'])}")
    
    # Show sample strategies
    print("\nSample Strategies:")
    for name, strategy in list(strategies['strategies'].items())[:3]:
        print(f"\n  {strategy['name'].upper()}")
        print(f"    Category: {strategy['category']}")
        print(f"    Risk: {strategy['risk_level']}")
        print(f"    Description: {strategy['description']}")
        print(f"    Conditions: {len(strategy['conditions'])}")
    
    # 3. Create custom strategy
    print("\n[3] CREATING CUSTOM STRATEGY")
    print("-" * 80)
    
    custom_strategy_data = {
        'name': 'demo_custom_strategy',
        'description': 'Demo strategy combining momentum and value',
        'strategy_type': 'hybrid',
        'conditions': [
            {'indicator': 'rsi_14', 'operator': 'between', 'value': [40, 60], 'weight': 1.5},
            {'indicator': 'roe', 'operator': '>', 'value': 0.15, 'weight': 2.0},
            {'indicator': 'trailing_pe', 'operator': '<', 'value': 20, 'weight': 1.0},
        ],
        'metadata': {
            'category': 'Custom',
            'risk_level': 'Medium',
            'holding_period': '3-6 months'
        }
    }
    
    # Validate first
    validation = screener.validate_strategy(custom_strategy_data)
    print(f"Validation Result: {'✓ VALID' if validation['valid'] else '✗ INVALID'}")
    if validation['errors']:
        print(f"Errors: {validation['errors']}")
    
    if validation['valid']:
        result = screener.create_custom_strategy(custom_strategy_data)
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
    
    # 4. Run screening
    print("\n[4] RUNNING SCREENING - Momentum Strategy")
    print("-" * 80)
    
    screening_result = screener.run_screening('momentum', max_results=10)
    
    if screening_result['status'] == 'success':
        print(f"Found: {screening_result['count']} stocks")
        print(f"Execution Time: {screening_result['execution_time']}s")
        
        if screening_result['results']:
            print("\nTop 5 Results:")
            for i, stock in enumerate(screening_result['results'][:5], 1):
                print(f"\n  {i}. {stock['ticker']}")
                print(f"     Score: {stock['score']}/100")
                print(f"     Price: ₹{stock['current_price']}")
                print(f"     Confidence: {stock['confidence']}%")
                print(f"     RSI: {stock['key_indicators']['rsi_14']}")
                print(f"     20D Change: {stock['key_indicators']['price_change_20d']}%")
    
    # 5. Get stock analysis
    if screening_result['status'] == 'success' and screening_result['results']:
        top_ticker = screening_result['results'][0]['ticker']
        
        print(f"\n[5] DETAILED ANALYSIS - {top_ticker}")
        print("-" * 80)
        
        analysis = screener.get_stock_analysis(top_ticker)
        
        if analysis['status'] == 'success':
            print(f"Current Price: ₹{analysis['current_price']}")
            print(f"\nKey Technical Indicators:")
            print(f"  RSI 14: {analysis['indicators'].get('rsi_14', 'N/A')}")
            print(f"  MACD Hist: {analysis['indicators'].get('macd_hist', 'N/A')}")
            print(f"  ADX 14: {analysis['indicators'].get('adx_14', 'N/A')}")
            
            if analysis['patterns']:
                print(f"\nDetected Patterns:")
                for pattern, detected in analysis['patterns'].items():
                    if detected:
                        print(f"  ✓ {pattern}")
            
            if analysis['fundamentals']:
                print(f"\nFundamentals:")
                print(f"  P/E Ratio: {analysis['fundamentals'].get('trailing_pe', 'N/A')}")
                print(f"  ROE: {analysis['fundamentals'].get('roe', 'N/A')}")
                print(f"  Debt/Equity: {analysis['fundamentals'].get('debt_to_equity', 'N/A')}")
    
    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("All methods return JSON-serializable data ready for React frontend")
    print("="*80 + "\n")


if __name__ == "__main__":
    interactive_demo()

    """
Flask API Endpoints for Interactive Advanced Stock Screener
===========================================================
Complete API integration for React frontend

Endpoints:
- GET  /api/screener/catalog - Get indicator catalog
- GET  /api/screener/strategies - Get all strategies
- GET  /api/screener/strategies/<name> - Get specific strategy
- POST /api/screener/strategies - Create custom strategy
- PUT  /api/screener/strategies/<name> - Update strategy
- DEL  /api/screener/strategies/<name> - Delete strategy
- POST /api/screener/validate - Validate strategy
- POST /api/screener/run - Run screening
- GET  /api/screener/analysis/<ticker> - Get stock analysis
- POST /api/screener/export - Export strategy
- POST /api/screener/import - Import strategy
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from IntegratedPostGreSQL import NSEDataPipeline, DB_URL
import logging
from functools import wraps
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize components
pipeline = NSEDataPipeline(DB_URL)
screener = InteractiveStockScreener(pipeline, cache_ttl=3600)

# Request tracking for rate limiting
request_times = {}


def rate_limit(max_requests=60, window=60):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            now = time.time()
            
            if client_ip not in request_times:
                request_times[client_ip] = []
            
            # Remove old requests
            request_times[client_ip] = [
                t for t in request_times[client_ip]
                if now - t < window
            ]
            
            # Check rate limit
            if len(request_times[client_ip]) >= max_requests:
                return jsonify({
                    'status': 'error',
                    'message': 'Rate limit exceeded. Please try again later.'
                }), 429
            
            request_times[client_ip].append(now)
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# ==================== INDICATOR CATALOG ENDPOINTS ====================

@app.route('/api/screener/catalog', methods=['GET'])
@rate_limit(max_requests=100, window=60)
def get_indicator_catalog():
    """
    Get complete indicator catalog
    
    Response:
    {
        'technical_indicators': {...},
        'fundamental_indicators': {...},
        'candlestick_patterns': [...],
        'operators': [...]
    }
    """
    try:
        catalog = screener.get_indicator_catalog()
        return jsonify({
            'status': 'success',
            'data': catalog
        })
    except Exception as e:
        logger.error(f"Error fetching catalog: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/screener/catalog/technical', methods=['GET'])
@rate_limit()
def get_technical_indicators():
    """Get only technical indicators"""
    try:
        return jsonify({
            'status': 'success',
            'data': IndicatorCatalog.get_technical_indicators()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/screener/catalog/fundamental', methods=['GET'])
@rate_limit()
def get_fundamental_indicators():
    """Get only fundamental indicators"""
    try:
        return jsonify({
            'status': 'success',
            'data': IndicatorCatalog.get_fundamental_indicators()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/screener/catalog/patterns', methods=['GET'])
@rate_limit()
def get_patterns():
    """Get candlestick patterns"""
    try:
        return jsonify({
            'status': 'success',
            'data': IndicatorCatalog.get_candlestick_patterns()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== STRATEGY ENDPOINTS ====================

@app.route('/api/screener/strategies', methods=['GET'])
@rate_limit()
def get_strategies():
    """
    Get all strategies (predefined + custom)
    
    Query params:
    - category: Filter by category (optional)
    - type: 'predefined' or 'custom' or 'all' (default: 'all')
    """
    try:
        strategy_type = request.args.get('type', 'all')
        category = request.args.get('category')
        
        if strategy_type == 'predefined' or strategy_type == 'all':
            predefined = screener.get_predefined_strategies(category)
        else:
            predefined = {'strategies': {}, 'categories': []}
        
        if strategy_type == 'custom' or strategy_type == 'all':
            custom = screener.get_custom_strategies()
        else:
            custom = []
        
        return jsonify({
            'status': 'success',
            'data': {
                'predefined': predefined,
                'custom': custom
            }
        })
    except Exception as e:
        logger.error(f"Error fetching strategies: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/screener/strategies/categories', methods=['GET'])
@rate_limit()
def get_strategy_categories():
    """Get all strategy categories"""
    try:
        return jsonify({
            'status': 'success',
            'data': StrategyLibrary.get_strategy_categories()
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/screener/strategies/<strategy_name>', methods=['GET'])
@rate_limit()
def get_strategy(strategy_name):
    """Get specific strategy details"""
    try:
        result = screener.export_strategy(strategy_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/screener/strategies', methods=['POST'])
@rate_limit(max_requests=20, window=60)
def create_strategy():
    """
    Create custom strategy
    
    Request body:
    {
        'name': 'my_strategy',
        'description': 'Strategy description',
        'strategy_type': 'technical',
        'conditions': [
            {
                'indicator': 'rsi_14',
                'operator': '>',
                'value': 50,
                'weight': 1.0
            },
            ...
        ],
        'metadata': {
            'category': 'Custom',
            'risk_level': 'Medium',
            'holding_period': '1-3 months'
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        result = screener.create_custom_strategy(data)
        
        if result['status'] == 'success':
            return jsonify(result), 201
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/screener/strategies/<strategy_name>', methods=['DELETE'])
@rate_limit(max_requests=20, window=60)
def delete_strategy(strategy_name):
    """Delete custom strategy"""
    try:
        result = screener.delete_strategy(strategy_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


@app.route('/api/screener/strategies/validate', methods=['POST'])
@rate_limit()
def validate_strategy():
    """
    Validate strategy before creation
    
    Request body: Same as create_strategy
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        result = screener.validate_strategy(data)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ==================== SCREENING ENDPOINTS ====================

@app.route('/api/screener/run', methods=['POST'])
@rate_limit(max_requests=10, window=60)
def run_screening():
    """
    Run stock screening
    
    Request body:
    {
        'strategy_name': 'momentum',
        'max_results': 50
    }
    
    Response:
    {
        'status': 'success',
        'strategy_name': 'momentum',
        'count': 25,
        'execution_time': 15.32,
        'results': [
            {
                'ticker': 'RELIANCE',
                'score': 85.5,
                'current_price': 2456.75,
                'conditions_passed': 4,
                'total_conditions': 5,
                'confidence': 80.0,
                'key_indicators': {...},
                'patterns': [...]
            },
            ...
        ],
        'timestamp': '2026-01-30T...'
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'strategy_name' not in data:
            return jsonify({
                'status': 'error',
                'message': 'strategy_name is required'
            }), 400
        
        strategy_name = data['strategy_name']
        max_results = data.get('max_results', 50)
        
        logger.info(f"Running screening: {strategy_name}")
        
        result = screener.run_screening(strategy_name, max_results)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Screening error: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/screener/analysis/<ticker>', methods=['GET'])
@rate_limit(max_requests=30, window=60)
def get_stock_analysis(ticker):
    """
    Get complete analysis for a single stock
    
    Response:
    {
        'status': 'success',
        'ticker': 'RELIANCE',
        'current_price': 2456.75,
        'indicators': {
            'rsi_14': 62.5,
            'macd_hist': 15.23,
            'adx_14': 28.5,
            ...
        },
        'patterns': {
            'doji': false,
            'hammer': true,
            ...
        },
        'fundamentals': {
            'trailing_pe': 18.5,
            'roe': 0.145,
            ...
        },
        'timestamp': '2026-01-30T...'
    }
    """
    try:
        result = screener.get_stock_analysis(ticker.upper())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Analysis error for {ticker}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ==================== IMPORT/EXPORT ENDPOINTS ====================

@app.route('/api/screener/strategies/export/<strategy_name>', methods=['GET'])
@rate_limit()
def export_strategy(strategy_name):
    """Export strategy as JSON"""
    try:
        result = screener.export_strategy(strategy_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/screener/strategies/import', methods=['POST'])
@rate_limit(max_requests=10, window=60)
def import_strategy():
    """
    Import strategy from JSON
    
    Request body: Complete strategy object
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        result = screener.import_strategy(data)
        
        if result['status'] == 'success':
            return jsonify(result), 201
        else:
            return jsonify(result), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ==================== UTILITY ENDPOINTS ====================

@app.route('/api/screener/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Interactive Stock Screener',
        'version': '3.0',
        'components': {
            'database': 'connected',
            'screener': 'active',
            'strategy_manager': 'active'
        }
    })


@app.route('/api/screener/stats', methods=['GET'])
@rate_limit()
def get_stats():
    """Get screener statistics"""
    try:
        custom_strategies = screener.get_custom_strategies()
        predefined_strategies = screener.get_predefined_strategies()
        
        return jsonify({
            'status': 'success',
            'data': {
                'total_strategies': len(custom_strategies) + len(predefined_strategies['strategies']),
                'custom_strategies': len(custom_strategies),
                'predefined_strategies': len(predefined_strategies['strategies']),
                'categories': len(predefined_strategies['categories']),
                'cache_size': len(screener.cache.cache)
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'status': 'error',
        'message': 'Rate limit exceeded. Please try again later.'
    }), 429


# ==================== DOCUMENTATION ENDPOINT ====================

@app.route('/api/screener/docs', methods=['GET'])
def api_documentation():
    """Get API documentation"""
    return jsonify({
        'service': 'Interactive Advanced Stock Screener API',
        'version': '3.0',
        'endpoints': {
            'Catalog': {
                'GET /api/screener/catalog': 'Get complete indicator catalog',
                'GET /api/screener/catalog/technical': 'Get technical indicators',
                'GET /api/screener/catalog/fundamental': 'Get fundamental indicators',
                'GET /api/screener/catalog/patterns': 'Get candlestick patterns'
            },
            'Strategies': {
                'GET /api/screener/strategies': 'Get all strategies',
                'GET /api/screener/strategies/<name>': 'Get specific strategy',
                'POST /api/screener/strategies': 'Create custom strategy',
                'DELETE /api/screener/strategies/<name>': 'Delete custom strategy',
                'POST /api/screener/strategies/validate': 'Validate strategy',
                'GET /api/screener/strategies/categories': 'Get strategy categories'
            },
            'Screening': {
                'POST /api/screener/run': 'Run stock screening',
                'GET /api/screener/analysis/<ticker>': 'Get stock analysis'
            },
            'Import/Export': {
                'GET /api/screener/strategies/export/<name>': 'Export strategy',
                'POST /api/screener/strategies/import': 'Import strategy'
            },
            'Utility': {
                'GET /api/screener/health': 'Health check',
                'GET /api/screener/stats': 'Get statistics',
                'GET /api/screener/docs': 'API documentation'
            }
        },
        'rate_limits': {
            'default': '60 requests per minute',
            'screening': '10 requests per minute',
            'strategy_creation': '20 requests per minute'
        }
    })


# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("="*80)
    logger.info("STARTING INTERACTIVE STOCK SCREENER API")
    logger.info("="*80)
    logger.info("Service: Interactive Advanced Stock Screener")
    logger.info("Version: 3.0")
    logger.info("Port: 5001")
    logger.info("Documentation: http://localhost:5001/api/screener/docs")
    logger.info("="*80)
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        threaded=True
    )