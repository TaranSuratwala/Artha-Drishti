from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from IntegratedPostGreSQL import NSEDataPipeline, DB_URL
from MLPredictor import ProductionStockPredictor
from StockScreener import AdvancedStockScreener, ScreenerConfig, BacktestEngine
import decimal
import datetime
import logging
import os
from functools import wraps
import time
from collections import defaultdict
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize components with production config
pipeline = NSEDataPipeline(DB_URL)

screener_config = ScreenerConfig(
    max_workers=15,
    cache_ttl_seconds=1800,
    timeout_seconds=45,
    enable_caching=True,
    min_data_points=50
)

screener = AdvancedStockScreener(pipeline, screener_config)
backtest_engine = BacktestEngine(pipeline, screener_config)
predictor = ProductionStockPredictor(DB_URL)

# Rate limiting
request_counts = defaultdict(list)
RATE_LIMIT = 100  # requests per minute
RATE_WINDOW = 60  # seconds

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        now = time.time()
        
        # Clean old requests
        request_counts[client_ip] = [
            req_time for req_time in request_counts[client_ip]
            if now - req_time < RATE_WINDOW
        ]
        
        # Check rate limit
        if len(request_counts[client_ip]) >= RATE_LIMIT:
            return jsonify({
                "error": "Rate limit exceeded",
                "retry_after": RATE_WINDOW
            }), 429
        
        request_counts[client_ip].append(now)
        return f(*args, **kwargs)
    return decorated_function

def clean_row(row):
    """Convert database row to JSON-serializable format"""
    cleaned = {}
    for key, value in row.items():
        if isinstance(value, decimal.Decimal):
            cleaned[key] = float(value)
        elif isinstance(value, (datetime.date, datetime.datetime)):
            cleaned[key] = value.isoformat()
        else:
            cleaned[key] = value
    return cleaned

# ==================== STOCK DATA ENDPOINTS ====================

