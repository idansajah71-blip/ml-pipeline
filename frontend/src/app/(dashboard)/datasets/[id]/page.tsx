'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Database, Trash2, BarChart3 } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { datasets } from '@/lib/api';
import { Dataset } from '@/types';

export default function DatasetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'preview' | 'stats' | 'columns'>('preview');

  useEffect(() => {
    fetchData();
  }, [params.id]);

  const fetchData = async () => {
    try {
      const [dsRes, previewRes] = await Promise.all([
        datasets.get(params.id as string),
        datasets.preview(params.id as string).catch(() => ({ data: null })),
      ]);
      setDataset(dsRes.data);
      setPreview(previewRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!dataset) return;
    if (!confirm('Delete this dataset?')) return;
    await datasets.delete(dataset.id);
    router.push('/datasets');
  };

  if (loading) {
    return <LoadingSpinner size="lg" className="mx-auto mt-20" />;
  }

  if (!dataset) {
    return (
      <div className="flex flex-col items-center justify-center mt-20">
        <p className="text-gray-500">Dataset not found</p>
        <button onClick={() => router.push('/datasets')} className="mt-4 text-primary-600 hover:underline">
          Back to Datasets
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.push('/datasets')}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Datasets
      </button>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-green-100">
              <Database className="h-7 w-7 text-green-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{dataset.name}</h1>
              <p className="text-gray-500">{dataset.description || 'No description'}</p>
            </div>
          </div>
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-100"
          >
            <Trash2 className="h-4 w-4" />
            Delete
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-500">Rows</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{dataset.rows_count?.toLocaleString() || '-'}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-500">Columns</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{dataset.columns_count || '-'}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-500">Target</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{dataset.target_column || '-'}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-500">File Size</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            {dataset.file_size ? `${(dataset.file_size / 1024).toFixed(1)} KB` : '-'}
          </p>
        </div>
      </div>

      {preview && (
        <div className="rounded-xl border border-gray-200 bg-white">
          <div className="flex border-b border-gray-200">
            {(['preview', 'stats', 'columns'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-3 text-sm font-medium capitalize ${
                  activeTab === tab
                    ? 'border-b-2 border-primary-600 text-primary-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="p-6">
            {activeTab === 'preview' && preview.head && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      {Object.keys(preview.head[0] || {}).map((col) => (
                        <th key={col} className="px-4 py-2 text-left font-medium text-gray-600">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.head.map((row: any, i: number) => (
                      <tr key={i} className="border-b border-gray-100">
                        {Object.values(row).map((val: any, j: number) => (
                          <td key={j} className="px-4 py-2 text-gray-900">
                            {String(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'stats' && preview.statistics && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="px-4 py-2 text-left font-medium text-gray-600">Column</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-600">Type</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-600">Mean</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-600">Std</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-600">Min</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-600">Max</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(preview.statistics).map(([col, stats]: [string, any]) => (
                      <tr key={col} className="border-b border-gray-100">
                        <td className="px-4 py-2 font-medium text-gray-900">{col}</td>
                        <td className="px-4 py-2 text-gray-600">{stats.dtype || '-'}</td>
                        <td className="px-4 py-2 text-gray-600">{stats.mean?.toFixed(2) || '-'}</td>
                        <td className="px-4 py-2 text-gray-600">{stats.std?.toFixed(2) || '-'}</td>
                        <td className="px-4 py-2 text-gray-600">{stats.min?.toFixed(2) || '-'}</td>
                        <td className="px-4 py-2 text-gray-600">{stats.max?.toFixed(2) || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'columns' && (
              <div className="space-y-2">
                {dataset.column_names?.map((col) => (
                  <div key={col} className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2">
                    <span className="font-medium text-gray-900">{col}</span>
                    <span className="text-sm text-gray-500">{dataset.column_types?.[col] || '-'}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
