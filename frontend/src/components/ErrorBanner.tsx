/**
 * ShopSmart AI - Error Banner Component
 * Author: Ivan Sytnyk (КН-М524)
 */

import React from 'react';
import type { ErrorBannerProps } from '../types';

const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss }) => {
  return (
    <div className="max-w-2xl mx-auto mb-6 p-4 bg-red-50 border-l-4 border-red-500 rounded-xl shadow-sm animate-slide-in">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <span className="text-2xl">⚠️</span>
        </div>
        <div className="ml-3 flex-1">
          <h3 className="font-bold text-red-800">Error</h3>
          <p className="text-red-700 mt-1">{message}</p>
          <div className="mt-3 flex gap-3">
            <button
              onClick={onDismiss}
              className="text-sm text-red-600 hover:text-red-800 underline font-medium"
            >
              Dismiss
            </button>
            <button
              onClick={() => window.location.reload()}
              className="text-sm text-red-600 hover:text-red-800 underline font-medium"
            >
              Refresh Page
            </button>
          </div>
        </div>
        <button
          onClick={onDismiss}
          className="flex-shrink-0 ml-4 text-red-400 hover:text-red-600 transition-colors"
          aria-label="Close"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default ErrorBanner;
