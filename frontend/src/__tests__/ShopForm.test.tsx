import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ShopForm } from '../components';
import { META, mockFetch } from '../test/fixtures';
import { renderWithLanguage } from '../test/render';

const storeGroup = () => screen.getByRole('group', { name: 'Select Supermarkets' });
const storeNames = () =>
  Array.from(storeGroup().querySelectorAll('button')).map(b => b.textContent);
const submitButton = () => screen.getByRole('button', { name: /Generate Shopping List/ });

describe('ShopForm', () => {
  it('renders store chips from the catalog meta and changes them with the country', async () => {
    mockFetch();
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);

    await screen.findByRole('button', { name: 'Penny' });
    expect(storeNames()).toEqual(['Lidl', 'Penny']);
    expect(screen.getByRole('button', { name: /Austria/ }).getAttribute('aria-pressed')).toBe('true');

    await user.click(screen.getByRole('button', { name: 'Lidl' }));
    await user.click(screen.getByRole('button', { name: 'Penny' }));
    await user.click(screen.getByRole('button', { name: /Germany/ }));

    expect(storeNames()).toEqual(['Lidl', 'Rewe']);
    // Lidl exists in DE too and stays selected; Penny doesn't and is dropped.
    expect(screen.getByRole('button', { name: 'Lidl' }).getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('button', { name: 'Rewe' }).getAttribute('aria-pressed')).toBe('false');
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
  });

  it('submits country, stores, diets, mode and days', async () => {
    mockFetch();
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={onSubmit} />);

    await user.click(await screen.findByRole('button', { name: 'Lidl' }));
    await user.click(screen.getByRole('button', { name: 'Penny' }));
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
    expect(submitButton()).toHaveProperty('disabled', true);

    await user.click(screen.getByRole('button', { name: 'Lidl' }));
    expect(submitButton()).toHaveProperty('disabled', false);

    const budget = screen.getByLabelText(/Weekly Budget/);
    await user.clear(budget);
    await user.type(budget, '5');
    expect(submitButton()).toHaveProperty('disabled', true);
    await user.type(budget, '0');
    await waitFor(() => expect(submitButton()).toHaveProperty('disabled', false));
  });

  it('allows at most five stores', async () => {
    const stores = ['A', 'B', 'C', 'D', 'E', 'F'];
    mockFetch({ ...META, countries: { AT: stores, DE: [] } });
    const user = userEvent.setup();
    renderWithLanguage(<ShopForm onSubmit={vi.fn()} />);

    await screen.findByRole('button', { name: 'F' });
    for (const store of stores.slice(0, 5)) {
      await user.click(screen.getByRole('button', { name: store }));
    }
    expect(screen.getByRole('button', { name: 'F' })).toHaveProperty('disabled', true);
  });
});
