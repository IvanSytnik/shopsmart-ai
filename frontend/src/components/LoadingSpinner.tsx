import React from 'react';
import { useLanguage } from '../LanguageContext';

export const LoadingSpinner: React.FC = () => {
  const { t } = useLanguage();

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 text-center animate-fade-in">
      <div className="inline-block p-4 bg-gradient-to-br from-primary-100 to-purple-100 rounded-full mb-4">
        <span className="text-4xl animate-bounce inline-block">🛒</span>
      </div>
      <h2 className="text-xl font-semibold text-gray-800 mb-2">
        {t('aiCreating')}
      </h2>
      <p className="text-gray-500 mb-6">{t('analyzingPrices')}</p>
      <div className="flex justify-center gap-2">
        <div className="w-3 h-3 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
        <div className="w-3 h-3 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
        <div className="w-3 h-3 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
      </div>
      <div className="mt-6 p-4 bg-blue-50 rounded-xl">
        <p className="text-sm text-blue-700">
          💡 <strong>{t('didYouKnow')}</strong> {t('funFact')}
        </p>
      </div>
    </div>
  );
};
