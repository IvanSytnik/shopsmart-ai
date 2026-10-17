import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Country, DietTag, GenerateRequest, Mode } from '../types';
import {
  BUDGET_PRESETS,
  BUDGET_MIN,
  BUDGET_MAX,
  COUNTRIES,
  DAY_OPTIONS,
  DIET_LABELS,
  FAMILY_SIZE_OPTIONS,
  MAX_STORES,
  PREFERENCES_TEXT_MAX_LENGTH,
} from '../constants';
import { useLanguage } from '../LanguageContext';
import { useCatalogMeta } from '../hooks/useCatalogMeta';
import { normalizeDecimalInput, parseDecimal } from '../numberInput';

interface ShopFormProps {
  onSubmit: (input: GenerateRequest) => void;
}

// Wishes, not diets: sent as text in `preferences`. Diets come from the catalog meta.
const preferenceKeys = [
  { key: 'highProtein', emoji: '💪' },
  { key: 'lowCarb', emoji: '🏃' },
  { key: 'familyFriendly', emoji: '👶' },
  { key: 'organic', emoji: '🌿' },
  { key: 'budgetSaver', emoji: '💰' },
] as const;

type PreferenceKey = (typeof preferenceKeys)[number]['key'];

const chipClass = (selected: boolean) =>
  `flex items-center gap-1 px-3 py-2 rounded-lg border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
    selected
      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
      : 'border-gray-200 dark:border-gray-600 dark:text-gray-300'
  }`;

const toggle = <T,>(list: T[], value: T): T[] =>
  list.includes(value) ? list.filter(v => v !== value) : [...list, value];

