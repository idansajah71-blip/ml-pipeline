'use client';

import { useState, useEffect } from 'react';
import { Layers, Download, Clock, CheckCircle, XCircle, Loader } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { mlOps } from '@/lib/api';
import { BatchJob } from '@/types';

export default function BatchJobsPage() {
  const [jobs, setJobs] = useState<BatchJob[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    setLoading(true);
    try {
      const res = await mlOps.listBatchJobs();
      setJobs(res.data.items);
    } catch (err) {
      console.error('Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed': return <XCircle className="h-5 w-5 text-red-500" />;
      case 'running': return <Loader className="h-5 w-5 text-blue-500 animate-spin" />;
      default: return <Clock className="h-5 w-5 text-gray-400" />;
    }
  };

  const formatDate = (d: string | null) => d ? new Date(d).toLocaleString() : '-';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Batch Predictions</h1>
        <p className="text-gray-500 dark:text-gray-400">Run bulk predictions and download results</p>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" className="mx-auto" />
      ) : jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 py-16">
          <Layers className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-500 dark:text-gray-400">No batch jobs yet</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-sm font-medium text-gray-500 dark:text-gray-400">
                <th className="px-6 py-4">Name</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Progress</th>
                <th className="px-6 py-4">Avg Latency</th>
                <th className="px-6 py-4">Created</th>
                <th className="px-6 py-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4">
                    <p className="font-medium text-gray-900 dark:text-white">{job.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">ID: {job.id.slice(0, 8)}</p>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {statusIcon(job.status)}
                      <span className="text-sm capitalize text-gray-700 dark:text-gray-300">{job.status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-primary-500 h-2 rounded-full"
                          style={{ width: `${job.total_rows > 0 ? (job.processed_rows / job.total_rows) * 100 : 0}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {job.processed_rows}/{job.total_rows}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                    {job.avg_latency_ms > 0 ? `${job.avg_latency_ms}ms` : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{formatDate(job.created_at)}</td>
                  <td className="px-6 py-4">
                    {job.status === 'completed' && (
                      <a
                        href={mlOps.batchJobDownload(job.id)}
                        className="flex items-center gap-1 text-primary-600 hover:text-primary-800 text-sm"
                      >
                        <Download className="h-4 w-4" />
                        Download
                      </a>
                    )}
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
