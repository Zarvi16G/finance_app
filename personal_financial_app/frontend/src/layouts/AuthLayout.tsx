/**
 * The signed-out shell: a dark brand panel on the left, the form on the right.
 *
 * The left panel carries the one sentence that tells the visitor where they
 * are in the sign-in sequence — which is what makes the second-factor step
 * legible as a step rather than as an error.
 */
import type { ReactNode } from 'react';

export default function AuthLayout({
  headline,
  blurb,
  footnote,
  children,
}: {
  headline: string;
  blurb: string;
  footnote: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <div className="hidden w-[46%] shrink-0 flex-col justify-between bg-[#241f1b] px-14 py-14 text-[#f0ece4] lg:flex">
        <div className="fig text-[23px] font-medium">Patrimonio</div>
        <div>
          <h2 className="fig m-0 max-w-[18ch] text-[34px] font-normal leading-tight">{headline}</h2>
          <p className="m-0 mt-4 max-w-[44ch] text-[15px] leading-relaxed text-[#b3aa9e]">
            {blurb}
          </p>
        </div>
        <div className="text-[13px] text-[#7d746a]">{footnote}</div>
      </div>

      <div className="flex flex-grow items-center justify-center px-6 py-14">
        <div className="w-full max-w-[400px]">{children}</div>
      </div>
    </div>
  );
}
