'use client';

import { useState, useEffect } from 'react';
import { Zap, Plus, Trash2, Activity, AlertCircle } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { serving, models, formatApiError } from '@/lib/api';

export default function ServingPage() {
  const [endpoints, setEndpoints] = useState<any[]>([]);
  const [modelList, setModelList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newEndpoint, setNewEndpoint] = useState({ name: '', model_id: '', description: '', cache_ttl_seconds: 300 });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [predictInput, setPredictInput] = useState('');
  const [predictResult, setPredictResult] = useState<any>(null);
  const [predictError, setPredictError] = useState('');

  useEffect(() => {
    loadEndpoints();
    loadModels();
  }, []);

  const loadEndpoints = async () => {
    setLoading(true);
    try {
      const res = await serving.listEndpoints();
      setEndpoints(res.data);
    } catch (err) {
      setLoadError(formatApiError(err, 'Gagal memuat daftar endpoint'));
    }
    setLoading(false);
  };

  const loadModels = async () => {
    try {
      const res = await models.list();
      setModelList(res.data.items || []);
    } catch (err) {
      setLoadError(formatApiError(err, 'Gagal memuat daftar model'));
    }
  };

  const loadMetrics = async (endpointId: string) => {
    setSelectedEndpoint(endpointId);
    try {
      const res = await serving.metrics(endpointId, 24);
      setMetrics(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const createEndpoint = async () => {
    if (!newEndpoint.name || !newEndpoint.model_id) return;
    setCreating(true);
    setCreateError('');
    try {
      await serving.createEndpoint(newEndpoint);
      setShowCreate(false);
      setNewEndpoint({ name: '', model_id: '', description: '', cache_ttl_seconds: 300 });
      loadEndpoints();
    } catch (err) {
      setCreateError(formatApiError(err, 'Gagal membuat endpoint'));
    } finally {
      setCreating(false);
    }
  };

  const handlePredict = async () => {
    if (!selectedEndpoint || !predictInput) return;
    setPredictError('');
    setPredictResult(null);
    try {
      const data = JSON.parse(predictInput);
      const res = await serving.predict(selectedEndpoint, data);
      setPredictResult(res.data);
    } catch (err) {
      setPredictError(formatApiError(err, 'JSON tidak valid atau prediksi gagal'));
    }
  };

  const deleteEndpoint = async (id: string) => {
    if (!confirm('Hapus endpoint ini? Tindakan tidak dapat dibatalkan.')) return;
    await serving.delete(id);
    if (selectedEndpoint === id) { setSelectedEndpoint(null); setMetrics(null); }
    loadEndpoints();
  };

  const inputCls = 'rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white w-full focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20';

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Model Serving</h1>
          <p className="text-gray-500 dark:text-gray-400">Endpoint inferensi untuk produksi dengan caching</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" /> Endpoint Baru
        </button>
      </div>

      {loadError && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" /> {loadError}
        </div>
      )}

      {showCreate && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Buat Endpoint Baru</h2>
          {createError && (
            <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400">
              {createError}
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Nama Endpoint</label>
              <input
                placeholder="Nama endpoint..."
                value={newEndpoint.name}
                onChange={(e) => setNewEndpoint({ ...newEndpoint, name: e.target.value })}
                className={inputCls}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Model</label>
              <select
                value={newEndpoint.model_id}
                onChange={(e) => setNewEndpoint({ ...newEndpoint, model_id: e.target.value })}
                className={inputCls}
              >
                <option value="">{modelList.length === 0 ? 'Memuat model...' : 'Pilih model...'}</option>
                {modelList.map((m) => <option key={m.id} value={m.id}>{m.name} ({m.algorithm})</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Deskripsi</label>
              <input
                placeholder="Deskripsi singkat..."
                value={newEndpoint.description}
                onChange={(e) => setNewEndpoint({ ...newEndpoint, description: e.target.value })}
                className={inputCls}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Cache TTL (detik)</label>
              <input
                type="number"
                placeholder="300"
                value={newEndpoint.cache_ttl_seconds}
                onChange={(e) => setNewEndpoint({ ...newEndpoint, cache_ttl_seconds: Number(e.target.value) })}
                className={inputCls}
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={createEndpoint}
              disabled={!newEndpoint.name || !newEndpoint.model_id || creating}
              className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {creating && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />}
              Buat
            </button>
            <button
              onClick={() => { setShowCreate(false); setCreateError(''); }}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Batal
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Endpoint list */}
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Daftar Endpoint</h2>
          {loading ? <LoadingSpinner size="sm" /> : (
            <div className="space-y-2">
              {endpoints.map((ep) => (
                <div
                  key={ep.id}
                  className={`rounded-lg px-3 py-2.5 ${selectedEndpoint === ep.id ? 'bg-primary-50 dark:bg-primary-900/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}
                >
                  <button onClick={() => loadMetrics(ep.id)} className="w-full text-left">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{ep.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Cache TTL: {ep.cache_ttl_seconds}s</p>
                  </button>
                  <button
                    onClick={() => deleteEndpoint(ep.id)}
                    className="mt-1 text-red-400 hover:text-red-600"
                    aria-label="Hapus endpoint"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
              {endpoints.length === 0 && (
                <p className="text-sm text-gray-500 dark:text-gray-400">Belum ada endpoint</p>
              )}
            </div>
          )}
        </div>

        {selectedEndpoint && (
          <div className="lg:col-span-2 space-y-6">
            {/* Metrics */}
            {metrics && (
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-4">
                  <p className="text-sm text-blue-600 dark:text-blue-400">Total Request</p>
                  <p className="text-2xl font-bold text-blue-900 dark:text-blue-200">{metrics.total_requests}</p>
                </div>
                <div className="rounded-lg bg-green-50 dark:bg-green-900/20 p-4">
                  <p className="text-sm text-green-600 dark:text-green-400">Rata-rata Latensi</p>
                  <p className="text-2xl font-bold text-green-900 dark:text-green-200">{metrics.avg_latency_ms}ms</p>
                </div>
                <div className="rounded-lg bg-purple-50 dark:bg-purple-900/20 p-4">
                  <p className="text-sm text-purple-600 dark:text-purple-400">Cache Hit</p>
                  <p className="text-2xl font-bold text-purple-900 dark:text-purple-200">{metrics.cache_hits}</p>
                </div>
                <div className="rounded-lg bg-orange-50 dark:bg-orange-900/20 p-4">
                  <p className="text-sm text-orange-600 dark:text-orange-400">Tingkat Cache Hit</p>
                  <p className="text-2xl font-bold text-orange-900 dark:text-orange-200">{metrics.cache_hit_rate}%</p>
                </div>
              </div>
            )}

            {/* Test prediction */}
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Uji Prediksi</h2>
              <textarea
                placeholder='{"feature1": 1.5, "feature2": "nilai"}'
                value={predictInput}
                onChange={(e) => setPredictInput(e.target.value)}
                className="mb-3 h-24 w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 font-mono text-sm text-gray-900 dark:text-white"
              />
              {predictError && (
                <p className="mb-2 text-xs text-red-600 dark:text-red-400">{predictError}</p>
              )}
              <button
                onClick={handlePredict}
                disabled={!predictInput}
                className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
              >
                <Zap className="h-4 w-4" /> Prediksi
              </button>
              {predictResult && (
                <pre className="mt-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 p-4 text-sm text-gray-900 dark:text-white overflow-auto max-h-64">
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
