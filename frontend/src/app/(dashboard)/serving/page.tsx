'use client';

import { useState, useEffect } from 'react';
import { Zap, Plus, Trash2, Activity } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { serving, models } from '@/lib/api';

export default function ServingPage() {
  const [endpoints, setEndpoints] = useState<any[]>([]);
  const [modelList, setModelList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newEndpoint, setNewEndpoint] = useState({ name: '', model_id: '', description: '', cache_ttl_seconds: 300 });
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [predictInput, setPredictInput] = useState('');
  const [predictResult, setPredictResult] = useState<any>(null);

  useEffect(() => {
    loadEndpoints();
    loadModels();
  }, []);

  const loadEndpoints = async () => {
    setLoading(true);
    try {
      const res = await serving.listEndpoints();
      setEndpoints(res.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const loadModels = async () => {
    try {
      const res = await models.list();
      setModelList(res.data.items || []);
    } catch (err) { console.error(err); }
  };

  const loadMetrics = async (endpointId: string) => {
    setSelectedEndpoint(endpointId);
    try {
      const res = await serving.metrics(endpointId, 24);
      setMetrics(res.data);
    } catch (err) { console.error(err); }
  };

  const createEndpoint = async () => {
    if (!newEndpoint.name || !newEndpoint.model_id) return;
    try {
      await serving.createEndpoint(newEndpoint);
      setShowCreate(false);
      setNewEndpoint({ name: '', model_id: '', description: '', cache_ttl_seconds: 300 });
      loadEndpoints();
    } catch (err) { alert('Failed to create endpoint'); }
  };

  const handlePredict = async () => {
    if (!selectedEndpoint || !predictInput) return;
    try {
      const data = JSON.parse(predictInput);
      const res = await serving.predict(selectedEndpoint, data);
      setPredictResult(res.data);
    } catch (err) { alert('Invalid JSON or prediction failed'); }
  };

  const deleteEndpoint = async (id: string) => {
    if (!confirm('Delete this endpoint?')) return;
    await serving.delete(id);
    loadEndpoints();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Model Serving</h1>
          <p className="text-gray-500 dark:text-gray-400">Production inference endpoints with caching</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700">
          <Plus className="h-4 w-4" /> New Endpoint
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Create Endpoint</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <input placeholder="Endpoint Name" value={newEndpoint.name} onChange={e => setNewEndpoint({...newEndpoint, name: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
            <select value={newEndpoint.model_id} onChange={e => setNewEndpoint({...newEndpoint, model_id: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white">
              <option value="">Select model...</option>
              {modelList.map(m => <option key={m.id} value={m.id}>{m.name} ({m.algorithm})</option>)}
            </select>
            <input placeholder="Description" value={newEndpoint.description} onChange={e => setNewEndpoint({...newEndpoint, description: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
            <input type="number" placeholder="Cache TTL (seconds)" value={newEndpoint.cache_ttl_seconds} onChange={e => setNewEndpoint({...newEndpoint, cache_ttl_seconds: Number(e.target.value)})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={createEndpoint} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">Create</button>
            <button onClick={() => setShowCreate(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Endpoints</h2>
          {loading ? <LoadingSpinner size="sm" /> : (
            <div className="space-y-2">
              {endpoints.map(ep => (
                <div key={ep.id} className={`rounded-lg px-3 py-2 ${selectedEndpoint === ep.id ? 'bg-primary-50 dark:bg-primary-900/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                  <button onClick={() => loadMetrics(ep.id)} className="w-full text-left">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{ep.name}</p>
                    <p className="text-xs text-gray-500">TTL: {ep.cache_ttl_seconds}s</p>
                  </button>
                  <button onClick={() => deleteEndpoint(ep.id)} className="mt-1 text-red-500 hover:text-red-700">
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))}
              {endpoints.length === 0 && <p className="text-sm text-gray-500">No endpoints yet</p>}
            </div>
          )}
        </div>

        {selectedEndpoint && (
          <div className="lg:col-span-2 space-y-6">
            {metrics && (
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-4">
                  <p className="text-sm text-blue-600">Total Requests</p>
                  <p className="text-2xl font-bold text-blue-900">{metrics.total_requests}</p>
                </div>
                <div className="rounded-lg bg-green-50 dark:bg-green-900/20 p-4">
                  <p className="text-sm text-green-600">Avg Latency</p>
                  <p className="text-2xl font-bold text-green-900">{metrics.avg_latency_ms}ms</p>
                </div>
                <div className="rounded-lg bg-purple-50 dark:bg-purple-900/20 p-4">
                  <p className="text-sm text-purple-600">Cache Hits</p>
                  <p className="text-2xl font-bold text-purple-900">{metrics.cache_hits}</p>
                </div>
                <div className="rounded-lg bg-orange-50 dark:bg-orange-900/20 p-4">
                  <p className="text-sm text-orange-600">Cache Hit Rate</p>
                  <p className="text-2xl font-bold text-orange-900">{metrics.cache_hit_rate}%</p>
                </div>
              </div>
            )}

            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Test Prediction</h2>
              <textarea placeholder='{"feature1": 1.5, "feature2": "value"}' value={predictInput} onChange={e => setPredictInput(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white h-24 font-mono mb-3" />
              <button onClick={handlePredict} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700">
                <Zap className="h-4 w-4" /> Predict
              </button>
              {predictResult && (
                <pre className="mt-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 p-4 text-sm text-gray-900 dark:text-white overflow-auto">
                  {JSON.stringify(predictResult, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
