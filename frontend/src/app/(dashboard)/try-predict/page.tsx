'use client';

import { useState, useMemo, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Brain, Sparkles, ArrowRight, RefreshCw, CheckCircle2,
  AlertCircle, Lightbulb, BarChart3, BookOpen,
  Rocket, Target, ArrowLeft, Loader2, Database,
  Play, Trophy, Wand2, Send
} from 'lucide-react';
import { models, experiments as experimentsApi, formatApiError } from '@/lib/api';
import { useModels, useDatasets } from '@/lib/hooks';
import { useToast } from '@/components/Toast';
import { useFunnelTracker } from '@/lib/useFunnelTracker';
import Link from 'next/link';
import { SmartInputForm } from '@/components/SmartInput';
import StatusBadge from '@/components/StatusBadge';
import { MLModel, Experiment, PredictionItem } from '@/types';

type Phase = 'select' | 'input' | 'result';

const SAMPLE_VALUES: Record<string, string> = {
  luas_bangunan: '120', luas_tanah: '200', kamar_tidur: '3', kamar_mandi: '2',
  jumlah_kamar: '3', lantai: '2', tahun: '2020', tahun_produksi: '2019',
  jarak_pusat: '5', jarak: '150', jarak_km: '150', jarak_tempuh_km: '35000',
  lama_berlangganan_bulan: '24', total_tagihan: '250000', jumlah_komplain: '2',
  frekuensi_login_per_bulan: '12', fitur_yang_digunakan: '5', perubahan_paket_6_bulan: '-1',
  ipk: '3.2', ipk_semester_terakhir: '3.5', persentase_kehadiran: '85',
  jumlah_mata_kuliah_lulus: '15', jumlah_mata_kuliah_gagal: '1', aktivitas_ekstrakulikuler: '1',
  beasiswa: '0', harga_jual: '150000', diskon_persen: '10', jumlah_iklan: '20',
  stok_tersedia: '100', penjualan_bulan_lalu: '250', bulan: '6', volume_penjualan: '300',
  jumlah_transaksi: '15', jam_transaksi: '14', lokasi_berbeda: '1',
  frekuensi_per_hari: '8', rata_rata_transaksi_bulanan: '500000', umur_akun_hari: '365',
  suhu_mesin_celsius: '200', tekanan_bar: '5', kecepatan_rpm: '1500',
  kelembaban_persen: '60', waktu_proses_menit: '25', shift_kerja: '1',
  pengalaman: '5', tahun_pengalaman: '5', tingkat_pendidikan: '3', jumlah_skill: '8',
  skor_keahlian: '75', lokasi_kota: '3', lokasi: '3', jenis_industri: '2',
  ukuran_perusahaan: '3', pendapatan_per_bulan: '8', total_utang: '20',
  jumlah_tanggungan: '2', lamanya_kerja_bulan: '48', riwayat_tepat_waktu: '85',
  jumlah_pinjaman_aktif: '2', skor_kredit: '700', jenis_bahan_bakar: '2',
  kapasitas_mesin_cc: '1500', kondisi_exterior: '4', kondisi_interior: '4', jumlah_pemilik: '2',
  warna_daun: '2', bintik_daun: '1', kondisi_akar: '1', suhu_lahan: '28',
  kelembaban_tanah: '65', curah_hujan_mingguan: '150', umur_tanaman_hari: '90',
  jumlah_penghuni: '3', luas_rumah_m2: '80', jumlah_ac: '2', jumlah_kulkas: '1',
  jam_penggunaan_tv: '5', jam_penggunaan_mesin_cuci: '3', musim: '2',
  pm25: '35', pm10: '50', suhu_celsius: '30', angin: '10', kecepatan_angin_kmh: '10',
  lalu_lintas_kendaraan: '50', industri_terdekat: '0',
  jumlah_huruf_kapital: '5', jumlah_tautan: '2', jumlah_akhir_tanda_tanya: '1',
  panjang_teks: '200', ada_kata_gratis: '0', ada_kata_klik: '0', pengirim_dikenal: '1',
  jenis_layanan: '2', berat_paket_kg: '5', kota_asal: '1', kota_tujuan: '5',
  kondisi_cuaca: '1', hari_dalam_minggu: '3', hari: '3',
  jumlah_emoji: '2', ada_kata_positif: '1', ada_kata_negatif: '0',
  rating_bintang: '4', jumlah_kalimat: '8', pola_kapital: '0',
  nama_komoditas: '1', harga_bulan_lalu: '35', persediaan_ton: '100',
  jumlah_petani: '500', inflasi_persen: '3.5', hari_libur: '0', libur: '0',
  omset_per_bulan_juta: '25', biaya_operasional_juta: '15', lama_usaha_bulan: '36',
  jumlah_karyawan: '5', jenis_usaha: '3', riwayat_kredit: '1', jaminan: '1',
  penjualan_30_hari: '200', tren_penjualan: '5', hari_libur_mendatang: '2',
  jumlah_sku: '50', lead_time_hari: '7', promo_mendatang: '0',
  ca_125: '15', cea: '2', psa: '4', hemoglobin: '13', leukosit: '7',
  trombosit: '250', kreatinin: '1', sgot_sgot_rasio: '1.2',
  booking_online: '1', event_lokasi: '0', cuaca_prediksi: '1',
  harga_kamar_rata: '500000', tren_liburan: '50',
  waktu_tunggu_menit: '10', akurasi_pesanan: '1', suhu_makanan: '60',
  rating_layanan: '4', repeat_order: '1', total_belanja: '150000',
  curah_hujan_bulan_lalu: '200', suhu_permukaan_laut: '29', kelembaban_relatif: '75',
  tekanan_udara: '1010', angin_monsum: '1', el_nino_index: '0.5',
  tinggi_badan_cm: '85', berat_badan_kg: '12', umur_bulan: '24',
  lingkar_lengan: '15', lingkar_kepala: '48', imunisasi_lengkap: '1', asi_eksklusif: '1',
  views_per_video: '5000', engagement_rate: '0.05', frekuensi_upload: '3',
  durasi_rata_video: '12', topik_konten: '5', jumlah_kolaborasi: '2',
  subscriber: '10000', views: '5000', durasi_jam: '20', jumlah_modul: '15',
  rating_instruktur: '4.5', sertifikat: '1', platform_hosting: '1',
  frekuensi_posting: '5', waktu_aktif_reguler: '1', rasio_following_followers: '0.8',
  panjang_komentar_rata: '30', ada_link_spam: '0', usia_akun_hari: '500', variasi_waktu_posting: '0.5',
  ketinggian_mdpl: '500', lintang_bujur: '50',
  rasio_lebar_tinggi_wajah: '0.75', posisi_alis: '3', bentuk_rajang: '3',
  panjang_rambut: '2', textur_kulit: '3', sudut_dahi: '3', proporsi_mata: '3',
  suhu: '28', tekstur: '3', berat: '100', ukuran: '50', bau: '2', air: '50',
  ph: '7.0', turbidity_ntu: '10', turbidity: '10', tds_ppm: '200', tds: '200',
  klorin_mg_l: '0.5', bakteri_coliform: '0', logam_berat_ppm: '0', logam: '0',
  harga_kemarin: '1000000', nilai_tukar_usd: '15500', inflasi: '3',
  suku_bunga: '6', harga_minyak: '80', indeks_saham: '6500', volume_perdagangan: '5000',
  area_opacitas_persen: '25', lokasi_lesi: '2', simetri_paru: '3',
  kontras_gambar: '3', tekstur_jaringan: '3', batas_cabang: '3', intensitas_pixel: '3',
  opacitas: '25', topik: '5',
};

