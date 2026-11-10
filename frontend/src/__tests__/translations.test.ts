import { describe, expect, it } from 'vitest';
import { ERROR_MESSAGE_KEYS } from '../errorMessages';
import { translations } from '../translations';

describe('translations', () => {
  it('has the same keys in every language', () => {
    const en = Object.keys(translations.en).sort();
    expect(Object.keys(translations.uk).sort()).toEqual(en);
    expect(Object.keys(translations.de).sort()).toEqual(en);
  });

  it('has compact mode labels that are part of the full ones', () => {
    // The full label is the accessible name, so it must contain what narrow screens show.
    for (const lang of ['en', 'uk', 'de'] as const) {
      const t = translations[lang];
      for (const [full, short] of [
        [t.shoppingList, t.shoppingListShort],
        [t.mealPlanning, t.mealPlanningShort],
        [t.compareMode, t.compareModeShort],
      ]) {
        expect(full.toLowerCase()).toContain(short.toLowerCase());
      }
    }
  });

  it('has a non-empty message for every error code', () => {
    for (const lang of ['en', 'uk', 'de'] as const) {
      for (const key of Object.values(ERROR_MESSAGE_KEYS)) {
        expect(translations[lang][key]).toBeTruthy();
      }
    }
  });
});
