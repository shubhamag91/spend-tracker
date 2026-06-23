import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../api/client';
import { useSelectedAccountId } from '../store/selectedAccount';
import type { SubscriptionSummary, SubscriptionRule } from '../types';

export function useSubscriptionSummary(mode: string) {
  const accountId = useSelectedAccountId();
  return useQuery<SubscriptionSummary>({
    queryKey: ['subscriptions', 'summary', mode, accountId],
    queryFn: () => {
      const params: Record<string, string | number> = { mode };
      if (accountId != null) params.account_id = accountId;
      return client.get('/subscriptions/summary', { params }).then((r) => r.data);
    },
  });
}

export function useSubscriptionRules() {
  return useQuery<SubscriptionRule[]>({
    queryKey: ['subscription-rules'],
    queryFn: () => client.get('/subscription-rules').then((r) => r.data),
  });
}

function invalidate(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['subscription-rules'] });
  qc.invalidateQueries({ queryKey: ['subscriptions'] });
}

export function useCreateSubscriptionRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; keyword: string; type: string; frequency: string; min_amount?: number | null; monthly_amount?: number | null }) =>
      client.post('/subscription-rules', body).then((r) => r.data),
    onSuccess: () => invalidate(qc),
  });
}

export function useUpdateSubscriptionRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; type?: string; frequency?: string; name?: string }) =>
      client.patch(`/subscription-rules/${id}`, body).then((r) => r.data),
    onSuccess: () => invalidate(qc),
  });
}

export function useDeleteSubscriptionRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => client.delete(`/subscription-rules/${id}`),
    onSuccess: () => invalidate(qc),
  });
}
