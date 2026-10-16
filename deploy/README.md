# Deployment

Backend → **Google Cloud Run** (`europe-west1`, one instance), frontend → **Cloudflare Pages** (built from GitHub), at `https://shopsmart.sytnik.app`.

| Piece | Where | Config |
|---|---|---|
| API | Cloud Run service `shopsmart-api` | `deploy/deploy_backend.sh`; OpenAI key from Secret Manager (`openai-api-key`) |
| Frontend | Cloudflare Pages project, root `frontend` | `VITE_API_URL` at build time; `public/_redirects`, `public/_headers` (generated) |

Scripts (run from the repo root, all need `bash`):

| Script | Does |
|---|---|
| `deploy/deploy_backend.sh` | builds `backend/` with Cloud Build, deploys it, curls `/health` |
| `deploy/update_cors.sh` | changes only `CORS_ORIGINS` on the running service |
| `deploy/smoke.sh <api_url> <frontend_url>` | end-to-end checks; makes **one real OpenAI call** |

The shell examples below set these first:

```bash
export PROJECT_ID=shopsmart-ai-123456   # your GCP project id
export REGION=europe-west1
export SERVICE=shopsmart-api
```

## 1. OpenAI: project key and spend limit

1. <https://platform.openai.com> → project picker (top left) → **Create project**, name it `shopsmart`.
2. In that project: **Settings → Limits**
   - **Model usage**: allow only `gpt-4o-mini` (the model in `OPENAI_MODEL`), so a leaked key can't call expensive models.
   - **Budget**: set a monthly budget (e.g. $5) and an alert threshold (e.g. 80 %).
3. **API keys → Create new secret key**, owned by the `shopsmart` project, permissions *All* (or *Restricted* with write access to *Model capabilities*). Copy it; it's shown once. Don't paste it into a file or a command line.
4. Organization **Settings → Billing**: use prepaid credits with **auto recharge off**. That's the hard ceiling: the API stops when the credits are used up, whatever the budget settings say.

## 2. GCP project, billing and a €5 budget alert

1. <https://console.cloud.google.com/projectcreate> → create a project (e.g. `shopsmart-ai`); note its **project id**.
2. **Billing** → link the project to a billing account (a card is required even for the free tier).
3. **Billing → Budgets & alerts → Create budget**
   - Scope: this project; all services.
   - Amount: **€5**, monthly.
   - Thresholds: 50 %, 90 %, 100 % actual, 100 % forecasted; email billing admins.

   A budget only sends emails, it doesn't stop spending. The real limits are `--max-instances 1`, `RATE_LIMIT`, `DAILY_GENERATE_CAP` and the OpenAI credit balance.

## 3. Install gcloud and log in

```bash
brew install --cask google-cloud-sdk     # macOS; other OS: https://cloud.google.com/sdk/docs/install
gcloud init                               # or: gcloud auth login
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"
```

## 4. Enable the APIs

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --project "$PROJECT_ID"
```

## 5. Store the OpenAI key in Secret Manager

The key goes in through stdin, so it never appears in a command line or shell history.

```bash
# Option A (macOS): copy the key to the clipboard, then
pbpaste | tr -d '[:space:]' | gcloud secrets create openai-api-key \
  --project "$PROJECT_ID" --replication-policy automatic --data-file=-

# Option B: type/paste it at a hidden prompt (bash or zsh)
read -rs OPENAI_KEY        # paste the key, press Enter; nothing is echoed
printf '%s' "$OPENAI_KEY" | gcloud secrets create openai-api-key \
  --project "$PROJECT_ID" --replication-policy automatic --data-file=-
unset OPENAI_KEY
```

Check that a version exists (doesn't print the value): `gcloud secrets versions list openai-api-key --project "$PROJECT_ID"`.

## 6. Let the Cloud Run service account read the secret

Cloud Run runs as the Compute Engine default service account unless told otherwise:

```bash
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format 'value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding openai-api-key \
  --project "$PROJECT_ID" \
  --member "serviceAccount:${RUNTIME_SA}" \
  --role roles/secretmanager.secretAccessor
```

## 7. First backend deploy

The frontend URL doesn't exist yet; start with the planned domain and fix it in step 10.

```bash
CORS_ORIGINS=https://shopsmart.sytnik.app ./deploy/deploy_backend.sh
```

- The first `--source` deploy asks to create the Artifact Registry repo `cloud-run-source-deploy` in the region: answer **Y**.
- The script ends with `Service URL: https://shopsmart-api-….europe-west1.run.app` and the `/health` JSON. Keep that URL; it's `VITE_API_URL` below.
- If the build fails with a permission error for the build service account, grant it the builder role and run the script again:

  ```bash
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member "serviceAccount:${RUNTIME_SA}" --role roles/run.builder
  ```

