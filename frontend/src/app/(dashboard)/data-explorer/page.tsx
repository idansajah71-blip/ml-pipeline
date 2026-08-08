'use client';

import { useState, useCallback } from 'react';
import {
  Search,
  Database,
  Download,
  ExternalLink,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Globe,
  FileSpreadsheet,
  Info,
  X,
} from 'lucide-react';
import { useToast } from '@/components/Toast';
import Badge from '@/components/Badge';
import { externalData, type ExternalSearchResult, type ExternalDataSource, type ExternalDataPreview, formatApiError } from '@/lib/api';

const SOURCE_BADGES: Record<string, { color: string; label: string }> = {
  bps: { color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200', label: 'BPS' },
  worldbank: { color: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200', label: 'World Bank' },
  datagoid: { color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200', label: 'data.go.id' },
};

export default function DataExplorerPage() {
  const { toast: showToast } = useToast();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ExternalSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedResult, setSelectedResult] = useState<ExternalSearchResult | null>(null);
  const [preview, setPreview] = useState<ExternalDataPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [imported, setImported] = useState<string[]>([]);
  const [sources, setSources] = useState<ExternalDataSource[]>([]);
  const [activeSource, setActiveSource] = useState<string>('');

  const loadSources = useCallback(async () => {
    try {
      const res = await externalData.sources();
      setSources(res.data);
    } catch {
      // Sources not critical for search
    }
  }, []);

  const handleSearch = useCallback(async () => {
    if (!query.trim() || query.trim().length < 2) return;
    setLoading(true);
    setResults([]);
    try {
      if (sources.length === 0) await loadSources();
      const res = await externalData.search(query.trim(), activeSource || undefined, 30);
      setResults(res.data);
      if (res.data.length === 0) {
        showToast('Tidak ada hasil ditemukan untuk pencarian ini', 'info');
      }
    } catch (err) {
      showToast(formatApiError(err, 'Gagal mencari data'), 'error');
    } finally {
      setLoading(false);
    }
  }, [query, activeSource, sources.length, loadSources, showToast]);

  const handlePreview = useCallback(async (result: ExternalSearchResult) => {
    setSelectedResult(result);
    setPreview(null);
    setPreviewLoading(true);
    try {
      const res = await externalData.preview(result.id, result.source_slug);
      setPreview(res.data);
    } catch (err) {
      showToast(formatApiError(err, 'Gagal memuat preview'), 'error');
    } finally {
      setPreviewLoading(false);
    }
  }, [showToast]);

  const handleImport = useCallback(async () => {
    if (!selectedResult || !preview) return;
    setImporting(true);
    try {
      const res = await externalData.import({
        result_id: selectedResult.id,
        source_slug: selectedResult.source_slug,
        title: selectedResult.title,
        description: selectedResult.description,
      });
      setImported((prev) => [...prev, selectedResult.id]);
      setSelectedResult(null);
      setPreview(null);
      showToast(`Dataset berhasil diimpor! ID: ${res.data.dataset_id.slice(0, 8)}...`, 'success');
    } catch (err) {
      showToast(formatApiError(err, 'Gagal mengimpor data'), 'error');
    } finally {
      setImporting(false);
    }
  }, [selectedResult, preview, showToast]);

  const getSourceBadge = (slug: string) => {
    const info = SOURCE_BADGES[slug] || { color: 'bg-gray-100 text-gray-800', label: slug.toUpperCase() };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${info.color}`}>
        <Globe className="w-3 h-3 mr-1" />
        {info.label}
      </span>
    );
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Search className="w-6 h-6 text-primary-600" />
          Cari Data Online
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Cari dataset dari sumber data resmi pemerintah dan organisasi internasional.
          Data yang ditemukan bisa langsung diimpor ke platform.
        </p>
      </div>

      {/* Source filter pills */}
      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setActiveSource('')}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
            activeSource === ''
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
          }`}
        >
          Semua Sumber
        </button>
        {sources.map((s) => (
          <button
            key={s.slug}
            onClick={() => setActiveSource(s.slug)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
              activeSource === s.slug
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
            }`}
          >
            {s.name}
            {s.requires_api_key && (
              <span className="ml-1 text-xs opacity-60">(key)</span>
            )}
          </button>
        ))}
      </div>

      {/* Search bar */}
      <div className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Cari data apa yang kamu butuhkan? (misal: harga beras, populasi, kemiskinan)"
            className="w-full pl-10 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={loading || query.trim().length < 2}
          className="px-6 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center gap-2"
        >
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Search className="w-5 h-5" />}
          Cari
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="mb-6">
          <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
            {results.length} hasil ditemukan
          </h2>
          <div className="grid gap-3">
            {results.map((r) => (
              <div
                key={r.id}
                className={`border rounded-lg p-4 cursor-pointer transition hover:shadow-md ${
                  selectedResult?.id === r.id
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-950'
                    : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600'
                } ${imported.includes(r.id) ? 'opacity-60' : ''}`}
                onClick={() => handlePreview(r)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {getSourceBadge(r.source_slug)}
                      {imported.includes(r.id) && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                          <CheckCircle2 className="w-3 h-3 mr-1" />
                          Diimpor
                        </span>
                      )}
                    </div>
                    <h3 className="font-medium text-gray-900 dark:text-white truncate">{r.title}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mt-0.5">{r.description}</p>
                  </div>
                  <div className="flex items-center gap-2 ml-4 text-xs text-gray-400">
                    {r.row_count != null && (
                      <span className="flex items-center gap-1">
                        <FileSpreadsheet className="w-3 h-3" />
                        {r.row_count.toLocaleString()} baris
                      </span>
                    )}
                    {r.source_url && (
                      <a
                        href={r.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="hover:text-primary-500"
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <Loader2 className="w-8 h-8 animate-spin mb-3" />
          <p>Mencari data dari semua sumber...</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && results.length === 0 && query.length >= 2 && (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <Database className="w-12 h-12 mb-3 opacity-50" />
          <p className="text-lg font-medium">Belum ada hasil</p>
          <p className="text-sm">Coba kata kunci lain atau ubah filter sumber</p>
        </div>
      )}

      {/* Initial state */}
      {!loading && results.length === 0 && query.length < 2 && (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400">
          <Search className="w-12 h-12 mb-3 opacity-50" />
          <p className="text-lg font-medium">Ketik kata kunci untuk mulai mencari</p>
          <p className="text-sm mt-1">Contoh: &quot;harga beras&quot;, &quot;populasi provinsi&quot;, &quot;GDP Indonesia&quot;</p>
          <div className="flex flex-wrap gap-2 mt-4 justify-center">
            {['harga beras', 'populasi', 'kemiskinan', 'inflasi', 'pendidikan'].map((s) => (
              <button
                key={s}
                onClick={() => { setQuery(s); }}
                className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {selectedResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={() => { setSelectedResult(null); setPreview(null); }}>
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            {/* Modal header */}
            <div className="flex items-start justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  {getSourceBadge(selectedResult.source_slug)}
                  {imported.includes(selectedResult.id) && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      Sudah Diimpor
                    </span>
                  )}
                </div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{selectedResult.title}</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{selectedResult.description}</p>
              </div>
              <button
                onClick={() => { setSelectedResult(null); setPreview(null); }}
                className="ml-4 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal body */}
            <div className="p-6 overflow-auto max-h-[60vh]">
              {previewLoading ? (
                <div className="flex items-center justify-center py-12 text-gray-400">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  Memuat preview data...
                </div>
              ) : preview ? (
                <div>
                  {/* Stats */}
                  <div className="flex flex-wrap gap-4 mb-4 text-sm">
                    <div className="flex items-center gap-1 text-gray-600 dark:text-gray-300">
                      <FileSpreadsheet className="w-4 h-4" />
                      {preview.row_count.toLocaleString()} baris
                    </div>
                    <div className="flex items-center gap-1 text-gray-600 dark:text-gray-300">
                      <Database className="w-4 h-4" />
                      {preview.columns.length} kolom
                    </div>
                  </div>

                  {/* License */}
                  <div className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg mb-4 text-sm text-blue-700 dark:text-blue-300">
                    <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>{preview.license}</span>
                  </div>

                  {/* Table preview */}
                  <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 dark:bg-gray-800">
                          {preview.columns.map((col) => (
                            <th key={col} className="px-3 py-2 text-left font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {preview.preview.map((row, i) => (
                          <tr key={i} className="border-t border-gray-100 dark:border-gray-800">
                            {preview.columns.map((col) => (
                              <td key={col} className="px-3 py-2 text-gray-600 dark:text-gray-400 whitespace-nowrap">
                                {row[col] != null ? String(row[col]) : '-'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-400 py-8">
                  Klik tombol di bawah untuk memuat preview
                </div>
              )}
            </div>

            {/* Modal footer */}
            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => { setSelectedResult(null); setPreview(null); }}
                className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
              >
                Tutup
              </button>
              {!imported.includes(selectedResult.id) && (
                <button
                  onClick={handleImport}
                  disabled={importing || !preview}
                  className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition flex items-center gap-2"
                >
                  {importing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4" />
                  )}
                  {importing ? 'Mengimpor...' : 'Gunakan Data Ini'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
