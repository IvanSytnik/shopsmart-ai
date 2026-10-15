import { describe, expect, it, vi } from 'vitest';
import {
  HISTORY_KEY,
  clearHistory,
  deleteFromHistory,
  loadHistory,
  saveToHistory,
} from '../history';
import { SHOPPING } from '../test/fixtures';

describe('history', () => {
  it('saves and loads v2 plans, newest first, at most 10', () => {
    for (let i = 0; i < 12; i++) {
      vi.spyOn(Date, 'now').mockReturnValue(1000 + i);
      saveToHistory({ ...SHOPPING, total: i });
    }
    const plans = loadHistory();
    expect(plans.map(p => p.response.total)).toEqual([11, 10, 9, 8, 7, 6, 5, 4, 3, 2]);

    expect(deleteFromHistory(plans[0].id)).toHaveLength(9);
    clearHistory();
    expect(localStorage.getItem(HISTORY_KEY)).toBeNull();
  });

  it('drops v1 data and malformed entries', () => {
    localStorage.setItem('shopsmart-history', '[{"itemCount": 1, "totalCost": 1}]');
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify([
        { id: 'ok', savedAt: '2026-10-15T10:00:00Z', response: SHOPPING },
        {
          id: 'v1',
          savedAt: '2026-10-15T10:00:00Z',
          response: { items: [{ product: 'Milk', quantity: '1 l' }] },
        },
        null,
      ])
    );

    expect(loadHistory().map(p => p.id)).toEqual(['ok']);
    expect(localStorage.getItem('shopsmart-history')).toBeNull();
  });

  it('survives invalid JSON and storage that throws', () => {
    localStorage.setItem(HISTORY_KEY, '{not json');
    expect(loadHistory()).toEqual([]);

    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    expect(loadHistory()).toEqual([]);
    expect(() => saveToHistory(SHOPPING)).not.toThrow();
  });
});
