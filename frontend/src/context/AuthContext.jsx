import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { loginUser, signupUser, fetchCurrentUser, loginWithGoogle, clearApiCache, abortAllPending, resetLogoutGuard } from '../services/api';

// ─── Context ────────────────────────────────────────────────────────────────

const AuthContext = createContext(null);

// ─── Provider ───────────────────────────────────────────────────────────────

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const mountedRef = useRef(true);

    // Bootstrap: try to restore session from localStorage
    useEffect(() => {
        mountedRef.current = true;
        const token = localStorage.getItem('auth_token');
        if (token) {
            fetchCurrentUser()
                .then(userData => {
                    if (!mountedRef.current) return;

                    if (userData && userData.id) {
                        setUser(userData);
                        setIsAuthenticated(true);
                        return;
                    }

                    // No active session (204/null or missing profile)
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('auth_user');
                    setUser(null);
                    setIsAuthenticated(false);
                })
                .catch(() => {
                    // Token invalid/expired
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('auth_user');
                    if (mountedRef.current) {
                        setUser(null);
                        setIsAuthenticated(false);
                    }
                })
                .finally(() => {
                    if (mountedRef.current) setLoading(false);
                });
        } else {
            setLoading(false);
        }

        // Listen for forced-logout events from the API layer (401)
        const handleForceLogout = () => {
            abortAllPending();   // cancel in-flight requests so stale 401s can't race
            clearApiCache();     // purge stale session data
            setUser(null);
            setIsAuthenticated(false);
        };
        window.addEventListener('auth:logout', handleForceLogout);

        return () => {
            mountedRef.current = false;
            window.removeEventListener('auth:logout', handleForceLogout);
        };
    }, []);

    // ── Login ────────────────────────────────────────────────────────────
    const login = useCallback(async (username, password) => {
        const data = await loginUser(username, password);
        const token = data.access_token;
        const userData = data.user;

        // Reset API state for the new session
        resetLogoutGuard();
        clearApiCache();

        localStorage.setItem('auth_token', token);
        localStorage.setItem('auth_user', JSON.stringify(userData));

        setUser(userData);
        setIsAuthenticated(true);
        return userData;
    }, []);

    // ── Signup ───────────────────────────────────────────────────────────
    const signup = useCallback(async (username, email, password) => {
        const data = await signupUser(username, email, password);
        return data;
    }, []);

    // ── Google OAuth ─────────────────────────────────────────────────────
    const googleLogin = useCallback(async (credential) => {
        const data = await loginWithGoogle(credential);
        const token = data.access_token;
        const userData = data.user;

        resetLogoutGuard();
        clearApiCache();

        localStorage.setItem('auth_token', token);
        localStorage.setItem('auth_user', JSON.stringify(userData));

        setUser(userData);
        setIsAuthenticated(true);
        return userData;
    }, []);

    // ── Logout ───────────────────────────────────────────────────────────
    const logout = useCallback(() => {
        abortAllPending();
        clearApiCache();
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        setUser(null);
        setIsAuthenticated(false);
    }, []);

    const value = {
        user,
        loading,
        isAuthenticated,
        login,
        signup,
        googleLogin,
        logout,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

// ─── Hook ───────────────────────────────────────────────────────────────────

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
    return ctx;
}

export default AuthContext;
