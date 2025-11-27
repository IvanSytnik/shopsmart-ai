import React from 'react';
import { useLanguage } from '../LanguageContext';

interface ErrorBannerProps {
  message: string;
  onDismiss: () => void;
  onRetry: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss, onRetry }) => {
  const { t } = useLanguage();

  return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 animate-fade-in">
      <div className="flex items-start gap-3">
        <span className="text-2xl">⚠️</span>
        <div className="flex-1">
          <h3 className="font-semibold text-red-800">{t('error')}</h3>
          <p className="text-red-600 text-sm">{message}</p>
          <div className="mt-2 flex gap-2">
            <button
              onClick={onDismiss}
              className="text-sm text-red-600 hover:text-red-800 underline"
            >
              {t('dismiss')}
            </button>
            <button
              onClick={onRetry}
              className="text-sm text-red-600 hover:text-red-800 underline"
            >
              {t('refreshPage')}
            </button>
          </div>
        </div>
        <button onClick={onDismiss} className="text-red-400 hover:text-red-600">
          ✕
        </button>
      </div>
    </div>
  );
};
