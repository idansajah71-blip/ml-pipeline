'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Brain, Database, FlaskConical, X, ArrowRight, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { models as modelsApi, datasets as datasetsApi, experiments as experimentsApi } from '@/lib/api';
import { useDebounce } from '@/lib/useDebounce';

interface SearchResult {
  id: string;
  type: 'model' | 'dataset' | 'experiment';
  name: string;
  sub: string;
  href: string;
}

const TYPE_META = {
  model:      { icon: Brain,      label: 'Model',      color: 'text-purple-500' },
  dataset:    { icon: Database,   label: 'Dataset',    color: 'text-blue-500'   },
  experiment: { icon: FlaskConical, label: 'Eksperimen', color: 'text-green-500' },
};

export default function GlobalSearch() {
  const router = useRouter();
  const [open, setOpen]   = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebounce(query, 250);

  // ── Cmd/Ctrl+K to open ──────────────────────────────────────────────────
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((p) => !p);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  useEffect(() => {
    if (open) { setTimeout(() => inputRef.current?.focus(), 50); setQuery(''); setResults([]); }
  }, [open]);

  // ── Search across all entities ─────────────────────────────────────────
  useEffect(() => {
    if (!debouncedQuery.trim()) { setResults([]); return; }
    const q = debouncedQuery.toLowerCase();
    setLoading(true);

    Promise.allSettled([
      modelsApi.list(),
      datasetsApi.list(),
      experimentsApi.list(),
    ]).then(([mRes, dRes, eRes]) => {
      const out: SearchResult[] = [];

      if (mRes.status === 'fulfilled') {
        (mRes.value.data.items ?? [])
          .filter((m: any) => m.name?.toLowerCase().includes(q) || m.algorithm?.toLowerCase().includes(q))
          .slice(0, 4)
          .forEach((m: any) => out.push({
            id: m.id, type: 'model',
            name: m.name,
            sub: `${m.algorithm} · v${m.version} · ${m.status}`,
            href: `/models/${m.id}`,
          }));
      }
      if (dRes.status === 'fulfilled') {
        (Array.isArray(dRes.value.data) ? dRes.value.data : [])
          .filter((d: any) => d.name?.toLowerCase().includes(q))
          .slice(0, 3)
          .forEach((d: any) => out.push({
            id: d.id, type: 'dataset',
            name: d.name,
            sub: `${d.rows_count?.toLocaleString('id-ID') ?? '?'} baris · ${d.columns_count ?? '?'} kolom`,
            href: `/datasets/${d.id}`,
          }));
      }
      if (eRes.status === 'fulfilled') {
        (eRes.value.data.items ?? [])
          .filter((e: any) => e.name?.toLowerCase().includes(q))
          .slice(0, 3)
          .forEach((e: any) => out.push({
            id: e.id, type: 'experiment',
            name: e.name,
            sub: e.status,
            href: `/experiments`,
          }));
      }

      setResults(out);
      setActive(0);
    }).finally(() => setLoading(false));
  }, [debouncedQuery]);

  const navigate = useCallback((href: string) => {
    setOpen(false);
    router.push(href);
  }, [router]);

  // ── Keyboard navigation ─────────────────────────────────────────────────
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((p) => Math.min(p + 1, results.length - 1)); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setActive((p) => Math.max(p - 1, 0)); }
    if (e.key === 'Enter' && results[active]) navigate(results[active].href);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500 transition-colors hover:border-gray-300 hover:bg-white dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
        aria-label="Cari (Ctrl+K)"
      >
        <Search className="h-4 w-4" />
        <span className="hidden sm:inline">Cari di sini...</span>
        <kbd className="hidden rounded border border-gray-200 bg-white px-1.5 py-0.5 text-xs text-gray-400 dark:border-gray-600 dark:bg-gray-700 sm:inline">
          ⌘K
        </kbd>
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[10vh] px-4" role="dialog" aria-modal="true" aria-label="Pencarian global">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setOpen(false)} />

      {/* Modal */}
      <div className="relative w-full max-w-xl overflow-hidden rounded-2xl bg-white shadow-2xl dark:bg-gray-900">
        {/* Input */}
        <div className="flex items-center gap-3 border-b border-gray-200 px-4 py-3 dark:border-gray-700">
          {loading
            ? <Loader2 className="h-5 w-5 shrink-0 animate-spin text-gray-400" />
            : <Search className="h-5 w-5 shrink-0 text-gray-400" />}
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Cari model, dataset, eksperimen..."
            className="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-400 focus:outline-none dark:text-white dark:placeholder-gray-500"
          />
          <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Results */}
        {results.length > 0 ? (
          <ul className="max-h-72 divide-y divide-gray-100 overflow-y-auto dark:divide-gray-800">
            {results.map((r, i) => {
              const { icon: Icon, label, color } = TYPE_META[r.type];
              return (
                <li key={r.id}>
                  <button
                    onClick={() => navigate(r.href)}
                    onMouseEnter={() => setActive(i)}
                    className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors ${
                      i === active ? 'bg-primary-50 dark:bg-primary-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                    }`}
                  >
                    <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800`}>
                      <Icon className={`h-4 w-4 ${color}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-gray-900 dark:text-white">{r.name}</p>
                      <p className="truncate text-xs text-gray-500 dark:text-gray-400">{label} · {r.sub}</p>
                    </div>
                    <ArrowRight className={`h-4 w-4 shrink-0 ${i === active ? 'text-primary-500' : 'text-transparent'}`} />
                  </button>
                </li>
              );
            })}
          </ul>
        ) : query.trim() && !loading ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
            Tidak ada hasil untuk <span className="font-medium text-gray-700 dark:text-gray-300">"{query}"</span>
          </div>
        ) : !query.trim() ? (
          <div className="px-4 py-6 text-center text-xs text-gray-400 dark:text-gray-500">
            Ketik untuk mencari lintas model, dataset, dan eksperimen
          </div>
        ) : null}

        {/* Footer hint */}
        <div className="border-t border-gray-100 px-4 py-2 dark:border-gray-800">
          <p className="text-xs text-gray-400 dark:text-gray-500">
            ↑↓ navigasi · Enter pilih · Esc tutup
          </p>
        </div>
      </div>
    </div>
  );
}
