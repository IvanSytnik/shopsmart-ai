import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Results } from '../components';
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

    expect(screen.getByRole('complementary').textContent).toBe('💡 Tip: Buy seasonal.');
    expect(screen.queryByRole('status')).toBeNull(); // no warnings
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
    expect(within(monday).getAllByText('Rice')).toHaveLength(2);
    const removed = within(monday).getByText('Potato chips');
    expect(removed.tagName).toBe('S');
    expect(removed.parentElement?.textContent).toBe('Potato chips removed (budget)');

    await user.click(screen.getByRole('tab', { name: /Products for this menu/ }));
    expect(screen.getByRole('region', { name: 'Penny' })).toBeTruthy();
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

  it('renders in German', () => {
    renderWithLanguage(<Results response={MENU} onReset={vi.fn()} />, 'de');

    expect(screen.getByText('entfernt (Budget)')).toBeTruthy();
    expect(screen.getByText(/Gekaufte Lebensmittel ≈ 1455 kcal pro Person\/Tag/)).toBeTruthy();
  });
});
