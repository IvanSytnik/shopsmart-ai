export interface UserInput {
  supermarkets: string[];
  budget: number;
  preferences: string;
  family_size: number;
  language: string;
  mode: 'shopping' | 'menu';
  days?: number;
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
