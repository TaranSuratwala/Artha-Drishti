# import yfinance as yf
# import pandas as pd
# import requests
# import io
# import time
# from sqlalchemy import create_engine, text
# from tqdm import tqdm

# # --- CONFIGURATION ---
# # SECURITY WARNING: Use environment variables for passwords in production!
# DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"
# NSE_LIST_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

# class NSEDataPipeline:
#     def __init__(self, db_url):
#         self.engine = create_engine(db_url, pool_pre_ping=True)
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#         }
#         self.init_timescaledb()

#     def init_timescaledb(self):
#         with self.engine.begin() as conn:
#             conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
#             conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS nse_stocks (
#                     date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
#                     ticker VARCHAR(20) NOT NULL,
#                     open DOUBLE PRECISION,
#                     high DOUBLE PRECISION,
#                     low DOUBLE PRECISION,
#                     close DOUBLE PRECISION,
#                     adj_close DOUBLE PRECISION,
#                     volume BIGINT,
#                     UNIQUE (date, ticker)
#                 );
#             """))
#             try:
#                 conn.execute(text("SELECT create_hypertable('nse_stocks', 'date', if_not_exists => TRUE);"))
#             except Exception:
#                 pass

#     # --- NEW METHODS ADDED FOR FLASK API ---
#     def get_latest_data(self, limit=None):
#         """Fetches the most recent record for every unique ticker."""
#         # DISTINCT ON (ticker) ensures we get one row per stock (the latest one)
#         query_str = """
#             SELECT DISTINCT ON (ticker) * FROM nse_stocks 
#             ORDER BY ticker, date DESC
#         """
#         if limit:
#             query_str = f"SELECT * FROM ({query_str}) AS sub LIMIT {limit}"
            
#         with self.engine.connect() as conn:
#             result = conn.execute(text(query_str))
#             # Convert SQLAlchemy Rows to list of dicts
#             return [dict(row._mapping) for row in result]

#     def get_ticker_history(self, ticker):
#         """Fetches full history for a specific ticker for plotting."""
#         query = text("SELECT * FROM nse_stocks WHERE ticker = :ticker ORDER BY date ASC")
#         with self.engine.connect() as conn:
#             result = conn.execute(query, {"ticker": ticker})
#             return [dict(row._mapping) for row in result]
#     # ----------------------------------------

#     def get_all_nse_symbols(self):
#         print("Fetching latest NSE symbol list...")
#         try:
#             response = requests.get(NSE_LIST_URL, headers=self.headers, timeout=10)
#             df = pd.read_csv(io.StringIO(response.text))
#             df.columns = [c.strip() for c in df.columns]
#             symbols = [f"{symbol}.NS" for symbol in df['SYMBOL'].unique()]
#             return symbols
#         except Exception as e:
#             print(f"Failed to fetch NSE list: {e}")
#             return []

#     def _process_yfinance_data(self, data, batch_tickers):
#         batch_list = []
        
#         def clean_df(df_in, ticker_name):
#             df_in = df_in.copy().reset_index()
#             # Rename standard yfinance columns to lowercase DB columns
#             cols_map = {
#                 'Date': 'date', 'Open': 'open', 'High': 'high', 
#                 'Low': 'low', 'Close': 'close', 'Adj Close': 'adj_close', 
#                 'Volume': 'volume'
#             }
#             df_in = df_in.rename(columns=cols_map)
            
#             # Ensure date is naive (no timezone) for Postgres
#             if 'date' in df_in.columns:
#                  df_in['date'] = pd.to_datetime(df_in['date']).dt.tz_localize(None)
            
#             df_in['ticker'] = ticker_name.replace('.NS', '')
            
#             # Filter only valid columns
#             valid_cols = ['date', 'ticker', 'open', 'high', 'low', 'close', 'adj_close', 'volume']
#             return df_in[[c for c in valid_cols if c in df_in.columns]]

#         # Handle yfinance MultiIndex (when downloading multiple tickers)
#         if isinstance(data.columns, pd.MultiIndex):
#             for ticker in data.columns.levels[0]:
#                 try:
#                     # Select data for this ticker
#                     df_temp = data[ticker].dropna(how='all')
#                     if not df_temp.empty:
#                         batch_list.append(clean_df(df_temp, ticker))
#                 except KeyError: continue
#         # Handle Flat Index (single ticker or failed multi-download)
#         else:
#             if not data.empty and len(batch_tickers) == 1:
#                 batch_list.append(clean_df(data, batch_tickers[0]))

#         if not batch_list: return pd.DataFrame()
#         return pd.concat(batch_list)

#     def upsert_to_timescale(self, df):
#         if df.empty: return
#         temp_table = "temp_batch_upload"
#         with self.engine.begin() as conn:
#             conn.execute(text(f"DROP TABLE IF EXISTS {temp_table}"))
#             conn.execute(text(f"CREATE TEMP TABLE {temp_table} (LIKE nse_stocks INCLUDING ALL)"))
#             df.to_sql(temp_table, conn, if_exists='append', index=False)
#             conn.execute(text(f"""
#                 INSERT INTO nse_stocks (date, ticker, open, high, low, close, adj_close, volume)
#                 SELECT date, ticker, open, high, low, close, adj_close, volume FROM {temp_table}
#                 ON CONFLICT (date, ticker) DO UPDATE SET
#                     open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
#                     close = EXCLUDED.close, adj_close = EXCLUDED.adj_close, volume = EXCLUDED.volume;
#             """))
#             conn.execute(text(f"DROP TABLE IF EXISTS {temp_table}"))

#     def download_and_store(self, symbols, period="5y"):
#         chunk_size = 50 
#         print(f"Starting pipeline for {len(symbols)} tickers...")
#         for i in tqdm(range(0, len(symbols), chunk_size), unit="batch"):
#             batch = symbols[i:i + chunk_size]
#             try:
#                 # auto_adjust=False ensures we get 'Adj Close' and 'Close' separately
#                 data = yf.download(tickers=batch, period=period, interval="1d", 
#                                    group_by='ticker', threads=True, progress=False)
#                 if not data.empty:
#                     final_df = self._process_yfinance_data(data, batch)
#                     self.upsert_to_timescale(final_df)
#             except Exception as e:
#                 print(f"Error in batch {i}: {e}")
#                 time.sleep(1)
#         print("--- COMPLETE ---")

# if __name__ == "__main__":
#     pipeline = NSEDataPipeline(DB_URL)
    
#     # 1. Fetch all symbols
#     all_symbols = pipeline.get_all_nse_symbols()
    
#     # 2. Check if symbols were found and start download
#     if all_symbols:
#         print(f"Found {len(all_symbols)} tickers. Starting download...")
#         pipeline.download_and_store(all_symbols, period="5y")








# import yfinance as yf
# import pandas as pd
# import requests
# import io
# import time
# import logging
# import sys
# import csv
# from datetime import datetime, timedelta
# from sqlalchemy import create_engine, text
# from tqdm import tqdm
# import numpy as np
# from typing import List, Optional, Dict, Tuple
# import os
# from concurrent.futures import ThreadPoolExecutor, as_completed

# # --- WINDOWS CONSOLE FIX ---
# if sys.platform.startswith('win'):
#     try:
#         sys.stdout.reconfigure(encoding='utf-8')
#     except Exception:
#         pass

# DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Taran%4017@localhost:5432/StockDB")

# # --- CONFIGURATION ---
# class Config:
#     DB_URL = os.getenv("DB_URL", "postgresql://postgres:Taran%4017@localhost:5432/StockDB")
#     NSE_LIST_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    
#     CHUNK_SIZE = 50
#     MAX_WORKERS = 4
#     MAX_RETRIES = 3
#     REQUEST_TIMEOUT = 30
    
#     DB_POOL_SIZE = 10
#     DB_MAX_OVERFLOW = 20
#     RATE_LIMIT_DELAY = 0.5
    
#     HEADERS = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
#         'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#         'Connection': 'keep-alive'
#     }

# # --- LOGGING ---
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('nse_pipeline.log', encoding='utf-8'),
#         logging.StreamHandler(sys.stdout)
#     ]
# )
# logger = logging.getLogger(__name__)

# class NSEDataPipeline:
#     def __init__(self, db_url: str = Config.DB_URL):
#         self.engine = create_engine(
#             db_url, 
#             pool_pre_ping=True, 
#             pool_size=Config.DB_POOL_SIZE, 
#             max_overflow=Config.DB_MAX_OVERFLOW,
#             pool_recycle=3600
#         )
#         self.session = requests.Session()
#         self.session.headers.update(Config.HEADERS)
#         self.init_database()
#         self.failed_tickers = []
#         self.success_count = 0
#         self.error_count = 0
#         logger.info("NSE Data Pipeline initialized")

#     def init_database(self):
#         """Initialize database schema"""
#         with self.engine.begin() as conn:
#             conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            
#             # Main table
#             conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS nse_stocks (
#                     date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
#                     ticker VARCHAR(20) NOT NULL,
#                     open DOUBLE PRECISION,
#                     high DOUBLE PRECISION,
#                     low DOUBLE PRECISION,
#                     close DOUBLE PRECISION,
#                     adj_close DOUBLE PRECISION,
#                     volume BIGINT,
#                     split_factor DOUBLE PRECISION DEFAULT 1.0,
#                     delivery_qty BIGINT DEFAULT 0,
#                     delivery_percentage DOUBLE PRECISION DEFAULT 0.0,
#                     traded_qty BIGINT DEFAULT 0,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     PRIMARY KEY (ticker, date)
#                 );
#             """))
            
#             # Hypertable
#             try:
#                 conn.execute(text("""
#                     SELECT create_hypertable('nse_stocks', 'date', 
#                         if_not_exists => TRUE,
#                         chunk_time_interval => INTERVAL '1 month');
#                 """))
#             except Exception:
#                 pass 

#             # Stock Metadata
#             conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS stock_metadata (
#                     ticker VARCHAR(20) PRIMARY KEY,
#                     company_name VARCHAR(200),
#                     isin VARCHAR(20),
#                     last_fetched_date DATE,
#                     is_active BOOLEAN DEFAULT TRUE,
#                     last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                 );
#             """))
            
