import React from 'react';

/**
 * SkeletonLoader - Animated loading placeholder
 * Variants: text, card, table, chart
 */
export const SkeletonLoader = ({ variant = 'text', lines = 1, className = '', type, rows }) => {
    const resolvedVariant = type || variant;
    const resolvedLines = rows ?? lines;
    const baseClass = 'skeleton animate-pulse bg-gradient-to-r from-white/5 via-white/10 to-white/5 rounded';
    const chartBarHeights = [34, 42, 58, 64, 52, 48, 71, 56, 62, 44, 68, 54];

    if (resolvedVariant === 'text') {
        return (
            <div className={`space-y-2 ${className}`}>
                {Array.from({ length: resolvedLines }).map((_, i) => (
                    <div
                        key={i}
                        className={`${baseClass} h-4 ${i === resolvedLines - 1 && resolvedLines > 1 ? 'w-3/4' : 'w-full'}`}
                    />
                ))}
            </div>
        );
    }

    if (resolvedVariant === 'card') {
        return (
            <div className={`${baseClass} p-6 space-y-4 ${className}`}>
                <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-xl bg-white/10" />
                    <div className="flex-1 space-y-2">
                        <div className="h-4 w-1/3 bg-white/10 rounded" />
                        <div className="h-3 w-2/3 bg-white/10 rounded" />
                    </div>
                </div>
                <div className="space-y-2">
                    <div className="h-3 w-full bg-white/10 rounded" />
                    <div className="h-3 w-5/6 bg-white/10 rounded" />
                </div>
            </div>
        );
    }

    if (resolvedVariant === 'table') {
        return (
            <div className={`space-y-3 ${className}`}>
                {/* Header */}
                <div className="flex gap-4">
                    {Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className={`${baseClass} h-8 flex-1`} />
                    ))}
                </div>
                {/* Rows */}
                {Array.from({ length: resolvedLines }).map((_, i) => (
                    <div key={i} className="flex gap-4">
                        {Array.from({ length: 5 }).map((_, j) => (
                            <div key={j} className={`${baseClass} h-10 flex-1`} />
                        ))}
                    </div>
                ))}
            </div>
        );
    }

    if (resolvedVariant === 'chart') {
        return (
            <div className={`${baseClass} h-64 relative overflow-hidden ${className}`}>
                <div className="absolute inset-0 flex items-end justify-around p-4">
                    {chartBarHeights.map((height, i) => (
                        <div
                            key={i}
                            className="w-4 bg-white/10 rounded-t"
                            style={{ height: `${height}%` }}
                        />
                    ))}
                </div>
            </div>
        );
    }

    if (resolvedVariant === 'stats') {
        return (
            <div className={`grid grid-cols-2 md:grid-cols-4 gap-4 ${className}`}>
                {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className={`${baseClass} p-4`}>
                        <div className="h-3 w-1/2 bg-white/10 rounded mb-2" />
                        <div className="h-6 w-3/4 bg-white/10 rounded" />
                    </div>
                ))}
            </div>
        );
    }

    return <div className={`${baseClass} h-4 w-full ${className}`} />;
};

export default SkeletonLoader;
