import { compressToEncodedURIComponent } from 'lz-string';
import { describe, expect, it } from 'vitest';
import {
  MAX_SHARE_URL_LENGTH,
  SHARE_HASH_PREFIX,
  buildShareLink,
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
