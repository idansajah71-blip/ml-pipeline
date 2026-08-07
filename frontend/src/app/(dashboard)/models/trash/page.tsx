'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ArrowLeft, Trash2, RefreshCcw } from 'lucide-react';
import { useToast } from '@/components/Toast';
import LoadingSpinner from '@/components/LoadingSpinner';
import { useDeletedModels } from '@/lib/hooks';
import { models } from '@/lib/api';

export default function ModelsTrashPage() {
  const { toast } = useToast();
  const { models: deletedModels, isLoading, mutate } = useDeletedModels();
  const [restoringId, setRestoringId] = useState<string | null>(null);

  const handleRestore = async (id: string) => {
    setRestoringId(id);
    try {
      await models.restore(id);
      await mutate();
      toast('success', 'Model berhasil dipulihkan.');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Gagal memulihkan model';
      toast('error', message);
    } finally {
      setRestoringId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Sampah Model</h1>
          <p className="text-gray-500 dark:text-gray-400">Lihat model yang telah diarsipkan dan pulihkan jika diperlukan.</p>
        </div>
        <Link href="/models" className="inline-flex items-center gap-2 rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700">
          <ArrowLeft className="h-4 w-4" /> Kembali
        </Link>
      </div>

      {isLoading ? (
        <LoadingSpinner size="lg" className="mx-auto" />
      ) : deletedModels.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-10 text-center dark:border-gray-700 dark:bg-gray-800">
          <Trash2 className="mx-auto mb-4 h-10 w-10 text-gray-400" />
          <p className="text-gray-500 dark:text-gray-400">Tidak ada model yang diarsipkan saat ini.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm text-gray-600 dark:text-gray-300">
              <thead className="border-b border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400">
                <tr>
                  <th className="px-4 py-3">Nama</th>
                  <th className="px-4 py-3">Algoritma</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {deletedModels.map((model) => (
                  <tr key={model.id} className="border-b border-gray-100 dark:border-gray-700">
                    <td className="px-4 py-4 font-medium text-gray-900 dark:text-white">{model.name}</td>
                    <td className="px-4 py-4">{model.algorithm}</td>
                    <td className="px-4 py-4 text-sm text-gray-500 dark:text-gray-400">{model.status}</td>
                    <td className="px-4 py-4">
                      <button
                        onClick={() => handleRestore(model.id)}
                        disabled={restoringId === model.id}
                        className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-3 py-2 text-xs font-medium text-white hover:bg-primary-700 disabled:opacity-50"
                      >
                        <RefreshCcw className="h-3 w-3" />
                        {restoringId === model.id ? 'Memulihkan...' : 'Pulihkan'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
