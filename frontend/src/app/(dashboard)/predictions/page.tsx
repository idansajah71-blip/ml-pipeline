'use client';

import { useEffect, useState } from 'react';
import { Zap, Loader2 } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { models } from '@/lib/api';
import { MLModel } from '@/types';

export default function PredictionsPage() {
  const [modelsList, setModelsList] = useState<MLModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [inputData, setInputData] = useState('');
  const [predicting, setPredicting] = useState(false);
  const [results, setResults] = useState<any>(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const res = await models.list();
        setModelsList(res.data.items.filter((m) => m.status === 'deployed' || m.status === 'trained'));
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchModels();
  }, []);

  const handlePredict = async () => {
    if (!selectedModel || !inputData) return;
    setPredicting(true);
    setResults(null);
    try {
      const data = JSON.parse(inputData);
      const res = await models.predict(selectedModel, { data: Array.isArray(data) ? data : [data] });
      setResults(res.data);
    } catch (err: any) {
      setResults({ error: err.response?.data?.detail || err.message });
    } finally {
      setPredicting(false);
    }
  };

  const model = modelsList.find((m) => m.id === selectedModel);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Predictions</h1>
        <p className="text-gray-500">Make predictions using your trained models</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold">Input</h2>

          <div>
            <label className="block text-sm font-medium text-gray-700">Select Model</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              <option value="">Choose a model...</option>
              {modelsList.map((m) => (
                <option key={m.id} value={m.id}>{m.name} ({m.algorithm} v{m.version})</option>
              ))}
            </select>
          </div>

          {model && (
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-xs text-gray-500">Features: {model.feature_names?.join(', ')}</p>
              <p className="text-xs text-gray-500">Target: {model.target_column}</p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700">Input Data (JSON)</label>
            <textarea
              value={inputData}
              onChange={(e) => setInputData(e.target.value)}
              rows={8}
              placeholder={model ? `{\n  ${model.feature_names?.map((f) => `"${f}": 0`).join(',\n  ')}\n}` : '{ "feature1": 0, "feature2": 0 }'}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-4 py-2.5 font-mono text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            />
          </div>

          <button
            onClick={handlePredict}
            disabled={!selectedModel || !inputData || predicting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            {predicting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            {predicting ? 'Predicting...' : 'Predict'}
          </button>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold">Results</h2>
          {!results ? (
            <div className="flex flex-col items-center justify-center py-16">
              <Zap className="mb-4 h-12 w-12 text-gray-300" />
              <p className="text-gray-500">Make a prediction to see results</p>
            </div>
          ) : results.error ? (
            <div className="rounded-lg bg-red-50 p-4">
              <p className="text-sm text-red-700">{results.error}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {results.predictions?.map((pred: any, i: number) => (
                <div key={i} className="rounded-lg border border-gray-100 p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-500">Prediction {i + 1}</span>
                    {pred.probability && (
                      <span className="text-sm text-gray-500">
                        Confidence: {(pred.probability * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                  <p className="text-2xl font-bold text-primary-600">{pred.prediction}</p>
                  {pred.probabilities && (
                    <div className="mt-2 space-y-1">
                      {Object.entries(pred.probabilities).map(([cls, prob]: [string, any]) => (
                        <div key={cls} className="flex items-center gap-2">
                          <span className="w-20 text-xs text-gray-500">{cls}</span>
                          <div className="flex-1 rounded-full bg-gray-200">
                            <div
                              className="rounded-full bg-primary-500"
                              style={{ width: `${prob * 100}%`, height: '8px' }}
                            />
                          </div>
                          <span className="w-12 text-right text-xs text-gray-600">{(prob * 100).toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {results.latency_ms !== undefined && (
                <p className="text-xs text-gray-500">Latency: {results.latency_ms}ms</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
