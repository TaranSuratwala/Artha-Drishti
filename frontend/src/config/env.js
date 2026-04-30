/**
 * Environment configuration for GenAI Stock Intelligence
 * 
 * In development: reads from import.meta.env (Vite .env files)
 * In production: reads from window.__ENV__ or import.meta.env
 */

const env = {
    // Google OAuth Client ID – set VITE_GOOGLE_CLIENT_ID in .env
    GOOGLE_CLIENT_ID: import.meta.env.VITE_GOOGLE_CLIENT_ID || '',

    // API base URL (empty = same origin, useful for production)
    API_BASE_URL: import.meta.env.VITE_API_BASE_URL || '',

    // Feature flags
    ENABLE_GOOGLE_AUTH: !!import.meta.env.VITE_GOOGLE_CLIENT_ID,

    // App meta
    APP_NAME: 'GenAI Stock Intelligence',
    APP_VERSION: '2.0.0',

    // Is production build?
    IS_PROD: import.meta.env.PROD,
};

export default env;
