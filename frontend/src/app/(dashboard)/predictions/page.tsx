'use client';

import { useState, useMemo } from 'react';
import {
  Zap, Loader2, CheckCircle, AlertCircle, ChevronDown, ChevronUp,
  RefreshCw, Upload, FileSpreadsheet, X
} from 'lucide-react';
import { models, formatApiError } from '@/lib/api';
import { useModels } from '@/lib/hooks';
import { PredictionItem, MLModel } from '@/types';

// ─── Types ────────────────────────────────────────────────────────────────────

interface PredictionResult {
  predictions?: PredictionItem[];
  latency_ms?: number;
  error?: string;
}

// ─── Result Card ──────────────────────────────────────────────────────────────

function PredictionResultCard({
  pred,
  index,
  model,
  feedbackState,
  feedbackComment,
  onFeedbackChange,
  onFeedback,
}: {
  pred: PredictionItem;
  index: number;
  model: MLModel | undefined;
  feedbackState: 'idle' | 'saving' | 'submitted' | 'error';
  feedbackComment: string;
  onFeedbackChange: (v: string) => void;
  onFeedback: (correct: boolean) => void;
}) {
  const [showFeedback, setShowFeedback] = useState(false);
  const isClassification = pred.probabilities !== undefined || typeof pred.prediction === 'string';
  const predVal = pred.prediction;
  const prob = pred.probability;

  const confidenceColor = prob === undefined ? '' :
    prob >= 0.8 ? 'text-green-600 dark:text-green-400' :
    prob >= 0.5 ? 'text-orange-500 dark:text-orange-400' :
    'text-red-500 dark:text-red-400';

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
          Prediksi #{index + 1}
        </span>
        {prob !== undefined && (
          <span className={`text-sm font-medium ${confidenceColor}`}>
            Keyakinan {(prob * 100).toFixed(1)}%
          </span>
        )}
      </div>

      {/* Main result */}
      <div className={`mb-4 rounded-xl p-4 ${
        isClassification
          ? 'bg-primary-50 dark:bg-primary-900/20'
          : 'bg-gray-50 dark:bg-gray-700/40'
      }`}>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {model?.target_column ? `Nilai: ${model.target_column}` : 'Hasil'}
        </p>
        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
          {typeof predVal === 'number'
            ? predVal.toLocaleString('id-ID', { maximumFractionDigits: 4 })
            : String(predVal)}
        </p>
      </div>

      {/* Probability bars for classification */}
      {pred.probabilities && Object.keys(pred.probabilities).length > 0 && (
        <div className="mb-4 space-y-2">
          <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Distribusi Probabilitas</p>
          {Object.entries(pred.probabilities)
            .sort(([, a], [, b]) => b - a)
            .map(([cls, p]) => (
              <div key={cls}>
                <div className="mb-0.5 flex items-center justify-between text-xs">
                  <span className="text-gray-600 dark:text-gray-400">{cls}</span>
                  <span className="font-medium text-gray-700 dark:text-gray-300">{(p * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-600">
                  <div
                    className="h-2 rounded-full bg-primary-500 transition-all duration-500"
                    style={{ width: `${p * 100}%` }}
                  />
                </div>
              </div>
            ))}
        </div>
      )}

      {/* Feedback toggle */}
      {feedbackState === 'submitted' ? (
        <p className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
          <CheckCircle className="h-3.5 w-3.5" /> Terima kasih, feedback tersimpan
        </p>
      ) : (
        <div>
          <button
            onClick={() => setShowFeedback((p) => !p)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            {showFeedback ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            Beri feedback
          </button>
          {showFeedback && (
            <div className="mt-2 space-y-2">
              <textarea
                value={feedbackComment}
                onChange={(e) => onFeedbackChange(e.target.value)}
                rows={2}
                placeholder="Komentar singkat (opsional)..."
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => onFeedback(true)}
                  disabled={!pred.id || feedbackState === 'saving'}
                  className="flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
                >
                  👍 Benar
                </button>
                <button
                  onClick={() => onFeedback(false)}
                  disabled={!pred.id || feedbackState === 'saving'}
                  className="flex items-center gap-1 rounded-lg bg-red-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-600 disabled:opacity-50"
                >
                  👎 Salah
                </button>
              </div>
              {feedbackState === 'error' && (
                <p className="text-xs text-red-600 dark:text-red-400">Gagal mengirim feedback. Coba lagi.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ─── Smart field detection helpers ───────────────────────────────────────────

type FieldKind = 'currency' | 'date' | 'percent' | 'number' | 'text';

const CURRENCY_KEYWORDS = ['harga', 'gaji', 'pendapatan', 'biaya', 'tagihan', 'omset', 'laba', 'revenue', 'cost', 'price', 'salary', 'income'];
const DATE_KEYWORDS     = ['tanggal', 'tgl', 'date', 'waktu', 'time', 'bulan', 'tahun'];
const PERCENT_KEYWORDS  = ['persen', 'persentase', 'percent', 'rate', 'rasio', 'ratio'];

function detectFieldKind(name: string): FieldKind {
  const n = name.toLowerCase();
  if (DATE_KEYWORDS.some((k) => n.includes(k)))    return 'date';
  if (CURRENCY_KEYWORDS.some((k) => n.includes(k))) return 'currency';
  if (PERCENT_KEYWORDS.some((k) => n.includes(k)))  return 'percent';
  return 'text';
}

/** Format a raw string as Indonesian thousand-separated number while typing */
function formatCurrency(raw: string): string {
  const digits = raw.replace(/[^\d]/g, '');
  if (!digits) return '';
  return Number(digits).toLocaleString('id-ID');
}

/** Strip thousand separators before submitting */
function parseCurrency(formatted: string): number {
  return Number(formatted.replace(/\./g, '').replace(',', '.')) || 0;
}

// ─── Smart field input ────────────────────────────────────────────────────────

function SmartField({
  name,
  value,
  onChange,
}: {
  name: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const kind = detectFieldKind(name);
  const label = name.replace(/_/g, ' ');
  const inputCls = 'w-full rounded-lg border border-gray-300 bg-white text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500';

  if (kind === 'date') {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
        <input
          type="date"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`${inputCls} px-3 py-2.5`}
        />
      </div>
    );
  }

  if (kind === 'currency') {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
        <div className="relative">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium text-gray-500 dark:text-gray-400">Rp</span>
          <input
            type="text"
            inputMode="numeric"
            value={value}
            onChange={(e) => onChange(formatCurrency(e.target.value))}
            placeholder="0"
            className={`${inputCls} py-2.5 pl-9 pr-3`}
          />
        </div>
        <p className="mt-0.5 text-xs text-gray-400">Format otomatis ribuan (contoh: 1.500.000)</p>
      </div>
    );
  }

  if (kind === 'percent') {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
        <div className="relative">
          <input
            type="number"
            min={0}
            max={100}
            step={0.1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="0 – 100"
            className={`${inputCls} py-2.5 pl-3 pr-9`}
          />
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-500 dark:text-gray-400">%</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Masukkan ${label}...`}
        className={`${inputCls} px-3 py-2.5`}
      />
    </div>
  );
}

// ─── Smart Input Form ─────────────────────────────────────────────────────────

function SmartInputForm({
  model,
  onSubmit,
  loading,
}: {
  model: MLModel;
  onSubmit: (rows: Record<string, any>[]) => void;
  loading: boolean;
}) {
  const features = model.feature_names ?? [];
  const [inputMode, setInputMode] = useState<'fields' | 'csv'>('fields');
  const [fieldValues, setFieldValues] = useState<Record<string, string>>(
    () => Object.fromEntries(features.map((f) => [f, '']))
  );
  const [csvError, setCsvError] = useState('');

  // Reset fields when model changes
  useMemo(() => {
    setFieldValues(Object.fromEntries(features.map((f) => [f, ''])));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model.id]);

  const handleFields = () => {
    const row: Record<string, any> = {};
    features.forEach((f) => {
      const raw = fieldValues[f];
      const kind = detectFieldKind(f);
      if (kind === 'currency') {
        row[f] = parseCurrency(raw);
      } else if (kind === 'date') {
        row[f] = raw; // ISO date string
      } else if (raw !== '' && !isNaN(Number(raw.replace(/\./g, '').replace(',', '.')))) {
        row[f] = Number(raw.replace(/\./g, '').replace(',', '.'));
      } else {
        row[f] = raw;
      }
    });
    onSubmit([row]);
  };

  const handleCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvError('');
    try {
      const text = await file.text();
      const lines = text.trim().split('\n');
      const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
      const rows = lines.slice(1).map((line) => {
        const vals = line.split(',').map((v) => v.trim().replace(/^"|"$/g, ''));
        const row: Record<string, any> = {};
        headers.forEach((h, i) => {
          const val = vals[i] ?? '';
          row[h] = !isNaN(Number(val)) && val !== '' ? Number(val) : val;
        });
        return row;
      });
      onSubmit(rows);
    } catch {
      setCsvError('Format CSV tidak valid. Pastikan baris pertama berisi nama kolom.');
    }
  };

  const allFilled = features.every((f) => fieldValues[f] !== '');

  return (
    <div>
      {/* Mode toggle */}
      {features.length > 0 && (
        <div className="mb-4 flex gap-2">
          <button
            onClick={() => setInputMode('fields')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              inputMode === 'fields'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
            }`}
          >
            Isi Form
          </button>
          <button
            onClick={() => setInputMode('csv')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              inputMode === 'csv'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
            }`}
          >
            <FileSpreadsheet className="h-3.5 w-3.5" /> Upload CSV
          </button>
        </div>
      )}

      {inputMode === 'fields' ? (
        features.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Pilih model untuk melihat kolom input yang dibutuhkan.
          </p>
        ) : (
          <>
            <div className="space-y-3">
              {features.map((f) => (
                <SmartField
                  key={f}
                  name={f}
                  value={fieldValues[f]}
                  onChange={(v) => setFieldValues((p) => ({ ...p, [f]: v }))}
                />
              ))}
            </div>

            <button
              onClick={handleFields}
              disabled={!allFilled || loading}
              className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
              {loading ? 'Memproses...' : 'Prediksi'}
            </button>
          </>
        )
      ) : (
        <div>
          <label
            htmlFor="csv-upload"
            className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 p-8 hover:border-primary-400 dark:border-gray-600"
          >
            <Upload className="mb-2 h-8 w-8 text-gray-400" />
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Upload file CSV</p>
            <p className="mt-1 text-xs text-gray-500">Kolom harus sesuai: {features.join(', ')}</p>
            <input id="csv-upload" type="file" accept=".csv" className="hidden" onChange={handleCsv} />
          </label>
          {csvError && (
            <p className="mt-2 flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
              <AlertCircle className="h-3.5 w-3.5" /> {csvError}
            </p>
          )}
        </div>
      )}
    </div>
  );
}


// ─── Main Page ────────────────────────────────────────────────────────────────

export default function PredictionsPage() {
  const { models: modelsList, isLoading } = useModels();
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [predicting, setPredicting] = useState(false);
  const [results, setResults] = useState<PredictionResult | null>(null);
  const [feedbackState, setFeedbackState] = useState<Record<string, 'idle' | 'saving' | 'submitted' | 'error'>>({});
  const [feedbackComment, setFeedbackComment] = useState<Record<string, string>>({});

  const deployableModels = modelsList.filter(
    (m) => m.status === 'deployed' || m.status === 'trained'
  );

  const model = deployableModels.find((m) => m.id === selectedModel);

  const handlePredict = async (rows: Record<string, any>[]) => {
    if (!selectedModel) return;
    setPredicting(true);
    setResults(null);
    try {
      const res = await models.predict(selectedModel, { data: rows });
      setResults(res.data);
    } catch (err: unknown) {
      setResults({ error: formatApiError(err, 'Prediksi gagal') });
    } finally {
      setPredicting(false);
    }
  };

  const sendFeedback = async (predictionId: string, correct: boolean) => {
    if (!selectedModel) return;
    setFeedbackState((prev) => ({ ...prev, [predictionId]: 'saving' }));
    try {
      await models.feedbackPrediction(selectedModel, predictionId, {
        correct,
        comment: feedbackComment[predictionId],
      });
      setFeedbackState((prev) => ({ ...prev, [predictionId]: 'submitted' }));
    } catch {
      setFeedbackState((prev) => ({ ...prev, [predictionId]: 'error' }));
    }
  };

  return (
    <div className="space-y-6">
      {/* Page title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Prediksi</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Jalankan prediksi dari model yang sudah dilatih
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* ── Left: input panel ── */}
        <div className="space-y-5 rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Data Input</h2>

          {/* Model selector */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              Pilih Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => {
                setSelectedModel(e.target.value);
                setResults(null);
              }}
              className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="">
                {isLoading ? 'Memuat model...' : deployableModels.length === 0 ? 'Belum ada model siap pakai' : 'Pilih model...'}
              </option>
              {deployableModels.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.algorithm} v{m.version})
                </option>
              ))}
            </select>
          </div>

          {/* Model info badge */}
          {model && (
            <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
              <div className="flex flex-wrap gap-x-4 gap-y-1">
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Kolom target: <span className="font-medium text-gray-700 dark:text-gray-200">{model.target_column ?? '–'}</span>
                </span>
                {model.metrics?.accuracy !== undefined && (
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Akurasi: <span className="font-medium text-green-600 dark:text-green-400">{(model.metrics.accuracy * 100).toFixed(1)}%</span>
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Smart form */}
          {model ? (
            <SmartInputForm model={model} onSubmit={handlePredict} loading={predicting} />
          ) : (
            <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-200 py-10 dark:border-gray-700">
              <Zap className="mb-2 h-10 w-10 text-gray-300 dark:text-gray-600" />
              <p className="text-sm text-gray-400 dark:text-gray-500">Pilih model untuk mulai prediksi</p>
            </div>
          )}
        </div>

        {/* ── Right: results panel ── */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Hasil Prediksi</h2>
            {results && !results.error && (
              <button
                onClick={() => setResults(null)}
                className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {!results ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Zap className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
              <p className="text-center text-sm text-gray-500 dark:text-gray-400">
                Isi data di sebelah kiri dan tekan Prediksi
              </p>
            </div>
          ) : results.error ? (
            <div className="rounded-lg bg-red-50 p-4 dark:bg-red-900/30">
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                <p className="text-sm text-red-700 dark:text-red-300">{results.error}</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {results.predictions?.map((pred, i) => (
                <PredictionResultCard
                  key={pred.id ?? i}
                  pred={pred}
                  index={i}
                  model={model}
                  feedbackState={feedbackState[pred.id] ?? 'idle'}
                  feedbackComment={feedbackComment[pred.id] ?? ''}
                  onFeedbackChange={(v) => setFeedbackComment((p) => ({ ...p, [pred.id]: v }))}
                  onFeedback={(correct) => pred.id && sendFeedback(pred.id, correct)}
                />
              ))}
              {results.latency_ms !== undefined && (
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  Waktu proses: {results.latency_ms}ms
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
