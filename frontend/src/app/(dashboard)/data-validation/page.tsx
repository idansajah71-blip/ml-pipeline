'use client';

import { useState } from 'react';
import { FileCheck, RefreshCw, CheckCircle, AlertTriangle, XCircle, Info } from 'lucide-react';
import api from '@/lib/api';
import PageHeader from '@/components/PageHeader';

interface CheckResult {
  type: string;
  column?: string;
  status: string;
  severity: string;
  message: string;
  details?: Record<string, any>;
}

interface ValidationResult {
  dataset_name: string;
  row_count: number;
  column_count: number;
  checks: CheckResult[];
  passed: boolean;
  summary: {
    total_checks: number;
    passed: number;
    failed: number;
    warnings: number;
    pass_rate: number;
  };
}

export default function DataValidationPage() {
  const [datasetId, setDatasetId] = useState('');
  const [targetColumn, setTargetColumn] = useState('');
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runValidation = async () => {
    if (!datasetId) return;
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (targetColumn) params.append('target_column', targetColumn);
      const res = await api.post(`/data-validation/${datasetId}/validate?${params.toString()}`);
      setResult(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Gagal menjalankan validasi');
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'warning': return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default: return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Validasi Data"
        description="Validasi kualitas dataset menggunakan Great Expectations"
      />

      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          value={datasetId}
          onChange={(e) => setDatasetId(e.target.value)}
          placeholder="Dataset ID (UUID)"
          className="flex-1 min-w-[200px] rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800"
        />
        <input
          type="text"
          value={targetColumn}
          onChange={(e) => setTargetColumn(e.target.value)}
          placeholder="Target column (opsional)"
          className="flex-1 min-w-[200px] rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-800"
        />
        <button
          onClick={runValidation}
          disabled={!datasetId || loading}
          className="btn-primary flex items-center gap-2"
        >
          {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <FileCheck className="h-4 w-4" />}
          Validasi
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 rounded-lg border p-4 ${
            result.passed ? 'border-green-200 bg-green-50 dark:bg-green-900/20' : 'border-red-200 bg-red-50 dark:bg-red-900/20'
          }">
            {result.passed ? (
              <CheckCircle className="h-6 w-6 text-green-500" />
            ) : (
              <XCircle className="h-6 w-6 text-red-500" />
            )}
            <div>
              <p className="font-semibold">
                {result.passed ? 'Semua validasi lulus' : 'Beberapa validasi gagal'}
              </p>
              <p className="text-sm text-gray-600">
                {result.summary.passed}/{result.summary.total_checks} lulus 
                ({(result.summary.pass_rate * 100).toFixed(1)}%)
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-sm text-gray-500">Total Cek</p>
              <p className="text-2xl font-bold">{result.summary.total_checks}</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-sm text-gray-500">Lulus</p>
              <p className="text-2xl font-bold text-green-600">{result.summary.passed}</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-sm text-gray-500">Gagal</p>
              <p className="text-2xl font-bold text-red-600">{result.summary.failed}</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-sm text-gray-500">Peringatan</p>
              <p className="text-2xl font-bold text-yellow-600">{result.summary.warnings}</p>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
            <div className="border-b border-gray-200 px-4 py-3 dark:border-gray-700">
              <h3 className="font-semibold">Hasil Pemeriksaan</h3>
            </div>
            <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto">
              {result.checks.map((check, i) => (
                <div key={i} className="flex items-start gap-3 px-4 py-3">
                  {getStatusIcon(check.status)}
                  <div className="flex-1">
                    <p className="font-medium">{check.type.replace(/_/g, ' ')}</p>
                    {check.column && <p className="text-sm text-gray-500">Kolom: {check.column}</p>}
                    {check.message && <p className="text-sm text-gray-600 dark:text-gray-400">{check.message}</p>}
                  </div>
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                    check.severity === 'error' ? 'bg-red-100 text-red-700' :
                    check.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {check.severity}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
