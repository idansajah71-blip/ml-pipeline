import axios from 'axios';
import { LoginPayload, RegisterPayload, TokenResponse, Stats, Dataset, MLModel, Experiment, ABTest, PredictionFeedbackResponse } from '@/types';

declare module 'axios' {
  interface AxiosRequestConfig {
    _retry?: boolean;
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

const HTTP_STATUS_MESSAGES: Record<number, string> = {
  400: 'Permintaan tidak valid. Periksa kembali data yang dikirim.',
  401: 'Sesi Anda sudah berakhir atau tidak valid. Silakan masuk kembali.',
  403: 'Anda tidak memiliki izin untuk mengakses sumber daya ini.',
  404: 'Data yang Anda cari tidak ditemukan.',
  405: 'Metode permintaan tidak didukung.',
  408: 'Waktu tunggu permintaan habis. Silakan coba lagi.',
  409: 'Terjadi konflik data. Periksa kembali permintaan Anda.',
  413: 'File yang diunggah terlalu besar.',
  415: 'Format file tidak didukung.',
  422: 'Data yang dikirim tidak valid. Periksa kembali isian Anda.',
  429: 'Terlalu banyak permintaan dalam waktu singkat. Silakan tunggu sebentar lalu coba lagi.',
  500: 'Terjadi kesalahan internal pada sistem. Tim kami telah mendapat notifikasi.',
  502: 'Layanan sedang sibuk atau tidak tersedia. Silakan coba lagi.',
  503: 'Layanan sedang tidak tersedia. Silakan coba lagi sebentar lagi.',
  504: 'Waktu tunggu layanan habis. Silakan coba lagi.',
};

export function formatApiError(err: unknown, fallback = 'Terjadi kesalahan'): string {
  if (!err) return fallback;
  const data = (err as any)?.response?.data;
  const status = (err as any)?.response?.status;
  const statusMsg = status ? HTTP_STATUS_MESSAGES[status] : undefined;

  // Pesan detail dari backend sudah diterjemahkan — jangan tambahkan kode HTTP mentah.
  if (typeof data?.detail === 'string' && data.detail) {
    return data.detail;
  }
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((d: any) => {
        const loc = d?.loc ? `[${String(d.loc).replace(/,/g, ' -> ')}] ` : '';
        return `${loc}${d?.msg ?? String(d)}`;
      })
      .join('; ');
  }
  if (data?.rule && data?.matched) {
    return `Request diblokir: ${data.detail}. Aturan=${data.rule}.`;
  }
  if (data?.errors && Array.isArray(data.errors)) {
    return data.errors.map(String).join('; ');
  }
  const msg = (err as any)?.message;
  if (msg && msg !== 'Request failed with status code 400') {
    return msg;
  }
  // Tidak ada detail → gunakan terjemahan kode HTTP, bukan kode mentah.
  if (statusMsg) return statusMsg;
  if (status) return `${fallback} (HTTP ${status})`;
  return fallback;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const res = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const newToken = res.data.access_token;
          const newRefresh = res.data.refresh_token;
          localStorage.setItem('token', newToken);
          localStorage.setItem('refresh_token', newRefresh);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        } catch {
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
      } else {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const auth = {
  login: (data: LoginPayload) => api.post<TokenResponse>('/auth/login', data),
  register: (data: RegisterPayload) => api.post<TokenResponse>('/auth/register', data),
  refresh: (refreshToken: string) => api.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }),
  me: () => api.get('/auth/me'),
};

export const datasets = {
  list: () => api.get<Dataset[]>('/datasets'),
  get: (id: string) => api.get<Dataset>(`/datasets/${id}`),

  upload: (formData: FormData) =>
    api.post<Dataset>('/datasets', formData),

  update: (id: string, data: Partial<Pick<Dataset, 'name' | 'description' | 'target_column' | 'tags'>>) =>
    api.put<Dataset>(`/datasets/${id}`, data),

  preview: (id: string) => api.get(`/datasets/${id}/preview`),
  profile: (id: string, targetColumn?: string) => {
    const params = targetColumn ? `?target_column=${targetColumn}` : '';
    return api.get(`/datasets/${id}/profile${params}`);
  },
  delete: (id: string) => api.delete(`/datasets/${id}`),
  trash: () => api.get<Dataset[]>('/datasets/trash'),
  restore: (id: string) => api.post(`/datasets/${id}/restore`, null),
  importGoogleSheet: (formData: FormData) =>
    api.post<Dataset>('/datasets/import/google-sheet', formData),
};

