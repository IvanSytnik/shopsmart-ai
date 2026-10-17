import React, { useState } from 'react';
import { GenerateResponse } from '../types';
import { CATEGORY_ICONS } from '../constants';
import { useLanguage } from '../LanguageContext';
import { formatSize, groupByStore, money, productName } from './results/format';

interface ShoppingListProps {
  response: GenerateResponse;
}

export const ShoppingList: React.FC<ShoppingListProps> = ({ response }) => {
  const { t, tn, language } = useLanguage();
  const [checked, setChecked] = useState<Set<string>>(new Set());

  const toggleItem = (productId: string) => {
    setChecked(prev => {
      const next = new Set(prev);
      if (next.has(productId)) {
        next.delete(productId);
      } else {
        next.add(productId);
      }
      return next;
    });
  };

  const progress = response.items.length ? (checked.size / response.items.length) * 100 : 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 px-1">
        <span>
          {tn('item', response.items.length)} •{' '}
          {tn('store', Object.keys(response.subtotals_by_store).length)}
        </span>
        <span>
          {progress.toFixed(0)}% {t('completed').toLowerCase()}
        </span>
      </div>

      {groupByStore(response.items).map(([store, items]) => (
        <section
          key={store}
          aria-label={store}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden transition-colors"
        >
          <div className="bg-gradient-to-r from-primary-500 to-purple-600 px-6 py-4 flex items-baseline justify-between">
            <h3 className="text-lg font-semibold text-white">{store}</h3>
            <p className="text-primary-100 text-sm">
              {tn('item', items.length)} •{' '}
              <span data-testid={`subtotal-${store}`}>
                €{money(response.subtotals_by_store[store] ?? 0)}
              </span>
            </p>
          </div>
          <ul className="divide-y dark:divide-gray-700">
            {items.map(item => {
              const isChecked = checked.has(item.product_id);
              return (
                <li key={item.product_id}>
                  <button
                    type="button"
                    onClick={() => toggleItem(item.product_id)}
                    aria-pressed={isChecked}
                    className={`w-full text-left flex items-center gap-4 p-4 transition-all ${isChecked ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'}`}
                  >
                    <span
                      className={`w-6 h-6 shrink-0 rounded-full border-2 flex items-center justify-center ${isChecked ? 'bg-green-500 border-green-500' : 'border-gray-300 dark:border-gray-600'}`}
                    >
                      {isChecked && <span className="text-white text-sm">✓</span>}
                    </span>
                    <span className="text-2xl" title={t(item.category)}>
                      {CATEGORY_ICONS[item.category]}
                    </span>
                    <span className="flex-1 min-w-0">
                      <span
                        className={`block font-medium ${isChecked ? 'line-through text-gray-400 dark:text-gray-500' : 'text-gray-800 dark:text-gray-200'}`}
                      >
                        {productName(item, language)}
                      </span>
                      <span className="block text-sm text-gray-500 dark:text-gray-400">
                        {item.packs} × {formatSize(item.pack_size, item.unit, language, t)} • €
                        {money(item.unit_price)} {t('perPack')}
                      </span>
                    </span>
                    <span className="font-semibold text-gray-800 dark:text-gray-200">
                      €{money(item.line_total)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
};
