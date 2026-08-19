// shadcn/ui primitive: badge — restyled as statement stamps:
// squared-off, monospace, uppercase, printed on tinted stock.
import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from 'src/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-[2px] border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.12em] transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border-transparent text-primary-foreground bg-primary',
        primary: 'border-transparent text-primary-foreground bg-primary',
        secondary: 'border-transparent bg-secondary text-secondary-foreground',
        success: 'border-transparent bg-success text-white dark:text-dark',
        warning: 'border-transparent bg-warning text-white dark:text-dark',
        info: 'border-transparent bg-info text-white dark:text-dark',
        error: 'border-transparent bg-error text-white dark:text-dark',
        outline: 'border-primary text-primary',
        outlineSecondary: 'border-secondary text-secondary',
        outlineSuccess: 'border-success text-success',
        outlineWarning: 'border-warning text-warning',
        outlineError: 'border-error text-error',
        outlineInfo: 'border-info text-info',
        lightPrimary: 'bg-lightprimary text-primary border-0',
        lightSecondary: 'bg-lightsecondary text-secondary border-0',
        lightSuccess: 'bg-lightsuccess text-success border-0',
        lightError: 'bg-lighterror text-error border-0',
        lightInfo: 'bg-lightinfo text-info border-0',
        lightWarning: 'bg-lightwarning text-warning border-0',
        destructive: 'border-transparent bg-destructive text-destructive-foreground',
        gray: 'border-transparent bg-muted text-foreground'
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
  VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
