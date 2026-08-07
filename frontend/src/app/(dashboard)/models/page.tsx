'use client';

import { useState, useMemo, useEffect } from 'react';
import { Plus, Trash2, Rocket, Brain, Loader2, Eye, Star, Zap } from 'lucide-react';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import Pagination from '@/components/Pagination';
import SearchInput from '@/components/SearchInput';
import { CardSkeleton } from '@/components/Skeleton';
import { useToast } from '@/components/Toast';
import FavoriteStar from '@/components/FavoriteStar';
import { models, datasets as datasetsApi, algorithms } from '@/lib/api';
import { useModels, useDatasets, useAlgorithms } from '@/lib/hooks';
import { useFavorites } from '@/lib/useFavorites';
import { ALGORITHMS } from '@/lib/algorithms';
import Tooltip from '@/components/Tooltip';
import Link from 'next/link';

const ITEMS_PER_PAGE = 9;

export default function ModelsPage() {
  const { toast } = useToast();
  const { models: modelsList, isLoading, mutate } = useModels();
  const { datasets: datasetsList } = useDatasets();
  const { classificationAlgorithms: algorithmsList } = useAlgorithms();
  const { favoriteIds, isFavorite } = useFavorites('model');
  const [showCreate, setShowCreate] = useState(false);
  const [training, setTraining] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({ name: '', algorithm: 'random_forest', target_column: '', description: '' });
  const [trainForms, setTrainForms] = useState<Record<string, { dataset_id: string }>>({});
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [systemModels, setSystemModels] = useState<any[]>([]);
  const [showSystem, setShowSystem] = useState(false);

  // Fetch system (platform) models
  useEffect(() => {
    models.systemList().then((res) => setSystemModels(res.data.items || [])).catch(() => {});
  }, []);

  // Merge user models + system models
  const allModels = useMemo(() => {
    const userModels = modelsList.map((m) => ({ ...m, _isSystem: false }));
    const sysModels = systemModels.map((m) => ({ ...m, _isSystem: true }));
    return [...userModels, ...sysModels];
  }, [modelsList, systemModels]);

  // Pinned models float to top
  const filteredModels = useMemo(() => {
    const source = showSystem ? allModels : allModels.filter((m) => !m._isSystem);
    const matched = source.filter(
      (m) =>
        m.name.toLowerCase().includes(search.toLowerCase()) ||
        m.algorithm.toLowerCase().includes(search.toLowerCase())
    );
    return [
      ...matched.filter((m) => isFavorite(m.id)),
      ...matched.filter((m) => !isFavorite(m.id)),
    ];
  }, [allModels, search, favoriteIds, showSystem]); // eslint-disable-line react-hooks/exhaustive-deps

  const totalPages = Math.ceil(filteredModels.length / ITEMS_PER_PAGE);
  const paginatedModels = filteredModels.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  const handleCreate = async () => {
    try {
      await models.create(createForm);
      setShowCreate(false);
      setCreateForm({ name: '', algorithm: 'random_forest', target_column: '', description: '' });
      mutate();
      toast('success', 'Model created successfully');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Create failed';
      toast('error', message);
    }
  };

  const handleTrain = async (modelId: string) => {
    const datasetId = trainForms[modelId]?.dataset_id || '';
    if (!datasetId) return;
    setTraining(modelId);
    try {
      await models.train(modelId, {
        dataset_id: datasetId,
        algorithm: 'random_forest',
      });
      mutate();
      toast('success', 'Training completed successfully');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Training failed';
      toast('error', message);
    } finally {
      setTraining(null);
    }
  };

  const handleDeploy = async (modelId: string) => {
    try {
      await models.deploy(modelId);
      mutate();
      toast('success', 'Model deployed successfully');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Deploy failed';
      toast('error', message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Archive this model? It will move to the trash and can be restored later.')) return;
    await models.delete(id);
    mutate();
    toast('success', 'Model archived successfully');
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Models</h1>
          <p className="text-gray-500 dark:text-gray-400">Create, train, and manage your ML models</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/models/trash"
            className="inline-flex items-center justify-center rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
          >
            View Model Trash
          </Link>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
          >
            <Plus className="h-4 w-4" />
            Create Model
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Create New Model</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <input
              type="text"
              placeholder="Model Name"
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
            />
            <div className="relative">
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Algoritma</label>
              <div className="grid max-h-64 grid-cols-1 gap-1.5 overflow-y-auto rounded-lg border border-gray-200 p-2 dark:border-gray-600">
                {algorithmsList.length === 0 && (
                  <p className="px-2 py-1 text-xs text-gray-400">Memuat algoritma...</p>
                )}
                {algorithmsList.map((alg) => {
                  const info = ALGORITHMS[alg];
                  const isSelected = createForm.algorithm === alg;
                  return (
                    <button
                      key={alg}
                      type="button"
                      onClick={() => setCreateForm({ ...createForm, algorithm: alg })}
                      className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                        isSelected
                          ? 'border border-primary-300 bg-primary-50 text-primary-700 dark:border-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                          : 'border border-transparent hover:bg-gray-50 dark:hover:bg-gray-700'
                      }`}
                    >
                      <span className="font-medium">{info?.label || alg}</span>
                      {info && (
                        <span className="ml-2 text-xs text-gray-400">— {info.bestFor}</span>
                      )}
                    </button>
                  );
                })}
              </div>
              {createForm.algorithm && ALGORITHMS[createForm.algorithm] && (
                <div className="mt-1.5 rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-700 dark:bg-blue-900/20 dark:text-blue-300">
                  {ALGORITHMS[createForm.algorithm].description}
                </div>
              )}
            </div>
            <input
              type="text"
              placeholder="Target Column"
              value={createForm.target_column}
              onChange={(e) => setCreateForm({ ...createForm, target_column: e.target.value })}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
            />
            <button
              onClick={handleCreate}
              disabled={!createForm.name || !createForm.target_column}
              className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </div>
      )}

      <div className="flex items-center gap-4">
        <div className="flex-1">
          <SearchInput value={search} onChange={setSearch} placeholder="Search models..." />
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : paginatedModels.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16 dark:border-gray-600">
          <Brain className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-500 dark:text-gray-400">
            {search ? 'No models match your search' : 'No models yet. Create your first model!'}
          </p>
        </div>
      ) : (
        <>
          {/* Pinned section label */}
          {favoriteIds.length > 0 && !search && (
            <div className="flex items-center gap-2 text-xs font-medium text-yellow-600 dark:text-yellow-400">
              <Star className="h-3.5 w-3.5 fill-yellow-400" />
              Model favorit ditampilkan di atas
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {paginatedModels.map((model) => (
              <div key={model.id} className={`rounded-xl border bg-white p-5 dark:bg-gray-800 ${isFavorite(model.id) ? 'border-yellow-300 dark:border-yellow-600/50' : 'border-gray-200 dark:border-gray-700'}`}>
                <div className="mb-3 flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white">{model.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{model.algorithm} v{model.version}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <FavoriteStar id={model.id} type="model" />
                    <StatusBadge status={model.status} />
                  </div>
                </div>

                {model.metrics?.accuracy !== undefined && (
                  <div className="mb-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Accuracy</p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {(model.metrics.accuracy * 100).toFixed(1)}%
                    </p>
                  </div>
                )}

                <div className="mb-3 flex flex-wrap gap-1">
                  {model.tags?.map((tag) => (
                    <span key={tag} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">{tag}</span>
                  ))}
                </div>

                <div className="flex gap-2">
                  <Link
                    href={`/models/${model.id}`}
                    className="flex items-center gap-1 rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                  >
                    <Eye className="h-3 w-3" />
                    View
                  </Link>
                  {model.status === 'trained' && (
                    <select
                      value={trainForms[model.id]?.dataset_id || ''}
                      onChange={(e) => setTrainForms(prev => ({ ...prev, [model.id]: { dataset_id: e.target.value } }))}
                      className="flex-1 rounded-lg border border-gray-300 bg-white px-2 py-1.5 text-xs dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    >
                      <option value="">Pilih Dataset</option>
                      {datasetsList.map((ds) => (
                        <option key={ds.id} value={ds.id}>{ds.name}</option>
                      ))}
                    </select>
                  )}
                  {model.status === 'trained' && (
                    <button
                      onClick={() => handleTrain(model.id)}
                      disabled={!trainForms[model.id]?.dataset_id || training === model.id}
                      className="flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
                    >
                      {training === model.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Rocket className="h-3 w-3" />}
                      Train
                    </button>
                  )}
                  {model.status === 'trained' && (
                    <button
                      onClick={() => handleDeploy(model.id)}
                      className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
                    >
                      Deploy
                    </button>
                  )}
                  <button
                    onClick={() => handleDelete(model.id)}
                    className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
          <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={setCurrentPage} />
        </>
      )}
    </div>
  );
}
