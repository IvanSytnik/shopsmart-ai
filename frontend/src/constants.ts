/**
 * ShopSmart AI - Constants
 * Author: Ivan Sytnyk (КН-М524)
 */

import type { Supermarket, CategoryInfo, PreferencePreset } from './types';

// ============== Supermarkets ==============

export const SUPERMARKETS: Supermarket[] = [
  { 
    id: 'lidl', 
    name: 'Lidl', 
    type: 'discount',
    color: '#0050aa',
    icon: '🔵'
  },
  { 
    id: 'aldi', 
    name: 'Aldi', 
    type: 'discount',
    color: '#00005f',
    icon: '🟠'
  },
  { 
    id: 'edeka', 
    name: 'Edeka', 
    type: 'premium',
    color: '#fff000',
    icon: '🟡'
  },
  { 
    id: 'rewe', 
    name: 'Rewe', 
    type: 'standard',
    color: '#cc0000',
    icon: '🔴'
  },
  { 
    id: 'kaufland', 
    name: 'Kaufland', 
    type: 'hypermarket',
    color: '#e30613',
    icon: '🟤'
  }
];

// ============== Categories ==============

export const CATEGORIES: CategoryInfo[] = [
  { id: 'vegetables', name: 'Vegetables', icon: '🥬' },
  { id: 'fruits', name: 'Fruits', icon: '🍎' },
  { id: 'meat', name: 'Meat', icon: '🥩' },
  { id: 'fish', name: 'Fish', icon: '🐟' },
  { id: 'dairy', name: 'Dairy', icon: '🥛' },
  { id: 'bread', name: 'Bread & Bakery', icon: '🍞' },
  { id: 'beverages', name: 'Beverages', icon: '🥤' },
  { id: 'snacks', name: 'Snacks', icon: '🍪' },
  { id: 'frozen', name: 'Frozen Foods', icon: '🧊' },
  { id: 'pantry', name: 'Pantry', icon: '🥫' },
  { id: 'cleaning', name: 'Cleaning', icon: '🧹' },
  { id: 'hygiene', name: 'Hygiene', icon: '🧴' }
];

export const CATEGORY_ICONS: Record<string, string> = {
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
  default: '🛒'
};

// ============== Preference Presets ==============

export const PREFERENCE_PRESETS: PreferencePreset[] = [
  { 
    id: 'vegetarian',
    label: 'Vegetarian', 
    icon: '🥗',
    value: 'vegetarian diet, no meat' 
  },
  { 
    id: 'vegan',
    label: 'Vegan', 
    icon: '🌱',
    value: 'vegan diet, no animal products' 
  },
  { 
    id: 'gluten-free',
    label: 'Gluten-Free', 
    icon: '🚫',
    value: 'gluten-free products only' 
  },
  { 
    id: 'high-protein',
    label: 'High Protein', 
    icon: '💪',
    value: 'high protein foods, fitness diet' 
  },
  { 
    id: 'low-carb',
    label: 'Low Carb', 
    icon: '🏃',
    value: 'low carbohydrate diet, keto friendly' 
  },
  { 
    id: 'family',
    label: 'Family Friendly', 
    icon: '👶',
    value: 'family friendly meals, kid-friendly options' 
  },
  { 
    id: 'organic',
    label: 'Organic', 
    icon: '🌿',
    value: 'prefer organic and bio products' 
  },
  { 
    id: 'budget',
    label: 'Budget Saver', 
    icon: '💰',
    value: 'focus on cheapest options, maximize quantity' 
  }
];

// ============== Budget Presets ==============

export const BUDGET_PRESETS = [30, 50, 75, 100, 150];

// ============== Family Size Options ==============

export const FAMILY_SIZE_OPTIONS = [
  { value: 1, label: '1 person' },
  { value: 2, label: '2 people' },
  { value: 3, label: '3 people' },
  { value: 4, label: '4 people' },
  { value: 5, label: '5+ people' }
];

// ============== API Configuration ==============

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_TIMEOUT = 30000; // 30 seconds

// ============== Store Colors ==============

export const STORE_COLORS: Record<string, string> = {
  'Lidl': 'bg-blue-600',
  'Aldi': 'bg-orange-600',
  'Edeka': 'bg-yellow-500',
  'Rewe': 'bg-red-600',
  'Kaufland': 'bg-red-700'
};

export const getStoreColor = (storeName: string): string => {
  return STORE_COLORS[storeName] || 'bg-gray-600';
};

// ============== Helper Functions ==============

export const getCategoryIcon = (category: string): string => {
  const key = category?.toLowerCase() || 'default';
  return CATEGORY_ICONS[key] || CATEGORY_ICONS['default'];
};

export const getSupermarketByName = (name: string): Supermarket | undefined => {
  return SUPERMARKETS.find(s => s.name.toLowerCase() === name.toLowerCase());
};

export const formatPrice = (price: string | number): string => {
  const numPrice = typeof price === 'string' ? parseFloat(price) : price;
  return isNaN(numPrice) ? '0.00' : numPrice.toFixed(2);
};
