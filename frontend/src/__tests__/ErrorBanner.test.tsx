import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ErrorBanner } from '../components/ErrorBanner';
import type { ErrorCode } from '../api';
import { renderWithLanguage } from '../test/render';

const refresh = () => screen.queryByRole('button', { name: 'Refresh Page' });

describe('ErrorBanner', () => {
  it.each<ErrorCode>(['ai_unavailable', 'ai_timeout', 'generation_failed'])(
    'offers a retry for %s',
    async code => {
      const onRetry = vi.fn();
      renderWithLanguage(<ErrorBanner code={code} onDismiss={vi.fn()} onRetry={onRetry} />);

      await userEvent.setup().click(refresh()!);
      expect(onRetry).toHaveBeenCalledOnce();
    }
  );

  it.each<ErrorCode>(['not_enough_products', 'validation_error', 'unknown_store'])(
    'has no retry for %s, only dismiss',
    code => {
      renderWithLanguage(<ErrorBanner code={code} onDismiss={vi.fn()} onRetry={vi.fn()} />);

      expect(refresh()).toBeNull();
      expect(screen.getAllByRole('button', { name: 'Dismiss' })).toHaveLength(2);
    }
  );
});
