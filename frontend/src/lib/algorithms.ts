export interface AlgorithmInfo {
  label: string;
  description: string;
  bestFor: string;
}

export const PREDICTION_TYPE_COLORS = {
  classification: {
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    border: 'border-blue-300',
    dot: 'bg-blue-500',
    darkBg: 'dark:bg-blue-900/30',
    darkText: 'dark:text-blue-300',
    darkBorder: 'dark:border-blue-700',
  },
  regression: {
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-300',
    dot: 'bg-emerald-500',
    darkBg: 'dark:bg-emerald-900/30',
    darkText: 'dark:text-emerald-300',
    darkBorder: 'dark:border-emerald-700',
  },
} as const;

export const ALGORITHMS: Record<string, AlgorithmInfo> = {
  random_forest: {
    label: 'Random Forest',
    description: 'Kumpulan banyak pohon keputusan yang digabungkan. Stabil, tahan overfitting, cocok untuk hampir semua jenis data.',
    bestFor: 'Pilihan aman untuk pemula, data campuran angka & kategori',
  },
  gradient_boosting: {
    label: 'Gradient Boosting',
    description: 'Melatih model berurutan, setiap model memperbaiki kesalahan sebelumnya. Akurat tapi lebih lambat.',
    bestFor: 'Ketika akurasi lebih penting dari kecepatan training',
  },
  logistic_regression: {
    label: 'Logistic Regression',
    description: 'Model paling sederhana untuk klasifikasi. Cepat, mudah dijelaskan, dan mudah dipahami.',
    bestFor: 'Klasifikasi biner, data linier, baseline pertama',
  },
  svm: {
    label: 'Support Vector Machine',
    description: 'Mencari batas terbaik antara kategori. Bagus untuk data berdimensi tinggi tapi lambat di data besar.',
    bestFor: 'Teks, data berdimensi tinggi, dataset kecil-menengah',
  },
  knn: {
    label: 'K-Nearest Neighbors',
    description: 'Memprediksi berdasarkan data terdekat. Sangat sederhana tapi bisa lambat pada data besar.',
    bestFor: 'Dataset kecil, rekomendasi, pola berdasarkan kemiripan',
  },
  decision_tree: {
    label: 'Decision Tree',
    description: 'Satu pohon keputusan yang mudah divisualisasikan. Gampang dipahami tapi mudah overfitting.',
    bestFor: 'Ketika perlu menjelaskan alasan prediksi',
  },
  adaboost: {
    label: 'AdaBoost',
    description: 'Menggabungkan banyak model lemah jadi satu model kuat. Efektif dan cepat.',
    bestFor: 'Dataset dengan noise, klasifikasi biner',
  },
  bagging: {
    label: 'Bagging',
    description: 'Menggabungkan beberapa model yang dilatih secara paralel pada subset data. Mengurangi overfitting.',
    bestFor: 'Model yang stabil dan tahan noise',
  },
  mlp: {
    label: 'Neural Network (MLP)',
    description: 'Jaringan saraf tiruan sederhana. Bisa menangkap pola kompleks tapi butuh lebih banyak data.',
    bestFor: 'Pola non-linier kompleks, data besar',
  },
  xgboost: {
    label: 'XGBoost',
    description: 'Gradient Boosting yang dioptimasi. Industry standard untuk kompetisi ML dan data tabular.',
    bestFor: 'Kompetisi Kaggle, dataset tabular, performa maksimal',
  },
  lightgbm: {
    label: 'LightGBM',
    description: 'Gradient Boosting yang sangat cepat dan hemat memori. Cocok untuk dataset besar.',
    bestFor: 'Dataset besar (100k+ baris), ketika butuh kecepatan',
  },
  catboost: {
    label: 'CatBoost',
    description: 'Gradient Boosting yang otomatis menangani kategori. Paling mudah digunakan tanpa preprocessing.',
    bestFor: 'Data dengan banyak kategori, minim preprocessing',
  },
};

export const REGRESSION_ALGORITHMS: Record<string, AlgorithmInfo> = {
  random_forest: {
    label: 'Random Forest Regressor',
    description: 'Random Forest untuk prediksi angka. Stabil dan tahan overfitting.',
    bestFor: 'Regresi umum, baseline pertama',
  },
  gradient_boosting: {
    label: 'Gradient Boosting Regressor',
    description: 'Gradient Boosting untuk prediksi angka. Sangat akurat.',
    bestFor: 'Akurasi regresi tinggi',
  },
  ridge: {
    label: 'Ridge Regression',
    description: 'Regresi linier dengan regularisasi L2. Mencegah overfitting pada fitur banyak.',
    bestFor: 'Data dengan banyak fitur, mencegah overfitting',
  },
  lasso: {
    label: 'Lasso Regression',
    description: 'Regresi linier dengan regularisasi L1. Bisa menghilangkan fitur yang tidak penting.',
    bestFor: 'Feature selection otomatis',
  },
  elastic_net: {
    label: 'Elastic Net',
    description: 'Gabungan Ridge dan Lasso. Mengambil yang terbaik dari keduanya.',
    bestFor: 'Banyak fitur korelasi',
  },
  svr: {
    label: 'Support Vector Regressor',
    description: 'SVM untuk regresi. Bagus untuk data berdimensi tinggi.',
    bestFor: 'Regresi non-linier, data berdimensi tinggi',
  },
  knn: {
    label: 'KNN Regressor',
    description: 'KNN untuk prediksi angka. Sederhana tapi lambat di data besar.',
    bestFor: 'Dataset kecil, prediksi berdasarkan kemiripan',
  },
  decision_tree: {
    label: 'Decision Tree Regressor',
    description: 'Pohon keputusan untuk regresi. Mudah dipahami tapi overfitting.',
    bestFor: 'Ketika perlu interpretasi mudah',
  },
  adaboost: {
    label: 'AdaBoost Regressor',
    description: 'AdaBoost untuk regresi. Menggabungkan model lemah.',
    bestFor: 'Dataset dengan noise',
  },
  bagging: {
    label: 'Bagging Regressor',
    description: 'Bagging untuk regresi. Stabil dan tahan noise.',
    bestFor: 'Regresi stabil',
  },
  mlp: {
    label: 'Neural Network Regressor',
    description: 'MLP untuk prediksi angka. Menangkap pola kompleks.',
    bestFor: 'Pola non-linier kompleks',
  },
  xgboost: {
    label: 'XGBoost Regressor',
    description: 'XGBoost untuk regresi. Industry standard.',
    bestFor: 'Performa regresi maksimal',
  },
  lightgbm: {
    label: 'LightGBM Regressor',
    description: 'LightGBM untuk regresi. Sangat cepat.',
    bestFor: 'Regresi dataset besar',
  },
  catboost: {
    label: 'CatBoost Regressor',
    description: 'CatBoost untuk regresi. Otomatis menangani kategori.',
    bestFor: 'Regresi dengan fitur kategori',
  },
};

export const ALGORITHM_LIST = Object.entries(ALGORITHMS).map(([value, info]) => ({
  value,
  ...info,
}));

export const REGRESSION_ALGORITHM_LIST = Object.entries(REGRESSION_ALGORITHMS).map(([value, info]) => ({
  value,
  ...info,
}));
