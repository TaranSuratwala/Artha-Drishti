import React, { useState, useEffect, useMemo } from 'react';
import { Save, Plus, Trash2, Info, AlertCircle, CheckCircle, Loader, ArrowLeft, Zap, Copy } from 'lucide-react';
import { Button, Card } from '../ui';
import { getIndicatorCatalog, createCustomStrategy } from '../../services/api';

// Quick-start templates for common strategies
const STRATEGY_TEMPLATES = [
    {
        id: 'oversold_bounce',
        name: 'Oversold Bounce',
        description: 'Find stocks that are oversold and likely to reverse upward',
        riskLevel: 'High',
        category: 'Technical',
        conditions: [
            { indicator: 'rsi', operator: '<', value: '30', weight: 1.5 },
            { indicator: 'volume_ratio', operator: '>', value: '1.2', weight: 1.0 },
            { indicator: 'bb_lower', operator: '>', value: '0', weight: 0.8 }
        ]
    },
    {
        id: 'value_pick',
        name: 'Value Pick',
        description: 'Low valuation stocks with strong fundamentals',
        riskLevel: 'Low',
        category: 'Fundamental',
        conditions: [
            { indicator: 'pe_ratio', operator: '<', value: '15', weight: 1.5 },
            { indicator: 'roe', operator: '>', value: '12', weight: 1.2 },
            { indicator: 'debt_equity', operator: '<', value: '1', weight: 1.0 }
        ]
    },
    {
        id: 'momentum_breakout',
        name: 'Momentum Breakout',
        description: 'Stocks breaking out with strong momentum',
        riskLevel: 'High',
        category: 'Technical',
        conditions: [
            { indicator: 'rsi', operator: '>', value: '60', weight: 1.0 },
            { indicator: 'adx', operator: '>', value: '25', weight: 1.2 },
            { indicator: 'volume_ratio', operator: '>', value: '1.5', weight: 1.5 },
            { indicator: 'sma_20', operator: '>', value: '0', weight: 0.8 }
        ]
    },
    {
        id: 'dividend_income',
        name: 'Dividend Income',
        description: 'High-yield dividend stocks with stable earnings',
        riskLevel: 'Low',
        category: 'Fundamental',
        conditions: [
            { indicator: 'dividend_yield', operator: '>', value: '3', weight: 1.5 },
            { indicator: 'profit_margin', operator: '>', value: '10', weight: 1.0 },
            { indicator: 'current_ratio', operator: '>', value: '1.5', weight: 0.8 }
        ]
    }
];

/**
 * StrategyBuilder Component
 * Allows users to create custom trading strategies with a visual interface
 */
