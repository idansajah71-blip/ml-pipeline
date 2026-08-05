'use client';

import { useState, useEffect } from 'react';
import { PieChart, TrendingUp } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { explainDashboard, models } from '@/lib/api';

export default function ExplainDashboardPage() {
  const [modelList, setModelList] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [globalResult, setGlobalResult] = useState<any>(null);
  const [predictInput, setPredictInput] = useState('');
  const [predictionResult, setPredictionResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    models.list()
      .then(res => { setModelList(res.data.items || []); setLoading(false); })
      .catch(() => { setLoadError('Gagal memuat daftar model'); setLoading(false); });
  }, []);

  const loadGlobal = async () => {
    if (!selectedModel) return;
    try {
      const res = await explainDashboard.global(selectedModel);
      setGlobalResult(res.data);
    } catch (err) { alert('Failed'); }
  };

  const explainPrediction = async () => {
    if (!selectedModel || !predictInput) return;
    try {
      const data = JSON.parse(predictInput);
      const res = await explainDashboard.prediction(selectedModel, data);
      setPredictionResult(res.data);
    } catch (err) { alert('Invalid JSON'); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Explainability Dashboard</h1>
        <p className="text-gray-500 dark:text-gray-400">Interactive model explanations with SHAP</p>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        {loadError && (
          <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400">
            {loadError}
          </div>
        )}
        <div className="flex gap-4">
          <select value={selectedModel} onChange={e => setSelectedModel(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white">
            <option value="">{loading ? 'Memuat model...' : 'Pilih model...'}</option>
            {modelList.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <button onClick={loadGlobal} disabled={!selectedModel}
            className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
            <TrendingUp className="h-4 w-4" /> Global Explanation
          </button>
        </div>
      </div>

      {globalResult && !globalResult.error && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Feature Importance (Global)</h2>
          <div className="space-y-2">
            {Object.entries(globalResult.feature_importance || {}).map(([feature, importance]: [string, any]) => (
              <div key={feature} className="flex items-center gap-4">
                <span className="w-40 text-sm text-gray-700 dark:text-gray-300 truncate">{feature}</span>
                <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-4">
                  <div className="bg-primary-500 h-4 rounded-full" style={{ width: `${Math.min(importance * 1000, 100)}%` }} />
                </div>
                <span className="w-16 text-right text-sm font-mono text-gray-600 dark:text-gray-400">{importance.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Prediction Explanation</h2>
        <textarea placeholder='{"feature1": 1.5, "feature2": "value"}' value={predictInput} onChange={e => setPredictInput(e.target.value)}
          className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white h-24 font-mono mb-3" />
        <button onClick={explainPrediction} disabled={!selectedModel}
          className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700 disabled:opacity-50">
          <PieChart className="h-4 w-4" /> Explain Prediction
        </button>

        {predictionResult && !predictionResult.error && (
          <div className="mt-4 space-y-4">
            <div className="rounded-lg bg-gray-50 dark:bg-gray-700/50 p-4">
              <p className="text-sm text-gray-500">Prediction: <span className="font-bold text-gray-900 dark:text-white">{JSON.stringify(predictionResult.prediction)}</span></p>
              <p className="text-sm text-gray-500">Base value: <span className="font-mono">{predictionResult.base_value}</span></p>
            </div>
            <div className="space-y-2">
              {predictionResult.contributions?.map((c: any, i: number) => (
                <div key={i} className="flex items-center gap-4">
                  <span className="w-32 text-sm text-gray-700 dark:text-gray-300">{c.feature}</span>
                  <span className="w-20 text-sm font-mono text-gray-500">{c.value}</span>
                  <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                    <div className={`h-3 rounded-full ${c.direction === 'positive' ? 'bg-green-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(Math.abs(c.contribution) * 500, 100)}%` }} />
                  </div>
                  <span className={`w-16 text-right text-xs font-mono ${c.direction === 'positive' ? 'text-green-600' : 'text-red-600'}`}>
                    {c.contribution > 0 ? '+' : ''}{c.contribution.toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
