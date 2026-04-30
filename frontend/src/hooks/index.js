/**
 * Custom React hooks for the GenAI Stock Intelligence app.
 * 
 * These hooks encapsulate common patterns:
 *  • useDebounce       – delay a rapidly-changing value
 *  • useLocalStorage   – persistent state in localStorage
 *  • useApi            – data-fetching with loading/error/refresh
 *  • useAbortController – auto-cancelled fetch on unmount
 *  • useKeyboardShortcut – global hotkey bindings
 *  • useOnlineStatus   – network connectivity detection
 */

import { useState, useEffect, useRef, useCallback } from 'react';

// ═══════════════════════════════════════════════════════════════════════
//  useDebounce
// ═══════════════════════════════════════════════════════════════════════

export function useDebounce(value, delayMs = 300) {
    const [debounced, setDebounced] = useState(value);

    useEffect(() => {
        const id = setTimeout(() => setDebounced(value), delayMs);
        return () => clearTimeout(id);
    }, [value, delayMs]);

    return debounced;
}

// ═══════════════════════════════════════════════════════════════════════
//  useLocalStorage
// ═══════════════════════════════════════════════════════════════════════

export function useLocalStorage(key, defaultValue) {
    const [value, setValue] = useState(() => {
        try {
            const stored = localStorage.getItem(key);
            return stored !== null ? JSON.parse(stored) : defaultValue;
        } catch {
            return defaultValue;
        }
    });

    useEffect(() => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch { /* quota exceeded – silent */ }
    }, [key, value]);

    return [value, setValue];
}

// ═══════════════════════════════════════════════════════════════════════
//  useApi – generic data-fetching hook
// ═══════════════════════════════════════════════════════════════════════

export function useApi(apiFn, {
    immediate = true,
    args = [],
    onSuccess = null,
    onError = null,
} = {}) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(immediate);
    const [error, setError] = useState(null);
    const mountedRef = useRef(true);

    useEffect(() => {
        mountedRef.current = true;
        return () => { mountedRef.current = false; };
    }, []);

    const execute = useCallback(async (...callArgs) => {
        setLoading(true);
        setError(null);
        try {
            const result = await apiFn(...(callArgs.length ? callArgs : args));
            if (mountedRef.current) {
                setData(result);
                onSuccess?.(result);
            }
            return result;
        } catch (err) {
            if (mountedRef.current) {
                setError(err);
                onError?.(err);
            }
            throw err;
        } finally {
            if (mountedRef.current) setLoading(false);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [apiFn, ...args]);

    // Fire on mount if immediate
    useEffect(() => {
        if (immediate) execute().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [immediate]);

    return { data, loading, error, execute, setData };
}

// ═══════════════════════════════════════════════════════════════════════
//  useAbortController – auto-cancel on unmount
// ═══════════════════════════════════════════════════════════════════════

export function useAbortController() {
    const controllerRef = useRef(null);

    const getSignal = useCallback(() => {
        // Abort previous
        controllerRef.current?.abort();
        controllerRef.current = new AbortController();
        return controllerRef.current.signal;
    }, []);

    useEffect(() => {
        return () => controllerRef.current?.abort();
    }, []);

    return getSignal;
}

// ═══════════════════════════════════════════════════════════════════════
//  useKeyboardShortcut
// ═══════════════════════════════════════════════════════════════════════

export function useKeyboardShortcut(key, callback, { ctrl = false, shift = false, alt = false } = {}) {
    useEffect(() => {
        const handler = (e) => {
            if (
                e.key.toLowerCase() === key.toLowerCase() &&
                e.ctrlKey === ctrl &&
                e.shiftKey === shift &&
                e.altKey === alt
            ) {
                e.preventDefault();
                callback(e);
            }
        };

        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [key, callback, ctrl, shift, alt]);
}

// ═══════════════════════════════════════════════════════════════════════
//  useOnlineStatus
// ═══════════════════════════════════════════════════════════════════════

export function useOnlineStatus() {
    const [online, setOnline] = useState(navigator.onLine);

    useEffect(() => {
        const handleOnline = () => setOnline(true);
        const handleOffline = () => setOnline(false);
        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);
        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    return online;
}

// ═══════════════════════════════════════════════════════════════════════
//  useDocumentTitle
// ═══════════════════════════════════════════════════════════════════════

export function useDocumentTitle(title) {
    useEffect(() => {
        const prev = document.title;
        document.title = title ? `${title} | GenAI Stock Intel` : 'GenAI Stock Intelligence';
        return () => { document.title = prev; };
    }, [title]);
}

// ═══════════════════════════════════════════════════════════════════════
//  useMediaQuery
// ═══════════════════════════════════════════════════════════════════════

export function useMediaQuery(query) {
    const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

    useEffect(() => {
        const mql = window.matchMedia(query);
        const handler = (e) => setMatches(e.matches);
        mql.addEventListener('change', handler);
        return () => mql.removeEventListener('change', handler);
    }, [query]);

    return matches;
}
