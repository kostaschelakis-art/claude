import axios from 'axios';
import type {
  User,
  GeneratedImage,
  GenerateRequest,
  ExportRequest,
  ImageReview,
  Template,
  Market,
  LegalDisclaimer,
  BrandGuideline,
  QAScore,
  DimensionPreset,
  DashboardStats,
  AuditLog,
} from '@/types';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('brandforge_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('brandforge_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth
export const auth = {
  login: async (email: string): Promise<{ access_token: string; user: User }> => {
    const { data } = await api.post('/auth/login', { email });
    return data;
  },
  getMe: async (): Promise<User> => {
    const { data } = await api.get('/auth/me');
    return data;
  },
};

// Images
export const images = {
  generate: async (request: GenerateRequest): Promise<GeneratedImage> => {
    const { data } = await api.post('/images/generate', request);
    return data;
  },
  getImage: async (id: string): Promise<GeneratedImage> => {
    const { data } = await api.get(`/images/${id}`);
    return data;
  },
  listImages: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
    market_id?: string;
  }): Promise<GeneratedImage[]> => {
    const { data } = await api.get('/images', { params });
    // Backend returns { items, total, limit, offset } — unwrap to array for
    // callers that expect a plain list.
    return (data && data.items) ? data.items : data;
  },
  reviewImage: async (id: string, review: ImageReview): Promise<GeneratedImage> => {
    const { data } = await api.post(`/images/${id}/review`, review);
    return data;
  },
  exportImage: async (
    id: string,
    format: string,
    width?: number,
    height?: number,
    quality?: number
  ): Promise<Blob> => {
    const { data } = await api.post(
      `/images/${id}/export`,
      { format, width, height, quality },
      { responseType: 'blob' }
    );
    return data;
  },
  getPresets: async (): Promise<DimensionPreset[]> => {
    const { data } = await api.get('/images/presets/dimensions');
    return data;
  },
};

// Templates
export const templates = {
  list: async (params?: {
    category?: string;
    skip?: number;
    limit?: number;
  }): Promise<Template[]> => {
    const { data } = await api.get('/templates', { params });
    // Backend returns { items, total, limit, offset } — unwrap to array.
    return (data && data.items) ? data.items : data;
  },
  create: async (templateData: Partial<Template>): Promise<Template> => {
    const { data } = await api.post('/templates', templateData);
    return data;
  },
  analyze: async (file: File): Promise<Template> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/templates/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
  getVariations: async (
    id: string,
    params?: { width?: number; height?: number }
  ): Promise<GeneratedImage[]> => {
    const { data } = await api.get(`/templates/${id}/variations`, { params });
    return (data && data.items) ? data.items : data;
  },
};

// Markets
export const markets = {
  list: async (): Promise<Market[]> => {
    const { data } = await api.get('/markets');
    return (data && data.items) ? data.items : data;
  },
  get: async (id: string): Promise<Market> => {
    const { data } = await api.get(`/markets/${id}`);
    return data;
  },
  update: async (id: string, marketData: Partial<Market>): Promise<Market> => {
    const { data } = await api.put(`/markets/${id}`, marketData);
    return data;
  },
  updateLegal: async (id: string, legal: LegalDisclaimer[]): Promise<Market> => {
    const { data } = await api.put(`/markets/${id}/legal`, { legal_disclaimers: legal });
    return data;
  },
};

// Brand
export const brand = {
  listGuidelines: async (): Promise<BrandGuideline[]> => {
    const { data } = await api.get('/brand/guidelines');
    return (data && data.items) ? data.items : data;
  },
  createGuideline: async (guidelineData: Partial<BrandGuideline>): Promise<BrandGuideline> => {
    const { data } = await api.post('/brand/guidelines', guidelineData);
    return data;
  },
  runQA: async (imageId: string): Promise<QAScore> => {
    const { data } = await api.post(`/brand/qa/${imageId}`);
    return data;
  },
  getQAResults: async (imageId: string): Promise<QAScore> => {
    const { data } = await api.get(`/brand/qa/${imageId}`);
    return data;
  },
  listAssets: async (): Promise<any[]> => {
    const { data } = await api.get('/brand/assets');
    return (data && data.items) ? data.items : data;
  },
  uploadAsset: async (file: File, category?: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    if (category) formData.append('category', category);
    const { data } = await api.post('/brand/assets', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },
};

// Dashboard
export const dashboard = {
  getStats: async (): Promise<DashboardStats> => {
    const { data } = await api.get('/dashboard/stats');
    return data;
  },
};

// Admin
export const admin = {
  listUsers: async (): Promise<User[]> => {
    const { data } = await api.get('/admin/users');
    return data;
  },
  updateUserRole: async (userId: string, role: string): Promise<User> => {
    const { data } = await api.put(`/admin/users/${userId}/role`, { role });
    return data;
  },
  getAuditLogs: async (params?: { skip?: number; limit?: number }): Promise<AuditLog[]> => {
    const { data } = await api.get('/admin/audit-logs', { params });
    return data;
  },
  getUsageMetrics: async (): Promise<any> => {
    const { data } = await api.get('/admin/usage');
    return data;
  },
};

export default api;
