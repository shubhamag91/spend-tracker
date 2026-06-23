import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import { formatCurrency } from '../../utils/formatters';
import type { TimeSeriesPoint } from '../../types';
import LoadingSpinner from '../shared/LoadingSpinner';

interface Props {
  data?: TimeSeriesPoint[];
  isLoading: boolean;
  title: string;
}

interface BarTooltipProps {
  active?: boolean;
  payload?: { value: number }[];
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: BarTooltipProps) => {
  if (active && payload?.length) {
    return (
      <div className="bg-white border border-slate-100 rounded-xl px-4 py-3 shadow-lg text-sm">
        <p className="text-slate-400 text-xs mb-1">{label}</p>
        <p className="font-bold text-slate-800 text-base">{formatCurrency(payload[0].value)}</p>
      </div>
    );
  }
  return null;
};

function groupByWeek(data: TimeSeriesPoint[]): TimeSeriesPoint[] {
  const map = new Map<string, number>();
  data.forEach(({ label, total }) => {
    const d = parseISO(label);
    const day = d.getDay();
    const diff = (day === 0 ? -6 : 1) - day;
    const weekStart = new Date(d);
    weekStart.setDate(d.getDate() + diff);
    const key = format(weekStart, 'd MMM');
    map.set(key, (map.get(key) ?? 0) + total);
  });
  return Array.from(map.entries()).map(([label, total]) => ({ label, total }));
}

function groupByMonth(data: TimeSeriesPoint[]): TimeSeriesPoint[] {
  const map = new Map<string, number>();
  data.forEach(({ label, total }) => {
    const key = format(parseISO(label), 'MMM yy');
    map.set(key, (map.get(key) ?? 0) + total);
  });
  return Array.from(map.entries()).map(([label, total]) => ({ label, total }));
}

function formatDayLabel(label: string): string {
  try { return format(parseISO(label), 'd MMM'); } catch { return label; }
}

export default function SpendBarChart({ data, isLoading, title }: Props) {
  const count = data?.length ?? 0;

  // Choose grouping based on how many days of data we have
  let chartData: TimeSeriesPoint[];
  let groupLabel: string;

  if (count === 0) {
    chartData = [];
    groupLabel = '';
  } else if (count <= 45) {
    // Show individual days
    chartData = data!.map(d => ({ label: formatDayLabel(d.label), total: d.total }));
    groupLabel = 'Daily';
  } else if (count <= 120) {
    // Group by week
    chartData = groupByWeek(data!);
    groupLabel = 'Grouped by week';
  } else {
    // Group by month
    chartData = groupByMonth(data!);
    groupLabel = 'Grouped by month';
  }

  const maxVal = chartData.length ? Math.max(...chartData.map(d => d.total)) : 0;

  // For daily view with many bars, skip some labels
  const tickInterval = chartData.length > 20 ? Math.floor(chartData.length / 15) : 0;

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
      <div className="flex items-start justify-between mb-5">
        <div>
          <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
          {groupLabel && <p className="text-xs text-slate-400 mt-0.5">{groupLabel}</p>}
        </div>
        {chartData.length > 0 && (
          <span className="text-xs text-slate-400 bg-slate-50 px-2 py-1 rounded-lg">
            {chartData.length} {count <= 45 ? 'days' : count <= 120 ? 'weeks' : 'months'}
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-52"><LoadingSpinner size="lg" /></div>
      ) : !chartData.length ? (
        <div className="flex flex-col items-center justify-center h-52 text-slate-300 gap-2">
          <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
            <path d="M3 3v18h18"/><path d="M7 16l4-4 4 4 4-7"/>
          </svg>
          <span className="text-sm">No data for this period</span>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={chartData} margin={{ top: 22, right: 4, left: 0, bottom: 0 }} barCategoryGap="25%">
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2940" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: '#94a3b8', fontWeight: 500 }}
              tickLine={false}
              axisLine={false}
              interval={tickInterval}
            />
            <YAxis
              tickFormatter={(v) => `₹${v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v}`}
              tick={{ fontSize: 11, fill: '#94a3b8' }}
              tickLine={false}
              axisLine={false}
              width={44}
            />
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#1e2940', radius: 6 } as any} />
            <Bar dataKey="total" radius={[5, 5, 0, 0]} maxBarSize={chartData.length <= 45 ? 28 : 48}>
              {chartData.map((entry, i) => (
                <Cell key={i} fill={entry.total === maxVal ? '#6366f1' : '#3a3a78'} />
              ))}
              {/* Only show labels when there are few enough bars */}
              {chartData.length <= 20 && (
                <LabelList
                  dataKey="total"
                  position="top"
                  formatter={(v) => {
                    const n = Number(v);
                    return `₹${n >= 1000 ? (n / 1000).toFixed(1) + 'k' : n}`;
                  }}
                  style={{ fontSize: 10, fontWeight: 600, fill: '#6366f1' }}
                />
              )}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
