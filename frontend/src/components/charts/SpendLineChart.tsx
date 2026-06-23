import {
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Area, AreaChart, LabelList,
} from 'recharts';
import { formatCurrency, formatMonthLabel } from '../../utils/formatters';
import type { TimeSeriesPoint } from '../../types';
import LoadingSpinner from '../shared/LoadingSpinner';

interface Props {
  data?: TimeSeriesPoint[];
  isLoading: boolean;
  title: string;
}

interface LineTooltipProps {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: LineTooltipProps) => {
  if (active && payload?.length) {
    return (
      <div className="bg-white border border-slate-100 rounded-xl px-4 py-3 shadow-lg text-sm">
        <p className="text-slate-400 text-xs mb-1">{formatMonthLabel(label ?? '')}</p>
        <p className="font-bold text-slate-800 text-base">{formatCurrency(payload[0].value)}</p>
      </div>
    );
  }
  return null;
};

export default function SpendLineChart({ data, isLoading, title }: Props) {
  const avg = data?.length ? data.reduce((s, p) => s + p.total, 0) / data.length : 0;

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div className="mb-5">
        <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
        <p className="text-xs text-slate-400 mt-0.5">Monthly spend over time</p>
      </div>
      {isLoading ? (
        <div className="flex items-center justify-center h-52"><LoadingSpinner size="lg" /></div>
      ) : !data?.length ? (
        <div className="flex flex-col items-center justify-center h-52 text-slate-300 gap-2">
          <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M7 16l4-4 4 4 4-7"/></svg>
          <span className="text-sm">No data for this period</span>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={data} margin={{ top: 24, right: 4, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2940" vertical={false} />
            <XAxis
              dataKey="label"
              tickFormatter={formatMonthLabel}
              tick={{ fontSize: 11, fill: '#94a3b8', fontWeight: 500 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tickFormatter={(v) => `₹${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              tickLine={false}
              axisLine={false}
              width={44}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={avg} stroke="#3a3a78" strokeDasharray="4 4" label={{ value: 'avg', fill: '#a5b4fc', fontSize: 10, position: 'insideTopRight' }} />
            <Area
              type="monotone"
              dataKey="total"
              stroke="#6366f1"
              strokeWidth={2.5}
              fill="url(#spendGradient)"
              dot={{ r: 3.5, fill: '#6366f1', strokeWidth: 0 }}
              activeDot={{ r: 6, fill: '#6366f1', strokeWidth: 2, stroke: '#3a3a78' }}
            >
              <LabelList
                dataKey="total"
                position="top"
                formatter={(v) => {
                  const n = Number(v);
                  return `₹${n >= 1000 ? (n / 1000).toFixed(1) + 'k' : n}`;
                }}
                style={{ fontSize: 10, fontWeight: 600, fill: '#6366f1' }}
              />
            </Area>
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
