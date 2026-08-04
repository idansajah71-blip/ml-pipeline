'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Zap, Trophy, Loader2 } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { models, datasets as datasetsApi } from '@/lib/api';
import { useDatasets, useAlgorithms } from '@/lib/hooks';
import { Dataset } from '@/types';

export default function AutoMLPage() {
  const router = useRouter();
  const { datasets: datasetList, isLoading: datasetsLoading } = useDatasets();
  const { algorithms: algoList, isLoading: algosLoading } = useAlgorithms();
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [targetColumn, setTargetColumn] = useState<string>('');
  const [selectedAlgos, setSelectedAlgos] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<string>('');
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    if (!taskId || !running) return;

    const interval = setInterval(async () => {
      try {
        const res = await models.taskStatus(taskId);
        const data = res.data;
        setProgress(data.progress || 0);
        setStatus(data.status);

        if (data.status === 'SUCCESS') {
          setResult(data.result);
          setRunning(false);
          clearInterval(interval);
        } else if (data.status === 'FAILURE') {
          setRunning(false);
          clearInterval(interval);
          alert('AutoML failed: ' + (data.result?.error || 'Unknown error'));
        }
      } catch {}
    }, 2000);

    return () => clearInterval(interval);
  }, [taskId, running]);

  const handleRunAutoML = async () => {
    if (!selectedDataset || !targetColumn) return;
    setRunning(true);
    setResult(null);
    try {
      const res = await models.automl({
        dataset_id: selectedDataset,
        target_column: targetColumn,
        algorithms: selectedAlgos.length > 0 ? selectedAlgos : undefined,
      });
      setTaskId(res.data.task_id);
    } catch (err: any) {
      setRunning(false);
      alert(err?.response?.data?.detail || 'Failed to start AutoML');
    }
  };

  const toggleAlgo = (algo: string) => {
    setSelectedAlgos((prev) =>
      prev.includes(algo) ? prev.filter((a) => a !== algo) : [...prev, algo]
    );
  };

  if (datasetsLoading || algosLoading) {
    return <LoadingSpinner size="lg" className="mx-auto mt-20" />;
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.push('/models')}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Models
      </button>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-yellow-100">
            <Zap className="h-6 w-6 text-yellow-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AutoML</h1>
            <p className="text-gray-500">Otomatis bandingkan semua algoritma dan temukan yang terbaik</p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Dataset</label>
              <select
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm"
                value={selectedDataset}
                onChange={(e) => setSelectedDataset(e.target.value)}
              >
                <option value="">Select dataset...</option>
                {datasetList.map((d: Dataset) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.rows_count || '?'} rows)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Target Column</label>
              <input
                type="text"
                className="w-full rounded-lg border border-gray-300 px-4 py-2 text-sm"
                placeholder="e.g. species"
                value={targetColumn}
                onChange={(e) => setTargetColumn(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Algorithms {selectedAlgos.length > 0 && `(${selectedAlgos.length} selected)`}
              </label>
              <div className="flex flex-wrap gap-2">
                {algoList.map((algo) => (
                  <button
                    key={algo}
                    onClick={() => toggleAlgo(algo)}
                    className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                      selectedAlgos.includes(algo)
                        ? 'bg-primary-100 text-primary-700 border border-primary-300'
                        : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'
                    }`}
                  >
                    {algo}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-xs text-gray-500">Kosongkan untuk menjalankan semua algoritma</p>
            </div>

            <button
              onClick={handleRunAutoML}
              disabled={running || !selectedDataset || !targetColumn}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-yellow-600 px-4 py-3 text-sm font-medium text-white hover:bg-yellow-700 disabled:opacity-50"
            >
              {running ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running AutoML... {progress}%
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  Run AutoML
                </>
              )}
            </button>
          </div>

          {running && (
            <div className="flex flex-col items-center justify-center">
              <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
                <div
                  className="bg-yellow-500 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-sm text-gray-600">{status}</p>
            </div>
          )}

          {result && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-yellow-500" />
                <h3 className="font-semibold text-gray-900">Best: {result.best_algorithm}</h3>
              </div>

              <div className="space-y-2 max-h-96 overflow-y-auto">
                {result.results?.map((r: any, i: number) => (
                  <div
                    key={i}
                    className={`rounded-lg border p-4 ${
                      i === 0 ? 'border-yellow-300 bg-yellow-50' : 'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-900">{r.algorithm}</span>
                      {i === 0 && (
                        <span className="rounded-full bg-yellow-200 px-2 py-0.5 text-xs font-medium text-yellow-800">
                          BEST
                        </span>
                      )}
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-sm">
                      {r.metrics?.accuracy != null && (
                        <div>
                          <span className="text-gray-500">Accuracy</span>
                          <p className="font-semibold">{(r.metrics.accuracy * 100).toFixed(1)}%</p>
                        </div>
                      )}
                      {r.metrics?.f1_macro != null && (
                        <div>
                          <span className="text-gray-500">F1</span>
                          <p className="font-semibold">{(r.metrics.f1_macro * 100).toFixed(1)}%</p>
                        </div>
                      )}
                      {r.duration_seconds != null && (
                        <div>
                          <span className="text-gray-500">Time</span>
                          <p className="font-semibold">{r.duration_seconds}s</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
