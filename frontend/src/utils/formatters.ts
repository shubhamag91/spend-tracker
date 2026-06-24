import { format, parseISO } from 'date-fns';

export function formatCurrency(amount: number): string {
  if (!Number.isFinite(amount)) amount = 0;  // guard NaN/undefined → "₹0", never "₹NaN"
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'dd MMM yyyy');
  } catch {
    return dateStr;
  }
}

export function formatMonthLabel(label: string): string {
  // label is "YYYY-MM"
  try {
    return format(parseISO(label + '-01'), 'MMM yy');
  } catch {
    return label;
  }
}

export function formatWeekLabel(label: string): string {
  // label is "YYYY-Www"
  return label.replace('W', 'W');
}
