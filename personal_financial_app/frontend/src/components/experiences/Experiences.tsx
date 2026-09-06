/**
 * Experiencias de vida — a trip, a course, a wedding: something with a date
 * and a budget of its own, separate from a plain savings goal.
 *
 * The screen's job is to keep two numbers apart that are easy to confuse and
 * that the backend deliberately does not reconcile:
 *
 *   meta de ahorro     what the user decided to save   (they own this number)
 *   presupuesto        what the itemised lines add up to
 *
 * Their difference is the useful signal — a trip budgeted at 8M against a 7M
 * target is a plan with a hole in it — so it gets its own column instead of
 * being silently smoothed away.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Icon } from '@iconify/react';
import PageHeader from '../shared/PageHeader';
import BaseCurrencyBadge from '../shared/BaseCurrencyBadge';
import EmptyState from '../shared/EmptyState';
import { Button } from '../ui/button';
import BudgetItemForm from './BudgetItemForm';
import { budgetCategoryLabel, budgetItemsApi, experiencesApi } from '../../api/experiences';
import { getErrorMessage } from '../../api/client';
import { fmtDate, fmtFigure, fmtPercent } from '../../lib/money';
import type { Experience, ExperienceBudgetItem, LifeExperiences } from '../../types';

const COLS = 'grid grid-cols-[1.5fr_1fr_1fr_1fr_0.8fr_40px] items-center gap-5';

/** Rotating neutrals for the category split — a share of a plan is not money
 *  coming in or going out, so it must not borrow the income/expense colours. */
const SPLIT_TONES = ['bg-foreground', 'bg-secondary', 'bg-muted-foreground', 'bg-muted'];

