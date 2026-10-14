import { UserInput, AIResponse, ApiErrorBody, ApiErrorCode } from './types';
import { translations } from './translations';

// Set VITE_API_URL at build time; the localhost fallback applies to `npm run dev` only.
const API_BASE_URL: string =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

// Every backend error code (app/errors.py) has a translated message.
const ERROR_MESSAGE_KEYS: Record<ApiErrorCode, keyof (typeof translations)['en']> = {
  validation_error: 'errorValidation',
  rate_limited: 'errorRateLimited',
  daily_limit: 'errorDailyLimit',
  ai_unavailable: 'errorAiUnavailable',
  ai_timeout: 'errorTimeout',
  generation_failed: 'errorGenerationFailed',
};

const isApiErrorBody = (body: unknown): body is ApiErrorBody =>
  typeof body === 'object' &&
  body !== null &&
  'code' in body &&
  typeof body.code === 'string' &&
  Object.keys(ERROR_MESSAGE_KEYS).includes(body.code);

class ApiService {
  private baseUrl: string;
  // Above the backend's 55 s request deadline, so its 504 arrives before we abort.
  private timeout: number = 70000;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  async generateShoppingList(input: UserInput): Promise<AIResponse> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(`${this.baseUrl}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(input),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const body: unknown = await response.json().catch(() => null);
        const code = isApiErrorBody(body) ? body.code : null;
        const key = code ? ERROR_MESSAGE_KEYS[code] : 'errorGenerationFailed';
        throw new Error(translations[input.language][key]);
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(translations[input.language].errorTimeout);
      }
      throw error;
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const apiService = new ApiService();
