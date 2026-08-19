/**
 * AI-powered financial analysis page: runs the
analysis service (optionally on filtered
records) and renders the text report.
 */
import { useState } from 'react';
import CardBox from '../shared/CardBox';
import PageHeader from '../shared/PageHeader';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { aiApi } from '../../api/ai';
import { getErrorMessage } from '../../api/client';
import { Alert, AlertDescription, AlertTitle } from '../ui/alert';
import { Icon } from '@iconify/react';

function renderRichText(text: string) {
  return text.split('\n').map((line, i) => {
    const trimmed = line.trim();
    if (!trimmed) return <div key={i} className="h-2" />;

    if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      return (
        <div key={i} className="flex gap-2">
          <span className="text-primary">•</span>
          <span>{renderInline(trimmed.replace(/^[-•]\s*/, ''))}</span>
        </div>
      );
    }

    if (/^\d+\.\s/.test(trimmed)) {
      return (
        <div key={i} className="flex gap-2">
          <span className="font-semibold text-primary">{trimmed.match(/^\d+\./)?.[0]}</span>
          <span>{renderInline(trimmed.replace(/^\d+\.\s*/, ''))}</span>
        </div>
      );
    }

    if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
      return (
        <h3 key={i} className="mt-5 mb-1 font-display text-xl font-normal text-foreground">
          {renderInline(trimmed)}
        </h3>
      );
    }

    return <p key={i} className="text-foreground/90">{renderInline(trimmed)}</p>;
  });
}

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? (
      <strong key={i} className="font-semibold text-foreground">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export default function Analysis() {
  const [analysis, setAnalysis] = useState('');
  const [usedFallback, setUsedFallback] = useState(false);
  const [loading, setLoading] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [error, setError] = useState('');

  const runAnalysis = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await aiApi.analyze();
      setAnalysis(result.analysis);
      setUsedFallback(result.used_fallback);
      setHasRun(true);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Auditor's Report"
        title="Financial analysis"
        description="An AI audit of your spending, savings and goals — run it whenever you like."
        actions={
          <Button onClick={runAnalysis} disabled={loading}>
            {loading ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Analyzing…
              </>
            ) : (
              <>
                <Icon icon="solar:magic-stick-3-linear" height={18} width={18} />
                {hasRun ? 'Run Again' : 'Start Analysis'}
              </>
            )}
          </Button>
        }
      />

      {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

      {!hasRun && !loading && (
        <CardBox className="px-10 py-14 text-center">
          <p className="letterhead">Report Status · Not Yet Issued</p>
          <p className="mt-2 font-display text-2xl font-normal text-foreground md:text-3xl">
            The books are waiting
          </p>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            Run an analysis to get an executive health audit, budget leak analysis and actionable
            steps — printed from your own records.
          </p>
          <Button onClick={runAnalysis} className="mt-6" disabled={loading}>
            <Icon icon="solar:magic-stick-3-linear" height={18} width={18} />
            Start Analysis
          </Button>
        </CardBox>
      )}

      {hasRun && (
        <CardBox>
          <div className="border-b border-border px-6 py-4">
            <p className="letterhead">Auditor's Report · {new Date().toLocaleDateString()}</p>
          </div>
          <div className="p-6">
            {usedFallback && (
              <Alert className="mb-4 border-warning bg-lightwarning text-warning">
                <AlertTitle className="font-mono text-[10px] uppercase tracking-[0.14em]">
                  Rule-based analysis
                </AlertTitle>
                <AlertDescription>
                  No external AI provider responded, so the built-in expert system generated this
                  report.
                </AlertDescription>
              </Alert>
            )}
            <div className="flex flex-wrap gap-2">
              <Badge variant="lightPrimary">Financial Health</Badge>
              <Badge variant="lightSuccess">Actionable</Badge>
            </div>
            <div className="mt-4 max-w-3xl space-y-1">{renderRichText(analysis)}</div>
          </div>
        </CardBox>
      )}
    </div>
  );
}