# import pandas as pd
# import pandas_ta as ta
# import yfinance as yf
# from textblob import TextBlob
# import numpy as np
# from typing import Dict, List, Tuple, Optional
# import logging
# from datetime import datetime, timedelta
# import warnings
# from functools import lru_cache
# from sklearn.preprocessing import RobustScaler
# from sqlalchemy import create_engine, text, inspect
# from sqlalchemy.exc import ProgrammingError
# from tqdm import tqdm

# # Filter warnings
# warnings.filterwarnings('ignore')

# # Configure logging (ASCII only for Windows compatibility)
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('feature_engineering.log'),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

# # --- CONFIGURATION ---
# DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"

# class StockFeatureEngineer:
#     """
#     Production-grade feature engineering pipeline for stock price prediction.
#     """
    
#     def __init__(self, df: pd.DataFrame, ticker: str = None):
#         """
#         Initialize with OHLCV data.
#         Sets DatetimeIndex for pandas_ta compatibility.
#         """
#         # Lowercase columns for consistency
#         df.columns = [c.lower() for c in df.columns]
        
#         required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
#         missing_cols = [col for col in required_cols if col not in df.columns]
#         if missing_cols:
#             raise ValueError(f"Missing required columns: {missing_cols}")
        
#         self.df = df.copy()
#         self.ticker = ticker
        
#         # 1. Convert date to datetime
#         self.df['date'] = pd.to_datetime(self.df['date'])
        
#         # 2. Set Date as Index (Required for VWAP and Time-Series functions)
#         self.df.set_index('date', inplace=True)
#         self.df.sort_index(inplace=True)
        
#         # 3. Handle Duplicate Indices
#         if not self.df.index.is_unique:
#             self.df = self.df.loc[~self.df.index.duplicated(keep='first')]

#         # Use adj_close if available, otherwise close
#         if 'adj_close' in self.df.columns:
#             self.df['price'] = self.df['adj_close']
#         else:
#             self.df['price'] = self.df['close']
        
#         # Store original columns
#         self.original_cols = self.df.columns.tolist()

#     def add_technical_indicators(self) -> pd.DataFrame:
#         """Comprehensive technical indicators suite."""
#         # 1. Moving Averages
#         for period in [5, 10, 20, 50, 100, 200]:
#             self.df[f'sma_{period}'] = self.df.ta.sma(length=period)
#             self.df[f'ema_{period}'] = self.df.ta.ema(length=period)
        
#         # 2. MACD
#         try:
#             macd = self.df.ta.macd(fast=12, slow=26, signal=9)
#             if macd is not None:
#                 self.df = pd.concat([self.df, macd], axis=1)
#         except Exception: pass
        
#         # 3. ADX
#         try:
#             adx = self.df.ta.adx(length=14)
#             if adx is not None:
#                 self.df = pd.concat([self.df, adx], axis=1)
#         except Exception: pass
        
#         # 4. Ichimoku Cloud
#         try:
#             ichimoku = self.df.ta.ichimoku()
#             if ichimoku is not None and len(ichimoku) > 0:
#                 self.df = pd.concat([self.df, ichimoku[0]], axis=1)
#         except Exception: pass
        
#         # 5. Parabolic SAR
#         try:
#             psar = self.df.ta.psar()
#             if psar is not None:
#                 self.df = pd.concat([self.df, psar], axis=1)
#         except Exception: pass
        
#         # 6. RSI
#         for period in [9, 14, 21]:
#             self.df[f'rsi_{period}'] = self.df.ta.rsi(length=period)
        
#         # 7. Stochastic
#         try:
#             stoch = self.df.ta.stoch(k=14, d=3)
#             if stoch is not None:
#                 self.df = pd.concat([self.df, stoch], axis=1)
#         except Exception: pass
        
#         # 8. Williams %R
#         self.df['willr'] = self.df.ta.willr(length=14)
        
#         # 9. ROC
#         for period in [9, 14, 21]:
#             self.df[f'roc_{period}'] = self.df.ta.roc(length=period)
        
#         # 10. CCI
#         self.df['cci'] = self.df.ta.cci(length=20)
        
#         # 11. MFI
#         self.df['mfi'] = self.df.ta.mfi(length=14)
        
#         # 12. Bollinger Bands
#         try:
#             bbands = self.df.ta.bbands(length=20, std=2)
#             if bbands is not None:
#                 self.df = pd.concat([self.df, bbands], axis=1)
#                 if 'BBU_20_2.0' in self.df.columns and 'BBL_20_2.0' in self.df.columns:
#                     self.df['bb_width'] = (self.df['BBU_20_2.0'] - self.df['BBL_20_2.0']) / (self.df['BBM_20_2.0'] + 1e-10)
#         except Exception: pass
        
#         # 13. ATR
#         for period in [7, 14, 21]:
#             self.df[f'atr_{period}'] = self.df.ta.atr(length=period)
        
#         # 14. Keltner Channels
#         try:
#             kc = self.df.ta.kc(length=20)
#             if kc is not None:
#                 self.df = pd.concat([self.df, kc], axis=1)
#         except Exception: pass
        
#         # 15. Historical Volatility
#         self.df['hist_vol_20'] = self.df['close'].pct_change().rolling(20).std() * np.sqrt(252)
        
#         # 16. Volume SMA
#         self.df['volume_sma_20'] = self.df['volume'].rolling(20).mean()
#         self.df['volume_ratio'] = self.df['volume'] / (self.df['volume_sma_20'] + 1e-10)
        
#         # 17. OBV
#         self.df['obv'] = self.df.ta.obv()
        
#         # 18. VWAP
#         try:
#             if not isinstance(self.df.index, pd.DatetimeIndex):
#                 self.df.index = pd.to_datetime(self.df.index)
            
#             vwap = self.df.ta.vwap()
#             if isinstance(vwap, pd.Series):
#                 self.df['vwap'] = vwap
#             elif isinstance(vwap, pd.DataFrame):
#                 self.df['vwap'] = vwap.iloc[:, 0]
#         except Exception:
#             tp = (self.df['high'] + self.df['low'] + self.df['close']) / 3
#             self.df['vwap'] = (tp * self.df['volume']).cumsum() / (self.df['volume'].cumsum() + 1e-10)
        
#         # 19. Accumulation/Distribution
#         self.df['ad'] = self.df.ta.ad()
        
#         # 20. Chaikin Money Flow
#         self.df['cmf'] = self.df.ta.cmf(length=20)
        
#         # 21. SuperTrend
#         for mult in [2, 3]:
#             try:
#                 st = self.df.ta.supertrend(length=10, multiplier=mult)
#                 if st is not None:
#                     self.df = pd.concat([self.df, st.add_suffix(f'_{mult}')], axis=1)
#             except Exception: pass
        
#         return self.df

#     def add_price_patterns(self) -> pd.DataFrame:
#         """Advanced candlestick pattern detection."""
#         patterns = [
#             'doji', 'hammer', 'inverted_hammer', 'hanging_man',
#             'engulfing', 'harami', 'piercing', 'dark_cloud_cover',
#             'morning_star', 'evening_star', 'shooting_star', 'marubozu'
#         ]
        
#         for pattern in patterns:
#             try:
#                 result = self.df.ta.cdl_pattern(name=pattern)
#                 if result is not None:
#                     self.df[f'cdl_{pattern}'] = result / 100.0
#             except Exception: pass
        
#         # Price Action Features
#         self.df['body_size'] = abs(self.df['close'] - self.df['open']) / (self.df['close'] + 1e-10)
#         self.df['swing_high'] = self.df['high'].rolling(window=10, center=True).max()
#         self.df['swing_low'] = self.df['low'].rolling(window=10, center=True).min()
#         self.df['gap_up'] = ((self.df['open'] - self.df['close'].shift(1)) / (self.df['close'].shift(1) + 1e-10)) > 0.02
        
#         return self.df

#     def add_statistical_features(self) -> pd.DataFrame:
#         """Statistical features."""
#         for period in [1, 3, 5, 10, 20]:
#             self.df[f'return_{period}d'] = self.df['close'].pct_change(period)
#             self.df[f'log_return_{period}d'] = np.log(self.df['close'] / (self.df['close'].shift(period) + 1e-10))
        
#         for window in [5, 10, 20]:
#             self.df[f'return_mean_{window}'] = self.df['return_1d'].rolling(window).mean()
#             self.df[f'return_std_{window}'] = self.df['return_1d'].rolling(window).std()
        
#         for period in [20, 50]:
#             mean = self.df['close'].rolling(period).mean()
#             std = self.df['close'].rolling(period).std()
#             self.df[f'zscore_{period}'] = (self.df['close'] - mean) / (std + 1e-10)
        
#         self.df['momentum_10'] = self.df['close'] - self.df['close'].shift(10)
#         return self.df

#     def add_market_microstructure(self) -> pd.DataFrame:
#         """Liquidity features."""
#         self.df['hl_spread'] = (self.df['high'] - self.df['low']) / (self.df['close'] + 1e-10)
#         self.df['amihud_ratio'] = abs(self.df['return_1d']) / (self.df['volume'] * self.df['close'] + 1e-10)
        
#         if 'vwap' in self.df.columns:
#             self.df['vwap_deviation'] = (self.df['close'] - self.df['vwap']) / (self.df['vwap'] + 1e-10)
        
#         return self.df

#     @lru_cache(maxsize=128)
#     def get_fundamental_data(self, ticker: str) -> Dict:
#         """Fetch fundamental data with caching."""
#         if not ticker: return {}
#         try:
#             stock = yf.Ticker(ticker)
#             info = stock.info
#             return {
#                 'market_cap': info.get('marketCap', 0),
#                 'pe_ratio': info.get('trailingPE', 0),
#                 'forward_pe': info.get('forwardPE', 0),
#                 'pb_ratio': info.get('priceToBook', 0),
#                 'profit_margins': info.get('profitMargins', 0),
#                 'roe': info.get('returnOnEquity', 0),
#                 'debt_to_equity': info.get('debtToEquity', 0),
#                 'revenue_growth': info.get('revenueGrowth', 0),
#                 'beta': info.get('beta', 1.0)
#             }
#         except Exception:
#             return {}

#     def get_sentiment_analysis(self, ticker: str) -> Dict:
#         """Basic sentiment analysis."""
#         if not ticker: return {'sentiment_score': 0}
#         try:
#             stock = yf.Ticker(ticker)
#             news = stock.news
#             if not news: return {'sentiment_score': 0}
            
#             sentiments = []
#             for article in news[:5]:
#                 text = f"{article.get('title', '')}. {article.get('summary', '')}"
#                 blob = TextBlob(text)
#                 sentiments.append(blob.sentiment.polarity)
            
#             return {
#                 'sentiment_score': np.mean(sentiments) if sentiments else 0,
#                 'sentiment_std': np.std(sentiments) if len(sentiments) > 1 else 0
#             }
#         except Exception:
#             return {'sentiment_score': 0}

#     def add_fundamental_features(self) -> pd.DataFrame:
#         if not self.ticker: return self.df
#         fundamentals = self.get_fundamental_data(self.ticker)
#         for key, value in fundamentals.items():
#             self.df[f'fund_{key}'] = value
#         return self.df

#     def add_sentiment_features(self) -> pd.DataFrame:
#         if not self.ticker: return self.df
#         sentiment = self.get_sentiment_analysis(self.ticker)
#         for key, value in sentiment.items():
#             self.df[f'sent_{key}'] = value
#         return self.df

#     def add_target_variables(self, forward_periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
#         """Create targets for ML models."""
#         for period in forward_periods:
#             self.df[f'target_close_{period}d'] = self.df['close'].shift(-period)
#             self.df[f'target_high_{period}d'] = self.df['high'].rolling(period).max().shift(-period)
#             self.df[f'target_low_{period}d'] = self.df['low'].rolling(period).min().shift(-period)
            
