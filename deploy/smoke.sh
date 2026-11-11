#!/usr/bin/env bash
# Smoke test of a deployed stack. Makes one real /generate call (one OpenAI request,
# counts against RATE_LIMIT and DAILY_GENERATE_CAP); /compare is computed from the catalog
# and uses neither.
#
#   ./deploy/smoke.sh https://shopsmart-api-xxxx.europe-west1.run.app https://shopsmart.sytnik-studio.com
#
# Needs curl and python3. Exits non-zero if any check fails.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <api_url> <frontend_url>" >&2
  exit 2
fi
api="${1%/}"
frontend="${2%/}"
origin="$(printf '%s' "$frontend" | sed -E 's#^([a-zA-Z]+://[^/]+).*#\1#')"

failures=0
pass() { echo "  ok   $1"; }
fail() {
  echo "  FAIL $1" >&2
  failures=$((failures + 1))
}

# Runs a Python check on the JSON on stdin; prints the error and returns 1 on failure.
json_check() {
  python3 -c "
import json, sys
data = json.load(sys.stdin)
$1
"
}

echo "API $api"

if body="$(curl -fsS --max-time 30 "$api/health")" &&
  printf '%s' "$body" | json_check '
assert data.get("status") == "healthy", data
assert data.get("catalog_version"), data
print("  catalog_version", data["catalog_version"])'; then
  pass "/health"
else
  fail "/health"
fi

if body="$(curl -fsS --max-time 30 "$api/api/catalog/meta")" &&
  printf '%s' "$body" | json_check '
stores = data["countries"]["AT"]
assert "Billa" in stores and "Hofer" in stores, stores'; then
  pass "/api/catalog/meta has Billa and Hofer"
else
  fail "/api/catalog/meta has Billa and Hofer"
fi

# Concepts sold by both Billa and Hofer (SHARED_CONCEPTS in backend/tests/test_catalog_at.py).
compare_concepts='"milk_whole", "butter", "cheese_gouda"'

if body="$(curl -fsS --max-time 30 "$api/api/catalog/concepts?country=AT")" &&
  printf '%s' "$body" | json_check "
assert data['country'] == 'AT', data['country']
concepts = {c['concept_id']: c for c in data['concepts']}
assert concepts, 'no concepts'
for concept_id in ($compare_concepts):
    stores = concepts[concept_id]['stores']
    assert {'Billa', 'Hofer'} <= set(stores), (concept_id, stores)
print('  %d concepts' % len(concepts))"; then
  pass "/api/catalog/concepts?country=AT"
else
  fail "/api/catalog/concepts?country=AT"
fi

request='{"country":"AT","stores":["Billa","Hofer"],"items":[{"concept_id":"milk_whole","quantity":2},{"concept_id":"butter","quantity":1},{"concept_id":"cheese_gouda","quantity":1}]}'
if body="$(curl -fsS --max-time 30 -H 'Content-Type: application/json' -H "Origin: $origin" \
  -d "$request" "$api/compare")" &&
  printf '%s' "$body" | json_check "
rankings = data['single_store_rankings']
assert sorted(s['store'] for s in rankings) == ['Billa', 'Hofer'], rankings
split = data['split_basket']
assert split['missing_concepts'] == [], split['missing_concepts']
# The split takes every item where it is cheapest: never above a store that has them all.
complete = [s['total_eur'] for s in rankings if not s['missing_concepts']]
assert 0 < split['total_eur'] <= min(complete, default=split['total_eur']), (split, complete)
strategy, store = data['recommended_strategy'], data['recommended_store']
assert strategy in ('single_store', 'split_basket'), strategy
assert (store == rankings[0]['store']) if strategy == 'single_store' else store is None, store
print('  %s %s, split EUR %.2f, best store EUR %.2f' % (
    strategy, store or '', split['total_eur'], rankings[0]['total_eur']))"; then
  pass "POST /compare (3 concepts, Billa+Hofer)"
else
  fail "POST /compare (3 concepts, Billa+Hofer)"
fi

request='{"country":"AT","supermarkets":["Billa","Hofer"],"budget":40,"family_size":2,"language":"en","mode":"shopping"}'
if body="$(curl -fsS --max-time 75 -H 'Content-Type: application/json' -H "Origin: $origin" \
  -d "$request" "$api/generate")" &&
  printf '%s' "$body" | json_check '
assert data["items"], "no items"
assert data["budget"] == 40, data["budget"]
assert data["total"] <= data["budget"], (data["total"], data["budget"])
print("  %d items, total EUR %.2f" % (len(data["items"]), data["total"]))'; then
  pass "POST /generate (Billa+Hofer, EUR 40, 2 people)"
else
  fail "POST /generate (Billa+Hofer, EUR 40, 2 people)"
fi

if headers="$(curl -sS --max-time 30 -o /dev/null -D - -X OPTIONS \
  -H "Origin: $origin" \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: content-type' \
  "$api/generate")" &&
  printf '%s' "$headers" | tr -d '\r' |
  grep -qix "access-control-allow-origin: $origin"; then
  pass "CORS preflight allows $origin"
else
  fail "CORS preflight allows $origin"
fi

echo "Frontend $frontend"

# The fragment is never sent to the server; this checks the same page is served for it.
for path in "/" "/#/plan/x" "/#/list/x"; do
  code=""
  if code="$(curl -sS --max-time 30 -o /dev/null -w '%{http_code}' "$frontend$path")" &&
    [[ "$code" == 200 ]]; then
    pass "GET $path -> 200"
  else
    fail "GET $path -> ${code:-error}"
  fi
done

if headers="$(curl -sS --max-time 30 -o /dev/null -D - "$frontend/")" &&
  printf '%s' "$headers" | tr -d '\r' | grep -qi '^x-content-type-options: nosniff'; then
  pass "X-Content-Type-Options: nosniff"
else
  fail "X-Content-Type-Options: nosniff"
fi

if [[ $failures -gt 0 ]]; then
  echo "$failures check(s) failed" >&2
  exit 1
fi
echo "All checks passed"
