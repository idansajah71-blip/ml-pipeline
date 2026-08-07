"""
Train real ML models for all 40 platform marketplace models.
Saves joblib artifacts to models/platform/ directory.
Run once: python scripts/train_platform_models.py
"""
import os
import sys
import json
import numpy as np
import joblib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier, RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error, accuracy_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)
N_SAMPLES = 1000
MODELS_DIR = Path(__file__).resolve().parent.parent / "models" / "platform"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def gen_regression(n, feature_ranges, target_fn, noise_std=0.1):
    """Generate regression data with realistic noise."""
    X = []
    for low, high in feature_ranges:
        X.append(np.random.uniform(low, high, n))
    X = np.column_stack(X)
    y = target_fn(X) + np.random.normal(0, noise_std * np.std(target_fn(X)), n)
    return X, y


def gen_classification(n, feature_ranges, decision_fn, noise=0.05):
    """Generate classification data."""
    X = []
    for spec in feature_ranges:
        if isinstance(spec, tuple) and len(spec) == 2:
            X.append(np.random.uniform(spec[0], spec[1], n))
        else:
            X.append(np.random.choice(spec, n))
    X = np.column_stack(X)
    y = decision_fn(X) ^ (np.random.random(n) < noise).astype(int)
    return X, y


def train_and_save(name, model, X, y, feature_names, is_regression, metrics_extra=None):
    """Train model, evaluate, save as joblib."""
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    info = {"features": feature_names, "is_regression": is_regression}

    if is_regression:
        info["metrics"] = {
            "r2": round(r2_score(y_test, y_pred), 4),
            "mae": round(mean_absolute_error(y_test, y_pred), 2),
            "rmse": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 2),
        }
    else:
        info["metrics"] = {
            "accuracy": round(accuracy_score(y_test, y_pred), 4),
            "f1": round(f1_score(y_test, y_pred, average='weighted'), 4),
            "precision": round(precision_score(y_test, y_pred, average='weighted', zero_division=0), 4),
            "recall": round(recall_score(y_test, y_pred, average='weighted'), 4),
        }
        if metrics_extra:
            info["metrics"].update(metrics_extra)

    joblib.dump(model, MODELS_DIR / f"{name}.joblib")
    with open(MODELS_DIR / f"{name}_meta.json", "w") as f:
        json.dump(info, f)

    m = info["metrics"]
    if is_regression:
        print(f"  {name}: R2={m['r2']:.3f} MAE={m['mae']:.1f} RMSE={m['rmse']:.1f}")
    else:
        print(f"  {name}: Acc={m['accuracy']:.3f} F1={m['f1']:.3f}")
    return model


# ─── Platform 1: Prediksi Harga Rumah ──────────────────────────────────────
def train_p1():
    features = ["luas_bangunan", "luas_tanah", "kamar_tidur", "kamar_mandi", "lantai", "tahun", "jarak_pusat"]
    ranges = [(30, 300), (60, 500), (1, 6), (1, 5), (1, 4), (1990, 2025), (0.5, 30)]
    def target(X):
        return (X[:, 0] * 3.5 + X[:, 1] * 2.8 + X[:, 2] * 25 + X[:, 3] * 15 +
                X[:, 4] * 30 + (X[:, 5] - 1990) * 2 - X[:, 6] * 5 + 100)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.08)
    train_and_save("platform-1", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 2: Deteksi Churn ─────────────────────────────────────────────
def train_p2():
    features = ["lama_bulan", "total_tagihan", "komplain", "login_per_bulan", "fitur_dipakai", "perubahan_paket"]
    ranges = [(1, 72), (50, 500), (0, 15), (1, 30), (1, 20), (-3, 3)]
    def decision(X):
        return ((X[:, 2] > 5) | ((X[:, 4] < 5) & (X[:, 5] < -1)) |
                ((X[:, 3] < 5) & (X[:, 1] > 200))).astype(int)
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.08)
    train_and_save("platform-2", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y, features, False)

