# Artha-Drishti

Artha-Drishti is a full-stack stock market intelligence platform that combines multi-strategy screening, ML price predictions, and backtesting in a single workflow.

## Highlights

- Multi-strategy stock screening (momentum, piotroski, swing, breakout, value, custom)
- LSTM + attention predictions with batch price target endpoints
- Historical backtesting and strategy comparison
- PostgreSQL + TimescaleDB data pipeline with optional Redis cache
- React dashboard for watchlists, charts, and strategy results

## Architecture

- Backend: Flask API, scheduler, ML pipeline, and screener engine
- Frontend: React + Vite SPA with dashboard and charting
- Data: PostgreSQL/TimescaleDB, optional Redis

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

Backend `.env` keys (see `backend/.env.example`):

- DATABASE_URL
- CORS_ORIGINS
- APP_HOST, APP_PORT, APP_ENV, APP_DEBUG, APP_USE_RELOADER, APP_THREADED
- SECRET_KEY, JWT_SECRET_KEY
- NEWSAPI_KEY, FINNHUB_KEY, ALPHAVANTAGE_KEY (optional)
- SCHEDULER_ENABLED, SCHEDULER_HOUR, SCHEDULER_MINUTE, SCHEDULER_AUTO_START
- SCHEDULER_AUTO_CATCHUP, SCHEDULER_AUTO_TRAIN, SCHEDULER_IN_WEB_WORKER

Frontend `.env` keys (see `frontend/.env.example`):

- VITE_GOOGLE_CLIENT_ID
- VITE_API_BASE_URL

## Project Structure

```
backend/   Flask API, data pipeline, ML prediction, backtesting
frontend/  React SPA dashboard
```

## Docs

- Backend docs: `backend/README.md`
- Frontend docs: `frontend/README.md`

## License

MIT License
