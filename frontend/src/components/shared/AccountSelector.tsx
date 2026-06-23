import { useAccounts } from '../../hooks/useAccounts';
import { useSelectedAccountStore } from '../../store/selectedAccount';

// Global account scope: "All accounts" (combined view) or a single bank/card.
export default function AccountSelector() {
  const { data: accounts } = useAccounts();
  const accountId = useSelectedAccountStore((s) => s.accountId);
  const setAccount = useSelectedAccountStore((s) => s.setAccount);

  if (!accounts || accounts.length === 0) return null;

  const banks = accounts.filter((a) => a.type === 'bank');
  const cards = accounts.filter((a) => a.type === 'card');

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-slate-400 text-xs hidden sm:inline">Account</span>
      <select
        value={accountId ?? ''}
        onChange={(e) => setAccount(e.target.value === '' ? null : Number(e.target.value))}
        className="border border-slate-200 rounded-lg px-2.5 py-1.5 text-sm text-slate-700 bg-white hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-100 focus:border-indigo-300 max-w-44"
      >
        <option value="">All accounts</option>
        {banks.length > 0 && (
          <optgroup label="Banks">
            {banks.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </optgroup>
        )}
        {cards.length > 0 && (
          <optgroup label="Cards">
            {cards.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </optgroup>
        )}
      </select>
    </label>
  );
}
