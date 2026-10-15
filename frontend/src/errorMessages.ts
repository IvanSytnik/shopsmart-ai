import type { ErrorCode } from './api';
import type { TranslationKey } from './translations';

// Every error code has a translated message; the backend's `detail` is never shown.
export const ERROR_MESSAGE_KEYS: Record<ErrorCode, TranslationKey> = {
  validation_error: 'errorValidation',
  unknown_store: 'errorUnknownStore',
  not_enough_products: 'errorNotEnoughProducts',
  rate_limited: 'errorRateLimited',
  daily_limit: 'errorDailyLimit',
  ai_unavailable: 'errorAiUnavailable',
  ai_timeout: 'errorTimeout',
  generation_failed: 'errorGenerationFailed',
  network_error: 'errorNetwork',
};
