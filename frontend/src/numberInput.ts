/**
 * Clean up what the user typed into a decimal field, keeping it a string so the field can
 * be empty while editing: drops anything but digits and one separator ("," or "."), and
 * leading zeros before another digit ("040" → "40", "0,5" stays).
 */
export function normalizeDecimalInput(raw: string): string {
  const kept = raw.replace(/[^\d.,]/g, '');
  const separator = kept.search(/[.,]/);
  const cleaned =
    separator === -1
      ? kept
      : kept.slice(0, separator + 1) + kept.slice(separator + 1).replace(/[.,]/g, '');
  return cleaned.replace(/^0+(?=\d)/, '');
}

/** The number in a normalized field ("12,5" → 12.5); NaN when it is empty. */
export function parseDecimal(text: string): number {
  return text === '' ? NaN : Number(text.replace(',', '.'));
}
