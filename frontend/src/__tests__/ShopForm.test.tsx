import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ShopForm } from '../components';
import { META, mockFetch } from '../test/fixtures';
import { renderWithLanguage } from '../test/render';

const storeGroup = () => screen.getByRole('group', { name: 'Select Supermarkets' });
const storeChips = () =>
  Array.from(storeGroup().querySelectorAll('button')).map(
    b => `${b.textContent}${b.getAttribute('aria-pressed') === 'true' ? ' ✓' : ''}`
  );
const submitButton = () => screen.getByRole('button', { name: /Generate Shopping List/ });

describe('ShopForm', () => {
  it('renders store chips from the catalog meta and changes them with the country', async () => {
    mockFetch({ ...META, countries: { AT: ['Lidl', 'Penny', 'Spar'], DE: ['Lidl', 'Rewe'] } });
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);

    await screen.findByRole('button', { name: 'Penny' });
    // The first two stores are preselected.
    await waitFor(() => {
      expect(storeChips()).toEqual(['Lidl ✓', 'Penny ✓', 'Spar']);
    });
    expect(screen.getByRole('button', { name: /Austria/ }).getAttribute('aria-pressed')).toBe(
      'true'
    );

    await user.click(screen.getByRole('button', { name: /Germany/ }));
    // Lidl exists in DE too and stays selected; Penny doesn't and is dropped.
    await waitFor(() => {
      expect(storeChips()).toEqual(['Lidl ✓', 'Rewe']);
    });
  });

  it('preselects the first two stores when nothing valid is left after a country change', async () => {
    mockFetch({ ...META, countries: { AT: ['Penny', 'Spar'], DE: ['Edeka', 'Lidl', 'Rewe'] } });
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);

    await screen.findByRole('button', { name: 'Penny' });
    await user.click(screen.getByRole('button', { name: /Germany/ }));

    await waitFor(() => {
      expect(storeChips()).toEqual(['Edeka ✓', 'Lidl ✓', 'Rewe']);
    });
  });

  it('labels every form field and names every option group', async () => {
    mockFetch(META);
    const user = userEvent.setup();
    const { container } = renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);
    await screen.findByRole('button', { name: 'Penny' });
    await user.click(screen.getByRole('button', { name: /Meal Planning/ }));

    for (const label of container.querySelectorAll('label')) {
      expect(label.control, label.textContent ?? '').not.toBeNull();
    }
    for (const field of container.querySelectorAll('input, select, textarea')) {
      expect((field as HTMLInputElement).labels?.length, field.id).toBeGreaterThan(0);
    }
    const groups = screen.getAllByRole('group').map(g => g.getAttribute('aria-labelledby'));
    expect(groups).toHaveLength(6);
    for (const id of groups) {
      expect(document.getElementById(id ?? '')?.textContent).toBeTruthy();
    }
    expect(screen.getByRole('group', { name: 'Mode' })).toBeTruthy();
    expect(screen.getByRole('group', { name: 'Family Size' })).toBeTruthy();
  });

  it('hides a country without stores', async () => {
    mockFetch({ ...META, countries: { AT: ['Lidl', 'Penny'], DE: [] } });
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);

    await screen.findByRole('button', { name: 'Penny' });
    expect(screen.queryByRole('button', { name: /Germany/ })).toBeNull();
  });

  it('shows loading, then an error with a working retry', async () => {
    const fetchMock = mockFetch({ status: 500, body: null });
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);

    expect(screen.getByRole('status').textContent).toBe('Loading stores…');
    expect(await screen.findByText('Could not load the store list.')).toBeTruthy();
    expect(submitButton()).toHaveProperty('disabled', true);

    fetchMock.mockImplementation(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(META) } as Response)
    );
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByRole('button', { name: 'Penny' })).toBeTruthy();
    expect(storeChips()).toEqual(['Lidl ✓', 'Penny ✓']);
  });

  it('submits country, stores, diets, mode and days', async () => {
    mockFetch();
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={onSubmit} />);

    await screen.findByRole('button', { name: 'Lidl' });
    await user.click(screen.getByRole('button', { name: /Vegetarian/ }));
    await user.click(screen.getByRole('button', { name: /Meal Planning/ }));
    await user.click(screen.getByRole('button', { name: '3' }));
    await user.click(screen.getByRole('button', { name: /Generate Menu/ }));

    expect(onSubmit).toHaveBeenCalledWith({
      country: 'AT',
      supermarkets: ['Lidl', 'Penny'],
      budget: 50,
      family_size: 2,
      diets: ['vegetarian'],
      preferences: '',
      language: 'en',
      mode: 'menu',
      days: 3,
    });
  });

  it('needs at least one store and a budget of 10-1000', async () => {
    mockFetch();
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);

    await screen.findByRole('button', { name: 'Lidl' });
    expect(submitButton()).toHaveProperty('disabled', false);

    // Deselecting everything doesn't bring the defaults back.
    await user.click(screen.getByRole('button', { name: 'Lidl' }));
    await user.click(screen.getByRole('button', { name: 'Penny' }));
    expect(storeChips()).toEqual(['Lidl', 'Penny']);
    expect(submitButton()).toHaveProperty('disabled', true);

    await user.click(screen.getByRole('button', { name: 'Lidl' }));
    const budget = screen.getByLabelText(/^💰 Budget$/);
    await user.clear(budget);
    await user.type(budget, '5');
    expect(submitButton()).toHaveProperty('disabled', true);
    await user.type(budget, '0');
    await waitFor(() => expect(submitButton()).toHaveProperty('disabled', false));
  });

  describe('budget field', () => {
    const budgetInput = () => screen.getByLabelText<HTMLInputElement>(/^💰 Budget$/);
    const budgetError = () => screen.queryByText('Enter a budget between €10 and €1000.');

    it('can be cleared to empty and retyped', async () => {
      mockFetch();
      const user = userEvent.setup();
      renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);
      await screen.findByRole('button', { name: 'Lidl' });

      await user.clear(budgetInput());
      expect(budgetInput().value).toBe('');
      expect(budgetError()).toBeTruthy();
      expect(submitButton()).toHaveProperty('disabled', true);

      await user.type(budgetInput(), '40');
      expect(budgetInput().value).toBe('40');
      expect(budgetError()).toBeNull();
      expect(submitButton()).toHaveProperty('disabled', false);
    });

    it('strips leading zeros and accepts a decimal comma', async () => {
      mockFetch();
      const onSubmit = vi.fn();
      const user = userEvent.setup();
      renderWithLanguage(<ShopForm onSubmit={onSubmit} />, 'de');
      await screen.findByRole('button', { name: 'Lidl' });
      const input = screen.getByLabelText<HTMLInputElement>(/^💰 Budget$/);

      await user.clear(input);
      await user.type(input, '040');
      expect(input.value).toBe('40');

      await user.clear(input);
      await user.type(input, '12,5');
      expect(input.value).toBe('12,5');
      await user.click(screen.getByRole('button', { name: /Einkaufsliste erstellen/ }));
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ budget: 12.5 }));
    });

    it('shows a message and blocks submit outside 10-1000', async () => {
      mockFetch();
      const onSubmit = vi.fn();
      const user = userEvent.setup();
      renderWithLanguage(<ShopForm onSubmit={onSubmit} />);
      await screen.findByRole('button', { name: 'Lidl' });

      await user.clear(budgetInput());
      await user.type(budgetInput(), '5');

      expect(budgetError()).toBeTruthy();
      expect(budgetInput().getAttribute('aria-invalid')).toBe('true');
      expect(submitButton()).toHaveProperty('disabled', true);
      await user.click(submitButton());
      expect(onSubmit).not.toHaveBeenCalled();

      await user.click(budgetInput()); // selects all
      await user.keyboard('{End}000');
      expect(budgetInput().value).toBe('5000');
      expect(budgetError()).toBeTruthy();
    });

    it('selects the whole amount on focus, so typing replaces it', async () => {
      mockFetch();
      const onSubmit = vi.fn();
      const user = userEvent.setup();
      renderWithLanguage(<ShopForm onSubmit={onSubmit} />);
      await screen.findByRole('button', { name: 'Lidl' });

      await user.click(budgetInput());
      expect([budgetInput().selectionStart, budgetInput().selectionEnd]).toEqual([0, 2]);

      await user.keyboard('80');
      expect(budgetInput().value).toBe('80');
      await user.click(submitButton());
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ budget: 80 }));
    });

    it('a later click inside the focused field places the cursor normally', async () => {
      mockFetch();
      const user = userEvent.setup();
      renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);
      await screen.findByRole('button', { name: 'Lidl' });

      await user.click(budgetInput());
      await user.keyboard('{End}');
      await user.keyboard('5');
      expect(budgetInput().value).toBe('505');
    });

    it('preset chips set the field', async () => {
      mockFetch();
      const user = userEvent.setup();
      renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);
      await screen.findByRole('button', { name: 'Lidl' });

      await user.clear(budgetInput());
      await user.click(screen.getByRole('button', { name: '€100' }));
      expect(budgetInput().value).toBe('100');
    });
  });

  it('labels the budget per mode', async () => {
    mockFetch();
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);

    expect(screen.getByLabelText(/^💰 Budget$/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: /Meal Planning/ }));
    expect(screen.getByLabelText(/^💰 Budget for 7 days$/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: '1' }));
    expect(screen.getByLabelText(/^💰 Budget for 1 day$/)).toBeTruthy();
  });

  it('allows at most five stores', async () => {
    const stores = ['A', 'B', 'C', 'D', 'E', 'F'];
    mockFetch({ ...META, countries: { AT: stores, DE: [] } });
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);

    await screen.findByRole('button', { name: 'F' });
    for (const store of ['C', 'D', 'E']) {
      await user.click(screen.getByRole('button', { name: store }));
    }
    expect(screen.getByRole('button', { name: 'F' })).toHaveProperty('disabled', true);
  });
});

describe('budget label in Ukrainian', () => {
  it('uses the plural form of the day count', async () => {
    mockFetch();
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />, 'uk');

    await user.click(screen.getByRole('button', { name: /Планування меню/ }));
    await user.click(screen.getByRole('button', { name: '3' }));
    expect(screen.getByLabelText(/^💰 Бюджет на 3 дні$/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: '5' }));
    expect(screen.getByLabelText(/^💰 Бюджет на 5 днів$/)).toBeTruthy();
  });
});
