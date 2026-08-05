export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: 'admin' | 'data_scientist' | 'user';
  is_active: boolean;
  api_key: string | null;
  created_at: string;
  updated_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  file_path: string;
  file_size: number | null;
  rows_count: number | null;
  columns_count: number | null;
  column_names: string[] | null;
  column_types: Record<string, string> | null;
  target_column: string | null;
  tags: string[];
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface MLModel {
  id: string;
  name: string;
  description: string | null;
  algorithm: string;
  version: number;
  status: 'training' | 'trained' | 'deployed' | 'archived' | 'failed';
  file_path: string | null;
  metrics: Record<string, any>;
  parameters: Record<string, any>;
  feature_names: string[];
  target_column: string | null;
  tags: string[];
  is_default: number;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface Experiment {
  id: string;
  name: string;
  description: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  parameters: Record<string, any>;
  results: Record<string, any>;
  logs: string | null;
  duration_seconds: string | null;
  dataset_id: string;
  model_id: string;
  owner_id: string;
  created_at: string;
  completed_at: string | null;
}

export interface ABTest {
  id: string;
  name: string;
  description: string | null;
  status: 'draft' | 'active' | 'paused' | 'completed';
  traffic_split: number;
  model_a_id: string;
  model_b_id: string;
  model_a_requests: number;
  model_b_requests: number;
  model_a_accuracy: number;
  model_b_accuracy: number;
  results: Record<string, any>;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface Stats {
  total_models: number;
  total_datasets: number;
  total_experiments: number;
  total_predictions: number;
  active_models: number;
  training_experiments: number;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export type UserRole = 'admin' | 'data_scientist' | 'user';

export type ModelStatus = MLModel['status'];
export type ExperimentStatus = Experiment['status'];
export type ABTestStatus = ABTest['status'];

export type SortDirection = 'asc' | 'desc';

export interface SortConfig {
  field: string;
  direction: SortDirection;
}

export interface FilterConfig {
  field: string;
  value: string | number | boolean;
  operator: 'eq' | 'neq' | 'gt' | 'lt' | 'contains' | 'in';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export interface SystemInfo {
  cpu_percent: number;
  memory: {
    percent: number;
    available: number;
    total: number;
  };
  disk: {
    percent: number;
    used: number;
    total: number;
  };
  platform: string;
  python_version: string;
}

export interface PredictionResult {
  predictions: Array<{
    prediction: string | number;
    probability?: number;
    probabilities?: Record<string, number>;
  }>;
  latency_ms: number;
}

export interface ColumnInfo {
  name: string;
  dtype: string;
  null_count: number;
  unique_count: number;
}

export interface DatasetProfile {
  summary: {
    rows: number;
    columns: number;
    numeric_columns: number;
    categorical_columns: number;
    memory_usage_bytes: number;
    duplicated_rows: number;
    total_missing: number;
    missing_percentage: number;
    column_names: string[];
  };
  column_profiles: Record<string, {
    dtype: string;
    non_null_count: number;
    null_count: number;
    null_percentage: number;
    unique_count: number;
    statistics: Record<string, any>;
  }>;
  missing_values: {
    total_missing: number;
    total_cells: number;
    missing_percentage: number;
    columns_with_missing: string[];
    missing_by_column: Record<string, { count: number; percentage: number }>;
    complete_rows: number;
    complete_rows_percentage: number;
  };
  outliers: Record<string, {
    q1: number;
    q3: number;
    iqr: number;
    lower_bound: number;
    upper_bound: number;
    outlier_count: number;
    outlier_percentage: number;
  }>;
  correlations: {
    matrix: Record<string, Record<string, number>>;
    strong_correlations: Array<{
      feature_1: string;
      feature_2: string;
      correlation: number;
      strength: string;
    }>;
  };
  class_distribution?: {
    column: string;
    num_classes: number;
    distribution: Record<string, { count: number; percentage: number }>;
    imbalance_ratio: number;
    is_imbalanced: boolean;
    majority_class: string;
    minority_class: string;
  };
}

export interface DataDriftResult {
  drift_detected: boolean;
  severity: string;
  summary: {
    total_features: number;
    drifted_features: number;
    drift_percentage: number;
  };
  psi: Record<string, { psi: number; bins: number; drifted: boolean }>;
  ks_test: Record<string, { statistic: number; p_value: number; drifted: boolean }>;
  distribution_shift: Record<string, {
    ref_mean: number;
    curr_mean: number;
    mean_shift: number;
    ref_std: number;
    curr_std: number;
    std_shift: number;
  }>;
  drifted_features: Array<{ feature: string; metric: string; value: number }>;
}

export interface TaskStatus {
  task_id: string;
  status: string;
  progress?: number;
  result?: Record<string, any>;
}

export interface ExplainResult {
  explanations: Array<{
    prediction: string;
    confidence: number | null;
    feature_contributions: Array<{
      feature: string;
      value: number;
      contribution: number;
      direction: 'positive' | 'negative';
    }>;
    base_value: number;
  }>;
  global_importance: Record<string, number>;
  feature_names: string[];
}

export interface AutoMLResult {
  task_id: string | null;
  experiment_id: string;
  message: string;
  status: string;
}

export interface DataQualityReport {
  id: string;
  dataset_id: string;
  status: 'passed' | 'failed';
  total_checks: number;
  passed_checks: number;
  failed_checks: number;
  score: number;
  checks: Array<{
    name: string;
    status: string;
    message: string;
    details: Record<string, any>;
  }>;
  created_at: string;
}

export interface BatchJob {
  id: string;
  name: string;
  model_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  input_file_path: string | null;
  output_file_path: string | null;
  total_rows: number;
  processed_rows: number;
  failed_rows: number;
  avg_latency_ms: number;
  results_summary: Record<string, any>;
  error_message: string | null;
  task_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, any>;
  ip_address: string | null;
  created_at: string;
}

export interface BenchmarkResult {
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  throughput_rps: number;
  accuracy?: number;
  f1?: number;
}

export interface PruneResult {
  total_features: number;
  kept_features: number;
  pruned_features: number;
  importance_threshold: number;
  feature_importances: Record<string, number>;
  kept: string[];
  pruned: string[];
}

export interface ABTestMetrics {
  test_id: string;
  model_a_requests: number;
  model_b_requests: number;
  model_a_accuracy: number;
  model_b_accuracy: number;
  statistical_test: {
    test_name: string;
    statistic: number;
    p_value: number;
    significant: boolean;
    confidence_level: number;
    model_a_value: number;
    model_b_value: number;
    winner: string | null;
  } | null;
  confidence_level: number;
  duration_hours: number | null;
}
