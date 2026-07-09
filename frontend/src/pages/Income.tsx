import { useState } from 'react';
import { useMode } from '../store/demoMode';
import {
  useSummary, useIncomeMonthly, useIncomeSources, useSavingsTrajectory,
} from '../hooks/useAnalytics';
import DateRangeFilter, { type DateRange, DEFAULT_RANGE } from '../components/dashboard/DateRangeFilter';
import { formatCurrency, formatMonthLabel } from '../utils/formatters';

function SectionLabel({ children }: { children: string }) {
  return <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">{children}</p>;
}

function StatCard({ label, value, sub, subColor = 'text-slate-400' }: {
  label: string; value: string; sub?: string; subColor?: string;
}) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">{label}</p>
      <p className="text-3xl font-extrabold text-slate-800 tracking-tight leading-none mb-2">{value}</p>
      {sub && <p className={`text-xs font-medium ${subColor}`}>{sub}</p>}
    </div>
  );
}

export default function Income() {
  const mode = useMode();
  const [range, setRange] = useState<DateRange>(DEFAULT_RANGE);
  const dateRange = range.start ? { start: range.start, end: range.end } : undefined;

  const summary = useSummary(mode, dateRange);
  const monthly = useIncomeMonthly(mode);
  const sources = useIncomeSources(mode, dateRange);
  const savings = useSavingsTrajectory(mode);

  const totalIncome = summary.data?.total_credits ?? 0;
  const totalSpend = summary.data?.total_spend ?? 0;
  const savingsRate = totalIncome > 0 ? Math.round(((totalIncome - totalSpend) / totalIncome) * 100) : 0;

  const maxMonthly = Math.max(...(monthly.data?.map(m => m.actual) ?? [1]), 1);
  const maxSavings = Math.max(...(savings.data?.map(s => s.saved) ?? [1]), 1);

  const sourceTypeIcon: Record<string, string> = {
    salary: '💼', freelance: '💻', interest: '📈', other: '💰',
  };
  const sourceTypeLabel: Record<string, string> = {
    salary: 'Stable', freelance: 'Variable', interest: 'Passive', other: 'Other',
  };
  const sourceTypeBadge: Record<string, string> = {
    salary: 'bg-[#15241d] text-[#6ee7b7]',
    freelance: 'bg-[#241c10] text-[#d9b066]',
    interest: 'bg-indigo-50 text-indigo-700',
    other: 'bg-slate-100 text-slate-600',
  };

  // stability score — simple heuristic
  const months = monthly.data ?? [];
  const expected = months[0]?.expected ?? 0;
  const onTarget = months.filter(m => m.actual >= expected * 0.95).length;
  const stability = months.length > 0 ? Math.round((onTarget / months.length) * 80 + 20) : 0;
  const stabilityColor = stability >= 75 ? 'text-[#5cc99e]' : stability >= 50 ? 'text-[#d9b066]' : 'text-[#e88e9b]';

  // avg / best / worst savings
  const savingsList = savings.data ?? [];
  const avgRate = savingsList.length ? Math.round(savingsList.reduce((s, x) => s + x.rate, 0) / savingsList.length) : 0;
  const bestRate = savingsList.length ? Math.max(...savingsList.map(x => x.rate)) : 0;
  const worstRate = savingsList.length ? Math.min(...savingsList.map(x => x.rate)) : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">Income</h1>
        <p className="text-xs text-slate-400 mt-1">Salary, freelance, interest and all credits</p>
      </div>

      <DateRangeFilter selected={range} onChange={setRange} />

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Income"
          value={formatCurrency(totalIncome)}
          sub={savingsRate > 0 ? `↑ saving ${savingsRate}% of income` : undefined}
          subColor="text-[#5cc99e]"
        />
        <StatCard
          label="Total Spend"
          value={formatCurrency(totalSpend)}
          sub={totalIncome > 0 ? `${Math.round(totalSpend / totalIncome * 100)}% of income` : undefined}
          subColor="text-[#e88e9b]"
        />
        <StatCard
          label="Savings Rate"
          value={`${savingsRate}%`}
          sub={savingsRate >= 30 ? 'Great discipline!' : 'Room to improve'}
          subColor={savingsRate >= 30 ? 'text-[#5cc99e]' : 'text-[#d9b066]'}
        />
        <StatCard
          label="Income Stability"
          value={`${stability}/100`}
          sub={stability >= 75 ? 'Mostly predictable' : stability >= 50 ? 'Some variation' : 'High variability'}
          subColor={stabilityColor}
        />
      </div>

      {/* ── Income trend ── */}
      <SectionLabel>Income Trend & Stability</SectionLabel>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Monthly income bars */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <h3 className="text-sm font-semibold text-slate-800 mb-1">Monthly Income</h3>
          <p className="text-xs text-slate-400 mb-5">Actual income each month vs expected baseline</p>
          {monthly.isLoading ? (
            <div className="h-40 flex items-center justify-center text-slate-300 text-sm">Loading…</div>
          ) : !months.length ? (
            <div className="h-40 flex items-center justify-center text-slate-300 text-sm">No income data yet</div>
          ) : (
            <>
              <div className="flex items-end gap-2 h-44">
                {months.slice(-8).map((m, i) => {
                  const isLast = i === months.slice(-8).length - 1;
                  // cap bar height so the value label + month label fit inside h-44 (no overflow into the subtitle)
                  const h = Math.max(8, Math.round((m.actual / maxMonthly) * 120));
                  const belowExpected = m.actual < m.expected * 0.95;
                  return (
                    <div key={m.month} className="flex-1 flex flex-col items-center gap-1.5">
                      <span className="text-xs text-slate-400">{formatCurrency(m.actual)}</span>
                      <div
                        className="w-full rounded-t-md"
                        style={{
                          height: h,
                          background: belowExpected ? '#b3924a' : isLast ? 'linear-gradient(180deg,#4f9e7e,#2f6b54)' : '#4d8f73',
                        }}
                      />
                      <span className={`text-xs ${isLast ? 'text-[#5cc99e] font-bold' : 'text-slate-400'}`}>
                        {formatMonthLabel(m.month)}
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="flex gap-4 mt-3 text-xs text-slate-400">
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-[#4d8f73] inline-block" />Normal</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-[#b3924a] inline-block" />Below expected</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-[#4f9e7e] inline-block" />Latest</span>
              </div>
            </>
          )}
        </div>

        {/* Stability score */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <h3 className="text-sm font-semibold text-slate-800 mb-1">Income Stability Score</h3>
          <p className="text-xs text-slate-400 mb-5">How predictable your income is · 100 = perfectly stable</p>
          <div className="flex flex-col items-center mb-6">
            <div className="relative w-32 h-32">
              <svg viewBox="0 0 130 130" width="130" height="130">
                <circle cx="65" cy="65" r="52" fill="none" stroke="#2a3650" strokeWidth="14" />
                <circle
                  cx="65" cy="65" r="52" fill="none"
                  stroke={stability >= 75 ? '#4f9e7e' : stability >= 50 ? '#c69a52' : '#cf7d8a'}
                  strokeWidth="14"
                  strokeDasharray={`${(stability / 100) * 326} 326`}
                  strokeDashoffset="81.5"
                  transform="rotate(-90 65 65)"
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-extrabold text-slate-800">{stability}</span>
                <span className="text-xs text-slate-400">/ 100</span>
              </div>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center px-3 py-2.5 bg-[#15241d] rounded-xl">
              <span className="text-xs font-medium text-[#6ee7b7]">✅ {onTarget} of {months.length} months on target</span>
              <span className="text-xs font-bold text-[#5cc99e]">+{Math.round(onTarget / Math.max(months.length, 1) * 40)} pts</span>
            </div>
            {sources.data?.some(s => s.source_type === 'salary') && (
              <div className="flex justify-between items-center px-3 py-2.5 bg-[#15241d] rounded-xl">
                <span className="text-xs font-medium text-[#6ee7b7]">✅ Salary income detected</span>
                <span className="text-xs font-bold text-[#5cc99e]">+40 pts</span>
              </div>
            )}
            {sources.data?.some(s => s.source_type === 'freelance') && (
              <div className="flex justify-between items-center px-3 py-2.5 bg-[#241c10] rounded-xl">
                <span className="text-xs font-medium text-[#d9b066]">⚠ Variable income (freelance)</span>
                <span className="text-xs font-bold text-[#d9b066]">varies</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Income diversification ── */}
      <SectionLabel>Income Diversification</SectionLabel>
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-1">Income Sources Breakdown</h3>
        <p className="text-xs text-slate-400 mb-5">What percentage of income comes from each source</p>
        {sources.isLoading ? (
          <div className="h-24 flex items-center justify-center text-slate-300 text-sm">Loading…</div>
        ) : !sources.data?.length ? (
          <div className="h-24 flex items-center justify-center text-slate-300 text-sm">No income data</div>
        ) : (
          <>
            {/* Stacked bar */}
            <div className="flex h-5 rounded-xl overflow-hidden mb-5">
              {sources.data.map((s) => (
                <div
                  key={s.name}
                  style={{
                    width: `${s.percentage}%`,
                    background: s.source_type === 'salary' ? '#4f9e7e' : s.source_type === 'freelance' ? '#6366f1' : s.source_type === 'interest' ? '#c69a52' : '#94a3b8',
                  }}
                  title={`${s.name}: ${s.percentage}%`}
                />
              ))}
            </div>
            <div>
              {sources.data.map((s) => (
                <div key={s.name} className="flex items-center gap-3 py-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center flex-shrink-0 text-lg">
                    {sourceTypeIcon[s.source_type] ?? '💰'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{s.name}</p>
                    <div className="mt-1.5 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${s.percentage}%`,
                          background: s.source_type === 'salary' ? '#4f9e7e' : s.source_type === 'freelance' ? '#6366f1' : '#c69a52',
                        }}
                      />
                    </div>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-1 rounded-full ${sourceTypeBadge[s.source_type] ?? 'bg-slate-100 text-slate-600'}`}>
                    {sourceTypeLabel[s.source_type]}
                  </span>
                  <div className="text-right flex-shrink-0">
                    <p className="text-sm font-bold text-slate-800">{formatCurrency(s.total)}</p>
                    <p className="text-xs text-slate-400">{s.percentage}%</p>
                  </div>
                </div>
              ))}
            </div>
            {sources.data.some(s => s.source_type === 'salary' && s.percentage > 70) && (
              <div className="mt-4 p-3 bg-[#241c10] border border-[#3b2d14] rounded-xl text-xs text-[#d9b066]">
                💡 <strong>High salary dependency.</strong> Consider building freelance income or passive income streams to reduce single-source risk.
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Expected vs actual ── */}
      <SectionLabel>Expected vs Actual</SectionLabel>
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-1">Expected vs Actual Income</h3>
        <p className="text-xs text-slate-400 mb-5">How each month compared to your expected baseline</p>
        {monthly.isLoading ? (
          <div className="h-24 flex items-center justify-center text-slate-300 text-sm">Loading…</div>
        ) : !months.length ? (
          <div className="h-24 flex items-center justify-center text-slate-300 text-sm">No data</div>
        ) : (
          <div className="space-y-4">
            {months.slice(-6).map((m, i) => {
              const isLatest = i === months.slice(-6).length - 1;
              const diff = m.actual - m.expected;
              const actualPct = Math.min(100, Math.round((m.actual / (m.expected * 1.25)) * 100));
              const expectedPct = Math.min(100, Math.round((m.expected / (m.expected * 1.25)) * 100));
              return (
                <div key={m.month} className="flex items-center gap-3">
                  <span className={`text-xs font-medium w-10 flex-shrink-0 ${isLatest ? 'text-indigo-600 font-bold' : 'text-slate-500'}`}>
                    {formatMonthLabel(m.month)}
                  </span>
                  <div className="flex-1 space-y-1.5">
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${actualPct}%`, background: diff >= 0 ? '#4f9e7e' : '#b3924a' }} />
                    </div>
                    <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-slate-200" style={{ width: `${expectedPct}%` }} />
                    </div>
                  </div>
                  <span className="text-xs font-bold text-slate-800 w-20 text-right">{formatCurrency(m.actual)}</span>
                  <span className={`text-xs font-semibold w-16 text-right ${diff >= 0 ? 'text-[#5cc99e]' : 'text-[#e88e9b]'}`}>
                    {diff >= 0 ? '+' : ''}{formatCurrency(diff)}
                  </span>
                </div>
              );
            })}
            <div className="flex gap-4 pt-1 text-xs text-slate-400">
              <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded bg-[#4f9e7e] inline-block" />Actual</span>
              <span className="flex items-center gap-1.5"><span className="w-3 h-1.5 rounded bg-slate-200 inline-block" />Expected</span>
            </div>
          </div>
        )}
      </div>

      {/* ── Savings trajectory ── */}
      <SectionLabel>Savings Trajectory</SectionLabel>
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <h3 className="text-sm font-semibold text-slate-800 mb-1">Monthly Savings</h3>
        <p className="text-xs text-slate-400 mb-5">How much you saved each month (income minus spend)</p>
        {savings.isLoading ? (
          <div className="h-32 flex items-center justify-center text-slate-300 text-sm">Loading…</div>
        ) : !savingsList.length ? (
          <div className="h-32 flex items-center justify-center text-slate-300 text-sm">No data</div>
        ) : (
          <>
            <div className="flex items-end gap-2 h-36 mb-3">
              {savingsList.slice(-8).map((s, i) => {
                const isLast = i === savingsList.slice(-8).length - 1;
                const h = Math.max(6, Math.round((s.saved / maxSavings) * 96));
                return (
                  <div key={s.month} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-xs text-slate-400">{formatCurrency(s.saved)}</span>
                    <div
                      className="w-full rounded-t-md"
                      style={{
                        height: h,
                        background: isLast ? 'linear-gradient(180deg,#4f9e7e,#2f6b54)' : s.rate < 30 ? '#b3924a' : '#4d8f73',
                      }}
                    />
                    <span className={`text-xs ${isLast ? 'text-[#5cc99e] font-bold' : 'text-slate-400'}`}>
                      {formatMonthLabel(s.month)}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="grid grid-cols-3 gap-3 mt-2">
              <div className="text-center p-3 bg-slate-50 rounded-xl">
                <p className="text-xs text-slate-400 mb-1">Avg rate</p>
                <p className="text-xl font-extrabold text-slate-800">{avgRate}%</p>
              </div>
              <div className="text-center p-3 bg-[#15241d] rounded-xl">
                <p className="text-xs text-slate-400 mb-1">Best month</p>
                <p className="text-xl font-extrabold text-[#5cc99e]">{Math.round(bestRate)}%</p>
              </div>
              <div className="text-center p-3 bg-[#251720] rounded-xl">
                <p className="text-xs text-slate-400 mb-1">Worst month</p>
                <p className="text-xl font-extrabold text-[#e88e9b]">{Math.round(worstRate)}%</p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
