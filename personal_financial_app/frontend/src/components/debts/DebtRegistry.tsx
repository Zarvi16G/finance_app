/**
 * Debt registry page: CRUD table with debt
summary tiles and payoff progress tracking.
 */
import { useEffect, useState, type FormEvent } from 'react';
import CardBox from '../shared/CardBox';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { debtsApi, type DebtInput } from '../../api/debts';
import { getErrorMessage } from '../../api/client';
import type { Debt } from '../../types';
import { Icon } from '@iconify/react';

const DEBT_TYPES = [
  { value: 'credit_card', label: 'Credit Card' },
  { value: 'personal_loan', label: 'Personal Loan' },
  { value: 'mortgage', label: 'Mortgage' },
  { value: 'auto_loan', label: 'Auto Loan' },
  { value: 'student_loan', label: 'Student Loan' },
  { value: 'medical_debt', label: 'Medical Debt' },
  { value: 'other', label: 'Other' },
];

const EMPTY_FORM: DebtInput = {
  name: '',
  debt_type: 'credit_card',
  creditor: '',
  original_amount: '',
  current_balance: '',
  interest_rate: '',
  minimum_payment: '',
  due_date: 1,
  start_date: '',
  notes: '',
};

export default function DebtRegistry() {
  const [debts, setDebts] = useState<Debt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Debt | null>(null);
  const [form, setForm] = useState<DebtInput>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const fetchDebts = async () => {
    setLoading(true);
    try {
      setDebts(await debtsApi.list());
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDebts();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (debt: Debt) => {
    setEditing(debt);
    setForm({
      name: debt.name,
      debt_type: debt.debt_type,
      creditor: debt.creditor,
      original_amount: String(debt.original_amount),
      current_balance: String(debt.current_balance),
      interest_rate: String(debt.interest_rate),
      minimum_payment: String(debt.minimum_payment),
      due_date: debt.due_date,
      start_date: debt.start_date,
      notes: debt.notes ?? '',
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    const payload: DebtInput = {
      ...form,
      original_amount: Number(form.original_amount),
      current_balance: Number(form.current_balance),
      interest_rate: Number(form.interest_rate),
      minimum_payment: Number(form.minimum_payment),
      due_date: Number(form.due_date),
    };
    try {
      if (editing) {
        await debtsApi.update(editing.id, payload);
      } else {
        await debtsApi.create(payload);
      }
      setDialogOpen(false);
      await fetchDebts();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this debt?')) return;
    await debtsApi.remove(id);
    await fetchDebts();
  };

  const totalBalance = debts.reduce((sum, d) => sum + Number(d.current_balance), 0);
  const totalMinPayment = debts.reduce((sum, d) => sum + Number(d.minimum_payment), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-foreground">Debt Registry</h2>
          <p className="text-sm text-muted-foreground">Track balances, interest and payments</p>
        </div>
        <Button onClick={openCreate}>
          <Icon icon="solar:add-circle-linear" height={18} width={18} className="mr-2" />
          Add Debt
        </Button>
      </div>

      {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

      {!loading && debts.length > 0 && (
        <div className="grid gap-6 md:grid-cols-3">
          <CardBox>
            <div className="p-5">
              <p className="text-sm text-muted-foreground">Total Balance</p>
              <p className="text-2xl font-semibold text-foreground">
                ${totalBalance.toLocaleString()}
              </p>
            </div>
          </CardBox>
          <CardBox>
            <div className="p-5">
              <p className="text-sm text-muted-foreground">Minimum Payments / Month</p>
              <p className="text-2xl font-semibold text-foreground">
                ${totalMinPayment.toLocaleString()}
              </p>
            </div>
          </CardBox>
          <CardBox>
            <div className="p-5">
              <p className="text-sm text-muted-foreground">Active Debts</p>
              <p className="text-2xl font-semibold text-foreground">
                {debts.filter((d) => d.status === 'active').length}
              </p>
            </div>
          </CardBox>
        </div>
      )}

      <CardBox className="overflow-hidden">
        {loading ? (
          <div className="h-60 animate-pulse rounded-lg m-5 bg-muted" />
        ) : debts.length === 0 ? (
          <div className="p-10 text-center">
            <Icon
              icon="solar:wallet-money-outline"
              height={48}
              width={48}
              className="mx-auto text-muted-foreground"
            />
            <p className="mt-3 text-muted-foreground">
              No debts tracked. Add your first debt to start a payoff plan.
            </p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Balance</TableHead>
                <TableHead className="text-right">Rate</TableHead>
                <TableHead className="text-right">Min Payment</TableHead>
                <TableHead>Progress</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {debts.map((debt) => (
                <TableRow key={debt.id}>
                  <TableCell>
                    <p className="font-medium text-foreground">{debt.name}</p>
                    <p className="text-xs text-muted-foreground">{debt.creditor}</p>
                  </TableCell>
                  <TableCell>{debt.debt_type_display}</TableCell>
                  <TableCell className="text-right font-semibold text-foreground">
                    ${Number(debt.current_balance).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">{debt.interest_rate}%</TableCell>
                  <TableCell className="text-right">
                    ${Number(debt.minimum_payment).toLocaleString()}
                  </TableCell>
                  <TableCell className="min-w-[140px]">
                    <div className="h-2 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${Math.min(debt.progress_percentage, 100)}%` }}
                      />
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {debt.progress_percentage}% paid
                    </p>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={debt.status === 'active' ? 'primary' : debt.status === 'paid_off' ? 'success' : 'gray'}
                    >
                      {debt.status_display}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(debt)}>
                        <Icon icon="solar:pen-linear" height={16} width={16} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-error hover:text-error"
                        onClick={() => handleDelete(debt.id)}
                      >
                        <Icon icon="solar:trash-bin-trash-linear" height={16} width={16} />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardBox>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Debt' : 'Add Debt'}</DialogTitle>
            <DialogDescription>Track the debt details to compute payoff progress.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="d-name">Name</Label>
                <Input
                  id="d-name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="d-type">Type</Label>
                <Select
                  value={form.debt_type}
                  onValueChange={(v) => setForm({ ...form, debt_type: v })}
                >
                  <SelectTrigger id="d-type" className="mt-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DEBT_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="d-creditor">Creditor</Label>
              <Input
                id="d-creditor"
                value={form.creditor}
                onChange={(e) => setForm({ ...form, creditor: e.target.value })}
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="d-original">Original Amount ($)</Label>
                <Input
                  id="d-original"
                  type="number"
                  min="0"
                  step="0.01"
                  value={String(form.original_amount)}
                  onChange={(e) => setForm({ ...form, original_amount: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="d-balance">Current Balance ($)</Label>
                <Input
                  id="d-balance"
                  type="number"
                  min="0"
                  step="0.01"
                  value={String(form.current_balance)}
                  onChange={(e) => setForm({ ...form, current_balance: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="d-rate">Interest Rate (% annual)</Label>
                <Input
                  id="d-rate"
                  type="number"
                  min="0"
                  step="0.01"
                  value={String(form.interest_rate)}
                  onChange={(e) => setForm({ ...form, interest_rate: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="d-min">Minimum Payment ($)</Label>
                <Input
                  id="d-min"
                  type="number"
                  min="0"
                  step="0.01"
                  value={String(form.minimum_payment)}
                  onChange={(e) => setForm({ ...form, minimum_payment: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="d-due">Due Day (1-31)</Label>
                <Input
                  id="d-due"
                  type="number"
                  min="1"
                  max="31"
                  value={form.due_date}
                  onChange={(e) => setForm({ ...form, due_date: Number(e.target.value) })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="d-start">Start Date</Label>
                <Input
                  id="d-start"
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                  required
                />
              </div>
            </div>
            <div>
              <Label htmlFor="d-notes">Notes</Label>
              <Textarea
                id="d-notes"
                rows={2}
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : editing ? 'Save Changes' : 'Add Debt'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}