import type { Language } from './translations';

// Mirrors backend app/schemas/catalog.py.
export type Country = 'AT' | 'DE';
export type DietTag = 'vegetarian' | 'vegan' | 'gluten_free' | 'lactose_free';
export type Unit = 'kg' | 'l' | 'pcs' | 'pack';
export type Category =
  | 'vegetables'
  | 'fruits'
  | 'meat'
  | 'fish'
  | 'dairy'
  | 'bread'
  | 'beverages'
  | 'snacks'
  | 'frozen'
  | 'pantry'
  | 'cleaning'
  | 'hygiene'
  | 'other';

export type Mode = 'shopping' | 'menu';

// Mirrors backend app/schemas/requests.py (GenerateRequest).
export interface GenerateRequest {
  country: Country;
  supermarkets: string[]; // 1-5, unique, from CatalogMeta.countries[country]
  budget: number; // 10-1000
  family_size: number; // 1-10
  diets: DietTag[]; // unique
  preferences: string; // max 300 chars after trimming
  language: Language;
  mode: Mode;
  days: number; // 1-7, only used for mode 'menu'
}

// Mirrors backend app/schemas/responses.py.
export type LocalizedNames = Record<Language, string>;

export interface Nutrition {
  kcal: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
}

export interface Item {
  product_id: string;
  name: string; // in the request language
  names: LocalizedNames; // from the catalog; the UI shows the current language
  store: string;
  category: Category;
  packs: number;
  pack_size: number;
  unit: Unit;
  unit_price: number; // per pack
  line_total: number;
  nutrition: Nutrition | null; // for all packs; null for non-food
}

export interface TrimmedItem {
  product_id: string;
  name: string; // in the request language; removed lines aren't in `items`
  names: LocalizedNames;
  from_packs: number;
  to_packs: number; // 0 = removed
}

export interface MealIngredient {
  product_id: string;
  // One person's amount in this meal: g (unit kg), ml (unit l) or pieces (pcs, pack).
  amount_per_person: number;
}

export interface Meal {
  name: string;
  description: string;
  ingredients: MealIngredient[];
}

export interface DayMenu {
  day: string;
  breakfast: Meal;
  lunch: Meal;
  dinner: Meal;
  snack: Meal | null;
}

export type ResponseWarning = 'low_kcal' | 'budget_trimmed';
// menu: what the menu's portions provide; purchased: all purchased packs (an upper bound).
export type KcalBasis = 'menu' | 'purchased';

export interface GenerateResponse {
  items: Item[];
  subtotals_by_store: Record<string, number>;
  total: number;
  budget: number;
  budget_remaining: number;
  nutrition_totals: Nutrition;
  kcal_per_person_day: number; // see kcal_basis
  kcal_basis: KcalBasis;
  trimmed: TrimmedItem[];
  menu: DayMenu[] | null;
  notes: string;
  warnings: ResponseWarning[];
  catalog_version: string;
  price_date: string; // YYYY-MM-DD
  generated_at: string; // ISO 8601 with time zone
}

export interface CatalogMeta {
  catalog_version: string;
  price_date: string; // YYYY-MM-DD
  countries: Record<Country, string[]>; // every country; an empty list = no stores
  diet_tags: DietTag[];
  categories: Category[];
}

// Mirrors backend app/errors.py: every error response is { detail, code }.
export type ApiErrorCode =
  | 'validation_error'
  | 'unknown_store'
  | 'not_enough_products'
  | 'rate_limited'
  | 'daily_limit'
  | 'ai_unavailable'
  | 'ai_timeout'
  | 'generation_failed';

export interface ApiErrorBody {
  detail: string;
  code: ApiErrorCode;
  errors?: { loc: (string | number)[]; msg: string }[]; // only for validation_error
}
