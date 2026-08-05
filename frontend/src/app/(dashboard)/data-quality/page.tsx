'use client';

import { useState } from 'react';
import { Shield, CheckCircle, AlertTriangle, Play } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { mlOps } from '@/lib/api';
import { useDatasets } from '@/lib/hooks';
import Link from 'next/link';

export default function DataQualityPage() {
  const { datasets: datasetsList, isLoading: loadingDatasets } = useDatasets();
  const [selectedDataset, setSelectedDataset] = useState<string>('');
  const [report, setReport] = useState<any>(null);
  const [validating, setValidating] = useState(false);

  const handleValidate = async () => {
    if (!selectedDataset) return;
    setValidating(true);
    try {
      const res = await mlOps.validateDataset(selectedDataset);
      setReport(res.data);
    } catch (err) {
      alert('Validation failed');
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Data Quality</h1>
        <p className="text-gray-500 dark:text-gray-400">Validate dataset quality with automated checks</p>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Run Quality Check</h2>
        <div className="flex gap-4">
          <select
            value={selectedDataset}
            onChange={(e) => setSelectedDataset(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white"
          >
            <option value="">{loadingDatasets ? 'Memuat dataset...' : 'Pilih dataset...'}</option>
            {!loadingDatasets && datasetsList.map((ds) => (
              <option key={ds.id} value={ds.id}>{ds.name}</option>
            ))}
          </select>
          <button
            onClick={handleValidate}
            disabled={!selectedDataset || validating}
            className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {validating ? <LoadingSpinner size="sm" /> : <Play className="h-4 w-4" />}
            {validating ? 'Validating...' : 'Validate'}
          </button>
        </div>
      </div>

      {report && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className={`rounded-lg p-4 ${report.status === 'passed' ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20'}`}>
              <p className={`text-sm ${report.status === 'passed' ? 'text-green-600' : 'text-red-600'}`}>Status</p>
              <p className={`text-2xl font-bold ${report.status === 'passed' ? 'text-green-900' : 'text-red-900'}`}>
                {report.status === 'passed' ? 'PASSED' : 'FAILED'}
              </p>
            </div>
            <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-4">
              <p className="text-sm text-blue-600">Score</p>
              <p className="text-2xl font-bold text-blue-900">{report.score}%</p>
            </div>
            <div className="rounded-lg bg-green-50 dark:bg-green-900/20 p-4">
              <p className="text-sm text-green-600">Passed</p>
              <p className="text-2xl font-bold text-green-900">{report.passed_checks}</p>
            </div>
            <div className="rounded-lg bg-red-50 dark:bg-red-900/20 p-4">
              <p className="text-sm text-red-600">Failed</p>
              <p className="text-2xl font-bold text-red-900">{report.failed_checks}</p>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Check Results</h2>
            <div className="space-y-2">
              {report.checks.map((check: any, i: number) => (
                <div key={i} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-700/50 px-4 py-3">
                  <div className="flex items-center gap-3">
                    {check.status === 'passed' ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-red-500" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{check.name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{check.message}</p>
                    </div>
                  </div>
                  <span className={`text-xs font-medium ${check.status === 'passed' ? 'text-green-600' : 'text-red-600'}`}>
                    {check.status.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {!report && !validating && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 py-16">
          <Shield className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-500 dark:text-gray-400">Select a dataset and run validation to see results</p>
        </div>
      )}
    </div>
  );
}
