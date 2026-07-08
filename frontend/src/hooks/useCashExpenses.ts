import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../api/client';

export interface CashExpense {
  id: number;
  name: string;
  amount: number;
  day_of_month: number;
  type: string;
  frequency: string;
  active: boolean;
  start_date: string | null;
}

export function useCashExpenses() {
  return useQuery<CashExpense[]>({
    queryKey: ['cash-expenses'],
    queryFn: () => client.get('/cash-expenses').then((r) => r.data),
  });
}

// A cash expense generates real transactions, so refetch spend/fixed-spends/list too.
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['cash-expenses'] });
  qc.invalidateQueries({ queryKey: ['subscriptions'] });
  qc.invalidateQueries({ queryKey: ['analytics'] });
  qc.invalidateQueries({ queryKey: ['transactions'] });
}

export function useCreateCashExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; amount: number; day_of_month: number; type?: string }) =>
      client.post('/cash-expenses', body).then((r) => r.data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteCashExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.delete(`/cash-expenses/${id}`),
    onSuccess: () => invalidateAll(qc),
  });
}
