import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { formatCurrency } from '../../utils/formatters';
import type { InvestmentMonthly } from '../../hooks/useInvestments';

const INVESTED = '#6d6af0';   // indigo
const RETURNS = '#4f9e7e';    // muted green

function compactInr(v: number) {
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(1)}Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(1)}L`;
  if (v >= 1e3) return `₹${Math.round(v / 1e3)}k`;
  return `₹${v}`;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const inv = payload.find((p: any) => p.dataKey === 'invested')?.value ?? 0;
  const ret = payload.find((p: any) => p.dataKey === 'returns')?.value ?? 0;
  return (
    <div className="bg-white border border-slate-100 rounded-xl px-4 py-3 shadow-lg text-sm">
      <p className="font-semibold text-slate-700 mb-1.5">{label}</p>
      <div className="flex items-center justify-between gap-6 text-xs">
        <span className="flex items-center gap-1.5 text-slate-500"><span className="w-2 h-2 rounded-full" style={{ background: INVESTED }} />Invested</span>
        <span className="font-medium text-slate-700">{formatCurrency(inv)}</span>
      </div>
      <div className="flex items-center justify-between gap-6 text-xs mt-1">
        <span className="flex items-center gap-1.5 text-slate-500"><span className="w-2 h-2 rounded-full" style={{ background: RETURNS }} />Returns</span>
        <span className="font-medium text-slate-700">{formatCurrency(ret)}</span>
      </div>
      <div className="flex items-center justify-between gap-6 text-xs mt-1.5 pt-1.5 border-t border-slate-100">
        <span className="text-slate-400">Net</span>
        <span className="font-semibold text-slate-800">{formatCurrency(inv - ret)}</span>
      </div>
    </div>
  );
};

interface Props {
  monthly: InvestmentMonthly;
  selected: string | null;            // null = All
  onSelect: (platform: string | null) => void;
}

export default function InvestmentMonthlyChart({ monthly, selected, onSelect }: Props) {
  const { platforms, data } = monthly;

  const chip = (active: boolean) =>
    `px-3 py-1 text-xs font-medium rounded-full border transition-colors ${
      active ? 'bg-indigo-600 text-white border-indigo-600' : 'border-slate-200 text-slate-500 hover:text-slate-700'
    }`;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <h2 className="font-semibold text-slate-800">
          Monthly invested vs returns
          <span className="text-xs font-normal text-slate-400"> · {selected ?? 'all platforms'}</span>
        </h2>
      </div>

      {/* platform picker */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        <button onClick={() => onSelect(null)} className={chip(selected === null)}>All</button>
        {platforms.map((p) => (
          <button key={p} onClick={() => onSelect(p)} className={chip(selected === p)}>{p}</button>
        ))}
      </div>

      {data.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-slate-400 text-sm">No data for this selection</div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data} margin={{ top: 5, right: 8, left: 0, bottom: 0 }} barGap={2} barCategoryGap="34%">
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2940" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} tickFormatter={compactInr} width={52} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#1e2940' }} />
            <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={9} />
            <Bar dataKey="invested" name="Invested" fill={INVESTED} radius={[3, 3, 0, 0]} />
            <Bar dataKey="returns" name="Returns" fill={RETURNS} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
