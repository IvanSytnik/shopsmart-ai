import { describe, expect, it } from 'vitest';
import { pluralForm } from '../plural';
import { pluralNouns } from '../translations';

const form = (language: 'en' | 'uk' | 'de', noun: 'item' | 'store' | 'person', count: number) =>
  `${count} ${pluralForm(language, count, pluralNouns[language][noun])}`;

describe('pluralForm', () => {
  it('uses one / other in English and German', () => {
    expect([1, 2, 0].map(n => form('en', 'store', n))).toEqual(['1 store', '2 stores', '0 stores']);
    expect(form('en', 'person', 1)).toBe('1 person');
    expect(form('en', 'person', 3)).toBe('3 people');
    expect(form('de', 'store', 1)).toBe('1 Geschäft');
    expect(form('de', 'store', 4)).toBe('4 Geschäfte');
    expect(form('de', 'item', 1)).toBe('1 Artikel');
  });

  it('uses one / few / many / other in Ukrainian', () => {
    expect([1, 2, 5, 11, 21, 22, 25].map(n => form('uk', 'item', n))).toEqual([
      '1 товар',
      '2 товари',
      '5 товарів',
      '11 товарів',
      '21 товар',
      '22 товари',
      '25 товарів',
    ]);
    expect(form('uk', 'item', 1.5)).toBe('1.5 товару');
    expect([1, 3, 5].map(n => form('uk', 'person', n))).toEqual(['1 особа', '3 особи', '5 осіб']);
  });

  it('falls back to `other` for a category without its own form', () => {
    expect(pluralForm('uk', 2, { other: 'x' })).toBe('x');
  });
});
