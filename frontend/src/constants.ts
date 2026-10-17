import type { Category, Country, DietTag, Unit } from './types';
import type { TranslationKey } from './translations';

export const BUDGET_PRESETS = [30, 50, 75, 100, 150];

export const BUDGET_MIN = 10;
export const BUDGET_MAX = 1000;

// Backend allows 300 chars for chips + free text combined; all chips together are ≤ 102 chars.
export const PREFERENCES_TEXT_MAX_LENGTH = 190;

export const FAMILY_SIZE_OPTIONS = [1, 2, 3, 4, 5];

export const MAX_STORES = 5;
export const DAY_OPTIONS = [1, 2, 3, 4, 5, 6, 7];

// Display order; a country with no stores in the catalog is hidden.
export const COUNTRIES: readonly { code: Country; key: TranslationKey; flag: string }[] = [
  { code: 'AT', key: 'countryAT', flag: '🇦🇹' },
  { code: 'DE', key: 'countryDE', flag: '🇩🇪' },
];

export const DIET_LABELS: Record<DietTag, { key: TranslationKey; emoji: string }> = {
  vegetarian: { key: 'vegetarian', emoji: '🥗' },
  vegan: { key: 'vegan', emoji: '🌱' },
  gluten_free: { key: 'glutenFree', emoji: '🚫' },
  lactose_free: { key: 'lactoseFree', emoji: '🥛' },
};

export const UNIT_KEYS: Record<Unit, TranslationKey> = {
  kg: 'unitKg',
  l: 'unitL',
  pcs: 'unitPcs',
  pack: 'unitPack',
};

export const CATEGORY_ICONS: Record<Category, string> = {
  vegetables: '🥬',
  fruits: '🍎',
  meat: '🥩',
  fish: '🐟',
  dairy: '🥛',
  bread: '🍞',
  beverages: '🥤',
  snacks: '🍪',
  frozen: '🧊',
  pantry: '🥫',
  cleaning: '🧹',
  hygiene: '🧴',
  other: '📦',
};

// Checked before CATEGORY_ICONS: a keyword that is one segment of the product id
// ("at-billa-eggs-m-10" has "eggs"). Eggs are in dairy, but a milk glass is wrong for them.
export const PRODUCT_ICON_OVERRIDES: readonly { keyword: string; icon: string }[] = [
  { keyword: 'eggs', icon: '🥚' },
];

export const productIcon = (item: { product_id: string; category: Category }): string => {
  const segments = item.product_id.split('-');
  const override = PRODUCT_ICON_OVERRIDES.find(o => segments.includes(o.keyword));
  return override?.icon ?? CATEGORY_ICONS[item.category];
};
