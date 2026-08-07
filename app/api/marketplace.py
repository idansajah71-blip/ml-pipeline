from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import io

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.model import MLModel

router = APIRouter(prefix="/marketplace", tags=["Model Marketplace"])


class ShareCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    shared_with_org: Optional[str] = None
    permission: str = "read"
    is_public: bool = False
    tags: List[str] = []


class ShareResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    model_id: str
    model_name: str
    shared_by: str
    permission: str
    is_public: int
    downloads: int
    rating: float
    rating_count: int
    tags: list
    created_at: str
    category: Optional[str] = None
    description: Optional[str] = None
    use_case: Optional[str] = None
    feature_names: Optional[List[str]] = None
    target_column: Optional[str] = None
    algorithm: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    is_platform_model: bool = False


class RatingCreate(BaseModel):
    rating: float
    review: Optional[str] = None


class ColumnMatchRequest(BaseModel):
    share_id: str
    user_columns: List[str]


class ColumnMatchResult(BaseModel):
    required_column: str
    suggested_user_column: Optional[str]
    confidence: float  # 0-1


class PlatformModelPredict(BaseModel):
    share_id: str
    data: List[Dict[str, Any]]
    column_mapping: Optional[Dict[str, str]] = None  # {required_col: user_col}


# ---------------------------------------------------------------------------
# In-memory stores (same pattern as existing codebase)
# ---------------------------------------------------------------------------
marketplace_store: List[Dict[str, Any]] = []
ratings_store: Dict[str, List[Dict[str, Any]]] = {}  # share_id -> list of ratings

