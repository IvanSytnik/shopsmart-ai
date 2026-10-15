import { describe, expect, it } from 'vitest';
import { formatPortion, formatSize } from '../components/results/format';
import { translations, Language, TranslationKey } from '../translations';

const fmt = (size: number, unit: 'kg' | 'l' | 'pcs' | 'pack', language: Language = 'en') =>
  formatSize(size, unit, language, (key: TranslationKey) => translations[language][key]);

describe('formatSize', () => {
  it.each([
    [0.4, 'kg', '400 g'],
    [0.175, 'kg', '175 g'],
    [1, 'kg', '1 kg'],
    [1.5, 'kg', '1.5 kg'],
    [0.33, 'l', '330 ml'],
    [0.5, 'l', '500 ml'],
    [1, 'l', '1 l'],
    [1.5, 'l', '1.5 l'],
    [10, 'pcs', '10 pcs'],
    [1, 'pack', '1 pack'],
  ] as const)('%s %s → %s', (size, unit, expected) => {
    expect(fmt(size, unit)).toBe(expected);
  });

  it('uses the UI language for units and decimals', () => {
    expect(fmt(0.4, 'kg', 'uk')).toBe('400 г');
    expect(fmt(1.5, 'kg', 'de')).toBe('1,5 kg');
    expect(fmt(10, 'pcs', 'de')).toBe('10 Stk.');
  });
});

describe('formatPortion', () => {
  const portion = (amount: number, unit: 'kg' | 'l' | 'pcs' | 'pack', language: Language = 'en') =>
    formatPortion(amount, unit, language, (key: TranslationKey) => translations[language][key]);

  it('shows grams for kg products, ml for l, pieces otherwise', () => {
    expect(portion(80, 'kg')).toBe('80 g');
    expect(portion(200, 'l')).toBe('200 ml');
    expect(portion(2, 'pcs')).toBe('2 pcs');
    expect(portion(1, 'pack')).toBe('1 pcs');
    expect(portion(80, 'kg', 'de')).toBe('80 g');
    expect(portion(2, 'pcs', 'uk')).toBe('2 шт.');
  });
});
