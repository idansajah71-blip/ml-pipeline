'use client';

import { useState, useMemo } from 'react';
import { Search, ArrowLeft, Info, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { ALGORITHMS, REGRESSION_ALGORITHMS } from '@/lib/algorithms';
import { NEED_SCENARIOS } from '@/lib/recommendations';

type ProblemType = 'all' | 'classification' | 'regression';

export default function PanduanAlgoritmaPage() {
  const [search, setSearch] = useState('');
  const [problemFilter, setProblemFilter] = useState<ProblemType>('all');

  const filteredScenarios = useMemo(() => {
    return NEED_SCENARIOS.filter((s) => {
      const matchesType = problemFilter === 'all' || s.problemType === problemFilter;
      const q = search.toLowerCase();
      const matchesSearch = !q || s.need.toLowerCase().includes(q) || s.description.toLowerCase().includes(q) || s.tags.some((t) => t.includes(q));
      return matchesType && matchesSearch;
    });
  }, [search, problemFilter]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <Link href="/" className="mb-6 inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200">
          <ArrowLeft className="h-4 w-4" /> Kembali ke dasbor
        </Link>

        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Panduan Algoritma</h1>
          <p className="mt-1 text-gray-500">Temukan algoritma yang tepat berdasarkan kebutuhan Anda</p>
        </div>

        {/* Search & Filter */}
        <div className="mb-6 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Ketik kebutuhan Anda (contoh: harga, churn, spam)..."
              className="w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
            />
          </div>
          <div className="flex gap-2">
            {([
              { value: 'all', label: 'Semua' },
              { value: 'classification', label: 'Klasifikasi' },
              { value: 'regression', label: 'Regresi' },
            ] as const).map((opt) => (
              <button
                key={opt.value}
                onClick={() => setProblemFilter(opt.value)}
                className={`rounded-lg px-4 py-2.5 text-sm font-medium transition-colors ${
                  problemFilter === opt.value
                    ? 'bg-primary-600 text-white'
                    : 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Scenarios */}
        <div className="space-y-4">
          {filteredScenarios.length === 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-8 text-center dark:border-gray-700 dark:bg-gray-800">
              <p className="text-gray-500">Tidak ada skenario yang cocok dengan pencarian Anda.</p>
              <p className="mt-1 text-sm text-gray-400">Coba kata kunci lain atau lihat semua skenario.</p>
            </div>
          )}

          {filteredScenarios.map((scenario) => {
            const algoList = scenario.problemType === 'classification' ? ALGORITHMS : REGRESSION_ALGORITHMS;
            return (
              <div key={scenario.id} className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
                <div className="mb-3 flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{scenario.need}</h3>
                    <p className="mt-1 text-sm text-gray-500">{scenario.description}</p>
                  </div>
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    scenario.problemType === 'classification'
                      ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                      : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                  }`}>
                    {scenario.problemType === 'classification' ? 'Klasifikasi' : 'Regresi'}
                  </span>
                </div>

                <div className="mb-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-900/50">
                  <p className="text-xs font-medium text-gray-500 mb-1">Contoh kasus:</p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{scenario.exampleUseCase}</p>
                </div>

                <div>
                  <p className="mb-2 text-xs font-medium text-gray-500">Algoritma yang disarankan:</p>
                  <div className="flex flex-wrap gap-2">
                    {scenario.suggestedAlgorithms.map((algoKey) => {
                      const info = algoList[algoKey];
                      if (!info) return null;
                      return (
                        <div key={algoKey} className="group relative">
                          <span className="inline-flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:border-primary-300 hover:bg-primary-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300">
                            <CheckCircle2 className="h-3 w-3 text-green-500" />
                            {info.label}
                          </span>
                          <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 whitespace-normal rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-600 shadow-lg opacity-0 transition-opacity group-hover:opacity-100 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 w-64">
                            <p className="font-medium text-gray-900 dark:text-white mb-1">{info.label}</p>
                            <p>{info.description}</p>
                            <p className="mt-1 text-primary-600 dark:text-primary-400">Cocok untuk: {info.bestFor}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Limitations notice */}
        <div className="mt-8 rounded-xl border border-amber-200 bg-amber-50 p-5 dark:border-amber-800 dark:bg-amber-900/20">
          <div className="flex gap-3">
            <Info className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-amber-800 dark:text-amber-200">Fitur yang belum tersedia</h3>
              <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                Saat ini platform hanya mendukung <strong>klasifikasi</strong> dan <strong>regresi</strong> pada data tabular.
                Fitur <strong>clustering</strong> (pengelompokan) dan <strong>time series</strong> (prediksi deret waktu) belum tersedia.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