#             # Risk/Reward Targets
#             max_gain = (self.df[f'target_high_{period}d'] - self.df['close'])
#             max_loss = (self.df['close'] - self.df[f'target_low_{period}d'])
#             self.df[f'target_rr_ratio_{period}d'] = max_gain / (max_loss + 1e-10)
        
#         if 'atr_14' in self.df.columns:
#             self.df['suggested_stop_loss'] = self.df['close'] - (2 * self.df['atr_14'])
        
#         return self.df

#     def add_lag_features(self, lags: List[int] = [1, 2, 3, 5]) -> pd.DataFrame:
#         """Add lagged features."""
#         features_to_lag = ['close', 'volume', 'rsi_14', 'atr_14']
#         for feature in features_to_lag:
#             if feature in self.df.columns:
#                 for lag in lags:
#                     self.df[f'{feature}_lag_{lag}'] = self.df[feature].shift(lag)
#         return self.df

#     def handle_missing_values(self) -> pd.DataFrame:
#         """Fill NaNs and remove infinite values."""
#         self.df = self.df.replace([np.inf, -np.inf], np.nan)
#         self.df = self.df.ffill().bfill().fillna(0)
#         return self.df

#     def build_features(self, 
#                        include_fundamentals: bool = True,
#                        include_sentiment: bool = True,
#                        include_targets: bool = True) -> pd.DataFrame:
#         """
#         Master execution method.
#         Returns DataFrame with 'date' as a column (Index Reset).
#         """
#         self.add_technical_indicators()
#         self.add_price_patterns()
#         self.add_statistical_features()
#         self.add_market_microstructure()
#         self.add_lag_features()
        
#         if include_fundamentals and self.ticker:
#             self.add_fundamental_features()
        
#         if include_sentiment and self.ticker:
#             self.add_sentiment_features()
        
#         if include_targets:
#             self.add_target_variables()
        
#         self.handle_missing_values()
        
#         # Important: Reset index so 'date' is a column
#         self.df.reset_index(inplace=True)
        
#         # CRITICAL FIX: Remove duplicate columns
#         # Some indicators may produce duplicate column names (e.g. ISA_9)
#         # This deduplicates columns, keeping the first occurrence.
#         self.df = self.df.loc[:, ~self.df.columns.duplicated()]
        
#         return self.df


# class PipelineOrchestrator:
#     """Manages Database Connections and Batch Processing"""
    
#     def __init__(self, db_url: str):
#         self.engine = create_engine(db_url, pool_pre_ping=True)
#         self.table_name = 'engineered_features'

#     def get_all_tickers(self) -> List[str]:
#         """Fetch unique tickers from DB."""
#         try:
#             with self.engine.connect() as conn:
#                 result = conn.execute(text("SELECT DISTINCT ticker FROM nse_stocks ORDER BY ticker"))
#                 return [row[0] for row in result]
#         except Exception as e:
#             logger.error(f"Failed to fetch tickers: {e}")
#             return []

#     def get_stock_data(self, ticker: str) -> pd.DataFrame:
#         """Fetch data for ticker."""
#         query = text("""
#             SELECT date, open, high, low, close, volume, adj_close
#             FROM nse_stocks 
#             WHERE ticker = :ticker 
#             ORDER BY date ASC
#         """)
#         return pd.read_sql(query, self.engine, params={'ticker': ticker})

#     def sync_table_schema(self, df: pd.DataFrame, inspector):
#         """
#         Ensures DB table has all columns present in DataFrame.
#         Adds missing columns dynamically.
#         """
#         try:
#             # Get existing columns in DB
#             existing_columns = [col['name'] for col in inspector.get_columns(self.table_name)]
            
#             # Identify missing columns
#             df_columns = list(df.columns)
#             missing_cols = [col for col in df_columns if col not in existing_columns]
            
#             if missing_cols:
#                 logger.info(f"Syncing schema: Adding {len(missing_cols)} new columns to {self.table_name}")
#                 with self.engine.begin() as conn:
#                     for col in missing_cols:
#                         # Map pandas types to SQL types generically
#                         dtype = df[col].dtype
#                         if pd.api.types.is_integer_dtype(dtype):
#                             sql_type = "BIGINT"
#                         elif pd.api.types.is_float_dtype(dtype):
#                             sql_type = "DOUBLE PRECISION"
#                         elif pd.api.types.is_datetime64_any_dtype(dtype):
#                             sql_type = "TIMESTAMP"
#                         elif pd.api.types.is_bool_dtype(dtype):
#                             sql_type = "BOOLEAN"
#                         else:
#                             sql_type = "TEXT"
                            
#                         # Add column - Use quote identifier to handle special chars/case
#                         conn.execute(text(f'ALTER TABLE "{self.table_name}" ADD COLUMN "{col}" {sql_type}'))
#         except Exception as e:
#             logger.error(f"Schema sync failed: {e}")
#             raise

#     def save_features(self, df: pd.DataFrame):
#         """
#         Save features to DB with Schema Evolution and Safe Writes.
#         1. Deduplicates DataFrame columns.
#         2. Checks if table exists (Creates if not).
#         3. Syncs schema (Adds new columns if DF has them).
#         4. Deletes old records for the specific ticker (Deduplication).
#         5. Inserts new records.
#         """
#         if df.empty: return
        
#         # Double check deduplication before any DB op
#         df = df.loc[:, ~df.columns.duplicated()]
        
#         ticker = df['ticker'].iloc[0]
#         inspector = inspect(self.engine)
        
#         try:
#             # 1. Check Table Existence
#             if not inspector.has_table(self.table_name):
#                 logger.info(f"Table {self.table_name} does not exist. Creating...")
#                 # Use DataFrame to create initial table structure
#                 # We use duplicated check here too just in case
#                 df.head(0).to_sql(self.table_name, self.engine, if_exists='replace', index=False)
                
#                 # Add constraints/indexes immediately after creation
#                 with self.engine.begin() as conn:
#                     conn.execute(text(f"""
#                         ALTER TABLE "{self.table_name}" 
#                         ADD CONSTRAINT pk_engineered_features PRIMARY KEY (ticker, date);
#                     """))
#                     conn.execute(text(f"""
#                         CREATE INDEX IF NOT EXISTS idx_ef_ticker ON "{self.table_name}" (ticker);
#                     """))
#             else:
#                 # 2. Sync Schema (Add missing columns)
#                 self.sync_table_schema(df, inspector)

#             # 3. Deduplicate (Delete existing data for this ticker)
#             # Wrapped in try-except to handle race conditions or phantom tables
#             try:
#                 with self.engine.begin() as conn:
#                     conn.execute(
#                         text(f'DELETE FROM "{self.table_name}" WHERE ticker = :ticker'),
#                         {'ticker': ticker}
#                     )
#             except ProgrammingError:
#                 # If delete fails due to table missing (race condition), ignore and proceed to insert
#                 logger.warning(f"Delete failed for {ticker}, table might have been dropped. Proceeding to insert.")

#             # 4. Insert Data
#             df.to_sql(
#                 self.table_name, 
#                 self.engine, 
#                 if_exists='append', 
#                 index=False, 
#                 method='multi', 
#                 chunksize=500
#             )
            
#         except Exception as e:
#             logger.error(f"Failed to save features for {ticker}: {e}")
#             raise e

#     def run_pipeline(self):
#         """Run pipeline for all stocks."""
#         tickers = self.get_all_tickers()
        
#         if not tickers:
#             logger.error("No tickers found in database.")
#             return

#         logger.info(f"[START] Feature Engineering Pipeline for {len(tickers)} stocks")
        
#         success_count = 0
#         error_count = 0
        
#         pbar = tqdm(tickers, desc="Processing")
        
#         for ticker in pbar:
#             try:
#                 # 1. Fetch Data
#                 df_raw = self.get_stock_data(ticker)
                
#                 if df_raw.empty or len(df_raw) < 50:
#                     continue
                
#                 # 2. Process
#                 engineer = StockFeatureEngineer(df_raw, ticker=ticker)
                
#                 # Skipping external API calls for bulk speed
#                 df_features = engineer.build_features(
#                     include_fundamentals=False,
#                     include_sentiment=False,
#                     include_targets=True
#                 )
                
#                 # 3. Add Ticker Column
#                 if 'ticker' not in df_features.columns:
#                     df_features['ticker'] = ticker
                
#                 # CRITICAL CHANGE: Keep only the latest row (Snapshot Logic)
#                 # Since we calculated features using history, taking the last row gives
#                 # us the "Latest Date" features.
#                 df_features = df_features.iloc[[-1]]
                
#                 # 4. Save
#                 self.save_features(df_features)
#                 success_count += 1
                
#             except Exception as e:
#                 # Log to file, keep console clean
#                 logger.debug(f"Error processing {ticker}: {e}")
#                 error_count += 1
        
#         logger.info(f"[DONE] Success: {success_count}, Errors: {error_count}")


# if __name__ == "__main__":
#     try:
#         pipeline = PipelineOrchestrator(DB_URL)
#         pipeline.run_pipeline()
#     except Exception as e:
#         logger.critical(f"Critical Failure: {e}")





# import pandas as pd
# import pandas_ta as ta
# import yfinance as yf
# from textblob import TextBlob
# import numpy as np
# from typing import Dict, List, Tuple, Optional
# import logging
# from datetime import datetime, timedelta
# import warnings
# from functools import lru_cache
# from sklearn.preprocessing import RobustScaler
# from sqlalchemy import create_engine, text, inspect
# from sqlalchemy.exc import ProgrammingError
# from tqdm import tqdm

# # Filter warnings
# warnings.filterwarnings('ignore')

# # Configure logging (ASCII only for Windows compatibility)
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('feature_engineering.log'),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

# # --- CONFIGURATION ---
# DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"

# class StockFeatureEngineer:
#     """
#     Production-grade feature engineering pipeline for stock price prediction.
#     """
    
#     def __init__(self, df: pd.DataFrame, ticker: str = None):
#         """
#         Initialize with OHLCV data.
#         Sets DatetimeIndex for pandas_ta compatibility.
#         """
#         # Lowercase columns for consistency
#         df.columns = [c.lower() for c in df.columns]
        
#         required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
#         missing_cols = [col for col in required_cols if col not in df.columns]
#         if missing_cols:
#             raise ValueError(f"Missing required columns: {missing_cols}")
        
#         self.df = df.copy()
#         self.ticker = ticker
        
#         # 1. Convert date to datetime
#         self.df['date'] = pd.to_datetime(self.df['date'])
        
#         # 2. Set Date as Index (Required for VWAP and Time-Series functions)
#         self.df.set_index('date', inplace=True)
#         self.df.sort_index(inplace=True)
        
#         # 3. Handle Duplicate Indices
#         if not self.df.index.is_unique:
#             self.df = self.df.loc[~self.df.index.duplicated(keep='first')]

#         # Use adj_close if available, otherwise close
#         if 'adj_close' in self.df.columns:
#             self.df['price'] = self.df['adj_close']
#         else:
#             self.df['price'] = self.df['close']
        
#         # Store original columns
#         self.original_cols = self.df.columns.tolist()

#     def add_technical_indicators(self) -> pd.DataFrame:
#         """Comprehensive technical indicators suite."""
#         # 1. Moving Averages
#         for period in [5, 10, 20, 50, 100, 200]:
#             self.df[f'sma_{period}'] = self.df.ta.sma(length=period)
#             self.df[f'ema_{period}'] = self.df.ta.ema(length=period)
        
#         # 2. MACD
#         try:
#             macd = self.df.ta.macd(fast=12, slow=26, signal=9)
#             if macd is not None:
#                 self.df = pd.concat([self.df, macd], axis=1)
#         except Exception: pass
        
#         # 3. ADX
#         try:
#             adx = self.df.ta.adx(length=14)
#             if adx is not None:
#                 self.df = pd.concat([self.df, adx], axis=1)
#         except Exception: pass
        
