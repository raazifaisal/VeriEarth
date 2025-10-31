// API utility for secure requests with CSRF protection
let csrfToken: string | null = null;

export async function getCsrfToken(forceRefresh: boolean = false): Promise<string> {
  if (!csrfToken || forceRefresh) {
    try {
      const response = await fetch('http://localhost:8000/csrf-token', {
        credentials: 'include',
      });
      const data = await response.json();
      csrfToken = data.csrf_token;
    } catch (error) {
      console.error('Failed to get CSRF token:', error);
      throw error;
    }
  }
  return csrfToken as string;
}

export async function apiRequest(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  // Get CSRF token for non-GET requests
  if (options.method && options.method !== 'GET') {
    const token = await getCsrfToken();
    options.headers = {
      ...options.headers,
      'X-CSRF-Token': token,
    };
  }

  // Always include credentials for cookies
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    // Do NOT force Content-Type; let callers set it (JSON, form-encoded, etc.)
    headers: {
      ...(options.headers || {}),
    },
  });

  // If CSRF token is invalid or expired, refresh and retry once
  if (response.status === 403) {
    const errorData = await response.json().catch(() => ({}));
    if (errorData.detail && (
      errorData.detail.includes('CSRF') || 
      errorData.detail.includes('token')
    )) {
      console.log('CSRF token invalid, refreshing and retrying...');
      // Clear and refresh token
      csrfToken = null;
      const newToken = await getCsrfToken(true);
      
      // Retry the request with new token
      if (options.method && options.method !== 'GET') {
        const retryOptions = {
          ...options,
          headers: {
            ...options.headers,
            'X-CSRF-Token': newToken,
          },
        };
        return fetch(url, {
          ...retryOptions,
          credentials: 'include',
        });
      }
    }
  }

  // If unauthorized, clear CSRF token to force refresh
  if (response.status === 401) {
    csrfToken = null;
  }

  // Refresh CSRF token after successful state-changing requests
  if (response.ok && options.method && options.method !== 'GET') {
    // Asynchronously refresh the token for next request (don't await)
    getCsrfToken(true).catch(() => {
      // Ignore errors, token will be refreshed on next request
    });
  }

  return response;
}

export async function login(email: string, password: string): Promise<void> {
  const form = new URLSearchParams();
  form.set('username', email);
  form.set('password', password);

  const response = await apiRequest('http://localhost:8000/auth/login', {
    method: 'POST',
    body: form,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }
  
  // Refresh CSRF token after successful login
  csrfToken = null;
  await getCsrfToken(true);
}

export async function register(fullName: string, email: string, password: string): Promise<void> {
  const response = await apiRequest('http://localhost:8000/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
    }),
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }
}

export async function logout(): Promise<void> {
  await apiRequest('http://localhost:8000/auth/logout', {
    method: 'POST',
  });
  // Clear CSRF token after logout
  csrfToken = null;
}

export async function getCurrentUser(): Promise<any> {
  const response = await apiRequest('http://localhost:8000/auth/me');
  
  if (!response.ok) {
    throw new Error('Not authenticated');
  }
  
  return response.json();
}

export async function refreshToken(): Promise<void> {
  await apiRequest('http://localhost:8000/auth/refresh', {
    method: 'POST',
  });
}
