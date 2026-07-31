'use client';

import { useEffect, useState } from 'react';
import { BarChart3, Cpu, HardDrive, MemoryStick } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import LoadingSpinner from '@/components/LoadingSpinner';
import { monitoring } from '@/lib/api';

const COLORS = ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B', '#EF4444', '#6366F1'];

export default function MonitoringPage() {
  const [stats, setStats] = useState<any>(null);
  const [system, setSystem] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, systemRes] = await Promise.all([
          monitoring.stats().catch(() => ({ data: null })),
          monitoring.system().catch(() => ({ data: null })),
        ]);
        setStats(statsRes.data);
        setSystem(systemRes.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const statsChartData = stats
    ? Object.entries(stats).map(([key, value]) => ({
        name: key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
        value: Number(value),
      }))
    : [];

  const systemChartData = system
    ? [
        { name: 'CPU', value: system.cpu_percent || 0, color: '#3B82F6' },
        { name: 'Memory', value: system.memory?.percent || 0, color: '#8B5CF6' },
        { name: 'Disk', value: system.disk?.percent || 0, color: '#10B981' },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Monitoring</h1>
        <p className="text-gray-500">System and model performance metrics</p>
      </div>

      {stats && (
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold">Pipeline Stats</h2>
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(stats).map(([key, value]) => (
              <div key={key} className="rounded-lg bg-gray-50 p-4">
                <p className="text-sm text-gray-500">{key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}</p>
                <p className="mt-1 text-2xl font-semibold text-gray-900">{String(value)}</p>
              </div>
            ))}
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statsChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="value" fill="#3B82F6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {system && (
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold">System Resources</h2>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div className="space-y-4">
              <div className="rounded-lg bg-gray-50 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <Cpu className="h-5 w-5 text-blue-600" />
                  <p className="text-sm font-medium text-gray-700">CPU</p>
                  <span className="ml-auto text-lg font-semibold">{system.cpu_percent}%</span>
                </div>
                <div className="h-2 rounded-full bg-gray-200">
                  <div
                    className={`h-2 rounded-full transition-all ${system.cpu_percent > 80 ? 'bg-red-500' : system.cpu_percent > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${system.cpu_percent}%` }}
                  />
                </div>
              </div>

              <div className="rounded-lg bg-gray-50 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <MemoryStick className="h-5 w-5 text-purple-600" />
                  <p className="text-sm font-medium text-gray-700">Memory</p>
                  <span className="ml-auto text-lg font-semibold">{system.memory?.percent}%</span>
                </div>
                <div className="h-2 rounded-full bg-gray-200">
                  <div
                    className={`h-2 rounded-full transition-all ${system.memory?.percent > 80 ? 'bg-red-500' : system.memory?.percent > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${system.memory?.percent || 0}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  {((system.memory?.available || 0) / 1073741824).toFixed(1)} GB available of {((system.memory?.total || 0) / 1073741824).toFixed(1)} GB
                </p>
              </div>

              <div className="rounded-lg bg-gray-50 p-4">
                <div className="mb-2 flex items-center gap-2">
                  <HardDrive className="h-5 w-5 text-green-600" />
                  <p className="text-sm font-medium text-gray-700">Disk</p>
                  <span className="ml-auto text-lg font-semibold">{system.disk?.percent}%</span>
                </div>
                <div className="h-2 rounded-full bg-gray-200">
                  <div
                    className={`h-2 rounded-full transition-all ${system.disk?.percent > 80 ? 'bg-red-500' : system.disk?.percent > 60 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${system.disk?.percent || 0}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  {((system.disk?.used || 0) / 1073741824).toFixed(1)} / {((system.disk?.total || 0) / 1073741824).toFixed(1)} GB
                </p>
              </div>

              <div className="rounded-lg bg-gray-50 p-4">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5 text-orange-600" />
                  <p className="text-sm font-medium text-gray-700">Platform</p>
                </div>
                <p className="mt-2 font-medium text-gray-900">{system.platform}</p>
                <p className="text-xs text-gray-500">Python {system.python_version}</p>
              </div>
            </div>

            <div className="flex items-center justify-center">
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={systemChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {systemChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => `${value}%`} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="mt-4 flex justify-center gap-6">
            {systemChartData.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-sm text-gray-600">{item.name}: {item.value}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!stats && !system && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16">
          <BarChart3 className="mb-4 h-12 w-12 text-gray-300" />
          <p className="text-gray-500">Monitoring data requires admin access and running server</p>
        </div>
      )}
    </div>
  );
}
