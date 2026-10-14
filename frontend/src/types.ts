import type { Language } from './translations';

export type StoreName = 'Lidl' | 'Aldi' | 'Edeka' | 'Rewe' | 'Kaufland';

// Mirrors backend app/schemas/requests.py (GenerateRequest).
export interface UserInput {
  supermarkets: StoreName[]; // 1-5, unique
  budget: number; // 10-1000
  preferences: string; // max 300 chars after trimming
  family_size: number; // 1-10
  language: Language;
  mode: 'shopping' | 'menu';
  days?: number; // 1-7, only used for mode 'menu'
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
