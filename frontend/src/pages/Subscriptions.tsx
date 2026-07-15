import { useState } from 'react';
import { useMode } from '../store/demoMode';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useSubscriptionSummary, useSubscriptionMonthly } from '../hooks/useSubscriptions';
import { useCashExpenses, useCreateCashExpense, useDeleteCashExpense } from '../hooks/useCashExpenses';
import DateRangeFilter, { type DateRange, DEFAULT_RANGE } from '../components/dashboard/DateRangeFilter';
import { formatCurrency, formatDate } from '../utils/formatters';
import LoadingSpinner from '../components/shared/LoadingSpinner';

function compactInr(v: number) {
  if (!Number.isFinite(v)) return '₹0';
  const a = Math.abs(v);
  if (a >= 1e7) return `₹${(a / 1e7).toFixed(1)}Cr`;
  if (a >= 1e5) return `₹${(a / 1e5).toFixed(1)}L`;
  if (a >= 1e3) return `₹${Math.round(a / 1e3)}k`;
  return `₹${Math.round(a)}`;
}

const FixedTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const types = Object.entries(p.by_type || {}).filter(([, v]) => (v as number) > 0);
  return (
    <div className="bg-white border border-slate-100 rounded-xl px-4 py-3 shadow-lg text-sm">
      <p className="font-semibold text-slate-700 mb-1.5">{label} · {formatCurrency(p.total)}</p>
      {types.map(([t, v]) => (
        <div key={t} className="flex items-center justify-between gap-6 text-xs">
          <span className="text-slate-500">{t}</span>
          <span className="font-medium text-slate-700">{formatCurrency(v as number)}</span>
        </div>
      ))}
    </div>
  );
};

const TYPE_COLORS: Record<string, string> = {
  Rent: 'bg-purple-100 text-purple-700',
  Electricity: 'bg-yellow-100 text-yellow-700',
  Phone: 'bg-blue-100 text-blue-700',
  Internet: 'bg-cyan-100 text-cyan-700',
  Utilities: 'bg-cyan-100 text-cyan-700',
  Insurance: 'bg-teal-100 text-teal-700',
  EMI: 'bg-orange-100 text-orange-700',
  Loan: 'bg-orange-100 text-orange-700',
  Staff: 'bg-lime-100 text-lime-700',
  Maintenance: 'bg-stone-100 text-stone-700',
  OTT: 'bg-rose-100 text-rose-700',
  AI: 'bg-indigo-100 text-indigo-700',
  Music: 'bg-emerald-100 text-emerald-700',
  Productivity: 'bg-amber-100 text-amber-700',
  Cloud: 'bg-sky-100 text-sky-700',
  Other: 'bg-slate-100 text-slate-600',
};

const TYPE_SUGGESTIONS = ['Rent', 'Electricity', 'Internet', 'Phone', 'Utilities', 'Insurance', 'EMI', 'Loan', 'Staff', 'Maintenance', 'OTT', 'AI', 'Music', 'Productivity', 'Cloud', 'Other'];

function typeClass(t: string) { return TYPE_COLORS[t] ?? TYPE_COLORS.Other; }

