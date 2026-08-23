'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Upload,
  Target,
  Cpu,
  CheckCircle2,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Info,
  Zap,
  BarChart3,
  Eye,
  AlertTriangle,
  Hash,
  Tag,
  RotateCcw,
} from 'lucide-react';
import { useToast } from '@/components/Toast';
import Badge from '@/components/Badge';
import AdvancedSection from '@/components/AdvancedSection';
import { models, datasets as datasetsApi, recommendations, quota, experiments, formatApiError } from '@/lib/api';
import { useDatasets } from '@/lib/hooks';
import { useWizardDraft, loadDraft, clearDraft } from '@/lib/useWizardDraft';
import { useFunnelTracker } from '@/lib/useFunnelTracker';
import Link from 'next/link';

type WizardStep = 'upload' | 'target' | 'purpose' | 'preview' | 'mode' | 'review' | 'training' | 'results';

interface WizardState {
  datasetFile: File | null;
  datasetId: string | null;
  datasetName: string;
  targetColumn: string;
  predictionType: 'number' | 'category' | null;
  mode: 'simple' | 'advanced';
  algorithm: string;
  trainingResult: any | null;
}

const STEPS: { key: WizardStep; label: string; icon: any }[] = [
  { key: 'upload', label: 'Unggah Data', icon: Upload },
  { key: 'target', label: 'Pilih Target', icon: Target },
  { key: 'purpose', label: 'Tujuan Prediksi', icon: BarChart3 },
  { key: 'preview', label: 'Pratinjau', icon: Eye },
  { key: 'mode', label: 'Pilih Mode', icon: Cpu },
  { key: 'review', label: 'Konfirmasi', icon: CheckCircle },
  { key: 'results', label: 'Hasil', icon: CheckCircle2 },
];

const MAX_FILE_SIZE_MB = 100;

import { ALGORITHMS, REGRESSION_ALGORITHMS } from '@/lib/algorithms';
import Tooltip from '@/components/Tooltip';
import { NEED_SCENARIOS } from '@/lib/recommendations';

const ALGORITHM_LABELS: Record<string, string> = Object.fromEntries(
  Object.entries(ALGORITHMS).map(([k, v]) => [k, v.label])
);

const GLOSSARY = {
  accuracy: {
    label: 'akurasi',
    description: 'Seberapa sering model kamu benar. Lebih tinggi berarti prediksi lebih bisa dipercaya.',
  },
  overfitting: {
    label: 'overfitting',
    description: 'Model yang terlalu fokus menghafal data lama, jadi nanti mudah bingung kalau data baru sedikit beda.',
  },
  epoch: {
    label: 'epoch',
    description: 'Satu kali model melihat semua data pelatihan sekali. Semakin banyak epoch, model belajar lebih banyak, tapi bisa juga terlalu banyak.',
  },
  feature: {
    label: 'fitur',
    description: 'Kolom informasi yang digunakan model untuk belajar, misalnya umur, pendapatan, atau skor kredit.',
  },
  target: {
    label: 'target',
    description: 'Apa yang ingin kamu prediksi, misalnya churn, harga, atau kategori produk.',
  },
  dataset: {
    label: 'dataset',
    description: 'Kumpulan data yang dipakai untuk melatih model. Anggap ini sebagai buku latihan atau contoh soal.',
  },
  trainingDataset: {
    label: 'dataset training',
    description: 'Data yang digunakan model untuk belajar. Ini seperti soal latihan untuk murid.',
  },
  testingDataset: {
    label: 'dataset testing',
    description: 'Data yang digunakan untuk menguji model setelah dilatih, supaya kita tahu model benar-benar ngerti pola.',
  },
};

function GlossaryTerm({ term }: { term: keyof typeof GLOSSARY }) {
  const item = GLOSSARY[term];
  return (
    <Tooltip content={item.description} position="top" className="!max-w-sm">
      <span className="inline-flex cursor-help items-center gap-1 text-primary-600 hover:text-primary-800">
        {item.label}
        <span className="rounded-full bg-primary-100 px-1 text-[10px] font-semibold text-primary-700">?</span>
      </span>
    </Tooltip>
  );
}

