import { useState } from 'react';
import type { Transaction } from '../../types';
import type { SortField, SortDir } from '../../hooks/useTransactions';
import { useCategories } from '../../hooks/useCategories';
import { useUpdateCategory } from '../../hooks/useTransactions';
import { useSetInvestment } from '../../hooks/useInvestments';
import { formatDate, formatCurrency } from '../../utils/formatters';
import CategoryBadge from './CategoryBadge';
import LoadingSpinner from '../shared/LoadingSpinner';

interface Props {
  transactions: Transaction[];
  isLoading: boolean;
  total: number;
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

function CategoryDropdown({ txnId, currentCategoryId }: { txnId: number; currentCategoryId: number | null }) {
  const { data: categories } = useCategories();
  const updateCategory = useUpdateCategory();
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs text-indigo-600 hover:underline"
      >
        Change
      </button>
      {open && (
        <div className="absolute z-20 left-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg py-1 min-w-40">
          <button
            className="w-full text-left px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-50"
            onClick={() => { updateCategory.mutate({ txnId, categoryId: null }); setOpen(false); }}
          >
            Uncategorized
          </button>
          {categories?.map((cat) => (
            <button
              key={cat.id}
              className={`w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 ${cat.id === currentCategoryId ? 'font-semibold' : ''}`}
              onClick={() => { updateCategory.mutate({ txnId, categoryId: cat.id }); setOpen(false); }}
            >
              {cat.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function TransactionTable({ transactions, isLoading, total, page, totalPages, onPageChange, sortBy, sortDir, onSort }: Props) {
  const setInvestment = useSetInvestment();

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
        <span className="text-sm text-slate-500">{total} transactions</span>
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
              <th className="px-4 py-3 text-left">Category</th>
              <th className="px-4 py-3 text-left">Source</th>
              <SortHeader label="Amount" field="amount" sortBy={sortBy} sortDir={sortDir} onSort={onSort} align="right" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {transactions.map((txn) => (
              <tr key={txn.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 text-slate-500 whitespace-nowrap">{formatDate(txn.date)}</td>
                <td className="px-4 py-3 text-slate-800 max-w-xs">
                  <div className="flex items-center gap-2">
                    <span className="truncate">{txn.description}</span>
                    {txn.is_internal_transfer && (
                      <span
                        className="flex-shrink-0 text-[10px] font-semibold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-full"
                        title="Self transfer between your own accounts — excluded from income & spend totals"
                      >
                        ↔ Internal
                      </span>
                    )}
                    {txn.is_investment && (
                      <span
                        className="flex-shrink-0 text-[10px] font-semibold bg-indigo-50 text-indigo-600 px-1.5 py-0.5 rounded-full"
                        title="Tagged as an investment — excluded from spend"
                      >
                        📈 Investment
                      </span>
                    )}
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
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {txn.category ? (
                      <CategoryBadge name={txn.category.name} color={txn.category.color} />
                    ) : (
                      <span className="text-xs text-slate-400">Uncategorized</span>
                    )}
                    <CategoryDropdown txnId={txn.id} currentCategoryId={txn.category?.id ?? null} />
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">{txn.source}</span>
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
