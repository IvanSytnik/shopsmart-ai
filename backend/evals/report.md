# Offline eval report

20261015T141547Z · model `gpt-4o-mini` · catalog `at-2026-10-15` · 20 runs (20 cases × 1) · **PASS**

| Metric | Value |
|---|---|
| Valid output rate | 100% |
| First-attempt acceptance, shopping / menu | 67% / 55% |
| Repair rate, shopping / menu | 33% / 46% |
| Budget adherence (must be 100%) | 100% |
| Diet violations (must be 0) | 0 |
| kcal in range (menu) | 55% |
| Runs trimmed to budget | 7 |
| Menus with scaled portions | 9 |
| Latency p50 / p95 | 7.5 s / 21.2 s |
| Avg cost per request | $0.0014 |
| Rejected before the LLM (not enough products, unknown store) | 0 |

## Cases

| Case | Run | Status | Attempts | Scaled | Trimmed | Total / budget (€) | kcal/person/day | Diet violations | Latency (s) | Tokens in/out | Cost ($) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| shop-en-both-2p-50 | 1 | ok | 1 |  |  | 33.48 / 50.00 | 966 (purchased) |  | 5.3 | 3877/248 | 0.0007 |
| shop-de-billa-1p-30 | 1 | ok | 2 |  | 2 | 29.10 / 30.00 | 1475 (purchased) |  | 7.9 | 5485/549 | 0.0012 |
| shop-uk-hofer-3p-80 | 1 | ok | 1 |  |  | 45.96 / 80.00 | 847 (purchased) |  | 2.7 | 1915/230 | 0.0004 |
| shop-en-both-4p-120-vegetarian | 1 | ok | 1 |  |  | 53.18 / 120.00 | 838 (purchased) |  | 4.3 | 3053/342 | 0.0007 |
| shop-de-billa-2p-60-vegan | 1 | ok | 1 |  |  | 35.61 / 60.00 | 1116 (purchased) |  | 7.0 | 1816/211 | 0.0004 |
| shop-uk-both-5p-150-gluten-free | 1 | ok | 1 |  |  | 85.92 / 150.00 | 768 (purchased) |  | 4.2 | 3168/421 | 0.0007 |
| shop-en-hofer-2p-40-lactose-free | 1 | ok | 2 |  |  | 37.28 / 40.00 | 774 (purchased) |  | 4.7 | 2164/327 | 0.0005 |
| shop-en-both-3p-100-gf-lf | 1 | ok | 1 |  |  | 50.78 / 100.00 | 908 (purchased) |  | 3.9 | 2226/274 | 0.0005 |
| tight-shop-en-both-1p-15 | 1 | ok | 2 |  | 1 | 11.67 / 15.00 | 875 (purchased) |  | 5.3 | 8042/406 | 0.0014 |
| menu-en-both-2p-1d-25 | 1 | ok | 1 | yes |  | 14.82 / 25.00 | 1691 (menu) |  | 4.5 | 5048/390 | 0.0010 |
| menu-de-both-2p-3d-50 | 1 | ok | 1 |  |  | 49.39 / 50.00 | 1620 (menu) |  | 9.6 | 5176/900 | 0.0013 |
| menu-uk-billa-3p-3d-60 | 1 | ok | 2 | yes | 12 | 58.12 / 60.00 | 1426 (menu) ⚠ |  | 19.5 | 8329/2249 | 0.0026 |
| menu-en-both-4p-7d-150 | 1 | ok | 2 | yes | 6 | 149.24 / 150.00 | 1549 (menu) ⚠ |  | 40.7 | 12344/4173 | 0.0044 |
| menu-de-hofer-2p-1d-20 | 1 | ok | 1 |  |  | 15.06 / 20.00 | 1628 (menu) |  | 6.2 | 2646/670 | 0.0008 |
| menu-uk-both-1p-7d-60-vegetarian | 1 | ok | 1 | yes |  | 59.11 / 60.00 | 1681 (menu) |  | 20.2 | 4280/2306 | 0.0020 |
| menu-en-billa-2p-3d-45-vegan | 1 | ok | 1 | yes |  | 38.88 / 45.00 | 1682 (menu) |  | 8.3 | 2416/892 | 0.0009 |
| menu-de-both-3p-3d-70-gluten-free | 1 | ok | 2 | yes | 5 | 69.34 / 70.00 | 1523 (menu) ⚠ |  | 15.7 | 8896/1756 | 0.0024 |
| menu-uk-both-2p-3d-50-lactose-free | 1 | ok | 2 | yes | 3 | 49.27 / 50.00 | 1528 (menu) ⚠ |  | 18.5 | 8564/1936 | 0.0024 |
| menu-de-billa-2p-7d-100-veg-lf | 1 | ok | 1 | yes |  | 67.05 / 100.00 | 1668 (menu) |  | 18.6 | 2477/1996 | 0.0016 |
| tight-menu-en-both-5p-3d-40 | 1 | ok | 2 | yes | 16 | 39.68 / 40.00 | 1014 (menu) ⚠ |  | 14.7 | 11053/1641 | 0.0026 |

Cost uses {'gpt-4o-mini': (0.15, 0.6)} USD per 1M tokens (input, output); see `evals/run.py`. kcal basis: `menu` = what the portions provide, `purchased` = all bought packs.
