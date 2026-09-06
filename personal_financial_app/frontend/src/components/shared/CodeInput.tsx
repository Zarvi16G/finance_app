/**
 * The six-box code field used by the login challenge and by 2FA enrollment.
 *
 * It is one real `<input>` behind six drawn boxes rather than six inputs.
 * That keeps paste working (a code copied from an authenticator app arrives
 * as one string), keeps the browser's autofill for one-time codes working,
 * and means there is a single value to submit — six inputs would need
 * focus-juggling on every keystroke and would break paste entirely.
 */
import { useId, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { cn } from '../../lib/utils';

export default function CodeInput({
  value,
  onChange,
  onComplete,
  length = 6,
  disabled,
  autoFocus,
  label,
  size = 'md',
}: {
  value: string;
  onChange: (value: string) => void;
  /** Fired once the last digit lands, so the form can submit itself. */
  onComplete?: (value: string) => void;
  length?: number;
  disabled?: boolean;
  autoFocus?: boolean;
  label?: string;
  size?: 'md' | 'lg';
}) {
  const { t } = useTranslation();
  const inputRef = useRef<HTMLInputElement>(null);
  const id = useId();

  const boxes = Array.from({ length }, (_, i) => i);
  const activeIndex = Math.min(value.length, length - 1);

  const handleChange = (raw: string) => {
    const digits = raw.replace(/\D/g, '').slice(0, length);
    onChange(digits);
    if (digits.length === length) onComplete?.(digits);
  };

  const dims = size === 'lg' ? 'h-[68px] w-14 text-[26px]' : 'h-[54px] w-11 text-[21px]';

  return (
    <div>
      {label && (
        <label htmlFor={id} className="mb-2 block text-xs text-muted-foreground">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          ref={inputRef}
          id={id}
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          disabled={disabled}
          autoFocus={autoFocus}
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={length}
          aria-label={label ?? t('auth.codeLabel')}
          // Invisible but focusable and on top, so a click anywhere on the
          // boxes lands in the field the keyboard actually writes to.
          className="absolute inset-0 z-10 h-full w-full cursor-text opacity-0"
        />
        <div className="flex gap-2" aria-hidden="true">
          {boxes.map((i) => (
            <div
              key={i}
              className={cn(
                'flex items-center justify-center border bg-card font-mono tabular-nums',
                dims,
                value[i]
                  ? 'border-foreground'
                  : i === activeIndex && !disabled
                    ? 'border-2 border-primary'
                    : 'border-input',
              )}
            >
              {value[i] ?? ''}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
