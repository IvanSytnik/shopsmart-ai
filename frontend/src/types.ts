import type { Language } from './translations';

// Mirrors backend app/schemas/catalog.py.
export type Country = 'AT' | 'DE';
export type DietTag = 'vegetarian' | 'vegan' | 'gluten_free' | 'lactose_free';
export type Unit = 'kg' | 'l' | 'pcs' | 'pack';
// What a menu portion is counted in; 'pack' = a fraction of one pack.
export type PortionUnit = 'g' | 'ml' | 'pcs' | 'pack';
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
// The app's tabs: the two modes of /generate, and comparing a list across stores (/compare).
export type AppMode = Mode | 'compare';

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
  portion_unit: PortionUnit;
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
  // One person's amount in this meal, in the item's portion_unit.
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

export type ResponseWarning = 'low_kcal' | 'budget_trimmed' | 'kcal_topped_up';
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

// Mirrors backend app/schemas/compare.py (GET /api/catalog/concepts, POST /compare).
export interface ConceptSummary {
  concept_id: string;
  name: LocalizedNames; // neutral, without store brands: shown in the list
  names: LocalizedNames[]; // its products' names in the country: searched too
  category: Category;
  unit: Unit;
  stores: string[]; // sorted
  reference_pack_size: number; // what quantity 1 means: the smallest pack, in `unit`
}

export interface ConceptsResponse {
  country: Country;
  concepts: ConceptSummary[]; // sorted by concept_id
}

export interface CompareItemRequest {
  concept_id: string;
  quantity: number; // 1-50 reference packs
}

export interface CompareRequest {
  items: CompareItemRequest[]; // 1-50, unique concept ids
  stores: string[]; // 1-5, unique, from CatalogMeta.countries[country]
  diet_tags?: DietTag[]; // unique; default []
  min_split_savings_eur?: number; // 0-1000, 2 decimals; default 3
  country?: Country; // default 'AT'
}

export interface MatchedStoreItem {
  concept_id: string;
  product_id: string;
  names: LocalizedNames;
  store: string;
  packs_needed: number;
  pack_size: number;
  unit: Unit;
  price_eur: number; // per pack, today: the promo price while a promotion runs
  regular_price_eur: number;
  promo_price_eur: number | null; // only while the promotion runs
  promo_valid_until: string | null; // YYYY-MM-DD, only while the promotion runs
  line_total_eur: number;
  price_per_base_unit_eur: number; // per 1 kg, 1 l, 1 piece or 1 pack (`unit`)
}

export interface StoreComparison {
  store: string;
  items: MatchedStoreItem[]; // in request order
  total_eur: number;
  promo_savings_eur: number;
  missing_concepts: string[]; // requested concepts this store doesn't sell (for the diets)
}

export interface SplitStoreGroup {
  store: string;
  items: MatchedStoreItem[];
  total_eur: number;
}

export interface SplitBasket {
  stores: SplitStoreGroup[]; // only stores with items, sorted by name
  total_eur: number;
  missing_concepts: string[]; // sold by none of the stores (for the diets)
  total_savings_vs_worst_eur: number;
}

export type Strategy = 'single_store' | 'split_basket';

export interface CompareResponse {
  // Fewest missing concepts first, then the lowest total, then the store name.
  single_store_rankings: StoreComparison[];
  split_basket: SplitBasket;
  recommended_strategy: Strategy;
  recommended_store: string | null; // the best single store; null for split_basket
  split_extra_savings_eur: number; // what the split saves over the best single store
  catalog_version: string;
  price_date: string; // YYYY-MM-DD
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
