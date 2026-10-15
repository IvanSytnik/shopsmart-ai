import { describe, expect, it } from 'vitest';
import { ERROR_MESSAGE_KEYS } from '../errorMessages';
import { translations } from '../translations';

describe('translations', () => {
  it('has the same keys in every language', () => {
    const en = Object.keys(translations.en).sort();
    expect(Object.keys(translations.uk).sort()).toEqual(en);
    expect(Object.keys(translations.de).sort()).toEqual(en);
  });

  it('has a non-empty message for every error code', () => {
    for (const lang of ['en', 'uk', 'de'] as const) {
      for (const key of Object.values(ERROR_MESSAGE_KEYS)) {
        expect(translations[lang][key]).toBeTruthy();
      }
    }
  });
});