export const models = {
  list: () => api.get<{ total: number; items: MLModel[] }>('/models'),
  systemList: () => api.get<{ total: number; items: MLModel[] }>('/models/system'),
  get: (id: string) => api.get<MLModel>(`/models/${id}`),
  create: (data: { name: string; algorithm: string; target_column: string; description?: string }) =>
    api.post<MLModel>('/models', data),
  train: (id: string, data: { dataset_id: string; algorithm: string; target_column?: string; parameters?: Record<string, any>; async_training?: boolean }) =>
    api.post(`/models/${id}/train`, data),
  predict: (id: string, data: { data: Record<string, any>[] }) =>
    api.post(`/models/${id}/predict`, data),
  batchPredict: (id: string, data: { data: Record<string, any>[] }) =>
    api.post(`/models/${id}/predict/batch`, data),
  feedbackPrediction: (id: string, predictionId: string, data: { correct: boolean; comment?: string }) =>
    api.post<PredictionFeedbackResponse>(`/models/${id}/predict/${predictionId}/feedback`, data),
  deploy: (id: string) => api.post(`/models/${id}/deploy`),
  delete: (id: string) => api.delete(`/models/${id}`),
  trash: () => api.get<MLModel[]>('/models/trash'),
  restore: (id: string) => api.post(`/models/${id}/restore`, null),
  stage: (id: string, data: { stage: string }) =>
    api.post(`/models/${id}/stage`, data),
  rollback: (id: string) => api.post(`/models/${id}/rollback`),
  card: (id: string) => api.get(`/models/${id}/card`),
  updateCard: (id: string, data: { model_card: Record<string, any> }) =>
    api.put(`/models/${id}/card`, data),
  explain: (id: string, data: { data: Record<string, any>[]; top_k?: number }) =>
    api.post(`/models/${id}/explain`, data),
  taskStatus: (taskId: string) => api.get(`/models/tasks/${taskId}`),
  automl: (data: { dataset_id: string; target_column: string; algorithms?: string[] }) =>
    api.post('/models/automl', data),
  compare: (modelAId: string, modelBId: string) =>
    api.get(`/models/compare/${modelAId}/${modelBId}`),
};

export const experiments = {
  list: (params?: { algorithm?: string; status?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.algorithm) searchParams.set('algorithm', params.algorithm);
    if (params?.status) searchParams.set('status', params.status);
    const query = searchParams.toString();
    return api.get<{ total: number; items: Experiment[] }>(`/experiments${query ? `?${query}` : ''}`);
  },
  get: (id: string) => api.get<Experiment>(`/experiments/${id}`),
  metrics: (id: string) => api.get(`/experiments/${id}/metrics`),
  logs: (id: string) => api.get(`/experiments/${id}/logs`),
  compare: (experimentIds: string[]) =>
    api.post('/experiments/compare', { experiment_ids: experimentIds }),
};

export const abTests = {
  list: () => api.get<{ total: number; items: ABTest[] }>('/ab-tests'),
  get: (id: string) => api.get<ABTest>(`/ab-tests/${id}`),
  create: (data: { name: string; model_a_id: string; model_b_id: string; traffic_split?: number }) =>
    api.post<ABTest>('/ab-tests', data),
  update: (id: string, data: Partial<ABTest>) => api.put(`/ab-tests/${id}`, data),
  metrics: (id: string, confidenceLevel?: number) => {
    const params = confidenceLevel ? `?confidence_level=${confidenceLevel}` : '';
    return api.get(`/ab-tests/${id}/metrics${params}`);
  },
  route: (id: string) => api.post(`/ab-tests/${id}/route`),
  record: (id: string, group: string, correct: boolean) =>
    api.post(`/ab-tests/${id}/record`, null, { params: { group, correct } }),
};

