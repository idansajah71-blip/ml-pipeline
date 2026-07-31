'use client';

import { useEffect, useState } from 'react';
import { Database, Brain, FlaskConical, Zap, Activity, Rocket } from 'lucide-react';
import StatsCard from '@/components/StatsCard';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import { monitoring, models, datasets } from '@/lib/api';
import { Stats, MLModel, Dataset } from '@/types';

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentModels, setRecentModels] = useState<MLModel[]>([]);
  const [recentDatasets, setRecentDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, modelsRes, datasetsRes] = await Promise.all([
          monitoring.stats().catch(() => ({ data: { total_models: 0, total_datasets: 0, total_experiments: 0, total_predictions: 0, active_models: 0, training_experiments: 0 } })),
          models.list().catch(() => ({ data: { items: [] } })),
          datasets.list().catch(() => ({ data: [] })),
        ]);
        setStats(statsRes.data);
        setRecentModels(modelsRes.data.items.slice(0, 5));
        setRecentDatasets((Array.isArray(datasetsRes.data) ? datasetsRes.data : []).slice(0, 5));
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

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Overview of your ML Pipeline</p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <StatsCard title="Total Models" value={stats?.total_models || 0} icon={Brain} iconColor="text-blue-600" />
        <StatsCard title="Total Datasets" value={stats?.total_datasets || 0} icon={Database} iconColor="text-green-600" />
        <StatsCard title="Experiments" value={stats?.total_experiments || 0} icon={FlaskConical} iconColor="text-purple-600" />
        <StatsCard title="Predictions" value={stats?.total_predictions || 0} icon={Zap} iconColor="text-yellow-600" />
        <StatsCard title="Active Models" value={stats?.active_models || 0} icon={Rocket} iconColor="text-indigo-600" />
        <StatsCard title="Training" value={stats?.training_experiments || 0} icon={Activity} iconColor="text-orange-600" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Recent Models</h2>
          {recentModels.length === 0 ? (
            <p className="text-sm text-gray-500">No models yet. Create your first model!</p>
          ) : (
            <div className="space-y-3">
              {recentModels.map((model) => (
                <div key={model.id} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
                  <div>
                    <p className="font-medium text-gray-900">{model.name}</p>
                    <p className="text-xs text-gray-500">{model.algorithm} v{model.version}</p>
                  </div>
                  <StatusBadge status={model.status} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Recent Datasets</h2>
          {recentDatasets.length === 0 ? (
            <p className="text-sm text-gray-500">No datasets yet. Upload your first dataset!</p>
          ) : (
            <div className="space-y-3">
              {recentDatasets.map((ds) => (
                <div key={ds.id} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
                  <div>
                    <p className="font-medium text-gray-900">{ds.name}</p>
                    <p className="text-xs text-gray-500">{ds.rows_count} rows, {ds.columns_count} columns</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">{ds.target_column}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
