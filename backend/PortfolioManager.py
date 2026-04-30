import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PortfolioManager:
    """
    Manages user portfolio, transactions, and holdings calculations.
    Persists data to user-specific JSON files.
    """
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        # Ensure data directory exists
        os.makedirs(os.path.abspath(data_dir), exist_ok=True)

    def _get_user_file(self, user_id):
        """Get file path for specific user"""
        return os.path.join(self.data_dir, f"portfolio_{user_id}.json")

    def _load_data(self, user_id):
        """Load portfolio data for user from JSON file"""
        file_path = self._get_user_file(user_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                # Ensure structure
                if 'transactions' not in data:
                    data['transactions'] = []
                if 'holdings' not in data:
                    data['holdings'] = {}
                return data
                    
            except Exception as e:
                logger.error(f"Error loading portfolio data for user {user_id}: {e}")
                return {'transactions': [], 'holdings': {}}
        else:
            # Return empty structure (will be saved on first write)
            return {'transactions': [], 'holdings': {}}

    def _save_data(self, user_id, data):
        """Save portfolio data to user-specific JSON file"""
        file_path = self._get_user_file(user_id)
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving portfolio data for user {user_id}: {e}")

    def add_transaction(self, user_id, ticker, type, quantity, price, date=None):
        """Add a buy/sell transaction and update holdings"""
        data = self._load_data(user_id)
        
        if not date:
            date = datetime.now().isoformat()
        
        transaction = {
            'id': str(int(datetime.now().timestamp() * 1000)), # Simple unique ID
            'ticker': ticker.upper(),
            'type': type.upper(), # 'BUY' or 'SELL'
            'quantity': float(quantity),
            'price': float(price),
            'date': date
        }
        
        data['transactions'].append(transaction)
        self._recalculate_holdings(data)
        self._save_data(user_id, data)
        
        return transaction

    def delete_transaction(self, user_id, transaction_id):
        """Delete a transaction by ID"""
        data = self._load_data(user_id)
        initial_len = len(data['transactions'])
        
        data['transactions'] = [t for t in data['transactions'] if t['id'] != str(transaction_id)]
        
        if len(data['transactions']) < initial_len:
            self._recalculate_holdings(data)
            self._save_data(user_id, data)
            return True
        return False

    def reset_portfolio(self, user_id):
        """Clear all transactions and holdings"""
        data = {'transactions': [], 'holdings': {}}
        self._save_data(user_id, data)

    def _recalculate_holdings(self, data):
        """Recalculate current holdings based on all transactions"""
        holdings = {}
        
        for t in data['transactions']:
            ticker = t['ticker']
            qty = t['quantity']
            price = t['price']
            
            if ticker not in holdings:
                holdings[ticker] = {'quantity': 0.0, 'total_cost': 0.0, 'avg_price': 0.0}
            
            current = holdings[ticker]
            
            if t['type'] == 'BUY':
                current['quantity'] += qty
                current['total_cost'] += qty * price
            elif t['type'] == 'SELL':
                if current['quantity'] > 0:
                    # Reduce cost basis proportionally
                    cost_per_share = current['total_cost'] / current['quantity']
                    current['total_cost'] -= qty * cost_per_share
                    current['quantity'] -= qty
                
            # Update average price
            if current['quantity'] > 0:
                current['avg_price'] = current['total_cost'] / current['quantity']
            else:
                current['avg_price'] = 0.0
                current['total_cost'] = 0.0
        
        # Filter out closed positions (near zero)
        data['holdings'] = {
            k: {
                'ticker': k,
                'quantity': round(float(v['quantity']), 4),
                'avg_price': round(float(v['avg_price']), 2),
                'total_cost': round(float(v['total_cost']), 2)
            }
            for k, v in holdings.items() 
            if v['quantity'] > 0.0001
        }

    def get_portfolio_summary(self, user_id, current_prices=None):
        """
        Get portfolio summary with calculated P&L using current prices.
        current_prices: Dict[ticker, price]
        """
        data = self._load_data(user_id)
        holdings_list = []
        total_value = 0.0
        total_cost = 0.0
        
        for ticker, holding in data['holdings'].items():
            current_price = 0.0
            if current_prices and ticker in current_prices:
                current_price = current_prices[ticker]
            
            market_value = holding['quantity'] * current_price
            cost_basis = holding['total_cost']
            unrealized_pnl = market_value - cost_basis
            pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            holdings_list.append({
                **holding,
                'current_price': current_price,
                'market_value': round(market_value, 2),
                'unrealized_pnl': round(unrealized_pnl, 2),
                'pnl_pct': round(pnl_pct, 2)
            })
            
            total_value += market_value
            total_cost += cost_basis
            
        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
        
        return {
            'holdings': holdings_list,
            'summary': {
                'total_value': round(total_value, 2),
                'total_cost': round(total_cost, 2),
                'total_pnl': round(total_pnl, 2),
                'total_pnl_pct': round(total_pnl_pct, 2),
                'portfolio_count': len(holdings_list)
            },
            'transactions': data['transactions']
        }