export interface SystemHealthComponent {
  name: string;
  status: 'ok' | 'degraded' | 'error';
  detail: string;
  latency_ms?: number | null;
  detail_error?: string;
  worker_count?: number;
  artifact_count?: number;
  used_pct?: number | null;
  [key: string]: any;
}

export interface SystemHealth {
  status: 'ok' | 'degraded' | 'error';
  checked_at: string;
  environment: string;
  app_version: string;
  components: SystemHealthComponent[];
  summary: { total: number; ok: number; degraded: number; error: number };
}

export const systemHealth = {
  check: () => api.get<SystemHealth>('/admin/system-health'),
};

export const monitoring = {
  stats: () => api.get<Stats>('/monitoring/stats'),
  system: () => api.get('/monitoring/system'),
  modelMetrics: (id: string) => api.get(`/monitoring/model/${id}/metrics`),
  modelPerformance: (id: string, hours: number = 24) =>
    api.get(`/monitoring/model/${id}/performance?hours=${hours}`),
  predictionHistory: (data: {
    model_id?: string;
    start_date?: string;
    end_date?: string;
    prediction_value?: string;
    min_confidence?: number;
    skip?: number;
    limit?: number;
  }) => api.post('/monitoring/predictions/history', data),
  predictionStats: (modelId?: string, hours: number = 24) => {
    const params = new URLSearchParams({ hours: String(hours) });
    if (modelId) params.set('model_id', modelId);
    return api.get(`/monitoring/predictions/stats?${params.toString()}`);
  },
  alerts: () => api.get('/monitoring/alerts'),
  retrain: (modelId: string) => api.post(`/monitoring/retrain/${modelId}`),
};

export const notifications = {
  dataDrift: (data: { reference_dataset_id: string; current_dataset_id: string; target_column?: string; threshold_psi?: number; threshold_ks?: number }) =>
    api.post('/notifications/data-drift', data),
  driftCheck: (data: { model_id: string; reference_window?: number; current_window?: number; threshold?: number }) =>
    api.post('/notifications/drift-check', data),
};

export const algorithms = {
  list: () => api.get<{ classification: { algorithms: string[]; default_params: Record<string, any> }; regression: { algorithms: string[]; default_params: Record<string, any> } }>('/algorithms'),
};

export const mlOps = {
  validateDataset: (datasetId: string, config?: Record<string, any>) =>
    api.post(`/ml-ops/datasets/${datasetId}/validate`, config || {}),
  qualityReport: (datasetId: string) =>
    api.get(`/ml-ops/datasets/${datasetId}/quality`),
  createBatchJob: (data: { name: string; model_id: string; input_file_path: string }) =>
    api.post('/ml-ops/batch-jobs', data),
  listBatchJobs: () => api.get('/ml-ops/batch-jobs'),
  batchJob: (id: string) => api.get(`/ml-ops/batch-jobs/${id}`),
  batchJobDownload: (id: string) => `/api/v1/ml-ops/batch-jobs/${id}/download`,
  auditLogs: (params?: { action?: string; resource_type?: string; skip?: number; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.action) searchParams.set('action', params.action);
    if (params?.resource_type) searchParams.set('resource_type', params.resource_type);
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return api.get(`/ml-ops/audit-logs${query ? `?${query}` : ''}`);
  },
  benchmarkModel: (id: string, nSamples?: number) =>
    api.post(`/models/${id}/benchmark`, null, { params: { n_samples: nSamples || 100 } }),
  pruneModel: (id: string, threshold?: number) =>
    api.post(`/models/${id}/prune`, null, { params: { importance_threshold: threshold || 0.01 } }),
  exportModel: (id: string, format?: string) =>
    api.post(`/models/${id}/export`, null, { params: { format: format || 'joblib' } }),
};

export const featureStore = {
  listGroups: () => api.get('/feature-store/groups'),
  createGroup: (data: { name: string; description?: string; tags?: string[] }) =>
    api.post('/feature-store/groups', data),
  listFeatures: (groupId: string) => api.get(`/feature-store/groups/${groupId}/features`),
  addFeature: (groupId: string, data: { name: string; data_type: string; description?: string }) =>
    api.post(`/feature-store/groups/${groupId}/features`, data),
  ingest: (groupId: string, data: { row_key: string; features: Record<string, any> }) =>
    api.post(`/feature-store/groups/${groupId}/ingest`, data),
  get: (groupId: string, rowKey: string) =>
    api.get(`/feature-store/groups/${groupId}/get/${rowKey}`),
  getBatch: (groupId: string, rowKeys: string[]) =>
    api.post(`/feature-store/groups/${groupId}/get-batch`, rowKeys),
};

