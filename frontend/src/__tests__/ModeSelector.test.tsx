import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ModeSelector } from '../components/ModeSelector';
import { renderWithLanguage } from '../test/render';

describe('mode tabs', () => {
  it('shows compact labels on narrow screens and keeps the full ones as names', async () => {
    const onChange = vi.fn();
    renderWithLanguage(<ModeSelector mode="compare" onChange={onChange} />, 'de');

    const buttons = screen.getAllByRole('button');
    expect(buttons.map(b => b.getAttribute('aria-pressed'))).toEqual(['false', 'false', 'true']);
    // The compact label is only visible below `sm`; screen readers get the full one.
    expect(
      buttons.map(b => [
        b.querySelector('[aria-hidden="true"].sm\\:hidden')?.textContent,
        b.querySelector('.sr-only')?.textContent,
      ])
    ).toEqual([
      ['Einkauf', 'Einkaufsliste'],
      ['Menü', 'Menüplanung'],
      ['Vergleich', 'Vergleichen'],
    ]);

    await userEvent.setup().click(screen.getByRole('button', { name: 'Menüplanung' }));
    expect(onChange).toHaveBeenCalledWith('menu');
  });
});
