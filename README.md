# Artha Drishti

Artha Drishti is a stock market intelligence platform that brings screening, prediction, and backtesting into a single workflow. It pairs a modern React dashboard with a Flask API to deliver data, models, and strategy evaluation in one place.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![React](https://img.shields.io/badge/react-18-61dafb)
![Vite](https://img.shields.io/badge/vite-4.x-646cff)
![License](https://img.shields.io/badge/license-MIT-green)

## Product Highlights

- Multi-strategy screener covering momentum, value, breakout, swing, and custom logic
- LSTM + attention price prediction endpoints for batch and per-ticker requests
- Backtesting engine with performance metrics and historical comparisons
- Portfolio watchlist and dashboard views for faster review cycles
- Scheduler-driven data pipeline with PostgreSQL and TimescaleDB

## System Overview

- Frontend: React 18 + Vite single-page application
- Backend: Flask API (Python 3.9+)
- Database: PostgreSQL 14+ with TimescaleDB extension
- ML: PyTorch models with pretrained artifacts
- Optional: Redis for caching

## Run Locally

1. Start the backend API:
   ```bash
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   python application.py
   ```
2. Start the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Open the app at http://localhost:5173

Optional check: `GET http://localhost:5000/api/health`

## Configuration

### Backend (.env)

Copy [backend/.env.example](backend/.env.example) to `backend/.env` and update values as needed.

Key variables:

- `DATABASE_URL`
- `CORS_ORIGINS`
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `SCHEDULER_ENABLED`

### Frontend (.env.local)

Copy [frontend/.env.example](frontend/.env.example) to `frontend/.env.local` and set:

- `VITE_API_BASE_URL` (leave empty for same-origin proxy)

## API Highlights

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/screen/momentum` | POST | Momentum screening |
| `/api/screen/piotroski` | POST | Piotroski screening |
| `/api/predict/<ticker>` | POST | Price prediction |
| `/api/train/<ticker>` | POST | Train/update model |
| `/api/backtest/<strategy>` | POST | Strategy backtest |

## Project Structure

```
Project sem-6/
├── backend/                    # Flask API
│   ├── application.py          # Main server
│   ├── IntegratedPostGreSQL.py # NSE data pipeline
│   ├── MLPredictor.py          # AI prediction engine
│   ├── StockScreener.py        # Multi-strategy screener
│   ├── FeatureEngineering.py   # Indicators
│   ├── Backtesting.py          # Strategy backtesting
│   ├── config.py               # Configuration
│   ├── requirements.txt        # Python dependencies
│   └── README.md               # Backend docs
│
└── frontend/                   # React + Vite SPA
    ├── src/
    │   ├── components/         # UI and chart components
    │   ├── services/           # API service layer
    │   ├── styles/             # Design system
    │   └── App.jsx             # Main application
    ├── package.json            # Frontend dependencies
    ├── vite.config.js          # Vite configuration
    └── README.md               # Frontend docs
```

## Documentation

- Backend details: [backend/README.md](backend/README.md)
- Frontend details: [frontend/README.md](frontend/README.md)

## License

MIT License
