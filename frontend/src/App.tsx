/**
 * ShopSmart AI - Main Application Component
 * 
 * Intelligent shopping list generator powered by GPT-4
 * 
 * Author: Ivan Sytnyk (КН-М524)
 * Supervisor: Kharchenko A.O.
 * NTU "KhPI" - 2025
 */

import { useState, useCallback } from 'react';
import { ShopForm, ShoppingList, LoadingSpinner, ErrorBanner } from './components';
import { apiService } from './api';
import type { UserInput, AIResponse } from './types';

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inputData, setInputData] = useState<UserInput | null>(null);

  const handleGenerate = useCallback(async (data: UserInput) => {
    setLoading(true);
    setError(null);
    setInputData(data);

    try {
      const response = await apiService.generateShoppingList(data);
      setResult(response);
    } catch (err) {
      console.error('Generation error:', err);
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to generate shopping list. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const handleReset = useCallback(() => {
    setResult(null);
    setError(null);
    setInputData(null);
  }, []);

  const handleDismissError = useCallback(() => {
    setError(null);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 py-8 px-4">
      <div className="container mx-auto max-w-4xl">
        {/* Error Banner */}
        {error && <ErrorBanner message={error} onDismiss={handleDismissError} />}

        {/* Loading State */}
        {loading && <LoadingSpinner />}

        {/* Main Content */}
        {!loading && !result && (
          <ShopForm onSubmit={handleGenerate} loading={loading} />
        )}

        {!loading && result && inputData && (
          <ShoppingList data={result} inputData={inputData} onReset={handleReset} />
        )}

        {/* Footer */}
        <footer className="mt-12 text-center text-gray-500 text-sm">
          <p>Built with ❤️ using React, TypeScript, FastAPI & GPT-4</p>
          <p className="mt-1">
            ShopSmart AI © 2025 | Diploma Project by Ivan Sytnyk (КН-М524)
          </p>
          <p className="mt-1 text-xs">
            Supervisor: Kharchenko A.O. | NTU "KhPI"
          </p>
        </footer>
      </div>
    </div>
  );
}

export default App;
