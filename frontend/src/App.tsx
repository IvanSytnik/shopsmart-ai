import React, { useEffect, useState } from 'react';
import {
  ShopForm,
  Results,
  LoadingSpinner,
  ErrorBanner,
  LanguageSelector,
  ThemeToggle,
  History,
} from './components';
import { LanguageProvider, useLanguage } from './LanguageContext';
import { ThemeProvider } from './ThemeContext';
import { ApiError, ErrorCode, generate } from './api';
import { saveToHistory } from './history';
import { SharedPlan, parseShareHash } from './share';
import { GenerateRequest, GenerateResponse } from './types';

const AppContent: React.FC = () => {
  const [response, setResponse] = useState<GenerateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ErrorCode | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [isMenuMode, setIsMenuMode] = useState(false);
  const [shared, setShared] = useState<SharedPlan>(() => parseShareHash(window.location.hash));
  const { t } = useLanguage();

  // A share link pasted into an open tab only changes the hash.
  useEffect(() => {
    const onHashChange = () => setShared(parseShareHash(window.location.hash));
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const leaveShared = () => {
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
    setShared({ kind: 'none' });
  };

  const handleGenerate = async (input: GenerateRequest) => {
    setLoading(true);
    setError(null);
    setIsMenuMode(input.mode === 'menu');
    try {
      const result = await generate(input);
      setResponse(result);
      saveToHistory(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : 'generation_failed');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResponse(null);
    setError(null);
  };

  const handleLoadFromHistory = (savedResponse: GenerateResponse) => {
    leaveShared();
    setError(null);
    setResponse(savedResponse);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 transition-colors duration-300">
      {/* In flow above the logo below md (at sm a pinned toolbar still covers it). */}
      <div className="flex items-center justify-end gap-2 px-4 pt-4 md:fixed md:top-4 md:right-4 md:z-50 md:p-0">
        <button
          onClick={() => setHistoryOpen(true)}
          className="p-2 rounded-full bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-md hover:shadow-lg transition-all"
          title={t('history')}
        >
          <span className="text-xl">📜</span>
        </button>
        <ThemeToggle />
        <LanguageSelector />
      </div>

      <History
        isOpen={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onLoad={handleLoadFromHistory}
      />

      <div className="container mx-auto px-4 pt-4 pb-8 md:pt-8 max-w-4xl">
        <header className="text-center mb-8">
          <div className="inline-block p-4 bg-gradient-to-br from-primary-500 to-purple-600 rounded-2xl shadow-lg mb-4">
            <span className="text-4xl">🛒</span>
          </div>
          <h1 className="text-4xl font-bold bg-gradient-to-r from-primary-600 to-purple-600 bg-clip-text text-transparent mb-2">
            {t('appName')}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">{t('appDescription')}</p>
        </header>

        {shared.kind === 'plan' && (
          <>
            <p className="mb-4 text-center text-sm font-medium text-gray-600 dark:text-gray-400">
              🔗 {t('sharedPlan')}
            </p>
            <Results response={shared.plan} onReset={leaveShared} shared />
          </>
        )}
        {shared.kind === 'invalid' && (
          <div
            role="alert"
            className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-6 text-center animate-fade-in"
          >
            <p className="text-amber-800 dark:text-amber-300 mb-4">{t('sharedInvalid')}</p>
            <button
              onClick={leaveShared}
              className="px-6 py-3 bg-gradient-to-r from-primary-500 to-purple-600 text-white rounded-xl hover:from-primary-600 hover:to-purple-700 transition-all"
            >
              ✨ {t('createYourOwn')}
            </button>
          </div>
        )}

        {shared.kind === 'none' && error && (
          <ErrorBanner code={error} onDismiss={() => setError(null)} onRetry={handleReset} />
        )}

        {shared.kind === 'none' && loading && <LoadingSpinner isMenu={isMenuMode} />}
        {shared.kind === 'none' && !loading && response && (
          <Results response={response} onReset={handleReset} />
        )}
        {/* Kept mounted while loading so the user's choices survive an error. */}
        {shared.kind === 'none' && !response && (
          <div className={loading ? 'hidden' : undefined}>
            <ShopForm onSubmit={handleGenerate} />
          </div>
        )}

        <footer className="mt-12 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>
            {t('builtWith')} ❤️ {t('using')}
          </p>
          <p className="mt-1">
            {t('appName')} © 2025–2026 | {t('diplomaProject')}
          </p>
          <p>
            {t('supervisor')} | {t('university')}
          </p>
        </footer>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AppContent />
      </LanguageProvider>
    </ThemeProvider>
  );
};

export default App;
