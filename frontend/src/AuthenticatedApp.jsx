import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
    Search, TrendingUp, Filter, Brain, BarChart2, Target, AlertTriangle,
    Sparkles, Activity, DollarSign, Settings, Briefcase, ChevronRight,
    RefreshCw, Clock, ArrowUpRight, ArrowDownRight, X, Play, Layers,
    PieChart, Star, StarOff, Trash2, Download, Plus, LogOut, WifiOff,
    ChevronLeft, ChevronsLeft, ChevronsRight, User, Shield, Gauge, FileText,
    ArrowLeft, TrendingDown, Crosshair, Award
} from 'lucide-react';
import { useAuth } from './context/AuthContext';

// Components
import { Card, Button, StatCard, LoadingSpinner, Toast, ThemeToggle, SkeletonLoader } from './components/ui';
import { PriceChart, StrategyComparison } from './components/charts';
import { MultiStrategyPanel, StrategyBuilder } from './components/screener';
import { MarketOverview, TopMovers, PriceTargetsDashboard, StockRecommendations } from './components/dashboard';
import { WatchlistSearch, PortfolioDashboard } from './components/portfolio';

// API Services
import * as api from './services/api';

// Custom hooks
import { useDebounce, useOnlineStatus, useDocumentTitle, useKeyboardShortcut } from './hooks';

// Strategy configurations
// Initial Predefined Strategies
const INITIAL_STRATEGIES = [
    { id: 'momentum', name: 'Momentum', icon: TrendingUp, color: 'blue' },
    { id: 'piotroski', name: 'Piotroski', icon: BarChart2, color: 'purple' },
    { id: 'swing', name: 'Swing', icon: Activity, color: 'green' },
    { id: 'breakout', name: 'Breakout', icon: Sparkles, color: 'yellow' },
    { id: 'value', name: 'Value', icon: DollarSign, color: 'emerald' },
    { id: 'garp', name: 'GARP', icon: TrendingUp, color: 'indigo' },
    { id: 'mean_reversion', name: 'Mean Reversion', icon: ArrowDownRight, color: 'orange' },
    { id: 'quality_dividend', name: 'Dividend Quality', icon: DollarSign, color: 'cyan' },
    { id: 'trend_following', name: 'Trend Following', icon: TrendingUp, color: 'teal' },
    { id: 'contrarian', name: 'Contrarian', icon: ArrowDownRight, color: 'red' },
    { id: 'quality_growth', name: 'Quality Growth', icon: Star, color: 'violet' }
];

const TABS = [
    { id: 'dashboard', name: 'Dashboard', icon: BarChart2 },
    { id: 'screener', name: 'Screener', icon: Filter },
    { id: 'backtest', name: 'Backtest', icon: Clock },
    { id: 'portfolio', name: 'Portfolio', icon: Briefcase },
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'settings', name: 'Settings', icon: Settings }
];

