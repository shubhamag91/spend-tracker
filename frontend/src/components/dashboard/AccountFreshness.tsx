import { differenceInCalendarDays, parseISO } from 'date-fns';
import { useMode } from '../../store/demoMode';
import { useAccountStatus } from '../../hooks/useAccounts';
import { formatDate } from '../../utils/formatters';

// Staleness thresholds (days since the account's latest transaction).
function freshness(days: number | null) {
  if (days == null) return { dot: 'bg-slate-300', text: 'text-slate-400', label: 'no data' };
  if (days <= 7) return { dot: 'bg-emerald-500', text: 'text-emerald-600', label: `${days}d ago` };
  if (days <= 30) return { dot: 'bg-amber-500', text: 'text-amber-600', label: `${days}d ago` };
  return { dot: 'bg-red-500', text: 'text-red-600', label: `${days}d ago` };
}

export default function AccountFreshness() {
  const mode = useMode();
  const { data: accounts } = useAccountStatus(mode);
  if (!accounts || accounts.length === 0) return null;

  const today = new Date();
  const withDays = accounts.map((a) => ({
    ...a,
    days: a.latest_transaction_date ? differenceInCalendarDays(today, parseISO(a.latest_transaction_date)) : null,
  }));
  const stale = withDays.filter((a) => a.days != null && a.days > 30).length;

  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-700">Accounts — data freshness</h3>
        <span className="text-xs text-slate-400">
          {stale > 0 ? <span className="text-red-600 font-medium">{stale} need updating</span> : 'all current'}
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {withDays.map((a) => {
          const f = freshness(a.days);
          return (
            <div key={a.id} className="flex items-center gap-2.5 rounded-xl border border-slate-100 px-3 py-2">
              <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${f.dot}`} title={f.label} />
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-700 truncate">
                  {a.name} <span className="text-[10px] text-slate-400 uppercase">{a.type}</span>
                </p>
                <p className="text-xs text-slate-400">
                  {a.latest_transaction_date ? <>through {formatDate(a.latest_transaction_date)} · <span className={f.text}>{f.label}</span></> : 'no transactions'}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
