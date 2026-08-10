'use client';

import { useState, useMemo } from 'react';
import { Upload, FileSpreadsheet, Zap, RefreshCw } from 'lucide-react';

export type FieldKind = 'currency' | 'date' | 'percent' | 'number' | 'text';

const CURRENCY_KEYWORDS = ['harga', 'gaji', 'pendapatan', 'biaya', 'tagihan', 'omset', 'laba', 'revenue', 'cost', 'price', 'salary', 'income'];
const DATE_KEYWORDS     = ['tanggal', 'tgl', 'date', 'waktu', 'time', 'bulan', 'tahun'];
const PERCENT_KEYWORDS  = ['persen', 'persentase', 'percent', 'rate', 'rasio', 'ratio'];

export function detectFieldKind(name: string): FieldKind {
  const n = name.toLowerCase();
  if (DATE_KEYWORDS.some((k) => n.includes(k)))    return 'date';
  if (CURRENCY_KEYWORDS.some((k) => n.includes(k))) return 'currency';
  if (PERCENT_KEYWORDS.some((k) => n.includes(k)))  return 'percent';
  return 'text';
}

export function formatCurrency(raw: string): string {
  const digits = raw.replace(/[^\d]/g, '');
  if (!digits) return '';
  return Number(digits).toLocaleString('id-ID');
}

export function parseCurrency(formatted: string): number {
  return Number(formatted.replace(/\./g, '').replace(',', '.')) || 0;
}

export function SmartField({
  name,
  value,
  onChange,
}: {
  name: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const kind = detectFieldKind(name);
  const label = name.replace(/_/g, ' ');
  const inputCls = 'w-full rounded-lg border border-gray-300 bg-white text-sm text-gray-900 placeholder-gray-400 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-500';

  if (kind === 'date') {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
        <input
          type="date"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`${inputCls} px-3 py-2.5`}
        />
      </div>
    );
  }

  if (kind === 'currency') {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
        <div className="relative">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-medium text-gray-500 dark:text-gray-400">Rp</span>
          <input
            type="text"
            inputMode="numeric"
            value={value}
            onChange={(e) => onChange(formatCurrency(e.target.value))}
            placeholder="0"
            className={`${inputCls} py-2.5 pl-9 pr-3`}
          />
        </div>
        <p className="mt-0.5 text-xs text-gray-400">Format otomatis ribuan (contoh: 1.500.000)</p>
      </div>
    );
  }

  if (kind === 'percent') {
    return (
      <div>
        <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
        <div className="relative">
          <input
            type="number"
            min={0}
            max={100}
            step={0.1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="0 – 100"
            className={`${inputCls} py-2.5 pl-3 pr-9`}
          />
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-500 dark:text-gray-400">%</span>
        </div>
      </div>
    );
  }

  return (
    <div>
      <label className="mb-1 block text-sm font-medium capitalize text-gray-700 dark:text-gray-300">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Masukkan ${label}...`}
        className={`${inputCls} px-3 py-2.5`}
      />
    </div>
  );
}

export function SmartInputForm({
  model,
  onSubmit,
  loading,
  sampleData,
}: {
  model: {
    feature_names: string[];
    target_column: string | null;
  };
  onSubmit: (rows: Record<string, any>[]) => void;
  loading: boolean;
  sampleData?: Record<string, string>;
}) {
  const features = model.feature_names ?? [];
  const [inputMode, setInputMode] = useState<'fields' | 'csv'>('fields');
  const [fieldValues, setFieldValues] = useState<Record<string, string>>(
    () => Object.fromEntries(features.map((f) => [f, sampleData?.[f] ?? '']))
  );
  const [csvError, setCsvError] = useState('');

  useMemo(() => {
    setFieldValues(Object.fromEntries(features.map((f) => [f, sampleData?.[f] ?? ''])));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [model.feature_names?.join(',')]);

  const handleFields = () => {
    const row: Record<string, any> = {};
    features.forEach((f) => {
      const raw = fieldValues[f];
      const kind = detectFieldKind(f);
      if (kind === 'currency') {
        row[f] = parseCurrency(raw);
      } else if (kind === 'date') {
        row[f] = raw;
      } else if (raw !== '' && !isNaN(Number(raw.replace(/\./g, '').replace(',', '.')))) {
        row[f] = Number(raw.replace(/\./g, '').replace(',', '.'));
      } else {
        row[f] = raw;
      }
    });
    onSubmit([row]);
  };

  const handleCsv = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setCsvError('');
    try {
      const text = await file.text();
      const lines = text.trim().split('\n');
      const headers = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
      const rows = lines.slice(1).map((line) => {
        const vals = line.split(',').map((v) => v.trim().replace(/^"|"$/g, ''));
        const row: Record<string, any> = {};
        headers.forEach((h, i) => {
          const val = vals[i] ?? '';
          row[h] = !isNaN(Number(val)) && val !== '' ? Number(val) : val;
        });
        return row;
      });
      onSubmit(rows);
    } catch {
      setCsvError('Format CSV tidak valid. Pastikan baris pertama berisi nama kolom.');
    }
  };

  const allFilled = features.every((f) => fieldValues[f] !== '');

  const fillSample = () => {
    if (sampleData) {
      setFieldValues(sampleData);
    }
  };

  return (
    <div>
      {/* Mode toggle */}
      {features.length > 0 && (
        <div className="mb-4 flex gap-2">
          <button
            type="button"
            onClick={() => setInputMode('fields')}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              inputMode === 'fields'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
            }`}
          >
            Isi Form
          </button>
          <button
            type="button"
            onClick={() => setInputMode('csv')}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              inputMode === 'csv'
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300'
            }`}
          >
            <FileSpreadsheet className="h-3.5 w-3.5" /> Upload CSV
          </button>
        </div>
      )}

      {inputMode === 'fields' ? (
        features.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Pilih model untuk melihat kolom input yang dibutuhkan.
          </p>
        ) : (
          <>
            {sampleData && (
              <button
                type="button"
                onClick={fillSample}
                className="mb-3 inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
              >
                <RefreshCw className="h-3 w-3" /> Isi Contoh
              </button>
            )}
            <div className="space-y-3">
              {features.map((f) => (
                <SmartField
                  key={f}
                  name={f}
                  value={fieldValues[f]}
                  onChange={(v) => setFieldValues((p) => ({ ...p, [f]: v }))}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={handleFields}
              disabled={!allFilled || loading}
              className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-50"
            >
              {loading ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" /> : <Zap className="h-4 w-4" />}
              {loading ? 'Memproses...' : 'Jalankan Prediksi'}
            </button>
          </>
        )
      ) : (
        <div>
          <label
            htmlFor="csv-upload"
            className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 p-8 hover:border-primary-400 dark:border-gray-600"
          >
            <Upload className="mb-2 h-8 w-8 text-gray-400" />
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Upload file CSV</p>
            <p className="mt-1 text-xs text-gray-500">Kolom harus sesuai: {features.join(', ')}</p>
            <input id="csv-upload" type="file" accept=".csv" className="hidden" onChange={handleCsv} />
          </label>
          {csvError && (
            <p className="mt-2 flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
              {csvError}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
