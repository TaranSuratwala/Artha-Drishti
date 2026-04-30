import React, { useState } from 'react';
import { Layers, Play, RefreshCw, ChevronRight } from 'lucide-react';
import { Button } from '../ui';
import { Card } from '../ui';



/**
 * MultiStrategyPanel - Screen stocks across multiple strategies and find overlaps
 */
export const MultiStrategyPanel = ({ onAnalyze, onRunMultiStrategy, availableStrategies = [] }) => {
    const [selectedStrategies, setSelectedStrategies] = useState(['momentum', 'value']);
    const [minOverlap, setMinOverlap] = useState(2);
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const toggleStrategy = (strategyId) => {
        setSelectedStrategies(prev =>
            prev.includes(strategyId)
                ? prev.filter(s => s !== strategyId)
                : [...prev, strategyId]
        );
    };

    const handleRunScan = async () => {
        if (selectedStrategies.length < 2) {
            setError('Please select at least 2 strategies');
            return;
        }

        setError(null);
        setLoading(true);
        setResults(null);

        try {
            const data = await onRunMultiStrategy(selectedStrategies, minOverlap);
            setResults(data);
        } catch (err) {
            const rawMessage = String(err?.message || '').toLowerCase();
            if (rawMessage.includes('request cancelled') || rawMessage.includes('timeout')) {
                setError('Scan timed out before completion. Try fewer strategies or a lower overlap and run again.');
            } else {
                setError(err.message || 'Failed to run multi-strategy scan');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <Card className="p-6">
                <div className="flex items-center gap-3 mb-6">
                    <div className="p-3 bg-gradient-to-br from-purple-500/20 to-blue-500/20 rounded-xl">
                        <Layers className="w-6 h-6 text-purple-300" />
                    </div>
                    <div>
                        <h2 className="text-2xl font-black text-white">Multi-Strategy Screener</h2>
                        <p className="text-sm text-gray-400">Find stocks that match multiple trading strategies</p>
                    </div>
                </div>

                {/* Strategy Selection Grid */}
                <div className="mb-6">
                    <label className="text-sm font-semibold text-blue-200 mb-3 block">
                        Select Strategies (minimum 2)
                    </label>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                        {availableStrategies.filter(s => s.id !== 'custom').map(strategy => {
                            const isSelected = selectedStrategies.includes(strategy.id);
                            const IconComponent = strategy.icon;
                            return (
                                <button
                                    key={strategy.id}
                                    onClick={() => toggleStrategy(strategy.id)}
                                    className={`p-4 rounded-xl font-bold transition-all flex flex-col items-center gap-2 border-2 ${isSelected
                                        ? 'bg-gradient-to-r from-blue-200 to-cyan-200 text-slate-900 border-blue-300 shadow-lg'
                                        : 'bg-white/5 text-gray-300 border-white/10 hover:bg-white/10 hover:border-white/20'
                                        }`}
                                >
                                    <IconComponent className="w-6 h-6" />
                                    <span className="text-sm">{strategy.name}</span>
                                    {isSelected && (
                                        <span className="absolute -top-1 -right-1 w-5 h-5 bg-white rounded-full flex items-center justify-center">
                                            <span className="text-xs text-purple-600 font-black">✓</span>
                                        </span>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Minimum Overlap Slider */}
                <div className="mb-6">
                    <label className="text-sm font-semibold text-blue-200 mb-2 block">
                        Minimum Strategy Overlap: <span className="text-white font-black">{minOverlap}</span>
                    </label>
                    <input
                        type="range"
                        min="2"
                        max={Math.max(2, selectedStrategies.length)}
                        value={minOverlap}
                        onChange={(e) => setMinOverlap(Number(e.target.value))}
                        className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-purple-500"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                        <span>2 strategies</span>
                        <span>{Math.max(2, selectedStrategies.length)} strategies</span>
                    </div>
                </div>

                {/* Error Display */}
                {error && (
                    <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-xl text-red-300 text-sm">
                        {error}
                    </div>
                )}

                {/* Run Button */}
                <Button
                    onClick={handleRunScan}
                    disabled={loading || selectedStrategies.length < 2}
                    variant="purple"
                    size="lg"
                    className="w-full"
                >
                    {loading ? (
                        <>
                            <RefreshCw className="w-5 h-5 animate-spin" />
                            Scanning across {selectedStrategies.length} strategies...
                        </>
                    ) : (
                        <>
                            <Play className="w-5 h-5" />
                            Find Overlapping Stocks
                        </>
                    )}
                </Button>
            </Card>

            {/* Results Display */}
            {results && (
                <Card className="overflow-hidden animate-fade-in">
                    <div className="px-6 py-4 bg-gradient-to-r from-purple-500/20 to-blue-500/20 border-b border-white/10">
                        <h3 className="text-lg font-black text-white flex items-center gap-2">
                            <Layers className="w-5 h-5 text-purple-400" />
                            Found {results.count || 0} Overlapping Stocks
                        </h3>
                        <p className="text-sm text-gray-400 mt-1">
                            Stocks appearing in {minOverlap}+ of: {results.strategies_used?.join(', ')}
                        </p>
                    </div>

                    {/* Strategy Counts Summary */}
                    {results.strategy_counts && (
                        <div className="px-6 py-3 bg-white/5 border-b border-white/10">
                            <div className="flex flex-wrap gap-3">
                                {Object.entries(results.strategy_counts).map(([strategy, count]) => (
                                    <span key={strategy} className="px-3 py-1 bg-white/10 rounded-full text-xs font-semibold text-gray-300">
                                        {strategy}: {count} stocks
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Results Table */}
                    {results.results && results.results.length > 0 ? (
                        <div className="overflow-x-auto">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Ticker</th>
                                        <th>Overlap</th>
                                        <th>Matching Strategies</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {results.results.map((row, idx) => (
                                        <tr key={idx}>
                                            <td className="font-bold text-blue-400">{row.ticker}</td>
                                            <td>
                                                <span className={`px-2 py-1 rounded-full text-xs font-bold ${row.overlap_count >= 4 ? 'bg-green-500/20 text-green-300' :
                                                    row.overlap_count >= 3 ? 'bg-blue-500/20 text-blue-300' :
                                                        'bg-purple-500/20 text-purple-300'
                                                    }`}>
                                                    {row.overlap_count} strategies
                                                </span>
                                            </td>
                                            <td>
                                                <div className="flex flex-wrap gap-1">
                                                    {row.strategies?.map(s => (
                                                        <span key={s} className="px-2 py-0.5 bg-white/10 rounded text-xs text-gray-300 capitalize">
                                                            {s}
                                                        </span>
                                                    ))}
                                                </div>
                                            </td>
                                            <td>
                                                <Button onClick={() => onAnalyze && onAnalyze(row.ticker)} size="sm" variant="secondary">
                                                    <ChevronRight className="w-4 h-4" />
                                                    Analyze
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="p-8 text-center text-gray-400">
                            <Layers className="w-12 h-12 mx-auto mb-3 opacity-50" />
                            <p>No stocks found matching {minOverlap}+ strategies</p>
                            <p className="text-sm text-gray-500 mt-1">Try reducing the minimum overlap requirement</p>
                        </div>
                    )}
                </Card>
            )}
        </div>
    );
};

export default MultiStrategyPanel;