export default function TrainingWizard() {
  const router = useRouter();
  const { toast } = useToast();
  const { datasets: datasetsList, mutate: mutateDatasets } = useDatasets();
  const [currentStep, setCurrentStep] = useState<WizardStep>('upload');
  const [state, setState] = useState<WizardState>({
    datasetFile: null,
    datasetId: null,
    datasetName: '',
    targetColumn: '',
    predictionType: null,
    mode: 'simple',
    algorithm: 'random_forest',
    trainingResult: null,
  });

  // ── Draft restore ────────────────────────────────────────────────────────
  const [draftToRestore, setDraftToRestore] = useState(() => loadDraft());
  const [showDraftBanner, setShowDraftBanner] = useState(() => !!loadDraft());

  // ── Funnel tracker ───────────────────────────────────────────────────────
  const { transition, abandon } = useFunnelTracker('training-wizard');

  // Wrap setCurrentStep so every transition is tracked automatically
  const goToStep = useCallback((next: WizardStep) => {
    setCurrentStep((prev) => {
      if (prev !== next) transition(prev, next);
      return next;
    });
  }, [transition]);

  // Track abandon when user navigates away mid-funnel
  useEffect(() => {
    const handleUnload = () => {
      if (!['training', 'results'].includes(currentStep)) {
        abandon(currentStep, { datasetName: state.datasetName });
      }
    };
    window.addEventListener('beforeunload', handleUnload);
    return () => window.removeEventListener('beforeunload', handleUnload);
  }, [currentStep, state.datasetName, abandon]);

  // ── Auto-save draft ──────────────────────────────────────────────────────
  const activeForDraft = !['training', 'results'].includes(currentStep);
  useWizardDraft(
    currentStep,
    {
      datasetId: state.datasetId,
      datasetName: state.datasetName,
      targetColumn: state.targetColumn,
      predictionType: state.predictionType,
      mode: state.mode,
      algorithm: state.algorithm,
    },
    activeForDraft,
  );
  const [uploading, setUploading] = useState(false);
  const [training, setTraining] = useState(false);
  const [previewData, setPreviewData] = useState<any[] | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [trainingStep, setTrainingStep] = useState('');
  const [recommendation, setRecommendation] = useState<any>(null);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [quotaInfo, setQuotaInfo] = useState<any | null>(null);
  const [quotaLoading, setQuotaLoading] = useState(false);
  const [previousExperiments, setPreviousExperiments] = useState<any[] | null>(null);
  const [previousLoading, setPreviousLoading] = useState(false);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const lastSavedTargetRef = useRef<{ datasetId: string | null; targetColumn: string | null }>({
    datasetId: null,
    targetColumn: null,
  });
  const [savingTarget, setSavingTarget] = useState(false);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const fetchQuotaInfo = useCallback(async () => {
    setQuotaLoading(true);
    try {
      const res = await quota.get();
      setQuotaInfo(res.data);
    } catch {
      setQuotaInfo(null);
    } finally {
      setQuotaLoading(false);
    }
  }, []);

  const fetchPreviousExperiments = useCallback(async () => {
    if (!state.datasetId) return;
    setPreviousLoading(true);
    try {
      const res = await experiments.list({ status: 'completed' });
      const items = res.data.items || [];
      const filtered = items
        .filter((item: any) => item.dataset_id === state.datasetId)
        .filter((item: any) => item.id !== state.trainingResult?.id)
        .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 3);
      setPreviousExperiments(filtered);
    } catch {
      setPreviousExperiments(null);
    } finally {
      setPreviousLoading(false);
    }
  }, [state.datasetId, state.trainingResult]);

  useEffect(() => {
    if (currentStep === 'review') {
      fetchQuotaInfo();
    }
  }, [currentStep, fetchQuotaInfo]);

  useEffect(() => {
    if (currentStep === 'results') {
      fetchPreviousExperiments();
    }
  }, [currentStep, fetchPreviousExperiments]);

  const persistTargetToBackend = useCallback(async () => {
    if (!state.datasetId || !state.targetColumn) return true;
    const last = lastSavedTargetRef.current;
    if (last.datasetId === state.datasetId && last.targetColumn === state.targetColumn) {
      return true;
    }
    setSavingTarget(true);
    try {
      await datasetsApi.update(state.datasetId, { target_column: state.targetColumn });
      lastSavedTargetRef.current = {
        datasetId: state.datasetId,
        targetColumn: state.targetColumn,
      };
      mutateDatasets();
      return true;
    } catch (err: unknown) {
      toast('error', formatApiError(err, 'Gagal menyimpan kolom target'));
      return false;
    } finally {
      setSavingTarget(false);
    }
  }, [state.datasetId, state.targetColumn, mutateDatasets, toast]);

  const handleFileSelect = useCallback(async (file: File | null) => {
    if (!file) return;

    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      toast('error', `Ukuran file maksimal ${MAX_FILE_SIZE_MB}MB`);
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', file.name.replace(/\.[^/.]+$/, ''));
      formData.append('description', 'Diunggah melalui Training Wizard');

      const result = await datasetsApi.upload(formData);
      mutateDatasets();

      const previewResult = await datasetsApi.preview(result.data.id);

      setState((prev) => ({
        ...prev,
        datasetFile: file,
        datasetId: result.data.id,
        datasetName: result.data.name,
      }));

      const preview = previewResult.data as any;
      const cols = preview?.columns || result.data.column_names || [];
      setColumns(cols);
      setPreviewData(preview?.head || preview?.data || null);

      toast('success', 'Dataset berhasil diunggah');
      goToStep('target');
    } catch (err: unknown) {
      toast('error', formatApiError(err, 'Gagal mengunggah file'));
    } finally {
      setUploading(false);
    }
  }, [mutateDatasets, toast]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileSelect(file);
  }, [handleFileSelect]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  }, [handleFileSelect]);

  const pollTaskStatus = useCallback((taskId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const resp = await models.taskStatus(taskId);
        const status = resp.data as any;
        const progress = status.progress || 0;
        const step = String(status.status || '');

        setTrainingProgress(progress);
        setTrainingStep(step);

        if (step === 'completed' || status.result) {
          if (pollRef.current) clearInterval(pollRef.current);
          setState((prev) => ({ ...prev, trainingResult: status }));
          goToStep('results');
          setTraining(false);
          toast('success', 'Training berhasil diselesaikan!');
        } else if (step === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current);
          toast('error', status.error || 'Training gagal');
          goToStep('review');
          setTraining(false);
        }
      } catch {
        // poll error, continue
      }
    }, 2000);
  }, [toast]);

  const handleTrain = async () => {
    if (!state.datasetId || !state.targetColumn) {
      toast('error', 'Pilih dataset dan kolom target terlebih dahulu');
      return;
    }

    setTraining(true);
    setTrainingProgress(0);
    setTrainingStep('Mempersiapkan...');
    goToStep('training');

    try {
      const modelResp = await models.create({
        name: `Model Wizard - ${state.datasetName}`,
        algorithm: state.mode === 'simple' ? 'random_forest' : state.algorithm,
        target_column: state.targetColumn,
        description: `Dibuat melalui Training Wizard (mode ${state.mode})`,
      });

      const modelResult = modelResp.data as any;

      const trainResp = await models.train(modelResult.id, {
        dataset_id: state.datasetId,
        algorithm: state.mode === 'simple' ? 'random_forest' : state.algorithm,
        target_column: state.targetColumn,
        async_training: true,
      });

      const trainResult = trainResp.data as any;

      if (trainResult.task_id) {
        pollTaskStatus(trainResult.task_id);
      } else {
        setState((prev) => ({ ...prev, trainingResult: trainResult }));
        clearDraft(); // training done — draft no longer needed
        goToStep('results');
        setTraining(false);
        toast('success', 'Training berhasil diselesaikan!');
      }
    } catch (err: unknown) {
      toast('error', formatApiError(err, 'Training gagal'));
      goToStep('review');
      setTraining(false);
    }
  };

  const getStepStatus = (stepIndex: number) => {
    const currentIndex = STEPS.findIndex((s) => s.key === currentStep);
    if (stepIndex < currentIndex) return 'completed';
    if (stepIndex === currentIndex) return 'active';
    return 'pending';
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 'upload':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">Unggah Dataset Anda</h2>
              <p className="mt-2 text-gray-500">
                Seret dan lepas file CSV, Excel, atau JSON, atau klik untuk memilih
              </p>
            </div>

            <div
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 py-16 transition-colors hover:border-primary-400 hover:bg-primary-50"
            >
              <Upload className="mb-4 h-12 w-12 text-gray-400" />
              <p className="mb-2 text-sm font-medium text-gray-700">
                {uploading ? 'Mengunggah...' : 'Letakkan file Anda di sini'}
              </p>
              <p className="mb-4 text-xs text-gray-500">CSV, TSV, JSON, XLS, XLSX, ODS (maks {MAX_FILE_SIZE_MB}MB)</p>
              <label className="cursor-pointer rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
                <input
                  type="file"
                  accept=".csv,.tsv,.json,.xls,.xlsx,.ods"
                  onChange={handleFileInput}
                  className="hidden"
                  disabled={uploading}
                />
                {uploading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Mengunggah...
                  </span>
                ) : (
                  'Pilih File'
                )}
              </label>
            </div>

            {datasetsList.length > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-4">
                <p className="mb-3 text-sm font-medium text-gray-700">Atau pilih dataset yang sudah ada:</p>
                <select
                  onChange={async (e) => {
                    const ds = datasetsList.find((d) => d.id === e.target.value);
                    if (!ds) return;
                    setState((prev) => ({
                      ...prev,
                      datasetId: ds.id,
                      datasetName: ds.name,
                      targetColumn: (ds as any).target_column || prev.targetColumn,
                    }));
                    lastSavedTargetRef.current = { datasetId: null, targetColumn: null };
                    try {
                      const previewRes = await datasetsApi.preview(ds.id);
                      const preview = previewRes.data as any;
                      const cols = preview?.columns || (ds as any).column_names || [];
                      setColumns(cols);
                      setPreviewData(preview?.head || preview?.data || null);
                    } catch {
                      const cols = (ds as any).column_names || [];
                      setColumns(cols);
                    }
                    goToStep('target');
                  }}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                >
                  <option value="">Pilih dataset...</option>
                  {datasetsList.map((ds) => (
                    <option key={ds.id} value={ds.id}>{ds.name}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        );

      case 'target':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">Pilih Kolom Target</h2>
              <p className="mt-2 text-gray-500">
                Kolom mana yang ingin Anda prediksi? <GlossaryTerm term="target" />
              </p>
              <p className="mt-2 text-sm text-gray-500">
                Kami butuh target supaya model tahu apa yang harus ditebak — seperti memberi tugas "tebak harga" atau "tebak churn".
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Kolom Target
                </label>
                <select
                  value={state.targetColumn}
                  onChange={(e) => {
                    setState((prev) => ({ ...prev, targetColumn: e.target.value }));
                    setRecommendation(null);
                  }}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                >
                  <option value="">Pilih kolom yang ingin diprediksi...</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div className="rounded-lg bg-blue-50 p-4">
                <div className="flex gap-3">
                  <Info className="h-5 w-5 text-blue-500 flex-shrink-0" />
                  <div className="text-sm text-blue-700">
                    <p className="font-medium">Tips memilih target:</p>
                    <ul className="mt-1 list-disc list-inside space-y-1">
                      <li>Pilih kolom yang ingin Anda prediksi</li>
                      <li>Klasifikasi: label kategori (contoh: &quot;spam&quot;, &quot;ya/tidak&quot;)</li>
                      <li>Regresi: nilai angka (contoh: harga, suhu)</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => goToStep('upload')}
                className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Kembali
              </button>
              <button
                onClick={async () => {
                  if (!state.targetColumn) return;
                  const ok = await persistTargetToBackend();
                  if (ok) goToStep('purpose');
                }}
                disabled={!state.targetColumn || savingTarget}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {savingTarget ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Menyimpan...
                  </>
                ) : (
                  <>
                    Selanjutnya
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        );

      case 'purpose':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">Apa yang Ingin Anda Prediksi?</h2>
              <p className="mt-2 text-gray-500">
                Pilih jenis prediksi yang sesuai dengan kebutuhan Anda.
              </p>
              <p className="mt-3 text-sm text-gray-500">
                Di sini kita memutuskan apakah model harus menebak nilai angka atau memilih kategori yang tepat.
                Ini mirip memilih apakah Anda ingin memperkirakan suhu besok atau menentukan apakah email itu spam atau bukan.
              </p>
            </div>

            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
              <p className="text-sm font-medium text-blue-800">Analogi cepat</p>
              <p className="mt-2 text-sm text-blue-700">
                Prediksi angka seperti memperkirakan jumlah pelanggan, sedangkan prediksi kategori seperti memilih warna atau jenis barang.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <button
                onClick={() => setState((prev) => ({ ...prev, predictionType: 'number', algorithm: 'random_forest' }))}
                className={`rounded-xl border-2 p-6 text-left transition-all ${
                  state.predictionType === 'number'
                    ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500/20'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="mb-3 flex items-center gap-3">
                  <div className={`rounded-lg p-2 ${state.predictionType === 'number' ? 'bg-primary-100' : 'bg-gray-100'}`}>
                    <Hash className={`h-6 w-6 ${state.predictionType === 'number' ? 'text-primary-600' : 'text-gray-500'}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Mau Prediksi Angka</h3>
                    <p className="text-sm text-gray-500">Regresi</p>
                  </div>
                </div>
                <p className="text-sm text-gray-600">Contoh: harga rumah, suhu, jumlah penjualan, total biaya</p>
              </button>

              <button
                onClick={() => setState((prev) => ({ ...prev, predictionType: 'category', algorithm: 'random_forest' }))}
                className={`rounded-xl border-2 p-6 text-left transition-all ${
                  state.predictionType === 'category'
                    ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500/20'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="mb-3 flex items-center gap-3">
                  <div className={`rounded-lg p-2 ${state.predictionType === 'category' ? 'bg-primary-100' : 'bg-gray-100'}`}>
                    <Tag className={`h-6 w-6 ${state.predictionType === 'category' ? 'text-primary-600' : 'text-gray-500'}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Mau Prediksi Kategori</h3>
                    <p className="text-sm text-gray-500">Klasifikasi</p>
                  </div>
                </div>
                <p className="text-sm text-gray-600">Contoh: spam/ham, ya/tidak, spesies bunga, jenis barang</p>
              </button>
            </div>

            {/* Concrete scenarios based on selection */}
            {state.predictionType && (
              <div className="rounded-xl border border-primary-200 bg-primary-50/50 p-4">
                <p className="mb-2 text-xs font-semibold text-primary-700 uppercase tracking-wide">Contoh skenario konkret:</p>
                <div className="space-y-2">
                  {NEED_SCENARIOS
                    .filter((s) => state.predictionType === 'number' ? s.problemType === 'regression' : s.problemType === 'classification')
                    .slice(0, 3)
                    .map((scenario) => (
                      <div key={scenario.id} className="flex items-start gap-2 rounded-lg bg-white p-3 border border-primary-100">
                        <CheckCircle2 className="h-4 w-4 text-primary-500 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">{scenario.need}</p>
                          <p className="text-xs text-gray-500">{scenario.exampleUseCase}</p>
                        </div>
                      </div>
                    ))}
                </div>
                <Link href="/panduan-algoritma" className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary-600 hover:text-primary-700">
                  Lihat semua skenario <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            )}

            <div className="flex justify-between">
              <button
                onClick={() => goToStep('target')}
                className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Kembali
              </button>
              <button
                onClick={async () => {
                  if (!state.predictionType) return;
                  await persistTargetToBackend();
                  goToStep('preview');
                  if (state.datasetId && state.targetColumn) {
                    setRecommendationLoading(true);
                    setRecommendation(null);
                    recommendations.analyze(state.datasetId, state.targetColumn)
                      .then((res) => setRecommendation(res.data))
                      .catch(() => setRecommendation(null))
                      .finally(() => setRecommendationLoading(false));
                  }
                }}
                disabled={!state.predictionType || savingTarget}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                Selanjutnya
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        );

      case 'preview':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">Pratinjau Data</h2>
              <p className="mt-2 text-gray-500">
                Periksa data Anda sebelum memulai training
              </p>
            </div>

            <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
              <p className="text-sm font-medium text-blue-800">Mengapa ini penting?</p>
              <p className="mt-2 text-sm text-blue-700">
                Pratinjau membantu Anda memastikan kolom target sudah benar dan melihat apakah ada nilai kosong atau format yang tidak konsisten.
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-4 grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-gray-50 p-3 text-center">
                  <p className="text-xs text-gray-500">Kolom</p>
                  <p className="text-lg font-semibold text-gray-900">{columns.length}</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3 text-center">
                  <p className="text-xs text-gray-500">Target</p>
                  <p className="text-lg font-semibold text-primary-600">{state.targetColumn}</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3 text-center">
                  <p className="text-xs text-gray-500">Dataset</p>
                  <p className="text-sm font-medium text-gray-900 truncate">{state.datasetName}</p>
                </div>
              </div>

              {previewData && previewData.length > 0 && (
                <div className="overflow-x-auto">
                  <p className="mb-2 text-sm font-medium text-gray-700">5 Baris Pertama:</p>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200">
                        {Object.keys(previewData[0]).map((key) => (
                          <th key={key} className={`px-3 py-2 text-left font-medium text-gray-600 ${key === state.targetColumn ? 'bg-primary-50 text-primary-700' : ''}`}>
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.slice(0, 5).map((row, i) => (
                        <tr key={i} className="border-b border-gray-100">
                          {Object.values(row).map((val, j) => (
                            <td key={j} className="px-3 py-2 text-gray-700">
                              {val === null || val === undefined ? (
                                <span className="text-gray-400 italic">kosong</span>
                              ) : (
                                String(val)
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {!previewData && (
                <div className="rounded-lg bg-gray-50 p-4 text-center text-sm text-gray-500">
                  Pratinjau data tidak tersedia
                </div>
              )}
            </div>

            {/* Auto-recommendation */}
            {recommendationLoading && (
              <div className="rounded-xl border border-primary-200 bg-primary-50 p-4">
                <div className="flex items-center gap-2 text-sm text-primary-700">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Menganalisis dataset untuk rekomendasi...
                </div>
              </div>
            )}

            {recommendation && !recommendationLoading && (
              <div className="rounded-xl border-2 border-primary-200 bg-primary-50/50 p-5">
                <div className="mb-3 flex items-center gap-2">
                  <Zap className="h-5 w-5 text-primary-600" />
                  <h3 className="font-semibold text-primary-900">Rekomendasi Otomatis</h3>
                </div>

                <div className="mb-3 rounded-lg bg-white p-3 border border-primary-100">
                  <p className="text-sm text-gray-700">
                    <span className="font-medium">Kolom &quot;{state.targetColumn}&quot;</span> → {recommendation.reason}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {recommendation.rows} baris, {recommendation.columns} kolom, {recommendation.missing_pct}% missing values
                  </p>
                </div>

                <div className="mb-3">
                  <p className="mb-1.5 text-xs font-semibold text-primary-700 uppercase">Algoritma yang disarankan:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {recommendation.suggested_algorithms.slice(0, 4).map((algo: any) => (
                      <span key={algo.key} className="inline-flex items-center gap-1 rounded-full bg-white border border-primary-200 px-2.5 py-1 text-xs font-medium text-primary-700">
                        <CheckCircle2 className="h-3 w-3 text-green-500" />
                        {algo.key.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                </div>

                {recommendation.warnings.length > 0 && (
                  <div className="mb-3 rounded-lg bg-amber-50 border border-amber-200 p-3">
                    {recommendation.warnings.map((w: string, i: number) => (
                      <p key={i} className="text-xs text-amber-700">{w}</p>
                    ))}
                  </div>
                )}

                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setState((prev) => ({
                        ...prev,
                        predictionType: recommendation.suggested_problem_type === 'regression' ? 'number' : 'category',
                        algorithm: 'random_forest',
                      }));
                      toast('success', `Tipe prediksi diatur ke ${recommendation.suggested_problem_type === 'regression' ? 'Regresi' : 'Klasifikasi'}`);
                    }}
                    className="rounded-lg bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700"
                  >
                    Pakai saran ini
                  </button>
                  <Link href="/panduan-algoritma" className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50">
                    Lihat panduan lengkap
                  </Link>
                </div>
              </div>
            )}

            <div className="flex justify-between">
              <button
                onClick={() => goToStep('purpose')}
                className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Kembali
              </button>
              <button
                onClick={() => goToStep(state.mode === 'simple' ? 'review' : 'mode')}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
              >
                Selanjutnya
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        );

      case 'mode':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">Pilih Mode Training</h2>
              <p className="mt-2 text-gray-500">
                Bagaimana Anda ingin melatih model?
              </p>
              <p className="mt-3 text-sm text-gray-500">
                Mode simple akan membuat proses lebih cepat dan otomatis, sedangkan mode advanced memberi Anda kontrol ekstra jika Anda ingin mencoba opsi lain.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <button
                onClick={() => setState((prev) => ({ ...prev, mode: 'simple' }))}
                className={`rounded-xl border-2 p-6 text-left transition-all ${
                  state.mode === 'simple'
                    ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500/20'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="mb-3 flex items-center gap-3">
                  <div className={`rounded-lg p-2 ${state.mode === 'simple' ? 'bg-primary-100' : 'bg-gray-100'}`}>
                    <Zap className={`h-6 w-6 ${state.mode === 'simple' ? 'text-primary-600' : 'text-gray-500'}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Mode Sederhana</h3>
                    <p className="text-sm text-gray-500">Cocok untuk pemula</p>
                  </div>
                </div>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Pemilihan model otomatis
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Pra-pemrosesan data otomatis
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Hasil mudah dipahami
                  </li>
                </ul>
              </button>

              <button
                onClick={() => setState((prev) => ({ ...prev, mode: 'advanced' }))}
                className={`rounded-xl border-2 p-6 text-left transition-all ${
                  state.mode === 'advanced'
                    ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500/20'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="mb-3 flex items-center gap-3">
                  <div className={`rounded-lg p-2 ${state.mode === 'advanced' ? 'bg-primary-100' : 'bg-gray-100'}`}>
                    <Cpu className={`h-6 w-6 ${state.mode === 'advanced' ? 'text-primary-600' : 'text-gray-500'}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">Mode Lanjutan</h3>
                    <p className="text-sm text-gray-500">Kontrol penuh atas training</p>
                  </div>
                </div>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Pilih algoritma apapun
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Hyperparameter kustom
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Metrik detail
                  </li>
                </ul>
              </button>
            </div>

            {state.mode === 'advanced' && (
              <AdvancedSection label="Pilih Algoritma" defaultOpen={true}>
                <p className="mb-3 text-xs text-gray-500">
                  {state.predictionType === 'number'
                    ? 'Menampilkan algoritma Regresi (untuk prediksi angka)'
                    : 'Menampilkan algoritma Klasifikasi (untuk prediksi kategori)'}
                </p>
                <div className="space-y-2">
                  {Object.entries(state.predictionType === 'number' ? REGRESSION_ALGORITHMS : ALGORITHMS).map(([value, info]) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setState((prev) => ({ ...prev, algorithm: value }))}
                      className={`w-full rounded-lg border p-3 text-left transition-all ${
                        state.algorithm === value
                          ? 'border-primary-500 bg-primary-50 ring-2 ring-primary-500/20'
                          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900">{info.label}</span>
                        <Tooltip content={info.description} position="left" className="!whitespace-normal !max-w-xs">
                          <span className="ml-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-gray-100 text-xs text-gray-500 hover:bg-gray-200">
                            ?
                          </span>
                        </Tooltip>
                      </div>
                      <p className="mt-1 text-xs text-gray-500">{info.bestFor}</p>
                    </button>
                  ))}
                </div>
              </AdvancedSection>
            )}

            <div className="flex justify-between">
              <button
                onClick={() => goToStep('preview')}
                className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Kembali
              </button>
              <button
                onClick={() => goToStep('review')}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
              >
                Selanjutnya
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        );

      case 'review':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">Konfirmasi Konfigurasi</h2>
              <p className="mt-2 text-gray-500">
                Pastikan pengaturan training Anda sudah benar
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">Dataset</span>
                <span className="text-sm font-medium text-gray-900">{state.datasetName}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">Kolom Target</span>
                <span className="text-sm font-medium text-gray-900">{state.targetColumn}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">Jenis Prediksi</span>
                <span className="text-sm font-medium text-gray-900">
                  {state.predictionType === 'number' ? 'Prediksi Angka (Regresi)' : 'Prediksi Kategori (Klasifikasi)'}
                </span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">Mode</span>
                <span className="text-sm font-medium text-gray-900">{state.mode === 'simple' ? 'Sederhana' : 'Lanjutan'}</span>
              </div>
              {state.mode === 'advanced' && (
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-gray-500">Algoritma</span>
                  <span className="text-sm font-medium text-gray-900">{ALGORITHM_LABELS[state.algorithm] || state.algorithm}</span>
                </div>
              )}
            </div>

            {state.mode === 'simple' && (
              <div className="rounded-lg bg-green-50 p-4">
                <div className="flex gap-3">
                  <Zap className="h-5 w-5 text-green-500 flex-shrink-0" />
                  <div className="text-sm text-green-700">
                    <p className="font-medium">Mode Sederhana</p>
                    <p className="mt-1">
                      Sistem akan otomatis memilih algoritma terbaik dan memproses data Anda.
                      Anda akan mendapatkan ringkasan hasil yang mudah dipahami.
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="rounded-lg border border-gray-200 bg-blue-50 p-4">
              <div className="flex gap-3">
                <Info className="h-5 w-5 text-blue-500 flex-shrink-0" />
                <div className="text-sm text-blue-700">
                  <p className="font-medium">Tenang, semua berjalan otomatis</p>
                  <p className="mt-1">
                    Proses training dijalankan di server. Jika ada masalah antrian tugas, sistem akan memperbaiki secara otomatis sehingga training tetap bisa berlangsung.
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">Perkiraan Kuota Training</p>
                  <p className="text-sm text-gray-500">Training ini akan menggunakan satu unit kuota training.</p>
                </div>
                {quotaLoading ? (
                  <span className="text-sm text-gray-500">Memuat kuota...</span>
                ) : null}
              </div>
              {quotaInfo ? (
                <div className="space-y-3">
                  <div className="rounded-lg bg-gray-50 p-4">
                    <div className="flex items-center justify-between text-sm text-gray-700">
                      <span>Training hari ini</span>
                      <span>{quotaInfo.training?.daily?.current ?? 0}/{quotaInfo.training?.daily?.limit ?? 0}</span>
                    </div>
                    <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
                      <div
                        className="h-full rounded-full bg-primary-600"
                        style={{ width: `${Math.min(100, ((quotaInfo.training?.daily?.current ?? 0) / Math.max(1, quotaInfo.training?.daily?.limit ?? 1)) * 100)}%` }}
                      />
                    </div>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-4">
                    <div className="flex items-center justify-between text-sm text-gray-700">
                      <span>Training bulan ini</span>
                      <span>{quotaInfo.training?.monthly?.current ?? 0}/{quotaInfo.training?.monthly?.limit ?? 0}</span>
                    </div>
                    <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
                      <div
                        className="h-full rounded-full bg-primary-600"
                        style={{ width: `${Math.min(100, ((quotaInfo.training?.monthly?.current ?? 0) / Math.max(1, quotaInfo.training?.monthly?.limit ?? 1)) * 100)}%` }}
                      />
                    </div>
                  </div>
                  {(quotaInfo.training?.daily && quotaInfo.training.daily.current + 1 > quotaInfo.training.daily.limit) && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                      Peringatan: training ini mungkin akan melewati batas harian Anda.
                    </div>
                  )}
                  {(quotaInfo.training?.monthly && quotaInfo.training.monthly.current + 1 > quotaInfo.training.monthly.limit) && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                      Peringatan: training ini mungkin akan melewati batas bulanan Anda.
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-500">Tidak dapat memuat data kuota saat ini.</p>
              )}
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => goToStep(state.mode === 'simple' ? 'preview' : 'mode')}
                className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Kembali
              </button>
              <button
                onClick={handleTrain}
                disabled={training}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {training ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Memproses...
                  </>
                ) : (
                  <>
                    <Cpu className="h-4 w-4" />
                    Mulai Training
                  </>
                )}
              </button>
            </div>
          </div>
        );

      case 'training':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mb-4 flex justify-center">
                <div className="rounded-full bg-primary-100 p-4">
                  <Loader2 className="h-12 w-12 text-primary-600 animate-spin" />
                </div>
              </div>
              <h2 className="text-xl font-semibold text-gray-900">Training Sedang Berjalan</h2>
              <p className="mt-2 text-gray-500">
                Mohon tunggu sementara kami melatih model Anda...
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Progress</span>
                <span className="text-sm font-semibold text-primary-600">{trainingProgress}%</span>
              </div>
              <div className="mb-4 h-3 w-full overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-full rounded-full bg-primary-500 transition-all duration-500 ease-out"
                  style={{ width: `${trainingProgress}%` }}
                />
              </div>

              <div className="space-y-2">
                {[
                  { key: 'loading', label: 'Memuat dataset' },
                  { key: 'preprocessing', label: 'Pra-pemrosesan data' },
                  { key: 'training', label: 'Training model' },
                  { key: 'evaluating', label: 'Evaluasi hasil' },
                ].map(({ key, label }) => {
                  const stepOrder = ['loading', 'preprocessing', 'training', 'evaluating'];
                  const currentIdx = stepOrder.indexOf(trainingStep);
                  const thisIdx = stepOrder.indexOf(key);
                  const isDone = thisIdx < currentIdx || trainingStep === 'completed';
                  const isActive = thisIdx === currentIdx && trainingStep !== 'completed';

                  return (
                    <div key={key} className="flex items-center gap-3">
                      {isDone ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      ) : isActive ? (
                        <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
                      ) : (
                        <div className="h-2 w-2 rounded-full bg-gray-300" />
                      )}
                      <span className={`text-sm ${isDone ? 'text-gray-700' : isActive ? 'text-gray-700 font-medium' : 'text-gray-400'}`}>
                        {label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        );

      case 'results':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <div className="mb-4 flex justify-center">
                <div className="rounded-full bg-green-100 p-4">
                  <CheckCircle2 className="h-12 w-12 text-green-600" />
                </div>
              </div>
              <h2 className="text-xl font-semibold text-gray-900">Training Selesai!</h2>
              <p className="mt-2 text-gray-500">Model Anda telah berhasil dilatih</p>
            </div>

            {state.trainingResult && (
              <>
                <div className="rounded-xl border border-green-200 bg-green-50 p-5">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-green-700">Sertifikat Penyelesaian</p>
                      <p className="mt-1 text-sm text-green-700">Anda telah menyelesaikan Training Wizard dan siap mencoba model Anda.</p>
                    </div>
                    <Badge variant="success">Pemula</Badge>
                  </div>
                  <button
                    onClick={() => {
                      const svg = `<?xml version="1.0" encoding="UTF-8"?>\n<svg width="900" height="600" viewBox="0 0 900 600" xmlns="http://www.w3.org/2000/svg">\n  <rect width="900" height="600" fill="#f8fafc" rx="24" />\n  <rect x="48" y="48" width="804" height="504" fill="#ffffff" rx="20" stroke="#d1d5db" stroke-width="2" />\n  <text x="450" y="130" text-anchor="middle" font-family="Inter, sans-serif" font-size="34" font-weight="700" fill="#111827">Sertifikat Penyelesaian</text>\n  <text x="450" y="190" text-anchor="middle" font-family="Inter, sans-serif" font-size="18" fill="#4b5563">Telah menyelesaikan Training Wizard di platform ML Pipeline</text>\n  <text x="450" y="260" text-anchor="middle" font-family="Inter, sans-serif" font-size="24" font-weight="600" fill="#111827">${state.datasetName || 'Dataset Anda'}</text>\n  <text x="450" y="300" text-anchor="middle" font-family="Inter, sans-serif" font-size="18" fill="#6b7280">Target: ${state.targetColumn || 'N/A'}</text>\n  <text x="450" y="340" text-anchor="middle" font-family="Inter, sans-serif" font-size="16" fill="#6b7280">Algoritma: ${state.mode === 'simple' ? 'Auto' : state.algorithm}</text>\n  <text x="450" y="420" text-anchor="middle" font-family="Inter, sans-serif" font-size="16" fill="#111827">Tanggal: ${new Date().toLocaleDateString('id-ID')}</text>\n  <text x="450" y="470" text-anchor="middle" font-family="Inter, sans-serif" font-size="14" fill="#6b7280">Selamat! Anda siap mengambil langkah berikutnya dalam pembelajaran machine learning.</text>\n</svg>`;
                      const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
                      const url = URL.createObjectURL(blob);
                      const link = document.createElement('a');
                      link.href = url;
                      link.download = 'sertifikat-training-wizard.svg';
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);
                      URL.revokeObjectURL(url);
                    }}
                    className="mt-4 inline-flex items-center justify-center rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700"
                  >
                    Unduh Sertifikat
                  </button>
                </div>

                {state.trainingResult.results?.readiness && (
                  <div className={`rounded-xl border p-5 ${
                    state.trainingResult.results.readiness.score >= 80 ? 'border-green-200 bg-green-50' :
                    state.trainingResult.results.readiness.score >= 50 ? 'border-yellow-200 bg-yellow-50' :
                    'border-red-200 bg-red-50'
                  }`}>
                    <div className="flex items-start gap-4">
                      <div className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl text-2xl font-bold ${
                        state.trainingResult.results.readiness.grade === 'A' ? 'bg-green-600 text-white' :
                        state.trainingResult.results.readiness.grade === 'B' ? 'bg-blue-600 text-white' :
                        state.trainingResult.results.readiness.grade === 'C' ? 'bg-yellow-500 text-white' :
                        'bg-red-500 text-white'
                      }`}>
                        {state.trainingResult.results.readiness.grade}
                      </div>
                      <div className="flex-1">
                        <p className={`text-lg font-bold ${
                          state.trainingResult.results.readiness.score >= 80 ? 'text-green-700' :
                          state.trainingResult.results.readiness.score >= 50 ? 'text-yellow-700' :
                          'text-red-700'
                        }`}>
                          {state.trainingResult.results.readiness.label}
                        </p>
                        <p className="mt-0.5 text-sm text-gray-600">
                          Skor Kesiapan: {state.trainingResult.results.readiness.score}/100
                        </p>
                        <div className="mt-2 h-3 w-full rounded-full bg-gray-200">
                          <div className={`h-3 rounded-full transition-all ${
                            state.trainingResult.results.readiness.score >= 80 ? 'bg-green-500' :
                            state.trainingResult.results.readiness.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                          }`} style={{ width: `${state.trainingResult.results.readiness.score}%` }} />
                        </div>
                        {state.trainingResult.results.readiness.recommendations?.length > 0 && (
                          <div className="mt-3 space-y-1">
                            {state.trainingResult.results.readiness.recommendations.map((r: string, i: number) => (
                              <p key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400" />
                                {r}
                              </p>
                            ))}
                          </div>
                        )}
                        {state.trainingResult.results.readiness.score >= 65 && (
                          <p className="mt-3 text-sm font-medium text-green-700">
                            Model ini siap dipublikasikan ke Marketplace!
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-6">
                  <div>
                    <h3 className="mb-4 font-semibold text-gray-900">Ringkasan Hasil</h3>
                    {state.trainingResult.results?.human_summary ? (
                      <div className="space-y-4">
                        <div className="rounded-lg bg-gray-50 p-4">
                          <p className="text-sm text-gray-700">
                            {state.trainingResult.results.human_summary.performance?.description}
                          </p>
                        </div>
                        {state.trainingResult.results.human_summary.warnings?.length > 0 && (
                          <div className="rounded-lg bg-yellow-50 p-4">
                            <div className="flex gap-3">
                              <AlertCircle className="h-5 w-5 text-yellow-500 flex-shrink-0" />
                              <div>
                                <p className="text-sm font-medium text-yellow-800">Peringatan:</p>
                                <ul className="mt-1 space-y-1">
                                  {state.trainingResult.results.human_summary.warnings.map((w: string, i: number) => (
                                    <li key={i} className="text-sm text-yellow-700">{w}</li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 gap-4">
                        {state.trainingResult.results?.metrics?.accuracy !== undefined && (
                          <div className="rounded-lg bg-gray-50 p-4">
                            <p className="text-xs text-gray-500">Akurasi</p>
                            <p className="text-lg font-semibold text-gray-900">
                              {(state.trainingResult.results.metrics.accuracy * 100).toFixed(1)}%
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              {state.trainingResult.results.metrics.accuracy >= 0.9
                                ? 'Luar biasa! Model sangat akurat.'
                                : state.trainingResult.results.metrics.accuracy >= 0.8
                                ? 'Bagus! Model cukup andal.'
                                : state.trainingResult.results.metrics.accuracy >= 0.7
                                ? 'Lumayan. Model perlu perbaikan.'
                                : 'Model kurang akurat. Coba tambah data atau algoritma lain.'}
                            </p>
                          </div>
                        )}
                        {state.trainingResult.results?.metrics?.f1_macro !== undefined && (
                          <div className="rounded-lg bg-gray-50 p-4">
                            <p className="text-xs text-gray-500">Skor F1</p>
                            <p className="text-lg font-semibold text-gray-900">
                              {(state.trainingResult.results.metrics.f1_macro * 100).toFixed(1)}%
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              {state.trainingResult.results.metrics.f1_macro >= 0.9
                                ? 'Seimbang — presisi dan recall tinggi.'
                                : state.trainingResult.results.metrics.f1_macro >= 0.8
                                ? 'Cukup seimbang.'
                                : 'Model mungkin miss banyak data positif atau negatif.'}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-sm font-medium text-gray-900">Eksperimen Terakhir</p>
                      <p className="text-sm text-gray-500">Bandingkan dengan hasil training sebelumnya pada dataset ini.</p>
                    </div>
                    {previousLoading ? (
                      <span className="text-sm text-gray-500">Memuat...</span>
                    ) : null}
                  </div>

                  {previousLoading ? (
                    <div className="rounded-lg bg-white p-4 text-sm text-gray-500">Memuat eksperimen sebelumnya...</div>
                  ) : previousExperiments && previousExperiments.length > 0 ? (
                    <div className="space-y-3">
                      {previousExperiments.map((exp) => (
                        <div key={exp.id} className="rounded-lg bg-white p-4 border border-gray-200">
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <p className="font-medium text-gray-900">{exp.name}</p>
                              <p className="text-xs text-gray-500">{exp.parameters?.algorithm || 'unknown'} • {new Date(exp.created_at).toLocaleDateString('id-ID')}</p>
                            </div>
                            <span className="text-xs font-semibold text-gray-700">{exp.status}</span>
                          </div>
                          <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-gray-600">
                            <div className="rounded-lg bg-gray-50 p-3">
                              <p className="text-xs text-gray-500">Akurasi</p>
                              <p className="font-semibold text-gray-900">{exp.metrics?.accuracy !== undefined ? `${(exp.metrics.accuracy * 100).toFixed(1)}%` : '-'}</p>
                            </div>
                            <div className="rounded-lg bg-gray-50 p-3">
                              <p className="text-xs text-gray-500">Skor F1</p>
                              <p className="font-semibold text-gray-900">{exp.metrics?.f1_macro !== undefined ? `${(exp.metrics.f1_macro * 100).toFixed(1)}%` : '-'}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-lg bg-white p-4 text-sm text-gray-500">Belum ada eksperimen sebelumnya pada dataset ini.</div>
                  )}
                </div>
              </>
            )}

            {/* ── Langkah Selanjutnya ── */}
            <div className="rounded-xl border border-primary-200 bg-primary-50 p-5">
              <p className="text-sm font-semibold text-primary-900 mb-3">Langkah selanjutnya</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  onClick={() => router.push(`/try-predict?modelId=${state.trainingResult?.model_id || ''}`)}
                  className="rounded-lg bg-white border border-primary-200 p-3 text-left hover:bg-primary-100 transition-colors"
                >
                  <p className="text-sm font-medium text-primary-900">Coba Prediksi</p>
                  <p className="text-xs text-primary-600">Masukkan data baru dan lihat hasilnya</p>
                </button>
                <button
                  onClick={() => router.push('/training-wizard')}
                  className="rounded-lg bg-white border border-primary-200 p-3 text-left hover:bg-primary-100 transition-colors"
                >
                  <p className="text-sm font-medium text-primary-900">Bandung Model</p>
                  <p className="text-xs text-primary-600">Latih dengan algoritma lain dan bandingkan</p>
                </button>
                <button
                  onClick={() => router.push(`/models`)}
                  className="rounded-lg bg-white border border-primary-200 p-3 text-left hover:bg-primary-100 transition-colors"
                >
                  <p className="text-sm font-medium text-primary-900">Lihat Models</p>
                  <p className="text-xs text-primary-600">Deploy model agar bisa dipakai dari luar</p>
                </button>
              </div>
            </div>

            <div className="flex justify-center gap-4">
              <button
                onClick={() => {
                  goToStep('upload');
                  setState({
                    datasetFile: null,
                    datasetId: null,
                    datasetName: '',
                    targetColumn: '',
                    predictionType: null,
                    mode: 'simple',
                    algorithm: 'random_forest',
                    trainingResult: null,
                  });
                  clearDraft();
                  setShowDraftBanner(false);
                  setPreviewData(null);
                  setColumns([]);
                  setTrainingProgress(0);
                  setTrainingStep('');
                }}
                className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Latih Model Lain
              </button>
              <button
                onClick={() => router.push('/models')}
                className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
              >
                Lihat Semua Model
              </button>
              {state.trainingResult?.results?.readiness?.score >= 65 && (
                <button
                  onClick={() => router.push('/marketplace')}
                  className="rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-purple-700"
                >
                  Publikasikan ke Marketplace
                </button>
              )}
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Training Wizard</h1>
        <p className="text-gray-500">Latih model dalam beberapa langkah sederhana</p>
      </div>

      {/* ── Draft restore banner ─────────────────────────────────────────── */}
      {showDraftBanner && draftToRestore && (
        <div className="flex items-center justify-between gap-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-700 dark:bg-amber-900/20">
          <div className="flex items-center gap-3">
            <RotateCcw className="h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                Ada draft yang belum selesai
              </p>
              <p className="text-xs text-amber-600 dark:text-amber-400">
                {draftToRestore.state.datasetName
                  ? `Dataset: ${draftToRestore.state.datasetName} · Step: ${draftToRestore.currentStep}`
                  : `Terakhir disimpan: ${new Date(draftToRestore.savedAt).toLocaleString('id-ID')}`}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              onClick={() => {
                const d = draftToRestore;
                setState((prev) => ({
                  ...prev,
                  datasetId: d.state.datasetId,
                  datasetName: d.state.datasetName,
                  targetColumn: d.state.targetColumn,
                  predictionType: d.state.predictionType,
                  mode: d.state.mode,
                  algorithm: d.state.algorithm,
                }));
                // Restore columns from the existing datasets list if available
                goToStep(d.currentStep as WizardStep);
                setShowDraftBanner(false);
                toast('success', 'Draft dipulihkan — lanjutkan dari langkah sebelumnya');
              }}
              className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
            >
              Lanjutkan
            </button>
            <button
              onClick={() => {
                clearDraft();
                setShowDraftBanner(false);
                setDraftToRestore(null);
              }}
              className="rounded-lg border border-amber-300 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 dark:border-amber-600 dark:text-amber-400"
            >
              Mulai baru
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          const status = getStepStatus(index);

          return (
            <div key={step.key} className="flex items-center">
              <div className={`flex h-8 w-8 items-center justify-center rounded-full ${  // h-8 w-8 for mobile, h-10 w-10 for desktop
              status === 'completed'
                ? 'bg-success-100 text-success-600'
                : status === 'active'
                ? 'bg-primary-100 text-primary-600'
                : 'bg-gray-100 text-gray-400'
            } sm:h-10 sm:w-10`}>
                {status === 'completed' ? (
                  <CheckCircle2 className="h-5 w-5" />
                ) : (
                  <Icon className="h-5 w-5" />
                )}
              </div>
              <span
                className={`ml-2 hidden text-sm font-medium sm:block ${
                  status === 'active' ? 'text-primary-600' : status === 'completed' ? 'text-success-600' : 'text-gray-400'
                }`}
              >
                {step.label}
              </span>
              {index < STEPS.length - 1 && (
                <div
                  className={`hidden ml-4 h-0.5 w-8 sm:block ${
                    status === 'completed' ? 'bg-success-200' : 'bg-gray-200'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        {renderStepContent()}
      </div>
    </div>
  );
}
