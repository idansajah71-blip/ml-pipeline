'use client';

import { useState } from 'react';
import { Upload, Trash2, Eye, Database } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { datasets } from '@/lib/api';
import { useDatasets } from '@/lib/hooks';
import Link from 'next/link';

export default function DatasetsPage() {
  const { datasets: datasetsList, isLoading, mutate } = useDatasets();
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [formData, setFormData] = useState({ name: '', description: '', target_column: '' });

  const handleUpload = async () => {
    if (!selectedFile || !formData.name) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('name', formData.name);
      fd.append('description', formData.description);
      fd.append('target_column', formData.target_column);
      await datasets.upload(fd);
      setSelectedFile(null);
      setFormData({ name: '', description: '', target_column: '' });
      mutate();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      alert(message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this dataset?')) return;
    await datasets.delete(id);
    mutate();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Datasets</h1>
          <p className="text-gray-500">Upload and manage your datasets</p>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold">Upload Dataset</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <input
            type="text"
            placeholder="Dataset Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          />
          <input
            type="text"
            placeholder="Target Column (optional)"
            value={formData.target_column}
            onChange={(e) => setFormData({ ...formData, target_column: e.target.value })}
            className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          />
          <div className="flex gap-2">
            <input
              type="file"
              accept=".csv,.xls,.xlsx"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              className="flex-1 text-sm text-gray-500 file:mr-4 file:rounded-lg file:border-0 file:bg-primary-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-primary-700 hover:file:bg-primary-100"
            />
            <button
              onClick={handleUpload}
              disabled={uploading || !selectedFile || !formData.name}
              className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </div>
      </div>

      {isLoading ? (
        <LoadingSpinner size="lg" className="mx-auto" />
      ) : datasetsList.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16">
          <Database className="mb-4 h-12 w-12 text-gray-300" />
          <p className="text-gray-500">No datasets yet. Upload your first dataset above!</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 text-left text-sm font-medium text-gray-500">
                <th className="px-6 py-4">Name</th>
                <th className="px-6 py-4">Rows</th>
                <th className="px-6 py-4">Columns</th>
                <th className="px-6 py-4">Target</th>
                <th className="px-6 py-4">Tags</th>
                <th className="px-6 py-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {datasetsList.map((ds) => (
                <tr key={ds.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <p className="font-medium text-gray-900">{ds.name}</p>
                    <p className="text-xs text-gray-500">{ds.description || 'No description'}</p>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">{ds.rows_count?.toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{ds.columns_count}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{ds.target_column || '-'}</td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {ds.tags?.map((tag) => (
                        <span key={tag} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{tag}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/datasets/${ds.id}`}
                        className="text-primary-600 hover:text-primary-800"
                      >
                        <Eye className="h-4 w-4" />
                      </Link>
                      <button onClick={() => handleDelete(ds.id)} className="text-red-500 hover:text-red-700">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
