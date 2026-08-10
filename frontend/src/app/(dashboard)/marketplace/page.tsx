'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Store, Search, Star, Download, Zap, ChevronRight, ArrowLeft,
  Upload, CheckCircle, AlertCircle, Loader2, X, FileSpreadsheet,
  Home, Users, ShieldCheck, BarChart2, TrendingUp, Handshake,
  Lock, Settings, GraduationCap, Brain, Target, Layers,
} from 'lucide-react';
import { marketplaceApi, formatApiError } from '@/lib/api';
import { useToast } from '@/components/Toast';

// ─── Types ────────────────────────────────────────────────────────────────────

interface MarketplaceModel {
  id: string;
  model_name: string;
  category: string;
  use_case?: string;
  description?: string;
  tags: string[];
  feature_names: string[];
  target_column?: string;
  algorithm?: string;
  metrics?: Record<string, number>;
  downloads: number;
  rating: number;
  rating_count: number;
  is_platform_model: boolean;
  status?: 'pending' | 'approved' | 'rejected';
  icon?: string;
  result_label?: string;
  result_unit?: string;
  result_type?: string;
  class_labels?: Record<string, string>;
  shared_by?: string;
}

interface Category {
  id: string;
  label: string;
  description: string;
  icon: string;
  color: string;
}

interface ColumnMatch {
  required_column: string;
  suggested_user_column: string | null;
  confidence: number;
}

interface PredictionResult {
  index: number;
  prediction: string | number;
  prediction_label: string;
  probability?: number;
  probabilities?: Record<string, number>;
  result_type: string;
}

type View = 'gallery' | 'category' | 'detail' | 'predict';

// ─── Icon map: category & model icons (Lucide only, zero emoji) ──────────────

const MODEL_ICON_MAP: Record<string, React.ElementType> = {
  'platform-1': Home,
  'platform-2': Users,
  'platform-3': GraduationCap,
  'platform-4': TrendingUp,
  'platform-5': Lock,
  'platform-6': Settings,
  'platform-7': Brain,
  'platform-8': ShieldCheck,
  'platform-9': Layers,
  'platform-10': Target,
  'platform-11': Zap,
  'platform-12': BarChart2,
  'platform-13': Lock,
  'platform-14': TrendingUp,
  'platform-15': Users,
  'platform-16': TrendingUp,
  'platform-17': ShieldCheck,
  'platform-18': BarChart2,
  'platform-19': Brain,
  'platform-20': Settings,
  'platform-21': Target,
  'platform-22': BarChart2,
  'platform-23': Users,
  'platform-24': Zap,
  'platform-25': Brain,
  'platform-26': TrendingUp,
  'platform-27': ShieldCheck,
  'platform-28': BarChart2,
  'platform-29': Brain,
  'platform-30': GraduationCap,
  'platform-31': Lock,
  'platform-32': Layers,
  'platform-33': Target,
  'platform-34': Users,
  'platform-35': ShieldCheck,
  'platform-36': TrendingUp,
  'platform-37': Users,
  'platform-38': Zap,
  'platform-39': Brain,
  'platform-40': TrendingUp,
};

const CATEGORY_ICON_MAP: Record<string, React.ElementType> = {
  'model-siap-pakai': Zap,
  'prediksi-harga':   TrendingUp,
  'deteksi-churn':    Users,
  'klasifikasi-kualitas': ShieldCheck,
  'deteksi-anomali':  AlertCircle,
  'komunitas':        Handshake,
};

const CATEGORY_ICON_COLOR: Record<string, string> = {
  'model-siap-pakai':     'text-primary-600 dark:text-primary-400',
  'prediksi-harga':       'text-regression-600  dark:text-regression-400',
  'deteksi-churn':        'text-warning-600 dark:text-warning-400',
  'klasifikasi-kualitas': 'text-classification-600   dark:text-classification-400',
  'deteksi-anomali':      'text-error-600    dark:text-error-400',
  'komunitas':            'text-gray-600   dark:text-gray-400',
};

function ModelIcon({ modelId, category, size = 'md' }: { modelId: string; category?: string; size?: 'sm'|'md'|'lg' }) {
  const Icon = MODEL_ICON_MAP[modelId]
    ?? CATEGORY_ICON_MAP[category ?? '']
    ?? Brain;
  const sz = size === 'lg' ? 'h-8 w-8' : size === 'sm' ? 'h-4 w-4' : 'h-6 w-6';
  const color = CATEGORY_ICON_COLOR[category ?? ''] ?? 'text-primary-600 dark:text-primary-400';
  return <Icon className={`${sz} ${color} shrink-0`} />;
}

function CategoryIconEl({ catId, size = 24 }: { catId: string; size?: number }) {
  const Icon = CATEGORY_ICON_MAP[catId] ?? Target;
  const color = CATEGORY_ICON_COLOR[catId] ?? 'text-gray-500';
  return <Icon className={color} style={{ width: size, height: size }} />;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StarRating({ rating, count, size = 'sm' }: { rating: number; count: number; size?: 'sm'|'md' }) {
  const sz = size === 'md' ? 'h-5 w-5' : 'h-3.5 w-3.5';
  return (
    <div className="flex items-center gap-1">
      <div className="flex">
        {[1,2,3,4,5].map((v) => (
          <Star key={v} className={`${sz} ${v <= Math.round(rating) ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300 dark:text-gray-600'}`} />
        ))}
      </div>
      <span className={`${size === 'md' ? 'text-sm' : 'text-xs'} text-gray-500 dark:text-gray-400`}>
        {rating.toFixed(1)} ({count})
      </span>
    </div>
  );
}

function MetricBadge({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2 text-center dark:bg-gray-700/50">
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-0.5 text-sm font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}

function PlatformBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs font-medium text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
      <Zap className="h-3 w-3" /> Platform
    </span>
  );
}

