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
};

export const models = {
  list: () => api.get<{ total: number; items: MLModel[] }>('/models'),
  get: (id: string) => api.get<MLModel>(`/models/${id}`),
  create: (data: { name: string; algorithm: string; target_column: string; description?: string }) =>
    api.post<MLModel>('/models', data),
  train: (id: string, data: { dataset_id: string; algorithm: string; parameters?: Record<string, any>; async_training?: boolean }) =>
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
  list: () => api.get<{ algorithms: string[]; default_params: Record<string, any> }>('/algorithms'),
};

export const websocket = {
  training: (experimentId: string): WebSocket => {
    const wsUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');
    return new WebSocket(`${wsUrl}/ws/training/${experimentId}`);
  },
};

export default api;
