'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Upload,
  Target,
  Cpu,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Loader2,
  AlertCircle,
  Info,
  Zap,
  BarChart3,
  Eye,
  AlertTriangle,
} from 'lucide-react';
import { useToast } from '@/components/Toast';
import { models, datasets as datasetsApi } from '@/lib/api';
import { useDatasets } from '@/lib/hooks';

type WizardStep = 'upload' | 'target' | 'preview' | 'mode' | 'review' | 'training' | 'results';

interface WizardState {
  datasetFile: File | null;
  datasetId: string | null;
  datasetName: string;
  targetColumn: string;
  mode: 'simple' | 'advanced';
  algorithm: string;
  trainingResult: any | null;
}

const STEPS: { key: WizardStep; label: string; icon: any }[] = [
  { key: 'upload', label: 'Unggah Data', icon: Upload },
  { key: 'target', label: 'Pilih Target', icon: Target },
  { key: 'preview', label: 'Pratinjau', icon: Eye },
  { key: 'mode', label: 'Pilih Mode', icon: Cpu },
  { key: 'review', label: 'Konfirmasi', icon: BarChart3 },
  { key: 'results', label: 'Hasil', icon: CheckCircle2 },
];

const MAX_FILE_SIZE_MB = 100;

const ALGORITHM_LABELS: Record<string, string> = {
  random_forest: 'Random Forest',
  gradient_boosting: 'Gradient Boosting',
  logistic_regression: 'Logistik Regresi',
  svm: 'Support Vector Machine',
  knn: 'K-Nearest Tetangga',
  decision_tree: 'Pohon Keputusan',
};

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
    mode: 'simple',
    algorithm: 'random_forest',
    trainingResult: null,
  });
  const [uploading, setUploading] = useState(false);
  const [training, setTraining] = useState(false);
  const [previewData, setPreviewData] = useState<any[] | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [trainingProgress, setTrainingProgress] = useState(0);
  const [trainingStep, setTrainingStep] = useState('');
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

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
      setCurrentStep('target');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Gagal mengunggah file';
      toast('error', message);
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
          setCurrentStep('results');
          setTraining(false);
          toast('success', 'Training berhasil diselesaikan!');
        } else if (step === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current);
          toast('error', status.error || 'Training gagal');
          setCurrentStep('review');
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
    setCurrentStep('training');

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
        setCurrentStep('results');
        setTraining(false);
        toast('success', 'Training berhasil diselesaikan!');
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Training gagal';
      toast('error', message);
      setCurrentStep('review');
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
                  onChange={(e) => {
                    const ds = datasetsList.find((d) => d.id === e.target.value);
                    if (ds) {
                      setState((prev) => ({
                        ...prev,
                        datasetId: ds.id,
                        datasetName: ds.name,
                      }));
                      setCurrentStep('target');
                    }
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
                Kolom mana yang ingin Anda prediksi?
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Kolom Target
                </label>
                <select
                  value={state.targetColumn}
                  onChange={(e) => setState((prev) => ({ ...prev, targetColumn: e.target.value }))}
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
                onClick={() => setCurrentStep('upload')}
                className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Kembali
              </button>
              <button
                onClick={() => setCurrentStep('preview')}
                disabled={!state.targetColumn}
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

            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep('target')}
                className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Kembali
              </button>
              <button
                onClick={() => setCurrentStep('mode')}
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
              <div className="rounded-xl border border-gray-200 bg-white p-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pilih Algoritma
                </label>
                <select
                  value={state.algorithm}
                  onChange={(e) => setState((prev) => ({ ...prev, algorithm: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                >
                  {Object.entries(ALGORITHM_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep('preview')}
                className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Kembali
              </button>
              <button
                onClick={() => setCurrentStep('review')}
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

            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep('mode')}
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
              <p className="mt-2 text-gray-500">
                Model Anda telah berhasil dilatih
              </p>
            </div>

            {state.trainingResult && (
              <div className="rounded-xl border border-gray-200 bg-white p-6">
                <h3 className="mb-4 font-semibold text-gray-900">Ringkasan Hasil</h3>

                {state.trainingResult.results?.human_summary && (
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
                )}

                {!state.trainingResult.results?.human_summary && (
                  <div className="grid grid-cols-2 gap-4">
                    {state.trainingResult.results?.metrics?.accuracy !== undefined && (
                      <div className="rounded-lg bg-gray-50 p-4">
                        <p className="text-xs text-gray-500">Akurasi</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {(state.trainingResult.results.metrics.accuracy * 100).toFixed(1)}%
                        </p>
                      </div>
                    )}
                    {state.trainingResult.results?.metrics?.f1_macro !== undefined && (
                      <div className="rounded-lg bg-gray-50 p-4">
                        <p className="text-xs text-gray-500">Skor F1</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {(state.trainingResult.results.metrics.f1_macro * 100).toFixed(1)}%
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            <div className="flex justify-center gap-4">
              <button
                onClick={() => {
                  setCurrentStep('upload');
                  setState({
                    datasetFile: null,
                    datasetId: null,
                    datasetName: '',
                    targetColumn: '',
                    mode: 'simple',
                    algorithm: 'random_forest',
                    trainingResult: null,
                  });
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
            </div>
          </div>
        );
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Training Wizard</h1>
        <p className="text-gray-500">Latih model dalam beberapa langkah sederhana</p>
      </div>

      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          const status = getStepStatus(index);

          return (
            <div key={step.key} className="flex items-center">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full ${
                  status === 'completed'
                    ? 'bg-green-100 text-green-600'
                    : status === 'active'
                    ? 'bg-primary-100 text-primary-600'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {status === 'completed' ? (
                  <CheckCircle2 className="h-5 w-5" />
                ) : (
                  <Icon className="h-5 w-5" />
                )}
              </div>
              <span
                className={`ml-2 text-sm font-medium ${
                  status === 'active' ? 'text-primary-600' : status === 'completed' ? 'text-green-600' : 'text-gray-400'
                }`}
              >
                {step.label}
              </span>
              {index < STEPS.length - 1 && (
                <div
                  className={`ml-4 h-0.5 w-8 ${
                    status === 'completed' ? 'bg-green-200' : 'bg-gray-200'
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
