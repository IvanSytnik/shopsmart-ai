import React, { useState } from 'react';
import { GenerateResponse } from '../../types';
import { useLanguage } from '../../LanguageContext';
import { MealPlan } from '../MealPlan';
import { ShoppingList } from '../ShoppingList';
import { ResultSummary } from './ResultSummary';
import { ResultWarnings } from './ResultWarnings';
import { shoppingListText } from './exportText';

interface ResultsProps {
  response: GenerateResponse;
  onReset: () => void;
}

export const Results: React.FC<ResultsProps> = ({ response, onReset }) => {
  const { t } = useLanguage();
  const [tab, setTab] = useState<'menu' | 'products'>('menu');
  const menu = response.menu;

  const copyToClipboard = () => {
    navigator.clipboard?.writeText(shoppingListText(response, t)).catch(() => undefined);
  };

  const tabClass = (active: boolean) =>
    `py-3 rounded-xl font-medium transition-all ${
      active
        ? 'bg-primary-500 text-white'
        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
    }`;

  const actionClass =
    'flex-1 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-all';

  return (
    <div className="space-y-6 animate-fade-in">
      <ResultSummary response={response} />
      <ResultWarnings response={response} />

      {menu ? (
        <>
          <div
            className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-2 transition-colors no-print"
            role="tablist"
          >
            <div className="grid grid-cols-2 gap-2">
              <button
                role="tab"
                aria-selected={tab === 'menu'}
                onClick={() => setTab('menu')}
                className={tabClass(tab === 'menu')}
              >
                📅 {t('yourMealPlan')}
              </button>
              <button
                role="tab"
                aria-selected={tab === 'products'}
                onClick={() => setTab('products')}
                className={tabClass(tab === 'products')}
              >
                🛒 {t('productsForMenu')}
              </button>
            </div>
          </div>
          {tab === 'menu' ? (
            <MealPlan response={response} menu={menu} />
          ) : (
            <ShoppingList response={response} />
          )}
        </>
      ) : (
        <ShoppingList response={response} />
      )}

      {response.notes && (
        <aside className="rounded-xl bg-blue-50 dark:bg-blue-900/20 p-4 text-sm text-blue-800 dark:text-blue-200">
          💡 <span className="font-medium">{t('tip')}:</span> {response.notes}
        </aside>
      )}

      <div className="flex flex-wrap gap-3 no-print">
        <button onClick={copyToClipboard} className={actionClass}>
          📋 {t('copyToClipboard')}
        </button>
        <button onClick={() => window.print()} className={actionClass}>
          🖨️ {t('print')}
        </button>
        <button
          onClick={onReset}
          className="flex-1 py-3 bg-gradient-to-r from-primary-500 to-purple-600 text-white rounded-xl hover:from-primary-600 hover:to-purple-700 transition-all"
        >
          ✨ {t('newList')}
        </button>
      </div>
    </div>
  );
};
