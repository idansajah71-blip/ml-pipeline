'use client';

import { Database, Brain, FlaskConical, Zap, Activity, Rocket } from 'lucide-react';
import StatsCard from '@/components/StatsCard';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useModels, useDatasets, useExperiments } from '@/lib/hooks';

export default function DashboardPage() {
  const { models: modelsList, isLoading: modelsLoading } = useModels();
  const { datasets: datasetsList, isLoading: datasetsLoading } = useDatasets();
  const { experiments: experimentsList, isLoading: experimentsLoading } = useExperiments();

  const loading = modelsLoading || datasetsLoading || experimentsLoading;

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const totalModels = modelsList.length;
  const totalDatasets = datasetsList.length;
  const totalExperiments = experimentsList.length;
  const activeModels = modelsList.filter((m) => m.status === 'deployed').length;
  const trainingModels = modelsList.filter((m) => m.status === 'training').length;

  const recentModels = modelsList.slice(0, 5);
  const recentDatasets = datasetsList.slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500">Overview of your ML Pipeline</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatsCard title="Total Models" value={totalModels} icon={Brain} iconColor="text-blue-600" />
        <StatsCard title="Total Datasets" value={totalDatasets} icon={Database} iconColor="text-green-600" />
        <StatsCard title="Experiments" value={totalExperiments} icon={FlaskConical} iconColor="text-purple-600" />
        <StatsCard title="Predictions" value={0} icon={Zap} iconColor="text-yellow-600" />
        <StatsCard title="Active Models" value={activeModels} icon={Rocket} iconColor="text-indigo-600" />
        <StatsCard title="Training" value={trainingModels} icon={Activity} iconColor="text-orange-600" />
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