# ─── Platform 3: Kelulusan Mahasiswa ────────────────────────────────────────
def train_p3():
    features = ["ipk", "kehadiran", "lulus", "gagal", "ekskul", "beasiswa"]
    ranges = [(0, 4.0), (50, 100), (0, 20), (0, 8), (0, 1), (0, 1)]
    def decision(X):
        return ((X[:, 0] >= 2.5) & (X[:, 1] >= 70) & (X[:, 3] <= 2)).astype(int)
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.1)
    train_and_save("platform-3", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y, features, False)

# ─── Platform 4: Prediksi Penjualan ────────────────────────────────────────
def train_p4():
    features = ["harga", "diskon", "iklan", "bulan", "stok", "penjualan_lalu"]
    ranges = [(10000, 500000), (0, 50), (0, 100), (1, 12), (10, 1000), (10, 500)]
    def target(X):
        return (X[:, 5] * 0.8 - X[:, 0] * 0.001 + X[:, 1] * 2 + X[:, 2] * 0.5 + np.sin(X[:, 3]) * 20 + 50)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.12)
    train_and_save("platform-4", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 5: Deteksi Fraud ─────────────────────────────────────────────
def train_p5():
    features = ["jumlah_transaksi", "jam", "lokasi_beda", "frekuensi_hari", "rata_rata", "umur_akun"]
    ranges = [(1, 50), (0, 24), (0, 1), (1, 30), (100, 50000), (1, 2000)]
    def decision(X):
        return ((X[:, 2] == 1) & (X[:, 0] > 10) & (X[:, 5] < 30)).astype(int)
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.05)
    train_and_save("platform-5", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y, features, False)

# ─── Platform 6: Kualitas Produk ───────────────────────────────────────────
def train_p6():
    features = ["suhu", "tekanan", "rpm", "kelembaban", "waktu", "shift"]
    ranges = [(150, 250), (1, 10), (500, 3000), (20, 90), (5, 60), (1, 3)]
    def decision(X):
        return (((X[:, 0] > 200) & (X[:, 0] < 230) & (X[:, 2] > 1000) & (X[:, 2] < 2500)).astype(int))
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.08)
    train_and_save("platform-6", XGBClassifierCompat(), X, y, features, False)

class XGBClassifierCompat:
    """Wrapper to use GradientBoosting as XGBoost-like."""
    def __init__(self):
        self._m = GradientBoostingClassifier(n_estimators=100, random_state=42)
    def fit(self, X, y): self._m.fit(X, y); return self
    def predict(self, X): return self._m.predict(X)

# ─── Platform 7: Prediksi Gaji ─────────────────────────────────────────────
def train_p7():
    features = ["pengalaman", "pendidikan", "jumlah_skill", "skor", "lokasi", "industri", "ukuran"]
    ranges = [(0, 30), (1, 5), (1, 20), (30, 100), (1, 10), (1, 8), (1, 5)]
    def target(X):
        return (X[:, 0] * 1.2 + X[:, 1] * 2.5 + X[:, 2] * 0.3 + X[:, 3] * 0.1 +
                X[:, 4] * 0.5 + X[:, 5] * 0.3 + X[:, 6] * 0.8 + 3)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.1)
    train_and_save("platform-7", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 8: Risiko Kredit Macet ───────────────────────────────────────
def train_p8():
    features = ["pendapatan", "utang", "tanggungan", "kerja_bulan", "tepat_waktu", "pinjaman", "skor"]
    ranges = [(2, 50), (0, 100), (0, 8), (1, 360), (0, 100), (0, 10), (300, 850)]
    def decision(X):
        return ((X[:, 6] < 500) | ((X[:, 1] > 50) & (X[:, 4] < 50))).astype(int)
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.1)
    train_and_save("platform-8", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y, features, False)

