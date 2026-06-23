import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../api/client';
import type { Account } from '../types';

export function useAccounts() {
  return useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => client.get('/accounts').then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useCreateAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; type: 'bank' | 'card'; issuer?: string; last4?: string }) =>
      client.post<Account>('/accounts', body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts'] }),
  });
}
