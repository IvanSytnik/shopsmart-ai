import React, { useEffect, useId, useMemo, useState } from 'react';
import { CATEGORY_ICONS } from '../../constants';
import { useLanguage } from '../../LanguageContext';
import type { Category, ConceptSummary } from '../../types';
import { formatSize } from '../results/format';
import { matchConcepts } from './format';

// Display order of the category filter.
const CATEGORIES = Object.keys(CATEGORY_ICONS) as Category[];

interface ConceptSearchProps {
  concepts: ConceptSummary[];
  onList: ReadonlySet<string>; // concept ids already on the list
  full: boolean; // the list can't take another product
  onAdd: (concept: ConceptSummary) => void;
}

/**
 * Autocomplete over the concepts (ARIA 1.2 combobox with a listbox popup) and a category
 * filter. Focus, a click or typing opens the list; arrows move, Enter adds (and closes it),
 * Escape closes.
 */
export const ConceptSearch: React.FC<ConceptSearchProps> = ({ concepts, onList, full, onAdd }) => {
  const { t, language } = useLanguage();
  const id = useId();
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<Category | ''>('');
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [announcement, setAnnouncement] = useState('');

  const categories = useMemo(
    () => CATEGORIES.filter(c => concepts.some(concept => concept.category === c)),
    [concepts]
  );
  const matches = useMemo(
    () => matchConcepts(concepts, query, category, language),
    [concepts, query, category, language]
  );
  const optionId = (concept: ConceptSummary) => `${id}-option-${concept.concept_id}`;
  const activeOption = open ? matches[active] : undefined;
  const activeId = activeOption ? optionId(activeOption) : undefined;

  useEffect(() => {
    if (activeId) document.getElementById(activeId)?.scrollIntoView?.({ block: 'nearest' });
  }, [activeId]);

  // Closes the list: typing, a click on the field or ArrowDown opens it again.
  const choose = (concept: ConceptSummary) => {
    onAdd(concept);
    setAnnouncement(t('compareAdded', { name: concept.name[language] }));
    setQuery('');
    setOpen(false);
    setActive(-1);
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        setOpen(true);
        setActive(i => Math.min(matches.length - 1, i + 1));
        break;
      case 'ArrowUp':
        event.preventDefault();
        setActive(i => Math.max(0, i - 1));
        break;
      case 'Enter': {
        // The highlighted option, or the best match for what was typed.
        const target = activeOption ?? (open && query.trim() ? matches[0] : undefined);
        if (target) {
          event.preventDefault();
          choose(target);
        }
        break;
      }
      case 'Escape':
        if (open) {
          event.preventDefault();
          setOpen(false);
          setActive(-1);
        } else {
          setQuery('');
        }
        break;
    }
  };

  const fieldClass =
    'p-3 border border-gray-200 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50';

  return (
    <div>
      <label
        htmlFor={`${id}-input`}
        className="block text-sm text-gray-600 dark:text-gray-400 mb-2"
      >
        <span aria-hidden="true">🔎</span> {t('compareSearchLabel')}
      </label>
      <div className="flex flex-col sm:flex-row gap-2">
        <div className="relative flex-1">
          <input
            id={`${id}-input`}
            type="text"
            role="combobox"
            aria-expanded={open && matches.length > 0}
            aria-controls={`${id}-listbox`}
            aria-autocomplete="list"
            aria-activedescendant={activeId}
            autoComplete="off"
            value={query}
            placeholder={t('compareSearchPlaceholder')}
            disabled={full}
            onChange={e => {
              setQuery(e.target.value);
              setOpen(true);
              setActive(-1);
            }}
            onFocus={() => setOpen(true)}
            onClick={() => setOpen(true)}
            onBlur={() => {
              setOpen(false);
              setActive(-1);
            }}
            onKeyDown={onKeyDown}
            className={`w-full ${fieldClass}`}
          />
          <ul
            id={`${id}-listbox`}
            role="listbox"
            aria-label={t('compareSearchLabel')}
            hidden={!open || matches.length === 0}
            className="absolute z-20 mt-1 w-full max-h-72 overflow-y-auto rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-xl"
          >
            {matches.map((concept, index) => {
              const selected = index === active;
              return (
                <li
                  key={concept.concept_id}
                  id={optionId(concept)}
                  role="option"
                  aria-selected={selected}
                  // Keep focus in the input, so the click lands before the list closes.
                  onMouseDown={e => e.preventDefault()}
                  onClick={() => choose(concept)}
                  onMouseMove={() => setActive(index)}
                  className={`flex items-center gap-3 px-3 py-2 cursor-pointer ${
                    selected
                      ? 'bg-primary-100 ring-2 ring-inset ring-primary-600 dark:bg-primary-900 dark:ring-primary-400'
                      : ''
                  }`}
                >
                  <span className="text-xl" aria-hidden="true">
                    {CATEGORY_ICONS[concept.category]}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span
                      className={`block font-medium ${
                        selected
                          ? 'text-primary-900 dark:text-white'
                          : 'text-gray-800 dark:text-gray-200'
                      }`}
                    >
                      {concept.name[language]}
                    </span>
                    <span
                      className={`block text-xs ${
                        selected
                          ? 'text-primary-800 dark:text-primary-100'
                          : 'text-gray-500 dark:text-gray-400'
                      }`}
                    >
                      {formatSize(concept.reference_pack_size, concept.unit, language, t)} ·{' '}
                      {concept.stores.join(', ')}
                      {onList.has(concept.concept_id) && ` · ✓ ${t('compareInList')}`}
                    </span>
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
        <label htmlFor={`${id}-category`} className="sr-only">
          {t('compareCategory')}
        </label>
        <select
          id={`${id}-category`}
          value={category}
          onChange={e => {
            setCategory(e.target.value as Category | '');
            setActive(-1);
          }}
          className={`sm:w-48 ${fieldClass}`}
        >
          <option value="">{t('compareAllCategories')}</option>
          {categories.map(c => (
            <option key={c} value={c}>
              {CATEGORY_ICONS[c]} {t(c)}
            </option>
          ))}
        </select>
      </div>
      {open && matches.length === 0 && (
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{t('compareNoMatches')}</p>
      )}
      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>
    </div>
  );
};
