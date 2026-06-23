import { create } from 'zustand';

// null = "All accounts" (the combined, cross-account view).
interface SelectedAccountStore {
  accountId: number | null;
  setAccount: (id: number | null) => void;
}

export const useSelectedAccountStore = create<SelectedAccountStore>((set) => ({
  accountId: null,
  setAccount: (id) => set({ accountId: id }),
}));

export const useSelectedAccountId = () => useSelectedAccountStore((s) => s.accountId);
