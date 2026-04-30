# GenAI Stock Market Intelligence - Frontend

Modern React frontend for the AI-powered stock market analysis platform.

## Features

- **Dashboard**: Real-time stock overview with search and watchlist
- **Stock Screener**: 6 strategies (Momentum, Piotroski, Swing, Breakout, Value, Custom)
- **AI Predictions**: ML-powered 5-day price forecasts with trade suggestions
- **Backtesting**: Historical strategy performance with equity curves
- **Portfolio**: Personal watchlist management
- **Settings**: Screener configuration and cache management

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Lucide React** - Icons
- **Custom CSS** - Glassmorphism design system

## Project Structure

```
src/
├── components/
│   ├── ui/           # Reusable UI components
│   └── charts/       # Chart components
├── services/         # API service layer
├── styles/           # CSS design system
├── App.jsx           # Main application
└── main.jsx          # Entry point
```

## Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:5000/api
```

## API Proxy

Development server proxies `/api` requests to the backend at `localhost:5000`.

## Design

- Dark theme with glassmorphism effects
- Gradient backgrounds and animations
- Responsive design for all screen sizes
- Inter font family

## License

MIT License
