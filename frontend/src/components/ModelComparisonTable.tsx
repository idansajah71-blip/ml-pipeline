'use client';

import StatusBadge from './StatusBadge';
import { MLModel } from '@/types';
import clsx from 'clsx';

interface ModelComparisonTableProps {
  models: MLModel[];
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
}

const METRIC_KEYS = ['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc'];

export default function ModelComparisonTable({ models, selectedIds, onToggleSelect }: ModelComparisonTableProps) {
  const selectedModels = models.filter((m) => selectedIds.includes(m.id));

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50">
            <th className="px-4 py-3 text-left font-medium text-gray-600">Model</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Algorithm</th>
            <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
            {METRIC_KEYS.map((key) => (
              <th key={key} className="px-4 py-3 text-right font-medium text-gray-600">
                {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </th>
            ))}
            <th className="px-4 py-3 text-center font-medium text-gray-600">Select</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => {
            const isSelected = selectedIds.includes(model.id);
            return (
              <tr
                key={model.id}
                className={clsx(
                  'border-b border-gray-100 transition-colors',
                  isSelected ? 'bg-primary-50' : 'hover:bg-gray-50'
                )}
              >
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-900">{model.name}</p>
                  <p className="text-xs text-gray-500">v{model.version}</p>
                </td>
                <td className="px-4 py-3 text-gray-600">{model.algorithm}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={model.status} />
                </td>
                {METRIC_KEYS.map((key) => (
                  <td key={key} className="px-4 py-3 text-right text-gray-600">
                    {model.metrics?.[key] !== undefined
                      ? `${(model.metrics[key] * 100).toFixed(1)}%`
                      : '-'}
                  </td>
                ))}
                <td className="px-4 py-3 text-center">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => onToggleSelect(model.id)}
                    className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {selectedModels.length > 1 && (
        <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
          <p className="text-sm text-gray-600">
            Comparing {selectedModels.length} models:{' '}
            {selectedModels.map((m) => m.name).join(' vs ')}
          </p>
        </div>
      )}
    </div>
  );
}
