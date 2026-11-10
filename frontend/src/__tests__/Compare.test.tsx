import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { CompareView } from '../components';
import { COMPARE_LIST_KEY } from '../compareList';
import { parseShareHash } from '../share';
import { COMPARE_SINGLE, COMPARE_SPLIT, META, mockFetch } from '../test/fixtures';
import { renderWithLanguage } from '../test/render';
import { translations, type Language } from '../translations';
import type { CompareResponse } from '../types';

type Reply = { status: number; body: unknown };

async function renderCompare(compareReplies: Reply[] = [], language: Language = 'en') {
  const fetchMock = mockFetch(META, [], { compareReplies });
  const user = userEvent.setup();
  const view = renderWithLanguage(
    <CompareView onModeChange={vi.fn()} sharedList={null} />,
    language
  );
  await screen.findByRole('combobox', { name: SEARCH_LABEL });
  return { user, fetchMock, view };
}

// The search field in any UI language (a <select> is a combobox too).
const SEARCH_LABEL = new RegExp(
  Object.values(translations)
    .map(t => t.compareSearchLabel)
    .join('|')
);
const search = () => screen.getByRole('combobox', { name: SEARCH_LABEL });
const optionNames = () =>
  within(screen.getByRole('listbox'))
    .getAllByRole('option')
    .map(o => o.textContent ?? '');
const listRows = () =>
  Array.from(document.querySelectorAll('ul[aria-labelledby] > li')).map(li => li.textContent);

async function add(user: ReturnType<typeof userEvent.setup>, query: string, option: RegExp) {
  await user.clear(search());
  await user.type(search(), query);
  await user.click(screen.getByRole('option', { name: option }));
}

/** Adds 2 × yogurt, milk, bananas and butter: the list COMPARE_SPLIT answers. */
async function buildList(user: ReturnType<typeof userEvent.setup>) {
  await add(user, 'yog', /^Natural yogurt/);
  await user.click(screen.getByRole('button', { name: 'More: Natural yogurt' }));
  await add(user, 'milk', /^Whole milk/);
  await add(user, 'banan', /^Bananas/);
  await add(user, 'butter', /^Butter/);
}

async function compareWith(response: CompareResponse) {
  const result = await renderCompare([{ status: 200, body: response }]);
  await buildList(result.user);
  await result.user.click(screen.getByRole('button', { name: /Compare prices/ }));
  await screen.findByTestId('compare-recommendation');
  return result;
}

