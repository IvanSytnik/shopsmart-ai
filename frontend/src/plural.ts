import type { Language } from './translations';

// One string per CLDR plural category the language uses; `other` is always required.
export type PluralForms = Partial<Record<Intl.LDMLPluralRule, string>> & { other: string };

const rules = new Map<Language, Intl.PluralRules>();

/** The form of `forms` for `count` in `language` (uk: one / few / many / other). */
export const pluralForm = (language: Language, count: number, forms: PluralForms): string => {
  let rule = rules.get(language);
  if (!rule) {
    rule = new Intl.PluralRules(language);
    rules.set(language, rule);
  }
  return forms[rule.select(count)] ?? forms.other;
};
