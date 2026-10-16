import type { GenerateResponse } from './types';

export const HISTORY_KEY = 'shopsmart-history-v2';
// v1 lists have a different response shape (free-text products, model-made prices) and
// can't be shown any more.
const V1_HISTORY_KEY = 'shopsmart-history';
const MAX_ENTRIES = 10;

export interface SavedPlan {
  id: string;
  savedAt: string; // ISO 8601
  response: GenerateResponse;
}

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

// A light shape check: enough to render a stored or shared plan without crashing.
export const isGenerateResponse = (response: unknown): response is GenerateResponse =>
  isObject(response) &&
  Array.isArray(response.items) &&
  Array.isArray(response.trimmed) &&
  Array.isArray(response.warnings) &&
  isObject(response.subtotals_by_store) &&
  typeof response.total === 'number' &&
  typeof response.budget === 'number' &&
  (response.menu === null || Array.isArray(response.menu));

const isSavedPlan = (value: unknown): value is SavedPlan =>
  isObject(value) &&
  typeof value.id === 'string' &&
  typeof value.savedAt === 'string' &&
  isGenerateResponse(value.response);

// Storage can throw (private mode, quota, disabled); history is a convenience, so ignore it.
function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string | null): void {
  try {
    if (value === null) {
      localStorage.removeItem(key);
    } else {
      localStorage.setItem(key, value);
    }
  } catch {
    // ignored, see readStorage
  }
}

export function loadHistory(): SavedPlan[] {
  if (readStorage(V1_HISTORY_KEY) !== null) {
    writeStorage(V1_HISTORY_KEY, null);
  }
  const raw = readStorage(HISTORY_KEY);
  if (raw === null) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isSavedPlan) : [];
  } catch {
    return [];
  }
}

function storeHistory(plans: SavedPlan[]): void {
  writeStorage(HISTORY_KEY, plans.length ? JSON.stringify(plans) : null);
}

export function saveToHistory(response: GenerateResponse): void {
  const plan: SavedPlan = {
    id: Date.now().toString(),
    savedAt: new Date().toISOString(),
    response,
  };
  storeHistory([plan, ...loadHistory()].slice(0, MAX_ENTRIES));
}

export function deleteFromHistory(id: string): SavedPlan[] {
  const plans = loadHistory().filter(p => p.id !== id);
  storeHistory(plans);
  return plans;
}

export function clearHistory(): void {
  storeHistory([]);
}
