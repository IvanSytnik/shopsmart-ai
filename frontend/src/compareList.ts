import { COUNTRIES, DIET_LABELS, MAX_STORES } from './constants';
import { readStorage, writeStorage } from './history';
import type { CompareItemRequest, CompareRequest, Country, DietTag } from './types';

// The list being built in the compare tab is the request itself, every field filled in.
export type CompareList = Required<CompareRequest>;

export const COMPARE_LIST_KEY = 'shopsmart-compare-list-v1';
// Backend limits (app/schemas/compare.py).
export const MAX_COMPARE_ITEMS = 50;
export const MAX_QUANTITY = 50;
export const SPLIT_THRESHOLD_DEFAULT = 3;
export const SPLIT_THRESHOLD_MAX = 1000;

export const EMPTY_LIST: CompareList = {
  items: [],
  stores: [],
  diet_tags: [],
  min_split_savings_eur: SPLIT_THRESHOLD_DEFAULT,
  country: 'AT',
};

const CONCEPT_ID = /^[a-z0-9]+(?:_[a-z0-9]+)*$/;
const COUNTRY_CODES: readonly string[] = COUNTRIES.map(c => c.code);
const DIET_TAGS: readonly string[] = Object.keys(DIET_LABELS);

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

const isUnique = (values: unknown[]): boolean => new Set(values).size === values.length;

const isItem = (value: unknown): value is CompareItemRequest =>
  isObject(value) &&
  typeof value.concept_id === 'string' &&
  value.concept_id.length <= 80 &&
  CONCEPT_ID.test(value.concept_id) &&
  Number.isInteger(value.quantity) &&
  (value.quantity as number) >= 1 &&
  (value.quantity as number) <= MAX_QUANTITY;

/** Money the backend accepts: 0-1000 with at most 2 decimals. */
export const isSplitThreshold = (value: unknown): value is number =>
  typeof value === 'number' &&
  Number.isFinite(value) &&
  value >= 0 &&
  value <= SPLIT_THRESHOLD_MAX &&
  Math.abs(value * 100 - Math.round(value * 100)) < 1e-9;

/**
 * A list from storage or a share link, if it is one the backend would accept (apart from
 * being empty or having no stores, which the form shows); null otherwise.
 */
export function parseCompareList(value: unknown): CompareList | null {
  if (!isObject(value)) return null;
  const { items, stores, diet_tags, min_split_savings_eur, country } = value;
  if (
    !Array.isArray(items) ||
    items.length > MAX_COMPARE_ITEMS ||
    !items.every(isItem) ||
    !isUnique(items.map(i => i.concept_id)) ||
    !Array.isArray(stores) ||
    stores.length > MAX_STORES ||
    !stores.every(s => typeof s === 'string' && s.length > 0 && s.length <= 50) ||
    !isUnique(stores) ||
    !Array.isArray(diet_tags) ||
    !diet_tags.every(d => typeof d === 'string' && DIET_TAGS.includes(d)) ||
    !isUnique(diet_tags) ||
    !isSplitThreshold(min_split_savings_eur) ||
    typeof country !== 'string' ||
    !COUNTRY_CODES.includes(country)
  ) {
    return null;
  }
  return {
    items: items.map(({ concept_id, quantity }) => ({ concept_id, quantity })),
    stores: [...stores],
    diet_tags: diet_tags as DietTag[],
    min_split_savings_eur,
    country: country as Country,
  };
}

/** The saved list, or an empty one if there is none (or it can't be read). */
export function loadCompareList(): CompareList {
  const raw = readStorage(COMPARE_LIST_KEY);
  if (raw === null) return EMPTY_LIST;
  try {
    return parseCompareList(JSON.parse(raw)) ?? EMPTY_LIST;
  } catch {
    return EMPTY_LIST;
  }
}

export function saveCompareList(list: CompareList): void {
  writeStorage(COMPARE_LIST_KEY, JSON.stringify(list));
}

/** Adds one reference pack of `conceptId`: a new line, or one more on its line. */
export function addConcept(list: CompareList, conceptId: string): CompareList {
  if (list.items.some(i => i.concept_id === conceptId)) {
    return changeQuantity(list, conceptId, 1);
  }
  if (list.items.length >= MAX_COMPARE_ITEMS) return list;
  return { ...list, items: [...list.items, { concept_id: conceptId, quantity: 1 }] };
}

/** Changes a line's quantity by `delta`, kept within 1-50. */
export function changeQuantity(list: CompareList, conceptId: string, delta: number): CompareList {
  return {
    ...list,
    items: list.items.map(i =>
      i.concept_id === conceptId
        ? { ...i, quantity: Math.min(MAX_QUANTITY, Math.max(1, i.quantity + delta)) }
        : i
    ),
  };
}

export function removeConcept(list: CompareList, conceptId: string): CompareList {
  return { ...list, items: list.items.filter(i => i.concept_id !== conceptId) };
}
