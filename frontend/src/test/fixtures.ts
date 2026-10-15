import { vi } from 'vitest';
import type { CatalogMeta, GenerateResponse, Item } from '../types';

export const META: CatalogMeta = {
  catalog_version: 'test',
  price_date: '2026-10-01',
  countries: { AT: ['Lidl', 'Penny'], DE: ['Lidl', 'Rewe'] },
  diet_tags: ['vegetarian', 'vegan', 'gluten_free', 'lactose_free'],
  categories: ['dairy', 'fruits', 'pantry', 'snacks'],
};

const item = (overrides: Partial<Item> & Pick<Item, 'product_id' | 'name'>): Item => ({
  store: 'Lidl',
  category: 'dairy',
  packs: 1,
  pack_size: 1,
  unit: 'l',
  unit_price: 1,
  line_total: 1,
  nutrition: { kcal: 100, protein_g: 1, fat_g: 1, carbs_g: 1 },
  ...overrides,
});

export const SHOPPING: GenerateResponse = {
  items: [
    item({ product_id: 'at-lidl-milk-1l', name: 'Whole milk 3.5%', packs: 2, unit_price: 1.29, line_total: 2.58 }),
    item({
      product_id: 'at-lidl-apples-1kg',
      name: 'Apples',
      category: 'fruits',
      packs: 2,
      unit: 'kg',
      unit_price: 1.99,
      line_total: 3.98,
    }),
    item({
      product_id: 'at-penny-rice-1kg',
      name: 'Rice',
      store: 'Penny',
      category: 'pantry',
      unit: 'kg',
      unit_price: 2.29,
      line_total: 2.29,
    }),
  ],
  subtotals_by_store: { Lidl: 6.56, Penny: 2.29 },
  total: 8.85,
  budget: 10,
  budget_remaining: 1.15,
  nutrition_totals: { kcal: 5820, protein_g: 144, fat_g: 81, carbs_g: 1156 },
  kcal_per_person_day: 416,
  trimmed: [],
  auto_added: [],
  menu: null,
  notes: 'Buy seasonal.',
  warnings: [],
  catalog_version: 'test',
  price_date: '2026-10-01',
  generated_at: '2026-10-15T10:00:00Z',
};

export const MENU: GenerateResponse = {
  ...SHOPPING,
  kcal_per_person_day: 1455,
  trimmed: [
    { product_id: 'at-lidl-potato-chips-175g', from_packs: 2, to_packs: 0 },
    { product_id: 'at-lidl-apples-1kg', from_packs: 3, to_packs: 2 },
  ],
  warnings: ['low_kcal', 'budget_trimmed'],
  menu: [
    {
      day: 'Monday',
      breakfast: { name: 'Porridge', description: 'Warm', ingredient_ids: ['at-lidl-milk-1l', 'at-penny-rice-1kg'] },
      lunch: { name: 'Rice bowl', description: 'Filling', ingredient_ids: ['at-penny-rice-1kg'] },
      dinner: { name: 'Baked apples', description: 'Sweet', ingredient_ids: ['at-lidl-apples-1kg'] },
      snack: { name: 'Chips', description: 'Crunchy', ingredient_ids: ['at-lidl-potato-chips-175g'] },
    },
  ],
};

type Reply = { status: number; body: unknown } | Error;

/** Stubs global fetch: GET /api/catalog/meta returns `meta`, POST /generate the queued replies. */
export function mockFetch(meta: CatalogMeta | Reply = META, generateReplies: Reply[] = []) {
  const toResponse = (reply: Reply) => {
    if (reply instanceof Error) return Promise.reject(reply);
    return Promise.resolve({
      ok: reply.status >= 200 && reply.status < 300,
      status: reply.status,
      json: () => Promise.resolve(reply.body),
    } as Response);
  };
  const fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/api/catalog/meta')) {
      return toResponse('catalog_version' in meta ? { status: 200, body: meta } : meta);
    }
    if (url.endsWith('/generate')) {
      const reply = generateReplies.shift();
      if (!reply) throw new Error('unexpected /generate call');
      return toResponse(reply);
    }
    throw new Error(`unexpected fetch: ${url}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}
