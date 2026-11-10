import React, { useEffect, useId, useMemo, useState } from 'react';
import { ApiError, ErrorCode, compareBasket } from '../../api';
import {
  CompareList,
  MAX_COMPARE_ITEMS,
  MAX_QUANTITY,
  SPLIT_THRESHOLD_MAX,
  addConcept,
  changeQuantity,
  isSplitThreshold,
  loadCompareList,
  removeConcept,
  saveCompareList,
} from '../../compareList';
import { CATEGORY_ICONS, COUNTRIES, DIET_LABELS, MAX_STORES } from '../../constants';
import { ERROR_MESSAGE_KEYS } from '../../errorMessages';
import { useCatalogMeta } from '../../hooks/useCatalogMeta';
import { useConcepts } from '../../hooks/useConcepts';
import { useLanguage } from '../../LanguageContext';
import { normalizeDecimalInput, parseDecimal } from '../../numberInput';
import { buildListShareLink } from '../../share';
import type { TranslationKey } from '../../translations';
import type { AppMode, CompareRequest, CompareResponse, ConceptSummary } from '../../types';
import { chipClass, labelClass, toggle } from '../formControls';
import { ModeSelector } from '../ModeSelector';
import { CompareResults } from './CompareResults';
import { ConceptSearch } from './ConceptSearch';
import { conceptName, formatVolume } from './format';

interface CompareViewProps {
  onModeChange: (mode: AppMode) => void;
  // A list opened from a share link: it replaces the list being built.
  sharedList: CompareList | null;
}

interface Comparison {
  id: number; // a new one resets the result tabs and checklist
  request: CompareRequest;
  response: CompareResponse;
}

const thresholdText = (value: number) => String(value);