export const StrategyBuilder = ({ onSave, onCancel }) => {
    const [catalog, setCatalog] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    // Strategy State
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [riskLevel, setRiskLevel] = useState('Medium');
    const [category, setCategory] = useState('Custom');
    const [conditions, setConditions] = useState([
        { indicator: '', operator: '>', value: '', weight: 1.0 }
    ]);

    // Fallback catalog if API fails
    const FALLBACK_CATALOG = useMemo(() => ({
        technical_indicators: {
            momentum: [
                { id: 'rsi', name: 'RSI (Relative Strength Index)', description: 'Measures overbought/oversold conditions (0-100)' },
                { id: 'macd', name: 'MACD', description: 'Moving Average Convergence Divergence' },
                { id: 'macd_hist', name: 'MACD Histogram', description: 'MACD momentum indicator' },
                { id: 'stoch_k', name: 'Stochastic %K', description: 'Stochastic oscillator (0-100)' },
                { id: 'stoch_d', name: 'Stochastic %D', description: 'Stochastic signal line' },
                { id: 'williams_r', name: 'Williams %R', description: 'Momentum indicator (-100 to 0)' },
                { id: 'cci', name: 'CCI', description: 'Commodity Channel Index' },
                { id: 'roc', name: 'Rate of Change', description: 'Price momentum as percentage' }
            ],
            trend: [
                { id: 'sma_20', name: 'SMA 20', description: '20-period Simple Moving Average' },
                { id: 'sma_50', name: 'SMA 50', description: '50-period Simple Moving Average' },
                { id: 'sma_200', name: 'SMA 200', description: '200-period Simple Moving Average' },
                { id: 'ema_12', name: 'EMA 12', description: '12-period Exponential Moving Average' },
                { id: 'ema_26', name: 'EMA 26', description: '26-period Exponential Moving Average' },
                { id: 'adx', name: 'ADX', description: 'Average Directional Index (trend strength)' }
            ],
            volatility: [
                { id: 'bb_upper', name: 'Bollinger Upper', description: 'Upper Bollinger Band' },
                { id: 'bb_lower', name: 'Bollinger Lower', description: 'Lower Bollinger Band' },
                { id: 'bb_middle', name: 'Bollinger Middle', description: 'Middle Bollinger Band (SMA 20)' },
                { id: 'atr', name: 'ATR', description: 'Average True Range (volatility)' }
            ],
            volume: [
                { id: 'volume_ratio', name: 'Volume Ratio', description: 'Current vs average volume' },
                { id: 'obv', name: 'OBV', description: 'On-Balance Volume' },
                { id: 'vwap', name: 'VWAP', description: 'Volume Weighted Average Price' }
            ],
            relative: [
                { id: 'rsi_prev', name: 'RSI (Prev Day)', description: 'Previous day RSI value' },
                { id: 'macd_prev', name: 'MACD (Prev Day)', description: 'Previous day MACD value' },
                { id: 'macd_hist_prev', name: 'MACD Hist (Prev Day)', description: 'Previous day MACD histogram' },
                { id: 'close_prev', name: 'Close (Prev Day)', description: 'Previous day closing price' },
                { id: 'close_pct_change', name: 'Close % Change', description: 'Day-over-day price change (%)' },
                { id: 'volume_prev', name: 'Volume (Prev Day)', description: 'Previous day volume' },
                { id: 'adx_prev', name: 'ADX (Prev Day)', description: 'Previous day ADX value' },
                { id: 'sma_20_slope', name: 'SMA 20 Slope', description: 'SMA 20 trend direction (positive = rising)' },
                { id: 'sma_50_slope', name: 'SMA 50 Slope', description: 'SMA 50 trend direction (positive = rising)' },
                { id: 'rsi_change', name: 'RSI Change', description: 'Day-over-day RSI change' },
                { id: 'macd_change', name: 'MACD Change', description: 'Day-over-day MACD change' }
            ],
            multi_timeframe: [
                { id: 'weekly_rsi', name: 'Weekly RSI', description: 'RSI on weekly timeframe' },
                { id: 'weekly_macd', name: 'Weekly MACD', description: 'MACD on weekly timeframe' },
                { id: 'weekly_sma_20', name: 'Weekly SMA 20', description: 'SMA 20 on weekly timeframe' },
                { id: 'weekly_adx', name: 'Weekly ADX', description: 'ADX on weekly timeframe' },
                { id: 'monthly_rsi', name: 'Monthly RSI', description: 'RSI on monthly timeframe' },
                { id: 'monthly_sma_20', name: 'Monthly SMA 20', description: 'SMA 20 on monthly timeframe' },
                { id: 'weekly_close_above_sma50', name: 'Weekly Close > SMA 50', description: '1 if weekly close is above weekly SMA 50, else 0' },
                { id: 'daily_close_above_sma200', name: 'Daily Close > SMA 200', description: '1 if daily close is above SMA 200, else 0' }
            ]
        },
        fundamental_indicators: {
            valuation: [
                { id: 'pe_ratio', name: 'P/E Ratio', description: 'Price to Earnings ratio' },
                { id: 'pb_ratio', name: 'P/B Ratio', description: 'Price to Book ratio' },
                { id: 'ps_ratio', name: 'P/S Ratio', description: 'Price to Sales ratio' },
                { id: 'peg_ratio', name: 'PEG Ratio', description: 'PE to Growth ratio' }
            ],
            profitability: [
                { id: 'roe', name: 'ROE', description: 'Return on Equity (%)' },
                { id: 'roa', name: 'ROA', description: 'Return on Assets (%)' },
                { id: 'profit_margin', name: 'Profit Margin', description: 'Net profit margin (%)' },
                { id: 'operating_margin', name: 'Operating Margin', description: 'Operating margin (%)' }
            ],
            financial_health: [
                { id: 'current_ratio', name: 'Current Ratio', description: 'Current assets / Current liabilities' },
                { id: 'debt_equity', name: 'Debt/Equity', description: 'Total debt to equity ratio' },
                { id: 'quick_ratio', name: 'Quick Ratio', description: 'Liquid assets / Current liabilities' }
            ],
            growth: [
                { id: 'revenue_growth', name: 'Revenue Growth', description: 'YoY revenue growth (%)' },
                { id: 'earnings_growth', name: 'Earnings Growth', description: 'YoY earnings growth (%)' },
                { id: 'dividend_yield', name: 'Dividend Yield', description: 'Annual dividend yield (%)' }
            ]
        },
        operators: [
            { id: '>', name: '>' },
            { id: '<', name: '<' },
            { id: '>=', name: '>=' },
            { id: '<=', name: '<=' },
            { id: '==', name: '==' },
            { id: 'between', name: 'Between' },
            { id: 'crosses_above', name: 'Crosses Above' },
            { id: 'crosses_below', name: 'Crosses Below' },
            { id: 'increasing', name: 'Increasing (vs Prev Day)' },
            { id: 'decreasing', name: 'Decreasing (vs Prev Day)' },
            { id: 'above_indicator', name: 'Above Indicator' },
            { id: 'below_indicator', name: 'Below Indicator' }
        ]
    }), []);

    // Fetch Catalog on Mount
    useEffect(() => {
        const fetchCatalog = async () => {
            try {
                const data = await getIndicatorCatalog();
                if (data && (data.technical_indicators || data.fundamental_indicators)) {
                    setCatalog(data);
                } else {
                    // Use fallback if API returns empty data
                    console.warn('API returned empty catalog, using fallback');
                    setCatalog(FALLBACK_CATALOG);
                }
            } catch (err) {
                console.error('Failed to load catalog:', err);
                // Use fallback on error
                setCatalog(FALLBACK_CATALOG);
                setError('Using offline indicator catalog. Some features may be limited.');
            } finally {
                setLoading(false);
            }
        };

        fetchCatalog();
    }, [FALLBACK_CATALOG]);

    const handleAddCondition = () => {
        setConditions([...conditions, { indicator: '', operator: '>', value: '', weight: 1.0 }]);
    };

    const handleRemoveCondition = (index) => {
        const newConditions = [...conditions];
        newConditions.splice(index, 1);
        setConditions(newConditions);
    };

    const handleConditionChange = (index, field, value) => {
        const newConditions = [...conditions];
        newConditions[index][field] = value;
        setConditions(newConditions);
    };

    // Apply a pre-built template
    const applyTemplate = (template) => {
        setName(template.name);
        setDescription(template.description);
        setRiskLevel(template.riskLevel);
        setCategory(template.category);
        setConditions(template.conditions.map(c => ({ ...c })));
        setError(null);
        setSuccess(null);
    };

    const validateForm = () => {
        if (!name.trim()) return "Strategy name is required";
        if (!description.trim()) return "Description is required";
        if (conditions.length === 0) return "At least one condition is required";

        for (let i = 0; i < conditions.length; i++) {
            const c = conditions[i];
            if (!c.indicator) return `Condition ${i + 1}: Indicator is missing`;
            const noValueOps = ['increasing', 'decreasing'];
            if (c.value === '' && !noValueOps.includes(c.operator) && c.indicator !== 'macd_hist') return `Condition ${i + 1}: Value is missing`;
        }
        return null;
    };

    const handleSave = async () => {
        const validationError = validateForm();
        if (validationError) {
            setError(validationError);
            return;
        }

        setSaving(true);
        setError(null);
        setSuccess(null);

        const strategyData = {
            name: name.toLowerCase().replace(/\s+/g, '_'),
            description,
            strategy_type: 'custom',
            conditions: conditions.map(c => ({
                ...c,
                value: isNaN(Number(c.value)) ? c.value : Number(c.value),
                weight: Number(c.weight)
            })),
            metadata: {
                category,
                risk_level: riskLevel,
                created_at: new Date().toISOString()
            }
        };

        try {
            // Save the strategy directly (frontend validation above is sufficient)
            await createCustomStrategy(strategyData);
            setSuccess('Strategy created successfully!');

            setTimeout(() => {
                if (onSave) onSave(strategyData);
            }, 1500);

        } catch (err) {
            console.error('Failed to save strategy:', err);
            // Provide a clearer error message
            if (err.message === 'Request cancelled') {
                setError('Save request timed out. Please check that the backend server is running and try again.');
            } else {
                setError(err.message || 'Failed to save strategy');
            }
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-12">
                <Loader className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
        );
    }

    if (!catalog) {
        return (
            <div className="p-6 text-center text-red-400">
                <AlertCircle className="w-12 h-12 mx-auto mb-3" />
                <p>Failed to load component data.</p>
                <Button onClick={onCancel} className="mt-4">Go Back</Button>
            </div>
        );
    }

    // Flatten indicators for dropdown — grouped by category
    const technicalIndicators = Object.entries(catalog.technical_indicators || {}).flatMap(([cat, indicators]) =>
        indicators.map(ind => ({ ...ind, category: cat, group: 'Technical' }))
    );
    const fundamentalIndicators = Object.entries(catalog.fundamental_indicators || {}).flatMap(([cat, indicators]) =>
        indicators.map(ind => ({ ...ind, category: cat, group: 'Fundamental' }))
    );
    const allIndicators = [...technicalIndicators, ...fundamentalIndicators];
    const operators = catalog.operators || [];

    // Category labels for optgroup display
    const categoryLabels = {
        momentum: 'Momentum',
        trend: 'Trend',
        volatility: 'Volatility',
        volume: 'Volume',
        relative: 'Relative (Day-over-Day)',
        multi_timeframe: 'Multi-Timeframe',
        valuation: 'Valuation',
        profitability: 'Profitability',
        financial_health: 'Financial Health',
        growth: 'Growth',
    };

    // Group indicators by category for <optgroup>
    const indicatorGroups = {};
    allIndicators.forEach(ind => {
        const key = ind.category;
        if (!indicatorGroups[key]) indicatorGroups[key] = [];
        indicatorGroups[key].push(ind);
    });

    // Check if operator is a compare-to-indicator type
    const isIndicatorCompareOp = (op) => ['above_indicator', 'below_indicator'].includes(op);

    return (
        <div className="space-y-6 animate-fade-in relative">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Button variant="ghost" size="sm" onClick={onCancel}>
                        <ArrowLeft className="w-5 h-5" />
                    </Button>
                    <h2 className="text-2xl font-black text-white">Create New Strategy</h2>
                </div>
            </div>

            {/* Quick Start Templates */}
            <Card className="p-4 border-dashed border-2 border-blue-500/30 bg-blue-500/5">
                <div className="flex items-center gap-2 mb-3">
                    <Zap className="w-5 h-5 text-yellow-400" />
                    <h3 className="font-bold text-white text-sm">Quick Start — Use a Template</h3>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {STRATEGY_TEMPLATES.map(t => (
                        <button
                            key={t.id}
                            onClick={() => applyTemplate(t)}
                            className="p-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-blue-400/50 transition-all text-left group"
                        >
                            <div className="flex items-center gap-2 mb-1">
                                <Copy className="w-3.5 h-3.5 text-blue-400 group-hover:text-blue-300" />
                                <span className="text-sm font-semibold text-white">{t.name}</span>
                            </div>
                            <p className="text-xs text-gray-400 line-clamp-2">{t.description}</p>
                            <div className="flex gap-1 mt-2">
                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${t.riskLevel === 'High' ? 'bg-red-500/20 text-red-300' : t.riskLevel === 'Low' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'}`}>
                                    {t.riskLevel} Risk
                                </span>
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300">
                                    {t.conditions.length} conditions
                                </span>
                            </div>
                        </button>
                    ))}
                </div>
            </Card>

            {/* Error/Success Messages */}
            {error && (
                <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-xl flex items-center gap-3 text-red-200">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <span>{error}</span>
                </div>
            )}
            {success && (
                <div className="p-4 bg-green-500/20 border border-green-500/50 rounded-xl flex items-center gap-3 text-green-200">
                    <CheckCircle className="w-5 h-5 flex-shrink-0" />
                    <span>{success}</span>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Left Column: Form */}
                <div className="md:col-span-2 space-y-6">
                    <Card className="p-6">
                        <h3 className="text-lg font-bold text-white mb-4">Strategy Details</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-400 mb-1">Strategy Name</label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="e.g., Aggressive Momentum Breakout"
                                    className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-400 mb-1">Description</label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Describe what this strategy looks for..."
                                    rows="3"
                                    className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-400 mb-1">Risk Level</label>
                                    <select
                                        value={riskLevel}
                                        onChange={(e) => setRiskLevel(e.target.value)}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500"
                                    >
                                        <option value="Low">Low</option>
                                        <option value="Medium">Medium</option>
                                        <option value="High">High</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-400 mb-1">Category</label>
                                    <select
                                        value={category}
                                        onChange={(e) => setCategory(e.target.value)}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg p-3 text-white focus:outline-none focus:border-blue-500"
                                    >
                                        <option value="Custom">Custom</option>
                                        <option value="Technical">Technical</option>
                                        <option value="Fundamental">Fundamental</option>
                                        <option value="Hybrid">Hybrid</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </Card>

                    <Card className="p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-bold text-white">Conditions</h3>
                            <Button onClick={handleAddCondition} variant="secondary" size="sm">
                                <Plus className="w-4 h-4 mr-2" />
                                Add Condition
                            </Button>
                        </div>

                        <div className="space-y-3">
                            {conditions.map((condition, idx) => (
                                <div key={idx} className="p-4 bg-white/5 rounded-xl border border-white/10">
                                    <div className="flex items-center gap-2 mb-2">
                                        <span className="text-xs font-bold text-blue-400 bg-blue-500/20 rounded-full w-6 h-6 flex items-center justify-center">{idx + 1}</span>
                                        {condition.indicator && (
                                            <span className="text-xs text-gray-400 italic">
                                                {allIndicators.find(i => i.id === condition.indicator)?.description || ''}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex flex-wrap gap-3 items-end">
                                    <div className="flex-1 min-w-[200px]">
                                        <label className="block text-xs font-medium text-gray-400 mb-1">Indicator</label>
                                        <select
                                            value={condition.indicator}
                                            onChange={(e) => handleConditionChange(idx, 'indicator', e.target.value)}
                                            className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-blue-500"
                                        >
                                            <option value="">Select Indicator...</option>
                                            {Object.entries(indicatorGroups).map(([cat, inds]) => (
                                                <optgroup key={cat} label={categoryLabels[cat] || cat}>
                                                    {inds.map(ind => (
                                                        <option key={ind.id} value={ind.id}>{ind.name}</option>
                                                    ))}
                                                </optgroup>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="w-[160px]">
                                        <label className="block text-xs font-medium text-gray-400 mb-1">Operator</label>
                                        <select
                                            value={condition.operator}
                                            onChange={(e) => handleConditionChange(idx, 'operator', e.target.value)}
                                            className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-blue-500"
                                        >
                                            {operators.map(op => (
                                                <option key={op.id} value={op.id}>{op.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="flex-1 min-w-[100px]">
                                        <label className="block text-xs font-medium text-gray-400 mb-1">
                                            {isIndicatorCompareOp(condition.operator) ? 'Compare To Indicator' : 'Value'}
                                        </label>
                                        {isIndicatorCompareOp(condition.operator) ? (
                                            <select
                                                value={condition.value}
                                                onChange={(e) => handleConditionChange(idx, 'value', e.target.value)}
                                                className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-blue-500"
                                            >
                                                <option value="">Select Indicator...</option>
                                                {Object.entries(indicatorGroups).map(([cat, inds]) => (
                                                    <optgroup key={cat} label={categoryLabels[cat] || cat}>
                                                        {inds.filter(ind => ind.id !== condition.indicator).map(ind => (
                                                            <option key={ind.id} value={ind.id}>{ind.name}</option>
                                                        ))}
                                                    </optgroup>
                                                ))}
                                            </select>
                                        ) : (
                                            <input
                                                type="text"
                                                value={condition.value}
                                                onChange={(e) => handleConditionChange(idx, 'value', e.target.value)}
                                                placeholder={condition.operator === 'increasing' || condition.operator === 'decreasing' ? 'auto' : 'e.g. 50'}
                                                disabled={condition.operator === 'increasing' || condition.operator === 'decreasing'}
                                                className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-blue-500 disabled:opacity-50"
                                            />
                                        )}
                                    </div>
                                    <div className="w-[80px]">
                                        <label className="block text-xs font-medium text-gray-400 mb-1">Weight</label>
                                        <input
                                            type="number"
                                            step="0.1"
                                            value={condition.weight}
                                            onChange={(e) => handleConditionChange(idx, 'weight', e.target.value)}
                                            className="w-full bg-black/20 border border-white/10 rounded-lg p-2 text-sm text-white focus:outline-none focus:border-blue-500"
                                        />
                                    </div>
                                    <Button
                                        onClick={() => handleRemoveCondition(idx)}
                                        variant="danger"
                                        size="xs"
                                        className="h-[38px] w-[38px] p-0 flex items-center justify-center"
                                        disabled={conditions.length === 1}
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Card>
                </div>

                {/* Right Column: Preview/Summary */}
                <div className="space-y-6">
                    <Card className="p-6 bg-blue-900/10 border-blue-500/20">
                        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                            <Info className="w-5 h-5 text-blue-400" />
                            Summary
                        </h3>
                        <div className="space-y-4 text-sm text-gray-300">
                            <p><strong className="text-gray-400">Name:</strong> {name || 'Running...'}</p>
                            <p><strong className="text-gray-400">Type:</strong> {category}</p>
                            <p><strong className="text-gray-400">Conditions:</strong> {conditions.length}</p>

                            <div className="pt-4 border-t border-white/10">
                                <p className="text-xs text-gray-400 mb-2">Selected Indicators:</p>
                                <div className="flex flex-wrap gap-2">
                                    {conditions.filter(c => c.indicator).map((c, i) => (
                                        <span key={i} className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded text-xs">
                                            {allIndicators.find(ind => ind.id === c.indicator)?.name || c.indicator}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="mt-8 pt-6 border-t border-white/10">
                            <Button
                                onClick={handleSave}
                                disabled={saving}
                                className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-bold py-3 rounded-xl shadow-lg shadow-blue-500/20 transition-all transform hover:scale-[1.02]"
                            >
                                {saving ? (
                                    <>
                                        <Loader className="w-5 h-5 animate-spin mr-2" />
                                        Saving...
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-5 h-5 mr-2" />
                                        Save Strategy
                                    </>
                                )}
                            </Button>
                        </div>
                    </Card>

                    <div className="p-4 bg-yellow-500/10 rounded-xl border border-yellow-500/20">
                        <h4 className="font-bold text-yellow-500 flex items-center gap-2 mb-2">
                            <AlertCircle className="w-4 h-4" />
                            Strategy Building Tips
                        </h4>
                        <ul className="text-xs text-gray-400 space-y-2 list-disc pl-4">
                            <li>Higher weights (1.5+) give a condition more importance in scoring.</li>
                            <li><strong>RSI &lt; 30</strong> = oversold, <strong>RSI &gt; 70</strong> = overbought.</li>
                            <li><strong>ADX &gt; 25</strong> = strong trend, <strong>ADX &lt; 20</strong> = ranging market.</li>
                            <li><strong>P/E &lt; 15</strong> typically identifies value stocks.</li>
                            <li>Use <strong className="text-purple-300">Relative</strong> indicators for day-over-day comparisons (e.g., MACD rising).</li>
                            <li>Use <strong className="text-purple-300">Multi-Timeframe</strong> indicators for weekly/monthly signals.</li>
                            <li>Use <strong className="text-blue-300">Above/Below Indicator</strong> operators to compare two indicators (e.g., SMA 20 above SMA 50).</li>
                            <li>Use <strong className="text-blue-300">Increasing/Decreasing</strong> operators for momentum conditions (no value needed).</li>
                            <li>Combine Technical + Fundamental indicators for a &quot;Hybrid&quot; approach.</li>
                            <li>After saving, your strategy appears in the Screener tab.</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StrategyBuilder;
