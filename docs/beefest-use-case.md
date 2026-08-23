# Fase 4 — Use Case & Narasi Bisnis: Prediksi Kemiskinan Antar-Provinsi di Indonesia

## Problem Statement

Indonesia memiliki 34 provinsi dengan tingkat kemiskinan yang sangat bervariasi.
Data BPS (Badan Pusat Statistik) tersedia secara terbuka tetapi belum dimanfaatkan
secara optimal oleh pemerintah daerah untuk pengambilan keputusan berbasis data.
Proses analisis konvensional membutuhkan waktu berminggu-minggu dan tenaga ahli
statistik, sementara kebutuhan keputusan sering kali mendesak.

**Masalah inti:** Pemerintah daerah tidak memiliki cara cepat dan akurat untuk
memprediksi tren kemiskinan di wilayah mereka, sehingga alokasi anggaran program
perlindungan sosial sering kali tidak tepat sasaran.

## Solution

Platform ML Pipeline menyediakan solusi end-to-end yang memungkinkan analis data
pemerintah untuk:

1. **Mengambil data BPS secara otomatis** melalui integrasi External Data Explorer
   (sudah tersedia di platform)
2. **Melatih model prediktif** menggunakan Training Wizard tanpa perlu coding
3. **Mengevaluasi kualitas model** dengan quality gates (calibration, cross-validation,
   leakage prevention)
4. **Mendeploy model** untuk prediksi real-time via REST API
5. **Memantau drift** data secara otomatis

## Value Proposition

| Aspek | Konvensional | ML Pipeline |
|-------|-------------|-------------|
| Waktu analisis | 2-4 minggu | 15-30 menit |
| Skill dibutuhkan | Data scientist senior | Analyst dengan GUI |
| Biaya | Rp 50-100 juta/proyek | Open source, gratis |
| Aktualisasi data | Manual, quarterly | Otomatis, real-time |
| Jaminan kualitas | Tergantung SDM | Quality gates bawaan |

## Dataset Demo

**Nama:** Ekonomi Indonesia (Regresi) — sudah tersedia sebagai sample dataset

- **Sumber:** BPS Open Data
- **Fitur:** 34 provinsi × 7 indikator (GDP per kapita, inflasi, pengangguran,
  indeks harga, investasi, ekspor, tingkat pendidikan)
- **Target:** Persentase penduduk miskin per provinsi
- **Jenis:** Regresi (prediksi angka kontinu)

## Metrik Keberhasilan

### Teknis
- **R² Score** ≥ 0.70 (model menjelaskan ≥70% variansi)
- **MAE** < 2% (error prediksi < 2 persen poin)
- **Calibration Error** < 0.10 (prediksi terkalibrasi dengan baik)
- **No data leakage** — CI quality gate menjamin ini

### Bisnis
- **Akurasi prediksi** cukup tinggi untuk menjadi dasar pengambilan keputusan
- **Waktu respons** < 1 menit dari upload data hingga model siap
- **Adoptability** — bisa digunakan oleh analis non-teknis melalui GUI

## Skenario End-to-End (Live Demo)

### Langkah 1: Upload Dataset
- Upload file `indonesia_economy.csv` (atau gunakan sample dataset yang sudah ada)
- Platform otomatis mendeteksi kolom kategorikal (provinsi) dan numerik
- Data quality gate berjalan otomatis

### Langkah 2: Training Wizard
- Pilih target column: `kemiskinan_persen`
- Pilih algoritma: Random Forest (default) atau biarkan AutoML memilih
- Jalankan training — model terlatih dalam <30 detik
- Lihat hasil: R², feature importance, kurva kalibrasi

### Langkah 3: Evaluasi
- Periksa metrics di dashboard
- Lihat feature importance — indikator mana yang paling mempengaruhi kemiskinan
- Review calibration curve — prediksi model reliable

### Langkah 4: Deploy & Prediksi
- Deploy model ke serving endpoint
- Kirim data provinsi baru → dapatkan prediksi kemiskinan
- Contoh: {"GDP_per_kapita": 45000000, "inflasi": 3.2, ...} → prediksi: 8.5%

### Langkah 5: Monitoring
- Set up drift detection untuk memantau apakah data baru masih konsisten dengan
  data training
- Notifikasi otomatis jika drift terdeteksi

## Fitur Platform yang Diunggulkan

1. **No-code ML** — Training Wizard bisa digunakan tanpa coding
2. **Indonesian-first** — Error message dalam Bahasa Indonesia
3. **Data Quality Gates** — Mencegah data leakage, overfitting, model tidak reliabel
4. **Calibration & Conformal Prediction** — Prediksi dilengkapi confidence interval
5. **Artifact Signing (Ed25519)** — Menjamin integritas model
6. **AutoML** — Perbandingan otomatis multiple algorithms
7. **External Data Integration** — BPS, World Bank, data.go.id
8. **Drift Monitoring** — Deteksi otomatis perubahan data distribusi
9. **Model Marketplace** — Berbagi model antar tim

## Narasi Presentasi (3 menit)

> "Bayangkan seorang kepala dinas di sebuah provinsi ingin mengetahui prediksi
> tingkat kemiskinan tahun depan untuk menyiapkan anggaran program perlindungan
> sosial.
>
> Dengan ML Pipeline, beliau cukup upload data BPS terkini, jalankan Training
> Wizard, dan dalam 15 menit mendapatkan model prediktif yang sudah dievaluasi
> kualitasnya oleh quality gates bawaan.
>
> Yang membuat berbeda: setiap model yang dihasilkan sudah melewati 9 quality
> gates otomatis — mulai dari deteksi data leakage, calibration check, hingga
> artifact signing untuk keamanan. Ini bukan sekedar model machine learning,
> ini adalah ML yang benar secara metodologi.
>
> Dan yang paling penting: semua pesan error dalam Bahasa Indonesia, sehingga
> bisa digunakan oleh siapa saja tanpa latar belakang teknis yang mendalam."
