'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Bell } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { featureMonitoring } from '@/lib/api';

export default function FeatureMonitoringPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');
  const [driftCheck, setDriftCheck] = useState({ feature_name: '', current_value: '', baseline_mean: '', baseline_std: '' });
  const [driftResult, setDriftResult] = useState<any>(null);

  useEffect(() => { loadAlerts(); }, [filter]);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (filter) params.severity = filter;
      const res = await featureMonitoring.alerts(params);
      setAlerts(res.data);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const acknowledgeAlert = async (id: string) => {
    try {
      await featureMonitoring.acknowledgeAlert(id);
      loadAlerts();
    } catch (err) { alert('Failed'); }
  };

  const checkDrift = async () => {
    if (!driftCheck.feature_name || !driftCheck.current_value) return;
    try {
      const res = await featureMonitoring.checkDrift({
        feature_name: driftCheck.feature_name,
        current_value: Number(driftCheck.current_value),
        baseline_mean: Number(driftCheck.baseline_mean) || 0,
        baseline_std: Number(driftCheck.baseline_std) || 1,
      });
      setDriftResult(res.data);
      loadAlerts();
    } catch (err) { alert('Failed to check drift'); }
  };

  const severityColors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    warning: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    info: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Feature Monitoring</h1>
        <p className="text-gray-500 dark:text-gray-400">Monitor feature drift and data quality in real-time</p>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Check Feature Drift</h2>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <input placeholder="Feature Name" value={driftCheck.feature_name} onChange={e => setDriftCheck({...driftCheck, feature_name: e.target.value})}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
          <input type="number" placeholder="Current Value" value={driftCheck.current_value} onChange={e => setDriftCheck({...driftCheck, current_value: e.target.value})}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
          <input type="number" placeholder="Baseline Mean" value={driftCheck.baseline_mean} onChange={e => setDriftCheck({...driftCheck, baseline_mean: e.target.value})}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
          <input type="number" placeholder="Baseline Std" value={driftCheck.baseline_std} onChange={e => setDriftCheck({...driftCheck, baseline_std: e.target.value})}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white" />
        </div>
        <button onClick={checkDrift} className="mt-4 rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700">Check Drift</button>
        {driftResult && (
          <div className={`mt-4 rounded-lg p-4 ${driftResult.drift_detected ? 'bg-red-50 dark:bg-red-900/20' : 'bg-green-50 dark:bg-green-900/20'}`}>
            <p className={`font-medium ${driftResult.drift_detected ? 'text-red-800' : 'text-green-800'}`}>
              {driftResult.drift_detected ? `Drift Detected (z-score: ${driftResult.z_score})` : `No Drift (z-score: ${driftResult.z_score})`}
            </p>
            <p className={`text-sm ${driftResult.drift_detected ? 'text-red-600' : 'text-green-600'}`}>Severity: {driftResult.severity}</p>
          </div>
        )}
      </div>

      <div className="flex gap-4">
        {['', 'critical', 'warning', 'info'].map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${filter === f ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200'}`}>
            {f || 'All'}
          </button>
        ))}
      </div>

      {loading ? <LoadingSpinner size="lg" className="mx-auto" /> : alerts.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 py-16">
          <Bell className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-500 dark:text-gray-400">No drift alerts</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map(alert => (
            <div key={alert.id} className="flex items-center justify-between rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
              <div className="flex items-center gap-3">
                {alert.severity === 'critical' ? <AlertTriangle className="h-5 w-5 text-red-500" /> :
                 alert.severity === 'warning' ? <AlertTriangle className="h-5 w-5 text-yellow-500" /> :
                 <CheckCircle className="h-5 w-5 text-blue-500" />}
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{alert.feature_name}</p>
                  <p className="text-sm text-gray-500">{alert.drift_type} | z-score: {alert.drift_score?.toFixed(2)}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${severityColors[alert.severity] || ''}`}>{alert.severity}</span>
                {!alert.acknowledged && (
                  <button onClick={() => acknowledgeAlert(alert.id)} className="text-sm text-primary-600 hover:text-primary-800">Ack</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
