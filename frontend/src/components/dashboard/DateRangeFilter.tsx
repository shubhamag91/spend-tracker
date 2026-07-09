import { useState, useRef, useEffect } from 'react';
import { format, subDays, subMonths, startOfMonth, endOfMonth, startOfYear, endOfYear } from 'date-fns';

export interface DateRange {
  start?: string;
  end?: string;
  label: string;
}

const today = () => new Date();
const fmt = (d: Date) => format(d, 'yyyy-MM-dd');

// Indian financial year: Apr 1 – Mar 31. Before April, the current FY started last calendar year.
function startOfFinancialYear(d: Date): Date {
  const year = d.getMonth() >= 3 /* April */ ? d.getFullYear() : d.getFullYear() - 1;
  return new Date(year, 3, 1);
}
function financialYearLabel(d: Date): string {
  const startYear = startOfFinancialYear(d).getFullYear();
  return `FY ${startYear}–${String(startYear + 1).slice(-2)}`;
}

// Default view: current financial year onward — hides prior-FY data (e.g. an
// incomplete trailing March) without deleting it; still reachable via "All Time".
// eslint-disable-next-line react-refresh/only-export-components
export const DEFAULT_RANGE: DateRange = {
  label: financialYearLabel(today()),
  start: fmt(startOfFinancialYear(today())),
};

// eslint-disable-next-line react-refresh/only-export-components
export const PRESETS: DateRange[] = [
  { label: 'All Time' },
  DEFAULT_RANGE,
  {
    label: 'This Month',
    start: fmt(startOfMonth(today())),
    end: fmt(endOfMonth(today())),
  },
  {
    label: 'Last Month',
    start: fmt(startOfMonth(subMonths(today(), 1))),
    end: fmt(endOfMonth(subMonths(today(), 1))),
  },
  {
    label: 'Last 30 Days',
    start: fmt(subDays(today(), 30)),
    end: fmt(today()),
  },
  {
    label: 'This Year',
    start: fmt(startOfYear(today())),
    end: fmt(endOfYear(today())),
  },
];

interface Props {
  selected: DateRange;
  onChange: (range: DateRange) => void;
  /** Earliest and latest dates that actually have data — used to pre-fill the custom picker */
  dataBounds?: { min: string; max: string };
}

export default function DateRangeFilter({ selected, onChange, dataBounds }: Props) {
  const [showCustom, setShowCustom] = useState(false);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const panelRef = useRef<HTMLDivElement>(null);
  const isCustom = selected.label === 'Custom';

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowCustom(false);
      }
    }
    if (showCustom) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showCustom]);

  function applyCustom() {
    if (!fromDate || !toDate) return;
    onChange({ label: 'Custom', start: fromDate, end: toDate });
    setShowCustom(false);
  }

  function openCustom() {
    if (isCustom && selected.start && selected.end) {
      // Already has a custom range — keep it
      setFromDate(selected.start);
      setToDate(selected.end);
    } else if (dataBounds) {
      // Pre-fill with the actual data bounds
      setFromDate(dataBounds.min);
      setToDate(dataBounds.max);
    } else {
      setFromDate(fmt(subDays(today(), 30)));
      setToDate(fmt(today()));
    }
    setShowCustom(true);
  }

  const customLabel = isCustom && selected.start && selected.end
    ? `${format(new Date(selected.start), 'd MMM')} → ${format(new Date(selected.end), 'd MMM yy')}`
    : 'Custom Range';

  return (
    <div className="flex flex-wrap items-center gap-2">
      {PRESETS.map((preset) => (
        <button
          key={preset.label}
          onClick={() => { onChange(preset); setShowCustom(false); }}
          className={`px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
            selected.label === preset.label
              ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
              : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300 hover:text-indigo-600'
          }`}
        >
          {preset.label}
        </button>
      ))}

      <div className="relative" ref={panelRef}>
        <button
          onClick={openCustom}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
            isCustom
              ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
              : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300 hover:text-indigo-600'
          }`}
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <path d="M16 2v4M8 2v4M3 10h18" strokeLinecap="round" />
          </svg>
          {customLabel}
        </button>

        {showCustom && (
          <div className="absolute left-0 top-full mt-2 z-30 bg-white border border-slate-100 rounded-2xl shadow-xl p-4 w-72">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Custom Date Range</p>

            {dataBounds && (
              <div className="mb-3 px-3 py-2 bg-indigo-50 rounded-xl text-xs text-indigo-600 font-medium flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01" strokeLinecap="round"/>
                </svg>
                Data exists from <strong className="mx-1">{format(new Date(dataBounds.min), 'd MMM yy')}</strong> to <strong className="mx-1">{format(new Date(dataBounds.max), 'd MMM yy')}</strong>
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">From</label>
                <input
                  type="date"
                  value={fromDate}
                  min={dataBounds?.min}
                  max={toDate || dataBounds?.max || fmt(today())}
                  onChange={(e) => setFromDate(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">To</label>
                <input
                  type="date"
                  value={toDate}
                  min={fromDate || dataBounds?.min}
                  max={dataBounds?.max || fmt(today())}
                  onChange={(e) => setToDate(e.target.value)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400"
                />
              </div>
            </div>

            {/* Quick shortcuts based on data bounds */}
            {dataBounds && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                <button
                  onClick={() => { setFromDate(dataBounds.min); setToDate(dataBounds.max); }}
                  className="text-xs px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors"
                >
                  All data
                </button>
                <button
                  onClick={() => {
                    const d = new Date(dataBounds.max);
                    setFromDate(fmt(startOfMonth(d)));
                    setToDate(fmt(endOfMonth(d)));
                  }}
                  className="text-xs px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-lg text-slate-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors"
                >
                  Latest month
                </button>
              </div>
            )}

            <div className="flex gap-2 mt-4">
              <button
                onClick={() => setShowCustom(false)}
                className="flex-1 px-3 py-2 text-sm text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={applyCustom}
                disabled={!fromDate || !toDate}
                className="flex-1 px-3 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Apply
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
