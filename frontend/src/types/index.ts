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
