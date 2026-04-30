import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd(), '')

    return {
        plugins: [react()],

        // Path aliases for cleaner imports
        resolve: {
            alias: {
                '@': path.resolve(__dirname, './src'),
                '@components': path.resolve(__dirname, './src/components'),
                '@hooks': path.resolve(__dirname, './src/hooks'),
                '@services': path.resolve(__dirname, './src/services'),
                '@utils': path.resolve(__dirname, './src/utils'),
                '@config': path.resolve(__dirname, './src/config'),
                '@context': path.resolve(__dirname, './src/context'),
            }
        },

        server: {
            port: 5173,
            proxy: {
                '/api': {
                    target: env.VITE_API_BASE_URL || 'http://localhost:5000',
                    changeOrigin: true,
                    proxyTimeout: 300000,
                    timeout: 300000,
                    // Retry on backend restart
                    configure: (proxy) => {
                        proxy.on('error', (err, _req, _res) => {
                            console.warn('[proxy error]', err.message);
                        });
                    },
                },
            },
        },

        // Production build optimizations
        build: {
            outDir: 'dist',
            sourcemap: mode === 'development',
            minify: 'terser',
            target: 'es2020',
            cssMinify: true,
            terserOptions: {
                compress: {
                    drop_console: mode === 'production',
                    drop_debugger: true,
                    pure_funcs: mode === 'production' ? ['console.log', 'console.debug'] : [],
                },
            },
            rollupOptions: {
                output: {
                    manualChunks: {
                        vendor: ['react', 'react-dom'],
                        icons: ['lucide-react'],
                        auth: ['@react-oauth/google'],
                    },
                    // Cache-busting file names
                    assetFileNames: 'assets/[name]-[hash][extname]',
                    chunkFileNames: 'chunks/[name]-[hash].js',
                    entryFileNames: 'js/[name]-[hash].js',
                },
            },
            // Warn when chunks exceed 500KB
            chunkSizeWarningLimit: 500,
        },

        // Preview server (for testing production builds)
        preview: {
            port: 4173,
            proxy: {
                '/api': {
                    target: env.VITE_API_BASE_URL || 'http://localhost:5000',
                    changeOrigin: true,
                },
            },
        },
    }
})
