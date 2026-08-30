/**
 * Financial goals page: CRUD cards with progress
bars plus overall/category analytics from
/goals/analysis/.
 */
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import CardBox from '../shared/CardBox';
import PageHeader from '../shared/PageHeader';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Badge } from '../ui/badge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { goalsApi } from '../../api/goals';
import { profileApi } from '../../api/profile';
import { getErrorMessage } from '../../api/client';
import { fmtMoney, fmtMoneyCompact, convertToBase, convertFromBase } from '../../lib/money';
import type { ExpectedGoal, GoalsAnalysis } from '../../types';
import { Icon } from '@iconify/react';

const EMPTY_FORM = {
  title: '',
  target_amount: '',
  current_amount: '',
  category: '',
  end_date: '',
  description: '',
};

export default function GoalsList() {
  const [goals, setGoals] = useState<ExpectedGoal[]>([]);
  const [analysis, setAnalysis] = useState<GoalsAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<ExpectedGoal | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [currency, setCurrency] = useState('USD');

  useEffect(() => {
    profileApi.get().then((s) => setCurrency(s.currency || 'USD')).catch(() => {});
  }, []);

  const fetchData = async () => {
    try {
      const [goalsData, analysisData] = await Promise.all([goalsApi.list(), goalsApi.analysis()]);
      setGoals(goalsData);
      setAnalysis(analysisData);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const overallProgress = useMemo(
    () => analysis?.summary.overall_progress ?? 0,
    [analysis],
  );

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (goal: ExpectedGoal) => {
    setEditing(goal);
    setForm({
      title: goal.title,
      target_amount: String(goal.target_amount),
      current_amount: String(goal.current_amount),
      category: goal.category,
      end_date: goal.end_date,
      description: goal.description,
    });
    setDialogOpen(true);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        title: form.title,
        target_amount: Number(form.target_amount),
        current_amount: Number(form.current_amount) || 0,
        category: form.category,
        start_date: new Date().toISOString().slice(0, 10),
        end_date: form.end_date,
        description: form.description,
      };
      if (editing) {
        await goalsApi.update(editing.id, payload);
      } else {
        await goalsApi.create(payload);
      }
      setDialogOpen(false);
      setLoading(true);
      setError('');
      await fetchData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this goal?')) return;
    try {
      await goalsApi.remove(id);
      setLoading(true);
      setError('');
      await fetchData();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const statusColor = (status: string): 'success' | 'primary' | 'warning' | 'error' => {
    if (status === 'achieved') return 'success';
    if (status === 'ongoing') return 'primary';
    if (status === 'failed') return 'error';
    return 'warning';
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reserve Ledger"
        title="Savings goals"
        description="Track your savings targets — what you are setting aside, and why."
        actions={
          <Button onClick={openCreate}>
            <Icon icon="solar:add-circle-linear" height={18} width={18} />
            New Goal
          </Button>
        }
      />

      {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

      {loading ? (
        <div className="h-40 animate-pulse rounded-lg bg-muted" />
      ) : (
        <>
          {analysis && (
            <CardBox>
              <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
                <div>
                  <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
                    Overall Progress
                  </p>
                  <p className="mt-1 font-mono text-2xl font-medium tabular-nums text-foreground">
                    {overallProgress}%
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">
                    {analysis.summary.achieved_goals} / {analysis.summary.total_goals} achieved
                  </Badge>
                </div>
                <div className="h-1.5 w-64 max-w-full overflow-hidden rounded-sm bg-muted">
                  <div
                    className="h-full rounded-sm bg-success transition-all"
                    style={{ width: `${overallProgress}%` }}
                  />
                </div>
              </div>
            </CardBox>
          )}

          {goals.length === 0 ? (
            <CardBox className="p-10 text-center">
              <Icon
                icon="solar:target-outline"
                height={48}
                width={48}
                className="mx-auto text-muted-foreground"
              />
              <p className="mt-3 text-muted-foreground">
                No goals yet. Create your first savings goal.
              </p>
            </CardBox>
          ) : (
            <div className="grid gap-6 md:grid-cols-2">
              {goals.map((goal) => (
                <CardBox key={goal.id}>
                  <div className="p-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-foreground">{goal.title}</h3>
                        <p className="text-sm text-muted-foreground">{goal.category}</p>
                      </div>
                      <Badge variant={statusColor(goal.status)}>
                        {goal.status}
                      </Badge>
                    </div>

                    <div className="mt-4 flex items-end justify-between">
                      <div>
                        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                          Current
                        </p>
                        <p className="mt-0.5 font-mono text-lg font-medium tabular-nums text-foreground">
                          {fmtMoneyCompact(Number(goal.current_amount), currency)}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                          Target
                        </p>
                        <p className="mt-0.5 font-mono text-lg font-medium tabular-nums text-foreground">
                          {fmtMoneyCompact(Number(goal.target_amount), currency)}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 h-2 overflow-hidden rounded-sm bg-muted">
                      <div
                        className="h-full rounded-sm bg-success transition-all"
                        style={{ width: `${Math.min(goal.progress_percentage, 100)}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {goal.progress_percentage}% complete · Target date:{' '}
                      {goal.end_date || '—'}
                    </p>

                    {goal.description && (
                      <p className="mt-3 text-sm text-foreground/80">{goal.description}</p>
                    )}

                    <div className="mt-4 flex gap-2">
                      <Button variant="outline" size="sm" onClick={() => openEdit(goal)}>
                        Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-error hover:text-error"
                        onClick={() => handleDelete(goal.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </CardBox>
              ))}
            </div>
          )}
        </>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Goal' : 'New Goal'}</DialogTitle>
            <DialogDescription>
              Set a target amount and track your progress over time.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                required
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="target">Target Amount ($)</Label>
                <Input
                  id="target"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.target_amount}
                  onChange={(e) => setForm({ ...form, target_amount: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="current">Current Amount ($)</Label>
                <Input
                  id="current"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.current_amount}
                  onChange={(e) => setForm({ ...form, current_amount: e.target.value })}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="category">Category</Label>
                <Input
                  id="category"
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  required
                />
              </div>
              <div>
                <Label htmlFor="end_date">Target Date</Label>
                <Input
                  id="end_date"
                  type="date"
                  value={form.end_date}
                  onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                  required
                />
              </div>
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={3}
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : editing ? 'Save Changes' : 'Create Goal'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export { GoalsList };