# ─── Platform 9: Harga Kendaraan Bekas ─────────────────────────────────────
def train_p9():
    features = ["merek", "tahun", "jarak_tempuh", "bahan_bakar", "mesin_cc", "kondisi_ext", "kondisi_int", "pemilik"]
    ranges = [(1, 10), (2005, 2025), (1000, 200000), (1, 4), (900, 4000), (1, 5), (1, 5), (1, 5)]
    def target(X):
        return ((X[:, 1] - 2005) * 1.5 - X[:, 2] * 0.03 + X[:, 4] * 0.01 + X[:, 5] * 2 + X[:, 6] * 1.5 - X[:, 7] * 0.5 + 50)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.1)
    train_and_save("platform-9", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 10: Penyakit Padi ────────────────────────────────────────────
def train_p10():
    features = ["warna", "bintik", "akar", "suhu", "kelembaban", "hujan", "umur"]
    ranges = [(1, 5), (1, 5), (1, 4), (20, 40), (30, 90), (50, 300), (30, 150)]
    def decision(X):
        d = np.zeros(len(X), dtype=int)
        d[(X[:, 0] == 2) & (X[:, 5] > 200)] = 1
        d[(X[:, 1] >= 3) & (X[:, 3] > 30)] = 2
        d[(X[:, 2] == 3) & (X[:, 4] > 70)] = 3
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.1)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-10", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 11: Konsumsi Listrik ─────────────────────────────────────────
def train_p11():
    features = ["penghuni", "luas", "ac", "kulkas", "tv_jam", "mesin_cuci", "musim"]
    ranges = [(1, 8), (20, 200), (0, 5), (1, 3), (1, 12), (0, 10), (1, 4)]
    def target(X):
        return (X[:, 0] * 30 + X[:, 1] * 0.5 + X[:, 2] * 80 + X[:, 3] * 40 +
                X[:, 4] * 15 + X[:, 5] * 25 + X[:, 6] * 20 + 100)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.1)
    train_and_save("platform-11", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 12: Kualitas Udara ───────────────────────────────────────────
def train_p12():
    features = ["pm25", "pm10", "suhu", "kelembaban", "angin", "lalu_lintas", "industri"]
    ranges = [(0, 200), (0, 300), (20, 40), (20, 90), (0, 50), (0, 100), (0, 1)]
    def decision(X):
        d = np.zeros(len(X), dtype=int)
        d[(X[:, 0] > 50) | (X[:, 1] > 100)] = 1
        d[(X[:, 0] > 100) | (X[:, 1] > 200)] = 2
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.1)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-12", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 13: Email Spam ───────────────────────────────────────────────
def train_p13():
    features = ["huruf_kapital", "tautan", "tanda_tanya", "panjang", "kata_gratis", "kata_klik", "pengirim_dikenal"]
    ranges = [(0, 50), (0, 10), (0, 5), (10, 1000), (0, 1), (0, 1), (0, 1)]
    def decision(X):
        return ((X[:, 1] > 3) | ((X[:, 4] == 1) & (X[:, 5] == 1)) | (X[:, 2] > 2)).astype(int)
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.08)
    train_and_save("platform-13", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y, features, False)

