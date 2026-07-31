'use client';

import { useEffect, useState } from 'react';
import { FlaskConical, Plus, Play, Pause, Square } from 'lucide-react';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import { abTests, models } from '@/lib/api';
import { ABTest, MLModel } from '@/types';

export default function ABTestsPage() {
  const [tests, setTests] = useState<ABTest[]>([]);
  const [modelsList, setModelsList] = useState<MLModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', model_a_id: '', model_b_id: '', traffic_split: 50 });

  const fetchData = async () => {
    try {
      const [testsRes, modelsRes] = await Promise.all([
        abTests.list(),
        models.list(),
      ]);
      setTests(testsRes.data.items);
      setModelsList(modelsRes.data.items);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async () => {
    try {
      await abTests.create(createForm);
      setShowCreate(false);
      setCreateForm({ name: '', model_a_id: '', model_b_id: '', traffic_split: 50 });
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Create failed');
    }
  };

  const handleUpdateStatus = async (id: string, status: string) => {
    try {
      await abTests.update(id, { status: status as any });
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Update failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">A/B Tests</h1>
          <p className="text-gray-500">Compare model performance with A/B testing</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
        >
          <Plus className="h-4 w-4" />
          Create A/B Test
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold">Create New A/B Test</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <input
              type="text"
              placeholder="Test Name"
              value={createForm.name}
              onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            />
            <div>
              <label className="block text-sm text-gray-500">Traffic Split: {createForm.traffic_split}% to Model B</label>
              <input
                type="range"
                min="0"
                max="100"
                value={createForm.traffic_split}
                onChange={(e) => setCreateForm({ ...createForm, traffic_split: parseInt(e.target.value) })}
                className="w-full"
              />
            </div>
            <select
              value={createForm.model_a_id}
              onChange={(e) => setCreateForm({ ...createForm, model_a_id: e.target.value })}
              className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              <option value="">Model A (Control)</option>
              {modelsList.map((m) => (
                <option key={m.id} value={m.id}>{m.name} v{m.version}</option>
              ))}
            </select>
            <select
              value={createForm.model_b_id}
              onChange={(e) => setCreateForm({ ...createForm, model_b_id: e.target.value })}
              className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
            >
              <option value="">Model B (Variant)</option>
              {modelsList.map((m) => (
                <option key={m.id} value={m.id}>{m.name} v{m.version}</option>
              ))}
            </select>
            <button
              onClick={handleCreate}
              disabled={!createForm.name || !createForm.model_a_id || !createForm.model_b_id}
              className="rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              Create
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <LoadingSpinner size="lg" className="mx-auto" />
      ) : tests.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16">
          <FlaskConical className="mb-4 h-12 w-12 text-gray-300" />
          <p className="text-gray-500">No A/B tests yet. Create your first test!</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tests.map((test) => (
            <div key={test.id} className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{test.name}</h3>
                  <p className="text-sm text-gray-500">{test.description || 'No description'}</p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={test.status} />
                  {test.status === 'draft' && (
                    <button
                      onClick={() => handleUpdateStatus(test.id, 'active')}
                      className="flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700"
                    >
                      <Play className="h-3 w-3" /> Start
                    </button>
                  )}
                  {test.status === 'active' && (
                    <button
                      onClick={() => handleUpdateStatus(test.id, 'paused')}
                      className="flex items-center gap-1 rounded-lg bg-yellow-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-yellow-700"
                    >
                      <Pause className="h-3 w-3" /> Pause
                    </button>
                  )}
                  {test.status === 'active' && (
                    <button
                      onClick={() => handleUpdateStatus(test.id, 'completed')}
                      className="flex items-center gap-1 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
                    >
                      <Square className="h-3 w-3" /> Stop
                    </button>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="rounded-lg bg-gray-50 p-3 text-center">
                  <p className="text-xs text-gray-500">Traffic Split</p>
                  <p className="text-lg font-semibold">{test.traffic_split}%</p>
                  <p className="text-xs text-gray-400">to Model B</p>
                </div>
                <div className="rounded-lg bg-blue-50 p-3 text-center">
                  <p className="text-xs text-gray-500">Model A Requests</p>
                  <p className="text-lg font-semibold text-blue-700">{test.model_a_requests}</p>
                </div>
                <div className="rounded-lg bg-green-50 p-3 text-center">
                  <p className="text-xs text-gray-500">Model B Requests</p>
                  <p className="text-lg font-semibold text-green-700">{test.model_b_requests}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
