export interface Category {
  id: number;
  name: string;
  color: string;
  keywords: string[];
  created_at: string;
}

export interface Account {
  id: number;
  name: string;
  type: 'bank' | 'card';
  issuer: string | null;
  last4: string | null;
  created_at: string;
}

export interface AccountStatus {
  id: number;
  name: string;
  type: 'bank' | 'card';
  last4: string | null;
  latest_transaction_date: string | null;
  transaction_count: number;
}

export interface Transaction {
  id: number;
  date: string;
  amount: number;
  transaction_type: 'debit' | 'credit';
  description: string;
  source: string;
  data_mode: 'real' | 'demo';
  is_internal_transfer: boolean;
  is_investment: boolean;
  is_card_payment: boolean;
  bucket: string | null;
  created_at: string;
  category: { id: number; name: string; color: string } | null;
  account: { id: number; name: string; type: 'bank' | 'card' } | null;
}

export interface TransactionPage {
  items: Transaction[];
  total: number;
  total_amount: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AnalyticsSummary {
  total_spend: number;
  total_credits: number;
  daily_average: number;
  top_category: string | null;
  transaction_count: number;
}

export interface InsightItem {
  type: 'warning' | 'tip' | 'info' | 'positive';
  title: string;
  body: string;
}

export interface TimeSeriesPoint {
  label: string;
  total: number;
}

export interface CategorySpend {
  category: string;
  color: string;
  total: number;
  percentage: number;
}

export interface IngestLog {
  id: number;
  filename: string;
  file_hash: string;
  parser_used: string;
  rows_parsed: number;
  rows_inserted: number;
  rows_skipped: number;
  status: 'pending' | 'success' | 'failed';
  error_message: string | null;
  ingested_at: string;
}

export interface WeeklyVelocityPoint {
  week_label: string;
  total: number;
  change_pct: number | null;
}

export interface HeatmapCell {
  day: string;
  week_num: number;
  total: number;
}

export interface MerchantSpend {
  name: string;
  category: string;
  total: number;
  count: number;
  avg_per_txn: number;
}

export interface RecurringTransaction {
  name: string;
  category: string;
  amount: number;
  frequency: string;
  next_due: string | null;
}

export interface IncomeMonthPoint {
  month: string;
  actual: number;
  expected: number;
}

export interface IncomeSource {
  name: string;
  total: number;
  percentage: number;
  source_type: string;
}

export interface SavingsPoint {
  month: string;
  saved: number;
  rate: number;
}

export interface WalletSummary {
  loaded: number;
  topups: number;
  other_in: number;
  invested: number;
  spent: number;
  unspent: number;
  spend_txns: number;
}

export interface InvestmentRule {
  id: number;
  keyword: string;
  label: string | null;
  created_at: string;
}

export interface PlatformInvest {
  name: string;
  total: number;
  count: number;
  keyword: string | null;
}

export interface InvestmentSummary {
  total_invested: number;
  count: number;
  by_platform: PlatformInvest[];
}

export type Frequency = 'monthly' | 'quarterly' | 'half-yearly' | 'yearly' | 'weekly' | 'variable';

export interface SubscriptionRule {
  id: number;
  name: string;
  keyword: string;
  type: string;
  frequency: Frequency;
  min_amount: number | null;
  monthly_amount: number | null;
  created_at: string;
}

export interface SubscriptionItem {
  name: string;
  type: string;
  frequency: Frequency;
  monthly: number;
  amount: number;
  total: number;
  count: number;
  last_date: string | null;
}

export interface TypeBreakdown {
  type: string;
  monthly: number;
  count: number;
}

export interface SubscriptionSummary {
  monthly_total: number;
  window_total: number;
  service_count: number;
  by_type: TypeBreakdown[];
  items: SubscriptionItem[];
}

