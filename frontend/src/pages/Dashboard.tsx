import { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useMode } from '../store/demoMode';
import { useSummary, useByMonth, useByDay } from '../hooks/useAnalytics';
import DateRangeFilter, { type DateRange, PRESETS } from '../components/dashboard/DateRangeFilter';
import AccountFreshness from '../components/dashboard/AccountFreshness';
import FileUploadModal from '../components/upload/FileUploadModal';
import { formatCurrency, formatMonthLabel } from '../utils/formatters';

function compactInr(v: number) {
  if (!Number.isFinite(v)) return '₹0';
  const a = Math.abs(v), s = v < 0 ? '-' : '';
  if (a >= 1e7) return `${s}₹${(a / 1e7).toFixed(1)}Cr`;
  if (a >= 1e5) return `${s}₹${(a / 1e5).toFixed(1)}L`;
  if (a >= 1e3) return `${s}₹${Math.round(a / 1e3)}k`;
  return `${s}₹${a}`;
}

const TrendTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-100 rounded-xl px-3 py-2 shadow-lg text-sm">
      <p className="text-slate-400 text-xs mb-0.5">{formatMonthLabel(label)}</p>
      <p className="font-semibold text-slate-700">{formatCurrency(payload[0].value)}</p>
    </div>
  );
};

export default function Dashboard() {
  const mode = useMode();
  const [range, setRange] = useState<DateRange>(PRESETS[0]);
  const [showUpload, setShowUpload] = useState(false);
  const dateRange = range.start ? { start: range.start, end: range.end } : undefined;

  const summary = useSummary(mode, dateRange);
  const byMonth = useByMonth(mode, dateRange);
  const allDays = useByDay(mode);

  const dataBounds = allDays.data?.length
    ? { min: allDays.data[0].label, max: allDays.data[allDays.data.length - 1].label }
    : undefined;

  const s = summary.data;
  const trend = byMonth.data ?? [];
  const empty = !summary.isLoading && (s?.transaction_count ?? 0) === 0;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Spends</h1>
          <p className="text-sm text-slate-400 mt-0.5">What you actually consumed — investments &amp; transfers excluded.</p>
        </div>
        <button
          onClick={() => setShowUpload(true)}
          className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 flex items-center gap-2"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" /></svg>
          Import Statement
        </button>
      </div>

      <DateRangeFilter selected={range} onChange={setRange} dataBounds={dataBounds} />

      {empty ? (
        <div className="bg-white rounded-2xl border border-slate-100 h-64 flex flex-col items-center justify-center text-slate-400 gap-1">
          <p className="text-sm">No spending in this period.</p>
          <button onClick={() => setShowUpload(true)} className="text-xs text-indigo-600 hover:underline">Import a statement</button>
        </div>
      ) : (
        <>
          {/* Headline */}
          <div className="bg-white rounded-2xl border border-slate-100 p-7">
            <p className="text-slate-400 text-sm font-medium">You spent</p>
            <p className="text-4xl font-bold tracking-tight text-slate-900 mt-1">{formatCurrency(s?.total_spend ?? 0)}</p>
            <div className="flex flex-wrap gap-x-6 gap-y-1 mt-3 text-sm text-slate-400">
              <span>{s?.transaction_count ?? 0} transactions</span>
              <span>{formatCurrency(s?.daily_average ?? 0)}/day avg</span>
              {s?.top_category && <span>Top: <span className="text-slate-600 font-medium">{s.top_category}</span></span>}
            </div>
          </div>

          {/* Monthly trend */}
          <div className="bg-white rounded-2xl border border-slate-100 p-5">
            <h2 className="font-semibold text-slate-800 mb-3">Monthly trend</h2>
            {trend.length === 0 ? (
              <p className="text-sm text-slate-400">No data</p>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={trend} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e2940" vertical={false} />
                  <XAxis dataKey="label" tickFormatter={formatMonthLabel} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                  <YAxis tickFormatter={compactInr} tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={52} />
                  <Tooltip content={<TrendTooltip />} cursor={{ fill: '#1e2940' }} />
                  <Bar dataKey="total" fill="#6d6af0" radius={[3, 3, 0, 0]} maxBarSize={56} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <AccountFreshness />
        </>
      )}

      {showUpload && <FileUploadModal onClose={() => setShowUpload(false)} />}
    </div>
  );
}
