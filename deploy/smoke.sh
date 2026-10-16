#!/usr/bin/env bash
# Smoke test of a deployed stack. Makes one real /generate call (one OpenAI request,
# counts against RATE_LIMIT and DAILY_GENERATE_CAP).
#
#   ./deploy/smoke.sh https://shopsmart-api-xxxx.europe-west1.run.app https://shopsmart.sytnik.app
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
for path in "/" "/#/plan/x"; do
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
