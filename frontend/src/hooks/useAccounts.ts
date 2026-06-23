import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../api/client';
import type { Account, AccountStatus } from '../types';

export function useAccounts() {
  return useQuery<Account[]>({
    queryKey: ['accounts'],
    queryFn: () => client.get('/accounts').then((r) => r.data),
    staleTime: 60_000,
  });
}

export function useAccountStatus(mode: string) {
  return useQuery<AccountStatus[]>({
    queryKey: ['accounts', 'status', mode],
    queryFn: () => client.get('/accounts/status', { params: { mode } }).then((r) => r.data),
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
