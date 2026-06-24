import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import client from '../api/client';
import { useSelectedAccountId } from '../store/selectedAccount';
import type { InvestmentSummary, InvestmentRule } from '../types';

export function useInvestmentSummary(
  mode: string,
  range?: { start?: string; end?: string },
  direction: 'debit' | 'credit' = 'debit',  // debit = invested, credit = returns
) {
  const accountId = useSelectedAccountId();
  return useQuery<InvestmentSummary>({
    placeholderData: keepPreviousData,  // keep showing prior data while a new range loads
    queryKey: ['investments', 'summary', mode, accountId, range, direction],
    queryFn: () => {
      const params: Record<string, string | number> = { mode, direction };
      if (accountId != null) params.account_id = accountId;
      if (range?.start) params.start_date = range.start;
      if (range?.end) params.end_date = range.end;
      return client.get('/investments/summary', { params }).then((r) => r.data);
    },
  });
}

export interface InvestmentMonthly {
  platforms: string[];
  data: Array<Record<string, string | number>>;  // each row: { month, label, [platform]: amount }
}

export function useInvestmentMonthly(
  mode: string,
  range?: { start?: string; end?: string },
  direction: 'debit' | 'credit' = 'debit',
) {
  const accountId = useSelectedAccountId();
  return useQuery<InvestmentMonthly>({
    placeholderData: keepPreviousData,
    queryKey: ['investments', 'monthly', mode, accountId, range, direction],
    queryFn: () => {
      const params: Record<string, string | number> = { mode, direction };
      if (accountId != null) params.account_id = accountId;
      if (range?.start) params.start_date = range.start;
      if (range?.end) params.end_date = range.end;
      return client.get('/investments/monthly', { params }).then((r) => r.data);
    },
  });
}

export function useInvestmentRules() {
  return useQuery<InvestmentRule[]>({
    queryKey: ['investment-rules'],
    queryFn: () => client.get('/investment-rules').then((r) => r.data),
  });
}

// Invalidate everything that an investment re-classification can shift.
function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['investment-rules'] });
  qc.invalidateQueries({ queryKey: ['investments'] });
  qc.invalidateQueries({ queryKey: ['analytics'] });
  qc.invalidateQueries({ queryKey: ['transactions'] });
}

export function useCreateInvestmentRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { keyword: string; label?: string }) =>
      client.post('/investment-rules', body).then((r) => r.data),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteInvestmentRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.delete(`/investment-rules/${id}`),
    onSuccess: () => invalidateAll(qc),
  });
}

export function useSetInvestment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ txnId, value }: { txnId: number; value: boolean }) =>
      client.patch(`/transactions/${txnId}/investment`, null, { params: { is_investment: value } }),
    onSuccess: () => invalidateAll(qc),
  });
}
