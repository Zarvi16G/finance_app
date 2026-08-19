/**
 * Upload page: drag-and-drop PDF with
statement type/password optionals;
type is auto-detected server-side.
 */
import { useRef, useState, type DragEvent, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import CardBox from '../shared/CardBox';
import PageHeader from '../shared/PageHeader';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { statementsApi } from '../../api/statements';
import { getErrorMessage } from '../../api/client';
import { Icon } from '@iconify/react';

const STATEMENT_TYPES = [
  { value: 'savings', label: 'Savings Account' },
  { value: 'checking', label: 'Checking Account' },
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'loan', label: 'Loan Statement' },
  { value: 'investment', label: 'Investment Account' },
  { value: 'other', label: 'Other' },
];

export default function StatementUploader() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [statementType, setStatementType] = useState('other');
  const [password, setPassword] = useState('');
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    setError('');
    const f = files?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.');
      return;
    }
    setFile(f);
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a PDF file first.');
      return;
    }
    setUploading(true);
    setError('');
    try {
      const statement = await statementsApi.upload(file, statementType, password || undefined);
      if (statement.status === 'completed') {
        navigate(`/statements/${statement.id}/review`);
      } else {
        navigate('/statements');
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Account Statement · Import"
        title="Import a statement"
        description="Upload a PDF bank statement — transactions are extracted automatically."
      />

      <CardBox className="max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-5 p-6">
          <div
            className={`grid cursor-pointer place-items-center rounded-sm border-2 border-dashed p-12 text-center transition ${
              dragging
                ? 'border-primary bg-lightprimary'
                : 'border-border hover:border-primary/50'
            }`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
            <Icon
              icon={file ? 'solar:file-pdf-bold' : 'solar:cloud-upload-linear'}
              height={44}
              width={44}
              className={file ? 'text-error' : 'text-muted-foreground'}
            />
            <p className="mt-3 font-medium text-foreground">
              {file ? file.name : 'Drag & drop your PDF here, or click to browse'}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {file ? `${(file.size / 1024 / 1024).toFixed(2)} MB` : 'Only PDF files are supported'}
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="statement-type">Statement Type</Label>
              <Select value={statementType} onValueChange={setStatementType}>
                <SelectTrigger id="statement-type" className="mt-2">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {STATEMENT_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="password">Password (optional)</Label>
              <Input
                id="password"
                type="password"
                className="mt-2"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="For encrypted PDFs"
              />
            </div>
          </div>

          {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

          <div className="flex gap-3">
            <Button type="submit" disabled={uploading || !file}>
              {uploading ? (
                <>
                  <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Processing…
                </>
              ) : (
                <>
                  <Icon icon="solar:upload-linear" height={18} width={18} className="mr-2" />
                  Upload & Process
                </>
              )}
            </Button>
            <Button asChild variant="outline">
              <Link to="/statements">Cancel</Link>
            </Button>
          </div>
        </form>
      </CardBox>
    </div>
  );
}