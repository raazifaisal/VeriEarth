import axios from 'axios';
import type {
  Facility,
  Shipment,
  Route,
  DashboardKPIs,
  EnrichmentProgress,
  IngestResult,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// CSRF token storage
let csrfToken: string | null = null;

// Function to get CSRF token
async function getCsrfToken(forceRefresh: boolean = false): Promise<string> {
  if (!csrfToken || forceRefresh) {
    try {
      const response = await axios.get(`${API_BASE}/csrf-token`, {
        withCredentials: true,
      });
      csrfToken = response.data.csrf_token;
    } catch (error) {
      console.error('Failed to get CSRF token:', error);
      throw error;
    }
  }
  return csrfToken as string;
}

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor to add CSRF token
apiClient.interceptors.request.use(
  async (config) => {
    // Add CSRF token for non-GET requests
    if (config.method && config.method.toLowerCase() !== 'get') {
      try {
        const token = await getCsrfToken();
        config.headers['X-CSRF-Token'] = token;
      } catch (error) {
        console.error('Failed to add CSRF token:', error);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors and retry CSRF failures
apiClient.interceptors.response.use(
  (response) => {
    // Refresh CSRF token after successful state-changing requests
    const method = response.config.method?.toLowerCase();
    if (method && method !== 'get') {
      // Asynchronously refresh the token for next request (don't await)
      getCsrfToken(true).catch(() => {
        // Ignore errors, token will be refreshed on next request
      });
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Handle CSRF token errors with retry
    if (error.response?.status === 403 && !originalRequest._retry) {
      const errorDetail = error.response?.data?.detail || '';
      if (errorDetail.includes('CSRF') || errorDetail.includes('token')) {
        console.log('CSRF token invalid, refreshing and retrying...');
        originalRequest._retry = true;
        
        try {
          // Clear and refresh token
          csrfToken = null;
          const newToken = await getCsrfToken(true);
          originalRequest.headers['X-CSRF-Token'] = newToken;
          
          // Retry the request
          return apiClient(originalRequest);
        } catch (refreshError) {
          return Promise.reject(refreshError);
        }
      }
    }
    
    // Handle unauthorized errors
    if (error.response?.status === 401 || error.response?.status === 403) {
      csrfToken = null; // Clear CSRF token on auth errors
      
      // Emit custom event for auth failure
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }
    }
    
    return Promise.reject(error);
  }
);

export const facilitiesApi = {
  list: async (orgId: string): Promise<Facility[]> => {
    const response = await apiClient.get(`/api/facilities`, {
      params: { org_id: orgId },
    });
    return response.data;
  },

  enrich: async (facilityId: string, orgId: string): Promise<void> => {
    await apiClient.post(
      `/api/supply-chain/facilities/${facilityId}/enrich-eo`,
      {},
      { params: { org_id: orgId } }
    );
  },

  enrichAll: async (orgId: string): Promise<void> => {
    await apiClient.post(`/api/supply-chain/organizations/${orgId}/enrich-all`);
  },

  getEnrichmentProgress: async (facilityId: string): Promise<EnrichmentProgress> => {
    const response = await apiClient.get(
      `/api/supply-chain/facilities/${facilityId}/enrichment-progress`
    );
    return response.data;
  },
};

export const shipmentsApi = {
  list: async (orgId: string): Promise<Shipment[]> => {
    const response = await apiClient.get(`/api/supply-chain/shipments`, {
      params: { org_id: orgId },
    });
    return response.data;
  },
};

export const routesApi = {
  list: async (orgId: string): Promise<Route[]> => {
    const response = await apiClient.get(`/api/supply-chain/routes`, {
      params: { org_id: orgId },
    });
    return response.data;
  },
};

export const dashboardApi = {
  getKPIs: async (orgId: string): Promise<DashboardKPIs> => {
    const response = await apiClient.get(`/api/dashboard/kpis`, {
      params: { org_id: orgId },
    });
    return response.data;
  },

  getEmissionsTrend: async (orgId: string) => {
    const response = await apiClient.get(`/api/dashboard/emissions-trend`, {
      params: { org_id: orgId },
    });
    return response.data;
  },

  getTransportDistribution: async (orgId: string) => {
    const response = await apiClient.get(`/api/dashboard/transport-distribution`, {
      params: { org_id: orgId },
    });
    return response.data;
  },

  getOrganizations: async () => {
    const response = await apiClient.get(`/auth/me`);
    return response.data.organizations || [];
  },

  createOrganization: async (name: string) => {
    const response = await apiClient.post(`/auth/organizations`, { name });
    return response.data;
  },
};

export const organizationApi = {
  get: async (orgId: string) => {
    const res = await apiClient.get(`/api/organizations/${orgId}`);
    return res.data as {
      id: string; name: string; industry?: string | null; description?: string | null; address?: string | null; details?: any;
    };
  },
  update: async (
    orgId: string,
    data: { name?: string; industry?: string; description?: string; address?: string; details?: any }
  ) => {
    const res = await apiClient.put(`/api/organizations/${orgId}`, data);
    return res.data;
  },
  setSudoPassword: async (
    orgId: string,
    payload: { password: string; current_password?: string | null }
  ) => {
    const res = await apiClient.post(`/api/organizations/${orgId}/sudo-password`, payload);
    return res.data;
  },
};

export const userApi = {
  updateProfile: async (data: { full_name?: string }) => {
    const res = await apiClient.put(`/auth/me`, data);
    return res.data;
  },
  changePassword: async (data: { current_password: string; new_password: string }) => {
    const res = await apiClient.post(`/auth/me/password`, data);
    return res.data;
  },
};

export const ingestionApi = {
  upload: async (file: File, entityType: string, orgId: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('entity', entityType);
    formData.append('org_id', orgId);

    const response = await apiClient.post('/api/ingestion/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  preview: async (file: File, entityType: string): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('entity', entityType);

    const response = await apiClient.post('/api/ingestion/preview', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  import: async (file: File, entityType: string, orgId: string): Promise<IngestResult> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('entity', entityType);
    formData.append('org_id', orgId);

    const response = await apiClient.post('/api/ingestion/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export const dataManagementApi = {
  getEntityData: async (entityType: string, orgId: string): Promise<any[]> => {
    const response = await apiClient.get(`/api/data/${entityType}`, {
      params: { org_id: orgId },
    });
    return response.data;
  },

  getStats: async (orgId: string): Promise<Record<string, number>> => {
    const response = await apiClient.get(`/api/data/stats`, {
      params: { org_id: orgId },
    });
    return response.data;
  },

  deleteEntity: async (entityType: string, id: string, orgId: string): Promise<void> => {
    await apiClient.delete(`/api/data/${entityType}/${id}`, {
      params: { org_id: orgId },
    });
  },

  clearAll: async (entityType: string, orgId: string): Promise<void> => {
    await apiClient.delete(`/api/data/${entityType}`, {
      params: { org_id: orgId },
    });
  },

  clearOrganization: async (orgId: string, password: string): Promise<{ status: string; message: string }> => {
    const response = await apiClient.post(`/api/data/organizations/${orgId}/clear-all`, { password });
    return response.data;
  },

  updateEntity: async (entityType: string, id: string, data: any, orgId: string): Promise<any> => {
    const response = await apiClient.put(`/api/data/${entityType}/${id}`, data, {
      params: { org_id: orgId },
    });
    return response.data;
  },
};

export const eoApi = {
  backfill: async (orgId: string): Promise<{ status: string; facilities: number; rows: number }> => {
    const response = await apiClient.post(`/api/supply-chain/organizations/${orgId}/eo/backfill`);
    return response.data;
  },
  availability: async (orgId: string): Promise<Array<{ facility_id: string; rows: number; min_ts: string | null; max_ts: string | null }>> => {
    const response = await apiClient.get(`/api/supply-chain/organizations/${orgId}/eo/available`);
    return response.data;
  },
  timeseries: async (
    orgId: string,
    facilityId: string,
    opts?: { date_from?: string; date_to?: string; limit?: number; offset?: number }
  ): Promise<Array<{ observed_at: string; aqi_score: number | null; no2: number | null; co: number | null; so2: number | null; o3: number | null; ch4: number | null; aod: number | null }>> => {
    const response = await apiClient.get(`/api/supply-chain/facilities/${facilityId}/eo`, {
      params: { org_id: orgId, ...(opts || {}) },
    });
    return response.data;
  },
  series: async (
    orgId: string,
    opts?: { facility_id?: string; date_from?: string; date_to?: string; order?: 'asc' | 'desc'; limit?: number; offset?: number }
  ): Promise<Array<{ facility_id: string; observed_at: string; aqi_score: number | null; no2: number | null; co: number | null; so2: number | null; o3: number | null; ch4: number | null; aod: number | null }>> => {
    const response = await apiClient.get(`/api/supply-chain/organizations/${orgId}/eo/series`, {
      params: opts || {},
    });
    return response.data;
  },
  clear: async (orgId: string, password: string): Promise<{ status: string; deleted: number }> => {
    const response = await apiClient.post(`/api/supply-chain/organizations/${orgId}/eo/clear`, { password });
    return response.data;
  },
};

export default apiClient;