/** The compare tab: build a list of products, choose stores, compare their prices. */
export const CompareView: React.FC<CompareViewProps> = ({ onModeChange, sharedList }) => {
  const { t, tn, language } = useLanguage();
  const id = useId();
  const catalog = useCatalogMeta();
  const [list, setList] = useState<CompareList>(() => sharedList ?? loadCompareList());
  // Kept as typed so the field can be empty while editing; the list holds the last valid value.
  const [threshold, setThreshold] = useState(() => thresholdText(list.min_split_savings_eur));
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ErrorCode | null>(null);
  const [shareStatus, setShareStatus] = useState<TranslationKey | null>(null);
  const [openedShared, setOpenedShared] = useState(sharedList !== null);

  useEffect(() => {
    if (sharedList === null) return;
    setList(sharedList);
    setThreshold(thresholdText(sharedList.min_split_savings_eur));
    setComparison(null);
    setOpenedShared(true);
  }, [sharedList]);

  useEffect(() => {
    saveCompareList(list);
    setShareStatus(null); // a copied link no longer matches the list
  }, [list]);

  const meta = catalog.status === 'ready' ? catalog.meta : null;
  const countries = meta ? COUNTRIES.filter(c => meta.countries[c.code].length > 0) : [];
  // Fall back to the first country with stores if the list's one has none.
  const country = countries.some(c => c.code === list.country) ? list.country : countries[0]?.code;
  // Memoized: a new [] on every render would re-run the preselect effect forever.
  const stores = useMemo(() => (meta && country ? meta.countries[country] : []), [meta, country]);
  const chosenStores = list.stores.filter(s => stores.includes(s));

  // When the store list loads or the country changes and none of the list's stores is
  // there: compare all of them (up to the limit).
  useEffect(() => {
    if (stores.length === 0) return;
    setList(prev =>
      prev.stores.some(s => stores.includes(s))
        ? prev
        : { ...prev, stores: stores.slice(0, MAX_STORES) }
    );
  }, [stores]);

  const concepts = useConcepts(country);
  const conceptsById = useMemo(
    () =>
      new Map<string, ConceptSummary>(
        concepts.status === 'ready' ? concepts.concepts.map(c => [c.concept_id, c]) : []
      ),
    [concepts]
  );
  const onList = useMemo(() => new Set(list.items.map(i => i.concept_id)), [list.items]);

  const thresholdValid = isSplitThreshold(parseDecimal(threshold));
  const request: CompareRequest | null =
    country && list.items.length > 0 && chosenStores.length > 0 && thresholdValid
      ? {
          items: list.items,
          stores: chosenStores,
          diet_tags: list.diet_tags,
          min_split_savings_eur: list.min_split_savings_eur,
          country,
        }
      : null;
  const stale =
    comparison !== null && JSON.stringify(request) !== JSON.stringify(comparison.request);

  const changeThreshold = (raw: string) => {
    const text = normalizeDecimalInput(raw);
    setThreshold(text);
    const value = parseDecimal(text);
    if (isSplitThreshold(value)) setList(l => ({ ...l, min_split_savings_eur: value }));
  };

  const runCompare = async () => {
    if (!request) return;
    setLoading(true);
    setError(null);
    setOpenedShared(false);
    try {
      const response = await compareBasket(request);
      setComparison(prev => ({ id: (prev?.id ?? 0) + 1, request, response }));
    } catch (err) {
      setError(err instanceof ApiError ? err.code : 'generation_failed');
    } finally {
      setLoading(false);
    }
  };

  const shareList = async () => {
    const link = buildListShareLink({ ...list, stores: chosenStores, country: country ?? 'AT' });
    try {
      if (!link.ok || !navigator.clipboard) throw new Error('cannot share');
      await navigator.clipboard.writeText(link.url);
      setShareStatus('shareCopied');
    } catch {
      setShareStatus('shareFailed');
    }
  };

  // The backend's fallback code means "failed" here, not "could not generate a plan".
  const errorKey: TranslationKey | null =
    error === null
      ? null
      : error === 'generation_failed'
        ? 'compareFailed'
        : ERROR_MESSAGE_KEYS[error];
  const stepperClass =
    'w-9 h-9 shrink-0 rounded-lg border border-gray-200 dark:border-gray-600 text-lg font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed';
  const secondaryClass =
    'flex-1 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed';

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-4 sm:p-6 space-y-6 animate-fade-in transition-colors">
        <ModeSelector mode="compare" onChange={onModeChange} />

        {openedShared && (
          <p
            role="status"
            className="rounded-xl p-3 text-sm bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200"
          >
            <span aria-hidden="true">🔗</span> {t('sharedList')}
          </p>
        )}

        {catalog.status === 'loading' && (
          <p className="text-sm text-gray-500 dark:text-gray-400" role="status">
            {t('loadingStores')}
          </p>
        )}
        {catalog.status === 'error' && (
          <div className="flex items-center justify-between gap-3 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm">
            <span role="alert">{t('metaLoadFailed')}</span>
            <button onClick={catalog.reload} className="underline hover:no-underline">
              {t('retry')}
            </button>
          </div>
        )}
        {meta && countries.length === 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400">{t('noStores')}</p>
        )}

        {meta && country && (
          <>
            {countries.length > 1 && (
              <div>
                <p className={labelClass}>
                  <span aria-hidden="true">🌍</span>{' '}
                  <span id={`${id}-country`}>{t('country')}</span>
                </p>
                <div
                  className="flex flex-wrap gap-2"
                  role="group"
                  aria-labelledby={`${id}-country`}
                >
                  {countries.map(c => (
                    <button
                      key={c.code}
                      type="button"
                      onClick={() => setList(l => ({ ...l, country: c.code }))}
                      aria-pressed={country === c.code}
                      className={chipClass(country === c.code)}
                    >
                      <span aria-hidden="true">{c.flag}</span>
                      <span>{t(c.key)}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <section aria-labelledby={`${id}-list`} className="space-y-3">
              <h2 className={labelClass}>
                <span aria-hidden="true">📝</span>{' '}
                <span id={`${id}-list`}>{t('compareYourList')}</span>{' '}
                <span className="font-normal text-gray-500 dark:text-gray-400">
                  ({tn('item', list.items.length)})
                </span>
              </h2>

              {concepts.status === 'loading' && (
                <p className="text-sm text-gray-500 dark:text-gray-400" role="status">
                  {t('loadingProducts')}
                </p>
              )}
              {concepts.status === 'error' && (
                <div className="flex items-center justify-between gap-3 p-3 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 text-sm">
                  <span role="alert">{t('compareConceptsFailed')}</span>
                  <button onClick={concepts.reload} className="underline hover:no-underline">
                    {t('retry')}
                  </button>
                </div>
              )}
              {concepts.status === 'ready' && (
                <ConceptSearch
                  concepts={concepts.concepts}
                  onList={onList}
                  full={list.items.length >= MAX_COMPARE_ITEMS}
                  onAdd={c => setList(l => addConcept(l, c.concept_id))}
                />
              )}
              {list.items.length >= MAX_COMPARE_ITEMS && (
                <p className="text-sm text-amber-700 dark:text-amber-400">
                  {t('compareListFull', { max: MAX_COMPARE_ITEMS })}
                </p>
              )}

              {list.items.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-gray-400 py-2">
                  {t('compareEmptyList')}
                </p>
              ) : (
                <ul className="divide-y dark:divide-gray-700" aria-labelledby={`${id}-list`}>
                  {list.items.map(({ concept_id, quantity }) => {
                    const concept = conceptsById.get(concept_id);
                    const name = conceptName(conceptsById, concept_id, language);
                    return (
                      <li
                        key={concept_id}
                        className="flex flex-wrap items-center gap-2 sm:gap-3 py-3"
                      >
                        <span className="text-2xl" aria-hidden="true">
                          {concept ? CATEGORY_ICONS[concept.category] : '📦'}
                        </span>
                        <span className="flex-1 min-w-[8rem]">
                          <span className="block font-medium text-gray-800 dark:text-gray-200 break-words">
                            {name}
                          </span>
                          <span
                            className="block text-sm text-gray-500 dark:text-gray-400"
                            aria-live="polite"
                          >
                            {concept
                              ? formatVolume(
                                  quantity,
                                  concept.reference_pack_size,
                                  concept.unit,
                                  language,
                                  t
                                )
                              : `× ${quantity}${concepts.status === 'ready' ? ` · ${t('compareNotSold')}` : ''}`}
                          </span>
                        </span>
                        <div className="flex items-center gap-1 ml-auto">
                          <button
                            type="button"
                            onClick={() => setList(l => changeQuantity(l, concept_id, -1))}
                            disabled={quantity <= 1}
                            aria-label={t('compareLess', { name })}
                            className={stepperClass}
                          >
                            −
                          </button>
                          <button
                            type="button"
                            onClick={() => setList(l => changeQuantity(l, concept_id, 1))}
                            disabled={quantity >= MAX_QUANTITY}
                            aria-label={t('compareMore', { name })}
                            className={stepperClass}
                          >
                            +
                          </button>
                          <button
                            type="button"
                            onClick={() => setList(l => removeConcept(l, concept_id))}
                            aria-label={t('compareRemove', { name })}
                            className={`${stepperClass} text-red-600 dark:text-red-400`}
                          >
                            ✕
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
              {list.items.length > 0 && (
                <button
                  type="button"
                  onClick={() => setList(l => ({ ...l, items: [] }))}
                  className="text-sm text-gray-500 dark:text-gray-400 underline hover:no-underline"
                >
                  {t('compareClear')}
                </button>
              )}
            </section>

            <div>
              <p className={labelClass}>
                <span aria-hidden="true">🏪</span>{' '}
                <span id={`${id}-stores`}>{t('selectSupermarkets')}</span>{' '}
                <span
                  id={`${id}-stores-hint`}
                  className="font-normal text-gray-500 dark:text-gray-400"
                >
                  ({t('storesHint', { max: MAX_STORES })})
                </span>
              </p>
              <div
                className="grid grid-cols-2 sm:grid-cols-3 gap-3"
                role="group"
                aria-labelledby={`${id}-stores`}
                aria-describedby={`${id}-stores-hint`}
              >
                {stores.map(store => {
                  const selected = chosenStores.includes(store);
                  return (
                    <button
                      key={store}
                      type="button"
                      onClick={() => setList(l => ({ ...l, stores: toggle(chosenStores, store) }))}
                      aria-pressed={selected}
                      disabled={!selected && chosenStores.length >= MAX_STORES}
                      className={`${chipClass(selected)} justify-center p-3 rounded-xl border-2 font-medium`}
                    >
                      {store}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <p className={labelClass}>
                <span aria-hidden="true">🥗</span>{' '}
                <span id={`${id}-diets`}>{t('dietaryPreferences')}</span>
              </p>
              <div className="flex flex-wrap gap-2" role="group" aria-labelledby={`${id}-diets`}>
                {meta.diet_tags.map(tag => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => setList(l => ({ ...l, diet_tags: toggle(l.diet_tags, tag) }))}
                    aria-pressed={list.diet_tags.includes(tag)}
                    className={chipClass(list.diet_tags.includes(tag))}
                  >
                    <span aria-hidden="true">{DIET_LABELS[tag].emoji}</span>
                    <span>{t(DIET_LABELS[tag].key)}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className={labelClass} htmlFor={`${id}-threshold`}>
                <span aria-hidden="true">🔀</span> {t('compareThreshold')}
              </label>
              <input
                id={`${id}-threshold`}
                type="text"
                inputMode="decimal"
                autoComplete="off"
                value={threshold}
                onChange={e => changeThreshold(e.target.value)}
                aria-invalid={!thresholdValid}
                aria-describedby={`${id}-threshold-${thresholdValid ? 'hint' : 'error'}`}
                className="w-full sm:w-40 p-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
              {thresholdValid ? (
                <p
                  id={`${id}-threshold-hint`}
                  className="mt-2 text-sm text-gray-500 dark:text-gray-400"
                >
                  {t('compareThresholdHint')}
                </p>
              ) : (
                <p
                  id={`${id}-threshold-error`}
                  className="mt-2 text-sm text-red-600 dark:text-red-400"
                >
                  {t('compareThresholdInvalid', { max: SPLIT_THRESHOLD_MAX })}
                </p>
              )}
            </div>
          </>
        )}

        {errorKey && (
          <p
            role="alert"
            className="rounded-xl p-3 text-sm bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300"
          >
            <span aria-hidden="true">⚠️</span> {t(errorKey)}
          </p>
        )}

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={runCompare}
            disabled={request === null || loading}
            className="flex-[2] py-4 bg-gradient-to-r from-primary-500 to-purple-600 text-white font-semibold rounded-xl hover:from-primary-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
          >
            {loading ? t('comparing') : `${t('compareSubmit')} ⚖️`}
          </button>
          <button
            type="button"
            onClick={shareList}
            disabled={list.items.length === 0}
            className={secondaryClass}
          >
            <span aria-hidden="true">🔗</span> {t('compareShareList')}
          </button>
        </div>
        {shareStatus && (
          <p
            role="status"
            className={`text-sm text-center ${
              shareStatus === 'shareCopied'
                ? 'text-green-700 dark:text-green-400'
                : 'text-amber-700 dark:text-amber-400'
            }`}
          >
            {t(shareStatus)}
          </p>
        )}
      </div>

      {comparison && (
        <CompareResults
          key={comparison.id}
          response={comparison.response}
          request={comparison.request}
          conceptsById={conceptsById}
          stale={stale}
        />
      )}
    </div>
  );
};
