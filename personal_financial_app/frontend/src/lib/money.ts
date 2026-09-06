/**
 * Money formatting, following the rules stated on the design's token sheet:
 *
 *   COP has no decimals · 159.000.000
 *   USD and EUR have two · 1.500,00
 *   Dot groups thousands, comma marks decimals
 *
 * That is the es-CO convention, so the locale is pinned rather than left to
 * the browser: the same figure must not read as 1,500.00 for one visitor and
 * 1.500,00 for another when both are looking at pesos.
 *
 * Decimals come from ISO 4217 and mirror `Currency.decimals` in the backend.
 * A currency we do not know about falls back to two, which is the common case.
 */
const LOCALE = 'es-CO';

/** Currencies whose minor unit is not 1/100. */
const DECIMALS: Record<string, number> = {
  COP: 0,
  CLP: 0,
  JPY: 0,
  KRW: 0,
  ISK: 0,
  VND: 0,
  PYG: 0,
};

const decimalsFor = (currency: string): number => DECIMALS[currency?.toUpperCase()] ?? 2;

const toNumber = (v: number | string | null | undefined): number => {
  if (v === null || v === undefined || v === '') return 0;
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : 0;
};

/**
 * The bare figure, no currency marker: `159.000.000`.
 * This is what goes in a column of amounts whose currency is stated once in
 * the column header — repeating it on every row is noise.
 */
export function fmtFigure(value: number | string | null | undefined, currency = 'COP'): string {
  const digits = decimalsFor(currency);
  return toNumber(value).toLocaleString(LOCALE, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** The figure with its ISO code after it: `159.000.000 COP`. */
export function fmtMoney(value: number | string | null | undefined, currency = 'COP'): string {
  const code = (currency || 'COP').toUpperCase();
  return `${fmtFigure(value, code)} ${code}`;
}

/**
 * A figure that always carries its sign, for net flows where the direction is
 * the point: `+3.000.000`, `−2.000.000`.
 *
 * The minus is U+2212, not a hyphen — at Newsreader's weight a hyphen sits
 * too high and too short to read as a minus next to a large figure.
 */
export function fmtSigned(value: number | string | null | undefined, currency = 'COP'): string {
  const n = toNumber(value);
  const body = fmtFigure(Math.abs(n), currency);
  if (n > 0) return `+${body}`;
  if (n < 0) return `−${body}`;
  return body;
}

/**
 * A plain quantity that is not money and must not be formatted as if it were:
 * months of cover, a count of items. `4,5` rather than `4,50` or `5`.
 */
export function fmtNumber(value: number | string | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—';
  return toNumber(value).toLocaleString(LOCALE, {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

/** A percentage with one decimal: `60,0 %`. */
export function fmtPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  return `${Number(value).toLocaleString(LOCALE, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })} %`;
}

/** A percentage that carries its sign: `+12,4 %`. */
export function fmtSignedPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—';
  const n = Number(value);
  const body = fmtPercent(Math.abs(n), digits);
  if (n > 0) return `+${body}`;
  if (n < 0) return `−${body}`;
  return body;
}

/** `2027-04` or an ISO date rendered as `abr 2027`. */
export function fmtMonth(month: string | null | undefined): string {
  if (!month) return '—';
  const [year, m] = month.split('-');
  const index = Number(m) - 1;
  if (!year || Number.isNaN(index)) return month;
  const label = new Date(Number(year), index, 1).toLocaleDateString(LOCALE, { month: 'short' });
  return `${label} ${year}`;
}

/** An ISO date rendered as `12 nov 2026`. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(`${iso.slice(0, 10)}T00:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(LOCALE, { day: 'numeric', month: 'short', year: 'numeric' });
}
