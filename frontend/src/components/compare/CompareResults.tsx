import React, { useEffect, useId, useRef, useState } from 'react';
import { useLanguage } from '../../LanguageContext';
import type { TranslationKey } from '../../translations';
import type { CompareRequest, CompareResponse, ConceptSummary, Strategy } from '../../types';
import { formatDate, money } from '../results/format';
import { SplitChecklist } from './SplitChecklist';
import { StoreRankings } from './StoreRankings';
import { conceptName } from './format';

const TABS: readonly (readonly [Strategy, string, TranslationKey])[] = [
  ['single_store', '🏪', 'compareByStore'],
  ['split_basket', '🔀', 'compareSplitTab'],
];

interface CompareResultsProps {
  response: CompareResponse;
  request: CompareRequest; // what was compared
  conceptsById: ReadonlyMap<string, ConceptSummary>;
  stale: boolean; // the list has changed since
  onCompareAgain: (() => void) | null; // null: the list as it is can't be compared
  comparing: boolean;
  focusOnMount: boolean;
}

/** The recommendation, then each store's prices and the split basket in two tabs. */
export const CompareResults: React.FC<CompareResultsProps> = ({
  response,
  request,
  conceptsById,
  stale,
  onCompareAgain,
  comparing,
  focusOnMount,
}) => {
  const { t, tn, language } = useLanguage();
  const id = useId();
  const [tab, setTab] = useState<Strategy>(response.recommended_strategy);
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const tabRefs = useRef<Partial<Record<Strategy, HTMLButtonElement | null>>>({});
  const sectionRef = useRef<HTMLElement>(null);

  // Fixed for this result: each comparison mounts a new one (it's keyed by the comparison).
  useEffect(() => {
    if (focusOnMount) sectionRef.current?.focus();
  }, [focusOnMount]);

  const best = response.single_store_rankings[0];
  const basket = response.split_basket;
  const names = (ids: string[]) => ids.map(c => conceptName(conceptsById, c, language)).join(', ');
  const nothingSold = basket.stores.length === 0;

  const toggleChecked = (key: string) =>
    setChecked(prev => {
      const next = new Set(prev);
      if (!next.delete(key)) next.add(key);
      return next;
    });

  // Arrow keys move between the tabs (WAI-ARIA tabs pattern).
  const onTabKeyDown = (event: React.KeyboardEvent) => {
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    const index = TABS.findIndex(([value]) => value === tab);
    const step = event.key === 'ArrowRight' ? 1 : -1;
    const [next] = TABS[(index + step + TABS.length) % TABS.length];
    setTab(next);
    tabRefs.current[next]?.focus();
  };

  const tabClass = (active: boolean) =>
    `py-3 rounded-xl font-medium transition-all ${
      active
        ? 'bg-primary-500 text-white'
        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
    }`;
  const bannerClass =
    'rounded-2xl shadow-xl p-6 text-white bg-gradient-to-r from-primary-500 to-purple-600';
  const warningClass =
    'rounded-xl p-4 text-sm bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300';

  return (
    <section
      ref={sectionRef}
      tabIndex={-1}
      aria-label={t('compareResults')}
      className="space-y-6 animate-fade-in focus:outline-none"
    >
      {stale && (
        <div className={`${warningClass} flex flex-col sm:flex-row sm:items-center gap-3`}>
          <p role="status" className="flex-1">
            <span aria-hidden="true">↻</span> {t('compareOutdated')}
          </p>
          <button
            type="button"
            onClick={onCompareAgain ?? undefined}
            disabled={onCompareAgain === null || comparing}
            className="self-start sm:self-auto shrink-0 min-h-[40px] px-4 rounded-lg font-semibold bg-amber-700 text-white hover:bg-amber-800 dark:bg-amber-400 dark:text-gray-900 dark:hover:bg-amber-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {comparing ? t('comparing') : `${t('compareAgain')} ↻`}
          </button>
        </div>
      )}
      <div className={`space-y-6 transition-opacity ${stale ? 'opacity-60' : ''}`}>
        {nothingSold ? (
          <p role="alert" className={warningClass}>
            <span aria-hidden="true">⚠️</span> {t('compareNothingSold')}
          </p>
        ) : response.recommended_strategy === 'split_basket' ? (
          <div className={bannerClass} data-testid="compare-recommendation">
            <h2 className="text-2xl font-bold mb-2">
              <span aria-hidden="true">🔀</span> {t('compareSplitTitle')}
            </h2>
            <p className="text-lg">
              {t('compareSplitBody', {
                amount: money(response.split_extra_savings_eur),
                store: best.store,
              })}
            </p>
            <p className="mt-2 text-sm text-primary-100">
              {t('compareSplitSummary', {
                amount: money(basket.total_eur),
                stores: tn('store', basket.stores.length),
              })}
            </p>
          </div>
        ) : (
          <div className={bannerClass} data-testid="compare-recommendation">
            <h2 className="text-2xl font-bold mb-2">
              <span aria-hidden="true">🏪</span> {t('compareSingleTitle', { store: best.store })}
            </h2>
            <p className="text-lg">{t('compareSingleBody', { amount: money(best.total_eur) })}</p>
            {response.split_extra_savings_eur > 0 && (
              <p className="mt-2 text-sm text-primary-100">
                {t('compareSplitNotWorth', {
                  amount: money(response.split_extra_savings_eur),
                  min: money(request.min_split_savings_eur ?? 0),
                })}
              </p>
            )}
            {best.missing_concepts.length > 0 && (
              <p className="mt-2 text-sm text-primary-100">
                {t('compareStoreLacks', {
                  store: best.store,
                  items: tn('item', best.missing_concepts.length),
                })}{' '}
                {names(best.missing_concepts)}
              </p>
            )}
          </div>
        )}

        {!nothingSold && basket.missing_concepts.length > 0 && (
          <p className={warningClass}>
            <span aria-hidden="true">⚠️</span>{' '}
            {t('compareMissingEverywhere', { items: tn('item', basket.missing_concepts.length) })}{' '}
            {names(basket.missing_concepts)}
          </p>
        )}

        {!nothingSold && (
          <>
            <div
              role="tablist"
              aria-label={t('compareResults')}
              onKeyDown={onTabKeyDown}
              className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-2 grid grid-cols-2 gap-2 transition-colors"
            >
              {TABS.map(([value, emoji, key]) => (
                <button
                  key={value}
                  ref={el => {
                    tabRefs.current[value] = el;
                  }}
                  type="button"
                  role="tab"
                  id={`${id}-tab-${value}`}
                  aria-controls={`${id}-panel`}
                  aria-selected={tab === value}
                  tabIndex={tab === value ? 0 : -1}
                  onClick={() => setTab(value)}
                  className={tabClass(tab === value)}
                >
                  <span aria-hidden="true">{emoji}</span> {t(key)}
                </button>
              ))}
            </div>
            <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-tab-${tab}`}>
              {tab === 'single_store' ? (
                <StoreRankings response={response} conceptsById={conceptsById} />
              ) : (
                <SplitChecklist
                  basket={basket}
                  conceptsById={conceptsById}
                  checked={checked}
                  onToggle={toggleChecked}
                />
              )}
            </div>
          </>
        )}

        <p className="text-center text-xs text-gray-500 dark:text-gray-400">
          {t('pricesAsOf', { date: formatDate(response.price_date, language) })}
        </p>
      </div>
    </section>
  );
};
