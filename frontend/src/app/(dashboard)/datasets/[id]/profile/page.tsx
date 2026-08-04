'use client';

import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, BarChart3, AlertTriangle, CheckCircle } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useDatasetProfile } from '@/lib/hooks';

export default function DatasetProfilePage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { profile, isLoading, isError } = useDatasetProfile(id);

  if (isLoading) {
    return <LoadingSpinner size="lg" className="mx-auto mt-20" />;
  }

  if (isError || !profile) {
    return (
      <div className="flex flex-col items-center justify-center mt-20">
        <p className="text-gray-500">Profile data not available</p>
        <button onClick={() => router.push(`/datasets/${id}`)} className="mt-4 text-primary-600 hover:underline">
          Back to Dataset
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <button
        onClick={() => router.push(`/datasets/${id}`)}
        className="flex items-center gap-2 text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dataset
      </button>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100">
            <BarChart3 className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Dataset Profile</h1>
            <p className="text-gray-500">Analisis lengkap dataset</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-lg bg-blue-50 p-4">
            <p className="text-sm text-blue-600">Rows</p>
            <p className="text-2xl font-bold text-blue-900">{profile.summary.rows.toLocaleString()}</p>
          </div>
          <div className="rounded-lg bg-green-50 p-4">
            <p className="text-sm text-green-600">Columns</p>
            <p className="text-2xl font-bold text-green-900">{profile.summary.columns}</p>
          </div>
          <div className="rounded-lg bg-purple-50 p-4">
            <p className="text-sm text-purple-600">Numeric</p>
            <p className="text-2xl font-bold text-purple-900">{profile.summary.numeric_columns}</p>
          </div>
          <div className="rounded-lg bg-orange-50 p-4">
            <p className="text-sm text-orange-600">Categorical</p>
            <p className="text-2xl font-bold text-orange-900">{profile.summary.categorical_columns}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Missing Values</h2>
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              {profile.missing_values.total_missing > 0 ? (
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
              ) : (
                <CheckCircle className="h-5 w-5 text-green-500" />
              )}
              <span className="text-sm font-medium">
                {profile.missing_values.total_missing} missing values ({profile.missing_values.missing_percentage}%)
              </span>
            </div>
            <p className="text-sm text-gray-500">
              {profile.missing_values.complete_rows} complete rows ({profile.missing_values.complete_rows_percentage}%)
            </p>
          </div>
          {profile.missing_values.columns_with_missing.length > 0 && (
            <div className="space-y-2">
              {profile.missing_values.columns_with_missing.map((col) => (
                <div key={col} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2">
                  <span className="text-sm text-gray-700">{col}</span>
                  <span className="text-sm font-medium text-gray-900">
                    {profile.missing_values.missing_by_column[col]?.count} ({profile.missing_values.missing_by_column[col]?.percentage}%)
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Outliers (IQR Method)</h2>
          <div className="space-y-2">
            {Object.entries(profile.outliers).map(([col, info]) => (
              <div key={col} className="rounded-lg bg-gray-50 px-3 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">{col}</span>
                  <span className={`text-sm font-medium ${info.outlier_count > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                    {info.outlier_count} outliers ({info.outlier_percentage}%)
                  </span>
                </div>
                <div className="mt-1 flex gap-4 text-xs text-gray-500">
                  <span>Q1: {info.q1}</span>
                  <span>Q3: {info.q3}</span>
                  <span>IQR: {info.iqr}</span>
                </div>
              </div>
            ))}
            {Object.keys(profile.outliers).length === 0 && (
              <p className="text-gray-500 text-sm">No numeric columns to analyze</p>
            )}
          </div>
        </div>

        {profile.class_distribution && (
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Class Distribution ({profile.class_distribution.column})
            </h2>
            <div className="mb-4 flex items-center gap-4">
              <span className="text-sm text-gray-500">{profile.class_distribution.num_classes} classes</span>
              {profile.class_distribution.is_imbalanced && (
                <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800">
                  Imbalanced (ratio: {profile.class_distribution.imbalance_ratio})
                </span>
              )}
            </div>
            <div className="space-y-3">
              {Object.entries(profile.class_distribution.distribution).map(([cls, info]) => (
                <div key={cls}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-700">{cls}</span>
                    <span className="text-sm font-medium text-gray-900">{info.count} ({info.percentage}%)</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-500 h-2 rounded-full"
                      style={{ width: `${info.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-xl border border-gray-200 bg-white p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Strong Correlations</h2>
          {profile.correlations.strong_correlations.length > 0 ? (
            <div className="space-y-2">
              {profile.correlations.strong_correlations.map((corr, i) => (
                <div key={i} className="rounded-lg bg-gray-50 px-3 py-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-700">
                      {corr.feature_1} &harr; {corr.feature_2}
                    </span>
                    <span className={`text-sm font-medium ${
                      corr.strength === 'strong_positive' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {corr.correlation}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No strong correlations (|r| &gt; 0.7) found</p>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Column Profiles</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="px-4 py-2 text-left font-medium text-gray-500">Column</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">Type</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">Unique</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">Missing</th>
                <th className="px-4 py-2 text-left font-medium text-gray-500">Stats</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(profile.column_profiles).map(([col, info]) => (
                <tr key={col} className="border-b border-gray-100">
                  <td className="px-4 py-2 font-medium text-gray-900">{col}</td>
                  <td className="px-4 py-2 text-gray-600">{info.dtype}</td>
                  <td className="px-4 py-2 text-gray-600">{info.unique_count}</td>
                  <td className="px-4 py-2 text-gray-600">
                    {info.null_count > 0 ? (
                      <span className="text-yellow-600">{info.null_count} ({info.null_percentage}%)</span>
                    ) : (
                      <span className="text-green-600">0</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-gray-600">
                    {info.statistics.mean != null
                      ? `mean: ${info.statistics.mean?.toFixed(2)}, std: ${info.statistics.std?.toFixed(2)}`
                      : info.statistics.mode
                      ? `mode: ${info.statistics.mode}`
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
