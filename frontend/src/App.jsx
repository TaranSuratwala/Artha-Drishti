import React, { useState, useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import { LoadingSpinner, ThemeToggle } from './components/ui';
import { LoginPage } from './components/auth/LoginPage';
import { SignupPage } from './components/auth/SignupPage';
import AuthenticatedApp from './AuthenticatedApp';
import { Brain } from 'lucide-react';

function App() {
    // Core state
    const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');

    // Theme Effect
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');

    // --- AUTHENTICATION CHECK ---
    const { isAuthenticated, loading: authLoading } = useAuth();
    const [isSignup, setIsSignup] = useState(window.location.hash === '#signup');

    useEffect(() => {
        const handleHash = () => setIsSignup(window.location.hash === '#signup');
        window.addEventListener('hashchange', handleHash);
        return () => window.removeEventListener('hashchange', handleHash);
    }, []);

    if (authLoading) {
        return (
            <div className="app-boot-screen">
                <div className="app-boot-panel">
                    <div className="app-boot-logo">
                        <Brain className="w-7 h-7" />
                    </div>
                    <h1>Preparing Workspace</h1>
                    <p>Securing account session and syncing real-time market services...</p>
                    <LoadingSpinner text="Starting Artha Drishti" size="sm" />
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return (
            <div className="auth-shell-root auth-shell-root-compact">
                <div className="auth-shell-bg" aria-hidden="true" />

                <header className="auth-shell-header">
                    <div className="auth-shell-brand">
                        <span className="auth-shell-brand-icon"><Brain className="w-5 h-5" /></span>
                        <div>
                            <h1>Artha Drishti</h1>
                            <p>Sign in or create your account</p>
                        </div>
                    </div>
                    <div className="auth-shell-actions">
                        <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                    </div>
                </header>

                <main className="auth-shell-main auth-shell-main-compact">
                    <section className="auth-shell-form auth-shell-form-focus">
                        <div className="auth-entry-switch" role="tablist" aria-label="Authentication options">
                            <button
                                type="button"
                                role="tab"
                                aria-selected={!isSignup}
                                className={`auth-entry-btn ${!isSignup ? 'active' : ''}`}
                                onClick={() => { window.location.hash = '#login'; }}
                            >
                                Login
                            </button>
                            <button
                                type="button"
                                role="tab"
                                aria-selected={isSignup}
                                className={`auth-entry-btn ${isSignup ? 'active' : ''}`}
                                onClick={() => { window.location.hash = '#signup'; }}
                            >
                                Create account
                            </button>
                        </div>
                        <p className="auth-entry-caption">
                            {isSignup ? 'Create a new account to continue.' : 'Login to continue.'}
                        </p>

                        {isSignup ? (
                            <SignupPage onSwitchToLogin={() => { window.location.hash = '#login'; }} />
                        ) : (
                            <LoginPage />
                        )}
                    </section>
                </main>

            </div>
        );
    }

    // Once authenticated, render the main app
    return <AuthenticatedApp theme={theme} toggleTheme={toggleTheme} />;
}

export default App;
