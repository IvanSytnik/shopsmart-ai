import React, { useId } from 'react';
import { useLanguage } from '../../LanguageContext';
import type { CompareResponse, ConceptSummary } from '../../types';
import { money } from '../results/format';
import { MatchedItem } from './MatchedItem';
import { conceptName } from './format';

interface StoreRankingsProps {
  response: CompareResponse;
  conceptsById: ReadonlyMap<string, ConceptSummary>;
}

/** The whole list at each store, best first: what to buy there and what it lacks. */
export const StoreRankings: React.FC<StoreRankingsProps> = ({ response, conceptsById }) => {
  const { t, tn, language } = useLanguage();
  const id = useId();

  return (
    <ol className="space-y-4">
      {response.single_store_rankings.map((store, index) => {
        const recommended = store.store === response.recommended_store;
        const headingId = `${id}-${index}`;
        return (
          <li key={store.store}>
            <section
              aria-labelledby={headingId}
              className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden transition-colors"
            >
              <div
                className={`px-6 py-4 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 ${
                  recommended
                    ? 'bg-gradient-to-r from-primary-500 to-purple-600 text-white'
                    : 'bg-gray-50 dark:bg-gray-700/50 text-gray-800 dark:text-gray-100'
                }`}
              >
                <h3 id={headingId} className="text-lg font-semibold">
                  {index + 1}. {store.store}
                  {recommended && (
                    <span className="ml-2 align-middle text-xs font-medium px-2 py-0.5 rounded-full bg-white/20">
                      ✓ {t('compareRecommended')}
                    </span>
                  )}
                </h3>
                <p className="text-xl font-bold" data-testid={`store-total-${store.store}`}>
                  €{money(store.total_eur)}
                </p>
                <p
                  className={`w-full text-sm ${recommended ? 'text-primary-100' : 'text-gray-500 dark:text-gray-400'}`}
                >
                  {tn('item', store.items.length)}
                  {store.missing_concepts.length > 0 &&
                    ` · ${t('compareMissing', { items: tn('item', store.missing_concepts.length) })}`}
                  {store.promo_savings_eur > 0 &&
                    ` · ${t('comparePromoSavings', { amount: money(store.promo_savings_eur) })}`}
                </p>
              </div>
              {store.items.length > 0 && (
                <ul className="divide-y dark:divide-gray-700">
                  {store.items.map(item => (
                    <li key={item.concept_id} className="flex items-center gap-4 p-4">
                      <MatchedItem item={item} concept={conceptsById.get(item.concept_id)} />
                    </li>
                  ))}
                </ul>
              )}
              {store.missing_concepts.length > 0 && (
                <p className="px-6 py-3 text-sm bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300">
                  <span aria-hidden="true">⚠️</span> {t('compareNotHere')}{' '}
                  {store.missing_concepts
                    .map(c => conceptName(conceptsById, c, language))
                    .join(', ')}
                </p>
              )}
            </section>
          </li>
        );
      })}
    </ol>
  );
};