What the script sets: `ENVIRONMENT=production` (no `/docs`), `RATE_LIMIT=10/minute`, `DAILY_GENERATE_CAP=200`, `FORWARDED_ALLOW_IPS=*` (the container is reachable only through Google's front end, so the client IP in `X-Forwarded-For` is trusted for the rate limit), scale 0–1 instances, 20 concurrent requests, 512 MiB, 1 vCPU, 60 s request timeout. `--max-instances 1` is on purpose: the rate limit and daily cap are counted in memory per instance.

## 8. Cloudflare Pages

1. <https://dash.cloudflare.com> → **Workers & Pages → Create → Pages → Connect to Git** → pick the GitHub repo.
2. Build settings:

   | Setting | Value |
   |---|---|
   | Production branch | `main` |
   | Framework preset | None |
   | Root directory | `frontend` |
   | Build command | `npm ci && npm run build` |
   | Build output directory | `dist` |

3. **Environment variables** (Production, and Preview if you use previews):

   | Name | Value |
   |---|---|
   | `VITE_API_URL` | the Cloud Run service URL from step 7, no trailing slash |
   | `NODE_VERSION` | `20` |

4. **Save and Deploy.** The site is at `https://<project>.pages.dev`.

`npm run build` first runs `scripts/gen-headers.mjs`, which writes `public/_headers` from `security-headers.conf` (the same headers nginx sends in Docker) with the CSP `connect-src` set to the origin of `VITE_API_URL`. `VITE_API_URL` is baked in at build time: after changing it, **retry the deployment** (Deployments → ⋯ → Retry) so a new build picks it up.

`public/_redirects` (`/* /index.html 200`) serves the app for any path. Shared plans use the URL fragment (`/#/plan/…`), which never reaches the server, so this is only a fallback for mistyped paths.

## 9. Custom domain `shopsmart.sytnik.app`

Pages project → **Custom domains → Set up a custom domain** → `shopsmart.sytnik.app`.

- If `sytnik.app` uses Cloudflare DNS, Cloudflare adds the record itself.
- Otherwise add at your DNS provider: `CNAME shopsmart → <project>.pages.dev`, then wait for the domain to show **Active** (certificate issued; `.app` is HTTPS-only, so it won't load before that).

## 10. Point CORS at the real origins

```bash
CORS_ORIGINS=https://shopsmart.sytnik.app,https://<project>.pages.dev ./deploy/update_cors.sh
```

Only exact origins work (no wildcards), so preview deployments (`https://<hash>.<project>.pages.dev`) can't call the API unless you add their origin too.

## 11. Smoke test

```bash
API_URL="$(gcloud run services describe "$SERVICE" --region "$REGION" --format 'value(status.url)')"
./deploy/smoke.sh "$API_URL" https://shopsmart.sytnik.app
```

Checks `/health` (status and `catalog_version`), `/api/catalog/meta` lists Billa and Hofer, one real shopping-list `/generate` (Billa + Hofer, €40, 2 people) stays within budget, the CORS preflight from the frontend origin is allowed, `/` and `/#/plan/x` return 200, and the frontend sends `X-Content-Type-Options: nosniff`. Exits non-zero if anything fails. Each run uses one OpenAI call and one unit of the daily cap.

## 12. Logs

```bash
gcloud run services logs read "$SERVICE" --region "$REGION" --limit 100
gcloud beta run services logs tail "$SERVICE" --region "$REGION"   # live; needs the beta component
```

Or Console → Cloud Run → `shopsmart-api` → **Logs** (filter by severity, e.g. `Daily /generate cap` warnings). Frontend build logs: Pages project → **Deployments** → a deployment → **View details**.

## 13. Rollback

Backend: list revisions and send all traffic to a previous one.

```bash
gcloud run revisions list --service "$SERVICE" --region "$REGION"
gcloud run services update-traffic "$SERVICE" --region "$REGION" \
  --to-revisions shopsmart-api-00003-abc=100
```

Traffic stays pinned to that revision until you send it back to the newest: `gcloud run services update-traffic "$SERVICE" --region "$REGION" --to-latest`.

Frontend: Pages project → **Deployments** → an earlier production deployment → ⋯ → **Rollback to this deployment**.

## Rotating the OpenAI key

Create the new key in the OpenAI project, then add it as a new secret version (stdin, as in step 5) and start a new revision so it's read:

```bash
pbpaste | tr -d '[:space:]' | gcloud secrets versions add openai-api-key --data-file=-
gcloud run services update "$SERVICE" --region "$REGION" \
  --update-secrets OPENAI_API_KEY=openai-api-key:latest
```

Then revoke the old key in OpenAI.
