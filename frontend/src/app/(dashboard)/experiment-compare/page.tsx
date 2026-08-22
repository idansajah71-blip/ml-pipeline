'use client';

import { useState, useEffect } from 'react';
import { Trophy, ArrowRight } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useToast } from '@/components/Toast';
import { experimentCompare, experiments } from '@/lib/api';

export default function ExperimentComparePage() {
  const { toast } = useToast();
  const [experimentList, setExperimentList] = useState<any[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<any>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);

  useEffect(() => { loadExperiments(); loadLeaderboard(); }, []);

  const loadExperiments = async () => {
    try {
      const res = await experiments.list();
      setExperimentList(res.data.items || []);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const loadLeaderboard = async () => {
    try {
      const res = await experimentCompare.leaderboard();
      setLeaderboard(res.data.leaderboard || []);
    } catch (err) { console.error(err); }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : prev.length < 5 ? [...prev, id] : prev
    );
  };

  const handleCompare = async () => {
    if (selectedIds.length < 2) return;
    setComparing(true);
    try {
      const res = await experimentCompare.compare(selectedIds);
      setComparison(res.data);
    } catch (err) { toast('error', 'Gagal membandingkan experiment'); }
    setComparing(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Perbandingan Eksperimen</h1>
        <p className="text-gray-500 dark:text-gray-400">Bandingkan beberapa eksperimen dan lihat papan peringkat</p>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Pilih Eksperimen (2–5)</h2>
        {loading ? <LoadingSpinner size="sm" /> : (
          <>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2 mb-4 max-h-64 overflow-auto">
              {experimentList.map(exp => (
                <button key={exp.id} onClick={() => toggleSelect(exp.id)}
                  className={`flex items-center justify-between rounded-lg px-4 py-3 text-left text-sm ${
                    selectedIds.includes(exp.id) ? 'bg-primary-50 dark:bg-primary-900/30 border-2 border-primary-500' : 'bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100'
                  }`}>
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{exp.name}</p>
                    <p className="text-xs text-gray-500">{exp.results?.algorithm || 'tidak diketahui'}</p>
                  </div>
                  <span className="text-xs text-gray-500">{new Date(exp.created_at).toLocaleDateString('id-ID')}</span>
                </button>
              ))}
            </div>
            <button onClick={handleCompare} disabled={selectedIds.length < 2 || comparing}
              className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
              {comparing ? 'Membandingkan...' : `Bandingkan ${selectedIds.length} Eksperimen`}
              <ArrowRight className="h-4 w-4" />
            </button>
          </>
        )}
      </div>

      {comparison && (
        <div className="space-y-6">
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Hasil Perbandingan</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="px-4 py-2 text-left font-medium text-gray-500">Eksperimen</th>
                    <th className="px-4 py-2 text-left font-medium text-gray-500">Algoritma</th>
                    {Object.keys(comparison.metric_comparison).map(metric => (
                      <th key={metric} className="px-4 py-2 text-left font-medium text-gray-500">{metric}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {comparison.experiments.map((exp: any) => (
                    <tr key={exp.id} className="border-b border-gray-100 dark:border-gray-700">
                      <td className="px-4 py-2 font-medium text-gray-900 dark:text-white">{exp.name}</td>
                      <td className="px-4 py-2 text-gray-600 dark:text-gray-300">{exp.algorithm}</td>
                      {Object.keys(comparison.metric_comparison).map(metric => (
                        <td key={metric} className="px-4 py-2">
                          <span className={`text-sm font-medium ${
                            comparison.best_by_metric[metric]?.experiment_id === exp.id
                              ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-gray-300'
                          }`}>
                            {exp.metrics[metric]?.toFixed(4) || '-'}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {Object.entries(comparison.metric_comparison).map(([metric, stats]: [string, any]) => (
              <div key={metric} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{metric}</p>
                <div className="mt-2 flex justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-300">Min: {stats.min.toFixed(4)}</span>
                  <span className="text-gray-600 dark:text-gray-300">Max: {stats.max.toFixed(4)}</span>
                </div>
                <div className="mt-1 text-center text-lg font-bold text-gray-900 dark:text-white">{stats.mean.toFixed(4)}</div>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Spread: {stats.spread.toFixed(4)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Trophy className="h-5 w-5 text-yellow-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Papan Peringkat</h2>
        </div>
        {leaderboard.length === 0 ? (
          <p className="text-sm text-gray-500">Belum ada eksperimen selesai</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-left">
                <th className="px-4 py-2 font-medium text-gray-500">#</th>
                <th className="px-4 py-2 font-medium text-gray-500">Eksperimen</th>
                <th className="px-4 py-2 font-medium text-gray-500">Algoritma</th>
                <th className="px-4 py-2 font-medium text-gray-500">Akurasi</th>
                <th className="px-4 py-2 font-medium text-gray-500">F1 Macro</th>
              </tr>
            </thead>
            <tbody>
              {leaderboard.map((entry, i) => (
                <tr key={entry.experiment_id} className="border-b border-gray-100 dark:border-gray-700">
                  <td className="px-4 py-2 font-bold text-gray-900 dark:text-white">{i + 1}</td>
                  <td className="px-4 py-2 text-gray-900 dark:text-white">{entry.name}</td>
                  <td className="px-4 py-2 text-gray-600 dark:text-gray-300">{entry.algorithm}</td>
                  <td className="px-4 py-2 text-gray-600 dark:text-gray-300">{(entry.accuracy * 100).toFixed(1)}%</td>
                  <td className="px-4 py-2 text-gray-600 dark:text-gray-300">{(entry.f1_macro * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
