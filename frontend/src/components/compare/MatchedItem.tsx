import React from 'react';
import { productIcon } from '../../constants';
import { useLanguage } from '../../LanguageContext';
import type { ConceptSummary, MatchedStoreItem } from '../../types';
import { formatDate, formatSize, money } from '../results/format';
import { formatPerUnit } from './format';

/** Regular price struck through, the promo price, and the promotion's last day. */
const PromoBadge: React.FC<{ item: MatchedStoreItem; promo: number }> = ({ item, promo }) => {
  const { t, language } = useLanguage();
  return (
    <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
      <span className="px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 font-semibold">
        <span aria-hidden="true">🏷️</span> {t('comparePromo')}
      </span>
      <span className="text-gray-500 dark:text-gray-400">
        <span className="sr-only">{t('compareRegularPrice')}: </span>
        <del>€{money(item.regular_price_eur)}</del>
      </span>
      <span className="font-semibold text-red-600 dark:text-red-400">€{money(promo)}</span>
      {item.promo_valid_until && (
        <span className="text-gray-500 dark:text-gray-400">
          {t('comparePromoUntil', { date: formatDate(item.promo_valid_until, language) })}
        </span>
      )}
    </span>
  );
};

interface MatchedItemProps {
  item: MatchedStoreItem;
  concept: ConceptSummary | undefined;
  checked?: boolean; // in the split checklist: struck through once in the basket
}

/** A product a store sells for a list item: icon, name, packs, price per unit and promotion. */
export const MatchedItem: React.FC<MatchedItemProps> = ({ item, concept, checked = false }) => {
  const { t, language } = useLanguage();
  return (
    <>
      <span className="text-2xl" aria-hidden="true">
        {concept ? productIcon({ product_id: item.product_id, category: concept.category }) : '📦'}
      </span>
      <span className="flex-1 min-w-0">
        <span
          className={`block font-medium break-words ${checked ? 'line-through text-gray-400 dark:text-gray-500' : 'text-gray-800 dark:text-gray-200'}`}
        >
          {item.names[language]}
        </span>
        <span className="block text-sm text-gray-500 dark:text-gray-400">
          {item.packs_needed} × {formatSize(item.pack_size, item.unit, language, t)} ·{' '}
          {formatPerUnit(item, t)}
        </span>
        {item.promo_price_eur !== null && <PromoBadge item={item} promo={item.promo_price_eur} />}
      </span>
      <span className="font-semibold text-gray-800 dark:text-gray-200 whitespace-nowrap">
        €{money(item.line_total_eur)}
      </span>
    </>
  );
};
