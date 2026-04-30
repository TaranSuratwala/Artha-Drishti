import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import Card from './Card';

/**
 * Statistics display card with icon and optional change indicator
 */
export const StatCard = ({
    icon: Icon,
    label,
    value,
    change,
    color = 'blue',
    className = ''
}) => {
    const colorClasses = {
        blue: { bg: 'stat-chip stat-chip-blue', text: 'text-blue-400' },
        green: { bg: 'stat-chip stat-chip-green', text: 'text-green-400' },
        red: { bg: 'stat-chip stat-chip-red', text: 'text-red-400' },
        yellow: { bg: 'stat-chip stat-chip-yellow', text: 'text-yellow-400' },
        purple: { bg: 'stat-chip stat-chip-purple', text: 'text-purple-400' },
        emerald: { bg: 'stat-chip stat-chip-emerald', text: 'text-emerald-400' },
    };

    const colors = colorClasses[color] || colorClasses.blue;

    return (
        <Card className={`p-6 stat-card ${className}`} hover>
            <div className="flex items-center gap-4">
                <div className={`p-3.5 rounded-xl ${colors.bg}`}>
                    <Icon className={`w-5 h-5 ${colors.text}`} />
                </div>
                <div className="flex-1 min-w-0">
                    <p className="text-xs text-gray-400 mb-1.5 truncate font-medium uppercase tracking-wider">{label}</p>
                    <p className="text-2xl font-black text-white truncate">{value}</p>
                    {change !== undefined && (
                        <p className={`text-xs font-bold flex items-center gap-0.5 mt-0.5 ${change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {change >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                            {Math.abs(change).toFixed(2)}%
                        </p>
                    )}
                </div>
            </div>
        </Card>
    );
};

export default StatCard;
