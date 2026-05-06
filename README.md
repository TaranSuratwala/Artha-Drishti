# Artha-Drishti

GenAI Stock Market Intelligence System. A full-stack platform for stock screening, prediction, and backtesting with an interactive React dashboard and a Flask API backend.

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![React](https://img.shields.io/badge/react-18-61dafb)
![Vite](https://img.shields.io/badge/vite-4.x-646cff)
![License](https://img.shields.io/badge/license-MIT-green)

## Demo (Local)

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

## Highlights

- Multi-strategy screener (Momentum, Piotroski, Swing, Breakout, Value, Custom)
- LSTM + Attention price predictions with batch and per-ticker endpoints
- Backtesting engine with historical performance metrics
- Portfolio watchlist and dashboard views
- Scheduler-driven data pipeline (PostgreSQL + TimescaleDB)

## Architecture

- Frontend: React 18 + Vite SPA
- Backend: Flask API (Python 3.9+)
- Database: PostgreSQL 14+ with TimescaleDB extension
- ML: PyTorch-based models (pretrained artifacts included)
- Optional: Redis for caching

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python application.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

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
