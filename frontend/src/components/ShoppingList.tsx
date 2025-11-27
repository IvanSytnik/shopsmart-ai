import React, { useState } from 'react';
import { AIResponse } from '../types';
import { CATEGORIES } from '../constants';
import { useLanguage } from '../LanguageContext';

interface ShoppingListProps {
  response: AIResponse;
  onReset: () => void;
}

export const ShoppingList: React.FC<ShoppingListProps> = ({ response, onReset }) => {
  const { t } = useLanguage();
  const [checkedItems, setCheckedItems] = useState<Set<number>>(new Set());

  const toggleItem = (index: number) => {
    setCheckedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const groupedByStore = response.items.reduce((acc, item) => {
    if (!acc[item.store]) acc[item.store] = [];
    acc[item.store].push(item);
    return acc;
  }, {} as Record<string, typeof response.items>);

  const getCategoryIcon = (category: string) => {
    const cat = CATEGORIES.find(c => c.id.toLowerCase() === category.toLowerCase());
    return cat?.icon || '📦';
  };

  const copyToClipboard = () => {
    const text = response.items.map(item => `${item.product} - ${item.quantity} (${item.store}) €${item.approx_price}`).join('\n');
    navigator.clipboard.writeText(text);
  };

  const stores = Object.keys(groupedByStore);
  const progress = (checkedItems.size / response.items.length) * 100;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Stats */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 transition-colors">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-200 mb-4">{t('yourShoppingList')}</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-blue-50 dark:bg-blue-900/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{response.items.length}</div>
            <div className="text-sm text-blue-600 dark:text-blue-400">{t('items')}</div>
          </div>
          <div className="bg-green-50 dark:bg-green-900/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">€{response.total_cost.toFixed(2)}</div>
            <div className="text-sm text-green-600 dark:text-green-400">{t('estimatedCost')}</div>
          </div>
          <div className="bg-purple-50 dark:bg-purple-900/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{stores.length}</div>
            <div className="text-sm text-purple-600 dark:text-purple-400">{t('stores')}</div>
          </div>
          <div className="bg-orange-50 dark:bg-orange-900/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">{progress.toFixed(0)}%</div>
            <div className="text-sm text-orange-600 dark:text-orange-400">{t('completed')}</div>
          </div>
        </div>
      </div>

      {/* Items by Store */}
      {Object.entries(groupedByStore).map(([store, items]) => (
        <div key={store} className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl overflow-hidden transition-colors">
          <div className="bg-gradient-to-r from-primary-500 to-purple-600 px-6 py-4">
            <h3 className="text-lg font-semibold text-white">{store}</h3>
            <p className="text-primary-100 text-sm">{items.length} {t('items')} • €{items.reduce((sum, i) => sum + Number(i.approx_price), 0).toFixed(2)}</p>
          </div>
          <div className="divide-y dark:divide-gray-700">
            {items.map((item, idx) => {
              const globalIdx = response.items.indexOf(item);
              const isChecked = checkedItems.has(globalIdx);
              return (
                <div key={idx} onClick={() => toggleItem(globalIdx)} className={`flex items-center gap-4 p-4 cursor-pointer transition-all ${isChecked ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'}`}>
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${isChecked ? 'bg-green-500 border-green-500' : 'border-gray-300 dark:border-gray-600'}`}>
                    {isChecked && <span className="text-white text-sm">✓</span>}
                  </div>
                  <span className="text-2xl">{getCategoryIcon(item.category)}</span>
                  <div className="flex-1">
                    <div className={`font-medium ${isChecked ? 'line-through text-gray-400 dark:text-gray-500' : 'text-gray-800 dark:text-gray-200'}`}>{item.product}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">{item.quantity}</div>
                    {item.calories && item.calories > 0 && (
                      <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                        🔥{item.calories} • 🥩{item.protein}g • 🧈{item.fat}g • 🍞{item.carbs}g
                      </div>
                    )}
                  </div>
                  <div className="font-semibold text-gray-800 dark:text-gray-200">€{item.approx_price}</div>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <button onClick={copyToClipboard} className="flex-1 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-all">📋 {t('copyToClipboard')}</button>
        <button onClick={() => window.print()} className="flex-1 py-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-all">🖨️ {t('print')}</button>
        <button onClick={onReset} className="flex-1 py-3 bg-gradient-to-r from-primary-500 to-purple-600 text-white rounded-xl hover:from-primary-600 hover:to-purple-700 transition-all">✨ {t('newList')}</button>
      </div>
    </div>
  );
};