#         # 4. Ichimoku Cloud
#         try:
#             ichimoku = self.df.ta.ichimoku()
#             if ichimoku is not None and len(ichimoku) > 0:
#                 self.df = pd.concat([self.df, ichimoku[0]], axis=1)
#         except Exception: pass
        
#         # 5. Parabolic SAR
#         try:
#             psar = self.df.ta.psar()
#             if psar is not None:
#                 self.df = pd.concat([self.df, psar], axis=1)
#         except Exception: pass
        
#         # 6. RSI
#         for period in [9, 14, 21]:
#             self.df[f'rsi_{period}'] = self.df.ta.rsi(length=period)
        
#         # 7. Stochastic
#         try:
#             stoch = self.df.ta.stoch(k=14, d=3)
#             if stoch is not None:
#                 self.df = pd.concat([self.df, stoch], axis=1)
#         except Exception: pass
        
#         # 8. Williams %R
#         self.df['willr'] = self.df.ta.willr(length=14)
        
#         # 9. ROC
#         for period in [9, 14, 21]:
#             self.df[f'roc_{period}'] = self.df.ta.roc(length=period)
        
#         # 10. CCI
#         self.df['cci'] = self.df.ta.cci(length=20)
        
#         # 11. MFI
#         self.df['mfi'] = self.df.ta.mfi(length=14)
        
#         # 12. Bollinger Bands
#         try:
#             bbands = self.df.ta.bbands(length=20, std=2)
#             if bbands is not None:
#                 self.df = pd.concat([self.df, bbands], axis=1)
#                 if 'BBU_20_2.0' in self.df.columns and 'BBL_20_2.0' in self.df.columns:
#                     self.df['bb_width'] = (self.df['BBU_20_2.0'] - self.df['BBL_20_2.0']) / (self.df['BBM_20_2.0'] + 1e-10)
#         except Exception: pass
        
#         # 13. ATR
#         for period in [7, 14, 21]:
#             self.df[f'atr_{period}'] = self.df.ta.atr(length=period)
        
#         # 14. Keltner Channels
#         try:
#             kc = self.df.ta.kc(length=20)
#             if kc is not None:
#                 self.df = pd.concat([self.df, kc], axis=1)
#         except Exception: pass
        
#         # 15. Historical Volatility
#         self.df['hist_vol_20'] = self.df['close'].pct_change().rolling(20).std() * np.sqrt(252)
        
#         # 16. Volume SMA
#         self.df['volume_sma_20'] = self.df['volume'].rolling(20).mean()
#         self.df['volume_ratio'] = self.df['volume'] / (self.df['volume_sma_20'] + 1e-10)
        
#         # 17. OBV
#         self.df['obv'] = self.df.ta.obv()
        
#         # 18. VWAP
#         try:
#             if not isinstance(self.df.index, pd.DatetimeIndex):
#                 self.df.index = pd.to_datetime(self.df.index)
            
#             vwap = self.df.ta.vwap()
#             if isinstance(vwap, pd.Series):
#                 self.df['vwap'] = vwap
#             elif isinstance(vwap, pd.DataFrame):
#                 self.df['vwap'] = vwap.iloc[:, 0]
#         except Exception:
#             tp = (self.df['high'] + self.df['low'] + self.df['close']) / 3
#             self.df['vwap'] = (tp * self.df['volume']).cumsum() / (self.df['volume'].cumsum() + 1e-10)
        
#         # 19. Accumulation/Distribution
#         self.df['ad'] = self.df.ta.ad()
        
#         # 20. Chaikin Money Flow
#         self.df['cmf'] = self.df.ta.cmf(length=20)
        
#         # 21. SuperTrend
#         for mult in [2, 3]:
#             try:
#                 st = self.df.ta.supertrend(length=10, multiplier=mult)
#                 if st is not None:
#                     self.df = pd.concat([self.df, st.add_suffix(f'_{mult}')], axis=1)
#             except Exception: pass
        
#         return self.df

#     def add_price_patterns(self) -> pd.DataFrame:
#         """
#         Advanced candlestick pattern detection.
#         Uses pure pandas logic where TA-Lib is not available.
#         """
#         # Patterns supported by pandas-ta without TA-Lib
#         # 'doji' and 'inside' are usually available natively.
#         try:
#             self.df['cdl_doji'] = self.df.ta.cdl_doji(append=False) / 100.0
#         except Exception: pass

#         # --- Manual Python Fallbacks for patterns missing in pandas-ta default ---
#         # These will run if TA-Lib is absent to avoid "[X] pattern not found" errors
        
#         O, H, L, C = self.df['open'], self.df['high'], self.df['low'], self.df['close']
        
#         # Hammer (approximate logic)
#         # Small body near top, long lower wick
#         body = abs(C - O)
#         lower_wick = np.minimum(C, O) - L
#         upper_wick = H - np.maximum(C, O)
#         self.df['cdl_hammer'] = np.where(
#             (lower_wick > 2 * body) & (upper_wick < 0.2 * body), 1.0, 0.0
#         )

#         # Inverted Hammer
#         # Small body near bottom, long upper wick
#         self.df['cdl_inverted_hammer'] = np.where(
#             (upper_wick > 2 * body) & (lower_wick < 0.2 * body), 1.0, 0.0
#         )

#         # Shooting Star
#         # Same shape as Inverted Hammer but in an uptrend (simplified here to shape)
#         self.df['cdl_shooting_star'] = self.df['cdl_inverted_hammer'] # Logic context depends on trend usually

#         # Hanging Man
#         # Same shape as Hammer but in an uptrend
#         self.df['cdl_hanging_man'] = self.df['cdl_hammer'] 

#         # Marubozu (Long body, very small wicks)
#         avg_body = body.rolling(20).mean()
#         self.df['cdl_marubozu'] = np.where(
#             (body > 2 * avg_body) & (lower_wick < 0.05 * body) & (upper_wick < 0.05 * body), 
#             np.sign(C - O), 0.0
#         )

#         # Price Action Features
#         self.df['body_size'] = abs(self.df['close'] - self.df['open']) / (self.df['close'] + 1e-10)
#         self.df['swing_high'] = self.df['high'].rolling(window=10, center=True).max()
#         self.df['swing_low'] = self.df['low'].rolling(window=10, center=True).min()
#         self.df['gap_up'] = ((self.df['open'] - self.df['close'].shift(1)) / (self.df['close'].shift(1) + 1e-10)) > 0.02
        
#         return self.df

#     def add_statistical_features(self) -> pd.DataFrame:
#         """Statistical features."""
#         for period in [1, 3, 5, 10, 20]:
#             self.df[f'return_{period}d'] = self.df['close'].pct_change(period)
#             self.df[f'log_return_{period}d'] = np.log(self.df['close'] / (self.df['close'].shift(period) + 1e-10))
        
#         for window in [5, 10, 20]:
#             self.df[f'return_mean_{window}'] = self.df['return_1d'].rolling(window).mean()
#             self.df[f'return_std_{window}'] = self.df['return_1d'].rolling(window).std()
        
#         for period in [20, 50]:
#             mean = self.df['close'].rolling(period).mean()
#             std = self.df['close'].rolling(period).std()
#             self.df[f'zscore_{period}'] = (self.df['close'] - mean) / (std + 1e-10)
        
#         self.df['momentum_10'] = self.df['close'] - self.df['close'].shift(10)
#         return self.df

#     def add_market_microstructure(self) -> pd.DataFrame:
#         """Liquidity features."""
#         self.df['hl_spread'] = (self.df['high'] - self.df['low']) / (self.df['close'] + 1e-10)
#         self.df['amihud_ratio'] = abs(self.df['return_1d']) / (self.df['volume'] * self.df['close'] + 1e-10)
        
#         if 'vwap' in self.df.columns:
#             self.df['vwap_deviation'] = (self.df['close'] - self.df['vwap']) / (self.df['vwap'] + 1e-10)
        
#         return self.df

#     @lru_cache(maxsize=128)
#     def get_fundamental_data(self, ticker: str) -> Dict:
#         """Fetch fundamental data with caching."""
#         if not ticker: return {}
#         try:
#             stock = yf.Ticker(ticker)
#             info = stock.info
#             return {
#                 'market_cap': info.get('marketCap', 0),
#                 'pe_ratio': info.get('trailingPE', 0),
#                 'forward_pe': info.get('forwardPE', 0),
#                 'pb_ratio': info.get('priceToBook', 0),
#                 'profit_margins': info.get('profitMargins', 0),
#                 'roe': info.get('returnOnEquity', 0),
#                 'debt_to_equity': info.get('debtToEquity', 0),
#                 'revenue_growth': info.get('revenueGrowth', 0),
#                 'beta': info.get('beta', 1.0)
#             }
#         except Exception:
#             return {}

#     def get_sentiment_analysis(self, ticker: str) -> Dict:
#         """Basic sentiment analysis."""
#         if not ticker: return {'sentiment_score': 0}
#         try:
#             stock = yf.Ticker(ticker)
#             news = stock.news
#             if not news: return {'sentiment_score': 0}
            
#             sentiments = []
#             for article in news[:5]:
#                 text = f"{article.get('title', '')}. {article.get('summary', '')}"
#                 blob = TextBlob(text)
#                 sentiments.append(blob.sentiment.polarity)
            
#             return {
#                 'sentiment_score': np.mean(sentiments) if sentiments else 0,
#                 'sentiment_std': np.std(sentiments) if len(sentiments) > 1 else 0
#             }
#         except Exception:
#             return {'sentiment_score': 0}

#     def add_fundamental_features(self) -> pd.DataFrame:
#         if not self.ticker: return self.df
#         fundamentals = self.get_fundamental_data(self.ticker)
#         for key, value in fundamentals.items():
#             self.df[f'fund_{key}'] = value
#         return self.df

#     def add_sentiment_features(self) -> pd.DataFrame:
#         if not self.ticker: return self.df
#         sentiment = self.get_sentiment_analysis(self.ticker)
#         for key, value in sentiment.items():
#             self.df[f'sent_{key}'] = value
#         return self.df

#     def add_target_variables(self, forward_periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
#         """Create targets for ML models."""
#         for period in forward_periods:
#             self.df[f'target_close_{period}d'] = self.df['close'].shift(-period)
#             self.df[f'target_high_{period}d'] = self.df['high'].rolling(period).max().shift(-period)
#             self.df[f'target_low_{period}d'] = self.df['low'].rolling(period).min().shift(-period)
            
#             # Risk/Reward Targets
#             max_gain = (self.df[f'target_high_{period}d'] - self.df['close'])
#             max_loss = (self.df['close'] - self.df[f'target_low_{period}d'])
#             self.df[f'target_rr_ratio_{period}d'] = max_gain / (max_loss + 1e-10)
        
#         if 'atr_14' in self.df.columns:
#             self.df['suggested_stop_loss'] = self.df['close'] - (2 * self.df['atr_14'])
        
#         return self.df

#     def add_lag_features(self, lags: List[int] = [1, 2, 3, 5]) -> pd.DataFrame:
#         """Add lagged features."""
#         features_to_lag = ['close', 'volume', 'rsi_14', 'atr_14']
#         for feature in features_to_lag:
#             if feature in self.df.columns:
#                 for lag in lags:
#                     self.df[f'{feature}_lag_{lag}'] = self.df[feature].shift(lag)
#         return self.df

#     def handle_missing_values(self) -> pd.DataFrame:
#         """Fill NaNs and remove infinite values."""
#         self.df = self.df.replace([np.inf, -np.inf], np.nan)
#         self.df = self.df.ffill().bfill().fillna(0)
#         return self.df

#     def build_features(self, 
#                        include_fundamentals: bool = True,
#                        include_sentiment: bool = True,
#                        include_targets: bool = True) -> pd.DataFrame:
#         """
#         Master execution method.
#         Returns DataFrame with 'date' as a column (Index Reset).
#         """
#         self.add_technical_indicators()
#         self.add_price_patterns()
#         self.add_statistical_features()
#         self.add_market_microstructure()
#         self.add_lag_features()
        