export const serving = {
  listEndpoints: () => api.get('/serving/endpoints'),
  createEndpoint: (data: { name: string; model_id: string; description?: string; cache_ttl_seconds?: number }) =>
    api.post('/serving/endpoints', data),
  predict: (endpointId: string, data: Record<string, any>) =>
    api.post(`/serving/endpoints/${endpointId}/predict`, { data }),
  predictBatch: (endpointId: string, inputs: Record<string, any>[]) =>
    api.post(`/serving/endpoints/${endpointId}/predict-batch`, { inputs }),
  metrics: (endpointId: string, hours?: number) =>
    api.get(`/serving/endpoints/${endpointId}/metrics`, { params: { hours: hours || 24 } }),
  delete: (endpointId: string) => api.delete(`/serving/endpoints/${endpointId}`),
};

export const organizations = {
  list: () => api.get('/orgs'),
  create: (data: { name: string; slug: string }) => api.post('/orgs', data),
  get: (id: string) => api.get(`/orgs/${id}`),
  listMembers: (id: string) => api.get(`/orgs/${id}/members`),
  addMember: (orgId: string, userId: string, role?: string) =>
    api.post(`/orgs/${orgId}/members`, null, { params: { user_id: userId, role: role || 'member' } }),
  removeMember: (orgId: string, userId: string) =>
    api.delete(`/orgs/${orgId}/members/${userId}`),
};

export const quota = {
  get: () => api.get('/quota'),
  check: () => api.get('/quota/check'),
  setTier: (tier: string) => api.put('/quota/tier', { tier }),
};

export const recommendations = {
  analyze: (datasetId: string, targetColumn: string) =>
    api.get(`/recommendations/${datasetId}/analyze`, { params: { target_column: targetColumn } }),
};

export const modelVersions = {
  create: (data: { model_id: string; changelog?: string }) =>
    api.post('/model-versions', data),
  listByModel: (modelId: string) => api.get(`/model-versions/model/${modelId}`),
  get: (id: string) => api.get(`/model-versions/${id}`),
  promote: (id: string) => api.put(`/model-versions/${id}/promote`),
  lineage: (modelId: string) => api.get(`/model-versions/lineage/${modelId}`),
  createLineage: (data: { model_id: string; parent_model_id?: string; relationship_type: string }) =>
    api.post('/model-versions/lineage', data),
  artifacts: (modelId: string) => api.get(`/model-versions/artifacts/${modelId}`),
};

export const experimentCompare = {
  compare: (experimentIds: string[]) =>
    api.post('/experiment-compare', experimentIds),
  leaderboard: (algorithm?: string) =>
    api.get('/experiment-compare/leaderboard', { params: algorithm ? { algorithm } : {} }),
};

export const featureMonitoring = {
  alerts: (params?: { severity?: string; acknowledged?: number }) =>
    api.get('/feature-monitoring/alerts', { params }),
  acknowledgeAlert: (id: string) => api.post(`/feature-monitoring/alerts/${id}/acknowledge`),
  featureStats: (name: string, hours?: number) =>
    api.get(`/feature-monitoring/stats/${name}`, { params: { hours: hours || 24 } }),
  checkDrift: (data: { feature_name: string; current_value: number; baseline_mean: number; baseline_std: number }) =>
    api.post('/feature-monitoring/check', null, { params: data }),
};

export const webhooksApi = {
  list: () => api.get('/webhooks'),
  create: (data: { name: string; url: string; events: string[]; secret?: string }) =>
    api.post('/webhooks', data),
  delete: (id: string) => api.delete(`/webhooks/${id}`),
  logs: (id: string) => api.get(`/webhooks/${id}/logs`),
};

