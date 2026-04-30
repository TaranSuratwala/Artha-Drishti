
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.backtesting.data_handler import DataHandler
from backend.backtesting.strategy import Strategy
from backend.backtesting.engine import UniversalBacktestEngine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock Pipeline
class MockPipeline:
    def get_ticker_history(self, ticker):
        # Generate synthetic data
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='B')
        n = len(dates)
        
        # Random walk
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, n)
        price = 100 * np.cumprod(1 + returns)
        
        data = []
        for i in range(n):
            row = {
                'date': dates[i],
                'open': price[i],
                'high': price[i] * 1.01,
                'low': price[i] * 0.99,
                'close': price[i] * (1 + np.random.normal(0, 0.005)),
                'volume': 1000000,
                'adj_close': price[i] # Simple case
            }
            # Add ATR manually for test
            row['atr_14'] = row['close'] * 0.02
            data.append(row)
            
        return data

# Sample Strategy
class TestSMAStrategy(Strategy):
    def on_bar(self, bar, portfolio_value):
        # Very simple random logic for testing
        # In real life, we'd use indicators
        
        # Access internal state or calculator
        # For test, let's just buy on first bar and hold
        if self.position == 0:
            return {
                'action': 'BUY',
                'quantity': 10,
                'type': 'MARKET'
            }
        elif bar['close'] > 150 and self.position > 0:
             return {
                'action': 'SELL',
                'quantity': 10,
                'type': 'MARKET'
            }
        return None

def run_verification():
    logger.info("Running Backtest Verification...")
    
    pipeline = MockPipeline()
    data_handler = DataHandler(pipeline)
    engine = UniversalBacktestEngine(data_handler)
    
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    
    results = engine.run_backtest(
        ticker="TESTSCO",
        strategy_class=TestSMAStrategy,
        strategy_params={},
        start_date=start_date,
        end_date=end_date,
        initial_capital=10000.0
    )
    
    if "error" in results:
        logger.error(f"Backtest failed: {results['error']}")
    else:
        logger.info("Backtest Completed Successfully!")
        logger.info(f"Total Return: {results['total_return_pct']:.2f}%")
        logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        logger.info(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
        logger.info(f"Total Trades: {results['total_trades']}")

if __name__ == "__main__":
    run_verification()
