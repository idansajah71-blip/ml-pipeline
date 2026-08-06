'use client';

import { Database, Brain, FlaskConical, Zap, Activity, Rocket, ArrowRight, Search, BarChart3, HelpCircle } from 'lucide-react';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useModels, useDatasets, useExperiments } from '@/lib/hooks';
import { QUICKSTART_CARDS } from '@/lib/recommendations';
import Link from 'next/link';

const ICONS: Record<string, any> = { Brain, Search, BarChart3, HelpCircle };

const stats = [
  { key: 'models', title: 'Total Model', icon: Brain, color: 'bg-blue-50 text-blue-600', href: '/models' },
  { key: 'datasets', title: 'Total Dataset', icon: Database, color: 'bg-green-50 text-green-600', href: '/datasets' },
  { key: 'experiments', title: 'Eksperimen', icon: FlaskConical, color: 'bg-purple-50 text-purple-600', href: '/experiments' },
  { key: 'predictions', title: 'Prediksi', icon: Zap, color: 'bg-yellow-50 text-yellow-600', href: '/predictions' },
  { key: 'active', title: 'Model Aktif', icon: Rocket, color: 'bg-indigo-50 text-indigo-600', href: '/models' },
  { key: 'training', title: 'Training', icon: Activity, color: 'bg-orange-50 text-orange-600', href: '/experiments' },
] as const;

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

  const values: Record<string, number> = {
    models: modelsList.length,
    datasets: datasetsList.length,
    experiments: experimentsList.length,
    predictions: 0,
    active: modelsList.filter((m) => m.status === 'deployed').length,
    training: modelsList.filter((m) => m.status === 'training').length,
  };

  const recentModels = modelsList.slice(0, 5);
  const recentDatasets = datasetsList.slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dasbor</h1>
        <p className="text-gray-500">Ringkasan ML Pipeline Anda</p>
      </div>

      {/* Bantu Saya Mulai */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-500 uppercase tracking-wide">Bantu Saya Mulai</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {QUICKSTART_CARDS.map((card) => {
            const Icon = ICONS[card.icon];
            const isOnboarding = card.id === 'understand-platform';

            if (isOnboarding) {
              return (
                <button
                  key={card.id}
                  onClick={() => window.dispatchEvent(new Event('restart-onboarding'))}
                  className={`group rounded-xl border-2 p-4 transition-all text-left ${card.color}`}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <Icon className="h-5 w-5" />
                    <span className="font-semibold text-sm">{card.title}</span>
                  </div>
                  <p className="text-xs opacity-80">{card.description}</p>
                </button>
              );
            }

            return (
              <Link
                key={card.id}
                href={card.href}
                className={`group rounded-xl border-2 p-4 transition-all ${card.color}`}
              >
                <div className="mb-2 flex items-center gap-2">
                  <Icon className="h-5 w-5" />
                  <span className="font-semibold text-sm">{card.title}</span>
                </div>
                <p className="text-xs opacity-80">{card.description}</p>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {stats.map((s) => (
          <Link
            key={s.key}
            href={s.href}
            className="rounded-xl border border-gray-200 bg-white p-5 transition-colors hover:bg-gray-50"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500">{s.title}</p>
                <p className="mt-1 text-2xl font-semibold text-gray-900">{values[s.key]}</p>
              </div>
              <div className={`rounded-lg p-3 ${s.color}`}>
                <s.icon className="h-5 w-5" />
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900">Model Terbaru</h2>
            <Link href="/models" className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700">
              Lihat semua <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="p-6">
            {recentModels.length === 0 ? (
              <p className="text-sm text-gray-500">Belum ada model. Mulai training sekarang!</p>
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
        </div>

        <div className="rounded-xl border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900">Dataset Terbaru</h2>
            <Link href="/datasets" className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700">
              Lihat semua <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="p-6">
            {recentDatasets.length === 0 ? (
              <p className="text-sm text-gray-500">Belum ada dataset. Unggah dataset pertama Anda!</p>
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
    </div>
  );
}