export default function Experiences() {
  const [data, setData] = useState<LifeExperiences | null>(null);
  const [items, setItems] = useState<ExperienceBudgetItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editing, setEditing] = useState<ExperienceBudgetItem | 'new' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  // Bumped after a write, to re-run the lines fetch without changing the
  // selected trip.
  const [itemsVersion, setItemsVersion] = useState(0);

  /** The list of experiences with their totals. */
  const load = useCallback(async () => {
    setError(null);
    try {
      const overview = await experiencesApi.overview();
      setData(overview);
      // Keep the current selection if it survived the reload; otherwise fall
      // back to the first trip.
      setSelectedId((current) =>
        overview.experiences.some((e) => e.id === current)
          ? current
          : (overview.experiences[0]?.id ?? null),
      );
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // The lines belong to whichever trip is selected, so they are fetched on
  // their own — switching trips must not refetch every trip's totals.
  useEffect(() => {
    if (selectedId === null) {
      setItems([]);
      return;
    }
    let cancelled = false;
    budgetItemsApi
      .list(selectedId)
      .then((rows) => {
        if (!cancelled) setItems(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(getErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, itemsVersion]);

  /** Refresh both after a line was created, edited or deleted: the line list
   *  changed, and so did every total computed from it. */
  const reload = useCallback(async () => {
    setItemsVersion((v) => v + 1);
    await load();
  }, [load]);

  const removeItem = async (item: ExperienceBudgetItem) => {
    if (!window.confirm(`¿Eliminar la línea "${item.label}"?`)) return;
    try {
      await budgetItemsApi.remove(item.id);
      await reload();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  if (loading) return <p className="text-sm text-muted-foreground">Cargando tus experiencias…</p>;
  if (!data) {
    return <p className="border border-error/40 bg-lighterror p-4 text-sm text-error">{error}</p>;
  }

  const base = data.base_currency;
  const current: Experience | undefined = data.experiences.find((e) => e.id === selectedId);

  if (!current) {
    return (
      <div className="flex flex-col gap-8">
        <PageHeader
          eyebrow="Experiencias de vida"
          title="Todavía no hay ninguna"
          actions={<BaseCurrencyBadge currency={base} />}
        />
        <EmptyState
          label="Experiencias"
          headline="Ninguna todavía"
          explanation={
            <>
              Un viaje, un curso, una boda: algo con fecha y presupuesto propio, separado de tus
              metas de ahorro. Se crean desde{' '}
              <Link to="/metas" className="font-semibold text-primary hover:underline">
                Metas
              </Link>
              , marcando la meta como experiencia.
            </>
          }
          action={{ label: 'Ir a Metas', to: '/metas' }}
          className="max-w-lg"
        />
      </div>
    );
  }

  const b = current.budget;
  const gap = b.budget_vs_target;

  return (
    <div className="flex flex-col gap-8">
      <PageHeader
        eyebrow="Experiencias de vida"
        title={current.title}
        meta={
          <>
            {current.location && (
              <span className="flex items-center gap-2">
                <Icon icon="solar:map-point-linear" height={14} width={14} />
                {current.location}
              </span>
            )}
            {(current.experience_date || current.end_date) && (
              <span className="flex items-center gap-2">
                <Icon icon="solar:calendar-linear" height={14} width={14} />
                {fmtDate(current.experience_date ?? current.end_date)}
              </span>
            )}
          </>
        }
        actions={
          <>
            <BaseCurrencyBadge currency={base} />
            <Button onClick={() => setEditing('new')}>Añadir línea</Button>
          </>
        }
      />

      {data.experiences.length > 1 && (
        <div className="flex flex-wrap gap-2 border-b border-border pb-4">
          {data.experiences.map((exp) => (
            <button
              key={exp.id}
              type="button"
              onClick={() => setSelectedId(exp.id)}
              className={`border px-3.5 py-2 text-sm transition-colors ${
                exp.id === selectedId
                  ? 'border-primary text-primary'
                  : 'border-input text-inksoft hover:text-foreground'
              }`}
            >
              {exp.title}
            </button>
          ))}
        </div>
      )}

      {error && (
        <p className="border border-error/40 bg-lighterror p-3 text-sm text-error">{error}</p>
      )}

      {/* The two numbers, deliberately apart */}
      <div className="grid gap-10 border-y rule-strong border-b-border py-6 md:grid-cols-3">
        <div>
          <div className="eyebrow-sm mb-2.5">Meta de ahorro</div>
          <div className="fig text-[34px] font-medium">{fmtFigure(b.target_amount, base)}</div>
          <div className="mt-2 text-[13px] text-muted-foreground">Lo que decidiste ahorrar</div>
        </div>
        <div className="md:border-l md:border-border md:pl-10">
          <div className="eyebrow-sm mb-2.5">Presupuesto detallado</div>
          <div className="fig text-[34px] font-medium">{fmtFigure(b.estimated_total, base)}</div>
          <div className="mt-2 text-[13px] text-muted-foreground">Lo que suman tus líneas</div>
        </div>
        <div className="md:border-l md:border-border md:pl-10">
          <div className="eyebrow-sm mb-2.5">Diferencia</div>
          <div
            className={`fig text-[34px] font-medium ${gap > 0 ? 'text-error' : 'text-success'}`}
          >
            {gap > 0 ? '+' : gap < 0 ? '−' : ''}
            {fmtFigure(Math.abs(gap), base)}
          </div>
          <div className="mt-2 text-[13px] leading-relaxed text-inksoft">
            {gap > 0
              ? 'El plan cuesta más que la meta: es un plan con un hueco.'
              : gap < 0
                ? 'El plan cuesta menos que la meta. Con signo positivo, sería un plan con un hueco.'
                : 'El plan y la meta coinciden exactamente.'}
          </div>
        </div>
      </div>

      {/* Saving progress */}
      <div>
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <div className="fig text-[19px] font-medium">Progreso de ahorro</div>
          <div className="text-sm text-inksoft">
            <span className="fig text-[17px] text-foreground">
              {fmtFigure(b.saved_amount, base)}
            </span>{' '}
            ahorrados ·{' '}
            <span className="fig text-[17px] text-foreground">
              {fmtFigure(b.still_to_save, base)}
            </span>{' '}
            por reunir
          </div>
        </div>
        <div className="flex h-9 items-center border rule-strong bg-muted">
          <div
            className="flex h-full items-center bg-primary pl-3.5"
            style={{ width: `${Math.min(b.progress_percentage, 100)}%` }}
          >
            {b.progress_percentage >= 12 && (
              <span className="fig text-[15px] font-medium text-primary-foreground">
                {fmtPercent(b.progress_percentage, 0)}
              </span>
            )}
          </div>
          {b.progress_percentage < 12 && (
            <span className="fig ml-3.5 text-[15px] font-medium">
              {fmtPercent(b.progress_percentage, 0)}
            </span>
          )}
        </div>
      </div>

      {/* Budget lines */}
      <div>
        <div className="mb-1 flex flex-wrap items-baseline justify-between gap-2">
          <div className="fig text-[19px] font-medium">Líneas del presupuesto</div>
          <span className="text-[13px] text-muted-foreground">
            Cada línea guarda su moneda original; los totales se convierten a {base}.
          </span>
        </div>

        {items.length === 0 ? (
          <p className="border border-input bg-card p-6 text-sm text-inksoft">
            Sin líneas, el presupuesto de esta experiencia es cero y la diferencia contra la meta
            no dice nada. Añade lo que ya sabes que va a costar: vuelos, alojamiento, comida.
          </p>
        ) : (
          <>
            <div className={`${COLS} border-b rule-strong py-3`}>
              <span className="eyebrow-sm">Concepto</span>
              <span className="eyebrow-sm">Categoría</span>
              <span className="eyebrow-sm text-right">Estimado</span>
              <span className="eyebrow-sm text-right">En {base}</span>
              <span className="eyebrow-sm text-right">Estado</span>
              <span />
            </div>
            {items.map((item) => (
              <div key={item.id} className={`${COLS} border-b border-border py-4`}>
                <button
                  type="button"
                  onClick={() => setEditing(item)}
                  className="truncate text-left text-[15px] hover:text-primary"
                >
                  {item.label}
                </button>
                <span className="text-sm text-inksoft">
                  {budgetCategoryLabel(item.category)}
                </span>
                <span className="fig text-right text-base">
                  {fmtFigure(item.estimated_amount, item.currency)}{' '}
                  <span className="text-xs text-muted-foreground">{item.currency}</span>
                </span>
                <span className="fig text-right text-base">
                  {item.currency === base ? (
                    fmtFigure(item.estimated_amount, base)
                  ) : (
                    <span className="text-muted-foreground" title="Convertido en el total">
                      —
                    </span>
                  )}
                </span>
                <span className="text-right">
                  {item.is_booked ? (
                    <span className="border-b-2 border-success pb-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-success">
                      Reservado
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">Por reservar</span>
                  )}
                </span>
                <button
                  type="button"
                  onClick={() => removeItem(item)}
                  aria-label={`Eliminar ${item.label}`}
                  className="justify-self-end text-muted-foreground transition-colors hover:text-error"
                >
                  <Icon icon="solar:trash-bin-minimalistic-linear" height={16} width={16} />
                </button>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Category split + what is already locked in */}
      {b.by_category.length > 0 && (
        <div className="grid items-start gap-11 md:grid-cols-2">
          <div>
            <div className="fig mb-4 text-[19px] font-medium">Reparto del presupuesto</div>
            <div className="flex h-10 border rule-strong">
              {b.by_category.map((row, i) => (
                <div
                  key={row.category}
                  className={SPLIT_TONES[i % SPLIT_TONES.length]}
                  style={{ width: `${row.percentage}%` }}
                  title={`${budgetCategoryLabel(row.category)} · ${fmtPercent(row.percentage, 2)}`}
                />
              ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
              {b.by_category.map((row, i) => (
                <div key={row.category} className="flex items-center gap-2.5">
                  <span className={`h-3 w-3 ${SPLIT_TONES[i % SPLIT_TONES.length]}`} />
                  <span className="text-[13px]">{budgetCategoryLabel(row.category)}</span>
                  <span className="text-xs text-muted-foreground">
                    {fmtPercent(row.percentage, 2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="md:border-l md:border-border md:pl-11">
            <div className="fig mb-4 text-[19px] font-medium">Reservado hasta ahora</div>
            <div className="fig text-[30px] font-medium">
              {fmtFigure(b.booked_total, base)}{' '}
              <span className="text-base text-muted-foreground">
                de {fmtFigure(b.estimated_total, base)}
              </span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-inksoft">
              Una línea reservada ya está pagada: su precio no se moverá. El resto sigue expuesto
              al cambio de tarifas y al tipo de cambio.
            </p>
          </div>
        </div>
      )}

      {editing && (
        <BudgetItemForm
          item={editing === 'new' ? null : editing}
          goalId={current.id}
          goalTitle={current.title}
          baseCurrency={base}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await reload();
          }}
        />
      )}
    </div>
  );
}
