import { describe, expect, it } from 'vitest';
import { formatVolume, matchConcepts, searchable } from '../components/compare/format';
import { CONCEPTS } from '../test/fixtures';
import { translations } from '../translations';
import type { TranslationKey } from '../translations';

const t = (key: TranslationKey) => translations.en[key];
const ids = (query: string, language: 'en' | 'uk' | 'de' = 'en', category: '' | 'fruits' = '') =>
  matchConcepts(CONCEPTS.concepts, query, category, language).map(c => c.concept_id);

describe('concept search', () => {
  it('ignores case and accents', () => {
    expect(searchable('Äpfel')).toBe('apfel');
    expect(searchable('ЙОГУРТ')).toBe(searchable('йогурт'));
  });

  it('lists everything by name for an empty query, or one category', () => {
    expect(ids('')).toEqual(['bananas', 'butter', 'eggs', 'yogurt_natural', 'rice', 'milk_whole']);
    expect(ids('', 'de')).toEqual([
      'bananas',
      'butter',
      'eggs',
      'yogurt_natural',
      'rice',
      'milk_whole',
    ]);
    expect(ids('  ', 'en', 'fruits')).toEqual(['bananas']);
  });

  it('ranks the start of the name, then a word, then anywhere, then other names', () => {
    expect(ids('milk')).toEqual(['milk_whole']); // a word of "Whole milk"
    // Names starting with "b" first; milk only through a product's "Haltbar-Vollmilch".
    expect(ids('b')).toEqual(['bananas', 'butter', 'milk_whole']);
    expect(ids('yogurt', 'uk')).toEqual(['yogurt_natural']); // English name, Ukrainian UI
    expect(ids('clever')).toEqual(['butter', 'yogurt_natural', 'milk_whole']); // brands, by name
    expect(ids('ter')).toEqual(['butter']);
    expect(ids('nothing like it')).toEqual([]);
  });
});

describe('formatVolume', () => {
  it('shows packs and, for more than one, what they hold together', () => {
    expect(formatVolume(1, 0.25, 'kg', 'en', t)).toBe('1 × 250 g');
    expect(formatVolume(2, 0.25, 'kg', 'en', t)).toBe('2 × 250 g (500 g)');
    expect(formatVolume(4, 0.25, 'kg', 'en', t)).toBe('4 × 250 g (1 kg)');
    expect(formatVolume(3, 0.1, 'kg', 'en', t)).toBe('3 × 100 g (300 g)');
    expect(formatVolume(3, 1.5, 'l', 'de', t)).toBe('3 × 1,5 l (4,5 l)');
    expect(formatVolume(2, 6, 'pcs', 'en', t)).toBe('2 × 6 pcs (12 pcs)');
  });
});
