import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { formatCurrency } from '../../utils/formatters';
import type { InvestmentMonthly } from '../../hooks/useInvestments';

// Soothing, muted palette assigned per platform (sorted by total, biggest first).
const PALETTE = ['#6d6af0', '#4f9e7e', '#c69a52', '#cf7d8a', '#56a3c2', '#9b85cf', '#d08f5a', '#7e8ca3'];

function compactInr(v: number) {
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(1)}Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(1)}L`;
  if (v >= 1e3) return `₹${Math.round(v / 1e3)}k`;
  return `₹${v}`;
}

interface Props {
  monthly: InvestmentMonthly;
  isReturns: boolean;
}

export default function InvestmentMonthlyChart({ monthly, isReturns }: Props) {
  const { platforms, data } = monthly;
  if (!data.length) return null;

  const colorFor = (p: string) => PALETTE[platforms.indexOf(p) % PALETTE.length];

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const rows = payload.filter((p: any) => p.value > 0);
    const total = rows.reduce((s: number, p: any) => s + p.value, 0);
    return (
      <div className="bg-white border border-slate-100 rounded-xl px-4 py-3 shadow-lg text-sm">
        <p className="font-semibold text-slate-700 mb-1.5">{label}</p>
        {rows.map((p: any) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-6 text-xs">
            <span className="flex items-center gap-1.5 text-slate-500">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: p.color }} />{p.dataKey}
            </span>
            <span className="font-medium text-slate-700">{formatCurrency(p.value)}</span>
          </div>
        ))}
        <div className="flex items-center justify-between gap-6 text-xs mt-1.5 pt-1.5 border-t border-slate-100">
          <span className="text-slate-400">Total</span>
          <span className="font-semibold text-slate-800">{formatCurrency(total)}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h2 className="font-semibold text-slate-800 mb-3">
        Monthly {isReturns ? 'returns' : 'invested'}
        <span className="text-xs font-normal text-slate-400"> · by platform</span>
      </h2>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 5, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e2940" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} tickFormatter={compactInr} width={52} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: '#1e2940' }} />
          <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={9} />
          {platforms.map((p) => (
            <Bar key={p} dataKey={p} stackId="a" fill={colorFor(p)} maxBarSize={64} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
