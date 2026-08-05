'use client';

import { useState, useEffect } from 'react';
import { History, Filter } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { mlOps } from '@/lib/api';
import { AuditLog } from '@/types';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState('');
  const [resourceFilter, setResourceFilter] = useState('');

  useEffect(() => {
    loadLogs();
  }, [actionFilter, resourceFilter]);

  const loadLogs = async () => {
    setLoading(true);
    try {
      const res = await mlOps.auditLogs({
        action: actionFilter || undefined,
        resource_type: resourceFilter || undefined,
        limit: 100,
      });
      setLogs(res.data.items);
    } catch (err) {
      console.error('Failed to load logs');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (d: string) => new Date(d).toLocaleString();

  const actionColors: Record<string, string> = {
    create: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    delete: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    update: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    train: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    deploy: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  };

  const getActionColor = (action: string) => {
    for (const [key, color] of Object.entries(actionColors)) {
      if (action.includes(key)) return color;
    }
    return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Audit Logs</h1>
        <p className="text-gray-500 dark:text-gray-400">Track all system activities and user actions</p>
      </div>

      <div className="flex gap-4">
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white"
        >
          <option value="">All actions</option>
          <option value="create">Create</option>
          <option value="delete">Delete</option>
          <option value="update">Update</option>
          <option value="train">Train</option>
          <option value="deploy">Deploy</option>
          <option value="benchmark">Benchmark</option>
          <option value="export">Export</option>
        </select>
        <select
          value={resourceFilter}
          onChange={(e) => setResourceFilter(e.target.value)}
          className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white"
        >
          <option value="">All resources</option>
          <option value="model">Model</option>
          <option value="dataset">Dataset</option>
          <option value="experiment">Experiment</option>
          <option value="batch_job">Batch Job</option>
        </select>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" className="mx-auto" />
      ) : logs.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 py-16">
          <History className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-500 dark:text-gray-400">No audit logs found</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-sm font-medium text-gray-500 dark:text-gray-400">
                <th className="px-6 py-4">Action</th>
                <th className="px-6 py-4">Resource</th>
                <th className="px-6 py-4">Resource ID</th>
                <th className="px-6 py-4">User</th>
                <th className="px-6 py-4">IP</th>
                <th className="px-6 py-4">Time</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id} className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4">
                    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${getActionColor(log.action)}`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-700 dark:text-gray-300">{log.resource_type}</td>
                  <td className="px-6 py-4 text-xs font-mono text-gray-500 dark:text-gray-400">
                    {log.resource_id ? log.resource_id.slice(0, 8) + '...' : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                    {log.user_id ? log.user_id.slice(0, 8) + '...' : 'system'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">{log.ip_address || '-'}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{formatDate(log.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
