import React, { useState, useEffect, useCallback } from 'react';
import { TrendingUp, TrendingDown, Target, AlertCircle, Shield, Activity, Zap } from 'lucide-react';
import { Card, Button, LoadingSpinner } from '../ui';
import { fetchPriceTarget } from '../../services/api';

export const PriceTargets = ({ ticker }) => {
    const [target, setTarget] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    const loadPriceTarget = useCallback(async () => {
        try {
            setRefreshing(true);
            const data = await fetchPriceTarget(ticker);
            
            if (data && (data.status === 'success' || data.trade_setup)) {
                setTarget(data);
                setError(null);
            } else {
                setError(data?.error || 'Failed to fetch price target');
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [ticker]);

    useEffect(() => {
        loadPriceTarget();
        const interval = setInterval(loadPriceTarget, 30_000);
        return () => clearInterval(interval);
    }, [loadPriceTarget]);

    if (loading) {
        return <LoadingSpinner />;
    }

    if (error) {
        return (
            <Card className="p-4 bg-red-500/10 border-l-4 border-red-500">
                <div className="flex items-center gap-2 text-red-300">
                    <AlertCircle size={20} />
                    <span>{error}</span>
                </div>
            </Card>
        );
    }

    if (!target) {
        return null;
    }

    const { trade_setup, price_analysis, confidence, risk_management } = target;
    const adci = target.confidence_index || {};
    const regime = target.market_regime || {};
    const momentum = target.momentum_factor || {};
    const investorAction = target.investor_action || {};
    const lifecycle = target.signal_lifecycle || {};

    const currentPrice = price_analysis?.current_price || 0;
    const targetPrice = trade_setup?.target_price || currentPrice;
    const buyPrice = trade_setup?.buy_price || currentPrice;
    const stopLoss = trade_setup?.stop_loss || currentPrice;
    
    // Calculate potential return
    const potentialReturn = buyPrice > 0 ? ((targetPrice - buyPrice) / buyPrice) * 100 : 0;
    const maxRisk = buyPrice > 0 ? ((buyPrice - stopLoss) / buyPrice) * 100 : 0;
    
    // Signal colors
    const signal = trade_setup?.signal || 'HOLD';
    const isBuy = signal.includes('BUY');
    const isSell = signal.includes('SELL');
    
    const signalColor = isBuy ? 'text-green-600' : isSell ? 'text-red-600' : 'text-gray-600';
    const signalBgColor = isBuy ? 'bg-green-50' : isSell ? 'bg-red-50' : 'bg-gray-50';
    const signalBorderColor = isBuy ? 'border-green-500' : isSell ? 'border-red-500' : 'border-gray-500';

    // ADCI tier colors
    const adciScore = adci?.score || 0;
    const adciTier = adci?.tier || 'UNKNOWN';
    const adciColor = adciScore >= 70 ? 'text-green-600' : adciScore >= 40 ? 'text-yellow-600' : 'text-red-600';
    const adciBgColor = adciScore >= 70 ? 'bg-green-100' : adciScore >= 40 ? 'bg-yellow-100' : 'bg-red-100';

    // Regime colors
    const regimeColor = regime?.regime === 'BULL' ? 'text-green-600 bg-green-50' :
                        regime?.regime === 'BEAR' ? 'text-red-600 bg-red-50' :
                        regime?.regime === 'HIGH_VOLATILITY' ? 'text-orange-600 bg-orange-50' :
                        'text-blue-600 bg-blue-50';

    return (
        <div className="space-y-4">
            {/* Signal Card with ADCI */}
            <Card className={`p-6 ${signalBgColor} border-l-4 ${signalBorderColor}`}>
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h3 className="text-lg font-semibold text-gray-800">Trade Signal</h3>
                        <p className="text-sm text-gray-600">{ticker}</p>
                        {lifecycle?.status && (
                            <p className="text-xs text-gray-500 mt-1">
                                Expires: {lifecycle.expires_at || 'N/A'}
                            </p>
                        )}
                    </div>
                    <div className="text-right">
                        <p className={`text-3xl font-bold ${signalColor}`}>
                            {signal}
                        </p>
                        <p className="text-sm text-gray-600">
                            Confidence: {Math.round(confidence?.confidence_score || 0)}%
                        </p>
                        {adciScore > 0 && (
                            <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-semibold ${adciBgColor} ${adciColor}`}>
                                ADCI: {adciScore}/100
                            </span>
                        )}
                    </div>
                </div>
                <Button 
                    onClick={loadPriceTarget}
                    disabled={refreshing}
                    className="w-full"
                >
                    {refreshing ? 'Refreshing...' : 'Refresh Targets'}
                </Button>
            </Card>

            {/* v33: Market Regime & Momentum */}
            {(regime?.regimes_available || momentum?.active) && (
                <div className="grid grid-cols-2 gap-4">
                    {regime?.regimes_available && (
                        <Card className={`p-4 ${regimeColor} border-l-4 ${
                            regime.regime === 'BULL' ? 'border-green-500' :
                            regime.regime === 'BEAR' ? 'border-red-500' :
                            regime.regime === 'HIGH_VOLATILITY' ? 'border-orange-500' :
                            'border-blue-500'
                        }`}>
                            <div className="flex items-center gap-2 mb-2">
                                <Activity size={16} />
                                <p className="text-sm font-semibold">Market Regime</p>
                            </div>
                            <p className="text-xl font-bold">{regime.regime?.replace('_', ' ')}</p>
                            <p className="text-xs mt-1 opacity-75">
                                Conf: {Math.round((regime.confidence || 0) * 100)}%
                            </p>
                        </Card>
                    )}
                    {momentum?.active && (
                        <Card className={`p-4 border-l-4 ${
                            momentum.score > 20 ? 'border-green-500 bg-green-50' :
                            momentum.score < -20 ? 'border-red-500 bg-red-50' :
                            'border-gray-400 bg-gray-50'
                        }`}>
                            <div className="flex items-center gap-2 mb-2">
                                <Zap size={16} />
                                <p className="text-sm font-semibold">Momentum</p>
                            </div>
                            <p className="text-xl font-bold">
                                {momentum.regime?.replace('_', ' ')}
                            </p>
                            <p className="text-xs mt-1 opacity-75">
                                Score: {momentum.score?.toFixed(1) || 0}
                            </p>
                        </Card>
                    )}
                </div>
            )}

            {/* Current Price */}
            <Card className="p-4">
                <div className="flex justify-between items-center">
                    <span className="text-gray-700 font-semibold">Current Price</span>
                    <span className="text-2xl font-bold text-blue-600">₹{currentPrice.toFixed(2)}</span>
                </div>
            </Card>

            {/* Price Targets Grid */}
            <div className="grid grid-cols-2 gap-4">
                {/* Buy Price */}
                <Card className="p-4 border-l-4 border-blue-500">
                    <div className="flex items-center gap-2 mb-2">
                        <TrendingUp size={18} className="text-blue-600" />
                        <p className="text-sm text-gray-600 font-semibold">Buy Price</p>
                    </div>
                    <p className="text-2xl font-bold text-blue-600">₹{buyPrice.toFixed(2)}</p>
                    <p className="text-xs text-gray-500 mt-1">Entry Point</p>
                </Card>

                {/* Target Price */}
                <Card className="p-4 border-l-4 border-green-500">
                    <div className="flex items-center gap-2 mb-2">
                        <Target size={18} className="text-green-600" />
                        <p className="text-sm text-gray-600 font-semibold">Target Price</p>
                    </div>
                    <p className="text-2xl font-bold text-green-600">₹{targetPrice.toFixed(2)}</p>
                    <p className="text-xs text-green-600 mt-1">
                        ↑ {potentialReturn.toFixed(1)}% Gain
                    </p>
                </Card>

                {/* Stop Loss */}
                <Card className="p-4 border-l-4 border-red-500">
                    <div className="flex items-center gap-2 mb-2">
                        <TrendingDown size={18} className="text-red-600" />
                        <p className="text-sm text-gray-600 font-semibold">Stop Loss</p>
                    </div>
                    <p className="text-2xl font-bold text-red-600">₹{stopLoss.toFixed(2)}</p>
                    <p className="text-xs text-red-600 mt-1">
                        ↓ {maxRisk.toFixed(1)}% Loss
                    </p>
                </Card>

                {/* Risk/Reward Ratio */}
                <Card className="p-4 border-l-4 border-purple-500">
                    <div className="flex items-center gap-2 mb-2">
                        <Target size={18} className="text-purple-600" />
                        <p className="text-sm text-gray-600 font-semibold">Risk/Reward</p>
                    </div>
                    <p className="text-2xl font-bold text-purple-600">
                        1:{(trade_setup?.risk_reward_ratio || 0).toFixed(2)}
                    </p>
                    <p className="text-xs text-purple-600 mt-1">Ratio</p>
                </Card>
            </div>

            {/* Price Analysis */}
            <Card className="p-4">
                <h4 className="font-semibold text-gray-800 mb-3">Price Analysis</h4>
                <div className="space-y-2">
                    <div className="flex justify-between">
                        <span className="text-gray-600">5-Day Prediction</span>
                        <span className="font-semibold text-gray-800">₹{(price_analysis?.predicted_price_5d || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600">Expected Change</span>
                        <span className={`font-semibold ${(price_analysis?.predicted_change_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {(price_analysis?.predicted_change_pct || 0) >= 0 ? '↑' : '↓'} {Math.abs(price_analysis?.predicted_change_pct || 0).toFixed(2)}%
                        </span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600">Volatility</span>
                        <span className="font-semibold text-gray-800">{((price_analysis?.volatility || 0) * 100).toFixed(2)}%</span>
                    </div>
                </div>
            </Card>

            {/* Risk Management */}
            <Card className="p-4">
                <h4 className="font-semibold text-gray-800 mb-3">Risk Management</h4>
                <div className="space-y-2">
                    <div className="flex justify-between">
                        <span className="text-gray-600">Position Size</span>
                        <span className="font-semibold text-gray-800">{trade_setup?.position_size || 0} units</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600">Capital at Risk</span>
                        <span className="font-semibold text-gray-800">₹{(risk_management?.capital_at_risk || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600">Max Loss</span>
                        <span className="font-semibold text-red-600">-₹{(risk_management?.max_loss || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-gray-600">Trade Value</span>
                        <span className="font-semibold text-gray-800">₹{(risk_management?.trade_value || 0).toFixed(2)}</span>
                    </div>
                    {risk_management?.sizing_method && (
                        <div className="flex justify-between">
                            <span className="text-gray-600">Sizing Method</span>
                            <span className="text-xs font-medium text-gray-500">{risk_management.sizing_method}</span>
                        </div>
                    )}
                </div>
            </Card>

            {/* Confidence Metrics with ADCI */}
            <Card className="p-4">
                <h4 className="font-semibold text-gray-800 mb-3">Prediction Confidence</h4>
                <div className="space-y-3">
                    {/* ADCI Score Bar */}
                    {adciScore > 0 && (
                        <div>
                            <div className="flex justify-between mb-1">
                                <span className="text-sm text-gray-600">ADCI Score ({adciTier?.replace('_', ' ')})</span>
                                <span className={`text-sm font-semibold ${adciColor}`}>{adciScore}/100</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2.5">
                                <div 
                                    className={`h-2.5 rounded-full ${
                                        adciScore >= 70 ? 'bg-green-500' : adciScore >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                                    }`}
                                    style={{width: `${Math.min(adciScore, 100)}%`}}
                                />
                            </div>
                        </div>
                    )}

                    <div>
                        <div className="flex justify-between mb-1">
                            <span className="text-sm text-gray-600">Direction Probability</span>
                            <span className="text-sm font-semibold">{Math.round(confidence?.direction_probability || 50)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                                className="bg-blue-500 h-2 rounded-full" 
                                style={{width: `${Math.min(confidence?.direction_probability || 50, 100)}%`}}
                            />
                        </div>
                    </div>

                    <div>
                        <div className="flex justify-between mb-1">
                            <span className="text-sm text-gray-600">Confidence Score</span>
                            <span className="text-sm font-semibold">{Math.round(confidence?.confidence_score || 0)}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                                className="bg-green-500 h-2 rounded-full" 
                                style={{width: `${Math.min(confidence?.confidence_score || 0, 100)}%`}}
                            />
                        </div>
                    </div>

                    {confidence?.signal_quality && (
                        <div className="flex justify-between">
                            <span className="text-sm text-gray-600">Signal Quality</span>
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                                confidence.signal_quality === 'HIGH_CONFIDENCE' ? 'bg-green-100 text-green-700' :
                                confidence.signal_quality === 'SPECULATIVE' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-gray-100 text-gray-700'
                            }`}>{confidence.signal_quality}</span>
                        </div>
                    )}
                </div>
            </Card>

            {/* v33: Investor Action Summary */}
            {investorAction?.summary && (
                <Card className={`p-4 border-l-4 ${
                    isBuy ? 'border-green-500 bg-green-50' :
                    isSell ? 'border-red-500 bg-red-50' :
                    'border-gray-400 bg-gray-50'
                }`}>
                    <div className="flex items-center gap-2 mb-2">
                        <Shield size={18} className={isBuy ? 'text-green-600' : isSell ? 'text-red-600' : 'text-gray-600'} />
                        <h4 className="font-semibold text-gray-800">Investor Action</h4>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">
                        {investorAction.summary}
                    </p>
                </Card>
            )}

            {/* Disclaimer */}
            <Card className="p-3 bg-yellow-50 border-l-4 border-yellow-500">
                <p className="text-xs text-yellow-800">
                    {target.disclaimer?.text || 
                    'Disclaimer: This is an AI-generated prediction (Artha Drishti v33). Always do your own research and consult a SEBI-registered financial advisor before trading. Use stop-losses.'}
                </p>
            </Card>
        </div>
    );
};

export default PriceTargets;
