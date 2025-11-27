import React, { useState } from 'react';
import { ShopForm, ShoppingList, LoadingSpinner, ErrorBanner, LanguageSelector } from './components';
import { LanguageProvider, useLanguage } from './LanguageContext';
import { apiService } from './api';
import { AIResponse, UserInput } from './types';

const AppContent: React.FC = () => {
  const [response, setResponse] = useState<AIResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { t } = useLanguage();

  const handleGenerate = async (input: UserInput) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiService.generateShoppingList(input);
      setResponse(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResponse(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
      {/* Language Selector */}
      <div className="fixed top-4 right-4 z-50">
        <LanguageSelector />
      </div>

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <header className="text-center mb-8">
          <div className="inline-block p-4 bg-gradient-to-br from-primary-500 to-purple-600 rounded-2xl shadow-lg mb-4">
            <span className="text-4xl">🛒</span>
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-primary-600 to-purple-600 bg-clip-text text-transparent mb-2">
            {t('appName')}
          </h1>
          <p className="text-gray-600">{t('appDescription')}</p>
        </header>

        {/* Error Banner */}
        {error && (
          <ErrorBanner
            message={error}
            onDismiss={() => setError(null)}
            onRetry={handleReset}
          />
        )}

        {/* Main Content */}
        {loading ? (
          <LoadingSpinner />
        ) : response ? (
          <ShoppingList response={response} onReset={handleReset} />
        ) : (
          <ShopForm onSubmit={handleGenerate} />
        )}

        {/* Footer */}
        <footer className="mt-12 text-center text-sm text-gray-500">
          <p>
            {t('builtWith')} ❤️ {t('using')}
          </p>
          <p className="mt-1">
            {t('appName')} © 2025 | {t('diplomaProject')}
          </p>
          <p>{t('supervisor')} | {t('university')}</p>
        </footer>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
};

export default App;
