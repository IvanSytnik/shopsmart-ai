import React, { useState } from 'react';
import { UserInput } from '../types';
import { SUPERMARKETS, BUDGET_PRESETS, FAMILY_SIZE_OPTIONS } from '../constants';
import { useLanguage } from '../LanguageContext';

interface ShopFormProps {
  onSubmit: (input: UserInput) => void;
}

const preferenceKeys = [
  { key: 'vegetarian', emoji: '🥗' },
  { key: 'vegan', emoji: '🌱' },
  { key: 'glutenFree', emoji: '🚫' },
  { key: 'highProtein', emoji: '💪' },
  { key: 'lowCarb', emoji: '🏃' },
  { key: 'familyFriendly', emoji: '👶' },
  { key: 'organic', emoji: '🌿' },
  { key: 'budgetSaver', emoji: '💰' },
] as const;

export const ShopForm: React.FC<ShopFormProps> = ({ onSubmit }) => {
  const { t, language } = useLanguage();
  const [selectedSupermarkets, setSelectedSupermarkets] = useState<string[]>(['Lidl', 'Aldi']);
  const [budget, setBudget] = useState<number>(50);
  const [familySize, setFamilySize] = useState<number>(2);
  const [preferences, setPreferences] = useState<string>('');
  const [selectedPreferences, setSelectedPreferences] = useState<string[]>([]);
  const [mode, setMode] = useState<'shopping' | 'menu'>('shopping');
  const [days, setDays] = useState<number>(7);

  const toggleSupermarket = (name: string) => {
    setSelectedSupermarkets(prev =>
      prev.includes(name) ? prev.filter(s => s !== name) : [...prev, name]
    );
  };

  const togglePreference = (pref: string) => {
    setSelectedPreferences(prev =>
      prev.includes(pref) ? prev.filter(p => p !== pref) : [...prev, pref]
    );
  };

  const handleSubmit = () => {
    const allPreferences = [...selectedPreferences, preferences].filter(Boolean).join(', ');
    onSubmit({
      supermarkets: selectedSupermarkets,
      budget,
      preferences: allPreferences,
      family_size: familySize,
      language,
      mode,
      days: mode === 'menu' ? days : undefined,
    });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 space-y-6 animate-fade-in transition-colors">
      {/* Mode Selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          🎯 {t('mode')}
        </label>
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => setMode('shopping')}
            className={`p-4 rounded-xl border-2 transition-all ${
              mode === 'shopping'
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                : 'border-gray-200 dark:border-gray-600'
            }`}
          >
            <span className="text-2xl block mb-1">🛒</span>
            <span className={`font-medium ${mode === 'shopping' ? 'text-primary-700 dark:text-primary-300' : 'text-gray-700 dark:text-gray-300'}`}>
              {t('shoppingList')}
            </span>
          </button>
          <button
            onClick={() => setMode('menu')}
            className={`p-4 rounded-xl border-2 transition-all ${
              mode === 'menu'
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                : 'border-gray-200 dark:border-gray-600'
            }`}
          >
            <span className="text-2xl block mb-1">📅</span>
            <span className={`font-medium ${mode === 'menu' ? 'text-primary-700 dark:text-primary-300' : 'text-gray-700 dark:text-gray-300'}`}>
              {t('mealPlanning')}
            </span>
          </button>
        </div>
      </div>

      {/* Days Selector (only for menu mode) */}
      {mode === 'menu' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            📆 {t('days')}
          </label>
          <div className="flex flex-wrap gap-2">
            {[1, 2, 3, 4, 5, 6, 7].map(d => (
              <button
                key={d}
                onClick={() => setDays(d)}
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

      {/* Supermarkets */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          🏪 {t('selectSupermarkets')}
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {SUPERMARKETS.map(store => (
            <button
              key={store.name}
              onClick={() => toggleSupermarket(store.name)}
              className={`flex items-center gap-2 p-3 rounded-xl border-2 transition-all ${
                selectedSupermarkets.includes(store.name)
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'border-gray-200 dark:border-gray-600 dark:text-gray-300'
              }`}
            >
              <span className={`w-3 h-3 rounded-full ${store.color}`}></span>
              <span className="font-medium">{store.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Budget */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          💰 {t('weeklyBudget')}
        </label>
        <div className="flex flex-wrap gap-2 mb-3">
          {BUDGET_PRESETS.map(preset => (
            <button
              key={preset}
              onClick={() => setBudget(preset)}
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
          type="number"
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
          className="w-full p-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          min="10"
          max="1000"
        />
      </div>

      {/* Family Size */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          👨‍👩‍👧‍👦 {t('familySize')}
        </label>
        <div className="flex flex-wrap gap-2">
          {FAMILY_SIZE_OPTIONS.map(size => (
            <button
              key={size}
              onClick={() => setFamilySize(size)}
              className={`px-4 py-2 rounded-lg border transition-all ${
                familySize === size
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'border-gray-200 dark:border-gray-600 dark:text-gray-300'
              }`}
            >
              {size} {size === 1 ? t('person') : t('people')}
            </button>
          ))}
        </div>
      </div>

      {/* Dietary Preferences */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          🥗 {t('dietaryPreferences')}
        </label>
        <div className="flex flex-wrap gap-2">
          {preferenceKeys.map(({ key, emoji }) => (
            <button
              key={key}
              onClick={() => togglePreference(t(key))}
              className={`flex items-center gap-1 px-3 py-2 rounded-lg border transition-all ${
                selectedPreferences.includes(t(key))
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                  : 'border-gray-200 dark:border-gray-600 dark:text-gray-300'
              }`}
            >
              <span>{emoji}</span>
              <span>{t(key)}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Additional Preferences */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          📝 {t('additionalPreferences')}
        </label>
        <textarea
          value={preferences}
          onChange={(e) => setPreferences(e.target.value)}
          placeholder={t('preferencesPlaceholder')}
          className="w-full p-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 resize-none"
          rows={3}
        />
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={selectedSupermarkets.length === 0}
        className="w-full py-4 bg-gradient-to-r from-primary-500 to-purple-600 text-white font-semibold rounded-xl hover:from-primary-600 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
      >
        {mode === 'menu' ? t('generateMenu') : t('generateList')} ✨
      </button>
    </div>
  );
};
