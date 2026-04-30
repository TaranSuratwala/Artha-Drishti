import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './ui';

/**
 * ErrorBoundary - Catches React errors and displays fallback UI
 */
export class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        this.setState({ errorInfo });
        console.error('ErrorBoundary caught error:', error, errorInfo);
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
        window.location.reload();
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-pattern flex items-center justify-center p-4">
                    <div className="bg-white/5 backdrop-blur-xl rounded-3xl border border-red-500/30 p-8 max-w-lg w-full text-center shadow-xl">
                        <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <AlertTriangle className="w-8 h-8 text-red-400" />
                        </div>
                        <h2 className="text-2xl font-black text-white mb-2">Oops! Something went wrong</h2>
                        <p className="text-gray-400 mb-6">
                            We encountered an unexpected error. Don&apos;t worry, your data is safe.
                        </p>

                        {this.state.error && (
                            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6 text-left">
                                <p className="text-sm font-mono text-red-300 break-all">
                                    {this.state.error.toString()}
                                </p>
                            </div>
                        )}

                        <Button onClick={this.handleRetry} variant="primary" size="lg" className="w-full">
                            <RefreshCw className="w-5 h-5" />
                            Reload Application
                        </Button>

                        <p className="text-xs text-gray-500 mt-4">
                            If this problem persists, please contact support.
                        </p>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