export default function AuthenticatedApp({ theme, toggleTheme }) {
    // Auth hook
    const { user, logout } = useAuth();

    // Network status – Nielsen #1: Visibility of system status
    const isOnline = useOnlineStatus();

    // Core state
    const [activeTab, setActiveTab] = useState('dashboard');

    const [stocks, setStocks] = useState([]);
    const [strategies, setStrategies] = useState(INITIAL_STRATEGIES);
    const [showStrategyBuilder, setShowStrategyBuilder] = useState(false);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedTicker, setSelectedTicker] = useState(null);
    const [chartData, setChartData] = useState([]);
    const [chartPeriod, setChartPeriod] = useState('1y');
    const [health, setHealth] = useState(null);
    const [stats, setStats] = useState(null);

    // Pagination state – Nielsen #7: Flexibility
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 25;
    const [toast, setToast] = useState(null);

    // Screener state
    const [screenStrategy, setScreenStrategy] = useState('momentum');
    const [screenResults, setScreenResults] = useState([]);
    const [screening, setScreening] = useState(false);
    const [customConditions, setCustomConditions] = useState({
        price_min: '', price_max: '', rsi_min: '', rsi_max: '', volume_ratio: ''
    });
    const [screenerMode, setScreenerMode] = useState('single'); // 'single' or 'multi'
    const [screenElapsed, setScreenElapsed] = useState(0);   // elapsed seconds during scan

    // Strategy-specific parameter configs
    const STRATEGY_PARAMS = {
        momentum: { lookback_days: 20, min_return: 5.0 },
        piotroski: { min_score: 7 },
        swing: { rsi_oversold: 30, rsi_overbought: 70, min_volume: 100000 },
        breakout: { volume_threshold: 1.5, lookback: 20 },
        value: { max_pe: 15, min_dividend_yield: 2.0 },
        garp: { max_peg_ratio: 1.5, min_earnings_growth: 10 },
        mean_reversion: { z_score_threshold: -2.0, lookback_days: 20 },
        quality_dividend: { min_dividend_yield: 2.0, min_payout_years: 5 },
        trend_following: { ema_short: 20, ema_long: 50, adx_threshold: 25 },
        contrarian: { rsi_threshold: 30, price_drop_pct: -10 },
        quality_growth: { min_roe: 15, min_revenue_growth: 10 }
    };
    const [strategyParams, setStrategyParams] = useState(STRATEGY_PARAMS);

    // Prediction state
    const [prediction, setPrediction] = useState(null);
    const [predicting, setPredicting] = useState(false);
    const [capital, setCapital] = useState(100000);
    const [riskPct, setRiskPct] = useState(2);
    const [training, setTraining] = useState(false);
    const [trainingMessage, setTrainingMessage] = useState(null);
    const [generatingReport, setGeneratingReport] = useState(false);

    // Backtest state
    const [backtestStrategy, setBacktestStrategy] = useState('momentum');
    const [backtestResults, setBacktestResults] = useState(null);
    const [backtesting, setBacktesting] = useState(false);
    const [backtestTicker, setBacktestTicker] = useState('RELIANCE');
    const [backtestTickerSearch, setBacktestTickerSearch] = useState('');
    const [backtestMultiMode, setBacktestMultiMode] = useState(false);
    const [backtestTickers, setBacktestTickers] = useState(['RELIANCE']);
    const [backtestTickerInput, setBacktestTickerInput] = useState('');
    const [multiBacktestResults, setMultiBacktestResults] = useState(null);
    const [backtestParams, setBacktestParams] = useState({
        start_date: '2023-01-01',
        end_date: new Date().toISOString().split('T')[0],
        initial_capital: 100000,
        max_positions: 20,
        rebalance_frequency: 'monthly'
    });
    const [comparisonMode, setComparisonMode] = useState(false);
    const [comparisonResults, setComparisonResults] = useState(null);
    const [comparing, setComparing] = useState(false);
    const [selectedCompareStrategies, setSelectedCompareStrategies] = useState(
        ['momentum', 'piotroski', 'swing', 'breakout', 'value']
    );
    // Multi-stock comparison
    const [compareTickers, setCompareTickers] = useState(['RELIANCE']);
    const [compareTickerInput, setCompareTickerInput] = useState('');
    const [activeCompareTicker, setActiveCompareTicker] = useState(null);
    const [multiCompareResults, setMultiCompareResults] = useState(null); // { ticker: result }
    const TICKER_PRESETS = {
        'NIFTY 50': [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK',
            'LT', 'BAJFINANCE', 'HCLTECH', 'AXISBANK', 'SUNPHARMA', 'TITAN', 'MARUTI', 'ASIANPAINT', 'WIPRO', 'ULTRACEMCO',
            'ONGC', 'NTPC', 'TATAMOTORS', 'JSWSTEEL', 'POWERGRID', 'M&M', 'ADANIENT', 'TATASTEEL', 'COALINDIA', 'HINDALCO',
            'BAJAJFINSV', 'SBILIFE', 'INDUSINDBK', 'GRASIM', 'DRREDDY', 'CIPLA', 'DIVISLAB', 'NESTLEIND', 'BRITANNIA', 'APOLLOHOSP',
            'HDFCLIFE', 'EICHERMOT', 'HEROMOTOCO', 'TATACONSUM', 'TECHM', 'BAJAJ-AUTO', 'BPCL', 'DABUR', 'ADANIPORTS', 'SHRIRAMFIN'
        ],
        'NIFTY Next 50': [
            'ADANIPOWER', 'AMBUJACEM', 'AUROPHARMA', 'BANDHANBNK', 'BANKBARODA', 'BERGEPAINT', 'BIOCON', 'BOSCHLTD',
            'CANBK', 'CHOLAFIN', 'COLPAL', 'CONCOR', 'DLF', 'FEDERALBNK', 'GAIL', 'GODREJCP', 'HAVELLS', 'HINDPETRO',
            'ICICIPRULI', 'IDFCFIRSTB', 'IGL', 'INDUSTOWER', 'IOC', 'IRCTC', 'JINDALSTEL', 'LUPIN', 'MARICO',
            'MCDOWELL-N', 'MUTHOOTFIN', 'NAUKRI', 'NMDC', 'OBEROIRLTY', 'OFSS', 'PEL', 'PETRONET', 'PIDILITIND',
            'PNB', 'SBICARD', 'SIEMENS', 'SRF', 'TATACOMM', 'TATAPOWER', 'TORNTPHARM', 'TRENT', 'TVSMOTOR',
            'UPL', 'VEDL', 'VOLTAS', 'YESBANK', 'ZOMATO'
        ],
        'SENSEX 30': [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK',
            'LT', 'BAJFINANCE', 'HCLTECH', 'AXISBANK', 'SUNPHARMA', 'TITAN', 'MARUTI', 'ASIANPAINT', 'WIPRO', 'ULTRACEMCO',
            'M&M', 'NTPC', 'TATAMOTORS', 'JSWSTEEL', 'POWERGRID', 'TATASTEEL', 'INDUSINDBK', 'BAJAJFINSV', 'NESTLEIND', 'TECHM'
        ],
        'Bank NIFTY': ['HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK', 'INDUSINDBK', 'BANKBARODA', 'PNB', 'FEDERALBNK', 'IDFCFIRSTB', 'CANBK', 'AUBANK'],
        'IT Stocks': ['TCS', 'INFY', 'WIPRO', 'HCLTECH', 'TECHM', 'LTIM', 'MPHASIS', 'COFORGE', 'PERSISTENT', 'OFSS'],
        'FMCG': ['HINDUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA', 'DABUR', 'MARICO', 'GODREJCP', 'COLPAL', 'TATACONSUM', 'EMAMILTD'],
        'Auto': ['TATAMOTORS', 'MARUTI', 'M&M', 'BAJAJ-AUTO', 'HEROMOTOCO', 'EICHERMOT', 'ASHOKLEY', 'TVSMOTOR', 'BHARATFORG', 'MRF'],
        'Pharma': ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB', 'AUROPHARMA', 'BIOCON', 'LUPIN', 'TORNTPHARM', 'ALKEM', 'ABBOTINDIA'],
        'Energy': ['RELIANCE', 'ONGC', 'NTPC', 'POWERGRID', 'ADANIGREEN', 'ADANIPOWER', 'TATAPOWER', 'COALINDIA', 'BPCL', 'IOC'],
        'Metal & Mining': ['TATASTEEL', 'HINDALCO', 'JSWSTEEL', 'VEDL', 'NATIONALUM', 'SAIL', 'COALINDIA', 'NMDC', 'JINDALSTEL', 'APLAPOLLO'],
        'Realty': ['DLF', 'OBEROIRLTY', 'GODREJPROP', 'PRESTIGE', 'BRIGADE', 'PHOENIXLTD', 'SOBHA', 'SUNTECK'],
        'Financial Services': ['BAJFINANCE', 'BAJAJFINSV', 'CHOLAFIN', 'MUTHOOTFIN', 'SBICARD', 'SBILIFE', 'HDFCLIFE', 'ICICIPRULI', 'SHRIRAMFIN', 'MANAPPURAM'],
    };

    // Portfolio state
    const [watchlist, setWatchlist] = useState([]);

    // Settings state
    const [config, setConfig] = useState(null);
    const [configLoading, setConfigLoading] = useState(false);
    const [savingConfig, setSavingConfig] = useState(false);

    // Modal analysis tabs & data
    const [modalTab, setModalTab] = useState('overview');
    const [fundamentals, setFundamentals] = useState(null);
    const [riskMetrics, setRiskMetrics] = useState(null);
    const [strategyEval, setStrategyEval] = useState(null);
    const [loadingFundamentals, setLoadingFundamentals] = useState(false);
    const [loadingRisk, setLoadingRisk] = useState(false);
    const [loadingStrategies, setLoadingStrategies] = useState(false);
    const [fundamentalsError, setFundamentalsError] = useState('');
    const [riskError, setRiskError] = useState('');
    const [strategiesError, setStrategiesError] = useState('');

    // Real-time quotes (yfinance, 10-15 min delayed)
    const [liveQuotes, setLiveQuotes] = useState({});        // { ticker: { price, change, change_pct, ... } }
    const [liveQuoteTime, setLiveQuoteTime] = useState(null); // last fetch timestamp
    const [tickerQuote, setTickerQuote] = useState(null);     // single quote for modal header
    const LIVE_QUOTES_REFRESH_MS = 20_000;
    const DASHBOARD_REFRESH_MS = 45_000;

    // Refs for scroll-to-view
    const predictionResultRef = useRef(null);
    const modalContentRef = useRef(null);
    const screenResultRef = useRef(null);

    // Debounced search – Nielsen #2: Match between system & real world
    const debouncedSearch = useDebounce(searchTerm, 250);

    // Dynamic document title – Nielsen #1: System status
    useDocumentTitle(
        activeTab === 'dashboard' ? 'Dashboard' :
        activeTab === 'screener' ? 'Stock Screener' :
        activeTab === 'backtest' ? 'Backtesting' :
        activeTab === 'portfolio' ? 'Portfolio' :
        activeTab === 'profile' ? 'Profile' :
        activeTab === 'settings' ? 'Settings' : null
    );

    // Profile preferences (persisted to localStorage)
    const [profilePrefs, setProfilePrefs] = useState(() => {
        try {
            const saved = localStorage.getItem('artha_profile_prefs');
            return saved ? JSON.parse(saved) : {
                defaultExchange: 'NSE',
                chartPeriod: '1y',
                riskTolerance: 'moderate',
                notificationsEnabled: true,
                compactView: false,
            };
        } catch { return { defaultExchange: 'NSE', chartPeriod: '1y', riskTolerance: 'moderate', notificationsEnabled: true, compactView: false }; }
    });

    const showToast = useCallback((message, type = 'info') => {
        setToast({ message, type });
    }, []);

    const formatTickerForDisplay = useCallback((ticker) => {
        return String(ticker || '')
            .trim()
            .replace(/^\^+/, '')
            .toUpperCase();
    }, []);

    const normalizeTickerForAnalysis = useCallback((ticker) => {
        const normalized = String(ticker || '')
            .trim()
            .replace(/^\^+/, '')
            .toUpperCase();

        return normalized.replace(/\.(NS|BO|L)$/i, '');
    }, []);

    const selectedTickerForAnalysis = useMemo(
        () => normalizeTickerForAnalysis(selectedTicker),
        [selectedTicker, normalizeTickerForAnalysis]
    );

    const selectedTickerForDisplay = useMemo(
        () => formatTickerForDisplay(selectedTicker),
        [selectedTicker, formatTickerForDisplay]
    );

    const formatModalFetchMessage = useCallback((err, fallback) => {
        const raw = err?.message ? String(err.message) : '';
        const lower = raw.toLowerCase();
        if (!raw) return fallback;
        if (lower.includes('404') || lower.includes('not found')) {
            return `${fallback} Coverage is not available for this symbol yet.`;
        }
        if (lower.includes('timeout')) {
            return `${fallback} The request timed out. Please retry in a moment.`;
        }
        if (lower.includes('cancelled')) {
            return `${fallback} The request was interrupted. Please retry.`;
        }
        return raw;
    }, []);

    const saveProfilePrefs = useCallback((newPrefs) => {
        setProfilePrefs(newPrefs);
        localStorage.setItem('artha_profile_prefs', JSON.stringify(newPrefs));
        showToast('Preferences saved', 'success');
    }, [showToast]);

    // Keyboard shortcuts – Nielsen #7: Flexibility & efficiency of use
    useKeyboardShortcut('k', () => {
        document.querySelector('[data-search-input]')?.focus();
    }, { ctrl: true });

    useKeyboardShortcut('Escape', () => {
        if (selectedTicker) setSelectedTicker(null);
    });

    // Lock body scroll when modal is open – prevents background scrolling
    useEffect(() => {
        if (selectedTicker) {
            document.body.classList.add('modal-open');
        } else {
            document.body.classList.remove('modal-open');
        }
        return () => document.body.classList.remove('modal-open');
    }, [selectedTicker]);

    // Reset page on search change
    useEffect(() => { setCurrentPage(1); }, [debouncedSearch]);

    // Auto-scroll to prediction results when they load
    useEffect(() => {
        if (prediction && predictionResultRef.current) {
            setTimeout(() => {
                predictionResultRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 200);
        }
    }, [prediction]);

    // Initial data fetch
    useEffect(() => {
        fetchInitialData();
        loadStrategies();
        // fetchInitialData/loadStrategies are declared later in the component body.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ─── Real-time quote polling for visible stocks ───
    const fetchLiveQuotes = useCallback(async (tickers) => {
        if (!tickers || tickers.length === 0) return;
        try {
            const data = await api.fetchBatchQuotes(tickers);
            if (data?.quotes) {
                setLiveQuotes(prev => ({ ...prev, ...data.quotes }));
                setLiveQuoteTime(new Date().toLocaleTimeString());
            }
        } catch (err) {
            console.warn('Live quotes fetch failed:', err.message);
        }
    }, []);

    const fetchTickerHistoryWithFallback = useCallback(async (ticker, period) => {
        const primaryTicker = String(ticker || '').trim();
        if (!primaryTicker) return [];

        const candidates = [primaryTicker];
        const normalizedTicker = normalizeTickerForAnalysis(primaryTicker);
        if (normalizedTicker && normalizedTicker !== primaryTicker) {
            candidates.push(normalizedTicker);
        }

        let lastError = null;
        for (const candidate of candidates) {
            try {
                const history = await api.fetchTickerHistory(candidate, period);
                if (Array.isArray(history) && history.length > 0) {
                    return history;
                }
                if (candidate === candidates[candidates.length - 1]) {
                    return history;
                }
            } catch (err) {
                lastError = err;
            }
        }

        if (lastError) throw lastError;
        return [];
    }, [normalizeTickerForAnalysis]);

    // Fetch single-ticker quote when modal opens
    useEffect(() => {
        if (!selectedTicker) { setTickerQuote(null); return; }

        const fetchIt = async () => {
            try {
                const data = await api.fetchQuote(selectedTicker);
                if (data && data.price) setTickerQuote(data);
            } catch { /* silent */ }
        };
        fetchIt();
        const interval = setInterval(fetchIt, LIVE_QUOTES_REFRESH_MS);
        return () => clearInterval(interval);
    }, [selectedTicker, LIVE_QUOTES_REFRESH_MS]);

    const loadStrategies = useCallback(async () => {
        try {
            const data = await api.getStrategies();
            const customStrategies = (data.custom || []).map(s => ({
                id: s.name,
                name: s.name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                icon: Filter,
                color: 'pink',
                category: s.metadata?.category || 'Custom',
                description: s.description || '',
                conditions: s.conditions || [],
                riskLevel: s.metadata?.risk_level || 'Medium',
                isCustom: true
            }));

            // Replace all strategies (keep built-in + fresh custom list)
            setStrategies([...INITIAL_STRATEGIES, ...customStrategies]);
        } catch (err) {
            console.error("Failed to load strategies", err);
        }
    }, []);

    const fetchInitialData = useCallback(async () => {
        try {
            const [stocksData, healthData, statsData, watchlistData] = await Promise.all([
                api.fetchStocks(),
                api.fetchHealth().catch(() => null),
                api.fetchStats().catch(() => null),
                api.fetchWatchlist().catch(() => [])
            ]);
            setStocks(stocksData);
            setHealth(healthData);
            setStats(statsData);
            setWatchlist(watchlistData);
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            setLoading(false);
        }
    }, [showToast]);

    // Keep dashboard cards and table synced without forcing manual refresh.
    useEffect(() => {
        if (activeTab !== 'dashboard') return;
        const interval = setInterval(() => {
            fetchInitialData();
        }, DASHBOARD_REFRESH_MS);
        return () => clearInterval(interval);
    }, [activeTab, fetchInitialData, DASHBOARD_REFRESH_MS]);

    // Filtered stocks based on debounced search – Nielsen #2
    const filteredStocks = useMemo(() =>
        stocks.filter(s => (s.ticker || '').toLowerCase().includes(debouncedSearch.toLowerCase())),
        [stocks, debouncedSearch]
    );

    // Pagination – Nielsen #7: Efficiency
    const totalPages = Math.max(1, Math.ceil(filteredStocks.length / ITEMS_PER_PAGE));
    const paginatedStocks = useMemo(() => {
        const start = (currentPage - 1) * ITEMS_PER_PAGE;
        return filteredStocks.slice(start, start + ITEMS_PER_PAGE);
    }, [filteredStocks, currentPage, ITEMS_PER_PAGE]);

    // Poll live quotes for currently visible paginated stocks
    useEffect(() => {
        if (activeTab !== 'dashboard' || loading) return;
        const visibleTickers = paginatedStocks.map(s => s.ticker).filter(Boolean);
        if (visibleTickers.length === 0) return;

        // Fetch immediately
        fetchLiveQuotes(visibleTickers);

        // Then poll continuously for near real-time updates
        const interval = setInterval(() => {
            fetchLiveQuotes(visibleTickers);
        }, LIVE_QUOTES_REFRESH_MS);

        return () => clearInterval(interval);
    }, [activeTab, loading, paginatedStocks, fetchLiveQuotes, LIVE_QUOTES_REFRESH_MS]);

    // ==================== API HANDLERS ====================

    const handleRefresh = async () => {
        setLoading(true);
        await fetchInitialData();
        showToast('Data refreshed!', 'success');
    };

    const handleWatchlistAdd = async (ticker) => {
        try {
            const newList = await api.addToWatchlist(ticker);
            setWatchlist(newList);
            showToast(`${formatTickerForDisplay(ticker)} added to watchlist`, 'success');
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    const handleWatchlistRemove = async (ticker) => {
        try {
            const newList = await api.removeFromWatchlist(ticker);
            setWatchlist(newList);
            showToast(`${formatTickerForDisplay(ticker)} removed`, 'info');
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    const handleStrategySave = (newStrategy) => {
        loadStrategies();
        setShowStrategyBuilder(false);
        showToast(`Strategy "${newStrategy.name}" created!`, 'success');
        setScreenStrategy(newStrategy.name);
    };

    const handleDeleteStrategy = async (strategyId) => {
        try {
            await api.deleteCustomStrategy(strategyId);
            setStrategies(prev => prev.filter(s => s.id !== strategyId));
            if (screenStrategy === strategyId) setScreenStrategy('momentum');
            showToast('Strategy deleted', 'success');
        } catch (err) {
            showToast(err.message || 'Failed to delete strategy', 'error');
        }
    };

    // Derived: separate built-in vs saved custom strategies
    const customStrategiesList = strategies.filter(s => !INITIAL_STRATEGIES.some(is => is.id === s.id));

    const handleRunScreener = async () => {
        setScreening(true);
        setScreenResults([]);
        setScreenElapsed(0);

        // Start elapsed timer
        const timerStart = Date.now();
        const timerInterval = setInterval(() => {
            setScreenElapsed(Math.floor((Date.now() - timerStart) / 1000));
        }, 1000);

        try {
            let params = {};
            if (screenStrategy === 'custom') {
                const conditions = {};
                if (customConditions.price_min || customConditions.price_max) {
                    conditions.price = { min: Number(customConditions.price_min) || 0, max: Number(customConditions.price_max) || 999999 };
                }
                if (customConditions.rsi_min || customConditions.rsi_max) {
                    conditions.rsi = { min: Number(customConditions.rsi_min) || 0, max: Number(customConditions.rsi_max) || 100 };
                }
                if (customConditions.volume_ratio) {
                    conditions.volume_ratio = { min: Number(customConditions.volume_ratio) };
                }
                params = { conditions };
            } else {
                // Use strategy-specific parameters
                params = strategyParams[screenStrategy] || {};
            }

            const result = await api.runScreener(screenStrategy, params);

            // Handle multiple possible response formats from API
            let resultsData = [];
            if (result) {
                if (Array.isArray(result)) {
                    // Direct array response
                    resultsData = result;
                } else if (Array.isArray(result.results)) {
                    // Nested results array
                    resultsData = result.results;
                } else if (Array.isArray(result.data)) {
                    // Data wrapper
                    resultsData = result.data;
                } else if (result.stocks && Array.isArray(result.stocks)) {
                    // Stocks wrapper
                    resultsData = result.stocks;
                } else if (result.screened_stocks && Array.isArray(result.screened_stocks)) {
                    // screened_stocks format
                    resultsData = result.screened_stocks;
                } else if (typeof result === 'object' && !result.error) {
                    // Try to extract any array from result
                    const keys = Object.keys(result);
                    for (const key of keys) {
                        if (Array.isArray(result[key]) && result[key].length > 0) {
                            resultsData = result[key];
                            break;
                        }
                    }
                }
            }

            setScreenResults(resultsData);
            const count = resultsData.length || result?.count || 0;

            if (count > 0) {
                showToast(`Found ${count} stocks matching ${screenStrategy} strategy`, 'success');
            } else {
                showToast(`No stocks found for ${screenStrategy} strategy. Try different parameters.`, 'warning');
            }
        } catch (err) {
            console.error('Screener error:', err);
            showToast(err.message || 'Screening failed. Please try again.', 'error');
        } finally {
            clearInterval(timerInterval);
            setScreening(false);
        }
    };

    const handleOpenTicker = async (ticker) => {
        const normalizedSelection = String(ticker || '').trim().toUpperCase();
        if (!normalizedSelection) return;

        setSelectedTicker(normalizedSelection);
        setChartData([]);
        setPrediction(null);
        setModalTab('overview');
        setFundamentals(null);
        setRiskMetrics(null);
        setStrategyEval(null);
        setFundamentalsError('');
        setRiskError('');
        setStrategiesError('');
        try {
            const data = await fetchTickerHistoryWithFallback(normalizedSelection, chartPeriod);
            setChartData(data);
        } catch {
            showToast('Failed to load history', 'error');
        }
    };

    const handleCloseModal = () => {
        setSelectedTicker(null);
        setPrediction(null);
        setModalTab('overview');
        setFundamentals(null);
        setRiskMetrics(null);
        setStrategyEval(null);
        setFundamentalsError('');
        setRiskError('');
        setStrategiesError('');
    };

    // Fetch fundamentals data for selected ticker
    const handleFetchFundamentals = async () => {
        if (!selectedTickerForAnalysis || loadingFundamentals || fundamentals) return;
        setFundamentalsError('');
        setLoadingFundamentals(true);
        try {
            const [fundData, piotroskiData] = await Promise.all([
                api.fetchFundamentals(selectedTickerForAnalysis, 'NSE').catch(() => null),
                api.fetchPiotroskiScore(selectedTickerForAnalysis, 'NSE').catch(() => null)
            ]);
            // fundData = { status, data: { valuation, profitability, growth, ... }, score: { overall_score, rating, ... } }
            // piotroskiData = { status, symbol, piotroski_score, classification, details }
            const normalizedFundamentals = {
                data: fundData?.data || null,
                score: fundData?.score || null,
                piotroski: piotroskiData || null,
            };

            const hasFundamentalsPayload = Boolean(
                normalizedFundamentals.data ||
                normalizedFundamentals.score ||
                normalizedFundamentals.piotroski
            );

            if (!hasFundamentalsPayload) {
                setFundamentals(null);
                setFundamentalsError(`No fundamentals coverage is currently available for ${selectedTickerForDisplay}.`);
                return;
            }

            setFundamentals(normalizedFundamentals);
        } catch (err) {
            setFundamentals(null);
            const message = formatModalFetchMessage(err, 'Could not load fundamentals.');
            setFundamentalsError(message);
            showToast(message, 'warning');
        } finally {
            setLoadingFundamentals(false);
        }
    };

    // Fetch risk metrics for selected ticker
    const handleFetchRisk = async () => {
        if (!selectedTickerForAnalysis || loadingRisk || riskMetrics) return;
        setRiskError('');
        setLoadingRisk(true);
        try {
            const data = await api.fetchRiskMetrics(selectedTickerForAnalysis, '1y');
            const hasRiskPayload = Boolean(
                data &&
                typeof data === 'object' &&
                data.metrics &&
                Object.keys(data.metrics).length > 0
            );

            if (!hasRiskPayload) {
                setRiskMetrics(null);
                setRiskError(`No risk analytics are currently available for ${selectedTickerForDisplay}.`);
                return;
            }

            setRiskMetrics(data);
        } catch (err) {
            setRiskMetrics(null);
            const message = formatModalFetchMessage(err, 'Could not load risk analytics.');
            setRiskError(message);
            showToast(message, 'warning');
        } finally {
            setLoadingRisk(false);
        }
    };

    // Fetch strategy evaluation for selected ticker
    const handleFetchStrategies = async () => {
        if (!selectedTickerForAnalysis || loadingStrategies || strategyEval) return;
        setStrategiesError('');
        setLoadingStrategies(true);
        try {
            const data = await api.multiStrategyScreen(selectedTickerForAnalysis, 2, 60, '1y');
            const hasStrategyPayload = Boolean(
                data &&
                typeof data === 'object' &&
                (
                    Array.isArray(data.all_results) ||
                    data.strategies_evaluated != null ||
                    data.best_strategy != null
                )
            );

            if (!hasStrategyPayload) {
                setStrategyEval(null);
                setStrategiesError(`No strategy evaluation output is currently available for ${selectedTickerForDisplay}.`);
                return;
            }

            setStrategyEval(data);
        } catch (err) {
            setStrategyEval(null);
            const message = formatModalFetchMessage(err, 'Could not evaluate strategies.');
            setStrategiesError(message);
            showToast(message, 'warning');
        } finally {
            setLoadingStrategies(false);
        }
    };

    // Re-fetch chart data when period changes (without resetting prediction)
    useEffect(() => {
        if (!selectedTicker) return;
        (async () => {
            try {
                const data = await fetchTickerHistoryWithFallback(selectedTicker, chartPeriod);
                setChartData(data);
            } catch (err) {
                console.error('Failed to reload chart for new period', err);
            }
        })();
    }, [chartPeriod, fetchTickerHistoryWithFallback, selectedTicker]);

    const handlePrediction = async () => {
        if (!selectedTickerForAnalysis) return;
        setPredicting(true);
        setPrediction(null);
        try {
            const [result, latestQuote] = await Promise.all([
                api.fetchPrediction(selectedTickerForAnalysis, Number(capital), Number(riskPct)),
                api.fetchQuote(selectedTicker).catch(() => null),
            ]);

            if (latestQuote?.price) {
                setTickerQuote(latestQuote);
                const predictedPrice = Number(result?.predicted_price_5d ?? result?.price_analysis?.predicted_price_5d);
                const livePrice = Number(latestQuote.price);
                const liveBasedReturn = Number.isFinite(predictedPrice) && livePrice > 0
                    ? ((predictedPrice - livePrice) / livePrice) * 100
                    : result?.predicted_return_pct;

                setPrediction({
                    ...result,
                    current_price: livePrice,
                    live_price: livePrice,
                    predicted_return_pct: liveBasedReturn,
                });
            } else {
                setPrediction(result);
            }
            // The useEffect on `prediction` handles auto-scroll
        } catch (err) {
            showToast(err.message || `Prediction failed for ${selectedTickerForDisplay}`, 'error');
        } finally {
            setPredicting(false);
        }
    };

    // Keep displayed prediction upside anchored to freshest live quote.
    useEffect(() => {
        if (!prediction || !tickerQuote?.price) return;
        const predictedPrice = Number(prediction?.predicted_price_5d ?? prediction?.price_analysis?.predicted_price_5d);
        const livePrice = Number(tickerQuote.price);
        if (!Number.isFinite(predictedPrice) || livePrice <= 0) return;

        const liveBasedReturn = ((predictedPrice - livePrice) / livePrice) * 100;
        setPrediction((prev) => {
            if (!prev) return prev;
            if (prev.current_price === livePrice && Math.abs((prev.predicted_return_pct || 0) - liveBasedReturn) < 0.01) {
                return prev;
            }
            return {
                ...prev,
                current_price: livePrice,
                live_price: livePrice,
                predicted_return_pct: liveBasedReturn,
            };
        });
    }, [tickerQuote, prediction]);

    const handleTrain = async () => {
        if (!selectedTickerForAnalysis) return;
        setTraining(true);
        setTrainingMessage(null);
        try {
            const result = await api.trainModel(selectedTickerForAnalysis);
            setTrainingMessage(result.message || 'Training complete!');
            showToast('Model trained successfully', 'success');
        } catch (err) {
            setTrainingMessage(err.message);
            showToast('Training failed', 'error');
        } finally {
            setTraining(false);
        }
    };

    const handleOpenDetailedAnalysis = async () => {
        if (!selectedTickerForAnalysis || generatingReport) return;

        const reportWindow = window.open('', '_blank', 'noopener,noreferrer');
        if (!reportWindow) {
            showToast('Please allow pop-ups to open detailed analysis.', 'warning');
            return;
        }

        setGeneratingReport(true);
        reportWindow.document.write('<p style="font-family: system-ui, sans-serif; padding: 24px;">Generating detailed analysis...</p>');

        try {
            const report = await api.fetchStockReport(selectedTickerForAnalysis, 'html');
            if (typeof report !== 'string' || report.trim().length === 0) {
                throw new Error('Detailed analysis is currently unavailable for this ticker.');
            }

            reportWindow.document.open();
            reportWindow.document.write(report);
            reportWindow.document.close();
            showToast(`Detailed analysis ready for ${selectedTickerForDisplay}.`, 'success');
        } catch (err) {
            reportWindow.close();
            showToast(err.message || 'Failed to generate detailed analysis report.', 'error');
        } finally {
            setGeneratingReport(false);
        }
    };

    const [backtestElapsed, setBacktestElapsed] = useState(0);

    const handleBacktest = async () => {
        setBacktesting(true);
        setBacktestResults(null);
        setMultiBacktestResults(null);
        setBacktestElapsed(0);
        const t0 = Date.now();
        const iv = setInterval(() => setBacktestElapsed(Math.floor((Date.now() - t0) / 1000)), 1000);
        try {
            if (backtestMultiMode && backtestTickers.length > 0) {
                // Multi-stock backtest
                const results = {};
                for (const ticker of backtestTickers) {
                    try {
                        const result = await api.runBacktest(backtestStrategy, { ...backtestParams, ticker });
                        results[ticker] = result;
                    } catch (err) {
                        results[ticker] = { error: err.message };
                    }
                }
                setMultiBacktestResults(results);
                showToast(`Backtest complete across ${backtestTickers.length} stocks!`, 'success');
            } else {
                // Single stock backtest
                const result = await api.runBacktest(backtestStrategy, { ...backtestParams, ticker: backtestTicker });
                setBacktestResults(result);
                showToast('Backtest complete!', 'success');
            }
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            clearInterval(iv);
            setBacktesting(false);
        }
    };

    const addBacktestTicker = (ticker) => {
        const t = ticker.trim().toUpperCase();
        if (t && !backtestTickers.includes(t)) {
            setBacktestTickers(prev => [...prev, t]);
        }
        setBacktestTickerInput('');
    };

    const removeBacktestTicker = (ticker) => {
        setBacktestTickers(prev => prev.filter(t => t !== ticker));
    };

    const handleFetchConfig = useCallback(async () => {
        setConfigLoading(true);
        try {
            const configData = await api.fetchConfig();
            setConfig(configData);
        } catch {
            showToast('Failed to load config', 'error');
        } finally {
            setConfigLoading(false);
        }
    }, [showToast]);

    useEffect(() => {
        if (activeTab === 'settings' && !config) handleFetchConfig();
    }, [activeTab, config, handleFetchConfig]);

    const handleSaveConfig = async () => {
        setSavingConfig(true);
        try {
            const updatedConfig = await api.updateConfig(config);
            setConfig(updatedConfig);
            showToast('Configuration saved!', 'success');
        } catch {
            showToast('Failed to save config', 'error');
        } finally {
            setSavingConfig(false);
        }
    };

    const handleClearCache = async () => {
        try {
            await api.clearCache();
            showToast('Cache cleared!', 'success');
        } catch {
            showToast('Failed to clear cache', 'error');
        }
    };

    // Multi-strategy handler
    const handleMultiStrategy = async (strategies, minOverlap) => {
        const strategyCount = Array.isArray(strategies) ? strategies.length : 0;
        const heavyScan = strategyCount >= 5 || minOverlap >= 4;

        const result = await api.runMultiStrategy(strategies, minOverlap, {
            maxTickers: heavyScan ? 1000 : 800,
            maxResults: heavyScan ? 220 : 150,
            timeout: heavyScan ? 360_000 : 300_000,
        });
        return result;
    };

    // CSV Export handler
    const exportToCSV = (data, filename = 'screener_results') => {
        if (!data || data.length === 0) return;
        const headers = Object.keys(data[0]);
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(h => {
                const val = row[h];
                if (typeof val === 'object' && val !== null) return `"${JSON.stringify(val).replace(/"/g, '""')}"`;
                if (typeof val === 'string' && val.includes(',')) return `"${val}"`;
                return val ?? '';
            }).join(','))
        ].join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `${filename}_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(link.href);
        showToast(`Exported ${data.length} rows to CSV`, 'success');
    };

    // Strategy comparison handler — supports multiple tickers
    const handleCompareStrategies = async () => {
        if (selectedCompareStrategies.length < 2) {
            showToast('Select at least 2 strategies to compare', 'warning');
            return;
        }
        const tickers = compareTickers.length > 0 ? compareTickers : [backtestTicker];
        if (tickers.length === 0 || tickers.every(t => !t)) {
            showToast('Enter at least one ticker', 'warning');
            return;
        }
        setComparing(true);
        setComparisonResults(null);
        setMultiCompareResults(null);
        try {
            const strategies = selectedCompareStrategies.map(id => ({ name: id, params: {} }));
            if (tickers.length === 1) {
                // Single ticker — existing behavior
                const result = await api.compareStrategies(strategies, { ...backtestParams, ticker: tickers[0] });
                setComparisonResults(result);
                setActiveCompareTicker(null);
            } else {
                // Multiple tickers — run comparison for each
                const results = {};
                for (const ticker of tickers) {
                    try {
                        const result = await api.compareStrategies(strategies, { ...backtestParams, ticker });
                        results[ticker] = result;
                    } catch (err) {
                        results[ticker] = { error: err.message };
                    }
                }
                setMultiCompareResults(results);
                setActiveCompareTicker(tickers[0]);
                setComparisonResults(null);
            }
            showToast(`Comparison complete for ${tickers.length} ticker(s)!`, 'success');
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            setComparing(false);
        }
    };

    const addCompareTicker = (ticker) => {
        const t = ticker.trim().toUpperCase();
        if (t && !compareTickers.includes(t)) {
            setCompareTickers(prev => [...prev, t]);
        }
        setCompareTickerInput('');
    };

    const removeCompareTicker = (ticker) => {
        setCompareTickers(prev => prev.filter(t => t !== ticker));
    };

    const toggleCompareStrategy = (strategyId) => {
        setSelectedCompareStrategies(prev =>
            prev.includes(strategyId)
                ? prev.filter(id => id !== strategyId)
                : [...prev, strategyId]
        );
    };

    // ==================== RENDER ====================

    return (
        <div className={`min-h-screen bg-pattern relative enterprise-shell ${profilePrefs.compactView ? 'enterprise-shell-compact' : ''}`}>
            {/* Fixed background gradient */}
            <div className="enterprise-backdrop fixed inset-0 bg-gradient-to-br from-slate-900 via-blue-900/80 to-slate-900 -z-10" />

            {/* Nielsen #1: Network status indicator */}
            {!isOnline && (
                <div className="network-offline-bar" role="alert">
                    <WifiOff className="w-4 h-4 inline mr-2" />
                    You are offline. Some features may be unavailable.
                </div>
            )}

            {/* Header */}
            <header className="enterprise-header sticky top-0 z-40" role="banner"
                style={{ background: 'linear-gradient(180deg, rgba(8,15,30,0.99) 0%, rgba(12,20,38,0.98) 100%)', backdropFilter: 'blur(24px)', boxShadow: '0 4px 30px rgba(0,0,0,0.5), 0 1px 0 rgba(255,255,255,0.05)' }}>
                {/* Top Bar — Brand + Actions */}
                <div className="container">
                    <div className="enterprise-topbar flex items-center justify-between py-5 border-b border-white/5">
                        <div className="enterprise-brand flex items-center gap-4">
                            <div className="enterprise-brand-mark relative flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 shadow-lg shadow-blue-500/25">
                                <Brain className="w-7 h-7 text-white" />
                            </div>
                            <div>
                                <h1 className="enterprise-brand-title text-xl font-black text-white tracking-tight leading-tight">Artha Drishti</h1>
                                <p className="enterprise-brand-subtitle text-[10px] text-blue-300/70 font-medium uppercase tracking-[0.15em]">GenAI Stock Intelligence Platform</p>
                            </div>
                        </div>
                        <div className="enterprise-actions flex items-center gap-3">
                            {health?.status === 'healthy' && (
                                <div className="enterprise-health-pill hidden md:flex items-center gap-2.5 px-4 py-2 rounded-xl bg-emerald-500/8 border border-emerald-500/20">
                                    <span className="relative flex h-2.5 w-2.5">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400" />
                                    </span>
                                    <span className="text-xs text-emerald-300 font-semibold">Online</span>
                                    <span className="text-[10px] text-emerald-400/60 font-medium">{stats?.total_stocks || 0} Stocks</span>
                                </div>
                            )}
                            <Button onClick={handleRefresh} variant="secondary" size="sm" className="!rounded-xl !px-3 !py-2.5">
                                <RefreshCw className="w-4 h-4" />
                            </Button>
                            <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                            <Button onClick={logout} variant="secondary" size="sm" title="Logout" className="!rounded-xl !px-3 !py-2.5">
                                <LogOut className="w-4 h-4" />
                            </Button>
                        </div>
                    </div>

                    {/* Navigation Tabs — Professional pill style with generous spacing */}
                    <nav className="enterprise-nav flex items-center gap-3 py-5 overflow-x-auto" role="tablist" aria-label="Main navigation">
                        {TABS.map((tab) => (
                            <button
                                key={tab.id}
                                role="tab"
                                aria-selected={activeTab === tab.id}
                                aria-controls={`panel-${tab.id}`}
                                id={`tab-${tab.id}`}
                                tabIndex={activeTab === tab.id ? 0 : -1}
                                onClick={() => setActiveTab(tab.id)}
                                className={`enterprise-nav-tab px-7 py-3.5 rounded-xl font-semibold text-[13px] transition-all duration-200 flex items-center justify-center gap-3 whitespace-nowrap ${activeTab === tab.id
                                    ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-500/25 ring-1 ring-white/20'
                                    : 'text-slate-400 hover:text-white hover:bg-white/8'
                                    }`}
                            >
                                <tab.icon className={`w-[18px] h-[18px] ${activeTab === tab.id ? 'text-white' : ''}`} /> {tab.name}
                                {tab.id === 'screener' && screenResults.length > 0 && (
                                    <span className="ml-1 min-w-[20px] h-5 flex items-center justify-center bg-green-500 text-white text-[10px] font-bold rounded-full px-1.5">
                                        {screenResults.length}
                                    </span>
                                )}
                                {tab.id === 'portfolio' && watchlist.length > 0 && (
                                    <span className="ml-1 min-w-[20px] h-5 flex items-center justify-center bg-amber-500 text-slate-900 text-[10px] font-bold rounded-full px-1.5">
                                        {watchlist.length}
                                    </span>
                                )}
                            </button>
                        ))}
                    </nav>
                </div>
            </header>

            <main
                id="main-content"
                className={`enterprise-main container pt-10 pb-8 relative ${profilePrefs.compactView ? 'enterprise-main-compact' : ''}`}
                role="main"
            >
                {/* DASHBOARD TAB */}
                {activeTab === 'dashboard' && (
                    <div className="space-y-6 animate-fade-in dashboard-page industry-page-shell" role="tabpanel" id="panel-dashboard" aria-labelledby="tab-dashboard">
                        {/* User greeting – Nielsen #6: Recognition */}
                        {user && (
                            <div className="flex items-center gap-3 mb-2">
                                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white font-bold text-lg">
                                    {user.avatar_url ? (
                                        <img src={user.avatar_url} alt="" className="w-full h-full rounded-full object-cover" />
                                    ) : (
                                        (user.username || 'U')[0].toUpperCase()
                                    )}
                                </div>
                                <div>
                                    <h2 className="text-lg font-bold text-white">Welcome back, {user.username}!</h2>
                                    <p className="text-xs text-blue-200">Here&apos;s your market overview for today</p>
                                </div>
                            </div>
                        )}

                        {/* Stats Grid */}
                        {loading ? (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {[...Array(4)].map((_, i) => <SkeletonLoader key={i} type="card" />)}
                            </div>
                        ) : (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <StatCard icon={BarChart2} label="Total Stocks" value={stocks.length} color="blue" />
                                <StatCard icon={TrendingUp} label="Gainers" value={stocks.filter(s => s.close > s.open).length} color="green" />
                                <StatCard icon={ArrowDownRight} label="Losers" value={stocks.filter(s => s.close < s.open).length} color="red" />
                                <StatCard icon={Star} label="Watchlist" value={watchlist.length} color="yellow" />
                            </div>
                        )}

                        {/* Top Gainers/Losers - Live Data */}
                        <TopMovers onTickerClick={handleOpenTicker} />

                        {/* AI Stock Recommendations */}
                        <StockRecommendations onTickerClick={handleOpenTicker} />

                        {/* Market Overview Widget */}
                        <MarketOverview />

                        {/* Search – Nielsen #7: Accelerators */}
                        <Card className="p-4 industry-section-card industry-search-card">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 bg-blue-500/20 rounded-xl">
                                    <Search className="w-5 h-5 text-blue-300" />
                                </div>
                                <input
                                    type="text"
                                    data-search-input
                                    placeholder="Search by ticker (e.g., RELIANCE, TCS)... Ctrl+K"
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="flex-1 bg-transparent outline-none text-white placeholder-blue-200/50 font-medium"
                                    aria-label="Search stocks by ticker"
                                />
                                {searchTerm && (
                                    <button
                                        onClick={() => setSearchTerm('')}
                                        className="p-1 rounded-lg bg-white/10 hover:bg-white/20 text-gray-400 transition"
                                        aria-label="Clear search"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                )}
                                <span className="text-xs text-gray-500">
                                    {filteredStocks.length} results
                                </span>
                            </div>
                        </Card>

                        {/* Stocks Table with Pagination */}
                        {loading ? (
                            <Card className="p-6">
                                <SkeletonLoader type="table" rows={8} />
                            </Card>
                        ) : (
                            <Card className="overflow-hidden industry-table-shell industry-table-dashboard">
                                {/* Live data indicator */}
                                {liveQuoteTime && (
                                    <div className="px-4 pt-3 flex items-center gap-2 text-xs text-gray-400">
                                        <span className="live-dot" />
                                        <span>Realtime stream active &middot; Last update: {liveQuoteTime}</span>
                                    </div>
                                )}
                                <div className="overflow-x-auto industry-table-scroll">
                                    <table className="industry-dense-table industry-dashboard-table">
                                        <thead>
                                            <tr>
                                                <th>Ticker</th>
                                                <th className="text-right">DB Close</th>
                                                <th className="text-right">Live Price</th>
                                                <th className="text-right">Change</th>
                                                <th className="text-right">Day Range</th>
                                                <th className="text-right">Volume</th>
                                                <th className="text-center industry-action-col">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                            {paginatedStocks.map((stock, idx) => {
                                                const q = liveQuotes[stock.ticker];
                                                const livePrice = q?.price;
                                                const changePct = q?.change_pct;
                                                const isUp = changePct > 0;
                                                const isDown = changePct < 0;
                                                return (
                                                <tr key={stock.ticker || idx}>
                                                    <td
                                                        className="font-bold text-blue-400 cursor-pointer hover:text-blue-300 focus:text-blue-300"
                                                        onClick={() => handleOpenTicker(stock.ticker)}
                                                        tabIndex={0}
                                                        onKeyDown={(e) => e.key === 'Enter' && handleOpenTicker(stock.ticker)}
                                                        role="button"
                                                    >
                                                        {formatTickerForDisplay(stock.ticker)}
                                                    </td>
                                                    <td className="text-right text-sm text-gray-400">₹{(stock.close || 0).toFixed(2)}</td>
                                                    <td className="text-right font-bold">
                                                        {livePrice ? (
                                                            <span className={isUp ? 'text-green-400' : isDown ? 'text-red-400' : 'text-white'}>
                                                                ₹{livePrice.toFixed(2)}
                                                            </span>
                                                        ) : (
                                                            <span className="text-gray-500 text-xs">—</span>
                                                        )}
                                                    </td>
                                                    <td className="text-right text-sm">
                                                        {changePct != null ? (
                                                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold ${isUp ? 'bg-green-500/20 text-green-400' : isDown ? 'bg-red-500/20 text-red-400' : 'bg-gray-500/20 text-gray-400'}`}>
                                                                {isUp ? <ArrowUpRight className="w-3 h-3" /> : isDown ? <ArrowDownRight className="w-3 h-3" /> : null}
                                                                {changePct > 0 ? '+' : ''}{changePct.toFixed(2)}%
                                                            </span>
                                                        ) : (
                                                            <span className="text-gray-500 text-xs">—</span>
                                                        )}
                                                    </td>
                                                    <td className="text-right text-xs text-gray-300">
                                                        {q?.day_low != null && q?.day_high != null ? (
                                                            <span>₹{q.day_low.toFixed(0)} – ₹{q.day_high.toFixed(0)}</span>
                                                        ) : (
                                                            <span className="text-gray-500">—</span>
                                                        )}
                                                    </td>
                                                    <td className="text-right text-sm text-gray-300">
                                                        {(q?.volume || stock.volume || 0).toLocaleString()}
                                                    </td>
                                                    <td className="text-center industry-action-cell">
                                                        <button
                                                            onClick={() => watchlist.includes(stock.ticker) ? handleWatchlistRemove(stock.ticker) : handleWatchlistAdd(stock.ticker)}
                                                            className={`industry-action-btn industry-watchlist-toggle p-1.5 rounded-lg transition ${watchlist.includes(stock.ticker) ? 'bg-yellow-500/20 text-yellow-400' : 'bg-white/10 text-gray-400 hover:text-yellow-400'}`}
                                                            aria-label={watchlist.includes(stock.ticker) ? `Remove ${formatTickerForDisplay(stock.ticker)} from watchlist` : `Add ${formatTickerForDisplay(stock.ticker)} to watchlist`}
                                                        >
                                                            {watchlist.includes(stock.ticker) ? <Star className="w-4 h-4 fill-current" /> : <StarOff className="w-4 h-4" />}
                                                        </button>
                                                    </td>
                                                </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>

                                {/* Pagination – Nielsen #3: User control & #7: Flexibility */}
                                {totalPages > 1 && (
                                    <div className="pagination" role="navigation" aria-label="Stock table pagination">
                                        <button
                                            onClick={() => setCurrentPage(1)}
                                            disabled={currentPage === 1}
                                            aria-label="First page"
                                        >
                                            <ChevronsLeft className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                            disabled={currentPage === 1}
                                            aria-label="Previous page"
                                        >
                                            <ChevronLeft className="w-4 h-4" />
                                        </button>

                                        {/* Page numbers */}
                                        {(() => {
                                            const pages = [];
                                            const start = Math.max(1, currentPage - 2);
                                            const end = Math.min(totalPages, currentPage + 2);
                                            for (let i = start; i <= end; i++) {
                                                pages.push(
                                                    <button
                                                        key={i}
                                                        onClick={() => setCurrentPage(i)}
                                                        className={i === currentPage ? 'active' : ''}
                                                        aria-label={`Page ${i}`}
                                                        aria-current={i === currentPage ? 'page' : undefined}
                                                    >
                                                        {i}
                                                    </button>
                                                );
                                            }
                                            return pages;
                                        })()}

                                        <button
                                            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                            disabled={currentPage === totalPages}
                                            aria-label="Next page"
                                        >
                                            <ChevronRight className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => setCurrentPage(totalPages)}
                                            disabled={currentPage === totalPages}
                                            aria-label="Last page"
                                        >
                                            <ChevronsRight className="w-4 h-4" />
                                        </button>

                                        <span className="text-xs text-gray-400 ml-3">
                                            Page {currentPage} of {totalPages} ({filteredStocks.length} stocks)
                                        </span>
                                    </div>
                                )}
                            </Card>
                        )}
                    </div>
                )}

                {/* SCREENER TAB */}
                {activeTab === 'screener' && (
                    <div className="space-y-6 animate-fade-in screener-page industry-page-shell" role="tabpanel" aria-label="Stock Screener">
                        <Card className="enterprise-tab-hero p-6">
                            <div className="flex items-start gap-4">
                                <div className="enterprise-tab-icon">
                                    <Filter className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="enterprise-tab-eyebrow">Workflow</p>
                                    <h2 className="enterprise-tab-headline">Screener Command Center</h2>
                                    <p className="enterprise-tab-subtitle">
                                        Design and execute institutional-grade scans with single or multi-strategy pipelines.
                                    </p>
                                </div>
                            </div>
                        </Card>

                        {showStrategyBuilder ? (
                            <StrategyBuilder
                                onSave={handleStrategySave}
                                onCancel={() => setShowStrategyBuilder(false)}
                            />
                        ) : (
                            <>
                                <div className="enterprise-mode-row industry-toolbar flex justify-between items-center">
                                    {/* Mode Toggle */}
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setScreenerMode('single')}
                                            className={`enterprise-mode-btn px-4 py-2 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 ${screenerMode === 'single'
                                                ? 'bg-gradient-to-r from-purple-200 to-blue-200 text-slate-900 shadow-lg border border-purple-300'
                                                : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                                }`}
                                        >
                                            <Filter className="w-4 h-4" />
                                            Single Strategy
                                        </button>
                                        <button
                                            onClick={() => setScreenerMode('multi')}
                                            className={`enterprise-mode-btn px-4 py-2 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 ${screenerMode === 'multi'
                                                ? 'bg-gradient-to-r from-purple-200 to-blue-200 text-slate-900 shadow-lg border border-purple-300'
                                                : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                                }`}
                                        >
                                            <Layers className="w-4 h-4" />
                                            Multi-Strategy
                                        </button>
                                    </div>
                                    <Button onClick={() => setScreenStrategy('custom')} variant="secondary" size="sm" className="enterprise-outline-btn">
                                        <Filter className="w-4 h-4 mr-2" />
                                        Custom Scan
                                    </Button>
                                </div>

                                {/* Single Strategy Mode */}
                                {screenerMode === 'single' && (
                                    <>
                                        <Card className="p-6 industry-section-card">
                                            <div className="flex items-center gap-3 mb-6">
                                                <div className="p-3 bg-purple-500/20 rounded-xl">
                                                    <Filter className="w-6 h-6 text-purple-300" />
                                                </div>
                                                <h2 className="text-2xl font-black text-white">Stock Screener</h2>
                                            </div>

                                            {/* Strategy Grid — Built-in Strategies */}
                                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
                                                {INITIAL_STRATEGIES.map(s => (
                                                    <button
                                                        key={s.id}
                                                        onClick={() => setScreenStrategy(s.id)}
                                                        className={`p-4 rounded-xl font-bold transition-all flex items-center gap-2 ${screenStrategy === s.id
                                                            ? 'bg-gradient-to-r from-blue-200 to-cyan-200 text-slate-900 shadow-lg border border-blue-300'
                                                            : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                                            }`}
                                                    >
                                                        <s.icon className="w-5 h-5" />{s.name}
                                                    </button>
                                                ))}
                                            </div>

                                            {/* Saved Custom Strategies */}
                                            {customStrategiesList.length > 0 && (
                                                <div className="mb-4">
                                                    <div className="flex items-center gap-2 mb-3">
                                                        <Star className="w-4 h-4 text-yellow-400" />
                                                        <span className="text-sm font-semibold text-yellow-200">Your Saved Strategies</span>
                                                        <span className="text-xs text-gray-500 ml-1">({customStrategiesList.length})</span>
                                                    </div>
                                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                                        {customStrategiesList.map(s => (
                                                            <div
                                                                key={s.id}
                                                                className={`relative group p-4 rounded-xl font-bold transition-all flex items-center gap-2 cursor-pointer ${
                                                                    screenStrategy === s.id
                                                                        ? 'bg-gradient-to-r from-yellow-200 to-orange-200 text-slate-900 shadow-lg border border-yellow-300'
                                                                        : 'bg-gradient-to-br from-purple-500/10 to-pink-500/10 text-purple-200 hover:from-purple-500/20 hover:to-pink-500/20 border border-purple-400/20 hover:border-purple-400/40'
                                                                }`}
                                                                onClick={() => setScreenStrategy(s.id)}
                                                            >
                                                                <s.icon className="w-5 h-5" />
                                                                <span className="truncate">{s.name}</span>
                                                                {s.category && (
                                                                    <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded whitespace-nowrap ${
                                                                        screenStrategy === s.id
                                                                            ? 'bg-slate-800/20 text-slate-700'
                                                                            : 'bg-purple-500/20 text-purple-300'
                                                                    }`}>
                                                                        {s.category}
                                                                    </span>
                                                                )}
                                                                <button
                                                                    onClick={(e) => { e.stopPropagation(); handleDeleteStrategy(s.id); }}
                                                                    className="absolute -top-2 -right-2 w-6 h-6 bg-red-500/80 hover:bg-red-500 rounded-full items-center justify-center text-white opacity-0 group-hover:opacity-100 transition-all hidden group-hover:flex shadow-lg"
                                                                    title="Delete strategy"
                                                                >
                                                                    <X className="w-3 h-3" />
                                                                </button>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* New Strategy Button */}
                                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
                                                <button
                                                    onClick={() => setShowStrategyBuilder(true)}
                                                    className="p-4 rounded-xl font-bold transition-all flex items-center gap-2 bg-white/5 text-purple-300 hover:bg-purple-500/10 border border-dashed border-purple-400/30 hover:border-purple-400/60"
                                                >
                                                    <Plus className="w-5 h-5" />New Strategy
                                                </button>
                                            </div>

                                            {/* Custom Conditions */}
                                            {screenStrategy === 'custom' && (
                                                <div className="bg-white/5 rounded-xl p-4 mb-6 border border-white/10">
                                                    <h3 className="font-bold text-white mb-3">Custom Conditions</h3>
                                                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                                                        {Object.keys(customConditions).map(key => (
                                                            <input
                                                                key={key}
                                                                type="number"
                                                                placeholder={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                                                value={customConditions[key]}
                                                                onChange={(e) => setCustomConditions({ ...customConditions, [key]: e.target.value })}
                                                            />
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Strategy-Specific Parameters */}
                                            {screenStrategy !== 'custom' && strategyParams[screenStrategy] && (
                                                <div className="bg-white/5 rounded-xl p-4 mb-6 border border-white/10">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <h3 className="font-bold text-white text-sm">
                                                            {INITIAL_STRATEGIES.find(s => s.id === screenStrategy)?.name} Parameters
                                                        </h3>
                                                        <button
                                                            onClick={() => setStrategyParams(prev => ({ ...prev, [screenStrategy]: STRATEGY_PARAMS[screenStrategy] }))}
                                                            className="text-xs text-blue-400 hover:text-blue-300 transition"
                                                        >
                                                            Reset to Defaults
                                                        </button>
                                                    </div>
                                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                                        {Object.entries(strategyParams[screenStrategy]).map(([key, value]) => (
                                                            <div key={key}>
                                                                <label className="text-xs text-gray-400 block mb-1">
                                                                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                                                </label>
                                                                <input
                                                                    type="number"
                                                                    step={typeof value === 'number' && !Number.isInteger(value) ? '0.1' : '1'}
                                                                    value={value}
                                                                    onChange={(e) => setStrategyParams(prev => ({
                                                                        ...prev,
                                                                        [screenStrategy]: { ...prev[screenStrategy], [key]: Number(e.target.value) }
                                                                    }))}
                                                                />
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            <Button onClick={handleRunScreener} disabled={screening} variant="purple" size="lg" className="w-full">
                                                {screening ? (
                                                    <>
                                                        <RefreshCw className="w-5 h-5 animate-spin" />
                                                        Scanning... {screenElapsed}s
                                                        <span className="text-xs opacity-70 ml-1">(~2-5 min for all stocks)</span>
                                                    </>
                                                ) : (
                                                    <><Play className="w-5 h-5" />Run {strategies.find(s => s.id === screenStrategy)?.name || screenStrategy} Scan</>
                                                )}
                                            </Button>
                                        </Card>

                                        {/* Scanning indicator */}
                                        {screening && (
                                            <Card className="p-6 border-purple-500/30 industry-accent-card">
                                                <div className="flex flex-col items-center gap-4 py-8">
                                                    <div className="relative">
                                                        <div className="w-16 h-16 border-4 border-purple-500/30 border-t-purple-400 rounded-full animate-spin" />
                                                        <Brain className="w-6 h-6 text-purple-300 absolute inset-0 m-auto" />
                                                    </div>
                                                    <div className="text-center">
                                                        <p className="text-white font-bold text-lg">Analysing all NSE stocks...</p>
                                                        <p className="text-gray-400 text-sm mt-1">
                                                            Strategy: <span className="text-purple-300 capitalize">{strategies.find(s => s.id === screenStrategy)?.name || screenStrategy}</span>
                                                            {' '}&bull;{' '}Elapsed: <span className="text-white font-mono">{screenElapsed}s</span>
                                                        </p>
                                                        <div className="w-64 mx-auto mt-3 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                                            <div className="h-full bg-gradient-to-r from-purple-500 to-blue-500 rounded-full transition-all duration-1000"
                                                                style={{ width: `${Math.min(95, (screenElapsed / 180) * 100)}%` }} />
                                                        </div>
                                                    </div>
                                                </div>
                                            </Card>
                                        )}

                                        {/* Results */}
                                        {screenResults.length > 0 && (
                                            <Card ref={screenResultRef} className="overflow-hidden industry-table-shell industry-table-screener">
                                                <div className="px-6 py-4 bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-b border-white/10 flex items-center justify-between">
                                                    <h3 className="text-lg font-black text-green-300 flex items-center gap-2">
                                                        <TrendingUp className="w-5 h-5" />Found {screenResults.length} Stocks
                                                        <span className="text-xs font-normal text-gray-400 ml-2">in {screenElapsed}s</span>
                                                    </h3>
                                                    <Button onClick={() => exportToCSV(screenResults, `${screenStrategy}_screen`)} variant="secondary" size="sm">
                                                        <Download className="w-4 h-4" />Export CSV
                                                    </Button>
                                                </div>
                                                <div className="overflow-x-auto industry-table-scroll">
                                                    <table className="industry-dense-table industry-screener-table">
                                                        <thead>
                                                            <tr>
                                                                <th>Ticker</th>
                                                                <th>Score</th>
                                                                <th>Price</th>
                                                                <th>Conditions</th>
                                                                <th>Confidence</th>
                                                                <th>RSI (14)</th>
                                                                <th>Price Chg (20d)</th>
                                                                <th>Volume Ratio</th>
                                                                <th>Patterns</th>
                                                                <th className="industry-action-col">Action</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-white/5">
                                                            {screenResults.map((row, idx) => {
                                                                const ki = row.key_indicators || {};
                                                                const rsi = ki.rsi_14;
                                                                const priceChg = ki.price_change_20d;
                                                                const volRatio = ki.volume_ratio_20;
                                                                return (
                                                                    <tr key={idx}>
                                                                        <td className="text-sm font-semibold text-white">{formatTickerForDisplay(row.ticker) || '-'}</td>
                                                                        <td className="text-sm text-white">{typeof row.score === 'number' ? row.score.toLocaleString() : row.score ?? '-'}</td>
                                                                        <td className="text-sm text-white">{typeof row.current_price === 'number' ? `₹${row.current_price.toLocaleString()}` : row.current_price ?? '-'}</td>
                                                                        <td className="text-sm text-white font-mono">{row.conditions_passed ?? '?'}/{row.total_conditions ?? '?'}</td>
                                                                        <td className="text-sm">
                                                                            <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                                                                                (row.confidence ?? 0) >= 80 ? 'bg-green-500/20 text-green-300' :
                                                                                (row.confidence ?? 0) >= 60 ? 'bg-yellow-500/20 text-yellow-300' :
                                                                                'bg-red-500/20 text-red-300'
                                                                            }`}>
                                                                                {typeof row.confidence === 'number' ? `${row.confidence}%` : row.confidence ?? '-'}
                                                                            </span>
                                                                        </td>
                                                                        <td className="text-sm">
                                                                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                                                                rsi != null && rsi > 70 ? 'bg-red-500/20 text-red-300' :
                                                                                rsi != null && rsi < 30 ? 'bg-green-500/20 text-green-300' :
                                                                                'bg-blue-500/15 text-blue-300'
                                                                            }`}>
                                                                                {rsi != null ? rsi.toFixed(1) : '-'}
                                                                            </span>
                                                                        </td>
                                                                        <td className="text-sm">
                                                                            <span className={`font-medium ${
                                                                                priceChg != null && priceChg > 0 ? 'text-green-400' :
                                                                                priceChg != null && priceChg < 0 ? 'text-red-400' :
                                                                                'text-gray-400'
                                                                            }`}>
                                                                                {priceChg != null ? `${priceChg > 0 ? '+' : ''}${priceChg.toFixed(2)}%` : '-'}
                                                                            </span>
                                                                        </td>
                                                                        <td className="text-sm">
                                                                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                                                                                volRatio != null && volRatio > 1.5 ? 'bg-purple-500/20 text-purple-300' :
                                                                                volRatio != null && volRatio < 0.5 ? 'bg-gray-500/20 text-gray-400' :
                                                                                'bg-white/10 text-gray-300'
                                                                            }`}>
                                                                                {volRatio != null ? `${volRatio.toFixed(2)}x` : '-'}
                                                                            </span>
                                                                        </td>
                                                                        <td className="text-sm text-white">
                                                                            {Array.isArray(row.patterns) && row.patterns.length > 0
                                                                                ? <div className="flex flex-wrap gap-1">{row.patterns.map((p, pi) => (
                                                                                    <span key={pi} className="industry-pattern-chip px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 text-[10px] font-medium">{p}</span>
                                                                                  ))}</div>
                                                                                : <span className="text-gray-500">—</span>}
                                                                        </td>
                                                                        <td className="industry-action-cell">
                                                                            <Button onClick={() => handleOpenTicker(row.ticker)} size="sm" variant="secondary" className="industry-action-btn">
                                                                                Analyze
                                                                            </Button>
                                                                        </td>
                                                                    </tr>
                                                                );
                                                            })}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </Card>
                                        )}

                                        {/* Empty state when no results and not scanning */}
                                        {!screening && screenResults.length === 0 && (
                                            <Card className="p-12 text-center industry-empty-card">
                                                <Filter className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                                                <h3 className="text-xl font-bold text-gray-400 mb-2">No Scan Results Yet</h3>
                                                <p className="text-gray-500 text-sm max-w-md mx-auto">
                                                    Select a strategy above and click &quot;Run Scan&quot; to find stocks matching your criteria.
                                                    Scans typically take 2-5 minutes for all NSE stocks.
                                                </p>
                                            </Card>
                                        )}
                                    </>
                                )}

                                {/* Multi-Strategy Mode */}
                                {screenerMode === 'multi' && (
                                    <MultiStrategyPanel
                                        onAnalyze={handleOpenTicker}
                                        onRunMultiStrategy={handleMultiStrategy}
                                        availableStrategies={strategies}
                                    />
                                )}
                            </>
                        )}
                    </div>
                )}

                {/* BACKTEST TAB */}
                {activeTab === 'backtest' && (
                    <div className="space-y-6 animate-fade-in backtest-page industry-page-shell" role="tabpanel" aria-label="Backtesting">
                        <Card className="enterprise-tab-hero p-6">
                            <div className="flex items-start gap-4">
                                <div className="enterprise-tab-icon">
                                    <Clock className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="enterprise-tab-eyebrow">Simulation</p>
                                    <h2 className="enterprise-tab-headline">Backtest Lab</h2>
                                    <p className="enterprise-tab-subtitle">
                                        Validate strategy behavior across market regimes with single-run and comparative analytics.
                                    </p>
                                </div>
                            </div>
                        </Card>

                        {/* Mode Toggle */}
                        <div className="enterprise-mode-row industry-toolbar flex gap-3">
                            <button
                                onClick={() => setComparisonMode(false)}
                                className={`enterprise-mode-btn px-5 py-3 rounded-xl font-bold text-sm transition-all flex items-center gap-2.5 ${!comparisonMode
                                    ? 'bg-gradient-to-r from-blue-200 to-cyan-200 text-slate-900 shadow-lg border border-blue-300'
                                    : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                    }`}
                            >
                                <Clock className="w-5 h-5" />
                                Single Strategy
                            </button>
                            <button
                                onClick={() => setComparisonMode(true)}
                                className={`enterprise-mode-btn px-5 py-3 rounded-xl font-bold text-sm transition-all flex items-center gap-2.5 ${comparisonMode
                                    ? 'bg-gradient-to-r from-blue-200 to-cyan-200 text-slate-900 shadow-lg border border-blue-300'
                                    : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                    }`}
                            >
                                <BarChart2 className="w-5 h-5" />
                                Compare Strategies
                            </button>
                        </div>

                        {/* Single Strategy Backtest */}
                        {!comparisonMode && (
                            <>
                                <Card className="p-6 industry-section-card">
                                    <div className="flex items-center justify-between mb-6">
                                        <div className="flex items-center gap-3">
                                            <div className="p-3 bg-blue-500/20 rounded-xl">
                                                <Clock className="w-6 h-6 text-blue-300" />
                                            </div>
                                            <h2 className="text-2xl font-black text-white">Strategy Backtesting</h2>
                                        </div>
                                        <button
                                            onClick={() => setBacktestMultiMode(!backtestMultiMode)}
                                            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${backtestMultiMode
                                                ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg'
                                                : 'bg-white/5 text-gray-300 hover:bg-white/10 border border-white/10'
                                            }`}
                                        >
                                            <Layers className="w-4 h-4" />
                                            {backtestMultiMode ? 'Multi-Stock ON' : 'Multi-Stock'}
                                        </button>
                                    </div>

                                    {/* Ticker Input — single or multi */}
                                    {!backtestMultiMode ? (
                                        <div className="mb-5">
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Ticker</label>
                                            <div className="relative">
                                                <input
                                                    type="text"
                                                    value={backtestTicker}
                                                    onChange={(e) => { setBacktestTicker(e.target.value.toUpperCase()); setBacktestTickerSearch(e.target.value); }}
                                                    placeholder="e.g. RELIANCE"
                                                    className="w-full text-lg"
                                                />
                                                {backtestTickerSearch && stocks.filter(s => s.ticker?.toUpperCase().includes(backtestTickerSearch.toUpperCase())).slice(0, 5).length > 0 && (
                                                    <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-slate-800 border border-white/20 rounded-xl shadow-xl max-h-40 overflow-y-auto">
                                                        {stocks.filter(s => s.ticker?.toUpperCase().includes(backtestTickerSearch.toUpperCase())).slice(0, 5).map(s => (
                                                            <button key={s.ticker} onClick={() => { setBacktestTicker(s.ticker); setBacktestTickerSearch(''); }}
                                                                className="w-full text-left px-4 py-2.5 text-sm text-white hover:bg-white/10 transition">
                                                                {s.ticker}
                                                            </button>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="mb-5">
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Tickers (Multi-Stock)</label>
                                            <div className="flex flex-wrap gap-2 mb-3 min-h-[42px] p-2.5 bg-white/5 rounded-xl border border-white/10">
                                                {backtestTickers.map(t => (
                                                    <span key={t} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-500/20 text-blue-200 rounded-lg text-sm font-bold border border-blue-500/30">
                                                        {t}
                                                        <button onClick={() => removeBacktestTicker(t)} className="text-blue-300 hover:text-red-400 transition-colors ml-0.5">&times;</button>
                                                    </span>
                                                ))}
                                                <div className="relative flex-1 min-w-[140px]">
                                                    <input
                                                        type="text"
                                                        value={backtestTickerInput}
                                                        onChange={(e) => setBacktestTickerInput(e.target.value.toUpperCase())}
                                                        onKeyDown={(e) => {
                                                            if (e.key === 'Enter' || e.key === ',') {
                                                                e.preventDefault();
                                                                addBacktestTicker(backtestTickerInput);
                                                            } else if (e.key === 'Backspace' && !backtestTickerInput && backtestTickers.length > 0) {
                                                                removeBacktestTicker(backtestTickers[backtestTickers.length - 1]);
                                                            }
                                                        }}
                                                        placeholder={backtestTickers.length === 0 ? 'Type ticker + Enter...' : 'Add more...'}
                                                        className="w-full bg-transparent border-none outline-none text-white text-sm py-1 px-1"
                                                        style={{ boxShadow: 'none' }}
                                                    />
                                                    {backtestTickerInput && stocks.filter(s => s.ticker?.toUpperCase().includes(backtestTickerInput) && !backtestTickers.includes(s.ticker)).slice(0, 5).length > 0 && (
                                                        <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-slate-800 border border-white/20 rounded-xl shadow-xl max-h-40 overflow-y-auto">
                                                            {stocks.filter(s => s.ticker?.toUpperCase().includes(backtestTickerInput) && !backtestTickers.includes(s.ticker)).slice(0, 5).map(s => (
                                                                <button key={s.ticker} onClick={() => addBacktestTicker(s.ticker)}
                                                                    className="w-full text-left px-4 py-2.5 text-sm text-white hover:bg-white/10 transition">
                                                                    {s.ticker}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="flex flex-wrap gap-2">
                                                <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold self-center mr-1">Presets:</span>
                                                {Object.entries(TICKER_PRESETS).map(([name, tickers]) => (
                                                    <button key={name} onClick={() => setBacktestTickers(tickers)}
                                                        className="text-[11px] px-3 py-1.5 rounded-lg bg-white/5 text-gray-300 hover:bg-white/10 hover:text-white border border-white/10 transition-all font-medium">
                                                        {name}
                                                    </button>
                                                ))}
                                                <button onClick={() => setBacktestTickers([])}
                                                    className="text-[11px] px-3 py-1.5 rounded-lg bg-red-500/10 text-red-300 hover:bg-red-500/20 border border-red-500/20 transition-all font-medium">
                                                    Clear
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                                        <div>
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Strategy</label>
                                            <select value={backtestStrategy} onChange={(e) => setBacktestStrategy(e.target.value)}>
                                                {INITIAL_STRATEGIES.filter(s => s.id !== 'custom').map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Start Date</label>
                                            <input type="date" value={backtestParams.start_date} onChange={(e) => setBacktestParams({ ...backtestParams, start_date: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">End Date</label>
                                            <input type="date" value={backtestParams.end_date} onChange={(e) => setBacktestParams({ ...backtestParams, end_date: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Initial Capital (₹)</label>
                                            <input type="number" value={backtestParams.initial_capital} onChange={(e) => setBacktestParams({ ...backtestParams, initial_capital: Number(e.target.value) })} />
                                        </div>
                                        <div>
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Max Positions</label>
                                            <input type="number" value={backtestParams.max_positions} onChange={(e) => setBacktestParams({ ...backtestParams, max_positions: Number(e.target.value) })} />
                                        </div>
                                        <div>
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Rebalance</label>
                                            <select value={backtestParams.rebalance_frequency} onChange={(e) => setBacktestParams({ ...backtestParams, rebalance_frequency: e.target.value })}>
                                                <option value="daily">Daily</option>
                                                <option value="weekly">Weekly</option>
                                                <option value="monthly">Monthly</option>
                                            </select>
                                        </div>
                                    </div>

                                    <Button onClick={handleBacktest} disabled={backtesting} variant="primary" size="lg" className="w-full">
                                        {backtesting ? <><RefreshCw className="w-5 h-5 animate-spin" />Running backtest... {backtestElapsed}s</> : <><Play className="w-5 h-5" />Run Backtest{backtestMultiMode ? ` on ${backtestTickers.length} Stocks` : ''}</>}
                                    </Button>
                                </Card>

                                {/* Multi-Stock Backtest Results */}
                                {multiBacktestResults && backtestMultiMode && (
                                    <Card className="p-6 industry-table-shell industry-table-backtest">
                                        <h3 className="text-xl font-black text-white mb-5 flex items-center gap-2">
                                            <PieChart className="w-6 h-6 text-blue-400" />Multi-Stock Backtest — {backtestStrategy}
                                        </h3>
                                        <div className="overflow-x-auto mb-4 industry-table-scroll">
                                            <table className="w-full text-sm industry-dense-table industry-backtest-table">
                                                <thead>
                                                    <tr className="border-b border-white/10">
                                                        <th className="text-left text-[10px] text-gray-400 font-bold uppercase tracking-wider py-3 px-3">Ticker</th>
                                                        <th className="text-center text-[10px] text-gray-400 font-bold uppercase tracking-wider py-3 px-3">Total Return</th>
                                                        <th className="text-center text-[10px] text-gray-400 font-bold uppercase tracking-wider py-3 px-3">Final Value</th>
                                                        <th className="text-center text-[10px] text-gray-400 font-bold uppercase tracking-wider py-3 px-3">Sharpe</th>
                                                        <th className="text-center text-[10px] text-gray-400 font-bold uppercase tracking-wider py-3 px-3">Max DD</th>
                                                        <th className="text-center text-[10px] text-gray-400 font-bold uppercase tracking-wider py-3 px-3">Win Rate</th>
                                                        <th className="text-center text-[10px] text-gray-400 font-bold uppercase tracking-wider py-3 px-3">Trades</th>
                                                        <th className="text-center text-[10px] text-gray-400 font-bold uppercase tracking-wider py-3 px-3">Grade</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {Object.entries(multiBacktestResults).map(([ticker, r]) => {
                                                        if (r.error) return (
                                                            <tr key={ticker} className="border-b border-white/5">
                                                                <td className="py-3 px-3 font-bold text-white">{formatTickerForDisplay(ticker)}</td>
                                                                <td colSpan={6} className="py-3 px-3 text-red-400 text-xs">{r.error}</td>
                                                                <td className="py-3 px-3 text-center"><span className="text-[10px] px-2 py-1 bg-red-500/15 text-red-400 rounded-md font-bold">ERR</span></td>
                                                            </tr>
                                                        );
                                                        const grade = r.total_return_pct > 20 ? 'A' : r.total_return_pct > 10 ? 'B' : r.total_return_pct > 0 ? 'C' : 'D';
                                                        return (
                                                            <tr key={ticker} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                                                <td className="py-3 px-3 font-bold text-blue-400">{formatTickerForDisplay(ticker)}</td>
                                                                <td className={`py-3 px-3 text-center font-bold ${(r.total_return_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                    {(r.total_return_pct || 0) >= 0 ? '+' : ''}{r.total_return_pct?.toFixed(2)}%
                                                                </td>
                                                                <td className="py-3 px-3 text-center text-white font-medium">₹{r.final_value?.toLocaleString()}</td>
                                                                <td className="py-3 px-3 text-center text-white">{r.sharpe_ratio?.toFixed(2) || '—'}</td>
                                                                <td className="py-3 px-3 text-center text-red-400 font-medium">{r.max_drawdown}%</td>
                                                                <td className="py-3 px-3 text-center text-white">{r.win_rate}%</td>
                                                                <td className="py-3 px-3 text-center text-gray-400">{r.total_trades}</td>
                                                                <td className="py-3 px-3 text-center">
                                                                    <span className={`text-xs px-2.5 py-1 rounded-lg font-black ${grade === 'A' ? 'bg-green-500/15 text-green-400' : grade === 'B' ? 'bg-blue-500/15 text-blue-400' : grade === 'C' ? 'bg-yellow-500/15 text-yellow-400' : 'bg-red-500/15 text-red-400'}`}>
                                                                        {grade}
                                                                    </span>
                                                                </td>
                                                            </tr>
                                                        );
                                                    })}
                                                </tbody>
                                            </table>
                                        </div>
                                    </Card>
                                )}

                                {/* Backtest Results */}
                                {backtestResults && (
                                    <Card className="p-6 industry-section-card">
                                        <div className="flex items-center justify-between mb-6">
                                            <h3 className="text-xl font-black text-white flex items-center gap-2">
                                                <PieChart className="w-6 h-6 text-blue-400" />Backtest Results — {backtestStrategy}
                                            </h3>
                                            <Button onClick={() => exportToCSV(
                                                [{ strategy: backtestStrategy, ...backtestResults }],
                                                `backtest_${backtestStrategy}`
                                            )} variant="secondary" size="sm">
                                                <Download className="w-4 h-4" />Export
                                            </Button>
                                        </div>

                                        {/* Performance Grade */}
                                        <div className="mb-6 p-4 rounded-xl border border-white/10" style={{
                                            background: backtestResults.total_return_pct > 20 ? 'rgba(34,197,94,0.1)' :
                                                        backtestResults.total_return_pct > 0 ? 'rgba(59,130,246,0.1)' : 'rgba(239,68,68,0.1)'
                                        }}>
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <p className="text-xs text-gray-400">Performance Grade</p>
                                                    <p className={`text-3xl font-black ${backtestResults.total_return_pct > 20 ? 'text-green-400' :
                                                        backtestResults.total_return_pct > 10 ? 'text-blue-400' :
                                                        backtestResults.total_return_pct > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                        {backtestResults.total_return_pct > 20 ? 'A' :
                                                         backtestResults.total_return_pct > 10 ? 'B' :
                                                         backtestResults.total_return_pct > 0 ? 'C' : 'D'}
                                                    </p>
                                                </div>
                                                <div className="text-right">
                                                    <p className="text-xs text-gray-400">Risk-Adjusted Return</p>
                                                    <p className="text-2xl font-black text-white">
                                                        {backtestResults.sharpe_ratio ? (backtestResults.sharpe_ratio > 1 ? 'Good' : backtestResults.sharpe_ratio > 0.5 ? 'Fair' : 'Poor') : '—'}
                                                        {' '}{backtestResults.sharpe_ratio?.toFixed(2) || '—'}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                                            <StatCard icon={DollarSign} label="Final Value" value={`₹${backtestResults.final_value?.toLocaleString()}`} color="green" />
                                            <StatCard icon={TrendingUp} label="Total Return" value={`${backtestResults.total_return_pct}%`} change={backtestResults.total_return_pct} color="blue" />
                                            <StatCard icon={Target} label="Sharpe Ratio" value={backtestResults.sharpe_ratio?.toFixed(2)} color="purple" />
                                            <StatCard icon={AlertTriangle} label="Max Drawdown" value={`${backtestResults.max_drawdown}%`} color="red" />
                                        </div>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-6">
                                            <div className="bg-white/5 rounded-xl p-5 flex flex-col items-center justify-center text-center border border-white/10">
                                                <p className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">Win Rate</p>
                                                <p className="text-2xl font-black text-white leading-none">{backtestResults.win_rate}%</p>
                                                <div className="w-full bg-gray-700 rounded-full h-1.5 mt-3">
                                                    <div className="bg-green-400 h-1.5 rounded-full" style={{width: `${Math.min(100, backtestResults.win_rate || 0)}%`}} />
                                                </div>
                                            </div>
                                            <div className="bg-white/5 rounded-xl p-5 flex flex-col items-center justify-center text-center border border-white/10">
                                                <p className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">Total Trades</p>
                                                <p className="text-2xl font-black text-white leading-none">{backtestResults.total_trades}</p>
                                            </div>
                                            <div className="bg-white/5 rounded-xl p-5 flex flex-col items-center justify-center text-center border border-white/10">
                                                <p className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">Profit Factor</p>
                                                <p className={`text-2xl font-black leading-none ${(backtestResults.profit_factor || 0) > 1.5 ? 'text-green-400' : (backtestResults.profit_factor || 0) > 1 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                    {backtestResults.profit_factor?.toFixed(2) || '—'}
                                                </p>
                                            </div>
                                            <div className="bg-white/5 rounded-xl p-5 flex flex-col items-center justify-center text-center border border-white/10">
                                                <p className="text-[11px] text-gray-400 font-semibold uppercase tracking-wider mb-2">Avg Trade P&L</p>
                                                <p className={`text-2xl font-black leading-none ${(backtestResults.avg_trade_pnl || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                    {backtestResults.avg_trade_pnl ? `₹${backtestResults.avg_trade_pnl.toLocaleString()}` : '—'}
                                                </p>
                                            </div>
                                        </div>
                                        {backtestResults.equity_curve && <PriceChart data={backtestResults.equity_curve} />}
                                    </Card>
                                )}
                            </>
                        )}

                        {/* Strategy Comparison Mode */}
                        {comparisonMode && (
                            <>
                                <Card className="p-6 industry-section-card">
                                    <div className="flex items-center gap-3 mb-6">
                                        <div className="p-3 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-xl">
                                            <BarChart2 className="w-6 h-6 text-blue-300" />
                                        </div>
                                        <div>
                                            <h2 className="text-2xl font-black text-white">Multi-Stock Strategy Comparison</h2>
                                            <p className="text-sm text-gray-400 mt-0.5">{selectedCompareStrategies.length} strategies × {compareTickers.length} stock{compareTickers.length !== 1 ? 's' : ''}</p>
                                        </div>
                                    </div>

                                    {/* Strategy Selection */}
                                    <div className="mb-6">
                                        <label className="text-[11px] font-bold text-blue-300 block mb-3 uppercase tracking-wider">Select Strategies</label>
                                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                                            {INITIAL_STRATEGIES.filter(s => s.id !== 'custom').map(s => (
                                                <button
                                                    key={s.id}
                                                    onClick={() => toggleCompareStrategy(s.id)}
                                                    className={`p-3.5 rounded-xl font-semibold text-[13px] transition-all flex items-center justify-center gap-2.5 ${selectedCompareStrategies.includes(s.id)
                                                        ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg ring-1 ring-white/20'
                                                        : 'bg-white/5 text-gray-300 hover:bg-white/10 border border-white/10'
                                                        }`}
                                                >
                                                    <s.icon className="w-4 h-4 flex-shrink-0" />{s.name}
                                                    {selectedCompareStrategies.includes(s.id) && (
                                                        <span className="ml-auto text-[10px] bg-white/20 text-white rounded-full w-5 h-5 flex items-center justify-center font-black">✓</span>
                                                    )}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Multi-Ticker Input */}
                                    <div className="mb-6">
                                        <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Tickers</label>
                                        
                                        {/* Ticker Chips */}
                                        <div className="flex flex-wrap gap-2 mb-3 min-h-[44px] p-3 bg-white/4 rounded-xl border border-white/10">
                                            {compareTickers.map(t => (
                                                <span key={t} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-blue-500/20 to-purple-500/15 text-blue-200 rounded-lg text-sm font-bold border border-blue-400/25 shadow-sm">
                                                    {t}
                                                    <button onClick={() => removeCompareTicker(t)} className="text-blue-300 hover:text-red-400 transition-colors ml-1 text-lg leading-none">&times;</button>
                                                </span>
                                            ))}
                                            <div className="relative flex-1 min-w-[140px]">
                                                <input
                                                    type="text"
                                                    value={compareTickerInput}
                                                    onChange={(e) => setCompareTickerInput(e.target.value.toUpperCase())}
                                                    onKeyDown={(e) => {
                                                        if (e.key === 'Enter' || e.key === ',') {
                                                            e.preventDefault();
                                                            addCompareTicker(compareTickerInput);
                                                        } else if (e.key === 'Backspace' && !compareTickerInput && compareTickers.length > 0) {
                                                            removeCompareTicker(compareTickers[compareTickers.length - 1]);
                                                        }
                                                    }}
                                                    placeholder={compareTickers.length === 0 ? 'Type ticker + Enter...' : 'Add more...'}
                                                    className="w-full bg-transparent border-none outline-none text-white text-sm py-1.5 px-1"
                                                    style={{ boxShadow: 'none' }}
                                                />
                                                {compareTickerInput && stocks.filter(s => s.ticker?.toUpperCase().includes(compareTickerInput) && !compareTickers.includes(s.ticker)).slice(0, 6).length > 0 && (
                                                    <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-slate-800 border border-white/20 rounded-xl shadow-xl max-h-48 overflow-y-auto">
                                                        {stocks.filter(s => s.ticker?.toUpperCase().includes(compareTickerInput) && !compareTickers.includes(s.ticker)).slice(0, 6).map(s => (
                                                            <button key={s.ticker} onClick={() => addCompareTicker(s.ticker)}
                                                                className="w-full text-left px-4 py-2.5 text-sm text-white hover:bg-white/10 transition font-medium">
                                                                {s.ticker}
                                                            </button>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Preset Groups — improved grid layout */}
                                        <div className="flex flex-wrap gap-2 items-center">
                                            <span className="text-[10px] text-gray-500 uppercase tracking-wider font-bold mr-1">Quick Select:</span>
                                            {Object.entries(TICKER_PRESETS).map(([name, tickers]) => (
                                                <button
                                                    key={name}
                                                    onClick={() => setCompareTickers(tickers)}
                                                    className="text-[11px] px-3 py-1.5 rounded-lg bg-white/5 text-gray-300 hover:bg-blue-500/15 hover:text-blue-200 hover:border-blue-500/30 border border-white/10 transition-all font-semibold"
                                                >
                                                    {name} ({tickers.length})
                                                </button>
                                            ))}
                                            <button
                                                onClick={() => setCompareTickers([])}
                                                className="text-[11px] px-3 py-1.5 rounded-lg bg-red-500/8 text-red-300 hover:bg-red-500/20 border border-red-500/20 transition-all font-semibold"
                                            >
                                                Clear All
                                            </button>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                                        <div>
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Start Date</label>
                                            <input type="date" value={backtestParams.start_date} onChange={(e) => setBacktestParams({ ...backtestParams, start_date: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">End Date</label>
                                            <input type="date" value={backtestParams.end_date} onChange={(e) => setBacktestParams({ ...backtestParams, end_date: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="text-[11px] font-bold text-blue-300 block mb-2 uppercase tracking-wider">Initial Capital (₹)</label>
                                            <input type="number" value={backtestParams.initial_capital} onChange={(e) => setBacktestParams({ ...backtestParams, initial_capital: Number(e.target.value) })} />
                                        </div>
                                    </div>

                                    <Button onClick={handleCompareStrategies} disabled={comparing || selectedCompareStrategies.length < 2 || compareTickers.length === 0} variant="primary" size="lg" className="w-full">
                                        {comparing ? <><RefreshCw className="w-5 h-5 animate-spin" />Comparing across {compareTickers.length} stock(s)...</> : <><BarChart2 className="w-5 h-5" />Compare {selectedCompareStrategies.length} Strategies on {compareTickers.length} Stock{compareTickers.length !== 1 ? 's' : ''}</>}
                                    </Button>
                                </Card>

                                {/* Single-Ticker Comparison Results */}
                                {comparisonResults && !multiCompareResults && (
                                    <Card className="p-6 industry-table-shell industry-table-compare industry-compare-single">
                                        <h3 className="text-xl font-black text-white mb-4 flex items-center gap-2">
                                            <BarChart2 className="w-6 h-6 text-blue-400" />Strategy Comparison Results
                                        </h3>
                                        {/* Buy & Hold Benchmark Highlight */}
                                        {comparisonResults.benchmark && (
                                            <div className="mb-5 p-4 rounded-xl bg-gradient-to-r from-amber-500/10 to-yellow-500/10 border border-amber-500/25">
                                                <div className="flex flex-wrap items-center justify-between gap-3">
                                                    <div className="flex items-center gap-3">
                                                        <div className="p-2 bg-amber-500/20 rounded-lg">
                                                            <TrendingUp className="w-5 h-5 text-amber-400" />
                                                        </div>
                                                        <div>
                                                            <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">Buy & Hold Benchmark</p>
                                                            <p className="text-sm text-gray-300 mt-0.5">If you simply bought and held {comparisonResults.ticker}</p>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center gap-6">
                                                        <div className="text-center">
                                                            <p className="text-[10px] text-gray-500 uppercase">Total Return</p>
                                                            <p className={`text-xl font-black ${comparisonResults.benchmark.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                {comparisonResults.benchmark.total_return_pct >= 0 ? '+' : ''}{comparisonResults.benchmark.total_return_pct?.toFixed(2)}%
                                                            </p>
                                                        </div>
                                                        <div className="text-center">
                                                            <p className="text-[10px] text-gray-500 uppercase">Annualized</p>
                                                            <p className={`text-lg font-bold ${comparisonResults.benchmark.annualized_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                {comparisonResults.benchmark.annualized_return_pct >= 0 ? '+' : ''}{comparisonResults.benchmark.annualized_return_pct?.toFixed(2)}%
                                                            </p>
                                                        </div>
                                                        <div className="text-center">
                                                            <p className="text-[10px] text-gray-500 uppercase">Sharpe</p>
                                                            <p className="text-lg font-bold text-white">{comparisonResults.benchmark.sharpe_ratio?.toFixed(3)}</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                        <StrategyComparison data={comparisonResults} className="strategy-comparison-embedded" />
                                    </Card>
                                )}

                                {/* Multi-Ticker Comparison Results */}
                                {multiCompareResults && (
                                    <Card className="p-6 industry-table-shell industry-table-compare industry-compare-multi">
                                        <h3 className="text-xl font-black text-white mb-4 flex items-center gap-2">
                                            <BarChart2 className="w-6 h-6 text-blue-400" />Multi-Stock Comparison Results
                                        </h3>

                                        {/* Aggregated Buy & Hold Summary */}
                                        <div className="mb-5 overflow-x-auto industry-table-scroll">
                                            <table className="w-full text-sm industry-dense-table industry-compare-summary-table">
                                                <thead>
                                                    <tr className="border-b border-white/10">
                                                        <th className="text-left text-xs text-gray-400 font-bold uppercase tracking-wider py-2.5 px-3">Ticker</th>
                                                        <th className="text-center text-xs text-gray-400 font-bold uppercase tracking-wider py-2.5 px-3">Buy & Hold Return</th>
                                                        <th className="text-center text-xs text-gray-400 font-bold uppercase tracking-wider py-2.5 px-3">Best Strategy</th>
                                                        <th className="text-center text-xs text-gray-400 font-bold uppercase tracking-wider py-2.5 px-3">Best Return</th>
                                                        <th className="text-center text-xs text-gray-400 font-bold uppercase tracking-wider py-2.5 px-3">vs Buy & Hold</th>
                                                        <th className="text-center text-xs text-gray-400 font-bold uppercase tracking-wider py-2.5 px-3">Status</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {Object.entries(multiCompareResults).map(([ticker, result]) => {
                                                        if (result.error) {
                                                            return (
                                                                <tr key={ticker} className="border-b border-white/5">
                                                                    <td className="py-3 px-3 font-bold text-white">{formatTickerForDisplay(ticker)}</td>
                                                                    <td colSpan={4} className="py-3 px-3 text-red-400 text-xs">{result.error}</td>
                                                                    <td className="py-3 px-3 text-center"><span className="industry-status-chip text-[10px] px-2 py-1 bg-red-500/15 text-red-400 rounded-md font-bold">ERROR</span></td>
                                                                </tr>
                                                            );
                                                        }
                                                        const bnh = result.benchmark?.total_return_pct ?? 0;
                                                        const bestStrat = result.comparison?.reduce((a, b) => (b.total_return_pct || 0) > (a.total_return_pct || 0) ? b : a, result.comparison?.[0] || {});
                                                        const bestReturn = bestStrat?.total_return_pct ?? 0;
                                                        const excess = bestReturn - bnh;
                                                        return (
                                                            <tr key={ticker} className={`border-b border-white/5 cursor-pointer transition-colors ${activeCompareTicker === ticker ? 'bg-blue-500/10' : 'hover:bg-white/5'}`}
                                                                onClick={() => setActiveCompareTicker(ticker)}>
                                                                <td className="py-3 px-3 font-bold text-blue-400">{formatTickerForDisplay(ticker)}</td>
                                                                <td className={`py-3 px-3 text-center font-bold ${bnh >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                    {bnh >= 0 ? '+' : ''}{bnh.toFixed(2)}%
                                                                </td>
                                                                <td className="py-3 px-3 text-center text-white font-medium">
                                                                    {(bestStrat?.strategy || '—').replace(/_/g, ' ')}
                                                                </td>
                                                                <td className={`py-3 px-3 text-center font-bold ${bestReturn >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                    {bestReturn >= 0 ? '+' : ''}{bestReturn.toFixed(2)}%
                                                                </td>
                                                                <td className={`py-3 px-3 text-center font-bold ${excess >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                    {excess >= 0 ? '+' : ''}{excess.toFixed(2)}%
                                                                </td>
                                                                <td className="py-3 px-3 text-center">
                                                                    <span className={`industry-status-chip text-[10px] px-2 py-1 rounded-md font-bold ${excess >= 0 ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400'}`} data-label-short={excess >= 0 ? 'OUT' : 'UNDER'}>
                                                                        {excess >= 0 ? 'OUTPERFORM' : 'UNDERPERFORM'}
                                                                    </span>
                                                                </td>
                                                            </tr>
                                                        );
                                                    })}
                                                </tbody>
                                            </table>
                                        </div>

                                        {/* Ticker Tabs */}
                                        <div className="flex flex-wrap gap-2 mb-4">
                                            {Object.keys(multiCompareResults).filter(t => !multiCompareResults[t].error).map(ticker => (
                                                <button
                                                    key={ticker}
                                                    onClick={() => setActiveCompareTicker(ticker)}
                                                    className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${
                                                        activeCompareTicker === ticker
                                                            ? 'bg-gradient-to-r from-blue-200 to-cyan-200 text-slate-900 shadow-lg'
                                                            : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                                    }`}
                                                >
                                                    {formatTickerForDisplay(ticker)}
                                                </button>
                                            ))}
                                        </div>

                                        {/* Active ticker detail */}
                                        {activeCompareTicker && multiCompareResults[activeCompareTicker] && !multiCompareResults[activeCompareTicker].error && (
                                            <div>
                                                {/* Buy & Hold Banner for selected ticker */}
                                                {multiCompareResults[activeCompareTicker].benchmark && (
                                                    <div className="mb-4 p-4 rounded-xl bg-gradient-to-r from-amber-500/10 to-yellow-500/10 border border-amber-500/25">
                                                        <div className="flex flex-wrap items-center justify-between gap-3">
                                                            <div className="flex items-center gap-3">
                                                                <div className="p-2 bg-amber-500/20 rounded-lg">
                                                                    <TrendingUp className="w-5 h-5 text-amber-400" />
                                                                </div>
                                                                <div>
                                                                    <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">{activeCompareTicker} — Buy & Hold</p>
                                                                    <p className="text-sm text-gray-300 mt-0.5">Passive investment benchmark</p>
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center gap-6">
                                                                <div className="text-center">
                                                                    <p className="text-[10px] text-gray-500 uppercase">Total Return</p>
                                                                    <p className={`text-xl font-black ${multiCompareResults[activeCompareTicker].benchmark.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                        {multiCompareResults[activeCompareTicker].benchmark.total_return_pct >= 0 ? '+' : ''}{multiCompareResults[activeCompareTicker].benchmark.total_return_pct?.toFixed(2)}%
                                                                    </p>
                                                                </div>
                                                                <div className="text-center">
                                                                    <p className="text-[10px] text-gray-500 uppercase">Annualized</p>
                                                                    <p className={`text-lg font-bold ${multiCompareResults[activeCompareTicker].benchmark.annualized_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                        {multiCompareResults[activeCompareTicker].benchmark.annualized_return_pct >= 0 ? '+' : ''}{multiCompareResults[activeCompareTicker].benchmark.annualized_return_pct?.toFixed(2)}%
                                                                    </p>
                                                                </div>
                                                                <div className="text-center">
                                                                    <p className="text-[10px] text-gray-500 uppercase">Sharpe</p>
                                                                    <p className="text-lg font-bold text-white">{multiCompareResults[activeCompareTicker].benchmark.sharpe_ratio?.toFixed(3)}</p>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
                                                <StrategyComparison data={multiCompareResults[activeCompareTicker]} className="strategy-comparison-embedded" />
                                            </div>
                                        )}
                                    </Card>
                                )}
                            </>
                        )}
                    </div>
                )}

                {/* PORTFOLIO TAB */}
                {activeTab === 'portfolio' && (
                    <div className="space-y-6 animate-fade-in portfolio-page industry-page-shell" role="tabpanel" aria-label="Portfolio">
                        <Card className="enterprise-tab-hero p-6">
                            <div className="flex items-start gap-4">
                                <div className="enterprise-tab-icon">
                                    <Briefcase className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="enterprise-tab-eyebrow">Holdings</p>
                                    <h2 className="enterprise-tab-headline">Portfolio Intelligence</h2>
                                    <p className="enterprise-tab-subtitle">
                                        Track exposure, monitor watchlists, and surface actionable target insights from one unified view.
                                    </p>
                                </div>
                            </div>
                        </Card>

                        <PortfolioDashboard />

                        <Card className="p-6 industry-section-card">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-3">
                                    <div className="p-3 bg-yellow-500/20 rounded-xl">
                                        <Star className="w-6 h-6 text-yellow-300" />
                                    </div>
                                    <h2 className="text-2xl font-black text-white">Watchlist</h2>
                                </div>
                                <span className="text-sm text-gray-400">{watchlist.length} stocks</span>
                            </div>

                            {/* Search Bar */}
                            <div className="mb-6">
                                <WatchlistSearch
                                    onAddToWatchlist={handleWatchlistAdd}
                                    watchlist={watchlist}
                                />
                            </div>

                            {watchlist.length === 0 ? (
                                <div className="text-center py-12">
                                    <StarOff className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                                    <p className="text-gray-400">Your watchlist is empty</p>
                                    <p className="text-sm text-gray-500">Search for stocks above to add them</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {watchlist.map(ticker => {
                                        const stock = stocks.find(s => s.ticker === ticker);
                                        return (
                                            <div key={ticker} className="enterprise-watchlist-card bg-white/5 rounded-xl p-4 border border-white/10 flex justify-between items-center">
                                                <div>
                                                    <p className="font-bold text-blue-400 cursor-pointer hover:text-blue-300" onClick={() => handleOpenTicker(ticker)}>
                                                        {formatTickerForDisplay(ticker)}
                                                    </p>
                                                    {stock && <p className="text-lg font-semibold text-white">₹{stock.close?.toFixed(2)}</p>}
                                                </div>
                                                <div className="flex gap-2">
                                                    <Button onClick={() => handleOpenTicker(ticker)} size="sm" variant="secondary">
                                                        <ChevronRight className="w-4 h-4" />
                                                    </Button>
                                                    <Button onClick={() => handleWatchlistRemove(ticker)} size="sm" variant="danger">
                                                        <Trash2 className="w-4 h-4" />
                                                    </Button>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </Card>

                        {/* Price Targets for Watchlist */}
                        {watchlist.length > 0 && (
                            <Card className="p-6 industry-section-card">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="p-3 bg-green-500/20 rounded-xl">
                                        <Target className="w-6 h-6 text-green-300" />
                                    </div>
                                    <h2 className="text-xl font-black text-white">Price Targets & Analysis</h2>
                                </div>
                                <PriceTargetsDashboard tickers={watchlist.slice(0, 6)} />
                            </Card>
                        )}
                    </div>
                )}

                {/* PROFILE TAB */}
                {activeTab === 'profile' && (
                    <div className="space-y-6 animate-fade-in profile-page industry-page-shell" role="tabpanel" aria-label="Profile">
                        <Card className="enterprise-tab-hero p-6">
                            <div className="flex items-start gap-4">
                                <div className="enterprise-tab-icon">
                                    <User className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="enterprise-tab-eyebrow">Account</p>
                                    <h2 className="enterprise-tab-headline">Profile & Preferences</h2>
                                    <p className="enterprise-tab-subtitle">
                                        Personalize trading defaults and review your activity footprint with cleaner operational controls.
                                    </p>
                                </div>
                            </div>
                        </Card>

                        {/* Profile Header */}
                        <Card className="overflow-hidden industry-section-card">
                            <div className="px-6 py-8 bg-gradient-to-r from-blue-600/20 via-purple-600/15 to-indigo-600/20 border-b border-white/10">
                                <div className="flex items-center gap-5">
                                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-3xl font-black shadow-xl shadow-blue-500/25">
                                        {user?.avatar_url ? (
                                            <img src={user.avatar_url} alt="" className="w-full h-full rounded-2xl object-cover" />
                                        ) : (
                                            (user?.username || 'U')[0].toUpperCase()
                                        )}
                                    </div>
                                    <div>
                                        <h2 className="text-2xl font-black text-white">{user?.username || 'User'}</h2>
                                        <p className="text-sm text-blue-200/70 mt-1">{user?.email || 'Artha Drishti Member'}</p>
                                        <div className="flex items-center gap-2 mt-2">
                                            <span className="px-3 py-1 rounded-lg bg-blue-500/15 text-blue-300 text-xs font-bold border border-blue-500/25">
                                                Active Investor
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </Card>

                        {/* Trading Preferences */}
                        <Card className="p-6 industry-section-card">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-3 bg-purple-500/20 rounded-xl">
                                    <Gauge className="w-6 h-6 text-purple-300" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-black text-white">Trading Preferences</h3>
                                    <p className="text-xs text-gray-400">Customize your analysis defaults</p>
                                </div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                <div>
                                    <label className="text-xs font-semibold text-blue-200 block mb-2">Default Exchange</label>
                                    <select
                                        value={profilePrefs.defaultExchange}
                                        onChange={(e) => setProfilePrefs(prev => ({...prev, defaultExchange: e.target.value}))}
                                        className="w-full"
                                    >
                                        <option value="NSE">NSE (National Stock Exchange)</option>
                                        <option value="BSE">BSE (Bombay Stock Exchange)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-blue-200 block mb-2">Default Chart Period</label>
                                    <select
                                        value={profilePrefs.chartPeriod}
                                        onChange={(e) => setProfilePrefs(prev => ({...prev, chartPeriod: e.target.value}))}
                                        className="w-full"
                                    >
                                        <option value="1m">1 Month</option>
                                        <option value="3m">3 Months</option>
                                        <option value="6m">6 Months</option>
                                        <option value="1y">1 Year</option>
                                        <option value="all">All Time</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-blue-200 block mb-2">Risk Tolerance</label>
                                    <select
                                        value={profilePrefs.riskTolerance}
                                        onChange={(e) => setProfilePrefs(prev => ({...prev, riskTolerance: e.target.value}))}
                                        className="w-full"
                                    >
                                        <option value="conservative">Conservative</option>
                                        <option value="moderate">Moderate</option>
                                        <option value="aggressive">Aggressive</option>
                                    </select>
                                </div>
                                <div className="flex items-center gap-3 p-3 bg-white/3 rounded-xl border border-white/5">
                                    <input
                                        type="checkbox"
                                        checked={profilePrefs.compactView}
                                        onChange={(e) => setProfilePrefs(prev => ({...prev, compactView: e.target.checked}))}
                                    />
                                    <span className="text-white font-medium text-sm">Compact View Mode</span>
                                </div>
                            </div>
                            <div className="mt-6 flex gap-3">
                                <Button onClick={() => saveProfilePrefs(profilePrefs)} variant="success">
                                    <Download className="w-4 h-4" /> Save Preferences
                                </Button>
                            </div>
                        </Card>

                        {/* Account Summary */}
                        <Card className="p-6 industry-section-card">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-3 bg-cyan-500/20 rounded-xl">
                                    <Shield className="w-6 h-6 text-cyan-300" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-black text-white">Account Summary</h3>
                                    <p className="text-xs text-gray-400">Your activity on Artha Drishti</p>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div className="bg-white/5 rounded-xl p-5 text-center border border-white/5">
                                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1.5 font-semibold">Watchlist</p>
                                    <p className="text-2xl font-black text-blue-400">{watchlist.length}</p>
                                    <p className="text-[10px] text-gray-500 mt-1">stocks tracked</p>
                                </div>
                                <div className="bg-white/5 rounded-xl p-5 text-center border border-white/5">
                                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1.5 font-semibold">Strategies</p>
                                    <p className="text-2xl font-black text-purple-400">{strategies.length}</p>
                                    <p className="text-[10px] text-gray-500 mt-1">configured</p>
                                </div>
                                <div className="bg-white/5 rounded-xl p-5 text-center border border-white/5">
                                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1.5 font-semibold">Scans Run</p>
                                    <p className="text-2xl font-black text-green-400">{screenResults.length > 0 ? screenResults.length : 0}</p>
                                    <p className="text-[10px] text-gray-500 mt-1">results found</p>
                                </div>
                                <div className="bg-white/5 rounded-xl p-5 text-center border border-white/5">
                                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-1.5 font-semibold">Theme</p>
                                    <p className="text-2xl font-black text-yellow-400">{theme === 'dark' ? 'Dark' : 'Light'}</p>
                                    <p className="text-[10px] text-gray-500 mt-1">mode active</p>
                                </div>
                            </div>
                        </Card>

                        {/* Danger Zone */}
                        <Card className="p-6 border-red-500/20 border industry-section-card">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="p-3 bg-red-500/20 rounded-xl">
                                    <AlertTriangle className="w-6 h-6 text-red-400" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-black text-white">Account Actions</h3>
                                    <p className="text-xs text-gray-400">Manage your session</p>
                                </div>
                            </div>
                            <Button onClick={logout} variant="secondary" className="!border-red-500/30 !text-red-400 hover:!bg-red-500/10">
                                <LogOut className="w-4 h-4" /> Sign Out
                            </Button>
                        </Card>
                    </div>
                )}

                {/* SETTINGS TAB */}
                {activeTab === 'settings' && (
                    <div className="space-y-6 animate-fade-in settings-page industry-page-shell" role="tabpanel" aria-label="Settings">
                        <Card className="enterprise-tab-hero p-6">
                            <div className="flex items-start gap-4">
                                <div className="enterprise-tab-icon">
                                    <Settings className="w-6 h-6" />
                                </div>
                                <div>
                                    <p className="enterprise-tab-eyebrow">Operations</p>
                                    <h2 className="enterprise-tab-headline">Runtime Controls</h2>
                                    <p className="enterprise-tab-subtitle">
                                        Adjust performance and caching parameters to balance responsiveness, stability, and throughput.
                                    </p>
                                </div>
                            </div>
                        </Card>

                        <Card className="p-6 industry-section-card">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-3 bg-gray-500/20 rounded-xl">
                                    <Settings className="w-6 h-6 text-gray-300" />
                                </div>
                                <h2 className="text-2xl font-black text-white">Settings</h2>
                            </div>

                            {configLoading ? <LoadingSpinner text="Loading configuration..." /> : config && (
                                <div className="space-y-6">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Max Workers</label>
                                            <input type="number" value={config.max_workers} onChange={(e) => setConfig({ ...config, max_workers: Number(e.target.value) })} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Cache TTL (seconds)</label>
                                            <input type="number" value={config.cache_ttl_seconds} onChange={(e) => setConfig({ ...config, cache_ttl_seconds: Number(e.target.value) })} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Timeout (seconds)</label>
                                            <input type="number" value={config.timeout_seconds} onChange={(e) => setConfig({ ...config, timeout_seconds: Number(e.target.value) })} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Min Data Points</label>
                                            <input type="number" value={config.min_data_points} onChange={(e) => setConfig({ ...config, min_data_points: Number(e.target.value) })} />
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <input type="checkbox" checked={config.enable_caching} onChange={(e) => setConfig({ ...config, enable_caching: e.target.checked })} />
                                        <span className="text-white font-medium">Enable Caching</span>
                                    </div>
                                    <div className="flex gap-3">
                                        <Button onClick={handleSaveConfig} variant="success" disabled={savingConfig}>
                                            <Download className="w-4 h-4" />{savingConfig ? 'Saving...' : 'Save Configuration'}
                                        </Button>
                                        <Button onClick={handleClearCache} variant="secondary">
                                            <Trash2 className="w-4 h-4" />Clear Cache
                                        </Button>
                                    </div>
                                </div>
                            )}
                        </Card>
                    </div>
                )}
            </main>

            {/* Stock Detail Modal – Nielsen #3: User control (Escape to close) */}
            {selectedTicker && (
                <div className="stock-modal-overlay industry-modal-shell" role="dialog" aria-modal="true" aria-label={`${selectedTickerForDisplay} Stock Analysis`} onClick={(e) => e.target === e.currentTarget && handleCloseModal()}>
                    <div className="stock-modal-container industry-modal-container" ref={modalContentRef}>
                        {/* Modal Header – prominent back/close buttons + live price */}
                        <div className="stock-modal-header industry-modal-header">
                            <div className="flex items-center gap-3 industry-modal-primary">
                                <button onClick={handleCloseModal} className="stock-modal-close-btn" title="Go Back">
                                    <ArrowLeft className="w-5 h-5" />
                                </button>
                                <div className="industry-modal-heading-block">
                                    <h2 className="text-2xl font-black text-white industry-modal-title">{selectedTickerForDisplay}</h2>
                                    <p className="text-blue-100 text-sm industry-modal-subtitle">{tickerQuote?.name || 'Advanced Stock Intelligence'}</p>
                                </div>
                                {/* Live Price Badge */}
                                {tickerQuote && (
                                    <div className="ml-4 flex items-center gap-3 industry-modal-live">
                                        <div className="text-right">
                                            <div className="flex items-center gap-2">
                                                <span className="live-dot" />
                                                <span className="text-2xl font-black text-white">₹{tickerQuote.price?.toFixed(2)}</span>
                                            </div>
                                            <div className={`flex items-center gap-1 text-sm font-bold ${tickerQuote.change_pct > 0 ? 'text-green-400' : tickerQuote.change_pct < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                                                {tickerQuote.change_pct > 0 ? <ArrowUpRight className="w-4 h-4" /> : tickerQuote.change_pct < 0 ? <ArrowDownRight className="w-4 h-4" /> : null}
                                                <span>{tickerQuote.change > 0 ? '+' : ''}{tickerQuote.change?.toFixed(2)}</span>
                                                <span>({tickerQuote.change_pct > 0 ? '+' : ''}{tickerQuote.change_pct?.toFixed(2)}%)</span>
                                            </div>
                                        </div>
                                        {tickerQuote.day_low != null && tickerQuote.day_high != null && (
                                            <div className="hidden md:block text-xs text-gray-400 border-l border-white/10 pl-3 ml-1">
                                                <p>Day: ₹{tickerQuote.day_low?.toFixed(2)} – ₹{tickerQuote.day_high?.toFixed(2)}</p>
                                                <p>Prev Close: ₹{tickerQuote.prev_close?.toFixed(2)}</p>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                            <div className="flex items-center gap-2 industry-modal-actions">
                                <Button
                                    onClick={handleOpenDetailedAnalysis}
                                    variant="secondary"
                                    size="sm"
                                    disabled={generatingReport}
                                    className="industry-modal-report-btn"
                                >
                                    {generatingReport ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                                    <span>{generatingReport ? 'Generating...' : 'Detailed Analysis'}</span>
                                </Button>
                                <button
                                    onClick={() => watchlist.includes(selectedTicker) ? handleWatchlistRemove(selectedTicker) : handleWatchlistAdd(selectedTicker)}
                                    className={`p-2 rounded-lg transition-colors ${watchlist.includes(selectedTicker) ? 'bg-yellow-500/30 text-yellow-300' : 'bg-white/20 text-white hover:bg-white/30'}`}
                                    title={watchlist.includes(selectedTicker) ? 'Remove from watchlist' : 'Add to watchlist'}
                                >
                                    <Star className={`w-5 h-5 ${watchlist.includes(selectedTicker) ? 'fill-current' : ''}`} />
                                </button>
                                <button onClick={handleCloseModal} className="stock-modal-close-btn" title="Close">
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                        </div>

                        {/* Modal Tabs */}
                        <div className="modal-tabs industry-modal-tabs">
                            {[
                                { id: 'overview', label: 'Overview', icon: <BarChart2 className="w-4 h-4" /> },
                                { id: 'ai', label: 'AI Prediction', icon: <Brain className="w-4 h-4" /> },
                                { id: 'fundamentals', label: 'Fundamentals', icon: <FileText className="w-4 h-4" /> },
                                { id: 'risk', label: 'Risk Analysis', icon: <Shield className="w-4 h-4" /> },
                                { id: 'strategies', label: 'Strategies', icon: <Crosshair className="w-4 h-4" /> }
                            ].map(tab => (
                                <button
                                    key={tab.id}
                                    className={`modal-tab industry-modal-tab ${modalTab === tab.id ? 'active' : ''}`}
                                    onClick={() => {
                                        setModalTab(tab.id);
                                        if (tab.id === 'fundamentals') handleFetchFundamentals();
                                        if (tab.id === 'risk') handleFetchRisk();
                                        if (tab.id === 'strategies') handleFetchStrategies();
                                    }}
                                >
                                    {tab.icon}
                                    <span>{tab.label}</span>
                                </button>
                            ))}
                        </div>

                        {/* Modal Body – scrollable content */}
                        <div className="stock-modal-body reveal-stagger industry-modal-body">

                            {/* ==================== OVERVIEW TAB ==================== */}
                            {modalTab === 'overview' && (
                                <div className="space-y-6 modal-tab-panel modal-panel-overview">
                                    {/* Chart Period Selector */}
                                    <div className="flex gap-2 flex-wrap">
                                        {['1m', '3m', '6m', '1y', 'all'].map(p => (
                                            <button
                                                key={p}
                                                onClick={() => setChartPeriod(p)}
                                                className={`px-4 py-2 rounded-lg text-sm font-semibold transition ${chartPeriod === p ? 'bg-blue-500 text-white' : 'bg-white/10 text-gray-300 hover:bg-white/20'}`}
                                            >
                                                {p.toUpperCase()}
                                            </button>
                                        ))}
                                    </div>

                                    {/* Chart */}
                                    {chartData.length > 0 && (
                                        <Card className="p-4">
                                            <PriceChart data={chartData} />
                                        </Card>
                                    )}

                                    {/* Live Price Card (always visible when quote available) */}
                                    {tickerQuote && (
                                        <Card className="p-4 border border-blue-500/20">
                                            <h4 className="text-sm font-bold text-gray-300 mb-3 flex items-center gap-2">
                                                <span className="live-dot" />
                                                <Activity className="w-4 h-4 text-blue-400" /> Live Market Data
                                                <span className="text-xs text-gray-500 ml-auto">Delayed 10-15 min via yfinance</span>
                                            </h4>
                                            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                                                <div className="bg-white/5 rounded-lg p-3 text-center">
                                                    <p className="text-xs text-gray-400">Live Price</p>
                                                    <p className="text-lg font-bold text-white">₹{tickerQuote.price?.toFixed(2)}</p>
                                                </div>
                                                <div className="bg-white/5 rounded-lg p-3 text-center">
                                                    <p className="text-xs text-gray-400">Day Change</p>
                                                    <p className={`text-lg font-bold ${tickerQuote.change_pct > 0 ? 'text-green-400' : tickerQuote.change_pct < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                                                        {tickerQuote.change_pct > 0 ? '↑' : tickerQuote.change_pct < 0 ? '↓' : '—'} {Math.abs(tickerQuote.change_pct || 0).toFixed(2)}%
                                                    </p>
                                                </div>
                                                <div className="bg-white/5 rounded-lg p-3 text-center">
                                                    <p className="text-xs text-gray-400">Prev Close</p>
                                                    <p className="text-lg font-bold text-gray-300">₹{tickerQuote.prev_close?.toFixed(2) || '—'}</p>
                                                </div>
                                                <div className="bg-white/5 rounded-lg p-3 text-center">
                                                    <p className="text-xs text-gray-400">Day Low</p>
                                                    <p className="text-lg font-bold text-red-400">₹{tickerQuote.day_low?.toFixed(2) || '—'}</p>
                                                </div>
                                                <div className="bg-white/5 rounded-lg p-3 text-center">
                                                    <p className="text-xs text-gray-400">Day High</p>
                                                    <p className="text-lg font-bold text-green-400">₹{tickerQuote.day_high?.toFixed(2) || '—'}</p>
                                                </div>
                                            </div>
                                            {/* Live vs Prediction comparison */}
                                            {prediction && !prediction.error && prediction.predicted_price_5d && (
                                                <div className="mt-3 pt-3 border-t border-white/10">
                                                    <div className="grid grid-cols-3 gap-3 text-center">
                                                        <div>
                                                            <p className="text-xs text-gray-400">Live Price</p>
                                                            <p className="font-bold text-white">₹{tickerQuote.price?.toFixed(2)}</p>
                                                        </div>
                                                        <div>
                                                            <p className="text-xs text-gray-400">AI 5-Day Target</p>
                                                            <p className="font-bold text-blue-400">₹{prediction.predicted_price_5d?.toFixed(2)}</p>
                                                        </div>
                                                        <div>
                                                            <p className="text-xs text-gray-400">Upside from Live</p>
                                                            {(() => {
                                                                const upside = ((prediction.predicted_price_5d - tickerQuote.price) / tickerQuote.price * 100);
                                                                return (
                                                                    <p className={`font-bold ${upside > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                        {upside > 0 ? '+' : ''}{upside.toFixed(2)}%
                                                                    </p>
                                                                );
                                                            })()}
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </Card>
                                    )}

                                    {/* Quick Stats from prediction if available */}
                                    {prediction && !prediction.error && (
                                        <Card className="p-4">
                                            <h4 className="text-sm font-bold text-gray-300 mb-3 flex items-center gap-2">
                                                <Activity className="w-4 h-4 text-blue-400" /> AI Prediction Summary
                                            </h4>
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                                <div className="bg-white/5 rounded-lg p-3 text-center">
                                                    <p className="text-xs text-gray-400">DB Close (Model Input)</p>
                                                    <p className="text-lg font-bold text-white">₹{prediction.current_price?.toFixed(2)}</p>
                                                </div>
                                                <div className="bg-white/5 rounded-lg p-3 text-center">
                                                    <p className="text-xs text-gray-400">Signal</p>
                                                    <p className={`text-lg font-bold ${prediction.signal === 'BUY' ? 'text-green-400' : prediction.signal === 'SELL' ? 'text-red-400' : 'text-yellow-400'}`}>
                                                        {prediction.signal}
                                                    </p>
                                                </div>
                                                <div className="bg-white/5 rounded-lg p-3 text-center">
                                                    <p className="text-xs text-gray-400">5-Day Target</p>
                                                    <p className="text-lg font-bold text-blue-400">₹{prediction.predicted_price_5d?.toFixed(2)}</p>
                                                </div>
                                                <div className="bg-white/5 rounded-lg p-3 text-center">
                                                    <p className="text-xs text-gray-400">Return (from DB close)</p>
                                                    <p className={`text-lg font-bold ${prediction.predicted_return_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                        {prediction.predicted_return_pct > 0 ? '↑' : '↓'} {Math.abs(prediction.predicted_return_pct || 0).toFixed(2)}%
                                                    </p>
                                                </div>
                                            </div>
                                        </Card>
                                    )}

                                    {/* Technical Indicators from prediction */}
                                    {prediction && prediction.technical_indicators && Object.keys(prediction.technical_indicators).length > 0 && (
                                        <div className="analysis-section">
                                            <div className="analysis-section-header">
                                                <Gauge className="w-5 h-5 text-cyan-400" />
                                                <h4>Technical Indicators</h4>
                                            </div>
                                            <div className="analysis-metric-grid">
                                                {Object.entries(prediction.technical_indicators).slice(0, 12).map(([key, val]) => (
                                                    <div key={key} className="analysis-metric">
                                                        <span className="analysis-metric-label">{key.replace(/_/g, ' ')}</span>
                                                        <span className="analysis-metric-value">
                                                            {typeof val === 'number' ? val.toFixed(2) : String(val)}
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Support & Resistance */}
                                    {prediction?.pattern_analysis && (
                                        (prediction.pattern_analysis.support_levels?.length > 0 || prediction.pattern_analysis.resistance_levels?.length > 0) && (
                                            <div className="analysis-section">
                                                <div className="analysis-section-header">
                                                    <Layers className="w-5 h-5 text-blue-400" />
                                                    <h4>Support & Resistance Levels</h4>
                                                </div>
                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4">
                                                        <p className="text-sm font-semibold text-green-400 mb-2">Support</p>
                                                        {(prediction.pattern_analysis.support_levels || []).slice(0, 3).map((lvl, i) => {
                                                            const price = typeof lvl === 'object' ? lvl?.level : lvl;
                                                            const strength = typeof lvl === 'object' ? lvl?.strength : null;
                                                            const distPct = typeof lvl === 'object' ? lvl?.distance_pct : null;
                                                            if (price == null || isNaN(Number(price))) return null;
                                                            return (
                                                                <div key={i} className="flex items-center justify-between mb-1">
                                                                    <span className="text-sm text-green-300 font-bold">₹{Number(price).toFixed(2)}</span>
                                                                    {strength != null && <span className="text-xs text-gray-400">str: {strength}{distPct != null ? ` (${distPct > 0 ? '+' : ''}${Number(distPct).toFixed(1)}%)` : ''}</span>}
                                                                </div>
                                                            );
                                                        })}
                                                        {(prediction.pattern_analysis.support_levels || []).length === 0 && (
                                                            <p className="text-sm text-gray-500">—</p>
                                                        )}
                                                    </div>
                                                    <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
                                                        <p className="text-sm font-semibold text-red-400 mb-2">Resistance</p>
                                                        {(prediction.pattern_analysis.resistance_levels || []).slice(0, 3).map((lvl, i) => {
                                                            const price = typeof lvl === 'object' ? lvl?.level : lvl;
                                                            const strength = typeof lvl === 'object' ? lvl?.strength : null;
                                                            const distPct = typeof lvl === 'object' ? lvl?.distance_pct : null;
                                                            if (price == null || isNaN(Number(price))) return null;
                                                            return (
                                                                <div key={i} className="flex items-center justify-between mb-1">
                                                                    <span className="text-sm text-red-300 font-bold">₹{Number(price).toFixed(2)}</span>
                                                                    {strength != null && <span className="text-xs text-gray-400">str: {strength}{distPct != null ? ` (${distPct > 0 ? '+' : ''}${Number(distPct).toFixed(1)}%)` : ''}</span>}
                                                                </div>
                                                            );
                                                        })}
                                                        {(prediction.pattern_analysis.resistance_levels || []).length === 0 && (
                                                            <p className="text-sm text-gray-500">—</p>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        )
                                    )}

                                    <p className="text-xs text-gray-500 text-center">Switch to the <strong>AI Prediction</strong> tab for detailed prediction analysis</p>
                                </div>
                            )}

                            {/* ==================== AI PREDICTION TAB ==================== */}
                            {modalTab === 'ai' && (
                                <div className="space-y-6 modal-tab-panel modal-panel-ai">
                                    {/* Input Controls Card */}
                                    <Card className="overflow-hidden">
                                        <div className="px-6 py-4 bg-gradient-to-r from-purple-600/20 via-blue-600/15 to-indigo-600/20 border-b border-white/8">
                                            <h3 className="text-lg font-black text-white flex items-center gap-3">
                                                <div className="p-2 bg-purple-500/20 rounded-xl">
                                                    <Brain className="w-6 h-6 text-purple-400" />
                                                </div>
                                                AI Prediction Engine
                                                {tickerQuote && (
                                                    <span className="ml-auto text-[10px] font-semibold px-2.5 py-1 rounded-full bg-green-500/15 text-green-400 border border-green-500/25 flex items-center gap-1.5">
                                                        <span className="live-dot" style={{width:'6px',height:'6px'}} />
                                                        LIVE PRICE: ₹{tickerQuote.price?.toFixed(2)}
                                                    </span>
                                                )}
                                            </h3>
                                        </div>
                                        <div className="p-6">
                                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-5">
                                                <div>
                                                    <label className="text-xs font-bold text-blue-300 block mb-2 uppercase tracking-wider">Capital (₹)</label>
                                                    <input type="number" value={capital} onChange={(e) => setCapital(e.target.value)} className="w-full text-lg" />
                                                </div>
                                                <div>
                                                    <label className="text-xs font-bold text-blue-300 block mb-2 uppercase tracking-wider">Risk (%)</label>
                                                    <input type="number" value={riskPct} onChange={(e) => setRiskPct(e.target.value)} className="w-full text-lg" />
                                                </div>
                                                <Button onClick={handlePrediction} disabled={predicting} variant="purple" size="lg" className="self-end h-[52px]">
                                                    {predicting ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Target className="w-5 h-5" />}
                                                    <span className="font-black">Get AI Prediction</span>
                                                </Button>
                                                <Button onClick={handleTrain} disabled={training} variant="secondary" size="lg" className="self-end h-[52px]">
                                                    {training ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
                                                    <span>{training ? 'Training...' : 'Train Model'}</span>
                                                </Button>
                                            </div>
                                            {trainingMessage && (
                                                <div className="text-sm text-blue-200 bg-blue-500/10 rounded-xl p-3 border border-blue-500/20 flex items-center gap-2">
                                                    <Sparkles className="w-4 h-4 text-blue-400 flex-shrink-0" />
                                                    {trainingMessage}
                                                </div>
                                            )}
                                        </div>
                                    </Card>

                                    {/* Prediction error display */}
                                    {prediction && prediction.error && (
                                        <div className="flex items-center gap-3 p-4 rounded-xl bg-red-500/12 border border-red-500/30">
                                            <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0" />
                                            <p className="text-sm text-red-200 font-medium">{prediction.error}</p>
                                        </div>
                                    )}

                                    {/* Statistical fallback banner */}
                                    {prediction && prediction.prediction_type === 'statistical' && (
                                        <div className="flex items-center gap-3 p-4 rounded-xl bg-yellow-500/12 border border-yellow-500/30">
                                            <AlertTriangle className="w-6 h-6 text-yellow-400 flex-shrink-0" />
                                            <div>
                                                <p className="text-sm font-bold text-yellow-200">Statistical Estimate</p>
                                                <p className="text-xs text-yellow-300/70 mt-0.5">ML model is training. Using SMA/RSI analysis. Predictions will improve after training completes.</p>
                                            </div>
                                        </div>
                                    )}

                                    {/* Prediction Results */}
                                    {prediction && !prediction.error && (
                                        <div ref={predictionResultRef} className="space-y-5">
                                            {/* Signal + Target Hero Card */}
                                            <Card className={`overflow-hidden border-2 ${
                                                prediction.signal === 'BUY' ? 'border-green-500/40' :
                                                prediction.signal === 'SELL' ? 'border-red-500/40' :
                                                'border-yellow-500/40'
                                            }`}>
                                                <div className={`px-6 py-5 ${
                                                    prediction.signal === 'BUY' ? 'bg-gradient-to-r from-green-500/15 to-emerald-500/10' :
                                                    prediction.signal === 'SELL' ? 'bg-gradient-to-r from-red-500/15 to-rose-500/10' :
                                                    'bg-gradient-to-r from-yellow-500/15 to-amber-500/10'
                                                }`}>
                                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                                        {/* Signal */}
                                                        <div className="flex items-center gap-4">
                                                            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${
                                                                prediction.signal === 'BUY' ? 'bg-green-500/20' :
                                                                prediction.signal === 'SELL' ? 'bg-red-500/20' :
                                                                'bg-yellow-500/20'
                                                            }`}>
                                                                <Target className={`w-8 h-8 ${
                                                                    prediction.signal === 'BUY' ? 'text-green-400' :
                                                                    prediction.signal === 'SELL' ? 'text-red-400' :
                                                                    'text-yellow-400'
                                                                }`} />
                                                            </div>
                                                            <div>
                                                                <p className={`text-3xl font-black tracking-tight ${
                                                                    prediction.signal === 'BUY' ? 'text-green-400' :
                                                                    prediction.signal === 'SELL' ? 'text-red-400' :
                                                                    'text-yellow-400'
                                                                }`}>{prediction.signal}</p>
                                                                <div className="flex items-center gap-3 mt-1.5">
                                                                    {/* Confidence gauge */}
                                                                    <div className="flex items-center gap-2">
                                                                        <span className="text-xs text-gray-400 font-medium">Confidence</span>
                                                                        <div className="w-24 bg-gray-700/80 rounded-full h-2.5 overflow-hidden">
                                                                            <div className={`h-full rounded-full transition-all duration-700 ${
                                                                                prediction.prediction_confidence === 'HIGH' ? 'bg-gradient-to-r from-green-500 to-emerald-400 w-full' :
                                                                                prediction.prediction_confidence === 'MEDIUM' ? 'bg-gradient-to-r from-yellow-500 to-amber-400 w-2/3' :
                                                                                'bg-gradient-to-r from-red-500 to-orange-400 w-1/3'
                                                                            }`} />
                                                                        </div>
                                                                        <span className={`text-xs font-black ${
                                                                            prediction.prediction_confidence === 'HIGH' ? 'text-green-400' :
                                                                            prediction.prediction_confidence === 'MEDIUM' ? 'text-yellow-400' :
                                                                            'text-red-400'
                                                                        }`}>{prediction.prediction_confidence}</span>
                                                                    </div>
                                                                    {prediction.prediction_type && (
                                                                        <span className={`text-[10px] px-2.5 py-1 rounded-lg font-bold border ${
                                                                            prediction.prediction_type === 'ml'
                                                                                ? 'bg-purple-500/15 text-purple-300 border-purple-500/25'
                                                                                : 'bg-orange-500/15 text-orange-300 border-orange-500/25'
                                                                        }`}>
                                                                            {prediction.prediction_type === 'ml' ? 'ML Model' : 'Statistical'}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>

                                                        {/* 5-Day Target */}
                                                        <div className="bg-white/8 backdrop-blur-sm rounded-2xl p-5 text-right border border-white/10 min-w-[200px]">
                                                            <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-1">5-Day Target</p>
                                                            <p className="text-3xl font-black text-white">₹{prediction.predicted_price_5d?.toFixed(2)}</p>
                                                            <p className={`text-lg font-bold mt-1 flex items-center gap-1 justify-end ${prediction.predicted_return_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                {prediction.predicted_return_pct > 0 ? <ArrowUpRight className="w-5 h-5" /> : <ArrowDownRight className="w-5 h-5" />}
                                                                {prediction.predicted_return_pct > 0 ? '+' : ''}{Math.abs(prediction.predicted_return_pct || 0).toFixed(2)}%
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </Card>

                                            {/* Price Levels Grid */}
                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                                                <Card className="p-5 flex flex-col items-center justify-center text-center border border-white/5 hover:border-blue-500/25 transition-all duration-200">
                                                    <div className="p-2.5 bg-blue-500/15 rounded-xl mb-3">
                                                        <DollarSign className="w-5 h-5 text-blue-400" />
                                                    </div>
                                                    <p className="text-[11px] text-gray-400 font-semibold mb-2 uppercase tracking-wider">Current Price</p>
                                                    <p className="text-xl font-black text-white leading-none">₹{prediction.current_price?.toFixed(2)}</p>
                                                    {tickerQuote && prediction.current_price !== tickerQuote.price && (
                                                        <p className="text-[10px] text-gray-500 mt-2">Live: ₹{tickerQuote.price?.toFixed(2)}</p>
                                                    )}
                                                </Card>
                                                <Card className="p-5 flex flex-col items-center justify-center text-center border border-white/5 hover:border-red-500/25 transition-all duration-200">
                                                    <div className="p-2.5 bg-red-500/15 rounded-xl mb-3">
                                                        <Shield className="w-5 h-5 text-red-400" />
                                                    </div>
                                                    <p className="text-[11px] text-gray-400 font-semibold mb-2 uppercase tracking-wider">Stop Loss</p>
                                                    <p className="text-xl font-black text-red-400 leading-none">₹{prediction.stop_loss?.toFixed(2)}</p>
                                                    <p className="text-[10px] text-gray-500 mt-2">
                                                        {prediction.current_price && prediction.stop_loss ? `${((prediction.stop_loss - prediction.current_price) / prediction.current_price * 100).toFixed(1)}%` : ''}
                                                    </p>
                                                </Card>
                                                <Card className="p-5 flex flex-col items-center justify-center text-center border border-white/5 hover:border-green-500/25 transition-all duration-200">
                                                    <div className="p-2.5 bg-green-500/15 rounded-xl mb-3">
                                                        <Target className="w-5 h-5 text-green-400" />
                                                    </div>
                                                    <p className="text-[11px] text-gray-400 font-semibold mb-2 uppercase tracking-wider">Target Price</p>
                                                    <p className="text-xl font-black text-green-400 leading-none">₹{prediction.target_price?.toFixed(2)}</p>
                                                    <p className="text-[10px] text-gray-500 mt-2">
                                                        {prediction.current_price && prediction.target_price ? `+${((prediction.target_price - prediction.current_price) / prediction.current_price * 100).toFixed(1)}%` : ''}
                                                    </p>
                                                </Card>
                                                <Card className="p-5 flex flex-col items-center justify-center text-center border border-white/5 hover:border-purple-500/25 transition-all duration-200">
                                                    <div className="p-2.5 bg-purple-500/15 rounded-xl mb-3">
                                                        <Gauge className="w-5 h-5 text-purple-400" />
                                                    </div>
                                                    <p className="text-[11px] text-gray-400 font-semibold mb-2 uppercase tracking-wider">Risk/Reward</p>
                                                    <p className={`text-xl font-black leading-none ${(prediction.risk_reward_ratio || 0) >= 2 ? 'text-green-400' : (prediction.risk_reward_ratio || 0) >= 1 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                        {prediction.risk_reward_ratio?.toFixed(2)}
                                                    </p>
                                                    <p className="text-[10px] text-gray-500 mt-2">
                                                        {(prediction.risk_reward_ratio || 0) >= 2 ? 'Favorable' : (prediction.risk_reward_ratio || 0) >= 1 ? 'Moderate' : 'Unfavorable'}
                                                    </p>
                                                </Card>
                                            </div>

                                            {/* Trade Setup */}
                                            {prediction.suggested_quantity > 0 && (
                                                <Card className="p-6 border border-blue-500/15">
                                                    <h4 className="text-sm font-black text-white mb-4 flex items-center gap-2.5">
                                                        <Briefcase className="w-5 h-5 text-blue-400" />
                                                        Trade Setup
                                                    </h4>
                                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                        <div className="bg-white/5 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                                                            <p className="text-[11px] text-gray-400 mb-2 font-semibold uppercase tracking-wider">Quantity</p>
                                                            <p className="text-lg font-black text-white leading-none">{prediction.suggested_quantity} shares</p>
                                                        </div>
                                                        <div className="bg-white/5 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                                                            <p className="text-[11px] text-gray-400 mb-2 font-semibold uppercase tracking-wider">Investment</p>
                                                            <p className="text-lg font-black text-white leading-none">₹{prediction.trade_value?.toLocaleString()}</p>
                                                        </div>
                                                        <div className="bg-white/5 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                                                            <p className="text-[11px] text-gray-400 mb-2 font-semibold uppercase tracking-wider">Max Loss</p>
                                                            <p className="text-lg font-black text-red-400 leading-none">₹{prediction.max_loss_amount?.toFixed(0)}</p>
                                                        </div>
                                                        <div className="bg-white/5 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                                                            <p className="text-[11px] text-gray-400 mb-2 font-semibold uppercase tracking-wider">Position Size</p>
                                                            <p className="text-lg font-black text-blue-400 leading-none">{prediction.position_pct_of_capital}%</p>
                                                        </div>
                                                    </div>
                                                    {prediction.kelly_fraction_used != null && (
                                                        <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
                                                            <span>Kelly: <strong className="text-gray-400">{prediction.kelly_fraction_used}%</strong></span>
                                                            <span>Method: <strong className="text-gray-400">{prediction.sizing_method || 'ATR-based'}</strong></span>
                                                            <span>Direction Prob: <strong className="text-gray-400">{prediction.direction_probability}%</strong></span>
                                                        </div>
                                                    )}
                                                </Card>
                                            )}

                                            {/* Pattern Analysis */}
                                            {prediction.pattern_analysis && prediction.pattern_analysis.pattern_count > 0 && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <Crosshair className="w-5 h-5 text-purple-400" />
                                                        <h4>Pattern Analysis ({prediction.pattern_analysis.pattern_count} detected)</h4>
                                                    </div>
                                                    <div className="flex flex-wrap gap-2 mb-4">
                                                        {(prediction.pattern_analysis.patterns_detected || []).slice(0, 8).map((p, i) => (
                                                            <span key={i} className="text-xs px-3 py-1.5 rounded-lg bg-purple-500/15 text-purple-200 border border-purple-500/25 font-medium">
                                                                {typeof p === 'string' ? p : p.description || p.name || p.pattern_type?.replace(/_/g, ' ') || p.pattern || 'Pattern'}
                                                                {p.confidence != null && <span className="ml-1 opacity-60">({p.confidence}%)</span>}
                                                            </span>
                                                        ))}
                                                    </div>
                                                    <div className="grid grid-cols-3 gap-4">
                                                        <Card className="p-4 text-center">
                                                            <p className="text-xs text-gray-400 mb-1.5 font-medium">Confluence</p>
                                                            <p className="text-xl font-black text-purple-400">{prediction.pattern_analysis.confluence_score}%</p>
                                                        </Card>
                                                        <Card className="p-4 text-center">
                                                            <p className="text-xs text-gray-400 mb-1.5 font-medium">Agreement</p>
                                                            <p className="text-xl font-black text-purple-400">{prediction.pattern_analysis.pattern_agreement}%</p>
                                                        </Card>
                                                        <Card className="p-4 text-center">
                                                            <p className="text-xs text-gray-400 mb-1.5 font-medium">Trend Strength</p>
                                                            <p className="text-xl font-black text-purple-400">{prediction.pattern_analysis.trend_strength}%</p>
                                                        </Card>
                                                    </div>
                                                    {prediction.pattern_analysis.pattern_summary && (
                                                        <p className="text-xs text-gray-400 mt-3 italic leading-relaxed">{prediction.pattern_analysis.pattern_summary}</p>
                                                    )}
                                                </div>
                                            )}

                                            {/* Support & Resistance + Technical Indicators side by side */}
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                                {/* Support & Resistance */}
                                                {prediction.pattern_analysis && (
                                                    (prediction.pattern_analysis.support_levels?.length > 0 || prediction.pattern_analysis.resistance_levels?.length > 0) && (
                                                        <div className="analysis-section">
                                                            <div className="analysis-section-header">
                                                                <Layers className="w-5 h-5 text-blue-400" />
                                                                <h4>Support & Resistance</h4>
                                                            </div>
                                                            <div className="grid grid-cols-2 gap-3">
                                                                <div className="bg-green-500/8 border border-green-500/15 rounded-xl p-4">
                                                                    <p className="text-sm font-bold text-green-400 mb-2.5 flex items-center gap-1.5">
                                                                        <ArrowDownRight className="w-4 h-4" /> Support
                                                                    </p>
                                                                    {(prediction.pattern_analysis.support_levels || []).filter(lvl => {
                                                                        const v = typeof lvl === 'object' ? lvl?.level : lvl;
                                                                        return v != null && !isNaN(Number(v));
                                                                    }).slice(0, 3).map((lvl, i) => {
                                                                        const price = typeof lvl === 'object' ? lvl?.level : lvl;
                                                                        const strength = typeof lvl === 'object' ? lvl?.strength : null;
                                                                        return (
                                                                            <div key={i} className="flex items-center justify-between mb-2 py-1.5 border-b border-white/5 last:border-b-0">
                                                                                <span className="text-sm text-green-300 font-bold">₹{Number(price).toFixed(2)}</span>
                                                                                {strength != null && <span className="text-[10px] text-gray-500 bg-white/5 px-2 py-0.5 rounded">str: {strength}</span>}
                                                                            </div>
                                                                        );
                                                                    })}
                                                                    {(prediction.pattern_analysis.support_levels || []).filter(lvl => {
                                                                        const v = typeof lvl === 'object' ? lvl?.level : lvl;
                                                                        return v != null && !isNaN(Number(v));
                                                                    }).length === 0 && <p className="text-sm text-gray-500">—</p>}
                                                                </div>
                                                                <div className="bg-red-500/8 border border-red-500/15 rounded-xl p-4">
                                                                    <p className="text-sm font-bold text-red-400 mb-2.5 flex items-center gap-1.5">
                                                                        <ArrowUpRight className="w-4 h-4" /> Resistance
                                                                    </p>
                                                                    {(prediction.pattern_analysis.resistance_levels || []).filter(lvl => {
                                                                        const v = typeof lvl === 'object' ? lvl?.level : lvl;
                                                                        return v != null && !isNaN(Number(v));
                                                                    }).slice(0, 3).map((lvl, i) => {
                                                                        const price = typeof lvl === 'object' ? lvl?.level : lvl;
                                                                        const strength = typeof lvl === 'object' ? lvl?.strength : null;
                                                                        return (
                                                                            <div key={i} className="flex items-center justify-between mb-2 py-1.5 border-b border-white/5 last:border-b-0">
                                                                                <span className="text-sm text-red-300 font-bold">₹{Number(price).toFixed(2)}</span>
                                                                                {strength != null && <span className="text-[10px] text-gray-500 bg-white/5 px-2 py-0.5 rounded">str: {strength}</span>}
                                                                            </div>
                                                                        );
                                                                    })}
                                                                    {(prediction.pattern_analysis.resistance_levels || []).filter(lvl => {
                                                                        const v = typeof lvl === 'object' ? lvl?.level : lvl;
                                                                        return v != null && !isNaN(Number(v));
                                                                    }).length === 0 && <p className="text-sm text-gray-500">—</p>}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    )
                                                )}

                                                {/* Technical Indicators */}
                                                {prediction.technical_indicators && Object.keys(prediction.technical_indicators).length > 0 && (
                                                    <div className="analysis-section">
                                                        <div className="analysis-section-header">
                                                            <Activity className="w-5 h-5 text-cyan-400" />
                                                            <h4>Technical Indicators</h4>
                                                        </div>
                                                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
                                                            {Object.entries(prediction.technical_indicators).slice(0, 9).map(([key, val]) => (
                                                                <div key={key} className="bg-white/4 border border-white/5 rounded-lg px-3 py-2.5">
                                                                    <p className="text-[10px] text-gray-400 truncate font-medium uppercase tracking-wider">{key.replace(/_/g, ' ')}</p>
                                                                    <p className="text-sm font-bold text-white mt-0.5">
                                                                        {typeof val === 'number' ? val.toFixed(2) : String(val)}
                                                                    </p>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Model Performance */}
                                            {prediction.performance_metrics && Object.keys(prediction.performance_metrics).length > 0 && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <Award className="w-5 h-5 text-emerald-400" />
                                                        <h4>Model Performance</h4>
                                                    </div>
                                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                                        {Object.entries(prediction.performance_metrics).slice(0, 8).map(([key, val]) => (
                                                            <Card key={key} className="p-3.5 text-center">
                                                                <p className="text-[10px] text-gray-400 uppercase tracking-wider font-medium mb-1">{key.replace(/_/g, ' ')}</p>
                                                                <p className="text-base font-black text-emerald-400">
                                                                    {typeof val === 'number' ? (val < 1 && val > -1 ? (val * 100).toFixed(1) + '%' : val.toFixed(2)) : String(val)}
                                                                </p>
                                                            </Card>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Risk Disclaimer */}
                                            {prediction.disclaimer && (
                                                <div className="p-4 bg-yellow-500/5 border border-yellow-500/15 rounded-xl">
                                                    <div className="flex items-start gap-3">
                                                        <AlertTriangle className="w-5 h-5 text-yellow-500/70 mt-0.5 flex-shrink-0" />
                                                        <div>
                                                            <p className="text-xs text-yellow-300/60 leading-relaxed">{prediction.disclaimer.text}</p>
                                                            <p className="text-[10px] text-gray-500 mt-1.5 flex flex-wrap gap-3">
                                                                <span>Model v{prediction.model_version}</span>
                                                                <span>Test Accuracy: {prediction.disclaimer.model_accuracy_test}</span>
                                                                <span>{prediction.trade_method || 'ATR-rule-based'}</span>
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ==================== FUNDAMENTALS TAB ==================== */}
                            {modalTab === 'fundamentals' && (
                                <div className="space-y-6 modal-tab-panel modal-panel-fundamentals">
                                    {loadingFundamentals && (
                                        <div className="space-y-4">
                                            <div className="analysis-skeleton" style={{ height: '60px' }}></div>
                                            <div className="analysis-skeleton" style={{ height: '120px' }}></div>
                                            <div className="analysis-skeleton" style={{ height: '80px' }}></div>
                                        </div>
                                    )}

                                    {!loadingFundamentals && !fundamentals && (
                                        <Card className="p-8 text-center industry-empty-card">
                                            <FileText className="w-14 h-14 text-gray-500 mx-auto mb-4" />
                                            <p className="text-gray-200 text-lg font-semibold">Fundamentals are unavailable for {selectedTickerForDisplay}</p>
                                            <p className="text-sm text-gray-400 mt-2 max-w-xl mx-auto">
                                                {fundamentalsError || `Coverage may still be building for this symbol. Retry in a few moments or switch to another ticker.`}
                                            </p>
                                            <Button onClick={handleFetchFundamentals} variant="secondary" className="mt-4" size="lg">
                                                <RefreshCw className="w-5 h-5" /> Retry
                                            </Button>
                                        </Card>
                                    )}

                                    {fundamentals && (
                                        <>
                                            {/* Overall Score Summary */}
                                            {fundamentals.score && (
                                                <Card className="overflow-hidden">
                                                    <div className="px-6 py-4 bg-gradient-to-r from-yellow-600/20 via-amber-600/15 to-orange-600/20 border-b border-white/8">
                                                        <h3 className="text-lg font-black text-white flex items-center gap-3">
                                                            <div className="p-2 bg-yellow-500/20 rounded-xl">
                                                                <Award className="w-6 h-6 text-yellow-400" />
                                                            </div>
                                                            Overall Fundamental Rating
                                                        </h3>
                                                    </div>
                                                    <div className="p-6">
                                                        <div className="flex items-center gap-6 mb-5">
                                                            <div className="score-ring" style={{ '--score-color': fundamentals.score.overall_score >= 60 ? '#4ade80' : fundamentals.score.overall_score >= 40 ? '#facc15' : '#f87171' }}>
                                                                <span className="text-3xl font-black text-white">{fundamentals.score.overall_score}</span>
                                                                <span className="text-xs text-gray-400">/100</span>
                                                            </div>
                                                            <div>
                                                                <p className={`text-xl font-black ${fundamentals.score.rating === 'Strong Buy' || fundamentals.score.rating === 'Buy' ? 'text-green-400' : fundamentals.score.rating === 'Hold' ? 'text-yellow-400' : 'text-red-400'}`}>
                                                                    {fundamentals.score.rating}
                                                                </p>
                                                                <p className="text-sm text-gray-400 mt-0.5">Weighted multi-factor assessment</p>
                                                            </div>
                                                        </div>
                                                        {fundamentals.score.category_scores && (
                                                            <div className="space-y-3">
                                                                {Object.entries(fundamentals.score.category_scores).map(([key, val]) => (
                                                                    <div key={key} className="flex items-center gap-3">
                                                                        <span className="text-xs text-gray-400 font-bold uppercase tracking-wider w-28 flex-shrink-0">{key.replace(/_/g, ' ')}</span>
                                                                        <div className="flex-1 h-3 bg-white/8 rounded-full overflow-hidden">
                                                                            <div className="h-full rounded-full transition-all duration-700" style={{width: `${Math.min(val, 100)}%`, background: val >= 60 ? '#4ade80' : val >= 40 ? '#facc15' : '#f87171'}} />
                                                                        </div>
                                                                        <span className="text-sm font-black text-white w-14 text-right">{val}/100</span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}
                                                        <p className="text-[10px] text-gray-500 mt-4">Weights: Valuation 25% | Profitability 25% | Growth 20% | Financial Health 20% | Dividends 10%</p>
                                                    </div>
                                                </Card>
                                            )}

                                            {/* Piotroski F-Score */}
                                            {fundamentals.piotroski && (
                                                <Card className="overflow-hidden">
                                                    <div className="px-6 py-4 bg-gradient-to-r from-blue-600/20 via-indigo-600/15 to-cyan-600/20 border-b border-white/8">
                                                        <h3 className="text-lg font-black text-white flex items-center gap-3">
                                                            <div className="p-2 bg-blue-500/20 rounded-xl">
                                                                <Gauge className="w-6 h-6 text-blue-400" />
                                                            </div>
                                                            Piotroski F-Score
                                                        </h3>
                                                    </div>
                                                    <div className="p-6">
                                                    {(() => {
                                                        const ps = fundamentals.piotroski.piotroski_score ?? 0;
                                                        const cls = fundamentals.piotroski.classification || (ps >= 7 ? 'Strong' : ps >= 5 ? 'Moderate' : 'Weak');
                                                        return (
                                                            <>
                                                                <div className="flex items-center gap-6 mb-5">
                                                                    <div className="score-ring" style={{ '--score-color': ps >= 7 ? '#4ade80' : ps >= 5 ? '#facc15' : '#f87171' }}>
                                                                        <span className="text-3xl font-black text-white">{ps}</span>
                                                                        <span className="text-xs text-gray-400">/9</span>
                                                                    </div>
                                                                    <div>
                                                                        <p className={`text-xl font-black ${ps >= 7 ? 'text-green-400' : ps >= 5 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                                            {cls}
                                                                        </p>
                                                                        <p className="text-sm text-gray-400 mt-0.5">Financial Health Score</p>
                                                                    </div>
                                                                </div>
                                                                <p className="text-xs text-gray-400 mb-4 leading-relaxed bg-white/3 rounded-xl p-3 border border-white/5">
                                                                    The Piotroski F-Score (0-9) measures financial strength using 9 accounting criteria. 
                                                                    <span className="text-green-400 font-bold"> 7-9 = Strong</span> (high-quality fundamentals), 
                                                                    <span className="text-yellow-400 font-bold"> 4-6 = Moderate</span> (mixed signals), 
                                                                    <span className="text-red-400 font-bold"> 0-3 = Weak</span> (potential red flags).
                                                                </p>
                                                            </>
                                                        );
                                                    })()}
                                                    {fundamentals.piotroski.details && (
                                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                                            {Object.entries(fundamentals.piotroski.details).map(([key, val]) => {
                                                                const explanations = {
                                                                    positive_roa: 'Return on Assets > 0 indicates profitable use of company assets',
                                                                    positive_ocf: 'Positive operating cash flow shows the business generates real cash',
                                                                    increasing_roa: 'Year-over-year ROA improvement signals growing efficiency',
                                                                    quality_earnings: 'Cash flow exceeds net income — earnings are backed by real cash',
                                                                    low_leverage: 'Debt-to-equity below 100% — manageable debt levels',
                                                                    adequate_liquidity: 'Current ratio > 1 means the company can cover short-term obligations',
                                                                    no_dilution: 'No new share issuance — existing shareholders are not being diluted',
                                                                    good_margin: 'Gross margin > 20% indicates healthy pricing power',
                                                                    good_turnover: 'Asset turnover > 0.5 shows efficient revenue generation from assets',
                                                                };
                                                                return (
                                                                    <div key={key} className={`p-3.5 rounded-xl border ${val ? 'bg-green-500/6 border-green-500/20' : 'bg-red-500/6 border-red-500/20'}`} title={explanations[key] || ''}>
                                                                        <div className="flex items-center gap-2.5 mb-1.5">
                                                                            <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm font-black ${val ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                                                                {val ? '✓' : '✗'}
                                                                            </div>
                                                                            <span className="text-sm font-bold text-white capitalize">{key.replace(/_/g, ' ')}</span>
                                                                        </div>
                                                                        <p className="text-[10px] text-gray-500 leading-relaxed pl-[38px]">{explanations[key] || ''}</p>
                                                                    </div>
                                                                );
                                                            })}
                                                        </div>
                                                    )}
                                                    </div>
                                                </Card>
                                            )}

                                            {/* Valuation Metrics */}
                                            {fundamentals.data?.valuation && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <TrendingUp className="w-5 h-5 text-purple-400" />
                                                        <h4>Valuation</h4>
                                                    </div>
                                                    <p className="text-xs text-gray-400 mb-3">How the stock is priced relative to its earnings, book value, and revenue. Lower ratios may suggest undervaluation.</p>
                                                    <div className="analysis-metric-grid">
                                                        {(() => {
                                                            const v = fundamentals.data.valuation;
                                                            const items = [
                                                                { key: 'P/E Ratio', val: v.pe_ratio, tip: v.pe_ratio != null ? (v.pe_ratio < 15 ? 'Undervalued' : v.pe_ratio < 25 ? 'Fair' : 'Expensive') : null },
                                                                { key: 'Forward P/E', val: v.forward_pe, tip: null },
                                                                { key: 'P/B Ratio', val: v.pb_ratio, tip: v.pb_ratio != null ? (v.pb_ratio < 1.5 ? 'Below book value' : v.pb_ratio < 3 ? 'Fair' : 'Premium') : null },
                                                                { key: 'P/S Ratio', val: v.ps_ratio, tip: null },
                                                                { key: 'PEG Ratio', val: v.peg_ratio, tip: v.peg_ratio != null ? (v.peg_ratio < 1 ? 'Growth at discount' : v.peg_ratio < 2 ? 'Fairly priced' : 'Overpriced for growth') : null },
                                                                { key: 'EV/Revenue', val: v.ev_revenue, tip: null },
                                                                { key: 'EV/EBITDA', val: v.ev_ebitda, tip: v.ev_ebitda != null ? (v.ev_ebitda < 10 ? 'Attractive' : v.ev_ebitda < 20 ? 'Moderate' : 'Expensive') : null },
                                                                { key: 'Market Cap', val: v.market_cap, fmt: 'currency' },
                                                            ];
                                                            return items.filter(i => i.val != null).map(item => (
                                                                <div key={item.key} className="analysis-metric">
                                                                    <span className="analysis-metric-label">{item.key}</span>
                                                                    <span className="analysis-metric-value">
                                                                        {item.fmt === 'currency' ? `₹${(item.val / 10000000).toFixed(2)} Cr` : item.val.toFixed(2)}
                                                                    </span>
                                                                    {item.tip && <span className={`text-[10px] mt-0.5 block ${item.tip.includes('Under') || item.tip.includes('Attractive') || item.tip.includes('discount') ? 'text-green-400/70' : item.tip.includes('Expensive') || item.tip.includes('Over') || item.tip.includes('Premium') ? 'text-red-400/70' : 'text-yellow-400/70'}`}>{item.tip}</span>}
                                                                </div>
                                                            ));
                                                        })()}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Profitability */}
                                            {fundamentals.data?.profitability && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <DollarSign className="w-5 h-5 text-green-400" />
                                                        <h4>Profitability</h4>
                                                    </div>
                                                    <p className="text-xs text-gray-400 mb-3">How efficiently the company converts revenue into profit and uses shareholder equity.</p>
                                                    <div className="analysis-metric-grid">
                                                        {(() => {
                                                            const p = fundamentals.data.profitability;
                                                            const items = [
                                                                { key: 'Profit Margin', val: p.profit_margin, pct: true, tip: p.profit_margin != null ? (p.profit_margin > 0.15 ? 'Excellent' : p.profit_margin > 0.05 ? 'Healthy' : 'Low') : null },
                                                                { key: 'Operating Margin', val: p.operating_margin, pct: true },
                                                                { key: 'Gross Margin', val: p.gross_margin, pct: true, tip: p.gross_margin != null ? (p.gross_margin > 0.4 ? 'Strong pricing power' : p.gross_margin > 0.2 ? 'Adequate' : 'Thin margins') : null },
                                                                { key: 'ROE', val: p.roe, pct: true, tip: p.roe != null ? (p.roe > 0.15 ? 'Excellent shareholder returns' : p.roe > 0.08 ? 'Acceptable' : 'Below average') : null },
                                                                { key: 'ROA', val: p.roa, pct: true, tip: p.roa != null ? (p.roa > 0.1 ? 'Efficient asset use' : p.roa > 0.03 ? 'Average' : 'Poor asset utilization') : null },
                                                                { key: 'EBITDA Margin', val: p.ebitda_margin, pct: true },
                                                            ];
                                                            return items.filter(i => i.val != null).map(item => (
                                                                <div key={item.key} className="analysis-metric">
                                                                    <span className="analysis-metric-label">{item.key}</span>
                                                                    <span className="analysis-metric-value">{(item.val * 100).toFixed(1)}%</span>
                                                                    {item.tip && <span className={`text-[10px] mt-0.5 block ${item.tip.includes('Excellent') || item.tip.includes('Strong') || item.tip.includes('Efficient') ? 'text-green-400/70' : item.tip.includes('Low') || item.tip.includes('Thin') || item.tip.includes('Poor') || item.tip.includes('Below') ? 'text-red-400/70' : 'text-yellow-400/70'}`}>{item.tip}</span>}
                                                                </div>
                                                            ));
                                                        })()}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Financial Health */}
                                            {fundamentals.data?.financial_health && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <Shield className="w-5 h-5 text-cyan-400" />
                                                        <h4>Financial Health</h4>
                                                    </div>
                                                    <p className="text-xs text-gray-400 mb-3">Balance sheet strength — debt levels, liquidity, and cash position.</p>
                                                    <div className="analysis-metric-grid">
                                                        {(() => {
                                                            const h = fundamentals.data.financial_health;
                                                            const items = [
                                                                { key: 'Debt/Equity', val: h.debt_to_equity, tip: h.debt_to_equity != null ? (h.debt_to_equity < 50 ? 'Low debt' : h.debt_to_equity < 100 ? 'Moderate debt' : 'High leverage') : null },
                                                                { key: 'Current Ratio', val: h.current_ratio, tip: h.current_ratio != null ? (h.current_ratio > 2 ? 'Very liquid' : h.current_ratio > 1 ? 'Adequate' : 'Liquidity risk') : null },
                                                                { key: 'Quick Ratio', val: h.quick_ratio },
                                                                { key: 'Total Debt', val: h.total_debt, fmt: 'currency' },
                                                                { key: 'Total Cash', val: h.total_cash, fmt: 'currency' },
                                                                { key: 'Free Cash Flow', val: h.free_cash_flow, fmt: 'currency', tip: h.free_cash_flow != null ? (h.free_cash_flow > 0 ? 'Positive FCF' : 'Negative FCF — cash burn') : null },
                                                            ];
                                                            return items.filter(i => i.val != null).map(item => (
                                                                <div key={item.key} className="analysis-metric">
                                                                    <span className="analysis-metric-label">{item.key}</span>
                                                                    <span className="analysis-metric-value">
                                                                        {item.fmt === 'currency' ? `₹${(item.val / 10000000).toFixed(2)} Cr` : item.val.toFixed(2)}
                                                                    </span>
                                                                    {item.tip && <span className={`text-[10px] mt-0.5 block ${item.tip.includes('Low') || item.tip.includes('liquid') || item.tip.includes('Positive') ? 'text-green-400/70' : item.tip.includes('High') || item.tip.includes('risk') || item.tip.includes('burn') ? 'text-red-400/70' : 'text-yellow-400/70'}`}>{item.tip}</span>}
                                                                </div>
                                                            ));
                                                        })()}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Growth */}
                                            {fundamentals.data?.growth && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <TrendingUp className="w-5 h-5 text-emerald-400" />
                                                        <h4>Growth</h4>
                                                    </div>
                                                    <div className="analysis-metric-grid">
                                                        {(() => {
                                                            const g = fundamentals.data.growth;
                                                            const items = [
                                                                { key: 'Revenue Growth', val: g.revenue_growth, pct: true, tip: g.revenue_growth != null ? (g.revenue_growth > 0.2 ? 'High growth' : g.revenue_growth > 0.05 ? 'Steady growth' : g.revenue_growth > 0 ? 'Slow growth' : 'Declining') : null },
                                                                { key: 'Earnings Growth', val: g.earnings_growth, pct: true },
                                                                { key: 'Quarterly Rev. Growth', val: g.quarterly_revenue_growth, pct: true },
                                                                { key: 'Quarterly Earn. Growth', val: g.quarterly_earnings_growth, pct: true },
                                                            ];
                                                            return items.filter(i => i.val != null).map(item => (
                                                                <div key={item.key} className="analysis-metric">
                                                                    <span className="analysis-metric-label">{item.key}</span>
                                                                    <span className={`analysis-metric-value ${item.val > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                        {item.val > 0 ? '+' : ''}{(item.val * 100).toFixed(1)}%
                                                                    </span>
                                                                    {item.tip && <span className={`text-[10px] mt-0.5 block ${item.tip.includes('High') || item.tip.includes('Steady') ? 'text-green-400/70' : item.tip.includes('Declining') ? 'text-red-400/70' : 'text-yellow-400/70'}`}>{item.tip}</span>}
                                                                </div>
                                                            ));
                                                        })()}
                                                    </div>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            )}

                            {/* ==================== RISK ANALYSIS TAB ==================== */}
                            {modalTab === 'risk' && (
                                <div className="space-y-6 modal-tab-panel modal-panel-risk">
                                    {loadingRisk && (
                                        <div className="space-y-4">
                                            <div className="analysis-skeleton" style={{ height: '60px' }}></div>
                                            <div className="analysis-skeleton" style={{ height: '120px' }}></div>
                                        </div>
                                    )}

                                    {!loadingRisk && !riskMetrics && (
                                        <Card className="p-8 text-center industry-empty-card">
                                            <Shield className="w-14 h-14 text-gray-500 mx-auto mb-4" />
                                            <p className="text-gray-200 text-lg font-semibold">Risk analytics are unavailable for {selectedTickerForDisplay}</p>
                                            <p className="text-sm text-gray-400 mt-2 max-w-xl mx-auto">
                                                {riskError || `This symbol may have incomplete risk history for the selected period. Retry or open another ticker.`}
                                            </p>
                                            <Button onClick={handleFetchRisk} variant="secondary" className="mt-4" size="lg">
                                                <RefreshCw className="w-5 h-5" /> Retry
                                            </Button>
                                        </Card>
                                    )}

                                    {riskMetrics && (
                                        <>
                                            {/* Risk Overview Hero */}
                                            {(() => {
                                                const m = riskMetrics.metrics || {};
                                                const vol = m.annualized_volatility;
                                                const riskLevel = vol != null ? (vol > 40 ? 'HIGH' : vol > 20 ? 'MEDIUM' : 'LOW') : null;
                                                return (
                                                    <Card className="overflow-hidden">
                                                        <div className={`px-6 py-4 border-b border-white/8 ${
                                                            riskLevel === 'HIGH' ? 'bg-gradient-to-r from-red-600/20 via-orange-600/15 to-red-600/20' :
                                                            riskLevel === 'MEDIUM' ? 'bg-gradient-to-r from-yellow-600/20 via-amber-600/15 to-yellow-600/20' :
                                                            'bg-gradient-to-r from-green-600/20 via-emerald-600/15 to-green-600/20'
                                                        }`}>
                                                            <h3 className="text-lg font-black text-white flex items-center gap-3">
                                                                <div className="p-2 bg-orange-500/20 rounded-xl">
                                                                    <Shield className="w-6 h-6 text-orange-400" />
                                                                </div>
                                                                Risk Profile
                                                                {riskLevel && (
                                                                    <span className={`ml-auto risk-badge ${riskLevel === 'LOW' ? 'risk-low' : riskLevel === 'MEDIUM' ? 'risk-medium' : 'risk-high'}`}>
                                                                        {riskLevel} RISK
                                                                    </span>
                                                                )}
                                                            </h3>
                                                        </div>
                                                        <div className="p-6">
                                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                                                {vol != null && (
                                                                    <div className="bg-white/5 rounded-xl p-5 text-center border border-white/5 hover:border-orange-500/20 transition-colors">
                                                                        <div className="p-2 bg-orange-500/15 rounded-xl w-fit mx-auto mb-3">
                                                                            <Activity className="w-5 h-5 text-orange-400" />
                                                                        </div>
                                                                        <p className="text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wider">Ann. Volatility</p>
                                                                        <p className="text-2xl font-black text-orange-400">{vol.toFixed(1)}%</p>
                                                                        <p className="text-[10px] text-gray-500 mt-1.5">{vol > 40 ? 'Very volatile' : vol > 25 ? 'Above average' : vol > 15 ? 'Moderate' : 'Low risk'}</p>
                                                                    </div>
                                                                )}
                                                                {m.sharpe_ratio != null && (
                                                                    <div className="bg-white/5 rounded-xl p-5 text-center border border-white/5 hover:border-blue-500/20 transition-colors">
                                                                        <div className="p-2 bg-blue-500/15 rounded-xl w-fit mx-auto mb-3">
                                                                            <Target className="w-5 h-5 text-blue-400" />
                                                                        </div>
                                                                        <p className="text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wider">Sharpe Ratio</p>
                                                                        <p className={`text-2xl font-black ${m.sharpe_ratio > 1 ? 'text-green-400' : m.sharpe_ratio > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                                            {m.sharpe_ratio.toFixed(2)}
                                                                        </p>
                                                                        <p className="text-[10px] text-gray-500 mt-1.5">{m.sharpe_ratio > 2 ? 'Excellent risk-adjusted' : m.sharpe_ratio > 1 ? 'Good return/risk' : m.sharpe_ratio > 0 ? 'Positive but low' : 'Negative returns'}</p>
                                                                    </div>
                                                                )}
                                                                {m.var_95_historical != null && (
                                                                    <div className="bg-white/5 rounded-xl p-5 text-center border border-white/5 hover:border-red-500/20 transition-colors">
                                                                        <div className="p-2 bg-red-500/15 rounded-xl w-fit mx-auto mb-3">
                                                                            <AlertTriangle className="w-5 h-5 text-red-400" />
                                                                        </div>
                                                                        <p className="text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wider">VaR (95%)</p>
                                                                        <p className="text-2xl font-black text-red-400">{m.var_95_historical.toFixed(2)}%</p>
                                                                        <p className="text-[10px] text-gray-500 mt-1.5">Max daily loss in 95% of cases</p>
                                                                    </div>
                                                                )}
                                                                {m.max_drawdown != null && (
                                                                    <div className="bg-white/5 rounded-xl p-5 text-center border border-white/5 hover:border-red-500/20 transition-colors">
                                                                        <div className="p-2 bg-red-500/15 rounded-xl w-fit mx-auto mb-3">
                                                                            <TrendingDown className="w-5 h-5 text-red-400" />
                                                                        </div>
                                                                        <p className="text-xs text-gray-400 mb-1.5 font-medium uppercase tracking-wider">Max Drawdown</p>
                                                                        <p className="text-2xl font-black text-red-400">{m.max_drawdown.toFixed(1)}%</p>
                                                                        <p className="text-[10px] text-gray-500 mt-1.5">Largest peak-to-trough decline</p>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </Card>
                                                );
                                            })()}

                                            {/* Return Metrics */}
                                            {riskMetrics.metrics && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <TrendingUp className="w-5 h-5 text-green-400" />
                                                        <h4>Return Metrics</h4>
                                                    </div>
                                                    <p className="text-xs text-gray-400 mb-3">Historical return performance over the analysis period.</p>
                                                    <div className="analysis-metric-grid">
                                                        {(() => {
                                                            const m = riskMetrics.metrics;
                                                            const items = [
                                                                { key: 'Annualized Return', val: m.annualized_return, unit: '%' },
                                                                { key: 'Total Return', val: m.total_return, unit: '%' },
                                                                { key: 'CAGR', val: m.cagr, unit: '%', tip: 'Compound annual growth rate' },
                                                                { key: 'Best Day', val: m.best_day, unit: '%' },
                                                                { key: 'Worst Day', val: m.worst_day, unit: '%' },
                                                                { key: 'Win Rate', val: m.win_rate, unit: '%', tip: 'Percentage of positive months' },
                                                                { key: 'Positive Days', val: m.positive_days_pct, unit: '%' },
                                                            ];
                                                            return items.filter(i => i.val != null).map(item => (
                                                                <div key={item.key} className="analysis-metric">
                                                                    <span className="analysis-metric-label">{item.key}</span>
                                                                    <span className={`analysis-metric-value ${item.val > 0 ? 'text-green-400' : item.val < 0 ? 'text-red-400' : ''}`}>
                                                                        {item.val > 0 ? '+' : ''}{typeof item.val === 'number' ? item.val.toFixed(2) : item.val}{item.unit}
                                                                    </span>
                                                                    {item.tip && <span className="text-[10px] text-gray-500 mt-0.5 block">{item.tip}</span>}
                                                                </div>
                                                            ));
                                                        })()}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Risk-Adjusted & Volatility Metrics */}
                                            {riskMetrics.metrics && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <Activity className="w-5 h-5 text-cyan-400" />
                                                        <h4>Risk-Adjusted Performance</h4>
                                                    </div>
                                                    <p className="text-xs text-gray-400 mb-3">How well the stock compensates investors for the risk taken.</p>
                                                    <div className="analysis-metric-grid">
                                                        {(() => {
                                                            const m = riskMetrics.metrics;
                                                            const items = [
                                                                { key: 'Sharpe Ratio', val: m.sharpe_ratio, tip: m.sharpe_ratio != null ? (m.sharpe_ratio > 1 ? 'Good — return exceeds risk' : m.sharpe_ratio > 0 ? 'Positive but modest' : 'Negative — risk not rewarded') : null },
                                                                { key: 'Sortino Ratio', val: m.sortino_ratio, tip: 'Like Sharpe but only penalizes downside volatility' },
                                                                { key: 'Calmar Ratio', val: m.calmar_ratio, tip: 'Return relative to max drawdown risk' },
                                                                { key: 'Beta', val: m.beta, tip: m.beta != null ? (Math.abs(m.beta) > 1.2 ? 'More volatile than market' : Math.abs(m.beta) < 0.8 ? 'Less volatile than market' : 'Moves with market') : null },
                                                                { key: 'Alpha', val: m.alpha, unit: '%', tip: 'Excess return vs benchmark after adjusting for risk' },
                                                                { key: 'Treynor Ratio', val: m.treynor_ratio, tip: 'Excess return per unit of systematic risk' },
                                                                { key: 'Information Ratio', val: m.information_ratio, tip: m.information_ratio != null ? (m.information_ratio > 0.5 ? 'Consistently beats benchmark' : 'Low active return consistency') : null },
                                                                { key: 'R-Squared', val: m.r_squared, unit: '%', tip: 'How much the stock follows the benchmark' },
                                                            ];
                                                            return items.filter(i => i.val != null).map(item => (
                                                                <div key={item.key} className="analysis-metric">
                                                                    <span className="analysis-metric-label">{item.key}</span>
                                                                    <span className={`analysis-metric-value ${item.key === 'Alpha' ? (item.val > 0 ? 'text-green-400' : 'text-red-400') : ''}`}>
                                                                        {typeof item.val === 'number' ? item.val.toFixed(3) : item.val}{item.unit || ''}
                                                                    </span>
                                                                    {item.tip && <span className="text-[10px] text-gray-500 mt-0.5 block">{item.tip}</span>}
                                                                </div>
                                                            ));
                                                        })()}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Volatility Breakdown */}
                                            {riskMetrics.metrics && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <Activity className="w-5 h-5 text-orange-400" />
                                                        <h4>Volatility & Tail Risk</h4>
                                                    </div>
                                                    <p className="text-xs text-gray-400 mb-3">Measures of price variability and extreme event risk.</p>
                                                    <div className="analysis-metric-grid">
                                                        {(() => {
                                                            const m = riskMetrics.metrics;
                                                            const items = [
                                                                { key: 'Daily Volatility', val: m.daily_volatility, unit: '%' },
                                                                { key: 'Ann. Volatility', val: m.annualized_volatility, unit: '%' },
                                                                { key: '20-Day Volatility', val: m.volatility_20d, unit: '%', tip: 'Short-term volatility' },
                                                                { key: '60-Day Volatility', val: m.volatility_60d, unit: '%', tip: 'Medium-term volatility' },
                                                                { key: 'Downside Vol.', val: m.downside_volatility, unit: '%', tip: 'Volatility of negative returns only' },
                                                                { key: 'Upside/Downside', val: m.upside_downside_ratio, tip: m.upside_downside_ratio != null ? (m.upside_downside_ratio > 1 ? 'More upside variability — favorable' : 'More downside variability — unfavorable') : null },
                                                                { key: 'Skewness', val: m.skewness, tip: m.skewness != null ? (m.skewness > 0 ? 'Positive skew — more extreme gains' : 'Negative skew — more extreme losses') : null },
                                                                { key: 'Kurtosis', val: m.kurtosis, tip: m.kurtosis != null ? (m.kurtosis > 3 ? 'Fat tails — higher chance of extreme moves' : 'Normal distribution — predictable') : null },
                                                            ];
                                                            return items.filter(i => i.val != null).map(item => (
                                                                <div key={item.key} className="analysis-metric">
                                                                    <span className="analysis-metric-label">{item.key}</span>
                                                                    <span className="analysis-metric-value">{typeof item.val === 'number' ? item.val.toFixed(2) : item.val}{item.unit || ''}</span>
                                                                    {item.tip && <span className="text-[10px] text-gray-500 mt-0.5 block">{item.tip}</span>}
                                                                </div>
                                                            ));
                                                        })()}
                                                    </div>
                                                </div>
                                            )}

                                            {/* Drawdown & VaR Analysis */}
                                            {riskMetrics.metrics && (
                                                <div className="analysis-section">
                                                    <div className="analysis-section-header">
                                                        <TrendingDown className="w-5 h-5 text-red-400" />
                                                        <h4>Drawdown & Value-at-Risk</h4>
                                                    </div>
                                                    <p className="text-xs text-gray-400 mb-3">Worst-case scenarios and potential loss estimates.</p>
                                                    <div className="analysis-metric-grid">
                                                        {(() => {
                                                            const m = riskMetrics.metrics;
                                                            const items = [
                                                                { key: 'Max Drawdown', val: m.max_drawdown, unit: '%', tip: 'Largest peak-to-trough decline' },
                                                                { key: 'Current Drawdown', val: m.current_drawdown, unit: '%', tip: 'Current distance from all-time high' },
                                                                { key: 'Max DD Duration', val: m.max_drawdown_duration, unit: ' days', tip: 'Longest drawdown period' },
                                                                { key: 'Recovery Days', val: m.recovery_days, unit: ' days', tip: 'Days to recover from max drawdown' },
                                                                { key: 'VaR 95% (Hist)', val: m.var_95_historical, unit: '%', tip: 'Expected maximum daily loss with 95% confidence' },
                                                                { key: 'VaR 99% (Hist)', val: m.var_99_historical, unit: '%', tip: 'Expected maximum daily loss with 99% confidence' },
                                                                { key: 'CVaR 95%', val: m.cvar_95, unit: '%', tip: 'Average loss in worst 5% of days (Expected Shortfall)' },
                                                                { key: 'CVaR 99%', val: m.cvar_99, unit: '%', tip: 'Average loss in worst 1% of days' },
                                                            ];
                                                            return items.filter(i => i.val != null).map(item => (
                                                                <div key={item.key} className="analysis-metric">
                                                                    <span className="analysis-metric-label">{item.key}</span>
                                                                    <span className="analysis-metric-value text-red-400">
                                                                        {typeof item.val === 'number' ? item.val.toFixed(2) : item.val}{item.unit}
                                                                    </span>
                                                                    {item.tip && <span className="text-[10px] text-gray-500 mt-0.5 block">{item.tip}</span>}
                                                                </div>
                                                            ));
                                                        })()}
                                                    </div>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            )}

                            {/* ==================== STRATEGIES TAB ==================== */}
                            {modalTab === 'strategies' && (
                                <div className="space-y-6 modal-tab-panel modal-panel-strategies">
                                    {loadingStrategies && (
                                        <div className="space-y-4">
                                            <div className="analysis-skeleton" style={{ height: '60px' }}></div>
                                            <div className="analysis-skeleton" style={{ height: '200px' }}></div>
                                        </div>
                                    )}

                                    {!loadingStrategies && !strategyEval && (
                                        <Card className="p-8 text-center industry-empty-card">
                                            <Crosshair className="w-14 h-14 text-gray-500 mx-auto mb-4" />
                                            <p className="text-gray-200 text-lg font-semibold">Strategy evaluation is unavailable for {selectedTickerForDisplay}</p>
                                            <p className="text-sm text-gray-400 mt-2 max-w-xl mx-auto">
                                                {strategiesError || `No strategy output was returned for this symbol. Retry or choose a different ticker.`}
                                            </p>
                                            <Button onClick={handleFetchStrategies} variant="secondary" className="mt-4" size="lg">
                                                <RefreshCw className="w-5 h-5" /> Retry
                                            </Button>
                                        </Card>
                                    )}

                                    {strategyEval && (
                                        <>
                                            {/* Strategy Summary Hero */}
                                            <Card className="overflow-hidden">
                                                <div className="px-6 py-4 bg-gradient-to-r from-indigo-600/20 via-purple-600/15 to-violet-600/20 border-b border-white/8">
                                                    <h3 className="text-lg font-black text-white flex items-center gap-3">
                                                        <div className="p-2.5 bg-indigo-500/20 rounded-xl">
                                                            <Crosshair className="w-6 h-6 text-indigo-400" />
                                                        </div>
                                                        Multi-Strategy Evaluation
                                                    </h3>
                                                </div>
                                                <div className="p-6">
                                                    <p className="text-xs text-gray-400 mb-5 leading-relaxed bg-white/3 rounded-xl p-4 border border-white/5 text-center">
                                                        Committee-of-Experts approach: {strategyEval.strategies_evaluated || 0} independent technical strategies are evaluated. 
                                                        Strategies with ≥60% confidence are considered passing.
                                                    </p>

                                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                                                        <div className="bg-green-500/8 border border-green-500/20 rounded-xl p-5 flex flex-col items-center justify-center text-center">
                                                            <div className="p-2.5 bg-green-500/15 rounded-xl mb-3">
                                                                <ArrowUpRight className="w-5 h-5 text-green-400" />
                                                            </div>
                                                            <p className="text-[11px] text-gray-400 mb-1.5 font-semibold uppercase tracking-wider">Passing</p>
                                                            <p className="text-3xl font-black text-green-400 leading-none">{strategyEval.strategies_passing || 0}</p>
                                                            <p className="text-[10px] text-gray-500 mt-1.5">out of {strategyEval.strategies_evaluated || 0}</p>
                                                        </div>
                                                        <div className="bg-red-500/8 border border-red-500/20 rounded-xl p-5 flex flex-col items-center justify-center text-center">
                                                            <div className="p-2.5 bg-red-500/15 rounded-xl mb-3">
                                                                <ArrowDownRight className="w-5 h-5 text-red-400" />
                                                            </div>
                                                            <p className="text-[11px] text-gray-400 mb-1.5 font-semibold uppercase tracking-wider">Failing</p>
                                                            <p className="text-3xl font-black text-red-400 leading-none">{(strategyEval.strategies_evaluated || 0) - (strategyEval.strategies_passing || 0)}</p>
                                                            <p className="text-[10px] text-gray-500 mt-1.5">below 60% threshold</p>
                                                        </div>
                                                        <div className="bg-blue-500/8 border border-blue-500/20 rounded-xl p-5 flex flex-col items-center justify-center text-center">
                                                            <div className="p-2.5 bg-blue-500/15 rounded-xl mb-3">
                                                                <Gauge className="w-5 h-5 text-blue-400" />
                                                            </div>
                                                            <p className="text-[11px] text-gray-400 mb-1.5 font-semibold uppercase tracking-wider">Avg Confidence</p>
                                                            <p className="text-3xl font-black text-blue-400 leading-none">{strategyEval.avg_confidence?.toFixed(0) || 0}%</p>
                                                            <p className="text-[10px] text-gray-500 mt-1.5">of passing strategies</p>
                                                        </div>
                                                        <div className="bg-purple-500/8 border border-purple-500/20 rounded-xl p-5 flex flex-col items-center justify-center text-center">
                                                            <div className="p-2.5 bg-purple-500/15 rounded-xl mb-3">
                                                                <Award className="w-5 h-5 text-purple-400" />
                                                            </div>
                                                            <p className="text-[11px] text-gray-400 mb-1.5 font-semibold uppercase tracking-wider">Best Strategy</p>
                                                            <p className="text-sm font-black text-purple-400 truncate mt-1 leading-tight">{(strategyEval.best_strategy || '—').replace(/_/g, ' ')}</p>
                                                            <p className="text-[10px] text-gray-500 mt-1.5">{strategyEval.max_confidence?.toFixed(0) || 0}% confidence</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </Card>

                                            {/* Individual Strategy Results */}
                                            {strategyEval.all_results && strategyEval.all_results.length > 0 && (
                                                <Card className="p-6">
                                                    <h4 className="text-sm font-black text-white mb-2 flex items-center gap-2">
                                                        <Activity className="w-5 h-5 text-cyan-400" />
                                                        Strategy Breakdown
                                                    </h4>
                                                    <p className="text-xs text-gray-400 mb-5">Each strategy evaluates specific technical indicators. Confidence shows weighted score of rules passed.</p>
                                                    <div className="space-y-3">
                                                        {strategyEval.all_results.map((strat, i) => {
                                                            const isPassing = (strat.confidence || 0) >= 60;
                                                            return (
                                                                <div key={i} className={`flex items-center justify-between p-4 rounded-xl border transition-all hover:scale-[1.003] ${isPassing ? 'bg-green-500/5 border-green-500/20 hover:border-green-500/35' : 'bg-red-500/5 border-red-500/20 hover:border-red-500/35'}`}>
                                                                    <div className="flex items-center gap-3.5">
                                                                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-base font-black flex-shrink-0 ${isPassing ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                                                            {isPassing ? '✓' : '✗'}
                                                                        </div>
                                                                        <div>
                                                                            <p className="text-sm font-bold text-white leading-tight">{(strat.strategy || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</p>
                                                                            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                                                                                {strat.category && <span className="text-[10px] text-gray-400 bg-white/6 px-2.5 py-1 rounded-md font-semibold">{strat.category}</span>}
                                                                                {strat.risk_level && <span className="text-[10px] text-gray-400 bg-white/6 px-2.5 py-1 rounded-md font-semibold">{strat.risk_level} risk</span>}
                                                                                {strat.timeframe && <span className="text-[10px] text-gray-400 bg-white/6 px-2.5 py-1 rounded-md font-semibold">{strat.timeframe}</span>}
                                                                            </div>
                                                                            {strat.description && <p className="text-[10px] text-gray-500 mt-1.5 leading-relaxed max-w-md">{strat.description}</p>}
                                                                        </div>
                                                                    </div>
                                                                    <div className="text-right flex-shrink-0 ml-6 flex flex-col items-center justify-center min-w-[80px]">
                                                                        <p className={`text-xl font-black leading-none ${isPassing ? 'text-green-400' : 'text-red-400'}`}>{(strat.confidence || 0).toFixed(0)}%</p>
                                                                        <div className="flex items-center gap-2 mt-2 justify-center">
                                                                            <div className="w-20 bg-white/10 rounded-full h-2 overflow-hidden">
                                                                                <div className={`h-full rounded-full transition-all duration-500 ${isPassing ? 'bg-green-400' : 'bg-red-400'}`} style={{width: `${Math.min(100, strat.confidence || 0)}%`}} />
                                                                            </div>
                                                                            <p className="text-[10px] text-gray-500 font-semibold">{strat.rules_passing ?? strat.conditions_met ?? 0}/{strat.rules_total ?? strat.total_conditions ?? 0}</p>
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                </Card>
                                            )}

                                            {/* Signal Summary */}
                                            <Card className={`overflow-hidden border-2 ${
                                                strategyEval.qualifies ? 'border-green-500/40' : 'border-red-500/40'
                                            }`}>
                                                <div className={`flex flex-col items-center justify-center text-center py-8 px-6 ${
                                                    strategyEval.qualifies ? 'bg-green-500/8' : 'bg-red-500/8'
                                                }`}>
                                                    <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mb-4 ${
                                                        strategyEval.qualifies ? 'bg-green-500/20' : 'bg-red-500/20'
                                                    }`}>
                                                        <Target className={`w-8 h-8 ${strategyEval.qualifies ? 'text-green-400' : 'text-red-400'}`} />
                                                    </div>
                                                    <p className={`text-2xl font-black ${
                                                        strategyEval.qualifies ? 'text-green-400' : 'text-red-400'
                                                    }`}>
                                                        Multi-Strategy Signal: {strategyEval.qualifies ? 'BUY' : 'HOLD'}
                                                    </p>
                                                    <p className="text-sm text-gray-400 mt-3 max-w-lg leading-relaxed">
                                                        {strategyEval.qualifies 
                                                            ? `${strategyEval.strategies_passing} strategies agree on a bullish outlook with ${strategyEval.avg_confidence?.toFixed(0)}% average confidence.`
                                                            : `Not enough strategies (${strategyEval.strategies_passing}/${strategyEval.strategies_evaluated}) are passing to generate a buy signal.`
                                                        }
                                                    </p>
                                                </div>
                                            </Card>
                                        </>
                                    )}
                                </div>
                            )}

                            {/* Bottom spacer */}
                            <div className="h-8" />
                        </div>
                    </div>
                </div>
            )}

            {/* Toast */}
            {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
        </div>
    );
}
