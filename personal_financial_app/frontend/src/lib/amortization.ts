// Amortization schedule math for the debt detail page.
// Projects the outstanding balance month by month from the current
// balance, using the standard fixed-payment amortization formula.

export interface AmortizationPoint {
  key: string; // 'YYYY-MM'
  label: string; // 'Aug 2026'
  balance: number; // outstanding balance at the end of the month
  paid: number; // cumulative principal paid (original - balance)
  actual: boolean; // true when backed by recorded data, false when projected
}

export interface AmortizationSchedule {
  points: AmortizationPoint[];
  payoffKey: string | null; // 'YYYY-MM' of the projected payoff month, null if it never pays off
  neverPaysOff: boolean;
  projectedInterest: number; // total interest paid over the projected lifetime
}

export interface AmortizationOptions {
  originalAmount: number;
  currentBalance: number;
  annualRatePct: number;
  minPayment: number;
  startDate: string; // ISO date, 'YYYY-MM-DD'
  status?: string;
  maxMonths?: number; // projection cap, default 240
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const pad = (n: number) => String(n).padStart(2, '0');

export const currentMonthKey = () => {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;
};

export const monthLabel = (key: string) => {
  const [y, m] = key.split('-');
  return `${MONTHS[Number(m) - 1]} ${y.slice(2)}`;
};

const point = (key: string, balance: number, paid: number, actual: boolean): AmortizationPoint => ({
  key,
  label: monthLabel(key),
  balance,
  paid,
  actual,
});

export function buildAmortizationSchedule(opts: AmortizationOptions): AmortizationSchedule {
  const {
    originalAmount,
    currentBalance,
    annualRatePct,
    minPayment,
    startDate,
    status,
    maxMonths = 240,
  } = opts;

  const original = Math.max(0, Number(originalAmount) || 0);
  const balance0 = Math.max(0, Number(currentBalance) || 0);
  const monthlyRate = (Number(annualRatePct) || 0) / 100 / 12;
  const payment = Math.max(0, Number(minPayment) || 0);
  const nowKey = currentMonthKey();
  const startKey = startDate.slice(0, 7);

  // Debt already settled (or registered as such): a flat zero line.
  if (status === 'paid_off' || balance0 <= 0) {
    return {
      points: [
        point(startKey, 0, original, true),
        point(nowKey, 0, original, true),
      ],
      payoffKey: startKey,
      neverPaysOff: false,
      projectedInterest: 0,
    };
  }

  const points: AmortizationPoint[] = [];

  // Historical segment: we know where it started and where it stands today.
  if (startKey === nowKey) {
    points.push(point(startKey, balance0, original - balance0, true));
  } else {
    points.push(point(startKey, original, 0, true));
    points.push(point(nowKey, balance0, original - balance0, true));
  }

  // Projection: fixed minimum payment each month until the balance clears.
  let balance = balance0;
  let projectedInterest = 0;
  let payoffKey: string | null = null;
  let neverPaysOff = false;
  let [projYear, projMonth] = nowKey.split('-').map(Number);

  for (let i = 0; i < maxMonths; i++) {
    projMonth += 1;
    if (projMonth > 12) {
      projMonth = 1;
      projYear += 1;
    }
    const key = `${projYear}-${pad(projMonth)}`;

    const interest = balance * monthlyRate;

    // At the minimum payment, interest eats the whole payment: the debt
    // never decreases. Show a short trajectory and flag it.
    if (payment <= interest) {
      neverPaysOff = true;
      if (i < 36) {
        projectedInterest += interest;
        points.push(point(key, balance, original - balance, false));
      }
      continue;
    }

    const thisPayment = Math.min(payment, balance + interest);
    const principal = thisPayment - interest;
    balance = Math.max(0, balance - principal);
    projectedInterest += interest;
    points.push(point(key, balance, original - balance, false));

    if (balance <= 0) {
      payoffKey = key;
      break;
    }
  }

  return { points, payoffKey, neverPaysOff, projectedInterest };
}
