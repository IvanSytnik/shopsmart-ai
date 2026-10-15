import React from 'react';
import { GenerateResponse } from '../types';
import { useLanguage } from '../LanguageContext';
import { SavedPlan, clearHistory, deleteFromHistory, loadHistory } from '../history';

interface HistoryProps {
  isOpen: boolean;
  onClose: () => void;
  onLoad: (response: GenerateResponse) => void;
}

export const History: React.FC<HistoryProps> = ({ isOpen, onClose, onLoad }) => {
  const { t } = useLanguage();
  const [plans, setPlans] = React.useState<SavedPlan[]>([]);

  React.useEffect(() => {
    if (isOpen) setPlans(loadHistory());
  }, [isOpen]);

  const handleClear = () => {
    clearHistory();
    setPlans([]);
  };

  const handleLoad = (plan: SavedPlan) => {
    onLoad(plan.response);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-800 dark:text-gray-200">
            📜 {t('savedLists')}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors dark:text-gray-300"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {plans.length === 0 ? (
            <p className="text-center text-gray-500 dark:text-gray-400 py-8">{t('noSavedLists')}</p>
          ) : (
            <div className="space-y-3">
              {plans.map(plan => (
                <div
                  key={plan.id}
                  className="bg-gray-50 dark:bg-gray-700 rounded-xl p-4 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {plan.response.menu ? '📅' : '🛒'}{' '}
                      {new Date(plan.savedAt).toLocaleDateString()}
                    </span>
                    <span className="text-sm font-semibold text-green-600 dark:text-green-400">
                      €{plan.response.total.toFixed(2)} / €{plan.response.budget.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-700 dark:text-gray-300">
                      {plan.response.items.length} {t('items')} •{' '}
                      {Object.keys(plan.response.subtotals_by_store).join(', ')}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleLoad(plan)}
                        className="px-3 py-1 bg-primary-500 text-white text-sm rounded-lg hover:bg-primary-600 transition-colors"
                      >
                        {t('loadList')}
                      </button>
                      <button
                        onClick={() => setPlans(deleteFromHistory(plan.id))}
                        aria-label={t('deleteList')}
                        className="px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {plans.length > 0 && (
          <div className="p-4 border-t dark:border-gray-700">
            <button
              onClick={handleClear}
              className="w-full py-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              {t('clearHistory')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
