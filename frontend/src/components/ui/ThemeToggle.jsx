import React from 'react';
import { Sun, Moon } from 'lucide-react';

export const ThemeToggle = ({ theme, toggleTheme }) => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';

    return (
        <button
            type="button"
            onClick={toggleTheme}
            className="theme-toggle-btn p-2 rounded-xl transition-all border text-gray-400 hover:text-white"
            title={`Switch to ${nextTheme} mode`}
            aria-label={`Switch to ${nextTheme} mode`}
            style={{ borderColor: 'var(--border-color)' }}
        >
            {theme === 'dark' ? (
                <Sun className="w-5 h-5 text-amber-300" />
            ) : (
                <Moon className="w-5 h-5 text-slate-700" />
            )}
        </button>
    );
};
