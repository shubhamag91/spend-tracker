import { useQuery } from '@tanstack/react-query';
import client from '../api/client';
import { useSelectedAccountId } from '../store/selectedAccount';
import type {
  AnalyticsSummary, TimeSeriesPoint, CategorySpend, InsightItem,
  WeeklyVelocityPoint, HeatmapCell, MerchantSpend, RecurringTransaction,
  IncomeMonthPoint, IncomeSource, SavingsPoint, WalletSummary,
} from '../types';

interface DateRange {
  start?: string;
  end?: string;
}

function buildParams(mode: string, accountId: number | null, range?: DateRange) {
  const p: Record<string, string | number> = { mode };
  if (accountId != null) p.account_id = accountId;
  if (range?.start) p.start_date = range.start;
  if (range?.end) p.end_date = range.end;
  return p;
}

// Every analytics hook is scoped by the globally-selected account (null = all).
// accountId is part of the query key so switching accounts refetches automatically.
export function useSummary(mode: string, range?: DateRange) {
  const accountId = useSelectedAccountId();
  return useQuery<AnalyticsSummary>({
    queryKey: ['analytics', 'summary', mode, accountId, range],
    queryFn: () => client.get('/analytics/summary', { params: buildParams(mode, accountId, range) }).then((r) => r.data),
  });
}

export function useWallet(mode: string, range?: DateRange) {
  const accountId = useSelectedAccountId();
  return useQuery<WalletSummary>({
    queryKey: ['analytics', 'wallet', mode, accountId, range],
    queryFn: () => client.get('/analytics/wallet', { params: buildParams(mode, accountId, range) }).then((r) => r.data),
  });
}

export function useByDay(mode: string, range?: DateRange) {
  const accountId = useSelectedAccountId();
  return useQuery<TimeSeriesPoint[]>({
    queryKey: ['analytics', 'by-day', mode, accountId, range],
    queryFn: () => client.get('/analytics/by-day', { params: buildParams(mode, accountId, range) }).then((r) => r.data),
  });
}

export function useByMonth(mode: string, range?: DateRange) {
  const accountId = useSelectedAccountId();
  return useQuery<TimeSeriesPoint[]>({
    queryKey: ['analytics', 'by-month', mode, accountId, range],
    queryFn: () => client.get('/analytics/by-month', { params: buildParams(mode, accountId, range) }).then((r) => r.data),
  });
}

export function useByYear(mode: string) {
  const accountId = useSelectedAccountId();
  return useQuery<TimeSeriesPoint[]>({
    queryKey: ['analytics', 'by-year', mode, accountId],
    queryFn: () => client.get('/analytics/by-year', { params: buildParams(mode, accountId) }).then((r) => r.data),
  });
}

export function useByCategory(mode: string, range?: DateRange) {
  const accountId = useSelectedAccountId();
  return useQuery<CategorySpend[]>({
    queryKey: ['analytics', 'by-category', mode, accountId, range],
    queryFn: () => client.get('/analytics/by-category', { params: buildParams(mode, accountId, range) }).then((r) => r.data),
  });
}

export function useInsights(mode: string, range?: DateRange) {
  const accountId = useSelectedAccountId();
  return useQuery<InsightItem[]>({
    queryKey: ['analytics', 'insights', mode, accountId, range],
    queryFn: () => client.get('/analytics/insights', { params: buildParams(mode, accountId, range) }).then((r) => r.data),
  });
}

export function useWeeklyVelocity(mode: string, range?: DateRange) {
  const accountId = useSelectedAccountId();
  return useQuery<WeeklyVelocityPoint[]>({
    queryKey: ['analytics', 'weekly-velocity', mode, accountId, range],
    queryFn: () => client.get('/analytics/weekly-velocity', { params: buildParams(mode, accountId, range) }).then((r) => r.data),
  });
}

export function useHeatmap(mode: string) {
  const accountId = useSelectedAccountId();
  return useQuery<HeatmapCell[]>({
    queryKey: ['analytics', 'heatmap', mode, accountId],
    queryFn: () => client.get('/analytics/heatmap', { params: buildParams(mode, accountId) }).then((r) => r.data),
  });
}

export function useTopMerchants(mode: string, range?: DateRange) {
  const accountId = useSelectedAccountId();
  return useQuery<MerchantSpend[]>({
    queryKey: ['analytics', 'top-merchants', mode, accountId, range],
    queryFn: () => client.get('/analytics/top-merchants', { params: buildParams(mode, accountId, range) }).then((r) => r.data),
  });
}

export function useRecurring(mode: string) {
  const accountId = useSelectedAccountId();
  return useQuery<RecurringTransaction[]>({
    queryKey: ['analytics', 'recurring', mode, accountId],
    queryFn: () => client.get('/analytics/recurring', { params: buildParams(mode, accountId) }).then((r) => r.data),
  });
}

export function useIncomeMonthly(mode: string) {
  const accountId = useSelectedAccountId();
  return useQuery<IncomeMonthPoint[]>({
    queryKey: ['analytics', 'income-monthly', mode, accountId],
    queryFn: () => client.get('/analytics/income-monthly', { params: buildParams(mode, accountId) }).then((r) => r.data),
  });
}

export function useIncomeSources(mode: string, range?: DateRange) {
  const accountId = useSelectedAccountId();
  return useQuery<IncomeSource[]>({
    queryKey: ['analytics', 'income-sources', mode, accountId, range],
    queryFn: () => client.get('/analytics/income-sources', { params: buildParams(mode, accountId, range) }).then((r) => r.data),
  });
}

export function useSavingsTrajectory(mode: string) {
  const accountId = useSelectedAccountId();
  return useQuery<SavingsPoint[]>({
    queryKey: ['analytics', 'savings-trajectory', mode, accountId],
    queryFn: () => client.get('/analytics/savings-trajectory', { params: buildParams(mode, accountId) }).then((r) => r.data),
  });
}
