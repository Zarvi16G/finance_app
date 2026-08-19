/**
 * Statement review page: confirms and
bulk-confirms extracted transactions,
AI-categorizes rows and chats with the
AI assistant.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Input } from '../ui/input';
import { statementsApi, extractedApi } from '../../api/statements';
import { choicesApi } from '../../api/profile';
import { aiApi } from '../../api/ai';
import { getErrorMessage } from '../../api/client';
import type { BankStatement, Choice, ExtractedTransaction } from '../../types';
import { Icon } from '@iconify/react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

type OptimisticTxn = ExtractedTransaction & { confirmed?: boolean };

export default function StatementReview() {
  const { id } = useParams<{ id: string }>();
  const [statement, setStatement] = useState<BankStatement | null>(null);
  const [txns, setTxns] = useState<OptimisticTxn[]>([]);
  const [choices, setChoices] = useState<Choice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [confirming, setConfirming] = useState<number | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [aiRunning, setAiRunning] = useState(false);

  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const categories = useMemo(
    () => choices.filter((c) => c.choice_type === 'category'),
    [choices],
  );
  const types = useMemo(() => choices.filter((c) => c.choice_type === 'type'), [choices]);

  const fetchAll = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [statementData, txnData, choicesData] = await Promise.all([
        statementsApi.get(id),
        statementsApi.extracted(id),
        choicesApi.list(),
      ]);
      setStatement(statementData);
      setTxns((txnData as OptimisticTxn[]) ?? []);
      setChoices(choicesData);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const updateTxn = (txnId: number, patch: Partial<OptimisticTxn>) => {
    setTxns((prev) => prev.map((t) => (t.id === txnId ? { ...t, ...patch } : t)));
  };

  const handleConfirm = async (txnId: number) => {
    const txn = txns.find((t) => t.id === txnId);
    if (!txn) return;
    setConfirming(txnId);
    setError('');
    try {
      await extractedApi.confirm(txnId, {
        category: txn.user_confirmed_category || txn.suggested_category || '',
        type: txn.user_confirmed_type || txn.transaction_type,
        description: txn.cleaned_description,
      });
      updateTxn(txnId, { confirmed: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setConfirming(null);
    }
  };

  const handleBulkConfirm = async () => {
    const items = txns.filter((t) => selected.has(t.id));
    if (!items.length) return;
    setError('');
    try {
      await extractedApi.bulkConfirm(
        items.map((t) => ({
          id: t.id,
          category: t.user_confirmed_category || t.suggested_category || '',
          type: t.user_confirmed_type || t.transaction_type,
          description: t.cleaned_description,
        })),
      );
      setSelected(new Set());
      await fetchAll();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleAiCategorize = async () => {
    const ids = txns.filter((t) => !t.confirmed).map((t) => t.id);
    if (!ids.length) return;
    setAiRunning(true);
    setError('');
    try {
      const { results } = await aiApi.categorize(ids);
      const byId = new Map(results.filter((r) => r.id).map((r) => [r.id, r]));
      setTxns((prev) =>
        prev.map((t) => {
          const suggestion = byId.get(t.id);
          return suggestion
            ? {
                ...t,
                suggested_category: suggestion.suggested_category,
                suggested_category_display: suggestion.suggested_category,
                suggested_type: suggestion.suggested_type,
              }
            : t;
        }),
      );
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setAiRunning(false);
    }
  };

  const sendChat = async () => {
    const text = chatInput.trim();
    if (!text || chatBusy) return;
    const ids = txns.filter((t) => !t.confirmed).map((t) => t.id);
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setChatInput('');
    setChatBusy(true);
    try {
      const { reply } = await aiApi.chat(text, ids, history);
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${getErrorMessage(err)}` },
      ]);
    } finally {
      setChatBusy(false);
    }
  };

  const pendingCount = txns.filter((t) => !t.confirmed).length;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Account Statement · Review"
        title="Review transactions"
        description={`${statement?.original_filename ?? 'Statement'} · ${pendingCount} pending confirmation`}
        actions={
          <div className="flex flex-wrap gap-2">
            {pendingCount > 0 && (
              <Button variant="outline" onClick={handleAiCategorize} disabled={aiRunning}>
                <Icon icon="solar:magic-stick-3-linear" height={18} width={18} />
                {aiRunning ? 'Categorizing…' : 'AI Categorize'}
              </Button>
            )}
            {selected.size > 0 && (
              <Button onClick={handleBulkConfirm}>
                <Icon icon="solar:check-circle-linear" height={18} width={18} />
                Confirm {selected.size} selected
              </Button>
            )}
            <Button
              variant={chatOpen ? 'secondary' : 'default'}
              onClick={() => setChatOpen((o) => !o)}
            >
              <Icon icon="solar:chat-round-dots-linear" height={18} width={18} />
              AI Assistant
            </Button>
          </div>
        }
      />

      {error && <p className="rounded-md bg-error/10 px-3 py-2 text-sm text-error">{error}</p>}

      <div className="grid gap-6 xl:grid-cols-3">
        <CardBox className={`overflow-hidden ${chatOpen ? '' : 'xl:col-span-3'}`}>
          {loading ? (
            <div className="h-80 animate-pulse rounded-lg m-5 bg-muted" />
          ) : txns.length === 0 ? (
            <div className="p-10 text-center">
              <Icon
                icon="solar:inbox-outline"
                height={48}
                width={48}
                className="mx-auto text-muted-foreground"
              />
              <p className="mt-3 text-muted-foreground">No transactions extracted.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-primary"
                      checked={selected.size === txns.filter((t) => !t.confirmed).length && txns.length > 0}
                      onChange={(e) =>
                        setSelected(
                          e.target.checked
                            ? new Set(txns.filter((t) => !t.confirmed).map((t) => t.id))
                            : new Set(),
                        )
                      }
                    />
                  </TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {txns.map((txn) => (
                  <TableRow key={txn.id} className={txn.confirmed ? 'opacity-60' : ''}>
                    <TableCell>
                      {!txn.confirmed && (
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-primary"
                          checked={selected.has(txn.id)}
                          onChange={(e) => {
                            const next = new Set(selected);
                            if (e.target.checked) next.add(txn.id);
                            else next.delete(txn.id);
                            setSelected(next);
                          }}
                        />
                      )}
                    </TableCell>
                    <TableCell className="whitespace-nowrap font-mono text-xs tabular-nums text-muted-foreground">
                      {txn.date}
                    </TableCell>
                    <TableCell>
                      <p className="font-medium text-foreground">{txn.cleaned_description}</p>
                      <p className="text-xs text-muted-foreground">{txn.raw_description}</p>
                      {txn.needs_review && (
                        <Badge variant="warning" className="mt-1">
                          Needs review
                        </Badge>
                      )}
                      {txn.confirmed && (
                        <Badge variant="success" className="mt-1">
                          Confirmed
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-mono tabular-nums text-foreground">
                      ${Number(txn.amount).toLocaleString()}
                    </TableCell>
                    <TableCell className="min-w-[150px]">
                      <Select
                        value={txn.user_confirmed_category || txn.suggested_category || ''}
                        onValueChange={(v) => updateTxn(txn.id, { user_confirmed_category: v })}
                      >
                        <SelectTrigger className="h-8 text-sm">
                          <SelectValue placeholder="Category" />
                        </SelectTrigger>
                        <SelectContent>
                          {categories.map((c) => (
                            <SelectItem key={c.id} value={c.name}>
                              {c.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="min-w-[130px]">
                      <Select
                        value={txn.user_confirmed_type || txn.transaction_type}
                        onValueChange={(v) => updateTxn(txn.id, { user_confirmed_type: v })}
                      >
                        <SelectTrigger className="h-8 text-sm">
                          <SelectValue placeholder="Type" />
                        </SelectTrigger>
                        <SelectContent>
                          {types.map((t) => (
                            <SelectItem key={t.id} value={t.name}>
                              {t.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-right">
                      {!txn.confirmed && (
                        <Button
                          size="sm"
                          disabled={confirming === txn.id}
                          onClick={() => handleConfirm(txn.id)}
                        >
                          {confirming === txn.id ? '…' : 'Confirm'}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardBox>

        {chatOpen && (
          <CardBox className="flex h-[560px] flex-col">
            <div className="border-b border-border p-4">
              <h3 className="font-semibold text-foreground">AI Assistant</h3>
              <p className="text-xs text-muted-foreground">
                Ask about transactions, create categories, or get help
              </p>
            </div>
            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Hi! I can help review transactions and suggest categories. Try: "create a
                  category for subscriptions".
                </p>
              )}
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`max-w-[85%] rounded-sm px-3 py-2 text-sm ${
                    m.role === 'user'
                      ? 'ml-auto bg-primary text-primary-foreground'
                      : 'bg-muted text-foreground'
                  }`}
                >
                  {m.content}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
            <div className="flex gap-2 border-t border-border p-3">
              <Input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendChat()}
                placeholder="Type a message…"
                disabled={chatBusy}
              />
              <Button onClick={sendChat} disabled={chatBusy || !chatInput.trim()} size="icon">
                <Icon icon="solar:arrow-up-linear" height={18} width={18} />
              </Button>
            </div>
          </CardBox>
        )}
      </div>
    </div>
  );
}