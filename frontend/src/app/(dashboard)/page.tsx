'use client';

import { Database, Brain, FlaskConical, Zap, Activity, Rocket, ArrowRight, Search, BarChart3, HelpCircle } from 'lucide-react';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useModels, useDatasets, useExperiments } from '@/lib/hooks';
import { QUICKSTART_CARDS } from '@/lib/recommendations';
import Link from 'next/link';

const ICONS: Record<string, any> = { Brain, Search, BarChart3, HelpCircle };

const stats = [
  { key: 'models', title: 'Total Model', icon: Brain, iconBg: 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300', href: '/models' },
  { key: 'datasets', title: 'Total Dataset', icon: Database, iconBg: 'bg-success-50 text-success-700 dark:bg-success-900/30 dark:text-success-300', href: '/datasets' },
  { key: 'experiments', title: 'Eksperimen', icon: FlaskConical, iconBg: 'bg-classification-50 text-classification-700 dark:bg-classification-900/30 dark:text-classification-300', href: '/experiments' },
  { key: 'predictions', title: 'Prediksi', icon: Zap, iconBg: 'bg-warning-50 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300', href: '/predictions' },
  { key: 'active', title: 'Model Aktif', icon: Rocket, iconBg: 'bg-info-50 text-info-700 dark:bg-info-900/30 dark:text-info-300', href: '/models' },
  { key: 'training', title: 'Training', icon: Activity, iconBg: 'bg-regression-50 text-regression-700 dark:bg-regression-900/30 dark:text-regression-300', href: '/experiments' },
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
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dasbor</h1>
        <p className="text-gray-500 dark:text-gray-400">Ringkasan ML Pipeline Anda</p>
      </div>

      {/* Bantu Saya Mulai */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Bantu Saya Mulai</h2>
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
            className="rounded-xl border border-gray-200 bg-white p-5 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-750"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{s.title}</p>
                <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">{values[s.key]}</p>
              </div>
              <div className={`rounded-lg p-3 ${s.iconBg}`}>
                <s.icon className="h-5 w-5" />
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Model Terbaru</h2>
            <Link href="/models" className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700">
              Lihat semua <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="p-6">
            {recentModels.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">Belum ada model. Mulai training sekarang!</p>
            ) : (
              <div className="space-y-3">
                {recentModels.map((model) => (
                  <div key={model.id} className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-gray-700 p-3">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{model.name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{model.algorithm} v{model.version}</p>
                    </div>
                    <StatusBadge status={model.status} />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Dataset Terbaru</h2>
            <Link href="/datasets" className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700">
              Lihat semua <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="p-6">
            {recentDatasets.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">Belum ada dataset. Unggah dataset pertama Anda!</p>
            ) : (
              <div className="space-y-3">
                {recentDatasets.map((ds) => (
                  <div key={ds.id} className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-gray-700 p-3">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{ds.name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{ds.rows_count} rows, {ds.columns_count} columns</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500 dark:text-gray-400">{ds.target_column}</p>
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
