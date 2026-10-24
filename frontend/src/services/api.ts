const API_ORIGIN = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');
export const BASE_URL = `${API_ORIGIN}/api/v1`;

export class ApiError extends Error {
  status: number;
  details?: any;

  constructor(message: string, status: number, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('philomatrix_access_token');
  const institutionId = localStorage.getItem('philomatrix_institution_id');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(institutionId ? { 'X-Institution-ID': institutionId } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If unauthorized, clear token if expired
    if (!endpoint.includes('/auth/login')) {
      localStorage.removeItem('philomatrix_access_token');
      localStorage.removeItem('philomatrix_user');
      window.dispatchEvent(new Event('auth:unauthorized'));
    }
  }

  if (!response.ok) {
    let errorDetail = 'An unexpected error occurred';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || JSON.stringify(errJson);
    } catch {
      errorDetail = response.statusText;
    }
    throw new ApiError(errorDetail, response.status);
  }

  // If 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  get: <T>(url: string) => request<T>(url, { method: 'GET' }),
  post: <T>(url: string, data?: any) =>
    request<T>(url, { method: 'POST', body: data ? JSON.stringify(data) : undefined }),
  put: <T>(url: string, data?: any) =>
    request<T>(url, { method: 'PUT', body: data ? JSON.stringify(data) : undefined }),
  delete: <T>(url: string) => request<T>(url, { method: 'DELETE' }),

  downloadPdf: async (url: string, filename: string) => {
    const token = localStorage.getItem('philomatrix_access_token');
    const institutionId = localStorage.getItem('philomatrix_institution_id');
    const response = await fetch(`${BASE_URL}${url}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(institutionId ? { 'X-Institution-ID': institutionId } : {}),
      },
    });
    if (!response.ok) {
      throw new Error('Failed to generate or download report card PDF');
    }
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },
};
