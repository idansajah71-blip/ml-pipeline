export interface NeedScenario {
  id: string;
  need: string;
  description: string;
  problemType: 'classification' | 'regression';
  suggestedAlgorithms: string[];
  exampleUseCase: string;
  tags: string[];
}

export interface FAQEntry {
  id: string;
  question: string;
  answer: string;
  category: 'upload' | 'training' | 'algorithm' | 'result' | 'error' | 'pricing' | 'general';
  tags: string[];
}

export const NEED_SCENARIOS: NeedScenario[] = [
  {
    id: 'predict-price',
    need: 'Prediksi harga / angka',
    description: 'Memprediksi nilai kontinu seperti harga rumah, biaya operasional, atau jumlah penjualan.',
    problemType: 'regression',
    suggestedAlgorithms: ['xgboost', 'lightgbm', 'gradient_boosting', 'random_forest'],
    exampleUseCase: 'Prediksi harga rumah berdasarkan luas tanah, jumlah kamar, dan lokasi',
    tags: ['harga', 'price', 'biaya', 'jumlah', 'angka', 'nominal', 'forecasts', 'estimasi'],
  },
  {
    id: 'predict-churn',
    need: 'Prediksi pelanggan churn',
    description: 'Memprediksi apakah pelanggan akan berhenti menggunakan layanan (ya/tidak).',
    problemType: 'classification',
    suggestedAlgorithms: ['xgboost', 'lightgbm', 'random_forest', 'gradient_boosting'],
    exampleUseCase: 'Prediksi apakah pelanggan SaaS akan berhenti berlangganan bulan depan',
    tags: ['churn', 'keluar', 'berhenti', 'langganan', 'retention', 'pelanggan', 'customer'],
  },
  {
    id: 'predict-approval',
    need: 'Prediksi approval / persetujuan',
    description: 'Memprediksi apakah suatu pengajuan akan disetujui atau ditolak.',
    problemType: 'classification',
    suggestedAlgorithms: ['logistic_regression', 'random_forest', 'xgboost', 'svm'],
    exampleUseCase: 'Prediksi approve atau tolak pengajuan kredit berdasarkan profil nasabah',
    tags: ['approval', 'setuju', 'tolak', 'kredit', 'pinjaman', 'pengajuan', 'loan'],
  },
  {
    id: 'spam-detection',
    need: 'Deteksi spam / penipuan',
    description: 'Mengklasifikasikan pesan atau transaksi sebagai normal atau mencurigakan.',
    problemType: 'classification',
    suggestedAlgorithms: ['xgboost', 'random_forest', 'gradient_boosting', 'svm'],
    exampleUseCase: 'Deteksi email spam atau transaksi fraud pada kartu kredit',
    tags: ['spam', 'fraud', 'penipuan', 'scam', 'curang', 'deteksi', 'keamanan'],
  },
  {
    id: 'quality-classification',
    need: 'Klasifikasi kualitas',
    description: 'Mengelompokkan produk atau data ke dalam kategori kualitas (A/B/C, good/bad).',
    problemType: 'classification',
    suggestedAlgorithms: ['random_forest', 'xgboost', 'catboost', 'gradient_boosting'],
    exampleUseCase: 'Klasifikasi kualitas produk manufaktur berdasarkan hasil sensor',
    tags: ['kualitas', 'quality', 'grade', 'kelas', 'kategori', 'baik', 'buruk'],
  },
  {
    id: 'demand-forecast',
    need: 'Prediksi demand / permintaan',
    description: 'Memprediksi jumlah permintaan atau konsumsi di masa depan.',
    problemType: 'regression',
    suggestedAlgorithms: ['lightgbm', 'xgboost', 'gradient_boosting', 'random_forest'],
    exampleUseCase: 'Prediksi jumlah unit produk yang terjual bulan depan',
    tags: ['demand', 'permintaan', 'penjualan', 'stock', 'inventory', 'stok', 'jualan'],
  },
  {
    id: 'risk-scoring',
    need: 'Skor risiko',
    description: 'Memberikan skor risiko pada suatu entitas (nasabah, transaksi, proyek).',
    problemType: 'regression',
    suggestedAlgorithms: ['xgboost', 'gradient_boosting', 'lightgbm', 'ridge'],
    exampleUseCase: 'Skor risiko kredit nasabah berdasarkan riwayat keuangan',
    tags: ['risiko', 'risk', 'skor', 'score', 'kredit', 'credit', 'bahaya'],
  },
  {
    id: 'lead-scoring',
    need: 'Lead scoring',
    description: 'Mengidentifikasi prospek mana yang paling mungkin menjadi pelanggan.',
    problemType: 'classification',
    suggestedAlgorithms: ['logistic_regression', 'xgboost', 'random_forest', 'gradient_boosting'],
    exampleUseCase: 'Skor leads marketing: panas/dingin berdasarkan interaksi website',
    tags: ['lead', 'prospek', 'marketing', 'sales', 'pelanggan', 'konversi'],
  },
  {
    id: 'maintenance-prediction',
    need: 'Prediksi kegagalan mesin',
    description: 'Memprediksi apakah peralatan akan mengalami masalah dalam waktu dekat.',
    problemType: 'classification',
    suggestedAlgorithms: ['random_forest', 'xgboost', 'gradient_boosting', 'lightgbm'],
    exampleUseCase: 'Prediksi kapan mesin pabrik perlu maintenance berdasarkan sensor vibrasi',
    tags: ['maintenance', 'kegagalan', 'gagal', 'rusak', 'mesin', 'sensor', 'perawatan'],
  },
  {
    id: 'price-optimization',
    need: 'Optimasi harga',
    description: 'Menentukan harga optimal berdasarkan faktor-faktor yang mempengaruhi.',
    problemType: 'regression',
    suggestedAlgorithms: ['xgboost', 'lightgbm', 'catboost', 'elastic_net'],
    exampleUseCase: 'Optimasi harga tiket pesawat berdasarkan waktu, rute, dan demand',
    tags: ['harga', 'optimasi', 'pricing', 'optimal', 'strategi', 'kompetitif'],
  },
  {
    id: 'readmission',
    need: 'Prediksi readmisi rumah sakit',
    description: 'Memprediksi apakah pasien akan kembali dirawat dalam waktu singkat.',
    problemType: 'classification',
    suggestedAlgorithms: ['xgboost', 'random_forest', 'gradient_boosting', 'logistic_regression'],
    exampleUseCase: 'Prediksi pasien diabetes yang berisiko readmisi dalam 30 hari',
    tags: ['rumah sakit', 'pasien', 'readmisi', 'kesehatan', 'healthcare', 'medical'],
  },
  {
    id: 'crop-yield',
    need: 'Prediksi hasil panen',
    description: 'Memprediksi jumlah hasil panen berdasarkan kondisi tanah dan cuaca.',
    problemType: 'regression',
    suggestedAlgorithms: ['random_forest', 'xgboost', 'gradient_boosting', 'lightgbm'],
    exampleUseCase: 'Prediksi tonase hasil panen padi berdasarkan curah hujan dan jenis tanah',
    tags: ['panen', 'hasil', 'pertanian', 'crop', 'yield', 'farm', 'agrikultur'],
  },
  {
    id: 'customer-segmentation',
    need: 'Segmentasi pelanggan',
    description: 'Mengelompokkan pelanggan berdasarkan perilaku pembelian.',
    problemType: 'classification',
    suggestedAlgorithms: ['random_forest', 'gradient_boosting', 'xgboost', 'knn'],
    exampleUseCase: 'Klasifikasi pelanggan VIP vs reguler berdasarkan frekuensi dan nilai belanja',
    tags: ['segmentasi', 'segment', 'kelompok', 'pelanggan', 'customer', 'group'],
  },
];