# ─── Platform 14: Waktu Pengiriman ─────────────────────────────────────────
def train_p14():
    features = ["jarak", "layanan", "berat", "asal", "tujuan", "cuaca", "hari"]
    ranges = [(1, 2000), (1, 3), (0.5, 50), (1, 20), (1, 20), (1, 3), (1, 7)]
    def target(X):
        return (X[:, 0] * 0.05 + X[:, 1] * 5 + X[:, 2] * 0.3 + X[:, 5] * 3 + 10)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.15)
    train_and_save("platform-14", RandomForestRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 15: Sentimen Ulasan ──────────────────────────────────────────
def train_p15():
    features = ["panjang", "emoji", "kata_positif", "kata_negatif", "bintang", "kalimat", "kapital"]
    ranges = [(5, 500), (0, 10), (0, 1), (0, 1), (1, 5), (1, 20), (0, 1)]
    def decision(X):
        d = np.ones(len(X), dtype=int)  # netral default
        d[(X[:, 4] >= 4) & (X[:, 2] == 1)] = 2  # positif
        d[(X[:, 4] <= 2) | (X[:, 3] == 1)] = 0  # negatif
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.15)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-15", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 16: Harga Komoditas ──────────────────────────────────────────
def train_p16():
    features = ["komoditas", "harga_lalu", "persediaan", "petani", "hujan", "inflasi", "libur"]
    ranges = [(1, 10), (5, 100), (10, 500), (100, 5000), (50, 400), (1, 10), (0, 1)]
    def target(X):
        return (X[:, 1] * 0.9 - X[:, 2] * 0.01 + X[:, 6] * 2 + 10)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.1)
    train_and_save("platform-16", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 17: Kelayakan Pinjaman Mikro ─────────────────────────────────
def train_p17():
    features = ["omset", "biaya", "lama_usaha", "karyawan", "jenis", "kredit", "jaminan"]
    ranges = [(1, 100), (0.5, 80), (1, 240), (1, 50), (1, 10), (0, 1), (0, 1)]
    def decision(X):
        return ((X[:, 0] > 20) & (X[:, 2] > 12) & ((X[:, 5] == 1) | (X[:, 6] == 1))).astype(int)
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.1)
    train_and_save("platform-17", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y, features, False)

# ─── Platform 18: Pengunjung Website ───────────────────────────────────────
def train_p18():
    features = ["hari", "bulan", "kampanye", "postingan", "traffic_lalu", "tren", "libur"]
    ranges = [(1, 7), (1, 12), (0, 1), (0, 30), (100, 10000), (0, 100), (0, 1)]
    def target(X):
        return (X[:, 4] * 0.6 + X[:, 2] * 500 + X[:, 5] * 5 + 200)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.15)
    train_and_save("platform-18", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 19: Risiko Obesitas ──────────────────────────────────────────
def train_p19():
    features = ["tinggi", "berat", "usia", "jenis_kelamin", "olahraga", "kalori", "tidur", "riwayat"]
    ranges = [(140, 200), (40, 150), (15, 70), (0, 1), (0, 7), (1000, 5000), (4, 10), (0, 1)]
    def decision(X):
        bmi = X[:, 1] / (X[:, 0] / 100) ** 2
        d = np.zeros(len(X), dtype=int)
        d[bmi > 25] = 1
        d[bmi > 30] = 2
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.1)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-19", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 20: Biaya Operasional ────────────────────────────────────────
def train_p20():
    features = ["karyawan", "luas_kantor", "jenis", "perangkat", "sewa", "utilitas"]
    ranges = [(1, 200), (20, 2000), (1, 10), (1, 100), (5, 100), (1, 50)]
    def target(X):
        return (X[:, 0] * 0.5 + X[:, 1] * 0.02 + X[:, 3] * 0.3 + X[:, 4] * 0.8 + X[:, 5] * 1.2 + 10)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.1)
    train_and_save("platform-20", LinearRegression(), X, y, features, True)

