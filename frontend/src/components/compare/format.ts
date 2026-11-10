import { UNIT_KEYS } from '../../constants';
import type { Language } from '../../translations';
import type { Category, ConceptSummary, MatchedStoreItem, Unit } from '../../types';
import { Translate, formatSize, money } from '../results/format';

/** Lowercase without accents, so "apfel" finds "Äpfel" and "йогурт" finds "Йогурт". */
export const searchable = (text: string): string =>
  text
    .toLocaleLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

// Lower is better: the name starts with the query, a word of it does, it contains it, or
// only another language or one of the products' names (with brands) matches.
function matchRank(concept: ConceptSummary, query: string, language: Language): number | null {
  const name = searchable(concept.name[language]);
  if (name.startsWith(query)) return 0;
  if (name.split(/[\s,-]+/).some(word => word.startsWith(query))) return 1;
  if (name.includes(query)) return 2;
  const others = [concept.name, ...concept.names].flatMap(names => Object.values(names));
  return others.some(other => searchable(other).includes(query)) ? 3 : null;
}

/**
 * Concepts in `category` (all for '') that match `query`, best matches first, then by name
 * in the UI language. An empty query matches everything.
 */
export function matchConcepts(
  concepts: ConceptSummary[],
  query: string,
  category: Category | '',
  language: Language
): ConceptSummary[] {
  const wanted = searchable(query.trim());
  const collator = new Intl.Collator(language);
  return concepts
    .filter(concept => category === '' || concept.category === category)
    .map(concept => ({ concept, rank: wanted ? matchRank(concept, wanted, language) : 0 }))
    .filter((match): match is { concept: ConceptSummary; rank: number } => match.rank !== null)
    .sort(
      (a, b) =>
        a.rank - b.rank || collator.compare(a.concept.name[language], b.concept.name[language])
    )
    .map(match => match.concept);
}

/** "2 × 250 g (500 g)": `quantity` packs of `packSize`, and what they hold together. */
export const formatVolume = (
  quantity: number,
  packSize: number,
  unit: Unit,
  language: Language,
  t: Translate
): string => {
  const pack = `${quantity} × ${formatSize(packSize, unit, language, t)}`;
  return quantity === 1 ? pack : `${pack} (${formatSize(quantity * packSize, unit, language, t)})`;
};

/** "€2.40/kg": the price per 1 kg, 1 l, 1 piece or 1 pack. */
export const formatPerUnit = (item: MatchedStoreItem, t: Translate): string =>
  t('comparePerUnit', {
    price: money(item.price_per_base_unit_eur),
    unit: t(UNIT_KEYS[item.unit]),
  });

/** A concept's name in the UI language; its id for one the catalog doesn't (or no longer) has. */
export const conceptName = (
  conceptsById: ReadonlyMap<string, ConceptSummary>,
  conceptId: string,
  language: Language
): string => conceptsById.get(conceptId)?.name[language] ?? conceptId.replace(/_/g, ' ');
