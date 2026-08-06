import axios from 'axios';
import { LoginPayload, RegisterPayload, TokenResponse, Stats, Dataset, MLModel, Experiment, ABTest } from '@/types';

declare module 'axios' {
  interface AxiosRequestConfig {
    _retry?: boolean;
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

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
    api.post<Dataset>('/datasets', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  preview: (id: string) => api.get(`/datasets/${id}/preview`),
  profile: (id: string, targetColumn?: string) => {
    const params = targetColumn ? `?target_column=${targetColumn}` : '';
    return api.get(`/datasets/${id}/profile${params}`);
  },
  delete: (id: string) => api.delete(`/datasets/${id}`),
  importGoogleSheet: (formData: FormData) =>
    api.post<Dataset>('/datasets/import/google-sheet', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
};

export const models = {
  list: () => api.get<{ total: number; items: MLModel[] }>('/models'),
  get: (id: string) => api.get<MLModel>(`/models/${id}`),
  create: (data: { name: string; algorithm: string; target_column: string; description?: string }) =>
    api.post<MLModel>('/models', data),
  train: (id: string, data: { dataset_id: string; algorithm: string; target_column?: string; parameters?: Record<string, any>; async_training?: boolean }) =>
    api.post(`/models/${id}/train`, data),
  predict: (id: string, data: { data: Record<string, any>[] }) =>
    api.post(`/models/${id}/predict`, data),
  batchPredict: (id: string, data: { data: Record<string, any>[] }) =>
    api.post(`/models/${id}/predict/batch`, data),
  deploy: (id: string) => api.post(`/models/${id}/deploy`),
  delete: (id: string) => api.delete(`/models/${id}`),
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
  discover: (tag?: string, search?: string) => {
    const params: any = {};
    if (tag) params.tag = tag;
    if (search) params.search = search;
    return api.get('/marketplace/discover', { params });
  },
  share: (data: { model_id: string; is_public?: boolean; tags?: string[] }) =>
    api.post('/marketplace/share', data),
  download: (shareId: string) => api.post(`/marketplace/${shareId}/download`),
  rate: (shareId: string, rating: number) => api.post(`/marketplace/${shareId}/rate`, null, { params: { rating } }),
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

export default api;