# ─── Platform 21: Jenis Sampah ─────────────────────────────────────────────
def train_p21():
    features = ["warna", "tekstur", "berat", "ukuran", "bau", "kelembaban", "air"]
    ranges = [(1, 10), (1, 5), (1, 500), (1, 100), (1, 5), (10, 90), (10, 90)]
    def decision(X):
        d = np.zeros(len(X), dtype=int)
        d[(X[:, 6] > 60) & (X[:, 4] <= 2)] = 0  # sisa makanan
        d[(X[:, 5] < 40) & (X[:, 1] <= 2)] = 1  # daun
        d[(X[:, 2] < 50) & (X[:, 5] < 30)] = 2  # kertas
        d[(X[:, 1] >= 3) & (X[:, 6] < 30)] = 3  # kayu
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.12)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-21", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 22: Skor Kredit ──────────────────────────────────────────────
def train_p22():
    features = ["pendapatan", "tabungan", "nasabah_bulan", "transaksi", "saldo", "tepat_waktu", "tanggungan"]
    ranges = [(2, 100), (0, 500), (1, 240), (1, 100), (100, 50000), (0, 100), (0, 8)]
    def target(X):
        return (X[:, 0] * 1.5 + X[:, 1] * 0.1 + X[:, 4] * 0.005 + X[:, 5] * 0.8 - X[:, 6] * 5 + 300)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.1)
    train_and_save("platform-22", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 23: Stres Karyawan ───────────────────────────────────────────
def train_p23():
    features = ["jam_kerja", "deadline", "cuti", "tidur", "kepuasan", "lembur", "proyek"]
    ranges = [(20, 80), (0, 20), (0, 30), (4, 10), (1, 10), (0, 20), (0, 10)]
    def decision(X):
        d = np.zeros(len(X), dtype=int)
        d[(X[:, 0] > 50) | (X[:, 1] > 10)] = 1
        d[(X[:, 0] > 60) & (X[:, 6] > 5)] = 2
        d[(X[:, 0] > 70) & (X[:, 3] < 5) & (X[:, 1] > 12)] = 3
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.1)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-23", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 24: Suhu Harian ──────────────────────────────────────────────
def train_p24():
    features = ["suhu_kemarin", "kelembaban", "hujan", "angin", "ketinggian", "bulan", "koordinat"]
    ranges = [(18, 38), (30, 95), (0, 300), (0, 40), (0, 3000), (1, 12), (1, 100)]
    def target(X):
        return (X[:, 0] * 0.5 - X[:, 1] * 0.05 - X[:, 2] * 0.01 - X[:, 4] * 0.005 + 15)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.1)
    train_and_save("platform-24", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 25: Jenis Kelamin (simplified) ───────────────────────────────
def train_p25():
    features = ["rasio_wajah", "alis", "rahang", "rambut", "kulit", "dahi", "mata"]
    ranges = [(0.6, 0.9), (1, 5), (1, 5), (1, 5), (1, 5), (1, 5), (1, 5)]
    def decision(X):
        return ((X[:, 3] > 3) | (X[:, 5] > 3)).astype(int)
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.15)
    train_and_save("platform-25", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y, features, False)

# ─── Platform 26: Omset UMKM ──────────────────────────────────────────────
def train_p26():
    features = ["jenis", "karyawan", "luas_toko", "sewa", "traffic", "hari_op", "tren"]
    ranges = [(1, 20), (1, 50), (10, 500), (1, 50), (10, 1000), (5, 7), (0, 100)]
    def target(X):
        return (X[:, 1] * 0.5 + X[:, 3] * 2 + X[:, 4] * 0.03 + X[:, 5] * 1.5 + 5)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.12)
    train_and_save("platform-26", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 27: Kualitas Air ─────────────────────────────────────────────
def train_p27():
    features = ["ph", "turbidity", "tds", "suhu", "klorin", "bakteri", "logam"]
    ranges = [(5, 9), (0, 100), (50, 1000), (15, 35), (0, 2), (0, 100), (0, 1)]
    def decision(X):
        return (((X[:, 0] >= 6.5) & (X[:, 0] <= 8.5) & (X[:, 1] < 50) &
                (X[:, 4] < 1) & (X[:, 5] == 0) & (X[:, 6] == 0))).astype(int)
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.05)
    train_and_save("platform-27", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y, features, False)

