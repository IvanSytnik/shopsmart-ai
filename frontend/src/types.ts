/**
 * ShopSmart AI - Type Definitions
 * Author: Ivan Sytnyk (КН-М524)
 */

// ============== API Types ==============

export interface UserInput {
  supermarkets: string[];
  budget: number;
  preferences: string;
  family_size: number;
}

export interface ShoppingItem {
  product: string;
  quantity: string;
  store: string;
  approx_price: string;
  category: ProductCategory;
}

export interface AIResponse {
  items: ShoppingItem[];
  total_cost: number;
  notes?: string;
  generated_at?: string;
}

export interface ApiError {
  error: string;
  detail: string;
  timestamp: string;
}

// ============== UI Types ==============

export type ProductCategory = 
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
  | 'hygiene';

export interface Supermarket {
  id: string;
  name: string;
  type: 'discount' | 'standard' | 'premium' | 'hypermarket';
  color: string;
  icon: string;
}

export interface CategoryInfo {
  id: ProductCategory;
  name: string;
  icon: string;
}

export interface PreferencePreset {
  id: string;
  label: string;
  icon: string;
  value: string;
}

// ============== Component Props ==============

export interface ShopFormProps {
  onSubmit: (data: UserInput) => void;
  loading: boolean;
}

export interface ShoppingListProps {
  data: AIResponse;
  inputData: UserInput;
  onReset: () => void;
}

export interface LoadingSpinnerProps {
  message?: string;
}

export interface ErrorBannerProps {
  message: string;
  onDismiss: () => void;
}

// ============== State Types ==============

export interface AppState {
  loading: boolean;
  result: AIResponse | null;
  error: string | null;
  inputData: UserInput | null;
}

export type AppAction =
  | { type: 'START_LOADING' }
  | { type: 'SET_RESULT'; payload: AIResponse; inputData: UserInput }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'RESET' }
  | { type: 'CLEAR_ERROR' };
