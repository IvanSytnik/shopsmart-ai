# Offline eval report

20261017T151510Z · model `gpt-4o-mini` · catalog `at-2026-10-15` · 20 runs (20 cases × 1) · **PASS**

| Metric | Value |
|---|---|
| Valid output rate | 100% |
| First-attempt acceptance, shopping / menu | 100% / 82% |
| Repair rate, shopping / menu | 0% / 18% |
| Budget adherence (must be 100%) | 100% |
| Diet violations (must be 0) | 0 |
| kcal in range (menu) | 91% |
| kcal in range (shopping, purchased) | 89% |
| Shopping lists topped up for kcal | 6 |
| Runs trimmed to budget | 1 |
| Menus with scaled portions | 9 |
| Latency p50 / p95 | 4.5 s / 14.2 s |
| Avg cost per request | $0.0011 |
| Rejected before the LLM (not enough products, unknown store) | 0 |

## Cases

| Case | Run | Status | Attempts | Dropped | Scaled | Trimmed | Total / budget (€) | €/1000 kcal | kcal/person/day | Diet violations | Latency (s) | Tokens in/out | Out tokens (max attempt) | Attempts (out tokens, finish, s) | Cost ($) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| shop-en-both-2p-50 | 1 | ok | 1 | 14 |  |  | 19.56 / 50.00 | 0.83 | 1686 (purchased) |  | 2.4 | 3939/194 | 194 | 194 stop 2.4 | 0.0007 |
| shop-de-billa-1p-30 | 1 | ok | 1 | 8 |  |  | 17.27 / 30.00 | 1.38 | 1789 (purchased) |  | 1.9 | 2659/196 | 196 | 196 stop 1.9 | 0.0005 |
| shop-uk-hofer-3p-80 | 1 | ok | 1 | 6 |  |  | 45.77 / 80.00 | 1.35 | 1609 (purchased) |  | 1.7 | 1943/114 | 114 | 114 stop 1.7 | 0.0004 |
| shop-en-both-4p-120-vegetarian | 1 | ok | 1 | 10 |  |  | 38.27 / 120.00 | 0.85 | 1601 (purchased) |  | 2.0 | 3160/208 | 208 | 208 stop 2.0 | 0.0006 |
| shop-de-billa-2p-60-vegan | 1 | ok | 1 | 4 |  |  | 22.64 / 60.00 | 0.94 | 1716 (purchased) |  | 2.5 | 1964/197 | 197 | 197 stop 2.5 | 0.0004 |
| shop-uk-both-5p-150-gluten-free | 1 | ok | 1 | 9 |  |  | 61.94 / 150.00 | 0.97 | 1832 (purchased) |  | 2.4 | 3248/230 | 230 | 230 stop 2.4 | 0.0006 |
| shop-en-hofer-2p-40-lactose-free | 1 | ok | 1 | 1 |  |  | 39.74 / 40.00 | 2.37 | 1200 (purchased) ⚠ |  | 1.4 | 1128/112 | 112 | 112 stop 1.4 | 0.0002 |
| shop-en-both-3p-100-gf-lf | 1 | ok | 1 | 6 |  |  | 37.05 / 100.00 | 1.08 | 1631 (purchased) |  | 2.0 | 2365/210 | 210 | 210 stop 2.0 | 0.0005 |
| tight-shop-en-both-1p-15 | 1 | ok | 1 | 14 |  |  | 12.65 / 15.00 | 1.08 | 1671 (purchased) |  | 1.6 | 3939/152 | 152 | 152 stop 1.6 | 0.0007 |
| menu-en-both-2p-1d-25 | 1 | ok | 1 |  |  |  | 18.05 / 25.00 | 1.56 | 1692 (menu) |  | 4.7 | 5843/541 | 541 | 541 stop 4.6 | 0.0012 |
| menu-de-both-2p-3d-50 | 1 | ok | 1 |  | yes |  | 48.58 / 50.00 | 2.41 | 1683 (menu) |  | 6.8 | 5971/788 | 788 | 788 stop 6.8 | 0.0014 |
| menu-uk-billa-3p-3d-60 | 1 | ok | 1 | 8 | yes |  | 35.21 / 60.00 | 1.56 | 1679 (menu) |  | 7.0 | 3499/873 | 873 | 873 stop 7.0 | 0.0010 |
| menu-en-both-4p-7d-150 | 1 | ok | 1 | 14 | yes |  | 135.69 / 150.00 | 2.22 | 1684 (menu) |  | 12.3 | 4972/1710 | 1710 | 1710 stop 12.3 | 0.0018 |
| menu-de-hofer-2p-1d-20 | 1 | ok | 1 |  | yes |  | 13.52 / 20.00 | 1.73 | 1707 (menu) |  | 4.3 | 3027/539 | 539 | 539 stop 4.3 | 0.0008 |
| menu-uk-both-1p-7d-60-vegetarian | 1 | ok | 1 |  | yes |  | 54.14 / 60.00 | 1.86 | 1681 (menu) |  | 14.2 | 4904/2163 | 2163 | 2163 stop 14.1 | 0.0020 |
| menu-en-billa-2p-3d-45-vegan | 1 | ok | 1 |  | yes |  | 33.71 / 45.00 | 1.58 | 1675 (menu) |  | 6.9 | 2779/842 | 842 | 842 stop 6.9 | 0.0009 |
| menu-de-both-3p-3d-70-gluten-free | 1 | ok | 1 |  | yes |  | 67.78 / 70.00 | 2.91 | 1682 (menu) |  | 6.5 | 4535/783 | 783 | 783 stop 6.5 | 0.0012 |
| menu-uk-both-2p-3d-50-lactose-free | 1 | ok | 2 |  |  |  | 47.45 / 50.00 | 2.58 | 1642 (menu) |  | 14.1 | 9642/1931 | 966 | 965 stop 7.1; 966 stop 7.0 | 0.0026 |
| menu-de-billa-2p-7d-100-veg-lf | 1 | ok | 1 |  | yes |  | 64.55 / 100.00 | 2.05 | 1691 (menu) |  | 14.5 | 2840/1815 | 1815 | 1815 stop 14.5 | 0.0015 |
| tight-menu-en-both-5p-3d-40 | 1 | ok | 2 | 14 | yes | 9 | 39.71 / 40.00 | 1.49 | 1389 (menu) ⚠ |  | 12.8 | 10837/1541 | 772 | 772 stop 6.1; 769 stop 6.7 | 0.0026 |

Cost uses {'gpt-4o-mini': (0.15, 0.6)} USD per 1M tokens (input, output); see `evals/run.py`. kcal basis: `menu` = what the portions provide, `purchased` = all bought packs. €/1000 kcal = final total per 1000 purchased kcal. Dropped = food candidates left out because the budget was tight.
