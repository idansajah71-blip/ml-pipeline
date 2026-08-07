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
  'model-siap-pakai':     'text-purple-600 dark:text-purple-400',
  'prediksi-harga':       'text-green-600  dark:text-green-400',
  'deteksi-churn':        'text-orange-500 dark:text-orange-400',
  'klasifikasi-kualitas': 'text-blue-600   dark:text-blue-400',
  'deteksi-anomali':      'text-red-500    dark:text-red-400',
  'komunitas':            'text-gray-500   dark:text-gray-400',
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
    <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
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
            {model.is_platform_model && <PlatformBadge />}
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
  purple: 'border-purple-200 bg-purple-50 hover:border-purple-400 dark:border-purple-700 dark:bg-purple-900/20',
  green:  'border-green-200  bg-green-50  hover:border-green-400  dark:border-green-700  dark:bg-green-900/20',
  orange: 'border-orange-200 bg-orange-50 hover:border-orange-400 dark:border-orange-700 dark:bg-orange-900/20',
  blue:   'border-blue-200   bg-blue-50   hover:border-blue-400   dark:border-blue-700   dark:bg-blue-900/20',
  red:    'border-red-200    bg-red-50    hover:border-red-400    dark:border-red-700    dark:bg-red-900/20',
  gray:   'border-gray-200   bg-gray-50   hover:border-gray-400   dark:border-gray-700   dark:bg-gray-800',
};

const iconBgMap: Record<string, string> = {
  purple: 'bg-purple-100 dark:bg-purple-900/40',
  green:  'bg-green-100  dark:bg-green-900/40',
  orange: 'bg-orange-100 dark:bg-orange-900/40',
  blue:   'bg-blue-100   dark:bg-blue-900/40',
  red:    'bg-red-100    dark:bg-red-900/40',
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
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={onRate} className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">
              <Star className="h-4 w-4" /> Beri Rating
            </button>
            {model.is_platform_model && (
              <button onClick={onPredict} className="flex items-center gap-1.5 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
                <Zap className="h-4 w-4" /> Gunakan Model
              </button>
            )}
          </div>
        </div>

        <div className="mb-4 flex items-center gap-4">
          <StarRating rating={model.rating} count={model.rating_count} size="md" />
          <div className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
            <Download className="h-4 w-4" />{model.downloads.toLocaleString('id-ID')} digunakan
          </div>
        </div>

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
                  <div key={f}>
                    <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{f.replace(/_/g,' ')}</label>
                    <input type="text" value={formValues[f]}
                      onChange={(e) => setFormValues((p) => ({ ...p, [f]: e.target.value }))}
                      placeholder={`Masukkan ${f.replace(/_/g,' ')}...`}
                      className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
                  </div>
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
