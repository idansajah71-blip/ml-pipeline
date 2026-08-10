'use client';

import { useCallback } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Database,
  HardDrive,
  HeartPulse,
  RefreshCw,
  Server,
  ServerCog,
  ShieldAlert,
  XCircle,
  Zap,
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/lib/auth';
import { useSystemHealth } from '@/lib/hooks';
import { SystemHealthComponent } from '@/lib/api';
import LoadingSpinner from '@/components/LoadingSpinner';

const COMPONENT_CONFIG: Record<string, { icon: any; label: string }> = {
  Database: { icon: Database, label: 'Database' },
  Redis: { icon: Zap, label: 'Redis (Cache & Antrean)' },
  Celery: { icon: ServerCog, label: 'Celery (Worker)' },
  Storage: { icon: HardDrive, label: 'Storage (Model)' },
  Server: { icon: Server, label: 'Server' },
};

const STATUS_META: Record<
  string,
  { label: string; dot: string; badge: string; icon: any }
> = {
  ok: {
    label: 'Normal',
    dot: 'bg-green-500',
    badge: 'bg-green-50 text-green-700 border-green-200',
    icon: CheckCircle2,
  },
  degraded: {
    label: 'Peringatan',
    dot: 'bg-amber-500',
    badge: 'bg-amber-50 text-amber-700 border-amber-200',
    icon: AlertTriangle,
  },
  error: {
    label: 'Kritis',
    dot: 'bg-red-500',
    badge: 'bg-red-50 text-red-700 border-red-200',
    icon: XCircle,
  },
};

function formatLatency(ms?: number | null): string {
  if (ms === undefined || ms === null) return '—';
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} dtk`;
}

function StatusPill({ status }: { status: string }) {
  const meta = STATUS_META[status] || STATUS_META.error;
  const Icon = meta.icon;
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold',
        meta.badge
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {meta.label}
    </span>
  );
}

export default function SystemHealthPage() {
  const { user } = useAuth();
  const { health, isLoading, isError, mutate } = useSystemHealth();

  const refresh = useCallback(() => {
    mutate();
  }, [mutate]);

  const isAdmin = user?.role === 'admin';

  if (!isAdmin) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Kesehatan Sistem</h1>
          <p className="text-gray-500">Dashboard internal khusus admin</p>
        </div>
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-20">
          <ShieldAlert className="mb-4 h-12 w-12 text-gray-300" />
          <p className="font-medium text-gray-700">Akses ditolak</p>
          <p className="mt-1 text-sm text-gray-500">
            Halaman ini hanya dapat diakses oleh pengguna dengan peran Admin.
          </p>
        </div>
      </div>
    );
  }

  if (isLoading && !health) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isError && !health) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-20">
        <AlertTriangle className="mb-4 h-12 w-12 text-amber-400" />
        <p className="font-medium text-gray-700">Gagal memuat status sistem</p>
        <button
          onClick={refresh}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
        >
          <RefreshCw className="h-4 w-4" /> Coba lagi
        </button>
      </div>
    );
  }

  const overall = health?.status || 'error';
  const overallMeta = STATUS_META[overall] || STATUS_META.error;
  const checkedAt = health?.checked_at
    ? new Date(health.checked_at).toLocaleString('id-ID', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : '—';

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <HeartPulse className="h-7 w-7 text-primary-600" />
            Kesehatan Sistem
          </h1>
          <p className="mt-1 flex items-center gap-1.5 text-sm text-gray-500">
            <Clock className="h-4 w-4" />
            Terakhir diperiksa: {checkedAt}
            <span className="text-gray-400">·</span>auto-refresh tiap 15 detik
          </p>
        </div>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 min-h-[40px]"
        >
          <RefreshCw className="h-4 w-4" /> Periksa Sekarang
        </button>
      </div>

      <div
        className={clsx(
          'flex flex-wrap items-center gap-4 rounded-xl border p-5',
          overall === 'ok' && 'border-green-200 bg-green-50',
          overall === 'degraded' && 'border-amber-200 bg-amber-50',
          overall === 'error' && 'border-red-200 bg-red-50'
        )}
      >
        <div
          className={clsx(
            'flex h-12 w-12 items-center justify-center rounded-full',
            overall === 'ok' && 'bg-green-100 text-green-600',
            overall === 'degraded' && 'bg-amber-100 text-amber-600',
            overall === 'error' && 'bg-red-100 text-red-600'
          )}
        >
          <Activity className="h-6 w-6" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-lg font-semibold text-gray-900">
            Status keseluruhan:{' '}
            <span className={overall === 'ok' ? 'text-green-600' : overall === 'degraded' ? 'text-amber-600' : 'text-red-600'}>
              {overallMeta.label}
            </span>
          </p>
          <p className="text-sm text-gray-600">
            {health?.summary
              ? `${health.summary.ok} komponen normal · ${health.summary.degraded} peringatan · ${health.summary.error} kritis`
              : 'Memuat ringkasan…'}
          </p>
        </div>
        {health?.environment && (
          <span className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-gray-600">
            env: {health.environment} · v{health.app_version}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {health?.components.map((component: SystemHealthComponent) => {
          const config = COMPONENT_CONFIG[component.name] || {
            icon: Activity,
            label: component.name,
          };
          const Icon = config.icon;
          const meta = STATUS_META[component.status] || STATUS_META.error;
          return (
            <div
              key={component.name}
              className="group rounded-xl border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div
                    className={clsx(
                      'flex h-10 w-10 items-center justify-center rounded-lg',
                      component.status === 'ok' && 'bg-green-50 text-green-600',
                      component.status === 'degraded' && 'bg-amber-50 text-amber-600',
                      component.status === 'error' && 'bg-red-50 text-red-600'
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{config.label}</p>
                    <p className="text-xs text-gray-400">latensi {formatLatency(component.latency_ms)}</p>
                  </div>
                </div>
                <StatusPill status={component.status} />
              </div>

              <p className="mt-4 text-sm leading-relaxed text-gray-600">{component.detail}</p>

              {(component.worker_count !== undefined ||
                component.artifact_count !== undefined ||
                component.used_pct !== undefined) && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {component.worker_count !== undefined && (
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
                      {component.worker_count} worker
                    </span>
                  )}
                  {component.artifact_count !== undefined && (
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
                      {component.artifact_count} artefak model
                    </span>
                  )}
                  {component.used_pct !== undefined && (
                    <span
                      className={clsx(
                        'rounded-full px-2.5 py-1 text-xs font-medium',
                        (component.used_pct ?? 0) > 90
                          ? 'bg-red-50 text-red-600'
                          : 'bg-gray-100 text-gray-600'
                      )}
                    >
                      disk {component.used_pct}%
                    </span>
                  )}
                  {component.cpu_percent !== undefined && (
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
                      CPU {component.cpu_percent}%
                    </span>
                  )}
                  {component.memory_percent !== undefined && (
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
                      RAM {component.memory_percent}%
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <p className="text-xs text-gray-400">
        Dashboard ini memantau infrastruktur secara real-time. Jika Celery atau Redis bermasalah, sistem
        otomatis menjalankan pelatihan secara langsung (synchronous) sehingga pengguna tidak melihat error.
      </p>
    </div>
  );
}