#             # Engineered Features Table
#             conn.execute(text("""
#                 CREATE TABLE IF NOT EXISTS engineered_features (
#                     id SERIAL PRIMARY KEY,
#                     ticker VARCHAR(20) NOT NULL,
#                     date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
#                     open DOUBLE PRECISION,
#                     high DOUBLE PRECISION,
#                     low DOUBLE PRECISION,
#                     close DOUBLE PRECISION,
#                     adj_close DOUBLE PRECISION,
#                     volume BIGINT,
#                     returns DOUBLE PRECISION,
#                     log_returns DOUBLE PRECISION,
#                     rsi_7 DOUBLE PRECISION,
#                     rsi_14 DOUBLE PRECISION,
#                     rsi_21 DOUBLE PRECISION,
#                     macd DOUBLE PRECISION,
#                     macd_signal DOUBLE PRECISION,
#                     macd_histogram DOUBLE PRECISION,
#                     bb_upper DOUBLE PRECISION,
#                     bb_middle DOUBLE PRECISION,
#                     bb_lower DOUBLE PRECISION,
#                     bb_width DOUBLE PRECISION,
#                     bb_position DOUBLE PRECISION,
#                     atr_14 DOUBLE PRECISION,
#                     volatility_2 DOUBLE PRECISION,
#                     sma_5 DOUBLE PRECISION,
#                     sma_10 DOUBLE PRECISION,
#                     sma_20 DOUBLE PRECISION,
#                     sma_50 DOUBLE PRECISION,
#                     sma_100 DOUBLE PRECISION,
#                     sma_200 DOUBLE PRECISION,
#                     ema_5 DOUBLE PRECISION,
#                     ema_10 DOUBLE PRECISION,
#                     ema_12 DOUBLE PRECISION,
#                     ema_20 DOUBLE PRECISION,
#                     ema_50 DOUBLE PRECISION,
#                     ema_100 DOUBLE PRECISION,
#                     ema_200 DOUBLE PRECISION,
#                     adx DOUBLE PRECISION,
#                     stochastic_k DOUBLE PRECISION,
#                     stochastic_d DOUBLE PRECISION,
#                     cci DOUBLE PRECISION,
#                     williams_r DOUBLE PRECISION,
#                     obv DOUBLE PRECISION,
#                     obv_ema DOUBLE PRECISION,
#                     pattern_head_shoulders BOOLEAN,
#                     pattern_double_top BOOLEAN,
#                     pattern_double_bottom BOOLEAN,
#                     pattern_triangle BOOLEAN,
#                     pattern_flag BOOLEAN,
#                     support_level DOUBLE PRECISION,
#                     resistance_level DOUBLE PRECISION,
#                     trend_channel DOUBLE PRECISION,
#                     volume_sentiment DOUBLE PRECISION,
#                     liquidity_score DOUBLE PRECISION,
#                     strength_score DOUBLE PRECISION,
#                     signal_strength DOUBLE PRECISION,
#                     future_return_5d DOUBLE PRECISION,
#                     future_direction_5d INTEGER,
#                     feature_count INTEGER,
#                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                     UNIQUE (ticker, date)
#                 );
#             """))
            
#             # Add indexes for performance
#             conn.execute(text("""
#                 CREATE INDEX IF NOT EXISTS idx_nse_stocks_ticker_date 
#                 ON nse_stocks(ticker, date DESC);
#             """))
            
#             conn.execute(text("""
#                 CREATE INDEX IF NOT EXISTS idx_nse_stocks_date 
#                 ON nse_stocks(date DESC);
#             """))
            
#             conn.execute(text("""
#                 CREATE INDEX IF NOT EXISTS idx_engineered_features_ticker_date 
#                 ON engineered_features(ticker, date DESC);
#             """))
            
#             conn.execute(text("""
#                 CREATE INDEX IF NOT EXISTS idx_engineered_features_ticker 
#                 ON engineered_features(ticker);
#             """))

#     # --- METHODS REQUIRED BY SCREENER ---
#     def get_latest_data(self, limit=None):
#         """Fetches the most recent record for every unique ticker."""
#         # DISTINCT ON (ticker) ensures we get one row per stock (the latest one)
#         query_str = """
#             SELECT DISTINCT ON (ticker) * FROM nse_stocks 
#             ORDER BY ticker, date DESC
#         """
#         if limit:
#             query_str = f"SELECT * FROM ({query_str}) AS sub LIMIT {limit}"
            
#         with self.engine.connect() as conn:
#             result = conn.execute(text(query_str))
#             # Convert SQLAlchemy Rows to list of dicts
#             return [dict(row._mapping) for row in result]

#     def get_ticker_history(self, ticker):
#         """Fetches full history for a specific ticker."""
#         query = text("SELECT * FROM nse_stocks WHERE ticker = :ticker ORDER BY date ASC")
#         with self.engine.connect() as conn:
#             result = conn.execute(query, {"ticker": ticker})
#             return [dict(row._mapping) for row in result]

#     def store_engineered_features(self, ticker: str, df_engineered: pd.DataFrame):
#         """
#         Store engineered features in the engineered_features table with Schema Evolution.
#         Automatically adds missing columns to the table.
#         """
#         try:
#             if df_engineered.empty:
#                 logger.warning(f"Empty engineered features for {ticker}")
#                 return
            
#             # Prepare data
#             df_to_store = df_engineered.copy()
            
#             # Ensure date column is datetime and timezone-naive
#             if 'date' in df_to_store.columns:
#                 df_to_store['date'] = pd.to_datetime(df_to_store['date'])
#                 if hasattr(df_to_store['date'].dtype, 'tz') and df_to_store['date'].dt.tz is not None:
#                     df_to_store['date'] = df_to_store['date'].dt.tz_localize(None)
            
#             # Add metadata columns if missing
#             if 'ticker' not in df_to_store.columns:
#                 df_to_store['ticker'] = ticker
            
#             df_to_store['feature_count'] = len(df_to_store.columns)
#             df_to_store['updated_at'] = datetime.now()
            
#             # --- SCHEMA EVOLUTION ---
#             # 1. Get existing columns in DB
#             with self.engine.connect() as conn:
#                 # Get current table columns
#                 result = conn.execute(text("""
#                     SELECT column_name, data_type 
#                     FROM information_schema.columns 
#                     WHERE table_name = 'engineered_features'
#                 """))
#                 existing_cols = {row[0]: row[1] for row in result}
            
#             # 2. Identify missing columns in DF
#             df_cols = [c for c in df_to_store.columns if c not in existing_cols]
            
#             # 3. Add missing columns
#             if df_cols:
#                 logger.info(f"⚡ Schema Evolution: Adding {len(df_cols)} new columns to engineered_features")
#                 with self.engine.begin() as conn:
#                     for col in df_cols:
#                         # Map pandas types to SQL types
#                         dtype = df_to_store[col].dtype
#                         if pd.api.types.is_integer_dtype(dtype):
#                             sql_type = "BIGINT"
#                         elif pd.api.types.is_float_dtype(dtype):
#                             sql_type = "DOUBLE PRECISION"
#                         elif pd.api.types.is_datetime64_any_dtype(dtype):
#                             sql_type = "TIMESTAMP WITHOUT TIME ZONE"
#                         elif pd.api.types.is_bool_dtype(dtype):
#                             sql_type = "BOOLEAN"
#                         else:
#                             sql_type = "TEXT"
                            
#                         # Add column safe name
#                         conn.execute(text(f'ALTER TABLE engineered_features ADD COLUMN IF NOT EXISTS "{col}" {sql_type}'))
#                         # Update our local knowledge
#                         existing_cols[col] = sql_type

#             # --- DATA STORAGE ---
#             # Get valid columns again to be safe
#             valid_cols = list(existing_cols.keys())
#             cols_to_insert = [col for col in df_to_store.columns if col in valid_cols]
            
#             if not cols_to_insert:
#                 return

#             df_to_insert = df_to_store[cols_to_insert].copy()
            
#             # Handle boolean conversion for Postgres
#             for col in df_to_insert.columns:
#                 if df_to_insert[col].dtype == 'bool':
#                     df_to_insert[col] = df_to_insert[col].astype(bool)
            
#             raw_conn = self.engine.raw_connection()
#             try:
#                 cursor = raw_conn.cursor()
                
#                 # Create temp table
#                 cursor.execute("DROP TABLE IF EXISTS temp_ef_upload")
#                 cols_def = ', '.join([f'"{col}" TEXT' for col in cols_to_insert])
#                 cursor.execute(f"CREATE TEMP TABLE temp_ef_upload ({cols_def}) ON COMMIT DROP")
                
#                 # COPY data
#                 csv_buffer = io.StringIO()
#                 df_to_insert.to_csv(csv_buffer, sep='\t', header=False, index=False, na_rep='', quoting=csv.QUOTE_NONE)
#                 csv_buffer.seek(0)
                
#                 cols_names = ', '.join([f'"{col}"' for col in cols_to_insert])
#                 cursor.copy_expert(f"COPY temp_ef_upload ({cols_names}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t')", csv_buffer)
                
#                 # Generate SET clause for UPDATE
#                 # We exclude primary keys (ticker, date) and created_at from update
#                 update_cols = [c for c in cols_to_insert if c not in ('ticker', 'date', 'created_at')]
#                 set_clause = ', '.join([f'"{col}" = CAST(EXCLUDED."{col}" AS {existing_cols.get(col, "TEXT")})' for col in update_cols])
                
#                 # Build casting for SELECT
#                 select_casts = []
#                 for col in cols_to_insert:
#                     sql_type = existing_cols.get(col, "TEXT")
#                     select_casts.append(f'CAST("{col}" AS {sql_type})')
#                 select_clause = ', '.join(select_casts)

#                 # INSERT ... ON CONFLICT DO UPDATE
#                 query = f"""
#                     INSERT INTO engineered_features ({cols_names})
#                     SELECT {select_clause} FROM temp_ef_upload
#                     ON CONFLICT (ticker, date) 
#                     DO UPDATE SET
#                         {set_clause},
#                         updated_at = CURRENT_TIMESTAMP
#                 """
#                 cursor.execute(query)
                
#                 raw_conn.commit()
#                 logger.info(f"✅ Stored {len(df_to_insert)} rows of features for {ticker}")
                
#             except Exception as e:
#                 raw_conn.rollback()
#                 logger.error(f"Failed to copy features: {e}")
#                 raise
#             finally:
#                 cursor.close()
#                 raw_conn.close()

