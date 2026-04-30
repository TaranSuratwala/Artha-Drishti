import React from 'react'
import ReactDOM from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import App from './App.jsx'
import { ErrorBoundary } from './components/ErrorBoundary.jsx'
import './styles/index.css'

import { AuthProvider } from './context/AuthContext';
import env from './config/env';

function Root() {
    const inner = (
        <React.StrictMode>
            <ErrorBoundary>
                <AuthProvider>
                    <App />
                </AuthProvider>
            </ErrorBoundary>
        </React.StrictMode>
    );

    // Wrap with Google OAuth provider only when client ID is configured
    if (env.GOOGLE_CLIENT_ID) {
        return (
            <GoogleOAuthProvider clientId={env.GOOGLE_CLIENT_ID}>
                {inner}
            </GoogleOAuthProvider>
        );
    }

    return inner;
}

ReactDOM.createRoot(document.getElementById('root')).render(<Root />);
