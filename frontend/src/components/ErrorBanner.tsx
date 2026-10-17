import React from 'react';
import { useLanguage } from '../LanguageContext';
import type { ErrorCode } from '../api';
import { ERROR_MESSAGE_KEYS } from '../errorMessages';

// Trying again can't help: the request itself has to change.
const NOT_RETRYABLE: ReadonlySet<ErrorCode> = new Set([
  'not_enough_products',
  'validation_error',
  'unknown_store',
]);

interface ErrorBannerProps {
  code: ErrorCode;
  onDismiss: () => void;
  onRetry: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ code, onDismiss, onRetry }) => {
  const { t } = useLanguage();

  return (
    <div
      role="alert"
      className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 mb-6 animate-fade-in"
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl">⚠️</span>
        <div className="flex-1">
          <h3 className="font-semibold text-red-800 dark:text-red-300">{t('error')}</h3>
          <p className="text-red-600 dark:text-red-400 text-sm">{t(ERROR_MESSAGE_KEYS[code])}</p>
          <div className="mt-2 flex gap-2">
            <button
              onClick={onDismiss}
              className="text-sm text-red-600 dark:text-red-400 hover:text-red-800 underline"
            >
              {t('dismiss')}
            </button>
            {!NOT_RETRYABLE.has(code) && (
              <button
                onClick={onRetry}
                className="text-sm text-red-600 dark:text-red-400 hover:text-red-800 underline"
              >
                {t('refreshPage')}
              </button>
            )}
          </div>
        </div>
        <button
          onClick={onDismiss}
          aria-label={t('dismiss')}
          className="text-red-400 hover:text-red-600"
        >
          ✕
        </button>
      </div>
    </div>
  );
};
