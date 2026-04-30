import React from 'react';

/**
 * Animated loading spinner with glow effect
 */
export const LoadingSpinner = ({ text = 'Loading...', size = 'md' }) => {
    const sizeClasses = {
        sm: 'w-6 h-6 border-2',
        md: 'w-10 h-10 border-3',
        lg: 'w-14 h-14 border-4',
    };

    return (
        <div className="text-center py-8">
            <div className="inline-flex relative items-center justify-center">
                <div className="absolute inset-0 spinner-halo" />
                <div
                    className={`relative rounded-full animate-spin spinner-ring ${sizeClasses[size]}`}
                />
            </div>
            {text && <p className="mt-3 spinner-label">{text}</p>}
        </div>
    );
};

export default LoadingSpinner;
