/**
 * ShopSmart AI - Shopping Form Component
 * Author: Ivan Sytnyk (КН-М524)
 */

import React, { useState, useCallback } from 'react';
import type { ShopFormProps, UserInput } from '../types';
import {
  SUPERMARKETS,
  PREFERENCE_PRESETS,
  BUDGET_PRESETS,
  FAMILY_SIZE_OPTIONS,
} from '../constants';

const ShopForm: React.FC<ShopFormProps> = ({ onSubmit, loading }) => {
  const [selectedMarkets, setSelectedMarkets] = useState<string[]>([]);
  const [budget, setBudget] = useState<string>('');
  const [preferences, setPreferences] = useState<string>('');
  const [familySize, setFamilySize] = useState<number>(2);
  const [activePresets, setActivePresets] = useState<Set<string>>(new Set());

  const handleMarketToggle = useCallback((marketName: string) => {
    setSelectedMarkets((prev) =>
      prev.includes(marketName)
        ? prev.filter((m) => m !== marketName)
        : [...prev, marketName]
    );
  }, []);

  const handlePresetToggle = useCallback((preset: typeof PREFERENCE_PRESETS[0]) => {
    setActivePresets((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(preset.id)) {
        newSet.delete(preset.id);
        setPreferences((p) =>
          p
            .replace(preset.value + ', ', '')
            .replace(', ' + preset.value, '')
            .replace(preset.value, '')
            .trim()
        );
      } else {
        newSet.add(preset.id);
        setPreferences((p) => (p ? p + ', ' + preset.value : preset.value));
      }
      return newSet;
    });
  }, []);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();

      if (selectedMarkets.length === 0) {
        alert('Please select at least one supermarket');
        return;
      }

      const budgetNum = parseFloat(budget);
      if (!budget || isNaN(budgetNum) || budgetNum <= 0) {
        alert('Please enter a valid budget');
        return;
      }

      const data: UserInput = {
        supermarkets: selectedMarkets,
        budget: budgetNum,
        preferences: preferences.trim(),
        family_size: familySize,
      };

      onSubmit(data);
    },
    [selectedMarkets, budget, preferences, familySize, onSubmit]
  );

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl shadow-lg mb-4">
          <span className="text-4xl">🛒</span>
        </div>
        <h1 className="text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
          ShopSmart AI
        </h1>
        <p className="text-gray-600 mt-2">
          Your intelligent shopping assistant powered by GPT-4
        </p>
      </div>

      {/* Main Form Card */}
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100"
      >
        <div className="space-y-6">
          {/* Supermarkets Selection */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              🏪 Select Supermarkets
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {SUPERMARKETS.map((market) => (
                <button
                  key={market.id}
                  type="button"
                  onClick={() => handleMarketToggle(market.name)}
                  className={`flex items-center justify-center p-4 border-2 rounded-xl transition-all duration-200 ${
                    selectedMarkets.includes(market.name)
                      ? 'border-indigo-500 bg-indigo-50 shadow-md scale-105'
                      : 'border-gray-200 bg-white hover:border-indigo-300 hover:shadow'
                  }`}
                >
                  <span className="mr-2 text-xl">{market.icon}</span>
                  <span
                    className={`font-semibold ${
                      selectedMarkets.includes(market.name)
                        ? 'text-indigo-700'
                        : 'text-gray-700'
                    }`}
                  >
                    {market.name}
                  </span>
                  {selectedMarkets.includes(market.name) && (
                    <span className="ml-2 text-indigo-500">✓</span>
                  )}
                </button>
              ))}
            </div>
            {selectedMarkets.length > 0 && (
              <p className="mt-2 text-sm text-indigo-600">
                {selectedMarkets.length} supermarket(s) selected
              </p>
            )}
          </div>

          {/* Budget and Family Size Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Budget Input */}
            <div>
              <label
                htmlFor="budget"
                className="block text-sm font-semibold text-gray-700 mb-2"
              >
                💰 Weekly Budget (€)
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 text-lg">
                  €
                </span>
                <input
                  id="budget"
                  type="number"
                  min="10"
                  max="1000"
                  step="5"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  placeholder="50"
                  className="w-full pl-10 pr-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-lg"
                  required
                />
              </div>
              <div className="flex gap-2 mt-2 flex-wrap">
                {BUDGET_PRESETS.map((amount) => (
                  <button
                    key={amount}
                    type="button"
                    onClick={() => setBudget(amount.toString())}
                    className={`px-3 py-1 text-sm rounded-lg transition-all ${
                      budget === amount.toString()
                        ? 'bg-indigo-600 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    €{amount}
                  </button>
                ))}
              </div>
            </div>

            {/* Family Size */}
            <div>
              <label
                htmlFor="familySize"
                className="block text-sm font-semibold text-gray-700 mb-2"
              >
                👨‍👩‍👧‍👦 Family Size
              </label>
              <select
                id="familySize"
                value={familySize}
                onChange={(e) => setFamilySize(parseInt(e.target.value))}
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-lg"
              >
                {FAMILY_SIZE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Quick Preference Buttons */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              ⚡ Quick Preferences
            </label>
            <div className="flex flex-wrap gap-2">
              {PREFERENCE_PRESETS.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => handlePresetToggle(preset)}
                  className={`px-3 py-2 text-sm rounded-lg border-2 transition-all ${
                    activePresets.has(preset.id)
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-indigo-300'
                  }`}
                >
                  <span className="mr-1">{preset.icon}</span>
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Preferences Input */}
          <div>
            <label
              htmlFor="preferences"
              className="block text-sm font-semibold text-gray-700 mb-2"
            >
              📝 Additional Preferences (Optional)
            </label>
            <textarea
              id="preferences"
              value={preferences}
              onChange={(e) => setPreferences(e.target.value)}
              placeholder="e.g., prefer organic vegetables, need ingredients for pasta dishes, allergic to nuts..."
              rows={3}
              className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all resize-none"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className={`w-full py-4 px-6 rounded-xl font-bold text-lg transition-all duration-200 ${
              loading
                ? 'bg-gray-300 cursor-not-allowed text-gray-500'
                : 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
            }`}
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Generating...
              </span>
            ) : (
              <span className="flex items-center justify-center">
                <span className="mr-2">✨</span>
                Generate Smart Shopping List
              </span>
            )}
          </button>
        </div>
      </form>

      {/* Features */}
      <div className="mt-8 grid grid-cols-3 gap-4 text-center">
        <div className="p-4 bg-white rounded-xl shadow-sm">
          <span className="text-2xl">🎯</span>
          <p className="text-sm font-medium text-gray-700 mt-2">Budget Optimized</p>
        </div>
        <div className="p-4 bg-white rounded-xl shadow-sm">
          <span className="text-2xl">🤖</span>
          <p className="text-sm font-medium text-gray-700 mt-2">AI Powered</p>
        </div>
        <div className="p-4 bg-white rounded-xl shadow-sm">
          <span className="text-2xl">🏪</span>
          <p className="text-sm font-medium text-gray-700 mt-2">Multi-Store</p>
        </div>
      </div>
    </div>
  );
};

export default ShopForm;
