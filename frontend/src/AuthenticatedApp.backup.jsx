import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
    Search, TrendingUp, Filter, Brain, BarChart2, Target, AlertTriangle,
    Sparkles, Activity, DollarSign, Settings, Briefcase, ChevronRight,
    RefreshCw, Clock, ArrowUpRight, ArrowDownRight, X, Play, Layers,
    PieChart, Star, StarOff, Trash2, Download, Plus
} from 'lucide-react';

// Components
import { Card, Button, StatCard, LoadingSpinner, Toast, ThemeToggle } from './components/ui';
import { PriceChart, StrategyComparison } from './components/charts';
import { MultiStrategyPanel, StrategyBuilder } from './components/screener';
import { MarketOverview, TopMovers } from './components/dashboard';
import { WatchlistSearch, PortfolioDashboard } from './components/portfolio';

// API Services
import * as api from './services/api';

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
    { id: 'quality_growth', name: 'Quality Growth', icon: Star, color: 'violet' },
    { id: 'custom', name: 'Custom', icon: Filter, color: 'pink' } // Placeholder for custom
];

const TABS = [
    { id: 'dashboard', name: 'Dashboard', icon: BarChart2 },
    { id: 'screener', name: 'Screener', icon: Filter },
    { id: 'backtest', name: 'Backtest', icon: Clock },
    { id: 'portfolio', name: 'Portfolio', icon: Briefcase },
    { id: 'settings', name: 'Settings', icon: Settings }
];

