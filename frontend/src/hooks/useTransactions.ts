import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../api/client';
import type { TransactionPage } from '../types';

export type SortField = 'date' | 'amount';
export type SortDir = 'asc' | 'desc';

interface TransactionFilter {
  mode: string;
  account_id?: number | null;
  start_date?: string;
  end_date?: string;
  category_id?: number;
  is_investment?: boolean;
  transaction_type?: 'debit' | 'credit';
  kind?: 'spend' | 'income' | 'investment' | 'transfer' | 'poker';
  investment_platform?: string;   // filter by platform label (matches all its keywords)
  search?: string;
  sort_by?: SortField;
  sort_dir?: SortDir;
  page?: number;
  page_size?: number;
}

export function useTransactions(filter: TransactionFilter) {
  const params: Record<string, string | number | boolean> = { mode: filter.mode };
  if (filter.account_id != null) params.account_id = filter.account_id;
  if (filter.start_date) params.start_date = filter.start_date;
  if (filter.end_date) params.end_date = filter.end_date;
  if (filter.category_id) params.category_id = filter.category_id;
  if (filter.is_investment != null) params.is_investment = filter.is_investment;
  if (filter.transaction_type) params.transaction_type = filter.transaction_type;
  if (filter.kind) params.kind = filter.kind;
  if (filter.investment_platform) params.investment_platform = filter.investment_platform;
  if (filter.search) params.search = filter.search;
  if (filter.sort_by) params.sort_by = filter.sort_by;
  if (filter.sort_dir) params.sort_dir = filter.sort_dir;
  params.page = filter.page ?? 1;
  params.page_size = filter.page_size ?? 50;

  return useQuery<TransactionPage>({
    queryKey: ['transactions', filter],
    queryFn: () => client.get('/transactions', { params }).then((r) => r.data),
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ txnId, categoryId }: { txnId: number; categoryId: number | null }) =>
      client.patch(`/transactions/${txnId}/category`, null, { params: { category_id: categoryId } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  });
}

// Mark/unmark a transaction as a transfer — excludes it from spend & income, so refetch both.
export function useSetTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ txnId, value }: { txnId: number; value: boolean }) =>
      client.patch(`/transactions/${txnId}/transfer`, null, { params: { is_transfer: value } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}

// Mark/unmark a one-off transaction as poker — for a counterparty not worth
// adding to POKER_KEYWORDS. Excludes it from spend & income, so refetch both.
export function useSetPoker() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ txnId, value }: { txnId: number; value: boolean }) =>
      client.patch(`/transactions/${txnId}/poker`, null, { params: { is_poker: value } }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}
