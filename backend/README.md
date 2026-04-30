# GenAI Stock Market Intelligence System - Backend

An AI-powered stock market analysis platform with multi-strategy screening, LSTM-based predictions, and backtesting capabilities.

## Features

- **Stock Data Pipeline**: Automated NSE data fetching with PostgreSQL/TimescaleDB storage
- **AI Predictions**: LSTM + Attention neural network for 5-day price forecasting
- **Multi-Strategy Screener**: Piotroski, Momentum, Swing, Breakout, Value, Custom
- **Backtesting Engine**: Historical strategy performance analysis
- **Feature Engineering**: 50+ technical indicators

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 14+ with TimescaleDB extension
- Redis (optional, for caching)

### Installation

```bash
# Clone and navigate
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your database credentials

# Run the server
python application.py

# Notes:
# - Existing trained model artifacts are loaded at startup when available.
# - Scheduler auto-train is OFF by default (set SCHEDULER_AUTO_TRAIN=true to enable).
```

### Docker Deployment

```bash
# Build and run all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

## Production Deployment Notes

- The Flask app now starts in production-safe mode by default (`APP_DEBUG=false`, no reloader).
- Startup catch-up is disabled by default (`SCHEDULER_AUTO_CATCHUP=false`) to avoid heavy boot-time jobs.
- Model auto-training is disabled by default (`SCHEDULER_AUTO_TRAIN=false`) so the API reuses existing trained artifacts.
- In multi-worker Gunicorn deployments, in-process scheduler startup is blocked by default (`SCHEDULER_IN_WEB_WORKER=false`) to prevent duplicate jobs.
- To retrain manually, call `POST /api/train/<ticker>`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/stocks` | GET | Get all stocks latest data |
| `/api/history/<ticker>` | GET | Get ticker history |
| `/api/screen/momentum` | POST | Momentum screening |
| `/api/screen/piotroski` | POST | Piotroski F-Score screening |
| `/api/screen/swing` | GET | Swing trading screening |
| `/api/screen/breakout` | POST | Breakout screening |
| `/api/screen/value` | GET | Value investing screening |
| `/api/screen/custom` | POST | Custom conditions screening |
| `/api/predict/<ticker>` | POST | AI stock prediction |
| `/api/train/<ticker>` | POST | Train/update model |
| `/api/backtest/<strategy>` | POST | Backtest strategy |
| `/api/watchlist` | GET/POST/DELETE | Manage watchlist |

## Project Structure

```
backend/
├── application.py          # Main Flask API server
├── IntegratedPostGreSQL.py # NSE data pipeline
├── MLPredictor.py          # AI prediction engine
├── StockScreener.py        # Multi-strategy screener
├── FeatureEngineering.py   # Technical indicators
├── Backtesting.py          # Strategy backtesting
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container configuration
├── docker-compose.yml      # Multi-service orchestration
└── .env.example            # Environment template
```

## Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost:5432/StockDB
FLASK_ENV=development
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=5000
APP_DEBUG=false
APP_USE_RELOADER=false
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
REDIS_URL=redis://localhost:6379/0
SCHEDULER_ENABLED=true
SCHEDULER_AUTO_CATCHUP=false
SCHEDULER_AUTO_TRAIN=false
SCHEDULER_IN_WEB_WORKER=false
```

## License

MIT License