export const lineage = {
  create: (data: { source_type: string; source_id: string; target_type: string; target_id: string; transformation?: string }) =>
    api.post('/lineage', data),
  graph: (nodeType: string, nodeId: string, depth?: number) =>
    api.get(`/lineage/graph/${nodeType}/${nodeId}`, { params: { depth: depth || 3 } }),
  listMetrics: () => api.get('/lineage/metrics'),
  createMetric: (data: { name: string; metric_type: string; query_or_formula: string }) =>
    api.post('/lineage/metrics', data),
  recordMetric: (metricId: string, data: { value: number; labels?: Record<string, any> }) =>
    api.post(`/lineage/metrics/${metricId}/data`, data),
  metricData: (metricId: string) => api.get(`/lineage/metrics/${metricId}/data`),
};

export const explainDashboard = {
  global: (modelId: string, nSamples?: number) =>
    api.post('/explain/global', { model_id: modelId, n_samples: nSamples || 100 }),
  prediction: (modelId: string, data: Record<string, any>) =>
    api.post('/explain/prediction', null, { params: { model_id: modelId }, data }),
};

export const ensembleApi = {
  list: () => api.get('/ensemble'),
  create: (data: { name: string; model_ids: string[]; strategy?: string; weights?: Record<string, number> }) =>
    api.post('/ensemble', data),
  predict: (ensembleId: string, data: Record<string, any>) =>
    api.post('/ensemble/predict', { ensemble_id: ensembleId, data }),
};

export const dataVersions = {
  create: (datasetId: string, changelog?: string) =>
    api.post('/data-versions', { dataset_id: datasetId, changelog }),
  listByDataset: (datasetId: string) => api.get(`/data-versions/dataset/${datasetId}`),
  get: (id: string) => api.get(`/data-versions/${id}`),
};

export const marketplaceApi = {
  categories: () => api.get('/marketplace/categories'),
  discover: (params?: { tag?: string; search?: string; category?: string; is_platform?: boolean }) =>
    api.get('/marketplace/discover', { params }),
  platformModels: () => api.get('/marketplace/platform-models'),
  getModel: (shareId: string) => api.get(`/marketplace/${shareId}`),
  share: (data: { model_id: string; is_public?: boolean; tags?: string[]; permission?: string }) =>
    api.post('/marketplace/share', data),
  download: (shareId: string) => api.post(`/marketplace/${shareId}/download`),
  rate: (shareId: string, rating: number, review?: string) =>
    api.post(`/marketplace/${shareId}/rate`, { rating, review }),
  matchColumns: (shareId: string, userColumns: string[]) =>
    api.post('/marketplace/column-match', { share_id: shareId, user_columns: userColumns }),
  platformPredict: (data: { share_id: string; data: Record<string, any>[]; column_mapping?: Record<string, string> }) =>
    api.post('/marketplace/platform-predict', data),
};

export const costTracking = {
  record: (data: { resource_type: string; cost_usd: number; usage_hours?: number; gpu_hours?: number }) =>
    api.post('/costs', data),
  summary: (days?: number) => api.get('/costs/summary', { params: { days: days || 30 } }),
  byModel: () => api.get('/costs/by-model'),
};

export const mlflowApi = {
  status: () => api.get('/mlflow/status'),
  runs: (maxResults?: number) => api.get('/mlflow/runs', { params: { max_results: maxResults || 10 } }),
  logRun: (data: { model_id: string; parameters?: Record<string, any>; metrics?: Record<string, any>; tags?: Record<string, string> }) =>
    api.post('/mlflow/log', data),
};

export const benchmarkApi = {
  run: (modelId: string) => api.post(`/benchmark/${modelId}`),
};

export const dataValidationApi = {
  validate: (datasetId: string, targetColumn?: string) => {
    const params = targetColumn ? `?target_column=${targetColumn}` : '';
    return api.post(`/data-validation/${datasetId}/validate${params}`);
  },
  driftDetect: (refId: string, curId: string) =>
    api.post('/data-validation/drift-detect', null, { params: { reference_dataset_id: refId, current_dataset_id: curId } }),
  quality: (datasetId: string) => api.post(`/data-validation/${datasetId}/quality`),
};

export const websocket = {
  training: (experimentId: string): WebSocket => {
    const wsUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');
    return new WebSocket(`${wsUrl}/ws/training/${experimentId}`);
  },
};

