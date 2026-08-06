'use client';

import { useState, useEffect } from 'react';
import { LineChart, RefreshCw, ExternalLink, CheckCircle, XCircle, Clock } from 'lucide-react';
import api from '@/lib/api';
import PageHeader from '@/components/PageHeader';

interface MLflowRun {
  run_id: string;
  run_name?: string;
  status: string;
  start_time?: string;
  end_time?: string;
  metrics?: Record<string, number>;
  params?: Record<string, string>;
}

export default function MLflowPage() {
  const [status, setStatus] = useState<any>(null);
  const [runs, setRuns] = useState<MLflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statusRes, runsRes] = await Promise.all([
        api.get('/mlflow/status'),
        api.get('/mlflow/runs?max_results=20'),
      ]);
      setStatus(statusRes.data);
      setRuns(runsRes.data.runs || []);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Gagal memuat data MLflow');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="MLflow Experiment Tracking"
        description="Lacak eksperimen, parameter, metrik, dan model artifacts"
        action={
          <button onClick={fetchData} className="btn-primary flex items-center gap-2">
            <RefreshCw className="h-4 w-4" /> Muat Ulang
          </button>
        }
      />

      {loading ? (
        <div className="space-y-4">
          <div className="h-24 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-64 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
        </div>
      ) : error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-sm text-gray-500">Status</p>
              <p className="mt-1 flex items-center gap-2 text-lg font-semibold">
                {status?.available ? (
                  <><CheckCircle className="h-5 w-5 text-green-500" /> Tersedia</>
                ) : (
                  <><XCircle className="h-5 w-5 text-red-500" /> Tidak Tersedia</>
                )}
              </p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-sm text-gray-500">Tracking URI</p>
              <p className="mt-1 text-lg font-semibold">{status?.tracking_uri || 'default'}</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-sm text-gray-500">Experiment</p>
              <p className="mt-1 text-lg font-semibold">{status?.experiment_name}</p>
            </div>
          </div>

          {!status?.available && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 dark:bg-yellow-900/20">
              <p className="font-medium text-yellow-800 dark:text-yellow-300">MLflow belum terinstall</p>
              <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-400">
                Install dengan: <code className="rounded bg-yellow-100 px-1 py-0.5 dark:bg-yellow-800">pip install mlflow</code>
              </p>
            </div>
          )}

          <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
            <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
              <h3 className="font-semibold">Riwayat Run</h3>
            </div>
            {runs.length === 0 ? (
              <div className="p-8 text-center text-gray-500">
                <LineChart className="mx-auto mb-2 h-8 w-8 opacity-50" />
                <p>Belum ada run tercatat</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {runs.map((run, i) => (
                  <div key={run.run_id || i} className="flex items-center justify-between px-4 py-3">
                    <div>
                      <p className="font-medium">{run.run_name || run.run_id?.slice(0, 8)}</p>
                      <p className="text-xs text-gray-500">
                        {run.start_time && new Date(run.start_time).toLocaleString('id-ID')}
                      </p>
                    </div>
                    <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                      run.status === 'FINISHED' ? 'bg-green-100 text-green-700' :
                      run.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {run.status === 'FINISHED' ? 'Selesai' :
                       run.status === 'FAILED' ? 'Gagal' : run.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