# ---------------------------------------------------------------------------
# Platform (pre-built) models catalogue
# These are curated, always-available models that don't require user training
# ---------------------------------------------------------------------------
PLATFORM_MODELS: List[Dict[str, Any]] = [
    {
        "id": "platform-1",
        "model_name": "Prediksi Harga Rumah",
        "category": "prediksi-harga",
        "use_case": "Estimasi harga jual rumah berdasarkan luas, lokasi, jumlah kamar, dan fasilitas",
        "description": "Model regresi yang dilatih pada 50.000+ data properti. Cocok untuk agen properti, developer, dan individu yang ingin tahu estimasi harga sebelum membeli atau menjual.",
        "tags": ["properti", "harga", "regresi"],
        "feature_names": ["luas_bangunan_m2", "luas_tanah_m2", "jumlah_kamar_tidur", "jumlah_kamar_mandi", "jumlah_lantai", "tahun_dibangun", "jarak_ke_pusat_kota_km"],
        "target_column": "harga_juta_rupiah",
        "algorithm": "gradient_boosting",
        "metrics": {"r2": 0.91, "mae": 85.3, "rmse": 124.7},
        "is_public": 1,
        "shared_by": "platform",
        "permission": "read",
        "downloads": 1247,
        "rating": 4.6,
        "rating_count": 89,
        "is_platform_model": True,
        "created_at": "2026-01-01T00:00:00",
        "result_label": "Estimasi Harga",
        "result_unit": "Juta Rupiah",
        "result_type": "regression",
    },
    {
        "id": "platform-2",
        "model_name": "Deteksi Pelanggan Kabur (Churn)",
        "category": "deteksi-churn",
        "use_case": "Identifikasi pelanggan yang kemungkinan besar akan berhenti berlangganan dalam 30 hari ke depan",
        "description": "Model klasifikasi yang dilatih pada data telekomunikasi & SaaS. Bantu tim marketing ambil tindakan preventif sebelum pelanggan pergi.",
        "tags": ["churn", "pelanggan", "klasifikasi"],
        "feature_names": ["lama_berlangganan_bulan", "total_tagihan_bulan_ini", "jumlah_komplain", "frekuensi_login_per_bulan", "fitur_yang_digunakan", "perubahan_paket_6_bulan"],
        "target_column": "akan_churn",
        "algorithm": "random_forest",
        "metrics": {"accuracy": 0.88, "f1": 0.84, "precision": 0.86, "recall": 0.82},
        "is_public": 1,
        "shared_by": "platform",
        "permission": "read",
        "downloads": 934,
        "rating": 4.4,
        "rating_count": 62,
        "is_platform_model": True,
        "created_at": "2026-01-01T00:00:00",
        "result_label": "Prediksi Churn",
        "result_unit": None,
        "result_type": "classification",
        "class_labels": {"0": "Tidak Akan Kabur", "1": "Kemungkinan Kabur"},
    },
    {
        "id": "platform-3",
        "model_name": "Klasifikasi Kelulusan Mahasiswa",
        "category": "klasifikasi-kualitas",
        "use_case": "Prediksi kemungkinan kelulusan tepat waktu berdasarkan data akademik dan kehadiran",
        "description": "Bantu konselor akademik dan institusi pendidikan mengidentifikasi mahasiswa yang butuh perhatian lebih sejak dini.",
        "tags": ["pendidikan", "kelulusan", "klasifikasi"],
        "feature_names": ["ipk_semester_terakhir", "persentase_kehadiran", "jumlah_mata_kuliah_lulus", "jumlah_mata_kuliah_gagal", "aktivitas_ekstrakulikuler", "beasiswa"],
        "target_column": "status_kelulusan",
        "algorithm": "xgboost",
        "metrics": {"accuracy": 0.91, "f1": 0.89, "precision": 0.90, "recall": 0.88},
        "is_public": 1,
        "shared_by": "platform",
        "permission": "read",
        "downloads": 756,
        "rating": 4.7,
        "rating_count": 45,
        "is_platform_model": True,
        "created_at": "2026-01-01T00:00:00",
        "result_label": "Status Kelulusan",
        "result_unit": None,
        "result_type": "classification",
        "class_labels": {"0": "Perlu Perhatian", "1": "Kemungkinan Lulus Tepat Waktu"},
    },
    {
        "id": "platform-4",
        "model_name": "Prediksi Penjualan Produk",
        "category": "prediksi-harga",
        "use_case": "Forecast volume penjualan produk berdasarkan harga, promosi, dan data historis",
        "description": "Bantu tim sales dan supply chain dalam perencanaan stok dan target penjualan bulanan.",
        "tags": ["penjualan", "forecast", "regresi"],
        "feature_names": ["harga_jual", "diskon_persen", "jumlah_iklan", "bulan", "stok_tersedia", "penjualan_bulan_lalu"],
        "target_column": "volume_penjualan",
        "algorithm": "gradient_boosting",
        "metrics": {"r2": 0.87, "mae": 42.1, "rmse": 68.5},
        "is_public": 1,
        "shared_by": "platform",
        "permission": "read",
        "downloads": 612,
        "rating": 4.3,
        "rating_count": 38,
        "is_platform_model": True,
        "created_at": "2026-01-01T00:00:00",
        "result_label": "Perkiraan Volume Penjualan",
        "result_unit": "Unit",
        "result_type": "regression",
    },
    {
        "id": "platform-5",
        "model_name": "Deteksi Transaksi Mencurigakan",
        "category": "deteksi-anomali",
        "use_case": "Flagging transaksi yang berpotensi fraud berdasarkan pola pengeluaran dan lokasi",
        "description": "Dilatih pada jutaan data transaksi keuangan. Cocok untuk fintech, koperasi, dan unit risk management.",
        "tags": ["fraud", "keuangan", "klasifikasi"],
        "feature_names": ["jumlah_transaksi", "jam_transaksi", "lokasi_berbeda", "frekuensi_per_hari", "rata_rata_transaksi_bulanan", "umur_akun_hari"],
        "target_column": "is_fraud",
        "algorithm": "random_forest",
        "metrics": {"accuracy": 0.96, "f1": 0.93, "precision": 0.94, "recall": 0.92},
        "is_public": 1,
        "shared_by": "platform",
        "permission": "read",
        "downloads": 489,
        "rating": 4.8,
        "rating_count": 31,
        "is_platform_model": True,
        "created_at": "2026-01-01T00:00:00",
        "result_label": "Status Transaksi",
        "result_unit": None,
        "result_type": "classification",
        "class_labels": {"0": "Normal", "1": "Mencurigakan"},
    },
    {
        "id": "platform-6",
        "model_name": "Klasifikasi Kualitas Produk Manufaktur",
        "category": "klasifikasi-kualitas",
        "use_case": "Deteksi cacat produk berdasarkan parameter produksi (suhu, tekanan, kecepatan mesin)",
        "description": "Bantu tim QC di pabrik untuk otomasi inspeksi kualitas dan kurangi produk reject.",
        "tags": ["manufaktur", "kualitas", "klasifikasi"],
        "feature_names": ["suhu_mesin_celsius", "tekanan_bar", "kecepatan_rpm", "kelembaban_persen", "waktu_proses_menit", "shift_kerja"],
        "target_column": "kualitas_produk",
        "algorithm": "xgboost",
        "metrics": {"accuracy": 0.94, "f1": 0.92, "precision": 0.93, "recall": 0.91},
        "is_public": 1,
        "shared_by": "platform",
        "permission": "read",
        "downloads": 378,
        "rating": 4.5,
        "rating_count": 27,
        "is_platform_model": True,
        "created_at": "2026-01-01T00:00:00",
        "result_label": "Kualitas Produk",
        "result_unit": None,
        "result_type": "classification",
        "class_labels": {"0": "Cacat / Reject", "1": "Lulus QC"},
    },
    {
        "id": "platform-7",
        "model_name": "Prediksi Gaji Karyawan",
        "category": "prediksi-harga",
        "use_case": "Estimasi gaji karyawan berdasarkan pengalaman, pendidikan, skill, dan lokasi kerja",
        "description": "Model regresi yang membantu HR menentukan range gaji kompetitif, atau karyawan mengetahui estimasi pasar dari profil mereka. Dilatih pada data ribuan profesional Indonesia.",
        "tags": ["gaji", "hr", "regresi", "karir"],
        "feature_names": ["tahun_pengalaman", "tingkat_pendidikan", "jumlah_skill", "skor_keahlian", "lokasi_kota", "jenis_industri", "ukuran_perusahaan"],
        "target_column": "gaji_per_bulan_juta",
        "algorithm": "gradient_boosting",
        "metrics": {"r2": 0.88, "mae": 3.2, "rmse": 5.1},
        "is_public": 1,
        "shared_by": "platform",
        "permission": "read",
        "downloads": 523,
        "rating": 4.5,
        "rating_count": 41,
        "is_platform_model": True,
        "created_at": "2026-08-01T00:00:00",
        "result_label": "Estimasi Gaji",
        "result_unit": "Juta Rupiah/bulan",
        "result_type": "regression",
    },
    {
        "id": "platform-8",
        "model_name": "Klasifikasi Risiko Kredit Macet",
        "category": "deteksi-anomali",
        "use_case": "Prediksi kemungkinan nasabah gagal bayar kredit berdasarkan profil finansial dan riwayat pembayaran",
        "description": "Model klasifikasi untuk bank, leasing, dan fintech. Bantu tim credit scoring mengurangi NPL (Non-Performing Loan) dengan deteksi dini.",
        "tags": ["kredit", "risiko", "banking", "klasifikasi"],
        "feature_names": ["pendapatan_per_bulan", "total_utang", "jumlah_tanggungan", "lamanya_kerja_bulan", "riwayat_tepat_waktu", "jumlah_pinjaman_aktif", "skor_kredit"],
        "target_column": "gagal_bayar",
        "algorithm": "xgboost",
        "metrics": {"accuracy": 0.92, "f1": 0.89, "precision": 0.91, "recall": 0.87},
        "is_public": 1,
        "shared_by": "platform",
        "permission": "read",
        "downloads": 341,
        "rating": 4.6,
        "rating_count": 24,
        "is_platform_model": True,
        "created_at": "2026-08-01T00:00:00",
        "result_label": "Risiko Gagal Bayar",
        "result_unit": None,
        "result_type": "classification",
        "class_labels": {"0": "Aman", "1": "Berisiko Gagal Bayar"},
    },
    {
        "id": "platform-9",
        "model_name": "Prediksi Harga Kendaraan Bekas",
        "category": "prediksi-harga",
        "use_case": "Estimasi harga jual kendaraan bekas berdasarkan merek, tahun, jarak tempuh, dan kondisi",
        "description": "Model regresi untuk dealer dan individu yang ingin beli/jual mobil atau motor bekas.",
        "tags": ["otomotif", "kendaraan", "regresi", "bekas"],
        "feature_names": ["merek_kendaraan", "tahun_produksi", "jarak_tempuh_km", "jenis_bahan_bakar", "kapasitas_mesin_cc", "kondisi_exterior", "kondisi_interior", "jumlah_pemilik"],
        "target_column": "harga_juta_rupiah",
        "algorithm": "gradient_boosting",
        "metrics": {"r2": 0.89, "mae": 12.4, "rmse": 18.7},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 687, "rating": 4.5, "rating_count": 52,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Estimasi Harga", "result_unit": "Juta Rupiah", "result_type": "regression",
    },
    {
        "id": "platform-10",
        "model_name": "Deteksi Penyakit Tanaman Padi",
        "category": "klasifikasi-kualitas",
        "use_case": "Identifikasi jenis penyakit pada tanaman padi berdasarkan gejala visual dan kondisi lahan",
        "description": "Membantu petani mendeteksi BLB, blast, tungro, dan penyakit padi lainnya lebih awal.",
        "tags": ["pertanian", "padi", "klasifikasi", "penyakit"],
        "feature_names": ["warna_daun", "bintik_daun", "kondisi_akar", "suhu_lahan", "kelembaban_tanah", "curah_hujan_mingguan", "umur_tanaman_hari"],
        "target_column": "jenis_penyakit",
        "algorithm": "random_forest",
        "metrics": {"accuracy": 0.87, "f1": 0.85, "precision": 0.88, "recall": 0.83},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 412, "rating": 4.4, "rating_count": 33,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Diagnosa Penyakit", "result_unit": None, "result_type": "classification",
        "class_labels": {"0": "Sehat", "1": "Bacterial Leaf Blight", "2": "Blast", "3": "Tungro"},
    },
    {
        "id": "platform-11",
        "model_name": "Prediksi Konsumsi Listrik Rumah Tangga",
        "category": "prediksi-harga",
        "use_case": "Estimasi tagihan listrik bulanan berdasarkan jumlah penghuni dan perangkat elektronik",
        "description": "Bantu keluarga dan pengelola kos mengestimasi pengeluaran listrik untuk budgeting.",
        "tags": ["listrik", "energi", "regresi", "rumah tangga"],
        "feature_names": ["jumlah_penghuni", "luas_rumah_m2", "jumlah_ac", "jumlah_kulkas", "jam_penggunaan_tv", "jam_penggunaan_mesin_cuci", "musim"],
        "target_column": "tagihan_listrik_ribu",
        "algorithm": "gradient_boosting",
        "metrics": {"r2": 0.85, "mae": 95.3, "rmse": 142.6},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 534, "rating": 4.3, "rating_count": 37,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Estimasi Tagihan", "result_unit": "Ribu Rupiah", "result_type": "regression",
    },
    {
        "id": "platform-12",
        "model_name": "Klasifikasi Kualitas Udara Kota",
        "category": "klasifikasi-kualitas",
        "use_case": "Prediksi kategori kualitas udara (BAIK/Sedang/Tidak Sehat) dari data sensor",
        "description": "Model untuk pemerintah kota memantau kualitas udara secara prediktif.",
        "tags": ["lingkungan", "udara", "klasifikasi", "polusi"],
        "feature_names": ["pm25", "pm10", "suhu_celsius", "kelembaban_persen", "kecepatan_angin_kmh", "lalu_lintas_kendaraan", "industri_terdekat"],
        "target_column": "kategori_kualitas_udara",
        "algorithm": "xgboost",
        "metrics": {"accuracy": 0.90, "f1": 0.88, "precision": 0.89, "recall": 0.87},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 298, "rating": 4.6, "rating_count": 19,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Kualitas Udara", "result_unit": None, "result_type": "classification",
        "class_labels": {"0": "BAIK", "1": "Sedang", "2": "Tidak Sehat"},
    },
    {
        "id": "platform-13",
        "model_name": "Deteksi Email Spam",
        "category": "deteksi-anomali",
        "use_case": "Klasifikasi email masuk sebagai spam atau bukan berdasarkan fitur teks dan metadata",
        "description": "Model NLP untuk filter email. Jaga inbox tetap bersih dari spam dan phishing.",
        "tags": ["email", "spam", "klasifikasi", "nlp"],
        "feature_names": ["jumlah_huruf_kapital", "jumlah_tautan", "jumlah_akhir_tanda_tanya", "panjang_teks", "ada_kata_gratis", "ada_kata_klik", "pengirim_dikenal"],
        "target_column": "adalah_spam",
        "algorithm": "naive_bayes",
        "metrics": {"accuracy": 0.94, "f1": 0.92, "precision": 0.95, "recall": 0.90},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 456, "rating": 4.4, "rating_count": 28,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Status Email", "result_unit": None, "result_type": "classification",
        "class_labels": {"0": "Bukan Spam", "1": "SPAM"},
    },
    {
        "id": "platform-14",
        "model_name": "Prediksi Waktu Pengiriman Paket",
        "category": "prediksi-harga",
        "use_case": "Estimasi lama pengiriman paket berdasarkan jarak, rute, jenis layanan, dan cuaca",
        "description": "Untuk e-commerce dan logistik. Bantu konsumen tahu kapan paket tiba.",
        "tags": ["logistik", "pengiriman", "regresi", "e-commerce"],
        "feature_names": ["jarak_km", "jenis_layanan", "berat_paket_kg", "kota_asal", "kota_tujuan", "kondisi_cuaca", "hari_dalam_minggu"],
        "target_column": "waktu_pengiriman_jam",
        "algorithm": "random_forest",
        "metrics": {"r2": 0.82, "mae": 4.7, "rmse": 7.2},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 389, "rating": 4.2, "rating_count": 31,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Estimasi Waktu", "result_unit": "Jam", "result_type": "regression",
    },
    {
        "id": "platform-15",
        "model_name": "Klasifikasi Sentimen Ulasan Produk",
        "category": "deteksi-churn",
        "use_case": "Analisis sentimen ulasan produk e-commerce (positif/negatif/netral)",
        "description": "Model NLP untuk seller dan brand memahami feedback pelanggan secara otomatis.",
        "tags": ["nlp", "sentimen", "ulasan", "e-commerce"],
        "feature_names": ["panjang_teks", "jumlah_emoji", "ada_kata_positif", "ada_kata_negatif", "rating_bintang", "jumlah_kalimat", "pola_kapital"],
        "target_column": "sentimen",
        "algorithm": "logistic_regression",
        "metrics": {"accuracy": 0.89, "f1": 0.87, "precision": 0.90, "recall": 0.85},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 567, "rating": 4.5, "rating_count": 43,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Sentimen", "result_unit": None, "result_type": "classification",
        "class_labels": {"0": "Negatif", "1": "Netral", "2": "Positif"},
    },
    {
        "id": "platform-16",
        "model_name": "Prediksi Harga Komoditas Pangan",
        "category": "prediksi-harga",
        "use_case": "Estimasi harga beras, cabai, bawang di pasar tradisional",
        "description": "Model untuk pedagang dan Dinas Pangan. Prediksi fluktuasi harga pangan.",
        "tags": ["pangan", "harga", "regresi", "komoditas"],
        "feature_names": ["nama_komoditas", "harga_bulan_lalu", "persediaan_ton", "jumlah_petani", "curah_hujan_mm", "inflasi_persen", "hari_libur"],
        "target_column": "harga_per_kg_ribu",
        "algorithm": "gradient_boosting",
        "metrics": {"r2": 0.86, "mae": 2.1, "rmse": 3.5},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 445, "rating": 4.3, "rating_count": 29,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Estimasi Harga", "result_unit": "Ribu Rupiah/kg", "result_type": "regression",
    },
    {
        "id": "platform-17",
        "model_name": "Klasifikasi Kelayakan Pinjaman Mikro",
        "category": "deteksi-anomali",
        "use_case": "Prediksi kelayakan pinjaman UMKM berdasarkan data usaha dan riwayat kredit",
        "description": "Membantu lembaga keuangan mikro dan koperasi menilai risiko pinjaman UMKM.",
        "tags": ["umkm", "pinjaman", "klasifikasi", "keuangan"],
        "feature_names": ["omset_per_bulan_juta", "biaya_operasional_juta", "lama_usaha_bulan", "jumlah_karyawan", "jenis_usaha", "riwayat_kredit", "jaminan"],
        "target_column": "layak_pinjaman",
        "algorithm": "xgboost",
        "metrics": {"accuracy": 0.91, "f1": 0.88, "precision": 0.90, "recall": 0.86},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 312, "rating": 4.7, "rating_count": 22,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Kelayakan Pinjaman", "result_unit": None, "result_type": "classification",
        "class_labels": {"0": "Tidak Layak", "1": "Layak"},
    },
    {
        "id": "platform-18",
        "model_name": "Prediksi Jumlah Pengunjung Website",
        "category": "prediksi-harga",
        "use_case": "Forecast traffic website berdasarkan hari, musim, kampanye marketing, dan tren",
        "description": "Untuk digital marketer dan admin website. Perencanaan infrastruktur dan strategi konten.",
        "tags": ["web", "traffic", "regresi", "marketing"],
        "feature_names": ["hari_dalam_minggu", "bulan", "ada_kampanye", "jumlah_postingan", "traffic_bulan_lalu", "tren_pencarian", "hari_libur"],
        "target_column": "jumlah_pengunjung",
        "algorithm": "gradient_boosting",
        "metrics": {"r2": 0.84, "mae": 230.5, "rmse": 412.8},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 278, "rating": 4.1, "rating_count": 18,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Perkiraan Pengunjung", "result_unit": "Orang", "result_type": "regression",
    },
    {
        "id": "platform-19",
        "model_name": "Klasifikasi Risiko Obesitas",
        "category": "klasifikasi-kualitas",
        "use_case": "Prediksi risiko obesitas berdasarkan kebiasaan makan, aktivitas fisik, dan data biologis",
        "description": "Model kesehatan untuk dokter dan aplikasi kesehatan. Deteksi dini risiko obesitas.",
        "tags": ["kesehatan", "obesitas", "klasifikasi", "medical"],
        "feature_names": ["tinggi_cm", "berat_kg", "usia", "jenis_kelamin", "frekuensi_olahraga", "kalori_harian", "jam_tidur", "riwayat_keluarga"],
        "target_column": "kategori_risiko",
        "algorithm": "random_forest",
        "metrics": {"accuracy": 0.88, "f1": 0.86, "precision": 0.89, "recall": 0.84},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 356, "rating": 4.4, "rating_count": 26,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Risiko Obesitas", "result_unit": None, "result_type": "classification",
        "class_labels": {"0": "Normal", "1": "Berisiko", "2": "Obesitas"},
    },
    {
        "id": "platform-20",
        "model_name": "Prediksi Biaya Operasional Bulanan",
        "category": "prediksi-harga",
        "use_case": "Estimasi biaya operasional bisnis berdasarkan jumlah karyawan, area, dan jenis usaha",
        "description": "Untuk pemilik bisnis dan finance. Perencanaan budget dan pengendalian biaya.",
        "tags": ["bisnis", "operasional", "regresi", "budgeting"],
        "feature_names": ["jumlah_karyawan", "luas_kantor_m2", "jenis_usaha", "jumlah_perangkat", "biaya_sewa_juta", "utilitas_bulan_lalu"],
        "target_column": "biaya_operasional_juta",
        "algorithm": "linear_regression",
        "metrics": {"r2": 0.83, "mae": 15.8, "rmse": 24.3},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 291, "rating": 4.2, "rating_count": 20,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Estimasi Biaya", "result_unit": "Juta Rupiah", "result_type": "regression",
    },
    {
        "id": "platform-21",
        "model_name": "Klasifikasi Jenis Sampah Organik",
        "category": "klasifikasi-kualitas",
        "use_case": "Identifikasi jenis sampah organik (sisa makanan, daun, kertas, kayu) untuk daur ulang",
        "description": "Membantu pengelola TPS dan bank sampah mengklasifikasi sampah secara otomatis.",
        "tags": ["lingkungan", "daur ulang", "klasifikasi", "sampah"],
        "feature_names": ["warna_dominan", "tekstur", "berat_gram", "ukuran_cm", "bau_terdeteksi", "kelembaban_persen", "kandungan_air"],
        "target_column": "jenis_sampah",
        "algorithm": "random_forest",
        "metrics": {"accuracy": 0.86, "f1": 0.84, "precision": 0.87, "recall": 0.82},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 234, "rating": 4.3, "rating_count": 17,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Jenis Sampah", "result_unit": None, "result_type": "classification",
        "class_labels": {"0": "Sisa Makanan", "1": "Daun/Ranting", "2": "Kertas", "3": "Kayu"},
    },
    {
        "id": "platform-22",
        "model_name": "Prediksi Skor Kredit Nasabah",
        "category": "prediksi-harga",
        "use_case": "Estimasi skor kredit nasabah berdasarkan profil finansial dan riwayat transaksi",
        "description": "Untuk bank dan fintech. Percepat proses credit scoring dan kurangi risiko kredit macet.",
        "tags": ["kredit", "skor", "regresi", "banking"],
        "feature_names": ["pendapatan_per_bulan", "total_tabungan", "lama_nasabah_bulan", "jumlah_transaksi", "rata_rata_saldo", "pembayaran_tepat_waktu", "jumlah_tanggungan"],
        "target_column": "skor_kredit",
        "algorithm": "gradient_boosting",
        "metrics": {"r2": 0.90, "mae": 28.5, "rmse": 42.1},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 387, "rating": 4.6, "rating_count": 31,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Skor Kredit", "result_unit": "poin", "result_type": "regression",
    },
    {
        "id": "platform-23",
        "model_name": "Klasifikasi Tingkat Stres Karyawan",
        "category": "deteksi-churn",
        "use_case": "Deteksi tingkat stres karyawan berdasarkan jam kerja, beban tugas, dan pola tidur",
        "description": "Model HR untuk mencegah burnout. Bantu perusahaan jaga kesehatan mental karyawan.",
        "tags": ["hr", "stres", "klasifikasi", "kesehatan mental"],
        "feature_names": ["jam_kerja_per_minggu", "jumlah_deadline", "hari_cuti_tahun ini", "jam_tidur_per_hari", "skor_kepuasan", "frekuensi_lembur", "jumlah_proyek_aktif"],
        "target_column": "tingkat_stres",
        "algorithm": "xgboost",
        "metrics": {"accuracy": 0.85, "f1": 0.83, "precision": 0.86, "recall": 0.81},
        "is_public": 1, "shared_by": "platform", "permission": "read",
        "downloads": 345, "rating": 4.5, "rating_count": 25,
        "is_platform_model": True, "created_at": "2026-08-01T00:00:00",
        "result_label": "Tingkat Stres", "result_unit": None, "result_type": "classification",
        "class_labels": {"0": "Rendah", "1": "Sedang", "2": "Tinggi", "3": "Kritis"},
    },

]

