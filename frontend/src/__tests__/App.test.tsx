import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import App from '../App';
import { HISTORY_KEY } from '../history';
import { SHARE_HASH_PREFIX, encodePlan } from '../share';
import { SHOPPING, mockFetch } from '../test/fixtures';

// Lidl and Penny are preselected.
async function submitForm() {
  const user = userEvent.setup();
  await screen.findByRole('button', { name: 'Lidl' });
  await user.click(screen.getByRole('button', { name: /Generate Shopping List/ }));
  return user;
}

describe('App', () => {
  afterEach(() => {
    window.history.replaceState(null, '', '/');
  });

  it('shows the subtitle and footer credit without model names', async () => {
    mockFetch();
    render(<App />);
    await screen.findByRole('button', { name: 'Lidl' });

    expect(screen.getByText('AI meal & shopping planner with real store prices')).toBeTruthy();
    const footer = screen.getByRole('contentinfo').textContent ?? '';
    expect(footer).toContain('© 2025–2026');
    expect(footer).toContain('NTU "KhPI"');
    expect(document.body.textContent).not.toContain('GPT-4');
  });

  it.each([
    ['unknown_store', 422, 'A selected store is not available for this country.'],
    ['not_enough_products', 422, 'Add another store, or remove a diet.'],
    ['rate_limited', 429, 'Too many requests.'],
    ['ai_timeout', 504, 'The AI service took too long to respond.'],
  ])('shows the translated message for %s, not the backend detail', async (code, status, text) => {
    mockFetch(undefined, [{ status, body: { detail: 'Raw backend detail', code } }]);
    render(<App />);

    await submitForm();

    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain(text);
    expect(alert.textContent).not.toContain('Raw backend detail');
    // The form stays filled in.
    expect(screen.getByRole('button', { name: 'Lidl' }).getAttribute('aria-pressed')).toBe('true');
  });

  it('translates error codes into the selected language', async () => {
    localStorage.setItem('language', 'uk');
    mockFetch(undefined, [{ status: 429, body: { detail: 'x', code: 'rate_limited' } }]);
    render(<App />);

    const user = userEvent.setup();
    await screen.findByRole('button', { name: 'Lidl' });
    await user.click(screen.getByRole('button', { name: /Згенерувати список/ }));

    expect((await screen.findByRole('alert')).textContent).toContain('Забагато запитів.');
  });

  it('maps an unreachable server and an unknown error body', async () => {
    mockFetch(undefined, [new TypeError('Failed to fetch'), { status: 500, body: 'oops' }]);
    render(<App />);

    const user = await submitForm();
    expect((await screen.findByRole('alert')).textContent).toContain('Cannot reach the server.');
    await user.click(screen.getByRole('button', { name: /Generate Shopping List/ }));
    expect((await screen.findByRole('alert')).textContent).toContain('Could not generate a plan.');
  });

  it('sends the request, shows the result and saves it to history', async () => {
    const fetchMock = mockFetch(undefined, [{ status: 200, body: SHOPPING }]);
    render(<App />);

    await submitForm();

    expect((await screen.findByTestId('total')).textContent).toBe('€8.85');
    const [, init] = fetchMock.mock.calls[1] as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toMatchObject({
      country: 'AT',
      supermarkets: ['Lidl', 'Penny'],
    });
    const saved = JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]');
    expect(saved).toHaveLength(1);
    expect(saved[0].response.total).toBe(8.85);
  });

  it('ignores v1 history without crashing', async () => {
    localStorage.setItem(
      'shopsmart-history',
      JSON.stringify([
        { id: '1', totalCost: 40, response: { items: [{ product: 'Milk', quantity: '1 l' }] } },
      ])
    );
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify([{ id: '2', itemCount: 1, response: { items: [] } }])
    );
    mockFetch();
    render(<App />);

    const user = userEvent.setup();
    await user.click(screen.getByTitle('History'));

    expect(screen.getByText('No saved lists yet')).toBeTruthy();
    expect(localStorage.getItem('shopsmart-history')).toBeNull();
  });

  it('opens a shared plan read-only and leaves it with "Create your own"', async () => {
    window.history.replaceState(null, '', `/${SHARE_HASH_PREFIX}${encodePlan(SHOPPING)}`);
    mockFetch();
    render(<App />);

    expect(screen.getByText(/Shared plan \(read-only\)/)).toBeTruthy();
    expect(screen.getByTestId('total').textContent).toBe('€8.85');
    expect(screen.queryByRole('button', { name: /Generate Shopping List/ })).toBeNull();
    expect(localStorage.getItem(HISTORY_KEY)).toBeNull(); // not saved to the viewer's history

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Create your own/ }));

    expect(await screen.findByRole('button', { name: /Generate Shopping List/ })).toBeTruthy();
    expect(screen.queryByTestId('total')).toBeNull();
    expect(window.location.hash).toBe('');
  });

  it('explains an invalid share link and offers the form', async () => {
    window.history.replaceState(null, '', `/${SHARE_HASH_PREFIX}broken`);
    mockFetch();
    render(<App />);

    expect(screen.getByRole('alert').textContent).toContain('This share link is invalid');
    expect(screen.queryByRole('button', { name: /Generate Shopping List/ })).toBeNull();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Create your own/ }));
    expect(await screen.findByRole('button', { name: /Generate Shopping List/ })).toBeTruthy();
  });
});
