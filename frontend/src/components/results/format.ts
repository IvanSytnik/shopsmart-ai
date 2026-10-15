import type { Language } from '../../translations';
import type { GenerateResponse, Item } from '../../types';

const LOCALES: Record<Language, string> = { en: 'en-GB', uk: 'uk-UA', de: 'de-AT' };

export const money = (value: number): string => value.toFixed(2);

/** A YYYY-MM-DD date in the UI language. */
export const formatDate = (isoDate: string, language: Language): string => {
  const date = new Date(`${isoDate}T00:00:00`);
  return Number.isNaN(date.getTime()) ? isoDate : date.toLocaleDateString(LOCALES[language]);
};

/**
 * A readable name for a product that is no longer in `items` (removed to fit the budget).
 * The response has no name for it, so derive one from the id: "<country>-<store>-<slug>".
 */
export const nameFromId = (productId: string): string =>
  productId.split('-').slice(2).join(' ') || productId;

export const itemsById = (response: GenerateResponse): Map<string, Item> =>
  new Map(response.items.map(item => [item.product_id, item]));

export const groupByStore = (items: Item[]): [string, Item[]][] => {
  const groups = new Map<string, Item[]>();
  for (const item of items) {
    groups.set(item.store, [...(groups.get(item.store) ?? []), item]);
  }
  return [...groups.entries()];
};
