import { describe, expect, it } from 'vitest';
import {
  COMPARE_LIST_KEY,
  CompareList,
  EMPTY_LIST,
  addConcept,
  changeQuantity,
  isSplitThreshold,
  loadCompareList,
  parseCompareList,
  removeConcept,
  saveCompareList,
} from '../compareList';

const LIST: CompareList = {
  ...EMPTY_LIST,
  items: [{ concept_id: 'milk_whole', quantity: 2 }],
  stores: ['Billa'],
};

describe('compare list', () => {
  it('adds a product once and counts it up after that', () => {
    const list = addConcept(addConcept(LIST, 'eggs'), 'milk_whole');

    expect(list.items).toEqual([
      { concept_id: 'milk_whole', quantity: 3 },
      { concept_id: 'eggs', quantity: 1 },
    ]);
    expect(removeConcept(list, 'milk_whole').items).toEqual([{ concept_id: 'eggs', quantity: 1 }]);
  });

  it('keeps quantities within 1-50 and the list within 50 products', () => {
    expect(changeQuantity(LIST, 'milk_whole', -5).items[0].quantity).toBe(1);
    expect(changeQuantity(LIST, 'milk_whole', 100).items[0].quantity).toBe(50);

    const full = {
      ...LIST,
      items: Array.from({ length: 50 }, (_, i) => ({ concept_id: `c${i}`, quantity: 1 })),
    };
    expect(addConcept(full, 'eggs')).toBe(full);
  });

  it.each([
    [0, true],
    [3, true],
    [2.5, true],
    [0.05, true],
    [1000, true],
    [-1, false],
    [1000.01, false],
    [1.234, false],
    [Number.NaN, false],
    ['3', false],
  ])('accepts %s as a split threshold: %s', (value, valid) => {
    expect(isSplitThreshold(value)).toBe(valid);
  });

  it('restores a saved list and ignores one it cannot use', () => {
    saveCompareList(LIST);
    expect(loadCompareList()).toEqual(LIST);

    localStorage.setItem(COMPARE_LIST_KEY, '{not json');
    expect(loadCompareList()).toEqual(EMPTY_LIST);
    localStorage.setItem(COMPARE_LIST_KEY, JSON.stringify({ ...LIST, country: 'CH' }));
    expect(loadCompareList()).toEqual(EMPTY_LIST);
  });

  it('keeps only the fields the request has', () => {
    const parsed = parseCompareList({
      ...LIST,
      extra: true,
      items: [{ concept_id: 'eggs', quantity: 1, note: 'x' }],
    });

    expect(parsed).toEqual({ ...LIST, items: [{ concept_id: 'eggs', quantity: 1 }] });
  });

  it.each([
    ['six stores', { ...LIST, stores: ['A', 'B', 'C', 'D', 'E', 'F'] }],
    ['a repeated store', { ...LIST, stores: ['Billa', 'Billa'] }],
    ['a fractional quantity', { ...LIST, items: [{ concept_id: 'eggs', quantity: 1.5 }] }],
    ['no items array', { ...LIST, items: null }],
    ['a missing threshold', { ...LIST, min_split_savings_eur: undefined }],
  ])('rejects a list with %s', (_, value) => {
    expect(parseCompareList(value)).toBeNull();
  });
});