function getSampleForField(name: string): string | undefined {
  const key = name.toLowerCase().replace(/[^a-z0-9_]/g, '');
  if (SAMPLE_VALUES[key]) return SAMPLE_VALUES[key];
  const lower = name.toLowerCase();
  if (lower.includes('harga')) return '500000';
  if (lower.includes('jumlah')) return '10';
  if (lower.includes('umur')) return '25';
  if (lower.includes('tahun')) return '2020';
  if (lower.includes('skor')) return '70';
  if (lower.includes('tingkat')) return '3';
  if (lower.includes('rasio')) return '0.5';
  if (lower.includes('persen') || lower.includes('percent')) return '50';
  return undefined;
}

const ID_NAME_PATTERNS = /^(no|id|num|nomor|indeks|index|idx|urut|row|no\.|no_)$/i;
const OHE_PATTERN = /^(.+)_\d+$/;

function isHiddenFeature(name: string): boolean {
  if (ID_NAME_PATTERNS.test(name.trim().replace(/\.$/, '').toLowerCase())) return true;
  if (OHE_PATTERN.test(name)) return true;
  return false;
}

export default function TryPredictPage() {
  const router = useRouter();
  const { toast } = useToast();
  const { models: modelsList, isLoading: modelsLoading } = useModels();
  const { datasets: datasetsList } = useDatasets();
  const { transition } = useFunnelTracker('try-predict');

  const [platformModels, setPlatformModels] = useState<MLModel[]>([]);

  useEffect(() => {
    models.systemList().then((res) => {
      const items = (res.data as any).items || [];
      setPlatformModels(items.filter((m: MLModel) => m.status === 'trained'));
    }).catch(() => {});
  }, []);

  const [phase, setPhase] = useState<Phase>('select');
  const [selectedModel, setSelectedModel] = useState<MLModel | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [predictionResults, setPredictionResults] = useState<any>(null);
  const [previousExperiments, setPreviousExperiments] = useState<Experiment[]>([]);
  const [loadingExperiments, setLoadingExperiments] = useState(false);
  const [inputMode, setInputMode] = useState<'form' | 'file'>('form');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [mappingReport, setMappingReport] = useState<any>(null);

  const goToPhase = (next: Phase) => {
    transition(phase, next);
    setPhase(next);
  };

  const deployableModels = useMemo(() => {
    const user = modelsList.filter((m) => m.status === 'deployed' || m.status === 'trained');
    return [...platformModels, ...user];
  }, [modelsList, platformModels]);

  const systemModels = useMemo(() => deployableModels.filter((m) => m.is_default === 1 || platformModels.some((pm) => pm.id === m.id)), [deployableModels, platformModels]);
  const userModels = useMemo(() => deployableModels.filter((m) => m.is_default !== 1 && !platformModels.some((pm) => pm.id === m.id)), [deployableModels, platformModels]);

  const loadPreviousExperiments = useCallback(async () => {
    if (!selectedModel) return;
    setLoadingExperiments(true);
    try {
      const res = await experimentsApi.list({ status: 'completed' });
      const items = (res.data as any).items || [];
      const filtered = items
        .filter((item: any) => item.model_id === selectedModel.id || item.dataset_id === (selectedModel as any).dataset_id)
        .sort((a: Experiment, b: Experiment) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 3);
      setPreviousExperiments(filtered);
    } catch {
      setPreviousExperiments([]);
    } finally {
      setLoadingExperiments(false);
    }
  }, [selectedModel]);

  useEffect(() => {
    if (phase === 'result' && selectedModel) {
      loadPreviousExperiments();
    }
  }, [phase, selectedModel, loadPreviousExperiments]);

  const handlePredict = async (rows: Record<string, any>[]) => {
    if (!selectedModel) return;
    const allFeatures = selectedModel.feature_names || [];
    const hiddenFeatures = allFeatures.filter(isHiddenFeature);
    const enrichedRows = rows.map((row) => {
      const full = { ...row };
      hiddenFeatures.forEach((f) => {
        if (!(f in full) || full[f] === '' || full[f] === undefined) {
          full[f] = 0;
        }
      });
      return full;
    });
    setPredicting(true);
    setPredictionResults(null);
    try {
      const res = await models.predict(selectedModel.id, { data: enrichedRows });
      setPredictionResults(res.data);
      goToPhase('result');
      toast('success', 'Prediksi berhasil!');
    } catch (err: unknown) {
      toast('error', formatApiError(err, 'Prediksi gagal'));
    } finally {
      setPredicting(false);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedModel || !uploadFile) return;
    setPredicting(true);
    setPredictionResults(null);
    setMappingReport(null);
    try {
      const res = await models.predictFile(selectedModel.id, uploadFile);
      setPredictionResults(res.data);
      setMappingReport(res.data.mapping_report || null);
      goToPhase('result');
      const nPreds = res.data.predictions?.length || 0;
      toast('success', `Prediksi berhasil! ${nPreds} baris diproses.`);
    } catch (err: unknown) {
      toast('error', formatApiError(err, 'Prediksi dari file gagal'));
    } finally {
      setPredicting(false);
    }
  };

  const resetAll = () => {
    setSelectedModel(null);
    setPredictionResults(null);
    setPreviousExperiments([]);
    setInputMode('form');
    setUploadFile(null);
    setMappingReport(null);
  };

  const getConfidenceLabel = (prob?: number): { text: string; color: string } => {
    if (prob === undefined) return { text: 'Tidak tersedia', color: 'gray' };
    if (prob >= 0.85) return { text: 'Sangat yakin', color: 'green' };
    if (prob >= 0.7) return { text: 'Cukup yakin', color: 'blue' };
    if (prob >= 0.5) return { text: 'Sedikit ragu', color: 'yellow' };
    return { text: 'Tidak yakin', color: 'red' };
  };

  const getHumanSummary = (pred: PredictionItem, modelMetrics: Record<string, any>): string => {
    const confidence = pred.probability;
    const accuracy = modelMetrics?.accuracy;
    const isClassification = pred.probabilities !== undefined || typeof pred.prediction === 'string';

    if (isClassification) {
      if (confidence === undefined) {
        return `Model memprediksi kategori "${pred.prediction}". Tidak ada nilai keyakinan yang tersedia untuk prediksi ini.`;
      }
      if (confidence >= 0.8) {
        return `Berdasarkan data yang Anda masukkan, model sangat yakin bahwa hasilnya adalah "${pred.prediction}" dengan keyakinan ${(confidence * 100).toFixed(1)}%. Model ini dilatih dengan akurasi ${accuracy !== undefined ? (accuracy * 100).toFixed(1) : 'N/A'}%, jadi prediksi ini cukup dapat dipercaya.`;
      }
      if (confidence >= 0.5) {
        return `Model memprediksi "${pred.prediction}" dengan keyakinan ${(confidence * 100).toFixed(1)}%. Hasil ini cukup masuk akal, namun masih ada kemungkinan hasil lain. Disarankan untuk mempertimbangkan input yang lebih detail jika memungkinkan.`;
      }
      return `Model memprediksi "${pred.prediction}" dengan keyakinan hanya ${(confidence * 100).toFixed(1)}%. Hasil ini kurang pasti — coba periksa kembali data input atau gunakan model dengan akurasi lebih tinggi.`;
    }

    const val = typeof pred.prediction === 'number' ? pred.prediction.toLocaleString('id-ID') : pred.prediction;
    const r2 = modelMetrics?.r2_score;
    if (r2 !== undefined) {
      if (r2 >= 0.8) {
        return `Model memprediksi nilai ${val}. Model ini memiliki R² sebesar ${(r2 * 100).toFixed(1)}%, artinya prediksi ini cukup akurat berdasarkan pola yang dipelajari dari data training.`;
      }
      if (r2 >= 0.5) {
        return `Model memprediksi nilai ${val}. Dengan R² ${(r2 * 100).toFixed(1)}%, prediksi ini masuk akal namun masih memiliki kesalahan yang cukup besar.`;
      }
      return `Model memprediksi nilai ${val}. Namun model ini memiliki R² ${(r2 * 100).toFixed(1)}%, artinya prediksi ini kurang dapat dipercaya. Pertimbangkan untuk melatih ulang dengan data yang lebih banyak.`;
    }
    return `Model memprediksi nilai ${val}.`;
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Coba Prediksi Sendiri</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Pilih model, masukkan data, dan lihat hasilnya dalam bahasa yang mudah dipahami
        </p>
      </div>

      {/* Phase 1: Select Model */}
      {phase === 'select' && (
        <div className="space-y-6">
          <div className="rounded-xl border border-primary-200 bg-primary-50 p-5 dark:border-primary-700 dark:bg-primary-900/20">
            <div className="flex gap-3">
              <Sparkles className="h-6 w-6 shrink-0 text-primary-600 dark:text-primary-400" />
              <div>
                <p className="text-sm font-semibold text-primary-900 dark:text-primary-200">Mulai dari sini</p>
                <p className="mt-1 text-sm text-primary-700 dark:text-primary-300">
                  Pilih model yang sudah dilatih. Jika belum ada, Anda bisa menggunakan model contoh yang sudah disediakan platform.
                </p>
              </div>
            </div>
          </div>

          {modelsLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
            </div>
          ) : deployableModels.length === 0 ? (
            <div className="rounded-xl border-2 border-dashed border-gray-300 bg-white p-8 text-center dark:border-gray-600 dark:bg-gray-800">
              <Brain className="mx-auto mb-4 h-12 w-12 text-gray-300 dark:text-gray-600" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Belum ada model siap pakai</h3>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Anda perlu melatih model terlebih dahulu sebelum bisa memprediksi. Jangan khawatir, itu mudah!
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-3">
                <Link href="/training-wizard" className="inline-flex items-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700">
                  <Wand2 className="h-4 w-4" /> Buka Training Wizard
                </Link>
                <Link href="/datasets" className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200">
                  <Database className="h-4 w-4" /> Lihat Dataset
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {systemModels.length > 0 && (
                <div>
                  <div className="mb-3 flex items-center gap-2">
                    <Trophy className="h-4 w-4 text-yellow-500" />
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Rekomendasi Pemula</h3>
                  </div>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {systemModels.map((m) => (
                      <button
                        key={m.id}
                        onClick={() => { setSelectedModel(m); goToPhase('input'); }}
                        className="rounded-xl border-2 border-primary-200 bg-white p-5 text-left transition-all hover:border-primary-400 hover:shadow-md dark:border-primary-700 dark:bg-gray-800 dark:hover:border-primary-500"
                      >
                        <div className="mb-2 flex items-center justify-between">
                          <StatusBadge status={m.status} />
                          <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-[10px] font-semibold text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300">Rekomendasi</span>
                        </div>
                        <h4 className="font-semibold text-gray-900 dark:text-white">{m.name}</h4>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{m.algorithm} v{m.version}</p>
                        <div className="mt-3 flex items-center gap-1 text-xs font-medium text-primary-600 dark:text-primary-400">
                          Coba prediksi <ArrowRight className="h-3 w-3" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {userModels.length > 0 && (
                <div>
                  {systemModels.length > 0 && (
                    <div className="mb-3 flex items-center gap-2">
                      <Brain className="h-4 w-4 text-gray-500" />
                      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Model Anda</h3>
                    </div>
                  )}
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {userModels.map((m) => (
                      <button
                        key={m.id}
                        onClick={() => { setSelectedModel(m); goToPhase('input'); }}
                        className="rounded-xl border border-gray-200 bg-white p-5 text-left transition-all hover:border-gray-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-600"
                      >
                        <div className="mb-2">
                          <StatusBadge status={m.status} />
                        </div>
                        <h4 className="font-semibold text-gray-900 dark:text-white">{m.name}</h4>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{m.algorithm} v{m.version}</p>
                        {m.target_column && (
                          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                            Target: <span className="font-medium text-gray-700 dark:text-gray-300">{m.target_column}</span>
                          </p>
                        )}
                        <div className="mt-3 flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400">
                          Pilih model <ArrowRight className="h-3 w-3" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Phase 2: Input Data */}
      {phase === 'input' && selectedModel && (
        <div className="space-y-6">
          <button
            type="button"
            onClick={() => { goToPhase('select'); setSelectedModel(null); }}
            className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <ArrowLeft className="h-4 w-4" /> Ganti model
          </button>

          <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{selectedModel.name}</h2>
              <StatusBadge status={selectedModel.status} />
            </div>

            <div className="mb-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
                <p className="text-xs text-gray-500 dark:text-gray-400">Algoritma</p>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{selectedModel.algorithm}</p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
                <p className="text-xs text-gray-500 dark:text-gray-400">Target</p>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">{selectedModel.target_column ?? '–'}</p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
                <p className="text-xs text-gray-500 dark:text-gray-400">Akurasi</p>
                <p className="text-sm font-semibold text-green-600 dark:text-green-400">
                  {selectedModel.metrics?.accuracy !== undefined ? `${(selectedModel.metrics.accuracy * 100).toFixed(1)}%` : '–'}
                </p>
              </div>
              <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700">
                <p className="text-xs text-gray-500 dark:text-gray-400">Fitur</p>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">
                  {(selectedModel.feature_names?.filter((f) => !isHiddenFeature(f)).length ?? 0)}
                  {(selectedModel.feature_names?.length ?? 0) > (selectedModel.feature_names?.filter((f) => !isHiddenFeature(f)).length ?? 0) && (
                    <span className="text-xs font-normal text-gray-400"> / {selectedModel.feature_names?.length}</span>
                  )}
                </p>
              </div>
            </div>

            {/* Input mode tabs */}
            <div className="mt-5 flex gap-1 rounded-lg bg-gray-100 p-1 dark:bg-gray-700">
              <button
                type="button"
                onClick={() => setInputMode('form')}
                className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition ${
                  inputMode === 'form'
                    ? 'bg-white text-gray-900 shadow dark:bg-gray-600 dark:text-white'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'
                }`}
              >
                Input Manual
              </button>
              <button
                type="button"
                onClick={() => setInputMode('file')}
                className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition ${
                  inputMode === 'file'
                    ? 'bg-white text-gray-900 shadow dark:bg-gray-600 dark:text-white'
                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'
                }`}
              >
                Upload File
              </button>
            </div>

            {inputMode === 'form' ? (
              <div className="mt-5">
                <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
                  <div className="flex gap-3">
                    <Lightbulb className="h-5 w-5 shrink-0 text-blue-500" />
                    <div className="text-sm text-blue-700 dark:text-blue-300">
                      <p className="font-medium">Cara mengisi</p>
                      <p className="mt-1">
                        Masukkan nilai untuk kolom yang tersedia. Kolom identitas dan encoding tersembunyi diisi otomatis. Klik <strong>Isi Contoh</strong> untuk data sampel.
                      </p>
                    </div>
                  </div>
                </div>
                {(() => {
                  const allFeatures = selectedModel.feature_names || [];
                  const visibleFeatures = allFeatures.filter((f) => !isHiddenFeature(f));
                  const hasHidden = visibleFeatures.length < allFeatures.length;
                  const visibleSample = Object.fromEntries(
                    visibleFeatures.map((f) => [f, getSampleForField(f) ?? ''])
                  );
                  return (
                    <>
                      {hasHidden && (
                        <div className="mt-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {allFeatures.length - visibleFeatures.length} kolom identitas/encoding tersembunyi (diisi otomatis oleh sistem).
                          </p>
                        </div>
                      )}
                      <div className="mt-3">
                        <SmartInputForm
                          model={{ feature_names: visibleFeatures, target_column: selectedModel.target_column }}
                          onSubmit={handlePredict}
                          loading={predicting}
                          sampleData={visibleSample}
                        />
                      </div>
                    </>
                  );
                })()}
              </div>
            ) : (
              <div className="mt-5 space-y-4">
                <div className="rounded-lg bg-blue-50 p-4 dark:bg-blue-900/20">
                  <div className="flex gap-3">
                    <Lightbulb className="h-5 w-5 shrink-0 text-blue-500" />
                    <div className="text-sm text-blue-700 dark:text-blue-300">
                      <p className="font-medium">Upload file untuk prediksi massal</p>
                      <p className="mt-1">
                        Upload file CSV atau Excel. Kolom yang cocok dengan fitur model akan digunakan otomatis. Kolom yang tidak ditemukan akan diisi 0.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border-2 border-dashed border-gray-300 bg-white p-6 text-center dark:border-gray-600 dark:bg-gray-800">
                  <Database className="mx-auto mb-3 h-10 w-10 text-gray-300 dark:text-gray-600" />
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {uploadFile ? uploadFile.name : 'Pilih file CSV atau Excel'}
                  </p>
                  <p className="mt-1 text-xs text-gray-400">
                    {uploadFile
                      ? `${(uploadFile.size / 1024).toFixed(1)} KB`
                      : 'Drag & drop atau klik untuk memilih'}
                  </p>
                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls,.json"
                    className="mt-3 block w-full text-sm text-gray-500 file:mr-3 file:rounded-lg file:border-0 file:bg-primary-50 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-primary-700 hover:file:bg-primary-100 dark:file:bg-primary-900/50 dark:file:text-primary-300"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  />
                </div>

                {selectedModel.feature_names && (
                  <div className="rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Model ini menggunakan <span className="font-medium">{selectedModel.feature_names.length}</span> fitur.
                      Pastikan file memiliki kolom yang sesuai.
                    </p>
                  </div>
                )}

                <button
                  type="button"
                  disabled={!uploadFile || predicting}
                  onClick={handleFileUpload}
                  className="w-full rounded-lg bg-primary-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {predicting ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="h-4 w-4 animate-spin" /> Memproses...
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      <Rocket className="h-4 w-4" /> Jalankan Prediksi dari File
                    </span>
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Phase 3: Results */}
      {phase === 'result' && predictionResults && selectedModel && (
        <div className="space-y-6">
          <button
            type="button"
            onClick={() => { goToPhase('input'); setPredictionResults(null); }}
            className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <ArrowLeft className="h-4 w-4" /> Prediksi lagi
          </button>

          {predictionResults.error ? (
            <div className="rounded-lg bg-red-50 p-4 dark:bg-red-900/30">
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                <p className="text-sm text-red-700 dark:text-red-300">{predictionResults.error}</p>
              </div>
            </div>
          ) : (
            <>
              {/* Mapping report from file upload */}
              {mappingReport && (
                <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 dark:border-blue-700 dark:bg-blue-900/20">
                  <div className="flex gap-3">
                    <Database className="mt-0.5 h-5 w-5 shrink-0 text-blue-500" />
                    <div className="text-sm text-blue-700 dark:text-blue-300">
                      <p className="font-semibold">Laporan File</p>
                      <p className="mt-1">{mappingReport.total_rows} baris diproses</p>
                      {mappingReport.exact_match?.length > 0 && (
                        <p className="mt-0.5">Kolom cocok: {mappingReport.exact_match.join(', ')}</p>
                      )}
                      {mappingReport.missing_columns?.length > 0 && (
                        <p className="mt-0.5 text-yellow-600 dark:text-yellow-400">
                          Kolom tidak ditemukan (diisi 0): {mappingReport.missing_columns.join(', ')}
                        </p>
                      )}
                      {mappingReport.extra_columns?.length > 0 && (
                        <p className="mt-0.5 text-gray-500">
                          Kolom diabaikan: {mappingReport.extra_columns.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Human-readable summary */}
              <div className="rounded-xl border border-green-200 bg-green-50 p-6 dark:border-green-700 dark:bg-green-900/20">
                <div className="flex gap-3">
                  <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-green-600 dark:text-green-400" />
                  <div>
                    <h3 className="text-lg font-semibold text-green-900 dark:text-green-200">Ringkasan Prediksi</h3>
                    <div className="mt-2 space-y-2">
                      {predictionResults.predictions?.map((pred: PredictionItem, i: number) => (
                        <p key={i} className="text-sm text-green-800 dark:text-green-300">
                          {getHumanSummary(pred, selectedModel.metrics)}
                        </p>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Prediction cards */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {predictionResults.predictions?.map((pred: PredictionItem, i: number) => {
                  const confidence = pred.probability ?? (pred.probabilities ? Object.values(pred.probabilities).reduce((a: number, b: number) => Math.max(a, b), 0) : undefined);
                  const confidenceInfo = getConfidenceLabel(confidence);
                  const isClassification = pred.probabilities !== undefined || typeof pred.prediction === 'string';

                  return (
                    <div key={pred.id ?? i} className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800">
                      <div className="mb-3 flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-500 dark:text-gray-400">Prediksi #{i + 1}</span>
                        {confidence !== undefined && (
                          <span className={`text-xs font-medium ${
                            confidenceInfo.color === 'green' ? 'text-green-600 dark:text-green-400' :
                            confidenceInfo.color === 'blue' ? 'text-blue-600 dark:text-blue-400' :
                            confidenceInfo.color === 'yellow' ? 'text-yellow-600 dark:text-yellow-400' :
                            'text-red-600 dark:text-red-400'
                          }`}>
                            {confidenceInfo.text} ({(confidence * 100).toFixed(1)}%)
                          </span>
                        )}
                      </div>

                      <div className={`mb-4 rounded-xl p-4 ${isClassification ? 'bg-primary-50 dark:bg-primary-900/20' : 'bg-gray-50 dark:bg-gray-700/40'}`}>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {selectedModel.target_column ? `Nilai: ${selectedModel.target_column}` : 'Hasil'}
                        </p>
                        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
                          {typeof pred.prediction === 'number' ? pred.prediction.toLocaleString('id-ID', { maximumFractionDigits: 4 }) : String(pred.prediction)}
                        </p>
                      </div>

                      {confidence !== undefined && (
                        <div className="mb-4">
                          <div className="mb-1 flex items-center justify-between text-xs">
                            <span className="text-gray-600 dark:text-gray-400">Keyakinan</span>
                            <span className="font-medium text-gray-700 dark:text-gray-300">{(confidence * 100).toFixed(1)}%</span>
                          </div>
                          <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-600">
                            <div className={`h-2 rounded-full transition-all duration-500 ${confidenceInfo.color === 'green' ? 'bg-green-500' : confidenceInfo.color === 'blue' ? 'bg-blue-500' : confidenceInfo.color === 'yellow' ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${confidence * 100}%` }} />
                          </div>
                        </div>
                      )}

                      {pred.probabilities && Object.keys(pred.probabilities).length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-gray-600 dark:text-gray-400">Distribusi Probabilitas</p>
                          {Object.entries(pred.probabilities).sort(([, a], [, b]) => b - a).map(([cls, p]) => (
                            <div key={cls}>
                              <div className="mb-0.5 flex items-center justify-between text-xs">
                                <span className="text-gray-600 dark:text-gray-400">{cls}</span>
                                <span className="font-medium text-gray-700 dark:text-gray-300">{(p * 100).toFixed(1)}%</span>
                              </div>
                              <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-600">
                                <div className="h-2 rounded-full bg-primary-500 transition-all duration-500" style={{ width: `${p * 100}%` }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Baseline comparison */}
              <BaselineComparison
                pred={predictionResults.predictions[0]}
                modelMetrics={selectedModel.metrics}
                modelAccuracy={selectedModel.metrics?.accuracy}
                previousExperiments={previousExperiments}
                loadingExperiments={loadingExperiments}
              />

              {/* Next Steps */}
              <NextSteps
                model={selectedModel}
                predictionResults={predictionResults}
                datasetsList={datasetsList}
                onNewPrediction={() => { goToPhase('input'); setPredictionResults(null); }}
                onSelectModel={() => { resetAll(); goToPhase('select'); }}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Baseline Comparison Component ──

function BaselineComparison({ pred, modelMetrics, modelAccuracy, previousExperiments, loadingExperiments }: { pred: PredictionItem; modelMetrics: Record<string, any>; modelAccuracy?: number; previousExperiments: Experiment[]; loadingExperiments: boolean }) {
  const confidence = pred.probability ?? (pred.probabilities ? Object.values(pred.probabilities).reduce((a: number, b: number) => Math.max(a, b), 0) : undefined);
  const isClassification = pred.probabilities !== undefined || typeof pred.prediction === 'string';

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
        <BarChart3 className="h-5 w-5 text-primary-600" /> Perbandingan dengan Baseline
      </h3>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {modelAccuracy !== undefined && confidence !== undefined && (
          <div className="space-y-3">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Keyakinan Prediksi vs Akurasi Training</p>
            <div className="space-y-3">
              <div>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="text-gray-600 dark:text-gray-400">Keyakinan Prediksi</span>
                  <span className="font-medium text-gray-900 dark:text-white">{(confidence * 100).toFixed(1)}%</span>
                </div>
                <div className="h-3 w-full rounded-full bg-gray-200 dark:bg-gray-600">
                  <div className="h-3 rounded-full bg-primary-500 transition-all" style={{ width: `${confidence * 100}%` }} />
                </div>
              </div>
              <div>
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="text-gray-600 dark:text-gray-400">Akurasi Training (baseline)</span>
                  <span className="font-medium text-gray-900 dark:text-white">{(modelAccuracy * 100).toFixed(1)}%</span>
                </div>
                <div className="h-3 w-full rounded-full bg-gray-200 dark:bg-gray-600">
                  <div className="h-3 rounded-full bg-gray-400 transition-all" style={{ width: `${modelAccuracy * 100}%` }} />
                </div>
              </div>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {confidence >= modelAccuracy ? 'Keyakinan prediksi Anda sebanding atau lebih tinggi dari akurasi model saat training.' : 'Keyakinan prediksi Anda lebih rendah dari akurasi model. Model mungkin kurang yakin dengan input ini.'}
            </p>
          </div>
        )}

        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Eksperimen Sebelumnya</p>
          {loadingExperiments ? (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Memuat...
            </div>
          ) : previousExperiments.length > 0 ? (
            <div className="space-y-2">
              {previousExperiments.map((exp) => (
                <div key={exp.id} className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-700">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-900 dark:text-white">{exp.name}</span>
                    <span className="text-xs text-gray-500">{new Date(exp.created_at).toLocaleDateString('id-ID')}</span>
                  </div>
                  <div className="mt-2 flex gap-3 text-xs">
                    {(exp as any).results?.metrics?.accuracy !== undefined && (
                      <span className="text-gray-600 dark:text-gray-400">
                        Akurasi: <span className="font-medium text-gray-900 dark:text-white">{((exp as any).results.metrics.accuracy * 100).toFixed(1)}%</span>
                      </span>
                    )}
                    {(exp as any).results?.metrics?.f1_macro !== undefined && (
                      <span className="text-gray-600 dark:text-gray-400">
                        F1: <span className="font-medium text-gray-900 dark:text-white">{((exp as any).results.metrics.f1_macro * 100).toFixed(1)}%</span>
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400">Belum ada eksperimen sebelumnya untuk model ini.</p>
          )}
        </div>
      </div>

      {isClassification && modelMetrics?.class_distribution && (
        <div className="mt-4 rounded-lg bg-gray-50 p-4 dark:bg-gray-700">
          <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Baseline Acak (hanya menebak kelas terbanyak)</p>
          {(() => {
            const dist: any = modelMetrics.class_distribution;
            const majorityClass = dist.majority_class;
            const majorityPct = dist.distribution[majorityClass]?.percentage ?? 0;
            return (
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400">Kelas terbanyak: {majorityClass}</span>
                    <span className="font-medium text-gray-900 dark:text-white">{majorityPct.toFixed(1)}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-gray-200 dark:bg-gray-600">
                    <div className="h-2 rounded-full bg-gray-400" style={{ width: `${majorityPct}%` }} />
                  </div>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 max-w-[200px]">
                  Jika Anda hanya menebak kelas ini secara acak, akurasi Anda sekitar {majorityPct.toFixed(1)}%.
                </p>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}

// ─── Next Steps Component ─

function NextSteps({ model, predictionResults, datasetsList, onNewPrediction, onSelectModel }: { model: MLModel; predictionResults: any; datasetsList: any[]; onNewPrediction: () => void; onSelectModel: () => void }) {
  const isClassification = predictionResults.predictions?.[0]?.probabilities !== undefined || typeof predictionResults.predictions?.[0]?.prediction === 'string';
  const accuracy = model.metrics?.accuracy;
  const hasFeedback = model.status === 'deployed';

  const suggestions: { id: string; icon: any; title: string; description: string; action?: () => void; href?: string; variant: 'primary' | 'secondary' | 'purple' }[] = [
    { id: 'try-another', icon: RefreshCw, title: 'Coba dengan data lain', description: 'Ubah nilai input dan lihat bagaimana prediksi berubah.', action: onNewPrediction, variant: 'primary' },
    { id: 'explain', icon: BookOpen, title: 'Lihat penjelasan model', description: 'Pahami alasan di balik prediksi ini.', href: `/explain?modelId=${model.id}`, variant: 'secondary' },
  ];

  if (hasFeedback) {
    suggestions.push({ id: 'feedback', icon: Send, title: 'Beri feedback', description: 'Bantu model menjadi lebih baik dengan memberikan feedback.', href: `/models/${model.id}`, variant: 'secondary' });
  }
  if (isClassification && accuracy !== undefined && accuracy >= 0.8) {
    suggestions.push({ id: 'marketplace', icon: Rocket, title: 'Publikasikan ke Marketplace', description: 'Bagikan model Anda ke komunitas.', href: '/marketplace', variant: 'purple' });
  }
  if (datasetsList.length > 0) {
    suggestions.push({ id: 'retrain', icon: Play, title: 'Latih ulang dengan dataset lain', description: 'Coba dataset yang berbeda untuk meningkatkan performa.', href: '/training-wizard', variant: 'secondary' });
  }

  const variantStyles = { primary: 'border-primary-200 bg-primary-50 hover:border-primary-300 dark:border-primary-700 dark:bg-primary-900/20', secondary: 'border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800', purple: 'border-purple-200 bg-purple-50 hover:border-purple-300 dark:border-purple-700 dark:bg-purple-900/20' };
  const iconStyles = { primary: 'bg-primary-100 text-primary-600 dark:bg-primary-900/50 dark:text-primary-400', secondary: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400', purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/50 dark:text-purple-400' };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
      <div className="mb-4 flex items-center gap-2">
        <Target className="h-5 w-5 text-primary-600" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Langkah Selanjutnya</h3>
      </div>
      <p className="mb-4 text-sm text-gray-500 dark:text-gray-400">
        Berdasarkan hasil prediksi ini, berikut adalah langkah-langkah yang bisa Anda ambil:
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {suggestions.map((s) => {
          const Icon = s.icon;
          const content = (
            <>
              <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${iconStyles[s.variant]}`}>
                <Icon className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{s.title}</h4>
                <p className="text-xs text-gray-500 dark:text-gray-400">{s.description}</p>
              </div>
              <ArrowRight className="h-4 w-4 shrink-0 text-gray-400" />
            </>
          );

          return s.action ? (
            <button key={s.id} onClick={s.action} className={`flex items-center gap-3 rounded-xl border p-4 text-left transition-all ${variantStyles[s.variant]}`}>
              {content}
            </button>
          ) : (
            <Link key={s.id} href={s.href!} className={`flex items-center gap-3 rounded-xl border p-4 transition-all ${variantStyles[s.variant]}`}>
              {content}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
