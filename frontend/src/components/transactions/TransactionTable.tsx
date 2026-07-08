import type { Transaction } from '../../types';
import type { SortField, SortDir } from '../../hooks/useTransactions';
import { useSetTransfer } from '../../hooks/useTransactions';
import { useSetInvestment } from '../../hooks/useInvestments';
import { formatDate, formatCurrency } from '../../utils/formatters';
import LoadingSpinner from '../shared/LoadingSpinner';

interface Props {
  transactions: Transaction[];
  isLoading: boolean;
  total: number;
  totalAmount: number;
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  sortBy: SortField;
  sortDir: SortDir;
  onSort: (field: SortField) => void;
}

// A clickable column header that shows the active sort direction.
function SortHeader({
  label, field, sortBy, sortDir, onSort, align = 'left',
}: {
  label: string; field: SortField; sortBy: SortField; sortDir: SortDir;
  onSort: (f: SortField) => void; align?: 'left' | 'right';
}) {
  const active = sortBy === field;
  return (
    <th className={`px-4 py-3 text-${align}`}>
      <button
        onClick={() => onSort(field)}
        className={`inline-flex items-center gap-1 uppercase tracking-wide hover:text-slate-700 ${active ? 'text-slate-700 font-semibold' : ''}`}
      >
        {label}
        <span className="text-[10px]">{active ? (sortDir === 'asc' ? '▲' : '▼') : '↕'}</span>
      </button>
    </th>
  );
}

// The transaction's classification — mirrors the filter tabs (Spend / Income / …).
function txnKind(t: Transaction): { label: string; cls: string } {
  if (t.is_investment) return { label: '📈 Investment', cls: 'bg-indigo-50 text-indigo-600' };
  if (t.bucket === 'poker') return { label: '🃏 Poker', cls: 'bg-purple-100 text-purple-700' };
  if (t.is_internal_transfer) return { label: '↔ Transfer', cls: 'bg-slate-100 text-slate-500' };
  if (t.is_card_payment) return { label: 'Card payment', cls: 'bg-sky-100 text-sky-700' };
  if (t.transaction_type === 'credit') return { label: 'Income', cls: 'bg-emerald-100 text-emerald-700' };
  return { label: 'Spend', cls: 'bg-amber-100 text-amber-700' };
}

export default function TransactionTable({ transactions, isLoading, total, totalAmount, page, totalPages, onPageChange, sortBy, sortDir, onSort }: Props) {
  const setInvestment = useSetInvestment();
  const setTransfer = useSetTransfer();

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <span className="text-sm text-slate-500">{total} transactions · <span className="font-semibold text-slate-700">{formatCurrency(totalAmount)}</span></span>
        <div className="flex items-center gap-2">
          <button
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            className="px-2 py-1 text-xs rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
          >
            Prev
          </button>
          <span className="text-xs text-slate-500">{page} / {totalPages}</span>
          <button
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
            className="px-2 py-1 text-xs rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
          >
            Next
          </button>
        </div>
      </div>
      {transactions.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-slate-400 text-sm">No transactions found</div>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
            <tr>
              <SortHeader label="Date" field="date" sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
              <th className="px-4 py-3 text-left">Description</th>
              <th className="px-4 py-3 text-left">Type</th>
              <th className="px-4 py-3 text-left">Account</th>
              <SortHeader label="Amount" field="amount" sortBy={sortBy} sortDir={sortDir} onSort={onSort} align="right" />
            </tr>
          </thead>
          <tbody>
            {transactions.map((txn) => (
              <tr key={txn.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 text-slate-500 whitespace-nowrap">{formatDate(txn.date)}</td>
                <td className="px-4 py-3 text-slate-800 max-w-xs">
                  <div className="flex items-center gap-2">
                    <span className="truncate">{txn.description}</span>
                    {/* Mark/unmark investment — bank debits only (you invest from a bank, not a card) */}
                    {txn.account?.type === 'bank' && txn.transaction_type === 'debit' && !txn.is_internal_transfer && (
                      <button
                        onClick={() => setInvestment.mutate({ txnId: txn.id, value: !txn.is_investment })}
                        className="flex-shrink-0 text-[10px] text-slate-400 hover:text-indigo-600 hover:underline"
                        title={txn.is_investment ? 'Move back to spend' : 'Count this as an investment, not spend'}
                      >
                        {txn.is_investment ? 'unmark' : 'mark investment'}
                      </button>
                    )}
                    {/* Mark/unmark transfer — money moved, not spent/earned (e.g. a loan to a friend, repaid) */}
                    {!txn.is_investment && txn.bucket !== 'poker' && (
                      <button
                        onClick={() => setTransfer.mutate({ txnId: txn.id, value: !txn.is_internal_transfer })}
                        className="flex-shrink-0 text-[10px] text-slate-400 hover:text-slate-600 hover:underline"
                        title={txn.is_internal_transfer ? 'Count as spend/income again' : 'Money moved, not spent/earned — exclude from spend & income'}
                      >
                        {txn.is_internal_transfer ? 'unmark transfer' : 'mark transfer'}
                      </button>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {(() => {
                    const k = txnKind(txn);
                    return <span className={`text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap ${k.cls}`}>{k.label}</span>;
                  })()}
                </td>
                <td className="px-4 py-3">
                  {txn.account ? (
                    <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full inline-flex items-center gap-1">
                      <span>{txn.account.type === 'card' ? '💳' : '🏦'}</span>{txn.account.name}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400" title={`Imported from ${txn.source}`}>—</span>
                  )}
                </td>
                <td className={`px-4 py-3 text-right font-medium ${
                  txn.is_internal_transfer || txn.is_investment
                    ? 'text-slate-400'
                    : txn.transaction_type === 'debit' ? 'text-red-600' : 'text-green-600'
                }`}>
                  {txn.transaction_type === 'debit' ? '-' : '+'}{formatCurrency(txn.amount)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