export const FAQ_ENTRIES: FAQEntry[] = [
  {
    id: 'what-is',
    question: 'Apa itu ML Pipeline?',
    answer: 'ML Pipeline adalah platform machine learning yang memungkinkan Anda mengunggah dataset, melatih model, dan menggunakannya untuk prediksi — semua melalui antarmuka yang mudah digunakan tanpa perlu coding.',
    category: 'general',
    tags: ['apa itu', 'about', 'pengenalan', 'ml pipeline', 'platform'],
  },
  {
    id: 'no-code',
    question: 'Bisakah saya pakai tanpa bisa coding?',
    answer: 'Bisa! Training Wizard akan memandu Anda langkah demi langkah. Pilih dataset, pilih kolom target, pilih mode sederhana, dan sistem akan otomatis memilih algoritma terbaik untuk Anda.',
    category: 'general',
    tags: ['tidak bisa coding', 'pemula', 'no code', 'gampang', 'mudah', 'wizard'],
  },
  {
    id: 'supported-formats',
    question: 'Format file apa saja yang didukung?',
    answer: 'Format yang didukung: CSV (.csv), TSV (.tsv), JSON (.json), Excel (.xls, .xlsx), dan ODS (.ods). Ukuran maksimal tergantung tier: Free 10MB, Starter 50MB, Pro 200MB, Enterprise 1GB.',
    category: 'upload',
    tags: ['format', 'file', 'csv', 'excel', 'upload', 'unggah', 'ukuran'],
  },
  {
    id: 'min-data',
    question: 'Berapa minimum data yang dibutuhkan?',
    answer: 'Minimum 50 sampel, direkomendasikan 500+ sampel, dan idealnya 1000+ sampel. Semakin banyak data, semakin akurat model yang dihasilkan.',
    category: 'upload',
    tags: ['minimum', 'jumlah data', 'baris', 'rows', 'samples', 'sampel', 'sedikit'],
  },
  {
    id: 'missing-values',
    question: 'Bagaimana jika data saya ada yang kosong?',
    answer: 'Sistem otomatis menangani missing values: kolom numerik diisi dengan median, kolom kategorikal diisi dengan modus (nilai terbanyak). Kolom dengan >80% missing akan mendapat peringatan untuk dihapus.',
    category: 'upload',
    tags: ['kosong', 'missing', 'null', 'kosong', 'empty', 'kosong', 'hilang'],
  },
  {
    id: 'simple-vs-advanced',
    question: 'Apa beda mode sederhana dan lanjutan?',
    answer: 'Mode sederhana: sistem otomatis memilih algoritma dan preprocessing. Mode lanjutan: Anda bisa memilih algoritma (12 klasifikasi, 14 regresi) dan mengatur hyperparameter sendiri.',
    category: 'training',
    tags: ['mode', 'sederhana', 'lanjutan', 'advanced', 'simple', 'otomatis', 'manual'],
  },
  {
    id: 'training-time',
    question: 'Berapa lama training memakan waktu?',
    answer: 'Tergantung ukuran dataset dan algoritma. Dataset kecil (<1000 baris): 5-30 detik. Dataset menengah (1000-10000 baris): 1-5 menit. Dataset besar (>10000 baris): 5-30 menit.',
    category: 'training',
    tags: ['lama', 'waktu', 'cepat', 'lambat', 'training', 'durasi', 'menunggu'],
  },
  {
    id: 'choose-algorithm',
    question: 'Bagaimana cara memilih algoritma yang tepat?',
    answer: 'Gunakan rekomendasi otomatis di Training Wizard! Setelah Anda memilih jenis prediksi (angka/kategori), sistem akan menyarankan algoritma yang paling cocok. Anda juga bisa mencoba beberapa algoritma dan membandingkan hasilnya di halaman Benchmark.',
    category: 'algorithm',
    tags: ['algoritma', 'pilih', 'mana', 'tepat', 'cocok', 'bagus', 'terbaik'],
  },
  {
    id: 'accuracy-meaning',
    question: 'Apa arti "Akurasi" di hasil training?',
    answer: 'Akurasi = (Prediksi Benar) / (Total Prediksi). Contoh: akurasi 95% berarti model benar 95 dari 100 kali. Namun, akurasi saja tidak cukup — perhatikan juga F1 Score untuk data yang tidak seimbang.',
    category: 'result',
    tags: ['akurasi', 'accuracy', 'artinya', 'meaning', 'hasil', 'metrik', 'skor'],
  },
  {
    id: 'f1-score',
    question: 'Kapan harus melihat F1 Score daripada Akurasi?',
    answer: 'Gunakan F1 Score ketika kelas data tidak seimbang (misal 95% "Tidak" dan 5% "Ya"). F1 Score menyeimbangkan Precision (seberapa tepat prediksi positif) dan Recall (seberapa banyak positif yang tertangkap).',
    category: 'result',
    tags: ['f1', 'precision', 'recall', 'imbalance', 'tidak seimbang', 'metrik'],
  },
  {
    id: 'low-accuracy',
    question: 'Akurasi model saya rendah, bagaimana cara memperbaikinya?',
    answer: 'Coba langkah ini: 1) Kumpulkan lebih banyak data, 2) Bersihkan data dari error dan outlier, 3) Tambah kolom fitur yang relevan, 4) Coba algoritma berbeda via mode Advanced atau AutoML, 5) Periksa apakah ada data leakage (informasi masa depan di data training).',
    category: 'result',
    tags: ['rendah', 'buruk', 'perbaiki', 'tingkatkan', 'improve', 'akurasi', 'low'],
  },
  {
    id: 'overfitting',
    question: 'Apa itu overfitting dan bagaimana cara mengatasinya?',
    answer: 'Overfitting terjadi saat model menghafal data training tapi gagal di data baru. Tandanya: akurasi training jauh lebih tinggi dari test. Solusi: dapatkan lebih banyak data, sederhanakan model, gunakan regularisasi, atau pakai cross-validation.',
    category: 'result',
    tags: ['overfitting', 'menghafal', 'training bagus', 'test jelek', 'generalisasi'],
  },
  {
    id: 'cluster-unsupported',
    question: 'Bisakah saya melakukan clustering / pengelompokan?',
    answer: 'Fitur clustering belum tersedia di platform saat ini. Yang didukung: Klasifikasi (prediksi kategori) dan Regresi (prediksi angka). Jika Anda butuh clustering, pertimbangkan untuk menggunakan layanan lain atau request fitur ini.',
    category: 'general',
    tags: ['clustering', 'kmeans', 'dbscan', 'pengelompokan', 'segmentasi', 'group'],
  },
  {
    id: 'timeseries-unsupported',
    question: 'Bisakah saya memprediksi data time series?',
    answer: 'Fitur time series belum tersedia di platform saat ini. Platform mendukung data tabular saja (baris dan kolom). Untuk data deret waktu, Anda perlu mentransformasinya terlebih dahulu menjadi fitur tabular (misal: tambahkan kolom lag, moving average, dll).',
    category: 'general',
    tags: ['time series', 'deret waktu', 'forecasting', 'prediksi waktu', 'arima', 'lstm'],
  },
  {
    id: 'tier-limits',
    question: 'Apa batasan di tier Free?',
    answer: 'Tier Free: upload maks 10MB, 10.000 API calls/hari, 5 training/hari, maks 10 model. Untuk batas lebih tinggi, upgrade ke Starter ($9/bulan) atau Pro ($29/bulan).',
    category: 'pricing',
    tags: ['gratis', 'free', 'batas', 'limit', 'upgrade', 'bayar', 'harga'],
  },
  {
    id: 'data-security',
    question: 'Apakah data saya aman?',
    answer: 'Ya. Kami menggunakan: JWT authentication, penyimpanan data terenkripsi, kontrol akses berbasis role, retensi data otomatis sesuai tier, dan audit log untuk semua aktivitas.',
    category: 'general',
    tags: ['aman', 'security', 'keamanan', 'enkripsi', 'privasi', 'data'],
  },
  {
    id: 'deploy-model',
    question: 'Bagaimana cara menggunakan model setelah training selesai?',
    answer: 'Setelah training selesai, Anda bisa: 1) Deploy model untuk prediksi real-time, 2) Gunakan REST API untuk integrasi, 3) Export model dalam format joblib/pickle, 4) Bagikan ke marketplace untuk pengguna lain.',
    category: 'training',
    tags: ['deploy', 'gunakan', 'produksi', 'production', 'api', 'integrasi'],
  },
  {
    id: 'what-algorithms',
    question: 'Algoritma apa saja yang tersedia?',
    answer: 'Untuk Klasifikasi (12): Random Forest, Gradient Boosting, Logistic Regression, SVM, KNN, Decision Tree, AdaBoost, Bagging, MLP, XGBoost, LightGBM, CatBoost. Untuk Regresi (14): Ditambah Ridge, Lasso, Elastic Net, SVR.',
    category: 'algorithm',
    tags: ['algoritma', 'daftar', 'list', 'tersedia', 'apa saja', 'pilihan'],
  },
];

export const QUICKSTART_CARDS = [
  {
    id: 'new-prediction',
    title: 'Bikin Prediksi Baru',
    description: 'Unggah data dan latih model pertama Anda',
    icon: 'Brain',
    href: '/training-wizard',
    color: 'bg-blue-50 text-blue-600 border-blue-200',
  },
  {
    id: 'explore-models',
    title: 'Lihat Model Orang Lain',
    description: 'Temukan model siap pakai di marketplace',
    icon: 'Search',
    href: '/marketplace',
    color: 'bg-green-50 text-green-600 border-green-200',
  },
  {
    id: 'compare-models',
    title: 'Bandingin Model',
    description: 'Bandingkan performa berbagai algoritma',
    icon: 'BarChart3',
    href: '/benchmark',
    color: 'bg-purple-50 text-purple-600 border-purple-200',
  },
  {
    id: 'understand-platform',
    title: 'Belum Ngerti Platform?',
    description: 'Pelajari dasar-dasar ML Pipeline',
    icon: 'HelpCircle',
    href: '/onboarding',
    color: 'bg-amber-50 text-amber-600 border-amber-200',
  },
];
