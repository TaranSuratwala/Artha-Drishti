import os
import sys
import logging
from datetime import datetime

# Ensure we can import from backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from IntegratedPostGreSQL import NSEDataPipeline
from scheduler import is_market_day

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_pipeline():
    """Run the daily data fetch pipeline if it's a market day."""
    if not is_market_day():
        logger.info("Not a market day. Skipping execution.")
        return

    logger.info("Market day detected. Initializing data pipeline...")
    
    # Requires DATABASE_URL environment variable to be set
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable is missing!")
        sys.exit(1)

    try:
        pipeline = NSEDataPipeline(db_url)
        logger.info("Starting daily data update...")
        
        # 1. Get all symbols
        symbols = pipeline.get_all_nse_symbols()
        if not symbols:
            logger.error("Failed to retrieve symbols.")
            sys.exit(1)
            
        # 2. Run the update pipeline for these symbols
        pipeline.run_pipeline(symbols, force_full_refresh=False)
        
        logger.info("Daily data update completed successfully.")
    except Exception as e:
        logger.error(f"Error during data update: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()
