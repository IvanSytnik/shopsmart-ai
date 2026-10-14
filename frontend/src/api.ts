import { UserInput, AIResponse } from './types';
import { translations } from './translations';

// Set VITE_API_URL at build time; the localhost fallback applies to `npm run dev` only.
const API_BASE_URL: string =
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');

// Must match the backend's `detail` for the daily /generate cap (app/api/generate.py).
const DAILY_LIMIT_DETAIL = 'Daily limit reached, try tomorrow';

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

      if (response.status === 429) {
        throw new Error(translations[input.language].errorRateLimited);
      }

      if (response.status === 504) {
        throw new Error(translations[input.language].errorTimeout);
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        // 422 validation errors carry a list in `detail`; only show plain-string details.
        const detail = typeof error.detail === 'string' ? error.detail : null;
        // 503 is also used for "AI service unavailable"; the daily cap is told apart by detail.
        if (response.status === 503 && detail === DAILY_LIMIT_DETAIL) {
          throw new Error(translations[input.language].errorDailyLimit);
        }
        throw new Error(detail || `HTTP error! status: ${response.status}`);
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
