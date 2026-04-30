import React, { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, RefreshCw, Clock } from 'lucide-react';
import { fetchTopMovers } from '../../services/api';

/**
 * TopMovers Component - Displays top 4 gainers and top 4 losers
 * with live data refresh capability
 */
const TopMovers = ({ onTickerClick }) => {
    const [gainers, setGainers] = useState([]);
    const [losers, setLosers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [autoRefresh, setAutoRefresh] = useState(true);

    const loadMovers = useCallback(async () => {
        try {
            if (!gainers.length && !losers.length) setLoading(true);
            setRefreshing(true);
            setError(null);
            const data = await fetchTopMovers();
            setGainers(data.gainers || []);
            setLosers(data.losers || []);
            setLastUpdated(new Date());
        } catch (err) {
            console.error('Failed to fetch market movers:', err);
            setError('Failed to load market data');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [gainers.length, losers.length]);

    useEffect(() => {
        loadMovers();
    }, [loadMovers]);

    // Auto-refresh every 15 seconds
    useEffect(() => {
        if (!autoRefresh) return;

        const interval = setInterval(() => {
            loadMovers();
        }, 15000);

        return () => clearInterval(interval);
    }, [autoRefresh, loadMovers]);

    const formatPrice = (price) => {
        const value = Number(price);
        if (!Number.isFinite(value)) return '—';
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 2
        }).format(value);
    };

    const formatVolume = (volume) => {
        const value = Number(volume);
        if (!Number.isFinite(value) || value <= 0) return '—';
        if (value >= 10000000) return `${(value / 10000000).toFixed(2)} Cr`;
        if (value >= 100000) return `${(value / 100000).toFixed(2)} L`;
        if (value >= 1000) return `${(value / 1000).toFixed(1)} K`;
        return value.toString();
    };

    const formatTicker = (ticker) => String(ticker || '').trim().replace(/^\^+/, '').toUpperCase();

    const MoverCard = ({ stock, isGainer }) => {
        const changePct = Number(stock.change_pct ?? 0);
        const changeValue = Number(stock.change ?? 0);

        return (
        <button
            type="button"
            className={`mover-card top-mover-item ${isGainer ? 'top-mover-item-gainer' : 'top-mover-item-loser'} glass rounded-xl p-4 cursor-pointer transition-all hover:scale-[1.02] text-left w-full`}
            onClick={() => onTickerClick?.(stock.ticker)}
            style={{
                borderLeft: `4px solid ${isGainer ? 'var(--color-success)' : 'var(--color-danger)'}`,
                background: isGainer
                    ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%)'
                    : 'linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%)'
            }}
            aria-label={`Open ${formatTicker(stock.ticker)} details`}
        >
            <div className="flex justify-between items-start mb-2">
                <div>
                    <h4 className="font-semibold text-white text-sm">{formatTicker(stock.ticker)}</h4>
                    <p className="text-xs text-gray-400 truncate max-w-[120px]" title={stock.company_name}>
                        {stock.company_name || formatTicker(stock.ticker)}
                    </p>
                </div>
                <div className={`flex items-center gap-1 ${isGainer ? 'text-green-400' : 'text-red-400'}`}>
                    {isGainer ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                    <span className="font-bold text-sm">
                        {isGainer ? '+' : ''}{changePct.toFixed(2)}%
                    </span>
                </div>
            </div>
            <div className="flex justify-between items-end">
                <div>
                    <p className="text-lg font-bold text-white">{formatPrice(stock.current_price)}</p>
                    <p className={`text-xs ${isGainer ? 'text-green-400' : 'text-red-400'}`}>
                        {isGainer ? '+' : ''}{formatPrice(changeValue)}
                    </p>
                </div>
                <div className="text-right">
                    <p className="text-xs text-gray-400">Volume</p>
                    <p className="text-xs text-gray-300 font-medium">{formatVolume(stock.volume)}</p>
                </div>
            </div>
        </button>
    );
    };

    const LoadingSkeleton = () => (
        <div className="mover-card top-mover-skeleton glass rounded-xl p-4 animate-pulse">
            <div className="flex justify-between items-start mb-2">
                <div>
                    <div className="h-4 w-20 bg-white/10 rounded mb-1"></div>
                    <div className="h-3 w-32 bg-white/10 rounded"></div>
                </div>
                <div className="h-5 w-16 bg-white/10 rounded"></div>
            </div>
            <div className="flex justify-between items-end">
                <div>
                    <div className="h-6 w-24 bg-white/10 rounded mb-1"></div>
                    <div className="h-3 w-16 bg-white/10 rounded"></div>
                </div>
                <div className="text-right">
                    <div className="h-3 w-12 bg-white/10 rounded mb-1"></div>
                    <div className="h-3 w-10 bg-white/10 rounded"></div>
                </div>
            </div>
        </div>
    );

    return (
        <div className="top-movers-container top-movers-shell mb-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-4 top-movers-header">
                <h3 className="text-xl font-bold text-white flex items-center gap-2 top-movers-title">
                    <TrendingUp className="text-green-400" size={22} />
                    Market Movers
                </h3>
                <div className="flex items-center gap-3 top-movers-controls">
                    {lastUpdated && (
                        <span className="text-xs text-gray-400 flex items-center gap-1 top-movers-updated">
                            <Clock size={12} />
                            Updated {lastUpdated.toLocaleTimeString()}
                        </span>
                    )}
                    <button
                        type="button"
                        onClick={loadMovers}
                        disabled={refreshing}
                        className="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-all top-movers-refresh"
                        title="Refresh data"
                    >
                        <RefreshCw size={16} className={`text-gray-400 ${refreshing ? 'animate-spin' : ''}`} />
                    </button>
                    <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer top-movers-auto-toggle">
                        <input
                            type="checkbox"
                            checked={autoRefresh}
                            onChange={(e) => setAutoRefresh(e.target.checked)}
                            className="rounded"
                        />
                        Auto-refresh
                    </label>
                </div>
            </div>

            {error && (
                <div className="glass rounded-lg p-4 mb-4 border-l-4 border-red-500 bg-red-500/10 top-movers-error">
                    <p className="text-red-400 text-sm">{error}</p>
                </div>
            )}

            {/* Gainers and Losers Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 top-movers-board">
                {/* Top Gainers */}
                <div className="glass rounded-2xl p-4 top-movers-column top-movers-column-gainers">
                    <div className="flex items-center gap-2 mb-4 top-movers-column-header">
                        <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
                        <h4 className="font-semibold text-green-400 top-movers-column-title">Top Gainers</h4>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {loading ? (
                            <>
                                <LoadingSkeleton />
                                <LoadingSkeleton />
                                <LoadingSkeleton />
                                <LoadingSkeleton />
                            </>
                        ) : gainers.length > 0 ? (
                            gainers.map((stock) => (
                                <MoverCard key={stock.ticker} stock={stock} isGainer={true} />
                            ))
                        ) : (
                            <p className="text-gray-400 text-sm col-span-2 text-center py-4">
                                No gainers data available
                            </p>
                        )}
                    </div>
                </div>

                {/* Top Losers */}
                <div className="glass rounded-2xl p-4 top-movers-column top-movers-column-losers">
                    <div className="flex items-center gap-2 mb-4 top-movers-column-header">
                        <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></div>
                        <h4 className="font-semibold text-red-400 top-movers-column-title">Top Losers</h4>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {loading ? (
                            <>
                                <LoadingSkeleton />
                                <LoadingSkeleton />
                                <LoadingSkeleton />
                                <LoadingSkeleton />
                            </>
                        ) : losers.length > 0 ? (
                            losers.map((stock) => (
                                <MoverCard key={stock.ticker} stock={stock} isGainer={false} />
                            ))
                        ) : (
                            <p className="text-gray-400 text-sm col-span-2 text-center py-4">
                                No losers data available
                            </p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export { TopMovers };
export default TopMovers;