describe('compare list builder', () => {
  it('finds products by their clean name, other languages and product names', async () => {
    const { user } = await renderCompare();

    await user.type(search(), 'yog');
    expect(optionNames()[0]).toBe('🥛Natural yogurt250 g · Lidl, Penny');

    await user.clear(search());
    await user.type(search(), 'Teebutter'); // a brand-name product of the butter concept
    expect(optionNames()).toEqual(['🥛Butter250 g · Lidl, Penny']);

    await user.clear(search());
    await user.type(search(), 'vollmilch'); // German, while the UI is English
    expect(optionNames()).toEqual(['🥛Whole milk1 l · Lidl, Penny']);
  });

  it('adds with the keyboard and announces it', async () => {
    const { user } = await renderCompare();

    await user.type(search(), 'milk');
    await user.keyboard('{ArrowDown}');
    expect(search().getAttribute('aria-activedescendant')).toBe(
      screen.getByRole('option', { name: /^Whole milk/ }).id
    );
    await user.keyboard('{Enter}');

    expect(listRows()).toEqual(['🥛Whole milk1 × 1 l−+✕']);
    expect(search()).toHaveProperty('value', '');
    expect(screen.getByText('Added: Whole milk')).toBeTruthy();
    // The suggestions close after adding, until the next keystroke.
    expect(screen.getByRole('listbox', { hidden: true }).hidden).toBe(true);
    expect(search().getAttribute('aria-expanded')).toBe('false');
    expect(search().getAttribute('aria-activedescendant')).toBeNull();
    await user.keyboard('ban');
    expect(optionNames()).toEqual(['🍎Bananas1 kg · Lidl']);
    await user.keyboard('{Escape}');
    expect(screen.getByRole('listbox', { hidden: true }).hidden).toBe(true);
  });

  it('closes the suggestions after a click on one, and a click on the field opens them', async () => {
    const { user } = await renderCompare();

    await add(user, 'yog', /^Natural yogurt/);

    expect(search()).toBe(document.activeElement);
    expect(screen.getByRole('listbox', { hidden: true }).hidden).toBe(true);
    expect(screen.queryByText('No products match.')).toBeNull();
    await user.click(search());
    expect(search().getAttribute('aria-expanded')).toBe('true');
    expect(optionNames().length).toBeGreaterThan(1); // the whole catalog, nothing typed
  });

  it('filters by category', async () => {
    const { user } = await renderCompare();

    await user.selectOptions(screen.getByLabelText('Category'), 'fruits');
    await user.click(search());

    expect(optionNames()).toEqual(['🍎Bananas1 kg · Lidl']);
    expect(
      within(screen.getByLabelText('Category'))
        .getAllByRole('option')
        .map(o => o.textContent)
    ).toEqual(['All categories', '🍎 Fruits', '🥛 Dairy', '🥫 Pantry']);
  });

  it('shows how much each line holds and changes it with - and +', async () => {
    const { user } = await renderCompare();
    await add(user, 'yog', /^Natural yogurt/);
    const less = screen.getByRole('button', { name: 'Less: Natural yogurt' });
    const more = screen.getByRole('button', { name: 'More: Natural yogurt' });

    expect(listRows()).toEqual(['🥛Natural yogurt1 × 250 g−+✕']);
    expect(less).toHaveProperty('disabled', true);
    await user.click(more);
    await user.click(more);
    expect(screen.getByText('3 × 250 g (750 g)')).toBeTruthy();
    await user.click(less);
    expect(screen.getByText('2 × 250 g (500 g)')).toBeTruthy();

    // Adding it again adds one more.
    await add(user, 'yog', /^Natural yogurt.*on your list/);
    expect(screen.getByText('3 × 250 g (750 g)')).toBeTruthy();

    await user.click(screen.getByRole('button', { name: 'Remove: Natural yogurt' }));
    expect(screen.getByText('Search above to add products to compare.')).toBeTruthy();
  });

  it('sends the list, the stores, diets and split threshold', async () => {
    const { user, fetchMock } = await renderCompare([{ status: 200, body: COMPARE_SPLIT }]);
    const compareButton = screen.getByRole('button', { name: /Compare prices/ });
    expect(compareButton).toHaveProperty('disabled', true); // nothing on the list

    await add(user, 'yog', /^Natural yogurt/);
    await user.click(screen.getByRole('button', { name: 'More: Natural yogurt' }));
    await add(user, 'banan', /^Bananas/);
    await user.click(screen.getByRole('button', { name: 'Vegan' }));
    const threshold = screen.getByLabelText(/Split across stores only if/);
    expect(threshold).toHaveProperty('value', '3');

    await user.clear(threshold);
    await user.type(threshold, '1,234');
    expect(screen.getByText(/at most 2 decimals/)).toBeTruthy();
    expect(compareButton).toHaveProperty('disabled', true);
    await user.clear(threshold);
    await user.type(threshold, '5,5');
    await user.click(compareButton);

    await screen.findByTestId('compare-recommendation');
    const [url, init] = fetchMock.mock.calls.at(-1) as unknown as [string, RequestInit];
    expect(url).toMatch(/\/compare$/);
    expect(JSON.parse(String(init.body))).toEqual({
      items: [
        { concept_id: 'yogurt_natural', quantity: 2 },
        { concept_id: 'bananas', quantity: 1 },
      ],
      stores: ['Lidl', 'Penny'],
      diet_tags: ['vegan'],
      min_split_savings_eur: 5.5,
      country: 'AT',
    });
  });

  it('keeps the list in localStorage', async () => {
    const { user, view } = await renderCompare();
    await add(user, 'yog', /^Natural yogurt/);
    await user.click(screen.getByRole('button', { name: 'More: Natural yogurt' }));
    await user.click(screen.getByRole('button', { name: 'Penny' })); // compare Lidl only
    view.unmount();

    await renderCompare();

    expect(await screen.findByText('2 × 250 g (500 g)')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Penny' }).getAttribute('aria-pressed')).toBe(
      'false'
    );
    expect(JSON.parse(localStorage.getItem(COMPARE_LIST_KEY) ?? '{}')).toMatchObject({
      items: [{ concept_id: 'yogurt_natural', quantity: 2 }],
      stores: ['Lidl'],
    });
  });

  it('copies a link to the list that opens it again', async () => {
    const { user } = await renderCompare();
    await add(user, 'yog', /^Natural yogurt/);

    await user.click(screen.getByRole('button', { name: /Share list/ }));

    expect(await screen.findByText('Link copied to clipboard.')).toBeTruthy();
    const url = new URL(await navigator.clipboard.readText());
    expect(parseShareHash(url.hash)).toEqual({
      kind: 'list',
      list: {
        items: [{ concept_id: 'yogurt_natural', quantity: 1 }],
        stores: ['Lidl', 'Penny'],
        diet_tags: [],
        min_split_savings_eur: 3,
        country: 'AT',
      },
    });
  });
});

