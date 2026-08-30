// Currency symbol lookup, formatting, and COP conversion helpers.
export const CURRENCY_SYMBOLS: Record<string, string> = {
    COP: '$',
    USD: '$',
    EUR: '€',
    GBP: '£',
    JPY: '¥',
    INR: '₹',
    BRL: 'R$',
    CAD: '$',
    AUD: '$',
    CHF: 'Fr ',
    CNY: '¥',
    KRW: '₩',
    MXN: '$',
    SEK: 'kr ',
};

export const BASE_CURRENCY = 'COP';

// NEW: Convert amount using daily snapshot rates map
export const convertFromSnapshot = (
    amount: number | undefined | null,
    fromCurrency: string,
    rates: Record<string, number>,
    toCurrency: string = 'USD'
): number => {
    if (amount == null || amount === undefined) return 0;
    if (fromCurrency === toCurrency) return amount;
    if (fromCurrency === BASE_CURRENCY) {
        // Converting from COP to target
        const rate = rates[toCurrency];
        if (!rate || rate <= 0) return amount;
        return amount / rate;
    }
    if (toCurrency === BASE_CURRENCY) {
        // Converting from source to COP
        const rate = rates[fromCurrency];
        if (!rate || rate <= 0) return amount;
        return amount * rate;
    }
    // Convert via COP as intermediate
    const fromRate = rates[fromCurrency] || 1;
    const toRate = rates[toCurrency] || 1;
    // amount * (fromRate / toRate) gives us conversion from fromCurrency to toCurrency
    return (amount * fromRate) / toRate;
};

export const fmtMoney = (v: number | undefined | null, currency: string) => {
    const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;
    return `${symbol}${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};

export const fmtMoneyCompact = (v: number | undefined | null, currency: string): string => {
    const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;
    const abs = Math.abs(v ?? 0);
    if (abs >= 1_000_000) return `${symbol}${((v ?? 0) / 1_000_000).toFixed(1)}M`;
    if (abs >= 1_000) return `${symbol}${((v ?? 0) / 1_000).toFixed(1)}k`;
    return `${symbol}${Math.round(v ?? 0)}`;
};

/**
 * Convert an amount from `currency` to the base currency (COP)
 * using the provided exchange-rate map.
 * rate_to_cop means: 1 unit of `currency` = rate_to_cop COP.
 */
export const convertToBase = (
    amount: number,
    currency: string,
    rates: Record<string, number>,
): number => {
    if (!currency || currency === BASE_CURRENCY) return amount;
    const rate = rates[currency];
    if (!rate || rate <= 0) return amount;
    return amount * rate;
};

/**
 * Convert an amount from COP back to `currency`.
 */
export const convertFromBase = (
    copAmount: number,
    currency: string,
    rates: Record<string, number>,
): number => {
    if (!currency || currency === BASE_CURRENCY) return copAmount;
    const rate = rates[currency];
    if (!rate || rate <= 0) return copAmount;
    return copAmount / rate;
};
