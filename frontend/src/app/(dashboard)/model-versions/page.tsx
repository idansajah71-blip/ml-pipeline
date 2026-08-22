'use client';

import { useState, useEffect } from 'react';
import { GitBranch, Tag, Upload, ArrowUp } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useToast } from '@/components/Toast';
import { modelVersions, models } from '@/lib/api';

export default function ModelVersionsPage() {
  const { toast } = useToast();
  const [modelList, setModelList] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [changelog, setChangelog] = useState('');

  useEffect(() => { loadModels(); }, []);

  const loadModels = async () => {
    try {
      const res = await models.list();
      setModelList(res.data.items || []);
    } catch (err) {
      console.error(err);
      setLoadError('Gagal memuat daftar model');
    }
    setLoading(false);
  };

  const loadVersions = async (modelId: string) => {
    setSelectedModel(modelId);
    try {
      const res = await modelVersions.listByModel(modelId);
      setVersions(res.data);
    } catch (err) { console.error(err); }
  };

  const createVersion = async () => {
    if (!selectedModel) return;
    try {
      await modelVersions.create({ model_id: selectedModel, changelog: changelog || undefined });
      setChangelog('');
      loadVersions(selectedModel);
    } catch (err) { toast('error', 'Gagal membuat versi'); }
  };

  const promoteVersion = async (versionId: string) => {
    try {
      await modelVersions.promote(versionId);
      if (selectedModel) loadVersions(selectedModel);
    } catch (err) { toast('error', 'Gagal mempromosikan versi'); }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Model Versions</h1>
        <p className="text-gray-500 dark:text-gray-400">Track model versions and lineage</p>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        {loadError && (
          <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400">
            {loadError}
          </div>
        )}
        <div className="flex gap-4">
          <select value={selectedModel} onChange={e => loadVersions(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white">
            <option value="">{loading ? 'Memuat model...' : 'Pilih model...'}</option>
            {modelList.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <input placeholder="Changelog" value={changelog} onChange={e => setChangelog(e.target.value)}
            className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
          <button onClick={createVersion} disabled={!selectedModel}
            className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50">
            <Tag className="h-4 w-4" /> New Version
          </button>
        </div>
      </div>

      {loading ? <LoadingSpinner size="lg" className="mx-auto" /> : selectedModel ? (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-sm font-medium text-gray-500 dark:text-gray-400">
                <th className="px-6 py-4">Version</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Changelog</th>
                <th className="px-6 py-4">Created</th>
                <th className="px-6 py-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {versions.map(v => (
                <tr key={v.id} className="border-b border-gray-100 dark:border-gray-700">
                  <td className="px-6 py-4 font-mono text-sm text-gray-900 dark:text-white">v{v.version_number}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      v.status === 'promoted' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                      'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                    }`}>{v.status}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{v.changelog || '-'}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{new Date(v.created_at).toLocaleString()}</td>
                  <td className="px-6 py-4">
                    {v.status !== 'promoted' && (
                      <button onClick={() => promoteVersion(v.id)} className="flex items-center gap-1 text-primary-600 hover:text-primary-800 text-sm">
                        <ArrowUp className="h-4 w-4" /> Promote
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {versions.length === 0 && (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-gray-500">No versions yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 py-16">
          <GitBranch className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-500 dark:text-gray-400">Select a model to view versions</p>
        </div>
      )}
    </div>
  );
}
