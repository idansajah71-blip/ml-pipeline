'use client';

import { useState, useEffect } from 'react';
import { Layers, Plus, Zap } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { ensembleApi, models } from '@/lib/api';

export default function EnsemblePage() {
  const [ensembles, setEnsembles] = useState<any[]>([]);
  const [modelList, setModelList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newEnsemble, setNewEnsemble] = useState({ name: '', model_ids: [] as string[], strategy: 'voting' });
  const [predictEnsemble, setPredictEnsemble] = useState<string>('');
  const [predictInput, setPredictInput] = useState('');
  const [predictResult, setPredictResult] = useState<any>(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [ensRes, modelRes] = await Promise.all([ensembleApi.list(), models.list()]);
      setEnsembles(ensRes.data.ensembles || []);
      setModelList(modelRes.data.items || []);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const createEnsemble = async () => {
    if (!newEnsemble.name || newEnsemble.model_ids.length < 2) return;
    try {
      await ensembleApi.create(newEnsemble);
      setShowCreate(false);
      setNewEnsemble({ name: '', model_ids: [], strategy: 'voting' });
      loadData();
    } catch (err) { alert('Failed'); }
  };

  const toggleModel = (id: string) => {
    setNewEnsemble(prev => ({
      ...prev,
      model_ids: prev.model_ids.includes(id) ? prev.model_ids.filter(x => x !== id) : [...prev.model_ids, id],
    }));
  };

  const handlePredict = async () => {
    if (!predictEnsemble || !predictInput) return;
    try {
      const data = JSON.parse(predictInput);
      const res = await ensembleApi.predict(predictEnsemble, data);
      setPredictResult(res.data);
    } catch (err) { alert('Invalid JSON'); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Ensemble Model</h1>
          <p className="text-gray-500 dark:text-gray-400">Gabungkan beberapa model untuk prediksi yang lebih akurat</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700">
          <Plus className="h-4 w-4" /> Buat Ensemble
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Buat Ensemble Baru</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <input placeholder="Nama Ensemble" value={newEnsemble.name} onChange={e => setNewEnsemble({...newEnsemble, name: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
            <select value={newEnsemble.strategy} onChange={e => setNewEnsemble({...newEnsemble, strategy: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white">
              <option value="voting">Weighted Voting</option>
              <option value="averaging">Averaging</option>
            </select>
          </div>
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Pilih Model (minimal 2):</p>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
              {modelList.map(m => (
                <button key={m.id} onClick={() => toggleModel(m.id)}
                  className={`rounded-lg px-3 py-2 text-left text-sm ${newEnsemble.model_ids.includes(m.id) ? 'bg-primary-50 dark:bg-primary-900/30 border-2 border-primary-500' : 'bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100'}`}>
                  <p className="font-medium text-gray-900 dark:text-white">{m.name}</p>
                  <p className="text-xs text-gray-500">{m.algorithm}</p>
                </button>
              ))}
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={createEnsemble} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">Buat</button>
            <button onClick={() => setShowCreate(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 dark:border-gray-600 dark:text-gray-300">Batal</button>
          </div>
        </div>
      )}

      {loading ? <LoadingSpinner size="lg" className="mx-auto" /> : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Daftar Ensemble</h2>
            <div className="space-y-2">
              {ensembles.map(ens => (
                <button key={ens.id} onClick={() => setPredictEnsemble(ens.id)}
                  className={`w-full text-left rounded-lg px-4 py-3 ${predictEnsemble === ens.id ? 'bg-primary-50 dark:bg-primary-900/30 border-2 border-primary-500' : 'bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100'}`}>
                  <p className="font-medium text-gray-900 dark:text-white">{ens.name}</p>
                  <p className="text-xs text-gray-500">{ens.strategy} | {ens.model_ids.length} model</p>
                </button>
              ))}
              {ensembles.length === 0 && <p className="text-sm text-gray-500">Belum ada ensemble</p>}
            </div>
          </div>

          {predictEnsemble && (
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Uji Ensemble</h2>
              <textarea placeholder='{"feature1": 1.5}' value={predictInput} onChange={e => setPredictInput(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white h-24 font-mono mb-3" />
              <button onClick={handlePredict} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700">
                <Zap className="h-4 w-4" /> Prediksi
              </button>
              {predictResult && (
                <pre className="mt-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 p-4 text-sm overflow-auto">{JSON.stringify(predictResult, null, 2)}</pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
