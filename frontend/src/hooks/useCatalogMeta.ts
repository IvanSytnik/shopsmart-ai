import { useCallback, useEffect, useState } from 'react';
import { getCatalogMeta } from '../api';
import type { CatalogMeta } from '../types';

export type CatalogMetaState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; meta: CatalogMeta };

/** Stores, diets and price date from GET /api/catalog/meta, with a `reload` for retries. */
export function useCatalogMeta(): CatalogMetaState & { reload: () => void } {
  const [state, setState] = useState<CatalogMetaState>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setState({ status: 'loading' });
    getCatalogMeta()
      .then(meta => {
        if (active) setState({ status: 'ready', meta });
      })
      .catch(() => {
        if (active) setState({ status: 'error' });
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  const reload = useCallback(() => setAttempt(n => n + 1), []);
  return { ...state, reload };
}
