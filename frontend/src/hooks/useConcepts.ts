import { useCallback, useEffect, useState } from 'react';
import { fetchCatalogConcepts } from '../api';
import type { ConceptSummary, Country } from '../types';

export type ConceptsState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; concepts: ConceptSummary[] };

/**
 * What can go on a compare list in `country`, from GET /api/catalog/concepts, with a
 * `reload` for retries. Waits (loading) while `country` is undefined.
 */
export function useConcepts(country: Country | undefined): ConceptsState & { reload: () => void } {
  const [state, setState] = useState<ConceptsState>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (country === undefined) return;
    let active = true;
    setState({ status: 'loading' });
    fetchCatalogConcepts(country)
      .then(response => {
        if (active) setState({ status: 'ready', concepts: response.concepts });
      })
      .catch(() => {
        if (active) setState({ status: 'error' });
      });
    return () => {
      active = false;
    };
  }, [country, attempt]);

  const reload = useCallback(() => setAttempt(n => n + 1), []);
  return { ...state, reload };
}
