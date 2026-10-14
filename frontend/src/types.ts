import type { Language } from './translations';

export type StoreName = 'Lidl' | 'Aldi' | 'Edeka' | 'Rewe' | 'Kaufland';

// Mirrors backend app/schemas/catalog.py (DietTag, Country).
export type DietTag = 'vegetarian' | 'vegan' | 'gluten_free' | 'lactose_free';
export type Country = 'AT' | 'DE';

// Mirrors backend app/schemas/requests.py (GenerateRequest).
export interface UserInput {
  supermarkets: StoreName[]; // 1-5, unique
  budget: number; // 10-1000
  preferences: string; // max 300 chars after trimming
  diets: DietTag[]; // unique
  country?: Country; // backend default 'AT'; not in the UI yet
  family_size: number; // 1-10
  language: Language;
  mode: 'shopping' | 'menu';
  days?: number; // 1-7, only used for mode 'menu'
}

// Mirrors backend app/errors.py: every error response is { detail, code }.
export type ApiErrorCode =
  | 'validation_error'
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

export interface ShoppingItem {
  product: string;
  quantity: string;
  store: string;
  approx_price: number;
  category: string;
  calories?: number;
  protein?: number;
  fat?: number;
  carbs?: number;
}

export interface Meal {
  name: string;
  description: string;
  calories?: number;
}

export interface DayMenu {
  day: string;
  breakfast: Meal;
  lunch: Meal;
  dinner: Meal;
  snack?: Meal;
}

export interface AIResponse {
  items: ShoppingItem[];
  total_cost: number;
  notes: string;
  generated_at: string;
  total_nutrition?: {
    calories: number;
    protein: number;
    fat: number;
    carbs: number;
  };
  menu?: DayMenu[];
}

export type ProductCategory = 
  | 'vegetables' | 'fruits' | 'meat' | 'fish' | 'dairy' 
  | 'bread' | 'beverages' | 'snacks' | 'frozen' | 'pantry' 
  | 'cleaning' | 'hygiene' | 'other';
