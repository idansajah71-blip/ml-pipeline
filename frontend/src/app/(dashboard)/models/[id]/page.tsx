'use client';

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Brain, Trash2, Rocket, RotateCcw, Layers, Info, Play } from 'lucide-react';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import { models } from '@/lib/api';
import { useModel, useDatasetProfile } from '@/lib/hooks';
import { useToast } from '@/components/Toast';

export default function ModelDetailPage() {
  const { toast } = useToast();
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { model, isLoading, mutate } = useModel(id);
  const [activeTab, setActiveTab] = useState<'metrics' | 'parameters' | 'features' | 'explain' | 'card'>('metrics');
  const [explainData, setExplainData] = useState<Record<string, any>[]>([]);
  const [explainResult, setExplainResult] = useState<any>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [stageLoading, setStageLoading] = useState(false);

  const handleDeploy = async () => {
    if (!model) return;
    try {
      await models.deploy(model.id);
      mutate();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Deploy failed';
      toast('error', message);
    }
  };

  const handleRollback = async () => {
    if (!model) return;
    if (!confirm('Rollback to previous version?')) return;
    try {
      await models.rollback(model.id);
      mutate();
    } catch (err: any) {
      toast('error', err?.response?.data?.detail || 'Rollback failed');
    }
  };

  const handleStageUpdate = async (stage: string) => {
    if (!model) return;
    setStageLoading(true);
    try {
      await models.stage(model.id, { stage });
      mutate();
    } catch (err: any) {
      toast('error', err?.response?.data?.detail || 'Stage update failed');
    } finally {
      setStageLoading(false);
    }
  };

  const handleExplain = async () => {
    if (!model || explainData.length === 0) return;
    setExplainLoading(true);
    try {
      const res = await models.explain(model.id, { data: explainData, top_k: 10 });
      setExplainResult(res.data);
    } catch (err: any) {
      toast('error', err?.response?.data?.detail || 'Explanation failed');
    } finally {
      setExplainLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!model) return;
    if (!confirm('Delete this model?')) return;
    await models.delete(model.id);
    router.push('/models');
  };

  if (isLoading) {
    return <LoadingSpinner size="lg" className="mx-auto mt-20" />;
  }

  if (!model) {
    return (
      <div className="flex flex-col items-center justify-center mt-20">
        <p className="text-gray-500">Model not found</p>
        <button onClick={() => router.push('/models')} className="mt-4 text-primary-600 hover:underline">
          Back to Models
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.push('/models')}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Models
      </button>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary-100">
              <Brain className="h-7 w-7 text-primary-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{model.name}</h1>
              <p className="text-gray-500">{model.algorithm} v{model.version}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={model.status} />
            {model.status === 'trained' && (
              <>
                <button
                  onClick={handleDeploy}
                  className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  <Rocket className="h-4 w-4" />
                  Deploy
                </button>
                <button
                  onClick={handleRollback}
                  className="flex items-center gap-2 rounded-lg bg-yellow-50 px-4 py-2 text-sm font-medium text-yellow-600 hover:bg-yellow-100"
                >
                  <RotateCcw className="h-4 w-4" />
                  Rollback
                </button>
              </>
            )}
            <button
              onClick={handleDelete}
              className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-100"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          </div>
        </div>

        {model.description && (
          <p className="mt-4 text-gray-600">{model.description}</p>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          {model.tags?.map((tag) => (
            <span key={tag} className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
              {tag}
            </span>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-4">
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-500">Status</p>
          <p className="mt-1 text-lg font-semibold text-gray-900 capitalize">{model.status}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-500">Target Column</p>
          <p className="mt-1 text-lg font-semibold text-gray-900">{model.target_column || '-'}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-500">Features</p>
          <p className="mt-1 text-lg font-semibold text-gray-900">{model.feature_names?.length || 0}</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <p className="text-sm text-gray-500">Stage</p>
          <div className="mt-1 flex gap-2">
            {['development', 'staging', 'production', 'archived'].map((stage) => (
              <button
                key={stage}
                onClick={() => handleStageUpdate(stage)}
                disabled={stageLoading}
                className={`rounded px-2 py-1 text-xs font-medium ${
                  (model as any).stage === stage
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                }`}
              >
                {stage}
              </button>
            ))}
          </div>
        </div>
      </div>

      {model.metrics && Object.keys(model.metrics).length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white">
          <div className="flex border-b border-gray-200">
            {(['metrics', 'parameters', 'features', 'explain', 'card'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-6 py-3 text-sm font-medium capitalize ${
                  activeTab === tab
                    ? 'border-b-2 border-primary-600 text-primary-600'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="p-6">
            {activeTab === 'metrics' && (
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {Object.entries(model.metrics).map(([key, value]) => {
                  if (typeof value === 'object') return null;
                  return (
                    <div key={key} className="rounded-lg bg-gray-50 p-4">
                      <p className="text-xs text-gray-500">{key.replace(/_/g, ' ')}</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">
                        {typeof value === 'number' ? (key.includes('accuracy') || key.includes('f1') || key.includes('precision') || key.includes('recall') ? `${(value * 100).toFixed(1)}%` : value.toFixed(4)) : String(value)}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}

            {activeTab === 'parameters' && (
              <div className="space-y-2">
                {Object.entries(model.parameters || {}).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2">
                    <span className="text-sm text-gray-600">{key}</span>
                    <span className="text-sm font-medium text-gray-900">{String(value)}</span>
                  </div>
                ))}
                {Object.keys(model.parameters || {}).length === 0 && (
                  <p className="text-gray-500">No parameters recorded</p>
                )}
              </div>
            )}

            {activeTab === 'features' && (
              <div className="flex flex-wrap gap-2">
                {model.feature_names?.map((feature) => (
                  <span key={feature} className="rounded-lg bg-primary-50 px-3 py-1.5 text-sm text-primary-700">
                    {feature}
                  </span>
                ))}
                {(!model.feature_names || model.feature_names.length === 0) && (
                  <p className="text-gray-500">No features recorded</p>
                )}
              </div>
            )}

            {activeTab === 'explain' && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Input Data (JSON format)
                  </label>
                  <textarea
                    className="w-full rounded-lg border border-gray-300 p-3 text-sm font-mono"
                    rows={4}
                    placeholder='[{"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}]'
                    value={JSON.stringify(explainData, null, 2)}
                    onChange={(e) => {
                      try {
                        setExplainData(JSON.parse(e.target.value));
                      } catch {}
                    }}
                  />
                </div>
                <button
                  onClick={handleExplain}
                  disabled={explainLoading || explainData.length === 0}
                  className="flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
                >
                  <Play className="h-4 w-4" />
                  {explainLoading ? 'Explaining...' : 'Explain Prediction'}
                </button>

                {explainResult && (
                  <div className="mt-4 space-y-4">
                    <h3 className="font-semibold text-gray-900">Global Feature Importance</h3>
                    <div className="space-y-2">
                      {Object.entries(explainResult.global_importance || {})
                        .sort(([, a], [, b]) => (b as number) - (a as number))
                        .slice(0, 10)
                        .map(([feature, importance]) => (
                          <div key={feature} className="flex items-center gap-3">
                            <span className="w-32 text-sm text-gray-600 truncate">{feature}</span>
                            <div className="flex-1 bg-gray-100 rounded-full h-4">
                              <div
                                className="bg-purple-500 h-4 rounded-full"
                                style={{ width: `${Math.min(((importance as number) / Math.max(...Object.values(explainResult.global_importance) as number[])) * 100, 100)}%` }}
                              />
                            </div>
                            <span className="text-sm font-medium text-gray-900 w-16 text-right">
                              {(importance as number).toFixed(4)}
                            </span>
                          </div>
                        ))}
                    </div>

                    {explainResult.explanations?.[0] && (
                      <>
                        <h3 className="font-semibold text-gray-900 mt-4">Prediction Explanation</h3>
                        <div className="rounded-lg bg-gray-50 p-4">
                          <p className="text-sm">Prediction: <span className="font-semibold">{explainResult.explanations[0].prediction}</span></p>
                          {explainResult.explanations[0].confidence && (
                            <p className="text-sm">Confidence: <span className="font-semibold">{(explainResult.explanations[0].confidence * 100).toFixed(1)}%</span></p>
                          )}
                        </div>
                        <div className="space-y-1">
                          {explainResult.explanations[0].feature_contributions?.map((c: any, i: number) => (
                            <div key={i} className="flex items-center gap-2 text-sm">
                              <span className={`w-2 h-2 rounded-full ${c.direction === 'positive' ? 'bg-green-500' : 'bg-red-500'}`} />
                              <span className="w-32 truncate">{c.feature}</span>
                              <span className="text-gray-500">= {c.value}</span>
                              <span className={`font-medium ${c.direction === 'positive' ? 'text-green-600' : 'text-red-600'}`}>
                                {c.direction === 'positive' ? '+' : ''}{c.contribution.toFixed(4)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'card' && (
              <div className="space-y-4">
                <p className="text-sm text-gray-500">Model Card memuat informasi detail tentang model, termasuk intended use, training data, evaluation results, dan limitations.</p>
                <div className="rounded-lg bg-gray-50 p-4">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                    {JSON.stringify((model as any).model_card || {}, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
