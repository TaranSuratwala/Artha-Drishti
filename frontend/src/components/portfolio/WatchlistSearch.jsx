import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Search, Plus, TrendingUp, TrendingDown, X, Loader } from 'lucide-react';
import { searchStocks } from '../../services/api';

/**
 * WatchlistSearch Component - Search and add stocks to watchlist
 * Features: Debounced search, autocomplete dropdown, add to watchlist
 */
const WatchlistSearch = ({ onAddToWatchlist, watchlist = [] }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);
    const [error, setError] = useState(null);
    const inputRef = useRef(null);
    const dropdownRef = useRef(null);

    // Debounced search
    useEffect(() => {
        if (query.length < 1) {
            setResults([]);
            setShowDropdown(false);
            return;
        }

        const debounceTimer = setTimeout(async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await searchStocks(query);
                setResults(data.results || []);
                setShowDropdown(true);
            } catch (err) {
                console.error('Search failed:', err);
                setError('Search failed');
                setResults([]);
            } finally {
                setLoading(false);
            }
        }, 300);

        return () => clearTimeout(debounceTimer);
    }, [query]);

    // Click outside to close dropdown
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target) &&
                inputRef.current &&
                !inputRef.current.contains(event.target)
            ) {
                setShowDropdown(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleAddStock = useCallback(async (ticker) => {
        if (watchlist.includes(ticker)) {
            return; // Already in watchlist
        }

        try {
            await onAddToWatchlist(ticker);
            setQuery('');
            setShowDropdown(false);
            setResults([]);
        } catch (err) {
            console.error('Failed to add stock:', err);
        }
    }, [onAddToWatchlist, watchlist]);

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            setShowDropdown(false);
        }
    };

    return (
        <div className="watchlist-search relative industry-search-shell">
            {/* Search Input */}
            <div className="relative flex items-center">
                <div className="absolute left-3 pointer-events-none">
                    {loading ? (
                        <Loader size={18} className="text-blue-400 animate-spin" />
                    ) : (
                        <Search size={18} className="text-gray-400" />
                    )}
                </div>
                <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value.toUpperCase())}
                    onFocus={() => results.length > 0 && setShowDropdown(true)}
                    onKeyDown={handleKeyDown}
                    placeholder="Search stocks to add (e.g., RELIANCE, TCS)..."
                    className="w-full pl-10 pr-10 py-3 bg-white/5 border border-white/10 rounded-xl industry-search-input 
                             text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50
                             focus:ring-2 focus:ring-blue-500/20 transition-all"
                />
                {query && (
                    <button
                        onClick={() => {
                            setQuery('');
                            setResults([]);
                            setShowDropdown(false);
                        }}
                        className="absolute right-3 p-1 hover:bg-white/10 rounded-full transition-all industry-search-clear"
                    >
                        <X size={16} className="text-gray-400" />
                    </button>
                )}
            </div>

            {/* Dropdown Results */}
            {showDropdown && (
                <div
                    ref={dropdownRef}
                    className="absolute top-full left-0 right-0 mt-2 bg-slate-800/95 backdrop-blur-xl industry-search-dropdown 
                             border border-white/10 rounded-xl shadow-2xl z-50 max-h-80 overflow-y-auto"
                >
                    {error ? (
                        <div className="p-4 text-center text-red-400 text-sm">
                            {error}
                        </div>
                    ) : results.length === 0 ? (
                        <div className="p-4 text-center text-gray-400 text-sm">
                            {query.length > 0 ? 'No stocks found' : 'Start typing to search'}
                        </div>
                    ) : (
                        <ul className="divide-y divide-white/5">
                            {results.map((stock) => {
                                const isInWatchlist = watchlist.includes(stock.ticker);
                                const isPositive = stock.change_pct >= 0;

                                return (
                                    <li
                                        key={stock.ticker}
                                        className={`flex items-center justify-between p-3 hover:bg-white/5 industry-search-result 
                                                  transition-all cursor-pointer ${isInWatchlist ? 'opacity-50' : ''}`}
                                        onClick={() => !isInWatchlist && handleAddStock(stock.ticker)}
                                    >
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <span className="font-bold text-white">{stock.ticker}</span>
                                                {isInWatchlist && (
                                                    <span className="text-[10px] px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded-full">
                                                        In Watchlist
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-xs text-gray-400 truncate max-w-[200px]">
                                                {stock.company_name}
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <div className="text-right">
                                                <p className="font-semibold text-white text-sm">
                                                    ₹{stock.current_price?.toFixed(2)}
                                                </p>
                                                <div className={`flex items-center gap-1 text-xs ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                                                    {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                                                    <span>{isPositive ? '+' : ''}{stock.change_pct?.toFixed(2)}%</span>
                                                </div>
                                            </div>
                                            {!isInWatchlist && (
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleAddStock(stock.ticker);
                                                    }}
                                                    className="p-2 bg-blue-500/20 hover:bg-blue-500/30 rounded-lg transition-all"
                                                    title="Add to watchlist"
                                                >
                                                    <Plus size={16} className="text-blue-400" />
                                                </button>
                                            )}
                                        </div>
                                    </li>
                                );
                            })}
                        </ul>
                    )}
                </div>
            )}
        </div>
    );
};

export { WatchlistSearch };
export default WatchlistSearch;
