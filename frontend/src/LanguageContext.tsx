import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { translations, pluralNouns, Language, PluralNoun, TranslationKey } from './translations';
import { pluralForm } from './plural';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  // `{name}` placeholders are replaced from `vars`.
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string;
  // "3 items", "1 store": the count and the noun in its plural form.
  tn: (noun: PluralNoun, count: number) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguage] = useState<Language>(() => {
    const saved = localStorage.getItem('language');
    return (saved as Language) || 'en';
  });

  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  const t = (key: TranslationKey, vars?: Record<string, string | number>): string => {
    const text: string = translations[language][key] || translations.en[key] || key;
    return vars
      ? text.replace(/\{(\w+)\}/g, (match, name: string) => String(vars[name] ?? match))
      : text;
  };

  const tn = (noun: PluralNoun, count: number): string =>
    `${count} ${pluralForm(language, count, pluralNouns[language][noun])}`;

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, tn }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
