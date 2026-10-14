import type { StoreName } from './types';

export const SUPERMARKETS: { name: StoreName; color: string }[] = [
  { name: 'Lidl', color: 'bg-blue-500' },
  { name: 'Aldi', color: 'bg-orange-500' },
  { name: 'Edeka', color: 'bg-yellow-500' },
  { name: 'Rewe', color: 'bg-red-500' },
  { name: 'Kaufland', color: 'bg-amber-700' },
];

export const BUDGET_PRESETS = [30, 50, 75, 100, 150];

export const BUDGET_MIN = 10;
export const BUDGET_MAX = 1000;

// Backend allows 300 chars for chips + free text combined; all chips together are ≤ 102 chars.
export const PREFERENCES_TEXT_MAX_LENGTH = 190;

export const FAMILY_SIZE_OPTIONS = [1, 2, 3, 4, 5];

export const CATEGORIES = [
  { id: 'vegetables', icon: '🥬' },
  { id: 'fruits', icon: '🍎' },
  { id: 'meat', icon: '🥩' },
  { id: 'fish', icon: '🐟' },
  { id: 'dairy', icon: '🥛' },
  { id: 'bread', icon: '🍞' },
  { id: 'beverages', icon: '🥤' },
  { id: 'snacks', icon: '🍪' },
  { id: 'frozen', icon: '🧊' },
  { id: 'pantry', icon: '🥫' },
  { id: 'cleaning', icon: '🧹' },
  { id: 'hygiene', icon: '🧴' },
  { id: 'other', icon: '📦' },
];