describe('compare results', () => {
  it('recommends the split basket and checks it off per store', async () => {
    const { user } = await compareWith(COMPARE_SPLIT);

    const banner = screen.getByTestId('compare-recommendation');
    expect(within(banner).getByRole('heading').textContent).toContain('Split your shopping');
    expect(banner.textContent).toContain(
      'saves €3.00 compared with shopping only at Lidl.Total: €5.00 · 2 stores'
    );
    expect(screen.getByRole('tab', { name: /Split basket/ }).getAttribute('aria-selected')).toBe(
      'true'
    );
    const lidl = screen.getByRole('region', { name: 'Buy at Lidl · €4.00' });
    expect(screen.getByRole('region', { name: 'Buy at Penny · €1.00' })).toBeTruthy();

    const milk = within(lidl).getByRole('checkbox', { name: /Whole milk 3.5%/ });
    await user.click(milk);
    expect(milk).toHaveProperty('checked', true);
    expect(screen.getByText('1 of 4 in the basket')).toBeTruthy();

    // Ticks survive a look at the other tab.
    await user.click(screen.getByRole('tab', { name: /By store/ }));
    await user.click(screen.getByRole('tab', { name: /Split basket/ }));
    expect(screen.getByRole('checkbox', { name: /Whole milk 3.5%/ })).toHaveProperty(
      'checked',
      true
    );
  });

  it('ranks the stores with packs, price per unit, promotions and missing items', async () => {
    const { user } = await compareWith(COMPARE_SPLIT);

    screen.getByRole('tab', { name: /Split basket/ }).focus();
    await user.keyboard('{ArrowLeft}'); // arrow keys move between the tabs
    expect(screen.getByRole('tab', { name: /By store/ })).toBe(document.activeElement);

    const [lidl, penny] = screen.getAllByRole('region', { name: /^\d\. / });
    expect(within(lidl).getByRole('heading').textContent).toBe('1. Lidl');
    expect(screen.getByTestId('store-total-Lidl').textContent).toBe('€8.00');
    expect(lidl.textContent).toContain('4 items · Promotions save €0.50');
    const yogurt = within(lidl).getByText('Natural yogurt 3.6%').closest('li');
    expect(yogurt?.textContent).toContain('2 × 250 g · €8.00/kg€4.00');
    const butter = within(lidl).getByText('Butter').closest('li');
    expect(butter?.querySelector('del')?.textContent).toBe('€2.00');
    expect(butter?.textContent).toContain('🏷️ PromoRegular price: €2.00€1.50until 08/11/2026');

    expect(within(penny).getByRole('heading').textContent).toBe('2. Penny');
    expect(penny.textContent).toContain('3 items · Missing: 1 item');
    expect(penny.textContent).toContain('Not available here: Bananas');
  });

  it('explains a single-store recommendation and why splitting is not worth it', async () => {
    const { user } = await renderCompare([{ status: 200, body: COMPARE_SINGLE }]);
    await buildList(user);
    const threshold = screen.getByLabelText(/Split across stores only if/);
    await user.clear(threshold);
    await user.type(threshold, '5');
    await user.click(screen.getByRole('button', { name: /Compare prices/ }));

    const banner = await screen.findByTestId('compare-recommendation');
    expect(within(banner).getByRole('heading').textContent).toContain('Shop at Lidl');
    expect(banner.textContent).toContain('The cheapest single store for your list: €8.00.');
    expect(banner.textContent).toContain(
      'Splitting across stores would save only €3.00, less than your €5.00.'
    );
    expect(screen.getByRole('tab', { name: /By store/ }).getAttribute('aria-selected')).toBe(
      'true'
    );
    expect(screen.getAllByRole('region', { name: /^\d\. / })[0].textContent).toContain(
      '✓ Recommended'
    );
  });

  it('warns about products none of the stores sells', async () => {
    const response: CompareResponse = {
      ...COMPARE_SPLIT,
      split_basket: { ...COMPARE_SPLIT.split_basket, missing_concepts: ['rice', 'eggs'] },
    };
    await compareWith(response);

    expect(screen.getByText(/Not sold at any selected store \(2 items\):/).textContent).toContain(
      'Rice, Eggs'
    );
  });

  it('says so when no store sells anything on the list', async () => {
    const empty: CompareResponse = {
      ...COMPARE_SPLIT,
      single_store_rankings: COMPARE_SPLIT.single_store_rankings.map(s => ({
        ...s,
        items: [],
        total_eur: 0,
        missing_concepts: ['rice'],
      })),
      split_basket: {
        stores: [],
        total_eur: 0,
        missing_concepts: ['rice'],
        total_savings_vs_worst_eur: 0,
      },
      recommended_strategy: 'single_store',
      recommended_store: null,
      split_extra_savings_eur: 0,
    };
    const { user } = await renderCompare([{ status: 200, body: empty }]);
    await add(user, 'rice', /^Rice/);
    await user.click(screen.getByRole('button', { name: /Compare prices/ }));

    expect((await screen.findByRole('alert')).textContent).toContain(
      'None of the selected stores sells the products on your list.'
    );
    expect(screen.queryByRole('tablist')).toBeNull();
  });

  it('marks the result outdated once the list changes', async () => {
    const { user } = await compareWith(COMPARE_SPLIT);
    expect(screen.queryByText(/Your list has changed/)).toBeNull();

    await user.click(screen.getByRole('button', { name: 'More: Bananas' }));
    expect(screen.getByText(/Your list has changed/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Less: Bananas' }));
    expect(screen.queryByText(/Your list has changed/)).toBeNull();
  });

  it('compares again from the outdated notice and moves focus to the new result', async () => {
    const updated: CompareResponse = {
      ...COMPARE_SPLIT,
      split_basket: { ...COMPARE_SPLIT.split_basket, total_eur: 6 },
    };
    const { user, fetchMock } = await renderCompare([
      { status: 200, body: COMPARE_SPLIT },
      { status: 200, body: updated },
    ]);
    await buildList(user);
    await user.click(screen.getByRole('button', { name: /Compare prices/ }));
    await screen.findByTestId('compare-recommendation');
    expect(screen.queryByRole('button', { name: /Compare again/ })).toBeNull();

    await user.click(screen.getByRole('button', { name: 'More: Bananas' }));
    await user.click(screen.getByRole('button', { name: /Compare again/ }));

    await waitFor(() => {
      expect(screen.getByTestId('compare-recommendation').textContent).toContain('Total: €6.00');
    });
    expect(screen.queryByText(/Your list has changed/)).toBeNull();
    expect(screen.queryByRole('button', { name: /Compare again/ })).toBeNull();
    expect(document.activeElement).toBe(screen.getByRole('region', { name: 'Comparison' }));
    const [, init] = fetchMock.mock.calls.at(-1) as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body)).items).toContainEqual({
      concept_id: 'bananas',
      quantity: 2,
    });
  });

  it('cannot compare again from the notice while the list is empty', async () => {
    const { user } = await compareWith(COMPARE_SPLIT);

    await user.click(screen.getByRole('button', { name: 'Clear list' }));

    expect(screen.getByText(/Your list has changed/)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Compare again/ })).toHaveProperty('disabled', true);
  });

  it.each([
    [{ status: 500, body: null }, 'Could not compare prices. Please try again.'],
    [
      { status: 422, body: { detail: 'Raw backend detail', code: 'unknown_store' } },
      'A selected store is not available for this country.',
    ],
  ])('shows a translated error, never the backend detail', async (reply, message) => {
    const { user } = await renderCompare([reply]);
    await add(user, 'rice', /^Rice/);
    await user.click(screen.getByRole('button', { name: /Compare prices/ }));

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain(message);
    expect(alert.textContent).not.toContain('Raw backend detail');
  });
});

