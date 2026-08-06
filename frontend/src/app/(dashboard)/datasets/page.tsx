'use client';

import { useState } from 'react';
import { Upload, Trash2, Eye, Database, Download } from 'lucide-react';
import LoadingSpinner from '@/components/LoadingSpinner';
import DragDropUpload from '@/components/DragDropUpload';
import EmptyState from '@/components/EmptyState';
import ConfirmModal from '@/components/ConfirmModal';
import { datasets } from '@/lib/api';
import { useDatasets } from '@/lib/hooks';
import Link from 'next/link';

const SAMPLE_DATASETS = [
  { name: 'Iris (Klasifikasi)', file: '/samples/iris.csv', desc: '150 baris, 4 fitur, 3 kelas' },
  { name: 'Housing (Regresi)', file: '/samples/housing.csv', desc: '506 baris, 13 fitur, harga rumah' },
  { name: 'Titanic (Klasifikasi)', file: '/samples/titanic.csv', desc: '891 baris, 12 fitur, survive/tidak' },
  { name: 'Ekonomi Indonesia (Regresi)', file: '/samples/indonesia_economy.csv', desc: '34 provinsi, 7 fitur, GDP & kemiskinan' },
  { name: 'Cuaca Indonesia (Klasifikasi)', file: '/samples/indonesia_weather.csv', desc: '36 kota, 7 fitur, suhu & curah hujan' },
  { name: 'E-Commerce Indonesia (Regresi)', file: '/samples/indonesia_ecommerce.csv', desc: '27 produk, 11 fitur, harga & penjualan' },
  { name: 'UMKM Penjualan Indonesia (Regresi)', file: '/samples/indonesia_umkm_penjualan.csv', desc: '30 usaha, 14 fitur, laba & pendapatan' },
  { name: 'Nilai Siswa Indonesia (Klasifikasi)', file: '/samples/indonesia_nilai_siswa.csv', desc: '30 siswa, 9 mata pelajaran, status lulus' },
];

export default function DatasetsPage() {
  const { datasets: datasetsList, isLoading, mutate } = useDatasets();
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [formData, setFormData] = useState({ name: '', description: '', target_column: '' });
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  const handleUpload = async () => {
    if (!selectedFile || !formData.name) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('name', formData.name);
      fd.append('description', formData.description);
      fd.append('target_column', formData.target_column);
      await datasets.upload(fd);
      setSelectedFile(null);
      setFormData({ name: '', description: '', target_column: '' });
      mutate();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Gagal mengunggah file';
      alert(message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await datasets.delete(deleteTarget.id);
    setDeleteTarget(null);
    mutate();
  };

  const handleLoadSample = async (sample: typeof SAMPLE_DATASETS[0]) => {
    try {
      const resp = await fetch(sample.file);
      const blob = await resp.blob();
      const file = new File([blob], `${sample.name.toLowerCase().replace(/[^a-z]/g, '_')}.csv`, { type: 'text/csv' });

      const fd = new FormData();
      fd.append('file', file);
      fd.append('name', sample.name);
      fd.append('description', sample.desc);
      await datasets.upload(fd);
      mutate();
    } catch {
      alert('Gagal memuat dataset contoh');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dataset</h1>
          <p className="text-gray-500 dark:text-gray-400">Unggah dan kelola dataset Anda</p>
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Unggah Dataset</h2>
        <div className="grid grid-cols-1 gap-4">
          <input
            type="text"
            placeholder="Nama Dataset"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          />
          <input
            type="text"
            placeholder="Kolom Target (opsional)"
            value={formData.target_column}
            onChange={(e) => setFormData({ ...formData, target_column: e.target.value })}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          />
          <input
            type="text"
            placeholder="Deskripsi (opsional)"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-4 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
          />
          <DragDropUpload onFileSelect={setSelectedFile} disabled={uploading} />
          <button
            onClick={handleUpload}
            disabled={uploading || !selectedFile || !formData.name}
            className="flex items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
          >
            <Upload className="h-4 w-4" />
            {uploading ? 'Mengunggah...' : 'Unggah'}
          </button>
        </div>
      </div>

      {isLoading ? (
        <LoadingSpinner size="lg" className="mx-auto" />
      ) : datasetsList.length === 0 ? (
        <EmptyState
          icon={Database}
          title="Belum ada dataset"
          description="Unggah dataset pertama Anda atau coba dataset contoh untuk memulai."
          action={{ label: 'Lihat Wizard', href: '/training-wizard' }}
        />
      ) : (
        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-sm font-medium text-gray-500 dark:text-gray-400">
                <th className="px-6 py-4">Nama</th>
                <th className="px-6 py-4">Baris</th>
                <th className="px-6 py-4">Kolom</th>
                <th className="px-6 py-4">Target</th>
                <th className="px-6 py-4">Tag</th>
                <th className="px-6 py-4">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {datasetsList.map((ds) => (
                <tr key={ds.id} className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4">
                    <p className="font-medium text-gray-900 dark:text-white">{ds.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">{ds.description || 'Tanpa deskripsi'}</p>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{ds.rows_count?.toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{ds.columns_count}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-300">{ds.target_column || '-'}</td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {ds.tags?.map((tag) => (
                        <span key={tag} className="rounded bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs text-gray-600 dark:text-gray-300">{tag}</span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/datasets/${ds.id}`}
                        className="text-primary-600 hover:text-primary-800"
                      >
                        <Eye className="h-4 w-4" />
                      </Link>
                      <button
                        onClick={() => setDeleteTarget({ id: ds.id, name: ds.name })}
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        <h3 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">Dataset Contoh</h3>
        <p className="mb-4 text-xs text-gray-500">Coba platform dengan dataset siap pakai:</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {SAMPLE_DATASETS.map((sample) => (
            <button
              key={sample.name}
              onClick={() => handleLoadSample(sample)}
              className="flex items-center gap-3 rounded-lg border border-gray-200 dark:border-gray-600 p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              <Download className="h-4 w-4 text-primary-500 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900 dark:text-white">{sample.name}</p>
                <p className="text-xs text-gray-500">{sample.desc}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      <ConfirmModal
        open={!!deleteTarget}
        title="Hapus Dataset"
        message={`Anda yakin ingin menghapus "${deleteTarget?.name}"? Tindakan ini tidak dapat dibatalkan.`}
        confirmLabel="Hapus"
        danger
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
