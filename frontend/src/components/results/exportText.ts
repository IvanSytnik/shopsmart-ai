import type { Language } from '../../translations';
import type { GenerateResponse } from '../../types';
import { Translate, formatSize, groupByStore, money } from './format';

/** Plain-text shopping list for the clipboard, grouped by store. */
export function shoppingListText(
  response: GenerateResponse,
  language: Language,
  t: Translate
): string {
  const lines: string[] = [];
  for (const [store, items] of groupByStore(response.items)) {
    lines.push(`${store} — €${money(response.subtotals_by_store[store] ?? 0)}`);
    for (const item of items) {
      const amount = `${item.packs} × ${formatSize(item.pack_size, item.unit, language, t)}`;
      lines.push(`- ${item.name}, ${amount}: €${money(item.line_total)}`);
    }
    lines.push('');
  }
  lines.push(`${t('total')}: €${money(response.total)} / €${money(response.budget)}`);
  return lines.join('\n');
}
