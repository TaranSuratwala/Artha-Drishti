/**
 * GenAI Stock Intelligence — API Service Layer
 * 
 * Centralised HTTP client with:
 *  • Automatic JWT attachment
 *  • Request deduplication (prevents duplicate in-flight requests)
 *  • Response caching with TTL
 *  • Retry with exponential back-off (network errors / 5xx)
 *  • Abort-controller support (cancel on unmount)
 *  • Consistent error handling that downstream components can rely on
 */

// ─── Configuration ──────────────────────────────────────────────────────────

const buildApiBase = (rawBase) => {
    const normalized = (rawBase || '').trim().replace(/\/+$/, '');
    if (!normalized) return '/api';
    if (normalized.endsWith('/api')) return normalized;
    return `${normalized}/api`;
};

const API_BASE = buildApiBase(import.meta.env.VITE_API_BASE_URL); // proxied in dev; configurable in prod
const DEFAULT_TIMEOUT = 30_000;                // 30 s
const MAX_RETRIES = 2;
const RETRY_BASE_MS = 1000;

// ─── In-memory cache ────────────────────────────────────────────────────────

const _cache = new Map();                      // key → { data, expires }
const _inflight = new Map();                   // key → Promise

// ─── Logout guard: prevent stale 401s from clearing a fresh token ───────────

let _logoutDispatched = false;                 // true after first 401-driven logout
const _pendingControllers = new Set();         // track in-flight AbortControllers

/** Call on logout to abort every pending request so stale 401 handlers can't race. */
export function abortAllPending() {
    for (const ctrl of _pendingControllers) {
        try { ctrl.abort(); } catch { /* ignore */ }
    }
    _pendingControllers.clear();
}

/** Reset the logout guard (call after a successful login). */
export function resetLogoutGuard() {
    _logoutDispatched = false;
}

function cacheKey(method, url, body) {
    return `${method}:${url}:${body ? JSON.stringify(body) : ''}`;
}

function getCached(key) {
    const entry = _cache.get(key);
    if (entry && entry.expires > Date.now()) return entry.data;
    _cache.delete(key);
    return null;
}

function setCache(key, data, ttlMs = 60_000) {
    _cache.set(key, { data, expires: Date.now() + ttlMs });
}

export function clearApiCache() {
    _cache.clear();
}

// ─── Auth token helpers ─────────────────────────────────────────────────────

function getToken() {
    return localStorage.getItem('auth_token');
}

function authHeaders() {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
}

