'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Upload,
  Zap,
  CheckCircle2,
  Loader2,
  AlertCircle,
  ArrowRight,
  Brain,
  Target,
  BarChart3,
  Eye,
  Sparkles,
  FileSpreadsheet,
  Info,
  RotateCcw,
  ChevronRight,
  Database,
} from 'lucide-react';
import { useToast } from '@/components/Toast';
import { models, datasets as datasetsApi, formatApiError } from '@/lib/api';
import { useDatasets } from '@/lib/hooks';
import clsx from 'clsx';

type Step = 'upload' | 'analyzing' | 'review' | 'training' | 'results';

interface AutoState {
  datasetFile: File | null;
  datasetId: string | null;
  datasetName: string;
  analysis: any | null;
  selectedTarget: string;
  trainingResult: any | null;
}

const STEP_LABELS: Record<Step, string> = {
  upload: 'Unggah Data',
  analyzing: 'Menganalisis',
  review: 'Hasil Analisis',
  training: 'Melatih Model',
  results: 'Selesai',
};

export default function AutoModePage() {
  const router = useRouter();
  const { toast } = useToast();
  const { datasets: datasetsList, mutate: mutateDatasets } = useDatasets();
  const [step, setStep] = useState<Step>('upload');
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [trainingStep, setTrainingStep] = useState('');
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const [state, setState] = useState<AutoState>({
    datasetFile: null,
    datasetId: null,
    datasetName: '',
    analysis: null,
    selectedTarget: '',
    trainingResult: null,
  });

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // ── Step 1: Upload ────────────────────────────────────────────────────────
  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const uploadRes = await datasetsApi.upload(formData);
      const dataset = uploadRes.data || uploadRes;

      setState((s) => ({
        ...s,
        datasetFile: file,
        datasetId: dataset.id,
        datasetName: dataset.name || file.name,
      }));

      toast('success', 'Data berhasil diunggah');
      await mutateDatasets();
      startAnalysis(dataset.id);
    } catch (err: any) {
      toast('error', 'Gagal mengunggah: ' + formatApiError(err));
    } finally {
      setUploading(false);
    }
  };

  const handleSelectExisting = async (datasetId: string, datasetName: string) => {
    setState((s) => ({ ...s, datasetId, datasetName }));
    startAnalysis(datasetId);
  };

  // ── Step 2: Analyze ───────────────────────────────────────────────────────
  const startAnalysis = async (datasetId: string) => {
    setStep('analyzing');
    setAnalyzing(true);
    try {
      const res = await models.autoAnalyze({ dataset_id: datasetId });
      const data = res.data || res;
      setState((s) => ({
        ...s,
        analysis: data,
        selectedTarget: data.suggested_target,
      }));
      setStep('review');
    } catch (err: any) {
      toast('error', 'Gagal menganalisis: ' + formatApiError(err));
      setStep('upload');
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Step 3: Train ─────────────────────────────────────────────────────────
  const handleTrain = async () => {
    const { analysis, selectedTarget, datasetId } = state;
    if (!analysis || !datasetId || !selectedTarget) return;

    setStep('training');
    setTraining(true);
    setTrainingProgress(0);
    setTrainingStep('Menyiapkan data...');

    try {
      // Create model
      const modelRes = await models.create({
        name: `Auto-${analysis.dataset_name}`,
        algorithm: analysis.suggested_algorithm,
        target_column: selectedTarget,
        description: `Model otomatis dari "${analysis.dataset_name}"`,
      });
      const model = modelRes.data || modelRes;

      setTrainingProgress(10);
      setTrainingStep('Memulai pelatihan...');

      // Start training
      const trainRes = await models.train(model.id, {
        dataset_id: datasetId,
        algorithm: analysis.suggested_algorithm,
        target_column: selectedTarget,
        async_training: true,
        mode: 'simple',
        problem_type: analysis.problem_type,
      });
      const trainData = trainRes.data || trainRes;
      const taskId = trainData.task_id;

      if (!taskId) {
        throw new Error('Tidak ada task ID dari pelatihan');
      }

      setTrainingProgress(20);
      setTrainingStep('Melatih model...');

      // Poll for completion
      pollRef.current = setInterval(async () => {
        try {
          const statusRes = await models.taskStatus(taskId);
          const status = statusRes.data || statusRes;

          if (status.progress) {
            setTrainingProgress(Math.max(20, Math.min(90, status.progress)));
          }

          if (status.status === 'SUCCESS' || status.status === 'completed') {
            if (pollRef.current) clearInterval(pollRef.current);
            setTrainingProgress(100);
            setTrainingStep('Selesai!');
            setState((s) => ({ ...s, trainingResult: status.result || status }));
            setTimeout(() => setStep('results'), 500);
          } else if (status.status === 'FAILURE' || status.status === 'failed') {
            if (pollRef.current) clearInterval(pollRef.current);
            throw new Error(status.result?.error || 'Pelatihan gagal');
          }
        } catch (pollErr: any) {
          if (pollRef.current) clearInterval(pollRef.current);
          toast('error', 'Error polling: ' + formatApiError(pollErr));
          setStep('review');
          setTraining(false);
        }
      }, 2000);
    } catch (err: any) {
      toast('error', 'Gagal melatih: ' + formatApiError(err));
      setStep('review');
      setTraining(false);
    }
  };

  // ── Helpers ────────────────────────────────────────────────────────────────
  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const getMetricLabel = (key: string): string => {
    const labels: Record<string, string> = {
      accuracy: 'Akurasi',
      f1: 'F1 Score',
      f1_macro: 'F1 Macro',
      f1_weighted: 'F1 Weighted',
      precision: 'Presisi',
      precision_macro: 'Presisi Macro',
      recall: 'Recall',
      recall_macro: 'Recall Macro',
      r2: 'R²',
      rmse: 'RMSE',
      mae: 'MAE',
      mse: 'MSE',
      roc_auc: 'ROC AUC',
    };
    return labels[key] || key;
  };

  const getMetricInterpretation = (key: string, value: number): string => {
    if (key === 'accuracy' || key === 'f1' || key === 'f1_macro' || key === 'f1_weighted') {
      if (value >= 0.9) return 'Luar biasa!';
      if (value >= 0.8) return 'Bagus!';
      if (value >= 0.7) return 'Lumayan';
      return 'Perlu perbaikan';
    }
    if (key === 'r2') {
      if (value >= 0.9) return 'Sangat akurat';
      if (value >= 0.7) return 'Cukup akurat';
      if (value >= 0.5) return 'Sedang';
      return 'Kurang akurat';
    }
    return '';
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 bg-gradient-to-r from-primary-500 to-purple-600 text-white px-4 py-2 rounded-full text-sm font-medium mb-4">
          <Zap className="w-4 h-4" />
          Auto Mode
        </div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Unggah, Lihat, Selesai.
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Sistem akan menganalisis data kamu dan memandu langkah selanjutnya secara otomatis.
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center justify-center gap-2 mb-8">
        {(['upload', 'analyzing', 'review', 'training', 'results'] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center">
            <div
              className={clsx(
                'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all',
                step === s
                  ? 'bg-primary-500 text-white scale-110'
                  : i < (['upload', 'analyzing', 'review', 'training', 'results'].indexOf(step))
                    ? 'bg-green-500 text-white'
                    : 'bg-gray-200 dark:bg-gray-700 text-gray-500'
              )}
            >
              {i < (['upload', 'analyzing', 'review', 'training', 'results'].indexOf(step)) ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                i + 1
              )}
            </div>
            {i < 4 && <div className="w-8 h-0.5 bg-gray-200 dark:bg-gray-700 mx-1" />}
          </div>
        ))}
      </div>
      <div className="text-center text-sm text-gray-500 dark:text-gray-400 mb-8">
        {STEP_LABELS[step]}
      </div>

      {/* ── STEP: Upload ──────────────────────────────────────────────────── */}
      {step === 'upload' && (
        <div className="space-y-6">
          {/* File upload area */}
          <div
            onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              const file = e.dataTransfer.files?.[0];
              if (file) handleFileUpload(file);
            }}
            className={clsx(
              'border-2 border-dashed rounded-xl p-12 text-center transition-all cursor-pointer',
              'hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-900/10',
              uploading
                ? 'border-primary-400 bg-primary-50/50 dark:bg-primary-900/10'
                : 'border-gray-300 dark:border-gray-600'
            )}
          >
            <input
              type="file"
              accept=".csv,.xlsx,.xls,.json,.tsv"
              className="hidden"
              id="auto-upload"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileUpload(file);
              }}
            />
            <label htmlFor="auto-upload" className="cursor-pointer">
              {uploading ? (
                <Loader2 className="w-12 h-12 text-primary-500 mx-auto mb-4 animate-spin" />
              ) : (
                <FileSpreadsheet className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              )}
              <p className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-1">
                {uploading ? 'Mengunggah...' : 'Seret & lepas file di sini'}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                atau klik untuk memilih file (CSV, Excel, JSON)
              </p>
            </label>
          </div>

          {/* Existing datasets */}
          {datasetsList && datasetsList.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
                <span className="text-sm text-gray-500 dark:text-gray-400">atau pilih data yang sudah ada</span>
                <div className="h-px flex-1 bg-gray-200 dark:bg-gray-700" />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {datasetsList.slice(0, 6).map((ds: any) => (
                  <button
                    key={ds.id}
                    onClick={() => handleSelectExisting(ds.id, ds.name)}
                    className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition-all text-left"
                  >
                    <Database className="w-5 h-5 text-gray-400 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{ds.name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {ds.row_count || '?'} baris, {ds.column_count || '?'} kolom
                      </p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── STEP: Analyzing ────────────────────────────────────────────────── */}
      {step === 'analyzing' && (
        <div className="text-center py-16">
          <div className="relative inline-block mb-6">
            <Loader2 className="w-16 h-16 text-primary-500 animate-spin" />
            <Sparkles className="w-6 h-6 text-yellow-500 absolute -top-1 -right-1 animate-pulse" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Menganalisis data kamu...
          </h2>
          <p className="text-gray-500 dark:text-gray-400">
            Sistem sedang memeriksa kolom, tipe data, dan kualitas dataset.
          </p>
          <div className="mt-6 flex items-center justify-center gap-3 text-sm text-gray-400">
            <span className="flex items-center gap-1"><Eye className="w-4 h-4" /> Preview data</span>
            <span>•</span>
            <span className="flex items-center gap-1"><Target className="w-4 h-4" /> Deteksi target</span>
            <span>•</span>
            <span className="flex items-center gap-1"><Brain className="w-4 h-4" /> Pilih algoritma</span>
          </div>
        </div>
      )}

      {/* ── STEP: Review ──────────────────────────────────────────────────── */}
      {step === 'review' && state.analysis && (
        <div className="space-y-6">
          {/* Data summary card */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Eye className="w-5 h-5 text-primary-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Ringkasan Data</h2>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <p className="text-2xl font-bold text-primary-600">{state.analysis.rows}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Baris</p>
              </div>
              <div className="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <p className="text-2xl font-bold text-primary-600">{state.analysis.columns}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Kolom</p>
              </div>
              <div className="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <p className="text-2xl font-bold text-primary-600">{state.analysis.quality_score}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Kualitas</p>
              </div>
              <div className="text-center p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <p className="text-2xl font-bold text-primary-600">{state.analysis.dataset_size === 'small' ? 'Kecil' : state.analysis.dataset_size === 'medium' ? 'Sedang' : 'Besar'}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400">Ukuran</p>
              </div>
            </div>
          </div>

          {/* Auto-detection results */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-yellow-500" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Hasil Deteksi Otomatis</h2>
            </div>

            <div className="space-y-4">
              {/* Target column */}
              <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                <Target className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-blue-800 dark:text-blue-300">Kolom Target</p>
                  <p className="text-lg font-bold text-blue-900 dark:text-blue-200">{state.analysis.suggested_target}</p>
                  <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">{state.analysis.target_reason}</p>
                </div>
              </div>

              {/* Problem type */}
              <div className="flex items-start gap-3 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                <BarChart3 className="w-5 h-5 text-purple-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-purple-800 dark:text-purple-300">Tipe Prediksi</p>
                  <p className="text-lg font-bold text-purple-900 dark:text-purple-200">
                    {state.analysis.problem_type === 'classification' ? 'Klasifikasi' : 'Regresi'}
                  </p>
                  <p className="text-xs text-purple-600 dark:text-purple-400 mt-1">{state.analysis.problem_reason}</p>
                </div>
              </div>

              {/* Algorithm */}
              <div className="flex items-start gap-3 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                <Brain className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-green-800 dark:text-green-300">Algoritma Terpilih</p>
                  <p className="text-lg font-bold text-green-900 dark:text-green-200">
                    {state.analysis.suggested_algorithm.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400 mt-1">{state.analysis.algorithm_reason}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Warnings */}
          {state.analysis.warnings && state.analysis.warnings.length > 0 && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-xl border border-yellow-200 dark:border-yellow-800 p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300">Perhatian</p>
              </div>
              <ul className="space-y-1">
                {state.analysis.warnings.map((w: string, i: number) => (
                  <li key={i} className="text-sm text-yellow-700 dark:text-yellow-400 flex items-start gap-2">
                    <span>•</span> {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Column overview */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center gap-2 mb-4">
              <Info className="w-5 h-5 text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Detail Kolom</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400">Kolom</th>
                    <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400">Tipe</th>
                    <th className="text-right py-2 px-3 font-medium text-gray-500 dark:text-gray-400">Unique</th>
                    <th className="text-right py-2 px-3 font-medium text-gray-500 dark:text-gray-400">Missing</th>
                    <th className="text-left py-2 px-3 font-medium text-gray-500 dark:text-gray-400">Peran</th>
                  </tr>
                </thead>
                <tbody>
                  {state.analysis.column_summaries.map((col: any) => (
                    <tr key={col.name} className="border-b border-gray-100 dark:border-gray-700/50">
                      <td className="py-2 px-3 font-medium text-gray-900 dark:text-white">{col.name}</td>
                      <td className="py-2 px-3 text-gray-500 dark:text-gray-400">{col.dtype}</td>
                      <td className="py-2 px-3 text-right text-gray-500 dark:text-gray-400">{col.unique_count}</td>
                      <td className="py-2 px-3 text-right text-gray-500 dark:text-gray-400">{col.null_pct}%</td>
                      <td className="py-2 px-3">
                        <span className={clsx(
                          'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                          col.role === 'target'
                            ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                            : col.role === 'id'
                              ? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                              : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                        )}>
                          {col.role === 'target' ? 'Target' : col.role === 'id' ? 'ID' : 'Fitur'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center justify-between">
            <button
              onClick={() => { setStep('upload'); setState((s) => ({ ...s, analysis: null })); }}
              className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              Ganti Data
            </button>
            <button
              onClick={handleTrain}
              disabled={!state.analysis.ready_to_train}
              className={clsx(
                'flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all',
                state.analysis.ready_to_train
                  ? 'bg-gradient-to-r from-primary-500 to-purple-600 text-white hover:from-primary-600 hover:to-purple-700 shadow-lg shadow-primary-500/25'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
              )}
            >
              <Zap className="w-5 h-5" />
              Latih Model Sekarang
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* ── STEP: Training ─────────────────────────────────────────────────── */}
      {step === 'training' && (
        <div className="text-center py-16">
          <div className="relative inline-block mb-6">
            <Loader2 className="w-16 h-16 text-primary-500 animate-spin" />
            <Zap className="w-6 h-6 text-yellow-500 absolute -top-1 -right-1 animate-pulse" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Melatih model kamu...
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-6">{trainingStep}</p>

          {/* Progress bar */}
          <div className="max-w-md mx-auto">
            <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400 mb-2">
              <span>Progress</span>
              <span>{trainingProgress}%</span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
              <div
                className="bg-gradient-to-r from-primary-500 to-purple-600 h-3 rounded-full transition-all duration-500"
                style={{ width: `${trainingProgress}%` }}
              />
            </div>
          </div>

          <div className="mt-8 flex items-center justify-center gap-6 text-sm text-gray-400">
            <span className="flex items-center gap-1"><Eye className="w-4 h-4" /> Preprocessing</span>
            <span>•</span>
            <span className="flex items-center gap-1"><Brain className="w-4 h-4" /> Training</span>
            <span>•</span>
            <span className="flex items-center gap-1"><CheckCircle2 className="w-4 h-4" /> Evaluasi</span>
          </div>
        </div>
      )}

      {/* ── STEP: Results ──────────────────────────────────────────────────── */}
      {step === 'results' && state.trainingResult && (
        <div className="space-y-6">
          {/* Success header */}
          <div className="text-center py-6">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full mb-4">
              <CheckCircle2 className="w-8 h-8 text-green-600 dark:text-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">Model Berhasil Dilatih!</h2>
            <p className="text-gray-500 dark:text-gray-400">
              {state.analysis?.suggested_algorithm?.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())} siap digunakan
            </p>
          </div>

          {/* Metrics */}
          {state.trainingResult.metrics && (
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-5 h-5 text-primary-500" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Metrik Performa</h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {Object.entries(state.trainingResult.metrics)
                  .filter(([k]) => !['confusion_matrix', 'classification_report'].includes(k))
                  .map(([key, value]) => {
                    const numVal = typeof value === 'number' ? value : null;
                    const displayVal = numVal !== null
                      ? (numVal < 1 && numVal > -1 ? `${(numVal * 100).toFixed(1)}%` : numVal.toFixed(3))
                      : String(value);
                    const interp = numVal !== null ? getMetricInterpretation(key, numVal) : '';
                    return (
                      <div key={key} className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                        <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{getMetricLabel(key)}</p>
                        <p className="text-xl font-bold text-gray-900 dark:text-white">{displayVal}</p>
                        {interp && (
                          <p className={clsx(
                            'text-xs mt-1 font-medium',
                            numVal! >= 0.8 ? 'text-green-600 dark:text-green-400' :
                            numVal! >= 0.6 ? 'text-yellow-600 dark:text-yellow-400' :
                            'text-red-600 dark:text-red-400'
                          )}>
                            {interp}
                          </p>
                        )}
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Human summary */}
          {state.trainingResult.human_summary && (
            <div className="bg-gradient-to-br from-primary-50 to-purple-50 dark:from-primary-900/20 dark:to-purple-900/20 rounded-xl border border-primary-200 dark:border-primary-800 p-6">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-5 h-5 text-primary-500" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Ringkasan untuk Kamu</h3>
              </div>
              <div className="text-gray-700 dark:text-gray-300 whitespace-pre-line leading-relaxed">
                {typeof state.trainingResult.human_summary === 'string'
                  ? state.trainingResult.human_summary
                  : JSON.stringify(state.trainingResult.human_summary, null, 2)}
              </div>
            </div>
          )}

          {/* Next steps */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Langkah Selanjutnya</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={() => router.push('/models')}
                className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition-all text-left"
              >
                <Brain className="w-5 h-5 text-primary-500" />
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">Lihat Model</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Detail & metrics</p>
                </div>
              </button>
              <button
                onClick={() => router.push('/predictions')}
                className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition-all text-left"
              >
                <Zap className="w-5 h-5 text-green-500" />
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">Coba Prediksi</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Test dengan data baru</p>
                </div>
              </button>
              <button
                onClick={() => { setStep('upload'); setState({ datasetFile: null, datasetId: null, datasetName: '', analysis: null, selectedTarget: '', trainingResult: null }); }}
                className="flex items-center gap-2 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-400 hover:bg-primary-50/50 dark:hover:bg-primary-900/10 transition-all text-left"
              >
                <RotateCcw className="w-5 h-5 text-purple-500" />
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">Latih Lagi</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">Dataset baru</p>
                </div>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
