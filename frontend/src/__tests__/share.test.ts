import { compressToEncodedURIComponent } from 'lz-string';
import { describe, expect, it } from 'vitest';
import type { CompareList } from '../compareList';
import {
  LIST_HASH_PREFIX,
  MAX_SHARE_URL_LENGTH,
  SHARE_HASH_PREFIX,
  buildListShareLink,
  buildShareLink,
  encodeList,
  encodePlan,
  parseShareHash,
} from '../share';
import { MENU, SHOPPING } from '../test/fixtures';
import type { GenerateResponse } from '../types';

const BASE = 'https://shopsmart.example/';

// Text lz-string can't compress much, to push a plan over the URL limit.
const noise = (length: number) =>
  Array.from({ length }, (_, i) => String.fromCharCode(0x4e00 + ((i * 7919) % 20000))).join('');

describe('share link', () => {
  it.each([
    ['shopping', SHOPPING],
    ['menu', MENU],
  ])('round-trips a %s plan through the URL hash', (_, plan) => {
    const link = buildShareLink(plan, BASE);
    if (!link.ok) throw new Error('expected a link');

    expect(link.url.startsWith(`${BASE}${SHARE_HASH_PREFIX}`)).toBe(true);
    const hash = link.url.slice(BASE.length);
    expect(parseShareHash(hash)).toEqual({ kind: 'plan', plan });
  });

  it('refuses plans whose URL would exceed the limit', () => {
    const big: GenerateResponse = { ...MENU, notes: noise(MAX_SHARE_URL_LENGTH) };

    expect(buildShareLink(big, BASE)).toEqual({ ok: false, reason: 'too_large' });
  });

  it('ignores hashes that are not share links', () => {
    expect(parseShareHash('')).toEqual({ kind: 'none' });
    expect(parseShareHash('#top')).toEqual({ kind: 'none' });
  });

  it.each([
    ['garbage', `${SHARE_HASH_PREFIX}%%%not-lz%%%`],
    ['empty data', SHARE_HASH_PREFIX],
    ['non-JSON', SHARE_HASH_PREFIX + compressToEncodedURIComponent('not json')],
    [
      'an unknown version',
      SHARE_HASH_PREFIX + compressToEncodedURIComponent(JSON.stringify({ v: 3, plan: SHOPPING })),
    ],
    [
      'a plan of the wrong shape',
      SHARE_HASH_PREFIX +
        compressToEncodedURIComponent(JSON.stringify({ v: 2, plan: { items: 'x' } })),
    ],
    ['a truncated link', `${SHARE_HASH_PREFIX}${encodePlan(SHOPPING).slice(0, 40)}`],
  ])('reports %s as invalid', (_, hash) => {
    expect(parseShareHash(hash)).toEqual({ kind: 'invalid' });
  });
});

const LIST: CompareList = {
  items: [
    { concept_id: 'yogurt_natural', quantity: 2 },
    { concept_id: 'toilet_paper_10_rolls', quantity: 1 },
  ],
  stores: ['Billa', 'Hofer'],
  diet_tags: ['vegetarian'],
  min_split_savings_eur: 2.5,
  country: 'AT',
};

const listHash = (payload: unknown) =>
  LIST_HASH_PREFIX + compressToEncodedURIComponent(JSON.stringify(payload));

describe('list share link', () => {
  it('round-trips a compare list, and a list of 50 items fits', () => {
    const link = buildListShareLink(LIST, BASE);
    if (!link.ok) throw new Error('expected a link');

    expect(link.url.startsWith(`${BASE}${LIST_HASH_PREFIX}`)).toBe(true);
    expect(parseShareHash(link.url.slice(BASE.length))).toEqual({ kind: 'list', list: LIST });

    const items = Array.from({ length: 50 }, (_, i) => ({
      concept_id: `some_long_concept_name_${i}`,
      quantity: 50,
    }));
    expect(buildListShareLink({ ...LIST, items }, BASE).ok).toBe(true);
  });

  it.each([
    ['an unknown version', listHash({ v: 2, list: LIST })],
    [
      'a quantity over 50',
      listHash({ v: 1, list: { ...LIST, items: [{ concept_id: 'eggs', quantity: 51 }] } }),
    ],
    [
      'a repeated item',
      listHash({ v: 1, list: { ...LIST, items: [LIST.items[0], LIST.items[0]] } }),
    ],
    ['an unknown diet', listHash({ v: 1, list: { ...LIST, diet_tags: ['keto'] } })],
    [
      'a bad concept id',
      listHash({ v: 1, list: { ...LIST, items: [{ concept_id: 'Eggs 10', quantity: 1 }] } }),
    ],
    ['a truncated link', `${LIST_HASH_PREFIX}${encodeList(LIST).slice(0, 20)}`],
  ])('reports %s as invalid', (_, hash) => {
    expect(parseShareHash(hash)).toEqual({ kind: 'invalid' });
  });
});
