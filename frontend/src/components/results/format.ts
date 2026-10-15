import { UNIT_KEYS } from '../../constants';
import type { Language, TranslationKey } from '../../translations';
import type { GenerateResponse, Item, PortionUnit, TrimmedItem, Unit } from '../../types';

export type Translate = (key: TranslationKey, vars?: Record<string, string | number>) => string;

const LOCALES: Record<Language, string> = { en: 'en-GB', uk: 'uk-UA', de: 'de-AT' };

export const money = (value: number): string => value.toFixed(2);

const number = (value: number, language: Language): string =>
  new Intl.NumberFormat(LOCALES[language], { maximumFractionDigits: 3 }).format(value);

/** Pack size for display: under 1 kg / 1 l in g / ml; whole numbers without decimals. */
export const formatSize = (size: number, unit: Unit, language: Language, t: Translate): string => {
  if (unit === 'kg' && size < 1)
    return `${number(Math.round(size * 1000), language)} ${t('unitG')}`;
  if (unit === 'l' && size < 1)
    return `${number(Math.round(size * 1000), language)} ${t('unitMl')}`;
  return `${number(size, language)} ${t(UNIT_KEYS[unit])}`;
};

/** A per-person meal portion: g for products sold by kg, ml for l, pieces otherwise. */
const PORTION_UNIT_KEYS: Record<PortionUnit, TranslationKey> = {
  g: 'unitG',
  ml: 'unitMl',
  pcs: 'unitPcs',
  pack: 'unitPack',
};

// Plans saved before `portion_unit` existed: g for kg, ml for l, pieces otherwise.
const LEGACY_PORTION_UNITS: Record<Unit, PortionUnit> = {
  kg: 'g',
  l: 'ml',
  pcs: 'pcs',
  pack: 'pcs',
};

export const portionUnitOf = (item: Pick<Item, 'unit' | 'portion_unit'>): PortionUnit =>
  item.portion_unit ?? LEGACY_PORTION_UNITS[item.unit];

/** A per-person meal portion: "80 g", "200 ml", "2 pcs", "0.5 pack". */
export const formatPortion = (
  amount: number,
  portionUnit: PortionUnit,
  language: Language,
  t: Translate
): string => `${number(amount, language)} ${t(PORTION_UNIT_KEYS[portionUnit])}`;

/** A YYYY-MM-DD date in the UI language. */
export const formatDate = (isoDate: string, language: Language): string => {
  const date = new Date(`${isoDate}T00:00:00`);
  return Number.isNaN(date.getTime()) ? isoDate : date.toLocaleDateString(LOCALES[language]);
};

/**
 * Fallback name derived from an id ("<country>-<store>-<slug>"), for plans saved before
 * `trimmed[].name` existed.
 */
export const nameFromId = (productId: string): string =>
  productId.split('-').slice(2).join(' ') || productId;

/**
 * A product name in the UI language. Plans saved in history before `names` existed only
 * have `name` (the language the plan was made in), and older ones may lack even that.
 */
export const productName = (
  entry: Pick<Item | TrimmedItem, 'product_id' | 'name' | 'names'>,
  language: Language
): string => entry.names?.[language] || entry.name || nameFromId(entry.product_id);

export const itemsById = (response: GenerateResponse): Map<string, Item> =>
  new Map(response.items.map(item => [item.product_id, item]));

export const groupByStore = (items: Item[]): [string, Item[]][] => {
  const groups = new Map<string, Item[]>();
  for (const item of items) {
    groups.set(item.store, [...(groups.get(item.store) ?? []), item]);
  }
  return [...groups.entries()];
};
