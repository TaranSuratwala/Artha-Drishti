# GenAI Stock Market Intelligence System

A complete, production-ready AI-powered stock market analysis platform with multi-strategy screening, LSTM-based predictions, and backtesting capabilities.

## Project Structure

```
Project sem-6/
├── backend/                    # Python Flask API
│   ├── application.py          # Main API server
│   ├── IntegratedPostGreSQL.py # NSE data pipeline
│   ├── MLPredictor.py          # AI prediction engine
│   ├── StockScreener.py        # Multi-strategy screener
│   ├── FeatureEngineering.py   # Technical indicators
│   ├── Backtesting.py          # Strategy backtesting
│   ├── config.py               # Configuration
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Container config
│   ├── docker-compose.yml      # Multi-service setup
│   └── README.md               # Backend docs
│
└── frontend/                   # React + Vite SPA
    ├── src/
    │   ├── components/         # UI & chart components
    │   ├── services/           # API service layer
    │   ├── styles/             # CSS design system
    │   └── App.jsx             # Main application
    ├── package.json            # NPM dependencies
    ├── vite.config.js          # Vite configuration
    └── README.md               # Frontend docs
```

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python application.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Features

- 📊 **Dashboard** - Real-time stock data with search
- 🔍 **Screener** - 6 screening strategies
- 🤖 **AI Predictions** - LSTM + Attention neural network
- 📈 **Backtesting** - Historical strategy analysis
- ⭐ **Watchlist** - Portfolio management
- ⚙️ **Settings** - Configuration panel

## License

MIT License
