import sys
import os

# Add backend directory to path
sys.path.append(os.path.abspath(r"c:\Users\Lenovo\Documents\VS CODE codes(files)\helloworld\Project sem-6\backend"))

from StockScreener import InteractiveStockScreener
from IntegratedPostGreSQL import NSEDataPipeline
import pandas as pd

def test_screener():
    pipeline = NSEDataPipeline()
    screener = InteractiveStockScreener(pipeline=pipeline)
    # Mock data fetch to test
    df = pd.DataFrame({
        'open': [100]*50,
        'high': [105]*50,
        'low': [95]*50,
        'close': [100 + i for i in range(50)],
        'volume': [1000]*50
    })
    # Add a date index
    df['date'] = pd.date_range(start='2023-01-01', periods=50, freq='D')
    
    # Mock _get_tickers
    screener._get_tickers = lambda: ["RELIANCE.NS"]
    
    # Mock _fetch_stock_data
    screener._fetch_stock_data = lambda ticker: df.copy()
    
    res = screener.run_screening_multi(["macd_triple_alignment", "momentum"], max_results=5)
    
    print("Test Output:")
    print(res)

if __name__ == "__main__":
    test_screener()
