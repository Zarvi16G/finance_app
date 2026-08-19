// Currency symbol lookup and ledger-style money formatting.
export const CURRENCY_SYMBOLS: Record<string, string> = {
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

export const fmtMoney = (v: number | undefined | null, currency: string) => {
  const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;
  return `${symbol}${(v ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
};
