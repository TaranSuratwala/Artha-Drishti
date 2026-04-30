from flask import Flask, jsonify, request, send_file, g
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.exceptions import HTTPException, BadRequest
from UserManager import UserManager
import decimal
import datetime
import json
import logging
import os
import sys
import time
import uuid
from threading import Lock
import numpy as np
import pandas as pd
from functools import wraps
from collections import defaultdict
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ── Custom JSON provider for numpy/pandas types (Flask 3.x) ─────────────
# Flask's default provider cannot serialize numpy bool_, int64, float64,
# ndarray, or pandas Timestamps.  This provider converts them transparently.
from flask.json.provider import DefaultJSONProvider


class _NumpySafeJSONProvider(DefaultJSONProvider):
    """Flask JSON provider that gracefully handles numpy and pandas types."""

    def default(self, obj):
        # numpy scalar types
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj) if np.isfinite(obj) else None
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        # pandas Timestamp
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        # decimal.Decimal
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        # datetime types
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        return super().default(obj)

# Import database pipeline
from IntegratedPostGreSQL import NSEDataPipeline

# Import ML predictor (with fallback alias)
from MLPredictor import UnifiedStockPredictor

# Import stock screener (use legacy StockScreener wrapper which has scan methods)
from StockScreener import StockScreener, TradingStrategy, StrategyCondition

# Import Portfolio Manager
from PortfolioManager import PortfolioManager

# Import Data Scheduler
from scheduler import get_scheduler

# Import Exchange Manager
from ExchangeManager import get_exchange_manager

# Import Enhanced Backtest Engine
from BacktestEngine import BacktestEngine, WalkForwardEngine, get_backtest_engine
from backtest_models import (
    BacktestConfig, BacktestResult, WalkForwardConfig,
    MarketRegime, PositionSizingMode, OrderType,
)

# Import News Provider (now bridges to SentimentEngine)
from NewsProvider import get_news_aggregator

# Import Sentiment Engine
try:
    from SentimentEngine import get_sentiment_engine
    _HAS_SENTIMENT = True
except ImportError:
    _HAS_SENTIMENT = False
    def get_sentiment_engine(*a, **kw):
        return None

# ── NEW Patent-Pending Modules (ported from BTP SEM-5 + enhanced) ──

# Advanced Multi-Strategy Engine (18 strategies, committee screening)
try:
    from AdvancedStrategyEngine import get_strategy_engine, SectorRotationDetector
    _HAS_STRATEGY_ENGINE = True
except ImportError:
    _HAS_STRATEGY_ENGINE = False
    def get_strategy_engine():
        return None

# Fundamental Analysis (Piotroski F-Score, multi-category scoring)
try:
    from FundamentalAnalysis import get_fundamental_analyzer
    _HAS_FUNDAMENTALS = True
except ImportError:
    _HAS_FUNDAMENTALS = False
    def get_fundamental_analyzer():
        return None

# Risk Analytics (30+ metrics, VaR, Efficient Frontier, Portfolio Risk)
try:
    from RiskAnalytics import get_risk_analytics, get_portfolio_analyzer, get_stock_comparator
    _HAS_RISK = True
except ImportError:
    _HAS_RISK = False
    def get_risk_analytics():
        return None

    def get_portfolio_analyzer():
        return None

    def get_stock_comparator():
        return None

# Export Manager (CSV, JSON, HTML report generation)
try:
    from ExportManager import get_export_manager
    _HAS_EXPORT = True
except ImportError:
    _HAS_EXPORT = False
    def get_export_manager():
        return None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database URL from environment or default
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Taran%4017@localhost:5432/StockDB")


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse boolean environment variables consistently."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Read integer env vars with a safe fallback."""
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


APP_ENV = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "production")).strip().lower()
APP_DEBUG = _env_flag("APP_DEBUG", default=APP_ENV == "development")
if "FLASK_DEBUG" in os.environ:
    APP_DEBUG = _env_flag("FLASK_DEBUG", default=APP_DEBUG)
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = _env_int("APP_PORT", 5000)
APP_THREADED = _env_flag("APP_THREADED", default=True)
APP_USE_RELOADER = _env_flag("APP_USE_RELOADER", default=APP_DEBUG)
APP_STARTED_AT = time.time()

app = Flask(__name__)
app.json_provider_class = _NumpySafeJSONProvider  # Handle numpy/pandas types in all JSON responses
app.json = _NumpySafeJSONProvider(app)            # Apply to current app instance

# JWT Configuration
_DEFAULT_JWT_SECRET = "genai-stock-intel-secret-key-2024"
_jwt_secret = os.getenv("JWT_SECRET_KEY", _DEFAULT_JWT_SECRET)
STRICT_SECURITY = _env_flag("STRICT_SECURITY", default=False)
if APP_ENV in {"production", "staging"} and _jwt_secret == _DEFAULT_JWT_SECRET:
    msg = "Using default JWT secret. Set JWT_SECRET_KEY for production-grade security."
    if STRICT_SECURITY:
        raise RuntimeError(msg)
    logger.warning(msg)

app.config["JWT_SECRET_KEY"] = _jwt_secret
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(days=1)
jwt = JWTManager(app)

# CORS configuration - allow configured origins
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
CORS(app, resources={
    r"/api/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Request-Id"],
        "expose_headers": ["X-Request-Id", "X-Response-Time-Ms"]
    }
})

# Global API helpers and request lifecycle middleware
def _is_api_request() -> bool:
    return request.path.startswith('/api')


def _extract_client_ip() -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or "unknown"


def _api_error_response(
    message: str,
    status_code: int,
    code: str | None = None,
    details: object | None = None,
    retry_after: int | None = None,
):
    payload = {
        "error": message,
        "code": code or "API_ERROR",
        "request_id": getattr(g, "request_id", None),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }
    if details is not None:
        payload["details"] = details
    if retry_after is not None:
        payload["retry_after"] = int(retry_after)
    return jsonify(payload), status_code


def _get_json_payload(required_fields=None):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise BadRequest("Request body must be a valid JSON object")

    if required_fields:
        missing = [field for field in required_fields if payload.get(field) in (None, "")]
        if missing:
            raise BadRequest(f"Missing required fields: {', '.join(missing)}")

    return payload


@app.before_request
def _request_context_init():
    g.request_id = request.headers.get('X-Request-Id') or str(uuid.uuid4())
    g.request_started_at = time.perf_counter()


@app.after_request
def _response_enrichment(response):
    request_id = getattr(g, 'request_id', None)
    if request_id:
        response.headers['X-Request-Id'] = request_id

    started_at = getattr(g, 'request_started_at', None)
    if started_at is not None:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers['X-Response-Time-Ms'] = f"{elapsed_ms:.2f}"
    else:
        elapsed_ms = None

    response.headers.setdefault('X-Content-Type-Options', 'nosniff')
    response.headers.setdefault('X-Frame-Options', 'DENY')
    response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')

    if _is_api_request() and not request.path.startswith('/api/download/'):
        response.headers.setdefault('Cache-Control', 'no-store, max-age=0')

    if _is_api_request():
        msg = (
            "HTTP %s %s -> %s%s rid=%s ip=%s"
            % (
                request.method,
                request.path,
                response.status_code,
                f" ({elapsed_ms:.2f}ms)" if elapsed_ms is not None else "",
                request_id,
                _extract_client_ip(),
            )
        )
        if response.status_code >= 500:
            logger.error(msg)
        elif response.status_code >= 400:
            logger.warning(msg)
        else:
            logger.info(msg)

    return response


# Flask/Werkzeug generic exception handlers for API routes
@app.errorhandler(BadRequest)
def _handle_bad_request(error):
    if _is_api_request():
        return _api_error_response(
            message=error.description or "Invalid request payload",
            status_code=400,
            code="BAD_REQUEST",
        )
    return jsonify({"error": error.description or "Bad request"}), 400


@app.errorhandler(HTTPException)
def _handle_http_exception(error):
    if _is_api_request():
        return _api_error_response(
            message=error.description or "Request failed",
            status_code=error.code or 500,
            code=(error.name or "HTTP_ERROR").upper().replace(" ", "_"),
        )
    return jsonify({"error": error.description or "Request failed"}), error.code or 500


@app.errorhandler(Exception)
def _handle_unexpected_error(error):
    logger.exception("Unhandled exception rid=%s path=%s", getattr(g, "request_id", None), request.path)
    if _is_api_request():
        return _api_error_response(
            message="Internal server error",
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
        )
    return jsonify({"error": "Internal server error"}), 500


# Rate limiting configuration
request_counts = defaultdict(list)
_rate_limit_lock = Lock()
RATE_LIMIT = max(_env_int("RATE_LIMIT_PER_MINUTE", 100), 1)
RATE_WINDOW = max(_env_int("RATE_LIMIT_WINDOW_SECONDS", 60), 1)
RATE_LIMIT_ENABLED = _env_flag("RATE_LIMIT_ENABLED", default=True)

def rate_limit(f):
    """Rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not RATE_LIMIT_ENABLED or request.method == 'OPTIONS':
            return f(*args, **kwargs)

        client_ip = _extract_client_ip()
        now = time.time()

        with _rate_limit_lock:
            request_counts[client_ip] = [
                req_time for req_time in request_counts[client_ip]
                if now - req_time < RATE_WINDOW
            ]

            if len(request_counts[client_ip]) >= RATE_LIMIT:
                oldest = min(request_counts[client_ip]) if request_counts[client_ip] else now
                retry_after = max(1, int(RATE_WINDOW - (now - oldest)))
                return _api_error_response(
                    message="Rate limit exceeded",
                    status_code=429,
                    code="RATE_LIMIT_EXCEEDED",
                    retry_after=retry_after,
                )

            request_counts[client_ip].append(now)

        return f(*args, **kwargs)
    return decorated_function

# Screener configuration
@dataclass
class ScreenerConfig:
    max_workers: int = 15
    cache_ttl_seconds: int = 1800
    timeout_seconds: int = 45
    enable_caching: bool = True
    min_data_points: int = 50

screener_config = ScreenerConfig()

# ── Server-side result cache (screener / backtest / etc.) ──────────────
_result_cache = {}          # key → (data, expire_ts)
SCREEN_CACHE_TTL = 600      # 10 min

def _get_cached(key):
    entry = _result_cache.get(key)
    if entry and entry[1] > time.time():
        return entry[0]
    _result_cache.pop(key, None)
    return None

def _set_cached(key, data, ttl=SCREEN_CACHE_TTL):
    _result_cache[key] = (data, time.time() + ttl)

def screen_cache(ttl=SCREEN_CACHE_TTL):
    """Decorator: caches screener JSON responses for *ttl* seconds."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            body = request.get_json(silent=True) or {}
            cache_key = f"screen:{request.path}:{json.dumps(body, sort_keys=True, default=str)}"
            hit = _get_cached(cache_key)
            if hit is not None:
                logger.info(f"Screen cache HIT  → {request.path}")
                return jsonify(hit)
            response = f(*args, **kwargs)
            # Only cache 200 OK responses
            if isinstance(response, tuple):
                resp_obj, status_code = response[0], response[1]
            else:
                resp_obj, status_code = response, 200
            if status_code == 200:
                try:
                    payload = resp_obj.get_json() if hasattr(resp_obj, 'get_json') else resp_obj
                    _set_cached(cache_key, payload, ttl)
                except Exception:
                    pass
            return response
        wrapper.__name__ = f.__name__   # Flask needs unique endpoint names
        return wrapper
    return decorator

