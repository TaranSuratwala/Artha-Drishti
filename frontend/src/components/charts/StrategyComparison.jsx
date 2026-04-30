import React, { useState, useMemo } from 'react';
import {
    TrendingUp, Target, BarChart2,
    Award, Shield, Activity, ChevronDown, ChevronUp,
    ArrowUpRight, Minus, Info
} from 'lucide-react';

const EMPTY_COMPARISON = [];

/**
 * StrategyComparison - Comprehensive visual comparison of multiple strategy backtest results
 * Displays strategy cards, detailed metrics table, risk analysis, and rankings.
 */
export const StrategyComparison = ({ data, className = '' }) => {
    const [sortColumn, setSortColumn] = useState('sharpe_ratio');
    const [sortAsc, setSortAsc] = useState(false);
    const [activeView, setActiveView] = useState('overview'); // overview | risk | trades | regime
    const comparison = data?.comparison ?? EMPTY_COMPARISON;
    const benchmark = data?.benchmark;
    const ticker = data?.ticker;
    const trading_days = data?.trading_days;

    // Sorted comparison
    const sorted = useMemo(() => {
        const arr = [...comparison];
        arr.sort((a, b) => {
            const va = a[sortColumn] ?? 0;
            const vb = b[sortColumn] ?? 0;
            return sortAsc ? va - vb : vb - va;
        });
        return arr;
    }, [comparison, sortColumn, sortAsc]);

    const handleSort = (col) => {
        if (sortColumn === col) setSortAsc(!sortAsc);
        else { setSortColumn(col); setSortAsc(false); }
    };

    const SortIcon = ({ col }) => {
        if (sortColumn !== col) return <Minus className="w-3 h-3 opacity-30" />;
        return sortAsc ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />;
    };

    const best = useMemo(() => {
        if (!comparison.length) return {};
        return {
            sharpe: Math.max(...comparison.map(s => s.sharpe_ratio || 0)),
            return_pct: Math.max(...comparison.map(s => s.total_return_pct || 0)),
            win_rate: Math.max(...comparison.map(s => s.win_rate_pct || 0)),
            sortino: Math.max(...comparison.map(s => s.sortino_ratio || 0)),
            calmar: Math.max(...comparison.map(s => s.calmar_ratio || 0)),
            profit_factor: Math.max(...comparison.map(s => s.profit_factor || 0)),
            min_dd: Math.min(...comparison.map(s => s.max_drawdown_pct || 0)),
        };
    }, [comparison]);

    if (!comparison.length) {
        return (
            <div className="p-8 text-center text-gray-400">
                <BarChart2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No comparison data available</p>
            </div>
        );
    }

    const gradeStrategy = (s) => {
        let score = 0;
        if (s.sharpe_ratio > 1) score += 3; else if (s.sharpe_ratio > 0.5) score += 2; else if (s.sharpe_ratio > 0) score += 1;
        if (s.total_return_pct > 20) score += 3; else if (s.total_return_pct > 10) score += 2; else if (s.total_return_pct > 0) score += 1;
        if (s.win_rate_pct > 55) score += 2; else if (s.win_rate_pct > 45) score += 1;
        if (s.max_drawdown_pct < 10) score += 2; else if (s.max_drawdown_pct < 20) score += 1;
        if (s.profit_factor > 1.5) score += 2; else if (s.profit_factor > 1) score += 1;
        if (score >= 10) return { grade: 'A', color: 'text-green-400', bg: 'bg-green-500/20' };
        if (score >= 7) return { grade: 'B', color: 'text-blue-400', bg: 'bg-blue-500/20' };
        if (score >= 4) return { grade: 'C', color: 'text-yellow-400', bg: 'bg-yellow-500/20' };
        return { grade: 'D', color: 'text-red-400', bg: 'bg-red-500/20' };
    };

    // Colors for each strategy
    const colors = [
        { gradient: 'from-blue-500 to-blue-600' },
        { gradient: 'from-purple-500 to-purple-600' },
        { gradient: 'from-emerald-500 to-emerald-600' },
        { gradient: 'from-amber-500 to-amber-600' },
        { gradient: 'from-pink-500 to-pink-600' },
        { gradient: 'from-cyan-500 to-cyan-600' },
        { gradient: 'from-indigo-500 to-indigo-600' },
        { gradient: 'from-rose-500 to-rose-600' },
        { gradient: 'from-teal-500 to-teal-600' },
        { gradient: 'from-orange-500 to-orange-600' },
        { gradient: 'from-violet-500 to-violet-600' },
    ];

    const fmt = (v, d = 2) => (v != null ? Number(v).toFixed(d) : '—');
    const fmtPct = (v, d = 2) => v != null ? `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(d)}%` : '—';

    const tabBtnClass = (id) =>
        `px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${activeView === id
            ? 'bg-white/15 text-white border border-white/20'
            : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent'
        }`;

    return (
        <div className={`space-y-6 strategy-comparison-shell ${className}`.trim()}>
            {/* Header Info + Benchmark */}
            <div className="flex flex-wrap gap-4 justify-between items-center">
                <div className="text-sm text-gray-400 space-x-4">
                    <span>Ticker: <span className="text-white font-bold">{ticker}</span></span>
                    <span>Period: <span className="text-white font-medium">{data.start_date}</span> → <span className="text-white font-medium">{data.end_date}</span></span>
                    {trading_days && <span>({trading_days} days)</span>}
                </div>
                <div className="text-sm text-gray-400">
                    Capital: <span className="text-white font-medium">₹{(data.initial_capital || 100000).toLocaleString()}</span>
                </div>
            </div>

            {/* Benchmark Bar */}
            {benchmark && (
                <div className="flex items-center gap-4 px-4 py-3 bg-white/5 rounded-xl border border-white/10">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-gray-400" />
                        <span className="text-sm font-semibold text-gray-300">{benchmark.name}</span>
                    </div>
                    <span className={`text-sm font-bold ${benchmark.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {fmtPct(benchmark.total_return_pct)}
                    </span>
                    <span className="text-xs text-gray-500">Annual: {fmtPct(benchmark.annualized_return_pct)}</span>
                    <span className="text-xs text-gray-500">Sharpe: {fmt(benchmark.sharpe_ratio, 3)}</span>
                </div>
            )}

            {/* View Tabs */}
            <div className="flex gap-2 flex-wrap">
                <button onClick={() => setActiveView('overview')} className={tabBtnClass('overview')}>
                    <span className="flex items-center gap-1"><BarChart2 className="w-3.5 h-3.5" /> Overview</span>
                </button>
                <button onClick={() => setActiveView('risk')} className={tabBtnClass('risk')}>
                    <span className="flex items-center gap-1"><Shield className="w-3.5 h-3.5" /> Risk Analysis</span>
                </button>
                <button onClick={() => setActiveView('trades')} className={tabBtnClass('trades')}>
                    <span className="flex items-center gap-1"><Activity className="w-3.5 h-3.5" /> Trade Statistics</span>
                </button>
                <button onClick={() => setActiveView('regime')} className={tabBtnClass('regime')}>
                    <span className="flex items-center gap-1"><Target className="w-3.5 h-3.5" /> Regime Analysis</span>
                </button>
            </div>

            {/* ═══════════════ OVERVIEW TAB ═══════════════ */}
            {activeView === 'overview' && (
                <>
                    {/* Strategy Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {sorted.map((s, idx) => {
                            const color = colors[idx % colors.length];
                            const { grade, color: gradeColor, bg: gradeBg } = gradeStrategy(s);
                            const isPositive = (s.total_return_pct || 0) >= 0;
                            const beatsBenchmark = benchmark ? s.total_return_pct > benchmark.total_return_pct : false;

                            return (
                                <div key={s.strategy} className="bg-white/5 rounded-2xl border border-white/10 overflow-hidden hover:border-white/20 transition-all">
                                    <div className={`px-4 py-3 bg-gradient-to-r ${color.gradient} flex justify-between items-center`}>
                                        <h4 className="font-bold text-white capitalize text-lg">{s.strategy.replace(/_/g, ' ')}</h4>
                                        <div className="flex items-center gap-2">
                                            {s.rank && <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full text-white font-bold">#{s.rank}</span>}
                                            <span className={`text-lg font-black ${gradeColor} ${gradeBg} px-2 py-0.5 rounded-lg`}>{grade}</span>
                                        </div>
                                    </div>
                                    <div className="p-4 space-y-3">
                                        {/* Return bar */}
                                        <div className="flex justify-between items-center">
                                            <span className="text-xs text-gray-400 flex items-center gap-1">
                                                <TrendingUp className="w-3 h-3" /> Return
                                            </span>
                                            <div className="flex items-center gap-2">
                                                <span className={`font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                                                    {fmtPct(s.total_return_pct)}
                                                </span>
                                                {beatsBenchmark && <ArrowUpRight className="w-3.5 h-3.5 text-green-400" />}
                                            </div>
                                        </div>
                                        {/* Key metrics 2x3 grid */}
                                        <div className="grid grid-cols-3 gap-2 pt-2 border-t border-white/10">
                                            <div className="text-center p-1.5 bg-white/5 rounded-lg">
                                                <p className="text-[10px] text-gray-500">Sharpe</p>
                                                <p className={`font-bold text-sm ${s.sharpe_ratio >= 1 ? 'text-green-400' : s.sharpe_ratio > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                    {fmt(s.sharpe_ratio)}
                                                </p>
                                            </div>
                                            <div className="text-center p-1.5 bg-white/5 rounded-lg">
                                                <p className="text-[10px] text-gray-500">Sortino</p>
                                                <p className={`font-bold text-sm ${s.sortino_ratio > 1 ? 'text-green-400' : s.sortino_ratio > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                    {fmt(s.sortino_ratio)}
                                                </p>
                                            </div>
                                            <div className="text-center p-1.5 bg-white/5 rounded-lg">
                                                <p className="text-[10px] text-gray-500">Calmar</p>
                                                <p className="font-bold text-sm text-white">{fmt(s.calmar_ratio)}</p>
                                            </div>
                                            <div className="text-center p-1.5 bg-white/5 rounded-lg">
                                                <p className="text-[10px] text-gray-500">Max DD</p>
                                                <p className="font-bold text-sm text-red-400">{fmt(s.max_drawdown_pct, 1)}%</p>
                                            </div>
                                            <div className="text-center p-1.5 bg-white/5 rounded-lg">
                                                <p className="text-[10px] text-gray-500">Win Rate</p>
                                                <p className="font-bold text-sm text-emerald-400">{fmt(s.win_rate_pct, 1)}%</p>
                                            </div>
                                            <div className="text-center p-1.5 bg-white/5 rounded-lg">
                                                <p className="text-[10px] text-gray-500">Trades</p>
                                                <p className="font-bold text-sm text-blue-400">{s.total_trades}</p>
                                            </div>
                                        </div>
                                        {/* Profit Factor + Final Capital */}
                                        <div className="flex justify-between text-xs pt-1 border-t border-white/5">
                                            <span className="text-gray-500">PF: <span className={`font-bold ${(s.profit_factor || 0) > 1.5 ? 'text-green-400' : (s.profit_factor || 0) > 1 ? 'text-yellow-400' : 'text-red-400'}`}>{fmt(s.profit_factor)}</span></span>
                                            <span className="text-gray-500">Final: <span className="text-white font-bold">₹{Math.round(s.final_capital || 0).toLocaleString()}</span></span>
                                            {s.excess_return_pct != null && (
                                                <span className="text-gray-500">
                                                    vs B&H: <span className={`font-bold ${s.excess_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmtPct(s.excess_return_pct)}</span>
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    {/* Comprehensive Summary Table */}
                    <div className="overflow-x-auto strategy-comparison-scroll industry-table-scroll">
                        <table className="w-full text-xs strategy-comparison-table strategy-comparison-table-overview">
                            <thead>
                                <tr className="bg-white/5">
                                    {[
                                        { key: 'strategy', label: 'Strategy', align: 'left' },
                                        { key: 'total_return_pct', label: 'Return' },
                                        { key: 'annualized_return_pct', label: 'CAGR' },
                                        { key: 'sharpe_ratio', label: 'Sharpe' },
                                        { key: 'sortino_ratio', label: 'Sortino' },
                                        { key: 'calmar_ratio', label: 'Calmar' },
                                        { key: 'max_drawdown_pct', label: 'Max DD' },
                                        { key: 'volatility_annual_pct', label: 'Vol (ann)' },
                                        { key: 'win_rate_pct', label: 'Win %' },
                                        { key: 'profit_factor', label: 'PF' },
                                        { key: 'total_trades', label: 'Trades' },
                                        { key: 'expectancy_per_trade', label: 'Expect.' },
                                        { key: 'final_capital', label: 'Final ₹' },
                                    ].map(col => (
                                        <th
                                            key={col.key}
                                            className={`px-3 py-2 cursor-pointer hover:bg-white/10 transition select-none whitespace-nowrap ${col.align === 'left' ? 'text-left' : 'text-right'}`}
                                            onClick={() => handleSort(col.key)}
                                        >
                                            <span className="inline-flex items-center gap-1">
                                                {col.label} <SortIcon col={col.key} />
                                            </span>
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {sorted.map((s) => {
                                    const isBestSharpe = s.sharpe_ratio === best.sharpe;
                                    const isBestReturn = s.total_return_pct === best.return_pct;
                                    return (
                                        <tr key={s.strategy} className="hover:bg-white/5 transition">
                                            <td className="px-3 py-2 font-bold capitalize text-white whitespace-nowrap">
                                                {s.rank && <span className="text-gray-500 mr-1">#{s.rank}</span>}
                                                {s.strategy.replace(/_/g, ' ')}
                                            </td>
                                            <td className={`px-3 py-2 text-right font-bold ${(s.total_return_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'} ${isBestReturn ? 'underline decoration-dotted' : ''}`}>
                                                {fmtPct(s.total_return_pct)}
                                            </td>
                                            <td className={`px-3 py-2 text-right ${(s.annualized_return_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {fmtPct(s.annualized_return_pct)}
                                            </td>
                                            <td className={`px-3 py-2 text-right font-bold ${isBestSharpe ? 'text-yellow-300 underline decoration-dotted' : s.sharpe_ratio >= 1 ? 'text-green-400' : s.sharpe_ratio > 0 ? 'text-white' : 'text-red-400'}`}>
                                                {fmt(s.sharpe_ratio)}
                                            </td>
                                            <td className={`px-3 py-2 text-right ${s.sortino_ratio > 1 ? 'text-green-400' : 'text-white'}`}>
                                                {fmt(s.sortino_ratio)}
                                            </td>
                                            <td className="px-3 py-2 text-right text-white">{fmt(s.calmar_ratio)}</td>
                                            <td className="px-3 py-2 text-right text-red-400">{fmt(s.max_drawdown_pct, 1)}%</td>
                                            <td className="px-3 py-2 text-right text-gray-300">{fmt(s.volatility_annual_pct, 1)}%</td>
                                            <td className={`px-3 py-2 text-right ${(s.win_rate_pct || 0) > 55 ? 'text-green-400' : (s.win_rate_pct || 0) > 45 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {fmt(s.win_rate_pct, 1)}%
                                            </td>
                                            <td className={`px-3 py-2 text-right ${(s.profit_factor || 0) > 1.5 ? 'text-green-400' : (s.profit_factor || 0) > 1 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                {fmt(s.profit_factor)}
                                            </td>
                                            <td className="px-3 py-2 text-right text-gray-300">{s.total_trades}</td>
                                            <td className={`px-3 py-2 text-right ${(s.expectancy_per_trade || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {fmt(s.expectancy_per_trade)}
                                            </td>
                                            <td className="px-3 py-2 text-right text-white font-semibold whitespace-nowrap">
                                                ₹{Math.round(s.final_capital || 0).toLocaleString()}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </>
            )}

            {/* ═══════════════ RISK ANALYSIS TAB ═══════════════ */}
            {activeView === 'risk' && (
                <div className="space-y-4">
                    <div className="overflow-x-auto strategy-comparison-scroll industry-table-scroll">
                        <table className="w-full text-xs strategy-comparison-table strategy-comparison-table-risk">
                            <thead>
                                <tr className="bg-white/5">
                                    <th className="text-left px-3 py-2">Strategy</th>
                                    <th className="text-right px-3 py-2">Sharpe</th>
                                    <th className="text-right px-3 py-2">Sortino</th>
                                    <th className="text-right px-3 py-2">Calmar</th>
                                    <th className="text-right px-3 py-2">Max DD %</th>
                                    <th className="text-right px-3 py-2">DD Duration</th>
                                    <th className="text-right px-3 py-2">Volatility</th>
                                    <th className="text-right px-3 py-2">Best Trade</th>
                                    <th className="text-right px-3 py-2">Worst Trade</th>
                                    <th className="text-right px-3 py-2">Max Consec. Loss</th>
                                    <th className="text-right px-3 py-2">Costs ₹</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {sorted.map((s) => (
                                    <tr key={s.strategy} className="hover:bg-white/5 transition">
                                        <td className="px-3 py-2 font-bold capitalize text-white whitespace-nowrap">{s.strategy.replace(/_/g, ' ')}</td>
                                        <td className={`px-3 py-2 text-right font-bold ${s.sharpe_ratio >= 1 ? 'text-green-400' : s.sharpe_ratio > 0 ? 'text-white' : 'text-red-400'}`}>
                                            {fmt(s.sharpe_ratio, 3)}
                                        </td>
                                        <td className={`px-3 py-2 text-right ${s.sortino_ratio > 1 ? 'text-green-400' : 'text-white'}`}>{fmt(s.sortino_ratio, 3)}</td>
                                        <td className="px-3 py-2 text-right text-white">{fmt(s.calmar_ratio, 3)}</td>
                                        <td className="px-3 py-2 text-right text-red-400 font-bold">{fmt(s.max_drawdown_pct, 2)}%</td>
                                        <td className="px-3 py-2 text-right text-gray-300">{s.max_drawdown_duration_days ?? '—'} days</td>
                                        <td className="px-3 py-2 text-right text-gray-300">{fmt(s.volatility_annual_pct, 1)}%</td>
                                        <td className="px-3 py-2 text-right text-green-400">{fmtPct(s.best_trade_pct)}</td>
                                        <td className="px-3 py-2 text-right text-red-400">{fmtPct(s.worst_trade_pct)}</td>
                                        <td className="px-3 py-2 text-right text-orange-400">{s.max_consecutive_losses ?? '—'}</td>
                                        <td className="px-3 py-2 text-right text-gray-300">
                                            ₹{Math.round(s.total_costs || 0).toLocaleString()}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    {/* Risk Visual Summary */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {sorted.map((s) => {
                            const riskScore = Math.min(100, Math.max(0, 100 - s.max_drawdown_pct * 3 + s.sharpe_ratio * 15));
                            const riskLevel = riskScore > 70 ? 'Low Risk' : riskScore > 40 ? 'Medium Risk' : 'High Risk';
                            const riskColor = riskScore > 70 ? 'text-green-400' : riskScore > 40 ? 'text-yellow-400' : 'text-red-400';
                            const barColor = riskScore > 70 ? 'bg-green-500' : riskScore > 40 ? 'bg-yellow-500' : 'bg-red-500';
                            return (
                                <div key={s.strategy} className="bg-white/5 rounded-xl p-4 border border-white/10">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-sm font-bold text-white capitalize">{s.strategy.replace(/_/g, ' ')}</span>
                                        <span className={`text-xs font-bold ${riskColor}`}>{riskLevel} ({Math.round(riskScore)}/100)</span>
                                    </div>
                                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                        <div className={`h-full ${barColor} rounded-full transition-all`} style={{ width: `${riskScore}%` }} />
                                    </div>
                                    <div className="flex justify-between text-[10px] text-gray-500 mt-1.5">
                                        <span>Return/Risk: {s.max_drawdown_pct > 0 ? fmt(s.total_return_pct / s.max_drawdown_pct, 2) : '∞'}</span>
                                        <span>Excess vs B&H: {fmtPct(s.excess_return_pct)}</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* ═══════════════ TRADE STATISTICS TAB ═══════════════ */}
            {activeView === 'trades' && (
                <div className="space-y-4">
                    <div className="overflow-x-auto strategy-comparison-scroll industry-table-scroll">
                        <table className="w-full text-xs strategy-comparison-table strategy-comparison-table-trades">
                            <thead>
                                <tr className="bg-white/5">
                                    <th className="text-left px-3 py-2">Strategy</th>
                                    <th className="text-right px-3 py-2">Total</th>
                                    <th className="text-right px-3 py-2">Won</th>
                                    <th className="text-right px-3 py-2">Lost</th>
                                    <th className="text-right px-3 py-2">Win %</th>
                                    <th className="text-right px-3 py-2">Avg Win %</th>
                                    <th className="text-right px-3 py-2">Avg Loss %</th>
                                    <th className="text-right px-3 py-2">W/L Ratio</th>
                                    <th className="text-right px-3 py-2">Profit Factor</th>
                                    <th className="text-right px-3 py-2">Expectancy</th>
                                    <th className="text-right px-3 py-2">Avg Hold</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {sorted.map((s) => {
                                    const wlRatio = s.average_loss_pct > 0 ? (s.average_win_pct / s.average_loss_pct).toFixed(2) : '∞';
                                    return (
                                        <tr key={s.strategy} className="hover:bg-white/5 transition">
                                            <td className="px-3 py-2 font-bold capitalize text-white whitespace-nowrap">{s.strategy.replace(/_/g, ' ')}</td>
                                            <td className="px-3 py-2 text-right text-white font-bold">{s.total_trades}</td>
                                            <td className="px-3 py-2 text-right text-green-400">{s.winning_trades}</td>
                                            <td className="px-3 py-2 text-right text-red-400">{s.losing_trades}</td>
                                            <td className={`px-3 py-2 text-right font-bold ${s.win_rate_pct > 55 ? 'text-green-400' : s.win_rate_pct > 45 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {fmt(s.win_rate_pct, 1)}%
                                            </td>
                                            <td className="px-3 py-2 text-right text-green-400">{fmt(s.average_win_pct)}%</td>
                                            <td className="px-3 py-2 text-right text-red-400">{fmt(s.average_loss_pct)}%</td>
                                            <td className={`px-3 py-2 text-right font-bold ${Number(wlRatio) > 1.5 ? 'text-green-400' : 'text-white'}`}>{wlRatio}</td>
                                            <td className={`px-3 py-2 text-right font-bold ${s.profit_factor > 1.5 ? 'text-green-400' : s.profit_factor > 1 ? 'text-yellow-400' : 'text-red-400'}`}>
                                                {fmt(s.profit_factor)}
                                            </td>
                                            <td className={`px-3 py-2 text-right ${s.expectancy_per_trade > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {fmt(s.expectancy_per_trade)}
                                            </td>
                                            <td className="px-3 py-2 text-right text-gray-300">{fmt(s.average_holding_days, 1)}d</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                    {/* Exit Reason Breakdown */}
                    {sorted.some(s => s.exit_reasons && Object.keys(s.exit_reasons).length > 0) && (
                        <div>
                            <h4 className="text-sm font-bold text-gray-300 mb-3 flex items-center gap-2">
                                <Info className="w-4 h-4" /> Exit Reason Breakdown
                            </h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {sorted.filter(s => s.exit_reasons && Object.keys(s.exit_reasons).length > 0).map(s => (
                                    <div key={s.strategy} className="bg-white/5 rounded-xl p-3 border border-white/10">
                                        <p className="text-xs font-bold text-white capitalize mb-2">{s.strategy.replace(/_/g, ' ')}</p>
                                        <div className="space-y-1">
                                            {Object.entries(s.exit_reasons).sort((a, b) => b[1] - a[1]).map(([reason, count]) => (
                                                <div key={reason} className="flex items-center justify-between">
                                                    <span className="text-[10px] text-gray-400 capitalize">{reason.replace(/_/g, ' ')}</span>
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${(count / s.total_trades) * 100}%` }} />
                                                        </div>
                                                        <span className="text-[10px] text-gray-300 font-mono w-6 text-right">{count}</span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ═══════════════ REGIME ANALYSIS TAB ═══════════════ */}
            {activeView === 'regime' && (
                <div className="space-y-4">
                    {sorted.some(s => s.regime_performance && Object.keys(s.regime_performance).length > 0) ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {sorted.filter(s => s.regime_performance && Object.keys(s.regime_performance).length > 0).map((s, idx) => (
                                <div key={s.strategy} className="bg-white/5 rounded-xl border border-white/10 overflow-hidden">
                                    <div className={`px-4 py-2 bg-gradient-to-r ${colors[idx % colors.length].gradient}`}>
                                        <h4 className="font-bold text-white capitalize text-sm">{s.strategy.replace(/_/g, ' ')}</h4>
                                    </div>
                                    <div className="p-3">
                                        <table className="w-full text-xs strategy-comparison-table strategy-comparison-table-regime">
                                            <thead>
                                                <tr className="border-b border-white/10">
                                                    <th className="text-left py-1 text-gray-400">Regime</th>
                                                    <th className="text-right py-1 text-gray-400">Trades</th>
                                                    <th className="text-right py-1 text-gray-400">Win %</th>
                                                    <th className="text-right py-1 text-gray-400">Avg Ret %</th>
                                                    <th className="text-right py-1 text-gray-400">PnL ₹</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-white/5">
                                                {Object.entries(s.regime_performance).map(([regime, rp]) => (
                                                    <tr key={regime} className="hover:bg-white/5">
                                                        <td className="py-1.5 capitalize text-white font-medium">{regime.replace(/_/g, ' ')}</td>
                                                        <td className="py-1.5 text-right text-gray-300">{rp.total_trades}</td>
                                                        <td className={`py-1.5 text-right ${rp.win_rate_pct > 50 ? 'text-green-400' : 'text-red-400'}`}>
                                                            {rp.win_rate_pct?.toFixed(1)}%
                                                        </td>
                                                        <td className={`py-1.5 text-right ${rp.avg_return_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                            {rp.avg_return_pct?.toFixed(2)}%
                                                        </td>
                                                        <td className={`py-1.5 text-right font-bold ${rp.total_pnl > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                            ₹{Math.round(rp.total_pnl || 0).toLocaleString()}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="p-8 text-center text-gray-400">
                            <Target className="w-12 h-12 mx-auto mb-3 opacity-50" />
                            <p>No regime performance data available</p>
                            <p className="text-xs text-gray-500 mt-1">Regime analysis requires sufficient trading history</p>
                        </div>
                    )}
                </div>
            )}

            {/* Rankings Footer */}
            {data.rankings && Object.keys(data.rankings).length > 0 && activeView === 'overview' && (
                <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                    <h4 className="text-sm font-bold text-gray-300 mb-3 flex items-center gap-2">
                        <Award className="w-4 h-4 text-yellow-400" /> Rankings
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                        {[
                            { key: 'by_return', label: 'By Return', icon: TrendingUp },
                            { key: 'by_sharpe', label: 'By Sharpe', icon: Target },
                            { key: 'by_win_rate', label: 'By Win Rate', icon: Award },
                            { key: 'by_drawdown', label: 'By Risk (DD)', icon: Shield },
                            { key: 'by_calmar', label: 'By Calmar', icon: Activity },
                        ].map(({ key, label, icon: Icon }) => {
                            const ranking = data.rankings[key];
                            if (!ranking || ranking.length === 0) return null;
                            return (
                                <div key={key} className="bg-white/5 rounded-lg p-3 border border-white/5">
                                    <p className="text-[10px] text-gray-500 mb-1.5 flex items-center gap-1">
                                        <Icon className="w-3 h-3" /> {label}
                                    </p>
                                    <div className="space-y-1">
                                        {ranking.slice(0, 3).map((name, i) => (
                                            <div key={name} className="flex items-center gap-1.5">
                                                <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-black ${i === 0 ? 'bg-yellow-500/30 text-yellow-300' : i === 1 ? 'bg-gray-400/20 text-gray-300' : 'bg-amber-700/20 text-amber-500'}`}>
                                                    {i + 1}
                                                </span>
                                                <span className="text-xs text-white capitalize truncate">{name.replace(/_/g, ' ')}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

export default StrategyComparison;