#         except Exception as e:
#             logger.error(f"Error storing engineered features for {ticker}: {e}")
#             raise
#     # ------------------------------------

#     def get_all_nse_symbols(self) -> List[str]:
#         """Fetch NSE symbol list with retry logic"""
#         logger.info("Fetching NSE symbol list...")
#         for attempt in range(Config.MAX_RETRIES):
#             try:
#                 response = self.session.get(
#                     Config.NSE_LIST_URL, 
#                     timeout=Config.REQUEST_TIMEOUT
#                 )
#                 response.raise_for_status()
#                 df = pd.read_csv(io.StringIO(response.text))
#                 df.columns = [c.strip() for c in df.columns]
                
#                 # Upsert Metadata
#                 metadata_df = df[['SYMBOL', 'NAME OF COMPANY', 'ISIN NUMBER']].copy()
#                 metadata_df.columns = ['ticker', 'company_name', 'isin']
#                 metadata_df = metadata_df[metadata_df['ticker'].str.len() > 0]
#                 metadata_df = metadata_df.drop_duplicates(subset=['ticker'])
                
#                 with self.engine.begin() as conn:
#                     for _, row in metadata_df.iterrows():
#                         conn.execute(text("""
#                             INSERT INTO stock_metadata (ticker, company_name, isin, last_updated)
#                             VALUES (:t, :c, :i, CURRENT_TIMESTAMP)
#                             ON CONFLICT (ticker) DO UPDATE SET 
#                                 company_name = EXCLUDED.company_name,
#                                 isin = EXCLUDED.isin,
#                                 is_active = TRUE,
#                                 last_updated = CURRENT_TIMESTAMP
#                         """), {'t': row['ticker'], 'c': row['company_name'], 'i': row['isin']})
                
#                 symbols = [f"{s}.NS" for s in metadata_df['ticker'].unique()]
#                 logger.info(f"Found {len(symbols)} active NSE symbols")
#                 return symbols
                
#             except Exception as e:
#                 logger.warning(f"Attempt {attempt + 1}/{Config.MAX_RETRIES} failed: {e}")
#                 if attempt < Config.MAX_RETRIES - 1:
#                     time.sleep(2 ** attempt)
#                 else:
#                     logger.error(f"Failed to fetch NSE list after {Config.MAX_RETRIES} attempts")
#                     return []

#     def get_ticker_date_ranges(self, tickers: List[str]) -> Dict[str, datetime]:
#         """Get last fetch date for each ticker"""
#         clean_tickers = [t.replace('.NS', '') for t in tickers]
#         ticker_map = {}
        
#         with self.engine.connect() as conn:
#             query = text("""
#                 SELECT ticker, MAX(date) as last_date
#                 FROM nse_stocks
#                 WHERE ticker = ANY(:tickers)
#                 GROUP BY ticker
#             """)
#             result = conn.execute(query, {'tickers': clean_tickers})
#             for row in result:
#                 if row.last_date:
#                     ticker_map[row.ticker] = row.last_date
        
#         logger.info(f"Found existing data for {len(ticker_map)} tickers")
#         return ticker_map

#     def download_batch(self, batch_tickers: List[str], period: str = None, 
#                       start=None, end=None) -> pd.DataFrame:
#         """Download stock data with improved error handling"""
#         try:
#             time.sleep(Config.RATE_LIMIT_DELAY)
            
#             # auto_adjust=False ensures we get BOTH Close and Adj Close columns.
#             if start and end:
#                 data = yf.download(
#                     batch_tickers, start=start, end=end, interval='1d', 
#                     progress=False, group_by='ticker', auto_adjust=False, 
#                     threads=False, repair=True, actions=True 
#                 )
#             else:
#                 p = period if period else '5y'
#                 data = yf.download(
#                     batch_tickers, period=p, interval='1d', 
#                     progress=False, group_by='ticker', auto_adjust=False, 
#                     threads=False, repair=True, actions=True 
#                 )

#             if data.empty:
#                 return pd.DataFrame()

#             # Handle MultiIndex columns
#             if isinstance(data.columns, pd.MultiIndex):
#                 data = data.stack(level=0, future_stack=True)
#                 data.index.names = ['Date', 'ticker']
#                 data = data.reset_index()
#             else:
#                 data = data.reset_index()
#                 if len(batch_tickers) == 1:
#                     data['ticker'] = batch_tickers[0]

#             return data
            
#         except Exception as e:
#             error_msg = str(e)
#             if "No data found" not in error_msg and "No timezone found" not in error_msg:
#                 logger.warning(f"Batch download issue: {error_msg[:100]}")
#             return pd.DataFrame()

#     def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Process and validate dataframe with robust error handling"""
#         if df.empty: 
#             return df
        
#         try:
#             # Standardize columns
#             df.columns = [str(c).lower().strip() for c in df.columns]
            
#             rename_map = {
#                 'date': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 
#                 'close': 'close', 'adj close': 'adj_close', 'volume': 'volume', 
#                 'ticker': 'ticker', 'dividends': 'dividends', 'stock splits': 'stock_splits'
#             }
#             df = df.rename(columns=rename_map)
            
#             # Clean Ticker
#             df['ticker'] = df['ticker'].astype(str).str.replace('.NS', '', regex=False).str.strip()
            
#             # Handle Date with timezone awareness
#             if df['date'].dtype == 'object':
#                 df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
#             # Remove timezone if present
#             if hasattr(df['date'].dtype, 'tz') and df['date'].dt.tz is not None:
#                 df['date'] = df['date'].dt.tz_localize(None)
#             elif df['date'].dtype != 'datetime64[ns]':
#                 df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
#             # Remove rows with invalid dates
#             df = df.dropna(subset=['date'])
            
#             if df.empty:
#                 return df
            
#             # Numeric conversion for price columns
#             price_cols = ['open', 'high', 'low', 'close', 'adj_close']
#             for col in price_cols:
#                 if col in df.columns:
#                     df[col] = pd.to_numeric(df[col], errors='coerce')
#                     df.loc[df[col] < 0, col] = np.nan
            
#             # If adj_close is missing, copy from close
#             if 'adj_close' in df.columns and 'close' in df.columns:
#                 close_adj_identical = (df['close'] == df['adj_close']).all()
#                 if close_adj_identical:
#                     logger.debug(f"Note: Close and Adj Close are identical for {df['ticker'].iloc[0] if len(df) > 0 else 'unknown'}")
            
#             if 'adj_close' not in df.columns:
#                 logger.warning("adj_close column missing! Using close as fallback")
#                 df['adj_close'] = df['close']

#             # Integer columns
#             int_cols = ['volume', 'delivery_qty', 'traded_qty']
#             for col in int_cols:
#                 if col not in df.columns:
#                     df[col] = 0
#                 else:
#                     df[col] = pd.to_numeric(df[col], errors='coerce')
#                     df[col] = df[col].replace([np.inf, -np.inf], np.nan)
#                     df[col] = df[col].fillna(0)
#                     df[col] = df[col].round(0)
#                     df[col] = df[col].astype('int64')

#             # Calculate Split Factor using Close/Adj Close ratio
#             if 'close' in df.columns and 'adj_close' in df.columns:
#                 with np.errstate(divide='ignore', invalid='ignore'):
#                     df['split_factor'] = np.where(
#                         (df['adj_close'] > 0) & (df['close'] > 0) & 
#                         np.isfinite(df['adj_close']) & np.isfinite(df['close']),
#                         (df['close'] / df['adj_close']).round(6),
#                         1.0
#                     )
#                 df.loc[df['split_factor'] <= 0, 'split_factor'] = 1.0
#                 df.loc[df['split_factor'] > 1000, 'split_factor'] = 1.0
#                 df.loc[~np.isfinite(df['split_factor']), 'split_factor'] = 1.0
#             else:
#                 df['split_factor'] = 1.0

#             # Add missing columns
#             if 'delivery_percentage' not in df.columns:
#                 df['delivery_percentage'] = 0.0

#             # Data quality validation
#             df = df[
#                 (df['close'] > 0) &
#                 np.isfinite(df['close']) &
#                 (df['high'] >= df['low']) &
#                 (df['high'] >= df['close']) &
#                 (df['high'] >= df['open']) &
#                 (df['low'] <= df['close']) &
#                 (df['low'] <= df['open'])
#             ]
            
#             # Remove duplicates
#             df = df.drop_duplicates(subset=['ticker', 'date'], keep='last')
            
#             required_cols = ['date', 'ticker', 'open', 'high', 'low', 'close', 
#                             'adj_close', 'volume', 'split_factor', 'delivery_qty', 
#                             'delivery_percentage', 'traded_qty']
            
#             df['updated_at'] = datetime.now()
            
#             return df[required_cols + ['updated_at']]
            
#         except Exception as e:
#             logger.error(f"Error processing dataframe: {e}")
#             return pd.DataFrame()

#     def fast_bulk_upsert(self, df: pd.DataFrame):
#         """Optimized bulk upsert"""
#         if df.empty: 
#             return

#         output = io.StringIO()
#         df.to_csv(output, sep='\t', header=False, index=False, na_rep='\\N', 
#                  quoting=csv.QUOTE_NONE, escapechar='\\')
#         output.seek(0)

#         raw_conn = self.engine.raw_connection()
#         try:
#             cursor = raw_conn.cursor()
            
#             cursor.execute("DROP TABLE IF EXISTS temp_stock_upload")
#             cursor.execute("""
#                 CREATE TEMP TABLE temp_stock_upload (
#                     date TIMESTAMP, ticker VARCHAR, open FLOAT, high FLOAT, low FLOAT, 
#                     close FLOAT, adj_close FLOAT, volume BIGINT, split_factor FLOAT, 
#                     delivery_qty BIGINT, delivery_percentage FLOAT, traded_qty BIGINT,
#                     updated_at TIMESTAMP
#                 ) ON COMMIT DROP
#             """)
            
#             cursor.copy_expert(
#                 "COPY temp_stock_upload FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')", 
#                 output
#             )
            