export interface ExternalDataSource {
  id: string;
  name: string;
  slug: string;
  source_type: string;
  license: string | null;
  is_active: boolean;
  requires_api_key?: boolean;
}

export interface ExternalSearchResult {
  id: string;
  source_slug: string;
  title: string;
  description: string;
  row_count: number | null;
  column_names: string[];
  last_updated: string | null;
  source_url: string | null;
}

export interface ExternalDataPreview {
  columns: string[];
  row_count: number;
  preview: Record<string, any>[];
  license: string;
}

export const externalData = {
  sources: () => api.get<ExternalDataSource[]>('/external-data/sources'),
  search: (query: string, source?: string, limit?: number) => {
    const params: Record<string, any> = { q: query };
    if (source) params.source = source;
    if (limit) params.limit = limit;
    return api.get<ExternalSearchResult[]>('/external-data/search', { params });
  },
  preview: (resultId: string, sourceSlug: string) =>
    api.get<ExternalDataPreview>(`/external-data/${resultId}/preview`, { params: { source_slug: sourceSlug } }),
  import: (data: { result_id: string; source_slug: string; title: string; description?: string }) =>
    api.post<{ dataset_id: string; message: string }>('/external-data/import', data),
};

export interface ScrapeJob {
  id: string;
  url: string;
  title: string | null;
  status: string;
  raw_row_count: number;
  clean_row_count: number;
  column_count: number;
  duplicates_removed: number;
  tables_data: any[];
  columns_typed: Record<string, string>;
  columns_renamed: Record<string, string>;
  quality_score: number;
  quality_issues: string[];
  clusters: Record<string, any>;
  ml_processing_applied: string[];
  advanced_analysis: Record<string, any> | null;
  sentiment_analysis: Record<string, any> | null;
  pattern_analysis: Record<string, any> | null;
  scrape_metadata: Record<string, any> | null;
  scrape_type: string | null;
  error_message: string | null;
  created_at: string | null;
  scraped_at: string | null;
  processed_at: string | null;
}

export interface ScrapePreview {
  title: string;
  tables: { headers: string[]; rows: Record<string, string>[]; row_count: number }[];
  lists: string[][];
  metadata: Record<string, any>;
  row_count: number;
  column_count: number;
  content_hash: string;
  links: string[];
  images: { src: string; alt: string }[];
  json_ld: Record<string, any>[];
  feeds: string[];
  api_endpoints: { url: string; type: string }[];
  open_graph: Record<string, string>;
  keywords: string[];
  language: string;
  word_count: number;
  reading_time_minutes: number;
  scrape_duration_ms: number;
}

export interface AdvancedAnalysis {
  row_count: number;
  column_count: number;
  memory_usage_mb: number;
  total_null_pct: number;
  duplicate_rows: number;
  duplicate_pct: number;
  columns: {
    name: string;
    dtype: string;
    null_pct: number;
    unique_count: number;
    is_numeric: boolean;
    is_categorical: boolean;
    is_datetime: boolean;
    is_text: boolean;
    is_id_like: boolean;
    stats: Record<string, any>;
    distribution: Record<string, any>;
    sample_values: string[];
    top_values: { value: string; count: number; pct?: number }[];
    entropy: number;
    recommendation: string;
  }[];
  correlations: {
    strong_pairs: { col_1: string; col_2: string; correlation: number; strength: string }[];
  };
  outlier_summary: { columns: Record<string, any>; total_outlier_rows: number };
  time_series_analysis: Record<string, any>;
  text_analysis: Record<string, any>;
  categorical_analysis: Record<string, any>;
  data_quality_score: number;
  quality_issues: string[];
  recommendations: string[];
  insights: string[];
  auto_viz_suggestions: string[];
  summary: string;
}

export interface SentimentAnalysis {
  overall_score: number;
  overall_label: string;
  total_texts: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  distribution: { positive_pct: number; negative_pct: number; neutral_pct: number };
  top_positive_words: { word: string; count: number }[];
  top_negative_words: { word: string; count: number }[];
  column_sentiments: Record<string, any>;
  summary: string;
}

