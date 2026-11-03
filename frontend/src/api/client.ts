/**
 * API client — all requests go through here.
 * Uses relative /api paths (works with Vite proxy in dev and Flask in prod).
 * Automatically redirects to /login on 401.
 */

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    public readonly data: Record<string, unknown> = {}
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type JsonBody = Record<string, unknown> | FormData;

async function request<T>(
  method: string,
  path: string,
  body?: JsonBody,
  isFormData = false
): Promise<T> {
  const headers: Record<string, string> = {};

  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  // CSRF: include a custom header so Flask can distinguish XHR from form posts
  headers['X-Requested-With'] = 'XMLHttpRequest';

  const init: RequestInit = {
    method,
    credentials: 'include',
    headers,
  };

  if (body) {
    init.body = isFormData ? (body as FormData) : JSON.stringify(body);
  }

  const res = await fetch(path, init);

  // Handle session expiry
  if (res.status === 401) {
    // Only redirect if we are not already on /login
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login?expired=1';
    }
    const data = await res.json().catch(() => ({}));
    throw new ApiError(
      (data as { code?: string }).code ?? 'UNAUTHORIZED',
      (data as { message?: string }).message ?? 'Session expired.',
      401,
      data as Record<string, unknown>
    );
  }

  let data: Record<string, unknown>;
  try {
    data = await res.json();
  } catch {
    throw new ApiError('PARSE_ERROR', 'Server returned non-JSON response.', res.status);
  }

  if (!res.ok || !data.ok) {
    throw new ApiError(
      (data.code as string) ?? 'ERROR',
      (data.message as string) ?? 'An error occurred.',
      res.status,
      data
    );
  }

  return data as T;
}

export const client = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body: Record<string, unknown>) =>
    request<T>('POST', path, body),
  postForm: <T>(path: string, form: FormData) =>
    request<T>('POST', path, form, true),
};