export default function Subscriptions() {
  const mode = useMode();
  const [range, setRange] = useState<DateRange>(DEFAULT_RANGE);
  const dateRange = range.start ? { start: range.start, end: range.end } : undefined;
  const { data: summary, isLoading } = useSubscriptionSummary(mode, dateRange);
  const { data: monthly } = useSubscriptionMonthly(mode, dateRange);

  const { data: cashExpenses } = useCashExpenses();
  const createCash = useCreateCashExpense();
  const deleteCash = useDeleteCashExpense();
  const [cashForm, setCashForm] = useState({ name: '', amount: '', day: '1', type: 'Staff' });

  function addCash(e: React.FormEvent) {
    e.preventDefault();
    if (!cashForm.name.trim() || !cashForm.amount) return;
    createCash.mutate(
      { name: cashForm.name.trim(), amount: Number(cashForm.amount), day_of_month: Number(cashForm.day) || 1, type: cashForm.type.trim() || 'Cash' },
      { onSuccess: () => setCashForm({ ...cashForm, name: '', amount: '' }) },
    );
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><LoadingSpinner size="lg" /></div>;
  }

  const items = summary?.items ?? [];

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Fixed Spends</h1>
          <p className="text-sm text-slate-400 mt-0.5">Your recurring monthly commitments — rent, bills, EMIs, subscriptions — each normalised to a monthly cost.</p>
        </div>
        <DateRangeFilter selected={range} onChange={setRange} />
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Per month</p>
          <p className="text-2xl font-bold text-indigo-700 mt-1">{formatCurrency(summary?.monthly_total ?? 0)}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">normalised by each item's frequency</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Fixed charges</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{summary?.service_count ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wide">By type (per month)</p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {(summary?.by_type ?? []).map((b) => (
              <span key={b.type} className={`text-xs font-medium px-2 py-0.5 rounded-full ${typeClass(b.type)}`}>
                {b.type} · {formatCurrency(b.monthly)}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Month by month — the ACTUAL fixed spend paid each month (it varies) */}
      {monthly && monthly.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Month by month
            <span className="text-xs font-normal text-slate-400"> · actual fixed spend paid (hover for the breakdown)</span>
          </h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={monthly} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e2940" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tickFormatter={compactInr} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={52} />
              <Tooltip content={<FixedTooltip />} cursor={{ fill: '#1e2940' }} />
              <Bar dataKey="total" fill="#6d6af0" radius={[3, 3, 0, 0]} maxBarSize={56} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: detected items */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">Your fixed spends</h2>
          </div>
          {items.length === 0 ? (
            <div className="h-40 flex items-center justify-center text-slate-400 text-sm text-center px-6">
              Nothing detected in this period.
            </div>
          ) : (
            <table className="w-full text-sm">
              <tbody>
                {items.map((it) => (
                  <tr key={it.name} className="hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-800">{it.name}</span>
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${typeClass(it.type)}`}>{it.type}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {it.frequency} · {it.count}× · last {it.last_date ? formatDate(it.last_date) : '—'}
                      </p>
                    </td>
                    <td className="px-5 py-3 text-right whitespace-nowrap">
                      <span className="font-semibold text-slate-800">{formatCurrency(it.monthly)}</span>
                      <span className="text-slate-400">/mo</span>
                      {it.frequency !== 'monthly' && (
                        <p className="text-xs text-slate-400">{formatCurrency(it.amount)} charge</p>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Right: managers */}
        <div className="space-y-5 h-fit">
        <datalist id="fixed-types">
          {TYPE_SUGGESTIONS.map((t) => <option key={t} value={t} />)}
        </datalist>

        {/* Cash expenses — recurring spends that never hit a statement (cook, maid…) */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-800">Cash expenses</h2>
          <p className="text-xs text-slate-400 mt-0.5 mb-3">Recurring cash payments that never appear on a statement (cook, maid, driver…). Each one auto-adds a monthly entry to spend &amp; the list above — no manual entry.</p>
          <form onSubmit={addCash} className="space-y-2 mb-3">
            <input
              value={cashForm.name}
              onChange={(e) => setCashForm({ ...cashForm, name: e.target.value })}
              placeholder="Name (e.g. House cook)"
              className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
            />
            <div className="flex gap-2">
              <input
                type="number"
                value={cashForm.amount}
                onChange={(e) => setCashForm({ ...cashForm, amount: e.target.value })}
                placeholder="₹ / month"
                className="flex-1 min-w-0 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
              />
              <input
                list="fixed-types"
                value={cashForm.type}
                onChange={(e) => setCashForm({ ...cashForm, type: e.target.value })}
                placeholder="Type"
                className="w-24 min-w-0 border border-slate-200 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
              />
              <input
                type="number" min="1" max="28"
                value={cashForm.day}
                onChange={(e) => setCashForm({ ...cashForm, day: e.target.value })}
                title="Day of month it's paid"
                className="w-16 min-w-0 border border-slate-200 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
              />
            </div>
            <button type="submit" disabled={createCash.isPending} className="w-full px-3 py-1.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50">Add cash expense</button>
          </form>
          <div className="space-y-1.5">
            {(cashExpenses ?? []).length === 0 && <p className="text-sm text-slate-400">None yet.</p>}
            {(cashExpenses ?? []).map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-2 bg-slate-50 rounded-lg px-3 py-1.5">
                <div className="min-w-0">
                  <span className="text-sm font-medium text-slate-700 truncate">{c.name}</span>
                  <span className="text-xs text-slate-400 ml-1.5">{formatCurrency(c.amount)}/mo · day {c.day_of_month}</span>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${typeClass(c.type)}`}>{c.type}</span>
                  <button
                    onClick={() => { if (window.confirm(`Remove "${c.name}"? Its generated monthly entries will be deleted too.`)) deleteCash.mutate(c.id); }}
                    className="text-slate-400 hover:text-red-600 text-sm" title="Remove (deletes its generated entries)"
                  >&times;</button>
                </div>
              </div>
            ))}
          </div>
        </div>
        </div>
      </div>
    </div>
  );
}
