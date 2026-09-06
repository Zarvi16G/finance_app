/**
 * Chart colours read from the CSS token layer rather than hard-coded.
 *
 * Recharts needs literal colour strings, not `var(--chart-1)`, so the values
 * have to be resolved in JS. Doing that once at module load would freeze the
 * light-theme palette into every chart; the hook below re-resolves whenever
 * the theme changes, so charts follow the toggle like the rest of the page.
 */
import { useEffect, useState } from 'react';

export interface ChartPalette {
  income: string;
  expense: string;
  brand: string;
  intermediate: string;
  remainder: string;
  ink: string;
  rule: string;
  muted: string;
  mutedText: string;
}

const read = (name: string, fallback: string): string => {
  if (typeof window === 'undefined') return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
};

const resolve = (): ChartPalette => ({
  income: read('--chart-1', '#2f6b4f'),
  expense: read('--chart-2', '#9c4a3a'),
  brand: read('--chart-3', '#3b4a6b'),
  intermediate: read('--chart-4', '#8a5c1e'),
  remainder: read('--chart-5', '#8b8078'),
  ink: read('--foreground', '#241f1b'),
  rule: read('--border', '#e2ddd3'),
  muted: read('--muted', '#e8e3da'),
  mutedText: read('--muted-foreground', '#8b8078'),
});

export function useChartPalette(): ChartPalette {
  const [palette, setPalette] = useState<ChartPalette>(resolve);

  useEffect(() => {
    // Watch the class attribute rather than the theme context: the provider
    // writes that class from its own effect, and a child's effect runs first,
    // so subscribing to the context value would read the previous theme's
    // colours. The attribute changing is the moment the palette is actually
    // different.
    const root = document.documentElement;
    const observer = new MutationObserver(() => setPalette(resolve()));
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    setPalette(resolve());
    return () => observer.disconnect();
  }, []);

  return palette;
}
