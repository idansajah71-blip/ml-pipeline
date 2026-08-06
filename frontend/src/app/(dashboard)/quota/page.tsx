'use client';

import { useEffect, useState } from 'react';
import { quota } from '@/lib/api';
import { Shield, Activity, Clock, Calendar, ArrowUp, Brain, AlertTriangle } from 'lucide-react';

interface QuotaData {
  tier: string;
  rpm: { current: number; limit: number };
  daily: { current: number; limit: number };
  monthly: { current: number; limit: number };
  training: {
    daily: { current: number; limit: number };
    monthly: { current: number; limit: number };
  };
}

const TIER_INFO: Record<string, { label: string; color: string; description: string }> = {
  free: { label: 'Free', color: 'bg-gray-500', description: 'Cocok untuk eksperimen ringan' },
  starter: { label: 'Starter', color: 'bg-blue-500', description: 'Untuk proyek kecil-menengah' },
  pro: { label: 'Pro', color: 'bg-purple-500', description: 'Untuk tim dan produksi' },
  enterprise: { label: 'Enterprise', color: 'bg-amber-500', description: 'Untuk skala besar' },
};

function QuotaBar({ label, current, limit, icon }: { label: string; current: number; limit: number; icon: React.ReactNode }) {
  const pct = limit > 0 ? Math.min((current / limit) * 100, 100) : 0;
  const isHigh = pct >= 80;
  const isCritical = pct >= 95;
  const remaining = Math.max(0, limit - current);

  return (
    <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-600 dark:text-zinc-400">
          {icon}
          {label}
        </div>
        <span className="text-xs text-zinc-500">
          {current.toLocaleString('id-ID')} / {limit.toLocaleString('id-ID')}
        </span>
      </div>
      <div className="w-full h-3 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isCritical ? 'bg-red-500' : isHigh ? 'bg-amber-500' : 'bg-emerald-500'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className={`text-xs font-medium ${isCritical ? 'text-red-500' : isHigh ? 'text-amber-500' : 'text-emerald-500'}`}>
          {pct.toFixed(1)}% terpakai
        </span>
        <span className="text-xs text-zinc-500">
          Sisa: {remaining.toLocaleString('id-ID')}
        </span>
      </div>
      {isCritical && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-red-500">
          <AlertTriangle className="h-3 w-3" />
          Mendekati batas! Pertimbangkan untuk upgrade tier.
        </div>
      )}
      {isHigh && !isCritical && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-amber-500">
          <AlertTriangle className="h-3 w-3" />
          Penggunaan sudah tinggi, perhatikan limit Anda.
        </div>
      )}
    </div>
  );
}

