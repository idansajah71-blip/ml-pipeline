'use client';

import { useState, useEffect } from 'react';
import { X, Table } from 'lucide-react';
import { datasets } from '@/lib/api';
import LoadingSpinner from './LoadingSpinner';

interface PreviewModalProps {
  datasetId: string;
  datasetName: string;
  onClose: () => void;
}

interface PreviewData {
  columns: string[];
  rows: Record<string, any>[];
  total_rows: number;
}

export default function DatasetPreviewModal({ datasetId, datasetName, onClose }: PreviewModalProps) {
  const [data, setData] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchPreview = async () => {
      try {
        const res = await datasets.preview(datasetId);
        setData(res.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load preview');
      } finally {
        setLoading(false);
      }
    };
    fetchPreview();
  }, [datasetId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="max-h-[80vh] w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-100">
              <Table className="h-5 w-5 text-primary-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{datasetName}</h2>
              <p className="text-sm text-gray-500">Preview</p>
            </div>
          </div>
          <button onClick={onClose} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="overflow-auto p-6">
          {loading ? (
            <div className="flex h-48 items-center justify-center">
              <LoadingSpinner size="lg" />
            </div>
          ) : error ? (
            <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</div>
          ) : data ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    {data.columns.map((col) => (
                      <th key={col} className="px-4 py-2 text-left font-medium text-gray-600">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row, i) => (
                    <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                      {data.columns.map((col) => (
                        <td key={col} className="px-4 py-2 text-gray-700">
                          {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-4 text-center text-sm text-gray-500">
                Showing {data.rows.length} of {data.total_rows.toLocaleString()} rows
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
