import { describe, expect, it } from 'vitest';
import { formatPortion, formatSize, portionUnitOf } from '../components/results/format';
import { productIcon } from '../constants';
import type { Item } from '../types';
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
  const portion = (amount: number, unit: 'g' | 'ml' | 'pcs' | 'pack', language: Language = 'en') =>
    formatPortion(amount, unit, language, (key: TranslationKey) => translations[language][key]);

  it('shows the amount in its portion unit', () => {
    expect(portion(80, 'g')).toBe('80 g');
    expect(portion(200, 'ml')).toBe('200 ml');
    expect(portion(2, 'pcs')).toBe('2 pcs');
    expect(portion(0.5, 'pack')).toBe('0.5 pack');
    expect(portion(0.75, 'pack', 'de')).toBe('0,75 Pkg.');
    expect(portion(2, 'pcs', 'uk')).toBe('2 шт.');
  });

  it('derives the portion unit for plans saved without one', () => {
    expect(portionUnitOf({ unit: 'kg', portion_unit: 'pack' })).toBe('pack');
    const legacy = { unit: 'kg' } as unknown as Pick<Item, 'unit' | 'portion_unit'>;
    expect(portionUnitOf(legacy)).toBe('g');
  });
});

describe('productIcon', () => {
  it('uses a product override before the category icon', () => {
    expect(productIcon({ product_id: 'at-billa-eggs-m-10', category: 'dairy' })).toBe('🥚');
    expect(productIcon({ product_id: 'at-billa-uht-whole-milk-1l', category: 'dairy' })).toBe('🥛');
    // Whole id segments only: egg noodles keep their category icon.
    expect(productIcon({ product_id: 'at-x-egg-noodles-500g', category: 'pantry' })).toBe('🥫');
  });
});