export default function AuthenticatedApp({ theme, toggleTheme }) {
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
    const [toast, setToast] = useState(null);

    // Screener state
    const [screenStrategy, setScreenStrategy] = useState('momentum');
    const [screenResults, setScreenResults] = useState([]);
    const [screening, setScreening] = useState(false);
    const [customConditions, setCustomConditions] = useState({
        price_min: '', price_max: '', rsi_min: '', rsi_max: '', volume_ratio: ''
    });
    const [screenerMode, setScreenerMode] = useState('single'); // 'single' or 'multi'

    // Prediction state
    const [prediction, setPrediction] = useState(null);
    const [predicting, setPredicting] = useState(false);
    const [capital, setCapital] = useState(100000);
    const [riskPct, setRiskPct] = useState(2);
    const [training, setTraining] = useState(false);
    const [trainingMessage, setTrainingMessage] = useState(null);

    // Backtest state
    const [backtestStrategy, setBacktestStrategy] = useState('momentum');
    const [backtestResults, setBacktestResults] = useState(null);
    const [backtesting, setBacktesting] = useState(false);
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

    // Portfolio state
    const [watchlist, setWatchlist] = useState([]);

    // Settings state
    const [config, setConfig] = useState(null);
    const [configLoading, setConfigLoading] = useState(false);

    // Initial data fetch
    useEffect(() => {
        fetchInitialData();
        loadStrategies();
    }, []);

    const loadStrategies = async () => {
        try {
            const data = await api.getStrategies();
            const customStrategies = (data.custom || []).map(s => ({
                id: s.name,
                name: s.name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                icon: Filter,
                color: 'pink',
                category: s.metadata?.category || 'Custom'
            }));

            // Merge custom strategies into the list
            setStrategies(prev => {
                const existingIds = new Set(prev.map(p => p.id));
                const newCustom = customStrategies.filter(c => !existingIds.has(c.id));
                return [...prev, ...newCustom];
            });
        } catch (err) {
            console.error("Failed to load strategies", err);
        }
    };

    const fetchInitialData = async () => {
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
    };

    const showToast = useCallback((message, type = 'info') => {
        setToast({ message, type });
    }, []);

    // Filtered stocks based on search
    const filteredStocks = useMemo(() =>
        stocks.filter(s => (s.ticker || '').toLowerCase().includes(searchTerm.toLowerCase())),
        [stocks, searchTerm]
    );

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
            showToast(`${ticker} added to watchlist`, 'success');
        } catch (err) {
            showToast(err.message, 'error');
        }
    };

    const handleWatchlistRemove = async (ticker) => {
        try {
            const newList = await api.removeFromWatchlist(ticker);
            setWatchlist(newList);
            showToast(`${ticker} removed`, 'info');
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

    const handleRunScreener = async () => {
        setScreening(true);
        setScreenResults([]);

        try {
            let params = {};
            if (screenStrategy === 'momentum') params = { lookback_days: 20, min_return: 5.0 };
            else if (screenStrategy === 'piotroski') params = { min_score: 7 };
            else if (screenStrategy === 'breakout') params = { volume_threshold: 1.5 };
            else if (screenStrategy === 'custom') {
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
            }

            const result = await api.runScreener(screenStrategy, params);
            setScreenResults(result.results || []);
            showToast(`Found ${result.count || 0} stocks`, 'success');
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            setScreening(false);
        }
    };

    const handleOpenTicker = async (ticker) => {
        setSelectedTicker(ticker);
        setChartData([]);
        setPrediction(null);
        try {
            const data = await api.fetchTickerHistory(ticker, chartPeriod);
            setChartData(data);
        } catch (err) {
            showToast('Failed to load history', 'error');
        }
    };

    useEffect(() => {
        if (selectedTicker) handleOpenTicker(selectedTicker);
    }, [chartPeriod]);

    const handlePrediction = async () => {
        if (!selectedTicker) return;
        setPredicting(true);
        setPrediction(null);
        try {
            const result = await api.fetchPrediction(selectedTicker, Number(capital), Number(riskPct));
            setPrediction(result);
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            setPredicting(false);
        }
    };

    const handleTrain = async () => {
        if (!selectedTicker) return;
        setTraining(true);
        setTrainingMessage(null);
        try {
            const result = await api.trainModel(selectedTicker);
            setTrainingMessage(result.message || 'Training complete!');
            showToast('Model trained successfully', 'success');
        } catch (err) {
            setTrainingMessage(err.message);
            showToast('Training failed', 'error');
        } finally {
            setTraining(false);
        }
    };

    const handleBacktest = async () => {
        setBacktesting(true);
        setBacktestResults(null);
        try {
            const result = await api.runBacktest(backtestStrategy, backtestParams);
            setBacktestResults(result);
            showToast('Backtest complete!', 'success');
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            setBacktesting(false);
        }
    };

    const handleFetchConfig = async () => {
        setConfigLoading(true);
        try {
            const configData = await api.fetchConfig();
            setConfig(configData);
        } catch (err) {
            showToast('Failed to load config', 'error');
        } finally {
            setConfigLoading(false);
        }
    };

    useEffect(() => {
        if (activeTab === 'settings' && !config) handleFetchConfig();
    }, [activeTab]);

    const handleSaveConfig = async () => {
        try {
            const updatedConfig = await api.updateConfig(config);
            setConfig(updatedConfig);
            showToast('Configuration saved!', 'success');
        } catch (err) {
            showToast('Failed to save config', 'error');
        }
    };

    const handleClearCache = async () => {
        try {
            await api.clearCache();
            showToast('Cache cleared!', 'success');
        } catch (err) {
            showToast('Failed to clear cache', 'error');
        }
    };

    // Multi-strategy handler
    const handleMultiStrategy = async (strategies, minOverlap) => {
        const result = await api.runMultiStrategy(strategies, minOverlap);
        return result;
    };

    // Strategy comparison handler
    const handleCompareStrategies = async () => {
        setComparing(true);
        setComparisonResults(null);
        try {
            const strategies = INITIAL_STRATEGIES.slice(0, 5).map(s => ({ name: s.id, params: {} }));
            const result = await api.compareStrategies(strategies, backtestParams);
            setComparisonResults(result);
            showToast('Comparison complete!', 'success');
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            setComparing(false);
        }
    };

    // ==================== RENDER ====================

    return (
        <div className="min-h-screen bg-pattern relative">
            {/* Fixed background gradient */}
            <div className="fixed inset-0 bg-gradient-to-br from-slate-900 via-blue-900/80 to-slate-900 -z-10" />

            {/* Header */}
            <header className="glass-strong sticky top-0 z-40 border-b border-white/10">
                <div className="container py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="relative">
                                <div className="absolute inset-0 bg-blue-500 blur-xl opacity-50 animate-pulse" />
                                <Brain className="relative w-9 h-9 text-blue-400" />
                            </div>
                            <div>
                                <h1 className="text-xl font-black text-white tracking-tight">GenAI Stock Intelligence</h1>
                                <p className="text-xs text-blue-200">AI-Powered Market Analysis</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            {health?.status === 'healthy' && (
                                <span className="hidden md:flex items-center gap-2 text-xs text-emerald-300">
                                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                                    Backend Online • {stats?.total_stocks || 0} Stocks
                                </span>
                            )}
                            <Button onClick={handleRefresh} variant="secondary" size="sm">
                                <RefreshCw className="w-4 h-4" />
                            </Button>
                            <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                        </div>
                    </div>

                    {/* Navigation Tabs */}
                    <div className="flex gap-1 mt-4 overflow-x-auto pb-1">
                        {TABS.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 whitespace-nowrap ${activeTab === tab.id
                                    ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg'
                                    : 'bg-white/5 text-white hover:bg-white/10'
                                    }`}
                            >
                                <tab.icon className="w-4 h-4" />{tab.name}
                            </button>
                        ))}
                    </div>
                </div>
            </header>

            <main className="container py-6 relative">
                {/* DASHBOARD TAB */}
                {activeTab === 'dashboard' && (
                    <div className="space-y-6 animate-fade-in">
                        {/* Stats Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <StatCard icon={BarChart2} label="Total Stocks" value={stocks.length} color="blue" />
                            <StatCard icon={TrendingUp} label="Gainers" value={stocks.filter(s => s.close > s.open).length} color="green" />
                            <StatCard icon={ArrowDownRight} label="Losers" value={stocks.filter(s => s.close < s.open).length} color="red" />
                            <StatCard icon={Star} label="Watchlist" value={watchlist.length} color="yellow" />
                        </div>

                        {/* Top Gainers/Losers - Live Data */}
                        <TopMovers onTickerClick={handleOpenTicker} />

                        {/* Market Overview Widget */}
                        <MarketOverview stocks={stocks} />

                        {/* Search */}
                        <Card className="p-4">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 bg-blue-500/20 rounded-xl">
                                    <Search className="w-5 h-5 text-blue-300" />
                                </div>
                                <input
                                    type="text"
                                    placeholder="Search by ticker (e.g., RELIANCE, TCS)..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="flex-1 bg-transparent outline-none text-white placeholder-blue-200/50 font-medium"
                                />
                            </div>
                        </Card>

                        {/* Stocks Table */}
                        {loading ? <LoadingSpinner text="Loading market data..." /> : (
                            <Card className="overflow-hidden">
                                <div className="overflow-x-auto">
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Ticker</th>
                                                <th>Date</th>
                                                <th className="text-right">Close</th>
                                                <th className="text-right">High</th>
                                                <th className="text-right">Low</th>
                                                <th className="text-right">Volume</th>
                                                <th className="text-center">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                            {filteredStocks.slice(0, 50).map((stock, idx) => (
                                                <tr key={idx}>
                                                    <td
                                                        className="font-bold text-blue-400 cursor-pointer hover:text-blue-300"
                                                        onClick={() => handleOpenTicker(stock.ticker)}
                                                    >
                                                        {stock.ticker}
                                                    </td>
                                                    <td className="text-sm text-gray-300">{(stock.date || '').split('T')[0]}</td>
                                                    <td className="text-right font-semibold text-white">₹{(stock.close || 0).toFixed(2)}</td>
                                                    <td className="text-right text-green-400">₹{(stock.high || 0).toFixed(2)}</td>
                                                    <td className="text-right text-red-400">₹{(stock.low || 0).toFixed(2)}</td>
                                                    <td className="text-right text-sm text-gray-300">{(stock.volume || 0).toLocaleString()}</td>
                                                    <td className="text-center">
                                                        <button
                                                            onClick={() => watchlist.includes(stock.ticker) ? handleWatchlistRemove(stock.ticker) : handleWatchlistAdd(stock.ticker)}
                                                            className={`p-1.5 rounded-lg transition ${watchlist.includes(stock.ticker) ? 'bg-yellow-500/20 text-yellow-400' : 'bg-white/10 text-gray-400 hover:text-yellow-400'}`}
                                                        >
                                                            {watchlist.includes(stock.ticker) ? <Star className="w-4 h-4 fill-current" /> : <StarOff className="w-4 h-4" />}
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </Card>
                        )}
                    </div>
                )}

                {/* SCREENER TAB */}
                {activeTab === 'screener' && (
                    <div className="space-y-6 animate-fade-in">
                        {showStrategyBuilder ? (
                            <StrategyBuilder
                                onSave={handleStrategySave}
                                onCancel={() => setShowStrategyBuilder(false)}
                            />
                        ) : (
                            <>
                                <div className="flex justify-between items-center">
                                    {/* Mode Toggle */}
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setScreenerMode('single')}
                                            className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 ${screenerMode === 'single'
                                                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                                                : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                                }`}
                                        >
                                            <Filter className="w-4 h-4" />
                                            Single Strategy
                                        </button>
                                        <button
                                            onClick={() => setScreenerMode('multi')}
                                            className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 ${screenerMode === 'multi'
                                                ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                                                : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                                }`}
                                        >
                                            <Layers className="w-4 h-4" />
                                            Multi-Strategy
                                        </button>
                                    </div>
                                    <Button onClick={() => setShowStrategyBuilder(true)} variant="purple" size="sm">
                                        <Plus className="w-4 h-4 mr-2" />
                                        New Strategy
                                    </Button>
                                </div>

                                {/* Single Strategy Mode */}
                                {screenerMode === 'single' && (
                                    <>
                                        <Card className="p-6">
                                            <div className="flex items-center gap-3 mb-6">
                                                <div className="p-3 bg-purple-500/20 rounded-xl">
                                                    <Filter className="w-6 h-6 text-purple-300" />
                                                </div>
                                                <h2 className="text-2xl font-black text-white">Stock Screener</h2>
                                            </div>

                                            {/* Strategy Grid */}
                                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
                                                {INITIAL_STRATEGIES.map(s => (
                                                    <button
                                                        key={s.id}
                                                        onClick={() => setScreenStrategy(s.id)}
                                                        className={`p-4 rounded-xl font-bold transition-all flex items-center gap-2 ${screenStrategy === s.id
                                                            ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white shadow-lg'
                                                            : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                                            }`}
                                                    >
                                                        <s.icon className="w-5 h-5" />{s.name}
                                                    </button>
                                                ))}
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

                                            <Button onClick={handleRunScreener} disabled={screening} variant="purple" size="lg" className="w-full">
                                                {screening ? <><RefreshCw className="w-5 h-5 animate-spin" />Scanning...</> : <><Play className="w-5 h-5" />Run {screenStrategy} Scan</>}
                                            </Button>
                                        </Card>

                                        {/* Results */}
                                        {screenResults.length > 0 && (
                                            <Card className="overflow-hidden">
                                                <div className="px-6 py-4 bg-gradient-to-r from-green-500/20 to-emerald-500/20 border-b border-white/10">
                                                    <h3 className="text-lg font-black text-green-300 flex items-center gap-2">
                                                        <TrendingUp className="w-5 h-5" />Found {screenResults.length} Stocks
                                                    </h3>
                                                </div>
                                                <div className="overflow-x-auto">
                                                    <table>
                                                        <thead>
                                                            <tr>
                                                                {Object.keys(screenResults[0] || {}).map(key => (
                                                                    <th key={key}>{key.replace(/_/g, ' ')}</th>
                                                                ))}
                                                                <th>Action</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-white/5">
                                                            {screenResults.map((row, idx) => (
                                                                <tr key={idx}>
                                                                    {Object.values(row).map((val, i) => (
                                                                        <td key={i} className="text-sm text-white">
                                                                            {typeof val === 'object' && val !== null
                                                                                ? Array.isArray(val)
                                                                                    ? val.join(', ')
                                                                                    : Object.entries(val).map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toFixed(2) : v}`).join(', ')
                                                                                : typeof val === 'number'
                                                                                    ? val.toLocaleString()
                                                                                    : val ?? '-'}
                                                                        </td>
                                                                    ))}
                                                                    <td>
                                                                        <Button onClick={() => handleOpenTicker(row.ticker)} size="sm" variant="secondary">
                                                                            Analyze
                                                                        </Button>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
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
                    <div className="space-y-6 animate-fade-in">
                        {/* Mode Toggle */}
                        <div className="flex gap-2">
                            <button
                                onClick={() => setComparisonMode(false)}
                                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 ${!comparisonMode
                                    ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg'
                                    : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                    }`}
                            >
                                <Clock className="w-4 h-4" />
                                Single Strategy
                            </button>
                            <button
                                onClick={() => setComparisonMode(true)}
                                className={`px-4 py-2 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 ${comparisonMode
                                    ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg'
                                    : 'bg-white/5 text-white hover:bg-white/10 border border-white/10'
                                    }`}
                            >
                                <BarChart2 className="w-4 h-4" />
                                Compare Strategies
                            </button>
                        </div>

                        {/* Single Strategy Backtest */}
                        {!comparisonMode && (
                            <>
                                <Card className="p-6">
                                    <div className="flex items-center gap-3 mb-6">
                                        <div className="p-3 bg-blue-500/20 rounded-xl">
                                            <Clock className="w-6 h-6 text-blue-300" />
                                        </div>
                                        <h2 className="text-2xl font-black text-white">Strategy Backtesting</h2>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Strategy</label>
                                            <select value={backtestStrategy} onChange={(e) => setBacktestStrategy(e.target.value)}>
                                                {INITIAL_STRATEGIES.slice(0, 5).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                                            </select>
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Start Date</label>
                                            <input type="date" value={backtestParams.start_date} onChange={(e) => setBacktestParams({ ...backtestParams, start_date: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">End Date</label>
                                            <input type="date" value={backtestParams.end_date} onChange={(e) => setBacktestParams({ ...backtestParams, end_date: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Initial Capital (₹)</label>
                                            <input type="number" value={backtestParams.initial_capital} onChange={(e) => setBacktestParams({ ...backtestParams, initial_capital: Number(e.target.value) })} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Max Positions</label>
                                            <input type="number" value={backtestParams.max_positions} onChange={(e) => setBacktestParams({ ...backtestParams, max_positions: Number(e.target.value) })} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Rebalance</label>
                                            <select value={backtestParams.rebalance_frequency} onChange={(e) => setBacktestParams({ ...backtestParams, rebalance_frequency: e.target.value })}>
                                                <option value="daily">Daily</option>
                                                <option value="weekly">Weekly</option>
                                                <option value="monthly">Monthly</option>
                                            </select>
                                        </div>
                                    </div>

                                    <Button onClick={handleBacktest} disabled={backtesting} variant="primary" size="lg" className="w-full">
                                        {backtesting ? <><RefreshCw className="w-5 h-5 animate-spin" />Running...</> : <><Play className="w-5 h-5" />Run Backtest</>}
                                    </Button>
                                </Card>

                                {/* Backtest Results */}
                                {backtestResults && (
                                    <Card className="p-6">
                                        <h3 className="text-xl font-black text-white mb-6 flex items-center gap-2">
                                            <PieChart className="w-6 h-6 text-blue-400" />Backtest Results
                                        </h3>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                                            <StatCard icon={DollarSign} label="Final Value" value={`₹${backtestResults.final_value?.toLocaleString()}`} color="green" />
                                            <StatCard icon={TrendingUp} label="Total Return" value={`${backtestResults.total_return_pct}%`} change={backtestResults.total_return_pct} color="blue" />
                                            <StatCard icon={Target} label="Sharpe Ratio" value={backtestResults.sharpe_ratio} color="purple" />
                                            <StatCard icon={AlertTriangle} label="Max Drawdown" value={`${backtestResults.max_drawdown}%`} color="red" />
                                        </div>
                                        <div className="grid grid-cols-3 gap-4 mb-6">
                                            <div className="bg-white/5 rounded-xl p-4 text-center border border-white/10">
                                                <p className="text-xs text-gray-400">Win Rate</p>
                                                <p className="text-2xl font-black text-white">{backtestResults.win_rate}%</p>
                                            </div>
                                            <div className="bg-white/5 rounded-xl p-4 text-center border border-white/10">
                                                <p className="text-xs text-gray-400">Total Trades</p>
                                                <p className="text-2xl font-black text-white">{backtestResults.total_trades}</p>
                                            </div>
                                            <div className="bg-white/5 rounded-xl p-4 text-center border border-white/10">
                                                <p className="text-xs text-gray-400">Profit Factor</p>
                                                <p className="text-2xl font-black text-white">{backtestResults.profit_factor}</p>
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
                                <Card className="p-6">
                                    <div className="flex items-center gap-3 mb-6">
                                        <div className="p-3 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-xl">
                                            <BarChart2 className="w-6 h-6 text-blue-300" />
                                        </div>
                                        <div>
                                            <h2 className="text-2xl font-black text-white">Strategy Comparison</h2>
                                            <p className="text-sm text-gray-400">Compare all 5 strategies side-by-side</p>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Start Date</label>
                                            <input type="date" value={backtestParams.start_date} onChange={(e) => setBacktestParams({ ...backtestParams, start_date: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">End Date</label>
                                            <input type="date" value={backtestParams.end_date} onChange={(e) => setBacktestParams({ ...backtestParams, end_date: e.target.value })} />
                                        </div>
                                        <div>
                                            <label className="text-xs font-semibold text-blue-200 block mb-1">Initial Capital (₹)</label>
                                            <input type="number" value={backtestParams.initial_capital} onChange={(e) => setBacktestParams({ ...backtestParams, initial_capital: Number(e.target.value) })} />
                                        </div>
                                    </div>

                                    <Button onClick={handleCompareStrategies} disabled={comparing} variant="primary" size="lg" className="w-full">
                                        {comparing ? <><RefreshCw className="w-5 h-5 animate-spin" />Comparing...</> : <><BarChart2 className="w-5 h-5" />Compare All Strategies</>}
                                    </Button>
                                </Card>

                                {/* Comparison Results */}
                                {comparisonResults && (
                                    <Card className="p-6">
                                        <h3 className="text-xl font-black text-white mb-6 flex items-center gap-2">
                                            <BarChart2 className="w-6 h-6 text-blue-400" />Strategy Comparison Results
                                        </h3>
                                        <StrategyComparison data={comparisonResults} />
                                    </Card>
                                )}
                            </>
                        )}
                    </div>
                )}

                {/* PORTFOLIO TAB */}
                {activeTab === 'portfolio' && (
                    <div className="space-y-6 animate-fade-in">
                        <PortfolioDashboard />

                        <Card className="p-6">
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
                                            <div key={ticker} className="bg-white/5 rounded-xl p-4 border border-white/10 flex justify-between items-center">
                                                <div>
                                                    <p className="font-bold text-blue-400 cursor-pointer hover:text-blue-300" onClick={() => handleOpenTicker(ticker)}>
                                                        {ticker}
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
                    </div>
                )}

                {/* SETTINGS TAB */}
                {activeTab === 'settings' && (
                    <div className="space-y-6 animate-fade-in">
                        <Card className="p-6">
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
                                        <Button onClick={handleSaveConfig} variant="success">
                                            <Download className="w-4 h-4" />Save Configuration
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

            {/* Stock Detail Modal */}
            {selectedTicker && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
                    <div className="bg-gradient-to-br from-slate-900 to-blue-900 rounded-3xl w-full max-w-5xl max-h-[90vh] overflow-y-auto shadow-2xl border border-white/20">
                        {/* Modal Header */}
                        <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4 flex justify-between items-center border-b border-white/20 rounded-t-3xl z-10">
                            <div>
                                <h2 className="text-2xl font-black text-white">{selectedTicker}</h2>
                                <p className="text-blue-100 text-sm">Stock Analysis & AI Predictions</p>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => watchlist.includes(selectedTicker) ? handleWatchlistRemove(selectedTicker) : handleWatchlistAdd(selectedTicker)}
                                    className={`p-2 rounded-lg ${watchlist.includes(selectedTicker) ? 'bg-yellow-500/30 text-yellow-300' : 'bg-white/20 text-white'}`}
                                >
                                    <Star className={`w-5 h-5 ${watchlist.includes(selectedTicker) ? 'fill-current' : ''}`} />
                                </button>
                                <button onClick={() => setSelectedTicker(null)} className="w-10 h-10 bg-white/20 hover:bg-white/30 rounded-full text-white text-xl font-bold">
                                    ×
                                </button>
                            </div>
                        </div>

                        <div className="p-6 space-y-6">
                            {/* Chart Period Selector */}
                            <div className="flex gap-2 mb-4">
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

                            {/* AI Prediction Panel */}
                            <Card className="p-6">
                                <h3 className="font-black text-white mb-4 flex items-center gap-2">
                                    <Brain className="w-6 h-6 text-purple-400" />AI Prediction Engine
                                </h3>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                                    <div>
                                        <label className="text-xs font-semibold text-blue-200 block mb-1">Capital (₹)</label>
                                        <input type="number" value={capital} onChange={(e) => setCapital(e.target.value)} />
                                    </div>
                                    <div>
                                        <label className="text-xs font-semibold text-blue-200 block mb-1">Risk (%)</label>
                                        <input type="number" value={riskPct} onChange={(e) => setRiskPct(e.target.value)} />
                                    </div>
                                    <Button onClick={handlePrediction} disabled={predicting} variant="purple" className="self-end">
                                        {predicting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Target className="w-4 h-4" />}Predict
                                    </Button>
                                    <Button onClick={handleTrain} disabled={training} variant="secondary" className="self-end">
                                        {training ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Brain className="w-4 h-4" />}Train
                                    </Button>
                                </div>
                                {trainingMessage && <p className="text-sm text-blue-200 mb-4">{trainingMessage}</p>}

                                {/* Prediction Results */}
                                {prediction && !prediction.error && (
                                    <div className={`rounded-xl p-5 border-2 ${prediction.signal === 'BUY' ? 'bg-green-500/10 border-green-500/50' :
                                        prediction.signal === 'SELL' ? 'bg-red-500/10 border-red-500/50' :
                                            'bg-yellow-500/10 border-yellow-500/50'
                                        }`}>
                                        <div className="flex justify-between items-start mb-4">
                                            <div>
                                                <h4 className={`text-2xl font-black ${prediction.signal === 'BUY' ? 'text-green-400' :
                                                    prediction.signal === 'SELL' ? 'text-red-400' :
                                                        'text-yellow-400'
                                                    }`}>
                                                    <Target className="w-6 h-6 inline mr-2" />{prediction.signal}
                                                </h4>
                                                <p className="text-sm text-gray-300">Confidence: <span className="font-semibold">{prediction.prediction_confidence}</span></p>
                                            </div>
                                            <div className="text-right bg-white/10 rounded-xl p-3">
                                                <p className="text-xs text-gray-400">5-Day Target</p>
                                                <p className="text-2xl font-black text-white">₹{prediction.predicted_price_5d?.toFixed(2)}</p>
                                                <p className={`text-lg font-bold ${prediction.predicted_return_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                    {prediction.predicted_return_pct > 0 ? '↑' : '↓'} {Math.abs(prediction.predicted_return_pct || 0).toFixed(2)}%
                                                </p>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                            <div className="bg-white/5 rounded-lg p-3">
                                                <p className="text-xs text-gray-400">Current Price</p>
                                                <p className="text-lg font-bold text-white">₹{prediction.current_price?.toFixed(2)}</p>
                                            </div>
                                            <div className="bg-white/5 rounded-lg p-3">
                                                <p className="text-xs text-gray-400">Stop Loss</p>
                                                <p className="text-lg font-bold text-red-400">₹{prediction.stop_loss?.toFixed(2)}</p>
                                            </div>
                                            <div className="bg-white/5 rounded-lg p-3">
                                                <p className="text-xs text-gray-400">Target Price</p>
                                                <p className="text-lg font-bold text-green-400">₹{prediction.target_price?.toFixed(2)}</p>
                                            </div>
                                            <div className="bg-white/5 rounded-lg p-3">
                                                <p className="text-xs text-gray-400">Risk/Reward</p>
                                                <p className="text-lg font-bold text-blue-400">{prediction.risk_reward_ratio?.toFixed(2)}</p>
                                            </div>
                                        </div>

                                        {prediction.suggested_quantity && (
                                            <div className="mt-4 p-3 bg-white/5 rounded-lg">
                                                <p className="text-sm text-gray-300">
                                                    <span className="font-semibold text-white">Trade Suggestion:</span> Buy {prediction.suggested_quantity} shares
                                                    (₹{prediction.trade_value?.toLocaleString()}) | Max Loss: ₹{prediction.max_loss_amount?.toFixed(0)}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </Card>
                        </div>
                    </div>
                </div>
            )}

            {/* Toast */}
            {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
        </div>
    );
}
