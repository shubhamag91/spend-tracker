import { useState } from 'react';
import { useMode } from '../store/demoMode';
import {
  useSubscriptionSummary, useSubscriptionRules,
  useCreateSubscriptionRule, useUpdateSubscriptionRule, useDeleteSubscriptionRule,
} from '../hooks/useSubscriptions';
import { useCashExpenses, useCreateCashExpense, useDeleteCashExpense } from '../hooks/useCashExpenses';
import { formatCurrency, formatDate } from '../utils/formatters';
import LoadingSpinner from '../components/shared/LoadingSpinner';

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
const FREQUENCIES = ['monthly', 'quarterly', 'half-yearly', 'yearly', 'weekly', 'variable'];

function typeClass(t: string) { return TYPE_COLORS[t] ?? TYPE_COLORS.Other; }

export default function Subscriptions() {
  const mode = useMode();
  const { data: summary, isLoading } = useSubscriptionSummary(mode);
  const { data: rules } = useSubscriptionRules();
  const createRule = useCreateSubscriptionRule();
  const updateRule = useUpdateSubscriptionRule();
  const deleteRule = useDeleteSubscriptionRule();
  const [form, setForm] = useState({ name: '', keyword: '', type: 'Rent', frequency: 'monthly', minAmount: '', monthlyAmount: '' });

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

  function addRule(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.keyword.trim()) return;
    createRule.mutate(
      {
        name: form.name.trim(), keyword: form.keyword.trim(), type: form.type, frequency: form.frequency,
        min_amount: form.minAmount ? Number(form.minAmount) : null,
        monthly_amount: form.monthlyAmount ? Number(form.monthlyAmount) : null,
      },
      { onSuccess: () => setForm({ ...form, name: '', keyword: '', minAmount: '', monthlyAmount: '' }) },
    );
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><LoadingSpinner size="lg" /></div>;
  }

  const items = summary?.items ?? [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Fixed Spends</h1>
        <p className="text-sm text-slate-400 mt-0.5">Your recurring monthly commitments — rent, bills, EMIs, subscriptions — each normalised to a monthly cost.</p>
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: detected items */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">Your fixed spends</h2>
          </div>
          {items.length === 0 ? (
            <div className="h-40 flex items-center justify-center text-slate-400 text-sm text-center px-6">
              Nothing detected in this period. Add a rule on the right — e.g. your landlord's name as "Rent".
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
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-800">Tracked items</h2>
          <p className="text-xs text-slate-400 mt-0.5 mb-3">Any transaction whose description contains the keyword is counted here. Pick its billing frequency so the monthly cost is right (e.g. a 3-month broadband plan = quarterly).</p>
          <form onSubmit={addRule} className="space-y-2 mb-3">
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Display name (e.g. Flat rent)"
              className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
            />
            <input
              value={form.keyword}
              onChange={(e) => setForm({ ...form, keyword: e.target.value })}
              placeholder="Keyword (e.g. landlord name)"
              className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
            />
            <div className="flex gap-2">
              <input
                list="fixed-types"
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
                placeholder="Type"
                className="flex-1 min-w-0 border border-slate-200 rounded-lg px-2 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
              />
              <datalist id="fixed-types">
                {TYPE_SUGGESTIONS.map((t) => <option key={t} value={t} />)}
              </datalist>
              <select
                value={form.frequency}
                onChange={(e) => setForm({ ...form, frequency: e.target.value })}
                className="border border-slate-200 rounded-lg px-2 py-1.5 text-sm bg-white"
              >
                {FREQUENCIES.map((f) => <option key={f} value={f}>{f}</option>)}
              </select>
            </div>
            <div className="flex gap-2">
              <input
                type="number"
                value={form.minAmount}
                onChange={(e) => setForm({ ...form, minAmount: e.target.value })}
                placeholder="Min ₹ (optional)"
                title="Only count charges at or above this amount — separates a big bill from small ones to the same payee"
                className="flex-1 min-w-0 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
              />
              <input
                type="number"
                value={form.monthlyAmount}
                onChange={(e) => setForm({ ...form, monthlyAmount: e.target.value })}
                placeholder="₹/mo override"
                title="Set the true monthly cost — useful for lump-sum prepaids (e.g. ₹20,007 recharge that's really ₹5,200/mo)"
                className="flex-1 min-w-0 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
              />
            </div>
            <button type="submit" disabled={createRule.isPending} className="w-full px-3 py-1.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50">Add item</button>
          </form>
          {createRule.isError && <p className="text-xs text-red-600 mb-2">Couldn't add — that keyword may already exist.</p>}
          <div className="space-y-1.5 max-h-[28rem] overflow-y-auto">
            {(rules ?? []).map((r) => (
              <div key={r.id} className="flex items-center justify-between gap-2 bg-slate-50 rounded-lg px-3 py-1.5">
                <div className="min-w-0">
                  <span className="text-sm font-medium text-slate-700 truncate">{r.name}</span>
                  <span className="text-xs text-slate-400 ml-1.5">{r.keyword}</span>
                  {r.min_amount != null && <span className="text-[10px] text-slate-400 ml-1">≥ ₹{r.min_amount.toLocaleString('en-IN')}</span>}
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${typeClass(r.type)}`}>{r.type}</span>
                  <select
                    value={r.frequency}
                    onChange={(e) => updateRule.mutate({ id: r.id, frequency: e.target.value })}
                    className="text-[11px] border border-slate-200 rounded px-1 py-0.5 bg-white text-slate-600"
                    title="Billing frequency"
                  >
                    {FREQUENCIES.map((f) => <option key={f} value={f}>{f}</option>)}
                  </select>
                  <button onClick={() => deleteRule.mutate(r.id)} className="text-slate-400 hover:text-red-600 text-sm" title="Remove">&times;</button>
                </div>
              </div>
            ))}
          </div>
        </div>

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
