/**
 * ShopSmart AI - Shopping List Component
 * Author: Ivan Sytnyk (КН-М524)
 */

import React, { useState, useMemo, useCallback } from 'react';
import type { ShoppingListProps, ShoppingItem } from '../types';
import { getCategoryIcon, getStoreColor, formatPrice } from '../constants';

const ShoppingList: React.FC<ShoppingListProps> = ({ data, inputData, onReset }) => {
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({});
  const [sortBy, setSortBy] = useState<'store' | 'category' | 'price'>('store');

  // Group items by store
  const groupedByStore = useMemo(() => {
    return data.items.reduce((acc, item) => {
      const store = item.store || 'Other';
      if (!acc[store]) {
        acc[store] = [];
      }
      acc[store].push(item);
      return acc;
    }, {} as Record<string, ShoppingItem[]>);
  }, [data.items]);

  // Calculate statistics
  const stats = useMemo(() => {
    const totalChecked = Object.values(checkedItems).filter(Boolean).length;
    const progress = (totalChecked / data.items.length) * 100;
    const budgetUsed = ((data.total_cost / inputData.budget) * 100).toFixed(0);
    
    return {
      totalChecked,
      progress,
      budgetUsed,
      storeCount: Object.keys(groupedByStore).length,
    };
  }, [checkedItems, data.items.length, data.total_cost, inputData.budget, groupedByStore]);

  // Toggle item checked state
  const toggleItem = useCallback((storeIndex: number, itemIndex: number) => {
    const key = `${storeIndex}-${itemIndex}`;
    setCheckedItems((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  }, []);

  // Copy list to clipboard
  const copyToClipboard = useCallback(() => {
    const text = Object.entries(groupedByStore)
      .map(
        ([store, items]) =>
          `📍 ${store}:\n${items
            .map((i) => `  • ${i.product} (${i.quantity}) - €${i.approx_price}`)
            .join('\n')}`
      )
      .join('\n\n');
    
    navigator.clipboard?.writeText(text);
    alert('Shopping list copied to clipboard!');
  }, [groupedByStore]);

  // Calculate store total
  const getStoreTotal = useCallback((items: ShoppingItem[]) => {
    return items.reduce((sum, item) => {
      const price = parseFloat(item.approx_price) || 0;
      return sum + price;
    }, 0);
  }, []);

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Header Card */}
      <div className="bg-white rounded-2xl shadow-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-3xl font-bold text-gray-800 flex items-center">
              <span className="mr-3">📋</span>
              Your Shopping List
            </h2>
            <p className="text-gray-500 mt-1">
              Generated for €{inputData.budget} budget, {inputData.family_size} person(s)
            </p>
          </div>
          <button
            onClick={onReset}
            className="px-5 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-medium transition-all flex items-center"
          >
            <span className="mr-2">←</span>
            New List
          </button>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
          <div className="bg-gradient-to-br from-indigo-50 to-purple-50 p-4 rounded-xl">
            <p className="text-sm text-gray-600">Total Items</p>
            <p className="text-2xl font-bold text-indigo-600">{data.items.length}</p>
          </div>
          <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-4 rounded-xl">
            <p className="text-sm text-gray-600">Estimated Total</p>
            <p className="text-2xl font-bold text-green-600">
              €{formatPrice(data.total_cost)}
            </p>
          </div>
          <div className="bg-gradient-to-br from-orange-50 to-yellow-50 p-4 rounded-xl">
            <p className="text-sm text-gray-600">Stores</p>
            <p className="text-2xl font-bold text-orange-600">{stats.storeCount}</p>
          </div>
          <div className="bg-gradient-to-br from-pink-50 to-rose-50 p-4 rounded-xl">
            <p className="text-sm text-gray-600">Budget Used</p>
            <p className="text-2xl font-bold text-pink-600">{stats.budgetUsed}%</p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-2">
            <span>Shopping Progress</span>
            <span>
              {stats.totalChecked} / {data.items.length} items
            </span>
          </div>
          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300"
              style={{ width: `${stats.progress}%` }}
            />
          </div>
        </div>

        {/* Notes */}
        {data.notes && (
          <div className="p-4 bg-amber-50 border-l-4 border-amber-400 rounded-r-xl">
            <p className="text-sm text-amber-800">
              <strong className="mr-2">💡 AI Tips:</strong>
              {data.notes}
            </p>
          </div>
        )}
      </div>

      {/* Sort Controls */}
      <div className="flex items-center justify-between mb-4 px-2">
        <span className="text-sm text-gray-600">Sort by:</span>
        <div className="flex gap-2">
          {(['store', 'category', 'price'] as const).map((option) => (
            <button
              key={option}
              onClick={() => setSortBy(option)}
              className={`px-3 py-1 text-sm rounded-lg transition-all ${
                sortBy === option
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {option.charAt(0).toUpperCase() + option.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Shopping Lists by Store */}
      <div className="space-y-6">
        {Object.entries(groupedByStore).map(([store, items], storeIndex) => {
          const storeTotal = getStoreTotal(items);

          return (
            <div
              key={store}
              className="bg-white rounded-2xl shadow-lg overflow-hidden"
            >
              {/* Store Header */}
              <div className={`${getStoreColor(store)} px-6 py-4`}>
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold text-white flex items-center">
                    <span className="mr-3 text-2xl">🏪</span>
                    {store}
                  </h3>
                  <div className="flex items-center space-x-4 text-white">
                    <span className="text-sm opacity-90">{items.length} items</span>
                    <span className="font-bold">€{formatPrice(storeTotal)}</span>
                  </div>
                </div>
              </div>

              {/* Items List */}
              <div className="p-4">
                <div className="space-y-2">
                  {items.map((item, itemIndex) => {
                    const key = `${storeIndex}-${itemIndex}`;
                    const isChecked = checkedItems[key];

                    return (
                      <div
                        key={itemIndex}
                        onClick={() => toggleItem(storeIndex, itemIndex)}
                        className={`flex items-center p-4 rounded-xl cursor-pointer transition-all ${
                          isChecked
                            ? 'bg-green-50 border-2 border-green-200'
                            : 'bg-gray-50 hover:bg-gray-100 border-2 border-transparent'
                        }`}
                      >
                        {/* Checkbox */}
                        <div
                          className={`w-6 h-6 rounded-full border-2 flex items-center justify-center mr-4 transition-all ${
                            isChecked
                              ? 'bg-green-500 border-green-500'
                              : 'border-gray-300'
                          }`}
                        >
                          {isChecked && (
                            <svg
                              className="w-4 h-4 text-white"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={3}
                                d="M5 13l4 4L19 7"
                              />
                            </svg>
                          )}
                        </div>

                        {/* Category Icon */}
                        <span className="text-2xl mr-4">
                          {getCategoryIcon(item.category)}
                        </span>

                        {/* Product Info */}
                        <div
                          className={`flex-1 ${
                            isChecked ? 'line-through text-gray-400' : ''
                          }`}
                        >
                          <h4 className="font-semibold text-gray-800">
                            {item.product}
                          </h4>
                          <div className="flex items-center space-x-3 mt-1 text-sm text-gray-500">
                            <span className="bg-white px-2 py-0.5 rounded-md">
                              📦 {item.quantity}
                            </span>
                            <span className="bg-white px-2 py-0.5 rounded-md capitalize">
                              {item.category}
                            </span>
                          </div>
                        </div>

                        {/* Price */}
                        <div className={`text-right ${isChecked ? 'text-gray-400' : ''}`}>
                          <p className="text-xl font-bold text-indigo-600">
                            €{item.approx_price}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Buttons */}
      <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
        <button
          onClick={copyToClipboard}
          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium transition-all flex items-center justify-center"
        >
          <span className="mr-2">📋</span>
          Copy to Clipboard
        </button>
        <button
          onClick={() => window.print()}
          className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-xl font-medium transition-all flex items-center justify-center"
        >
          <span className="mr-2">🖨️</span>
          Print List
        </button>
        <button
          onClick={onReset}
          className="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-xl font-medium transition-all flex items-center justify-center"
        >
          <span className="mr-2">🔄</span>
          Generate New List
        </button>
      </div>
    </div>
  );
};

export default ShoppingList;
