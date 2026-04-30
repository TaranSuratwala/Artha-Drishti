import React, { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

/**
 * Toast notification component with auto-dismiss
 */
export const Toast = ({ message, type = 'info', onClose, duration = 3000 }) => {
    useEffect(() => {
        if (typeof onClose !== 'function') return undefined;
        const timer = setTimeout(onClose, duration);
        return () => clearTimeout(timer);
    }, [onClose, duration]);

    const typeConfig = {
        info: {
            bg: 'toast-info',
            icon: Info,
            border: 'border-blue-400/40'
        },
        success: {
            bg: 'toast-success',
            icon: CheckCircle,
            border: 'border-green-400/40'
        },
        error: {
            bg: 'toast-error',
            icon: AlertCircle,
            border: 'border-red-400/40'
        },
        warning: {
            bg: 'toast-warning',
            icon: AlertTriangle,
            border: 'border-yellow-400/40'
        },
    };

    const config = typeConfig[type] || typeConfig.info;
    const IconComponent = config.icon;

    return (
        <div
            className={`toast-shell fixed bottom-4 right-4 ${config.bg} text-white px-4 py-3 rounded-xl shadow-2xl
        flex items-center gap-3 animate-fade-in z-50 border ${config.border} backdrop-blur-sm`}
        >
            <IconComponent className="w-5 h-5 flex-shrink-0" />
            <span className="font-medium">{message}</span>
            <button
                type="button"
                onClick={onClose}
                className="hover:bg-white/20 rounded p-1 transition-colors ml-2"
                aria-label="Close notification"
            >
                <X className="w-4 h-4" />
            </button>
        </div>
    );
};

export default Toast;
