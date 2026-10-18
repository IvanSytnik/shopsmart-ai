# Offline eval report

20261018T221443Z · model `gpt-4o-mini` · catalog `at-2026-10-15` · 20 runs (20 cases × 1) · **PASS**

Raw results, with the LLM's lines and the final basket per run: [results/20261018T221443Z.json](results/20261018T221443Z.json)

| Metric | Value |
|---|---|
| Valid output rate | 100% |
| First-attempt acceptance, shopping / menu | 100% / 82% |
| Repair rate, shopping / menu | 0% / 18% |
| Budget adherence (must be 100%) | 100% |
| Diet violations (must be 0) | 0 |
| kcal in range (menu) | 91% |
| kcal in range (shopping, purchased) | 89% |
| Shopping lists topped up for kcal | 5 |
| Runs trimmed to budget | 3 |
| Menus with scaled portions | 10 |
| Latency p50 / p95 | 4.1 s / 15.4 s |
| Avg cost per request | $0.0011 |
| Rejected before the LLM (not enough products, unknown store) | 0 |

## Cases

| Case | Run | Status | Attempts | Dropped | Scaled | Trimmed | Total / budget (€) | €/1000 kcal | kcal/person/day | Diet violations | Latency (s) | Tokens in/out | Out tokens (max attempt) | Attempts (out tokens, finish, s) | Cost ($) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| shop-en-both-2p-50 | 1 | ok | 1 | 14 |  |  | 26.44 / 50.00 | 1.11 | 1696 (purchased) |  | 2.5 | 3939/188 | 188 | 188 stop 2.5 | 0.0007 |
| shop-de-billa-1p-30 | 1 | ok | 1 | 8 |  |  | 15.96 / 30.00 | 1.30 | 1750 (purchased) |  | 2.6 | 2659/162 | 162 | 162 stop 2.6 | 0.0005 |
| shop-uk-hofer-3p-80 | 1 | ok | 1 | 6 |  |  | 52.64 / 80.00 | 1.51 | 1662 (purchased) |  | 2.6 | 1943/151 | 151 | 151 stop 2.6 | 0.0004 |
| shop-en-both-4p-120-vegetarian | 1 | ok | 1 | 10 |  |  | 37.27 / 120.00 | 0.83 | 1604 (purchased) |  | 3.1 | 3160/228 | 228 | 228 stop 3.0 | 0.0006 |
| shop-de-billa-2p-60-vegan | 1 | ok | 1 | 4 |  |  | 22.85 / 60.00 | 1.01 | 1617 (purchased) |  | 2.5 | 1964/160 | 160 | 160 stop 2.5 | 0.0004 |
| shop-uk-both-5p-150-gluten-free | 1 | ok | 1 | 9 |  |  | 66.13 / 150.00 | 1.15 | 1647 (purchased) |  | 2.5 | 3248/192 | 192 | 192 stop 2.5 | 0.0006 |
| shop-en-hofer-2p-40-lactose-free | 1 | ok | 1 | 4 |  |  | 30.23 / 40.00 | 1.35 | 1601 (purchased) |  | 2.0 | 1356/132 | 132 | 132 stop 2.0 | 0.0003 |
| shop-en-both-3p-100-gf-lf | 1 | ok | 1 | 6 |  |  | 43.22 / 100.00 | 1.20 | 1717 (purchased) |  | 3.0 | 2365/227 | 227 | 227 stop 3.0 | 0.0005 |
| tight-shop-en-both-1p-15 | 1 | ok | 1 | 14 |  | 1 | 14.86 / 15.00 | 1.49 | 1427 (purchased) ⚠ |  | 2.0 | 3939/152 | 152 | 152 stop 1.9 | 0.0007 |
| menu-en-both-2p-1d-25 | 1 | ok | 1 |  |  |  | 16.20 / 25.00 | 1.71 | 1853 (menu) |  | 5.1 | 5843/640 | 640 | 640 stop 5.1 | 0.0013 |
| menu-de-both-2p-3d-50 | 1 | ok | 1 |  | yes |  | 49.02 / 50.00 | 2.23 | 1669 (menu) |  | 7.0 | 5971/785 | 785 | 785 stop 7.0 | 0.0014 |
| menu-uk-billa-3p-3d-60 | 1 | ok | 1 | 8 | yes |  | 41.76 / 60.00 | 1.77 | 1666 (menu) |  | 7.3 | 3499/903 | 903 | 903 stop 7.3 | 0.0011 |
| menu-en-both-4p-7d-150 | 1 | ok | 1 | 14 | yes |  | 109.79 / 150.00 | 2.03 | 1690 (menu) |  | 15.2 | 4972/1791 | 1791 | 1791 stop 15.2 | 0.0018 |
| menu-de-hofer-2p-1d-20 | 1 | ok | 1 |  | yes |  | 12.20 / 20.00 | 1.70 | 1688 (menu) |  | 2.7 | 3027/236 | 236 | 236 stop 2.7 | 0.0006 |
| menu-uk-both-1p-7d-60-vegetarian | 1 | ok | 1 |  | yes |  | 47.89 / 60.00 | 1.97 | 1696 (menu) |  | 15.6 | 4904/2055 | 2055 | 2055 stop 15.5 | 0.0020 |
| menu-en-billa-2p-3d-45-vegan | 1 | ok | 1 |  | yes |  | 37.21 / 45.00 | 1.88 | 1685 (menu) |  | 8.0 | 2779/869 | 869 | 869 stop 8.0 | 0.0009 |
| menu-de-both-3p-3d-70-gluten-free | 1 | ok | 1 |  | yes |  | 59.60 / 70.00 | 2.57 | 1689 (menu) |  | 6.2 | 4535/815 | 815 | 815 stop 6.2 | 0.0012 |
| menu-uk-both-2p-3d-50-lactose-free | 1 | ok | 2 |  | yes | 2 | 48.55 / 50.00 | 2.51 | 1669 (menu) |  | 15.4 | 10895/1868 | 934 | 934 stop 8.2; 934 stop 7.2 | 0.0028 |
| menu-de-billa-2p-7d-100-veg-lf | 1 | ok | 1 |  | yes |  | 51.74 / 100.00 | 1.72 | 1690 (menu) |  | 13.2 | 2976/1863 | 1863 | 1863 stop 13.2 | 0.0016 |
| tight-menu-en-both-5p-3d-40 | 1 | ok | 2 | 14 | yes | 6 | 39.34 / 40.00 | 1.43 | 1468 (menu) ⚠ |  | 14.4 | 10787/1451 | 726 | 726 stop 7.3; 725 stop 7.2 | 0.0025 |

Cost uses {'gpt-4o-mini': (0.15, 0.6)} USD per 1M tokens (input, output); see `evals/run.py`. kcal basis: `menu` = what the portions provide, `purchased` = all bought packs. €/1000 kcal = final total per 1000 purchased kcal. Dropped = food candidates left out because the budget was tight.