# ─── Platform 28: Harga Emas ──────────────────────────────────────────────
def train_p28():
    features = ["harga_kemarin", "usd", "inflasi", "suku_bunga", "minyak", "saham", "volume"]
    ranges = [(800000, 1200000), (14000, 17000), (2, 10), (3, 10), (60, 100), (5000, 7500), (1000, 10000)]
    def target(X):
        return (X[:, 0] * 1.001 - X[:, 1] * 2 + X[:, 2] * 5000 - X[:, 3] * 3000 + 200000)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.02)
    train_and_save("platform-28", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 29: Pneumonia ────────────────────────────────────────────────
def train_p29():
    features = ["opacitas", "lesi", "simetri", "kontras", "tekstur", "cabang", "intensitas"]
    ranges = [(0, 100), (1, 5), (1, 5), (1, 5), (1, 5), (1, 5), (1, 5)]
    def decision(X):
        d = np.zeros(len(X), dtype=int)
        d[(X[:, 0] > 30) | (X[:, 1] > 2)] = 1
        d[(X[:, 0] > 50) & (X[:, 6] > 3)] = 2
        d[(X[:, 0] > 70) & (X[:, 1] > 3)] = 3
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.1)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-29", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 30: Biaya Kursus ─────────────────────────────────────────────
def train_p30():
    features = ["topik", "durasi", "modul", "rating_instruktur", "siswa", "sertifikat", "hosting"]
    ranges = [(1, 20), (1, 100), (5, 100), (1, 5), (10, 10000), (0, 1), (1, 5)]
    def target(X):
        return (X[:, 1] * 0.5 + X[:, 2] * 0.3 + X[:, 3] * 10 + X[:, 4] * 0.01 + 50)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.12)
    train_and_save("platform-30", RandomForestRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 31: Deteksi Bot ──────────────────────────────────────────────
def train_p31():
    features = ["frekuensi", "aktif_reguler", "follow_ratio", "komentar", "link_spam", "usia_akun", "variasi_waktu"]
    ranges = [(1, 50), (0, 1), (0.01, 10), (1, 200), (0, 1), (1, 3650), (0, 1)]
    def decision(X):
        return ((X[:, 5] < 30) & ((X[:, 0] > 20) | (X[:, 4] == 1))).astype(int)
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.08)
    train_and_save("platform-31", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y, features, False)

# ─── Platform 32: Stok Gudang ──────────────────────────────────────────────
def train_p32():
    features = ["penjualan_30", "tren", "libur", "musim", "sku", "lead_time", "promo"]
    ranges = [(10, 1000), (-50, 50), (0, 10), (1, 4), (10, 500), (1, 30), (0, 1)]
    def target(X):
        return (X[:, 0] * 1.1 + X[:, 1] * 0.5 + X[:, 2] * 5 + X[:, 6] * 50 + 20)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.12)
    train_and_save("platform-32", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 33: Kualitas Teh ─────────────────────────────────────────────
def train_p33():
    features = ["warna", "aroma", "bentuk", "ukuran", "kelembaban", "kafein", "tahun"]
    ranges = [(1, 10), (1, 10), (1, 5), (1, 50), (10, 80), (1, 5), (2020, 2026)]
    def decision(X):
        d = np.zeros(len(X), dtype=int)
        d[(X[:, 0] > 5) & (X[:, 1] > 5)] = 2  # grade A
        d[(X[:, 0] > 3) & (X[:, 1] > 3)] = 1  # grade B
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.12)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-33", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 34: Retensi Pelanggan ────────────────────────────────────────
def train_p34():
    features = ["login", "fitur", "bergabung", "tagihan", "ticket", "nps", "referensi"]
    ranges = [(1, 30), (1, 20), (1, 60), (5, 500), (0, 20), (1, 10), (0, 10)]
    def target(X):
        return (X[:, 2] * 0.1 + X[:, 4] * 0.3 + X[:, 5] * 0.5 + X[:, 6] * 0.8 + 3)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.15)
    train_and_save("platform-34", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 35: Kanker dari Lab ──────────────────────────────────────────
def train_p35():
    features = ["ca125", "cea", "psa", "hemoglobin", "leukosit", "trombosit", "kreatinin", "sgot_ratio"]
    ranges = [(0, 100), (0, 10), (0, 20), (8, 18), (3, 15), (150, 400), (0.5, 5), (0.5, 3)]
    def decision(X):
        d = np.zeros(len(X), dtype=int)
        d[(X[:, 0] > 35) | (X[:, 1] > 5)] = 1
        d[(X[:, 2] > 10) | (X[:, 7] > 2)] = 3
        d[(X[:, 3] < 10) | (X[:, 5] < 200)] = 2
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.12)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-35", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 36: Tamu Hotel ───────────────────────────────────────────────
def train_p36():
    features = ["bulan", "hari", "booking", "event", "cuaca", "harga", "tren"]
    ranges = [(1, 12), (1, 7), (0, 1), (0, 1), (1, 3), (200, 2000), (0, 100)]
    def target(X):
        return (X[:, 3] * 50 + X[:, 6] * 0.5 + np.sin(X[:, 0]) * 20 + 50)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.15)
    train_and_save("platform-36", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 37: Kepuasan Restoran ────────────────────────────────────────
def train_p37():
    features = ["tunggu", "akurasi", "suhu_makanan", "layanan", "komplain", "repeat", "belanja"]
    ranges = [(1, 60), (0, 1), (40, 70), (1, 5), (0, 10), (0, 1), (10, 500)]
    def decision(X):
        d = np.ones(len(X), dtype=int)
        d[(X[:, 0] < 15) & (X[:, 1] == 1) & (X[:, 3] >= 4)] = 3
        d[(X[:, 0] > 30) | (X[:, 4] > 5)] = 0
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.15)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-37", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 38: Curah Hujan ──────────────────────────────────────────────
def train_p38():
    features = ["hujan_lalu", "suhu_laut", "kelembaban", "tekanan", "monsum", "el_nino", "bulan"]
    ranges = [(0, 500), (25, 32), (50, 95), (990, 1020), (0, 1), (-2, 2), (1, 12)]
    def target(X):
        return (X[:, 0] * 0.5 + X[:, 2] * 0.3 - X[:, 3] * 0.1 + X[:, 4] * 50 + 50)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.15)
    train_and_save("platform-38", RandomForestRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)

