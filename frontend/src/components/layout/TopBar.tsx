import { Link, useLocation } from 'react-router-dom';
import DemoModeToggle from '../shared/DemoModeToggle';
import AccountSelector from '../shared/AccountSelector';

const NAV = [
  { path: '/', label: 'Dashboard' },
  { path: '/transactions', label: 'Transactions' },
  { path: '/investments', label: 'Investments' },
  { path: '/subscriptions', label: 'Fixed Spends' },
  { path: '/income', label: 'Income' },
  { path: '/categories', label: 'Categories' },
];

export default function TopBar() {
  const location = useLocation();

  return (
    <header className="bg-white border-b border-slate-100 px-8 flex items-center justify-between sticky top-0 z-10 h-15 shadow-sm" style={{ height: 60 }}>
      <div className="flex items-center gap-10">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <span className="font-extrabold text-base text-slate-800 tracking-tight">SpendTracker</span>
        </div>
        <nav className="flex gap-0.5">
          {NAV.map(({ path, label }) => {
            const active = path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(path);
            return (
              <Link
                key={path}
                to={path}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? 'bg-indigo-50 text-indigo-700 font-semibold'
                    : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
                }`}
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="flex items-center gap-4">
        <AccountSelector />
        <DemoModeToggle />
      </div>
    </header>
  );
}