# Feature Engineering wrapper function for scheduler
def run_feature_engineering():
    """
    Wrapper function to run feature engineering via scheduler.
    This will be called automatically when scheduler runs.
    Uses ThreadPoolExecutor for parallel batch processing across all tickers.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time as _time

    MAX_WORKERS = 6          # Parallel DB-read + compute threads
    PROGRESS_EVERY = 50      # Log progress every N tickers

    def _process_one_ticker(ticker, StockFeatureEngineer, pd):
        """Process a single ticker — meant to run in a thread."""
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return ticker, False, "no history"
        df = pd.DataFrame([dict(row) for row in ticker_data])
        if df.empty or len(df) < 30:
            return ticker, False, f"too few rows ({len(df)})"
        engineer = StockFeatureEngineer(df, ticker=ticker)
        eng_df = engineer.build_features(include_fundamentals=False)
        pipeline.store_engineered_features(ticker, eng_df)
        return ticker, True, None

    try:
        logger.info("🔧 Starting feature engineering pipeline...")

        try:
            from FeatureEngineering import StockFeatureEngineer
            import pandas as pd

            # 1. Get unique tickers from latest data (single query)
            all_data = pipeline.get_latest_data(limit=None)
            if not all_data:
                logger.warning("   ⚠️  No data found for feature engineering")
                return

            tickers = sorted(set(row['ticker'] for row in all_data))
            total = len(tickers)
            logger.info(f"   Found {total} unique tickers — processing with {MAX_WORKERS} workers...")

            # 2. Process in parallel using ThreadPoolExecutor
            processed_count = 0
            failed_count = 0
            t0 = _time.time()

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {
                    executor.submit(_process_one_ticker, t, StockFeatureEngineer, pd): t
                    for t in tickers
                }
                for idx, future in enumerate(as_completed(futures), 1):
                    ticker = futures[future]
                    try:
                        _, ok, reason = future.result(timeout=120)
                        if ok:
                            processed_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.debug(f"   ⚠️  {ticker}: {e}")

                    if idx % PROGRESS_EVERY == 0 or idx == total:
                        elapsed = _time.time() - t0
                        rate = idx / max(elapsed, 0.1)
                        eta = (total - idx) / max(rate, 0.01)
                        logger.info(
                            f"   [{idx}/{total}] done={processed_count} fail={failed_count} "
                            f"({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)"
                        )

            elapsed = _time.time() - t0
            logger.info(
                f"   ✅ Feature engineering completed: {processed_count}/{total} stocks "
                f"({failed_count} skipped) in {elapsed:.1f}s"
            )
        except ImportError as e:
            logger.warning(f"   ⚠️  FeatureEngineering module not available: {e}")
            logger.info("   ℹ️  This is optional — screening will continue with basic features")
        except Exception as e:
            logger.error(f"   ❌ Feature engineering pipeline failed: {e}")
            raise

    except Exception as e:
        logger.error(f"❌ Failed to run feature engineering: {e}")
        raise


# Sentiment pre-caching wrapper for scheduler
def run_sentiment_precache():
    """
    Pre-cache sentiment analysis for the most actively traded tickers.
    Called by the scheduler after feature engineering.
    Uses yfinance fallback if Finnhub key is not set.
    """
    MAX_TICKERS = 100  # Pre-cache top N tickers to avoid excessive API calls

    try:
        logger.info("📰 Starting sentiment pre-caching...")

        try:
            from SentimentEngine import get_sentiment_engine
        except ImportError:
            logger.warning("   ⚠️  SentimentEngine not available — skipping sentiment pre-cache")
            return

        engine = get_sentiment_engine()

        # Get top tickers by volume (most likely to be viewed by users)
        all_data = pipeline.get_latest_data(limit=None)
        if not all_data:
            logger.warning("   ⚠️  No data to determine top tickers")
            return

        # Sort by volume descending if available, else just take first N
        try:
            sorted_data = sorted(all_data, key=lambda r: float(r.get('volume', 0) or 0), reverse=True)
        except Exception:
            sorted_data = all_data

        tickers = []
        seen = set()
        for row in sorted_data:
            t = row.get('ticker', '')
            if t and t not in seen:
                seen.add(t)
                tickers.append(t)
                if len(tickers) >= MAX_TICKERS:
                    break

        logger.info(f"   Pre-caching sentiment for top {len(tickers)} tickers...")
        cached = 0
        for i, ticker in enumerate(tickers, 1):
            try:
                features = engine.get_sentiment_features(ticker, days_back=14)
                if features and features.get('sentiment_volume', 0) > 0:
                    cached += 1
            except Exception as e:
                logger.debug(f"   Sentiment cache miss for {ticker}: {e}")

            if i % 25 == 0:
                logger.info(f"   [{i}/{len(tickers)}] cached={cached}")

        logger.info(f"   ✅ Sentiment pre-cached: {cached}/{len(tickers)} tickers had news articles")
    except Exception as e:
        logger.warning(f"   ⚠️  Sentiment pre-caching failed (non-critical): {e}")


# Initialize components with error handling
try:
    pipeline = NSEDataPipeline(DB_URL)
    # Initialize User Manager
    user_manager = UserManager(pipeline.engine)
    
    # InteractiveStockScreener takes pipeline and cache_ttl
    screener = StockScreener(pipeline, cache_ttl=screener_config.cache_ttl_seconds, max_workers=screener_config.max_workers, max_tickers=2500)
    # UnifiedStockPredictor manages its own DB engine; we pass the URL directly.
    predictor = UnifiedStockPredictor(DB_URL)
    predictor._load_model()
    if predictor.model is not None:
        logger.info("✅ Loaded existing trained model artifacts")
    else:
        logger.warning("⚠️  No trained model artifacts found — predictions requiring ML will need manual training")
    # Portfolio Manager
    portfolio_manager = PortfolioManager()
    
    # Initialize Exchange Manager
    exchange_manager = get_exchange_manager(default_exchange='NSE')
    
    # Initialize Data Scheduler.
    # Auto-training is controlled by SCHEDULER_AUTO_TRAIN (default: false).
    data_scheduler = get_scheduler(
        data_pipeline=pipeline,
        feature_engineer_func=run_feature_engineering,
        model_train_func=predictor.train,
        sentiment_func=run_sentiment_precache,  # Pre-cache sentiment analysis
    )
    # Guard against duplicate schedulers in Flask reloader and multi-worker Gunicorn.
    _werkzeug_main = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    _is_gunicorn = 'gunicorn' in os.environ.get('SERVER_SOFTWARE', '').lower()
    _allow_scheduler_in_gunicorn = _env_flag('SCHEDULER_IN_WEB_WORKER', default=False)

    if _is_gunicorn and not _allow_scheduler_in_gunicorn:
        should_start_scheduler = False
        logger.info("⏸️  Scheduler disabled in Gunicorn web workers (set SCHEDULER_IN_WEB_WORKER=true for single-worker setups)")
    elif APP_DEBUG and APP_USE_RELOADER and not _werkzeug_main:
        should_start_scheduler = False
        logger.info("⏸️  Scheduler deferred — waiting for Flask reloader to start actual server process")
    else:
        should_start_scheduler = True

    if should_start_scheduler:
        data_scheduler.start()
    
    logger.info("✅ All components initialized successfully")
    logger.info("⏰ Scheduler Status:")
    scheduler_status = data_scheduler.get_status()
    logger.info(f"   - Enabled: {scheduler_status.get('enabled')}")
    logger.info(f"   - Running: {scheduler_status.get('running')}")
    logger.info(f"   - Schedule: Every weekday at {scheduler_status.get('schedule')}")
except Exception as e:
    logger.error(f"❌ Failed to initialize components: {e}")
    raise

def clean_row(row):
    """Convert database row to JSON-serializable format"""
    cleaned: dict = {}
    for key, value in row.items():
        if isinstance(value, decimal.Decimal):
            cleaned[key] = float(value)
        elif isinstance(value, (datetime.date, datetime.datetime)):
            cleaned[key] = value.isoformat()
        else:
            cleaned[key] = value
    return cleaned

# ==================== REAL-TIME QUOTES (yfinance) ====================

import threading

# In-memory quote cache: { "TICKER": { data: {...}, expires: timestamp } }
_quote_cache = {}
_quote_cache_lock = threading.Lock()
_QUOTE_TTL = 180  # seconds – yfinance is 10-15 min delayed anyway; cache 3 min

def _get_cached_quote(ticker):
    """Return cached quote if fresh, else None."""
    with _quote_cache_lock:
        entry = _quote_cache.get(ticker)
        if entry and entry['expires'] > time.time():
            return entry['data']
    return None

def _set_cached_quote(ticker, data):
    """Cache a quote for _QUOTE_TTL seconds."""
    with _quote_cache_lock:
        _quote_cache[ticker] = {'data': data, 'expires': time.time() + _QUOTE_TTL}


def _normalize_ticker_symbol(ticker: str) -> str:
    """Normalize ticker text to uppercase without surrounding whitespace."""
    return str(ticker or '').strip().upper()


_SERIES_SUFFIXES = {
    'BE', 'BZ', 'BL', 'SM', 'ST', 'SZ', 'EQ', 'GB', 'LT', 'IV', 'PP', 'TB', 'XD', 'XT', 'RR'
}


def _strip_series_suffix(symbol: str) -> str:
    """Strip common NSE series suffixes (e.g., -RE2, -EQ) without touching core symbols."""
    if '-' not in symbol:
        return symbol

    base, suffix = symbol.rsplit('-', 1)
    if not base:
        return symbol

    suffix = suffix.strip().upper()
    if suffix in _SERIES_SUFFIXES:
        return base
    if suffix == 'RE' or (suffix.startswith('RE') and suffix[2:].isdigit()):
        return base
    return symbol


def _base_ticker_symbol(ticker: str) -> str:
    """Return symbol without index prefix or common exchange/series suffixes."""
    symbol = _normalize_ticker_symbol(ticker).lstrip('^')
    for suffix in ('.NS', '.BO', '.L'):
        if symbol.endswith(suffix):
            symbol = symbol[: -len(suffix)]
            break
    return _strip_series_suffix(symbol)


def _to_yfinance_symbol(ticker: str, exchange: str = 'NSE') -> str:
    """Build a yfinance-compatible symbol, preserving index tickers with ^ prefix."""
    symbol = _normalize_ticker_symbol(ticker)
    if not symbol:
        return symbol
    if symbol.startswith('^'):
        return symbol
    if any(symbol.endswith(s) for s in ('.NS', '.BO', '.L', '.NYSE', '.NASDAQ')):
        return symbol

    exchange_code = str(exchange or 'NSE').strip().upper()
    if exchange_code == 'BSE':
        return f"{symbol}.BO"
    if exchange_code == 'NSE':
        return f"{symbol}.NS"
    return symbol


def _quote_symbol_candidates(ticker: str) -> list[str]:
    """Return candidate yfinance symbols for quote lookup in priority order."""
    symbol = _normalize_ticker_symbol(ticker)
    if not symbol:
        return []

    candidates = []

    def _push(value: str):
        if value and value not in candidates:
            candidates.append(value)

    base_symbol = _base_ticker_symbol(symbol)

    if symbol.startswith('^'):
        _push(symbol)
        _push(base_symbol)
        return candidates

    if any(symbol.endswith(s) for s in ('.NS', '.BO', '.L', '.NYSE', '.NASDAQ')):
        _push(symbol)
        _push(base_symbol)
        return candidates

    _push(f"{base_symbol}.NS")
    _push(f"{base_symbol}.BO")
    _push(base_symbol)
    return candidates

def _fetch_single_quote(ticker):
    """Fetch real-time quote for one ticker from yfinance."""
    import yfinance as yf

    normalized_ticker = _normalize_ticker_symbol(ticker)
    for yf_ticker in _quote_symbol_candidates(normalized_ticker):
        try:
            stock = yf.Ticker(yf_ticker)
            info = stock.info or {}

            current = info.get('currentPrice') or info.get('regularMarketPrice')
            prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
            day_high = info.get('dayHigh') or info.get('regularMarketDayHigh')
            day_low = info.get('dayLow') or info.get('regularMarketDayLow')
            volume = info.get('volume') or info.get('regularMarketVolume')
            open_price = info.get('open') or info.get('regularMarketOpen')
            market_cap = info.get('marketCap')
            name = info.get('shortName') or info.get('longName') or normalized_ticker

            if current and current > 0:
                change = round(current - prev_close, 2) if prev_close else 0
                change_pct = round((change / prev_close) * 100, 2) if prev_close and prev_close > 0 else 0
                quote = {
                    'ticker': normalized_ticker,
                    'name': name,
                    'price': round(current, 2),
                    'prev_close': round(prev_close, 2) if prev_close else None,
                    'open': round(open_price, 2) if open_price else None,
                    'day_high': round(day_high, 2) if day_high else None,
                    'day_low': round(day_low, 2) if day_low else None,
                    'change': change,
                    'change_pct': change_pct,
                    'volume': volume,
                    'market_cap': market_cap,
                    'source': 'yfinance',
                    'delayed': True,       # 10-15 min delay
                    'timestamp': datetime.datetime.now().isoformat(),
                }
                return quote
        except Exception:
            continue
    return None

def _fetch_batch_quotes(tickers, timeout_seconds=15, allow_individual_fallback=True):
    """
    Efficient batch fetch using yf.download for multiple tickers.
    Falls back to individual fetches for failures when enabled.
    """
    import yfinance as yf

    results = {}
    # Check cache first
    uncached = []
    for t in tickers:
        cached = _get_cached_quote(t)
        if cached:
            results[t] = cached
        else:
            uncached.append(t)

    if not uncached:
        return results

    # Batch download for uncached tickers
    nse_map = {}  # yf_ticker → original_ticker
    for t in uncached:
        original = _normalize_ticker_symbol(t)
        yf_t = _to_yfinance_symbol(original, exchange='NSE')
        if yf_t:
            nse_map[yf_t] = original

    try:
        yf_tickers_str = ' '.join(nse_map.keys())
        data = yf.download(yf_tickers_str, period='5d', progress=False, timeout=timeout_seconds)

        if not data.empty:
            # Handle MultiIndex columns for multiple tickers
            is_multi = isinstance(data.columns, pd.MultiIndex)

            for yf_t, orig_t in nse_map.items():
                try:
                    if is_multi:
                        close_col = data['Close'][yf_t] if yf_t in data['Close'].columns else None
                        open_col = data['Open'][yf_t] if yf_t in data['Open'].columns else None
                        high_col = data['High'][yf_t] if yf_t in data['High'].columns else None
                        low_col = data['Low'][yf_t] if yf_t in data['Low'].columns else None
                        vol_col = data['Volume'][yf_t] if yf_t in data['Volume'].columns else None
                    else:
                        # Single ticker — no second level
                        close_col = data['Close']
                        open_col = data['Open']
                        high_col = data['High']
                        low_col = data['Low']
                        vol_col = data['Volume']

                    if close_col is not None and not close_col.dropna().empty:
                        current = float(close_col.dropna().iloc[-1])
                        prev = float(close_col.dropna().iloc[-2]) if len(close_col.dropna()) >= 2 else current
                        change = round(current - prev, 2)
                        change_pct = round((change / prev) * 100, 2) if prev > 0 else 0

                        quote = {
                            'ticker': orig_t,
                            'name': orig_t,
                            'price': round(current, 2),
                            'prev_close': round(prev, 2),
                            'open': round(float(open_col.dropna().iloc[-1]), 2) if open_col is not None and not open_col.dropna().empty else None,
                            'day_high': round(float(high_col.dropna().iloc[-1]), 2) if high_col is not None and not high_col.dropna().empty else None,
                            'day_low': round(float(low_col.dropna().iloc[-1]), 2) if low_col is not None and not low_col.dropna().empty else None,
                            'change': change,
                            'change_pct': change_pct,
                            'volume': int(vol_col.dropna().iloc[-1]) if vol_col is not None and not vol_col.dropna().empty else None,
                            'market_cap': None,
                            'source': 'yfinance',
                            'delayed': True,
                            'timestamp': datetime.datetime.now().isoformat(),
                        }
                        results[orig_t] = quote
                        _set_cached_quote(orig_t, quote)
                except Exception as e:
                    logger.debug(f"Batch parse failed for {orig_t}: {e}")
    except Exception as e:
        logger.warning(f"Batch download failed: {e}")

    # Individual fallback for remaining tickers
    if allow_individual_fallback:
        for t in uncached:
            if t not in results:
                quote = _fetch_single_quote(t)
                if quote:
                    results[t] = quote
                    _set_cached_quote(t, quote)

    return results


@app.route('/api/quote/<ticker>', methods=['GET'])
@rate_limit
def get_realtime_quote(ticker):
    """
    Get real-time quote for a single ticker (10-15 min delayed via yfinance).
    Cached for 60 seconds server-side to avoid rate-limiting.
    """
    try:
        ticker = _normalize_ticker_symbol(ticker)

        # Check cache
        cached = _get_cached_quote(ticker)
        if cached:
            return jsonify({'status': 'success', 'cached': True, **cached})

        quote = _fetch_single_quote(ticker)
        if not quote:
            return jsonify({'error': f'No live data for {ticker}'}), 404

        _set_cached_quote(ticker, quote)
        return jsonify({'status': 'success', 'cached': False, **quote})
    except Exception as e:
        logger.error(f"Error fetching quote for {ticker}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/quotes/batch', methods=['POST'])
@rate_limit
def get_batch_quotes():
    """
    Get real-time quotes for multiple tickers in one call.
    Body: { "tickers": ["RELIANCE", "TCS", "INFY", ...] }
    Efficient batch yf.download + server-side caching.
    Max 50 tickers per batch.
    """
    try:
        data = request.get_json() or {}
        tickers = data.get('tickers', [])

        if not tickers:
            return jsonify({'error': 'No tickers provided'}), 400

        # Limit batch size
        tickers = [_normalize_ticker_symbol(t) for t in tickers[:50]]

        quotes = _fetch_batch_quotes(tickers)

        return jsonify({
            'status': 'success',
            'quotes': quotes,
            'fetched': len(quotes),
            'requested': len(tickers),
            'timestamp': datetime.datetime.now().isoformat(),
        })
    except Exception as e:
        logger.error(f"Error fetching batch quotes: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== STOCK DATA ENDPOINTS ====================

@app.route('/api/stocks', methods=['GET'])
def fetch_stocks():
    """Fetch all stocks latest data"""
    try:
        raw_data = pipeline.get_latest_data(limit=None)
        clean_data = [clean_row(row) for row in raw_data]
        return jsonify(clean_data)
    except Exception as e:
        logger.error(f"Error fetching stocks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/history/<ticker>', methods=['GET'])
def fetch_history(ticker):
    """Fetch historical data for a specific ticker, optionally filtered by period."""
    try:
        normalized_ticker = _normalize_ticker_symbol(ticker)
        history_candidates = [normalized_ticker]

        base_symbol = _base_ticker_symbol(normalized_ticker)
        if base_symbol and base_symbol not in history_candidates:
            history_candidates.append(base_symbol)

        raw_data = []
        for candidate in history_candidates:
            raw_data = pipeline.get_ticker_history(candidate)
            if raw_data:
                break

        clean_data = [clean_row(row) for row in raw_data]

        # Apply period filter
        period = request.args.get('period', 'all')
        if period != 'all' and clean_data:
            import datetime as _dt
            period_map = {'1m': 30, '3m': 90, '6m': 180, '1y': 365, '2y': 730, '5y': 1825}
            days = period_map.get(period)
            if days:
                cutoff = (_dt.datetime.now() - _dt.timedelta(days=days)).isoformat()
                clean_data = [d for d in clean_data if str(d.get('date', '')) >= cutoff]

        return jsonify(clean_data)
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== MARKET MOVERS ENDPOINTS ====================

_market_movers_cache = {'data': None, 'expires': 0}

@app.route('/api/market/movers', methods=['GET'])
@rate_limit
def get_market_movers():
    """
    Get top gainers and top losers with LIVE yfinance prices.
    First builds candidate list from DB, then enriches top candidates with live quotes.
    Cached server-side for 3 minutes.
    """
    # Serve from cache if fresh
    count = int(request.args.get('count', 5))
    cache_key = f"{count}"
    if _market_movers_cache.get('key') == cache_key and _market_movers_cache['data'] and _market_movers_cache['expires'] > time.time():
        return jsonify(_market_movers_cache['data'])
    try:
        import yfinance as yf

        raw_data = pipeline.get_latest_data(limit=None)
        clean_data = [clean_row(row) for row in raw_data]

        # Build candidate list from DB (fast)
        movers = []
        for stock in clean_data:
            try:
                close = float(stock.get('close', 0))
                open_price = float(stock.get('open', 0))
                prev_close = float(stock.get('prev_close', open_price))
                if prev_close and prev_close > 0:
                    pct_change = ((close - prev_close) / prev_close) * 100
                elif open_price and open_price > 0:
                    pct_change = ((close - open_price) / open_price) * 100
                else:
                    continue
                movers.append({
                    'ticker': stock.get('ticker', ''),
                    'company_name': stock.get('company_name', stock.get('ticker', '')),
                    'current_price': close,
                    'open': open_price,
                    'prev_close': prev_close,
                    'change': round(close - prev_close, 2),
                    'change_pct': round(pct_change, 2),
                    'volume': stock.get('volume', 0),
                    'high': stock.get('high', close),
                    'low': stock.get('low', close),
                    'date': stock.get('date', '')
                })
            except (ValueError, TypeError, KeyError):
                continue

        movers.sort(key=lambda x: x['change_pct'], reverse=True)

        count = int(request.args.get('count', 5))
        top_gainers_db = movers[:count * 2]   # fetch extra candidates
        top_losers_db = movers[-(count * 2):]

        # Enrich top candidates with live yfinance data
        candidate_tickers = list({m['ticker'] for m in top_gainers_db + top_losers_db})
        live_quotes = _fetch_batch_quotes(candidate_tickers)

        def enrich(stock):
            lq = live_quotes.get(stock['ticker'])
            if lq and lq.get('price') and lq['price'] > 0:
                stock['current_price'] = lq['price']
                stock['prev_close'] = lq.get('prev_close', stock['prev_close'])
                stock['open'] = lq.get('open', stock['open'])
                stock['high'] = lq.get('day_high', stock['high'])
                stock['low'] = lq.get('day_low', stock['low'])
                stock['volume'] = lq.get('volume', stock['volume'])
                stock['change'] = lq.get('change', stock['change'])
                stock['change_pct'] = lq.get('change_pct', stock['change_pct'])
                stock['live'] = True
            else:
                stock['live'] = False
            return stock

        enriched = [enrich(m) for m in movers]
        enriched.sort(key=lambda x: x['change_pct'], reverse=True)

        gainers = enriched[:count]
        losers = enriched[-count:][::-1]

        result = {
            "status": "success",
            "gainers": gainers,
            "losers": losers,
            "timestamp": datetime.datetime.now().isoformat(),
            "total_stocks": len(enriched),
            "live": True
        }

        # Cache for 3 minutes
        _market_movers_cache['data'] = result
        _market_movers_cache['expires'] = time.time() + 180
        _market_movers_cache['key'] = cache_key

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error fetching market movers: {e}")
        return jsonify({"error": str(e)}), 500


# Server-side cache for market overview (avoid hammering yfinance)
_market_overview_cache = {'data': None, 'expires': 0}

@app.route('/api/market/overview', methods=['GET'])
@rate_limit
def get_market_overview():
    """
    Live market overview with index quotes, market breadth from DB,
    and sectoral performance.  Cached server-side for 3 minutes.
    """
    # Serve from cache if fresh
    if _market_overview_cache['data'] and _market_overview_cache['expires'] > time.time():
        return jsonify(_market_overview_cache['data'])
    try:
        import yfinance as yf

        # ── 1. Live index quotes ──
        # Use working Yahoo Finance symbols for Indian indices.
        # Index tickers use ^ prefix and must NOT have .NS/.BO appended.
        indices = {
            '^NSEI':        {'name': 'NIFTY 50',        'short': 'NIFTY'},
            '^BSESN':       {'name': 'SENSEX',          'short': 'SENSEX'},
            '^NSEBANK':     {'name': 'BANK NIFTY',      'short': 'BANKNIFTY'},
            'JUNIORBEES.NS': {'name': 'NIFTY NEXT 50 (ETF Proxy)', 'short': 'NXTFIFTY'},
        }

        index_data = []
        try:
            yf_tickers = ' '.join(indices.keys())
            data = yf.download(yf_tickers, period='5d', progress=False, timeout=6)
            if not data.empty:
                # Deep-copy to fix numpy read-only issue
                data = data.copy(deep=True)
                is_multi = isinstance(data.columns, pd.MultiIndex)
                for yf_sym, meta in indices.items():
                    try:
                        if is_multi:
                            close_s = data['Close'][yf_sym] if yf_sym in data['Close'].columns else None
                        else:
                            close_s = data['Close']
                        if close_s is not None and not close_s.dropna().empty:
                            vals = close_s.dropna()
                            current = float(vals.iloc[-1])
                            prev = float(vals.iloc[-2]) if len(vals) >= 2 else current
                            change = round(current - prev, 2)
                            change_pct = round((change / prev) * 100, 2) if prev > 0 else 0
                            index_data.append({
                                'symbol': meta['short'],
                                'name': meta['name'],
                                'value': round(current, 2),
                                'change': change,
                                'change_pct': change_pct,
                            })
                    except Exception:
                        pass
        except Exception as e:
            logger.warning(f"Index fetch failed: {e}")

        # ── 2. Market breadth from DB (fast) ──
        raw = pipeline.get_latest_data(limit=None)
        cleaned = [clean_row(r) for r in raw]
        advancers = 0
        decliners = 0
        unchanged = 0
        total_volume = 0
        for s in cleaned:
            try:
                c = float(s.get('close', 0))
                o = float(s.get('open', 0))
                v = int(s.get('volume', 0) or 0)
                total_volume += v
                if c > o:
                    advancers += 1
                elif c < o:
                    decliners += 1
                else:
                    unchanged += 1
            except (ValueError, TypeError):
                pass

        total = advancers + decliners + unchanged
        breadth_pct = round((advancers / total) * 100, 1) if total > 0 else 50

        # ── 3. Sectoral performance via representative large-cap stocks ──
        # Many sectoral index tickers (^CNXIT, ^CNXPHARMA, etc.) are
        # no longer available on Yahoo Finance.  Instead, compute a
        # proxy from the largest constituent of each sector.
        sector_proxies = {
            'TCS.NS':       'IT',
            'SUNPHARMA.NS': 'Pharma',
            'HDFCBANK.NS':  'Financial',
            'MARUTI.NS':    'Auto',
            'TATASTEEL.NS': 'Metal',
            'RELIANCE.NS':  'Energy',
            'DLF.NS':       'Realty',
            'HINDUNILVR.NS':'FMCG',
        }
        sectors = []
        try:
            sec_tickers = ' '.join(sector_proxies.keys())
            sec_data = yf.download(sec_tickers, period='5d', progress=False, timeout=6)
            if not sec_data.empty:
                sec_data = sec_data.copy(deep=True)
                is_multi = isinstance(sec_data.columns, pd.MultiIndex)
                for yf_s, label in sector_proxies.items():
                    try:
                        if is_multi:
                            cs = sec_data['Close'][yf_s] if yf_s in sec_data['Close'].columns else None
                        else:
                            cs = sec_data['Close']
                        if cs is not None and not cs.dropna().empty:
                            vals = cs.dropna()
                            cur = float(vals.iloc[-1])
                            prv = float(vals.iloc[-2]) if len(vals) >= 2 else cur
                            ch_pct = round(((cur - prv) / prv) * 100, 2) if prv > 0 else 0
                            sectors.append({'name': label, 'change_pct': ch_pct})
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Sector fetch failed: {e}")

        sectors.sort(key=lambda x: x['change_pct'], reverse=True)

        result = {
            "status": "success",
            "indices": index_data,
            "breadth": {
                "advancers": advancers,
                "decliners": decliners,
                "unchanged": unchanged,
                "total": total,
                "bullish_pct": breadth_pct,
            },
            "volume": total_volume,
            "sectors": sectors,
            "timestamp": datetime.datetime.now().isoformat(),
            "live": True,
        }

        # Cache for 3 minutes to avoid repeated yfinance calls
        _market_overview_cache['data'] = result
        _market_overview_cache['expires'] = time.time() + 180

        return jsonify(result)

    except Exception as e:
        logger.error(f"Market overview error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stocks/search', methods=['GET'])
@rate_limit
def search_stocks():
    """
    Search stocks by symbol or company name.
    Query parameter: q (search term)
    Returns up to 20 matching stocks.
    """
    try:
        query = request.args.get('q', '').strip().upper()
        
        if not query or len(query) < 1:
            return jsonify({
                "status": "success",
                "query": query,
                "results": [],
                "count": 0
            })
        
        raw_data = pipeline.get_latest_data(limit=None)
        clean_data = [clean_row(row) for row in raw_data]
        
        # Filter stocks matching the query
        matches = []
        for stock in clean_data:
            ticker = stock.get('ticker', '').upper()
            company_name = stock.get('company_name', '').upper()
            
            # Match if query is in ticker or company name
            if query in ticker or query in company_name:
                # Prioritize exact ticker matches
                priority = 0 if ticker == query else (1 if ticker.startswith(query) else 2)
                matches.append({
                    'ticker': stock.get('ticker', ''),
                    'company_name': stock.get('company_name', stock.get('ticker', '')),
                    'current_price': float(stock.get('close', 0)),
                    'change_pct': round(
                        ((float(stock.get('close', 0)) - float(stock.get('prev_close', stock.get('open', 1)))) / 
                         float(stock.get('prev_close', stock.get('open', 1)))) * 100, 2
                    ) if float(stock.get('prev_close', stock.get('open', 1))) > 0 else 0,
                    '_priority': priority
                })
        
        # Sort by priority and limit to 20 results
        matches.sort(key=lambda x: (x['_priority'], x['ticker']))
        results = [{k: v for k, v in m.items() if k != '_priority'} for m in matches[:20]]
        
        return jsonify({
            "status": "success",
            "query": query,
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        logger.error(f"Error searching stocks: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== SCREENING ENDPOINTS ====================

def _run_screen(strategy_name, params=None):
    """
    Unified helper: runs any screening strategy through the
    InteractiveStockScreener engine with server-side caching.
    Returns a Flask JSON response.
    """
    params = params or {}
    cache_key = f"screen:{strategy_name}:{json.dumps(params, sort_keys=True, default=str)}"
    hit = _get_cached(cache_key)
    if hit is not None:
        logger.info(f"Screen cache HIT  → {strategy_name}")
        return jsonify(hit)

    logger.info(f"Running {strategy_name} screen (params={params})")
    try:
        # run_screening returns {status, results, count, ...}
        raw = screener._interactive.run_screening(strategy_name, max_results=200)
        if raw.get('status') != 'success':
            return jsonify({"error": raw.get('message', 'Screening failed'), "strategy": strategy_name, "results": [], "count": 0}), 500

        results_data = raw.get('results', [])

        payload = {
            "strategy": strategy_name,
            "count": len(results_data),
            "results": results_data,
            "execution_time": raw.get('execution_time'),
        }
        _set_cached(cache_key, payload)
        return jsonify(payload)
    except Exception as e:
        logger.error(f"{strategy_name} screening error: {e}")
        return jsonify({"error": str(e), "strategy": strategy_name, "results": [], "count": 0}), 500


@app.route('/api/screen/piotroski', methods=['POST'])
def screen_piotroski():
    return _run_screen('piotroski', request.get_json(silent=True))

@app.route('/api/screen/momentum', methods=['POST'])
def screen_momentum():
    return _run_screen('momentum', request.get_json(silent=True))

@app.route('/api/screen/swing', methods=['GET'])
def screen_swing():
    return _run_screen('swing')

@app.route('/api/screen/breakout', methods=['POST'])
def screen_breakout():
    return _run_screen('breakout', request.get_json(silent=True))

@app.route('/api/screen/value', methods=['GET'])
def screen_value():
    return _run_screen('value')

@app.route('/api/screen/custom', methods=['POST'])
def screen_custom():
    """Custom screening with user-defined conditions"""
    try:
        data = request.get_json() or {}
        conditions = data.get('conditions', {})
        
        logger.info(f"Running Custom scan with conditions: {conditions}")
        results = screener.custom_scan(conditions)
        
        if hasattr(results, 'to_dict'):
            results_data = results.to_dict(orient='records')
        else:
            results_data = results
            
        return jsonify({
            "strategy": "custom",
            "count": len(results_data) if results_data else 0,
            "results": results_data
        })
    except Exception as e:
        logger.error(f"Custom screening error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/screen/garp', methods=['POST'])
def screen_garp():
    return _run_screen('garp', request.get_json(silent=True))

@app.route('/api/screen/mean_reversion', methods=['POST'])
def screen_mean_reversion():
    return _run_screen('mean_reversion', request.get_json(silent=True))

@app.route('/api/screen/quality_dividend', methods=['POST'])
def screen_quality_dividend():
    return _run_screen('quality_dividend', request.get_json(silent=True))

@app.route('/api/screen/trend_following', methods=['POST'])
def screen_trend_following():
    return _run_screen('trend_following', request.get_json(silent=True))

@app.route('/api/screen/contrarian', methods=['POST'])
def screen_contrarian():
    return _run_screen('contrarian', request.get_json(silent=True))

@app.route('/api/screen/quality_growth', methods=['POST'])
def screen_quality_growth():
    return _run_screen('quality_growth', request.get_json(silent=True))


# ==================== STOCK RECOMMENDATIONS =====================

_recommendations_build_lock = threading.Lock()
_RECOMMENDATIONS_BUILD_TIMEOUT_SECONDS = _env_int('RECOMMENDATIONS_BUILD_TIMEOUT_SECONDS', 12)
_RECOMMENDATIONS_WAIT_FOR_INFLIGHT_SECONDS = _env_int('RECOMMENDATIONS_WAIT_FOR_INFLIGHT_SECONDS', 6)
_RECOMMENDATIONS_CACHE_TTL_SECONDS = _env_int('RECOMMENDATIONS_CACHE_TTL_SECONDS', 300)
_RECOMMENDATIONS_STALE_TTL_SECONDS = _env_int('RECOMMENDATIONS_STALE_TTL_SECONDS', 1800)
_RECOMMENDATIONS_MAX_RESULTS = _env_int('RECOMMENDATIONS_MAX_RESULTS', 100)
_RECOMMENDATIONS_MAX_TICKERS = _env_int('RECOMMENDATIONS_MAX_TICKERS', 500)
_RECOMMENDATIONS_DB_FALLBACK_SCAN_LIMIT = _env_int('RECOMMENDATIONS_DB_FALLBACK_SCAN_LIMIT', 1200)
_RECOMMENDATIONS_DB_PARTIAL_FILL_SCAN_LIMIT = _env_int('RECOMMENDATIONS_DB_PARTIAL_FILL_SCAN_LIMIT', 600)
_RECOMMENDATIONS_TOTAL_TARGET_SECONDS = _env_int('RECOMMENDATIONS_TOTAL_TARGET_SECONDS', 13)
_RECOMMENDATIONS_SCREENING_BUDGET_SECONDS = _env_int(
    'RECOMMENDATIONS_SCREENING_BUDGET_SECONDS',
    max(1, _RECOMMENDATIONS_BUILD_TIMEOUT_SECONDS - 2),
)
_RECOMMENDATIONS_ENRICH_MAX_TIMEOUT_SECONDS = _env_int('RECOMMENDATIONS_ENRICH_MAX_TIMEOUT_SECONDS', 5)
_RECOMMENDATIONS_ENRICH_MIN_TIMEOUT_SECONDS = _env_int('RECOMMENDATIONS_ENRICH_MIN_TIMEOUT_SECONDS', 1)
_RECOMMENDATIONS_PARTIAL_ENRICH_LIMIT = _env_int('RECOMMENDATIONS_PARTIAL_ENRICH_LIMIT', 5)
_RECOMMENDATIONS_SKIP_ENRICH_ON_PARTIAL = _env_flag('RECOMMENDATIONS_SKIP_ENRICH_ON_PARTIAL', default=True)


def _as_stale_recommendations(payload, message):
    """Return a non-mutating stale recommendations payload."""
    return {
        **payload,
        'stale': True,
        'live': False,
        'message': message,
    }


def _confidence_label(score):
    """Map numeric confidence score to a human-readable tier."""
    if score >= 90:
        return 'VERY HIGH'
    if score >= 70:
        return 'HIGH'
    if score >= 50:
        return 'MODERATE'
    return 'LOW'


def _build_db_fallback_recommendations(limit=10, scan_limit=None, exclude_tickers=None):
    """Fast fallback recommendations from latest DB snapshot."""
    try:
        effective_scan_limit = scan_limit if scan_limit is not None else _RECOMMENDATIONS_DB_FALLBACK_SCAN_LIMIT
        raw = pipeline.get_latest_data(limit=effective_scan_limit)
        cleaned = [clean_row(r) for r in raw]
    except Exception as e:
        logger.warning(f"DB fallback recommendations unavailable: {e}")
        return []

    seen = {
        str(t).strip().upper()
        for t in (exclude_tickers or set())
        if t
    }

    candidates = []
    for row in cleaned:
        try:
            ticker = str(row.get('ticker') or '').strip().upper()
            if not ticker or ticker in seen:
                continue

            seen.add(ticker)

            close = float(row.get('close') or 0)
            prev_close = float(row.get('prev_close') or row.get('open') or 0)
            volume = int(row.get('volume') or 0)

            if close <= 0 or prev_close <= 0 or volume <= 0:
                continue

            change_pct = ((close - prev_close) / prev_close) * 100

            # Keep fallback useful even in down markets by ranking relatively,
            # while still rewarding liquidity and positive momentum.
            liquidity_bonus = min(10.0, max(0.0, float(np.log10(volume + 1))))
            confidence = round(min(88.0, max(42.0, 52.0 + (change_pct * 6.0) + liquidity_bonus)), 1)
            avg_score = round(min(100.0, max(0.0, 50.0 + (change_pct * 8.0) + liquidity_bonus)), 2)

            candidates.append({
                'ticker': ticker,
                'strategies': ['fallback_momentum_db'],
                'strategy_count': 1,
                'avg_score': avg_score,
                'confidence': confidence,
                'price': round(close, 2),
                'change_pct': round(change_pct, 2),
                'change': round(close - prev_close, 2),
                'prev_close': round(prev_close, 2),
                'volume': volume,
                'details': {'fallback': {'source': 'database_snapshot'}},
                'live': False,
            })
        except (TypeError, ValueError):
            continue

    candidates.sort(key=lambda x: (x['confidence'], x.get('volume') or 0), reverse=True)
    return candidates[:limit]

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """
    Aggregate strategy screens and rank by composite score.
    Supports timeframe-specific suggestions: daily, weekly, monthly.
    """
    timeframe = request.args.get('timeframe', 'weekly')
    timeframe = str(timeframe or 'weekly').strip().lower()

    strategy_map = {
        'daily': ['momentum', 'breakout', 'contrarian'],
        'weekly': ['momentum', 'trend_following', 'breakout'],
        'monthly': ['trend_following', 'value', 'quality_growth'],
    }
    if timeframe not in strategy_map:
        timeframe = 'weekly'

    strategies = strategy_map[timeframe]
    cache_key = f"recommendations:{timeframe}:top10"
    stale_key = f"recommendations:{timeframe}:last_success"

    hit = _get_cached(cache_key)
    if hit is not None:
        logger.info("Recommendations cache HIT")
        return jsonify(hit)

    # Single-flight guard: only one request builds recommendations at a time.
    build_lock_acquired = _recommendations_build_lock.acquire(blocking=False)
    if not build_lock_acquired:
        if _recommendations_build_lock.acquire(timeout=_RECOMMENDATIONS_WAIT_FOR_INFLIGHT_SECONDS):
            _recommendations_build_lock.release()
            hit = _get_cached(cache_key)
            if hit is not None:
                logger.info("Recommendations cache HIT after waiting for inflight build")
                return jsonify(hit)

        stale_payload = _get_cached(stale_key)
        if stale_payload is not None:
            logger.warning("Recommendations build still in progress, serving stale snapshot")
            return jsonify(_as_stale_recommendations(
                stale_payload,
                "Fresh recommendations are still being generated. Showing recent snapshot."
            ))

        return jsonify({
            "count": 0,
            "recommendations": [],
            "timeframe": timeframe,
            "strategies_used": strategies,
            "live": False,
            "stale": True,
            "message": "Recommendations are being generated. Please retry shortly.",
            "timestamp": datetime.datetime.now().isoformat(),
        }), 202

    logger.info("Building stock recommendations …")
    try:
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, wait, ALL_COMPLETED
        build_started = time.perf_counter()
        screening_started = time.perf_counter()
        screening_mode = "shared_multi_strategy"
        screening_ms = 0.0
        merge_rank_ms = 0.0
        enrichment_ms = 0.0
        enrichment_timeout_seconds = 0
        enrichment_skipped = False
        used_partial_db_fill = False
        partial_db_fill_count = 0
        shared_processed_tickers = 0
        shared_submitted_tickers = 0
        shared_requested_tickers = 0

        all_results = {s: [] for s in strategies}
        timed_out_strategies = []
        used_multi_strategy_engine = False

        # Fast path: shared parallel screening evaluates all strategies in one ticker pass.
        def _run_shared_multi_screening():
            return screener.run_multiple_strategies(
                strategies,
                max_results=_RECOMMENDATIONS_MAX_RESULTS,
                max_tickers=_RECOMMENDATIONS_MAX_TICKERS,
                time_budget_seconds=_RECOMMENDATIONS_SCREENING_BUDGET_SECONDS,
            )

        shared_pool = ThreadPoolExecutor(max_workers=1)
        try:
            shared_future = shared_pool.submit(_run_shared_multi_screening)
            try:
                shared_results = shared_future.result(timeout=_RECOMMENDATIONS_BUILD_TIMEOUT_SECONDS)
                if isinstance(shared_results, dict) and shared_results.get('status') == 'success':
                    raw_results = shared_results.get('results') or {}
                    for strat in strategies:
                        all_results[strat] = raw_results.get(strat, []) or []
                    shared_processed_tickers = int(shared_results.get('processed_tickers') or 0)
                    shared_submitted_tickers = int(shared_results.get('submitted_tickers') or 0)
                    shared_requested_tickers = int(shared_results.get('requested_tickers') or 0)
                    used_multi_strategy_engine = True
                    if shared_results.get('timed_out'):
                        timed_out_strategies = list(strategies)
                        screening_mode = "shared_multi_strategy_partial_timeout"
                    logger.info(
                        "Recommendations built via shared multi-strategy screener in %ss",
                        shared_results.get('execution_time', 'n/a'),
                    )
                else:
                    logger.warning(
                        "Shared multi-strategy recommendations run failed; falling back to per-strategy screens"
                    )
            except FuturesTimeoutError:
                timed_out_strategies = list(strategies)
                shared_future.cancel()
                screening_mode = "shared_multi_strategy_timeout"
                logger.warning("Shared multi-strategy recommendations run timed out")
        finally:
            shared_pool.shutdown(wait=False, cancel_futures=True)

        # Safe fallback path if shared engine fails for non-timeout reasons.
        if not used_multi_strategy_engine and not timed_out_strategies:
            screening_mode = "per_strategy_fallback"

            def _screen(name):
                try:
                    raw = screener._interactive.run_screening(name, max_results=_RECOMMENDATIONS_MAX_RESULTS)
                    return (name, raw.get('results', []) if raw.get('status') == 'success' else [])
                except Exception:
                    return (name, [])

            pool = ThreadPoolExecutor(max_workers=min(3, max(1, len(strategies))))
            try:
                futures = {pool.submit(_screen, s): s for s in strategies}
                done, not_done = wait(
                    futures,
                    timeout=_RECOMMENDATIONS_BUILD_TIMEOUT_SECONDS,
                    return_when=ALL_COMPLETED,
                )

                for f in done:
                    try:
                        name, results = f.result()
                    except Exception:
                        name, results = futures[f], []
                    all_results[name] = results

                for f in not_done:
                    timed_out_strategies.append(futures[f])
                    all_results[futures[f]] = []
                    f.cancel()
            finally:
                # Do not block request completion waiting for straggler tasks.
                pool.shutdown(wait=False, cancel_futures=True)

        screening_ms = (time.perf_counter() - screening_started) * 1000.0

        if timed_out_strategies:
            logger.warning(f"Recommendation screens timed out: {timed_out_strategies}")

        merge_rank_started = time.perf_counter()

        # Merge: count how many strategies picked each ticker + accumulate scores
        ticker_data = {}
        for strat, items in all_results.items():
            for item in items:
                t = item.get('ticker') or item.get('symbol', '')
                if not t:
                    continue
                if t not in ticker_data:
                    ticker_data[t] = {
                        'ticker': t,
                        'strategies': [],
                        'scores': [],
                        'price': item.get('close') or item.get('current_price') or item.get('price'),
                        'change_pct': item.get('change_pct') or item.get('returns_1m') or 0,
                        'volume': item.get('volume') or item.get('avg_volume') or 0,
                        'details': {},
                    }
                ticker_data[t]['strategies'].append(strat)
                # use any score the screener returned
                score = (
                    item.get('composite_score')
                    or item.get('momentum_score')
                    or item.get('score')
                    or item.get('total_score')
                    or 50
                )
                ticker_data[t]['scores'].append(float(score))
                ticker_data[t]['details'][strat] = {
                    k: v for k, v in item.items()
                    if k not in ('ticker', 'symbol')
                }

        ranked = []
        used_db_fallback = False

        if ticker_data:
            # Composite ranking: strategies_count * 30 + avg_score * 0.7
            for _, d in ticker_data.items():
                avg_score = sum(d['scores']) / len(d['scores']) if d['scores'] else 0
                d['confidence'] = round(len(d['strategies']) * 30 + avg_score * 0.7, 1)
                d['avg_score'] = round(avg_score, 2)
                d['strategy_count'] = len(d['strategies'])
                del d['scores']

            ranked = sorted(ticker_data.values(), key=lambda x: x['confidence'], reverse=True)[:10]

            # If screening timed out and produced too few results, top-up with fast DB fallback picks.
            if timed_out_strategies and len(ranked) < 10:
                required = 10 - len(ranked)
                supplement = _build_db_fallback_recommendations(
                    limit=required,
                    scan_limit=_RECOMMENDATIONS_DB_PARTIAL_FILL_SCAN_LIMIT,
                    exclude_tickers={r.get('ticker') for r in ranked},
                )
                if supplement:
                    used_partial_db_fill = True
                    partial_db_fill_count = len(supplement)
                    ranked.extend(supplement)
                    ranked = sorted(ranked, key=lambda x: x.get('confidence', 0), reverse=True)[:10]
                    logger.info(
                        "Supplemented partial recommendations with %s DB fallback candidates",
                        partial_db_fill_count,
                    )
        else:
            ranked = _build_db_fallback_recommendations(limit=10)
            used_db_fallback = len(ranked) > 0
            if used_db_fallback:
                logger.warning("Using DB fallback recommendations (strategy screens returned no candidates in time)")

        # Label confidence tiers
        for r in ranked:
            r['confidence_label'] = _confidence_label(float(r.get('confidence') or 0))

        merge_rank_ms = (time.perf_counter() - merge_rank_started) * 1000.0

        # ── Enrich top-10 with LIVE yfinance quotes (strategy-screen results only) ──
        if not used_db_fallback:
            elapsed_before_enrichment = time.perf_counter() - build_started
            remaining_budget_seconds = _RECOMMENDATIONS_TOTAL_TARGET_SECONDS - elapsed_before_enrichment

            if timed_out_strategies and _RECOMMENDATIONS_SKIP_ENRICH_ON_PARTIAL:
                enrichment_skipped = True
                for r in ranked:
                    r['live'] = False
                logger.info("Skipping recommendation enrichment for partial result set")
            elif remaining_budget_seconds <= max(0.5, _RECOMMENDATIONS_ENRICH_MIN_TIMEOUT_SECONDS):
                enrichment_skipped = True
                for r in ranked:
                    r['live'] = False
                logger.info(
                    "Skipping recommendation enrichment due to remaining budget %.2fs",
                    max(0.0, remaining_budget_seconds),
                )
            else:
                enrich_started = time.perf_counter()
                try:
                    # Partial screens prioritize response-time predictability over full quote enrichment.
                    enrich_limit = len(ranked)
                    if timed_out_strategies:
                        enrich_limit = min(len(ranked), max(1, _RECOMMENDATIONS_PARTIAL_ENRICH_LIMIT))

                    rec_tickers = [r['ticker'] for r in ranked[:enrich_limit]]
                    enrichment_timeout_seconds = int(max(
                        _RECOMMENDATIONS_ENRICH_MIN_TIMEOUT_SECONDS,
                        min(_RECOMMENDATIONS_ENRICH_MAX_TIMEOUT_SECONDS, remaining_budget_seconds),
                    ))

                    # Keep recommendations responsive: avoid slow per-ticker fallbacks.
                    live_quotes = _fetch_batch_quotes(
                        rec_tickers,
                        timeout_seconds=enrichment_timeout_seconds,
                        allow_individual_fallback=False,
                    )
                    for i, r in enumerate(ranked):
                        if i >= enrich_limit:
                            r['live'] = False
                            continue
                        lq = live_quotes.get(r['ticker'])
                        if lq and lq.get('price') and lq['price'] > 0:
                            r['price'] = lq['price']
                            r['change_pct'] = lq.get('change_pct', r.get('change_pct', 0))
                            r['change'] = lq.get('change', 0)
                            r['prev_close'] = lq.get('prev_close')
                            r['day_high'] = lq.get('day_high')
                            r['day_low'] = lq.get('day_low')
                            r['volume'] = lq.get('volume', r.get('volume', 0))
                            r['market_cap'] = lq.get('market_cap')
                            r['live'] = True
                        else:
                            r['live'] = False
                except Exception as enrich_err:
                    logger.warning(f"Failed to enrich recommendations with live data: {enrich_err}")
                finally:
                    enrichment_ms = (time.perf_counter() - enrich_started) * 1000.0

        total_ms = (time.perf_counter() - build_started) * 1000.0
        fallback_used = used_db_fallback or used_partial_db_fill

        payload = {
            "count": len(ranked),
            "recommendations": ranked,
            "timeframe": timeframe,
            "strategies_used": strategies,
            "partial": len(timed_out_strategies) > 0,
            "timed_out_strategies": timed_out_strategies,
            "fallback_used": fallback_used,
            "partial_db_fill_used": used_partial_db_fill,
            "partial_db_fill_count": partial_db_fill_count,
            "effective_source": (
                "database_fallback"
                if used_db_fallback
                else ("strategy_screens_with_db_fill" if used_partial_db_fill else "strategy_screens")
            ),
            "build_profile": {
                "screening_mode": screening_mode,
                "screening_ms": round(screening_ms, 2),
                "merge_rank_ms": round(merge_rank_ms, 2),
                "enrichment_ms": round(enrichment_ms, 2),
                "total_ms": round(total_ms, 2),
                "max_tickers": _RECOMMENDATIONS_MAX_TICKERS,
                "max_results": _RECOMMENDATIONS_MAX_RESULTS,
                "screening_budget_seconds": _RECOMMENDATIONS_SCREENING_BUDGET_SECONDS,
                "shared_processed_tickers": shared_processed_tickers,
                "shared_submitted_tickers": shared_submitted_tickers,
                "shared_requested_tickers": shared_requested_tickers,
                "enrichment_timeout_seconds": enrichment_timeout_seconds,
                "enrichment_skipped": enrichment_skipped,
                "partial_db_fill_count": partial_db_fill_count,
            },
            "live": True,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        logger.info(
            "Recommendations build complete: mode=%s, count=%s, fallback=%s, total=%.1fms (screen=%.1fms, merge=%.1fms, enrich=%.1fms)",
            screening_mode,
            len(ranked),
            fallback_used,
            total_ms,
            screening_ms,
            merge_rank_ms,
            enrichment_ms,
        )

        _set_cached(cache_key, payload, ttl=_RECOMMENDATIONS_CACHE_TTL_SECONDS)
        _set_cached(stale_key, payload, ttl=_RECOMMENDATIONS_STALE_TTL_SECONDS)
        return jsonify(payload)
    except Exception as e:
        logger.error(f"Recommendations error: {e}")

        stale_payload = _get_cached(stale_key)
        if stale_payload is not None:
            logger.warning("Serving stale recommendations due to build error")
            return jsonify(_as_stale_recommendations(
                stale_payload,
                "Live recommendations are temporarily unavailable. Showing recent snapshot."
            ))

        return jsonify({"error": str(e), "recommendations": [], "timeframe": timeframe}), 500
    finally:
        if build_lock_acquired:
            _recommendations_build_lock.release()


# ==================== PREDICTION ENDPOINTS ====================

def _sanitize_for_json(obj):
    """Recursively convert numpy/pandas types to JSON-safe Python natives."""
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, float) and (obj != obj or obj == float('inf') or obj == float('-inf')):
        return None  # NaN / Inf → null
    return obj


@app.route('/api/predict/<ticker>', methods=['POST'])
def predict_stock(ticker):
    """Generate AI prediction for a stock"""
    try:
        data = request.get_json() or {}
        capital = data.get('capital', 100000)
        risk_pct = data.get('risk_pct', 2.0)
        use_ensemble = data.get('use_ensemble', False)  # Kept for API compatibility, not used directly.

        normalized_ticker = _normalize_ticker_symbol(ticker)
        base_ticker = _base_ticker_symbol(normalized_ticker)

        prediction_candidates = []
        for candidate in (base_ticker, normalized_ticker):
            if candidate and candidate not in prediction_candidates:
                prediction_candidates.append(candidate)

        logger.info(
            f"Predicting {normalized_ticker}: capital={capital}, risk={risk_pct}, ensemble={use_ensemble}, candidates={prediction_candidates}"
        )

        # UnifiedStockPredictor has a global model; prediction is per-ticker.
        raw = None
        resolved_ticker = normalized_ticker
        last_error_payload = None

        for candidate in prediction_candidates:
            try:
                candidate_raw = predictor.predict(candidate, capital=float(capital), risk_pct=float(risk_pct))
            except Exception as pred_err:
                logger.warning(f"Prediction attempt failed for {candidate}: {pred_err}")
                last_error_payload = {"error": str(pred_err)}
                continue

            if isinstance(candidate_raw, dict) and "error" in candidate_raw:
                last_error_payload = candidate_raw
                continue

            raw = candidate_raw
            resolved_ticker = candidate
            break

        if raw is None:
            if isinstance(last_error_payload, dict):
                return jsonify(last_error_payload), 400
            return jsonify({"error": f"Prediction unavailable for {normalized_ticker}"}), 400

        # Adapt UnifiedStockPredictor output to the shape expected by the React UI.
        rec = raw.get("recommendation", {})
        price = raw.get("price_analysis", {})
        trade = raw.get("trade_setup", {})
        risk = raw.get("risk_management", {})
        patterns = raw.get("pattern_analysis", {})
        technicals = raw.get("technical_indicators", {})
        perf = raw.get("performance_metrics", {})

        # Build adapted response with all analysis layers
        detailed = raw.get("detailed_analysis", "")
        accuracy = raw.get("prediction_accuracy", {})
        rl_status = raw.get("rl_status", {})

        # Determine prediction type: 'ml' if model loaded, 'statistical' otherwise
        is_ml = predictor.model is not None
        pred_type = 'ml' if is_ml else 'statistical'

        # Fetch news sentiment for the prediction response (non-blocking)
        news_sentiment = None
        try:
            stock_news = news_aggregator.get_stock_news(resolved_ticker, limit=5, days_back=7)
            if stock_news and stock_news.get('articles'):
                news_sentiment = {
                    'overall_sentiment': stock_news.get('overall_sentiment', 'NEUTRAL'),
                    'sentiment_score': stock_news.get('aggregate', {}).get('sentiment_score', 0),
                    'article_count': stock_news.get('article_count', 0),
                    'articles': stock_news.get('articles', [])[:3],
                }
        except Exception:
            pass

        adapted = {
            "ticker": raw.get("ticker", resolved_ticker),
            "resolved_ticker": resolved_ticker,
            "model_version": raw.get("model_version", "14.0.0"),
            "model_artifact": raw.get("model_artifact", {}),
            "data_drift": raw.get("data_drift", {}),
            "signal_policy": raw.get("signal_policy", {}),
            "investor_action": raw.get("investor_action", {}),
            "prediction_type": pred_type,
            "signal": rec.get("signal"),
            "prediction_confidence": rec.get("signal_strength"),
            "direction_probability": rec.get("direction_probability"),
            "confidence_score": rec.get("confidence_score"),
            "min_confidence_threshold": rec.get("min_confidence_threshold"),
            "mc_uncertainty": rec.get("mc_uncertainty"),
            "current_price": price.get("current_price"),
            "predicted_price_5d": price.get("predicted_price_5d"),
            "buy_price": trade.get("buy_price"),
            "predicted_return_pct": price.get("expected_change_pct"),
            "expected_change": price.get("expected_change"),
            "predicted_volatility": price.get("predicted_volatility"),
            "historical_volatility_annual": price.get("historical_volatility_annual"),
            "atr_20": price.get("atr_20"),
            "prediction_uncertainty": price.get("prediction_uncertainty"),
            "confidence_interval": price.get("confidence_interval"),
            "price_prediction_note": price.get("price_prediction_note"),
            "stop_loss": trade.get("stop_loss"),
            "target_price": trade.get("target_price"),
            "risk_reward_ratio": trade.get("risk_reward_ratio"),
            "atr_sl_distance": trade.get("atr_sl_distance"),
            "atr_tp_distance": trade.get("atr_tp_distance"),
            "trade_method": trade.get("method"),
            "suggested_quantity": risk.get("suggested_quantity"),
            "trade_value": risk.get("position_size"),
            "position_pct_of_capital": risk.get("position_pct_of_capital"),
            "kelly_fraction_full": risk.get("kelly_fraction_full"),
            "kelly_fraction_used": risk.get("kelly_fraction_used"),
            "max_loss_amount": risk.get("max_loss_amount"),
            "risk_per_share": risk.get("risk_per_share"),
            "reward_per_share": risk.get("reward_per_share"),
            "sizing_method": risk.get("sizing_method"),
            # Pattern analysis (Patent-Pending CPCS Engine)
            "pattern_analysis": {
                "patterns_detected": patterns.get("patterns_detected", []),
                "pattern_count": patterns.get("pattern_count", 0),
                "confluence_score": patterns.get("confluence_score", 0),
                "pattern_agreement": patterns.get("pattern_agreement", 0),
                "dominant_pattern_signal": patterns.get("dominant_pattern_signal", "NEUTRAL"),
                "support_levels": patterns.get("support_levels", []),
                "resistance_levels": patterns.get("resistance_levels", []),
                "trend_strength": patterns.get("trend_strength", 50),
                "pattern_summary": patterns.get("pattern_summary", ""),
            },
            # Technical indicators snapshot
            "technical_indicators": technicals,
            # Model performance metrics
            "performance_metrics": perf,
            # Enhanced analysis
            "detailed_analysis": detailed,
            "prediction_accuracy": accuracy,
            "rl_status": rl_status,
            # News sentiment
            "news_sentiment": news_sentiment,
            # v14: Risk disclaimer (mandatory for real-world usage)
            "disclaimer": raw.get("disclaimer", {}),
        }

        return jsonify(_sanitize_for_json(adapted))
    except Exception as e:
        logger.error(f"Prediction error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/train/<ticker>', methods=['POST'])
@rate_limit
def train_model(ticker):
    """Trigger model training/fine-tune for a specific ticker."""
    try:
        logger.info(f"Training model for {ticker}")
        # UnifiedStockPredictor.train() retrains the global model using all
        # available data.  The ticker hint is logged but the model is universal.
        result = predictor.train()
        predictor._load_model()
        model_path = predictor._get_paths()[0]
        return jsonify({
            "status": "success",
            "message": f"Model training completed for {ticker}",
            "details": result if isinstance(result, dict) else {"info": str(result)},
            "model_version": getattr(predictor, "_model_version", None),
            "model_path": model_path,
        })
    except Exception as e:
        logger.error(f"Training error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/model/info', methods=['GET'])
@rate_limit
def model_info():
    """Get ML model status, age, accuracy, and training metadata."""
    try:
        predictor._reload_model_if_updated()
        model_path, scaler_path, target_path, feature_path, metrics_path = predictor._get_paths()
        
        model_trained = os.path.exists(model_path) and os.path.exists(scaler_path)
        loaded_mtime = getattr(predictor, "_loaded_model_mtime", None)
        
        info = {
            "status": "trained" if model_trained else "untrained",
            "model_exists": model_trained,
            "model_version": getattr(predictor, "_model_version", None),
            "artifacts": {
                "artifact_base_dir": os.path.dirname(os.path.dirname(model_path)),
                "model_path": model_path,
                "feature_scaler_path": scaler_path,
                "target_scalers_path": target_path,
                "feature_cols_path": feature_path,
                "metrics_path": metrics_path,
                "loaded_model_path": getattr(predictor, "_loaded_model_path", None),
                "loaded_model_mtime": loaded_mtime,
                "loaded_model_timestamp": (
                    datetime.datetime.fromtimestamp(loaded_mtime).isoformat()
                    if loaded_mtime else None
                ),
            },
        }
        
        if model_trained:
            # Model age
            model_mtime = os.path.getmtime(model_path)
            model_age_hours = (time.time() - model_mtime) / 3600
            info["model_age_hours"] = round(model_age_hours, 1)
            info["last_trained"] = datetime.datetime.fromtimestamp(model_mtime).isoformat()
            
            # Training metrics (stored via joblib)
            if os.path.exists(metrics_path):
                try:
                    import joblib as _jl
                    metrics_data = _jl.load(metrics_path)
                    info["metrics"] = metrics_data
                except Exception:
                    try:
                        with open(metrics_path, 'r') as f:
                            info["metrics"] = json.load(f)
                    except Exception:
                        info["metrics"] = predictor._get_training_metrics_summary()
            
            # RL feedback stats
            rl_status = predictor.get_rl_status()
            info["rl_feedback"] = rl_status
        else:
            info["message"] = (
                "Model not trained yet. Training runs automatically at 4:00 PM IST "
                "after daily data update. Predictions will use statistical fallback "
                "until the model is ready."
            )
        
        return jsonify(info)
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== REAL-TIME PRICE TARGETS ====================

@app.route('/api/price-target/<ticker>', methods=['GET', 'POST'])
@rate_limit
def get_price_target(ticker):
    """
    Get real-time price target, buy price, stop loss, and risk/reward ratio
    for a stock based on ML prediction.
    
    Query params:
    - capital: Investment capital (default 100000)
    - risk_pct: Risk percentage per trade (default 2.0)
    
    Returns:
    - current_price: Current market price
    - predicted_price: ML predicted future price
    - target_price: Target selling price
    - buy_price: Recommended entry price
    - stop_loss: Stop loss price
    - risk_reward_ratio: Risk to reward ratio
    - signal: BUY/SELL/HOLD
    - confidence: Confidence score (0-100)
    """
    try:
        capital = float(request.args.get('capital', 100000))
        risk_pct = float(request.args.get('risk_pct', 2.0))
        normalized_ticker = _base_ticker_symbol(ticker)
        
        logger.info(f"Fetching price target for {normalized_ticker}")
        
        # Get ML prediction
        pred = predictor.predict(normalized_ticker, capital=capital, risk_pct=risk_pct)
        
        if "error" in pred:
            return jsonify({"error": pred["error"]}), 400
        
        # Extract relevant data from multi-target prediction
        rec = pred.get("recommendation", {})
        price = pred.get("price_analysis", {})
        trade = pred.get("trade_setup", {})
        risk = pred.get("risk_management", {})
        patterns = pred.get("pattern_analysis", {})
        
        current_price = price.get("current_price", 0)
        predicted_price = price.get("predicted_price_5d", current_price)
        target_price = trade.get("target_price", current_price * 1.1)
        stop_loss = trade.get("stop_loss", current_price * 0.95)
        buy_price = trade.get("buy_price", current_price)
        reward_risk_ratio = trade.get("risk_reward_ratio", 0)
        
        # Validate data
        if reward_risk_ratio == float('inf') or reward_risk_ratio < 0:
            reward_risk_ratio = 0
        
        return jsonify({
            "status": "success",
            "ticker": normalized_ticker,
            "timestamp": datetime.datetime.now().isoformat(),
            "model_version": pred.get("model_version", "34.0.0"),
            "model_artifact": pred.get("model_artifact", {}),
            "data_drift": pred.get("data_drift", {}),
            "signal_policy": pred.get("signal_policy", {}),
            "price_analysis": {
                "current_price": round(current_price, 2),
                "predicted_price_5d": round(predicted_price, 2),
                "predicted_change_pct": round(
                    ((predicted_price - current_price) / current_price * 100) if current_price > 0 else 0, 2
                ),
                "volatility": round(price.get("predicted_volatility", 0), 4),
                "prediction_uncertainty": price.get("prediction_uncertainty", 0),
                "confidence_interval": price.get("confidence_interval", {}),
            },
            "trade_setup": {
                "signal": rec.get("signal", "HOLD"),
                "signal_strength": rec.get("signal_strength", "LOW"),
                "buy_price": round(buy_price, 2),
                "target_price": round(target_price, 2),
                "stop_loss": round(stop_loss, 2),
                "risk_reward_ratio": round(reward_risk_ratio, 2),
                "ml_predicted_rr": trade.get("ml_predicted_rr", 0),
                "position_size": int(risk.get("suggested_quantity", 0)),
                "method": trade.get("method", "ATR-rule-based"),
            },
            "confidence": {
                "prediction_confidence": rec.get("signal_strength", "LOW"),
                "direction_probability": rec.get("direction_probability", 50),
                "confidence_score": rec.get("confidence_score", 50),
                "signal_quality": rec.get("signal_quality", "NEUTRAL"),
                "mc_uncertainty": rec.get("mc_uncertainty", 0),
            },
            "risk_management": {
                "capital_at_risk": round(capital * (risk_pct / 100), 2),
                "max_loss": round(risk.get("max_loss_amount", 0), 2),
                "trade_value": round(risk.get("position_size", 0), 2),
                "risk_per_share": risk.get("risk_per_share", 0),
                "reward_per_share": risk.get("reward_per_share", 0),
                "position_pct_of_capital": risk.get("position_pct_of_capital", 0),
                "kelly_fraction_used": risk.get("kelly_fraction_used", 0),
                "sizing_method": risk.get("sizing_method", "Kelly"),
            },
            "pattern_analysis": {
                "patterns_detected": patterns.get("patterns_detected", []),
                "pattern_count": patterns.get("pattern_count", 0),
                "confluence_score": patterns.get("confluence_score", 0),
                "dominant_signal": patterns.get("dominant_pattern_signal", "NEUTRAL"),
                "support_levels": patterns.get("support_levels", []),
                "resistance_levels": patterns.get("resistance_levels", []),
            },
            # v33: Quantitative Finance Enhancements
            "confidence_index": pred.get("confidence_index", {}),
            "market_regime": pred.get("market_regime", {}),
            "momentum_factor": pred.get("momentum_factor", {}),
            "ensemble_prediction": pred.get("ensemble_prediction", {}),
            "mvo_sizing": pred.get("mvo_sizing", {}),
            "investor_action": pred.get("investor_action", {}),
            "signal_lifecycle": pred.get("signal_lifecycle", {}),
            "execution_plan": pred.get("execution_plan", {}),
            "disclaimer": pred.get("disclaimer", {}),
            # v34: 5-Pillar Quantitative Intelligence
            "v34_quant_intelligence": pred.get("v34_quant_intelligence", {}),
        })
        
    except Exception as e:
        logger.error(f"Error fetching price target for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/price-targets/batch', methods=['POST'])
@rate_limit
def get_batch_price_targets():
    """
    Get price targets for multiple stocks in batch
    
    Body params:
    - tickers: List of ticker symbols
    - capital: Investment capital per stock (default 100000)
    - risk_pct: Risk percentage per trade (default 2.0)
    """
    try:
        data = request.get_json() or {}
        tickers = data.get('tickers', [])
        capital = float(data.get('capital', 100000))
        risk_pct = float(data.get('risk_pct', 2.0))
        
        if not tickers:
            return jsonify({"error": "tickers list is required"}), 400
        
        logger.info(f"Fetching price targets for {len(tickers)} stocks")
        
        targets = []
        errors = []
        
        for ticker in tickers:
            normalized_ticker = _base_ticker_symbol(ticker)
            try:
                pred = predictor.predict(normalized_ticker, capital=capital, risk_pct=risk_pct)
                
                if "error" in pred:
                    errors.append({"ticker": normalized_ticker, "error": pred["error"]})
                    continue
                
                rec = pred.get("recommendation", {})
                price = pred.get("price_analysis", {})
                trade = pred.get("trade_setup", {})
                risk = pred.get("risk_management", {})
                patterns = pred.get("pattern_analysis", {})
                
                current_price = price.get("current_price", 0)
                predicted_price = price.get("predicted_price_5d", current_price)
                target_price = trade.get("target_price", current_price * 1.1)
                stop_loss = trade.get("stop_loss", current_price * 0.95)
                buy_price = trade.get("buy_price", current_price)
                reward_risk_ratio = trade.get("risk_reward_ratio", 0)
                
                targets.append({
                    "ticker": normalized_ticker,
                    "model_version": pred.get("model_version", "34.0.0"),
                    "model_artifact": pred.get("model_artifact", {}),
                    "signal": rec.get("signal", "HOLD"),
                    "current_price": round(current_price, 2),
                    "predicted_price_5d": round(predicted_price, 2),
                    "target_price": round(target_price, 2),
                    "buy_price": round(buy_price, 2),
                    "stop_loss": round(stop_loss, 2),
                    "risk_reward_ratio": round(reward_risk_ratio, 2),
                    "confidence": rec.get("signal_strength", "LOW"),
                    "direction_probability": rec.get("direction_probability", 50),
                    "data_drift": pred.get("data_drift", {}),
                    "signal_policy": pred.get("signal_policy", {}),
                    "pattern_count": patterns.get("pattern_count", 0),
                    "confluence_score": patterns.get("confluence_score", 0),
                    "position_size": int(risk.get("suggested_quantity", 0))
                })
                
            except Exception as e:
                logger.warning(f"Error fetching target for {ticker}: {e}")
                errors.append({"ticker": normalized_ticker, "error": str(e)})
        
        return jsonify({
            "status": "success",
            "count": len(targets),
            "targets": targets,
            "errors_count": len(errors),
            "errors": errors,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Batch price targets error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/price-target/<ticker>/levels', methods=['GET'])
@rate_limit
def get_price_levels(ticker):
    """
    Get multiple price targets (support/resistance levels, bollinger bands, etc.)
    
    Returns multiple price levels for technical analysis
    """
    try:
        logger.info(f"Fetching price levels for {ticker}")
        
        # Get data from database
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return jsonify({"error": f"No data found for {ticker}"}), 404
        
        # Convert to list if needed
        if not isinstance(ticker_data, list):
            ticker_data = ticker_data.fetchall() if hasattr(ticker_data, 'fetchall') else list(ticker_data)
        
        if isinstance(ticker_data, list) and len(ticker_data) > 0:
            # Get latest price
            latest = ticker_data[-1]
            current_price = float(latest.get('close', 0)) if hasattr(latest, 'get') else latest[4]
            
            # Calculate price levels from recent data
            prices = [float(r.get('close', 0) if hasattr(r, 'get') else r[4]) for r in ticker_data[-50:]]
            
            high_50d = max(prices) if prices else current_price
            low_50d = min(prices) if prices else current_price
            sma_20 = sum(prices[-20:]) / len(prices[-20:]) if len(prices) >= 20 else current_price
            
            return jsonify({
                "status": "success",
                "ticker": ticker,
                "current_price": round(current_price, 2),
                "levels": {
                    "support_1": round(low_50d, 2),
                    "support_2": round(low_50d * 0.95, 2),
                    "pivot": round((high_50d + low_50d) / 2, 2),
                    "resistance_1": round(high_50d, 2),
                    "resistance_2": round(high_50d * 1.05, 2),
                    "sma_20": round(sma_20, 2)
                },
                "technical": {
                    "52_week_high": round(high_50d * 1.3, 2),  # Estimated
                    "52_week_low": round(low_50d * 0.7, 2),   # Estimated
                    "monthly_range": {
                        "high": round(high_50d, 2),
                        "low": round(low_50d, 2)
                    }
                }
            })
        else:
            return jsonify({"error": "Insufficient data"}), 400
            
    except Exception as e:
        logger.error(f"Error fetching price levels for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== DATA QUALITY & ANALYTICS ENDPOINTS ====================

@app.route('/api/data-quality/report', methods=['GET'])
@rate_limit
def get_data_quality_report():
    """Get comprehensive data quality report"""
    try:
        limit_tickers = request.args.get('limit_tickers', None, type=int)
        report = pipeline.get_data_quality_report(limit_tickers=limit_tickers)
        return jsonify({
            "status": "success",
            **report
        })
    except Exception as e:
        logger.error(f"Error getting data quality report: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/data-quality/reconcile', methods=['POST'])
@rate_limit
def reconcile_data_quality():
    """Reconcile and fix data quality issues"""
    try:
        data = request.get_json() or {}
        ticker = data.get('ticker')  # Optional - reconcile specific ticker or all
        
        result = pipeline.reconcile_data(ticker=ticker)
        return jsonify({
            "status": "success",
            **result
        })
    except Exception as e:
        logger.error(f"Error reconciling data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stocks/gaps/<ticker>', methods=['GET'])
@rate_limit
def detect_trading_gaps(ticker):
    """Detect trading gaps for a specific ticker"""
    try:
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return jsonify({"error": f"No data found for {ticker}"}), 404
        
        import pandas as pd
        df = pd.DataFrame([dict(row) if hasattr(row, 'keys') else row._asdict() for row in ticker_data])
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
        
        gaps = pipeline._detect_trading_gaps(df)
        
        return jsonify({
            "status": "success",
            "ticker": ticker,
            "gaps_detected": len(gaps.get(ticker, [])),
            "gap_dates": gaps.get(ticker, [])
        })
    except Exception as e:
        logger.error(f"Error detecting gaps for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stocks/validation/<ticker>', methods=['GET'])
@rate_limit
def validate_stock_data(ticker):
    """Validate data quality for a specific ticker"""
    try:
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return jsonify({"error": f"No data found for {ticker}"}), 404
        
        import pandas as pd
        df = pd.DataFrame([dict(row) if hasattr(row, 'keys') else row._asdict() for row in ticker_data])
        
        metrics = pipeline._get_data_quality_metrics(df, ticker=ticker)
        
        return jsonify({
            "status": "success",
            "ticker": ticker,
            **metrics
        })
    except Exception as e:
        logger.error(f"Error validating data for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== FEATURE ENGINEERING QUALITY ENDPOINTS ====================

@app.route('/api/features/quality-report', methods=['GET'])
@rate_limit
def get_feature_quality_report():
    """Get comprehensive feature engineering quality report"""
    try:
        limit_tickers = request.args.get('limit_tickers', 50, type=int)
        
        from FeatureEngineering import PipelineOrchestrator
        feature_orch = PipelineOrchestrator(
            "postgresql://postgres:Taran%4017@localhost:5432/StockDB"
        )
        
        report = feature_orch.get_feature_quality_report(limit_tickers=limit_tickers)
        
        return jsonify({
            "status": "success",
            "timestamp": datetime.datetime.now().isoformat(),
            **report
        })
    except Exception as e:
        logger.error(f"Error generating feature quality report: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/features/validate/<ticker>', methods=['GET'])
@rate_limit
def validate_ticker_features(ticker):
    """Validate engineered features for a specific ticker"""
    try:
        from FeatureEngineering import PipelineOrchestrator
        feature_orch = PipelineOrchestrator(
            "postgresql://postgres:Taran%4017@localhost:5432/StockDB"
        )
        
        validation_result = feature_orch.validate_feature_consistency(ticker)
        
        return jsonify({
            "status": "success",
            "timestamp": datetime.datetime.now().isoformat(),
            **validation_result
        })
    except Exception as e:
        logger.error(f"Error validating features for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/features/quality/<ticker>', methods=['GET'])
@rate_limit
def get_ticker_feature_quality(ticker):
    """Get feature quality metrics for a specific ticker with trend analysis"""
    try:
        from FeatureEngineering import PipelineOrchestrator
        feature_orch = PipelineOrchestrator(
            "postgresql://postgres:Taran%4017@localhost:5432/StockDB"
        )
        
        with feature_orch.engine.connect() as conn:
            from sqlalchemy import text
            
            # Get feature stats for the ticker
            query = text("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN rsi_14 IS NOT NULL THEN 1 END) as rsi_records,
                    COUNT(CASE WHEN hist_vol_20 IS NOT NULL THEN 1 END) as volatility_records,
                    COUNT(CASE WHEN sma_20 IS NOT NULL THEN 1 END) as sma_records,
                    COUNT(CASE WHEN ema_20 IS NOT NULL THEN 1 END) as ema_records,
                    COUNT(CASE WHEN atr_14 IS NOT NULL THEN 1 END) as atr_records,
                    MIN(rsi_14) as min_rsi,
                    MAX(rsi_14) as max_rsi,
                    AVG(rsi_14) as avg_rsi,
                    AVG(hist_vol_20) as avg_volatility
                FROM engineered_features 
                WHERE ticker = :ticker
            """)
            
            result = conn.execute(query, {'ticker': ticker}).fetchone()
            
            if not result or result[0] == 0:
                return jsonify({"error": f"No engineered features found for {ticker}"}), 404
            
            total, rsi_cnt, vol_cnt, sma_cnt, ema_cnt, atr_cnt, min_rsi, max_rsi, avg_rsi, avg_vol = result
            
            quality_pct = (rsi_cnt + vol_cnt + sma_cnt + ema_cnt + atr_cnt) / (5 * total) * 100 if total > 0 else 0
            
            return jsonify({
                "status": "success",
                "ticker": ticker,
                "total_records": total,
                "quality_percentage": round(quality_pct, 2),
                "quality_status": "EXCELLENT" if quality_pct >= 95 else "GOOD" if quality_pct >= 80 else "NEEDS_ATTENTION",
                "features": {
                    "rsi_14": {"calculated": rsi_cnt, "percentage": round(rsi_cnt * 100 / total, 2) if total > 0 else 0, "avg": round(avg_rsi, 2) if avg_rsi else None, "range": [round(min_rsi, 2) if min_rsi else None, round(max_rsi, 2) if max_rsi else None]},
                    "volatility_20": {"calculated": vol_cnt, "percentage": round(vol_cnt * 100 / total, 2) if total > 0 else 0, "avg": round(avg_vol, 2) if avg_vol else None},
                    "sma_20": {"calculated": sma_cnt, "percentage": round(sma_cnt * 100 / total, 2) if total > 0 else 0},
                    "ema_20": {"calculated": ema_cnt, "percentage": round(ema_cnt * 100 / total, 2) if total > 0 else 0},
                    "atr_14": {"calculated": atr_cnt, "percentage": round(atr_cnt * 100 / total, 2) if total > 0 else 0}
                }
            })
    except Exception as e:
        logger.error(f"Error getting feature quality for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== UTILITY ENDPOINTS ====================

def _build_health_snapshot() -> dict:
    db_status = "connected"
    db_error = None
    try:
        pipeline.get_latest_data(limit=1)
    except Exception as exc:
        db_status = "degraded"
        db_error = str(exc)

    scheduler_running = bool(getattr(data_scheduler, 'is_running', False)) if 'data_scheduler' in globals() else False
    predictor_ready = bool(getattr(predictor, 'model', None)) if 'predictor' in globals() else False

    components = {
        "pipeline": "active" if 'pipeline' in globals() else "missing",
        "predictor": "ready" if predictor_ready else "warming",
        "scheduler": "running" if scheduler_running else "idle",
        "portfolio": "active" if 'portfolio_manager' in globals() else "missing",
    }

    overall_status = "healthy" if db_status == "connected" else "degraded"
    return {
        "status": overall_status,
        "environment": APP_ENV,
        "debug": APP_DEBUG,
        "database": db_status,
        "database_error": db_error,
        "components": components,
        "uptime_seconds": round(time.time() - APP_STARTED_AT, 2),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "request_id": getattr(g, 'request_id', None),
    }

@app.route('/api/health', methods=['GET'])
def health_check():
    """Detailed system health snapshot for monitoring dashboards."""
    snapshot = _build_health_snapshot()
    return jsonify(snapshot), (200 if snapshot["status"] == "healthy" else 503)


@app.route('/api/health/live', methods=['GET'])
def health_live():
    """Kubernetes-style liveness probe: process is alive."""
    return jsonify({
        "status": "alive",
        "uptime_seconds": round(time.time() - APP_STARTED_AT, 2),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "request_id": getattr(g, 'request_id', None),
    }), 200


@app.route('/api/health/ready', methods=['GET'])
def health_ready():
    """Readiness probe: core dependencies (db/pipeline) are reachable."""
    snapshot = _build_health_snapshot()
    ready = snapshot.get("database") == "connected" and snapshot.get("components", {}).get("pipeline") == "active"
    payload = {
        "status": "ready" if ready else "not_ready",
        "database": snapshot.get("database"),
        "components": snapshot.get("components"),
        "timestamp": snapshot.get("timestamp"),
        "request_id": snapshot.get("request_id"),
    }
    return jsonify(payload), (200 if ready else 503)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get database statistics"""
    try:
        stocks = pipeline.get_latest_data(limit=None)
        return jsonify({
            "total_stocks": len(stocks),
            "database": "operational",
            "environment": APP_ENV,
            "uptime_seconds": round(time.time() - APP_STARTED_AT, 2),
            "request_id": getattr(g, 'request_id', None),
        })
    except Exception as e:
        return _api_error_response("Failed to collect stats", 500, code="STATS_UNAVAILABLE", details=str(e))

# ==================== BACKTESTING ENDPOINTS ====================

@app.route('/api/backtest/<strategy>', methods=['POST'])
@rate_limit
def backtest_strategy(strategy):
    """
    Backtest a screening strategy using the universal BacktestEngine.
    
    Body params:
    - ticker: Stock ticker to backtest on (required)
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - initial_capital: Starting capital
    - sizing_mode: Position sizing mode (fixed_pct, risk_based, fixed_qty, equal_weight)
    - use_atr_stops: Enable ATR-based stops
    - use_trailing_stop: Enable trailing stop
    - strategy_params: Strategy-specific parameters
    """
    try:
        data = request.get_json() or {}
        
        ticker = data.get('ticker', 'NIFTY')
        start_date = data.get('start_date', '2023-01-01')
        end_date = data.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
        initial_capital = data.get('initial_capital', 100000)
        sizing_mode_str = data.get('sizing_mode', 'risk_based')
        use_atr_stops = data.get('use_atr_stops', True)
        use_trailing_stop = data.get('use_trailing_stop', False)
        
        logger.info(f"Backtesting {strategy} on {ticker} from {start_date} to {end_date}")
        
        # Build config
        sizing_map = {
            'risk_based': PositionSizingMode.RISK_BASED,
            'volatility_adjusted': PositionSizingMode.VOLATILITY_ADJUSTED,
            'fixed_dollar': PositionSizingMode.FIXED_DOLLAR,
            'portfolio_heat': PositionSizingMode.PORTFOLIO_HEAT,
        }
        config = BacktestConfig(
            initial_capital=float(initial_capital),
            sizing_mode=sizing_map.get(sizing_mode_str, PositionSizingMode.RISK_BASED),
            use_atr_stops=use_atr_stops,
            use_trailing_stop=use_trailing_stop,
        )
        engine = BacktestEngine(data_pipeline=pipeline, config=config)
        
        # Fetch price data
        import pandas as pd
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return jsonify({"error": f"No data found for {ticker}"}), 404
        
        price_data = pd.DataFrame([dict(row) for row in ticker_data])
        if 'date' in price_data.columns:
            price_data['date'] = pd.to_datetime(price_data['date'])
            price_data = price_data[
                (price_data['date'] >= start_date) & (price_data['date'] <= end_date)
            ]
        
        if price_data.empty or len(price_data) < 50:
            return jsonify({"error": f"Insufficient data for {ticker} in date range"}), 400
        
        # Generate signals based on strategy
        # Check if this is a custom strategy first
        _predefined = {
            'momentum', 'breakout', 'swing', 'mean_reversion', 'trend_following',
            'piotroski', 'value', 'garp', 'quality_dividend', 'contrarian', 'quality_growth'
        }
        if strategy.lower() in _predefined:
            signals = _generate_strategy_signals(strategy, price_data, data.get('strategy_params', {}))
        else:
            # Try loading as custom strategy
            import json as _json_bt
            _cfile = 'data/custom_strategies.json'
            _cstrats = []
            if os.path.exists(_cfile):
                try:
                    with open(_cfile, 'r') as _f:
                        _cstrats = _json_bt.load(_f)
                except Exception:
                    pass
            _cmap = {s['name'].lower(): s for s in _cstrats}
            if strategy.lower() in _cmap:
                signals = _generate_custom_strategy_signals(
                    _cmap[strategy.lower()].get('conditions', []), price_data
                )
            else:
                signals = _generate_strategy_signals(strategy, price_data, data.get('strategy_params', {}))
        
        # Run backtest
        result = engine.backtest_strategy(signals, price_data, strategy_name=strategy)
        
        # Use model's built-in serialisation, then overlay extra context
        result_dict = result.to_dict()
        # Alias fields that the frontend expects
        result_dict["final_value"] = result_dict.get("final_capital", 0)
        result_dict["max_drawdown"] = result_dict.get("max_drawdown_pct", 0)
        result_dict["win_rate"] = result_dict.get("win_rate_pct", 0)
        result_dict["avg_trade_pnl"] = result_dict.get("expectancy_per_trade", 0)
        result_dict["annualized_return"] = result_dict.get("annualized_return_pct", 0)
        result_dict["cagr"] = result_dict.get("cagr_pct", 0)
        result_dict["avg_holding_days"] = result_dict.get("average_holding_days", 0)
        result_dict.update({
            "status": "success",
            "strategy": strategy,
            "ticker": ticker,
        })
        return jsonify(result_dict)
        
    except Exception as e:
        logger.error(f"Backtest error for {strategy}: {e}")
        return jsonify({"error": str(e)}), 500


def _compute_rsi(series, period=14):
    """Compute RSI."""
    import numpy as np
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = -delta.where(delta < 0, 0).rolling(period).mean()
    rs = gain / (loss + 1e-8)
    return 100 - (100 / (1 + rs))


def _compute_macd(series, fast=12, slow=26, signal=9):
    """Compute MACD line, signal line, histogram."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _compute_bollinger(series, period=20, std_dev=2):
    """Compute Bollinger Bands."""
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, sma, lower


def _compute_adx(high, low, close, period=14):
    """Compute ADX (Average Directional Index)."""
    import numpy as np
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(period, min_periods=1).mean()
    plus_di = 100 * (plus_dm.rolling(period, min_periods=1).mean() / (atr + 1e-8))
    minus_di = 100 * (minus_dm.rolling(period, min_periods=1).mean() / (atr + 1e-8))
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-8)
    adx = dx.rolling(period, min_periods=1).mean()
    return adx, plus_di, minus_di


