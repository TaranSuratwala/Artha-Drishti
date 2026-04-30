import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, AlertCircle } from 'lucide-react';
import { Card, Button, LoadingSpinner } from '../ui';
import { PriceTargets } from './PriceTargets';
import { fetchBatchPriceTargets } from '../../services/api';

export const PriceTargetsDashboard = ({ tickers = [] }) => {
    const [targets, setTargets] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedTicker, setSelectedTicker] = useState(null);
    const [errors, setErrors] = useState([]);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [autoRefresh, setAutoRefresh] = useState(true);

    const loadBatchTargets = useCallback(async () => {
        if (!tickers.length) return;
        
        try {
            setLoading(true);
            const data = await fetchBatchPriceTargets(tickers);
            
            if (data && (data.status === 'success' || data.targets)) {
                setTargets(data.targets || []);
                setErrors(data.errors || []);
                setLastUpdated(new Date());
            }
        } catch (err) {
            console.error('Batch fetch error:', err);
            setErrors([{ error: err.message }]);
        } finally {
            setLoading(false);
        }
    }, [tickers]);

    useEffect(() => {
        if (tickers.length > 0) {
            loadBatchTargets();
        }
    }, [tickers, loadBatchTargets]);

    useEffect(() => {
        if (!autoRefresh || tickers.length === 0 || selectedTicker) return;
        const interval = setInterval(loadBatchTargets, 30_000);
        return () => clearInterval(interval);
    }, [autoRefresh, tickers.length, selectedTicker, loadBatchTargets]);

    if (selectedTicker) {
        return (
            <div className="price-targets-dashboard">
                <Button 
                    onClick={() => setSelectedTicker(null)}
                    className="mb-4 bg-gray-500 hover:bg-gray-600 price-targets-back-btn"
                >
                    ← Back to Price Targets
                </Button>
                <PriceTargets ticker={selectedTicker} />
            </div>
        );
    }

    if (loading) {
        return <LoadingSpinner />;
    }

    if (!tickers.length) {
        return (
            <Card className="p-8 text-center text-gray-500 industry-empty-card">
                No stocks selected. Please select stocks from your watchlist or portfolio.
            </Card>
        );
    }

    return (
        <div className="space-y-4 price-targets-dashboard">
            <div className="flex justify-between items-center price-targets-toolbar">
                <div>
                    <h3 className="text-lg font-semibold text-white">Realtime Price Targets</h3>
                    {lastUpdated && (
                        <p className="text-xs text-gray-500 mt-1">Last update: {lastUpdated.toLocaleTimeString()}</p>
                    )}
                </div>
                <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer price-targets-auto-refresh">
                        <input
                            type="checkbox"
                            checked={autoRefresh}
                            onChange={(e) => setAutoRefresh(e.target.checked)}
                            className="rounded"
                        />
                        Auto-refresh
                    </label>
                    <Button
                        onClick={loadBatchTargets}
                        disabled={loading}
                        className="flex items-center gap-2"
                    >
                        <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                        {loading ? 'Updating...' : 'Refresh All'}
                    </Button>
                </div>
            </div>

            {errors.length > 0 && (
                <Card className="p-4 bg-red-500/10 border-l-4 border-red-500 price-targets-error">
                    <div className="flex items-center gap-2 text-red-300">
                        <AlertCircle size={18} />
                        <span>{errors.length} stocks failed to load</span>
                    </div>
                </Card>
            )}

            {targets.length === 0 ? (
                <Card className="p-8 text-center text-gray-500 industry-empty-card">
                    No price targets available
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {targets.map((target, idx) => (
                        <Card 
                            key={idx}
                            className={`p-4 cursor-pointer hover:shadow-lg transition-shadow border-l-4 industry-section-card price-target-card ${
                                target.signal === 'BUY' ? 'border-green-500 signal-buy' :
                                target.signal === 'SELL' ? 'border-red-500 signal-sell' : 'border-gray-500 signal-neutral'
                            }`}
                            onClick={() => setSelectedTicker(target.ticker)}
                        >
                            <div className="flex justify-between items-start mb-3">
                                <div>
                                    <h4 className="font-semibold text-white">{target.ticker}</h4>
                                    <p className="text-xs text-gray-500">
                                        Current: ₹{target.current_price.toFixed(2)}
                                    </p>
                                </div>
                                <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                    target.signal === 'BUY' ? 'bg-green-500/20 text-green-300' :
                                    target.signal === 'SELL' ? 'bg-red-500/20 text-red-300' : 'bg-gray-500/20 text-gray-300'
                                }`}>
                                    {target.signal}
                                </span>
                            </div>

                            <div className="space-y-2 mb-3 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Target</span>
                                    <span className="font-semibold text-green-400">₹{target.target_price.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Stop Loss</span>
                                    <span className="font-semibold text-red-400">₹{target.stop_loss.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">R:R Ratio</span>
                                    <span className="font-semibold text-cyan-300">
                                        1:{target.risk_reward_ratio.toFixed(2)}
                                    </span>
                                </div>
                            </div>

                            <div className="flex items-center gap-2 text-xs">
                                <div className="flex-1 bg-white/10 rounded h-1.5">
                                    <div 
                                        className="bg-blue-500 h-1.5 rounded" 
                                        style={{width: `${Math.min(target.confidence * 100, 100)}%`}}
                                    />
                                </div>
                                <span className="text-gray-400 font-semibold w-10">
                                    {Math.round(target.confidence * 100)}%
                                </span>
                            </div>

                            <p className="text-xs text-gray-500 mt-2">
                                Position: {target.position_size} units
                            </p>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
};

export default PriceTargetsDashboard;
