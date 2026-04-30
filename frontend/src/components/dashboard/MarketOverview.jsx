import React, { useState, useEffect, useCallback } from 'react';
import {
    Activity, RefreshCw, Clock,
    BarChart3, Zap, Globe, ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import { Card } from '../ui';
import { fetchMarketOverview } from '../../services/api';

/**
 * MarketOverview — Live dashboard widget with index quotes,
 * market breadth, sectoral heatmap, and volume stats.
 * Auto-refreshes every 20 seconds.
 */
export const MarketOverview = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);

    const load = useCallback(async () => {
        try {
            if (!data) setLoading(true);
            setRefreshing(true);
            setError(null);
            const res = await fetchMarketOverview();
            setData(res);
            setLastUpdated(new Date());
        } catch (e) {
            console.error('Market overview fetch failed:', e);
            setError(e.message || 'Failed to load market data');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [data]);

    useEffect(() => { load(); }, [load]);

    // Auto-refresh every 20s
    useEffect(() => {
        const interval = setInterval(load, 20_000);
        
        return () => clearInterval(interval);
    }, [load]);

    const formatVolume = (v) => {
        if (!v) return '—';
        if (v >= 1e9) return `${(v / 1e9).toFixed(2)} B`;
        if (v >= 1e7) return `${(v / 1e7).toFixed(2)} Cr`;
        if (v >= 1e5) return `${(v / 1e5).toFixed(2)} L`;
        if (v >= 1e3) return `${(v / 1e3).toFixed(1)} K`;
        return v.toString();
    };

    const formatNum = (n) =>
        n != null ? Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—';

    // ── Loading skeleton ──
    if (loading && !data) {
        return (
            <Card className="overflow-hidden animate-pulse">
                <div className="h-14 bg-gradient-to-r from-indigo-500/20 to-cyan-500/20" />
                <div className="p-6 space-y-6">
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="h-20 bg-white/5 rounded-xl" />
                        ))}
                    </div>
                    <div className="h-32 bg-white/5 rounded-xl" />
                </div>
            </Card>
        );
    }

    if (error && !data) {
        return (
            <Card className="p-6 text-center">
                <Activity className="w-10 h-10 mx-auto mb-2 text-red-400 opacity-60" />
                <p className="text-red-400 text-sm mb-2">{error}</p>
                <button onClick={load} className="text-xs text-blue-400 underline">Retry</button>
            </Card>
        );
    }

    if (!data) return null;

    const { indices = [], breadth = {}, volume, sectors = [] } = data;
    const bullPct = breadth.bullish_pct ?? 50;

    return (
        <Card className="overflow-hidden industry-section-card market-overview-shell">
            {/* ── Header ── */}
            <div className="px-5 py-3.5 bg-gradient-to-r from-indigo-600/25 via-blue-600/20 to-cyan-500/20 border-b border-white/10 flex items-center justify-between market-overview-header">
                <h3 className="text-lg font-black text-white flex items-center gap-2 market-overview-title">
                    <Globe className="w-5 h-5 text-cyan-400" />
                    Market Overview
                    <span className="ml-2 text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 border border-green-500/30 market-overview-live-chip">
                        LIVE
                    </span>
                </h3>
                <div className="flex items-center gap-3">
                    {lastUpdated && (
                        <span className="text-[10px] text-gray-400 flex items-center gap-1 market-overview-updated">
                            <Clock size={10} />
                            {lastUpdated.toLocaleTimeString()}
                        </span>
                    )}
                    <button
                        onClick={load}
                        disabled={refreshing}
                        className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition market-overview-refresh"
                        title="Refresh"
                    >
                        <RefreshCw size={14} className={`text-gray-400 ${refreshing ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            <div className="p-5 space-y-5 market-overview-body">
                {/* ── Index Ticker Cards ── */}
                {indices.length > 0 && (
                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 market-overview-index-grid">
                        {indices.map((idx) => {
                            const changePct = Number(idx.change_pct ?? 0);
                            const changeValue = Number(idx.change ?? 0);
                            const up = changePct >= 0;
                            return (
                                <div
                                    key={idx.symbol}
                                    className={`relative rounded-xl p-3.5 border transition-all hover:scale-[1.02] cursor-default overflow-hidden market-overview-index-item ${up ? 'market-overview-index-up' : 'market-overview-index-down'}`}
                                    style={{
                                        borderColor: up ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.25)',
                                        background: up
                                            ? 'linear-gradient(145deg, rgba(34,197,94,0.08) 0%, rgba(34,197,94,0.02) 100%)'
                                            : 'linear-gradient(145deg, rgba(239,68,68,0.08) 0%, rgba(239,68,68,0.02) 100%)',
                                    }}
                                >
                                    {/* Glow accent */}
                                    <div
                                        className="absolute rounded-full pointer-events-none"
                                        style={{
                                            top: '-1.5rem',
                                            right: '-1.5rem',
                                            width: '4rem',
                                            height: '4rem',
                                            filter: 'blur(40px)',
                                            opacity: 0.3,
                                            background: up ? '#22c55e' : '#ef4444',
                                        }}
                                    />
                                    <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">{idx.symbol}</p>
                                    <p className="text-lg font-black text-white leading-tight">{formatNum(idx.value)}</p>
                                    <div className={`flex items-center gap-1 mt-1 ${up ? 'text-green-400' : 'text-red-400'}`}>
                                        {up ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                                        <span className="text-sm font-bold">
                                            {up ? '+' : ''}{changePct.toFixed(2)}%
                                        </span>
                                        <span className="text-[10px] text-gray-500 ml-1">
                                            ({up ? '+' : ''}{formatNum(changeValue)})
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* ── Market Breadth + Volume ── */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 market-overview-metrics-grid">
                    {/* Sentiment Gauge */}
                    <div className="md:col-span-2 bg-white/5 rounded-xl p-4 border border-white/5 market-overview-breadth">
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="text-sm font-bold text-gray-200 flex items-center gap-2 market-overview-subtitle">
                                <BarChart3 size={15} className="text-blue-400" />
                                Market Breadth
                            </h4>
                            <span className={`text-sm font-black ${bullPct >= 50 ? 'text-green-400' : 'text-red-400'}`}>
                                {bullPct}% Bullish
                            </span>
                        </div>
                        {/* Progress bar */}
                        <div className="h-4 bg-gray-800 rounded-full overflow-hidden flex mb-3 relative">
                            <div
                                className="h-full transition-all duration-700 rounded-l-full"
                                style={{
                                    width: `${bullPct}%`,
                                    background: 'linear-gradient(90deg, #22c55e 0%, #4ade80 100%)',
                                }}
                            />
                            <div
                                className="h-full transition-all duration-700 rounded-r-full"
                                style={{
                                    width: `${100 - bullPct}%`,
                                    background: 'linear-gradient(90deg, #f87171 0%, #ef4444 100%)',
                                }}
                            />
                            {/* Center marker */}
                            <div
                                className="absolute inset-y-0"
                                style={{ left: '50%', width: '1px', background: 'rgba(255,255,255,0.3)' }}
                            />
                        </div>
                        <div className="grid grid-cols-3 gap-3 text-center">
                            <div>
                                <p className="text-xl font-black text-green-400">{breadth.advancers ?? '—'}</p>
                                <p className="text-[10px] text-gray-500 uppercase tracking-wider">Advancers</p>
                            </div>
                            <div>
                                <p className="text-xl font-black text-gray-400">{breadth.unchanged ?? '—'}</p>
                                <p className="text-[10px] text-gray-500 uppercase tracking-wider">Unchanged</p>
                            </div>
                            <div>
                                <p className="text-xl font-black text-red-400">{breadth.decliners ?? '—'}</p>
                                <p className="text-[10px] text-gray-500 uppercase tracking-wider">Decliners</p>
                            </div>
                        </div>
                    </div>

                    {/* Volume Card */}
                    <div className="bg-white/5 rounded-xl p-4 border border-white/5 flex flex-col justify-between market-overview-volume">
                        <div>
                            <h4 className="text-sm font-bold text-gray-200 flex items-center gap-2 mb-2 market-overview-subtitle">
                                <Zap size={15} className="text-yellow-400" />
                                Market Volume
                            </h4>
                            <p className="text-2xl font-black text-white">{formatVolume(volume)}</p>
                            <p className="text-[10px] text-gray-500 mt-1">Total shares traded today</p>
                        </div>
                        <div className="mt-3 pt-3 border-t border-white/5">
                            <p className="text-[10px] text-gray-500">Total Stocks</p>
                            <p className="text-lg font-black text-blue-400">{breadth.total ?? '—'}</p>
                        </div>
                    </div>
                </div>

                {/* ── Sectoral Heatmap ── */}
                {sectors.length > 0 && (
                    <div className="market-overview-sectors">
                        <h4 className="text-sm font-bold text-gray-200 mb-3 flex items-center gap-2 market-overview-subtitle">
                            <Activity size={15} className="text-purple-400" />
                            Sector Performance
                        </h4>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 market-overview-sector-grid">
                            {sectors.map((sec) => {
                                const changePct = Number(sec.change_pct ?? 0);
                                const up = changePct >= 0;
                                // Intensity based on magnitude
                                const intensity = Math.min(Math.abs(changePct) / 3, 1);
                                const bg = up
                                    ? `rgba(34,197,94,${0.06 + intensity * 0.2})`
                                    : `rgba(239,68,68,${0.06 + intensity * 0.2})`;
                                const border = up
                                    ? `rgba(34,197,94,${0.15 + intensity * 0.3})`
                                    : `rgba(239,68,68,${0.15 + intensity * 0.3})`;

                                return (
                                    <div
                                        key={sec.name}
                                        className={`rounded-lg p-3 text-center transition-all hover:scale-[1.03] cursor-default market-overview-sector-item ${up ? 'market-overview-sector-up' : 'market-overview-sector-down'}`}
                                        style={{ background: bg, border: `1px solid ${border}` }}
                                    >
                                        <p className="text-xs font-semibold text-gray-300 mb-1">{sec.name}</p>
                                        <p className={`text-sm font-black ${up ? 'text-green-400' : 'text-red-400'}`}>
                                            {up ? '+' : ''}{changePct.toFixed(2)}%
                                        </p>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}
            </div>
        </Card>
    );
};

export default MarketOverview;
