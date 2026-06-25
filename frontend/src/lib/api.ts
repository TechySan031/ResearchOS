const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
console.log("API_BASE_URL =", API_BASE_URL);
console.log("WS_BASE_URL =", process.env.NEXT_PUBLIC_WS_URL);

class ApiError extends Error {
  status: number;
  info: any;

  constructor(message: string, status: number, info?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.info = info;
  }
}

/**
 * Retrieve the stored access token for automatic injection.
 * Returns null on the server side or when not authenticated.
 */
function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('researchos_access_token');
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const headers = new Headers(options?.headers);

  // Auto-inject authorization header if a token exists and isn't already set
  if (!headers.has('Authorization')) {
    const token = getStoredToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  if (!headers.has('Content-Type') && !(options?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorInfo;
    try {
      errorInfo = await response.json();
    } catch {
      errorInfo = { message: await response.text() };
    }
    throw new ApiError(
      errorInfo.detail || errorInfo.message || 'An error occurred while fetching data.',
      response.status,
      errorInfo
    );
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { ...options, method: 'GET' }),

  post: <T>(path: string, body?: any, options?: RequestInit) =>
    request<T>(path, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  patch: <T>(path: string, body?: any, options?: RequestInit) =>
    request<T>(path, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  delete: <T>(path: string, options?: RequestInit) =>
    request<T>(path, { ...options, method: 'DELETE' }),

  baseUrl: API_BASE_URL,
};
