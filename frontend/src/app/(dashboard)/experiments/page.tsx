'use client';

import { useEffect, useState } from 'react';
import { FlaskConical } from 'lucide-react';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import { experiments } from '@/lib/api';
import { Experiment } from '@/types';
import { format } from 'date-fns';

export default function ExperimentsPage() {
  const [experimentsList, setExperimentsList] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Experiment | null>(null);

  useEffect(() => {
    const fetchExperiments = async () => {
      try {
        const res = await experiments.list();
        setExperimentsList(res.data.items);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchExperiments();
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Experiments</h1>
        <p className="text-gray-500">Track your model training experiments</p>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" className="mx-auto" />
      ) : experimentsList.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16">
          <FlaskConical className="mb-4 h-12 w-12 text-gray-300" />
          <p className="text-gray-500">No experiments yet. Train a model to create an experiment!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-1">
            {experimentsList.map((exp) => (
              <button
                key={exp.id}
                onClick={() => setSelected(exp)}
                className={`w-full rounded-xl border p-4 text-left transition-colors ${
                  selected?.id === exp.id
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-gray-200 bg-white hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center justify-between">
                  <p className="font-medium text-gray-900">{exp.name}</p>
                  <StatusBadge status={exp.status} />
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  {format(new Date(exp.created_at), 'MMM d, yyyy HH:mm')}
                </p>
                {exp.duration_seconds && (
                  <p className="text-xs text-gray-500">Duration: {exp.duration_seconds}s</p>
                )}
              </button>
            ))}
          </div>

          <div className="lg:col-span-2">
            {selected ? (
              <div className="rounded-xl border border-gray-200 bg-white p-6">
                <h2 className="mb-4 text-lg font-semibold">{selected.name}</h2>

                <div className="mb-4 grid grid-cols-2 gap-4">
                  <div className="rounded-lg bg-gray-50 p-3">
                    <p className="text-xs text-gray-500">Status</p>
                    <StatusBadge status={selected.status} />
                  </div>
                  <div className="rounded-lg bg-gray-50 p-3">
                    <p className="text-xs text-gray-500">Duration</p>
                    <p className="font-medium">{selected.duration_seconds || '-'}s</p>
                  </div>
                </div>

                {Object.keys(selected.parameters).length > 0 && (
                  <div className="mb-4">
                    <h3 className="mb-2 text-sm font-medium text-gray-700">Parameters</h3>
                    <pre className="overflow-auto rounded-lg bg-gray-50 p-4 text-xs">
                      {JSON.stringify(selected.parameters, null, 2)}
                    </pre>
                  </div>
                )}

                {Object.keys(selected.results).length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium text-gray-700">Results</h3>
                    <pre className="max-h-96 overflow-auto rounded-lg bg-gray-50 p-4 text-xs">
                      {JSON.stringify(selected.results, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white py-16">
                <FlaskConical className="mb-4 h-12 w-12 text-gray-300" />
                <p className="text-gray-500">Select an experiment to view details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