#             cursor.execute("""
#                 INSERT INTO nse_stocks (
#                     date, ticker, open, high, low, close, adj_close, volume, 
#                     split_factor, delivery_qty, delivery_percentage, traded_qty, updated_at
#                 )
#                 SELECT * FROM temp_stock_upload
#                 ON CONFLICT (ticker, date) DO UPDATE SET
#                     open = EXCLUDED.open,
#                     high = EXCLUDED.high,
#                     low = EXCLUDED.low,
#                     close = EXCLUDED.close,
#                     adj_close = EXCLUDED.adj_close,
#                     volume = EXCLUDED.volume,
#                     split_factor = EXCLUDED.split_factor,
#                     delivery_qty = EXCLUDED.delivery_qty,
#                     delivery_percentage = EXCLUDED.delivery_percentage,
#                     traded_qty = EXCLUDED.traded_qty,
#                     updated_at = CURRENT_TIMESTAMP;
#             """)
            
#             # Update metadata (compatible with existing schema)
#             cursor.execute("""
#                 INSERT INTO stock_metadata (ticker, last_fetched_date, last_updated)
#                 SELECT ticker, MAX(date)::date, CURRENT_TIMESTAMP
#                 FROM temp_stock_upload
#                 GROUP BY ticker
#                 ON CONFLICT (ticker) DO UPDATE SET
#                     last_fetched_date = EXCLUDED.last_fetched_date,
#                     last_updated = CURRENT_TIMESTAMP;
#             """)
            
#             raw_conn.commit()
#             rows_inserted = len(df)
#             self.success_count += rows_inserted
            
#         except Exception as e:
#             raw_conn.rollback()
#             self.error_count += 1
#             logger.error(f"Bulk insert failed: {e}")
#             raise
#         finally:
#             cursor.close()
#             raw_conn.close()

#     def run_pipeline(self, symbols: List[str], force_full_refresh: bool = False):
#         """Main pipeline with progress tracking"""
#         logger.info(f"🚀 Starting pipeline for {len(symbols)} symbols")
        
#         last_dates = self.get_ticker_date_ranges(symbols)
#         today = datetime.now()
        
#         full_download_tickers = []
#         incremental_tickers = []
        
#         for sym in symbols:
#             clean_sym = sym.replace('.NS', '')
            
#             if force_full_refresh or clean_sym not in last_dates:
#                 full_download_tickers.append(sym)
#             else:
#                 last_date = last_dates[clean_sym]
#                 days_since_update = (today - last_date).days
                
#                 if days_since_update > 1:
#                     incremental_tickers.append(sym)
        
#         tasks = []
        
#         # Full Downloads
#         for i in range(0, len(full_download_tickers), Config.CHUNK_SIZE):
#             batch = full_download_tickers[i:i + Config.CHUNK_SIZE]
#             tasks.append({
#                 'tickers': batch, 
#                 'period': '5y', 
#                 'start': None, 
#                 'end': None
#             })
            
#         # Incremental Downloads
#         if incremental_tickers:
#             start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
#             for i in range(0, len(incremental_tickers), Config.CHUNK_SIZE):
#                 batch = incremental_tickers[i:i + Config.CHUNK_SIZE]
#                 tasks.append({
#                     'tickers': batch, 
#                     'period': None, 
#                     'start': start_date, 
#                     'end': today.strftime('%Y-%m-%d')
#                 })

#         logger.info(f"📊 Processing: {len(full_download_tickers)} Full | {len(incremental_tickers)} Incremental | {len(tasks)} batches")
        
#         with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
#             future_to_batch = {
#                 executor.submit(
#                     self.download_batch, 
#                     t['tickers'], 
#                     t['period'], 
#                     t['start'], 
#                     t['end']
#                 ): t for t in tasks
#             }
            
#             for future in tqdm(as_completed(future_to_batch), total=len(tasks), 
#                              desc="📥 Downloading & Storing", unit="batch"):
#                 try:
#                     raw_df = future.result(timeout=120)
#                     if not raw_df.empty:
#                         clean_df = self.process_dataframe(raw_df)
#                         if not clean_df.empty:
#                             self.fast_bulk_upsert(clean_df)
#                 except Exception as e:
#                     batch_info = future_to_batch[future]
#                     logger.error(f"Worker failed: {str(e)[:100]}")
#                     self.failed_tickers.extend(batch_info['tickers'])

#         self.print_statistics()

#     def print_statistics(self):
#         """Print pipeline execution statistics"""
#         logger.info("=" * 60)
#         logger.info("📈 PIPELINE STATISTICS")
#         logger.info("=" * 60)
#         logger.info(f"✅ Successful operations: {self.success_count}")
#         logger.info(f"❌ Failed operations: {self.error_count}")
#         logger.info(f"⚠️  Failed tickers: {len(self.failed_tickers)}")
        
#         if self.failed_tickers:
#             failed_clean = [t.replace('.NS', '') for t in self.failed_tickers[:20]]
#             logger.warning(f"Failed tickers: {', '.join(failed_clean)}")
#             if len(self.failed_tickers) > 20:
#                 logger.warning(f"... and {len(self.failed_tickers) - 20} more")
        
#         try:
#             with self.engine.connect() as conn:
#                 result = conn.execute(text("""
#                     SELECT 
#                         COUNT(DISTINCT ticker) as total_stocks,
#                         COUNT(*) as total_records,
#                         MIN(date) as earliest_date,
#                         MAX(date) as latest_date
#                     FROM nse_stocks
#                 """))
#                 row = result.fetchone()
#                 if row:
#                     logger.info(f"📊 Database: {row.total_stocks} stocks, {row.total_records:,} records")
#                     logger.info(f"📅 Date range: {row.earliest_date} to {row.latest_date}")
#         except Exception as e:
#             logger.error(f"Failed to fetch statistics: {e}")
        
#         logger.info("=" * 60)

# if __name__ == "__main__":
#     start_time = time.time()
    
#     import argparse
#     parser = argparse.ArgumentParser(description='NSE Stock Data Pipeline')
#     parser.add_argument('--force-refresh', action='store_true', 
#                        help='Force full refresh of all stocks')
#     args = parser.parse_args()
    
#     pipeline = NSEDataPipeline()
#     symbols = pipeline.get_all_nse_symbols()
    
#     if symbols:
#         pipeline.run_pipeline(symbols, force_full_refresh=args.force_refresh)
#     else:
#         logger.error("No symbols found. Exiting.")
    
#     elapsed_time = time.time() - start_time
#     logger.info(f"🏁 Process completed in {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")









import yfinance as yf
import pandas as pd
import requests
import io
import time
import logging
import sys
import csv
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from tqdm import tqdm
import numpy as np
from typing import List, Optional, Dict, Tuple
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- WINDOWS CONSOLE FIX ---
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Taran%4017@localhost:5432/StockDB")

