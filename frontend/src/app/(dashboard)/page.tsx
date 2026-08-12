'use client';

import {
  Database, Brain, FlaskConical, Zap, Activity, Rocket, ArrowRight,
  ChevronRight, Upload, BrainCircuit, PlayCircle, BarChart3,
  TestTube2, Clock
} from 'lucide-react';
import type { ComponentType } from 'react';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useModels, useDatasets, useExperiments, useStats } from '@/lib/hooks';
import Link from 'next/link';

type IconComponent = ComponentType<{ className?: string }>;

// ── ML Lifecycle Pipeline ────────────────────────────────────────────────────

const LIFECYCLE_STEPS = [
  { label: 'Data', icon: Database, href: '/datasets', color: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30 dark:text-emerald-400' },
  { label: 'Experiment', icon: FlaskConical, href: '/experiments', color: 'text-blue-600 bg-blue-50 dark:bg-blue-900/30 dark:text-blue-400' },
  { label: 'Train', icon: BrainCircuit, href: '/training-wizard', color: 'text-violet-600 bg-violet-50 dark:bg-violet-900/30 dark:text-violet-400' },
  { label: 'Evaluate', icon: BarChart3, href: '/benchmark', color: 'text-amber-600 bg-amber-50 dark:bg-amber-900/30 dark:text-amber-400' },
  { label: 'Register', icon: Brain, href: '/models', color: 'text-primary-600 bg-primary-50 dark:bg-primary-900/30 dark:text-primary-400' },
  { label: 'Deploy', icon: Rocket, href: '/serving', color: 'text-rose-600 bg-rose-50 dark:bg-rose-900/30 dark:text-rose-400' },
  { label: 'Predict', icon: Zap, href: '/predictions', color: 'text-orange-600 bg-orange-50 dark:bg-orange-900/30 dark:text-orange-400' },
  { label: 'Monitor', icon: Activity, href: '/monitoring', color: 'text-cyan-600 bg-cyan-50 dark:bg-cyan-900/30 dark:text-cyan-400' },
];

// ── Stat Card ────────────────────────────────────────────────────────────────

function StatCard({ title, value, icon: Icon, iconBg, href }: {
  title: string; value: number; icon: IconComponent; iconBg: string; href: string;
}) {
  return (
    <Link
      href={href}
      className="rounded-xl border border-gray-200 bg-white p-5 transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-750"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">{value}</p>
        </div>
        <div className={`rounded-lg p-3 ${iconBg}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </Link>
  );
}

// ── Activity Item ────────────────────────────────────────────────────────────

function ActivityItem({ icon: Icon, iconColor, title, subtitle, time, href }: {
  icon: IconComponent; iconColor: string; title: string; subtitle: string; time: string; href?: string;
}) {
  const content = (
    <div className="flex items-start gap-3">
      <div className={`mt-0.5 rounded-full p-1.5 ${iconColor}`}>
        <Icon className="h-3.5 w-3.5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{title}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{subtitle}</p>
      </div>
      <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">{time}</span>
    </div>
  );

  return href ? (
    <Link href={href} className="block rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
      {content}
    </Link>
  ) : (
    <div className="p-3">{content}</div>
  );
}

// ── Dashboard Page ───────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { models: modelsList, isLoading: modelsLoading } = useModels();
  const { datasets: datasetsList, isLoading: datasetsLoading } = useDatasets();
  const { experiments: experimentsList, isLoading: experimentsLoading } = useExperiments();
  const { stats, isLoading: statsLoading } = useStats();

  const loading = modelsLoading || datasetsLoading || experimentsLoading;

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const deployedModels = modelsList.filter((m) => m.status === 'deployed');
  const trainingModels = modelsList.filter((m) => m.status === 'training');
  const recentModels = modelsList.slice(0, 3);
  const recentDatasets = datasetsList.slice(0, 3);
  const recentExperiments = experimentsList.slice(0, 3);

  // Build activity feed from available data
  const activities: Array<{
    icon: IconComponent; iconColor: string; title: string; subtitle: string; time: string; href?: string;
  }> = [];

  recentModels.forEach((m) => {
    activities.push({
      icon: Brain,
      iconColor: 'bg-primary-100 text-primary-600 dark:bg-primary-900/50 dark:text-primary-400',
      title: `Model "${m.name}"`,
      subtitle: `${m.algorithm} - ${m.status}`,
      time: 'baru',
      href: `/models`,
    });
  });

  recentDatasets.forEach((d) => {
    activities.push({
      icon: Database,
      iconColor: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/50 dark:text-emerald-400',
      title: `Dataset "${d.name}"`,
      subtitle: `${d.rows_count?.toLocaleString()} rows, ${d.columns_count} columns`,
      time: 'baru',
      href: '/datasets',
    });
  });

  recentExperiments.forEach((e) => {
    activities.push({
      icon: FlaskConical,
      iconColor: 'bg-blue-100 text-blue-600 dark:bg-blue-900/50 dark:text-blue-400',
      title: `Experiment`,
      subtitle: `${e.status} - ${e.name || 'N/A'}`,
      time: 'baru',
      href: '/experiments',
    });
  });

  if (trainingModels.length > 0) {
    activities.unshift({
      icon: Activity,
      iconColor: 'bg-amber-100 text-amber-600 dark:bg-amber-900/50 dark:text-amber-400',
      title: `${trainingModels.length} model sedang training`,
      subtitle: 'Proses berlangsung...',
      time: 'now',
    });
  }

  return (
    <div className="space-y-8">
      {/* ── Header ── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400">Your ML pipeline at a glance</p>
      </div>

      {/* ── ML Lifecycle Pipeline ── */}
      <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800 p-6">
        <h2 className="mb-4 text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">ML Lifecycle</h2>
        <div className="flex items-center justify-between gap-1 overflow-x-auto pb-2">
          {LIFECYCLE_STEPS.map((step, i) => {
            const Icon = step.icon;
            return (
              <div key={step.label} className="flex items-center">
                <Link
                  href={step.href}
                  className="flex flex-col items-center gap-2 rounded-lg p-3 transition-colors hover:bg-gray-50 dark:hover:bg-gray-700/50 min-w-[80px]"
                >
                  <div className={`rounded-xl p-2.5 ${step.color}`}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{step.label}</span>
                </Link>
                {i < LIFECYCLE_STEPS.length - 1 && (
                  <ChevronRight className="h-4 w-4 text-gray-300 dark:text-gray-600 flex-shrink-0 -mx-1" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Stats Grid ── */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          title="Datasets"
          value={stats?.total_datasets ?? datasetsList.length}
          icon={Database}
          iconBg="bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300"
          href="/datasets"
        />
        <StatCard
          title="Experiments"
          value={stats?.total_experiments ?? experimentsList.length}
          icon={FlaskConical}
          iconBg="bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
          href="/experiments"
        />
        <StatCard
          title="Models"
          value={stats?.total_models ?? modelsList.length}
          icon={Brain}
          iconBg="bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300"
          href="/models"
        />
        <StatCard
          title="Deployed"
          value={stats?.active_models ?? deployedModels.length}
          icon={Rocket}
          iconBg="bg-rose-50 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300"
          href="/serving"
        />
      </div>

      {/* ── Recent Activity + Quick Actions ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Activity Feed */}
        <div className="lg:col-span-2 rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Activity</h2>
          </div>
          <div className="p-2">
            {activities.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                <Clock className="h-10 w-10 mb-3 opacity-50" />
                <p className="text-sm">No activity yet. Start by uploading a dataset!</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100 dark:divide-gray-700">
                {activities.slice(0, 6).map((a, i) => (
                  <ActivityItem key={i} {...a} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <div className="border-b border-gray-100 dark:border-gray-700 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Quick Actions</h2>
          </div>
          <div className="p-4 space-y-2">
            <Link
              href="/datasets"
              className="flex items-center gap-3 rounded-lg p-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div className="rounded-lg bg-emerald-100 dark:bg-emerald-900/50 p-2">
                <Upload className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
              </div>
              Upload Dataset
            </Link>
            <Link
              href="/training-wizard"
              className="flex items-center gap-3 rounded-lg p-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div className="rounded-lg bg-violet-100 dark:bg-violet-900/50 p-2">
                <BrainCircuit className="h-4 w-4 text-violet-600 dark:text-violet-400" />
              </div>
              Training Wizard
            </Link>
            <Link
              href="/try-predict"
              className="flex items-center gap-3 rounded-lg p-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div className="rounded-lg bg-orange-100 dark:bg-orange-900/50 p-2">
                <PlayCircle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
              </div>
              Try Prediction
            </Link>
            <Link
              href="/data-explorer"
              className="flex items-center gap-3 rounded-lg p-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div className="rounded-lg bg-cyan-100 dark:bg-cyan-900/50 p-2">
                <Database className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
              </div>
              Find External Data
            </Link>
            <Link
              href="/marketplace"
              className="flex items-center gap-3 rounded-lg p-3 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
              <div className="rounded-lg bg-pink-100 dark:bg-pink-900/50 p-2">
                <TestTube2 className="h-4 w-4 text-pink-600 dark:text-pink-400" />
              </div>
              Browse Marketplace
            </Link>
          </div>
        </div>
      </div>

      {/* ── Recent Models & Datasets ── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Recent Models */}
        <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Models</h2>
            <Link href="/models" className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700">
              View all <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="p-6">
            {recentModels.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No models yet. Start training!</p>
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

        {/* Recent Datasets */}
        <div className="rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
          <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-700 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Datasets</h2>
            <Link href="/datasets" className="flex items-center gap-1 text-sm text-primary-600 hover:text-primary-700">
              View all <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="p-6">
            {recentDatasets.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">No datasets yet. Upload your first!</p>
            ) : (
              <div className="space-y-3">
                {recentDatasets.map((ds) => (
                  <div key={ds.id} className="flex items-center justify-between rounded-lg border border-gray-100 dark:border-gray-700 p-3">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{ds.name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">{ds.rows_count?.toLocaleString()} rows, {ds.columns_count} columns</p>
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
