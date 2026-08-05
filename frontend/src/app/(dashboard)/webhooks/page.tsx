'use client';

import { useState, useEffect } from 'react';
import { Bell, Plus, Trash2, ExternalLink, CheckCircle, XCircle } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { webhooksApi } from '@/lib/api';

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newWebhook, setNewWebhook] = useState({ name: '', url: '', events: '', secret: '' });
  const [selectedWebhook, setSelectedWebhook] = useState<string | null>(null);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    loadWebhooks();
  }, []);

  const loadWebhooks = async () => {
    setLoading(true);
    try {
      const res = await webhooksApi.list();
      setWebhooks(res.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const loadLogs = async (webhookId: string) => {
    setSelectedWebhook(webhookId);
    try {
      const res = await webhooksApi.logs(webhookId);
      setLogs(res.data);
    } catch (err) { console.error(err); }
  };

  const createWebhook = async () => {
    if (!newWebhook.name || !newWebhook.url) return;
    try {
      const events = newWebhook.events.split(',').map(e => e.trim()).filter(Boolean);
      await webhooksApi.create({
        name: newWebhook.name,
        url: newWebhook.url,
        events,
        secret: newWebhook.secret || undefined,
      });
      setShowCreate(false);
      setNewWebhook({ name: '', url: '', events: '', secret: '' });
      loadWebhooks();
    } catch (err) { alert('Failed to create webhook'); }
  };

  const deleteWebhook = async (id: string) => {
    if (!confirm('Delete this webhook?')) return;
    try {
      await webhooksApi.delete(id);
      loadWebhooks();
    } catch (err) { alert('Failed to delete webhook'); }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Webhooks</h1>
          <p className="text-gray-500 dark:text-gray-400">Configure event-driven HTTP callbacks</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700">
          <Plus className="h-4 w-4" /> New Webhook
        </button>
      </div>

      {showCreate && (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Create Webhook</h2>
          <div className="grid grid-cols-1 gap-4">
            <input placeholder="Webhook Name" value={newWebhook.name} onChange={e => setNewWebhook({...newWebhook, name: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
            <input placeholder="URL (https://example.com/webhook)" value={newWebhook.url} onChange={e => setNewWebhook({...newWebhook, url: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
            <input placeholder="Events (comma-separated: model.trained, model.deployed)" value={newWebhook.events} onChange={e => setNewWebhook({...newWebhook, events: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
            <input placeholder="Secret (optional, for signature verification)" value={newWebhook.secret} onChange={e => setNewWebhook({...newWebhook, secret: e.target.value})}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
          </div>
          <div className="mt-4 flex gap-2">
            <button onClick={createWebhook} className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">Create</button>
            <button onClick={() => setShowCreate(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Webhooks</h2>
          {loading ? <LoadingSpinner size="sm" /> : (
            <div className="space-y-2">
              {webhooks.map(wh => (
                <div key={wh.id} className={`rounded-lg px-3 py-2 ${selectedWebhook === wh.id ? 'bg-primary-50 dark:bg-primary-900/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}>
                  <button onClick={() => loadLogs(wh.id)} className="w-full text-left">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{wh.name}</p>
                      {wh.is_active ? <CheckCircle className="h-3 w-3 text-green-500" /> : <XCircle className="h-3 w-3 text-red-500" />}
                    </div>
                    <p className="text-xs text-gray-500 truncate">{wh.url}</p>
                  </button>
                  <button onClick={() => deleteWebhook(wh.id)} className="mt-1 text-red-500 hover:text-red-700">
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))}
              {webhooks.length === 0 && <p className="text-sm text-gray-500">No webhooks yet</p>}
            </div>
          )}
        </div>

        {selectedWebhook && (
          <div className="lg:col-span-2 space-y-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Delivery Logs</h2>
            <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-sm font-medium text-gray-500 dark:text-gray-400">
                    <th className="px-6 py-4">Event</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Duration</th>
                    <th className="px-6 py-4">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-6 py-4">
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 dark:bg-blue-900/30 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:text-blue-300">
                          <Bell className="h-3 w-3" />
                          {log.event}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1">
                          {log.success ? <CheckCircle className="h-4 w-4 text-green-500" /> : <XCircle className="h-4 w-4 text-red-500" />}
                          <span className="text-sm text-gray-700 dark:text-gray-300">{log.response_status || 'N/A'}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{log.duration_ms}ms</td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                  {logs.length === 0 && (
                    <tr><td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-500">No delivery logs yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
