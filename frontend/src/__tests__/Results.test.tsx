import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { LanguageSelector, Results } from '../components';
import { MAX_SHARE_URL_LENGTH, parseShareHash } from '../share';
import { MENU, SHOPPING } from '../test/fixtures';
import { renderWithLanguage } from '../test/render';

describe('Results', () => {
  it('shows total, budget bar and per-store subtotals', () => {
    renderWithLanguage(<Results response={SHOPPING} onReset={vi.fn()} />);

    expect(screen.getByTestId('total').textContent).toBe('€8.85');
    expect(screen.getByText(/€10\.00 budget/)).toBeTruthy();
    expect(screen.getByText('€1.15 left')).toBeTruthy();
    expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('89');
    expect(screen.getByText('🔥 Purchased food ≈ 416 kcal per person/day')).toBeTruthy();
    expect(screen.getByText(/Reference prices as of .*2026/)).toBeTruthy();

    const lidl = screen.getByRole('region', { name: 'Lidl' });
    expect(within(lidl).getByTestId('subtotal-Lidl').textContent).toBe('€6.56');
    expect(within(lidl).getByText('Whole milk 3.5%')).toBeTruthy();
    expect(within(lidl).getByText(/2 × 1 l • €1.29 per pack/)).toBeTruthy();
    expect(within(lidl).getByText('€2.58')).toBeTruthy();
    const penny = screen.getByRole('region', { name: 'Penny' });
    expect(within(penny).getByTestId('subtotal-Penny').textContent).toBe('€2.29');
    expect(within(penny).getByText('Rice')).toBeTruthy();
    expect(within(penny).getByText(/1 × 1 kg • €2.29 per pack/)).toBeTruthy();

    expect(screen.getByRole('complementary').textContent).toBe('💡 Tip: Buy seasonal.');
    expect(screen.queryByRole('status')).toBeNull(); // no warnings
  });

  it('labels kcal by their basis', () => {
    const { unmount } = renderWithLanguage(<Results response={SHOPPING} onReset={vi.fn()} />);
    expect(screen.getByText('🔥 Purchased food ≈ 416 kcal per person/day')).toBeTruthy();
    unmount();

    renderWithLanguage(<Results response={MENU} onReset={vi.fn()} />);
    expect(screen.getByText('🔥 Menu ≈ 1455 kcal per person/day')).toBeTruthy();
    expect(screen.queryByText(/Purchased food/)).toBeNull();
  });

  it('shows saved menus without portions', () => {
    const old = {
      ...MENU,
      menu: MENU.menu?.map(day => ({
        ...day,
        breakfast: { name: 'Porridge', description: 'Warm', ingredient_ids: ['x'] },
      })),
    } as unknown as typeof MENU;
    renderWithLanguage(<Results response={old} onReset={vi.fn()} />);

    expect(screen.getByText('Porridge')).toBeTruthy();
  });

  it('keeps the check-off progress', async () => {
    const user = userEvent.setup();
    renderWithLanguage(<Results response={SHOPPING} onReset={vi.fn()} />);

    expect(screen.getByText('0% completed')).toBeTruthy();
    await user.click(screen.getByRole('button', { name: /Rice/ }));
    expect(screen.getByText('33% completed')).toBeTruthy();
  });

  it('shows budget_trimmed and low_kcal notices', () => {
    renderWithLanguage(<Results response={MENU} onReset={vi.fn()} />);

    const [lowKcal, trimmed] = screen.getAllByRole('status');
    expect(lowKcal.textContent).toContain('≈ 1455 kcal per person/day');
    expect(trimmed.textContent).toContain('reduced or removed to stay within your budget');
    const changes = within(trimmed)
      .getAllByRole('listitem')
      .map(li => li.textContent);
    expect(changes).toEqual(['Potato chips: removed', 'Apples: reduced 3→2']);
  });

  it('strikes through a menu ingredient that was removed for the budget', async () => {
    const user = userEvent.setup();
    renderWithLanguage(<Results response={MENU} onReset={vi.fn()} />);

    const monday = screen.getByRole('region', { name: 'Monday' });
    expect(within(monday).getByText('Porridge')).toBeTruthy();
    // Portions per person: g for kg products, ml for l.
    expect(within(monday).getByText('Rice · 80 g')).toBeTruthy();
    expect(within(monday).getByText('Whole milk 3.5% · 200 ml')).toBeTruthy();
    const removed = within(monday).getByText('Potato chips');
    expect(removed.tagName).toBe('S');
    expect(removed.parentElement?.textContent).toBe('Potato chips removed (budget)');

    await user.click(screen.getByRole('tab', { name: /Products for this menu/ }));
    expect(screen.getByRole('region', { name: 'Penny' })).toBeTruthy();
  });

  it('marks an ingredient bought in fewer packs than the menu needs', () => {
    renderWithLanguage(<Results response={MENU} onReset={vi.fn()} />);

    const monday = screen.getByRole('region', { name: 'Monday' });
    // Apples were reduced from 3 to 2 packs; chips were removed completely.
    const apples = within(monday).getByText(/Apples · 150 g/);
    expect(apples.getAttribute('title')).toBe('only 2 of 3 packs bought (budget)');
    expect(
      within(apples).getByRole('img', { name: 'only 2 of 3 packs bought (budget)' })
    ).toBeTruthy();
    const milk = within(monday).getByText(/Whole milk 3.5% · 200 ml/);
    expect(milk.getAttribute('title')).toBeNull();
    expect(within(monday).getByText('Potato chips').tagName).toBe('S');
  });

  it('translates the partial-purchase note', () => {
    renderWithLanguage(<Results response={MENU} onReset={vi.fn()} />, 'uk');

    expect(screen.getByTitle('куплено лише 2 з 3 уп. (бюджет)')).toBeTruthy();
  });

  it('derives a name from the id for plans saved without trimmed names', () => {
    const old = {
      ...MENU,
      trimmed: [{ product_id: 'at-lidl-potato-chips-175g', from_packs: 2, to_packs: 0 }],
    } as unknown as typeof MENU;
    renderWithLanguage(<Results response={old} onReset={vi.fn()} />);

    expect(screen.getByText('potato chips 175g: removed')).toBeTruthy();
    expect(screen.getByText('potato chips 175g').tagName).toBe('S');
  });

  it('renders in German, product names included', () => {
    renderWithLanguage(<Results response={MENU} onReset={vi.fn()} />, 'de');

    expect(screen.getByText('entfernt (Budget)')).toBeTruthy();
    expect(screen.getByText(/Menü ≈ 1455 kcal pro Person\/Tag/)).toBeTruthy();
    expect(screen.getByText('Kartoffelchips: entfernt')).toBeTruthy();
    expect(screen.getByText('Kartoffelchips').tagName).toBe('S');
    expect(screen.getByText('Vollmilch 3,5% · 200 ml')).toBeTruthy();
  });

  it('re-labels products when the UI language changes; meals stay as generated', async () => {
    const user = userEvent.setup();
    renderWithLanguage(
      <>
        <LanguageSelector />
        <Results response={MENU} onReset={vi.fn()} />
      </>
    );
    const monday = () => screen.getByRole('region', { name: 'Monday' });
    expect(within(monday()).getByText('Whole milk 3.5% · 200 ml')).toBeTruthy();

    await user.click(screen.getByTitle('Українська'));

    expect(within(monday()).getByText('Молоко 3,5% · 200 мл')).toBeTruthy();
    expect(within(monday()).getByText('Porridge')).toBeTruthy();
    expect(screen.getByText('Картопляні чипси: прибрано')).toBeTruthy();
  });

  it('falls back to `name` for plans saved before `names` existed', () => {
    const old = {
      ...SHOPPING,
      items: SHOPPING.items.map(item => ({ ...item, names: undefined })),
    } as unknown as typeof SHOPPING;
    renderWithLanguage(<Results response={old} onReset={vi.fn()} />, 'de');

    expect(screen.getByText('Whole milk 3.5%')).toBeTruthy();
  });

  it('copies a share link that opens the same plan', async () => {
    const user = userEvent.setup(); // installs a clipboard stub
    renderWithLanguage(<Results response={MENU} onReset={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /Share/ }));

    expect(await screen.findByText('Link copied to clipboard.')).toBeTruthy();
    const url = new URL(await navigator.clipboard.readText());
    expect(parseShareHash(url.hash)).toEqual({ kind: 'plan', plan: MENU });
  });

  it('suggests copy or print when the plan is too large to share', async () => {
    const user = userEvent.setup();
    const notes = Array.from({ length: MAX_SHARE_URL_LENGTH }, (_, i) =>
      String.fromCharCode(0x4e00 + ((i * 7919) % 20000))
    ).join('');
    renderWithLanguage(<Results response={{ ...SHOPPING, notes }} onReset={vi.fn()} />);
    const writeText = vi.spyOn(navigator.clipboard, 'writeText');

    await user.click(screen.getByRole('button', { name: /Share/ }));

    expect((await screen.findByRole('status')).textContent).toContain('too large to share');
    expect(writeText).not.toHaveBeenCalled();
  });

  it('has no Share button for a shared plan and offers to create your own', async () => {
    const user = userEvent.setup();
    const onReset = vi.fn();
    renderWithLanguage(<Results response={SHOPPING} onReset={onReset} shared />);

    expect(screen.queryByRole('button', { name: /Share/ })).toBeNull();
    await user.click(screen.getByRole('button', { name: /Create your own/ }));
    expect(onReset).toHaveBeenCalledOnce();
  });
});
