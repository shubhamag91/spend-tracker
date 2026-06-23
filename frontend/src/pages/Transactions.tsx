import { useState, useEffect } from 'react';
import { useMode } from '../store/demoMode';
import { useSelectedAccountId } from '../store/selectedAccount';
import { useTransactions, type SortField, type SortDir } from '../hooks/useTransactions';
import { useByDay } from '../hooks/useAnalytics';
import TransactionTable from '../components/transactions/TransactionTable';
import DateRangeFilter, { type DateRange, PRESETS } from '../components/dashboard/DateRangeFilter';
import FileUploadModal from '../components/upload/FileUploadModal';
import { useDemoModeStore } from '../store/demoMode';

export default function Transactions() {
  const mode = useMode();
  const accountId = useSelectedAccountId();
  const isDemoMode = useDemoModeStore((s) => s.isDemoMode);
  const [range, setRange] = useState<DateRange>(PRESETS[0]);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<SortField>('date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [showUpload, setShowUpload] = useState(false);

  const dateRange = range.start ? { start: range.start, end: range.end } : undefined;

  // Switching account can shrink the result set — go back to page 1.
  useEffect(() => { setPage(1); }, [accountId]);

  const allDays = useByDay(mode);
  const dataBounds = allDays.data?.length
    ? { min: allDays.data[0].label, max: allDays.data[allDays.data.length - 1].label }
    : undefined;

  const { data, isLoading } = useTransactions({
    mode,
    account_id: accountId,
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

      <TransactionTable
        transactions={data?.items ?? []}
        isLoading={isLoading}
        total={data?.total ?? 0}
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