#         if include_fundamentals and self.ticker:
#             self.add_fundamental_features()
        
#         if include_sentiment and self.ticker:
#             self.add_sentiment_features()
        
#         if include_targets:
#             self.add_target_variables()
        
#         self.handle_missing_values()
        
#         # Important: Reset index so 'date' is a column
#         self.df.reset_index(inplace=True)
        
#         # CRITICAL FIX: Remove duplicate columns
#         # Some indicators may produce duplicate column names (e.g. ISA_9)
#         # This deduplicates columns, keeping the first occurrence.
#         self.df = self.df.loc[:, ~self.df.columns.duplicated()]
        
#         return self.df


# class PipelineOrchestrator:
#     """Manages Database Connections and Batch Processing"""
    
#     def __init__(self, db_url: str):
#         self.engine = create_engine(db_url, pool_pre_ping=True)
#         self.table_name = 'engineered_features'

#     def get_all_tickers(self) -> List[str]:
#         """Fetch unique tickers from DB."""
#         try:
#             with self.engine.connect() as conn:
#                 result = conn.execute(text("SELECT DISTINCT ticker FROM nse_stocks ORDER BY ticker"))
#                 return [row[0] for row in result]
#         except Exception as e:
#             logger.error(f"Failed to fetch tickers: {e}")
#             return []

#     def get_stock_data(self, ticker: str) -> pd.DataFrame:
#         """Fetch data for ticker."""
#         query = text("""
#             SELECT date, open, high, low, close, volume, adj_close
#             FROM nse_stocks 
#             WHERE ticker = :ticker 
#             ORDER BY date ASC
#         """)
#         return pd.read_sql(query, self.engine, params={'ticker': ticker})

#     def sync_table_schema(self, df: pd.DataFrame, inspector):
#         """
#         Ensures DB table has all columns present in DataFrame.
#         Adds missing columns dynamically.
#         """
#         try:
#             # Get existing columns in DB
#             existing_columns = [col['name'] for col in inspector.get_columns(self.table_name)]
            
#             # Identify missing columns
#             df_columns = list(df.columns)
#             missing_cols = [col for col in df_columns if col not in existing_columns]
            
#             if missing_cols:
#                 logger.info(f"Syncing schema: Adding {len(missing_cols)} new columns to {self.table_name}")
#                 with self.engine.begin() as conn:
#                     for col in missing_cols:
#                         # Map pandas types to SQL types generically
#                         dtype = df[col].dtype
#                         if pd.api.types.is_integer_dtype(dtype):
#                             sql_type = "BIGINT"
#                         elif pd.api.types.is_float_dtype(dtype):
#                             sql_type = "DOUBLE PRECISION"
#                         elif pd.api.types.is_datetime64_any_dtype(dtype):
#                             sql_type = "TIMESTAMP"
#                         elif pd.api.types.is_bool_dtype(dtype):
#                             sql_type = "BOOLEAN"
#                         else:
#                             sql_type = "TEXT"
                            
#                         # Add column - Use quote identifier to handle special chars/case
#                         conn.execute(text(f'ALTER TABLE "{self.table_name}" ADD COLUMN "{col}" {sql_type}'))
#         except Exception as e:
#             logger.error(f"Schema sync failed: {e}")
#             raise

#     def save_features(self, df: pd.DataFrame):
#         """
#         Save features to DB with Schema Evolution and Safe Writes.
#         1. Deduplicates DataFrame columns.
#         2. Checks if table exists (Creates if not).
#         3. Syncs schema (Adds new columns if DF has them).
#         4. Deletes old records for the specific ticker (Deduplication).
#         5. Inserts new records.
#         """
#         if df.empty: return
        
#         # Double check deduplication before any DB op
#         df = df.loc[:, ~df.columns.duplicated()]
        
#         ticker = df['ticker'].iloc[0]
#         inspector = inspect(self.engine)
        
#         try:
#             # 1. Check Table Existence
#             if not inspector.has_table(self.table_name):
#                 logger.info(f"Table {self.table_name} does not exist. Creating...")
#                 # Use DataFrame to create initial table structure
#                 # We use duplicated check here too just in case
#                 df.head(0).to_sql(self.table_name, self.engine, if_exists='replace', index=False)
                
#                 # Add constraints/indexes immediately after creation
#                 with self.engine.begin() as conn:
#                     conn.execute(text(f"""
#                         ALTER TABLE "{self.table_name}" 
#                         ADD CONSTRAINT pk_engineered_features PRIMARY KEY (ticker, date);
#                     """))
#                     conn.execute(text(f"""
#                         CREATE INDEX IF NOT EXISTS idx_ef_ticker ON "{self.table_name}" (ticker);
#                     """))
#             else:
#                 # 2. Sync Schema (Add missing columns)
#                 self.sync_table_schema(df, inspector)

#             # 3. Deduplicate (Delete existing data for this ticker)
#             # Wrapped in try-except to handle race conditions or phantom tables
#             try:
#                 with self.engine.begin() as conn:
#                     conn.execute(
#                         text(f'DELETE FROM "{self.table_name}" WHERE ticker = :ticker'),
#                         {'ticker': ticker}
#                     )
#             except ProgrammingError:
#                 # If delete fails due to table missing (race condition), ignore and proceed to insert
#                 logger.warning(f"Delete failed for {ticker}, table might have been dropped. Proceeding to insert.")

#             # 4. Insert Data
#             df.to_sql(
#                 self.table_name, 
#                 self.engine, 
#                 if_exists='append', 
#                 index=False, 
#                 method='multi', 
#                 chunksize=500
#             )
            
#         except Exception as e:
#             logger.error(f"Failed to save features for {ticker}: {e}")
#             raise e

#     def run_pipeline(self):
#         """Run pipeline for all stocks."""
#         tickers = self.get_all_tickers()
        
#         if not tickers:
#             logger.error("No tickers found in database.")
#             return

#         logger.info(f"[START] Feature Engineering Pipeline for {len(tickers)} stocks")
        
#         success_count = 0
#         error_count = 0
        
#         pbar = tqdm(tickers, desc="Processing")
        
#         for ticker in pbar:
#             try:
#                 # 1. Fetch Data
#                 df_raw = self.get_stock_data(ticker)
                
#                 if df_raw.empty or len(df_raw) < 50:
#                     continue
                
#                 # 2. Process
#                 engineer = StockFeatureEngineer(df_raw, ticker=ticker)
                
#                 # Skipping external API calls for bulk speed
#                 df_features = engineer.build_features(
#                     include_fundamentals=False,
#                     include_sentiment=False,
#                     include_targets=True
#                 )
                
#                 # 3. Add Ticker Column
#                 if 'ticker' not in df_features.columns:
#                     df_features['ticker'] = ticker
                
#                 # CRITICAL CHANGE: Keep only the latest row (Snapshot Logic)
#                 # Since we calculated features using history, taking the last row gives
#                 # us the "Latest Date" features.
#                 df_features = df_features.iloc[[-1]]
                
#                 # 4. Save
#                 self.save_features(df_features)
#                 success_count += 1
                
#             except Exception as e:
#                 # Log to file, keep console clean
#                 logger.debug(f"Error processing {ticker}: {e}")
#                 error_count += 1
        
#         logger.info(f"[DONE] Success: {success_count}, Errors: {error_count}")


# if __name__ == "__main__":
#     try:
#         pipeline = PipelineOrchestrator(DB_URL)
#         pipeline.run_pipeline()
#     except Exception as e:
#         logger.critical(f"Critical Failure: {e}")





# import pandas as pd
# import pandas_ta as ta
# import yfinance as yf
# from textblob import TextBlob
# import numpy as np
# from typing import Dict, List, Optional, Set
# import logging
# import warnings
# from functools import lru_cache
# from sqlalchemy import create_engine, text, inspect
# from sqlalchemy.dialects.postgresql import insert
# from tqdm import tqdm
# import concurrent.futures
# import multiprocessing

# # --- CONFIGURATION ---
# DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"

# # --- SETUP ---
# warnings.filterwarnings('ignore')

# # Configure logging
# # Note: In multiprocessing, logging to a single file can be tricky. 
# # We rely on the main process to handle the primary logs or file locking.
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('feature_engineering.log'),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

# class StockFeatureEngineer:
#     """
#     Production-grade feature engineering pipeline.
#     Calculates Technical, Statistical, and Fundamental features.
#     """
    
#     def __init__(self, df: pd.DataFrame, ticker: str = None):
#         # 1. Column Standardization
#         df.columns = [c.lower() for c in df.columns]
        
#         required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
#         missing_cols = [col for col in required_cols if col not in df.columns]
#         if missing_cols:
#             raise ValueError(f"Missing required columns: {missing_cols}")
        
#         self.df = df.copy()
#         self.ticker = ticker
        
#         # 2. Date Handling
#         self.df['date'] = pd.to_datetime(self.df['date'])
#         self.df.set_index('date', inplace=True)
#         self.df.sort_index(inplace=True)
        
#         # 3. Handle Duplicate Indices
#         if not self.df.index.is_unique:
#             self.df = self.df.loc[~self.df.index.duplicated(keep='first')]

#         # 4. Set 'price' column
#         self.df['price'] = self.df.get('adj_close', self.df['close'])
        
#         self.target_cols = []

#     def add_technical_indicators(self) -> pd.DataFrame:
#         try:
#             # Moving Averages
#             for period in [5, 10, 20, 50, 100, 200]:
#                 self.df[f'sma_{period}'] = self.df.ta.sma(length=period)
#                 self.df[f'ema_{period}'] = self.df.ta.ema(length=period)
            
#             # MACD
#             macd = self.df.ta.macd(fast=12, slow=26, signal=9)
#             if macd is not None: self.df = pd.concat([self.df, macd], axis=1)
            
#             # ADX
#             adx = self.df.ta.adx(length=14)
#             if adx is not None: self.df = pd.concat([self.df, adx], axis=1)
            
#             # RSI
#             self.df['rsi_14'] = self.df.ta.rsi(length=14)
            
#             # Bollinger Bands
#             bbands = self.df.ta.bbands(length=20, std=2)
#             if bbands is not None: 
#                 self.df = pd.concat([self.df, bbands], axis=1)
#                 if 'BBU_20_2.0' in self.df.columns and 'BBL_20_2.0' in self.df.columns:
#                     self.df['bb_width'] = (self.df['BBU_20_2.0'] - self.df['BBL_20_2.0']) / (self.df['BBM_20_2.0'] + 1e-10)

#             # ATR
#             self.df['atr_14'] = self.df.ta.atr(length=14)

#             # Volume Indicators
#             self.df['obv'] = self.df.ta.obv()
#             self.df['vwap'] = self.df.ta.vwap()
            
#         except Exception as e:
#             # Silent fail for indicators to keep logs clean in parallel mode
#             pass
        
#         return self.df

#     def add_advanced_oscillators(self) -> pd.DataFrame:
#         try:
#             # Aroon
#             aroon = self.df.ta.aroon(length=25)
#             if aroon is not None:
#                 self.df = pd.concat([self.df, aroon], axis=1)
#                 if 'AROONU_25' in self.df.columns and 'AROOND_25' in self.df.columns:
#                     self.df['aroon_osc'] = self.df['AROONU_25'] - self.df['AROOND_25']

#             # Stochastic
#             stoch = self.df.ta.stoch(k=14, d=3, smooth_k=3)
#             if stoch is not None:
#                 self.df = pd.concat([self.df, stoch], axis=1)

#             # CCI
#             self.df['cci_20'] = self.df.ta.cci(length=20)
            
#             # ROC
#             self.df['roc_10'] = self.df.ta.roc(length=10)

#         except Exception:
#             pass
            
#         return self.df

#     def add_price_patterns(self) -> pd.DataFrame:
#         try:
#             self.df['cdl_doji'] = self.df.ta.cdl_doji(append=False) / 100.0
#         except Exception: pass

