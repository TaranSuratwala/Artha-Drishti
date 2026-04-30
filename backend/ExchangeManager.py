"""
Exchange Abstraction Layer
==========================
Provides a unified interface for fetching stock data from multiple exchanges.
Supports: NSE, BSE, NYSE, NASDAQ
"""

import os
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExchangeConfig:
    """Configuration for an exchange"""
    name: str
    suffix: str  # Ticker suffix (e.g., ".NS" for NSE)
    currency: str
    timezone: str
    trading_hours: Dict[str, str]  # {'open': '09:15', 'close': '15:30'}
    holidays: List[str] = None  # List of holiday dates
    
    def format_ticker(self, symbol: str) -> str:
        """Format symbol with exchange suffix"""
        if self.suffix and not symbol.endswith(self.suffix):
            return f"{symbol}{self.suffix}"
        return symbol


# Predefined exchange configurations
EXCHANGES = {
    'NSE': ExchangeConfig(
        name='National Stock Exchange of India',
        suffix='.NS',
        currency='INR',
        timezone='Asia/Kolkata',
        trading_hours={'open': '09:15', 'close': '15:30'}
    ),
    'BSE': ExchangeConfig(
        name='Bombay Stock Exchange',
        suffix='.BO',
        currency='INR',
        timezone='Asia/Kolkata',
        trading_hours={'open': '09:15', 'close': '15:30'}
    ),
    'NYSE': ExchangeConfig(
        name='New York Stock Exchange',
        suffix='',  # No suffix for US stocks
        currency='USD',
        timezone='America/New_York',
        trading_hours={'open': '09:30', 'close': '16:00'}
    ),
    'NASDAQ': ExchangeConfig(
        name='NASDAQ',
        suffix='',  # No suffix for US stocks
        currency='USD',
        timezone='America/New_York',
        trading_hours={'open': '09:30', 'close': '16:00'}
    ),
    'LSE': ExchangeConfig(
        name='London Stock Exchange',
        suffix='.L',
        currency='GBP',
        timezone='Europe/London',
        trading_hours={'open': '08:00', 'close': '16:30'}
    )
}


class ExchangeDataProvider(ABC):
    """Abstract base class for exchange data providers"""
    
    @abstractmethod
    def fetch_stock_data(self, symbol: str, period: str = '1y') -> pd.DataFrame:
        """Fetch historical stock data"""
        pass
    
    @abstractmethod
    def fetch_live_price(self, symbol: str) -> Dict[str, Any]:
        """Fetch current live price"""
        pass
    
    @abstractmethod
    def search_symbol(self, query: str) -> List[Dict[str, str]]:
        """Search for symbols matching query"""
        pass


