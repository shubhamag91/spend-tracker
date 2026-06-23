import { useState } from 'react';
import { useMode } from '../store/demoMode';
import {
  useSubscriptionSummary, useSubscriptionRules,
  useCreateSubscriptionRule, useDeleteSubscriptionRule,
} from '../hooks/useSubscriptions';
import { formatCurrency, formatDate } from '../utils/formatters';
import LoadingSpinner from '../components/shared/LoadingSpinner';

const TYPE_COLORS: Record<string, string> = {
  OTT: 'bg-rose-100 text-rose-700',
  AI: 'bg-indigo-100 text-indigo-700',
  Music: 'bg-emerald-100 text-emerald-700',
  Productivity: 'bg-amber-100 text-amber-700',
  Cloud: 'bg-sky-100 text-sky-700',
  Other: 'bg-slate-100 text-slate-600',
};

function typeClass(t: string) { return TYPE_COLORS[t] ?? TYPE_COLORS.Other; }

export default function Subscriptions() {
  const mode = useMode();
  const { data: summary, isLoading } = useSubscriptionSummary(mode);
  const { data: rules } = useSubscriptionRules();
  const createRule = useCreateSubscriptionRule();
  const deleteRule = useDeleteSubscriptionRule();
  const [form, setForm] = useState({ name: '', keyword: '', type: 'OTT' });

  function addRule(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.keyword.trim()) return;
    createRule.mutate(
      { name: form.name.trim(), keyword: form.keyword.trim(), type: form.type },
      { onSuccess: () => setForm({ name: '', keyword: '', type: form.type }) },
    );
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><LoadingSpinner size="lg" /></div>;
  }

  const items = summary?.items ?? [];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Subscriptions</h1>
        <p className="text-sm text-slate-400 mt-0.5">Recurring services detected by name — OTT, AI, and more.</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Services</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{summary?.service_count ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Total in this period</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{formatCurrency(summary?.total ?? 0)}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Types</p>
          <div className="flex flex-wrap gap-1.5 mt-2">
            {(summary?.by_type ?? []).map((b) => (
              <span key={b.type} className={`text-xs font-medium px-2 py-0.5 rounded-full ${typeClass(b.type)}`}>
                {b.type} · {formatCurrency(b.total)}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: detected subscriptions */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">Your subscriptions</h2>
          </div>
          {items.length === 0 ? (
            <div className="h-40 flex items-center justify-center text-slate-400 text-sm text-center px-6">
              No subscriptions detected in this period. Add a service on the right if one's missing.
            </div>
          ) : (
            <table className="w-full text-sm">
              <tbody className="divide-y divide-slate-100">
                {items.map((it) => (
                  <tr key={it.name} className="hover:bg-slate-50">
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-800">{it.name}</span>
                        <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${typeClass(it.type)}`}>{it.type}</span>
                      </div>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {it.count}× · last {it.last_date ? formatDate(it.last_date) : '—'}
                      </p>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <span className="font-semibold text-slate-800">{formatCurrency(it.amount)}</span>
                      <p className="text-xs text-slate-400">latest charge</p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Right: rules manager */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 h-fit">
          <h2 className="font-semibold text-slate-800">Tracked services</h2>
          <p className="text-xs text-slate-400 mt-0.5 mb-3">Any transaction whose description contains a keyword is counted as that subscription. Comes with common services pre-loaded.</p>
          <form onSubmit={addRule} className="space-y-2 mb-3">
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Display name (e.g. Hotstar)"
              className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
            />
            <div className="flex gap-2">
              <input
                value={form.keyword}
                onChange={(e) => setForm({ ...form, keyword: e.target.value })}
                placeholder="Keyword (e.g. HOTSTAR)"
                className="flex-1 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
              />
              <select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
                className="border border-slate-200 rounded-lg px-2 py-1.5 text-sm bg-white"
              >
                {['OTT', 'AI', 'Music', 'Productivity', 'Cloud', 'Other'].map((t) => <option key={t}>{t}</option>)}
              </select>
            </div>
            <button type="submit" disabled={createRule.isPending} className="w-full px-3 py-1.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50">Add service</button>
          </form>
          {createRule.isError && <p className="text-xs text-red-600 mb-2">Couldn't add — that keyword may already exist.</p>}
          <div className="space-y-1.5 max-h-96 overflow-y-auto">
            {(rules ?? []).map((r) => (
              <div key={r.id} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-1.5">
                <div className="min-w-0">
                  <span className="text-sm font-medium text-slate-700">{r.name}</span>
                  <span className="text-xs text-slate-400 ml-2">{r.keyword}</span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${typeClass(r.type)}`}>{r.type}</span>
                  <button onClick={() => deleteRule.mutate(r.id)} className="text-slate-400 hover:text-red-600 text-sm" title="Remove">&times;</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
