/**
 * Ledgerline brand mark: an "L" drawn as a column of ledger rules.
 * Renders in currentColor so it follows the active theme.
 */
export default function LedgerMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <rect x="8" y="7" width="2.5" height="17" fill="currentColor" />
      <rect x="8" y="9" width="16" height="2.5" fill="var(--success)" />
      <rect x="8" y="14" width="12" height="2.5" fill="currentColor" />
      <rect x="8" y="19" width="8" height="2.5" fill="currentColor" />
    </svg>
  );
}