#         O, H, L, C = self.df['open'], self.df['high'], self.df['low'], self.df['close']
#         body = abs(C - O)
        
#         self.df['gap_up'] = ((O - C.shift(1)) / (C.shift(1) + 1e-10)) > 0.005
#         self.df['gap_down'] = ((O - C.shift(1)) / (C.shift(1) + 1e-10)) < -0.005
        
#         self.df['body_size'] = body / (C + 1e-10)
#         self.df['upper_wick'] = H - np.maximum(O, C)
#         self.df['lower_wick'] = np.minimum(O, C) - L
        
#         return self.df

#     def add_statistical_features(self) -> pd.DataFrame:
#         for period in [1, 3, 5, 10, 20]:
#             self.df[f'return_{period}d'] = self.df['close'].pct_change(period)
#             self.df[f'log_return_{period}d'] = np.log(self.df['close'] / (self.df['close'].shift(period) + 1e-10))
        
#         self.df['hist_vol_20'] = self.df['close'].pct_change().rolling(20).std() * np.sqrt(252)
        
#         for period in [20, 50]:
#             mean = self.df['close'].rolling(period).mean()
#             std = self.df['close'].rolling(period).std()
#             self.df[f'zscore_{period}'] = (self.df['close'] - mean) / (std + 1e-10)
            
#         return self.df

#     @lru_cache(maxsize=128)
#     def get_fundamental_data(self, ticker: str) -> Dict:
#         if not ticker: return {}
#         try:
#             # FIX: Append .NS for NSE stocks
#             search_ticker = ticker
#             if not search_ticker.endswith('.NS') and not search_ticker.endswith('.BO'):
#                 search_ticker = f"{ticker}.NS"

#             stock = yf.Ticker(search_ticker)
#             info = stock.info
            
#             keys = ['marketCap', 'trailingPE', 'forwardPE', 'priceToBook', 'beta', 'returnOnEquity']
#             return {f"fund_{k}": info.get(k, 0) for k in keys}
#         except Exception:
#             return {}

#     def add_target_variables(self, forward_periods: List[int] = [1, 5]) -> pd.DataFrame:
#         for period in forward_periods:
#             col_name = f'target_return_{period}d'
#             self.df[col_name] = self.df['close'].shift(-period) / self.df['close'] - 1
#             self.target_cols.append(col_name)

#             col_class = f'target_is_up_{period}d'
#             self.df[col_class] = (self.df[col_name] > 0).astype(float)
#             self.df.loc[self.df.index[-period:], col_class] = np.nan
#             self.target_cols.append(col_class)

#         return self.df

#     def handle_missing_values(self) -> pd.DataFrame:
#         self.df = self.df.replace([np.inf, -np.inf], np.nan)
#         feature_cols = [c for c in self.df.columns if c not in self.target_cols]
#         self.df[feature_cols] = self.df[feature_cols].ffill().fillna(0)
#         return self.df

#     def build_features(self, include_fundamentals: bool = True) -> pd.DataFrame:
#         self.add_technical_indicators()
#         self.add_advanced_oscillators()
#         self.add_price_patterns()
#         self.add_statistical_features()
        
#         if include_fundamentals and self.ticker:
#             fundamentals = self.get_fundamental_data(self.ticker)
#             for k, v in fundamentals.items():
#                 self.df[k] = v
        
#         self.add_target_variables()
#         self.handle_missing_values()
        
#         self.df.reset_index(inplace=True)
#         self.df = self.df.loc[:, ~self.df.columns.duplicated()]
        
#         return self.df


# class PipelineOrchestrator:
#     """Manages Database Connections and Pipeline Execution."""
    
#     def __init__(self, db_url: str):
#         self.engine = create_engine(db_url, pool_pre_ping=True)
#         self.table_name = 'engineered_features'
#         self.known_columns: Set[str] = set()
#         self._initialize_schema_knowledge()

#     def _initialize_schema_knowledge(self):
#         inspector = inspect(self.engine)
#         if inspector.has_table(self.table_name):
#             self.known_columns = {col['name'] for col in inspector.get_columns(self.table_name)}
#         else:
#             self.known_columns = set()

#     def ensure_table_structure(self, df_sample: pd.DataFrame):
#         """Creates table structure based on a sample dataframe to prevent race conditions."""
#         if df_sample.empty: return
#         self.sync_table_schema(df_sample)

#     def get_all_tickers(self) -> List[str]:
#         try:
#             with self.engine.connect() as conn:
#                 result = conn.execute(text("SELECT DISTINCT ticker FROM nse_stocks ORDER BY ticker"))
#                 return [row[0] for row in result]
#         except Exception as e:
#             logger.error(f"Failed to fetch tickers: {e}")
#             return []

#     def get_stock_data(self, ticker: str) -> pd.DataFrame:
#         query = text("""
#             SELECT date, open, high, low, close, volume, adj_close
#             FROM nse_stocks 
#             WHERE ticker = :ticker 
#             ORDER BY date ASC
#         """)
#         return pd.read_sql(query, self.engine, params={'ticker': ticker})

#     def get_latest_db_date(self, ticker: str) -> Optional[pd.Timestamp]:
#         try:
#             if not self.known_columns: 
#                 return None
#             with self.engine.connect() as conn:
#                 query = text(f'SELECT MAX(date) FROM "{self.table_name}" WHERE ticker = :ticker')
#                 result = conn.execute(query, {'ticker': ticker}).fetchone()
#                 if result and result[0]:
#                     return pd.to_datetime(result[0])
#             return None
#         except Exception:
#             return None

#     def sync_table_schema(self, df: pd.DataFrame):
#         if df.empty: return
#         current_cols = set(df.columns)
#         new_cols = current_cols - self.known_columns
        
#         if not new_cols: return

#         if not self.known_columns:
#             # logger.info(f"Creating table {self.table_name}")
#             df.head(0).to_sql(self.table_name, self.engine, if_exists='replace', index=False)
#             with self.engine.begin() as conn:
#                 conn.execute(text(f"""
#                     ALTER TABLE "{self.table_name}" 
#                     ADD CONSTRAINT pk_engineered_features PRIMARY KEY (ticker, date);
#                 """))
#             self.known_columns = current_cols
#             return

#         with self.engine.begin() as conn:
#             for col in new_cols:
#                 # logger.info(f"Adding new column: {col}")
#                 dtype = df[col].dtype
#                 sql_type = "TEXT"
#                 if pd.api.types.is_integer_dtype(dtype): sql_type = "BIGINT"
#                 elif pd.api.types.is_float_dtype(dtype): sql_type = "DOUBLE PRECISION"
#                 elif pd.api.types.is_datetime64_any_dtype(dtype): sql_type = "TIMESTAMP"
#                 elif pd.api.types.is_bool_dtype(dtype): sql_type = "BOOLEAN"
                
#                 try:
#                     conn.execute(text(f'ALTER TABLE "{self.table_name}" ADD COLUMN "{col}" {sql_type}'))
#                 except Exception:
#                     # Ignore error if column was added by another process
#                     pass
        
#         self.known_columns.update(new_cols)

#     def save_features_incremental(self, df: pd.DataFrame):
#         if df.empty: return
#         ticker = df['ticker'].iloc[0]
#         latest_date = self.get_latest_db_date(ticker)
#         self.sync_table_schema(df)
        
#         if latest_date:
#             df_new = df[df['date'] > latest_date]
#             if not df_new.empty:
#                 try:
#                     df_new.to_sql(self.table_name, self.engine, if_exists='append', index=False, method='multi', chunksize=1000)
#                 except Exception:
#                     pass
#         else:
#             self.save_features_upsert(df)

#     def save_features_upsert(self, df: pd.DataFrame):
#         if df.empty: return
#         self.sync_table_schema(df)
#         try:
#             with self.engine.begin() as conn:
#                 conn.execute(text(f'DELETE FROM "{self.table_name}" WHERE ticker = :ticker'), {'ticker': df['ticker'].iloc[0]})
#                 df.to_sql(self.table_name, conn, if_exists='append', index=False, method='multi', chunksize=1000)
#         except Exception as e:
#             logger.error(f"Save failed for {df['ticker'].iloc[0]}: {e}")

# # --- GLOBAL WORKER FUNCTION FOR MULTIPROCESSING ---
# def process_ticker_safe(ticker: str, db_url: str, incremental: bool):
#     """
#     Isolated worker function to process a single ticker.
#     Has its own database connection to avoid conflict.
#     """
#     try:
#         # 1. Setup isolated orchestrator
#         local_orch = PipelineOrchestrator(db_url)
        
#         # 2. Fetch Data
#         df_raw = local_orch.get_stock_data(ticker)
#         if len(df_raw) < 200:
#             return False
            
#         # 3. Engineer Features
#         engineer = StockFeatureEngineer(df_raw, ticker=ticker)
#         # Setting include_fundamentals=True calls Yahoo API. 
#         # CAUTION: Yahoo might rate limit if max_workers is too high (>10).
#         df_features = engineer.build_features(include_fundamentals=True)
        
#         if 'ticker' not in df_features.columns:
#             df_features['ticker'] = ticker
            
#         # 4. Save
#         if incremental:
#             local_orch.save_features_incremental(df_features)
#         else:
#             local_orch.save_features_upsert(df_features)
            
#         return True
#     except Exception as e:
#         # logger.error(f"Worker failed on {ticker}: {e}")
#         return False

# def run_multiprocess_pipeline(db_url, incremental=True):
#     """
#     Main entry point for parallel processing.
#     """
#     # 1. Initialize Main Orchestrator
#     main_orch = PipelineOrchestrator(db_url)
#     tickers = main_orch.get_all_tickers()
    
#     if not tickers:
#         logger.error("No tickers found.")
#         return

#     logger.info(f"Starting {'INCREMENTAL' if incremental else 'FULL'} pipeline for {len(tickers)} stocks with Multiprocessing...")

#     # 2. PRE-WARM: Ensure Table Structure Exists
#     # We process ONE ticker linearly first to create the table/columns.
#     # This prevents 8 processes from trying to create the table simultaneously (Race Condition).
#     logger.info("Pre-warming schema with first ticker...")
#     try:
#         process_ticker_safe(tickers[0], db_url, incremental)
#         tickers = tickers[1:] # Remove the first one since it's done
#     except Exception as e:
#         logger.error(f"Pre-warm failed: {e}")

#     # 3. Start Pool
#     # max_workers = number of CPU cores. Adjust if you hit Yahoo Rate Limits.
#     max_workers = min(multiprocessing.cpu_count(), 8) 
    
#     success_count = 1 # We already did one
    
#     with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
#         # Map futures to tickers
#         future_to_ticker = {
#             executor.submit(process_ticker_safe, ticker, db_url, incremental): ticker 
#             for ticker in tickers
#         }
        
#         # Monitor Progress
#         for future in tqdm(concurrent.futures.as_completed(future_to_ticker), total=len(tickers), desc="Parallel Processing"):
#             ticker = future_to_ticker[future]
#             try:
#                 if future.result():
#                     success_count += 1
#             except Exception as e:
#                 logger.error(f"Ticker {ticker} generated an exception: {e}")

#     logger.info(f"Pipeline Completed. Processed: {success_count}")

# if __name__ == "__main__":
#     try:
#         # Run with incremental=True for daily updates (Appends new data)
#         # Run with incremental=False for full reload (Wipes and rebuilds)
#         run_multiprocess_pipeline(DB_URL, incremental=True)
#     except Exception as e:
#         logger.critical(f"Critical Failure: {e}")










import pandas as pd
import pandas_ta as ta
import yfinance as yf
import numpy as np
from typing import Dict, List, Optional, Set
import logging
import warnings
from functools import lru_cache
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.dialects.postgresql import insert
from tqdm import tqdm
import concurrent.futures
import multiprocessing