# --- CONFIGURATION ---
class Config:
    DB_URL = os.getenv("DB_URL", "postgresql://postgres:Taran%4017@localhost:5432/StockDB")
    NSE_LIST_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    
    CHUNK_SIZE = 50
    MAX_WORKERS = 4
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = (5, 10)  # (connect_timeout, read_timeout) in seconds
    
    DB_POOL_SIZE = 10
    DB_MAX_OVERFLOW = 20
    RATE_LIMIT_DELAY = 0.5
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.nseindia.com/',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
    }

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nse_pipeline.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class NSEDataPipeline:
    def __init__(self, db_url: str = Config.DB_URL):
        self.engine = create_engine(
            db_url, 
            pool_pre_ping=True, 
            pool_size=Config.DB_POOL_SIZE, 
            max_overflow=Config.DB_MAX_OVERFLOW,
            pool_recycle=3600
        )
        self.session = requests.Session()
        self.session.headers.update(Config.HEADERS)
        self.init_database()
        self.failed_tickers = []
        self.success_count = 0
        self.error_count = 0
        logger.info("NSE Data Pipeline initialized")

    def init_database(self):
        """Initialize database schema"""
        with self.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            
            # Main table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS nse_stocks (
                    date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    ticker VARCHAR(20) NOT NULL,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    adj_close DOUBLE PRECISION,
                    volume BIGINT,
                    split_factor DOUBLE PRECISION DEFAULT 1.0,
                    delivery_qty BIGINT DEFAULT 0,
                    delivery_percentage DOUBLE PRECISION DEFAULT 0.0,
                    traded_qty BIGINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (ticker, date)
                );
            """))
            
            # Hypertable
            try:
                conn.execute(text("""
                    SELECT create_hypertable('nse_stocks', 'date', 
                        if_not_exists => TRUE,
                        chunk_time_interval => INTERVAL '1 month');
                """))
            except Exception:
                pass 

            # Stock Metadata
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS stock_metadata (
                    ticker VARCHAR(20) PRIMARY KEY,
                    company_name VARCHAR(200),
                    isin VARCHAR(20),
                    last_fetched_date DATE,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            
            # Engineered Features Table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS engineered_features (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                    open DOUBLE PRECISION,
                    high DOUBLE PRECISION,
                    low DOUBLE PRECISION,
                    close DOUBLE PRECISION,
                    adj_close DOUBLE PRECISION,
                    volume BIGINT,
                    returns DOUBLE PRECISION,
                    log_returns DOUBLE PRECISION,
                    rsi_7 DOUBLE PRECISION,
                    rsi_14 DOUBLE PRECISION,
                    rsi_21 DOUBLE PRECISION,
                    macd DOUBLE PRECISION,
                    macd_signal DOUBLE PRECISION,
                    macd_histogram DOUBLE PRECISION,
                    bb_upper DOUBLE PRECISION,
                    bb_middle DOUBLE PRECISION,
                    bb_lower DOUBLE PRECISION,
                    bb_width DOUBLE PRECISION,
                    bb_position DOUBLE PRECISION,
                    atr_14 DOUBLE PRECISION,
                    volatility_2 DOUBLE PRECISION,
                    sma_5 DOUBLE PRECISION,
                    sma_10 DOUBLE PRECISION,
                    sma_20 DOUBLE PRECISION,
                    sma_50 DOUBLE PRECISION,
                    sma_100 DOUBLE PRECISION,
                    sma_200 DOUBLE PRECISION,
                    ema_5 DOUBLE PRECISION,
                    ema_10 DOUBLE PRECISION,
                    ema_12 DOUBLE PRECISION,
                    ema_20 DOUBLE PRECISION,
                    ema_50 DOUBLE PRECISION,
                    ema_100 DOUBLE PRECISION,
                    ema_200 DOUBLE PRECISION,
                    adx DOUBLE PRECISION,
                    stochastic_k DOUBLE PRECISION,
                    stochastic_d DOUBLE PRECISION,
                    cci DOUBLE PRECISION,
                    williams_r DOUBLE PRECISION,
                    obv DOUBLE PRECISION,
                    obv_ema DOUBLE PRECISION,
                    pattern_head_shoulders BOOLEAN,
                    pattern_double_top BOOLEAN,
                    pattern_double_bottom BOOLEAN,
                    pattern_triangle BOOLEAN,
                    pattern_flag BOOLEAN,
                    support_level DOUBLE PRECISION,
                    resistance_level DOUBLE PRECISION,
                    trend_channel DOUBLE PRECISION,
                    volume_sentiment DOUBLE PRECISION,
                    liquidity_score DOUBLE PRECISION,
                    strength_score DOUBLE PRECISION,
                    signal_strength DOUBLE PRECISION,
                    future_return_5d DOUBLE PRECISION,
                    future_direction_5d INTEGER,
                    feature_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (ticker, date)
                );
            """))
            
            # Add indexes for performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_nse_stocks_ticker_date 
                ON nse_stocks(ticker, date DESC);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_nse_stocks_date 
                ON nse_stocks(date DESC);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_engineered_features_ticker_date 
                ON engineered_features(ticker, date DESC);
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_engineered_features_ticker 
                ON engineered_features(ticker);
            """))

    # --- METHODS REQUIRED BY SCREENER ---
    def get_latest_data(self, limit=None):
        """Fetches the most recent record for every unique ticker."""
        # DISTINCT ON (ticker) ensures we get one row per stock (the latest one)
        query_str = """
            SELECT DISTINCT ON (ticker) * FROM nse_stocks 
            ORDER BY ticker, date DESC
        """
        if limit:
            query_str = f"SELECT * FROM ({query_str}) AS sub LIMIT {limit}"
            
        with self.engine.connect() as conn:
            result = conn.execute(text(query_str))
            # Convert SQLAlchemy Rows to list of dicts
            return [dict(row._mapping) for row in result]

    def get_ticker_history(self, ticker):
        """Fetches full history for a specific ticker."""
        query = text("SELECT * FROM nse_stocks WHERE ticker = :ticker ORDER BY date ASC")
        with self.engine.connect() as conn:
            result = conn.execute(query, {"ticker": ticker})
            return [dict(row._mapping) for row in result]

    def _detect_trading_gaps(self, df: pd.DataFrame) -> Dict[str, List]:
        """Detect gaps in trading data for each ticker"""
        gaps = {}
        
        if df.empty or 'ticker' not in df.columns or 'date' not in df.columns:
            return gaps
        
        for ticker in df['ticker'].unique():
            ticker_data = df[df['ticker'] == ticker].copy().sort_values('date')
            
            if len(ticker_data) < 2:
                continue
            
            # Calculate gaps between consecutive dates
            date_diffs = ticker_data['date'].diff().dt.days
            
            # Normal gaps should be 1-3 days (weekends/holidays)
            # Gaps > 3 days might indicate missing data
            large_gaps = date_diffs[date_diffs > 3]
            
            if not large_gaps.empty:
                gap_dates = ticker_data.loc[large_gaps.index, 'date'].tolist()
                gaps[ticker] = gap_dates
                if len(gap_dates) <= 5:
                    logger.info(f"ℹ️  Trading gap(s) detected for {ticker}: {len(gap_dates)} gap(s)")
        
        return gaps

    def _get_data_quality_metrics(self, df: pd.DataFrame, ticker: str = None) -> Dict:
        """Generate data quality metrics"""
        metrics = {
            'total_records': len(df),
            'unique_tickers': df['ticker'].nunique() if 'ticker' in df.columns else 0,
            'date_range': None,
            'null_counts': {},
            'outliers_detected': 0,
            'validation_status': 'PASS',
            'warnings': []
        }
        
        if df.empty:
            metrics['validation_status'] = 'FAIL'
            metrics['warnings'].append('Empty dataframe')
            return metrics
        
        if 'date' in df.columns:
            metrics['date_range'] = {
                'start': str(df['date'].min()),
                'end': str(df['date'].max())
            }
        
        # Check for nulls
        for col in ['open', 'high', 'low', 'close', 'adj_close', 'volume']:
            if col in df.columns:
                null_count = df[col].isna().sum()
                if null_count > 0:
                    metrics['null_counts'][col] = null_count
                    if null_count > len(df) * 0.1:  # > 10% nulls
                        metrics['validation_status'] = 'WARNING'
                        metrics['warnings'].append(f'{col}: {null_count} null values ({null_count/len(df)*100:.1f}%)')
        
        # Detect outliers in close price
        if 'close' in df.columns and len(df) > 10:
            close_pct_change = df['close'].pct_change().abs()
            outliers = (close_pct_change > 0.30).sum()  # > 30% change
            metrics['outliers_detected'] = int(outliers)
            if outliers > 0:
                metrics['validation_status'] = 'WARNING'
                metrics['warnings'].append(f'Detected {outliers} extreme price movements (>30%)')
        
        return metrics

    def get_data_quality_report(self, limit_tickers: int = None) -> Dict:
        """Generate comprehensive data quality report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'HEALTHY',
            'total_records': 0,
            'total_tickers': 0,
            'warnings': [],
            'ticker_status': []
        }
        
        try:
            with self.engine.connect() as conn:
                # Get overall stats
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_records,
                        COUNT(DISTINCT ticker) as total_tickers,
                        COUNT(DISTINCT DATE(date)) as trading_days,
                        MIN(date) as earliest_date,
                        MAX(date) as latest_date,
                        SUM(CASE WHEN close IS NULL OR close <= 0 THEN 1 ELSE 0 END) as invalid_closes,
                        SUM(CASE WHEN volume IS NULL OR volume < 0 THEN 1 ELSE 0 END) as invalid_volumes
                    FROM nse_stocks
                """))
                
                row = result.fetchone()
                if row:
                    report['total_records'] = row.total_records
                    report['total_tickers'] = row.total_tickers
                    report['trading_days'] = row.trading_days
                    report['date_range'] = {
                        'start': str(row.earliest_date),
                        'end': str(row.latest_date)
                    }
                    
                    if row.invalid_closes > 0:
                        report['overall_status'] = 'WARNING'
                        report['warnings'].append(f'Found {row.invalid_closes} invalid close prices')
                    
                    if row.invalid_volumes > 0:
                        report['overall_status'] = 'WARNING'
                        report['warnings'].append(f'Found {row.invalid_volumes} invalid volumes')
                
                # Get per-ticker stats
                ticker_query = text("""
                    SELECT 
                        ticker,
                        COUNT(*) as record_count,
                        MIN(date) as first_date,
                        MAX(date) as last_date,
                        ROUND(AVG(close), 2) as avg_price,
                        ROUND(AVG(volume), 0) as avg_volume,
                        COUNT(DISTINCT DATE(date)) as trading_days,
                        SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) as null_closes,
                        SUM(CASE WHEN volume = 0 THEN 1 ELSE 0 END) as zero_volumes
                    FROM nse_stocks
                    GROUP BY ticker
                    ORDER BY record_count DESC
                """)
                
                if limit_tickers:
                    ticker_query = text(f"""
                        SELECT 
                            ticker,
                            COUNT(*) as record_count,
                            MIN(date) as first_date,
                            MAX(date) as last_date,
                            ROUND(AVG(close), 2) as avg_price,
                            ROUND(AVG(volume), 0) as avg_volume,
                            COUNT(DISTINCT DATE(date)) as trading_days,
                            SUM(CASE WHEN close IS NULL THEN 1 ELSE 0 END) as null_closes,
                            SUM(CASE WHEN volume = 0 THEN 1 ELSE 0 END) as zero_volumes
                        FROM nse_stocks
                        GROUP BY ticker
                        ORDER BY record_count DESC
                        LIMIT {limit_tickers}
                    """)
                
                result = conn.execute(ticker_query)
                for row in result:
                    ticker_info = {
                        'ticker': row.ticker,
                        'records': row.record_count,
                        'date_range': f"{row.first_date} to {row.last_date}",
                        'avg_price': row.avg_price,
                        'avg_volume': int(row.avg_volume),
                        'trading_days': row.trading_days,
                        'quality_issues': []
                    }
                    
                    if row.null_closes > 0:
                        ticker_info['quality_issues'].append(f'{row.null_closes} null closes')
                    if row.zero_volumes > 0:
                        ticker_info['quality_issues'].append(f'{row.zero_volumes} zero volumes')
                    
                    report['ticker_status'].append(ticker_info)
        
        except Exception as e:
            logger.error(f"Failed to generate data quality report: {e}")
            report['overall_status'] = 'ERROR'
            report['warnings'].append(str(e))
        
        return report

    def reconcile_data(self, ticker: str = None) -> Dict:
        """Reconcile and fix data quality issues"""
        reconciliation_report = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'issues_found': 0,
            'issues_fixed': 0,
            'details': []
        }
        
        try:
            with self.engine.begin() as conn:
                if ticker:
                    # Reconcile specific ticker
                    query = text("""
                        SELECT ticker, date, open, high, low, close, adj_close, volume
                        FROM nse_stocks
                        WHERE ticker = :ticker
                        ORDER BY date
                    """)
                    result = conn.execute(query, {'ticker': ticker})
                else:
                    # Check for duplicate records
                    dup_query = text("""
                        SELECT ticker, date, COUNT(*) as cnt
                        FROM nse_stocks
                        GROUP BY ticker, date
                        HAVING COUNT(*) > 1
                    """)
                    result = conn.execute(dup_query)
                    dups = list(result)
                    
                    if dups:
                        reconciliation_report['issues_found'] = len(dups)
                        reconciliation_report['details'].append(f"Found {len(dups)} duplicate records")
                        
                        # Remove duplicates (keep latest)
                        for dup in dups[:10]:  # Fix first 10
                            delete_query = text("""
                                DELETE FROM nse_stocks
                                WHERE ticker = :ticker AND date = :date AND
                                      ctid NOT IN (SELECT ctid FROM nse_stocks 
                                                   WHERE ticker = :ticker AND date = :date
                                                   ORDER BY updated_at DESC LIMIT 1)
                            """)
                            conn.execute(delete_query, {'ticker': dup.ticker, 'date': dup.date})
                            reconciliation_report['issues_fixed'] += 1
                
                # Check for null prices
                null_query = text("""
                    SELECT ticker, COUNT(*) as null_count
                    FROM nse_stocks
                    WHERE close IS NULL OR close <= 0
                    GROUP BY ticker
                """)
                result = conn.execute(null_query)
                null_records = list(result)
                
                if null_records:
                    for record in null_records[:5]:
                        reconciliation_report['details'].append(
                            f"Ticker {record.ticker}: {record.null_count} records with null/invalid close"
                        )
                        reconciliation_report['issues_found'] += record.null_count
                
                # Check data consistency
                consistency_query = text("""
                    SELECT ticker, COUNT(*) as inconsistent_count
                    FROM nse_stocks
                    WHERE high < low OR high < close OR low > close
                    GROUP BY ticker
                """)
                result = conn.execute(consistency_query)
                consistency_issues = list(result)
                
                if consistency_issues:
                    for issue in consistency_issues[:5]:
                        reconciliation_report['details'].append(
                            f"Ticker {issue.ticker}: {issue.inconsistent_count} OHLC consistency issues"
                        )
                        reconciliation_report['issues_found'] += issue.inconsistent_count
                        
                        # Fix consistency issues
                        fix_query = text("""
                            UPDATE nse_stocks
                            SET high = GREATEST(open, high, low, close),
                                low = LEAST(open, high, low, close)
                            WHERE ticker = :ticker AND (high < low OR high < close OR low > close)
                        """)
                        conn.execute(fix_query, {'ticker': issue.ticker})
                        reconciliation_report['issues_fixed'] += issue.inconsistent_count
        
        except Exception as e:
            logger.error(f"Data reconciliation error: {e}")
            reconciliation_report['error'] = str(e)
        
        return reconciliation_report

    def store_engineered_features(self, ticker: str, df_engineered: pd.DataFrame):
        """
        Store engineered features in the engineered_features table with Schema Evolution.
        Automatically adds missing columns to the table.
        """
        try:
            if df_engineered.empty:
                logger.warning(f"Empty engineered features for {ticker}")
                return
            
            # Prepare data
            df_to_store = df_engineered.copy()
            
            # Ensure date column is datetime and timezone-naive
            if 'date' in df_to_store.columns:
                df_to_store['date'] = pd.to_datetime(df_to_store['date'])
                if hasattr(df_to_store['date'].dtype, 'tz') and df_to_store['date'].dt.tz is not None:
                    df_to_store['date'] = df_to_store['date'].dt.tz_localize(None)
            
            # Add metadata columns if missing
            if 'ticker' not in df_to_store.columns:
                df_to_store['ticker'] = ticker
            
            df_to_store['feature_count'] = len(df_to_store.columns)
            df_to_store['updated_at'] = datetime.now()
            
            # --- SCHEMA EVOLUTION ---
            # 1. Get existing columns in DB
            with self.engine.connect() as conn:
                # Get current table columns
                result = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'engineered_features'
                """))
                existing_cols = {row[0]: row[1] for row in result}
            
            # 2. Identify missing columns in DF
            df_cols = [c for c in df_to_store.columns if c not in existing_cols]
            
            # 3. Add missing columns
            if df_cols:
                logger.info(f"⚡ Schema Evolution: Adding {len(df_cols)} new columns to engineered_features")
                with self.engine.begin() as conn:
                    for col in df_cols:
                        # Map pandas types to SQL types
                        dtype = df_to_store[col].dtype
                        if pd.api.types.is_integer_dtype(dtype):
                            sql_type = "BIGINT"
                        elif pd.api.types.is_float_dtype(dtype):
                            sql_type = "DOUBLE PRECISION"
                        elif pd.api.types.is_datetime64_any_dtype(dtype):
                            sql_type = "TIMESTAMP WITHOUT TIME ZONE"
                        elif pd.api.types.is_bool_dtype(dtype):
                            sql_type = "BOOLEAN"
                        else:
                            sql_type = "TEXT"
                            
                        # Add column safe name
                        conn.execute(text(f'ALTER TABLE engineered_features ADD COLUMN IF NOT EXISTS "{col}" {sql_type}'))
                        # Update our local knowledge
                        existing_cols[col] = sql_type

            # --- DATA STORAGE ---
            # Get valid columns again to be safe
            valid_cols = list(existing_cols.keys())
            cols_to_insert = [col for col in df_to_store.columns if col in valid_cols]
            
            if not cols_to_insert:
                return

            df_to_insert = df_to_store[cols_to_insert].copy()
            
            # Handle boolean conversion for Postgres
            for col in df_to_insert.columns:
                if df_to_insert[col].dtype == 'bool':
                    df_to_insert[col] = df_to_insert[col].astype(bool)
            
            raw_conn = self.engine.raw_connection()
            try:
                cursor = raw_conn.cursor()
                
                # Create temp table
                cursor.execute("DROP TABLE IF EXISTS temp_ef_upload")
                cols_def = ', '.join([f'"{col}" TEXT' for col in cols_to_insert])
                cursor.execute(f"CREATE TEMP TABLE temp_ef_upload ({cols_def}) ON COMMIT DROP")
                
                # COPY data
                csv_buffer = io.StringIO()
                df_to_insert.to_csv(csv_buffer, sep='\t', header=False, index=False, na_rep='', quoting=csv.QUOTE_NONE)
                csv_buffer.seek(0)
                
                cols_names = ', '.join([f'"{col}"' for col in cols_to_insert])
                cursor.copy_expert(f"COPY temp_ef_upload ({cols_names}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t')", csv_buffer)
                
                # Generate SET clause for UPDATE
                # We exclude primary keys (ticker, date) and created_at from update
                update_cols = [c for c in cols_to_insert if c not in ('ticker', 'date', 'created_at')]
                set_clause = ', '.join([f'"{col}" = CAST(EXCLUDED."{col}" AS {existing_cols.get(col, "TEXT")})' for col in update_cols])
                
                # Build casting for SELECT
                select_casts = []
                for col in cols_to_insert:
                    sql_type = existing_cols.get(col, "TEXT")
                    select_casts.append(f'CAST("{col}" AS {sql_type})')
                select_clause = ', '.join(select_casts)

                # INSERT ... ON CONFLICT DO UPDATE
                query = f"""
                    INSERT INTO engineered_features ({cols_names})
                    SELECT {select_clause} FROM temp_ef_upload
                    ON CONFLICT (ticker, date) 
                    DO UPDATE SET
                        {set_clause},
                        updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(query)
                
                raw_conn.commit()
                logger.info(f"✅ Stored {len(df_to_insert)} rows of features for {ticker}")
                
            except Exception as e:
                raw_conn.rollback()
                logger.error(f"Failed to copy features: {e}")
                raise
            finally:
                cursor.close()
                raw_conn.close()

        except Exception as e:
            logger.error(f"Error storing engineered features for {ticker}: {e}")
            raise
    # ------------------------------------

    def get_all_nse_symbols(self) -> List[str]:
        """Fetch NSE symbol list with retry logic"""
        logger.info("Fetching NSE symbol list...")
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = self.session.get(
                    Config.NSE_LIST_URL, 
                    timeout=Config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                df = pd.read_csv(io.StringIO(response.text))
                df.columns = [c.strip() for c in df.columns]
                
                # Upsert Metadata
                metadata_df = df[['SYMBOL', 'NAME OF COMPANY', 'ISIN NUMBER']].copy()
                metadata_df.columns = ['ticker', 'company_name', 'isin']
                metadata_df = metadata_df[metadata_df['ticker'].str.len() > 0]
                metadata_df = metadata_df.drop_duplicates(subset=['ticker'])
                
                with self.engine.begin() as conn:
                    for _, row in metadata_df.iterrows():
                        conn.execute(text("""
                            INSERT INTO stock_metadata (ticker, company_name, isin, last_updated)
                            VALUES (:t, :c, :i, CURRENT_TIMESTAMP)
                            ON CONFLICT (ticker) DO UPDATE SET 
                                company_name = EXCLUDED.company_name,
                                isin = EXCLUDED.isin,
                                is_active = TRUE,
                                last_updated = CURRENT_TIMESTAMP
                        """), {'t': row['ticker'], 'c': row['company_name'], 'i': row['isin']})
                
                symbols = [f"{s}.NS" for s in metadata_df['ticker'].unique()]
                logger.info(f"Found {len(symbols)} active NSE symbols")
                return symbols
                
            except KeyboardInterrupt:
                logger.warning("NSE fetch interrupted by user, falling back to database...")
                break
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{Config.MAX_RETRIES} failed: {e}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch NSE list after {Config.MAX_RETRIES} attempts")
        
        # --- DATABASE FALLBACK ---
        # If NSE website is unreachable/blocked, use existing tickers from database
        return self._get_symbols_from_db()

    def _get_symbols_from_db(self) -> List[str]:
        """Fallback: fetch existing tickers from nse_stocks table when NSE website is unreachable"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT DISTINCT ticker FROM nse_stocks WHERE ticker IS NOT NULL ORDER BY ticker"
                ))
                tickers = [f"{row[0]}.NS" for row in result]
                if tickers:
                    logger.info(f"Database fallback: loaded {len(tickers)} existing tickers")
                else:
                    logger.warning("No tickers found in database fallback - database may be empty")
                return tickers
        except Exception as e:
            logger.error(f"Database fallback also failed: {e}")
            return []

    def get_ticker_date_ranges(self, tickers: List[str]) -> Dict[str, datetime]:
        """Get last fetch date for each ticker"""
        clean_tickers = set(t.replace('.NS', '') for t in tickers if t)
        ticker_map = {}

        if not clean_tickers:
            logger.info("Found existing data for 0 tickers")
            return ticker_map

        try:
            with self.engine.connect() as conn:
                # Simple query with no parameterization - fetch all, filter in Python
                result = conn.execute(text(
                    "SELECT ticker, MAX(date) as last_date FROM nse_stocks GROUP BY ticker"
                ))
                for row in result:
                    if row.ticker in clean_tickers and row.last_date:
                        ticker_map[row.ticker] = row.last_date
        except Exception as e:
            logger.warning(f"Could not fetch ticker date ranges: {e}")
        
        logger.info(f"Found existing data for {len(ticker_map)} tickers")
        return ticker_map

    def download_batch(self, batch_tickers: List[str], period: str = None, 
                      start=None, end=None) -> pd.DataFrame:
        """Download stock data with improved error handling and validation"""
        try:
            time.sleep(Config.RATE_LIMIT_DELAY)
            
            # auto_adjust=False ensures we get BOTH Close and Adj Close columns.
            if start and end:
                data = yf.download(
                    batch_tickers, start=start, end=end, interval='1d', 
                    progress=False, group_by='ticker', auto_adjust=False, 
                    threads=False, repair=True, actions=True 
                )
            else:
                p = period if period else '5y'
                data = yf.download(
                    batch_tickers, period=p, interval='1d', 
                    progress=False, group_by='ticker', auto_adjust=False, 
                    threads=False, repair=True, actions=True 
                )

            if data.empty:
                logger.warning(f"No data returned for batch: {', '.join(batch_tickers)}")
                return pd.DataFrame()

            # ── FIX: numpy 2.x + yfinance compatibility ──
            # yfinance returns read-only numpy arrays causing
            # ValueError('output array is read-only') on operations.
            # Deep-copy the DataFrame to make all arrays writable.
            data = data.copy(deep=True)
            for col in data.columns:
                if hasattr(data[col].values, 'flags') and not data[col].values.flags.writeable:
                    data[col] = data[col].values.copy()

            # Handle MultiIndex columns
            if isinstance(data.columns, pd.MultiIndex):
                data = data.stack(level=0, future_stack=True)
                data.index.names = ['Date', 'ticker']
                data = data.reset_index()
            else:
                data = data.reset_index()
                if len(batch_tickers) == 1:
                    data['ticker'] = batch_tickers[0]

            # Second copy after reshaping to ensure all derived columns are writable
            data = data.copy(deep=True)

            logger.info(f"✓ Downloaded data for {data['ticker'].nunique() if 'ticker' in data.columns else 0} tickers")
            return data
            
        except Exception as e:
            error_msg = str(e)
            if "No data found" not in error_msg and "No timezone found" not in error_msg:
                logger.warning(f"Batch download issue: {error_msg[:100]}")
            return pd.DataFrame()

    def _validate_price_logic(self, df: pd.DataFrame) -> pd.DataFrame:
        """Advanced validation for price consistency and outliers"""
        if df.empty:
            return df
        
        before_count = len(df)
        
        # 1. Basic sanity checks
        df = df[
            (df['close'] > 0) &
            np.isfinite(df['close']) &
            (df['high'] >= df['low']) &
            (df['high'] >= df['close']) &
            (df['high'] >= df['open']) &
            (df['low'] <= df['close']) &
            (df['low'] <= df['open']) &
            (df['open'] > 0) &
            (df['high'] > 0) &
            (df['low'] > 0) &
            np.isfinite(df['open']) &
            np.isfinite(df['high']) &
            np.isfinite(df['low'])
        ].copy()
        
        # 2. Detect and handle extreme outliers (likely data errors)
        if len(df) > 0:
            for col in ['open', 'high', 'low', 'close']:
                if col in df.columns:
                    # Calculate rolling statistics per ticker
                    price_stats = df.groupby('ticker')[col].rolling(window=20, min_periods=5).std()
                    price_mean = df.groupby('ticker')[col].rolling(window=20, min_periods=5).mean()
                    
                    # Flag extreme outliers (> 5 std deviations)
                    df.loc[:, '_valid_' + col] = True
        
        if len(df) > 0:
            # 3. Detect impossible price gaps (stock split detection)
            df.loc[:, '_price_change'] = np.abs(df.groupby('ticker')['close'].pct_change()) * 100
            
            # Flag extreme price changes (> 30% single day) as potential splits
            suspicious_splits = df[df['_price_change'] > 30].copy()
            if not suspicious_splits.empty:
                for ticker in suspicious_splits['ticker'].unique():
                    logger.warning(f"⚠️  Potential stock split detection for {ticker} - large price movement detected")
            
            df = df.drop('_price_change', axis=1)
        
        removed = before_count - len(df)
        if removed > 0:
            logger.info(f"Removed {removed} invalid records due to price validation")
        
        return df

    def _validate_volume(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhanced volume validation"""
        if df.empty:
            return df
        
        before_count = len(df)
        
        # 1. Volume must be non-negative
        df['volume'] = df['volume'].clip(lower=0)
        
        # 2. Detect abnormal volume spikes (> 5x median)
        for ticker in df['ticker'].unique():
            ticker_data = df[df['ticker'] == ticker].copy()
            if len(ticker_data) > 20:
                median_vol = ticker_data['volume'].median()
                if median_vol > 0:
                    max_expected = median_vol * 5
                    spike_rows = ticker_data[ticker_data['volume'] > max_expected]
                    if not spike_rows.empty:
                        logger.debug(f"Volume spike(s) detected for {ticker}: {len(spike_rows)} records")
        
        # 3. Handle zero volume
        zero_vol_rows = len(df[df['volume'] == 0])
        if zero_vol_rows > 0:
            logger.warning(f"Found {zero_vol_rows} records with zero volume - keeping for completeness")
        
        return df

    def _validate_adj_close(self, df: pd.DataFrame) -> pd.DataFrame:
        """Improved adj_close handling"""
        if df.empty:
            return df
        
        if 'adj_close' not in df.columns or 'close' not in df.columns:
            return df
        
        # 1. Fill missing adj_close with close
        missing_adj = df[df['adj_close'].isna()]
        if not missing_adj.empty:
            logger.info(f"Filling {len(missing_adj)} missing adj_close values with close price")
            df.loc[df['adj_close'].isna(), 'adj_close'] = df.loc[df['adj_close'].isna(), 'close']
        
        # 2. Validate adj_close is not greater than high or less than low
        invalid_adj = df[(df['adj_close'] > df['high']) | (df['adj_close'] < df['low'])]
        if not invalid_adj.empty:
            logger.warning(f"Correcting {len(invalid_adj)} invalid adj_close values")
            df.loc[invalid_adj.index, 'adj_close'] = df.loc[invalid_adj.index, 'close']
        
        return df

    def _calculate_split_factor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate split factor with better handling"""
        if df.empty:
            return df
        
        if 'close' not in df.columns or 'adj_close' not in df.columns:
            df['split_factor'] = 1.0
            return df
        
        with np.errstate(divide='ignore', invalid='ignore'):
            df['split_factor'] = np.where(
                (df['adj_close'] > 0) & (df['close'] > 0) & 
                np.isfinite(df['adj_close']) & np.isfinite(df['close']),
                (df['close'] / df['adj_close']).round(6),
                1.0
            )
        
        # Validate split factor
        df.loc[df['split_factor'] <= 0, 'split_factor'] = 1.0
        df.loc[df['split_factor'] > 10, 'split_factor'] = 1.0  # Reduced threshold
        df.loc[~np.isfinite(df['split_factor']), 'split_factor'] = 1.0
        
        # Log significant splits
        significant_splits = df[(df['split_factor'] != 1.0) & (df['split_factor'] > 1.01)]
        if not significant_splits.empty:
            for ticker in significant_splits['ticker'].unique():
                splits = significant_splits[significant_splits['ticker'] == ticker]
                logger.info(f"Stock split adjustments found for {ticker}: {len(splits)} dates")
        
        return df

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and validate dataframe with enhanced error handling"""
        if df.empty: 
            return df
        
        try:
            # Standardize columns
            df.columns = [str(c).lower().strip() for c in df.columns]
            
            rename_map = {
                'date': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 
                'close': 'close', 'adj close': 'adj_close', 'volume': 'volume', 
                'ticker': 'ticker', 'dividends': 'dividends', 'stock splits': 'stock_splits'
            }
            df = df.rename(columns=rename_map)
            
            # Clean Ticker
            df['ticker'] = df['ticker'].astype(str).str.replace('.NS', '', regex=False).str.strip()
            
            # Handle Date with timezone awareness
            if df['date'].dtype == 'object':
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # Remove timezone if present
            if hasattr(df['date'].dtype, 'tz') and df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)
            elif df['date'].dtype != 'datetime64[ns]':
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # Remove rows with invalid dates
            df = df.dropna(subset=['date'])
            
            if df.empty:
                return df
            
            # Numeric conversion for price columns
            price_cols = ['open', 'high', 'low', 'close', 'adj_close']
            for col in price_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    # Keep negative values for now - will validate later
                    df.loc[df[col] < 0, col] = np.nan
            
            # Ensure adj_close exists
            if 'adj_close' not in df.columns or df['adj_close'].isna().all():
                if 'close' in df.columns:
                    logger.warning("adj_close column missing or all NaN! Using close as fallback")
                    df['adj_close'] = df['close']
                else:
                    logger.error("Neither adj_close nor close column found!")
                    return pd.DataFrame()

            # Integer columns
            int_cols = ['volume', 'delivery_qty', 'traded_qty']
            for col in int_cols:
                if col not in df.columns:
                    df[col] = 0
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].replace([np.inf, -np.inf], np.nan)
                    df[col] = df[col].fillna(0)
                    df[col] = df[col].round(0)
                    df[col] = df[col].astype('int64')

            # Add missing columns
            if 'delivery_percentage' not in df.columns:
                df['delivery_percentage'] = 0.0

            # --- ENHANCED VALIDATION PIPELINE ---
            # 1. Validate adj_close
            df = self._validate_adj_close(df)
            
            # 2. Calculate split factor
            df = self._calculate_split_factor(df)
            
            # 3. Validate price logic
            df = self._validate_price_logic(df)
            
            # 4. Validate volume
            df = self._validate_volume(df)
            
            # Remove duplicates (keep last occurrence)
            df = df.drop_duplicates(subset=['ticker', 'date'], keep='last')
            
            # Final data check
            if df.empty:
                logger.warning("All records filtered out during validation")
                return df
            
            required_cols = ['date', 'ticker', 'open', 'high', 'low', 'close', 
                            'adj_close', 'volume', 'split_factor', 'delivery_qty', 
                            'delivery_percentage', 'traded_qty']
            
            df['updated_at'] = datetime.now()
            
            # Log validation summary
            logger.info(f"✓ Processed {len(df)} valid records from yfinance")
            
            return df[required_cols + ['updated_at']]
            
        except Exception as e:
            logger.error(f"Error processing dataframe: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    def fast_bulk_upsert(self, df: pd.DataFrame):
        """Optimized bulk upsert"""
        if df.empty: 
            return

        output = io.StringIO()
        df.to_csv(output, sep='\t', header=False, index=False, na_rep='\\N', 
                 quoting=csv.QUOTE_NONE, escapechar='\\')
        output.seek(0)

        raw_conn = self.engine.raw_connection()
        try:
            cursor = raw_conn.cursor()
            
            cursor.execute("DROP TABLE IF EXISTS temp_stock_upload")
            cursor.execute("""
                CREATE TEMP TABLE temp_stock_upload (
                    date TIMESTAMP, ticker VARCHAR, open FLOAT, high FLOAT, low FLOAT, 
                    close FLOAT, adj_close FLOAT, volume BIGINT, split_factor FLOAT, 
                    delivery_qty BIGINT, delivery_percentage FLOAT, traded_qty BIGINT,
                    updated_at TIMESTAMP
                ) ON COMMIT DROP
            """)
            
            cursor.copy_expert(
                "COPY temp_stock_upload FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N')", 
                output
            )
            
            cursor.execute("""
                INSERT INTO nse_stocks (
                    date, ticker, open, high, low, close, adj_close, volume, 
                    split_factor, delivery_qty, delivery_percentage, traded_qty, updated_at
                )
                SELECT * FROM temp_stock_upload
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    adj_close = EXCLUDED.adj_close,
                    volume = EXCLUDED.volume,
                    split_factor = EXCLUDED.split_factor,
                    delivery_qty = EXCLUDED.delivery_qty,
                    delivery_percentage = EXCLUDED.delivery_percentage,
                    traded_qty = EXCLUDED.traded_qty,
                    updated_at = CURRENT_TIMESTAMP;
            """)
            
            # Update metadata (compatible with existing schema)
            cursor.execute("""
                INSERT INTO stock_metadata (ticker, last_fetched_date, last_updated)
                SELECT ticker, MAX(date)::date, CURRENT_TIMESTAMP
                FROM temp_stock_upload
                GROUP BY ticker
                ON CONFLICT (ticker) DO UPDATE SET
                    last_fetched_date = EXCLUDED.last_fetched_date,
                    last_updated = CURRENT_TIMESTAMP;
            """)
            
            raw_conn.commit()
            rows_inserted = len(df)
            self.success_count += rows_inserted
            
        except Exception as e:
            raw_conn.rollback()
            self.error_count += 1
            logger.error(f"Bulk insert failed: {e}")
            raise
        finally:
            cursor.close()
            raw_conn.close()

    def run_pipeline(self, symbols: List[str], force_full_refresh: bool = False):
        """Main pipeline with progress tracking, graceful shutdown, and retry logic.
        
        Fixes spurious KeyboardInterrupt on Windows caused by worker-thread
        network errors (connection resets, SSL timeouts, yfinance rate-limits)
        propagating through ThreadPoolExecutor.as_completed().
        """
        logger.info(f"🚀 Starting pipeline for {len(symbols)} symbols")
        
        last_dates = self.get_ticker_date_ranges(symbols)
        today = datetime.now()
        
        full_download_tickers = []
        incremental_tickers = []
        
        for sym in symbols:
            clean_sym = sym.replace('.NS', '')
            
            if force_full_refresh or clean_sym not in last_dates:
                full_download_tickers.append(sym)
            else:
                last_date = last_dates[clean_sym]
                days_since_update = (today - last_date).days
                
                if days_since_update > 1:
                    incremental_tickers.append(sym)
        
        tasks = []
        
        # Full Downloads
        for i in range(0, len(full_download_tickers), Config.CHUNK_SIZE):
            batch = full_download_tickers[i:i + Config.CHUNK_SIZE]
            tasks.append({
                'tickers': batch, 
                'period': '5y', 
                'start': None, 
                'end': None,
                'download_type': 'FULL'
            })
            
        # Incremental Downloads
        if incremental_tickers:
            start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
            for i in range(0, len(incremental_tickers), Config.CHUNK_SIZE):
                batch = incremental_tickers[i:i + Config.CHUNK_SIZE]
                tasks.append({
                    'tickers': batch, 
                    'period': None, 
                    'start': start_date, 
                    'end': today.strftime('%Y-%m-%d'),
                    'download_type': 'INCREMENTAL'
                })

        logger.info(f"📊 Processing: {len(full_download_tickers)} Full | {len(incremental_tickers)} Incremental | {len(tasks)} batches")
        
        failed_tasks = []  # Collect for retry
        
        try:
            with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
                future_to_batch = {
                    executor.submit(
                        self.download_batch, 
                        t['tickers'], 
                        t['period'], 
                        t['start'], 
                        t['end']
                    ): t for t in tasks
                }
                
                for future in tqdm(as_completed(future_to_batch), total=len(tasks), 
                                 desc="📥 Downloading & Storing", unit="batch"):
                    try:
                        raw_df = future.result(timeout=180)
                        if not raw_df.empty:
                            gaps = self._detect_trading_gaps(raw_df)
                            clean_df = self.process_dataframe(raw_df)
                            
                            if not clean_df.empty:
                                self.fast_bulk_upsert(clean_df)
                                metrics = self._get_data_quality_metrics(clean_df)
                                if metrics['validation_status'] != 'PASS':
                                    logger.warning(f"⚠️  Quality check: {metrics['validation_status']} - {metrics['warnings']}")
                            else:
                                batch_info = future_to_batch[future]
                                logger.warning(f"No valid records after processing for batch: {batch_info['tickers']}")
                    except TimeoutError:
                        batch_info = future_to_batch[future]
                        logger.warning(f"⏱️ Timeout for {batch_info['download_type']} batch ({len(batch_info['tickers'])} tickers) — will retry")
                        failed_tasks.append(batch_info)
                    except Exception as e:
                        batch_info = future_to_batch[future]
                        err_msg = str(e)[:120]
                        logger.error(f"Worker failed for {batch_info['download_type']} ({len(batch_info['tickers'])} tickers): {err_msg}")
                        failed_tasks.append(batch_info)
        except KeyboardInterrupt:
            logger.warning("⚠️ Pipeline interrupted — saving progress and shutting down gracefully...")
            # executor.__exit__ will call shutdown(wait=True), which may hang.
            # We let it finish the current in-flight downloads but don't retry.
            failed_tasks.clear()
        except Exception as e:
            logger.error(f"Pipeline executor error: {e}")
        
        # ---- Retry failed batches sequentially (avoids thread-pool issues) ----
        if failed_tasks:
            logger.info(f"🔄 Retrying {len(failed_tasks)} failed batches sequentially...")
            for task in failed_tasks:
                try:
                    raw_df = self.download_batch(
                        task['tickers'], task['period'], task['start'], task['end']
                    )
                    if not raw_df.empty:
                        clean_df = self.process_dataframe(raw_df)
                        if not clean_df.empty:
                            self.fast_bulk_upsert(clean_df)
                            logger.info(f"   ✅ Retry succeeded for {len(task['tickers'])} tickers")
                            continue
                    logger.warning(f"   ⚠️ Retry returned no data for {task['tickers'][:3]}...")
                    self.failed_tickers.extend(task['tickers'])
                except Exception as e:
                    logger.error(f"   ❌ Retry also failed: {str(e)[:80]}")
                    self.failed_tickers.extend(task['tickers'])

        self.print_statistics()

    def print_statistics(self):
        """Print pipeline execution statistics with quality metrics"""
        logger.info("=" * 70)
        logger.info("📈 PIPELINE STATISTICS")
        logger.info("=" * 70)
        logger.info(f"✅ Successful operations: {self.success_count}")
        logger.info(f"❌ Failed operations: {self.error_count}")
        logger.info(f"⚠️  Failed tickers: {len(self.failed_tickers)}")
        
        if self.failed_tickers:
            failed_clean = [t.replace('.NS', '') for t in self.failed_tickers[:20]]
            logger.warning(f"Failed tickers: {', '.join(failed_clean)}")
            if len(self.failed_tickers) > 20:
                logger.warning(f"... and {len(self.failed_tickers) - 20} more")
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(DISTINCT ticker) as total_stocks,
                        COUNT(*) as total_records,
                        MIN(date) as earliest_date,
                        MAX(date) as latest_date,
                        ROUND(AVG(volume), 0) as avg_volume,
                        SUM(CASE WHEN volume > 0 THEN 1 ELSE 0 END) as records_with_volume
                    FROM nse_stocks
                """))
                row = result.fetchone()
                if row:
                    logger.info(f"📊 Database: {row.total_stocks} stocks, {row.total_records:,} records")
                    logger.info(f"📅 Date range: {row.earliest_date} to {row.latest_date}")
                    logger.info(f"📊 Avg volume: {int(row.avg_volume):,} | Records with volume: {row.records_with_volume:,}")
                    
                    # Data quality percentage
                    quality_pct = (row.records_with_volume / row.total_records * 100) if row.total_records > 0 else 0
                    quality_status = "✅ EXCELLENT" if quality_pct > 95 else "⚠️  GOOD" if quality_pct > 85 else "❌ NEEDS ATTENTION"
                    logger.info(f"📈 Data Quality: {quality_status} ({quality_pct:.1f}% valid records)")
        except Exception as e:
            logger.error(f"Failed to fetch statistics: {e}")
        
        logger.info("=" * 70)

if __name__ == "__main__":
    start_time = time.time()
    
    import argparse
    parser = argparse.ArgumentParser(description='NSE Stock Data Pipeline')
    parser.add_argument('--force-refresh', action='store_true', 
                       help='Force full refresh of all stocks')
    args = parser.parse_args()
    
    pipeline = NSEDataPipeline()
    symbols = pipeline.get_all_nse_symbols()
    
    if symbols:
        pipeline.run_pipeline(symbols, force_full_refresh=args.force_refresh)
    else:
        logger.error("No symbols found. Exiting.")
    
    elapsed_time = time.time() - start_time
    logger.info(f"🏁 Process completed in {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")