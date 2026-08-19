/**
 * Bank statements list: uploads, status,
inline type editing, reprocess and PDF
download actions.
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import CardBox from '../shared/CardBox';
import PageHeader from '../shared/PageHeader';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { statementsApi } from '../../api/statements';
import { getErrorMessage } from '../../api/client';
import type { BankStatement } from '../../types';
import { Icon } from '@iconify/react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';

const statusTone: Record<string, 'success' | 'warning' | 'error'> = {
  completed: 'success',
  processing: 'warning',
  failed: 'error',
};

const STATEMENT_TYPE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'savings', label: 'Savings Account' },
  { value: 'checking', label: 'Checking Account' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'loan', label: 'Loan Statement' },
  { value: 'investment', label: 'Investment Account' },
  { value: 'other', label: 'Other' },
];

export default function StatementList() {
  const [statements, setStatements] = useState<BankStatement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [processingId, setProcessingId] = useState<number | string | null>(null);
  const [updatingType, setUpdatingType] = useState<number | string | null>(null);
  const [deletingId, setDeletingId] = useState<number | string | null>(null);

  const fetchStatements = async () => {
    setLoading(true);
    try {
      setStatements(await statementsApi.list());
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatements();
  }, []);

  const handleReprocess = async (id: number | string) => {
    setProcessingId(id);
    setError('');
    try {
      await statementsApi.reprocess(id);
      await fetchStatements();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setProcessingId(null);
    }
  };

  const handleDelete = async (id: number | string) => {
    const statement = statements.find((s) => s.id === id);
    if (!window.confirm(`Delete "${statement?.original_filename ?? 'this statement'}"?\nThe file and its extracted transactions will be removed.`)) {
      return;
    }
    setDeletingId(id);
    setError('');
    try {
      await statementsApi.remove(id);
      await fetchStatements();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDeletingId(null);
    }
  };

  const handleTypeChange = async (id: number | string, value: string) => {
    const previous = statements.find((s) => s.id === id);
    setUpdatingType(id);
    setError('');
    setStatements((prev) => prev.map((s) => (s.id === id ? { ...s, statement_type: value } : s)));
    try {
      await statementsApi.update(id, { statement_type: value });
    } catch (err) {
      if (previous) {
        setStatements((prev) =>
          prev.map((s) => (s.id === id ? { ...s, statement_type: previous.statement_type } : s)),
        );
      }
      setError(getErrorMessage(err));
    } finally {
      setUpdatingType(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Transaction Ledger · Imports"
        title="Bank statements"
        description="Uploaded statements and extraction status — import a PDF to add transactions."
        actions={
          <Button asChild>
            <Link to="/statements/upload">
              <Icon icon="solar:upload-linear" height={18} width={18} />
              Upload Statement
            </Link>
          </Button>
        }
      />

      {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

      <CardBox className="overflow-hidden">
        {loading ? (
          <div className="h-60 animate-pulse rounded-lg m-5 bg-muted" />
        ) : statements.length === 0 ? (
          <div className="p-10 text-center">
            <Icon
              icon="solar:document-text-outline"
              height={48}
              width={48}
              className="mx-auto text-muted-foreground"
            />
            <p className="mt-3 text-muted-foreground">
              No statements yet. Upload your first bank statement PDF.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>File</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Extracted</TableHead>
                <TableHead>Uploaded</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {statements.map((st) => (
                <TableRow key={st.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Icon
                        icon="solar:file-pdf-bold"
                        height={20}
                        width={20}
                        className="text-error"
                      />
                      <div>
                        <p className="font-medium text-foreground">{st.original_filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {st.file_size_mb} MB {st.bank_name ? `· ${st.bank_name}` : ''}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Select
                      value={st.statement_type}
                      disabled={updatingType === st.id}
                      onValueChange={(value) => handleTypeChange(st.id, value)}
                    >
                      <SelectTrigger className="h-7 w-40 text-xs">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {STATEMENT_TYPE_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={opt.value}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {updatingType === st.id && (
                      <p className="mt-1 text-xs text-muted-foreground">Saving…</p>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusTone[st.status] ?? 'gray'}>{st.status_display}</Badge>
                    {st.error_message && (
                      <p className="mt-1 text-xs text-error">{st.error_message}</p>
                    )}
                  </TableCell>
                  <TableCell>
                    {st.total_transactions_imported} / {st.total_transactions_extracted}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(st.uploaded_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button asChild variant="outline" size="sm">
                        <Link to={`/statements/${st.id}/review`}>Review</Link>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={processingId === st.id}
                        onClick={() => handleReprocess(st.id)}
                      >
                        <Icon icon="solar:restart-linear" height={16} width={16} />
                        <span className="ml-1">
                          {processingId === st.id ? 'Reprocessing…' : 'Reprocess'}
                        </span>
                      </Button>
                      {st.status === 'completed' && (
                        <Button asChild variant="ghost" size="sm">
                          <a href={statementsApi.fileUrl(st.id)} target="_blank" rel="noreferrer">
                            <Icon icon="solar:download-linear" height={16} width={16} />
                            <span className="ml-1">PDF</span>
                          </a>
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-error hover:text-error"
                        disabled={deletingId === st.id}
                        onClick={() => handleDelete(st.id)}
                      >
                        <Icon
                          icon={deletingId === st.id ? 'solar:trash-bin-minimalistic-linear' : 'solar:trash-bin-trash-linear'}
                          height={16}
                          width={16}
                        />
                        <span className="ml-1">{deletingId === st.id ? 'Deleting…' : 'Delete'}</span>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardBox>
    </div>
  );
}