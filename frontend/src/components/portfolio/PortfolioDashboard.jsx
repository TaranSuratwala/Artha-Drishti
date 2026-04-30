import React, { useState, useEffect } from 'react';
import { Plus, TrendingUp, TrendingDown, PieChart, Trash2, ArrowUpRight, ArrowDownRight, Activity, Newspaper, ExternalLink, RefreshCw } from 'lucide-react';
import { Card, Button, LoadingSpinner } from '../ui';
import * as api from '../../services/api';
import { formatINR, formatINRWithSign, formatPercent } from '../../utils/currencyUtils';

export const PortfolioDashboard = () => {
    const [portfolio, setPortfolio] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [news, setNews] = useState([]);
    const [newsLoading, setNewsLoading] = useState(false);

    // Form state
    const [formData, setFormData] = useState({
        ticker: '', type: 'BUY', quantity: '', price: '', date: new Date().toISOString().split('T')[0]
    });

    useEffect(() => {
        loadPortfolio();
        loadNews();
    }, []);

    const loadPortfolio = async () => {
        try {
            const result = await api.getPortfolio();
            if (result?.success && result.data) {
                setPortfolio(result.data);
            } else if (result) {
                // Fallback if API returns direct data
                setPortfolio(result);
            }
        } catch (err) {
            console.error('Failed to load portfolio:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadNews = async () => {
        setNewsLoading(true);
        try {
            const result = await api.getPortfolioNews(10);
            // API returns { portfolio: { SYMBOL: { articles: [...] } } }
            if (result?.portfolio && typeof result.portfolio === 'object') {
                const allArticles = [];
                for (const [ticker, data] of Object.entries(result.portfolio)) {
                    const articles = data?.articles || [];
                    for (const art of articles) {
                        allArticles.push({
                            title: art.headline || art.title || '',
                            source: art.source || 'News',
                            published_at: art.datetime || art.published_at || '',
                            url: art.url || '',
                            tickers: [ticker],
                            sentiment: art.sentiment ?? null,
                        });
                    }
                }
                // Sort by date descending, newest first
                allArticles.sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''));
                setNews(allArticles);
            } else if (result?.news) {
                setNews(result.news);
            } else if (Array.isArray(result)) {
                setNews(result);
            }
        } catch (err) {
            console.error('Failed to load portfolio news:', err);
        } finally {
            setNewsLoading(false);
        }
    };

    const handleAddTransaction = async (e) => {
        e.preventDefault();
        try {
            await api.addTransaction(formData);
            setShowAddModal(false);
            setFormData({ ticker: '', type: 'BUY', quantity: '', price: '', date: new Date().toISOString().split('T')[0] });
            loadPortfolio();
        } catch (err) {
            alert(err.message);
        }
    };

    const handleDelete = async (id) => {
        if (!confirm('Delete transaction?')) return;
        try {
            await api.deleteTransaction(id);
            loadPortfolio();
        } catch (err) {
            console.error(err);
        }
    };

    if (loading) return <LoadingSpinner text="Loading portfolio..." />;

    const { summary, holdings, transactions } = portfolio || {};

    return (
        <div className="space-y-6 animate-fade-in portfolio-dashboard">
            {/* Header */}
            <div className="flex justify-between items-center portfolio-dashboard-header">
                <h2 className="text-2xl font-bold flex items-center gap-2 portfolio-dashboard-title">
                    <Activity className="w-6 h-6 text-purple-400" />
                    My Portfolio
                </h2>
                <Button onClick={() => setShowAddModal(true)} variant="purple">
                    <Plus className="w-4 h-4 mr-2" /> Add Transaction
                </Button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card className="p-6 industry-section-card portfolio-kpi-card portfolio-kpi-card-value">
                    <div className="text-gray-300 text-sm font-medium mb-1 uppercase tracking-wider">Total Value</div>
                    <div className="text-3xl font-black text-white flex items-center gap-2">
                        <span className="text-blue-400 text-2xl">₹</span>
                        {formatINR(summary?.total_value).replace('₹', '')}
                    </div>
                </Card>
                <Card className="p-6 industry-section-card portfolio-kpi-card portfolio-kpi-card-cost">
                    <div className="text-gray-300 text-sm font-medium mb-1 uppercase tracking-wider">Total Cost</div>
                    <div className="text-3xl font-black text-white">
                        {formatINR(summary?.total_cost)}
                    </div>
                </Card>
                <Card className="p-6 industry-section-card portfolio-kpi-card portfolio-kpi-card-pnl">
                    <div className="text-gray-300 text-sm font-medium mb-1 uppercase tracking-wider">Total P&L</div>
                    <div className={`text-3xl font-black flex items-center gap-2 ${summary?.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {summary?.total_pnl >= 0 ? <TrendingUp className="w-6 h-6" /> : <TrendingDown className="w-6 h-6" />}
                        {formatINRWithSign(summary?.total_pnl)}
                        <span className="text-lg font-bold opacity-80 bg-black/20 px-2 py-0.5 rounded-lg">
                            {formatPercent(summary?.total_pnl_pct)}
                        </span>
                    </div>
                </Card>
            </div>

            {/* Holdings Table */}
            <Card className="overflow-hidden border-white/10 industry-table-shell portfolio-holdings-card">
                <div className="p-4 bg-white/5 border-b border-white/10 flex justify-between items-center portfolio-section-header">
                    <h3 className="font-bold text-lg flex items-center gap-2 text-blue-300">
                        <PieChart className="w-5 h-5" /> Current Holdings
                    </h3>
                    <span className="text-xs text-gray-500 uppercase font-semibold tracking-wider">
                        {holdings?.length || 0} Positions
                    </span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-black/40 text-left text-xs text-gray-400 uppercase tracking-wider font-semibold">
                            <tr>
                                <th className="p-4">Ticker</th>
                                <th className="p-4 text-right">Qty</th>
                                <th className="p-4 text-right">Avg Price</th>
                                <th className="p-4 text-right">Current Price</th>
                                <th className="p-4 text-right">Value</th>
                                <th className="p-4 text-right">Unrealized P&L</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {holdings?.map((h) => (
                                <tr key={h.ticker} className="hover:bg-white/5 transition duration-150 portfolio-holding-row">
                                    <td className="p-4 font-black text-white text-lg tracking-tight">{h.ticker}</td>
                                    <td className="p-4 text-right text-gray-300 font-mono">{h.quantity}</td>
                                    <td className="p-4 text-right text-gray-300 font-mono">{formatINR(h.avg_price)}</td>
                                    <td className="p-4 text-right font-mono font-semibold text-blue-300">{formatINR(h.current_price)}</td>
                                    <td className="p-4 text-right font-bold text-white font-mono">{formatINR(h.market_value)}</td>
                                    <td className={`p-4 text-right font-bold font-mono ${h.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        <div className="flex flex-col items-end leading-tight">
                                            <span>{formatINRWithSign(h.unrealized_pnl)}</span>
                                            <span className="text-xs opacity-70">({h.pnl_pct}%)</span>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {(!holdings || holdings.length === 0) && (
                                <tr>
                                    <td colSpan="6" className="p-12 text-center text-gray-500">
                                        <div className="flex flex-col items-center gap-3">
                                            <div className="p-4 bg-white/5 rounded-full">
                                                <PieChart className="w-8 h-8 opacity-50" />
                                            </div>
                                            <p className="text-lg font-medium">No holdings found</p>
                                            <p className="text-sm">Add your first transaction to start tracking your portfolio.</p>
                                            <Button size="sm" variant="secondary" onClick={() => setShowAddModal(true)} className="mt-2">
                                                Add Transaction
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </Card>

            {/* Portfolio News Section */}
            <Card className="border-white/10 industry-section-card portfolio-news-card">
                <div className="p-5 bg-white/5 border-b border-white/10 flex justify-between items-center portfolio-section-header">
                    <h3 className="font-bold text-lg flex items-center gap-2 text-orange-300">
                        <Newspaper className="w-5 h-5" /> Portfolio News & Sentiment
                    </h3>
                    <button
                        onClick={loadNews}
                        disabled={newsLoading}
                        className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition"
                    >
                        <RefreshCw className={`w-3 h-3 ${newsLoading ? 'animate-spin' : ''}`} />
                        Refresh
                    </button>
                </div>
                <div className="p-5">
                    {newsLoading ? (
                        <div className="text-center py-8 text-gray-500">
                            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                            Loading news...
                        </div>
                    ) : news.length > 0 ? (
                        <div className="space-y-3 max-h-96 overflow-y-auto">
                            {news.slice(0, 10).map((article, idx) => (
                                <a
                                    key={idx}
                                    href={article.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block p-4 bg-white/5 rounded-xl border border-white/5 hover:bg-white/10 hover:border-white/20 transition group portfolio-news-item"
                                >
                                    <div className="flex justify-between items-start gap-3">
                                        <div className="flex-1">
                                            <h4 className="font-semibold text-white group-hover:text-orange-300 transition line-clamp-2">
                                                {article.title || article.headline}
                                            </h4>
                                            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                                                <span className="text-xs text-gray-500">
                                                    {article.source} {article.published_at ? ` \u2022 ${new Date(article.published_at).toLocaleDateString()}` : ''}
                                                </span>
                                                {article.sentiment != null && article.sentiment !== 0 && (
                                                    <span className={`text-[10px] px-2 py-0.5 rounded-md font-bold ${
                                                        article.sentiment > 0.15 ? 'bg-green-500/15 text-green-400 border border-green-500/25' :
                                                        article.sentiment < -0.15 ? 'bg-red-500/15 text-red-400 border border-red-500/25' :
                                                        'bg-gray-500/15 text-gray-400 border border-gray-500/25'
                                                    }`}>
                                                        {article.sentiment > 0.15 ? 'Bullish' : article.sentiment < -0.15 ? 'Bearish' : 'Neutral'}
                                                    </span>
                                                )}
                                            </div>
                                            {article.tickers && article.tickers.length > 0 && (
                                                <div className="flex gap-1 mt-2">
                                                    {article.tickers.slice(0, 3).map((ticker, i) => (
                                                        <span key={i} className="px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded text-xs">
                                                            {ticker}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <ExternalLink className="w-4 h-4 text-gray-500 group-hover:text-orange-300 flex-shrink-0 mt-1" />
                                    </div>
                                </a>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-8 text-gray-500">
                            <Newspaper className="w-8 h-8 opacity-50 mx-auto mb-2" />
                            <p>No news available for your portfolio</p>
                            <p className="text-xs mt-1">Add holdings to see related news</p>
                        </div>
                    )}
                </div>
            </Card>

            {/* Recent Transactions (Optional, can be added later) */}
            {transactions?.length > 0 && (
                <Card className="pt-4 p-5 industry-section-card portfolio-transactions-card">
                    <h3 className="text-lg font-bold text-gray-400 mb-4 flex items-center gap-2">
                        <Activity className="w-5 h-5" /> Recent Transactions
                    </h3>
                    <div className="space-y-2">
                        {transactions.slice().reverse().slice(0, 5).map(t => (
                            <div key={t.id} className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/5 hover:bg-white/10 transition">
                                <div className="flex items-center gap-4">
                                    <div className={`p-2 rounded-lg ${t.type === 'BUY' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                                        {t.type === 'BUY' ? <ArrowDownRight className="w-4 h-4" /> : <ArrowUpRight className="w-4 h-4" />}
                                    </div>
                                    <div>
                                        <div className="font-bold text-white">{t.ticker}</div>
                                        <div className="text-xs text-gray-500">{t.date}</div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="font-mono text-white">{t.type} {t.quantity} @ {formatINR(t.price)}</div>
                                    <button onClick={() => handleDelete(t.id)} className="text-xs text-red-500 hover:text-red-400 mt-1 flex items-center justify-end gap-1">
                                        <Trash2 className="w-3 h-3" /> Delete
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>
            )}

            {/* Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/90 flex items-center justify-center z-50 p-4 animate-fade-in portfolio-modal-overlay">
                    <Card className="w-full max-w-md p-6 bg-slate-800 border-2 border-slate-600 shadow-2xl relative portfolio-modal-card">
                        <div className="absolute inset-0 bg-slate-800 rounded-lg" />
                        <h3 className="text-xl font-bold mb-6 flex items-center gap-2 relative">
                            <Plus className="w-5 h-5 text-purple-400" /> Add Transaction
                        </h3>
                        <form onSubmit={handleAddTransaction} className="space-y-4 relative">
                            <div>
                                <label className="block text-sm text-gray-400 mb-1.5 font-medium">Ticker Symbol</label>
                                <input
                                    className="w-full bg-black/40 border border-white/10 rounded-xl p-3.5 text-white focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none uppercase font-bold tracking-wide transition-all"
                                    value={formData.ticker}
                                    onChange={e => setFormData({ ...formData, ticker: e.target.value.toUpperCase() })}
                                    placeholder="E.g. AAPL, RELIANCE"
                                    required
                                    autoFocus
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-gray-400 mb-1.5 font-medium">Type</label>
                                    <div className="relative">
                                        <select
                                            className="w-full bg-black/40 border border-white/10 rounded-xl p-3.5 text-white focus:border-purple-500 outline-none appearance-none font-semibold"
                                            value={formData.type}
                                            onChange={e => setFormData({ ...formData, type: e.target.value })}
                                        >
                                            <option value="BUY">BUY</option>
                                            <option value="SELL">SELL</option>
                                        </select>
                                        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-gray-500">
                                            <ArrowDownRight className="w-4 h-4" />
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm text-gray-400 mb-1.5 font-medium">Date</label>
                                    <input
                                        type="date"
                                        className="w-full bg-black/40 border border-white/10 rounded-xl p-3.5 text-white focus:border-purple-500 outline-none text-sm"
                                        value={formData.date}
                                        onChange={e => setFormData({ ...formData, date: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-gray-400 mb-1.5 font-medium">Quantity</label>
                                    <input
                                        type="number" step="any"
                                        className="w-full bg-black/40 border border-white/10 rounded-xl p-3.5 text-white focus:border-purple-500 outline-none font-mono"
                                        value={formData.quantity}
                                        onChange={e => setFormData({ ...formData, quantity: e.target.value })}
                                        required
                                        placeholder="0.00"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-gray-400 mb-1.5 font-medium">Price per Share</label>
                                    <div className="relative">
                                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500">₹</span>
                                        <input
                                            type="number" step="any"
                                            className="w-full bg-black/40 border border-white/10 rounded-xl p-3.5 pl-8 text-white focus:border-purple-500 outline-none font-mono"
                                            value={formData.price}
                                            onChange={e => setFormData({ ...formData, price: e.target.value })}
                                            required
                                            placeholder="0.00"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="pt-4 flex gap-3">
                                <Button className="flex-1 py-3" variant="secondary" onClick={() => setShowAddModal(false)} type="button">
                                    Cancel
                                </Button>
                                <Button className="flex-1 py-3 font-bold shadow-lg shadow-purple-900/20" variant="purple" type="submit">
                                    Confirm Transaction
                                </Button>
                            </div>
                        </form>
                    </Card>
                </div>
            )}
        </div>
    );
};
