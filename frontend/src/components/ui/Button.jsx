import React from 'react';

/**
 * Styled Button component with multiple variants
 */
export const Button = ({
    children,
    onClick,
    disabled = false,
    variant = 'primary',
    size = 'md',
    className = '',
    type = 'button',
    ...rest
}) => {
    const baseClasses = 'btn font-bold rounded-xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2.5';

    const sizeClasses = {
        sm: 'px-3.5 py-2 text-xs min-h-[34px]',
        md: 'px-5 py-2.5 text-sm min-h-[40px]',
        lg: 'px-7 py-3.5 text-base min-h-[46px]',
    };

    const variantClasses = {
        primary: 'btn-primary text-white',
        secondary: 'btn-secondary text-white border border-white/20',
        success: 'btn-success text-white',
        danger: 'btn-danger text-white',
        warning: 'btn-warning text-white',
        purple: 'btn-purple text-white',
        ghost: 'btn-ghost text-white',
    };

    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            className={`${baseClasses} ${sizeClasses[size] || sizeClasses.md} ${variantClasses[variant] || variantClasses.primary} ${className}`}
            {...rest}
        >
            {children}
        </button>
    );
};

export default Button;