export interface PatternAnalysis {
  patterns_found: number;
  regex_patterns: { column: string; pattern: string; match_count: number; match_pct: number }[];
  value_patterns: { column: string; type: string; insight: string }[];
  structure_patterns: { column: string; format: string; pct: number }[];
  anomaly_patterns: { column: string; type: string; insight: string }[];
  text_patterns: { column: string; type: string; insight: string }[];
  encoding_patterns: { column: string; type: string; insight: string }[];
  summary: string;
}

export const scraping = {
  preview: (url: string) =>
    api.post<ScrapePreview>('/scraping/preview', { url }),
  scrapeAndProcess: (data: {
    url: string;
    auto_rename?: boolean;
    deduplicate?: boolean;
    detect_types?: boolean;
    cluster_text?: boolean;
    run_advanced_analysis?: boolean;
    run_sentiment?: boolean;
    run_patterns?: boolean;
    use_selenium?: boolean;
  }) => api.post<ScrapeJob>('/scraping/scrape-and-process', data),
  batchScrape: (data: {
    urls: string[];
    extract_tables?: boolean;
    extract_lists?: boolean;
    run_advanced_analysis?: boolean;
    run_sentiment?: boolean;
    run_patterns?: boolean;
    max_concurrent?: number;
    use_selenium?: boolean;
  }) => api.post<ScrapeJob>('/scraping/batch', data),
  recursiveScrape: (data: {
    url: string;
    max_depth?: number;
    max_pages?: number;
    run_advanced_analysis?: boolean;
    use_selenium?: boolean;
  }) => api.post<ScrapeJob>('/scraping/recursive', data),
  discoverScrape: (data: {
    url: string;
    max_pages?: number;
    run_advanced_analysis?: boolean;
    use_selenium?: boolean;
  }) => api.post<ScrapeJob>('/scraping/discover', data),
  jobs: (limit?: number, scrapeType?: string) =>
    api.get<ScrapeJob[]>('/scraping/jobs', { params: { limit: limit || 20, scrape_type: scrapeType } }),
  getJob: (jobId: string) =>
    api.get<ScrapeJob>(`/scraping/jobs/${jobId}`),
  importToDataset: (data: { job_id: string; dataset_name?: string; description?: string }) =>
    api.post<{ dataset_id: string; name: string; row_count: number; column_count: number; message: string }>(
      '/scraping/import', data
    ),
  deleteJob: (jobId: string) =>
    api.delete(`/scraping/jobs/${jobId}`),
  jsScrape: (data: { url: string; use_selenium?: boolean; wait_seconds?: number }) =>
    api.post('/scraping/js-scrape', data),
  smartExtract: (data: { url: string; css_selector?: string; use_selenium?: boolean }) =>
    api.post('/scraping/smart-extract', data),
  analyzeUrl: (url: string) =>
    api.get('/scraping/analyze-url', { params: { url } }),
  exportData: (data: { job_id: string; formats: string[] }) =>
    api.post('/scraping/export', data),
  exportStats: (jobId: string) =>
    api.get(`/scraping/export-stats/${jobId}`),
  getOperations: () =>
    api.get('/scraping/operations'),
  transformData: (data: { job_id: string; rules: { column: string; operation: string; params?: any }[] }) =>
    api.post('/scraping/transform', data),
  autoClean: (jobId: string) =>
    api.post(`/scraping/auto-clean?job_id=${jobId}`),
  dedupData: (data: { job_ids: string[]; method?: string; key_columns?: string[]; threshold?: number }) =>
    api.post('/scraping/dedup', data),
  templates: {
    list: (q?: string) =>
      api.get('/scraping/templates', { params: q ? { q } : {} }),
    get: (id: string) =>
      api.get(`/scraping/templates/${id}`),
    create: (data: any) =>
      api.post('/scraping/templates', data),
    update: (id: string, data: any) =>
      api.put(`/scraping/templates/${id}`, data),
    delete: (id: string) =>
      api.delete(`/scraping/templates/${id}`),
    clone: (id: string, name?: string) =>
      api.post(`/scraping/templates/${id}/clone`, null, { params: name ? { new_name: name } : {} }),
    popular: () =>
      api.get('/scraping/templates/popular'),
  },
  schedules: {
    list: () =>
      api.get('/scraping/schedules'),
    create: (data: any) =>
      api.post('/scraping/schedules', data),
    trigger: (id: string, urls: string[], config?: any) =>
      api.post(`/scraping/schedules/${id}/trigger`, { urls, config }),
  },
  getTaskStatus: (taskId: string) =>
    api.get(`/scraping/tasks/${taskId}`),
  cancelTask: (taskId: string) =>
    api.delete(`/scraping/tasks/${taskId}`),

  // Ultra Scraping
  authScrape: (data: any) =>
    api.post('/scraping/auth-scrape', data),
  fingerprintScrape: (data: any) =>
    api.post('/scraping/fingerprint-scrape', data),
  generateFingerprint: () =>
    api.get('/scraping/fingerprint/generate'),
  generateFingerprints: (count: number = 5) =>
    api.post(`/scraping/fingerprint/batch?count=${count}`),
  configureRateLimit: (domain: string, delay_ms: number, respect_robots: boolean) =>
    api.post(`/scraping/rate-limit/configure?domain=${domain}`, { delay_ms, respect_robots }),
  getRateLimitStats: () =>
    api.get('/scraping/rate-limit/stats'),
  diffScrapes: (data: any) =>
    api.post('/scraping/diff', data),
  configureWebhook: (data: any) =>
    api.post('/scraping/webhooks/configure', data),
  testWebhook: (name: string) =>
    api.post(`/scraping/webhooks/test?name=${name}`),
  getWebhookHistory: (limit: number = 20) =>
    api.get(`/scraping/webhooks/history?limit=${limit}`),
  createDistributedJob: (data: any) =>
    api.post('/scraping/distributed/create', data),
  executeDistributed: (jobId: string) =>
    api.post(`/scraping/distributed/execute/${jobId}`),
  getDistributedStatus: (jobId: string) =>
    api.get(`/scraping/distributed/status/${jobId}`),
  getDistributedWorkers: () =>
    api.get('/scraping/distributed/workers'),
  getDistributedQueue: () =>
    api.get('/scraping/distributed/queue'),
  validateData: (data: any) =>
    api.post('/scraping/validate', data),
  runAutoML: (data: any) =>
    api.post('/scraping/automl', data),
  profileData: (jobId: string) =>
    api.post(`/scraping/automl/profile?job_id=${jobId}`),
  detectAnomalies: (data: any) =>
    api.post('/scraping/anomaly', data),
  forecastData: (data: any) =>
    api.post('/scraping/forecast', data),
  clusterData: (data: any) =>
    api.post('/scraping/cluster', data),
  reduceDimensions: (data: any) =>
    api.post('/scraping/dim-reduce', data),
  engineerFeatures: (data: any) =>
    api.post('/scraping/feature-engineer', data),
  enrichData: (data: any) =>
    api.post('/scraping/enrich', data),
  targetScrape: (data: any) =>
    api.post('/scraping/target-scrape', data),
  targetSearch: (data: any) =>
    api.post('/scraping/target-scrape/search', data),
};

export const inAppNotifications = {
  list: (params?: { skip?: number; limit?: number; unread_only?: boolean }) => {
    const searchParams = new URLSearchParams();
    if (params?.skip) searchParams.set('skip', String(params.skip));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.unread_only) searchParams.set('unread_only', 'true');
    const query = searchParams.toString();
    return api.get<{ notifications: import('@/types').Notification[]; total: number; unread_count: number }>(
      `/in-app-notifications${query ? `?${query}` : ''}`
    );
  },
  unreadCount: () => api.get<{ unread_count: number }>('/in-app-notifications/unread-count'),
  markRead: (id: string) => api.put(`/in-app-notifications/${id}/read`),
  markAllRead: () => api.put('/in-app-notifications/read-all'),
  delete: (id: string) => api.delete(`/in-app-notifications/${id}`),
};

export const marketplaceStats = {
  myModels: () => api.get<import('@/types').ModelUsageStats>('/marketplace/my-models/stats'),
  contributorStats: () => api.get<import('@/types').ContributorStats>('/marketplace/contributor-stats'),
  quickFeedback: (data: { model_id: string; is_correct: boolean; comment?: string; prediction_id?: string }) =>
    api.post('/marketplace/quick-feedback', data),
};

export default api;