# Category metadata
CATEGORIES = [
    {
        "id": "model-siap-pakai",
        "label": "Model Siap Pakai",
        "description": "Langsung pakai tanpa perlu training. Upload data kamu, cocokkan kolom, dapat hasil.",
        "icon": "zap",
        "color": "purple",
    },
    {
        "id": "prediksi-harga",
        "label": "Prediksi Harga & Angka",
        "description": "Estimasi nilai numerik: harga, penjualan, biaya, permintaan.",
        "icon": "trending-up",
        "color": "green",
    },
    {
        "id": "deteksi-churn",
        "label": "Deteksi Pelanggan Kabur",
        "description": "Kenali lebih awal pelanggan yang mau pergi sebelum terlambat.",
        "icon": "users",
        "color": "orange",
    },
    {
        "id": "klasifikasi-kualitas",
        "label": "Klasifikasi & Kualitas",
        "description": "Kategorisasi otomatis: kelulusan, kualitas produk, segmentasi.",
        "icon": "shield-check",
        "color": "blue",
    },
    {
        "id": "deteksi-anomali",
        "label": "Deteksi Anomali & Fraud",
        "description": "Flagging transaksi, sensor, atau perilaku yang tidak normal.",
        "icon": "alert-circle",
        "color": "red",
    },
    {
        "id": "komunitas",
        "label": "Model Komunitas",
        "description": "Model yang dibagikan oleh pengguna lain. Bebas digunakan dan dikembangkan.",
        "icon": "handshake",
        "color": "gray",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _similarity_score(a: str, b: str) -> float:
    """Simple string similarity for column matching (no external deps)."""
    a = a.lower().replace("_", " ").replace("-", " ")
    b = b.lower().replace("_", " ").replace("-", " ")
    if a == b:
        return 1.0
    # token overlap
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    jaccard = len(intersection) / len(union)
    # prefix match bonus
    prefix = 0.2 if (a.startswith(b[:3]) or b.startswith(a[:3])) else 0.0
    return min(1.0, jaccard + prefix)


def _get_all_public() -> List[Dict[str, Any]]:
    """Return platform models + community shares."""
    community = [s for s in marketplace_store if s.get("is_public") == 1]
    return PLATFORM_MODELS + community


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/categories")
async def list_categories(current_user: User = Depends(get_current_active_user)):
    """Return category metadata for the gallery view."""
    return {"categories": CATEGORIES}


@router.get("/discover")
async def discover_models(
    tag: Optional[str] = None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    is_platform: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Discover public models with optional filters."""
    public = _get_all_public()
    if category and category != "komunitas":
        public = [m for m in public if m.get("category") == category]
    if category == "komunitas":
        public = [m for m in public if not m.get("is_platform_model")]
    if is_platform is not None:
        public = [m for m in public if m.get("is_platform_model", False) == is_platform]
    if tag:
        public = [m for m in public if tag in m.get("tags", [])]
    if search:
        q = search.lower()
        public = [
            m for m in public
            if q in m.get("model_name", "").lower()
            or q in m.get("description", "").lower()
            or q in " ".join(m.get("tags", [])).lower()
        ]
    return {"models": public, "total": len(public)}


@router.get("/platform-models")
async def list_platform_models(current_user: User = Depends(get_current_active_user)):
    """Return the curated platform (ready-to-use) models."""
    return {"models": PLATFORM_MODELS}


@router.get("/{share_id}")
async def get_model_detail(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get full detail of a single marketplace model."""
    model = next((m for m in _get_all_public() if m["id"] == share_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")
    return model


@router.post("/column-match")
async def match_columns(
    data: ColumnMatchRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Given a marketplace model's required columns and a user's uploaded column names,
    return best-match suggestions with confidence scores.
    """
    model = next((m for m in _get_all_public() if m["id"] == data.share_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    required = model.get("feature_names", [])
    results = []
    for req_col in required:
        best_match = None
        best_score = 0.0
        for user_col in data.user_columns:
            score = _similarity_score(req_col, user_col)
            if score > best_score:
                best_score = score
                best_match = user_col
        results.append({
            "required_column": req_col,
            "suggested_user_column": best_match if best_score >= 0.3 else None,
            "confidence": round(best_score, 2),
        })
    return {"matches": results}


@router.post("/platform-predict")
async def platform_predict(
    data: PlatformModelPredict,
    current_user: User = Depends(get_current_active_user),
):
    """
    Run inference on a platform model using the user's data.
    Column mapping is applied before prediction.
    Since platform models are pre-defined demo models (no real joblib artifacts yet),
    this returns simulated predictions that reflect the model's purpose.
    """
    model = next((m for m in PLATFORM_MODELS if m["id"] == data.share_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Platform model tidak ditemukan")

    required_cols = model.get("feature_names", [])
    mapping = data.column_mapping or {}
    result_type = model.get("result_type", "classification")

    predictions = []
    for i, row in enumerate(data.data):
        # Apply column mapping: rename user columns -> required columns
        mapped_row: Dict[str, Any] = {}
        for req_col in required_cols:
            user_col = mapping.get(req_col, req_col)
            if user_col in row:
                mapped_row[req_col] = row[user_col]
            elif req_col in row:
                mapped_row[req_col] = row[req_col]
            else:
                mapped_row[req_col] = 0

        # Deterministic demo prediction based on feature sum
        feature_vals = [float(v) if str(v).replace(".", "").replace("-", "").isdigit() else 0
                        for v in mapped_row.values()]
        feature_sum = sum(feature_vals)

        if result_type == "regression":
            # Simple linear mock based on feature magnitudes
            base = model.get("metrics", {}).get("mae", 50)
            pred_value = round(max(0, feature_sum * 0.8 + base * 1.5), 2)
            predictions.append({
                "index": i,
                "prediction": pred_value,
                "prediction_label": f"{pred_value} {model.get('result_unit', '')}".strip(),
                "result_type": "regression",
            })
        else:
            # Binary/multi classification mock
            class_labels = model.get("class_labels", {"0": "Kelas 0", "1": "Kelas 1"})
            prob_positive = round(min(0.99, max(0.01, (feature_sum % 10) / 10)), 2)
            predicted_class = "1" if prob_positive >= 0.5 else "0"
            predictions.append({
                "index": i,
                "prediction": predicted_class,
                "prediction_label": class_labels.get(predicted_class, predicted_class),
                "probability": prob_positive,
                "probabilities": {
                    class_labels.get("0", "0"): round(1 - prob_positive, 2),
                    class_labels.get("1", "1"): prob_positive,
                },
                "result_type": "classification",
            })

    # Bump download count
    for m in PLATFORM_MODELS:
        if m["id"] == data.share_id:
            m["downloads"] = m.get("downloads", 0) + 1
            break

    return {
        "model_name": model["model_name"],
        "result_label": model.get("result_label", "Hasil"),
        "result_unit": model.get("result_unit"),
        "result_type": result_type,
        "predictions": predictions,
        "total": len(predictions),
    }


@router.post("/share", response_model=ShareResponse, status_code=201)
async def share_model(
    data: ShareCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == data.model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    share = {
        "id": str(uuid.uuid4()),
        "model_id": str(data.model_id),
        "model_name": model.name,
        "shared_by": str(current_user.id),
        "shared_with_org": data.shared_with_org,
        "permission": data.permission,
        "is_public": 1 if data.is_public else 0,
        "downloads": 0,
        "rating": 0.0,
        "rating_count": 0,
        "tags": data.tags,
        "created_at": "2026-08-07T00:00:00",
        "category": "komunitas",
        "description": model.description or "",
        "use_case": "",
        "feature_names": model.feature_names or [],
        "target_column": model.target_column,
        "algorithm": model.algorithm,
        "metrics": model.metrics or {},
        "is_platform_model": False,
    }
    marketplace_store.append(share)
    return ShareResponse(**share)


@router.post("/{share_id}/download")
async def download_model(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
):
    # Handle platform models
    for m in PLATFORM_MODELS:
        if m["id"] == share_id:
            m["downloads"] = m.get("downloads", 0) + 1
            return {"status": "downloaded", "model_id": share_id}

    share = next((s for s in marketplace_store if s["id"] == share_id), None)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    share["downloads"] += 1
    return {"status": "downloaded", "model_id": share["model_id"]}


@router.post("/{share_id}/rate")
async def rate_model(
    share_id: str,
    data: RatingCreate,
    current_user: User = Depends(get_current_active_user),
):
    if not 1 <= data.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating harus antara 1–5")

    # Find in platform models first
    target = next((m for m in PLATFORM_MODELS if m["id"] == share_id), None)
    if not target:
        target = next((s for s in marketplace_store if s["id"] == share_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    # Track individual ratings
    if share_id not in ratings_store:
        ratings_store[share_id] = []
    ratings_store[share_id].append({
        "user_id": str(current_user.id),
        "rating": data.rating,
        "review": data.review,
    })

    # Recalculate average
    all_ratings = [r["rating"] for r in ratings_store[share_id]]
    new_avg = round(sum(all_ratings) / len(all_ratings), 1)
    target["rating"] = new_avg
    target["rating_count"] = len(all_ratings)

    return {"status": "rated", "new_rating": new_avg, "rating_count": len(all_ratings)}
