import React from 'react';
import { AIResponse } from '../types';
import { useLanguage } from '../LanguageContext';

interface SavedList {
  id: string;
  date: string;
  budget: number;
  itemCount: number;
  totalCost: number;
  response: AIResponse;
}

interface HistoryProps {
  isOpen: boolean;
  onClose: () => void;
  onLoad: (response: AIResponse) => void;
}

export const History: React.FC<HistoryProps> = ({ isOpen, onClose, onLoad }) => {
  const { t } = useLanguage();
  const [lists, setLists] = React.useState<SavedList[]>([]);

  React.useEffect(() => {
    const saved = localStorage.getItem('shopsmart-history');
    if (saved) {
      setLists(JSON.parse(saved));
    }
  }, [isOpen]);

  const deleteList = (id: string) => {
    const updated = lists.filter(l => l.id !== id);
    setLists(updated);
    localStorage.setItem('shopsmart-history', JSON.stringify(updated));
  };

  const clearAll = () => {
    setLists([]);
    localStorage.removeItem('shopsmart-history');
  };

  const handleLoad = (list: SavedList) => {
    onLoad(list.response);
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
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {lists.length === 0 ? (
            <p className="text-center text-gray-500 dark:text-gray-400 py-8">
              {t('noSavedLists')}
            </p>
          ) : (
            <div className="space-y-3">
              {lists.map((list) => (
                <div
                  key={list.id}
                  className="bg-gray-50 dark:bg-gray-700 rounded-xl p-4 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {new Date(list.date).toLocaleDateString()}
                    </span>
                    <span className="text-sm font-semibold text-green-600 dark:text-green-400">
                      €{list.totalCost.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-700 dark:text-gray-300">
                      {list.itemCount} {t('items')} • €{list.budget} {t('weeklyBudget').toLowerCase()}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleLoad(list)}
                        className="px-3 py-1 bg-primary-500 text-white text-sm rounded-lg hover:bg-primary-600 transition-colors"
                      >
                        {t('loadList')}
                      </button>
                      <button
                        onClick={() => deleteList(list.id)}
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
        {lists.length > 0 && (
          <div className="p-4 border-t dark:border-gray-700">
            <button
              onClick={clearAll}
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

// Функція для збереження списку
export const saveListToHistory = (response: AIResponse, budget: number) => {
  const saved = localStorage.getItem('shopsmart-history');
  const lists: SavedList[] = saved ? JSON.parse(saved) : [];
  
  const newList: SavedList = {
    id: Date.now().toString(),
    date: new Date().toISOString(),
    budget,
    itemCount: response.items.length,
    totalCost: response.total_cost,
    response,
  };
  
  lists.unshift(newList);
  
  // Зберігаємо максимум 10 списків
  if (lists.length > 10) {
    lists.pop();
  }
  
  localStorage.setItem('shopsmart-history', JSON.stringify(lists));
};
