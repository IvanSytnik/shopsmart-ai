/**
 * ShopSmart AI - Loading Spinner Component
 * Author: Ivan Sytnyk (КН-М524)
 */

import React from 'react';
import type { LoadingSpinnerProps } from '../types';

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'AI is creating your shopping list...',
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      {/* Main Spinner */}
      <div className="relative">
        {/* Outer ring */}
        <div className="w-24 h-24 border-4 border-indigo-100 rounded-full"></div>
        
        {/* Spinning ring */}
        <div className="absolute inset-0 w-24 h-24 border-4 border-transparent border-t-indigo-600 rounded-full animate-spin"></div>
        
        {/* Inner content */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-4xl animate-bounce">🛒</div>
        </div>
      </div>

      {/* Text */}
      <div className="mt-8 text-center">
        <p className="text-xl font-semibold text-gray-800">{message}</p>
        <p className="mt-2 text-gray-500">
          Analyzing prices and optimizing for your budget
        </p>
      </div>

      {/* Loading dots */}
      <div className="mt-6 flex space-x-2">
        <div
          className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce"
          style={{ animationDelay: '0ms' }}
        ></div>
        <div
          className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce"
          style={{ animationDelay: '150ms' }}
        ></div>
        <div
          className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce"
          style={{ animationDelay: '300ms' }}
        ></div>
      </div>

      {/* Tips */}
      <div className="mt-8 max-w-md text-center">
        <div className="bg-indigo-50 rounded-xl p-4">
          <p className="text-sm text-indigo-700">
            <span className="font-semibold">💡 Did you know?</span> ShopSmart AI
            considers current German supermarket prices and distributes items based
            on typical pricing at each store.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoadingSpinner;
