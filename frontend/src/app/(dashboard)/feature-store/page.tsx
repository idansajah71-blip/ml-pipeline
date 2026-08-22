'use client';

import { useState, useEffect } from 'react';
import { Database, Plus, Upload, Download, Trash2 } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useToast } from '@/components/Toast';
import DragDropUpload from '@/components/DragDropUpload';
import { featureStore } from '@/lib/api';

export default function FeatureStorePage() {
  const { toast } = useToast();
  const [groups, setGroups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newGroup, setNewGroup] = useState({ name: '', description: '', tags: '' });
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [features, setFeatures] = useState<any[]>([]);
  const [newFeature, setNewFeature] = useState({ name: '', data_type: 'float', description: '' });
  const [ingestData, setIngestData] = useState({ row_key: '', features: '' });
  const [lookupKey, setLookupKey] = useState('');
  const [lookupResult, setLookupResult] = useState<any>(null);

  useEffect(() => { loadGroups(); }, []);

  const loadGroups = async () => {
    setLoading(true);
    try {
      const res = await featureStore.listGroups();
      setGroups(res.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const loadFeatures = async (groupId: string) => {
    setSelectedGroup(groupId);
    try {
      const res = await featureStore.listFeatures(groupId);
      setFeatures(res.data);
    } catch (err) { console.error(err); }
  };

  const createGroup = async () => {
    if (!newGroup.name) return;
    try {
      await featureStore.createGroup({
        name: newGroup.name,
        description: newGroup.description,
        tags: newGroup.tags ? newGroup.tags.split(',').map(t => t.trim()) : [],
      });
      setShowCreate(false);
      setNewGroup({ name: '', description: '', tags: '' });
      loadGroups();
    } catch (err) { toast('error', 'Gagal membuat grup'); }
  };

  const addFeature = async () => {
    if (!selectedGroup || !newFeature.name) return;
    try {
      await featureStore.addFeature(selectedGroup, newFeature);
      setNewFeature({ name: '', data_type: 'float', description: '' });
      loadFeatures(selectedGroup);
    } catch (err) { toast('error', 'Gagal menambahkan fitur'); }
  };

  const ingestFeatures = async () => {
    if (!selectedGroup || !ingestData.row_key) return;
    try {
      const featuresObj = JSON.parse(ingestData.features);
      await featureStore.ingest(selectedGroup, { row_key: ingestData.row_key, features: featuresObj });
      setIngestData({ row_key: '', features: '' });
      toast('success', 'Fitur berhasil diingest');
    } catch (err) { toast('error', 'JSON tidak valid atau gagal mengingest'); }
  };

  const lookupFeatures = async () => {
    if (!selectedGroup || !lookupKey) return;
    try {
      const res = await featureStore.get(selectedGroup, lookupKey);
      setLookupResult(res.data);
    } catch (err) { setLookupResult(null); toast('error', 'Fitur tidak ditemukan'); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Feature Store</h1>
          <p className="text-gray-500 dark:text-gray-400">Manage features for ML models</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" /> New Group
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Create Feature Group</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <input placeholder="Group Name" value={newGroup.name} onChange={e => setNewGroup({...newGroup, name: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
            <input placeholder="Description" value={newGroup.description} onChange={e => setNewGroup({...newGroup, description: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
            <input placeholder="Tags (comma separated)" value={newGroup.tags} onChange={e => setNewGroup({...newGroup, tags: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={createGroup} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">Create</button>
            <button onClick={() => setShowCreate(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Feature Groups</h2>
          {loading ? <LoadingSpinner size="sm" /> : (
            <div className="space-y-2">
              {groups.map((g) => (
                <button key={g.id} onClick={() => loadFeatures(g.id)}
                  className={`w-full text-left rounded-lg px-3 py-2 text-sm ${selectedGroup === g.id ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700' : 'hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300'}`}>
                  <p className="font-medium">{g.name}</p>
                  <p className="text-xs text-gray-500">{g.tags?.length || 0} tags</p>
                </button>
              ))}
              {groups.length === 0 && <p className="text-sm text-gray-500">No feature groups yet</p>}
            </div>
          )}
        </div>

        {selectedGroup && (
          <div className="space-y-6">
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Features</h2>
              <div className="space-y-2 mb-4">
                {features.map((f) => (
                  <div key={f.id} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-gray-700/50 px-3 py-2">
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{f.name}</p>
                      <p className="text-xs text-gray-500">{f.data_type}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <input placeholder="Feature name" value={newFeature.name} onChange={e => setNewFeature({...newFeature, name: e.target.value})}
                  className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white" />
                <select value={newFeature.data_type} onChange={e => setNewFeature({...newFeature, data_type: e.target.value})}
                  className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white">
                  <option value="float">float</option>
                  <option value="int">int</option>
                  <option value="string">string</option>
                  <option value="bool">bool</option>
                </select>
                <button onClick={addFeature} className="rounded-lg bg-primary-600 px-3 py-2 text-sm text-white hover:bg-primary-700">Add</button>
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Ingest Features</h2>
              <div className="space-y-3">
                <input placeholder="Row Key" value={ingestData.row_key} onChange={e => setIngestData({...ingestData, row_key: e.target.value})}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
                <textarea placeholder='{"feature1": 1.5, "feature2": "value"}' value={ingestData.features} onChange={e => setIngestData({...ingestData, features: e.target.value})}
                  className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white h-24 font-mono" />
                <button onClick={ingestFeatures} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700">
                  <Upload className="h-4 w-4" /> Ingest
                </button>
              </div>
            </div>

            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Lookup</h2>
              <div className="flex gap-2 mb-3">
                <input placeholder="Row Key" value={lookupKey} onChange={e => setLookupKey(e.target.value)}
                  className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
                <button onClick={lookupFeatures} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2 text-sm text-white hover:bg-primary-700">
                  <Download className="h-4 w-4" /> Lookup
                </button>
              </div>
              {lookupResult && (
                <pre className="rounded-lg bg-gray-50 dark:bg-gray-700/50 p-4 text-sm text-gray-900 dark:text-white overflow-auto">
                  {JSON.stringify(lookupResult, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
