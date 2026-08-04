import axios from 'axios';
import { LoginPayload, RegisterPayload, TokenResponse, Stats, Dataset, MLModel, Experiment, ABTest } from '@/types';

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
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
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
  delete: (id: string) => api.delete(`/datasets/${id}`),
};

export const models = {
  list: () => api.get<{ total: number; items: MLModel[] }>('/models'),
  get: (id: string) => api.get<MLModel>(`/models/${id}`),
  create: (data: { name: string; algorithm: string; target_column: string; description?: string }) =>
    api.post<MLModel>('/models', data),
  train: (id: string, data: { dataset_id: string; algorithm: string; parameters?: Record<string, any> }) =>
    api.post(`/models/${id}/train`, data),
  predict: (id: string, data: { data: Record<string, any>[] }) =>
    api.post(`/models/${id}/predict`, data),
  deploy: (id: string) => api.post(`/models/${id}/deploy`),
  delete: (id: string) => api.delete(`/models/${id}`),
};

export const experiments = {
  list: () => api.get<{ total: number; items: Experiment[] }>('/experiments'),
  get: (id: string) => api.get<Experiment>(`/experiments/${id}`),
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
};

export const algorithms = {
  list: () => api.get<{ algorithms: string[]; default_params: Record<string, any> }>('/algorithms'),
};

export default api;
