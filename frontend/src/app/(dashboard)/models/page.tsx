'use client';

import { useState, useMemo } from 'react';
import { Plus, Trash2, Rocket, Brain, Loader2, Eye } from 'lucide-react';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import Pagination from '@/components/Pagination';
import SearchInput from '@/components/SearchInput';
import { CardSkeleton } from '@/components/Skeleton';
import { useToast } from '@/components/Toast';
import { models, datasets as datasetsApi, algorithms } from '@/lib/api';
import { useModels, useDatasets, useAlgorithms } from '@/lib/hooks';
import Link from 'next/link';

const ITEMS_PER_PAGE = 9;

export default function ModelsPage() {
  const { toast } = useToast();
  const { models: modelsList, isLoading, mutate } = useModels();
  const { datasets: datasetsList } = useDatasets();
  const { algorithms: algorithmsList } = useAlgorithms();
  const [showCreate, setShowCreate] = useState(false);
  const [training, setTraining] = useState<string | null>(null);
  const [createForm, setCreateForm] = useState({ name: '', algorithm: 'random_forest', target_column: '', description: '' });
  const [trainForm, setTrainForm] = useState({ dataset_id: '', algorithm: 'random_forest' });
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const filteredModels = useMemo(() => {
    return modelsList.filter(
      (m) =>
        m.name.toLowerCase().includes(search.toLowerCase()) ||
        m.algorithm.toLowerCase().includes(search.toLowerCase())
    );
  }, [modelsList, search]);

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
    setTraining(modelId);
    try {
      await models.train(modelId, {
        dataset_id: trainForm.dataset_id,
        algorithm: trainForm.algorithm,
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
    if (!confirm('Delete this model?')) return;
    await models.delete(id);
    mutate();
    toast('success', 'Model deleted successfully');
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Models</h1>
          <p className="text-gray-500">Create, train, and manage your ML models</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" />
          Create Model
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold">Create New Model</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <input
              type="text"
              placeholder="Model Name"
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            />
            <select
              value={createForm.algorithm}
              onChange={(e) => setCreateForm({ ...createForm, algorithm: e.target.value })}
              className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              {algorithmsList.map((alg) => (
                <option key={alg} value={alg}>{alg}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Target Column"
              value={createForm.target_column}
              onChange={(e) => setCreateForm({ ...createForm, target_column: e.target.value })}
              className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
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
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16">
          <Brain className="mb-4 h-12 w-12 text-gray-300" />
          <p className="text-gray-500">
            {search ? 'No models match your search' : 'No models yet. Create your first model!'}
          </p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {paginatedModels.map((model) => (
              <div key={model.id} className="rounded-xl border border-gray-200 bg-white p-5">
                <div className="mb-3 flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900">{model.name}</h3>
                    <p className="text-sm text-gray-500">{model.algorithm} v{model.version}</p>
                  </div>
                  <StatusBadge status={model.status} />
                </div>

                {model.metrics?.accuracy !== undefined && (
                  <div className="mb-3 rounded-lg bg-gray-50 p-3">
                    <p className="text-xs text-gray-500">Accuracy</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {(model.metrics.accuracy * 100).toFixed(1)}%
                    </p>
                  </div>
                )}

                <div className="flex flex-wrap gap-1 mb-3">
                  {model.tags?.map((tag) => (
                    <span key={tag} className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{tag}</span>
                  ))}
                </div>

                <div className="flex gap-2">
                  <Link
                    href={`/models/${model.id}`}
                    className="flex items-center gap-1 rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200"
                  >
                    <Eye className="h-3 w-3" />
                    View
                  </Link>
                  {model.status === 'trained' && (
                    <select
                      value={trainForm.dataset_id}
                      onChange={(e) => setTrainForm({ ...trainForm, dataset_id: e.target.value })}
                      className="flex-1 rounded-lg border border-gray-300 px-2 py-1.5 text-xs"
                    >
                      <option value="">Select Dataset</option>
                      {datasetsList.map((ds) => (
                        <option key={ds.id} value={ds.id}>{ds.name}</option>
                      ))}
                    </select>
                  )}
                  {model.status === 'trained' && (
                    <button
                      onClick={() => handleTrain(model.id)}
                      disabled={!trainForm.dataset_id || training === model.id}
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
                    className="rounded-lg bg-red-50 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-100"
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
