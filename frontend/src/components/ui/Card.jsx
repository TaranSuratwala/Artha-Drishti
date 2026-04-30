import React from 'react';

/**
 * Shared surface card with consistent spacing and optional accents.
 */
export const Card = ({ children, className = '', gradient = false, hover = false, ...rest }) => {
    const baseClasses = 'ui-card rounded-2xl border shadow-xl';
    const bgClasses = gradient
        ? 'ui-card-gradient'
        : 'ui-card-plain';
    const hoverClasses = hover ? 'ui-card-hover transition-all' : '';
    // If no explicit padding class is passed, apply default p-5
    const hasPadding = /\b(?:p|px|py|pt|pr|pb|pl)-\d+\b/.test(className);
    const controlsOwnLayout = /\boverflow-hidden\b/.test(className);
    const paddingClass = hasPadding || controlsOwnLayout ? '' : 'p-5';

    return (
        <div className={`${baseClasses} ${bgClasses} ${hoverClasses} ${paddingClass} ${className}`} {...rest}>
            {children}
        </div>
    );
};

export default Card;
