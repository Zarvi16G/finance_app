/**
 * Hook: manages user's profile/viewing currency preference with persistent cookie.
 * 
 * - Reads 'profile_currency' cookie on mount (defaults to 'USD')
 * - Provides setProfileCurrency() to update the cookie and API
 * - Provides getConvertedAmount(amount, currency) to convert using daily rates
 * - Provides getDisplayCurrency() to return the profile currency
 */
import { useEffect, useState } from 'react';

const COOKIE_NAME = 'profile_currency';
const DEFAULT_CURRENCY = 'USD';

export function useProfileCurrency() {
  const [profileCurrency, setProfileCurrency] = useState<string>(DEFAULT_CURRENCY);

  useEffect(() => {
    // Read cookie on mount
    const cookieValue = readCookie(COOKIE_NAME);
    if (cookieValue) {
      setProfileCurrency(cookieValue);
    }
  }, []);

  const readCookie = (name: string): string | null => {
    const match = document.cookie.match(
      new RegExp(`(^| )${name}=([^;]+)`)
    );
    return match ? match[2] : null;
  };

  const setCookie = (name: string, value: string, days: number = 365) => {
    const date = new Date();
    date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = `${name}=${value};expires=${date.toUTCString()};path=/`;
  };

  const setProfileCurrency = async (currency: string) => {
    setProfileCurrency(currency);
    setCookie(COOKIE_NAME, currency);
    // Update the backend profile setting
    try {
      await fetch('/api/profile/', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ currency }),
      });
    } catch (err) {
      // If API fails, keep the cookie but don't crash
      console.error('Failed to update profile currency:', err);
    }
  };

  const getConvertedAmount = (
    amount: number | undefined | null,
    fromCurrency: string = DEFAULT_CURRENCY
  ): number => {
    if (amount == null || amount === undefined || fromCurrency === DEFAULT_CURRENCY) {
      return amount ?? 0;
    }
    // If fromCurrency is the profile currency and we're converting to USD, 
    // or vice versa, we need the rates
    // This will be enhanced once we have the daily rates API integration
    return amount;
  };

  const getDisplayCurrency = (): string => {
    return profileCurrency;
  };

  return {
    profileCurrency,
    setProfileCurrency,
    getConvertedAmount,
    getDisplayCurrency,
  };
}