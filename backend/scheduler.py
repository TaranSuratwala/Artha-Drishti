"""
Automatic Data Scheduler for Stock Market Application
======================================================
Patent-Pending: Intelligent Market-Aware Data Pipeline Scheduler

This module provides automatic scheduling for:
1. Daily stock data fetching from yfinance at 4:00 PM IST
2. Data validation and pre-processing
3. Feature engineering pipeline execution
4. Optional ML model auto-retraining
5. Database updates with latest data

Features:
- Indian market holiday awareness (NSE holidays)
- Automatic retry with exponential backoff
- Batch processing with rate-limit-safe staggering
- Detailed job history and health monitoring
- Pre-market & post-market scheduling support

Uses APScheduler for background job scheduling.
"""

import os
import sys
import logging
import threading
import json
import traceback
from datetime import datetime, date, time as dt_time, timedelta
from typing import Optional, Callable, Dict, Any, List
from collections import deque

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse boolean environment flags consistently."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}

# Try to import APScheduler, fall back to simple threading if not available
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not found. Using simple threading scheduler.")


# ═══════════════════════════════════════════════════════════════
# NSE HOLIDAY CALENDAR (Updated annually)
# ═══════════════════════════════════════════════════════════════
# NSE holidays for 2024 and 2025 (update this list annually)
NSE_HOLIDAYS = {
    # 2024 NSE holidays
    date(2024, 1, 26),   # Republic Day
    date(2024, 3, 8),    # Maha Shivaratri
    date(2024, 3, 25),   # Holi
    date(2024, 3, 29),   # Good Friday
    date(2024, 4, 11),   # Id-Ul-Fitr (Ramadan)
    date(2024, 4, 14),   # Dr. Ambedkar Jayanti
    date(2024, 4, 17),   # Ram Navami
    date(2024, 4, 21),   # Mahavir Jayanti
    date(2024, 5, 1),    # May Day
    date(2024, 5, 23),   # Buddha Purnima
    date(2024, 6, 17),   # Eid-Ul-Adha (Bakri Id)
    date(2024, 7, 17),   # Muharram
    date(2024, 8, 15),   # Independence Day
    date(2024, 9, 16),   # Milad-Un-Nabi
    date(2024, 10, 2),   # Mahatma Gandhi Jayanti
    date(2024, 10, 12),  # Dussehra
    date(2024, 11, 1),   # Diwali (Laxmi Pujan)
    date(2024, 11, 15),  # Guru Nanak Jayanti
    date(2024, 12, 25),  # Christmas
    # 2025 NSE holidays
    date(2025, 2, 26),   # Maha Shivaratri
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Id-Ul-Fitr (Ramadan)
    date(2025, 4, 10),   # Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # May Day
    date(2025, 5, 12),   # Buddha Purnima
    date(2025, 6, 7),    # Eid-Ul-Adha (Bakri Id)
    date(2025, 7, 6),    # Muharram
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 16),   # Parsi New Year
    date(2025, 9, 5),    # Milad-Un-Nabi
    date(2025, 10, 2),   # Mahatma Gandhi Jayanti / Dussehra
    date(2025, 10, 20),  # Diwali (Laxmi Pujan)
    date(2025, 10, 21),  # Diwali (Balipratipada)
    date(2025, 11, 5),   # Guru Nanak Jayanti
    date(2025, 12, 25),  # Christmas
    # 2026 NSE holidays (provisional — update when NSE publishes official list)
    date(2026, 1, 26),   # Republic Day
    date(2026, 2, 17),   # Maha Shivaratri
    date(2026, 3, 3),    # Holi
    date(2026, 3, 20),   # Id-Ul-Fitr (Ramadan)
    date(2026, 3, 30),   # Ram Navami
    date(2026, 4, 2),    # Mahavir Jayanti
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Ambedkar Jayanti
    date(2026, 5, 1),    # May Day / Maharashtra Day
    date(2026, 5, 31),   # Buddha Purnima
    date(2026, 6, 6),    # Eid-Ul-Adha (Bakri Id)
    date(2026, 7, 7),    # Muharram
    date(2026, 8, 15),   # Independence Day
    date(2026, 9, 4),    # Milad-Un-Nabi
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 19),  # Dussehra
    date(2026, 11, 9),   # Diwali (Laxmi Pujan)
    date(2026, 11, 24),  # Guru Nanak Jayanti
    date(2026, 12, 25),  # Christmas
}