def _generate_strategy_signals(strategy: str, price_data, strategy_params: dict[str, object] | None = None):
    """
    Generate trading signals for a given strategy name.
    Each strategy uses a distinct, well-known technical approach so
    backtesting comparisons produce genuinely different results.
    """
    import pandas as pd
    import numpy as np

    params = strategy_params or {}
    df = price_data.copy()
    df['signal'] = 0

    # ── 1. Momentum ─────────────────────────────────────────
    #    Rate-of-change + RSI confirmation
    if strategy == 'momentum':
        lookback = params.get('lookback_days', 20)
        df['roc'] = df['close'].pct_change(lookback)
        df['rsi'] = _compute_rsi(df['close'], 14)
        df.loc[(df['roc'] > 0.05) & (df['rsi'] > 50) & (df['rsi'] < 80), 'signal'] = 1
        df.loc[(df['roc'] < -0.05) & (df['rsi'] < 50), 'signal'] = -1

    # ── 2. Breakout ─────────────────────────────────────────
    #    Donchian channel breakout with volume confirmation
    elif strategy == 'breakout':
        period = params.get('period', 20)
        vol_mult = params.get('volume_threshold', 1.5)
        df['high_n'] = df['high'].rolling(period).max()
        df['low_n'] = df['low'].rolling(period).min()
        df['avg_vol'] = df['volume'].rolling(20, min_periods=1).mean()
        df['vol_ratio'] = df['volume'] / (df['avg_vol'] + 1)
        df.loc[(df['close'] > df['high_n'].shift(1)) & (df['vol_ratio'] > vol_mult), 'signal'] = 1
        df.loc[df['close'] < df['low_n'].shift(1), 'signal'] = -1

    # ── 3. Swing ────────────────────────────────────────────
    #    RSI mean-reversion at extremes + MACD momentum confirmation
    elif strategy == 'swing':
        df['rsi'] = _compute_rsi(df['close'], 14)
        _, _, macd_hist = _compute_macd(df['close'])
        df['macd_hist'] = macd_hist
        df.loc[(df['rsi'] < 30) & (df['macd_hist'] > df['macd_hist'].shift(1)), 'signal'] = 1
        df.loc[(df['rsi'] > 70) & (df['macd_hist'] < df['macd_hist'].shift(1)), 'signal'] = -1

    # ── 4. Mean Reversion ───────────────────────────────────
    #    Bollinger Band reversion + RSI confirmation
    elif strategy == 'mean_reversion':
        df['rsi'] = _compute_rsi(df['close'], 14)
        bb_upper, bb_mid, bb_lower = _compute_bollinger(df['close'], 20, 2)
        df['bb_upper'] = bb_upper
        df['bb_lower'] = bb_lower
        df['bb_mid'] = bb_mid
        df.loc[(df['close'] < df['bb_lower']) & (df['rsi'] < 35), 'signal'] = 1
        df.loc[(df['close'] > df['bb_upper']) & (df['rsi'] > 65), 'signal'] = -1

    # ── 5. Trend Following ──────────────────────────────────
    #    Dual SMA crossover (50/200 Golden-/Death-cross) + ADX trend filter
    elif strategy == 'trend_following':
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        adx, _, _ = _compute_adx(df['high'], df['low'], df['close'])
        df['adx'] = adx
        df.loc[(df['sma_50'] > df['sma_200']) & (df['adx'] > 20), 'signal'] = 1
        df.loc[(df['sma_50'] < df['sma_200']) & (df['adx'] > 20), 'signal'] = -1

    # ── 6. Piotroski / F-Score proxy ────────────────────────
    #    Since we only have price/volume data, approximate with:
    #    Positive ROC (profitability proxy) + rising volume (operating cash flow proxy)
    #    + price > SMA200 (asset turnover proxy)
    elif strategy == 'piotroski':
        df['roc_60'] = df['close'].pct_change(60)
        df['roc_20'] = df['close'].pct_change(20)
        df['sma_200'] = df['close'].rolling(200).mean()
        df['vol_trend'] = df['volume'].rolling(20).mean() / (df['volume'].rolling(60).mean() + 1)
        # F-score proxy: price > SMA200, positive 60d return, rising volume, positive short momentum
        f_buy = (
            (df['close'] > df['sma_200']) &
            (df['roc_60'] > 0) &
            (df['vol_trend'] > 1.0) &
            (df['roc_20'] > 0)
        )
        f_sell = (
            (df['close'] < df['sma_200']) &
            (df['roc_60'] < 0)
        )
        df.loc[f_buy, 'signal'] = 1
        df.loc[f_sell, 'signal'] = -1

    # ── 7. Value ────────────────────────────────────────────
    #    Buy near 52-week low with improving momentum (deep value + catalyst)
    elif strategy == 'value':
        df['low_252'] = df['low'].rolling(252, min_periods=50).min()
        df['dist_from_low'] = (df['close'] - df['low_252']) / (df['low_252'] + 1e-8)
        df['rsi'] = _compute_rsi(df['close'], 14)
        df['roc_5'] = df['close'].pct_change(5)
        # Buy: within 10% of 52w low but short-term momentum turning positive
        df.loc[(df['dist_from_low'] < 0.10) & (df['roc_5'] > 0) & (df['rsi'] < 45), 'signal'] = 1
        # Sell: extended >50% above 52w low with RSI overbought
        df.loc[(df['dist_from_low'] > 0.50) & (df['rsi'] > 70), 'signal'] = -1

    # ── 8. GARP (Growth at Reasonable Price) ────────────────
    #    Steady uptrend (EMA slope) but not overbought; moderate momentum
    elif strategy == 'garp':
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_slope'] = df['ema_50'].pct_change(10)  # 10-day slope of EMA50
        df['rsi'] = _compute_rsi(df['close'], 14)
        df['roc_20'] = df['close'].pct_change(20)
        # Buy: rising EMA50, moderate momentum (not extreme), RSI in sweet spot
        df.loc[
            (df['ema_slope'] > 0.005) &
            (df['roc_20'] > 0.02) & (df['roc_20'] < 0.15) &
            (df['rsi'] > 40) & (df['rsi'] < 65),
            'signal'
        ] = 1
        # Sell: EMA slope turning negative or RSI very high
        df.loc[(df['ema_slope'] < -0.005) | (df['rsi'] > 75), 'signal'] = -1

    # ── 9. Quality Dividend proxy ───────────────────────────
    #    Low-volatility stocks in uptrend — dividend-like stability
    elif strategy == 'quality_dividend':
        df['sma_100'] = df['close'].rolling(100).mean()
        df['volatility'] = df['close'].pct_change().rolling(20).std()
        df['vol_med'] = df['volatility'].rolling(252, min_periods=50).median()
        df['roc_60'] = df['close'].pct_change(60)
        # Buy: low vol, positive long-term drift, price above SMA100
        df.loc[
            (df['volatility'] < df['vol_med']) &
            (df['close'] > df['sma_100']) &
            (df['roc_60'] > 0),
            'signal'
        ] = 1
        # Sell: vol spike or breakdown below SMA100
        df.loc[
            (df['volatility'] > df['vol_med'] * 1.5) |
            (df['close'] < df['sma_100'] * 0.97),
            'signal'
        ] = -1

    # ── 10. Contrarian ──────────────────────────────────────
    #    Buy extreme weakness, sell extreme strength — anti-momentum
    elif strategy == 'contrarian':
        rsi_thresh = params.get('rsi_threshold', 25)
        df['rsi'] = _compute_rsi(df['close'], 14)
        df['roc_10'] = df['close'].pct_change(10)
        df['avg_vol'] = df['volume'].rolling(20, min_periods=1).mean()
        df['vol_spike'] = df['volume'] / (df['avg_vol'] + 1)
        # Buy: deeply oversold with volume capitulation
        df.loc[(df['rsi'] < rsi_thresh) & (df['roc_10'] < -0.08) & (df['vol_spike'] > 1.5), 'signal'] = 1
        # Sell: extremely overbought or price reversed >15%
        df.loc[(df['rsi'] > 80) | (df['roc_10'] > 0.15), 'signal'] = -1

    # ── 11. Quality Growth ──────────────────────────────────
    #    Consistent upward channel: higher highs, higher lows, strong ADX
    elif strategy == 'quality_growth':
        adx, plus_di, minus_di = _compute_adx(df['high'], df['low'], df['close'], 14)
        df['adx'] = adx
        df['plus_di'] = plus_di
        df['minus_di'] = minus_di
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        # Buy: strong uptrend (ADX>25, +DI > -DI, price above both EMAs)
        df.loc[
            (df['adx'] > 25) &
            (df['plus_di'] > df['minus_di']) &
            (df['close'] > df['ema_20']) &
            (df['close'] > df['ema_50']),
            'signal'
        ] = 1
        # Sell: trend broken (ADX>20 with -DI > +DI, or price below EMA50)
        df.loc[
            ((df['adx'] > 20) & (df['minus_di'] > df['plus_di'])) |
            (df['close'] < df['ema_50'] * 0.98),
            'signal'
        ] = -1

    # ── Fallback ────────────────────────────────────────────
    else:
        # MACD crossover as a safe default
        macd_line, signal_line, _ = _compute_macd(df['close'])
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df.loc[df['macd'] > df['macd_signal'], 'signal'] = 1
        df.loc[df['macd'] < df['macd_signal'], 'signal'] = -1

    return df[['date', 'signal']].fillna(0)


