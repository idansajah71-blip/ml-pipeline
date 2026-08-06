'use client';

import { useState } from 'react';
import { DollarSign, TrendingUp, Server } from 'lucide-react';
import { costTracking } from '@/lib/api';

export default function CostTrackingPage() {
  const [summary, setSummary] = useState<any>(null);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const res = await costTracking.summary(days);
      setSummary(res.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Cost Tracking</h1>
        <p className="text-gray-500 dark:text-gray-400">Track compute costs per resource</p>
      </div>

      <div className="flex gap-4">
        <select value={days} onChange={e => setDays(Number(e.target.value))}
          className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white">
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
        <button onClick={loadSummary} disabled={loading}
          className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
          <TrendingUp className="h-4 w-4" /> {loading ? 'Loading...' : 'Load Summary'}
        </button>
      </div>

      {summary && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="rounded-lg bg-green-50 p-4 dark:bg-green-900/20">
              <p className="text-sm text-green-600 dark:text-green-400">Total Cost</p>
              <p className="text-2xl font-bold text-green-900 dark:text-green-300">${summary.total_cost_usd}</p>
            </div>
            <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
              <p className="text-sm text-blue-600 dark:text-blue-400">Usage Hours</p>
              <p className="text-2xl font-bold text-blue-900 dark:text-blue-300">{summary.total_usage_hours}h</p>
            </div>
            <div className="rounded-lg bg-purple-50 p-4 dark:bg-purple-900/20">
              <p className="text-sm text-purple-600 dark:text-purple-400">GPU Hours</p>
              <p className="text-2xl font-bold text-purple-900 dark:text-purple-300">{summary.total_gpu_hours}h</p>
            </div>
            <div className="rounded-lg bg-orange-50 p-4 dark:bg-orange-900/20">
              <p className="text-sm text-orange-600 dark:text-orange-400">Cost/Hour</p>
              <p className="text-2xl font-bold text-orange-900 dark:text-orange-300">${summary.cost_per_hour}</p>
            </div>
          </div>

          {Object.keys(summary.by_resource_type || {}).length > 0 && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Cost by Resource Type</h2>
              <div className="space-y-3">
                {Object.entries(summary.by_resource_type).map(([type, data]: [string, any]) => (
                  <div key={type} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-700/50 px-4 py-3">
                    <div className="flex items-center gap-3">
                      <Server className="h-5 w-5 text-gray-400" />
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{type}</span>
                    </div>
                    <div className="flex gap-6 text-sm">
                      <span className="text-gray-500">{data.count} entries</span>
                      <span className="text-gray-500">{data.hours.toFixed(1)}h</span>
                      <span className="font-medium text-gray-900 dark:text-white">${data.cost.toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Object.keys(summary.daily_costs || {}).length > 0 && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Daily Costs</h2>
              <div className="space-y-2">
                {Object.entries(summary.daily_costs).sort().map(([date, cost]: [string, any]) => (
                  <div key={date} className="flex items-center justify-between px-4 py-2">
                    <span className="text-sm text-gray-600 dark:text-gray-300">{date}</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">${cost.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