# ---- CRITICAL: Pre-import scipy BEFORE textblob/nltk to prevent ----
# ---- Windows importlib lock deadlock (KeyboardInterrupt in bootstrap) ----
# Catches BaseException (not just ImportError) because scipy C-extensions
# raise KeyboardInterrupt during their bootstrap on some Windows setups.
try:
    import scipy
    import scipy.stats
    import scipy.optimize
except BaseException:
    pass

try:
    from textblob import TextBlob
except ImportError:
    TextBlob = None

# --- CONFIGURATION ---
DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"
ENABLE_FUNDAMENTALS_IN_MULTIPROCESS = False

# --- SETUP ---
warnings.filterwarnings('ignore')

# Configure logging
# Note: In multiprocessing, logging to a single file can be tricky. 
# We rely on the main process to handle the primary logs or file locking.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('feature_engineering.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StockFeatureEngineer:
    """
    Production-grade feature engineering pipeline.
    Calculates Technical, Statistical, and Fundamental features.
    """
    
    def __init__(self, df: pd.DataFrame, ticker: str = None):
        # 1. Column Standardization
        df.columns = [c.lower() for c in df.columns]
        
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        self.df = df.copy()
        self.ticker = ticker
        
        # 2. Date Handling
        self.df['date'] = pd.to_datetime(self.df['date'])
        self.df.set_index('date', inplace=True)
        self.df.sort_index(inplace=True)
        
        # 3. Handle Duplicate Indices
        if not self.df.index.is_unique:
            self.df = self.df.loc[~self.df.index.duplicated(keep='first')]

        # 4. Set 'price' column
        self.df['price'] = self.df.get('adj_close', self.df['close'])
        
        self.target_cols = []

    def add_technical_indicators(self) -> pd.DataFrame:
        try:
            # Moving Averages
            for period in [5, 10, 20, 50, 100, 200]:
                try:
                    self.df[f'sma_{period}'] = self.df.ta.sma(length=period)
                    self.df[f'ema_{period}'] = self.df.ta.ema(length=period)
                except Exception as e:
                    logger.warning(f"Failed to calculate MA_{period} for {self.ticker}: {e}")
            
            # MACD
            try:
                macd = self.df.ta.macd(fast=12, slow=26, signal=9)
                if macd is not None: self.df = pd.concat([self.df, macd], axis=1)
            except Exception as e:
                logger.warning(f"MACD calculation failed for {self.ticker}: {e}")
            
            # ADX
            try:
                adx = self.df.ta.adx(length=14)
                if adx is not None: self.df = pd.concat([self.df, adx], axis=1)
            except Exception as e:
                logger.warning(f"ADX calculation failed for {self.ticker}: {e}")
            
            # RSI
            try:
                self.df['rsi_14'] = self.df.ta.rsi(length=14)
            except Exception as e:
                logger.warning(f"RSI calculation failed for {self.ticker}: {e}")
            
            # Bollinger Bands
            try:
                bbands = self.df.ta.bbands(length=20, std=2)
                if bbands is not None: 
                    self.df = pd.concat([self.df, bbands], axis=1)
                    if 'BBU_20_2.0' in self.df.columns and 'BBL_20_2.0' in self.df.columns:
                        self.df['bb_width'] = (self.df['BBU_20_2.0'] - self.df['BBL_20_2.0']) / (self.df['BBM_20_2.0'] + 1e-10)
            except Exception as e:
                logger.warning(f"Bollinger Bands calculation failed for {self.ticker}: {e}")

            # ATR
            try:
                self.df['atr_14'] = self.df.ta.atr(length=14)
            except Exception as e:
                logger.warning(f"ATR calculation failed for {self.ticker}: {e}")

            # Volume Indicators
            try:
                self.df['obv'] = self.df.ta.obv()
            except Exception as e:
                logger.warning(f"OBV calculation failed for {self.ticker}: {e}")
            
            try:
                self.df['vwap'] = self.df.ta.vwap()
            except Exception as e:
                logger.warning(f"VWAP calculation failed for {self.ticker}: {e}")
            
        except Exception as e:
            logger.error(f"Unexpected error in add_technical_indicators for {self.ticker}: {e}")
        
        return self.df

    def add_advanced_oscillators(self) -> pd.DataFrame:
        try:
            # Aroon
            try:
                aroon = self.df.ta.aroon(length=25)
                if aroon is not None:
                    self.df = pd.concat([self.df, aroon], axis=1)
                    if 'AROONU_25' in self.df.columns and 'AROOND_25' in self.df.columns:
                        self.df['aroon_osc'] = self.df['AROONU_25'] - self.df['AROOND_25']
            except Exception as e:
                logger.warning(f"Aroon calculation failed for {self.ticker}: {e}")

            # Stochastic
            try:
                stoch = self.df.ta.stoch(k=14, d=3, smooth_k=3)
                if stoch is not None:
                    self.df = pd.concat([self.df, stoch], axis=1)
            except Exception as e:
                logger.warning(f"Stochastic calculation failed for {self.ticker}: {e}")

            # CCI
            try:
                self.df['cci_20'] = self.df.ta.cci(length=20)
            except Exception as e:
                logger.warning(f"CCI calculation failed for {self.ticker}: {e}")
            
            # ROC
            try:
                self.df['roc_10'] = self.df.ta.roc(length=10)
            except Exception as e:
                logger.warning(f"ROC calculation failed for {self.ticker}: {e}")

        except Exception as e:
            logger.error(f"Unexpected error in add_advanced_oscillators for {self.ticker}: {e}")
            
        return self.df

    def add_price_patterns(self) -> pd.DataFrame:
        try:
            self.df['cdl_doji'] = self.df.ta.cdl_doji(append=False) / 100.0
        except Exception: pass

        O, H, L, C = self.df['open'], self.df['high'], self.df['low'], self.df['close']
        body = abs(C - O)
        
        self.df['gap_up'] = ((O - C.shift(1)) / (C.shift(1) + 1e-10)) > 0.005
        self.df['gap_down'] = ((O - C.shift(1)) / (C.shift(1) + 1e-10)) < -0.005
        
        self.df['body_size'] = body / (C + 1e-10)
        self.df['upper_wick'] = H - np.maximum(O, C)
        self.df['lower_wick'] = np.minimum(O, C) - L
        
        return self.df

    def add_statistical_features(self) -> pd.DataFrame:
        for period in [1, 3, 5, 10, 20]:
            self.df[f'return_{period}d'] = self.df['close'].pct_change(period)
            self.df[f'log_return_{period}d'] = np.log(self.df['close'] / (self.df['close'].shift(period) + 1e-10))
        
        self.df['hist_vol_20'] = self.df['close'].pct_change().rolling(20).std() * np.sqrt(252)
        
        for period in [20, 50]:
            mean = self.df['close'].rolling(period).mean()
            std = self.df['close'].rolling(period).std()
            self.df[f'zscore_{period}'] = (self.df['close'] - mean) / (std + 1e-10)
            
        return self.df

    @lru_cache(maxsize=128)
    def get_fundamental_data(self, ticker: str) -> Dict:
        if not ticker: return {}
        try:
            # FIX: Append .NS for NSE stocks
            search_ticker = ticker
            if not search_ticker.endswith('.NS') and not search_ticker.endswith('.BO'):
                search_ticker = f"{ticker}.NS"

            stock = yf.Ticker(search_ticker)
            info = stock.info
            
            keys = ['marketCap', 'trailingPE', 'forwardPE', 'priceToBook', 'beta', 'returnOnEquity']
            return {f"fund_{k}": info.get(k, 0) for k in keys}
        except KeyboardInterrupt:
            return {}
        except Exception:
            return {}

    def add_target_variables(self, forward_periods: List[int] = [1, 5]) -> pd.DataFrame:
        for period in forward_periods:
            col_name = f'target_return_{period}d'
            self.df[col_name] = self.df['close'].shift(-period) / self.df['close'] - 1
            self.target_cols.append(col_name)

            col_class = f'target_is_up_{period}d'
            self.df[col_class] = (self.df[col_name] > 0).astype(float)
            self.df.loc[self.df.index[-period:], col_class] = np.nan
            self.target_cols.append(col_class)

        return self.df

    def handle_missing_values(self) -> pd.DataFrame:
        self.df = self.df.replace([np.inf, -np.inf], np.nan)
        feature_cols = [c for c in self.df.columns if c not in self.target_cols]
        self.df[feature_cols] = self.df[feature_cols].ffill().fillna(0)
        return self.df

    def _validate_moving_averages(self) -> Dict[str, any]:
        """Validate SMA/EMA calculations are within price bounds"""
        validation_results = {'valid': True, 'issues': []}
        
        if len(self.df) < 200:
            return validation_results
        
        ma_columns = [col for col in self.df.columns if col.startswith('sma_') or col.startswith('ema_')]
        for col in ma_columns:
            if col in self.df.columns and self.df[col].notna().any():
                min_price = self.df['close'].min()
                max_price = self.df['close'].max()
                
                # Check if MA is within reasonable bounds (allow 5% margin)
                invalid_vals = ((self.df[col] < min_price * 0.95) | (self.df[col] > max_price * 1.05)) & self.df[col].notna()
                if invalid_vals.sum() > 0:
                    validation_results['issues'].append(f"{col}: {invalid_vals.sum()} values outside price bounds")
                    # Clip to bounds
                    self.df.loc[:, col] = self.df[col].clip(min_price * 0.5, max_price * 1.5)
        
        return validation_results

    def _validate_oscillators(self) -> Dict[str, any]:
        """Validate RSI, Stochastic, CCI bounds"""
        validation_results = {'valid': True, 'issues': []}
        
        # RSI should be 0-100
        if 'rsi_14' in self.df.columns:
            invalid_rsi = ((self.df['rsi_14'] < 0) | (self.df['rsi_14'] > 100)) & self.df['rsi_14'].notna()
            if invalid_rsi.sum() > 0:
                validation_results['issues'].append(f"RSI: {invalid_rsi.sum()} values outside [0,100]")
                self.df.loc[:, 'rsi_14'] = self.df['rsi_14'].clip(0, 100)
        
        # Stochastic K and D should be 0-100
        for col in ['STOCHk_14_3_3', 'STOCHd_14_3_3']:
            if col in self.df.columns:
                invalid = ((self.df[col] < 0) | (self.df[col] > 100)) & self.df[col].notna()
                if invalid.sum() > 0:
                    validation_results['issues'].append(f"{col}: {invalid.sum()} values outside [0,100]")
                    self.df.loc[:, col] = self.df[col].clip(0, 100)
        
        # CCI should be bounded roughly -300 to +300 but allow wider range
        if 'cci_20' in self.df.columns:
            outlier_cci = self.df['cci_20'].abs() > 1000
            if outlier_cci.sum() > 0:
                validation_results['issues'].append(f"CCI: {outlier_cci.sum()} extreme outliers detected")
        
        # MACD signal should cross MACD line
        if 'MACD_12_26_9' in self.df.columns and 'MACDh_12_26_9' in self.df.columns:
            self.df['_macd_diff'] = self.df['MACD_12_26_9'] - self.df.get('MACDs_12_26_9', self.df['MACD_12_26_9'])
            invalid_macd_hist = (self.df['MACDh_12_26_9'] - self.df['_macd_diff']).abs() > 1e-6
            if invalid_macd_hist.sum() > 100:  # Allow some rounding errors
                validation_results['issues'].append(f"MACD: {invalid_macd_hist.sum()} histogram inconsistencies")
        
        return validation_results

    def _validate_bollinger_bands(self) -> Dict[str, any]:
        """Validate Bollinger Band relationships: upper > middle > lower"""
        validation_results = {'valid': True, 'issues': []}
        
        if 'BBU_20_2.0' not in self.df.columns or 'BBL_20_2.0' not in self.df.columns:
            return validation_results
        
        # Check: Upper > Middle > Lower
        invalid_order = (self.df['BBU_20_2.0'] < self.df['BBM_20_2.0']) | (self.df['BBM_20_2.0'] < self.df['BBL_20_2.0'])
        if invalid_order.sum() > 0:
            validation_results['issues'].append(f"BB: {invalid_order.sum()} ordering violations (U<M or M<L)")
            # Fix by recalculating or sorting
            self.df.loc[invalid_order, 'BBL_20_2.0'] = self.df.loc[invalid_order, 'BBM_20_2.0'] - abs(self.df.loc[invalid_order, 'BBU_20_2.0'] - self.df.loc[invalid_order, 'BBM_20_2.0'])
        
        # Check bandwidth is positive
        if 'bb_width' in self.df.columns:
            invalid_width = self.df['bb_width'] < 0
            if invalid_width.sum() > 0:
                validation_results['issues'].append(f"BB Width: {invalid_width.sum()} negative values")
                self.df.loc[invalid_width, 'bb_width'] = 0
        
        return validation_results

    def _validate_statistical_features(self) -> Dict[str, any]:
        """Validate returns and volatility calculations"""
        validation_results = {'valid': True, 'issues': []}
        
        # Returns should rarely exceed ±50% in a single period
        for period in [1, 3, 5, 10, 20]:
            col = f'return_{period}d'
            if col in self.df.columns:
                extreme_returns = (self.df[col].abs() > 5.0) & self.df[col].notna()  # 500%+
                if extreme_returns.sum() > 0:
                    validation_results['issues'].append(f"{col}: {extreme_returns.sum()} extreme returns (>500%)")
        
        # Historical volatility should be positive
        if 'hist_vol_20' in self.df.columns:
            negative_vol = self.df['hist_vol_20'] < 0
            if negative_vol.sum() > 0:
                validation_results['issues'].append(f"Hist_Vol: {negative_vol.sum()} negative values")
                self.df.loc[negative_vol, 'hist_vol_20'] = 0
        
        # Zscore should be roughly -4 to +4 (99.9% of data)
        for period in [20, 50]:
            col = f'zscore_{period}'
            if col in self.df.columns:
                extreme_z = self.df[col].abs() > 10
                if extreme_z.sum() > 0:
                    validation_results['issues'].append(f"{col}: {extreme_z.sum()} extreme zscores (>10)")
        
        return validation_results

    def _validate_volume_features(self) -> Dict[str, any]:
        """Validate volume-based indicators (OBV, VWAP)"""
        validation_results = {'valid': True, 'issues': []}
        
        # OBV should be monotonic trend (generally increasing or decreasing)
        if 'obv' in self.df.columns and len(self.df) > 1:
            obv_changes = self.df['obv'].diff()
            obv_reversals = ((obv_changes > 0).astype(int).diff().abs() > 0).sum()
            # Some reversals expected, but extreme means data issue
            if obv_reversals > len(self.df) * 0.8:
                validation_results['issues'].append(f"OBV: {obv_reversals} trend reversals (high volatility)")
        
        # VWAP should track close price closely
        if 'vwap' in self.df.columns:
            vwap_deviation = (self.df['vwap'] - self.df['close']).abs() / self.df['close']
            high_deviation = (vwap_deviation > 0.1).sum()  # >10% deviation
            if high_deviation > len(self.df) * 0.1:
                validation_results['issues'].append(f"VWAP: {high_deviation} records with >10% deviation from close")
        
        return validation_results

    def _get_feature_quality_metrics(self) -> Dict[str, any]:
        """Calculate comprehensive feature quality metrics"""
        metrics = {
            'total_features': len([c for c in self.df.columns if c not in ['date', 'ticker', 'open', 'high', 'low', 'close', 'volume', 'adj_close', 'price']]),
            'null_counts': {},
            'inf_counts': {},
            'validation_status': 'PASS',
            'warnings': [],
            'total_rows': len(self.df)
        }
        
        feature_cols = [c for c in self.df.columns if c not in self.target_cols and c not in ['date', 'ticker', 'open', 'high', 'low', 'close', 'volume', 'adj_close', 'price']]
        
        for col in feature_cols:
            null_count = self.df[col].isna().sum()
            inf_count = np.isinf(self.df[col]).sum() if self.df[col].dtype in [np.float64, np.float32] else 0
            
            if null_count > 0:
                metrics['null_counts'][col] = int(null_count)
            if inf_count > 0:
                metrics['inf_counts'][col] = int(inf_count)
                metrics['validation_status'] = 'WARNING'
                metrics['warnings'].append(f"{col}: {inf_count} inf values")
        
        return metrics

    def build_features(self, include_fundamentals: bool = True) -> pd.DataFrame:
        """Build features with comprehensive validation and quality checks"""
        try:
            self.add_technical_indicators()
            self.add_advanced_oscillators()
            self.add_price_patterns()
            self.add_statistical_features()
            
            # Run validations
            ma_validation = self._validate_moving_averages()
            osc_validation = self._validate_oscillators()
            bb_validation = self._validate_bollinger_bands()
            stat_validation = self._validate_statistical_features()
            vol_validation = self._validate_volume_features()
            
            # Log validation results
            all_issues = []
            for val_result in [ma_validation, osc_validation, bb_validation, stat_validation, vol_validation]:
                if val_result.get('issues'):
                    all_issues.extend(val_result['issues'])
            
            if all_issues and self.ticker:
                logger.info(f"Feature validation for {self.ticker}: {len(all_issues)} issues found and corrected")
                for issue in all_issues[:3]:  # Log first 3 issues
                    logger.debug(f"  - {issue}")
            
            if include_fundamentals and self.ticker:
                try:
                    fundamentals = self.get_fundamental_data(self.ticker)
                    for k, v in fundamentals.items():
                        self.df[k] = v
                except Exception as e:
                    logger.warning(f"Failed to fetch fundamentals for {self.ticker}: {e}")
            
            self.add_target_variables()
            self.handle_missing_values()
            
            # Get quality metrics
            quality_metrics = self._get_feature_quality_metrics()
            
            # Log quality summary
            null_total = sum(quality_metrics['null_counts'].values())
            if null_total > 0:
                logger.debug(f"{self.ticker}: {null_total} null values in features after processing")
            
            self.df.reset_index(inplace=True)
            self.df = self.df.loc[:, ~self.df.columns.duplicated()]
            
            return self.df
        
        except Exception as e:
            logger.error(f"Critical error in build_features for {self.ticker}: {e}")
            raise


