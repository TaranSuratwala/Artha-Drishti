import React, { useState, useEffect } from 'react';
import { useAuth } from './context/AuthContext';
import { LoadingSpinner, ThemeToggle } from './components/ui';
import { LoginPage } from './components/auth/LoginPage';
import { SignupPage } from './components/auth/SignupPage';
import AuthenticatedApp from './AuthenticatedApp';

function App() {
    // Core state
    const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

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
            <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
                <LoadingSpinner text="Initializing secure session..." />
            </div>
        );
    }

    if (!isAuthenticated) {
        return (
            <div className="font-sans text-gray-100 bg-gray-900 min-h-screen transition-colors duration-300">
                <div className="absolute top-4 right-4 z-50">
                    <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
                </div>
                {isSignup ? <SignupPage onSwitchToLogin={() => window.location.hash = '#login'} /> : <LoginPage />}
            </div>
        );
    }

    // Once authenticated, render the main app
    return <AuthenticatedApp theme={theme} toggleTheme={toggleTheme} />;
}

export default App;
