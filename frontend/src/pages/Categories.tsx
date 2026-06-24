import { useState, useEffect } from 'react';
import { useQueryClient, useMutation } from '@tanstack/react-query';
import { useCategories } from '../hooks/useCategories';
import { useByCategory } from '../hooks/useAnalytics';
import { useMode } from '../store/demoMode';
import client from '../api/client';
import type { Category } from '../types';
import { formatCurrency } from '../utils/formatters';

const SWATCH_COLORS = [
  '#6366f1', '#06b6d4', '#10b981', '#f59e0b', '#ef4444',
  '#8b5cf6', '#ec4899', '#f97316', '#14b8a6', '#84cc16',
];

const EMOJI: Record<string, string> = {
  Food: '🍕', Transport: '🚗', Groceries: '🛒', Shopping: '🛍️',
  Utilities: '⚡', Health: '💊', Entertainment: '🎬', Travel: '✈️',
};

export default function Categories() {
  const mode = useMode();
  const qc = useQueryClient();
  const { data: categories = [], isLoading } = useCategories();
  const { data: catSpend = [] } = useByCategory(mode);

  const spendMap: Record<string, { total: number; count: number }> = {};
  catSpend.forEach(c => { spendMap[c.category] = { total: c.total, count: 0 }; });

  const [selected, setSelected] = useState<Category | null>(null);
  const [editName, setEditName] = useState('');
  const [editColor, setEditColor] = useState('#6366f1');
  const [editKeywords, setEditKeywords] = useState<string[]>([]);
  const [kwInput, setKwInput] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createColor, setCreateColor] = useState('#6366f1');

  function selectCategory(cat: Category) {
    setSelected(cat);
    setEditName(cat.name);
    setEditColor(cat.color);
    setEditKeywords([...cat.keywords]);
    setKwInput('');
    setShowCreate(false);
  }

  function addKeyword() {
    const kw = kwInput.trim().toLowerCase();
    if (kw && !editKeywords.includes(kw)) {
      setEditKeywords([...editKeywords, kw]);
    }
    setKwInput('');
  }

  function removeKeyword(kw: string) {
    setEditKeywords(editKeywords.filter(k => k !== kw));
  }

  // Auto-select the first category so the editor is never an empty placeholder
  useEffect(() => {
    if (!selected && !showCreate && categories.length) {
      const c = categories[0];
      /* eslint-disable react-hooks/set-state-in-effect */
      setSelected(c);
      setEditName(c.name);
      setEditColor(c.color);
      setEditKeywords([...c.keywords]);
      /* eslint-enable react-hooks/set-state-in-effect */
    }
  }, [categories, selected, showCreate]);

  const saveCategory = useMutation({
    mutationFn: () =>
      client.patch(`/categories/${selected!.id}`, { name: editName, color: editColor, keywords: editKeywords }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories'] });
      qc.invalidateQueries({ queryKey: ['analytics'] });
    },
  });

  const deleteCategory = useMutation({
    mutationFn: () => client.delete(`/categories/${selected!.id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories'] });
      setSelected(null);
    },
  });

  const createCategory = useMutation({
    mutationFn: () => client.post('/categories', { name: createName, color: createColor, keywords: [] }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories'] });
      setShowCreate(false);
      setCreateName('');
      setCreateColor('#6366f1');
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-800 tracking-tight">Categories</h1>
          <p className="text-xs text-slate-400 mt-1">Edit keyword rules, colours and spend groupings</p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setSelected(null); }}
          className="px-4 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors shadow-sm"
        >
          + New Category
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5" style={{ alignItems: 'start' }}>
        {/* Left: category list */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-50 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-700">{categories.length} categories</span>
          </div>
          {isLoading ? (
            <div className="h-48 flex items-center justify-center text-slate-300 text-sm">Loading…</div>
          ) : (
            <div>
              {categories.map((cat) => {
                const spend = spendMap[cat.name];
                return (
                  <button
                    key={cat.id}
                    onClick={() => selectCategory(cat)}
                    className={`w-full flex items-center gap-3 px-5 py-3.5 hover:bg-slate-50 transition-colors text-left ${selected?.id === cat.id ? 'bg-indigo-50' : ''}`}
                  >
                    <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: cat.color }} />
                    <span className="flex-1 text-sm font-medium text-slate-800">{cat.name}</span>
                    <span className="text-xs text-slate-400">{cat.keywords.length} kw</span>
                    {spend && (
                      <span className="text-xs font-semibold text-slate-600">{formatCurrency(spend.total)}</span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: editor */}
        <div className="lg:col-span-2">
          {showCreate ? (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <h3 className="text-base font-bold text-slate-800 mb-5">New Category</h3>
              <div className="space-y-5">
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">Name</label>
                  <input
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm text-slate-800 outline-none focus:border-indigo-400"
                    value={createName}
                    onChange={e => setCreateName(e.target.value)}
                    placeholder="e.g. Subscriptions"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">Colour</label>
                  <div className="flex gap-2 flex-wrap">
                    {SWATCH_COLORS.map(c => (
                      <button
                        key={c}
                        onClick={() => setCreateColor(c)}
                        className="w-7 h-7 rounded-full border-2 transition-transform hover:scale-110"
                        style={{ background: c, borderColor: createColor === c ? '#0f172a' : 'transparent' }}
                      />
                    ))}
                  </div>
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => createCategory.mutate()}
                    disabled={!createName.trim()}
                    className="flex-1 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-40 transition-colors"
                  >
                    Create Category
                  </button>
                  <button
                    onClick={() => setShowCreate(false)}
                    className="px-4 py-2.5 bg-slate-100 text-slate-600 text-sm font-semibold rounded-xl hover:bg-slate-200 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          ) : selected ? (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-3.5 h-3.5 rounded-full flex-shrink-0" style={{ background: editColor }} />
                <h3 className="text-base font-bold text-slate-800">Editing: {selected.name}</h3>
              </div>

              {/* Stats */}
              {spendMap[selected.name] && (
                <div className="grid grid-cols-3 gap-3 mb-6">
                  <div className="bg-slate-50 rounded-xl p-3 text-center">
                    <p className="text-xs text-slate-400 mb-1">Total spend</p>
                    <p className="text-base font-bold text-slate-800">{formatCurrency(spendMap[selected.name].total)}</p>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-3 text-center">
                    <p className="text-xs text-slate-400 mb-1">Keywords</p>
                    <p className="text-base font-bold text-slate-800">{editKeywords.length}</p>
                  </div>
                  <div className="bg-slate-50 rounded-xl p-3 text-center">
                    <p className="text-xs text-slate-400 mb-1">Emoji</p>
                    <p className="text-xl">{EMOJI[selected.name] ?? '💰'}</p>
                  </div>
                </div>
              )}

              <div className="space-y-5">
                {/* Name */}
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">Category name</label>
                  <input
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm text-slate-800 outline-none focus:border-indigo-400"
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                  />
                </div>

                {/* Color */}
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">Colour</label>
                  <div className="flex gap-2 flex-wrap">
                    {SWATCH_COLORS.map(c => (
                      <button
                        key={c}
                        onClick={() => setEditColor(c)}
                        className="w-7 h-7 rounded-full border-2 transition-transform hover:scale-110"
                        style={{ background: c, borderColor: editColor === c ? '#0f172a' : 'transparent' }}
                      />
                    ))}
                  </div>
                </div>

                {/* Keywords */}
                <div>
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">
                    Keywords <span className="font-normal text-slate-400 normal-case">(match on transaction description)</span>
                  </label>
                  <div className="flex flex-wrap gap-2 mb-3">
                    {editKeywords.map(kw => (
                      <span key={kw} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-full text-xs font-medium">
                        {kw}
                        <button onClick={() => removeKeyword(kw)} className="text-indigo-300 hover:text-indigo-600 text-sm leading-none">✕</button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input
                      className="flex-1 px-3 py-2 border border-slate-200 rounded-xl text-sm text-slate-800 outline-none focus:border-indigo-400"
                      placeholder="Add keyword…"
                      value={kwInput}
                      onChange={e => setKwInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && addKeyword()}
                    />
                    <button
                      onClick={addKeyword}
                      className="px-4 py-2 bg-indigo-50 text-indigo-600 text-sm font-semibold rounded-xl hover:bg-indigo-100 transition-colors"
                    >
                      + Add
                    </button>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => saveCategory.mutate()}
                    disabled={saveCategory.isPending}
                    className="flex-1 py-2.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition-colors"
                  >
                    {saveCategory.isPending ? 'Saving…' : 'Save Changes'}
                  </button>
                  <button
                    onClick={() => { if (confirm(`Delete "${selected.name}"?`)) deleteCategory.mutate(); }}
                    className="px-4 py-2.5 border border-rose-200 text-rose-500 text-sm font-semibold rounded-xl hover:bg-rose-50 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 flex items-center justify-center">
              <div className="text-center text-slate-300">
                <svg className="w-10 h-10 mx-auto mb-3" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
                </svg>
                <p className="text-sm">Select a category to edit</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
