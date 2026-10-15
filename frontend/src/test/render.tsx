import React from 'react';
import { render } from '@testing-library/react';
import { LanguageProvider } from '../LanguageContext';
import type { Language } from '../translations';

export function renderWithLanguage(ui: React.ReactElement, language: Language = 'en') {
  localStorage.setItem('language', language);
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}