# ─── Platform 39: Status Gizi Balita ───────────────────────────────────────
def train_p39():
    features = ["tinggi", "berat", "umur", "lila", "lk", "imunisasi", "asi"]
    ranges = [(60, 120), (5, 25), (1, 60), (10, 20), (40, 55), (0, 1), (0, 1)]
    def decision(X):
        bmi = X[:, 1] / (X[:, 0] / 100) ** 2
        d = np.ones(len(X), dtype=int)
        d[bmi < 14] = 0
        d[bmi > 18] = 2
        return d
    X, y = gen_classification(N_SAMPLES, ranges, decision, noise=0.1)
    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    train_and_save("platform-39", RandomForestClassifier(n_estimators=100, random_state=42),
                   X, y_enc, features, False,
                   {"labels": [str(c) for c in le.classes_]})

# ─── Platform 40: Pendapatan Creator ───────────────────────────────────────
def train_p40():
    features = ["subscriber", "views", "engagement", "upload", "durasi", "topik", "kolaborasi"]
    ranges = [(100, 1000000), (100, 1000000), (0.01, 0.15), (1, 30), (5, 60), (1, 20), (0, 10)]
    def target(X):
        return (X[:, 1] * 0.001 + X[:, 2] * 100 + X[:, 3] * 0.5 + X[:, 6] * 2 + 1)
    X, y = gen_regression(N_SAMPLES, ranges, target, noise_std=0.2)
    train_and_save("platform-40", GradientBoostingRegressor(n_estimators=100, random_state=42),
                   X, y, features, True)


if __name__ == "__main__":
    print("Training 40 platform models...\n")
    trainers = [
        train_p1, train_p2, train_p3, train_p4, train_p5, train_p6, train_p7, train_p8,
        train_p9, train_p10, train_p11, train_p12, train_p13, train_p14, train_p15, train_p16,
        train_p17, train_p18, train_p19, train_p20, train_p21, train_p22, train_p23, train_p24,
        train_p25, train_p26, train_p27, train_p28, train_p29, train_p30, train_p31, train_p32,
        train_p33, train_p34, train_p35, train_p36, train_p37, train_p38, train_p39, train_p40,
    ]
    for fn in trainers:
        try:
            fn()
        except Exception as e:
            print(f"  ERROR in {fn.__name__}: {e}")
    print(f"\nDone! Models saved to {MODELS_DIR}")
