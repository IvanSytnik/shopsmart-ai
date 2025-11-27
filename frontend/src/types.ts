export interface UserInput {
  supermarkets: string[];
  budget: number;
  preferences: string;
  family_size: number;
  language: string;
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
}

export type ProductCategory = 
  | 'vegetables' | 'fruits' | 'meat' | 'fish' | 'dairy' 
  | 'bread' | 'beverages' | 'snacks' | 'frozen' | 'pantry' 
  | 'cleaning' | 'hygiene' | 'other';