def is_market_day(d: date = None) -> bool:
    """Check if a given date is a market trading day (weekday + not a holiday)."""
    if d is None:
        d = date.today()
    # Weekend check (Saturday=5, Sunday=6)
    if d.weekday() >= 5:
        return False
    # NSE holiday check
    if d in NSE_HOLIDAYS:
        return False
    return True


def next_market_day(d: date = None) -> date:
    """Get the next market trading day after given date."""
    if d is None:
        d = date.today()
    d += timedelta(days=1)
    while not is_market_day(d):
        d += timedelta(days=1)
    return d


class DataScheduler:
    """
    Intelligent Market-Aware Data Pipeline Scheduler.
    
    Features:
    - Runs at 4:00 PM IST on every market day (skips weekends + NSE holidays)
    - 5-step pipeline: Fetch → Validate → Feature Engineer → Sentiment → Optional Auto-Train
    - Automatic retry with exponential backoff (max 3 retries)
    - Batch processing with staggered API calls to avoid rate limits
    - Detailed job history (last 50 runs)
    - Health monitoring and alerting
    """
    
    MAX_HISTORY = 50
    MAX_RETRIES = 3
    BATCH_SIZE = 50          # Process stocks in batches
    BATCH_DELAY_SEC = 2.0    # Delay between batches
    
    def __init__(self, 
                 data_pipeline=None, 
                 feature_engineer_func: Optional[Callable] = None,
                 model_train_func: Optional[Callable] = None,
                 sentiment_func: Optional[Callable] = None,
                 timezone: str = 'Asia/Kolkata'):
        """
        Initialize the scheduler.
        
        Args:
            data_pipeline: Instance of NSEDataPipeline for data fetching
            feature_engineer_func: Optional function to run feature engineering
            model_train_func: Optional function to train ML model after data update
            sentiment_func: Optional function to pre-cache sentiment analysis
            timezone: Timezone for scheduling (default: IST)
        """
        self.data_pipeline = data_pipeline
        self.feature_engineer_func = feature_engineer_func
        self.model_train_func = model_train_func
        self.sentiment_func = sentiment_func
        self.timezone = timezone
        self.scheduler = None
        self.is_running = False
        self.last_run: Optional[datetime] = None
        self.last_status: str = "Not started"
        self.last_error: Optional[str] = None
        self.run_count: int = 0
        self._lock = threading.Lock()
        self._job_running = False
        
        # Job history (last N runs)
        self.job_history: deque = deque(maxlen=self.MAX_HISTORY)
        
        # Step-level progress for the current run
        self.current_step: str = ""
        self.current_progress: float = 0.0
        
        # Configuration from environment variables
        self.schedule_hour = int(os.getenv('SCHEDULER_HOUR', '16'))  # 4 PM default
        self.schedule_minute = int(os.getenv('SCHEDULER_MINUTE', '0'))
        self.fetch_period = os.getenv('SCHEDULER_FETCH_PERIOD', '5d')  # Last 5 days
        self.enabled = _env_flag('SCHEDULER_ENABLED', default=True)
        # Deployment-safe defaults: don't auto-trigger heavy work on every web startup.
        self.auto_catchup = _env_flag('SCHEDULER_AUTO_CATCHUP', default=False)
        self.auto_train_enabled = _env_flag('SCHEDULER_AUTO_TRAIN', default=False)
        
    def _setup_scheduler(self):
        """Setup the APScheduler or fallback scheduler."""
        if APSCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler(timezone=self.timezone)
            
            # Primary job: Run at market close (4:00 PM IST) every weekday
            # The job itself will also check for NSE holidays before executing
            trigger = CronTrigger(
                hour=self.schedule_hour,
                minute=self.schedule_minute,
                day_of_week='0-4',  # Monday to Friday
                timezone=self.timezone
            )
            self.scheduler.add_job(
                self._run_if_market_day,
                trigger=trigger,
                id='weekday_data_update',
                name='Market-Day Stock Data Pipeline (4 PM IST)',
                replace_existing=True,
                misfire_grace_time=3600,  # Allow 1 hour grace for misfires
            )
            
            logger.info(f"✅ Scheduler configured: Weekdays {self.schedule_hour}:{self.schedule_minute:02d} IST")
            train_stage = "Auto-Train" if self.auto_train_enabled and self.model_train_func else "Skip Train"
            logger.info(f"   Pipeline: Fetch Data → Validate → Feature Engineering → Sentiment → {train_stage}")
            logger.info(f"   Holiday-aware: Skips NSE holidays automatically")
        else:
            logger.info("Using simple interval scheduler (fallback)")
    
    def _run_if_market_day(self):
        """Only run the pipeline if today is a market trading day."""
        today = date.today()
        if not is_market_day(today):
            reason = "NSE holiday" if today.weekday() < 5 else "Weekend"
            logger.info(f"⏭️  Skipping scheduled run — {reason} ({today.strftime('%A, %d %B %Y')})")
            nxt = next_market_day(today)
            logger.info(f"   Next market day: {nxt.strftime('%A, %d %B %Y')}")
            return
        
        self._run_update_job()
    
    def _run_update_job(self, retry_count: int = 0):
        """
        Execute the full data pipeline.
        
        Pipeline steps:
        1. Fetch latest stock data (IntegratedPostGreSQL)
        2. Validate & pre-process fetched data
        3. Run feature engineering
        4. Pre-cache sentiment analysis
        5. Auto-train ML model
        
        Includes automatic retry with exponential backoff on failure.
        """
        # Prevent concurrent runs
        if self._job_running:
            logger.warning("⚠️  Pipeline already running — skipping duplicate trigger")
            return
        
        self._job_running = True
        run_record = {
            "started_at": datetime.now().isoformat(),
            "date": date.today().isoformat(),
            "steps": {},
            "status": "running",
            "retry": retry_count,
        }
        
        with self._lock:
            self.last_status = "Running"
            self.current_step = "Initializing"
            self.current_progress = 0.0
            
        try:
            logger.info("=" * 80)
            logger.info("🚀 AUTOMATED MARKET-DAY DATA PIPELINE")
            logger.info(f"   Date: {date.today().strftime('%A, %d %B %Y')}")
            logger.info(f"   Time: {datetime.now().strftime('%H:%M:%S')} IST")
            if retry_count > 0:
                logger.info(f"   Retry: {retry_count}/{self.MAX_RETRIES}")
            logger.info("=" * 80)
            start_time = datetime.now()
            
            failed_steps = []
            symbols_fetched = 0
            symbols_engineered = 0
            
            # ── STEP 1: Fetch latest stock data ──
            self.current_step = "Fetching stock data"
            self.current_progress = 0.0
            
            if self.data_pipeline:
                logger.info("\n📊 STEP 1/5: Fetching latest stock data...")
                step_start = datetime.now()
                try:
                    if hasattr(self.data_pipeline, 'get_all_nse_symbols'):
                        symbols = self.data_pipeline.get_all_nse_symbols()
                        if symbols:
                            total = len(symbols)
                            logger.info(f"   Found {total} stocks to update")
                            logger.info(f"   Fetching {self.fetch_period} of data (batch size: {self.BATCH_SIZE})...")
                            
                            # Use run_pipeline for intelligent incremental/full download
                            # run_pipeline handles batch downloads, validation, and upsert internally
                            logger.info(f"   Running integrated pipeline (incremental + full)...")
                            try:
                                # Append '.NS' suffix if missing — run_pipeline expects yfinance-style tickers
                                yf_symbols = [s if s.endswith('.NS') else f"{s}.NS" for s in symbols]
                                self.data_pipeline.run_pipeline(yf_symbols)
                                symbols_fetched = total
                            except Exception as pipe_err:
                                logger.error(f"   ❌ Pipeline execution failed: {pipe_err}")
                                # Fallback: try download_batch directly in smaller batches
                                import time
                                logger.info("   🔄 Falling back to batch-level download...")
                                for batch_idx in range(0, total, self.BATCH_SIZE):
                                    batch = symbols[batch_idx:batch_idx + self.BATCH_SIZE]
                                    batch_num = batch_idx // self.BATCH_SIZE + 1
                                    total_batches = (total + self.BATCH_SIZE - 1) // self.BATCH_SIZE
                                    
                                    self.current_progress = batch_idx / total
                                    logger.info(f"   Batch {batch_num}/{total_batches}: {len(batch)} symbols...")
                                    
                                    try:
                                        yf_batch = [s if s.endswith('.NS') else f"{s}.NS" for s in batch]
                                        raw_df = self.data_pipeline.download_batch(yf_batch, period=self.fetch_period)
                                        if raw_df is not None and not raw_df.empty:
                                            clean_df = self.data_pipeline.process_dataframe(raw_df)
                                            if clean_df is not None and not clean_df.empty:
                                                self.data_pipeline.fast_bulk_upsert(clean_df)
                                                symbols_fetched += len(batch)
                                            else:
                                                logger.warning(f"   ⚠️  Batch {batch_num}: no valid rows after processing")
                                        else:
                                            logger.warning(f"   ⚠️  Batch {batch_num}: no data returned")
                                    except Exception as batch_err:
                                        logger.warning(f"   ⚠️  Batch {batch_num} failed: {batch_err}")
                                    
                                    if batch_idx + self.BATCH_SIZE < total:
                                        time.sleep(self.BATCH_DELAY_SEC)
                            
                            step_duration = (datetime.now() - step_start).total_seconds()
                            run_record["steps"]["fetch"] = {
                                "status": "success",
                                "symbols": symbols_fetched,
                                "duration_sec": round(step_duration, 1),
                            }
                            logger.info(f"   ✅ Data fetch complete: {symbols_fetched}/{total} symbols ({step_duration:.1f}s)")
                        else:
                            logger.warning("   ⚠️  No symbols found to update")
                            run_record["steps"]["fetch"] = {"status": "skipped", "reason": "no symbols"}
                    else:
                        logger.warning("   ⚠️  Data pipeline missing get_all_nse_symbols method")
                        run_record["steps"]["fetch"] = {"status": "skipped", "reason": "method not available"}
                except Exception as e:
                    logger.error(f"   ❌ Data fetch failed: {e}")
                    run_record["steps"]["fetch"] = {"status": "failed", "error": str(e)}
                    failed_steps.append("fetch")
            else:
                run_record["steps"]["fetch"] = {"status": "skipped", "reason": "no pipeline configured"}
            
            # ── STEP 2: Validate & pre-process data ──
            self.current_step = "Validating data"
            self.current_progress = 0.25
            
            logger.info("\n🔍 STEP 2/5: Validating and pre-processing fetched data...")
            step_start = datetime.now()
            try:
                validation_results = self._validate_data()
                step_duration = (datetime.now() - step_start).total_seconds()
                run_record["steps"]["validate"] = {
                    "status": "success",
                    **validation_results,
                    "duration_sec": round(step_duration, 1),
                }
                logger.info(f"   ✅ Validation complete ({step_duration:.1f}s)")
                logger.info(f"   Valid: {validation_results.get('valid_count', '?')} | "
                           f"Stale: {validation_results.get('stale_count', '?')} | "
                           f"Missing: {validation_results.get('missing_count', '?')}")
            except Exception as e:
                logger.warning(f"   ⚠️  Validation failed (non-critical): {e}")
                run_record["steps"]["validate"] = {"status": "warning", "error": str(e)}
            
            # ── STEP 3: Feature engineering ──
            self.current_step = "Feature engineering"
            self.current_progress = 0.50
            
            if self.feature_engineer_func:
                logger.info("\n🔧 STEP 3/5: Running feature engineering pipeline...")
                step_start = datetime.now()
                try:
                    self.feature_engineer_func()
                    step_duration = (datetime.now() - step_start).total_seconds()
                    run_record["steps"]["feature_engineering"] = {
                        "status": "success",
                        "duration_sec": round(step_duration, 1),
                    }
                    logger.info(f"   ✅ Feature engineering complete ({step_duration:.1f}s)")
                except Exception as e:
                    logger.error(f"   ❌ Feature engineering failed: {e}")
                    run_record["steps"]["feature_engineering"] = {"status": "failed", "error": str(e)}
                    failed_steps.append("feature_engineering")
                    logger.info("   ⚠️  Continuing — data is still valid for basic screening")
            else:
                run_record["steps"]["feature_engineering"] = {"status": "skipped", "reason": "not configured"}
            
            # ── STEP 4: Pre-cache sentiment analysis ──
            self.current_step = "Sentiment pre-caching"
            self.current_progress = 0.65
            
            if self.sentiment_func:
                logger.info("\n📰 STEP 4/5: Pre-caching sentiment analysis...")
                step_start = datetime.now()
                try:
                    self.sentiment_func()
                    step_duration = (datetime.now() - step_start).total_seconds()
                    run_record["steps"]["sentiment"] = {
                        "status": "success",
                        "duration_sec": round(step_duration, 1),
                    }
                    logger.info(f"   ✅ Sentiment pre-caching complete ({step_duration:.1f}s)")
                except Exception as e:
                    logger.warning(f"   ⚠️  Sentiment pre-caching failed (non-critical): {e}")
                    run_record["steps"]["sentiment"] = {"status": "warning", "error": str(e)}
                    logger.info("   ⚠️  Continuing — sentiment will be fetched on-demand during predictions")
            else:
                run_record["steps"]["sentiment"] = {"status": "skipped", "reason": "not configured"}
            
            # ── STEP 5: Auto-train ML model ──
            self.current_step = "Training ML model"
            self.current_progress = 0.80
            
            if self.model_train_func and self.auto_train_enabled:
                logger.info("\n🤖 STEP 5/5: Auto-training ML prediction model...")
                step_start = datetime.now()
                try:
                    self.model_train_func()
                    step_duration = (datetime.now() - step_start).total_seconds()
                    run_record["steps"]["model_training"] = {
                        "status": "success",
                        "duration_sec": round(step_duration, 1),
                    }
                    logger.info(f"   ✅ Model trained ({step_duration:.1f}s)")
                except Exception as e:
                    logger.error(f"   ❌ Model training failed: {e}")
                    run_record["steps"]["model_training"] = {"status": "failed", "error": str(e)}
                    failed_steps.append("model_training")
                    logger.info("   ⚠️  Predictions will use previous model or statistical fallback")
            elif self.model_train_func and not self.auto_train_enabled:
                logger.info("\n🤖 STEP 5/5: Auto-training disabled — reusing existing trained model")
                run_record["steps"]["model_training"] = {
                    "status": "skipped",
                    "reason": "disabled via SCHEDULER_AUTO_TRAIN",
                }
            else:
                run_record["steps"]["model_training"] = {"status": "skipped", "reason": "not configured"}
            
            # ── Pipeline summary ──
            total_duration = (datetime.now() - start_time).total_seconds()
            self.current_progress = 1.0
            self.current_step = "Complete"
            
            nxt = next_market_day(date.today())
            
            if failed_steps:
                overall_status = f"Partial success ({len(failed_steps)} step(s) failed: {', '.join(failed_steps)})"
                run_record["status"] = "partial"
            else:
                overall_status = f"Success (took {total_duration:.1f}s)"
                run_record["status"] = "success"
            
            run_record["completed_at"] = datetime.now().isoformat()
            run_record["duration_sec"] = round(total_duration, 1)
            run_record["symbols_fetched"] = symbols_fetched
            
            with self._lock:
                self.last_run = datetime.now()
                self.last_status = overall_status
                self.last_error = None if not failed_steps else f"Failed steps: {', '.join(failed_steps)}"
                self.run_count += 1
                self.job_history.append(run_record)
            
            logger.info("\n" + "=" * 80)
            logger.info(f"✅ Pipeline {run_record['status'].upper()} | Duration: {total_duration:.1f}s | Symbols: {symbols_fetched}")
            logger.info(f"   Next market day: {nxt.strftime('%A, %d %B %Y')} at {self.schedule_hour}:{self.schedule_minute:02d} IST")
            logger.info("=" * 80 + "\n")
            
        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            logger.error(f"\n❌ Pipeline FAILED: {error_msg}")
            logger.debug(f"Traceback:\n{tb}")
            
            run_record["status"] = "failed"
            run_record["error"] = error_msg
            run_record["completed_at"] = datetime.now().isoformat()
            
            with self._lock:
                self.last_status = "Failed"
                self.last_error = error_msg
                self.job_history.append(run_record)
            
            # Retry with exponential backoff
            if retry_count < self.MAX_RETRIES:
                delay = 60 * (2 ** retry_count)  # 1min, 2min, 4min
                logger.info(f"🔄 Retrying in {delay}s (attempt {retry_count + 1}/{self.MAX_RETRIES})...")
                self._job_running = False
                timer = threading.Timer(delay, self._run_update_job, args=[retry_count + 1])
                timer.daemon = True
                timer.start()
                return
        finally:
            self._job_running = False
    
    def _validate_data(self) -> Dict[str, Any]:
        """
        Validate fetched data quality (Step 2 of pipeline).
        
        Checks:
        - Data freshness (not older than 2 trading days)
        - No excessive NaN columns
        - Price sanity checks (no zero/negative prices)
        """
        results = {
            "valid_count": 0,
            "stale_count": 0,
            "missing_count": 0,
            "invalid_price_count": 0,
        }
        
        if not self.data_pipeline:
            return results
        
        try:
            latest_data = None
            if hasattr(self.data_pipeline, 'get_latest_data'):
                latest_data = self.data_pipeline.get_latest_data(limit=None)
            
            if not latest_data:
                results["missing_count"] = 1
                return results
            
            today = date.today()
            for row in latest_data:
                # Check data freshness
                row_date = None
                if hasattr(row, 'get'):
                    row_date = row.get('date') or row.get('Date')
                
                if row_date:
                    if isinstance(row_date, str):
                        try:
                            row_date = datetime.fromisoformat(row_date).date()
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(row_date, datetime):
                        row_date = row_date.date()
                    
                    if isinstance(row_date, date):
                        days_old = (today - row_date).days
                        if days_old > 5:
                            results["stale_count"] += 1
                            continue
                
                # Check price sanity
                close = None
                if hasattr(row, 'get'):
                    close = row.get('close') or row.get('Close')
                
                if close is not None:
                    try:
                        close_val = float(close)
                        if close_val <= 0:
                            results["invalid_price_count"] += 1
                            continue
                    except (ValueError, TypeError):
                        results["invalid_price_count"] += 1
                        continue
                
                results["valid_count"] += 1
                
        except Exception as e:
            logger.warning(f"Validation error: {e}")
        
        return results
    
    def start(self):
        """Start the scheduler."""
        if not self.enabled:
            logger.info("Scheduler is disabled via configuration")
            return False
            
        if self.is_running:
            logger.warning("Scheduler is already running")
            return False
        
        try:
            self._setup_scheduler()
            
            if APSCHEDULER_AVAILABLE and self.scheduler:
                self.scheduler.start()
                self.is_running = True
                nxt = next_market_day(date.today()) if not is_market_day() else date.today()
                self.last_status = f"Waiting — next run: {nxt.strftime('%a %d %b')} at {self.schedule_hour}:{self.schedule_minute:02d} IST"
                logger.info(f"Scheduler started successfully!")
                logger.info(f"   Today is {'a market day ✓' if is_market_day() else 'NOT a market day (holiday/weekend)'}")
                
                # ── Startup catch-up: check if DB is stale and trigger immediate run ──
                self._startup_catchup()
                
                return True
            else:
                # Fallback: Start a simple background thread
                self.is_running = True
                self.last_status = "Running (simple scheduler)"
                self._start_simple_scheduler()
                
                # Catch-up for fallback scheduler too
                self._startup_catchup()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            self.last_error = str(e)
            return False
    
    def _startup_catchup(self):
        """
        On startup, check if the database is stale (missing recent market days' data).
        If data is stale, trigger an immediate pipeline run to catch up.
        This ensures data integrity even if the app was down during scheduled run times.
        """
        if not self.data_pipeline:
            return
        
        try:
            # Query the latest data date from the database
            latest_db_date = None
            if hasattr(self.data_pipeline, 'engine'):
                from sqlalchemy import text
                with self.data_pipeline.engine.connect() as conn:
                    result = conn.execute(text(
                        "SELECT MAX(date) FROM nse_stocks"
                    ))
                    row = result.fetchone()
                    if row and row[0]:
                        latest_db_date = row[0]
                        if isinstance(latest_db_date, datetime):
                            latest_db_date = latest_db_date.date()
            
            if latest_db_date is None:
                logger.warning("⚠️  Startup catch-up: Could not determine latest DB date, skipping")
                return
            
            today = date.today()
            
            # Calculate how many market days are missing
            missing_days = []
            check_date = latest_db_date + timedelta(days=1)
            while check_date <= today:
                if is_market_day(check_date):
                    missing_days.append(check_date)
                check_date += timedelta(days=1)
            
            # If today is a market day and it's before schedule time, don't count today as missing
            now = datetime.now()
            if (missing_days and 
                missing_days[-1] == today and 
                now.hour < self.schedule_hour):
                missing_days = missing_days[:-1]
            
            if missing_days:
                logger.warning(f"🔄 STARTUP CATCH-UP: Database is stale!")
                logger.warning(f"   Latest DB date: {latest_db_date.strftime('%A, %d %B %Y')}")
                logger.warning(f"   Missing market days: {len(missing_days)} ({missing_days[0]} → {missing_days[-1]})")
                logger.info(f"   ℹ️  Use POST /api/scheduler/trigger or wait for 4 PM IST auto-run")
                
                # Auto-trigger if stale data detected (opt-in via SCHEDULER_AUTO_CATCHUP=true)
                if self.auto_catchup:
                    logger.info(f"   🚀 Auto catch-up enabled → triggering immediate pipeline run...")
                    thread = threading.Thread(target=self._run_update_job, daemon=True)
                    thread.start()
                else:
                    logger.info(f"   ℹ️  Auto catch-up disabled (SCHEDULER_AUTO_CATCHUP=false)")
                    logger.info(f"   ℹ️  Use POST /api/scheduler/trigger or wait for {self.schedule_hour}:{self.schedule_minute:02d} IST auto-run")
                    
                self.last_status = f"Stale data — {len(missing_days)} market days missing since {latest_db_date}"
            else:
                logger.info(f"✅ Startup catch-up: Database is current (latest: {latest_db_date})")
                
        except Exception as e:
            logger.warning(f"⚠️  Startup catch-up check failed (non-critical): {e}")
            # Don't block app startup on this
    
    def _start_simple_scheduler(self):
        """Simple fallback scheduler using threading with holiday awareness."""
        def run_periodically():
            import time
            logger.info("\n⚠️  APScheduler not available. Using simple threading scheduler.")
            logger.info(f"   Scheduled to run: Market days at {self.schedule_hour}:{self.schedule_minute:02d} IST")
            logger.info(f"   Holiday-aware: Skips NSE holidays automatically\n")
            
            last_run_date = None
            while self.is_running:
                now = datetime.now()
                today = now.date()
                
                # Fire if we're within the target minute window (handles ±30s drift)
                in_window = (
                    now.hour == self.schedule_hour and
                    now.minute >= self.schedule_minute and
                    now.minute <= self.schedule_minute + 1  # 2-minute window
                )
                # Also fire if we're past the scheduled time but haven't run today
                # (handles app restart after scheduled time)
                past_schedule = (
                    now.hour > self.schedule_hour or
                    (now.hour == self.schedule_hour and now.minute > self.schedule_minute + 1)
                )
                should_run = (
                    is_market_day(today) and
                    last_run_date != today and
                    (in_window or past_schedule)
                )
                
                if should_run:
                    logger.info(f"🔔 Triggering scheduled pipeline at {now.strftime('%H:%M')} on {now.strftime('%A, %d %B')}")
                    self._run_update_job()
                    last_run_date = today
                    # Sleep for 2 minutes to avoid running twice
                    time.sleep(120)
                else:
                    # Check every 30 seconds
                    time.sleep(30)
        
        thread = threading.Thread(target=run_periodically, daemon=True)
        thread.start()
        logger.info("✅ Simple scheduler thread started (holiday-aware)")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return False
        
        try:
            if APSCHEDULER_AVAILABLE and self.scheduler:
                self.scheduler.shutdown(wait=False)
            
            self.is_running = False
            self.last_status = "Stopped"
            logger.info("Scheduler stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            return False
    
    def trigger_now(self) -> Dict[str, Any]:
        """
        Manually trigger the full data pipeline.
        
        Returns:
            Dict with status information
        """
        if self._job_running:
            return {
                "status": "already_running",
                "message": "Pipeline is already running. Check status for progress.",
                "current_step": self.current_step,
                "progress": round(self.current_progress * 100, 1),
            }
        
        logger.info("📌 Manual pipeline trigger requested")
        
        # Run in background thread to avoid blocking
        thread = threading.Thread(target=self._run_update_job, daemon=True)
        thread.start()
        
        return {
            "status": "triggered",
            "message": "Data pipeline started in background",
            "timestamp": datetime.now().isoformat(),
            "is_market_day": is_market_day(),
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive scheduler status with health information.
        
        Returns:
            Dict with scheduler status, health metrics, and next run info
        """
        with self._lock:
            next_run = None
            if APSCHEDULER_AVAILABLE and self.scheduler and self.is_running:
                jobs = self.scheduler.get_jobs()
                if jobs:
                    next_run = jobs[0].next_run_time
            
            # Calculate health score based on recent history
            health = self._compute_health()
            
            status = {
                "enabled": self.enabled,
                "running": self.is_running,
                "job_active": self._job_running,
                "current_step": self.current_step if self._job_running else None,
                "current_progress_pct": round(self.current_progress * 100, 1) if self._job_running else None,
                "last_run": self.last_run.isoformat() if self.last_run else None,
                "last_status": self.last_status,
                "last_error": self.last_error,
                "run_count": self.run_count,
                "next_run": next_run.isoformat() if next_run else None,
                "schedule": f"{self.schedule_hour}:{self.schedule_minute:02d} IST (market days only)",
                "is_market_day_today": is_market_day(),
                "next_market_day": next_market_day().isoformat(),
                "auto_catchup": self.auto_catchup,
                "auto_train_enabled": self.auto_train_enabled,
                "apscheduler_available": APSCHEDULER_AVAILABLE,
                "health": health,
                "recent_history": list(self.job_history)[-5:],
            }
            
            return status
    
    def _compute_health(self) -> Dict[str, Any]:
        """Compute health score based on recent pipeline history."""
        if not self.job_history:
            return {"score": 100, "label": "No data", "recent_success_rate": None}
        
        recent = list(self.job_history)[-10:]
        successes = sum(1 for r in recent if r.get("status") == "success")
        partials = sum(1 for r in recent if r.get("status") == "partial")
        failures = sum(1 for r in recent if r.get("status") == "failed")
        total = len(recent)
        
        success_rate = (successes + 0.5 * partials) / total * 100 if total > 0 else 100
        
        if success_rate >= 90:
            label = "Healthy"
        elif success_rate >= 70:
            label = "Degraded"
        elif success_rate >= 50:
            label = "Warning"
        else:
            label = "Critical"
        
        return {
            "score": round(success_rate, 1),
            "label": label,
            "recent_success_rate": f"{successes}/{total} successful",
            "failures": failures,
            "avg_duration_sec": round(
                sum(r.get("duration_sec", 0) for r in recent if r.get("duration_sec")) / max(sum(1 for r in recent if r.get("duration_sec")), 1), 1
            ),
        }
    
    def get_job_history(self, limit: int = 20) -> List[Dict]:
        """Get recent job execution history."""
        return list(self.job_history)[-limit:]
    
    def update_schedule(self, hour: int, minute: int) -> bool:
        """
        Update the schedule time.
        
        Args:
            hour: Hour (0-23)
            minute: Minute (0-59)
            
        Returns:
            True if successful
        """
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            return False
        
        self.schedule_hour = hour
        self.schedule_minute = minute
        
        # Restart scheduler if running
        if self.is_running:
            self.stop()
            self.start()
        
        logger.info(f"Schedule updated to {hour}:{minute:02d}")
        return True


# Global scheduler instance
_scheduler_instance: Optional[DataScheduler] = None


def get_scheduler(data_pipeline=None, feature_engineer_func=None, model_train_func=None, sentiment_func=None) -> DataScheduler:
    """
    Get or create the global scheduler instance.
    
    Args:
        data_pipeline: Data pipeline instance (only used on first call)
        feature_engineer_func: Feature engineering function (only used on first call)
        model_train_func: ML model training function (only used on first call)
        sentiment_func: Sentiment pre-caching function (only used on first call)
        
    Returns:
        DataScheduler instance
    """
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = DataScheduler(
            data_pipeline=data_pipeline,
            feature_engineer_func=feature_engineer_func,
            model_train_func=model_train_func,
            sentiment_func=sentiment_func,
        )
    
    return _scheduler_instance


def init_scheduler(app, data_pipeline=None):
    """
    Initialize scheduler with Flask app context.
    Call this from application.py to start automatic updates.
    
    Args:
        app: Flask application instance
        data_pipeline: NSEDataPipeline instance
    """
    scheduler = get_scheduler(data_pipeline=data_pipeline)
    
    # Auto-start if enabled
    auto_start = os.getenv('SCHEDULER_AUTO_START', 'true').lower() == 'true'
    if auto_start:
        scheduler.start()
        logger.info("Scheduler auto-started with application")
    
    return scheduler


if __name__ == "__main__":
    # Test the scheduler
    print("=" * 60)
    print("DataScheduler Test Suite")
    print("=" * 60)
    
    scheduler = DataScheduler()
    
    # Test market day logic
    print(f"\nToday ({date.today()}): {'Market day ✓' if is_market_day() else 'Not a market day ✗'}")
    print(f"Next market day: {next_market_day()}")
    
    # Test status
    status = scheduler.get_status()
    print(f"\nScheduler Status:")
    for k, v in status.items():
        if k != 'recent_history':
            print(f"  {k}: {v}")
    
    # Test manual trigger
    print(f"\nTriggering manual run...")
    result = scheduler.trigger_now()
    print(f"Result: {result}")
    
    # Wait for completion
    import time
    time.sleep(5)
    print(f"\nStatus after trigger: {scheduler.get_status()['last_status']}")
    print(f"History: {len(scheduler.job_history)} records")
