/**
 * Currency utilities for Indian Rupee formatting
 */

/**
 * Format a number as Indian Rupees (₹)
 * @param {number} amount - The amount to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted currency string
 */
export const formatINR = (amount, decimals = 2) => {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return '₹0.00';
    }

    // Use Indian locale for proper lakhs/crores formatting
    return `₹${Number(amount).toLocaleString('en-IN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    })}`;
};

/**
 * Format a number with plus/minus sign and INR
 * @param {number} amount - The amount to format
 * @returns {string} Formatted currency with sign
 */
export const formatINRWithSign = (amount, decimals = 2) => {
    if (amount === null || amount === undefined || isNaN(amount)) {
        return '₹0.00';
    }

    const sign = amount >= 0 ? '+' : '';
    return `${sign}${formatINR(amount, decimals)}`;
};

/**
 * Format percentage
 * @param {number} value - Percentage value
 * @param {number} decimals - Decimal places
 * @returns {string} Formatted percentage
 */
export const formatPercent = (value, decimals = 2) => {
    if (value === null || value === undefined || isNaN(value)) {
        return '0%';
    }
    const sign = value >= 0 ? '+' : '';
    return `${sign}${Number(value).toFixed(decimals)}%`;
};

export default { formatINR, formatINRWithSign, formatPercent };
