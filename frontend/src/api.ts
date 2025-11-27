/**
 * ShopSmart AI - API Service
 * Author: Ivan Sytnyk (КН-М524)
 */

import type { UserInput, AIResponse, ApiError } from './types';
import { API_BASE_URL, API_TIMEOUT } from './constants';

class ApiService {
  private baseUrl: string;
  private timeout: number;

  constructor(baseUrl: string = API_BASE_URL, timeout: number = API_TIMEOUT) {
    this.baseUrl = baseUrl;
    this.timeout = timeout;
  }

  private async fetchWithTimeout(
    url: string,
    options: RequestInit
  ): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout. Please try again.');
      }
      throw error;
    }
  }

  async generateShoppingList(data: UserInput): Promise<AIResponse> {
    const url = `${this.baseUrl}/generate`;
    
    try {
      const response = await this.fetchWithTimeout(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          supermarkets: data.supermarkets,
          budget: data.budget,
          preferences: data.preferences || null,
          family_size: data.family_size,
        }),
      });

      if (!response.ok) {
        const errorData: ApiError = await response.json().catch(() => ({
          error: 'Request failed',
          detail: `HTTP ${response.status}: ${response.statusText}`,
          timestamp: new Date().toISOString(),
        }));
        throw new Error(errorData.detail || 'Failed to generate shopping list');
      }

      const result: AIResponse = await response.json();
      return result;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('An unexpected error occurred');
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.fetchWithTimeout(`${this.baseUrl}/health`, {
        method: 'GET',
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  async getSupermarkets(): Promise<any[]> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}/api/supermarkets`, {
      method: 'GET',
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch supermarkets');
    }
    
    const data = await response.json();
    return data.supermarkets;
  }

  async getCategories(): Promise<any[]> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}/api/categories`, {
      method: 'GET',
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch categories');
    }
    
    const data = await response.json();
    return data.categories;
  }
}

// Export singleton instance
export const apiService = new ApiService();

// Export class for custom instances
export { ApiService };
