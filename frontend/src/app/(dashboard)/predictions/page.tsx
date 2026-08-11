'use client';

import { useState, useMemo } from 'react';
import {
  Zap, Loader2, CheckCircle, AlertCircle, ChevronDown, ChevronUp,
  X, Sparkles, Layers
} from 'lucide-react';
import WorkspaceTabs from '@/components/WorkspaceTabs';
import { models, formatApiError } from '@/lib/api';
import { useModels } from '@/lib/hooks';
import { PredictionItem, MLModel } from '@/types';
import { SmartInputForm } from '@/components/SmartInput';

const PREDICTIONS_TABS = [
  { label: 'Playground', href: '/try-predict', icon: Sparkles },
  { label: 'History', href: '/predictions', icon: Zap },
  { label: 'Batch', href: '/batch-jobs', icon: Layers },
];

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

  const confidenceLabel = pred.confidence_level === 'high' ? 'Tinggi' :
    pred.confidence_level === 'medium' ? 'Sedang' :
    pred.confidence_level === 'low' ? 'Rendah' : null;

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm font-medium text-gray-500 dark:text-gray-400">
          Prediksi #{index + 1}
        </span>
        <div className="flex items-center gap-2">
          {confidenceLabel && (
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
              pred.confidence_level === 'high' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
              pred.confidence_level === 'medium' ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
              'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            }`}>
              Keyakinan: {confidenceLabel}
            </span>
          )}
          {prob !== undefined && (
            <span className={`text-sm font-medium ${confidenceColor}`}>
              {(prob * 100).toFixed(1)}%
            </span>
          )}
        </div>
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

      {/* Confidence interval for regression */}
      {pred.confidence_interval && (
        <div className="mb-4 rounded-lg bg-blue-50 p-3 dark:bg-blue-900/20">
          <p className="text-xs font-medium text-blue-700 dark:text-blue-300">Rentang Kepercayaan (95%)</p>
          <p className="mt-1 text-sm text-blue-800 dark:text-blue-200">
            {pred.confidence_interval.lower.toLocaleString('id-ID', { maximumFractionDigits: 4 })}
            {' '}&mdash;{' '}
            {pred.confidence_interval.upper.toLocaleString('id-ID', { maximumFractionDigits: 4 })}
          </p>
        </div>
      )}

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

      {/* Feedback section */}
      {feedbackState === 'submitted' ? (
        <div className="flex items-center gap-2 rounded-lg bg-green-50 px-3 py-2 dark:bg-green-900/20">
          <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
          <p className="text-xs font-medium text-green-700 dark:text-green-300">
            Terima kasih! Feedbackmu membantu perbaiki model.
          </p>
        </div>
      ) : (
        <div>
          <button
            onClick={() => setShowFeedback((p) => !p)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            {showFeedback ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            Prediksi ini benar atau salah?
          </button>
          {showFeedback && (
            <div className="mt-2 space-y-2">
              <textarea
                value={feedbackComment}
                onChange={(e) => onFeedbackChange(e.target.value)}
                rows={2}
                placeholder="Ceritakan: apa nilai sebenarnya di dunia nyata? (opsional)"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => onFeedback(true)}
                  disabled={!pred.id || feedbackState === 'saving'}
                  className="flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
                >
                  👍 Benar
                </button>
                <button
                  onClick={() => onFeedback(false)}
                  disabled={!pred.id || feedbackState === 'saving'}
                  className="flex items-center gap-1.5 rounded-lg bg-red-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-600 disabled:opacity-50"
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
      <WorkspaceTabs
        tabs={PREDICTIONS_TABS}
        title="Predictions"
        description="Run predictions from trained models"
      />

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
