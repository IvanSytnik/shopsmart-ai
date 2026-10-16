import { compressToEncodedURIComponent, decompressFromEncodedURIComponent } from 'lz-string';
import { isGenerateResponse } from './history';
import type { GenerateResponse } from './types';

// The whole plan lives in the URL fragment, so nothing is stored on the server and the
// fragment never reaches it. Bump the version when GenerateResponse changes shape.
export const SHARE_VERSION = 2;
export const SHARE_HASH_PREFIX = '#/plan/';
// Links longer than this break in some browsers, chat apps and mail clients.
export const MAX_SHARE_URL_LENGTH = 8000;

interface SharePayload {
  v: number;
  plan: GenerateResponse;
}

export type ShareLink = { ok: true; url: string } | { ok: false; reason: 'too_large' };

// none: not a share link; invalid: a share link we can't read (corrupt or other version).
export type SharedPlan =
  | { kind: 'none' }
  | { kind: 'plan'; plan: GenerateResponse }
  | { kind: 'invalid' };

export function encodePlan(plan: GenerateResponse): string {
  const payload: SharePayload = { v: SHARE_VERSION, plan };
  return compressToEncodedURIComponent(JSON.stringify(payload));
}

/** A link to `plan` on the current page, or `too_large` above MAX_SHARE_URL_LENGTH. */
export function buildShareLink(
  plan: GenerateResponse,
  base: string = window.location.origin + window.location.pathname
): ShareLink {
  const url = `${base}${SHARE_HASH_PREFIX}${encodePlan(plan)}`;
  return url.length > MAX_SHARE_URL_LENGTH ? { ok: false, reason: 'too_large' } : { ok: true, url };
}

/** Reads a plan from a location hash such as `#/plan/<data>`. */
export function parseShareHash(hash: string): SharedPlan {
  if (!hash.startsWith(SHARE_HASH_PREFIX)) return { kind: 'none' };
  try {
    const json = decompressFromEncodedURIComponent(hash.slice(SHARE_HASH_PREFIX.length));
    if (!json) return { kind: 'invalid' };
    const payload: unknown = JSON.parse(json);
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
