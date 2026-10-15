import type {
  ApiErrorBody,
  ApiErrorCode,
  CatalogMeta,
  GenerateRequest,
  GenerateResponse,
} from './types';

// Set VITE_API_URL at build time; the localhost fallback applies to `npm run dev` only.
const API_BASE_URL: string =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

// Above the backend's 55 s request deadline, so its 504 arrives before we abort.
const GENERATE_TIMEOUT_MS = 70000;

// Backend codes plus one for when the server can't be reached at all.
export type ErrorCode = ApiErrorCode | 'network_error';

const API_ERROR_CODES: readonly ApiErrorCode[] = [
  'validation_error',
  'unknown_store',
  'not_enough_products',
  'rate_limited',
  'daily_limit',
  'ai_unavailable',
  'ai_timeout',
  'generation_failed',
];

/** A failed request. Show `code` through i18n; never show the backend's `detail`. */
export class ApiError extends Error {
  readonly code: ErrorCode;

  constructor(code: ErrorCode) {
    super(code);
    this.name = 'ApiError';
    this.code = code;
  }
}

const isApiErrorBody = (body: unknown): body is ApiErrorBody =>
  typeof body === 'object' &&
  body !== null &&
  'code' in body &&
  typeof body.code === 'string' &&
  (API_ERROR_CODES as readonly string[]).includes(body.code);

async function request<T>(path: string, init: RequestInit = {}, timeoutMs?: number): Promise<T> {
  const controller = new AbortController();
  const timeoutId =
    timeoutMs === undefined ? undefined : setTimeout(() => controller.abort(), timeoutMs);
  try {
    let response: Response;
    try {
      response = await fetch(`${API_BASE_URL}${path}`, { ...init, signal: controller.signal });
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new ApiError('ai_timeout');
      }
      throw new ApiError('network_error');
    }
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => null);
      throw new ApiError(isApiErrorBody(body) ? body.code : 'generation_failed');
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const getCatalogMeta = (): Promise<CatalogMeta> =>
  request<CatalogMeta>('/api/catalog/meta');

export const generate = (input: GenerateRequest): Promise<GenerateResponse> =>
  request<GenerateResponse>(
    '/generate',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
    GENERATE_TIMEOUT_MS
  );
