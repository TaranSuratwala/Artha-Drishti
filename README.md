# Artha Drishti

Artha Drishti is a stock market intelligence platform that brings screening, prediction, and backtesting into a single workflow. It pairs a modern React dashboard with a Flask API to deliver data, models, and strategy evaluation in one place.
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=0:0f172a,100:0b1b2b&height=120&section=header&text=Artha-Drishti&fontSize=36&fontColor=F8FAFC&fontAlignY=60" alt="Artha-Drishti banner" />
</p>

<p align="center">
  <img src="https://img.shields.io/github/last-commit/TaranSuratwala/Artha-Drishti?style=flat-square" alt="Last commit" />
  <img src="https://img.shields.io/github/languages/top/TaranSuratwala/Artha-Drishti?style=flat-square" alt="Top language" />
  <img src="https://img.shields.io/github/repo-size/TaranSuratwala/Artha-Drishti?style=flat-square" alt="Repo size" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python" />
  <img src="https://img.shields.io/badge/react-18-61dafb" alt="React" />
  <img src="https://img.shields.io/badge/vite-4.x-646cff" alt="Vite" />
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License" />
</p>

# Artha-Drishti

Artha-Drishti is a stock market intelligence platform that brings screening, prediction, and backtesting into a single workflow. It pairs a React dashboard with a Flask API to deliver data, models, and strategy evaluation in one place.

## Product Highlights

- Multi-strategy stock screening covering momentum, Piotroski, swing, breakout, value, and custom logic
- LSTM + attention predictions with batch and per-ticker endpoints
- Historical backtesting with performance metrics and strategy comparison
- Scheduler-driven data pipeline with PostgreSQL and TimescaleDB, with optional Redis caching
- Portfolio watchlists, charts, and summary dashboards for faster review

## System Overview

- Frontend: React 18 + Vite single-page application
- Backend: Flask API, scheduler, ML pipeline, and screener engine
- Data: PostgreSQL 14+ with TimescaleDB extension; optional Redis cache
- ML: PyTorch models with pretrained artifacts

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
- `APP_HOST`, `APP_PORT`, `APP_ENV`, `APP_DEBUG`, `APP_USE_RELOADER`, `APP_THREADED`
- `SECRET_KEY`, `JWT_SECRET_KEY`
- `NEWSAPI_KEY`, `FINNHUB_KEY`, `ALPHAVANTAGE_KEY` (optional)
- `SCHEDULER_ENABLED`, `SCHEDULER_HOUR`, `SCHEDULER_MINUTE`, `SCHEDULER_AUTO_START`
- `SCHEDULER_AUTO_CATCHUP`, `SCHEDULER_AUTO_TRAIN`, `SCHEDULER_IN_WEB_WORKER`

### Frontend (.env.local)

Copy [frontend/.env.example](frontend/.env.example) to `frontend/.env.local` and set:

- `VITE_GOOGLE_CLIENT_ID`
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
