import type { TranslationKey } from '../../translations';
import type { GenerateResponse } from '../../types';
import { UNIT_KEYS } from '../../constants';
import { groupByStore, money } from './format';

type Translate = (key: TranslationKey, vars?: Record<string, string | number>) => string;

/** Plain-text shopping list for the clipboard, grouped by store. */
export function shoppingListText(response: GenerateResponse, t: Translate): string {
  const lines: string[] = [];
  for (const [store, items] of groupByStore(response.items)) {
    lines.push(`${store} — €${money(response.subtotals_by_store[store] ?? 0)}`);
    for (const item of items) {
      const amount = `${item.packs} × ${item.pack_size} ${t(UNIT_KEYS[item.unit])}`;
      lines.push(`- ${item.name}, ${amount}: €${money(item.line_total)}`);
    }
    lines.push('');
  }
  lines.push(`${t('total')}: €${money(response.total)} / €${money(response.budget)}`);
  return lines.join('\n');
}
