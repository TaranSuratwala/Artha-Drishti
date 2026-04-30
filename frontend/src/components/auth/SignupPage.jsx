import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Button, LoadingSpinner } from '../ui';
import { Mail, User, Lock, AlertCircle, CheckCircle, Eye, EyeOff, ArrowRight } from 'lucide-react';
import env from '../../config/env';

export const SignupPage = ({ onSwitchToLogin }) => {
    const { signup, googleLogin } = useAuth();
    const canUseGoogleAuth = Boolean(env.ENABLE_GOOGLE_AUTH && env.GOOGLE_CLIENT_ID);
    const [formData, setFormData] = useState({ username: '', email: '', password: '' });
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [loading, setLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);

    useEffect(() => {
        document.title = 'Create Account | Artha Drishti';
    }, []);

    const passwordStrength = () => {
        const p = formData.password;
        if (p.length === 0) return null;
        if (p.length < 6) return { label: 'Too short', score: 25 };
        if (p.length < 8) return { label: 'Weak', score: 45 };
        if (/[A-Z]/.test(p) && /[0-9]/.test(p) && p.length >= 10) return { label: 'Strong', score: 100 };
        return { label: 'Medium', score: 72 };
    };

    const strength = passwordStrength();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (!formData.username.trim() || formData.username.length < 3) {
            setError('Username must be at least 3 characters.');
            return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
            setError('Enter a valid email address.');
            return;
        }
        if (formData.password.length < 6) {
            setError('Password must be at least 6 characters.');
            return;
        }

        setLoading(true);
        try {
            await signup(formData.username.trim(), formData.email.trim().toLowerCase(), formData.password);
            setSuccess(true);
            setTimeout(() => {
                if (onSwitchToLogin) onSwitchToLogin();
                else window.location.hash = '#login';
            }, 2000);
        } catch (err) {
            const msg = err.message || 'Registration failed';
            if (msg.toLowerCase().includes('exists')) {
                setError('Account already exists for this username or email.');
            } else {
                setError(msg);
            }
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleAuth = async () => {
        setError('');
        if (!canUseGoogleAuth) {
            setError('Google sign-up is not configured in the environment.');
            return;
        }

        setLoading(true);
        try {
            if (!window.google?.accounts?.id) {
                await new Promise((resolve, reject) => {
                    const existing = document.querySelector('script[src*="accounts.google.com/gsi/client"]');
                    if (existing) {
                        const interval = setInterval(() => {
                            if (window.google?.accounts?.id) {
                                clearInterval(interval);
                                resolve();
                            }
                        }, 100);
                        setTimeout(() => {
                            clearInterval(interval);
                            reject(new Error('timeout'));
                        }, 10000);
                        return;
                    }

                    const s = document.createElement('script');
                    s.src = 'https://accounts.google.com/gsi/client';
                    s.async = true;
                    s.onload = () => setTimeout(resolve, 300);
                    s.onerror = () => reject(new Error('network'));
                    document.head.appendChild(s);
                });
            }

            const clientId = env.GOOGLE_CLIENT_ID;
            if (!clientId) {
                setError('Google sign-up is not configured in the environment.');
                setLoading(false);
                return;
            }

            window.google.accounts.id.initialize({
                client_id: clientId,
                callback: async (response) => {
                    try {
                        await googleLogin(response.credential);
                    } catch (err) {
                        setError(err.message || 'Google sign-up failed.');
                        setLoading(false);
                    }
                },
            });

            window.google.accounts.id.prompt((notification) => {
                if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                    setError('Google popup was blocked or unavailable.');
                }
                setLoading(false);
            });
        } catch {
            setError('Google sign-up could not be initialized.');
            setLoading(false);
        }
    };

    if (success) {
        return (
            <section className="auth-panel auth-panel-success">
                <div className="auth-success-icon"><CheckCircle className="w-7 h-7" /></div>
                <h3>Account created</h3>
                <p>Your workspace is ready. Redirecting to login...</p>
                <div className="auth-success-progress">
                    <span className="auth-success-progress-bar" />
                </div>
            </section>
        );
    }

    return (
        <section className="auth-panel" aria-label="Signup panel">
            <div className="auth-panel-head">
                <h3>Create account</h3>
                <p>Start with a secure account and launch your live analytics workspace.</p>
            </div>

            {error && (
                <div className="auth-alert" role="alert">
                    <AlertCircle className="w-4 h-4" />
                    <span>{error}</span>
                </div>
            )}

            {canUseGoogleAuth && (
                <button type="button" disabled={loading} onClick={handleGoogleAuth} className="auth-google-btn auth-google-btn-top">
                    <svg viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg">
                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                    </svg>
                    <span>Sign up with Google</span>
                </button>
            )}

            {canUseGoogleAuth && <div className="auth-divider"><span>OR</span></div>}

            <form onSubmit={handleSubmit} className="auth-form" noValidate>
                <label className="auth-label" htmlFor="signup-username">Username</label>
                <div className="auth-input-wrap">
                    <User className="auth-input-icon" />
                    <input
                        id="signup-username"
                        type="text"
                        autoComplete="username"
                        minLength={3}
                        className="auth-input"
                        placeholder="Choose username"
                        value={formData.username}
                        onChange={(e) => {
                            setFormData({ ...formData, username: e.target.value });
                            setError('');
                        }}
                    />
                </div>

                <label className="auth-label" htmlFor="signup-email">Email</label>
                <div className="auth-input-wrap">
                    <Mail className="auth-input-icon" />
                    <input
                        id="signup-email"
                        type="email"
                        autoComplete="email"
                        className="auth-input"
                        placeholder="Enter email"
                        value={formData.email}
                        onChange={(e) => {
                            setFormData({ ...formData, email: e.target.value });
                            setError('');
                        }}
                    />
                </div>

                <label className="auth-label" htmlFor="signup-password">Password</label>
                <div className="auth-input-wrap">
                    <Lock className="auth-input-icon" />
                    <input
                        id="signup-password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        minLength={6}
                        className="auth-input auth-input-password"
                        placeholder="Create password"
                        value={formData.password}
                        onChange={(e) => {
                            setFormData({ ...formData, password: e.target.value });
                            setError('');
                        }}
                    />
                    <button
                        type="button"
                        className="auth-input-toggle"
                        onClick={() => setShowPassword((prev) => !prev)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                </div>

                {strength && (
                    <div className="auth-strength" aria-live="polite">
                        <div className="auth-strength-track">
                            <span className="auth-strength-fill" style={{ width: `${strength.score}%` }} />
                        </div>
                        <span>{strength.label}</span>
                    </div>
                )}

                <Button type="submit" disabled={loading} className="w-full auth-submit-btn" variant="primary">
                    {loading ? (
                        <>
                            <LoadingSpinner size="sm" text="" />
                            <span>Creating account...</span>
                        </>
                    ) : (
                        <>
                            <span>Create Account</span>
                            <ArrowRight className="w-4 h-4" />
                        </>
                    )}
                </Button>
            </form>

            <p className="auth-footnote">
                Already have an account?{' '}
                <button
                    type="button"
                    className="auth-link"
                    onClick={() => {
                        if (onSwitchToLogin) onSwitchToLogin();
                        else window.location.hash = '#login';
                    }}
                >
                    Sign in
                </button>
            </p>
        </section>
    );
};