class YFinanceProvider(ExchangeDataProvider):
    """
    Data provider using Yahoo Finance API.
    Works for most major exchanges.
    """
    
    def __init__(self, exchange_key: str = 'NSE'):
        self.exchange_key = exchange_key
        self.config = EXCHANGES.get(exchange_key, EXCHANGES['NSE'])
    
    def format_symbol(self, symbol: str) -> str:
        """Add exchange suffix to symbol"""
        return self.config.format_ticker(symbol.upper())
    
    def fetch_stock_data(self, symbol: str, period: str = '1y') -> pd.DataFrame:
        """
        Fetch historical stock data from Yahoo Finance.
        
        Args:
            symbol: Stock symbol (without exchange suffix)
            period: Data period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            formatted_symbol = self.format_symbol(symbol)
            ticker = yf.Ticker(formatted_symbol)
            
            # Fetch historical data
            df = ticker.history(period=period)
            
            if df.empty:
                logger.warning(f"No data found for {formatted_symbol}")
                return pd.DataFrame()
            
            # Standardize column names
            df = df.reset_index()
            df.columns = [c.lower().replace(' ', '_') for c in df.columns]
            
            # Add metadata
            df['ticker'] = symbol.upper()
            df['exchange'] = self.exchange_key
            df['currency'] = self.config.currency
            
            # Rename 'date' if it's 'Name: Date' or similar
            if 'date' not in df.columns and df.columns[0] != 'date':
                df = df.rename(columns={df.columns[0]: 'date'})
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_live_price(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch current live price data.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dict with current price information
        """
        try:
            formatted_symbol = self.format_symbol(symbol)
            ticker = yf.Ticker(formatted_symbol)
            info = ticker.info
            
            return {
                'symbol': symbol.upper(),
                'exchange': self.exchange_key,
                'current_price': info.get('currentPrice') or info.get('regularMarketPrice', 0),
                'open': info.get('open') or info.get('regularMarketOpen', 0),
                'high': info.get('dayHigh') or info.get('regularMarketDayHigh', 0),
                'low': info.get('dayLow') or info.get('regularMarketDayLow', 0),
                'prev_close': info.get('previousClose') or info.get('regularMarketPreviousClose', 0),
                'volume': info.get('volume') or info.get('regularMarketVolume', 0),
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'currency': self.config.currency,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching live price for {symbol}: {e}")
            return {}
    
    def search_symbol(self, query: str) -> List[Dict[str, str]]:
        """
        Search for symbols matching query.
        Note: yfinance doesn't have native search, so this is limited.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching symbols
        """
        # This is a basic implementation - could be enhanced with external API
        formatted_query = self.format_symbol(query)
        
        try:
            ticker = yf.Ticker(formatted_query)
            info = ticker.info
            
            if info.get('symbol'):
                return [{
                    'symbol': query.upper(),
                    'name': info.get('longName', info.get('shortName', query)),
                    'exchange': self.exchange_key,
                    'type': info.get('quoteType', 'EQUITY')
                }]
            return []
            
        except Exception:
            return []
    
    def get_multiple_stocks(self, symbols: List[str], period: str = '1y') -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple stocks.
        
        Args:
            symbols: List of stock symbols
            period: Data period
            
        Returns:
            Dict mapping symbol to DataFrame
        """
        result = {}
        for symbol in symbols:
            df = self.fetch_stock_data(symbol, period)
            if not df.empty:
                result[symbol.upper()] = df
        return result


class ExchangeManager:
    """
    Unified manager for multi-exchange support.
    Handles data fetching across different exchanges.
    """
    
    def __init__(self, default_exchange: str = 'NSE'):
        self.default_exchange = default_exchange
        self.providers: Dict[str, ExchangeDataProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize data providers for all supported exchanges"""
        for exchange_key in EXCHANGES.keys():
            self.providers[exchange_key] = YFinanceProvider(exchange_key)
    
    def get_provider(self, exchange: str = None) -> ExchangeDataProvider:
        """Get the data provider for an exchange"""
        exchange = exchange or self.default_exchange
        return self.providers.get(exchange.upper(), self.providers[self.default_exchange])
    
    def fetch_data(self, symbol: str, exchange: str = None, period: str = '1y') -> pd.DataFrame:
        """
        Fetch stock data from the specified exchange.
        
        Args:
            symbol: Stock symbol
            exchange: Exchange key (NSE, BSE, NYSE, etc.)
            period: Data period
            
        Returns:
            DataFrame with stock data
        """
        provider = self.get_provider(exchange)
        return provider.fetch_stock_data(symbol, period)
    
    def fetch_live(self, symbol: str, exchange: str = None) -> Dict[str, Any]:
        """Fetch live price from the specified exchange"""
        provider = self.get_provider(exchange)
        return provider.fetch_live_price(symbol)
    
    def search(self, query: str, exchange: str = None) -> List[Dict[str, str]]:
        """Search for symbols on the specified exchange"""
        provider = self.get_provider(exchange)
        return provider.search_symbol(query)
    
    def get_supported_exchanges(self) -> List[Dict[str, Any]]:
        """Get list of supported exchanges with their details"""
        return [
            {
                'key': key,
                'name': config.name,
                'currency': config.currency,
                'timezone': config.timezone,
                'trading_hours': config.trading_hours
            }
            for key, config in EXCHANGES.items()
        ]
    
    def set_default_exchange(self, exchange: str):
        """Set the default exchange"""
        if exchange.upper() in EXCHANGES:
            self.default_exchange = exchange.upper()
            return True
        return False


# Global instance
_exchange_manager: Optional[ExchangeManager] = None


def get_exchange_manager(default_exchange: str = 'NSE') -> ExchangeManager:
    """Get or create the global exchange manager instance"""
    global _exchange_manager
    if _exchange_manager is None:
        _exchange_manager = ExchangeManager(default_exchange)
    return _exchange_manager


if __name__ == "__main__":
    # Test the exchange manager
    manager = get_exchange_manager()
    
    print("Supported Exchanges:")
    for ex in manager.get_supported_exchanges():
        print(f"  {ex['key']}: {ex['name']} ({ex['currency']})")
    
    print("\nFetching NSE data for RELIANCE...")
    df = manager.fetch_data('RELIANCE', 'NSE', '1mo')
    if not df.empty:
        print(f"  Got {len(df)} rows")
        print(df.tail())
    
    print("\nFetching live price for TCS...")
    live = manager.fetch_live('TCS', 'NSE')
    if live:
        print(f"  Current Price: {live.get('current_price')}")