class PipelineOrchestrator:
    """Manages Database Connections and Pipeline Execution."""
    
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.table_name = 'engineered_features'
        self.ticker_query_timeout_ms = 30_000
        self.lock_timeout_ms = 5_000
        self.known_columns: Set[str] = set()
        self._initialize_schema_knowledge()

    def _configure_query_timeouts(self, conn):
        try:
            conn.execute(text("SET statement_timeout = :timeout"), {'timeout': self.ticker_query_timeout_ms})
            conn.execute(text("SET lock_timeout = :timeout"), {'timeout': self.lock_timeout_ms})
        except Exception:
            pass

    def _ensure_source_indexes(self, conn):
        return

    def _initialize_schema_knowledge(self):
        inspector = inspect(self.engine)
        if inspector.has_table(self.table_name):
            self.known_columns = {col['name'] for col in inspector.get_columns(self.table_name)}
        else:
            self.known_columns = set()

    def ensure_table_structure(self, df_sample: pd.DataFrame):
        """Creates table structure based on a sample dataframe to prevent race conditions."""
        if df_sample.empty: return
        self.sync_table_schema(df_sample)

    def get_all_tickers(self) -> List[str]:
        try:
            with self.engine.connect() as conn:
                self._configure_query_timeouts(conn)

                primary_query = text("""
                    SELECT ticker
                    FROM nse_stocks
                    WHERE ticker IS NOT NULL AND ticker <> ''
                    GROUP BY ticker
                """)
                result = conn.execute(primary_query)
                tickers = sorted(row[0] for row in result)

                if tickers:
                    return tickers

                fallback_query = text("""
                    SELECT ticker
                    FROM nse_stocks
                    WHERE ticker IS NOT NULL AND ticker <> ''
                    GROUP BY ticker
                """)
                fallback_result = conn.execute(fallback_query)
                return sorted(row[0] for row in fallback_result)
        except Exception as e:
            logger.error(f"Failed to fetch tickers: {e}")
            return []

    def get_stock_data(self, ticker: str) -> pd.DataFrame:
        query = text("""
            SELECT date, open, high, low, close, volume, adj_close
            FROM nse_stocks 
            WHERE ticker = :ticker 
            ORDER BY date ASC
        """)
        return pd.read_sql(query, self.engine, params={'ticker': ticker})

    def get_latest_db_date(self, ticker: str) -> Optional[pd.Timestamp]:
        try:
            if not self.known_columns: 
                return None
            with self.engine.connect() as conn:
                query = text(f'SELECT MAX(date) FROM "{self.table_name}" WHERE ticker = :ticker')
                result = conn.execute(query, {'ticker': ticker}).fetchone()
                if result and result[0]:
                    return pd.to_datetime(result[0])
            return None
        except Exception:
            return None

    def sync_table_schema(self, df: pd.DataFrame):
        if df.empty: return
        current_cols = set(df.columns)
        new_cols = current_cols - self.known_columns
        
        if not new_cols: return

        if not self.known_columns:
            # logger.info(f"Creating table {self.table_name}")
            df.head(0).to_sql(self.table_name, self.engine, if_exists='replace', index=False)
            with self.engine.begin() as conn:
                conn.execute(text(f"""
                    ALTER TABLE "{self.table_name}" 
                    ADD CONSTRAINT pk_engineered_features PRIMARY KEY (ticker, date);
                """))
            self.known_columns = current_cols
            return

        with self.engine.begin() as conn:
            for col in new_cols:
                # logger.info(f"Adding new column: {col}")
                dtype = df[col].dtype
                sql_type = "TEXT"
                if pd.api.types.is_integer_dtype(dtype): sql_type = "BIGINT"
                elif pd.api.types.is_float_dtype(dtype): sql_type = "DOUBLE PRECISION"
                elif pd.api.types.is_datetime64_any_dtype(dtype): sql_type = "TIMESTAMP"
                elif pd.api.types.is_bool_dtype(dtype): sql_type = "BOOLEAN"
                
                try:
                    conn.execute(text(f'ALTER TABLE "{self.table_name}" ADD COLUMN "{col}" {sql_type}'))
                except Exception:
                    # Ignore error if column was added by another process
                    pass
        
        self.known_columns.update(new_cols)

    def save_features_incremental(self, df: pd.DataFrame):
        if df.empty: return
        ticker = df['ticker'].iloc[0]
        latest_date = self.get_latest_db_date(ticker)
        self.sync_table_schema(df)
        
        try:
            if latest_date:
                df_new = df[df['date'] > latest_date]
                if not df_new.empty:
                    logger.debug(f"Inserting {len(df_new)} new records for {ticker}, columns: {df_new.columns.tolist()[:10]}")
                    df_new.to_sql(self.table_name, self.engine, if_exists='append', index=False, method='multi', chunksize=1000)
                    logger.info(f"Saved {len(df_new)} new records for {ticker}")
                else:
                    logger.debug(f"No new records for {ticker} (all data already in DB)")
            else:
                self.save_features_upsert(df)
        except Exception as e:
            logger.error(f"Incremental save failed for {ticker}: {e}", exc_info=True)
            raise

    def save_features_upsert(self, df: pd.DataFrame):
        if df.empty: return
        ticker = df['ticker'].iloc[0]
        self.sync_table_schema(df)
        try:
            # Verify data before insert
            non_null_counts = df.notna().sum()
            logger.debug(f"Upsert data for {ticker}: shape={df.shape}, non-null=[{non_null_counts['date']}/{non_null_counts['close']}/{non_null_counts.get('rsi_14', 0)}]")
            
            with self.engine.begin() as conn:
                # Delete old data for this ticker
                conn.execute(text(f'DELETE FROM "{self.table_name}" WHERE ticker = :ticker'), {'ticker': ticker})
                # Insert new data
                df.to_sql(self.table_name, conn, if_exists='append', index=False, method='multi', chunksize=1000)
                logger.info(f"Upserted {len(df)} records for {ticker}")
        except Exception as e:
            logger.error(f"Upsert save failed for {ticker}: {e}", exc_info=True)
            raise

    def get_feature_quality_report(self, limit_tickers: int = 50) -> Dict[str, any]:
        """Get comprehensive feature engineering quality report"""
        try:
            with self.engine.connect() as conn:
                # Get all engineered tickers
                all_tickers_query = text(f"SELECT DISTINCT ticker FROM \"{self.table_name}\" ORDER BY ticker LIMIT :limit")
                tickers_result = conn.execute(all_tickers_query, {'limit': limit_tickers})
                tickers = [row[0] for row in tickers_result]
                
                if not tickers:
                    return {
                        'overall_status': 'HEALTHY',
                        'total_tickers': 0,
                        'ticker_details': [],
                        'summary': 'No engineered features found'
                    }
                
                ticker_details = []
                
                for ticker in tickers:
                    # Count features per ticker
                    feature_count_query = text(f"SELECT COUNT(*) as cnt FROM \"{self.table_name}\" WHERE ticker = :ticker")
                    count_result = conn.execute(feature_count_query, {'ticker': ticker}).fetchone()
                    record_count = count_result[0] if count_result else 0
                    
                    # Check for missing values
                    null_query = text(f"""
                        SELECT COUNT(*) as total_nulls FROM "{self.table_name}" 
                        WHERE ticker = :ticker 
                        AND (rsi_14 IS NULL OR hist_vol_20 IS NULL OR sma_20 IS NULL)
                    """)
                    null_result = conn.execute(null_query, {'ticker': ticker}).fetchone()
                    null_count = null_result[0] if null_result else 0
                    
                    # Calculate quality percentage (100% - null percentage)
                    quality_pct = 100 if record_count == 0 else max(0, 100 - (null_count * 100 / record_count))
                    
                    ticker_details.append({
                        'ticker': ticker,
                        'records': record_count,
                        'null_count': null_count,
                        'quality_percentage': round(quality_pct, 2),
                        'status': 'EXCELLENT' if quality_pct >= 95 else 'GOOD' if quality_pct >= 80 else 'NEEDS_ATTENTION'
                    })
                
                # Determine overall status
                avg_quality = np.mean([t['quality_percentage'] for t in ticker_details]) if ticker_details else 100
                overall_status = 'EXCELLENT' if avg_quality >= 95 else 'GOOD' if avg_quality >= 80 else 'NEEDS_ATTENTION'
                
                return {
                    'overall_status': overall_status,
                    'average_quality_percentage': round(avg_quality, 2),
                    'total_tickers': len(tickers),
                    'ticker_details': ticker_details
                }
        
        except Exception as e:
            logger.error(f"Failed to generate feature quality report: {e}")
            return {'overall_status': 'ERROR', 'error': str(e)}

    def validate_feature_consistency(self, ticker: str) -> Dict[str, any]:
        """Validate consistency of engineered features for a specific ticker"""
        try:
            query = text(f"""
                SELECT rsi_14, hist_vol_20, sma_20, ema_20, atr_14, obv, vwap, 
                       return_1d, return_5d, hist_vol_20, zscore_20
                FROM "{self.table_name}" 
                WHERE ticker = :ticker 
                ORDER BY date DESC 
                LIMIT 1
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {'ticker': ticker}).fetchone()
                
                if not result:
                    return {'status': 'NO_DATA', 'ticker': ticker}
                
                validation_results = {
                    'ticker': ticker,
                    'status': 'PASS',
                    'checks': []
                }
                
                # Basic validation checks
                rsi, vol, sma, ema, atr, obv, vwap, r1d, r5d, hvol, zs = result
                
                checks = []
                # RSI bounds check
                if rsi is not None and (rsi < 0 or rsi > 100):
                    checks.append({'check': 'RSI bounds', 'status': 'FAIL', 'value': rsi})
                    validation_results['status'] = 'FAIL'
                
                # Volatility bounds
                if hvol is not None and hvol < 0:
                    checks.append({'check': 'Volatility', 'status': 'FAIL', 'value': hvol})
                    validation_results['status'] = 'FAIL'
                
                # Moving average relationship
                if sma is not None and ema is not None and abs(sma - ema) > sma * 0.2:
                    checks.append({'check': 'SMA/EMA divergence', 'status': 'WARNING', 'gap': abs(sma - ema)})
                
                # Zscore bounds
                if zs is not None and abs(zs) > 10:
                    checks.append({'check': 'Zscore extreme', 'status': 'WARNING', 'value': zs})
                
                validation_results['checks'] = checks if checks else [{'check': 'All validations', 'status': 'PASS'}]
                
                return validation_results
        except Exception as e:
            logger.error(f"Failed to validate features for {ticker}: {e}")
            return {'status': 'ERROR', 'ticker': ticker, 'error': str(e)}

## --- GLOBAL WORKER FUNCTION (COMPUTE ONLY — no DB writes) ---
def _compute_features_for_ticker(ticker: str, db_url: str):
    """
    Worker function: fetch data and compute features ONLY.
    Returns (ticker, DataFrame) or (ticker, None) on failure.
    
    CRITICAL: Does NOT write to DB. All DB writes happen in the main
    thread sequentially to avoid ALTER TABLE ACCESS EXCLUSIVE lock
    deadlocks when 8 threads simultaneously try sync_table_schema.
    """
    try:
        local_engine = create_engine(db_url, pool_pre_ping=True, pool_size=1, max_overflow=0)
        query = text("""
            SELECT * FROM nse_stocks WHERE ticker = :ticker ORDER BY date ASC
        """)
        df_raw = pd.read_sql(query, local_engine, params={'ticker': ticker})
        local_engine.dispose()
        
        if len(df_raw) < 200:
            return (ticker, None)
        
        engineer = StockFeatureEngineer(df_raw, ticker=ticker)
        df_features = engineer.build_features(
            include_fundamentals=ENABLE_FUNDAMENTALS_IN_MULTIPROCESS
        )
        
        if df_features.empty:
            return (ticker, None)
        
        if 'ticker' not in df_features.columns:
            df_features['ticker'] = ticker
        
        critical_cols = ['date', 'ticker']
        if not all(col in df_features.columns for col in critical_cols):
            return (ticker, None)
        
        return (ticker, df_features)
        
    except KeyboardInterrupt:
        return (ticker, None)
    except Exception:
        return (ticker, None)


# Legacy wrapper kept for compatibility (used by pre-warm)
def process_ticker_safe(ticker: str, db_url: str, incremental: bool):
    """Process a single ticker end-to-end (fetch + compute + save)."""
    try:
        local_orch = PipelineOrchestrator(db_url)
        df_raw = local_orch.get_stock_data(ticker)
        if len(df_raw) < 200:
            return False
        engineer = StockFeatureEngineer(df_raw, ticker=ticker)
        df_features = engineer.build_features(
            include_fundamentals=ENABLE_FUNDAMENTALS_IN_MULTIPROCESS
        )
        if df_features.empty:
            return False
        if 'ticker' not in df_features.columns:
            df_features['ticker'] = ticker
        if incremental:
            local_orch.save_features_incremental(df_features)
        else:
            local_orch.save_features_upsert(df_features)
        return True
    except KeyboardInterrupt:
        return False
    except Exception:
        return False


def run_multiprocess_pipeline(db_url, incremental=True):
    """
    Parallel feature engineering pipeline.
    
    Architecture (v34.1 — deadlock-free):
      Phase 1: PRE-WARM — process one ticker sequentially to create table schema
      Phase 2: COMPUTE — ThreadPoolExecutor computes features in parallel (no DB writes)
      Phase 3: SAVE — main thread writes results to DB sequentially (no lock contention)
      Phase 4: RETRY — failed tickers retried sequentially
    
    Root cause of previous deadlock:
      8 threads each created their own PipelineOrchestrator with empty known_columns,
      so ALL attempted ALTER TABLE ADD COLUMN simultaneously → ACCESS EXCLUSIVE lock
      on the same table → all threads blocked indefinitely → tqdm stuck at 0%.
    """
    main_orch = PipelineOrchestrator(db_url)
    tickers = main_orch.get_all_tickers()
    
    if not tickers:
        logger.error("No tickers found.")
        return

    total_count = len(tickers)
    logger.info(f"Starting {'INCREMENTAL' if incremental else 'FULL'} pipeline "
                f"for {total_count} stocks (compute-then-save architecture)...")

    # ── Phase 1: PRE-WARM ──
    logger.info("Phase 1: Pre-warming schema with first ticker...")
    try:
        process_ticker_safe(tickers[0], db_url, incremental)
        tickers = tickers[1:]
    except Exception as e:
        logger.error(f"Pre-warm failed: {e}")

    # ── Phase 2: PARALLEL COMPUTE (no DB writes) ──
    max_workers = min(multiprocessing.cpu_count(), 8)
    success_count = 1  # pre-warmed ticker
    save_failures = []
    
    # Suppress per-ticker INFO logs during parallel phase so tqdm works
    console_handlers = [h for h in logging.getLogger().handlers 
                        if isinstance(h, logging.StreamHandler) 
                        and not isinstance(h, logging.FileHandler)]
    original_levels = [(h, h.level) for h in console_handlers]
    for h in console_handlers:
        h.setLevel(logging.WARNING)
    
    logger.warning(f"Phase 2: Computing features with {max_workers} threads...")
    
    computed_results = []  # List of (ticker, DataFrame)
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {
                executor.submit(_compute_features_for_ticker, t, db_url): t
                for t in tickers
            }
            
            for future in tqdm(concurrent.futures.as_completed(future_to_ticker),
                             total=len(tickers), desc="Computing features"):
                try:
                    ticker, df_result = future.result(timeout=180)
                    if df_result is not None:
                        computed_results.append((ticker, df_result))
                except concurrent.futures.TimeoutError:
                    ticker = future_to_ticker[future]
                    save_failures.append(ticker)
                except Exception:
                    ticker = future_to_ticker[future]
                    save_failures.append(ticker)
                    
    except KeyboardInterrupt:
        logger.warning("Computation interrupted by user.")

    # Restore console log levels
    for h, lvl in original_levels:
        h.setLevel(lvl)

    logger.info(f"Phase 2 complete: {len(computed_results)} computed, "
                f"{len(save_failures)} failed")

    # ── Phase 3: SEQUENTIAL SAVE (no lock contention) ──
    logger.info(f"Phase 3: Saving {len(computed_results)} results to database...")
    
    for ticker, df_features in tqdm(computed_results, desc="Saving to DB"):
        try:
            if incremental:
                main_orch.save_features_incremental(df_features)
            else:
                main_orch.save_features_upsert(df_features)
            success_count += 1
        except Exception as e:
            logger.debug(f"Save failed for {ticker}: {e}")
            save_failures.append(ticker)

    # ── Phase 4: SEQUENTIAL RETRY ──
    retry_count = 0
    if save_failures:
        unique_failures = list(set(save_failures))
        logger.info(f"Phase 4: Retrying {len(unique_failures)} failed tickers...")
        for ticker in tqdm(unique_failures, desc="Retrying"):
            try:
                if process_ticker_safe(ticker, db_url, incremental):
                    success_count += 1
                    retry_count += 1
            except Exception:
                pass

    logger.info(f"\n{'='*60}")
    logger.info(f"Pipeline Complete")
    logger.info(f"  Total tickers:  {total_count}")
    logger.info(f"  Successful:     {success_count}")
    logger.info(f"  Failed:         {total_count - success_count}")
    logger.info(f"  Retried OK:     {retry_count}")
    logger.info(f"  Success rate:   {success_count/max(total_count,1)*100:.1f}%")
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        run_multiprocess_pipeline(DB_URL, incremental=True)
    except Exception as e:
        logger.critical(f"Critical Failure: {e}")