export const ShopForm: React.FC<ShopFormProps> = ({ onSubmit }) => {
  const { t, tn, language } = useLanguage();
  const catalog = useCatalogMeta();
  const [country, setCountry] = useState<Country>('AT');
  const [selectedStores, setSelectedStores] = useState<string[]>([]);
  // Kept as typed so the field can be empty while editing; parsed for validation and submit.
  const [budgetText, setBudgetText] = useState<string>('50');
  // Select the whole amount on focus so typing replaces it. Chrome and Safari clear that
  // selection on the mouseup of the focusing click, so that one mouseup is cancelled.
  const keepBudgetSelection = useRef(false);
  const [familySize, setFamilySize] = useState<number>(2);
  const [preferences, setPreferences] = useState<string>('');
  const [selectedDiets, setSelectedDiets] = useState<DietTag[]>([]);
  const [selectedPreferences, setSelectedPreferences] = useState<PreferenceKey[]>([]);
  const [mode, setMode] = useState<Mode>('shopping');
  const [days, setDays] = useState<number>(7);

  const meta = catalog.status === 'ready' ? catalog.meta : null;
  const countries = meta ? COUNTRIES.filter(c => meta.countries[c.code].length > 0) : [];
  // Fall back to the first country with stores if the default one has none.
  const activeCountry = countries.some(c => c.code === country) ? country : countries[0]?.code;
  // Memoized: a new [] on every render would re-run the preselect effect forever.
  const stores = useMemo(
    () => (meta && activeCountry ? meta.countries[activeCountry] : []),
    [meta, activeCountry]
  );
  const chosenStores = selectedStores.filter(s => stores.includes(s));

  // When the store list loads or the country changes: drop stores it doesn't have, and
  // preselect the first two if nothing valid is left.
  useEffect(() => {
    if (stores.length === 0) return;
    setSelectedStores(prev => {
      const valid = prev.filter(s => stores.includes(s));
      return valid.length > 0 ? valid : stores.slice(0, 2);
    });
  }, [stores]);

  const budget = parseDecimal(budgetText);
  const budgetValid = Number.isFinite(budget) && budget >= BUDGET_MIN && budget <= BUDGET_MAX;
  const storesValid = chosenStores.length >= 1 && chosenStores.length <= MAX_STORES;
  const canSubmit = activeCountry !== undefined && storesValid && budgetValid;

  const handleSubmit = () => {
    if (!canSubmit || activeCountry === undefined) return;
    const allPreferences = [...selectedPreferences.map(key => t(key)), preferences.trim()]
      .filter(Boolean)
      .join(', ');
    onSubmit({
      country: activeCountry,
      supermarkets: chosenStores,
      budget,
      family_size: familySize,
      diets: selectedDiets,
      preferences: allPreferences,
      language,
      mode,
      days,
    });
  };

  // Group captions are <p>s named by aria-labelledby: a <label> must point at one field.
  const labelClass = 'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3';

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 space-y-6 animate-fade-in transition-colors">
      {/* Mode Selector */}
      <div>
        <p className={labelClass}>
          <span aria-hidden="true">🎯</span> <span id="mode-label">{t('mode')}</span>
        </p>
        <div className="grid grid-cols-2 gap-3" role="group" aria-labelledby="mode-label">
          {(
            [
              ['shopping', '🛒', 'shoppingList'],
              ['menu', '📅', 'mealPlanning'],
            ] as const
          ).map(([value, emoji, key]) => (
            <button
              key={value}
              onClick={() => setMode(value)}
              aria-pressed={mode === value}
              className={`p-4 rounded-xl border-2 transition-all ${
                mode === value
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                  : 'border-gray-200 dark:border-gray-600'
              }`}
            >
              <span className="text-2xl block mb-1">{emoji}</span>
              <span
                className={`font-medium ${mode === value ? 'text-primary-700 dark:text-primary-300' : 'text-gray-700 dark:text-gray-300'}`}
              >
                {t(key)}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Days Selector (only for menu mode) */}
      {mode === 'menu' && (
        <div>
          <p className={labelClass}>
            <span aria-hidden="true">📆</span> <span id="days-label">{t('days')}</span>
          </p>
          <div className="flex flex-wrap gap-2" role="group" aria-labelledby="days-label">
            {DAY_OPTIONS.map(d => (
              <button
                key={d}
                onClick={() => setDays(d)}
                aria-pressed={days === d}
                className={`w-12 h-12 rounded-xl border-2 font-bold transition-all ${
                  days === d
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                    : 'border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Country + Supermarkets (from the catalog) */}
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
      {meta && activeCountry && (
        <>
          <div>
            <p className={labelClass}>
              <span aria-hidden="true">🌍</span> <span id="country-label">{t('country')}</span>
            </p>
            <div className="flex flex-wrap gap-2" role="group" aria-labelledby="country-label">
              {countries.map(c => (
                <button
                  key={c.code}
                  onClick={() => setCountry(c.code)}
                  aria-pressed={activeCountry === c.code}
                  className={chipClass(activeCountry === c.code)}
                >
                  <span>{c.flag}</span>
                  <span>{t(c.key)}</span>
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className={labelClass}>
              <span aria-hidden="true">🏪</span>{' '}
              <span id="stores-label">{t('selectSupermarkets')}</span>{' '}
              <span id="stores-hint" className="font-normal text-gray-500 dark:text-gray-400">
                ({t('storesHint', { max: MAX_STORES })})
              </span>
            </p>
            <div
              className="grid grid-cols-2 sm:grid-cols-3 gap-3"
              role="group"
              aria-labelledby="stores-label"
              aria-describedby="stores-hint"
            >
              {stores.map(store => {
                const selected = chosenStores.includes(store);
                return (
                  <button
                    key={store}
                    onClick={() => setSelectedStores(prev => toggle(prev, store))}
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
        </>
      )}

      {/* Budget */}
      <div>
        <label className={labelClass} htmlFor="budget">
          💰 {mode === 'menu' ? t('budgetForDays', { days: tn('day', days) }) : t('budget')}
        </label>
        <div className="flex flex-wrap gap-2 mb-3">
          {BUDGET_PRESETS.map(preset => (
            <button
              key={preset}
              onClick={() => setBudgetText(String(preset))}
              className={`px-4 py-2 rounded-lg border transition-all ${
                budget === preset
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'border-gray-200 dark:border-gray-600 dark:text-gray-300'
              }`}
            >
              €{preset}
            </button>
          ))}
        </div>
        <input
          id="budget"
          type="text"
          inputMode="decimal"
          autoComplete="off"
          value={budgetText}
          onChange={e => setBudgetText(normalizeDecimalInput(e.target.value))}
          onFocus={e => {
            e.currentTarget.select();
            keepBudgetSelection.current = true;
          }}
          onMouseUp={e => {
            if (keepBudgetSelection.current) e.preventDefault();
            keepBudgetSelection.current = false;
          }}
          onKeyDown={() => {
            keepBudgetSelection.current = false;
          }}
          onBlur={() => {
            keepBudgetSelection.current = false;
          }}
          aria-invalid={!budgetValid}
          aria-describedby={budgetValid ? undefined : 'budget-error'}
          className="w-full p-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
        />
        {!budgetValid && (
          <p id="budget-error" className="mt-2 text-sm text-red-600 dark:text-red-400">
            {t('budgetInvalid', { min: BUDGET_MIN, max: BUDGET_MAX })}
          </p>
        )}
      </div>

      {/* Family Size */}
      <div>
        <p className={labelClass}>
          <span aria-hidden="true">👨‍👩‍👧‍👦</span> <span id="family-size-label">{t('familySize')}</span>
        </p>
        <div className="flex flex-wrap gap-2" role="group" aria-labelledby="family-size-label">
          {FAMILY_SIZE_OPTIONS.map(size => (
            <button
              key={size}
              onClick={() => setFamilySize(size)}
              aria-pressed={familySize === size}
              className={`px-4 py-2 rounded-lg border transition-all ${
                familySize === size
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'border-gray-200 dark:border-gray-600 dark:text-gray-300'
              }`}
            >
              {tn('person', size)}
            </button>
          ))}
        </div>
      </div>

      {/* Diets (filter catalog products) and wishes (sent as text) */}
      <div>
        <p className={labelClass}>
          <span aria-hidden="true">🥗</span> <span id="diets-label">{t('dietaryPreferences')}</span>
        </p>
        <div className="flex flex-wrap gap-2" role="group" aria-labelledby="diets-label">
          {(meta?.diet_tags ?? []).map(tag => (
            <button
              key={tag}
              onClick={() => setSelectedDiets(prev => toggle(prev, tag))}
              aria-pressed={selectedDiets.includes(tag)}
              className={chipClass(selectedDiets.includes(tag))}
            >
              <span>{DIET_LABELS[tag].emoji}</span>
              <span>{t(DIET_LABELS[tag].key)}</span>
            </button>
          ))}
          {preferenceKeys.map(({ key, emoji }) => (
            <button
              key={key}
              onClick={() => setSelectedPreferences(prev => toggle(prev, key))}
              aria-pressed={selectedPreferences.includes(key)}
              className={chipClass(selectedPreferences.includes(key))}
            >
              <span>{emoji}</span>
              <span>{t(key)}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Additional Preferences */}
      <div>
        <label className={labelClass} htmlFor="preferences">
          📝 {t('additionalPreferences')}
        </label>
        <textarea
          id="preferences"
          value={preferences}
          onChange={e => setPreferences(e.target.value)}
          placeholder={t('preferencesPlaceholder')}
          className="w-full p-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 resize-none"
          rows={3}
          maxLength={PREFERENCES_TEXT_MAX_LENGTH}
        />
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={!canSubmit}
        className="w-full py-4 bg-gradient-to-r from-primary-500 to-purple-600 text-white font-semibold rounded-xl hover:from-primary-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
      >
        {mode === 'menu' ? t('generateMenu') : t('generateList')} ✨
      </button>
    </div>
  );
};
