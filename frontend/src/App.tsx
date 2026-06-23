import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/layout/Layout';
import Dashboard from './pages/Dashboard';
import Transactions from './pages/Transactions';
import Investments from './pages/Investments';
import Subscriptions from './pages/Subscriptions';
import Income from './pages/Income';
import Categories from './pages/Categories';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/investments" element={<Investments />} />
            <Route path="/subscriptions" element={<Subscriptions />} />
            <Route path="/income" element={<Income />} />
            <Route path="/categories" element={<Categories />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
