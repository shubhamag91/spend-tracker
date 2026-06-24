import { useState } from 'react';
import { useMode } from '../store/demoMode';
import { useDemoModeStore } from '../store/demoMode';
import {
  useSummary, useWallet, useByDay, useByCategory, useInsights,
  useWeeklyVelocity, useHeatmap, useTopMerchants, useRecurring,
} from '../hooks/useAnalytics';
import DateRangeFilter, { type DateRange, PRESETS } from '../components/dashboard/DateRangeFilter';
import AccountFreshness from '../components/dashboard/AccountFreshness';
import FileUploadModal from '../components/upload/FileUploadModal';
import { formatCurrency } from '../utils/formatters';
import { format, parseISO } from 'date-fns';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAYS_FULL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

const CAT_EMOJI: Record<string, string> = {
  Food: '🍕', Transport: '🚗', Groceries: '🛒', Shopping: '🛍️',
  Utilities: '⚡', Health: '💊', Entertainment: '🎬', Travel: '✈️',
};
const emoji = (c: string) => CAT_EMOJI[c] ?? '💰';

export default function Dashboard() {
  const mode = useMode();
  const isDemoMode = useDemoModeStore((s) => s.isDemoMode);
  const [range, setRange] = useState<DateRange>(PRESETS[0]);
  const [tab, setTab] = useState<'overview' | 'patterns'>('overview');
  const [showUpload, setShowUpload] = useState(false);
  const dateRange = range.start ? { start: range.start, end: range.end } : undefined;

  const summary = useSummary(mode, dateRange);
  const wallet = useWallet(mode, dateRange);
  const allDays = useByDay(mode);
  const byCategory = useByCategory(mode, dateRange);
  const insights = useInsights(mode, dateRange);
  const velocity = useWeeklyVelocity(mode, dateRange);
  const heatmap = useHeatmap(mode);
  const merchants = useTopMerchants(mode, dateRange);
  const recurring = useRecurring(mode);

  const dataBounds = allDays.data?.length
    ? { min: allDays.data[0].label, max: allDays.data[allDays.data.length - 1].label }
    : undefined;

  // Wallet model: money loaded → invested + spent + unspent
  const w = wallet.data;
  const loaded = w?.loaded ?? 0;
  const invested = w?.invested ?? 0;
  const spent = w?.spent ?? 0;
  const unspent = Math.max(0, w?.unspent ?? 0);
  const pctOfLoaded = (v: number) => (loaded > 0 ? Math.round((v / loaded) * 100) : 0);
  const invPct = pctOfLoaded(invested);
  const spentPct = pctOfLoaded(spent);
  const unspentPct = Math.max(0, 100 - invPct - spentPct);

  // Nothing in the selected period → collapse to a single empty state, no tabs
  const empty = !summary.isLoading && (summary.data?.transaction_count ?? 0) === 0;

  // Period labels — reflect the actual data window, not arbitrary calendar ranges
  const periodLabel = range.label;
  const fday = (s: string) => format(parseISO(s), 'd MMM yyyy');
  const dataLabel = dataBounds ? `${fday(dataBounds.min)} – ${fday(dataBounds.max)}` : '';
  // the window actually on screen, clamped to where data exists
  let shownLabel = dataLabel;
  if (dataBounds) {
    const lo = range.start && range.start > dataBounds.min ? range.start : dataBounds.min;
    const hi = range.end && range.end < dataBounds.max ? range.end : dataBounds.max;
    shownLabel = lo <= hi ? `${fday(lo)} – ${fday(hi)}` : '';
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Overview</h1>
          <p className="text-sm text-slate-400 mt-0.5 flex items-center gap-1.5">
            {dataBounds ? (
              <>
                <svg className="w-3.5 h-3.5 text-slate-300" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" strokeLinecap="round" />
                </svg>
                {empty ? `Data available ${dataLabel}` : `Showing ${shownLabel}`}
                {isDemoMode && <span className="ml-1 text-indigo-400">· demo</span>}
              </>
            ) : (
              isDemoMode ? 'Viewing demo data' : 'Your money at a glance'
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <DateRangeFilter selected={range} onChange={setRange} dataBounds={dataBounds} />
          {!isDemoMode && (
            <button
              onClick={() => setShowUpload(true)}
              className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white text-sm font-medium rounded-xl hover:bg-slate-800 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Import
            </button>
          )}
        </div>
      </div>

      {empty ? (
        <div className="bg-white rounded-2xl border border-slate-100 p-16 text-center">
          <div className="w-12 h-12 rounded-2xl bg-slate-50 flex items-center justify-center mx-auto mb-4 text-2xl">📭</div>
          <p className="text-base font-semibold text-slate-700">No transactions in {periodLabel}</p>
          <p className="text-sm text-slate-400 mt-1">
            {dataBounds
              ? `Your data covers ${dataLabel}. Try a different range.`
              : 'Import a bank statement to get started.'}
          </p>
        </div>
      ) : (
      <>
      {/* Hero — the wallet story: loaded → invested + spent + unspent */}
      <div className="bg-white rounded-3xl border border-slate-100 p-7 shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="text-slate-400 text-sm font-medium">You spent</p>
            <p className="text-4xl font-bold tracking-tight mt-1 text-slate-900">{formatCurrency(spent)}</p>
            <p className="text-slate-400 text-sm mt-2">
              of {formatCurrency(loaded)} loaded
              {invested > 0 && <span className="text-slate-600 font-medium"> · {formatCurrency(invested)} invested</span>}
            </p>
          </div>
          <div className="text-right">
            <p className="text-slate-400 text-sm font-medium">Unspent in wallet</p>
            <p className="text-3xl font-bold tracking-tight mt-1 text-slate-900">{formatCurrency(unspent)}</p>
          </div>
        </div>
        {/* where the loaded money went: invested / spent / unspent */}
        <div className="mt-6">
          <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden flex">
            <div className="h-full bg-indigo-400/80 transition-all" style={{ width: `${invPct}%` }} title="Invested" />
            <div className="h-full bg-slate-400 transition-all" style={{ width: `${spentPct}%` }} title="Spent" />
            <div className="h-full bg-slate-600 transition-all" style={{ width: `${unspentPct}%` }} title="Unspent" />
          </div>
          <div className="flex flex-wrap gap-x-5 gap-y-1 mt-2.5 text-xs text-slate-400">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-indigo-400/80 inline-block" />Invested {invPct}%</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-slate-400 inline-block" />Spent {spentPct}%</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-slate-600 inline-block" />Unspent {unspentPct}%</span>
          </div>
        </div>
      </div>

      {/* Slim KPI strip — supporting context */}
      <div className="grid grid-cols-3 gap-4">
        <Stat label="Daily spend" value={formatCurrency(summary.data?.daily_average ?? 0)} />
        <Stat label="Spend txns" value={String(summary.data?.transaction_count ?? 0)} />
        <Stat label="Top category" value={summary.data?.top_category ?? '—'} emoji={summary.data?.top_category ? emoji(summary.data.top_category) : undefined} />
      </div>

      {/* Per-account data freshness — which statement to pull next */}
      <AccountFreshness />

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-100">
        <Tab active={tab === 'overview'} onClick={() => setTab('overview')}>Overview</Tab>
        <Tab active={tab === 'patterns'} onClick={() => setTab('patterns')}>Patterns &amp; Trends</Tab>
      </div>

      {tab === 'overview' ? (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          {/* Spend by category — the main visual */}
          <div className="lg:col-span-3 bg-white rounded-2xl border border-slate-100 p-6">
            <h3 className="text-base font-semibold text-slate-900 mb-5">Where your money went</h3>
            {byCategory.isLoading ? (
              <Loading />
            ) : !byCategory.data?.length ? (
              <Empty />
            ) : (
              <div className="space-y-1">
                {byCategory.data.slice(0, 6).map((cat) => (
                  <div key={cat.category} className="flex items-center gap-3 py-2.5">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 text-lg" style={{ background: `${cat.color}15` }}>
                      {emoji(cat.category)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-medium text-slate-800">{cat.category}</span>
                        <span className="text-sm font-semibold text-slate-900">{formatCurrency(cat.total)}</span>
                      </div>
                      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${cat.percentage}%`, background: cat.color }} />
                      </div>
                    </div>
                    <span className="text-xs text-slate-400 w-9 text-right flex-shrink-0">{cat.percentage}%</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Insights — compact, max 3 */}
          <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-100 p-6">
            <h3 className="text-base font-semibold text-slate-900 mb-5">Insights</h3>
            {insights.isLoading ? (
              <Loading />
            ) : !insights.data?.length ? (
              <Empty msg="No insights yet" />
            ) : (
              <div className="space-y-3">
                {insights.data.slice(0, 3).map((item, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="w-1 rounded-full flex-shrink-0" style={{ background: INSIGHT_COLOR[item.type] ?? '#cbd5e1' }} />
                    <div>
                      <p className="text-sm font-medium text-slate-800">{item.title}</p>
                      <p className="text-xs text-slate-500 leading-relaxed mt-0.5">{item.body}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          {/* Weekly velocity */}
          <div className="bg-white rounded-2xl border border-slate-100 p-6">
            <h3 className="text-base font-semibold text-slate-900 mb-1">Weekly spend</h3>
            <p className="text-sm text-slate-400 mb-5">How your pace changed week to week</p>
            {velocity.isLoading ? <Loading /> : !velocity.data?.length ? <Empty /> : (
              <div className="space-y-3">
                {velocity.data.map((w) => {
                  const maxTotal = Math.max(...(velocity.data?.map(x => x.total) ?? [1]));
                  const pct = Math.round((w.total / maxTotal) * 100);
                  return (
                    <div key={w.week_label} className="flex items-center gap-3">
                      <span className="text-xs text-slate-400 w-14 flex-shrink-0">{w.week_label}</span>
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: w.change_pct && w.change_pct > 40 ? '#fb7185' : '#818cf8' }} />
                      </div>
                      <span className="text-sm font-medium text-slate-700 w-20 text-right">{formatCurrency(w.total)}</span>
                      {w.change_pct !== null && (
                        <span className={`text-xs font-medium w-12 text-right ${w.change_pct > 0 ? 'text-rose-400' : 'text-emerald-500'}`}>
                          {w.change_pct > 0 ? '↑' : '↓'}{Math.abs(w.change_pct)}%
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Heatmap — compact, colour-only (no number wall) */}
          <div className="bg-white rounded-2xl border border-slate-100 p-6">
            <h3 className="text-base font-semibold text-slate-900 mb-1">When you spend</h3>
            <p className="text-sm text-slate-400 mb-5">Average spend by day of week</p>
            {heatmap.isLoading ? <Loading /> : !heatmap.data?.length ? <Empty /> : (
              <Heatmap data={heatmap.data} />
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Top merchants */}
            <div className="bg-white rounded-2xl border border-slate-100 p-6">
              <h3 className="text-base font-semibold text-slate-900 mb-5">Top merchants</h3>
              {merchants.isLoading ? <Loading /> : !merchants.data?.length ? <Empty /> : (
                <div className="space-y-1">
                  {merchants.data.slice(0, 5).map((m, i) => (
                    <div key={m.name} className="flex items-center gap-3 py-2">
                      <span className="text-xs font-semibold text-slate-300 w-4 text-center flex-shrink-0">{i + 1}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">{m.name}</p>
                        <p className="text-xs text-slate-400">{m.count} transactions</p>
                      </div>
                      <span className="text-sm font-semibold text-slate-900 flex-shrink-0">{formatCurrency(m.total)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recurring */}
            <div className="bg-white rounded-2xl border border-slate-100 p-6">
              <h3 className="text-base font-semibold text-slate-900 mb-5">Recurring</h3>
              {recurring.isLoading ? <Loading /> : !recurring.data?.length ? <Empty msg="None detected" /> : (
                <div className="space-y-1">
                  {recurring.data.slice(0, 5).map((r) => (
                    <div key={r.name} className="flex items-center gap-3 py-2">
                      <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center flex-shrink-0 text-sm">
                        {emoji(r.category)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">{r.name}</p>
                        {r.next_due && <p className="text-xs text-slate-400">Next: {r.next_due}</p>}
                      </div>
                      <span className="text-sm font-semibold text-slate-900 flex-shrink-0">{formatCurrency(r.amount)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      </>
      )}

      {showUpload && <FileUploadModal onClose={() => setShowUpload(false)} />}
    </div>
  );
}

/* ── small building blocks ── */

const INSIGHT_COLOR: Record<string, string> = {
  warning: '#fb7185', tip: '#818cf8', positive: '#34d399', info: '#94a3b8',
};

function Stat({ label, value, emoji }: { label: string; value: string; emoji?: string }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 px-5 py-4">
      <p className="text-xs text-slate-400 font-medium">{label}</p>
      <p className="text-lg font-bold text-slate-900 mt-1 flex items-center gap-1.5 truncate">
        {emoji && <span className="text-base">{emoji}</span>}
        {value}
      </p>
    </div>
  );
}

function Tab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
        active ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-400 hover:text-slate-600'
      }`}
    >
      {children}
    </button>
  );
}

function Loading() {
  return <div className="h-32 flex items-center justify-center text-slate-300 text-sm">Loading…</div>;
}
function Empty({ msg = 'No data for this period' }: { msg?: string }) {
  return <div className="h-32 flex items-center justify-center text-slate-300 text-sm">{msg}</div>;
}

const HEAT = ['#f1f5f9', '#dbe1fb', '#b4befb', '#8b96f5', '#6366f1', '#4f46e5'];

function Heatmap({ data }: { data: { day: string; week_num: number; total: number }[] }) {
  // collapse to per-day average across weeks
  const byDay: Record<string, number[]> = {};
  data.forEach(c => {
    if (!byDay[c.day]) byDay[c.day] = [];
    if (c.total > 0) byDay[c.day].push(c.total);
  });
  const dayAvg = DAYS_FULL.map(d => {
    const vals = byDay[d] ?? [];
    return vals.length ? vals.reduce((s, x) => s + x, 0) / vals.length : 0;
  });
  const max = Math.max(...dayAvg, 1);
  const peakIdx = dayAvg.indexOf(Math.max(...dayAvg));

  return (
    <div>
      <div className="grid grid-cols-7 gap-2">
        {DAYS.map((d, i) => {
          const val = dayAvg[i];
          const intensity = Math.round((val / max) * (HEAT.length - 1));
          return (
            <div key={d} className="flex flex-col items-center gap-2">
              <div
                className="w-full aspect-square rounded-xl flex items-center justify-center"
                style={{ background: HEAT[val > 0 ? intensity : 0] }}
                title={formatCurrency(val)}
              >
                {i === peakIdx && val > 0 && <span className="text-white text-xs font-bold">peak</span>}
              </div>
              <span className={`text-xs ${i === peakIdx ? 'text-indigo-600 font-semibold' : 'text-slate-400'}`}>{d}</span>
            </div>
          );
        })}
      </div>
      {dayAvg[peakIdx] > 0 && (
        <p className="text-xs text-slate-400 mt-4">
          You spend most on <span className="text-indigo-600 font-medium">{DAYS_FULL[peakIdx]}s</span> — averaging {formatCurrency(dayAvg[peakIdx])}
        </p>
      )}
    </div>
  );
}
