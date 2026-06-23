import { useState } from 'react';
import { useMode } from '../store/demoMode';
import {
  useInvestmentSummary, useInvestmentRules,
  useCreateInvestmentRule, useDeleteInvestmentRule, useSetInvestment,
} from '../hooks/useInvestments';
import { useSelectedAccountId } from '../store/selectedAccount';
import { useTransactions } from '../hooks/useTransactions';
import { formatCurrency, formatDate } from '../utils/formatters';
import LoadingSpinner from '../components/shared/LoadingSpinner';

export default function Investments() {
  const mode = useMode();
  const accountId = useSelectedAccountId();
  const { data: summary, isLoading } = useInvestmentSummary(mode);
  const { data: rules } = useInvestmentRules();
  const createRule = useCreateInvestmentRule();
  const deleteRule = useDeleteInvestmentRule();
  const setInvestment = useSetInvestment();
  const [keyword, setKeyword] = useState('');
  const [label, setLabel] = useState('');
  const [rulesOpen, setRulesOpen] = useState(false);  // collapsed by default — guards against accidental edits
  const [page, setPage] = useState(1);

  const { data: txns } = useTransactions({
    mode, account_id: accountId, is_investment: true,
    sort_by: 'amount', sort_dir: 'desc', page, page_size: 25,
  });

  function addRule(e: React.FormEvent) {
    e.preventDefault();
    const k = keyword.trim();
    if (!k) return;
    createRule.mutate(
      { keyword: k, label: label.trim() || undefined },
      { onSuccess: () => { setKeyword(''); setLabel(''); } },
    );
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><LoadingSpinner size="lg" /></div>;
  }

  const platforms = summary?.by_platform ?? [];
  const maxTotal = platforms[0]?.total ?? 1;

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Investments</h1>
        <p className="text-sm text-slate-400 mt-0.5">Tracked separately from spend — money moved into investments, not consumed.</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Total invested</p>
          <p className="text-2xl font-bold text-indigo-700 mt-1">{formatCurrency(summary?.total_invested ?? 0)}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Transactions</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{summary?.count ?? 0}</p>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <p className="text-xs text-slate-400 uppercase tracking-wide">Platforms</p>
          <p className="text-2xl font-bold text-slate-800 mt-1">{platforms.length}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: by-platform + transactions */}
        <div className="lg:col-span-2 space-y-5">
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-800 mb-3">By platform</h2>
            {platforms.length === 0 ? (
              <p className="text-sm text-slate-400">No investments tagged yet. Add a rule on the right, or mark a transaction as investment.</p>
            ) : (
              <div className="space-y-2.5">
                {platforms.map((p) => (
                  <div key={p.name}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-700 font-medium">{p.name} <span className="text-slate-400 font-normal">· {p.count}×</span></span>
                      <span className="text-slate-800 font-semibold">{formatCurrency(p.total)}</span>
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${(p.total / maxTotal) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-800">Investment transactions</h2>
              <div className="flex items-center gap-2 text-xs">
                <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="px-2 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50">Prev</button>
                <span className="text-slate-500">{page} / {txns?.total_pages ?? 1}</span>
                <button disabled={page >= (txns?.total_pages ?? 1)} onClick={() => setPage(page + 1)} className="px-2 py-1 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50">Next</button>
              </div>
            </div>
            {(txns?.items.length ?? 0) === 0 ? (
              <div className="h-32 flex items-center justify-center text-slate-400 text-sm">No investment transactions</div>
            ) : (
              <table className="w-full text-sm">
                <tbody className="divide-y divide-slate-100">
                  {txns?.items.map((t) => (
                    <tr key={t.id} className="hover:bg-slate-50">
                      <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">{formatDate(t.date)}</td>
                      <td className="px-4 py-2.5 text-slate-700 max-w-xs truncate">{t.description}</td>
                      <td className="px-4 py-2.5 text-right font-medium text-indigo-700 whitespace-nowrap">{formatCurrency(t.amount)}</td>
                      <td className="px-4 py-2.5 text-right">
                        <button
                          onClick={() => setInvestment.mutate({ txnId: t.id, value: false })}
                          className="text-xs text-slate-400 hover:text-red-600"
                          title="Move back to spend"
                        >
                          Unmark
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Right: rules manager — collapsed by default so rules aren't deleted by mistake */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 h-fit">
          <button onClick={() => setRulesOpen((o) => !o)} className="w-full flex items-center justify-between text-left">
            <h2 className="font-semibold text-slate-800">Investment payee rules</h2>
            <span className="text-xs text-slate-400 flex items-center gap-1">
              {(rules ?? []).length} active · {rulesOpen ? 'done' : 'manage'} <span className="text-[10px]">{rulesOpen ? '▲' : '▾'}</span>
            </span>
          </button>
          {!rulesOpen ? (
            <p className="text-xs text-slate-400 mt-1.5">Auto-classifying matching transactions as investments. Click <span className="font-medium">manage</span> to add or edit.</p>
          ) : (
            <>
              <p className="text-xs text-slate-400 mt-1 mb-3">Any bank transaction whose description contains a keyword is counted as an investment, not spend — for existing and future imports. The optional label is how the platform shows in the breakdown (e.g. keyword INGENICO → label Grip).</p>
              <form onSubmit={addRule} className="flex gap-2 mb-3">
                <input
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="Keyword (e.g. LENDBOX)"
                  className="flex-1 min-w-0 border border-slate-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
                />
                <input
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder="Label (optional)"
                  className="w-28 min-w-0 border border-slate-200 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
                />
                <button type="submit" disabled={createRule.isPending} className="px-3 py-1.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50">Add</button>
              </form>
              {createRule.isError && <p className="text-xs text-red-600 mb-2">Couldn't add — maybe it already exists.</p>}
              <div className="space-y-1.5">
                {(rules ?? []).length === 0 && <p className="text-sm text-slate-400">No rules yet.</p>}
                {(rules ?? []).map((r) => (
                  <div key={r.id} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-1.5">
                    <span className="text-sm font-medium text-slate-700">{r.keyword}{r.label && <span className="text-xs text-slate-400 font-normal ml-1.5">→ {r.label}</span>}</span>
                    <button
                      onClick={() => { if (window.confirm(`Remove the "${r.keyword}" investment rule?\n\nExisting tagged transactions stay tagged, but future imports of this payee won't be auto-classified.`)) deleteRule.mutate(r.id); }}
                      className="text-slate-400 hover:text-red-600 text-sm"
                      title="Remove rule (keeps existing tags)"
                    >&times;</button>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-slate-400 mt-3">Removing a rule keeps already-tagged transactions tagged. Use "Unmark" on a row to move one back to spend.</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