describe('compare in Ukrainian', () => {
  it('uses clean names and the plural forms of items and stores', async () => {
    const { user } = await renderCompare([{ status: 200, body: COMPARE_SPLIT }], 'uk');
    const heading = () => screen.getByRole('heading', { name: /Ваш список/ }).textContent;
    expect(heading()).toContain('(0 товарів)');

    await add(user, 'йогурт', /^Натуральний йогурт/);
    expect(heading()).toContain('(1 товар)');
    await add(user, 'молоко', /^Цільне молоко/);
    await add(user, 'банан', /^Банани/);
    expect(heading()).toContain('(3 товари)');
    await add(user, 'масло', /^Вершкове масло/);
    await add(user, 'рис', /^Рис/);
    expect(heading()).toContain('(5 товарів)');

    await user.click(screen.getByRole('button', { name: /Порівняти ціни/ }));
    const banner = await screen.findByTestId('compare-recommendation');
    expect(banner.textContent).toContain('Разом: €5.00 · 2 магазини');
    await waitFor(() => {
      expect(screen.getByRole('region', { name: 'У Lidl взяти на €4.00' })).toBeTruthy();
    });

    await user.click(screen.getByRole('button', { name: 'Більше: Рис' }));
    expect(screen.getByText(/Список змінився/)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Порівняти ще раз/ })).toBeTruthy();
  });
});