function createRequestId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === 'function') {
        return globalThis.crypto.randomUUID();
    }
    return `req-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

// ─── Core fetch wrapper ─────────────────────────────────────────────────────

async function request(method, path, {
    body = null,
    cacheTtl = 0,        // ms – 0 = no cache
    retries = MAX_RETRIES,
    timeout = DEFAULT_TIMEOUT,
    signal = null,        // AbortSignal
    dedupe = true,        // deduplicate identical in-flight GETs
    abortable = true,     // false = immune to abortAllPending()
} = {}) {
    const url = `${API_BASE}${path}`;
    const key = cacheKey(method, url, body);

    // 1) Cache hit
    if (method === 'GET' && cacheTtl > 0) {
        const cached = getCached(key);
        if (cached) return cached;
    }

    // 2) Deduplicate identical in-flight GETs
    if (dedupe && method === 'GET' && _inflight.has(key)) {
        return _inflight.get(key);
    }

    const execute = async (attempt = 0) => {
        const controller = new AbortController();
        if (abortable) _pendingControllers.add(controller);
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        // Merge caller signal
        const onAbort = () => controller.abort();
        if (signal) {
            if (signal.aborted) {
                controller.abort();
            } else {
                signal.addEventListener('abort', onAbort, { once: true });
            }
        }

        // Capture the token we're sending so we can compare later
        const currentAuthHeaders = authHeaders();
        const sentToken = currentAuthHeaders.Authorization?.split(' ')[1] || null;
        const requestId = createRequestId();

        try {
            const headers = {
                ...currentAuthHeaders,
                'X-Request-Id': requestId,
            };

            if (body !== null && body !== undefined) {
                headers['Content-Type'] = 'application/json';
            }

            const opts = {
                method,
                headers,
                signal: controller.signal,
            };

            if (body !== null && body !== undefined) opts.body = JSON.stringify(body);

            const res = await fetch(url, opts);
            const responseRequestId = res.headers.get('X-Request-Id') || requestId;

            clearTimeout(timeoutId);
            if (abortable) _pendingControllers.delete(controller);
            if (signal) signal.removeEventListener('abort', onAbort);

            // Auth expired → force re-login
            // Only clear localStorage if the token hasn't been replaced by a fresh login
            if (res.status === 401) {
                const liveToken = localStorage.getItem('auth_token');
                // Skip if a newer token is already stored (user re-logged in)
                // or if this is a login/register request itself (invalid credentials)
                const isAuthEndpoint = path.startsWith('/auth/login') || path.startsWith('/auth/register') || path.startsWith('/auth/google');
                if (!isAuthEndpoint && (!liveToken || liveToken === sentToken)) {
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('auth_user');
                    if (!_logoutDispatched) {
                        _logoutDispatched = true;
                        window.dispatchEvent(new Event('auth:logout'));
                    }
                }
                throw new ApiError(
                    isAuthEndpoint ? 'Invalid credentials' : 'Session expired. Please log in again.',
                    401,
                    { request_id: responseRequestId },
                );
            }

            // Parse body (some endpoints return empty 204)
            let data = null;
            const text = await res.text();
            if (text) {
                try { data = JSON.parse(text); } catch { data = text; }
            }

            if (!res.ok) {
                const msg = data?.error || data?.message || `Request failed (${res.status})`;
                const payload = typeof data === 'object' && data !== null
                    ? { ...data, request_id: data.request_id || responseRequestId }
                    : { raw: data, request_id: responseRequestId };
                throw new ApiError(msg, res.status, payload);
            }

            // Cache GET results
            if (method === 'GET' && cacheTtl > 0) {
                setCache(key, data, cacheTtl);
            }

            return data;
        } catch (err) {
            clearTimeout(timeoutId);
            if (abortable) _pendingControllers.delete(controller);
            if (signal) signal.removeEventListener('abort', onAbort);

            // Retry on network errors or 5xx
            if (attempt < retries && (err.name === 'TypeError' || (err instanceof ApiError && err.status >= 500))) {
                const delay = RETRY_BASE_MS * 2 ** attempt + Math.random() * 500;
                await new Promise(r => setTimeout(r, delay));
                return execute(attempt + 1);
            }

            // Abort → don't throw to caller
            if (err.name === 'AbortError') {
                throw new ApiError('Request cancelled', 0);
            }

            throw err instanceof ApiError ? err : new ApiError(err.message || 'Network error', 0);
        }
    };

    const promise = execute().finally(() => _inflight.delete(key));
    if (dedupe && method === 'GET') _inflight.set(key, promise);
    return promise;
}

// ─── Error class ────────────────────────────────────────────────────────────

export class ApiError extends Error {
    constructor(message, status = 0, payload = null) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.payload = payload;
    }
}

// ─── Convenience verbs ──────────────────────────────────────────────────────

const get    = (path, opts) => request('GET',    path, opts);
const post   = (path, body, opts) => request('POST',   path, { body, ...opts });
const del    = (path, body, opts) => request('DELETE', path, { body, ...opts });

// ═══════════════════════════════════════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════════════════════════════════════

export async function loginUser(username, password) {
    return post('/auth/login', { username, password });
}

export async function signupUser(username, email, password) {
    return post('/auth/register', { username, email, password });
}

export async function fetchCurrentUser() {
    return get('/auth/me', { cacheTtl: 0 });
}

export async function loginWithGoogle(credential) {
    return post('/auth/google', { credential });
}

// ═══════════════════════════════════════════════════════════════════════════
//  HEALTH / META
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchHealth() {
    return get('/health', { cacheTtl: 30_000 });
}

export async function fetchStats() {
    return get('/stats', { cacheTtl: 30_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  STOCKS
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchStocks() {
    const data = await get('/stocks', { cacheTtl: 20_000 });
    return Array.isArray(data) ? data : data?.stocks || data?.data || [];
}

export async function fetchTickerHistory(ticker, period = '1y') {
    const data = await get(`/history/${encodeURIComponent(ticker)}?period=${encodeURIComponent(period)}`, { cacheTtl: 15_000 });
    return Array.isArray(data) ? data : data?.history || data?.data || [];
}

export async function searchStocks(query) {
    if (!query || query.length < 1) return [];
    const data = await get(`/stocks/search?q=${encodeURIComponent(query)}`, { cacheTtl: 30_000 });
    return Array.isArray(data) ? data : data?.results || data?.stocks || [];
}

export async function fetchTopMovers(count = 5) {
    const data = await get(`/market/movers?count=${count}`, { cacheTtl: 15_000, timeout: 12_000 });
    return data;
}

export async function fetchMarketOverview() {
    return get('/market/overview', { cacheTtl: 15_000, timeout: 12_000, retries: 1 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  REAL-TIME QUOTES (yfinance — 10-15 min delayed)
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchQuote(ticker) {
    return get(`/quote/${encodeURIComponent(ticker)}`, { cacheTtl: 5_000, timeout: 8_000, retries: 1 });
}

export async function fetchBatchQuotes(tickers) {
    if (!tickers || tickers.length === 0) return { quotes: {} };
    return post('/quotes/batch', { tickers }, { cacheTtl: 5_000, timeout: 10_000, retries: 1 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  PREDICTIONS / ML
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchPrediction(ticker, capital = 100000, riskPct = 2) {
    return post(`/predict/${encodeURIComponent(ticker)}`, { capital, risk_pct: riskPct }, { cacheTtl: 0, timeout: 120_000, retries: 0 });
}

export async function trainModel(ticker) {
    return post(`/train/${encodeURIComponent(ticker)}`, {}, { timeout: 300_000, retries: 0 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  SCREENER
// ═══════════════════════════════════════════════════════════════════════════

// Built-in strategy IDs that have dedicated backend routes
const BUILTIN_STRATEGY_IDS = new Set([
    'momentum', 'piotroski', 'swing', 'breakout', 'value', 'garp',
    'mean_reversion', 'quality_dividend', 'trend_following', 'contrarian',
    'macd_triple_alignment', 'quality_growth', 'custom'
]);

export async function runScreener(strategy, params = {}) {
    // If the strategy is NOT a built-in one, route to the custom strategy execution endpoint
    if (!BUILTIN_STRATEGY_IDS.has(strategy)) {
        return post(`/screen/custom/run/${encodeURIComponent(strategy)}`, params, { timeout: 120_000, retries: 1 });
    }
    // swing and value use GET; all others use POST
    const getStrategies = ['swing', 'value'];
    if (getStrategies.includes(strategy)) {
        return get(`/screen/${strategy}`, { timeout: 120_000 });
    }
    return post(`/screen/${strategy}`, params, { timeout: 120_000, retries: 1 });
}

export async function fetchRecommendations(timeframe = 'weekly') {
    const tf = String(timeframe || 'weekly').toLowerCase();
    return get(`/recommendations?timeframe=${encodeURIComponent(tf)}`, { cacheTtl: 20_000, timeout: 20_000, retries: 0 });
}

export async function runMultiStrategy(strategies, minOverlap = 2, opts = {}) {
    const {
        maxTickers = 800,
        maxResults = 150,
        timeout = 300_000,
        timeBudgetSeconds = null,
    } = opts;

    const timeoutSeconds = Math.max(60, Math.floor(timeout / 1000));
    const budgetSeconds = typeof timeBudgetSeconds === 'number'
        ? timeBudgetSeconds
        : Math.max(60, timeoutSeconds - 45);

    return post(
        '/screen/multi',
        {
            strategies,
            min_overlap: minOverlap,
            max_tickers: maxTickers,
            max_results: maxResults,
            time_budget_seconds: budgetSeconds,
        },
        { timeout, retries: 1 },
    );
}

export async function runMultiStrategyStream(strategies, minOverlap = 2, opts = {}) {
    const {
        maxTickers = 3000,
        maxResults = 150,
        timeBudgetSeconds = null,
        onProgress = null,
        signal = null,
    } = opts;

    const payload = {
        strategies,
        min_overlap: minOverlap,
        max_tickers: maxTickers,
        max_results: maxResults,
        time_budget_seconds: timeBudgetSeconds,
    };

    try {
        const res = await fetch(`${API_BASE}/screen/multi/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...authHeaders()
            },
            body: JSON.stringify(payload),
            signal
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || `HTTP error ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let finalResult = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            
            // Parse SSE chunks separated by \n\n
            const parts = buffer.split('\n\n');
            buffer = parts.pop() || ''; // Keep the last incomplete chunk in buffer
            
            for (const chunk of parts) {
                if (!chunk.trim()) continue;
                
                let eventType = 'message';
                let data = null;
                
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        eventType = line.substring(6).trim();
                    } else if (line.startsWith('data:')) {
                        try {
                            data = JSON.parse(line.substring(5).trim());
                        } catch(e) {
                            console.error('SSE JSON parse error:', e, line);
                        }
                    }
                }
                
                if (eventType === 'progress' && data && onProgress) {
                    onProgress(data);
                } else if (eventType === 'result' && data) {
                    finalResult = data;
                } else if (eventType === 'error' && data) {
                    throw new Error(data);
                }
            }
        }
        
        if (!finalResult) {
            throw new Error('Stream ended without returning a final result');
        }
        return finalResult;
    } catch (err) {
        if (err.name === 'AbortError') {
            // Throw custom ApiError structure so the UI knows it was cancelled
            const cancelErr = new Error('Request cancelled');
            cancelErr.status = 0;
            throw cancelErr;
        }
        throw err;
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  STRATEGIES
// ═══════════════════════════════════════════════════════════════════════════

export async function getStrategies() {
    return get('/screener/strategies', { cacheTtl: 120_000 });
}

export async function getIndicatorCatalog() {
    return get('/screener/catalog', { cacheTtl: 300_000 });
}

export async function createCustomStrategy(strategy) {
    // Use a direct fetch with generous timeout — immune to abortAllPending
    // so background 401 events can't kill the save request
    try {
        return await post('/screener/strategies', strategy, { timeout: 90_000, retries: 1, abortable: false });
    } catch (firstErr) {
        console.warn('Strategy save (wrapper) failed, trying direct fetch:', firstErr.message);
        // Fallback: plain fetch bypassing the entire request() machinery
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), 90_000);
        try {
            const res = await fetch(`${API_BASE}/screener/strategies`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
                body: JSON.stringify(strategy),
                signal: controller.signal,
            });
            clearTimeout(tid);
            const data = await res.json();
            if (!res.ok) throw new ApiError(data?.error || `Save failed (${res.status})`, res.status);
            return data;
        } catch (fallbackErr) {
            clearTimeout(tid);
            throw fallbackErr instanceof ApiError ? fallbackErr : new ApiError(fallbackErr.message || 'Failed to save strategy', 0);
        }
    }
}

export async function validateStrategy(strategy) {
    return post('/screener/strategies/validate', strategy, { timeout: 15_000, retries: 0 });
}

export async function deleteCustomStrategy(strategyName) {
    return del(`/screener/strategies/${encodeURIComponent(strategyName)}`, null, { timeout: 15_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  BACKTESTING
// ═══════════════════════════════════════════════════════════════════════════

export async function runBacktest(strategy, params = {}) {
    return post(`/backtest/${strategy}`, params, { timeout: 180_000, retries: 0 });
}

export async function compareStrategies(strategies, params = {}) {
    return post('/backtest/compare', { strategies, ...params }, { timeout: 300_000, retries: 0 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  WATCHLIST
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchWatchlist() {
    const data = await get('/watchlist', { cacheTtl: 10_000 });
    return data?.watchlist || data || [];
}

export async function addToWatchlist(ticker) {
    const data = await post('/watchlist', { ticker });
    return data?.watchlist || data || [];
}

export async function removeFromWatchlist(ticker) {
    const data = await del('/watchlist', { ticker });
    return data?.watchlist || data || [];
}

// ═══════════════════════════════════════════════════════════════════════════
//  PORTFOLIO
// ═══════════════════════════════════════════════════════════════════════════

export async function getPortfolio() {
    return get('/portfolio', { cacheTtl: 10_000 });
}

export async function addTransaction(transaction) {
    return post('/portfolio/transaction', transaction);
}

export async function deleteTransaction(transactionId) {
    return del(`/portfolio/transaction/${transactionId}`);
}

export async function getPortfolioNews() {
    return get('/news/portfolio', { cacheTtl: 60_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  PRICE TARGETS
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchPriceTarget(ticker, capital = 100000, riskPct = 2) {
    return get(`/price-target/${encodeURIComponent(ticker)}?capital=${capital}&risk_pct=${riskPct}`, { cacheTtl: 20_000, timeout: 15_000, retries: 1 });
}

export async function fetchBatchPriceTargets(tickers, capital = 100000, riskPct = 2) {
    return post('/price-targets/batch', { tickers, capital, risk_pct: riskPct }, { timeout: 120_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  CONFIG / SETTINGS
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchConfig() {
    return get('/config/screener', { cacheTtl: 0 });
}

export async function updateConfig(config) {
    return post('/config/screener', config);
}

export async function clearCache() {
    clearApiCache();                    // clear client-side cache too
    return post('/cache/clear', {});
}

// ═══════════════════════════════════════════════════════════════════════════
//  NEWS / SENTIMENT
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchNews(ticker) {
    return get(`/news/stock/${encodeURIComponent(ticker)}`, { cacheTtl: 120_000 });
}

export async function fetchSentiment(ticker) {
    return get(`/sentiment/${encodeURIComponent(ticker)}`, { cacheTtl: 120_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  FUNDAMENTALS (Patent-Pending Module)
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchFundamentals(ticker, exchange = 'NSE') {
    return get(`/fundamentals/${encodeURIComponent(ticker)}?exchange=${encodeURIComponent(exchange)}`, { cacheTtl: 300_000, timeout: 30_000 });
}

export async function fetchPiotroskiScore(ticker, exchange = 'NSE') {
    return get(`/fundamentals/${encodeURIComponent(ticker)}/piotroski?exchange=${encodeURIComponent(exchange)}`, { cacheTtl: 300_000, timeout: 30_000 });
}

export async function compareFundamentals(symbols, exchange = 'NSE') {
    return post('/fundamentals/compare', { symbols, exchange }, { timeout: 60_000 });
}

export async function fetchFinancialStatements(ticker, exchange = 'NSE') {
    return get(`/fundamentals/${encodeURIComponent(ticker)}/statements?exchange=${encodeURIComponent(exchange)}`, { cacheTtl: 300_000, timeout: 30_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  RISK ANALYTICS (Patent-Pending Module)
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchRiskMetrics(ticker, period = '2y') {
    return get(`/risk/${encodeURIComponent(ticker)}?period=${encodeURIComponent(period)}`, { cacheTtl: 300_000, timeout: 45_000 });
}

export async function analyzePortfolioRisk(holdings, period = '1y') {
    return post('/risk/portfolio', { holdings, period }, { timeout: 60_000 });
}

export async function fetchEfficientFrontier(symbols, period = '1y', nPortfolios = 5000) {
    return post('/risk/efficient-frontier', { symbols, period, n_portfolios: nPortfolios }, { timeout: 90_000 });
}

export async function compareStockRisk(symbols, period = '1y') {
    return post('/risk/compare', { symbols, period }, { timeout: 60_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  ADVANCED STRATEGY ENGINE (Patent-Pending Module)
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchStrategyCatalog() {
    return get('/strategies/catalog', { cacheTtl: 300_000 });
}

export async function evaluateStrategies(ticker, strategies = null, period = '1y') {
    return post(`/strategies/evaluate/${encodeURIComponent(ticker)}`, { strategies, period }, { timeout: 60_000 });
}

export async function multiStrategyScreen(ticker, minPassing = 2, minConfidence = 60, period = '1y') {
    return post(`/strategies/multi-screen/${encodeURIComponent(ticker)}`, {
        min_strategies_passing: minPassing,
        min_confidence: minConfidence,
        period
    }, { timeout: 60_000 });
}

export async function fetchSectorRotation(exchange = 'NSE') {
    return get(`/strategies/sector-rotation?exchange=${exchange}`, { cacheTtl: 300_000, timeout: 45_000 });
}

// ═══════════════════════════════════════════════════════════════════════════
//  EXPORT / REPORTS
// ═══════════════════════════════════════════════════════════════════════════

export async function fetchStockReport(ticker, format = 'html') {
    return get(`/export/report/${encodeURIComponent(ticker)}?format=${encodeURIComponent(format)}`, { timeout: 120_000, cacheTtl: 0 });
}
