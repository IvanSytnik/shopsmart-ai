import { compressToEncodedURIComponent, decompressFromEncodedURIComponent } from 'lz-string';
import { CompareList, parseCompareList } from './compareList';
import { isGenerateResponse } from './history';
import type { GenerateResponse } from './types';

// The whole plan lives in the URL fragment, so nothing is stored on the server and the
// fragment never reaches it. Bump the version when GenerateResponse changes shape.
export const SHARE_VERSION = 2;
export const SHARE_HASH_PREFIX = '#/plan/';
// A compare list: the items, stores and options, not prices, so it opens with today's prices.
export const LIST_SHARE_VERSION = 1;
export const LIST_HASH_PREFIX = '#/list/';
// Links longer than this break in some browsers, chat apps and mail clients.
export const MAX_SHARE_URL_LENGTH = 8000;

interface SharePayload {
  v: number;
  plan: GenerateResponse;
}

export type ShareLink = { ok: true; url: string } | { ok: false; reason: 'too_large' };

interface ListSharePayload {
  v: number;
  list: CompareList;
}

// none: not a share link; invalid: a share link we can't read (corrupt or other version).
export type SharedPlan =
  | { kind: 'none' }
  | { kind: 'plan'; plan: GenerateResponse }
  | { kind: 'list'; list: CompareList }
  | { kind: 'invalid' };

export function encodePlan(plan: GenerateResponse): string {
  const payload: SharePayload = { v: SHARE_VERSION, plan };
  return compressToEncodedURIComponent(JSON.stringify(payload));
}

export function encodeList(list: CompareList): string {
  const payload: ListSharePayload = { v: LIST_SHARE_VERSION, list };
  return compressToEncodedURIComponent(JSON.stringify(payload));
}

const currentPage = () => window.location.origin + window.location.pathname;

const linkOrTooLarge = (url: string): ShareLink =>
  url.length > MAX_SHARE_URL_LENGTH ? { ok: false, reason: 'too_large' } : { ok: true, url };

/** A link to `plan` on the current page, or `too_large` above MAX_SHARE_URL_LENGTH. */
export function buildShareLink(plan: GenerateResponse, base: string = currentPage()): ShareLink {
  return linkOrTooLarge(`${base}${SHARE_HASH_PREFIX}${encodePlan(plan)}`);
}

/** A link to a compare list on the current page (50 items fit easily). */
export function buildListShareLink(list: CompareList, base: string = currentPage()): ShareLink {
  return linkOrTooLarge(`${base}${LIST_HASH_PREFIX}${encodeList(list)}`);
}

const readPayload = (data: string): unknown => {
  const json = decompressFromEncodedURIComponent(data);
  return json ? JSON.parse(json) : null;
};

/** Reads a plan or a compare list from a location hash such as `#/plan/<data>`. */
export function parseShareHash(hash: string): SharedPlan {
  if (hash.startsWith(LIST_HASH_PREFIX)) {
    try {
      const payload = readPayload(hash.slice(LIST_HASH_PREFIX.length));
      if (
        typeof payload === 'object' &&
        payload !== null &&
        'v' in payload &&
        payload.v === LIST_SHARE_VERSION &&
        'list' in payload
      ) {
        const list = parseCompareList(payload.list);
        if (list) return { kind: 'list', list };
      }
    } catch {
      // corrupt data: fall through
    }
    return { kind: 'invalid' };
  }
  if (!hash.startsWith(SHARE_HASH_PREFIX)) return { kind: 'none' };
  try {
    const payload = readPayload(hash.slice(SHARE_HASH_PREFIX.length));
    if (
      typeof payload === 'object' &&
      payload !== null &&
      'v' in payload &&
      payload.v === SHARE_VERSION &&
      'plan' in payload &&
      isGenerateResponse(payload.plan)
    ) {
      return { kind: 'plan', plan: payload.plan };
    }
  } catch {
    // corrupt data: fall through
  }
  return { kind: 'invalid' };
}
