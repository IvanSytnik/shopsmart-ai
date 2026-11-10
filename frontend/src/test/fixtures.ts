import { vi } from 'vitest';
import type {
  CatalogMeta,
  CompareResponse,
  ConceptSummary,
  ConceptsResponse,
  GenerateResponse,
  Item,
  LocalizedNames,
  MatchedStoreItem,
} from '../types';

export const META: CatalogMeta = {
  catalog_version: 'test',
  price_date: '2026-10-01',
  countries: { AT: ['Lidl', 'Penny'], DE: ['Lidl', 'Rewe'] },
  diet_tags: ['vegetarian', 'vegan', 'gluten_free', 'lactose_free'],
  categories: ['dairy', 'fruits', 'pantry', 'snacks'],
};

const item = (overrides: Partial<Item> & Pick<Item, 'product_id' | 'name'>): Item => ({
  names: { en: overrides.name, uk: overrides.name, de: overrides.name },
  store: 'Lidl',
  category: 'dairy',
  packs: 1,
  pack_size: 1,
  unit: 'l',
  portion_unit: 'ml',
  unit_price: 1,
  line_total: 1,
  nutrition: { kcal: 100, protein_g: 1, fat_g: 1, carbs_g: 1 },
  ...overrides,
});

export const SHOPPING: GenerateResponse = {
  items: [
    item({
      product_id: 'at-lidl-milk-1l',
      name: 'Whole milk 3.5%',
      names: { en: 'Whole milk 3.5%', uk: 'Молоко 3,5%', de: 'Vollmilch 3,5%' },
      packs: 2,
      unit_price: 1.29,
      line_total: 2.58,
    }),
    item({
      product_id: 'at-lidl-apples-1kg',
      name: 'Apples',
      names: { en: 'Apples', uk: 'Яблука', de: 'Äpfel' },
      category: 'fruits',
      packs: 2,
      unit: 'kg',
      portion_unit: 'g',
      unit_price: 1.99,
      line_total: 3.98,
    }),
    item({
      product_id: 'at-penny-rice-1kg',
      name: 'Rice',
      store: 'Penny',
      category: 'pantry',
      unit: 'kg',
      portion_unit: 'g',
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
  kcal_basis: 'purchased',
  trimmed: [],
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
  kcal_basis: 'menu',
  trimmed: [
    {
      product_id: 'at-lidl-potato-chips-175g',
      name: 'Potato chips',
      names: { en: 'Potato chips', uk: 'Картопляні чипси', de: 'Kartoffelchips' },
      from_packs: 2,
      to_packs: 0,
    },
    {
      product_id: 'at-lidl-apples-1kg',
      name: 'Apples',
      names: { en: 'Apples', uk: 'Яблука', de: 'Äpfel' },
      from_packs: 3,
      to_packs: 2,
    },
  ],
  warnings: ['low_kcal', 'budget_trimmed'],
  menu: [
    {
      day: 'Monday',
      breakfast: {
        name: 'Porridge',
        description: 'Warm',
        ingredients: [
          { product_id: 'at-lidl-milk-1l', amount_per_person: 200 },
          { product_id: 'at-penny-rice-1kg', amount_per_person: 80 },
        ],
      },
      lunch: {
        name: 'Rice bowl',
        description: 'Filling',
        ingredients: [{ product_id: 'at-penny-rice-1kg', amount_per_person: 100 }],
      },
      dinner: {
        name: 'Baked apples',
        description: 'Sweet',
        ingredients: [{ product_id: 'at-lidl-apples-1kg', amount_per_person: 150 }],
      },
      snack: {
        name: 'Chips',
        description: 'Crunchy',
        ingredients: [{ product_id: 'at-lidl-potato-chips-175g', amount_per_person: 30 }],
      },
    },
  ],
};

const names = (en: string, uk: string, de: string): LocalizedNames => ({ en, uk, de });

const concept = (
  concept_id: string,
  name: LocalizedNames,
  fields: Partial<ConceptSummary> = {}
): ConceptSummary => ({
  concept_id,
  name,
  names: [name],
  category: 'dairy',
  unit: 'kg',
  stores: ['Lidl', 'Penny'],
  reference_pack_size: 1,
  ...fields,
});

// Product names carry brands and variants; concept names don't.
export const CONCEPTS: ConceptsResponse = {
  country: 'AT',
  concepts: [
    concept('bananas', names('Bananas', 'Банани', 'Bananen'), {
      category: 'fruits',
      stores: ['Lidl'],
    }),
    concept('butter', names('Butter', 'Вершкове масло', 'Butter'), {
      names: [
        names('Butter', 'Вершкове масло', 'Clever Teebutter'),
        names('Butter, lactose-free', 'Масло без лактози', 'Butter, laktosefrei'),
      ],
      reference_pack_size: 0.25,
    }),
    concept('eggs', names('Eggs', 'Яйця', 'Eier'), { unit: 'pcs', reference_pack_size: 6 }),
    concept('milk_whole', names('Whole milk', 'Цільне молоко', 'Vollmilch'), {
      names: [names('UHT whole milk 3.5%', 'Молоко 3,5%', 'Clever Haltbar-Vollmilch 3,5%')],
      unit: 'l',
    }),
    concept('rice', names('Rice', 'Рис', 'Reis'), { category: 'pantry' }),
    concept('yogurt_natural', names('Natural yogurt', 'Натуральний йогурт', 'Naturjoghurt'), {
      names: [names('Natural yogurt 3.6%', 'Йогурт 3,6%', 'Clever Joghurt Natur 3,6%')],
      reference_pack_size: 0.25,
    }),
  ],
};

const matched = (
  fields: Pick<MatchedStoreItem, 'concept_id' | 'product_id' | 'names' | 'store' | 'price_eur'> &
    Partial<MatchedStoreItem>
): MatchedStoreItem => {
  const { price_eur, packs_needed = 1, pack_size = 1 } = fields;
  return {
    packs_needed,
    pack_size,
    unit: 'kg',
    regular_price_eur: price_eur,
    promo_price_eur: null,
    promo_valid_until: null,
    line_total_eur: Math.round(price_eur * packs_needed * 100) / 100,
    price_per_base_unit_eur: Math.round((price_eur / pack_size) * 100) / 100,
    ...fields,
  };
};

const YOGURT = names('Natural yogurt 3.6%', 'Йогурт 3,6%', 'Joghurt Natur 3,6%');
const MILK = names('Whole milk 3.5%', 'Молоко 3,5%', 'Vollmilch 3,5%');
const LIDL_YOGURT = matched({
  concept_id: 'yogurt_natural',
  product_id: 'at-lidl-yogurt-250g',
  names: YOGURT,
  store: 'Lidl',
  price_eur: 2,
  packs_needed: 2,
  pack_size: 0.25,
});
const LIDL_MILK = matched({
  concept_id: 'milk_whole',
  product_id: 'at-lidl-milk-1l',
  names: MILK,
  store: 'Lidl',
  price_eur: 1,
  unit: 'l',
});
const LIDL_BANANAS = matched({
  concept_id: 'bananas',
  product_id: 'at-lidl-bananas-1kg',
  names: names('Bananas', 'Банани', 'Bananen'),
  store: 'Lidl',
  price_eur: 1.5,
});
const LIDL_BUTTER = matched({
  concept_id: 'butter',
  product_id: 'at-lidl-butter-250g',
  names: names('Butter', 'Вершкове масло', 'Teebutter'),
  store: 'Lidl',
  price_eur: 1.5,
  pack_size: 0.25,
  regular_price_eur: 2,
  promo_price_eur: 1.5,
  promo_valid_until: '2026-11-08',
});
const PENNY_YOGURT = matched({
  concept_id: 'yogurt_natural',
  product_id: 'at-penny-yogurt-500g',
  names: YOGURT,
  store: 'Penny',
  price_eur: 1,
  pack_size: 0.5,
});
const PENNY_MILK = matched({
  concept_id: 'milk_whole',
  product_id: 'at-penny-milk-1l',
  names: MILK,
  store: 'Penny',
  price_eur: 1.2,
  unit: 'l',
});
const PENNY_BUTTER = matched({
  concept_id: 'butter',
  product_id: 'at-penny-butter-250g',
  names: names('Butter', 'Вершкове масло', 'Butter'),
  store: 'Penny',
  price_eur: 1.8,
  pack_size: 0.25,
});

/**
 * 2 × yogurt, milk, bananas and butter at Lidl (€8.00, butter on promotion) and Penny
 * (€4.00, no bananas). Split: milk, bananas, butter at Lidl (€4.00), yogurt at Penny (€1.00):
 * €3.00 less than Lidl, the best store (Penny lacks bananas), so the split is recommended.
 */
export const COMPARE_SPLIT: CompareResponse = {
  single_store_rankings: [
    {
      store: 'Lidl',
      items: [LIDL_YOGURT, LIDL_MILK, LIDL_BANANAS, LIDL_BUTTER],
      total_eur: 8,
      promo_savings_eur: 0.5,
      missing_concepts: [],
    },
    {
      store: 'Penny',
      items: [PENNY_YOGURT, PENNY_MILK, PENNY_BUTTER],
      total_eur: 4,
      promo_savings_eur: 0,
      missing_concepts: ['bananas'],
    },
  ],
  split_basket: {
    stores: [
      { store: 'Lidl', items: [LIDL_MILK, LIDL_BANANAS, LIDL_BUTTER], total_eur: 4 },
      { store: 'Penny', items: [PENNY_YOGURT], total_eur: 1 },
    ],
    total_eur: 5,
    missing_concepts: [],
    total_savings_vs_worst_eur: 3,
  },
  recommended_strategy: 'split_basket',
  recommended_store: null,
  split_extra_savings_eur: 3,
  catalog_version: 'test',
  price_date: '2026-11-02',
};

// The same prices compared with a €5 threshold: Lidl alone is recommended.
export const COMPARE_SINGLE: CompareResponse = {
  ...COMPARE_SPLIT,
  recommended_strategy: 'single_store',
  recommended_store: 'Lidl',
};

type Reply = { status: number; body: unknown } | Error;

interface MockOptions {
  concepts?: ConceptsResponse | Reply;
  compareReplies?: Reply[];
}

/**
 * Stubs global fetch: GET /api/catalog/meta returns `meta`, GET /api/catalog/concepts
 * `concepts`, POST /generate and POST /compare their queued replies.
 */
export function mockFetch(
  meta: CatalogMeta | Reply = META,
  generateReplies: Reply[] = [],
  { concepts = CONCEPTS, compareReplies = [] }: MockOptions = {}
) {
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
    if (url.includes('/api/catalog/concepts?')) {
      return toResponse('concepts' in concepts ? { status: 200, body: concepts } : concepts);
    }
    if (url.endsWith('/compare')) {
      const reply = compareReplies.shift();
      if (!reply) throw new Error('unexpected /compare call');
      return toResponse(reply);
    }
    throw new Error(`unexpected fetch: ${url}`);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}
