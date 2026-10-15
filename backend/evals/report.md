# Offline eval report

20261015T235325Z · model `gpt-4o-mini` · catalog `at-2026-10-15` · 20 runs (20 cases × 1) · **PASS**

| Metric | Value |
|---|---|
| Valid output rate | 100% |
| First-attempt acceptance, shopping / menu | 100% / 82% |
| Repair rate, shopping / menu | 0% / 18% |
| Budget adherence (must be 100%) | 100% |
| Diet violations (must be 0) | 0 |
| kcal in range (menu) | 91% |
| Runs trimmed to budget | 2 |
| Menus with scaled portions | 9 |
| Latency p50 / p95 | 4.3 s / 12.1 s |
| Avg cost per request | $0.0011 |
| Rejected before the LLM (not enough products, unknown store) | 0 |

## Cases

| Case | Run | Status | Attempts | Dropped | Scaled | Trimmed | Total / budget (€) | €/1000 kcal | kcal/person/day | Diet violations | Latency (s) | Tokens in/out | Out tokens (max attempt) | Attempts (out tokens, finish, s) | Cost ($) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| shop-en-both-2p-50 | 1 | ok | 1 | 14 |  |  | 17.57 / 50.00 | 1.27 | 985 (purchased) |  | 2.5 | 3939/205 | 205 | 205 stop 2.5 | 0.0007 |
| shop-de-billa-1p-30 | 1 | ok | 1 | 8 |  |  | 14.24 / 30.00 | 1.15 | 1771 (purchased) |  | 2.4 | 2659/200 | 200 | 200 stop 2.4 | 0.0005 |
| shop-uk-hofer-3p-80 | 1 | ok | 1 | 6 |  |  | 39.40 / 80.00 | 1.80 | 1042 (purchased) |  | 1.3 | 1943/128 | 128 | 128 stop 1.3 | 0.0004 |
| shop-en-both-4p-120-vegetarian | 1 | ok | 1 | 10 |  |  | 33.41 / 120.00 | 0.98 | 1213 (purchased) |  | 2.0 | 3160/174 | 174 | 174 stop 2.0 | 0.0006 |
| shop-de-billa-2p-60-vegan | 1 | ok | 1 | 4 |  |  | 28.00 / 60.00 | 1.44 | 1387 (purchased) |  | 1.9 | 1964/185 | 185 | 185 stop 1.9 | 0.0004 |
| shop-uk-both-5p-150-gluten-free | 1 | ok | 1 | 9 |  |  | 42.12 / 150.00 | 1.16 | 1037 (purchased) |  | 2.1 | 3248/194 | 194 | 194 stop 2.1 | 0.0006 |
| shop-en-hofer-2p-40-lactose-free | 1 | ok | 1 | 1 |  |  | 26.77 / 40.00 | 2.06 | 930 (purchased) |  | 1.2 | 1128/94 | 94 | 94 stop 1.2 | 0.0002 |
| shop-en-both-3p-100-gf-lf | 1 | ok | 1 | 6 |  |  | 25.66 / 100.00 | 1.27 | 962 (purchased) |  | 2.3 | 2365/193 | 193 | 193 stop 2.3 | 0.0005 |
| tight-shop-en-both-1p-15 | 1 | ok | 1 | 14 |  |  | 11.16 / 15.00 | 0.92 | 1727 (purchased) |  | 1.7 | 3939/135 | 135 | 135 stop 1.7 | 0.0007 |
| menu-en-both-2p-1d-25 | 1 | ok | 1 |  |  |  | 22.32 / 25.00 | 1.70 | 1896 (menu) |  | 4.7 | 5843/685 | 685 | 685 stop 4.7 | 0.0013 |
| menu-de-both-2p-3d-50 | 1 | ok | 1 |  | yes |  | 41.82 / 50.00 | 2.13 | 1680 (menu) |  | 5.8 | 5971/814 | 814 | 814 stop 5.8 | 0.0014 |
| menu-uk-billa-3p-3d-60 | 1 | ok | 1 | 8 |  |  | 38.44 / 60.00 | 1.69 | 1619 (menu) |  | 5.7 | 3499/824 | 824 | 824 stop 5.7 | 0.0010 |
| menu-en-both-4p-7d-150 | 1 | ok | 1 | 14 | yes |  | 110.85 / 150.00 | 1.89 | 1677 (menu) |  | 12.1 | 4972/1749 | 1749 | 1749 stop 12.1 | 0.0018 |
| menu-de-hofer-2p-1d-20 | 1 | ok | 1 |  | yes |  | 11.72 / 20.00 | 1.92 | 1674 (menu) |  | 4.0 | 3027/524 | 524 | 524 stop 4.0 | 0.0008 |
| menu-uk-both-1p-7d-60-vegetarian | 1 | ok | 1 |  | yes |  | 47.76 / 60.00 | 2.09 | 1680 (menu) |  | 12.0 | 4904/1864 | 1864 | 1864 stop 12.0 | 0.0019 |
| menu-en-billa-2p-3d-45-vegan | 1 | ok | 1 |  | yes |  | 36.93 / 45.00 | 1.65 | 1664 (menu) |  | 6.0 | 2779/839 | 839 | 839 stop 6.0 | 0.0009 |
| menu-de-both-3p-3d-70-gluten-free | 1 | ok | 1 |  | yes |  | 62.99 / 70.00 | 2.44 | 1702 (menu) |  | 5.4 | 4535/778 | 778 | 778 stop 5.4 | 0.0011 |
| menu-uk-both-2p-3d-50-lactose-free | 1 | ok | 2 |  | yes | 1 | 49.20 / 50.00 | 3.23 | 1667 (menu) |  | 11.7 | 9539/1725 | 863 | 862 stop 6.0; 863 stop 5.7 | 0.0025 |
| menu-de-billa-2p-7d-100-veg-lf | 1 | ok | 1 |  | yes |  | 58.09 / 100.00 | 1.90 | 1689 (menu) |  | 12.9 | 2840/2010 | 2010 | 2010 stop 12.9 | 0.0016 |
| tight-menu-en-both-5p-3d-40 | 1 | ok | 2 | 14 | yes | 8 | 38.92 / 40.00 | 1.33 | 1542 (menu) ⚠ |  | 11.1 | 10845/1559 | 780 | 779 stop 5.8; 780 stop 5.3 | 0.0026 |

Cost uses {'gpt-4o-mini': (0.15, 0.6)} USD per 1M tokens (input, output); see `evals/run.py`. kcal basis: `menu` = what the portions provide, `purchased` = all bought packs. €/1000 kcal = final total per 1000 purchased kcal. Dropped = food candidates left out because the budget was tight.