// ─── Model Card ───────────────────────────────────────────────────────────────

function ModelCard({ model, onSelect }: { model: MarketplaceModel; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className="group w-full rounded-xl border border-gray-200 bg-white p-5 text-left transition-all hover:border-primary-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-primary-600"
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700">
            <ModelIcon modelId={model.id} category={model.category} size="md" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900 group-hover:text-primary-600 dark:text-white dark:group-hover:text-primary-400">
              {model.model_name}
            </h3>
            <div className="flex items-center gap-1.5">
              {model.is_platform_model && <PlatformBadge />}
              {!model.is_platform_model && model.status === 'pending' && (
                <span className="inline-flex items-center gap-1 rounded-full bg-warning-50 px-2 py-0.5 text-xs font-medium text-warning-700 dark:bg-warning-900/30 dark:text-warning-300">⏳ Review</span>
              )}
              {!model.is_platform_model && model.status === 'approved' && (
                <span className="inline-flex items-center gap-1 rounded-full bg-success-50 px-2 py-0.5 text-xs font-medium text-success-700 dark:bg-success-900/30 dark:text-success-300">✓ OK</span>
              )}
            </div>
          </div>
        </div>
        <ChevronRight className="h-4 w-4 shrink-0 text-gray-400 transition-transform group-hover:translate-x-0.5" />
      </div>

      <p className="mb-3 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">
        {model.use_case ?? model.description}
      </p>

      <div className="mb-3 flex flex-wrap gap-1">
        {model.tags.slice(0, 3).map((tag) => (
          <span key={tag} className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            {tag}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between border-t border-gray-100 pt-3 dark:border-gray-700">
        <StarRating rating={model.rating} count={model.rating_count} />
        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
          <Download className="h-3 w-3" />
          {model.downloads.toLocaleString('id-ID')}
        </div>
      </div>
    </button>
  );
}

// ─── Category Card ────────────────────────────────────────────────────────────

const colorMap: Record<string, string> = {
  primary: 'border-primary-200 bg-primary-50 hover:border-primary-400 dark:border-primary-700 dark:bg-primary-900/20',
  regression: 'border-regression-200  bg-regression-50  hover:border-regression-400  dark:border-regression-700  dark:bg-regression-900/20',
  warning: 'border-warning-200 bg-warning-50 hover:border-warning-400 dark:border-warning-700 dark:bg-warning-900/20',
  classification:   'border-classification-200   bg-classification-50   hover:border-classification-400   dark:border-classification-700   dark:bg-classification-900/20',
  error:    'border-error-200    bg-error-50    hover:border-error-400    dark:border-error-700    dark:bg-error-900/20',
  gray:   'border-gray-200   bg-gray-50   hover:border-gray-400   dark:border-gray-700   dark:bg-gray-800',
};

const iconBgMap: Record<string, string> = {
  primary: 'bg-primary-100 dark:bg-primary-900/40',
  regression:  'bg-regression-100  dark:bg-regression-900/40',
  warning: 'bg-warning-100 dark:bg-warning-900/40',
  classification:   'bg-classification-100   dark:bg-classification-900/40',
  error:    'bg-error-100    dark:bg-error-900/40',
  gray:   'bg-gray-100   dark:bg-gray-700',
};

function CategoryCard({ cat, modelCount, onSelect }: { cat: Category; modelCount: number; onSelect: () => void }) {
  const border = colorMap[cat.color] ?? colorMap.gray;
  const iconBg = iconBgMap[cat.color] ?? iconBgMap.gray;
  return (
    <button
      onClick={onSelect}
      className={`group w-full rounded-xl border-2 p-5 text-left transition-all hover:shadow-md ${border}`}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${iconBg}`}>
          <CategoryIconEl catId={cat.id} size={22} />
        </div>
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">{modelCount} model</span>
      </div>
      <h3 className="mb-1 font-semibold text-gray-900 dark:text-white">{cat.label}</h3>
      <p className="text-sm text-gray-500 dark:text-gray-400">{cat.description}</p>
      <div className="mt-3 flex items-center gap-1 text-sm font-medium text-primary-600 dark:text-primary-400">
        Lihat model <ChevronRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
      </div>
    </button>
  );
}

// ─── Rating Modal ─────────────────────────────────────────────────────────────

function RatingModal({ shareId, modelName, onClose, onSubmit }: {
  shareId: string; modelName: string;
  onClose: () => void;
  onSubmit: (rating: number, review: string) => void;
}) {
  const [hovered, setHovered] = useState(0);
  const [selected, setSelected] = useState(0);
  const [review, setReview] = useState('');
  const labels = ['', 'Sangat Buruk', 'Kurang Memuaskan', 'Cukup', 'Bagus', 'Sangat Bagus'];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="font-semibold text-gray-900 dark:text-white">Beri Rating</h3>
          <button onClick={onClose}><X className="h-5 w-5 text-gray-400 hover:text-gray-600" /></button>
        </div>
        <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">{modelName}</p>
        <div className="mb-2 flex justify-center gap-2">
          {[1,2,3,4,5].map((v) => (
            <button key={v} onMouseEnter={() => setHovered(v)} onMouseLeave={() => setHovered(0)} onClick={() => setSelected(v)}>
              <Star className={`h-8 w-8 transition-colors ${v <= (hovered || selected) ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300 dark:text-gray-600'}`} />
            </button>
          ))}
        </div>
        {selected > 0 && <p className="mb-4 text-center text-sm font-medium text-gray-700 dark:text-gray-300">{labels[selected]}</p>}
        <textarea value={review} onChange={(e) => setReview(e.target.value)} rows={3}
          placeholder="Ulasan singkat (opsional)..."
          className="mb-4 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
        <div className="flex gap-2">
          <button onClick={onClose} className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300">Batal</button>
          <button disabled={selected === 0} onClick={() => onSubmit(selected, review)}
            className="flex-1 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
            Kirim Rating
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Column Matching Panel ────────────────────────────────────────────────────

function ColumnMatchPanel({ matches, userColumns, onChange }: {
  matches: ColumnMatch[]; userColumns: string[];
  onChange: (mapping: Record<string, string>) => void;
}) {
  const [mapping, setMapping] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    matches.forEach((m) => { if (m.suggested_user_column) init[m.required_column] = m.suggested_user_column; });
    return init;
  });

  useEffect(() => {
    const init: Record<string, string> = {};
    matches.forEach((m) => { if (m.suggested_user_column) init[m.required_column] = m.suggested_user_column; });
    setMapping(init);
    onChange(init);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matches]);

  const update = (req: string, val: string) => {
    const next = { ...mapping, [req]: val };
    setMapping(next);
    onChange(next);
  };

  return (
    <div className="space-y-2">
      {matches.map((m) => (
        <div key={m.required_column} className="flex items-center gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
          <div className="w-48 shrink-0">
            <p className="text-xs font-medium text-gray-700 dark:text-gray-300">{m.required_column}</p>
            <p className="text-xs text-gray-400">Dibutuhkan model</p>
          </div>
          <div className="flex-1">
            <select value={mapping[m.required_column] ?? ''} onChange={(e) => update(m.required_column, e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
              <option value="">-- Pilih kolom --</option>
              {userColumns.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="w-16 shrink-0 text-right">
            {m.confidence >= 0.7
              ? <span className="text-xs font-medium text-green-600">Cocok</span>
              : m.confidence >= 0.3
              ? <span className="text-xs text-orange-500">Mirip</span>
              : <span className="text-xs text-gray-400">Manual</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Prediction Result Card ───────────────────────────────────────────────────

function PredictionResultCard({ result, resultLabel, resultUnit }: {
  result: PredictionResult; resultLabel: string; resultUnit?: string | null;
}) {
  if (result.result_type === 'regression') {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
        <p className="mb-1 text-sm text-gray-500 dark:text-gray-400">Data #{result.index + 1}</p>
        <div className="flex items-end gap-2">
          <span className="text-3xl font-bold text-primary-600 dark:text-primary-400">
            {Number(result.prediction).toLocaleString('id-ID', { maximumFractionDigits: 2 })}
          </span>
          {resultUnit && <span className="mb-1 text-sm text-gray-500">{resultUnit}</span>}
        </div>
        <p className="mt-1 text-xs text-gray-400">{resultLabel}</p>
      </div>
    );
  }
  const isPositive = String(result.prediction) === '1';
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
      <p className="mb-1 text-sm text-gray-500 dark:text-gray-400">Data #{result.index + 1}</p>
      <div className={`mb-3 inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${
        isPositive ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
                   : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'}`}>
        {isPositive ? <AlertCircle className="h-4 w-4" /> : <CheckCircle className="h-4 w-4" />}
        {result.prediction_label}
      </div>
      {result.probabilities && (
        <div className="space-y-1.5">
          {Object.entries(result.probabilities).map(([label, p]) => (
            <div key={label}>
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>{label}</span><span>{Math.round(Number(p) * 100)}%</span>
              </div>
              <div className="mt-0.5 h-2 rounded-full bg-gray-200 dark:bg-gray-600">
                <div className="h-2 rounded-full bg-primary-500 transition-all" style={{ width: `${Math.round(Number(p) * 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Detail View ──────────────────────────────────────────────────────────────

function ModelDetailView({ model, onBack, onPredict, onRate }: {
  model: MarketplaceModel; onBack: () => void; onPredict: () => void; onRate: () => void;
}) {
  const metricEntries = Object.entries(model.metrics ?? {}).filter(([, v]) => typeof v === 'number');
  const metricLabel: Record<string, string> = {
    accuracy: 'Akurasi', f1: 'F1 Score', precision: 'Presisi',
    recall: 'Recall', r2: 'R² Score', mae: 'MAE', rmse: 'RMSE',
  };
  const formatMetric = (k: string, v: number) =>
    ['accuracy','f1','precision','recall','r2'].includes(k) ? `${(v*100).toFixed(1)}%`
    : v.toLocaleString('id-ID', { maximumFractionDigits: 1 });

  return (
    <div className="space-y-6">
      <button onClick={onBack} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white">
        <ArrowLeft className="h-4 w-4" /> Kembali
      </button>

      <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="mb-4 flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gray-100 dark:bg-gray-700">
              <ModelIcon modelId={model.id} category={model.category} size="lg" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{model.model_name}</h1>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {model.is_platform_model && <PlatformBadge />}
                {model.algorithm && <span className="text-xs text-gray-500 dark:text-gray-400">Algoritma: {model.algorithm}</span>}
                {!model.is_platform_model && model.status === 'pending' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-warning-50 px-2 py-0.5 text-xs font-medium text-warning-700 dark:bg-warning-900/30 dark:text-warning-300">
                    ⏳ Menunggu Review
                  </span>
                )}
                {!model.is_platform_model && model.status === 'approved' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-success-50 px-2 py-0.5 text-xs font-medium text-success-700 dark:bg-success-900/30 dark:text-success-300">
                    ✓ Disetujui
                  </span>
                )}
                {!model.is_platform_model && model.status === 'rejected' && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-error-50 px-2 py-0.5 text-xs font-medium text-error-700 dark:bg-error-900/30 dark:text-error-300">
                    ✗ Ditolak
                  </span>
                )}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={onRate} className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">
              <Star className="h-4 w-4" /> Beri Rating
            </button>
            <button onClick={onPredict} className="flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
              <Zap className="h-4 w-4" /> Gunakan Model
            </button>
          </div>
        </div>

        <div className="mb-4 flex items-center gap-4">
          <StarRating rating={model.rating} count={model.rating_count} size="md" />
          <div className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
            <Download className="h-4 w-4" />{model.downloads.toLocaleString('id-ID')} digunakan
          </div>
        </div>

        {model.is_platform_model && (
          <div className="mb-4 grid grid-cols-3 gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
            <div className="text-center">
              <p className="text-lg font-bold text-primary-600 dark:text-primary-400">{(model.metrics?.accuracy ?? 0) > 1 ? ((model.metrics?.accuracy ?? 0)*100).toFixed(1)+'%' : 'N/A'}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Akurasi</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-primary-600 dark:text-primary-400">{model.downloads.toLocaleString()}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Pengguna</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-primary-600 dark:text-primary-400">{model.rating_count}</p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Rating</p>
            </div>
          </div>
        )}

        <p className="mb-4 text-gray-600 dark:text-gray-400">{model.description ?? model.use_case}</p>

        {model.use_case && model.description && (
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
            <Target className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
            <div>
              <p className="text-sm font-medium text-blue-800 dark:text-blue-300">Cocok untuk:</p>
              <p className="mt-0.5 text-sm text-blue-700 dark:text-blue-400">{model.use_case}</p>
            </div>
          </div>
        )}

        {metricEntries.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Performa Model</p>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {metricEntries.map(([k, v]) => (
                <MetricBadge key={k} label={metricLabel[k] ?? k} value={formatMetric(k, v)} />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <h2 className="mb-3 font-semibold text-gray-900 dark:text-white">
          Data yang Dibutuhkan ({model.feature_names.length} kolom)
        </h2>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {model.feature_names.map((f) => (
            <div key={f} className="flex items-center gap-2 rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-700/50">
              <CheckCircle className="h-4 w-4 shrink-0 text-green-500" />
              <span className="text-sm text-gray-700 dark:text-gray-300">{f}</span>
            </div>
          ))}
        </div>
        {model.target_column && (
          <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
            Menghasilkan: <span className="font-medium text-gray-700 dark:text-gray-300">{model.target_column}</span>
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Smart field detection for marketplace ──────────────────────────────────

type FieldKind = 'currency' | 'date' | 'percent' | 'number' | 'text';

const MKT_CURRENCY_KW = ['harga', 'gaji', 'pendapatan', 'biaya', 'tagihan', 'omset', 'laba', 'revenue', 'cost', 'price', 'salary', 'income', 'sewa', 'tagihan', 'belanja', 'skor', ' nilai'];
const MKT_DATE_KW = ['tanggal', 'tgl', 'date', 'waktu', 'time', 'bulan', 'tahun'];
const MKT_PERCENT_KW = ['persen', 'persentase', 'percent', 'rate', 'rasio', 'ratio', 'kelembaban'];

function detectMarketFieldKind(name: string): FieldKind {
  const n = name.toLowerCase();
  if (MKT_DATE_KW.some((k) => n.includes(k))) return 'date';
  if (MKT_CURRENCY_KW.some((k) => n.includes(k))) return 'currency';
  if (MKT_PERCENT_KW.some((k) => n.includes(k))) return 'percent';
  return 'text';
}

/** Realistic sample values per field name pattern */
const SAMPLE_VALUES: Record<string, string> = {
  luas_bangunan: '120', luas_tanah: '200', kamar_tidur: '3', kamar_mandi: '2',
  jumlah_kamar: '3', lantai: '2', tahun: '2020', tahun_produksi: '2019',
  jarak_pusat: '5', jarak: '150', jarak_km: '150', jarak_tempuh_km: '35000',
  lama_berlangganan_bulan: '24', total_tagihan: '250000', jumlah_komplain: '2',
  frekuensi_login_per_bulan: '12', fitur_yang_digunakan: '5', perubahan_paket_6_bulan: '-1',
  ipk: '3.2', ipk_semester_terakhir: '3.5', persentase_kehadiran: '85',
  jumlah_mata_kuliah_lulus: '15', jumlah_mata_kuliah_gagal: '1', aktivitas_ekstrakulikuler: '1',
  beasiswa: '0', harga_jual: '150000', diskon_persen: '10', jumlah_iklan: '20',
  stok_tersedia: '100', penjualan_bulan_lalu: '250', bulan: '6', volume_penjualan: '300',
  jumlah_transaksi: '15', jam_transaksi: '14', lokasi_berbeda: '1',
  frekuensi_per_hari: '8', rata_rata_transaksi_bulanan: '500000', umur_akun_hari: '365',
  suhu_mesin_celsius: '200', tekanan_bar: '5', kecepatan_rpm: '1500',
  kelembaban_persen: '60', waktu_proses_menit: '25', shift_kerja: '1',
  pengalaman: '5', tahun_pengalaman: '5', tingkat_pendidikan: '3', jumlah_skill: '8',
  skor_keahlian: '75', lokasi_kota: '3', lokasi: '3', jenis_industri: '2',
  ukuran_perusahaan: '3', pendapatan_per_bulan: '8', total_utang: '20',
  jumlah_tanggungan: '2', lamanya_kerja_bulan: '48', riwayat_tepat_waktu: '85',
  jumlah_pinjaman_aktif: '2', skor_kredit: '700', jenis_bahan_bakar: '2',
  kapasitas_mesin_cc: '1500', kondisi_exterior: '4', kondisi_interior: '4', jumlah_pemilik: '2',
  warna_daun: '2', bintik_daun: '1', kondisi_akar: '1', suhu_lahan: '28',
  kelembaban_tanah: '65', curah_hujan_mingguan: '150', umur_tanaman_hari: '90',
  jumlah_penghuni: '3', luas_rumah_m2: '80', jumlah_ac: '2', jumlah_kulkas: '1',
  jam_penggunaan_tv: '5', jam_penggunaan_mesin_cuci: '3', musim: '2',
  pm25: '35', pm10: '50', suhu_celsius: '30', angin: '10', kecepatan_angin_kmh: '10',
  lalu_lintas_kendaraan: '50', industri_terdekat: '0',
  jumlah_huruf_kapital: '5', jumlah_tautan: '2', jumlah_akhir_tanda_tanya: '1',
  panjang_teks: '200', ada_kata_gratis: '0', ada_kata_klik: '0', pengirim_dikenal: '1',
  jenis_layanan: '2', berat_paket_kg: '5', kota_asal: '1', kota_tujuan: '5',
  kondisi_cuaca: '1', hari_dalam_minggu: '3', hari: '3',
  jumlah_emoji: '2', ada_kata_positif: '1', ada_kata_negatif: '0',
  rating_bintang: '4', jumlah_kalimat: '8', pola_kapital: '0',
  nama_komoditas: '1', harga_bulan_lalu: '35', persediaan_ton: '100',
  jumlah_petani: '500', inflasi_persen: '3.5', hari_libur: '0', libur: '0',
  omset_per_bulan_juta: '25', biaya_operasional_juta: '15', lama_usaha_bulan: '36',
  jumlah_karyawan: '5', jenis_usaha: '3', riwayat_kredit: '1', jaminan: '1',
  penjualan_30_hari: '200', tren_penjualan: '5', hari_libur_mendatang: '2',
  jumlah_sku: '50', lead_time_hari: '7', promo_mendatang: '0',
  warna_daun_nilai: '7', aroma_intensitas: '6', bentuk_daun: '3',
  ukuran_daun_mm: '25', kadar_kafein: '2', tahun_panen: '2025',
  fitur_digunakan: '8', tagihan_bulan: '150', nps_score: '8', referensi_dibuat: '3',
  ca_125: '15', cea: '2', psa: '4', hemoglobin: '13', leukosit: '7',
  trombosit: '250', kreatinin: '1', sgot_sgot_rasio: '1.2',
  booking_online: '1', event_lokasi: '0', cuaca_prediksi: '1',
  harga_kamar_rata: '500000', tren_liburan: '50',
  waktu_tunggu_menit: '10', akurasi_pesanan: '1', suhu_makanan: '60',
  rating_layanan: '4', repeat_order: '1', total_belanja: '150000',
  curah_hujan_bulan_lalu: '200', suhu_permukaan_laut: '29', kelembaban_relatif: '75',
  tekanan_udara: '1010', angin_monsum: '1', el_nino_index: '0.5',
  tinggi_badan_cm: '85', berat_badan_kg: '12', umur_bulan: '24',
  lingkar_lengan: '15', lingkar_kepala: '48', imunisasi_lengkap: '1', asi_eksklusif: '1',
  views_per_video: '5000', engagement_rate: '0.05', frekuensi_upload: '3',
  durasi_rata_video: '12', topik_konten: '5', jumlah_kolaborasi: '2',
  subscriber: '10000', views: '5000', durasi_jam: '20', jumlah_modul: '15',
  rating_instruktur: '4.5', sertifikat: '1', platform_hosting: '1',
  frekuensi_posting: '5', waktu_aktif_reguler: '1', rasio_following_followers: '0.8',
  panjang_komentar_rata: '30', ada_link_spam: '0', usia_akun_hari: '500', variasi_waktu_posting: '0.5',
  ketinggian_mdpl: '500', lintang_bujur: '50',
  rasio_lebar_tinggi_wajah: '0.75', posisi_alis: '3', bentuk_rahang: '3',
  panjang_rambut: '2', textur_kulit: '3', sudut_dahi: '3', proporsi_mata: '3',
  suhu: '28', tekstur: '3', berat: '100', ukuran: '50', bau: '2', air: '50',
  ph: '7.0', turbidity_ntu: '10', turbidity: '10', tds_ppm: '200', tds: '200',
  klorin_mg_l: '0.5', bakteri_coliform: '0', logam_berat_ppm: '0', logam: '0',
  harga_kemarin: '1000000', nilai_tukar_usd: '15500', inflasi: '3',
  suku_bunga: '6', harga_minyak: '80', indeks_saham: '6500', volume_perdagangan: '5000',
  area_opacitas_persen: '25', lokasi_lesi: '2', simetri_paru: '3',
  kontras_gambar: '3', tekstur_jaringan: '3', batas_cabang: '3', intensitas_pixel: '3',
  opacitas: '25',
  topik: '5',
};

function formatCurrency(raw: string): string {
  const digits = raw.replace(/[^\d]/g, '');
  if (!digits) return '';
  return Number(digits).toLocaleString('id-ID');
}

// ─── Marketplace Smart Input ────────────────────────────────────────────────

function MarketplaceSmartField({ name, value, onChange }: { name: string; value: string; onChange: (v: string) => void }) {
  const kind = detectMarketFieldKind(name);
  const label = name.replace(/_/g, ' ');
  const sample = SAMPLE_VALUES[name] || '';
  const inputCls = 'w-full rounded-lg border border-gray-300 bg-white text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500';

  if (kind === 'date') {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
        <input type="date" value={value} onChange={(e) => onChange(e.target.value)} className={`${inputCls} px-3 py-2.5`} />
      </div>
    );
  }

  if (kind === 'currency') {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
        <div className="relative">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium text-gray-500 dark:text-gray-400">Rp</span>
          <input type="text" inputMode="numeric" value={value} onChange={(e) => onChange(formatCurrency(e.target.value))}
            placeholder={sample ? formatCurrency(sample) : '0'} className={`${inputCls} py-2.5 pl-9 pr-3`} />
        </div>
      </div>
    );
  }

  if (kind === 'percent') {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
        <div className="relative">
          <input type="number" min={0} max={100} step={0.1} value={value} onChange={(e) => onChange(e.target.value)}
            placeholder={sample || '0-100'} className={`${inputCls} py-2.5 pl-3 pr-9`} />
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-500 dark:text-gray-400">%</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
      <input type="text" value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={sample ? `contoh: ${sample}` : `Masukkan ${label}...`}
        className={`${inputCls} px-3 py-2.5`} />
    </div>
  );
}

// ─── Predict View ─────────────────────────────────────────────────────────────

function PredictView({ model, onBack }: { model: MarketplaceModel; onBack: () => void }) {
  const { toast } = useToast();
  const [step, setStep] = useState<'input'|'matching'|'results'>('input');
  const [formValues, setFormValues] = useState<Record<string, string>>(
    () => Object.fromEntries(model.feature_names.map((f) => [f, '']))
  );
  const [csvRows, setCsvRows] = useState<Record<string, any>[]>([]);
  const [csvColumns, setCsvColumns] = useState<string[]>([]);
  const [colMatches, setColMatches] = useState<ColumnMatch[]>([]);
  const [colMapping, setColMapping] = useState<Record<string, string>>({});
  const fileRef = useRef<HTMLInputElement>(null);
  const [predicting, setPredicting] = useState(false);
  const [results, setResults] = useState<PredictionResult[]>([]);
  const [resultMeta, setResultMeta] = useState<{ label: string; unit?: string|null }>({ label: '' });
  const [inputMode, setInputMode] = useState<'manual'|'csv'>('manual');

  const runManualPredict = async () => {
    setPredicting(true);
    try {
      const row: Record<string, any> = {};
      model.feature_names.forEach((f) => {
        const raw = formValues[f];
        row[f] = isNaN(Number(raw)) || raw === '' ? raw : Number(raw);
      });
      const res = await marketplaceApi.platformPredict({ share_id: model.id, data: [row] });
      setResults(res.data.predictions);
      setResultMeta({ label: res.data.result_label, unit: res.data.result_unit });
      setStep('results');
    } catch (err) { toast('error', formatApiError(err, 'Prediksi gagal')); }
    finally { setPredicting(false); }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    const lines = text.trim().split('\n');
    if (lines.length < 2) { toast('error', 'File CSV kosong atau tidak valid'); return; }
    const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
    const rows = lines.slice(1).map((line) => {
      const vals = line.split(',').map((v) => v.trim().replace(/^"|"$/g, ''));
      const row: Record<string, any> = {};
      headers.forEach((h, i) => { row[h] = vals[i] ?? ''; });
      return row;
    });
    setCsvColumns(headers); setCsvRows(rows);
    try {
      const matchRes = await marketplaceApi.matchColumns(model.id, headers);
      setColMatches(matchRes.data.matches);
    } catch {
      setColMatches(model.feature_names.map((f) => ({ required_column: f, suggested_user_column: null, confidence: 0 })));
    }
    setStep('matching');
  };

  const runCsvPredict = async () => {
    setPredicting(true);
    try {
      const res = await marketplaceApi.platformPredict({ share_id: model.id, data: csvRows, column_mapping: colMapping });
      setResults(res.data.predictions);
      setResultMeta({ label: res.data.result_label, unit: res.data.result_unit });
      setStep('results');
    } catch (err) { toast('error', formatApiError(err, 'Prediksi gagal')); }
    finally { setPredicting(false); }
  };

  const stepLabels = ['Masukkan Data', 'Cocokkan Kolom', 'Hasil'];
  const stepKeys  = ['input', 'matching', 'results'];
  const stepIdx   = stepKeys.indexOf(step);

  return (
    <div className="space-y-6">
      <button onClick={onBack} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white">
        <ArrowLeft className="h-4 w-4" /> Kembali ke Detail
      </button>

      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-700">
          <ModelIcon modelId={model.id} category={model.category} size="md" />
        </div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">Gunakan: {model.model_name}</h1>
      </div>

      <div className="flex gap-2">
        {stepLabels.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium ${
              i === stepIdx ? 'bg-primary-600 text-white'
              : i < stepIdx  ? 'bg-green-500 text-white'
                             : 'bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}`}>{i+1}</div>
            <span className="hidden text-xs text-gray-500 sm:block">{label}</span>
            {i < 2 && <ChevronRight className="h-3 w-3 text-gray-300" />}
          </div>
        ))}
      </div>

      {step === 'input' && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-4 flex gap-2">
            {(['manual','csv'] as const).map((m) => (
              <button key={m} onClick={() => setInputMode(m)}
                className={`rounded-lg px-4 py-2 text-sm font-medium ${inputMode === m ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'}`}>
                {m === 'manual' ? 'Isi Manual' : 'Upload CSV'}
              </button>
            ))}
          </div>
          {inputMode === 'manual' ? (
            <>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {model.feature_names.map((f) => (
                  <MarketplaceSmartField key={f} name={f} value={formValues[f]}
                    onChange={(v) => setFormValues((p) => ({ ...p, [f]: v }))} />
                ))}
              </div>
              <button onClick={runManualPredict}
                disabled={predicting || model.feature_names.some((f) => !formValues[f])}
                className="mt-5 flex items-center gap-2 rounded-lg bg-primary-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
                {predicting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                {predicting ? 'Memproses...' : 'Prediksi Sekarang'}
              </button>
            </>
          ) : (
            <div onClick={() => fileRef.current?.click()}
              className="cursor-pointer rounded-xl border-2 border-dashed border-gray-300 p-10 text-center hover:border-primary-400 dark:border-gray-600">
              <FileSpreadsheet className="mx-auto mb-3 h-10 w-10 text-gray-400" />
              <p className="font-medium text-gray-700 dark:text-gray-300">Upload file CSV kamu</p>
              <p className="mt-1 text-sm text-gray-500">Klik atau drag & drop di sini</p>
              <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
            </div>
          )}
        </div>
      )}

      {step === 'matching' && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="mb-1 font-semibold text-gray-900 dark:text-white">Cocokkan Kolom Data Kamu</h2>
          <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">Kami sudah otomatis mencocokkan — periksa dan sesuaikan jika perlu.</p>
          <ColumnMatchPanel matches={colMatches} userColumns={csvColumns} onChange={setColMapping} />
          <div className="mt-4 flex gap-2">
            <button onClick={() => setStep('input')} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300">Kembali</button>
            <button onClick={runCsvPredict} disabled={predicting}
              className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
              {predicting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
              {predicting ? 'Memproses...' : `Prediksi ${csvRows.length} Baris`}
            </button>
          </div>
        </div>
      )}

      {step === 'results' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900 dark:text-white">Hasil Prediksi ({results.length} data)</h2>
            <button onClick={() => { setStep('input'); setResults([]); }} className="text-sm text-primary-600 hover:underline dark:text-primary-400">Coba Lagi</button>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {results.map((r) => (
              <PredictionResultCard key={r.index} result={r} resultLabel={resultMeta.label} resultUnit={resultMeta.unit} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function MarketplacePage() {
  const { toast } = useToast();

  const [view, setView] = useState<View>('gallery');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<MarketplaceModel | null>(null);

  const [categories, setCategories] = useState<Category[]>([]);
  const [allModels, setAllModels] = useState<MarketplaceModel[]>([]);
  const [filteredModels, setFilteredModels] = useState<MarketplaceModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  const [showRating, setShowRating] = useState(false);
  const [ratingTarget, setRatingTarget] = useState<MarketplaceModel | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [catRes, modRes] = await Promise.all([
          marketplaceApi.categories(),
          marketplaceApi.discover(),
        ]);
        setCategories(catRes.data.categories ?? []);
        setAllModels(modRes.data.models ?? []);
        setFilteredModels(modRes.data.models ?? []);
      } catch (err) {
        toast('error', formatApiError(err, 'Gagal memuat marketplace'));
      } finally { setLoading(false); }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let list = allModels;
    if (activeCategory === 'model-siap-pakai') list = list.filter((m) => m.is_platform_model);
    else if (activeCategory === 'komunitas') list = list.filter((m) => !m.is_platform_model);
    else if (activeCategory) list = list.filter((m) => m.category === activeCategory);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((m) =>
        m.model_name.toLowerCase().includes(q) ||
        (m.description ?? '').toLowerCase().includes(q) ||
        m.tags.some((t) => t.toLowerCase().includes(q))
      );
    }
    setFilteredModels(list);
  }, [search, activeCategory, allModels]);

  const handleRate = async (rating: number, review: string) => {
    if (!ratingTarget) return;
    try {
      const res = await marketplaceApi.rate(ratingTarget.id, rating, review);
      toast('success', `Rating ${res.data.new_rating} tersimpan — terima kasih!`);
      setAllModels((prev) => prev.map((m) =>
        m.id === ratingTarget.id ? { ...m, rating: res.data.new_rating, rating_count: res.data.rating_count } : m
      ));
      if (selectedModel?.id === ratingTarget.id)
        setSelectedModel((m) => m ? { ...m, rating: res.data.new_rating, rating_count: res.data.rating_count } : m);
    } catch (err) { toast('error', formatApiError(err, 'Gagal menyimpan rating')); }
    setShowRating(false); setRatingTarget(null);
  };

  const modelCountByCategory = (catId: string) => {
    if (catId === 'model-siap-pakai') return allModels.filter((m) => m.is_platform_model).length;
    if (catId === 'komunitas') return allModels.filter((m) => !m.is_platform_model).length;
    return allModels.filter((m) => m.category === catId).length;
  };

  const openDetail = (m: MarketplaceModel) => { setSelectedModel(m); setView('detail'); };
  const openRate  = (m: MarketplaceModel) => { setRatingTarget(m); setShowRating(true); };

  // ── Predict view ──────────────────────────────────────────────────────────
  if (view === 'predict' && selectedModel)
    return <PredictView model={selectedModel} onBack={() => setView('detail')} />;

  // ── Detail view ───────────────────────────────────────────────────────────
  if (view === 'detail' && selectedModel)
    return (
      <>
        <ModelDetailView
          model={selectedModel}
          onBack={() => setView(activeCategory ? 'category' : 'gallery')}
          onPredict={() => setView('predict')}
          onRate={() => openRate(selectedModel)}
        />
        {showRating && ratingTarget && (
          <RatingModal shareId={ratingTarget.id} modelName={ratingTarget.model_name}
            onClose={() => { setShowRating(false); setRatingTarget(null); }} onSubmit={handleRate} />
        )}
      </>
    );

  // ── Gallery / category list ───────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        {activeCategory && (
          <button onClick={() => { setActiveCategory(null); setSearch(''); }}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 dark:hover:text-white">
            <ArrowLeft className="h-4 w-4" />
          </button>
        )}
        <Store className="h-7 w-7 text-primary-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {activeCategory ? (categories.find((c) => c.id === activeCategory)?.label ?? 'Marketplace') : 'Marketplace Model'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {activeCategory
              ? `${filteredModels.length} model tersedia`
              : 'Temukan model siap pakai untuk kasus bisnis kamu'}
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Cari berdasarkan kasus, kata kunci, atau tag..."
          className="w-full rounded-xl border border-gray-300 bg-white py-2.5 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-800 dark:text-white" />
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-40 animate-pulse rounded-xl bg-gray-200 dark:bg-gray-700" />
          ))}
        </div>
      ) : !activeCategory && !search ? (
        <>
          {/* Hero banner */}
          <div className="rounded-2xl bg-gradient-to-r from-purple-600 to-primary-600 p-6 text-white">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="mb-1 flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  <span className="text-sm font-medium opacity-90">Model Siap Pakai</span>
                </div>
                <h2 className="text-xl font-bold">Upload data kamu, langsung dapat hasil.</h2>
                <p className="mt-1 text-sm opacity-80">Tidak perlu training, tidak perlu paham algoritma — model sudah jadi dari awal.</p>
              </div>
              <button onClick={() => setActiveCategory('model-siap-pakai')}
                className="shrink-0 rounded-xl bg-white/20 px-4 py-2 text-sm font-medium hover:bg-white/30">
                Lihat Semua
              </button>
            </div>
          </div>

          {/* Category grid */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {categories.map((cat) => (
              <CategoryCard key={cat.id} cat={cat} modelCount={modelCountByCategory(cat.id)}
                onSelect={() => setActiveCategory(cat.id)} />
            ))}
          </div>

          {/* Top models */}
          <div>
            <h2 className="mb-3 font-semibold text-gray-900 dark:text-white">Paling Banyak Digunakan</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[...allModels].sort((a, b) => b.downloads - a.downloads).slice(0, 3).map((m) => (
                <ModelCard key={m.id} model={m} onSelect={() => openDetail(m)} />
              ))}
            </div>
          </div>
        </>
      ) : (
        filteredModels.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16 dark:border-gray-600">
            <Store className="mb-3 h-12 w-12 text-gray-300 dark:text-gray-600" />
            <p className="text-gray-500 dark:text-gray-400">Tidak ada model yang cocok</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredModels.map((m) => (
              <ModelCard key={m.id} model={m} onSelect={() => openDetail(m)} />
            ))}
          </div>
        )
      )}

      {showRating && ratingTarget && (
        <RatingModal shareId={ratingTarget.id} modelName={ratingTarget.model_name}
          onClose={() => { setShowRating(false); setRatingTarget(null); }} onSubmit={handleRate} />
      )}
    </div>
  );
}
