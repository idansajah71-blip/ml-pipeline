'use client';

import { useState, useCallback } from 'react';
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
} from 'lucide-react';
import { useToast } from '@/components/Toast';
import { models, datasets as datasetsApi } from '@/lib/api';
import { useDatasets } from '@/lib/hooks';

type WizardStep = 'upload' | 'target' | 'mode' | 'review' | 'training' | 'results';

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
  { key: 'upload', label: 'Upload Data', icon: Upload },
  { key: 'target', label: 'Select Target', icon: Target },
  { key: 'mode', label: 'Choose Mode', icon: Cpu },
  { key: 'review', label: 'Review', icon: BarChart3 },
  { key: 'results', label: 'Results', icon: CheckCircle2 },
];

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

  const handleFileUpload = useCallback(async (file: File) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('name', file.name.replace(/\.[^/.]+$/, ''));
      formData.append('description', 'Uploaded via training wizard');

      const result = await datasetsApi.create(formData);
      mutateDatasets();

      setState((prev) => ({
        ...prev,
        datasetFile: file,
        datasetId: result.id,
        datasetName: result.name,
      }));

      if (result.columns) {
        setColumns(result.columns);
      }

      toast('success', 'Dataset uploaded successfully');
      setCurrentStep('target');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Upload failed';
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
    if (file) {
      handleFileUpload(file);
    }
  }, [handleFileUpload]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleFileUpload(file);
    }
  }, [handleFileUpload]);

  const handleTrain = async () => {
    if (!state.datasetId || !state.targetColumn) {
      toast('error', 'Please select a dataset and target column');
      return;
    }

    setTraining(true);
    setCurrentStep('training');

    try {
      const modelResult = await models.create({
        name: `Wizard Model - ${state.datasetName}`,
        algorithm: state.mode === 'simple' ? 'random_forest' : state.algorithm,
        target_column: state.targetColumn,
        description: `Created via training wizard (${state.mode} mode)`,
      });

      const trainResult = await models.train(modelResult.id, {
        dataset_id: state.datasetId,
        algorithm: state.mode === 'simple' ? 'random_forest' : state.algorithm,
        target_column: state.targetColumn,
        mode: state.mode,
      });

      setState((prev) => ({ ...prev, trainingResult: trainResult }));
      setCurrentStep('results');
      toast('success', 'Training completed successfully!');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Training failed';
      toast('error', message);
      setCurrentStep('review');
    } finally {
      setTraining(false);
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 'upload':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">Upload Your Dataset</h2>
              <p className="mt-2 text-gray-500">
                Drag and drop your CSV or Excel file, or click to browse
              </p>
            </div>

            <div
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 py-16 transition-colors hover:border-primary-400 hover:bg-primary-50"
            >
              <Upload className="mb-4 h-12 w-12 text-gray-400" />
              <p className="mb-2 text-sm font-medium text-gray-700">
                {uploading ? 'Uploading...' : 'Drop your file here'}
              </p>
              <p className="mb-4 text-xs text-gray-500">CSV, XLS, or XLSX (max 100MB)</p>
              <label className="cursor-pointer rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">
                <input
                  type="file"
                  accept=".csv,.xls,.xlsx"
                  onChange={handleFileInput}
                  className="hidden"
                  disabled={uploading}
                />
                {uploading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Uploading...
                  </span>
                ) : (
                  'Browse Files'
                )}
              </label>
            </div>

            {datasetsList.length > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-4">
                <p className="mb-3 text-sm font-medium text-gray-700">Or select an existing dataset:</p>
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
                  <option value="">Select a dataset...</option>
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
              <h2 className="text-xl font-semibold text-gray-900">Select Target Column</h2>
              <p className="mt-2 text-gray-500">
                Which column do you want to predict?
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Target Column
                </label>
                <select
                  value={state.targetColumn}
                  onChange={(e) => setState((prev) => ({ ...prev, targetColumn: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                >
                  <option value="">Select the column to predict...</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div className="rounded-lg bg-blue-50 p-4">
                <div className="flex gap-3">
                  <Info className="h-5 w-5 text-blue-500 flex-shrink-0" />
                  <div className="text-sm text-blue-700">
                    <p className="font-medium">Tips for selecting a target:</p>
                    <ul className="mt-1 list-disc list-inside space-y-1">
                      <li>Choose the column you want to predict</li>
                      <li>For classification: category labels (e.g., "spam", "yes/no")</li>
                      <li>For regression: numeric values (e.g., price, temperature)</li>
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
                Back
              </button>
              <button
                onClick={() => setCurrentStep('mode')}
                disabled={!state.targetColumn}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                Next
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        );

      case 'mode':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">Choose Training Mode</h2>
              <p className="mt-2 text-gray-500">
                How would you like to train your model?
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
                    <h3 className="font-semibold text-gray-900">Simple Mode</h3>
                    <p className="text-sm text-gray-500">Recommended for beginners</p>
                  </div>
                </div>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Automatic model selection
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Auto data preprocessing
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Human-readable results
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
                    <h3 className="font-semibold text-gray-900">Advanced Mode</h3>
                    <p className="text-sm text-gray-500">Full control over training</p>
                  </div>
                </div>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Choose any algorithm
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Custom hyperparameters
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    Detailed metrics
                  </li>
                </ul>
              </button>
            </div>

            {state.mode === 'advanced' && (
              <div className="rounded-xl border border-gray-200 bg-white p-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Algorithm
                </label>
                <select
                  value={state.algorithm}
                  onChange={(e) => setState((prev) => ({ ...prev, algorithm: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
                >
                  <option value="random_forest">Random Forest</option>
                  <option value="gradient_boosting">Gradient Boosting</option>
                  <option value="logistic_regression">Logistic Regression</option>
                  <option value="svm">Support Vector Machine</option>
                  <option value="knn">K-Nearest Neighbors</option>
                  <option value="decision_tree">Decision Tree</option>
                </select>
              </div>
            )}

            <div className="flex justify-between">
              <button
                onClick={() => setCurrentStep('target')}
                className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                onClick={() => setCurrentStep('review')}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
              >
                Next
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        );

      case 'review':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">Review Configuration</h2>
              <p className="mt-2 text-gray-500">
                Please confirm your training settings
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">Dataset</span>
                <span className="text-sm font-medium text-gray-900">{state.datasetName}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">Target Column</span>
                <span className="text-sm font-medium text-gray-900">{state.targetColumn}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-500">Mode</span>
                <span className="text-sm font-medium text-gray-900 capitalize">{state.mode}</span>
              </div>
              {state.mode === 'advanced' && (
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm text-gray-500">Algorithm</span>
                  <span className="text-sm font-medium text-gray-900">{state.algorithm}</span>
                </div>
              )}
            </div>

            {state.mode === 'simple' && (
              <div className="rounded-lg bg-green-50 p-4">
                <div className="flex gap-3">
                  <Zap className="h-5 w-5 text-green-500 flex-shrink-0" />
                  <div className="text-sm text-green-700">
                    <p className="font-medium">Simple Mode</p>
                    <p className="mt-1">
                      The system will automatically select the best algorithm and preprocess your data.
                      You'll receive a human-readable summary of the results.
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
                Back
              </button>
              <button
                onClick={handleTrain}
                disabled={training}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                {training ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Training...
                  </>
                ) : (
                  <>
                    <Cpu className="h-4 w-4" />
                    Start Training
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
              <h2 className="text-xl font-semibold text-gray-900">Training in Progress</h2>
              <p className="mt-2 text-gray-500">
                Please wait while we train your model...
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-sm text-gray-700">Dataset loaded</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-sm text-gray-700">Data validated</span>
                </div>
                <div className="flex items-center gap-3">
                  <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
                  <span className="text-sm text-gray-700">Training model...</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-gray-300" />
                  <span className="text-sm text-gray-400">Evaluating results</span>
                </div>
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
              <h2 className="text-xl font-semibold text-gray-900">Training Complete!</h2>
              <p className="mt-2 text-gray-500">
                Your model has been trained successfully
              </p>
            </div>

            {state.trainingResult && (
              <div className="rounded-xl border border-gray-200 bg-white p-6">
                <h3 className="mb-4 font-semibold text-gray-900">Results Summary</h3>

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
                            <p className="text-sm font-medium text-yellow-800">Warnings:</p>
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
                        <p className="text-xs text-gray-500">Accuracy</p>
                        <p className="text-lg font-semibold text-gray-900">
                          {(state.trainingResult.results.metrics.accuracy * 100).toFixed(1)}%
                        </p>
                      </div>
                    )}
                    {state.trainingResult.results?.metrics?.f1_macro !== undefined && (
                      <div className="rounded-lg bg-gray-50 p-4">
                        <p className="text-xs text-gray-500">F1 Score</p>
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
                }}
                className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Train Another Model
              </button>
              <button
                onClick={() => router.push('/models')}
                className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
              >
                View All Models
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
        <p className="text-gray-500">Train a model in a few simple steps</p>
      </div>

      <div className="flex items-center justify-between">
        {STEPS.map((step, index) => {
          const Icon = step.icon;
          const isActive = step.key === currentStep;
          const isCompleted = STEPS.findIndex((s) => s.key === currentStep) > index;

          return (
            <div key={step.key} className="flex items-center">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full ${
                  isCompleted
                    ? 'bg-green-100 text-green-600'
                    : isActive
                    ? 'bg-primary-100 text-primary-600'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {isCompleted ? (
                  <CheckCircle2 className="h-5 w-5" />
                ) : (
                  <Icon className="h-5 w-5" />
                )}
              </div>
              <span
                className={`ml-2 text-sm font-medium ${
                  isActive ? 'text-primary-600' : isCompleted ? 'text-green-600' : 'text-gray-400'
                }`}
              >
                {step.label}
              </span>
              {index < STEPS.length - 1 && (
                <div
                  className={`ml-4 h-0.5 w-12 ${
                    isCompleted ? 'bg-green-200' : 'bg-gray-200'
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
