import React, { useId } from 'react';
import { useLanguage } from '../LanguageContext';
import type { TranslationKey } from '../translations';
import type { AppMode } from '../types';
import { labelClass } from './formControls';

const MODES: readonly (readonly [AppMode, string, TranslationKey])[] = [
  ['shopping', '🛒', 'shoppingList'],
  ['menu', '📅', 'mealPlanning'],
  ['compare', '⚖️', 'compareMode'],
];

interface ModeSelectorProps {
  mode: AppMode;
  onChange: (mode: AppMode) => void;
}

/** The app's three tabs, at the top of the plan form and of the compare form. */
export const ModeSelector: React.FC<ModeSelectorProps> = ({ mode, onChange }) => {
  const { t } = useLanguage();
  const labelId = useId(); // both forms stay mounted, so each needs its own id

  return (
    <div>
      <p className={labelClass}>
        <span aria-hidden="true">🎯</span> <span id={labelId}>{t('mode')}</span>
      </p>
      <div className="grid grid-cols-3 gap-2 sm:gap-3" role="group" aria-labelledby={labelId}>
        {MODES.map(([value, emoji, key]) => (
          <button
            key={value}
            type="button"
            onClick={() => onChange(value)}
            aria-pressed={mode === value}
            className={`p-3 sm:p-4 rounded-xl border-2 transition-all ${
              mode === value
                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30'
                : 'border-gray-200 dark:border-gray-600'
            }`}
          >
            <span className="text-2xl block mb-1" aria-hidden="true">
              {emoji}
            </span>
            <span
              className={`text-sm sm:text-base font-medium ${mode === value ? 'text-primary-700 dark:text-primary-300' : 'text-gray-700 dark:text-gray-300'}`}
            >
              {t(key)}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
};
