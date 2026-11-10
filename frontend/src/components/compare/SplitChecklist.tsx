import React, { useId } from 'react';
import { useLanguage } from '../../LanguageContext';
import type { ConceptSummary, SplitBasket } from '../../types';
import { money } from '../results/format';
import { MatchedItem } from './MatchedItem';

interface SplitChecklistProps {
  basket: SplitBasket;
  conceptsById: ReadonlyMap<string, ConceptSummary>;
  checked: ReadonlySet<string>; // `${store}:${product_id}`
  onToggle: (key: string) => void;
}

const checklistKey = (store: string, productId: string) => `${store}:${productId}`;

/** Each product at the store where it costs least, as a checklist per store. */
export const SplitChecklist: React.FC<SplitChecklistProps> = ({
  basket,
  conceptsById,
  checked,
  onToggle,
}) => {
  const { t, tn } = useLanguage();
  const id = useId();
  const total = basket.stores.reduce((n, group) => n + group.items.length, 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-gray-600 dark:text-gray-400 px-1">
        <span>
          {t('compareSplitSummary', {
            amount: money(basket.total_eur),
            stores: tn('store', basket.stores.length),
          })}
        </span>
        <span>{t('compareChecked', { done: checked.size, total })}</span>
      </div>
      {basket.total_savings_vs_worst_eur > 0 && (
        <p className="px-1 text-sm text-green-700 dark:text-green-400">
          {t('compareSavesUpTo', { amount: money(basket.total_savings_vs_worst_eur) })}
        </p>
      )}
      {basket.stores.map((group, index) => (
        <section
          key={group.store}
          aria-labelledby={`${id}-${index}`}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden transition-colors"
        >
          <h3
            id={`${id}-${index}`}
            className="bg-gradient-to-r from-primary-500 to-purple-600 px-6 py-4 text-lg font-semibold text-white"
          >
            {t('compareBuyAt', { store: group.store, amount: money(group.total_eur) })}
          </h3>
          <ul className="divide-y dark:divide-gray-700">
            {group.items.map(item => {
              const key = checklistKey(group.store, item.product_id);
              const isChecked = checked.has(key);
              return (
                <li key={key}>
                  <label
                    className={`flex items-center gap-4 p-4 cursor-pointer transition-all ${isChecked ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'}`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => onToggle(key)}
                      className="w-5 h-5 shrink-0 accent-green-600"
                    />
                    <MatchedItem
                      item={item}
                      concept={conceptsById.get(item.concept_id)}
                      checked={isChecked}
                    />
                  </label>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
};
