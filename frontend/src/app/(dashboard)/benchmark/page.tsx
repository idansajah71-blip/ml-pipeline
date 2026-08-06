'use client';

import { useState, useEffect } from 'react';
import { BarChart, RefreshCw, Activity, Clock, HardDrive, TrendingUp } from 'lucide-react';
import api from '@/lib/api';
import PageHeader from '@/components/PageHeader';

interface BenchmarkResult {
  algorithm: string;
  problem_type: string;
  metrics: Record<string, any>;
  inference: {
    mean_latency_ms: number;
    p95_latency_ms: number;
    p99_latency_ms: number;
  };
  model_size_mb: number;
  feature_importance: Record<string, number> | null;
  primary_metric: string;
  primary_metric_value: number;
  benchmark_timestamp: string;
}

export default function BenchmarkPage() {
  const [modelId, setModelId] = useState('');
  const [result, setResult] = useState<BenchmarkResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runBenchmark = async () => {
    if (!modelId) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.post(`/benchmark/${modelId}`);
      setResult(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Gagal menjalankan benchmark');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Model Benchmark"
        description="Uji performa model: metrik evaluasi, latensi inferensi, dan ukuran model"
      />

      <div className="flex gap-3">
        <input
          type="text"
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
          placeholder="Masukkan Model ID (UUID)"
          className="flex-1 rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800"
        />
        <button
          onClick={runBenchmark}
          disabled={!modelId || loading}
          className="btn-primary flex items-center gap-2"
        >
          {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <BarChart className="h-4 w-4" />}
          Jalankan Benchmark
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <TrendingUp className="h-4 w-4" /> Metrik Utama
              </div>
              <p className="mt-1 text-2xl font-bold">{result.primary_metric}</p>
              <p className="text-lg font-semibold text-primary-600">
                {(result.primary_metric_value * 100).toFixed(2)}%
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Clock className="h-4 w-4" /> Latensi Rata-rata
              </div>
              <p className="mt-1 text-2xl font-bold">{result.inference?.mean_latency_ms?.toFixed(2)} ms</p>
              <p className="text-xs text-gray-500">P95: {result.inference?.p95_latency_ms?.toFixed(2)} ms</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <HardDrive className="h-4 w-4" /> Ukuran Model
              </div>
              <p className="mt-1 text-2xl font-bold">{result.model_size_mb} MB</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Activity className="h-4 w-4" /> Algoritma
              </div>
              <p className="mt-1 text-2xl font-bold capitalize">{result.algorithm?.replace('_', ' ')}</p>
              <p className="text-xs text-gray-500">{result.problem_type}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="mb-3 font-semibold">Metrik Evaluasi</h3>
              <div className="space-y-2">
                {Object.entries(result.metrics || {}).filter(([k]) => !['confusion_matrix', 'classification_report'].includes(k)).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">{key}</span>
                    <span className="font-mono text-sm">
                      {typeof value === 'number' ? value.toFixed(4) : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="mb-3 font-semibold">Statistik Latensi</h3>
              <div className="space-y-2">
                {Object.entries(result.inference || {}).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">{key}</span>
                    <span className="font-mono text-sm">{typeof value === 'number' ? value.toFixed(3) : String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {result.feature_importance && Object.keys(result.feature_importance).length > 0 && (
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <h3 className="mb-3 font-semibold">Feature Importance</h3>
              <div className="space-y-2">
                {Object.entries(result.feature_importance).slice(0, 15).map(([name, importance]) => (
                  <div key={name} className="flex items-center gap-3">
                    <span className="w-48 text-sm truncate">{name}</span>
                    <div className="flex-1">
                      <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-700">
                        <div
                          className="h-2 rounded-full bg-primary-500"
                          style={{ width: `${Math.min((importance as number) * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                    <span className="font-mono text-xs w-16 text-right">{(importance as number).toFixed(4)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
