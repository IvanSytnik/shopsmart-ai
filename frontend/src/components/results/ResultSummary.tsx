import React from 'react';
import { GenerateResponse } from '../../types';
import { useLanguage } from '../../LanguageContext';
import { formatDate, money } from './format';

interface ResultSummaryProps {
  response: GenerateResponse;
}

export const ResultSummary: React.FC<ResultSummaryProps> = ({ response }) => {
  const { t, language } = useLanguage();
  const used = response.budget > 0 ? Math.min(response.total / response.budget, 1) : 0;
  const usedPercent = Math.round(used * 100);

  return (
    <section className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 transition-colors">
      <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-4">
        {response.menu ? t('yourMealPlan') : t('yourShoppingList')}
      </h2>
      <div className="flex items-baseline justify-between gap-4 mb-2">
        <div>
          <span className="text-sm text-gray-500 dark:text-gray-400">{t('total')} </span>
          <span className="text-2xl font-bold text-gray-800 dark:text-gray-100" data-testid="total">
            €{money(response.total)}
          </span>
          <span className="text-gray-500 dark:text-gray-400">
            {' '}
            / €{money(response.budget)} {t('budget').toLowerCase()}
          </span>
        </div>
        <span className="text-sm font-medium text-green-600 dark:text-green-400">
          {t('budgetLeft', { amount: money(response.budget_remaining) })}
        </span>
      </div>
      <div
        role="progressbar"
        aria-label={t('budgetUsed')}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={usedPercent}
        className="h-3 w-full rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden"
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-green-400 to-primary-500 transition-all"
          style={{ width: `${usedPercent}%` }}
        />
      </div>
      <div className="mt-4 flex flex-col sm:flex-row sm:justify-between gap-1 text-sm text-gray-600 dark:text-gray-400">
        <span>
          🔥{' '}
          {t(response.kcal_basis === 'menu' ? 'menuKcal' : 'purchasedKcal', {
            kcal: Math.round(response.kcal_per_person_day),
          })}
        </span>
        <span>🏷️ {t('pricesAsOf', { date: formatDate(response.price_date, language) })}</span>
      </div>
    </section>
  );
};