export default function QuotaPage() {
  const [quotaData, setQuotaData] = useState<QuotaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchQuota();
    const interval = setInterval(fetchQuota, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchQuota = async () => {
    try {
      const res = await quota.get();
      setQuotaData(res.data);
    } catch {
      setError('Gagal memuat data kuota');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800 p-4 text-red-600 dark:text-red-400">
          {error}
        </div>
      </div>
    );
  }

  if (!quotaData) return null;

  const tierInfo = TIER_INFO[quotaData.tier] || TIER_INFO.free;
  const trainingDaily = quotaData.training?.daily || { current: 0, limit: 5 };
  const trainingMonthly = quotaData.training?.monthly || { current: 0, limit: 100 };
  const trainingPct = trainingMonthly.limit > 0 ? Math.min((trainingMonthly.current / trainingMonthly.limit) * 100, 100) : 0;

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">Kuota API</h1>
        <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
          Pantau penggunaan API dan training Anda
        </p>
      </div>

      {/* Tier Badge */}
      <div className="flex items-center gap-4 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5">
        <div className={`w-12 h-12 rounded-lg ${tierInfo.color} flex items-center justify-center`}>
          <Shield className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">{tierInfo.label}</h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
              Tier Aktif
            </span>
          </div>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">{tierInfo.description}</p>
        </div>
      </div>

      {/* Training Quota - Highlighted */}
      <div className="rounded-xl border-2 border-primary-200 dark:border-primary-800 bg-primary-50 dark:bg-primary-900/20 p-5">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="h-5 w-5 text-primary-600" />
          <h3 className="font-semibold text-primary-900 dark:text-primary-100">Training Hari Ini</h3>
        </div>
        <div className="flex items-end gap-3 mb-2">
          <span className="text-4xl font-bold text-primary-700 dark:text-primary-300">
            {trainingDaily.current}
          </span>
          <span className="text-lg text-primary-500 mb-1">/ {trainingDaily.limit} training</span>
        </div>
        <div className="w-full h-4 rounded-full bg-primary-200 dark:bg-primary-800 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              trainingPct >= 90 ? 'bg-red-500' : trainingPct >= 70 ? 'bg-amber-500' : 'bg-primary-500'
            }`}
            style={{ width: `${trainingPct}%` }}
          />
        </div>
        <p className="mt-2 text-sm text-primary-700 dark:text-primary-300">
          {trainingMonthly.current} / {trainingMonthly.limit} training bulan ini
        </p>
        {trainingPct >= 80 && (
          <div className="mt-2 flex items-center gap-1.5 text-sm text-red-600 dark:text-red-400">
            <AlertTriangle className="h-4 w-4" />
            Kuota training bulanan sudah hampir habis!
          </div>
        )}
      </div>

      {/* API Quota Bars */}
      <div className="grid gap-4">
        <QuotaBar
          label="Rate Limit (per menit)"
          current={quotaData.rpm.current}
          limit={quotaData.rpm.limit}
          icon={<Activity className="w-4 h-4" />}
        />
        <QuotaBar
          label="Batas Harian (API calls)"
          current={quotaData.daily.current}
          limit={quotaData.daily.limit}
          icon={<Clock className="w-4 w-4" />}
        />
        <QuotaBar
          label="Batas Bulanan (API calls)"
          current={quotaData.monthly.current}
          limit={quotaData.monthly.limit}
          icon={<Calendar className="w-4 h-4" />}
        />
      </div>

      {/* Tier Comparison */}
      <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-3">Perbandingan Tier</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-200 dark:border-zinc-700">
                <th className="py-2 text-left text-zinc-500">Fitur</th>
                <th className="py-2 text-center text-zinc-500">Free</th>
                <th className="py-2 text-center text-zinc-500">Starter</th>
                <th className="py-2 text-center text-zinc-500">Pro</th>
                <th className="py-2 text-center text-zinc-500">Enterprise</th>
              </tr>
            </thead>
            <tbody className="text-zinc-700 dark:text-zinc-300">
              <tr className="border-b border-zinc-100 dark:border-zinc-800">
                <td className="py-2">Training/hari</td>
                <td className="py-2 text-center">5</td>
                <td className="py-2 text-center">20</td>
                <td className="py-2 text-center">100</td>
                <td className="py-2 text-center">500</td>
              </tr>
              <tr className="border-b border-zinc-100 dark:border-zinc-800">
                <td className="py-2">Training/bulan</td>
                <td className="py-2 text-center">100</td>
                <td className="py-2 text-center">500</td>
                <td className="py-2 text-center">3.000</td>
                <td className="py-2 text-center">15.000</td>
              </tr>
              <tr className="border-b border-zinc-100 dark:border-zinc-800">
                <td className="py-2">API calls/hari</td>
                <td className="py-2 text-center">10.000</td>
                <td className="py-2 text-center">100.000</td>
                <td className="py-2 text-center">500.000</td>
                <td className="py-2 text-center">5.000.000</td>
              </tr>
              <tr>
                <td className="py-2">Ukuran upload</td>
                <td className="py-2 text-center">10MB</td>
                <td className="py-2 text-center">50MB</td>
                <td className="py-2 text-center">200MB</td>
                <td className="py-2 text-center">1GB</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Info */}
      <div className="rounded-xl border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900/50 p-5">
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-white mb-2">Informasi Reset</h3>
        <ul className="text-sm text-zinc-600 dark:text-zinc-400 space-y-1">
          <li className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5" /> Rate limit reset setiap 1 menit
          </li>
          <li className="flex items-center gap-2">
            <Clock className="w-3.5 h-3.5" /> Batas harian & training harian reset setiap 24 jam
          </li>
          <li className="flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5" /> Batas bulanan reset setiap 30 hari
          </li>
          <li className="flex items-center gap-2">
            <Brain className="w-3.5 h-3.5" /> Training dihitung per eksperimen yang dijalankan
          </li>
          <li className="flex items-center gap-2">
            <ArrowUp className="w-3.5 h-3.5" /> Upgrade tier untuk batas lebih tinggi
          </li>
        </ul>
      </div>
    </div>
  );
}