@app.route('/api/stocks', methods=['GET'])
@rate_limit
def fetch_stocks():
    """Fetch all stocks latest data"""
    try:
        limit = request.args.get('limit', type=int)
        raw_data = pipeline.get_latest_data(limit=limit)
        clean_data = [clean_row(row) for row in raw_data]
        return jsonify({
            "status": "success",
            "count": len(clean_data),
            "data": clean_data
        })
    except Exception as e:
        logger.error(f"Error fetching stocks: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/history/<ticker>', methods=['GET'])
@rate_limit
def fetch_history(ticker):
    """Fetch historical data for a specific ticker"""
    try:
        period = request.args.get('period', 'all')  # all, 1y, 6m, 3m, 1m
        raw_data = pipeline.get_ticker_history(ticker)
        clean_data = [clean_row(row) for row in raw_data]
        
        # Filter by period if specified
        if period != 'all' and clean_data:
            days_map = {'1m': 30, '3m': 90, '6m': 180, '1y': 365}
            days = days_map.get(period, 365)
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            clean_data = [
                d for d in clean_data 
                if datetime.datetime.fromisoformat(d['date'].replace('Z', '+00:00')) >= cutoff_date
            ]
        
        return jsonify({
            "status": "success",
            "ticker": ticker,
            "count": len(clean_data),
            "data": clean_data
        })
    except Exception as e:
        logger.error(f"Error fetching history for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== ENHANCED SCREENING ENDPOINTS ====================

@app.route('/api/screen/<strategy>', methods=['POST'])
@rate_limit
def screen_stocks(strategy):
    """
    Enhanced screening endpoint with all strategies
    
    Strategies: piotroski, momentum, swing, breakout, value, custom, multi
    """
    try:
        data = request.get_json() or {}
        
        # Extract parameters
        params = {
            'rank': data.get('rank', True),
            'export_file': data.get('export_file'),
            'export_format': data.get('export_format', 'csv')
        }
        
        # Strategy-specific parameters
        if strategy == 'piotroski':
            params['min_score'] = data.get('min_score', 7)
            params['max_workers'] = data.get('max_workers')
            
        elif strategy == 'momentum':
            params['lookback_days'] = data.get('lookback_days', 20)
            params['min_return'] = data.get('min_return', 5.0)
            params['min_rsi'] = data.get('min_rsi', 30)
            params['max_rsi'] = data.get('max_rsi', 70)
            
        elif strategy == 'swing':
            params['rsi_range'] = tuple(data.get('rsi_range', [30, 70]))
            
        elif strategy == 'breakout':
            params['volume_threshold'] = data.get('volume_threshold', 1.5)
            params['lookback_period'] = data.get('lookback_period', 252)
            
        elif strategy == 'value':
            params['min_value_score'] = data.get('min_value_score', 3)
            
        elif strategy == 'custom':
            params['conditions'] = data.get('conditions', {})
            
        elif strategy == 'multi':
            params['strategies'] = data.get('strategies', [])
            params['min_overlap'] = data.get('min_overlap', 2)
        
        logger.info(f"Running {strategy} scan with params: {params}")
        
        results = screener.run_screener(strategy, **params)
        
        return jsonify({
            "status": "success",
            "strategy": strategy,
            "count": len(results),
            "results": results.to_dict(orient='records') if not results.empty else []
        })
        
    except Exception as e:
        logger.error(f"{strategy} screening error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== BACKTESTING ENDPOINTS ====================

@app.route('/api/backtest/<strategy>', methods=['POST'])
@rate_limit
def backtest_strategy(strategy):
    """
    Backtest a screening strategy
    
    Body params:
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - rebalance_frequency: daily, weekly, monthly
    - initial_capital: Starting capital
    - max_positions: Maximum number of positions
    - strategy_params: Strategy-specific parameters
    """
    try:
        data = request.get_json() or {}
        
        start_date = data.get('start_date', '2023-01-01')
        end_date = data.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
        rebalance_frequency = data.get('rebalance_frequency', 'monthly')
        initial_capital = data.get('initial_capital', 100000)
        max_positions = data.get('max_positions', 20)
        strategy_params = data.get('strategy_params', {})
        
        logger.info(f"Backtesting {strategy} from {start_date} to {end_date}")
        
        results = backtest_engine.backtest_strategy(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            rebalance_frequency=rebalance_frequency,
            initial_capital=initial_capital,
            max_positions=max_positions,
            **strategy_params
        )
        
        return jsonify({
            "status": "success",
            **results
        })
        
    except Exception as e:
        logger.error(f"Backtest error for {strategy}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/backtest/compare', methods=['POST'])
@rate_limit
def compare_strategies():
    """
    Compare multiple strategies via backtesting
    
    Body params:
    - strategies: List of {name, params} dicts
    - start_date, end_date, rebalance_frequency, etc.
    """
    try:
        data = request.get_json() or {}
        
        strategies = data.get('strategies', [])
        start_date = data.get('start_date', '2023-01-01')
        end_date = data.get('end_date', datetime.datetime.now().strftime('%Y-%m-%d'))
        
        common_params = {
            'rebalance_frequency': data.get('rebalance_frequency', 'monthly'),
            'initial_capital': data.get('initial_capital', 100000),
            'max_positions': data.get('max_positions', 20)
        }
        
        logger.info(f"Comparing {len(strategies)} strategies")
        
        comparison = backtest_engine.compare_strategies(
            strategies=strategies,
            start_date=start_date,
            end_date=end_date,
            **common_params
        )
        
        return jsonify({
            "status": "success",
            "comparison": comparison.to_dict(orient='records')
        })
        
    except Exception as e:
        logger.error(f"Strategy comparison error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== PREDICTION ENDPOINTS ====================

@app.route('/api/predict/<ticker>', methods=['POST'])
@rate_limit
def predict_stock(ticker):
    """Generate AI prediction for a stock"""
    try:
        data = request.get_json() or {}
        capital = data.get('capital', 100000)
        risk_pct = data.get('risk_pct', 2.0)
        monte_carlo_samples = data.get('monte_carlo_samples', 30)
        
        logger.info(f"Predicting {ticker}: capital={capital}, risk={risk_pct}")
        
        result = predictor.predict(
            ticker=ticker,
            capital=capital,
            risk_pct=risk_pct,
            monte_carlo_samples=monte_carlo_samples
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Prediction error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/train/<ticker>', methods=['POST'])
@rate_limit
def train_model(ticker):
    """Train or update model for a specific ticker"""
    try:
        data = request.get_json() or {}
        force_retrain = data.get('force_retrain', False)
        model_type = data.get('model_type', 'ensemble')
        epochs = data.get('epochs', 150)
        learning_rate = data.get('learning_rate', 0.001)
        
        logger.info(f"Training {ticker}: model={model_type}, epochs={epochs}")
        
        result = predictor.train(
            ticker=ticker,
            force_retrain=force_retrain,
            model_type=model_type,
            epochs=epochs,
            learning_rate=learning_rate
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Training error for {ticker}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/batch_train', methods=['POST'])
@rate_limit
def batch_train():
    """Train models for multiple tickers"""
    try:
        data = request.get_json() or {}
        tickers = data.get('tickers', [])
        model_type = data.get('model_type', 'ensemble')
        epochs = data.get('epochs', 100)
        max_stocks = data.get('max_stocks')
        
        if not tickers and max_stocks:
            # Train NIFTY 500
            logger.info(f"Batch training {max_stocks} stocks")
            results = predictor.batch_train_nifty500(
                model_type=model_type,
                max_stocks=max_stocks,
                epochs=epochs
            )
        else:
            # Train specific tickers
            results = {
                "success": [],
                "failed": [],
                "metrics_summary": []
            }
            
            for ticker in tickers:
                try:
                    result = predictor.train(
                        ticker=ticker,
                        model_type=model_type,
                        epochs=epochs
                    )
                    
                    if result['status'] == 'success':
                        results['success'].append(ticker)
                        results['metrics_summary'].append({
                            'ticker': ticker,
                            'rmse': result.get('rmse', 0),
                            'r2_score': result.get('r2_score', 0)
                        })
                    else:
                        results['failed'].append(ticker)
                        
                except Exception as e:
                    logger.error(f"Failed {ticker}: {e}")
                    results['failed'].append(ticker)
        
        return jsonify({
            "status": "success",
            "total": len(results['success']) + len(results['failed']),
            **results
        })
        
    except Exception as e:
        logger.error(f"Batch training error: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== UTILITY ENDPOINTS ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        stocks = pipeline.get_latest_data(limit=1)
        db_status = "connected" if stocks else "no_data"
        
        return jsonify({
            "status": "healthy",
            "database": db_status,
            "components": {
                "pipeline": "active",
                "screener": "active",
                "predictor": "active",
                "backtest_engine": "active"
            },
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/api/stats', methods=['GET'])
@rate_limit
def get_stats():
    """Get database and system statistics"""
    try:
        stocks = pipeline.get_latest_data(limit=None)
        
        # Screener stats
        screener_stats = screener.get_performance_stats()
        
        return jsonify({
            "database": {
                "total_stocks": len(stocks),
                "status": "operational"
            },
            "screener": screener_stats,
            "timestamp": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear screener cache"""
    try:
        screener.clear_cache()
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

# ==================== CONFIGURATION ENDPOINTS ====================

@app.route('/api/config/screener', methods=['GET', 'POST'])
def screener_configuration():
    """Get or update screener configuration"""
    if request.method == 'GET':
        return jsonify({
            "max_workers": screener_config.max_workers,
            "cache_ttl_seconds": screener_config.cache_ttl_seconds,
            "timeout_seconds": screener_config.timeout_seconds,
            "enable_caching": screener_config.enable_caching,
            "min_data_points": screener_config.min_data_points
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json() or {}
            
            # Update configuration
            if 'max_workers' in data:
                screener_config.max_workers = data['max_workers']
            if 'cache_ttl_seconds' in data:
                screener_config.cache_ttl_seconds = data['cache_ttl_seconds']
            if 'enable_caching' in data:
                screener_config.enable_caching = data['enable_caching']
            
            return jsonify({
                "status": "success",
                "message": "Configuration updated"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded", "message": str(e)}), 429

# ==================== MAIN ====================

if __name__ == '__main__':
    logger.info("🚀 Starting Production GenAI Stock Market System")
    logger.info("📊 Screening strategies: Piotroski, Momentum, Swing, Breakout, Value, Custom, Multi")
    logger.info("🔄 Backtesting engine: Active")
    logger.info("🤖 AI Prediction: Production-grade with ensemble models")
    logger.info("⚡ Rate limiting: Enabled")
    logger.info("💾 Caching: Enabled")
    
    # Run with production settings
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,  # Set to False in production
        threaded=True
    )