import React, { useState, useEffect, useCallback } from 'react';
import {
    Brain, RefreshCw, Clock, TrendingUp, ArrowUpRight, ArrowDownRight,
    Target, Flame, Zap, BarChart2, ChevronRight, Shield
} from 'lucide-react';
import { Card } from '../ui';
import { fetchRecommendations } from '../../services/api';

const formatRecommendationError = (rawError) => {
    const message = String(rawError?.message || rawError || 'Failed to load recommendations').trim();
    const lowered = message.toLowerCase();

    if (lowered.includes('cancelled') || lowered.includes('aborted')) {
        return 'Recommendation refresh was interrupted. Retry in a few seconds.';
    }

    if (lowered.includes('timeout')) {
        return 'Recommendation engine timed out. Please retry shortly.';
    }

    if (lowered.includes('network') || lowered.includes('fetch')) {
        return 'Network issue while loading recommendations. Check your connection and retry.';
    }

    return message;
};

/**
 * StockRecommendations — AI-powered stock pick suggestions with live prices,
 * multi-strategy confidence, and rich visual cards.
 * Auto-refreshes every 90 seconds.
 */
export const StockRecommendations = ({ onTickerClick }) => {
    const [recs, setRecs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [timeframe, setTimeframe] = useState('weekly');
    const [meta, setMeta] = useState({
        partial: false,
        fallbackUsed: false,
        effectiveSource: 'strategy_screens',
        timedOutStrategies: [],
        timeframe: 'weekly',
    });

    const timeframeLabels = {
        daily: 'Daily',
        weekly: 'Weekly',
        monthly: 'Monthly',
    };
    const activeTimeframeLabel = timeframeLabels[meta.timeframe] || timeframeLabels[timeframe] || 'Weekly';

    const formatTicker = (ticker) => String(ticker || '').trim().replace(/^\^+/, '').toUpperCase();

    const load = useCallback(async () => {
        if (!recs.length) setLoading(true);
        setRefreshing(true);
        setError(null);
        try {
            const data = await fetchRecommendations(timeframe);
            setRecs(data?.recommendations || []);
            setMeta({
                partial: Boolean(data?.partial),
                fallbackUsed: Boolean(data?.fallback_used),
                effectiveSource: data?.effective_source || 'strategy_screens',
                timedOutStrategies: data?.timed_out_strategies || [],
                timeframe: data?.timeframe || timeframe,
            });
            setLastUpdated(new Date());
        } catch (e) {
            setError(formatRecommendationError(e));
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [recs.length, timeframe]);

    useEffect(() => { load(); }, [load]);

    // Auto-refresh every 20s
    useEffect(() => {
        const interval = setInterval(load, 20_000);
        return () => clearInterval(interval);
    }, [load]);

    const formatPrice = (n) =>
        n != null ? `₹${Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '—';

    const formatVol = (v) => {
        if (!v) return null;
        if (v >= 1e7) return `${(v / 1e7).toFixed(1)} Cr`;
        if (v >= 1e5) return `${(v / 1e5).toFixed(1)} L`;
        if (v >= 1e3) return `${(v / 1e3).toFixed(0)} K`;
        return v.toString();
    };

    const formatMcap = (mc) => {
        if (!mc) return null;
        if (mc >= 1e12) return `₹${(mc / 1e12).toFixed(1)} T`;
        if (mc >= 1e9) return `₹${(mc / 1e9).toFixed(1)} B`;
        if (mc >= 1e7) return `₹${(mc / 1e7).toFixed(0)} Cr`;
        return `₹${mc}`;
    };

    const toTitleCase = (value) =>
        String(value || '')
            .split('_')
            .filter(Boolean)
            .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
            .join(' ');

    const confColor = (conf) => {
        if (conf >= 90) return { bg: 'from-green-500 to-emerald-500', ring: 'ring-green-500/40', text: 'text-green-400' };
        if (conf >= 70) return { bg: 'from-emerald-500 to-teal-500', ring: 'ring-emerald-500/30', text: 'text-emerald-400' };
        if (conf >= 50) return { bg: 'from-yellow-500 to-amber-500', ring: 'ring-yellow-500/30', text: 'text-yellow-400' };
        return { bg: 'from-gray-500 to-gray-600', ring: 'ring-gray-500/30', text: 'text-gray-400' };
    };

    const badgeCls = (label) => {
        switch (label) {
            case 'VERY HIGH': return 'bg-green-500/20 text-green-400 border-green-500/30';
            case 'HIGH':      return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
            case 'MODERATE':  return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
            default:          return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
        }
    };

    const stratMeta = (s) => {
        const strategy = String(s || '').toLowerCase();

        if (strategy.startsWith('fallback_')) {
            const fallbackName = toTitleCase(strategy.replace('fallback_', ''));
            return {
                icon: Shield,
                color: 'text-cyan-300',
                label: `${fallbackName} Fallback`,
            };
        }

        switch (strategy) {
            case 'momentum':
                return { icon: Flame, color: 'text-orange-400', label: 'Momentum' };
            case 'trend_following':
                return { icon: TrendingUp, color: 'text-blue-400', label: 'Trend Following' };
            case 'breakout':
                return { icon: Zap, color: 'text-yellow-400', label: 'Breakout' };
            default:
                return { icon: BarChart2, color: 'text-gray-300', label: toTitleCase(strategy) };
        }
    };

    return (
        <Card className="overflow-hidden industry-section-card recommendations-shell">
            {/* ── Header ── */}
            <div className="px-5 py-3.5 border-b border-white/10 flex items-center justify-between recommendations-header">
                <h3 className="text-lg font-black flex items-center gap-2 recommendations-title">
                    <Brain className="w-5 h-5 text-blue-400" />
                    AI Recommendations
                    <span className="ml-2 text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 recommendations-mode-chip">
                        <Shield size={8} className="inline mr-0.5 -mt-px" />
                        MULTI-STRATEGY
                    </span>
                </h3>
                <div className="flex items-center gap-3">
                    {lastUpdated && (
                        <span className="text-[10px] text-gray-400 flex items-center gap-1 recommendations-last-updated">
                            <Clock size={10} />
                            {lastUpdated.toLocaleTimeString()}
                        </span>
                    )}
                    <button
                        onClick={load}
                        disabled={refreshing}
                        className="p-1.5 rounded-lg transition recommendations-refresh-btn"
                        title="Refresh"
                    >
                        <RefreshCw size={14} className={`text-gray-400 ${refreshing ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            <div className="p-5">
                <div className="flex flex-wrap items-center gap-2 mb-4 recommendations-meta">
                    <span className="text-xs text-gray-500 recommendations-meta-copy">
                        {timeframeLabels[meta.timeframe] || 'Weekly'} picks synced to realtime market snapshots.
                    </span>
                    <div className="recommendations-timeframe-row" role="tablist" aria-label="Recommendation timeframe">
                        {Object.entries(timeframeLabels).map(([value, label]) => (
                            <button
                                key={value}
                                type="button"
                                role="tab"
                                aria-selected={timeframe === value}
                                onClick={() => setTimeframe(value)}
                                className={`recommendations-timeframe-btn ${timeframe === value ? 'active' : ''}`}
                            >
                                {label}
                            </button>
                        ))}
                    </div>
                    {meta.partial && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full border border-yellow-500/30 bg-yellow-500/15 text-yellow-300 recommendations-meta-chip recommendations-meta-chip-warning">
                            Partial strategy run
                        </span>
                    )}
                    {meta.fallbackUsed && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full border border-cyan-500/30 bg-cyan-500/15 text-cyan-300 recommendations-meta-chip recommendations-meta-chip-info">
                            Fast DB fallback
                        </span>
                    )}
                    {meta.timedOutStrategies.length > 0 && (
                        <span className="text-[10px] text-gray-500 recommendations-meta-chip recommendations-meta-chip-timeout">
                            timeout: {meta.timedOutStrategies.join(', ')}
                        </span>
                    )}
                </div>

                {/* Loading skeleton */}
                {loading && !recs.length && (
                    <div className="space-y-3">
                        {[...Array(5)].map((_, i) => (
                            <div key={i} className="animate-pulse rounded-xl bg-white/5 p-4 recommendation-skeleton">
                                <div className="flex items-center gap-3">
                                    <div className="w-11 h-11 rounded-xl bg-white/10" />
                                    <div className="flex-1 space-y-2">
                                        <div className="h-3.5 bg-white/10 rounded w-28" />
                                        <div className="h-2.5 bg-white/10 rounded w-48" />
                                    </div>
                                    <div className="h-8 w-20 bg-white/10 rounded-lg" />
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Error */}
                {error && !loading && (
                    <div className="recommendations-state-card recommendations-state-error" role="status" aria-live="polite">
                        <Target className="recommendations-state-icon" />
                        <div className="recommendations-state-content">
                            <p className="recommendations-state-title">Recommendations temporarily unavailable</p>
                            <p className="recommendations-state-copy">{error}</p>
                            <button onClick={load} className="recommendations-state-action" type="button">
                                Retry now
                            </button>
                        </div>
                    </div>
                )}

                {/* Empty */}
                {!loading && !error && recs.length === 0 && (
                    <div className="recommendations-state-card recommendations-state-empty" role="status" aria-live="polite">
                        <Target className="recommendations-state-icon" />
                        <div className="recommendations-state-content">
                            <p className="recommendations-state-title">No high-conviction recommendations right now</p>
                            <p className="recommendations-state-copy">
                                Signals are below confidence thresholds. Refresh shortly for the next strategy cycle.
                            </p>
                            <button onClick={load} className="recommendations-state-action" type="button">
                                Refresh recommendations
                            </button>
                        </div>
                    </div>
                )}

                {/* ── Recommendation Cards ── */}
                {recs.length > 0 && (
                    <div className="space-y-3 recommendations-list">
                        {recs.map((r, idx) => {
                            const confidence = Number(r.confidence ?? 0);
                            const confidenceClamped = Math.max(0, Math.min(100, confidence));
                            const changePct = Number(r.change_pct ?? 0);
                            const up = changePct >= 0;
                            const cc = confColor(confidence);
                            const dayLow = Number(r.day_low);
                            const dayHigh = Number(r.day_high);
                            const dayRange = Number.isFinite(dayLow) && Number.isFinite(dayHigh) && dayHigh > dayLow;
                            const dayRangePct = dayRange
                                ? ((Number(r.price ?? dayLow) - dayLow) / (dayHigh - dayLow)) * 100
                                : null;

                            return (
                                <button
                                    key={r.ticker}
                                    onClick={() => onTickerClick?.(r.ticker)}
                                    className="w-full rounded-xl border transition-all p-4 text-left group recommendation-row recommendation-row-card"
                                >
                                    <div className="flex items-start gap-3 recommendation-row-layout w-full">
                                        {/* Rank + confidence ring */}
                                        <div className="relative shrink-0">
                                            <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${cc.bg} flex items-center justify-center text-white font-black text-base ring-2 ${cc.ring} shadow-lg recommendation-rank-badge`}>
                                                {idx + 1}
                                            </div>
                                            {r.live && (
                                                <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-green-500 border-2 animate-pulse recommendation-live-dot" title="Live price" />
                                            )}
                                        </div>

                                        {/* Main info */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 flex-wrap recommendation-heading-row">
                                                <span className="font-black text-sm transition recommendation-ticker">
                                                    {formatTicker(r.ticker)}
                                                </span>
                                                <span className="recommendation-timeframe-pill">
                                                    {activeTimeframeLabel}
                                                </span>
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full border font-semibold recommendation-conviction-pill ${badgeCls(r.confidence_label)}`}>
                                                    {r.confidence_label}
                                                </span>
                                                {r.live && (
                                                    <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-500/15 text-green-400 border border-green-500/20 font-medium recommendation-live-chip">
                                                        LIVE
                                                    </span>
                                                )}
                                            </div>

                                            {/* Strategy pills */}
                                            <div className="flex items-center gap-2 mt-1.5 flex-wrap recommendation-strategy-row">
                                                {(r.strategies || []).map(s => {
                                                    const m = stratMeta(s);
                                                    const Icon = m.icon;
                                                    return (
                                                        <span
                                                            key={s}
                                                            className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md ${m.color} font-medium recommendation-pill recommendation-strategy-pill`}
                                                        >
                                                            <Icon size={10} />
                                                            {m.label}
                                                        </span>
                                                    );
                                                })}
                                            </div>

                                            {/* Day range bar (if live data available) */}
                                            {dayRange && (
                                                <div className="mt-2 flex items-center gap-2">
                                                    <span className="text-[9px] w-10 text-right recommendation-range-label">
                                                        {formatPrice(r.day_low).replace('₹', '')}
                                                    </span>
                                                    <div className="flex-1 h-1 rounded-full overflow-hidden relative recommendation-range-bar">
                                                        <div className="recommendation-range-track" />
                                                        <div
                                                            className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full"
                                                            style={{ width: `${Math.max(2, Math.min(98, dayRangePct))}%` }}
                                                        />
                                                    </div>
                                                    <span className="text-[9px] w-10 recommendation-range-label">
                                                        {formatPrice(r.day_high).replace('₹', '')}
                                                    </span>
                                                </div>
                                            )}

                                            {/* Extra live stats */}
                                            {(r.volume || r.market_cap) && (
                                                <div className="flex items-center gap-3 mt-1.5 recommendation-micro-row">
                                                    {r.volume && (
                                                        <span className="text-[9px] recommendation-micro-stat">
                                                            Volume <span className="font-medium recommendation-micro-value">{formatVol(r.volume)}</span>
                                                        </span>
                                                    )}
                                                    {r.market_cap && (
                                                        <span className="text-[9px] recommendation-micro-stat">
                                                            MCap <span className="font-medium recommendation-micro-value">{formatMcap(r.market_cap)}</span>
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                        </div>

                                        {/* Price + Change + Confidence */}
                                        <div className="shrink-0 text-right flex flex-col items-end gap-1.5 recommendation-right-rail">
                                            <div>
                                                <p className="text-sm font-black leading-tight recommendation-price">
                                                    {formatPrice(r.price)}
                                                </p>
                                                {r.change_pct != null && r.change_pct !== 0 && (
                                                    <div className={`flex items-center gap-0.5 justify-end recommendation-price-change ${up ? 'text-green-400' : 'text-red-400'}`}>
                                                        {up ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                                        <span className="text-xs font-bold">
                                                            {up ? '+' : ''}{changePct.toFixed(2)}%
                                                        </span>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Confidence arc / bar */}
                                            <div className={`recommendation-confidence-badge ${cc.text}`}>
                                                <span className="recommendation-confidence-badge-label">Confidence</span>
                                                <span className="recommendation-confidence-badge-value">{confidenceClamped}%</span>
                                            </div>
                                        </div>

                                        <ChevronRight size={16} className="transition shrink-0 mt-2 recommendation-row-chevron" />
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                )}
            </div>
        </Card>
    );
};

export default StockRecommendations;
