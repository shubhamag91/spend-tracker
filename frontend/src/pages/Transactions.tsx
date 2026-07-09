import { useState, useEffect } from 'react';
import { useMode } from '../store/demoMode';
import { useSelectedAccountId } from '../store/selectedAccount';
import { useTransactions, type SortField, type SortDir } from '../hooks/useTransactions';
import { useByDay } from '../hooks/useAnalytics';
import TransactionTable from '../components/transactions/TransactionTable';
import DateRangeFilter, { type DateRange, DEFAULT_RANGE } from '../components/dashboard/DateRangeFilter';
import FileUploadModal from '../components/upload/FileUploadModal';
import { useDemoModeStore } from '../store/demoMode';

export default function Transactions() {
  const mode = useMode();
  const accountId = useSelectedAccountId();
  const isDemoMode = useDemoModeStore((s) => s.isDemoMode);
  const [range, setRange] = useState<DateRange>(DEFAULT_RANGE);
  const [kind, setKind] = useState<'all' | 'spend' | 'income' | 'investment' | 'transfer' | 'poker'>('all');
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<SortField>('date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [showUpload, setShowUpload] = useState(false);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const dateRange = range.start ? { start: range.start, end: range.end } : undefined;

  // Switching account can shrink the result set — go back to page 1.
  useEffect(() => { setPage(1); }, [accountId]);
  // Debounce the search box so we don't refetch on every keystroke.
  useEffect(() => {
    const id = setTimeout(() => { setDebouncedSearch(search.trim()); setPage(1); }, 300);
    return () => clearTimeout(id);
  }, [search]);

  const allDays = useByDay(mode);
  const dataBounds = allDays.data?.length
    ? { min: allDays.data[0].label, max: allDays.data[allDays.data.length - 1].label }
    : undefined;

  const { data, isLoading } = useTransactions({
    mode,
    account_id: accountId,
    kind: kind === 'all' ? undefined : kind,
    search: debouncedSearch || undefined,
    start_date: dateRange?.start,
    end_date: dateRange?.end,
    sort_by: sortBy,
    sort_dir: sortDir,
    page,
    page_size: 50,
  });

  function handleRangeChange(r: DateRange) {
    setRange(r);
    setPage(1);
  }

  // Click a sortable header: toggle direction if already active, else default desc.
  function handleSort(field: SortField) {
    if (field === sortBy) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortDir('desc');
    }
    setPage(1);
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-slate-800">Transactions</h1>
        {!isDemoMode && (
          <button
            onClick={() => setShowUpload(true)}
            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            + Upload Statement
          </button>
        )}
      </div>

      <DateRangeFilter selected={range} onChange={handleRangeChange} dataBounds={dataBounds} />

      <div className="flex items-center justify-between gap-3 flex-wrap">
        {/* Kind filter — isolate spends / income / investments from the full ledger */}
        <div className="inline-flex rounded-xl border border-slate-200 bg-white p-1 flex-wrap">
          {([['all', 'All'], ['spend', 'Spends'], ['income', 'Income'], ['investment', 'Investments'], ['transfer', 'Transfers'], ['poker', 'Poker']] as const).map(([k, label]) => (
            <button
              key={k}
              onClick={() => { setKind(k); setPage(1); }}
              className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                kind === k ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Description search */}
        <div className="relative w-full sm:w-72">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search description…"
            className="w-full bg-white border border-slate-200 rounded-xl pl-9 pr-3 py-2 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300"
          />
        </div>
      </div>

      <TransactionTable
        transactions={data?.items ?? []}
        isLoading={isLoading}
        total={data?.total ?? 0}
        totalAmount={data?.total_amount ?? 0}
        page={data?.page ?? 1}
        totalPages={data?.total_pages ?? 1}
        onPageChange={setPage}
        sortBy={sortBy}
        sortDir={sortDir}
        onSort={handleSort}
      />

      {showUpload && <FileUploadModal onClose={() => setShowUpload(false)} />}
    </div>
  );
}