def _generate_custom_strategy_signals(conditions: list, price_data):
    """
    Generate trading signals from a custom strategy's condition set.
    Each condition has: indicator, operator, value, weight.
    BUY (1) when ALL conditions are satisfied; SELL (-1) when fewer than half are.
    """
    import pandas as pd
    import numpy as np

    df = price_data.copy()
    df['signal'] = 0

    # ── Pre-compute all indicators that might be referenced ──
    indicator_map = {}

    # Price columns
    for col in ('close', 'open', 'high', 'low', 'volume'):
        if col in df.columns:
            indicator_map[col] = df[col]

    # RSI
    indicator_map['rsi'] = _compute_rsi(df['close'], 14)
    indicator_map['rsi_14'] = indicator_map['rsi']

    # MACD
    macd_line, signal_line, macd_hist = _compute_macd(df['close'])
    indicator_map['macd'] = macd_line
    indicator_map['macd_signal'] = signal_line
    indicator_map['macd_hist'] = macd_hist

    # Stochastic
    low_14 = df['low'].rolling(14).min()
    high_14 = df['high'].rolling(14).max()
    indicator_map['stoch_k'] = ((df['close'] - low_14) / (high_14 - low_14 + 1e-8)) * 100
    indicator_map['stoch_d'] = indicator_map['stoch_k'].rolling(3).mean()

    # Williams %R
    indicator_map['williams_r'] = ((high_14 - df['close']) / (high_14 - low_14 + 1e-8)) * -100

    # CCI
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = tp.rolling(20).mean()
    mad = tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    indicator_map['cci'] = (tp - sma_tp) / (0.015 * mad + 1e-8)

    # ROC
    indicator_map['roc'] = df['close'].pct_change(12) * 100

    # Moving Averages
    indicator_map['sma_20'] = df['close'].rolling(20).mean()
    indicator_map['sma_50'] = df['close'].rolling(50).mean()
    indicator_map['sma_200'] = df['close'].rolling(200).mean()
    indicator_map['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    indicator_map['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()

    # ADX
    adx, plus_di, minus_di = _compute_adx(df['high'], df['low'], df['close'], 14)
    indicator_map['adx'] = adx
    indicator_map['plus_di'] = plus_di
    indicator_map['minus_di'] = minus_di

    # Bollinger Bands
    bb_upper, bb_mid, bb_lower = _compute_bollinger(df['close'], 20, 2)
    indicator_map['bb_upper'] = bb_upper
    indicator_map['bb_middle'] = bb_mid
    indicator_map['bb_lower'] = bb_lower

    # ATR
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift(1)).abs(),
        (df['low'] - df['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    indicator_map['atr'] = tr.rolling(14).mean()

    # Volume ratio
    avg_vol = df['volume'].rolling(20, min_periods=1).mean()
    indicator_map['volume_ratio'] = df['volume'] / (avg_vol + 1)

    # OBV
    obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
    indicator_map['obv'] = obv

    # VWAP (intraday proxy — cumulative)
    cum_vol = df['volume'].cumsum()
    cum_vp = (df['close'] * df['volume']).cumsum()
    indicator_map['vwap'] = cum_vp / (cum_vol + 1e-8)

    # ── Evaluate each condition per bar ──
    n = len(df)
    cond_masks = []

    for cond in conditions:
        ind_name = str(cond.get('indicator', '')).lower().strip()
        op = str(cond.get('operator', '>')).strip()
        raw_value = cond.get('value', 0)

        if ind_name not in indicator_map:
            continue  # skip unknown indicators

        ind_series = indicator_map[ind_name]

        # Resolve the comparison target — could be a number or another indicator
        if isinstance(raw_value, str) and raw_value.lower().strip() in indicator_map:
            target = indicator_map[raw_value.lower().strip()]
        else:
            try:
                target = float(raw_value)
            except (ValueError, TypeError):
                continue

        # Apply operator
        if op == '>':
            mask = ind_series > target
        elif op == '<':
            mask = ind_series < target
        elif op == '>=':
            mask = ind_series >= target
        elif op == '<=':
            mask = ind_series <= target
        elif op == '==':
            mask = (ind_series - target).abs() < 1e-6 if isinstance(target, (int, float)) else ind_series == target
        elif op == 'crosses_above':
            prev = ind_series.shift(1)
            if isinstance(target, pd.Series):
                mask = (prev <= target.shift(1)) & (ind_series > target)
            else:
                mask = (prev <= target) & (ind_series > target)
        elif op == 'crosses_below':
            prev = ind_series.shift(1)
            if isinstance(target, pd.Series):
                mask = (prev >= target.shift(1)) & (ind_series < target)
            else:
                mask = (prev >= target) & (ind_series < target)
        else:
            mask = pd.Series(True, index=df.index)

        cond_masks.append(mask.fillna(False))

    if not cond_masks:
        # No valid conditions — fallback to MACD crossover
        df['macd_line'] = macd_line
        df['macd_sig'] = signal_line
        df.loc[df['macd_line'] > df['macd_sig'], 'signal'] = 1
        df.loc[df['macd_line'] < df['macd_sig'], 'signal'] = -1
        return df[['date', 'signal']].fillna(0)

    # Count how many conditions are True per bar
    cond_df = pd.concat(cond_masks, axis=1)
    total_conds = len(cond_masks)
    passed_count = cond_df.sum(axis=1)

    # BUY when ALL conditions pass; SELL when fewer than half pass
    df.loc[passed_count == total_conds, 'signal'] = 1
    df.loc[passed_count < (total_conds / 2), 'signal'] = -1

    return df[['date', 'signal']].fillna(0)


@app.route('/api/backtest/compare', methods=['POST'])
@rate_limit
def compare_strategies():
    """
    Compare multiple strategies via real backtesting.
    Returns comprehensive per-strategy metrics plus cross-strategy rankings.
    """
    try:
        data = request.get_json() or {}
        import pandas as pd
        import numpy as np
        
        strategy_names = data.get('strategies', ['momentum', 'breakout', 'swing'])
        ticker = data.get('ticker', 'NIFTY')
        start_date = data.get('start_date', '2023-01-01')
        end_date = data.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
        initial_capital = data.get('initial_capital', 100000)
        
        # Fetch price data
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return jsonify({"error": f"No data found for {ticker}"}), 404
        
        price_data = pd.DataFrame([dict(row) for row in ticker_data])
        if 'date' in price_data.columns:
            price_data['date'] = pd.to_datetime(price_data['date'])
            price_data = price_data[
                (price_data['date'] >= start_date) & (price_data['date'] <= end_date)
            ]
        
        if price_data.empty or len(price_data) < 50:
            return jsonify({"error": f"Insufficient data for {ticker}"}), 400
        
        # Compute buy-and-hold benchmark return for the period
        bnh_start = price_data['close'].iloc[0]
        bnh_end = price_data['close'].iloc[-1]
        bnh_return_pct = ((bnh_end - bnh_start) / bnh_start) * 100 if bnh_start > 0 else 0
        trading_days = len(price_data)
        years = max(trading_days / 252, 0.01)
        bnh_annual = ((bnh_end / bnh_start) ** (1 / years) - 1) * 100 if bnh_start > 0 else 0
        bnh_daily_rets = price_data['close'].pct_change().dropna().values
        bnh_sharpe = (float(np.mean(bnh_daily_rets)) / max(float(np.std(bnh_daily_rets)), 1e-8)) * np.sqrt(252)

        config = BacktestConfig(initial_capital=float(initial_capital))
        engine = BacktestEngine(data_pipeline=pipeline, config=config)
        
        # Load custom strategies for potential lookup
        import json as _json
        _custom_strats = []
        _cstrat_file = 'data/custom_strategies.json'
        if os.path.exists(_cstrat_file):
            try:
                with open(_cstrat_file, 'r') as _f:
                    _custom_strats = _json.load(_f)
            except Exception:
                pass
        _custom_map = {s['name'].lower(): s for s in _custom_strats}
        
        # Predefined strategy names (ones handled by _generate_strategy_signals)
        _predefined_names = {
            'momentum', 'breakout', 'swing', 'mean_reversion', 'trend_following',
            'piotroski', 'value', 'garp', 'quality_dividend', 'contrarian', 'quality_growth'
        }
        
        # Generate signals for each strategy
        strategy_signals = {}
        for name in strategy_names:
            if isinstance(name, dict):
                name = name.get('name', 'unknown')
            sname = str(name).lower().strip()
            if sname in _predefined_names:
                strategy_signals[name] = _generate_strategy_signals(sname, price_data)
            elif sname in _custom_map:
                strategy_signals[name] = _generate_custom_strategy_signals(
                    _custom_map[sname].get('conditions', []), price_data
                )
            else:
                # Fallback to predefined (will use MACD default)
                strategy_signals[name] = _generate_strategy_signals(name, price_data)
        
        # Use engine compare
        comparison = engine.compare_strategies(strategy_signals, price_data)
        
        # Reshape results dict into rich comparison array
        raw_results = comparison.get('results', {})
        comparison_list = []
        for strat_name, rd in raw_results.items():
            if isinstance(rd, dict) and 'error' not in rd:
                # Build a full metrics dict
                entry = {
                    'strategy': strat_name,
                    # Return metrics
                    'total_return_pct': rd.get('total_return_pct', 0),
                    'annualized_return_pct': rd.get('annualized_return_pct', 0),
                    'annualized_return': rd.get('annualized_return_pct', 0),
                    'cagr_pct': rd.get('cagr_pct', 0),
                    'final_capital': rd.get('final_capital', 0),
                    'final_value': rd.get('final_capital', 0),
                    # Risk metrics
                    'sharpe_ratio': rd.get('sharpe_ratio', 0),
                    'sortino_ratio': rd.get('sortino_ratio', 0),
                    'calmar_ratio': rd.get('calmar_ratio', 0),
                    'max_drawdown_pct': rd.get('max_drawdown_pct', 0),
                    'max_drawdown': rd.get('max_drawdown_pct', 0),
                    'max_drawdown_duration_days': rd.get('max_drawdown_duration_days', 0),
                    'volatility_annual_pct': rd.get('volatility_annual_pct', 0),
                    # Trade metrics
                    'total_trades': rd.get('total_trades', 0),
                    'winning_trades': rd.get('winning_trades', 0),
                    'losing_trades': rd.get('losing_trades', 0),
                    'win_rate_pct': rd.get('win_rate_pct', 0),
                    'win_rate': rd.get('win_rate_pct', 0),
                    'average_win_pct': rd.get('average_win_pct', 0),
                    'average_loss_pct': rd.get('average_loss_pct', 0),
                    'profit_factor': rd.get('profit_factor', 0),
                    'expectancy_per_trade': rd.get('expectancy_per_trade', 0),
                    'average_holding_days': rd.get('average_holding_days', 0),
                    'max_consecutive_losses': rd.get('max_consecutive_losses', 0),
                    # Cost metrics
                    'total_transaction_costs': rd.get('total_transaction_costs', 0),
                    'total_slippage_costs': rd.get('total_slippage_costs', 0),
                    'total_costs': rd.get('total_transaction_costs', 0) + rd.get('total_slippage_costs', 0),
                    # Regime performance
                    'regime_performance': rd.get('regime_performance', {}),
                    # Equity curve (last 500 points max)
                    'equity_curve': rd.get('equity_curve', []),
                    # Derived: excess return over buy-and-hold
                    'excess_return_pct': round(rd.get('total_return_pct', 0) - bnh_return_pct, 2),
                }
                # Best & worst trade from trades list
                trades = rd.get('trades', [])
                if trades:
                    pnl_list = [t.get('pnl_pct', 0) for t in trades]
                    entry['best_trade_pct'] = round(max(pnl_list), 2) if pnl_list else 0
                    entry['worst_trade_pct'] = round(min(pnl_list), 2) if pnl_list else 0
                    # Exit reason breakdown
                    exit_reasons = {}
                    for t in trades:
                        reason = t.get('exit_reason', 'unknown')
                        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
                    entry['exit_reasons'] = exit_reasons
                else:
                    entry['best_trade_pct'] = 0
                    entry['worst_trade_pct'] = 0
                    entry['exit_reasons'] = {}

                comparison_list.append(entry)
        
        # Sort comparison_list by Sharpe descending for overall ranking
        comparison_list.sort(key=lambda x: x.get('sharpe_ratio', 0), reverse=True)

        # Assign overall rank
        for i, c in enumerate(comparison_list):
            c['rank'] = i + 1

        return jsonify({
            "status": "success",
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "trading_days": trading_days,
            "benchmark": {
                "name": "Buy & Hold",
                "total_return_pct": round(bnh_return_pct, 2),
                "annualized_return_pct": round(bnh_annual, 2),
                "sharpe_ratio": round(bnh_sharpe, 3),
            },
            "comparison": comparison_list,
            "rankings": comparison.get('rankings', {}),
        })
        
    except Exception as e:
        logger.error(f"Strategy comparison error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/backtest/walk-forward', methods=['POST'])
@rate_limit
def walk_forward_validate():
    """
    Run walk-forward validation on a strategy.
    
    Body params:
    - strategy: Strategy name
    - ticker: Stock ticker
    - n_splits: Number of walk-forward folds (default: 5)
    - in_sample_ratio: IS/OOS split ratio (default: 0.7)
    """
    try:
        data = request.get_json() or {}
        import pandas as pd
        
        strategy = data.get('strategy', 'momentum')
        ticker = data.get('ticker', 'NIFTY')
        n_splits = data.get('n_splits', 5)
        in_sample_ratio = data.get('in_sample_ratio', 0.7)
        initial_capital = data.get('initial_capital', 100000)
        
        logger.info(f"Walk-forward validation: {strategy} on {ticker}, {n_splits} folds")
        
        # Fetch data
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return jsonify({"error": f"No data found for {ticker}"}), 404
        
        price_data = pd.DataFrame([dict(row) for row in ticker_data])
        if 'date' in price_data.columns:
            price_data['date'] = pd.to_datetime(price_data['date'])
        
        if price_data.empty or len(price_data) < 200:
            return jsonify({"error": f"Insufficient data: need >= 200 bars"}), 400
        
        config = BacktestConfig(initial_capital=float(initial_capital))
        engine = BacktestEngine(data_pipeline=pipeline, config=config)
        wf_config = WalkForwardConfig(n_splits=n_splits, in_sample_ratio=in_sample_ratio)
        wf_engine = WalkForwardEngine(engine, wf_config)
        
        signals = _generate_strategy_signals(strategy, price_data)
        result = wf_engine.validate(signals, price_data, strategy_name=strategy)
        
        return jsonify({
            "status": "success",
            "strategy": strategy,
            "ticker": ticker,
            "n_folds": result.n_folds,
            "aggregate_oos_return": round(result.aggregate_oos_return, 2),
            "aggregate_oos_sharpe": round(result.aggregate_oos_sharpe, 2),
            "parameter_stability": result.parameter_stability,
            "is_robust": result.is_robust,
            "fold_details": [
                {
                    "fold": i + 1,
                    "oos_return": round(r.total_return_pct, 2),
                    "oos_sharpe": round(r.sharpe_ratio, 2),
                    "oos_trades": r.total_trades,
                    "oos_win_rate": round(r.win_rate, 1),
                }
                for i, r in enumerate(result.out_sample_results)
            ]
        })
        
    except Exception as e:
        logger.error(f"Walk-forward validation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/backtest/regimes/<ticker>', methods=['GET'])
@rate_limit
def get_market_regimes(ticker):
    """
    Analyze market regimes for a ticker.
    Returns the regime classification over time.
    """
    try:
        import pandas as pd
        from BacktestEngine import DataNormalizer, RegimeDetector
        
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return jsonify({"error": f"No data found for {ticker}"}), 404
        
        price_data = pd.DataFrame([dict(row) for row in ticker_data])
        if 'date' in price_data.columns:
            price_data['date'] = pd.to_datetime(price_data['date'])
        
        config = BacktestConfig()
        normalized = DataNormalizer.normalize(price_data, config)
        regimes = RegimeDetector.detect(normalized, config)
        
        # Count regime distribution
        regime_counts = regimes.value_counts().to_dict()
        regime_distribution = {
            r.value: count for r, count in regime_counts.items()
        }
        
        # Current regime
        current_regime = regimes.iloc[-1].value if len(regimes) > 0 else 'unknown'
        
        return jsonify({
            "status": "success",
            "ticker": ticker,
            "current_regime": current_regime,
            "regime_distribution": regime_distribution,
            "total_bars": len(regimes),
        })
        
    except Exception as e:
        logger.error(f"Regime analysis error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== RL & PREDICTION TRACKING ENDPOINTS ====================

@app.route('/api/rl/status', methods=['GET'])
@rate_limit
def get_rl_status():
    """Get reinforcement learning feedback loop status and accuracy."""
    try:
        status = predictor.get_rl_status()
        return jsonify({"status": "success", **status})
    except Exception as e:
        logger.error(f"RL status error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/rl/record-actual', methods=['POST'])
@rate_limit
def record_actual_price():
    """
    Record actual price for an earlier prediction to feed RL loop.
    
    Body params:
    - ticker: Stock ticker
    - date: Prediction date (YYYYMMDD)
    - actual_price: Actual price observed
    """
    try:
        data = request.get_json() or {}
        ticker = data.get('ticker')
        date_str = data.get('date')
        actual_price = data.get('actual_price')
        
        if not all([ticker, date_str, actual_price]):
            return jsonify({"error": "ticker, date, and actual_price are required"}), 400
        
        result = predictor.record_actual_price(ticker, date_str, float(actual_price))
        return jsonify({"status": "success", "result": result})
    except Exception as e:
        logger.error(f"Record actual price error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/prediction/accuracy/<ticker>', methods=['GET'])
@rate_limit
def get_prediction_accuracy(ticker):
    """Get prediction accuracy history for a specific ticker."""
    try:
        accuracy = predictor.prediction_tracker.get_accuracy(ticker)
        return jsonify({"status": "success", "ticker": ticker, **accuracy})
    except Exception as e:
        logger.error(f"Prediction accuracy error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/prediction/accuracy', methods=['GET'])
@rate_limit
def get_global_prediction_accuracy():
    """Get global prediction accuracy across all tracked tickers."""
    try:
        accuracy = predictor.prediction_tracker.get_global_accuracy()
        return jsonify({"status": "success", **accuracy})
    except Exception as e:
        logger.error(f"Global prediction accuracy error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== CUSTOM STRATEGY EXECUTION ====================

# Alias map: frontend indicator names → actual column names after
# TechnicalIndicatorEngine.calculate_all_indicators()
_INDICATOR_ALIASES = {
    'rsi': 'rsi_14',
    'macd': 'MACD_12_26_9',
    'macd_signal': 'MACDs_12_26_9',
    'macd_hist': 'MACDh_12_26_9',
    'adx': 'adx_14',
    'stoch_k': 'STOCHk_14_3_3',
    'stoch_d': 'STOCHd_14_3_3',
    'williams_r': 'willr_14',
    'ema_12': 'ema_12',
    'ema_26': 'ema_26',
    'bb_upper': 'BBU_20_2.0',
    'bb_lower': 'BBL_20_2.0',
    'bb_middle': 'BBM_20_2.0',
    'volume_ratio': 'volume_ratio_20',
    'atr': 'ATRr_14',
    'obv': 'OBV',
    'cci': 'CCI_20_0.015',
    'roc': 'ROC_12',
}

def _resolve_indicator_name(name: str, available_cols: dict) -> str:
    """Resolve a frontend indicator name to the actual column present in data."""
    if name in available_cols:
        return name
    alias = _INDICATOR_ALIASES.get(name)
    if alias and alias in available_cols:
        return alias
    # Try common pandas-ta naming patterns
    for col in available_cols:
        if col.lower().startswith(name.lower()):
            return col
    return name  # fallback


def _expand_custom_conditions(conditions: list) -> list:
    """
    Pre-process custom strategy conditions.
    Converts 'increasing'/'decreasing' operators into concrete comparisons
    using prev-day indicator values, and resolves indicator aliases.
    """
    expanded = []
    for cond in conditions:
        op = cond.get('operator', '>')
        indicator = cond.get('indicator', '')
        value = cond.get('value', 0)
        weight = cond.get('weight', 1.0)

        if op == 'increasing':
            # indicator > indicator_prev (previous day)
            # We add a condition that compares today's value to yesterday's
            # by using a special '_prev' suffix the screener will handle
            expanded.append({
                'indicator': indicator,
                'operator': '>',
                'value': f'{indicator}_prev',
                'weight': weight
            })
        elif op == 'decreasing':
            expanded.append({
                'indicator': indicator,
                'operator': '<',
                'value': f'{indicator}_prev',
                'weight': weight
            })
        elif op == 'crosses_above':
            # Current > value AND previous <= value
            expanded.append({
                'indicator': indicator,
                'operator': '>',
                'value': value,
                'weight': weight
            })
        elif op == 'crosses_below':
            expanded.append({
                'indicator': indicator,
                'operator': '<',
                'value': value,
                'weight': weight
            })
        else:
            expanded.append(cond)
    return expanded


@app.route('/api/screen/custom/run/<strategy_name>', methods=['POST'])
@rate_limit
def run_custom_strategy_screening(strategy_name):
    """
    Execute a saved custom strategy for stock screening.
    Uses the InteractiveStockScreener infrastructure for full parallel screening.
    """
    try:
        data = request.get_json() or {}

        # Load custom strategies
        import json
        base_dir = os.path.dirname(os.path.abspath(__file__))
        strategies_file = os.path.join(base_dir, 'data', 'custom_strategies.json')
        custom_strategies = []

        if os.path.exists(strategies_file):
            with open(strategies_file, 'r') as f:
                custom_strategies = json.load(f)

        # Find the requested strategy
        strategy_config = None
        for strat in custom_strategies:
            if strat['name'].lower() == strategy_name.lower():
                strategy_config = strat
                break

        if not strategy_config:
            return jsonify({
                'error': f'Custom strategy "{strategy_name}" not found'
            }), 404

        logger.info(f"Running custom strategy screening: {strategy_name}")
        import time as _time
        start_time = _time.time()

        raw_conditions = strategy_config.get('conditions', [])
        expanded = _expand_custom_conditions(raw_conditions)

        # Determine strategy type from metadata
        category = (strategy_config.get('metadata', {}).get('category', '')
                    or strategy_config.get('category', 'Custom')).lower()
        if category in ('technical', 'fundamental', 'hybrid'):
            strategy_type = category
        else:
            strategy_type = 'technical'

        # Build StrategyCondition list
        sc_conditions = []
        for c in expanded:
            sc_conditions.append(StrategyCondition(
                indicator=c.get('indicator', ''),
                operator=c.get('operator', '>'),
                value=c.get('value', 0),
                weight=float(c.get('weight', 1.0))
            ))

        strategy_obj = TradingStrategy(
            name=strategy_name,
            description=strategy_config.get('description', ''),
            strategy_type=strategy_type,
            conditions=sc_conditions,
            metadata=strategy_config.get('metadata', {})
        )

        # Access the InteractiveStockScreener and screen in parallel
        interactive = screener._interactive
        tickers = interactive._get_tickers()

        if not tickers:
            return jsonify({
                'status': 'success',
                'strategy': strategy_name,
                'count': 0,
                'results': [],
                'message': 'No tickers available'
            })

        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = []
        max_tickers = min(len(tickers), 2500)

        def _screen_custom(ticker):
            """Screen a single ticker with indicator-alias resolution."""
            try:
                df = interactive._fetch_stock_data(ticker)
                if df is None:
                    return None

                from StockScreener import TechnicalIndicatorEngine
                tech_engine = TechnicalIndicatorEngine(df)
                df_ind = tech_engine.calculate_all_indicators()

                if df_ind.empty or len(df_ind) < 2:
                    return None

                latest = df_ind.iloc[-1]
                prev = df_ind.iloc[-2]
                indicators = latest.to_dict()

                # Build prev indicators for increasing/decreasing support
                prev_dict = prev.to_dict()
                for key, val in prev_dict.items():
                    indicators[f'{key}_prev'] = val

                # Also add aliased prev values
                for alias, real in _INDICATOR_ALIASES.items():
                    if real in prev_dict:
                        indicators[f'{alias}_prev'] = prev_dict[real]

                # Resolve indicator aliases in conditions for this stock
                total_score = 0.0
                max_score = 0.0
                conditions_passed = 0

                for cond in strategy_obj.conditions:
                    max_score += cond.weight
                    resolved_ind = _resolve_indicator_name(cond.indicator, indicators)
                    ind_val = indicators.get(resolved_ind)

                    if ind_val is None:
                        continue

                    # Resolve comparison value (could be another indicator name)
                    cmp_value = cond.value
                    if isinstance(cmp_value, str):
                        resolved_cmp = _resolve_indicator_name(cmp_value, indicators)
                        if resolved_cmp in indicators:
                            cmp_value = indicators[resolved_cmp]
                        else:
                            try:
                                cmp_value = float(cmp_value)
                            except (ValueError, TypeError):
                                continue
                    else:
                        try:
                            cmp_value = float(cmp_value)
                        except (ValueError, TypeError):
                            continue

                    try:
                        ind_val = float(ind_val)
                        cmp_value = float(cmp_value)
                    except (ValueError, TypeError):
                        continue

                    passed = False
                    if cond.operator == '>':
                        passed = ind_val > cmp_value
                    elif cond.operator == '<':
                        passed = ind_val < cmp_value
                    elif cond.operator == '>=':
                        passed = ind_val >= cmp_value
                    elif cond.operator == '<=':
                        passed = ind_val <= cmp_value
                    elif cond.operator == '==':
                        passed = abs(ind_val - cmp_value) < 1e-6

                    if passed:
                        total_score += cond.weight
                        conditions_passed += 1

                # Require at least half the conditions to pass
                min_required = max(1, len(strategy_obj.conditions) // 2)
                if conditions_passed < min_required:
                    return None

                final_score = (total_score / max_score * 100) if max_score > 0 else 0

                return {
                    'ticker': ticker,
                    'score': round(final_score, 2),
                    'current_price': round(float(latest.get('close', 0)), 2),
                    'conditions_passed': conditions_passed,
                    'total_conditions': len(strategy_obj.conditions),
                    'confidence': round((conditions_passed / max(len(strategy_obj.conditions), 1)) * 100, 1),
                    'key_indicators': {
                        'rsi_14': round(float(indicators.get('rsi_14', indicators.get('RSI_14', 0))), 2),
                        'price_change_20d': round(float(indicators.get('price_change_20d', 0)), 2),
                        'volume_ratio_20': round(float(indicators.get('volume_ratio_20', 0)), 2),
                    }
                }
            except Exception as e:
                logger.debug(f"Error screening {ticker} with custom strategy: {e}")
                return None

        with ThreadPoolExecutor(max_workers=interactive.max_workers) as executor:
            future_to_ticker = {
                executor.submit(_screen_custom, t): t
                for t in tickers[:max_tickers]
            }
            for future in as_completed(future_to_ticker):
                try:
                    result = future.result(timeout=30)
                    if result and result['score'] > 0:
                        results.append(result)
                except Exception:
                    pass

        results = sorted(results, key=lambda x: x['score'], reverse=True)[:50]
        elapsed = _time.time() - start_time

        return jsonify({
            'status': 'success',
            'strategy': strategy_name,
            'strategy_type': strategy_type,
            'description': strategy_config.get('description', ''),
            'count': len(results),
            'execution_time': round(elapsed, 2),
            'results': results
        })

    except Exception as e:
        logger.error(f"Custom strategy screening error for {strategy_name}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/backtest/custom/<strategy_name>', methods=['POST'])
@rate_limit
def backtest_custom_strategy(strategy_name):
    """
    Backtest a custom strategy using the real BacktestEngine.
    
    Body params:
    - ticker: Stock ticker to backtest on (required)
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - initial_capital: Starting capital (default 100000)
    """
    try:
        data = request.get_json() or {}
        
        # Load custom strategies
        import json
        strategies_file = 'data/custom_strategies.json'
        custom_strategies = []
        
        if os.path.exists(strategies_file):
            with open(strategies_file, 'r') as f:
                custom_strategies = json.load(f)
        
        # Find the requested strategy
        strategy_config = None
        for strat in custom_strategies:
            if strat['name'].lower() == strategy_name.lower():
                strategy_config = strat
                break
        
        if not strategy_config:
            return jsonify({
                'error': f'Custom strategy "{strategy_name}" not found'
            }), 404
        
        ticker = data.get('ticker', 'NIFTY')
        start_date = data.get('start_date', '2023-01-01')
        end_date = data.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
        initial_capital = data.get('initial_capital', 100000)
        
        logger.info(f"Backtesting custom strategy: {strategy_name} on {ticker} from {start_date} to {end_date}")
        
        # Fetch price data
        import pandas as pd
        import numpy as np
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return jsonify({"error": f"No data found for {ticker}"}), 404
        
        price_data = pd.DataFrame([dict(row) for row in ticker_data])
        if 'date' in price_data.columns:
            price_data['date'] = pd.to_datetime(price_data['date'])
            price_data = price_data[
                (price_data['date'] >= start_date) & (price_data['date'] <= end_date)
            ]
        
        if price_data.empty or len(price_data) < 50:
            return jsonify({"error": f"Insufficient data for {ticker} in date range"}), 400
        
        # Generate signals from custom conditions
        signals = _generate_custom_strategy_signals(strategy_config.get('conditions', []), price_data)
        
        # Build config and run backtest
        config = BacktestConfig(initial_capital=float(initial_capital))
        engine = BacktestEngine(data_pipeline=pipeline, config=config)
        result = engine.backtest_strategy(signals, price_data, strategy_name=strategy_name)
        
        # Serialise the same way as the predefined endpoint
        result_dict = result.to_dict()
        result_dict["final_value"] = result_dict.get("final_capital", 0)
        result_dict["max_drawdown"] = result_dict.get("max_drawdown_pct", 0)
        result_dict["win_rate"] = result_dict.get("win_rate_pct", 0)
        result_dict["avg_trade_pnl"] = result_dict.get("expectancy_per_trade", 0)
        result_dict["annualized_return"] = result_dict.get("annualized_return_pct", 0)
        result_dict["cagr"] = result_dict.get("cagr_pct", 0)
        result_dict["avg_holding_days"] = result_dict.get("average_holding_days", 0)
        result_dict.update({
            "status": "success",
            "strategy": strategy_name,
            "strategy_type": "Custom",
            "description": strategy_config.get('description', ''),
            "ticker": ticker,
        })
        return jsonify(result_dict)
        
    except Exception as e:
        logger.error(f"Custom strategy backtest error for {strategy_name}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/compare/strategies', methods=['POST'])
@rate_limit
def compare_custom_strategies():
    """
    Compare multiple custom and predefined strategies
    
    Body params:
    - strategy_names: List of strategy names (custom or predefined)
    - start_date, end_date, initial_capital
    """
    try:
        data = request.get_json() or {}
        
        strategy_names = data.get('strategy_names', [])
        ticker = data.get('ticker', 'NIFTY')
        start_date = data.get('start_date', '2023-01-01')
        end_date = data.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
        initial_capital = data.get('initial_capital', 100000)
        
        if not strategy_names:
            return jsonify({
                'error': 'At least one strategy name is required'
            }), 400
        
        logger.info(f"Comparing strategies: {strategy_names} on {ticker}")
        
        # Load custom strategies
        import json
        import pandas as pd
        import numpy as np
        strategies_file = 'data/custom_strategies.json'
        custom_strategies = {}
        
        if os.path.exists(strategies_file):
            with open(strategies_file, 'r') as f:
                custom_list = json.load(f)
                custom_strategies = {s['name'].lower(): s for s in custom_list}
        
        _predefined_names = {
            'momentum', 'breakout', 'swing', 'mean_reversion', 'trend_following',
            'piotroski', 'value', 'garp', 'quality_dividend', 'contrarian', 'quality_growth'
        }
        
        # Fetch price data
        ticker_data = pipeline.get_ticker_history(ticker)
        if not ticker_data:
            return jsonify({"error": f"No data found for {ticker}"}), 404
        
        price_data = pd.DataFrame([dict(row) for row in ticker_data])
        if 'date' in price_data.columns:
            price_data['date'] = pd.to_datetime(price_data['date'])
            price_data = price_data[
                (price_data['date'] >= start_date) & (price_data['date'] <= end_date)
            ]
        
        if price_data.empty or len(price_data) < 50:
            return jsonify({"error": f"Insufficient data for {ticker}"}), 400
        
        config = BacktestConfig(initial_capital=float(initial_capital))
        engine = BacktestEngine(data_pipeline=pipeline, config=config)
        
        # Generate signals for each strategy
        strategy_signals = {}
        for sn in strategy_names:
            sname = str(sn).lower().strip()
            if sname in _predefined_names:
                strategy_signals[sn] = _generate_strategy_signals(sname, price_data)
            elif sname in custom_strategies:
                strategy_signals[sn] = _generate_custom_strategy_signals(
                    custom_strategies[sname].get('conditions', []), price_data
                )
            else:
                strategy_signals[sn] = _generate_strategy_signals(sn, price_data)
        
        # Run comparison via engine
        comp_result = engine.compare_strategies(strategy_signals, price_data)
        raw_results = comp_result.get('results', {})
        
        comparison = []
        for strat_name, rd in raw_results.items():
            if isinstance(rd, dict) and 'error' not in rd:
                is_custom = strat_name.lower() in custom_strategies
                entry = {
                    "strategy": strat_name,
                    "is_custom": is_custom,
                    "total_return_pct": rd.get('total_return_pct', 0),
                    "annualized_return": rd.get('annualized_return_pct', 0),
                    "sharpe_ratio": rd.get('sharpe_ratio', 0),
                    "max_drawdown": rd.get('max_drawdown_pct', 0),
                    "win_rate": rd.get('win_rate_pct', 0),
                    "total_trades": rd.get('total_trades', 0),
                    "profit_factor": rd.get('profit_factor', 0),
                    "final_value": rd.get('final_capital', 0),
                    "equity_curve": rd.get('equity_curve', []),
                }
                if is_custom:
                    cs = custom_strategies[strat_name.lower()]
                    entry['description'] = cs.get('description', '')
                    entry['category'] = cs.get('category', 'Custom')
                comparison.append(entry)
        
        # Sort by total return descending
        comparison.sort(key=lambda x: x['total_return_pct'], reverse=True)
        
        return jsonify({
            "status": "success",
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "comparison": comparison,
            "count": len(comparison)
        })
        
    except Exception as e:
        logger.error(f"Strategy comparison error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== MULTI-STRATEGY SCREENING ====================

@app.route('/api/screen/multi', methods=['POST'])
@rate_limit
def screen_multi_strategy():
    """
    Screen stocks using multiple strategies and find overlaps
    """
    try:
        data = request.get_json() or {}

        raw_strategies = data.get('strategies', ['momentum', 'value'])
        strategies = [str(s).strip().lower() for s in raw_strategies if str(s).strip()]
        strategies = list(dict.fromkeys(strategies))

        if len(strategies) < 2:
            return jsonify({"error": "At least 2 strategies are required"}), 400

        def _safe_int(value, default):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        min_overlap = _safe_int(data.get('min_overlap', 2), 2)
        min_overlap = max(2, min(min_overlap, len(strategies)))

        max_tickers = _safe_int(data.get('max_tickers', 800), 800)
        max_tickers = max(100, min(max_tickers, 2500))

        max_results = _safe_int(data.get('max_results', 150), 150)
        max_results = max(20, min(max_results, 400))

        cache_key = (
            f"screen:multi:{','.join(sorted(strategies))}:"
            f"{min_overlap}:{max_tickers}:{max_results}"
        )
        cached_payload = _get_cached(cache_key)
        if cached_payload is not None:
            payload = dict(cached_payload)
            payload['cached'] = True
            return jsonify(payload)

        logger.info(
            "Running multi-strategy scan: %s, min_overlap=%s, max_tickers=%s, max_results=%s",
            strategies,
            min_overlap,
            max_tickers,
            max_results,
        )

        # Run all strategies in parallel/batch
        multi_results = screener.run_multiple_strategies(
            strategies,
            max_results=max_results,
            max_tickers=max_tickers,
        )

        if multi_results.get('status') == 'error':
            logger.error(f"Multi-strategy execution failed: {multi_results.get('message')}")
            return jsonify({"error": multi_results.get('message', 'Multi-strategy scan failed')}), 500

        raw_results = multi_results.get('results', {}) or {}

        # Merge strategy-wise outputs by ticker
        all_results = {}
        strategy_results = {strategy: 0 for strategy in strategies}

        for strategy, results_list in raw_results.items():
            try:
                normalized_results = results_list or []
                strategy_results[strategy] = len(normalized_results)

                for item in normalized_results:
                    ticker = item.get('ticker')
                    if not ticker:
                        continue

                    if ticker not in all_results:
                        all_results[ticker] = {'ticker': ticker, 'strategies': []}

                    all_results[ticker]['strategies'].append(strategy)

            except Exception as e:
                logger.warning(f"Strategy {strategy} processing failed: {e}")
                strategy_results[strategy] = 0

        # Filter by minimum overlap
        overlapping = [
            {**row, 'overlap_count': len(row['strategies'])}
            for row in all_results.values()
            if len(row['strategies']) >= min_overlap
        ]

        # Sort by overlap count descending
        overlapping.sort(key=lambda row: row['overlap_count'], reverse=True)

        response_payload = {
            "status": "success",
            "strategies_used": strategies,
            "min_overlap": min_overlap,
            "max_tickers": max_tickers,
            "max_results": max_results,
            "strategy_counts": strategy_results,
            "processed_tickers": multi_results.get('processed_tickers'),
            "execution_time": multi_results.get('execution_time'),
            "count": len(overlapping),
            "results": overlapping,
            "cached": False,
        }

        _set_cached(cache_key, response_payload, ttl=180)
        return jsonify(response_payload)
        
    except Exception as e:
        logger.error(f"Multi-strategy screening error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== STRATEGY MANAGEMENT ENDPOINTS ====================

@app.route('/api/screener/catalog', methods=['GET'])
@rate_limit
def get_indicator_catalog():
    """Get complete indicator catalog for building custom strategies"""
    try:
        if hasattr(screener, 'get_indicator_catalog'):
            catalog = screener.get_indicator_catalog()
        else:
            # Fallback with basic structure
            catalog = {
                'technical_indicators': {
                    'rsi': {'name': 'RSI', 'params': {'period': 14}},
                    'macd': {'name': 'MACD', 'params': {'fast': 12, 'slow': 26, 'signal': 9}},
                    'sma': {'name': 'SMA', 'params': {'period': 20}},
                    'ema': {'name': 'EMA', 'params': {'period': 20}},
                    'bollinger': {'name': 'Bollinger Bands', 'params': {'period': 20, 'std': 2}},
                    'atr': {'name': 'ATR', 'params': {'period': 14}},
                },
                'fundamental_indicators': {
                    'pe_ratio': {'name': 'P/E Ratio'},
                    'pb_ratio': {'name': 'P/B Ratio'},
                    'roe': {'name': 'ROE'},
                    'debt_to_equity': {'name': 'Debt to Equity'},
                },
                'operators': ['>', '<', '>=', '<=', '==', 'between', 'crosses_above', 'crosses_below']
            }
        return jsonify({
            'status': 'success',
            'data': catalog
        })
    except Exception as e:
        logger.error(f"Error fetching indicator catalog: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/screener/strategies', methods=['GET', 'POST'])
@rate_limit
def manage_strategies():
    """Get all strategies or create a new custom strategy"""
    if request.method == 'GET':
        try:
            strategy_type = request.args.get('type', 'all')
            
            # Predefined strategies
            predefined = [
                {'name': 'momentum', 'description': 'Momentum-based stock selection', 'category': 'Technical'},
                {'name': 'piotroski', 'description': 'Piotroski F-Score value investing', 'category': 'Fundamental'},
                {'name': 'swing', 'description': 'Swing trading opportunities', 'category': 'Technical'},
                {'name': 'breakout', 'description': 'Breakout detection with volume', 'category': 'Technical'},
                {'name': 'value', 'description': 'Value investing fundamentals', 'category': 'Fundamental'},
                {'name': 'garp', 'description': 'Growth at a Reasonable Price', 'category': 'Hybrid'},
                {'name': 'mean_reversion', 'description': 'Mean reversion strategy', 'category': 'Technical'},
                {'name': 'quality_dividend', 'description': 'Quality dividend stocks', 'category': 'Fundamental'},
                {'name': 'trend_following', 'description': 'Trend following momentum', 'category': 'Technical'},
                {'name': 'contrarian', 'description': 'Contrarian oversold picks', 'category': 'Technical'},
                {'name': 'quality_growth', 'description': 'Quality growth stocks', 'category': 'Fundamental'},
            ]
            
            # Load custom strategies from file if exists
            custom = []
            base_dir = os.path.dirname(os.path.abspath(__file__))
            strategies_file = os.path.join(base_dir, 'data', 'custom_strategies.json')
            if os.path.exists(strategies_file):
                try:
                    import json
                    with open(strategies_file, 'r') as f:
                        custom = json.load(f)
                except Exception:
                    pass
            
            return jsonify({
                'status': 'success',
                'predefined': predefined,
                'custom': custom
            })
        except Exception as e:
            logger.error(f"Error fetching strategies: {e}")
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            import json
            data = request.get_json() or {}
            
            if 'name' not in data or 'conditions' not in data:
                return jsonify({'error': 'Strategy name and conditions required'}), 400
            
            # Use absolute path so it works regardless of cwd
            base_dir = os.path.dirname(os.path.abspath(__file__))
            strategies_dir = os.path.join(base_dir, 'data')
            strategies_file = os.path.join(strategies_dir, 'custom_strategies.json')
            
            # Load existing custom strategies
            custom = []
            if os.path.exists(strategies_file):
                try:
                    with open(strategies_file, 'r') as f:
                        custom = json.load(f)
                except Exception:
                    pass
            
            # Add new strategy
            new_strategy = {
                'name': data['name'],
                'description': data.get('description', ''),
                'category': data.get('category', 'Custom'),
                'conditions': data['conditions'],
                'metadata': data.get('metadata', {})
            }
            
            # Replace if exists, otherwise append
            existing_idx = next((i for i, s in enumerate(custom) if s['name'] == data['name']), None)
            if existing_idx is not None:
                custom[existing_idx] = new_strategy
            else:
                custom.append(new_strategy)
            
            # Ensure data directory exists
            os.makedirs(strategies_dir, exist_ok=True)
            
            # Save
            with open(strategies_file, 'w') as f:
                json.dump(custom, f, indent=2)
            
            logger.info(f"Saved custom strategy: {data['name']}")
            
            return jsonify({
                'status': 'success',
                'message': f"Strategy '{data['name']}' saved",
                'strategy': new_strategy
            }), 201
            
        except Exception as e:
            logger.error(f"Error saving strategy: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/api/screener/strategies/<strategy_name>', methods=['DELETE'])
@rate_limit
def delete_strategy(strategy_name):
    """Delete a custom strategy"""
    try:
        import json
        base_dir = os.path.dirname(os.path.abspath(__file__))
        strategies_file = os.path.join(base_dir, 'data', 'custom_strategies.json')
        
        if not os.path.exists(strategies_file):
            return jsonify({'error': 'Strategy not found'}), 404
        
        with open(strategies_file, 'r') as f:
            custom = json.load(f)
        
        original_len = len(custom)
        custom = [s for s in custom if s['name'] != strategy_name]
        
        if len(custom) == original_len:
            return jsonify({'error': 'Strategy not found'}), 404
        
        with open(strategies_file, 'w') as f:
            json.dump(custom, f, indent=2)
        
        logger.info(f"Deleted strategy: {strategy_name}")
        return jsonify({'status': 'success', 'message': f"Strategy '{strategy_name}' deleted"})
        
    except Exception as e:
        logger.error(f"Error deleting strategy: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/screener/strategies/validate', methods=['POST'])
@rate_limit
def validate_strategy():
    """Validate a strategy configuration"""
    try:
        data = request.get_json() or {}
        conditions = data.get('conditions', {})
        
        errors = []
        warnings = []
        
        # Basic validation
        if not conditions:
            errors.append('At least one condition is required')
        
        return jsonify({
            'status': 'success',
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== CONFIGURATION ENDPOINTS ====================

@app.route('/api/config/screener', methods=['GET', 'POST'])
@rate_limit
def screener_configuration():
    """Get or update screener configuration"""
    if request.method == 'GET':
        return jsonify(asdict(screener_config))
    
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            
            # Update configuration
            if 'max_workers' in data:
                screener_config.max_workers = data['max_workers']
            if 'cache_ttl_seconds' in data:
                screener_config.cache_ttl_seconds = data['cache_ttl_seconds']
            if 'timeout_seconds' in data:
                screener_config.timeout_seconds = data['timeout_seconds']
            if 'enable_caching' in data:
                screener_config.enable_caching = data['enable_caching']
            if 'min_data_points' in data:
                screener_config.min_data_points = data['min_data_points']
            
            logger.info(f"Configuration updated: {asdict(screener_config)}")
            
            return jsonify({
                "status": "success",
                "message": "Configuration updated",
                "config": asdict(screener_config)
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/cache/clear', methods=['POST'])
@rate_limit
def clear_cache():
    """Clear screener cache"""
    try:
        # If screener has a clear_cache method, call it
        if hasattr(screener, 'clear_cache'):
            screener.clear_cache()
        
        logger.info("Cache cleared successfully")
        return jsonify({
            "status": "success",
            "message": "Cache cleared successfully"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/<filename>', methods=['GET'])
@rate_limit
def download_file(filename):
    """Download exported screening results"""
    try:
        if not os.path.exists(filename):
            return jsonify({"error": "File not found"}), 404
        
        return send_file(filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== WATCHLIST/PORTFOLIO ENDPOINTS ====================

# In-memory watchlist (in production, use database)
user_watchlist = []

@app.route('/api/watchlist', methods=['GET', 'POST', 'DELETE'])
@rate_limit
def manage_watchlist():
    """Manage user watchlist"""
    global user_watchlist
    
    if request.method == 'GET':
        return jsonify({
            "status": "success",
            "watchlist": user_watchlist,
            "count": len(user_watchlist)
        })
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        ticker = data.get('ticker', '').upper()
        
        if not ticker:
            return jsonify({"error": "Ticker is required"}), 400
        
        if ticker not in user_watchlist:
            user_watchlist.append(ticker)
            logger.info(f"Added {ticker} to watchlist")
        
        return jsonify({
            "status": "success",
            "message": f"{ticker} added to watchlist",
            "watchlist": user_watchlist
        })
    
    elif request.method == 'DELETE':
        data = request.get_json() or {}
        ticker = data.get('ticker', '').upper()
        
        if ticker in user_watchlist:
            user_watchlist.remove(ticker)
            logger.info(f"Removed {ticker} from watchlist")
        
        return jsonify({
            "status": "success",
            "message": f"{ticker} removed from watchlist",
            "watchlist": user_watchlist
        })

# ==================== ERROR HANDLERS ====================
# --- AUTHENTICATION ENDPOINTS ---
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = _get_json_payload(required_fields=['username', 'email', 'password'])

    username = str(data['username']).strip()
    email = str(data['email']).strip().lower()
    password = str(data['password'])
    res = user_manager.create_user(username, email, password)

    if "error" in res:
        return jsonify(res), 400
    return jsonify({"message": "User created", "user": res}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = _get_json_payload(required_fields=['username', 'password'])

    username = str(data['username']).strip()
    password = str(data['password'])
    user = user_manager.verify_user(username, password)

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Create token with user_id as identity
    access_token = create_access_token(identity=str(user['id']))
    return jsonify({
        "access_token": access_token, 
        "user": user
    })

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = user_manager.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


@app.route('/api/auth/google', methods=['POST'])
def google_login():
    """Authenticate via Google OAuth2 ID token."""
    data = _get_json_payload(required_fields=['credential'])
    credential = str(data.get('credential', '')).strip()
    if not credential:
        return jsonify({"error": "Missing Google credential"}), 400

    user = user_manager.verify_google_token(credential)
    if "error" in user:
        return jsonify(user), 400

    access_token = create_access_token(identity=str(user['id']))
    return jsonify({
        "access_token": access_token,
        "user": user
    })

# --- PORTFOLIO ENDPOINTS ---

@app.errorhandler(404)
def not_found(error):
    if _is_api_request():
        return _api_error_response("Endpoint not found", 404, code="NOT_FOUND")
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    if _is_api_request():
        return _api_error_response("Internal server error", 500, code="INTERNAL_SERVER_ERROR")
    return jsonify({"error": "Internal server error"}), 500

# ==================== PORTFOLIO ENDPOINTS ====================

@app.route('/api/portfolio', methods=['GET'])
@rate_limit
@jwt_required()
def get_portfolio():
    try:
        user_id = get_jwt_identity()
        # Access user-specific data via private method (temporary until public API expanded)
        # We need the tickers to fetch live prices
        user_data = portfolio_manager._load_data(user_id)
        holdings = user_data.get('holdings', {})
        tickers = list(holdings.keys())
        current_prices = {}
        
        # Helper function to try fetching price with different suffixes
        def fetch_price_with_suffix(ticker):
            """Try fetching price with Indian exchange suffixes if base ticker fails"""
            import yfinance as yf
            
            # List of suffixes to try: original, .NS (NSE), .BO (BSE)
            suffixes = ['', '.NS', '.BO']
            
            # If ticker already has suffix, just use it
            if any(ticker.endswith(s) for s in ['.NS', '.BO', '.NYSE', '.NASDAQ']):
                suffixes = ['']
            
            for suffix in suffixes:
                try:
                    test_ticker = ticker + suffix if suffix else ticker
                    stock = yf.Ticker(test_ticker)
                    # Try to get current price from info
                    info = stock.info
                    price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
                    if price and price > 0:
                        return price
                except:
                    continue
                    
            # Fallback: try download for 1 day
            for suffix in suffixes:
                try:
                    test_ticker = ticker + suffix if suffix else ticker
                    data = yf.download(test_ticker, period="1d", progress=False)
                    if not data.empty and 'Close' in data.columns:
                        close = data['Close'].iloc[-1]
                        if close > 0:
                            return float(close)
                except:
                    continue
            return None
        
        if tickers:
            try:
                import yfinance as yf
                # Try batch download first for efficiency
                # Add .NS suffix for all tickers as default for Indian market
                nse_tickers = [t if any(t.endswith(s) for s in ['.NS', '.BO']) else t + '.NS' for t in tickers]
                tickers_str = " ".join(nse_tickers)
                
                if tickers_str:
                    # Download 1 day data
                    data = yf.download(tickers_str, period="1d", progress=False, timeout=30)
                    
                    if not data.empty and 'Close' in data.columns:
                        close_data = data['Close']
                        last_prices = close_data.iloc[-1]
                        
                        for orig_ticker, nse_ticker in zip(tickers, nse_tickers):
                            try:
                                if len(nse_tickers) == 1:
                                    val = float(last_prices)
                                    if val > 0:
                                        current_prices[orig_ticker] = val
                                else:
                                    if nse_ticker in last_prices:
                                        val = float(last_prices[nse_ticker])
                                        if val > 0:
                                            current_prices[orig_ticker] = val
                            except:
                                pass
                
                # For any tickers that failed, try individual fetch
                for ticker in tickers:
                    if ticker not in current_prices or current_prices.get(ticker, 0) <= 0:
                        price = fetch_price_with_suffix(ticker)
                        if price:
                            current_prices[ticker] = price
                            
            except Exception as ex:
                logger.warning(f"Could not fetch live prices: {ex}")
                # Try individual fetch for all tickers
                for ticker in tickers:
                    try:
                        price = fetch_price_with_suffix(ticker)
                        if price:
                            current_prices[ticker] = price
                    except:
                        pass

        # Pass user_id and prices
        data = portfolio_manager.get_portfolio_summary(user_id, current_prices)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching portfolio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/portfolio/transaction', methods=['POST'])
@rate_limit
@jwt_required()
def add_transaction():
    try:
        user_id = get_jwt_identity()
        data = request.json
        required = ['ticker', 'type', 'quantity', 'price']
        if not all(k in data for k in required):
            return jsonify({"error": "Missing fields"}), 400
            
        txn = portfolio_manager.add_transaction(
            user_id,
            data['ticker'], 
            data['type'], 
            data['quantity'], 
            data['price'],
            data.get('date')
        )
        return jsonify({"message": "Transaction added", "transaction": txn})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/portfolio/transaction/<txn_id>', methods=['DELETE'])
@rate_limit
@jwt_required()
def delete_transaction(txn_id):
    try:
        user_id = get_jwt_identity()
        success = portfolio_manager.delete_transaction(user_id, txn_id)
        if success:
            return jsonify({"message": "Transaction deleted"})
        return jsonify({"error": "Transaction not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== NEWS ENDPOINTS ====================

# Initialize news aggregator
news_aggregator = get_news_aggregator()

@app.route('/api/news/providers', methods=['GET'])
@rate_limit
def get_news_providers():
    """Get list of available news providers"""
    try:
        providers = news_aggregator.get_providers()
        return jsonify({
            "status": "success",
            "providers": providers,
            "count": len(providers)
        })
    except Exception as e:
        logger.error(f"Error getting news providers: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/news/market', methods=['GET'])
@rate_limit
def get_market_news():
    """Get general market news"""
    try:
        limit = request.args.get('limit', 20, type=int)
        result = news_aggregator.get_market_news(limit=limit)
        return jsonify({
            "status": "success",
            "count": result.get('count', 0),
            "news": result.get('articles', [])
        })
    except Exception as e:
        logger.error(f"Error fetching market news: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/news/stock/<symbol>', methods=['GET'])
@rate_limit
def get_stock_news(symbol):
    """Get news for a specific stock with sentiment analysis"""
    try:
        limit = request.args.get('limit', 10, type=int)
        result = news_aggregator.get_stock_news(symbol.upper(), limit=limit)
        return jsonify({
            "status": "success",
            "symbol": symbol.upper(),
            "count": result.get('article_count', 0),
            "news": result.get('articles', []),
            "sentiment": result.get('aggregate', {}),
            "overall_sentiment": result.get('overall_sentiment', 'NEUTRAL'),
        })
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/news/portfolio', methods=['GET'])
@rate_limit
@jwt_required()
def get_portfolio_news():
    """Get news for all stocks in user's portfolio"""
    try:
        user_id = get_jwt_identity()
        limit = request.args.get('limit', 20, type=int)
        
        # Get user's portfolio holdings
        portfolio_data = portfolio_manager.get_portfolio_summary(user_id)
        holdings = portfolio_data.get('holdings', [])
        
        if not holdings:
            return jsonify({
                "status": "success",
                "message": "No holdings in portfolio",
                "news": []
            })
        
        # Extract symbols from holdings
        symbols = [h.get('ticker', '') for h in holdings if h.get('ticker')]
        
        # Fetch news for all symbols
        result = news_aggregator.get_portfolio_news(symbols, limit_per_stock=limit)
        
        return jsonify({
            "status": "success",
            "symbols": symbols,
            "portfolio": result.get('portfolio', {}),
        })
    except Exception as e:
        logger.error(f"Error fetching portfolio news: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/sentiment/<ticker>', methods=['GET'])
@rate_limit
def get_sentiment(ticker):
    """Get detailed sentiment analysis for a stock.
    
    Uses SentimentEngine directly when Finnhub key is available,
    otherwise falls back to news_aggregator (yfinance + local NLP).
    """
    try:
        days = request.args.get('days', 14, type=int)

        # Primary path: SentimentEngine with Finnhub
        if _HAS_SENTIMENT:
            engine = get_sentiment_engine()
            if engine and engine.news_provider.api_key:
                result = engine.get_detailed_analysis(ticker.upper(), days_back=days)
                return jsonify({"status": "success", "data": result})

        # Fallback: use NewsAggregator (yfinance + local sentiment)
        result = news_aggregator.get_stock_news(ticker.upper(), limit=20, days_back=days)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"Error fetching sentiment for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== SCHEDULER ENDPOINTS ====================

@app.route('/api/scheduler/status', methods=['GET'])
@rate_limit
def get_scheduler_status():
    """Get current scheduler status"""
    try:
        status = data_scheduler.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scheduler/trigger', methods=['POST'])
@rate_limit
def trigger_data_update():
    """Manually trigger a data update"""
    try:
        result = data_scheduler.trigger_now()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error triggering data update: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scheduler/history', methods=['GET'])
@rate_limit
def get_scheduler_history():
    """Get recent pipeline execution history with per-step details"""
    try:
        limit = request.args.get('limit', 20, type=int)
        history = data_scheduler.get_job_history(limit)
        return jsonify({
            "status": "success",
            "count": len(history),
            "history": history,
        })
    except Exception as e:
        logger.error(f"Error getting scheduler history: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/scheduler/schedule', methods=['POST'])
@rate_limit
def update_schedule():
    """Update the scheduler time"""
    try:
        data = request.get_json() or {}
        hour = data.get('hour', 16)
        minute = data.get('minute', 0)
        
        if data_scheduler.update_schedule(hour, minute):
            return jsonify({
                "status": "success",
                "message": f"Schedule updated to {hour}:{minute:02d}",
                "schedule": f"{hour}:{minute:02d} IST"
            })
        return jsonify({"error": "Invalid schedule parameters"}), 400
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== EXCHANGE ENDPOINTS ====================

@app.route('/api/exchanges', methods=['GET'])
@rate_limit
def get_exchanges():
    """Get list of supported exchanges"""
    try:
        exchanges = exchange_manager.get_supported_exchanges()
        return jsonify({
            "status": "success",
            "exchanges": exchanges,
            "default": exchange_manager.default_exchange
        })
    except Exception as e:
        logger.error(f"Error getting exchanges: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/exchanges/default', methods=['POST'])
@rate_limit
def set_default_exchange():
    """Set default exchange"""
    try:
        data = request.get_json() or {}
        exchange = data.get('exchange', 'NSE')
        
        if exchange_manager.set_default_exchange(exchange):
            return jsonify({
                "status": "success",
                "message": f"Default exchange set to {exchange}",
                "default": exchange_manager.default_exchange
            })
        return jsonify({"error": f"Unsupported exchange: {exchange}"}), 400
    except Exception as e:
        logger.error(f"Error setting default exchange: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/exchanges/<exchange>/stock/<symbol>', methods=['GET'])
@rate_limit
def get_exchange_stock_data(exchange, symbol):
    """Fetch stock data from specific exchange"""
    try:
        period = request.args.get('period', '1y')
        df = exchange_manager.fetch_data(symbol, exchange, period)
        
        if df.empty:
            return jsonify({"error": f"No data found for {symbol} on {exchange}"}), 404
        
        data = df.to_dict(orient='records')
        return jsonify({
            "status": "success",
            "exchange": exchange,
            "symbol": symbol.upper(),
            "count": len(data),
            "data": data
        })
    except Exception as e:
        logger.error(f"Error fetching {symbol} from {exchange}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/exchanges/<exchange>/live/<symbol>', methods=['GET'])
@rate_limit
def get_exchange_live_price(exchange, symbol):
    """Get live price from specific exchange"""
    try:
        live_data = exchange_manager.fetch_live(symbol, exchange)
        
        if not live_data:
            return jsonify({"error": f"No live data for {symbol} on {exchange}"}), 404
        
        return jsonify({
            "status": "success",
            **live_data
        })
    except Exception as e:
        logger.error(f"Error fetching live price for {symbol} from {exchange}: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== ADVANCED STRATEGY ENGINE ENDPOINTS (Patent-Pending) ====================

@app.route('/api/strategies/catalog', methods=['GET'])
@rate_limit
def get_strategy_catalog():
    """Get full catalog of all 18+ available strategies with metadata."""
    if not _HAS_STRATEGY_ENGINE:
        return jsonify({"error": "Advanced Strategy Engine not available"}), 503
    try:
        engine = get_strategy_engine()
        catalog = engine.get_strategy_catalog()
        categories = engine.get_categories()
        return jsonify({
            "status": "success",
            "count": len(catalog),
            "categories": categories,
            "strategies": catalog,
        })
    except Exception as e:
        logger.error(f"Strategy catalog error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/evaluate/<ticker>', methods=['POST'])
@rate_limit
def evaluate_strategies(ticker):
    """Evaluate a stock against one or all strategies."""
    if not _HAS_STRATEGY_ENGINE:
        return jsonify({"error": "Advanced Strategy Engine not available"}), 503
    try:
        import yfinance as yf
        data = request.get_json(silent=True) or {}
        strategy_names = data.get('strategies')  # None = all strategies
        period = data.get('period', '1y')

        normalized_ticker = _normalize_ticker_symbol(ticker)
        yf_symbol = _to_yfinance_symbol(normalized_ticker, exchange='NSE')
        df = yf.download(yf_symbol, period=period, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return jsonify({"error": f"No data for {normalized_ticker}"}), 404

        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        engine = get_strategy_engine()
        results = engine.evaluate_multiple_strategies(df, strategy_names)

        return jsonify({
            "status": "success",
            "ticker": _base_ticker_symbol(normalized_ticker),
            "source_symbol": yf_symbol,
            "strategies_evaluated": len(results),
            "results": results,
        })
    except Exception as e:
        logger.error(f"Strategy evaluation error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/multi-screen/<ticker>', methods=['POST'])
@rate_limit
def multi_strategy_screen(ticker):
    """
    Patent-Pending: Committee-of-Experts multi-strategy screening.
    Evaluates a stock against ALL strategies and returns combined verdict.
    """
    if not _HAS_STRATEGY_ENGINE:
        return jsonify({"error": "Advanced Strategy Engine not available"}), 503
    try:
        import yfinance as yf
        data = request.get_json(silent=True) or {}
        min_passing = data.get('min_strategies_passing', 2)
        min_confidence = data.get('min_confidence', 60)
        period = data.get('period', '1y')

        normalized_ticker = _normalize_ticker_symbol(ticker)
        yf_symbol = _to_yfinance_symbol(normalized_ticker, exchange='NSE')
        df = yf.download(yf_symbol, period=period, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return jsonify({"error": f"No data for {normalized_ticker}"}), 404

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        engine = get_strategy_engine()
        result = engine.multi_strategy_screen(df, min_passing, min_confidence)

        return jsonify({
            "status": "success",
            "ticker": _base_ticker_symbol(normalized_ticker),
            "source_symbol": yf_symbol,
            **result,
        })
    except Exception as e:
        logger.error(f"Multi-strategy screen error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/sector-rotation', methods=['GET'])
@rate_limit
def get_sector_rotation():
    """Analyze sector rotation patterns across markets."""
    if not _HAS_STRATEGY_ENGINE:
        return jsonify({"error": "Advanced Strategy Engine not available"}), 503
    try:
        exchange = request.args.get('exchange', 'NSE')
        detector = SectorRotationDetector()
        analysis = detector.analyze_rotation(exchange)
        return jsonify({
            "status": "success",
            "exchange": exchange,
            "sectors": analysis,
        })
    except Exception as e:
        logger.error(f"Sector rotation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/strategies/custom', methods=['POST'])
@rate_limit
def add_custom_strategy():
    """Add a user-defined custom strategy."""
    if not _HAS_STRATEGY_ENGINE:
        return jsonify({"error": "Advanced Strategy Engine not available"}), 503
    try:
        data = request.get_json() or {}
        name = data.get('name')
        if not name:
            return jsonify({"error": "Strategy name is required"}), 400

        engine = get_strategy_engine()
        engine.add_custom_strategy(
            name=name,
            description=data.get('description', ''),
            category=data.get('category', 'Custom'),
            risk_level=data.get('risk_level', 'Unknown'),
            timeframe=data.get('timeframe', 'Unknown'),
            rules=data.get('rules', []),
        )
        return jsonify({"status": "success", "message": f"Strategy '{name}' added"})
    except Exception as e:
        logger.error(f"Custom strategy error: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== FUNDAMENTAL ANALYSIS ENDPOINTS (Patent-Pending) ====================

@app.route('/api/fundamentals/<ticker>', methods=['GET'])
@rate_limit
def get_fundamentals(ticker):
    """Get comprehensive fundamental analysis for a stock."""
    if not _HAS_FUNDAMENTALS:
        return jsonify({"error": "Fundamental Analysis module not available"}), 503
    try:
        exchange = request.args.get('exchange', 'NSE')
        normalized_ticker = _base_ticker_symbol(ticker)
        analyzer = get_fundamental_analyzer()
        fundamentals = analyzer.get_fundamentals(normalized_ticker, exchange)
        if not fundamentals:
            return jsonify({"error": f"No fundamental data for {normalized_ticker}"}), 404

        score_result = analyzer.score_fundamentals(fundamentals)

        return jsonify({
            "status": "success",
            "data": fundamentals,
            "score": score_result,
        })
    except Exception as e:
        logger.error(f"Fundamentals error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/fundamentals/<ticker>/piotroski', methods=['GET'])
@rate_limit
def get_piotroski_score(ticker):
    """Calculate Piotroski F-Score (0-9) for value investing assessment."""
    if not _HAS_FUNDAMENTALS:
        return jsonify({"error": "Fundamental Analysis module not available"}), 503
    try:
        exchange = request.args.get('exchange', 'NSE')
        normalized_ticker = _base_ticker_symbol(ticker)
        analyzer = get_fundamental_analyzer()
        result = analyzer.calculate_piotroski_score(normalized_ticker, exchange)
        if not result:
            return jsonify({"error": f"Cannot calculate Piotroski score for {normalized_ticker}"}), 404
        return jsonify({"status": "success", **result})
    except Exception as e:
        logger.error(f"Piotroski error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/fundamentals/compare', methods=['POST'])
@rate_limit
def compare_fundamentals():
    """Compare fundamentals of multiple stocks side-by-side."""
    if not _HAS_FUNDAMENTALS:
        return jsonify({"error": "Fundamental Analysis module not available"}), 503
    try:
        data = request.get_json() or {}
        symbols = data.get('symbols', [])
        exchange = data.get('exchange', 'NSE')
        if not symbols or len(symbols) < 2:
            return jsonify({"error": "At least 2 symbols required"}), 400

        normalized_symbols = [_base_ticker_symbol(symbol) for symbol in symbols if _base_ticker_symbol(symbol)]
        if len(normalized_symbols) < 2:
            return jsonify({"error": "At least 2 valid symbols required"}), 400

        analyzer = get_fundamental_analyzer()
        comparison_df = analyzer.compare_fundamentals(normalized_symbols, exchange)
        if comparison_df.empty:
            return jsonify({"error": "No data for comparison"}), 404

        return jsonify({
            "status": "success",
            "comparison": comparison_df.to_dict(orient="index"),
            "symbols": list(comparison_df.index),
        })
    except Exception as e:
        logger.error(f"Fundamentals comparison error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/fundamentals/<ticker>/statements', methods=['GET'])
@rate_limit
def get_financial_statements(ticker):
    """Get income statement, balance sheet, and cash flow data."""
    if not _HAS_FUNDAMENTALS:
        return jsonify({"error": "Fundamental Analysis module not available"}), 503
    try:
        exchange = request.args.get('exchange', 'NSE')
        normalized_ticker = _base_ticker_symbol(ticker)
        analyzer = get_fundamental_analyzer()
        result = analyzer.get_financial_statements(normalized_ticker, exchange)
        if not result:
            return jsonify({"error": f"No financial statements for {normalized_ticker}"}), 404

        # Convert timestamps to strings for JSON serialization
        serializable = {}
        for key, val in result.items():
            if val is not None:
                if isinstance(val, dict):
                    clean = {}
                    for k, v in val.items():
                        clean[str(k)] = {str(kk): (float(vv) if isinstance(vv, (int, float)) else str(vv))
                                         for kk, vv in v.items()} if isinstance(v, dict) else v
                    serializable[key] = clean
                else:
                    serializable[key] = val

        return jsonify({"status": "success", "ticker": normalized_ticker, **serializable})
    except Exception as e:
        logger.error(f"Financial statements error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== RISK ANALYTICS ENDPOINTS (Patent-Pending) ====================

@app.route('/api/risk/<ticker>', methods=['GET'])
@rate_limit
def get_risk_metrics(ticker):
    """Calculate 30+ risk metrics for a stock."""
    if not _HAS_RISK:
        return jsonify({"error": "Risk Analytics module not available"}), 503
    try:
        import yfinance as yf
        period = request.args.get('period', '2y')
        benchmark = request.args.get('benchmark', '^NSEI')

        normalized_ticker = _normalize_ticker_symbol(ticker)
        yf_symbol = _to_yfinance_symbol(normalized_ticker, exchange='NSE')
        df = yf.download(yf_symbol, period=period, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return jsonify({"error": f"No data for {normalized_ticker}"}), 404

        # Flatten multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Benchmark data
        bench_df = None
        try:
            bench_df = yf.download(benchmark, period=period, progress=False, auto_adjust=True)
            if isinstance(bench_df.columns, pd.MultiIndex):
                bench_df.columns = bench_df.columns.get_level_values(0)
        except Exception:
            pass

        analytics = get_risk_analytics()
        metrics = analytics.compute_all_metrics(df, bench_df)
        if not metrics:
            return jsonify({"error": "Insufficient data for risk analysis"}), 400

        return jsonify({
            "status": "success",
            "ticker": _base_ticker_symbol(normalized_ticker),
            "source_symbol": yf_symbol,
            "period": period,
            "benchmark": benchmark,
            "metrics": metrics,
        })
    except Exception as e:
        logger.error(f"Risk analytics error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk/portfolio', methods=['POST'])
@rate_limit
def analyze_portfolio_risk():
    """
    Analyze portfolio-level risk with Component VaR, Diversification Ratio,
    and marginal risk contribution.
    """
    if not _HAS_RISK:
        return jsonify({"error": "Risk Analytics module not available"}), 503
    try:
        import yfinance as yf
        data = request.get_json() or {}
        holdings = data.get('holdings', {})  # {symbol: weight}
        period = data.get('period', '1y')

        if len(holdings) < 2:
            return jsonify({"error": "At least 2 stocks required for portfolio analysis"}), 400

        stock_data = {}
        for symbol in holdings:
            normalized_symbol = _normalize_ticker_symbol(symbol)
            yf_symbol = _to_yfinance_symbol(normalized_symbol, exchange='NSE')
            df = yf.download(yf_symbol, period=period, progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                stock_data[symbol] = df

        if len(stock_data) < 2:
            return jsonify({"error": "Insufficient data for portfolio analysis"}), 400

        analyzer = get_portfolio_analyzer()
        result = analyzer.analyze_portfolio_risk(stock_data, holdings)
        if not result:
            return jsonify({"error": "Portfolio analysis failed"}), 500

        return jsonify({
            "status": "success",
            **result,
        })
    except Exception as e:
        logger.error(f"Portfolio risk error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk/efficient-frontier', methods=['POST'])
@rate_limit
def generate_efficient_frontier():
    """
    Patent-Pending: Monte Carlo Efficient Frontier generation.
    Identifies max-Sharpe and min-volatility optimal portfolios.
    """
    if not _HAS_RISK:
        return jsonify({"error": "Risk Analytics module not available"}), 503
    try:
        import yfinance as yf
        data = request.get_json() or {}
        symbols = data.get('symbols', [])
        period = data.get('period', '1y')
        n_portfolios = min(data.get('n_portfolios', 5000), 10000)

        if len(symbols) < 2:
            return jsonify({"error": "At least 2 stocks required"}), 400

        stock_data = {}
        for symbol in symbols:
            normalized_symbol = _normalize_ticker_symbol(symbol)
            yf_symbol = _to_yfinance_symbol(normalized_symbol, exchange='NSE')
            df = yf.download(yf_symbol, period=period, progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                stock_data[symbol] = df

        if len(stock_data) < 2:
            return jsonify({"error": "Insufficient data"}), 400

        analyzer = get_portfolio_analyzer()
        result = analyzer.efficient_frontier(stock_data, n_portfolios)
        if not result:
            return jsonify({"error": "Efficient frontier generation failed"}), 500

        return jsonify({
            "status": "success",
            **result,
        })
    except Exception as e:
        logger.error(f"Efficient frontier error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/risk/compare', methods=['POST'])
@rate_limit
def compare_stock_risk():
    """Compare and rank multiple stocks by risk-adjusted metrics."""
    if not _HAS_RISK:
        return jsonify({"error": "Risk Analytics module not available"}), 503
    try:
        import yfinance as yf
        data = request.get_json() or {}
        symbols = data.get('symbols', [])
        period = data.get('period', '1y')

        if len(symbols) < 2:
            return jsonify({"error": "At least 2 symbols required"}), 400

        stock_data = {}
        for symbol in symbols:
            normalized_symbol = _normalize_ticker_symbol(symbol)
            yf_symbol = _to_yfinance_symbol(normalized_symbol, exchange='NSE')
            df = yf.download(yf_symbol, period=period, progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                stock_data[symbol] = df

        comparator = get_stock_comparator()
        comparison = comparator.compare(stock_data)
        ranked = comparator.rank_stocks(comparison)

        return jsonify({
            "status": "success",
            "count": len(ranked),
            "ranked_stocks": ranked,
        })
    except Exception as e:
        logger.error(f"Stock comparison error: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== EXPORT ENDPOINTS ====================

@app.route('/api/export/report/<ticker>', methods=['GET'])
@rate_limit
def export_stock_report(ticker):
    """Generate a comprehensive HTML report for a stock.

    When format=html (default), returns the complete HTML document as a JSON
    string so the frontend API layer (which always JSON-parses) receives it
    correctly and can open it in a new window.

    When format=json, returns a structured JSON object with all data.
    When format=download, returns a raw HTML file with Content-Disposition.
    """
    if not _HAS_EXPORT:
        return jsonify({"error": "Export module not available"}), 503
    try:
        import yfinance as yf
        exchange = request.args.get('exchange', 'NSE')
        format_type = request.args.get('format', 'html')
        normalized_ticker = _base_ticker_symbol(ticker)
        yf_symbol = _to_yfinance_symbol(normalized_ticker, exchange=exchange)

        # Gather all available data
        analysis_data = {}
        fundamentals = None
        risk_metrics = None
        prediction_data = None
        technical_data = None
        news_data = None

        # Price data
        try:
            info = yf.Ticker(yf_symbol).info or {}
            current_price = info.get("currentPrice") or info.get("regularMarketPrice")
            market_cap = info.get("marketCap")
            pe_ratio = info.get("trailingPE")
            day_high = info.get("dayHigh") or info.get("regularMarketDayHigh")
            day_low = info.get("dayLow") or info.get("regularMarketDayLow")
            prev_close = info.get("previousClose")
            _52w_high = info.get("fiftyTwoWeekHigh")
            _52w_low = info.get("fiftyTwoWeekLow")
            dividend_yield = info.get("dividendYield")
            sector = info.get("sector", "N/A")
            industry = info.get("industry", "N/A")
            company_name = info.get("shortName") or info.get("longName") or normalized_ticker

            analysis_data = {
                "company_name": company_name,
                "sector": sector,
                "industry": industry,
                "current_price": f"₹{current_price:,.2f}" if isinstance(current_price, (int, float)) else "N/A",
                "market_cap": f"₹{market_cap:,.0f}" if isinstance(market_cap, (int, float)) else "N/A",
                "pe_ratio": f"{pe_ratio:.2f}" if isinstance(pe_ratio, (int, float)) else "N/A",
                "day_range": f"₹{day_low:,.2f} — ₹{day_high:,.2f}" if isinstance(day_low, (int, float)) and isinstance(day_high, (int, float)) else "N/A",
                "prev_close": f"₹{prev_close:,.2f}" if isinstance(prev_close, (int, float)) else "N/A",
                "52w_range": f"₹{_52w_low:,.2f} — ₹{_52w_high:,.2f}" if isinstance(_52w_low, (int, float)) and isinstance(_52w_high, (int, float)) else "N/A",
                "dividend_yield": f"{dividend_yield*100:.2f}%" if isinstance(dividend_yield, (int, float)) else "N/A",
                "rsi": "N/A",
            }
        except Exception as price_err:
            logger.debug(f"Price data fetch failed for {normalized_ticker}: {price_err}")

        # Fundamentals
        if _HAS_FUNDAMENTALS:
            try:
                analyzer = get_fundamental_analyzer()
                fundamentals = analyzer.get_fundamentals(normalized_ticker, exchange)
            except Exception:
                pass

        # Risk metrics
        if _HAS_RISK:
            try:
                df = yf.download(yf_symbol, period="1y", progress=False, auto_adjust=True)
                if df is not None and not df.empty:
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    analytics = get_risk_analytics()
                    risk_metrics = analytics.compute_all_metrics(df)
            except Exception:
                pass

        # AI Prediction — extract fields for the report
        try:
            pred = predictor.predict(normalized_ticker)
            if pred and "error" not in pred:
                rec = pred.get("recommendation", {})
                price = pred.get("price_analysis", {})
                trade = pred.get("trade_setup", {})
                patterns = pred.get("pattern_analysis", {})
                prediction_data = {
                    "signal": rec.get("signal", "HOLD"),
                    "confidence": rec.get("confidence_score") or rec.get("signal_strength", "N/A"),
                    "target_price": f"₹{trade.get('target_price', 0):,.2f}" if trade.get("target_price") else "N/A",
                    "stoploss": f"₹{trade.get('stop_loss', 0):,.2f}" if trade.get("stop_loss") else "N/A",
                    "direction_probability": rec.get("direction_probability"),
                    "predicted_price_5d": f"₹{price.get('predicted_price_5d', 0):,.2f}" if price.get("predicted_price_5d") else "N/A",
                    "predicted_return_pct": f"{price.get('expected_change_pct', 0):+.2f}%" if price.get("expected_change_pct") is not None else "N/A",
                    "risk_reward_ratio": f"{trade.get('risk_reward_ratio', 0):.2f}" if trade.get("risk_reward_ratio") else "N/A",
                    "mc_uncertainty": rec.get("mc_uncertainty"),
                }
                # Technical patterns for the report
                if patterns:
                    technical_data = {
                        "patterns_detected": patterns.get("patterns_detected", []),
                        "confluence_score": patterns.get("confluence_score", 0),
                        "pattern_agreement": patterns.get("pattern_agreement", 0),
                        "dominant_pattern_signal": patterns.get("dominant_pattern_signal", "NEUTRAL"),
                        "trend_strength": patterns.get("trend_strength", 50),
                        "pattern_summary": patterns.get("pattern_summary", ""),
                    }
        except Exception as pred_err:
            logger.debug(f"Prediction for report failed: {pred_err}")

        # News/Sentiment
        try:
            news_result = news_aggregator.get_stock_news(normalized_ticker, limit=5, days_back=7)
            if news_result and news_result.get('articles'):
                news_data = {
                    "articles": news_result.get("articles", [])[:5],
                    "overall_sentiment": news_result.get("overall_sentiment", "NEUTRAL"),
                    "sentiment_score": news_result.get("aggregate", {}).get("sentiment_score", 0),
                }
        except Exception:
            pass

        export_mgr = get_export_manager()

        if format_type == 'json':
            content = export_mgr.to_json({
                "ticker": normalized_ticker,
                "analysis": analysis_data,
                "fundamentals": fundamentals,
                "risk_metrics": risk_metrics,
                "prediction": prediction_data,
                "news": news_data,
            })
            return app.response_class(content, mimetype='application/json',
                                       headers={"Content-Disposition": f"attachment; filename={normalized_ticker}_report.json"})
        elif format_type == 'download':
            # Raw HTML file download
            html = export_mgr.generate_stock_report_html(
                normalized_ticker, analysis_data, fundamentals, technical_data,
                risk_metrics, prediction_data
            )
            return app.response_class(html, mimetype='text/html',
                                       headers={"Content-Disposition": f"attachment; filename={normalized_ticker}_report.html"})
        else:
            # Default: return HTML wrapped in JSON so the frontend API layer can parse it
            html = export_mgr.generate_stock_report_html(
                normalized_ticker, analysis_data, fundamentals, technical_data,
                risk_metrics, prediction_data
            )
            return jsonify(html)
    except Exception as e:
        logger.error(f"Export error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500



@app.route('/api/export/screener', methods=['POST'])
@rate_limit
def export_screener_results():
    """Export screener results as CSV."""
    if not _HAS_EXPORT:
        return jsonify({"error": "Export module not available"}), 503
    try:
        data = request.get_json() or {}
        results = data.get('results', [])
        export_mgr = get_export_manager()
        csv_content = export_mgr.screener_to_csv(results)
        return app.response_class(csv_content, mimetype='text/csv',
                                   headers={"Content-Disposition": "attachment; filename=screener_results.csv"})
    except Exception as e:
        logger.error(f"Export screener error: {e}")
        return jsonify({"error": str(e)}), 500


# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("🚀 Starting Artha Drishti v5.0 — AI Stock Intelligence Platform")
    logger.info("📊 Screening: 18+ strategies with Committee-of-Experts screening")
    logger.info("🤖 AI Prediction: Multi-Target Neural Network with Confidence Gating")
    logger.info("📋 Fundamentals: Piotroski F-Score + Multi-Category Scoring")
    logger.info("🛡️ Risk Analytics: 30+ metrics, VaR, Efficient Frontier")
    logger.info("⏰ Data Scheduler: Auto-update at 4:00 PM IST")
    logger.info("🌐 Multi-Exchange: NSE, BSE, NYSE, NASDAQ, LSE supported")
    logger.info("📤 Exports: HTML reports, CSV, JSON")
    logger.info(f"⚙️ Runtime: env={APP_ENV} debug={APP_DEBUG} reloader={APP_USE_RELOADER} host={APP_HOST} port={APP_PORT}")
    app.run(
        host=APP_HOST,
        port=APP_PORT,
        debug=APP_DEBUG,
        threaded=APP_THREADED,
        use_reloader=APP_USE_RELOADER,
    )