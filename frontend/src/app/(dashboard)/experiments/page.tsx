'use client';

import { useState } from 'react';
import { FlaskConical, ArrowRightLeft } from 'lucide-react';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import WorkspaceTabs from '@/components/WorkspaceTabs';
import { useExperiments } from '@/lib/hooks';
import { Experiment } from '@/types';
import { format } from 'date-fns';

const EXPERIMENTS_TABS = [
  { label: 'Experiments', href: '/experiments', icon: FlaskConical },
  { label: 'Comparison', href: '/experiment-compare', icon: ArrowRightLeft },
];

export default function ExperimentsPage() {
  const { experiments: experimentsList, isLoading } = useExperiments();
  const [selected, setSelected] = useState<Experiment | null>(null);

  return (
    <div className="space-y-6">
      <WorkspaceTabs
        tabs={EXPERIMENTS_TABS}
        title="Experiments"
        description="Track and compare model training experiments"
      />

      {isLoading ? (
        <LoadingSpinner size="lg" className="mx-auto" />
      ) : experimentsList.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16 dark:border-gray-600">
          <FlaskConical className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
          <p className="text-gray-500 dark:text-gray-400">No experiments yet. Train a model to create an experiment!</p>
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
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                    : 'border-gray-200 bg-white hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <p className="font-medium text-gray-900 dark:text-white">{exp.name}</p>
                  <StatusBadge status={exp.status} />
                </div>
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {format(new Date(exp.created_at), 'MMM d, yyyy HH:mm')}
                </p>
                {exp.duration_seconds && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">Duration: {exp.duration_seconds}s</p>
                )}
              </button>
            ))}
          </div>

          <div className="lg:col-span-2">
            {selected ? (
              <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
                <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">{selected.name}</h2>

                <div className="mb-4 grid grid-cols-2 gap-4">
                  <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Status</p>
                    <StatusBadge status={selected.status} />
                  </div>
                  <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">Duration</p>
                    <p className="font-medium text-gray-900 dark:text-white">{selected.duration_seconds || '-'}s</p>
                  </div>
                </div>

                {Object.keys(selected.parameters).length > 0 && (
                  <div className="mb-4">
                    <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Parameters</h3>
                    <pre className="overflow-auto rounded-lg bg-gray-50 p-4 text-xs dark:bg-gray-700 dark:text-gray-300">
                      {JSON.stringify(selected.parameters, null, 2)}
                    </pre>
                  </div>
                )}

                {Object.keys(selected.results).length > 0 && (
                  <div>
                    <h3 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">Results</h3>
                    <pre className="max-h-96 overflow-auto rounded-lg bg-gray-50 p-4 text-xs dark:bg-gray-700 dark:text-gray-300">
                      {JSON.stringify(selected.results, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white py-16 dark:border-gray-700 dark:bg-gray-800">
                <FlaskConical className="mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
                <p className="text-gray-500 dark:text-gray-400">Select an experiment to view details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
