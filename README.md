# NTARI Google Ads API

A FastAPI service that wraps the Google Ads API for managing NTARI's Ad Grants campaigns. Designed to be called from the NTARI Wix site and operated by Claude Code.

**Organization:** [Network Theory Applied Research Institute (NTARI)](https://ntari.org) — 501(c)(3) nonprofit, EIN 92-3047136

---

## Overview

This API manages Google Ad Grants campaigns for NTARI.org, enforcing Ad Grants compliance rules (5% CTR minimum, $2.00 CPC cap, Search-only campaigns, no single-word keywords) automatically at the API layer.

### Current Campaign Architecture (v7.0)

| Campaign | Ad Groups | Daily Budget | Purpose |
|---|---|---|---|
| EN_BlogContent_Search | 12 | $181 | Blog post & research content traffic |
| EN_Mission_Search | 3 | $82 | Brand awareness, registration, AI member benefits |
| EN_Support_Search | 1 | $33 | Donor acquisition |

**Geo targeting:** 52 Anglophone countries across all regions (US, UK, CA, AU, NZ, IE + South Asia, SE Asia, Africa, Caribbean, Oceania, Middle East).

---

## Stack

- **API:** FastAPI + Uvicorn (2 workers)
- **Auth:** Google Ads API v20 via `google-ads` Python SDK
- **Proxy:** Nginx reverse proxy
- **Tunnel:** Cloudflare Tunnel (public HTTPS endpoint)
- **Deployment:** Docker Compose (dev + prod configs)
- **Integration:** Wix backend module (`wix/googleAdsBackend.jsw`)

---

## API Endpoints

All routes are prefixed `/api/v1/customers/{customer_id}/` and require an `X-API-Key` header.

| Resource | Methods | Path |
|---|---|---|
| Campaigns | GET, POST, PATCH, DELETE | `/campaigns/` |
| Ad Groups | GET, POST, PATCH, DELETE | `/ad-groups/` |
| Keywords | POST, PATCH, DELETE | `/keywords/` |
| Responsive Search Ads | GET, POST, PATCH, DELETE | `/ads/` |
| Assets | POST | `/assets/` |
| Bidding Strategies | GET, POST, DELETE | `/bidding-strategies/` |
| Targeting | POST | `/targeting/geo`, `/targeting/language`, etc. |
| Batch Build | POST | `/batch/build-campaign` |

Health check: `GET /health`

---

## Setup

### Prerequisites

- Docker Desktop
- A Google Ads Developer token
- Google Ads OAuth2 credentials (refresh token)
- A Google Ad Grants account

### 1. Clone the repo

```bash
git clone https://github.com/NetworkTheoryAppliedResearchInstitute/googleadsapi.git
cd googleadsapi
```

### 2. Configure credentials

Copy the example files and fill in your values:

```bash
cp .env.example .env
cp google-ads.yaml.example google-ads.yaml
```

**`.env` required fields:**
```
GOOGLE_ADS_CUSTOMER_ID=your-10-digit-id
API_SECRET_KEY=your-strong-random-secret
ALLOWED_ORIGINS=https://www.ntari.org,https://ntari.org
```

**`google-ads.yaml` required fields:**
```yaml
developer_token: your-developer-token
client_id: your-oauth-client-id
client_secret: your-oauth-client-secret
refresh_token: your-refresh-token
use_proto_plus: True
```

To generate a refresh token:
```bash
python get_refresh_token.py
```

### 3. Start the stack

```bash
docker compose up -d
```

The API will be available at `http://localhost/api/v1`.

For production (with Cloudflare Tunnel):
```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Windows auto-start

`start.ps1` is scheduled via Windows Task Scheduler to launch the Docker stack on login. See the script for details.

---

## Campaign Management

### Build campaigns from scratch

`execute_plan.py` builds the full v7.0 campaign architecture via the batch API endpoint.

```bash
# Validate configs (no API calls)
python execute_plan.py --dry-run

# Build all 3 campaigns
python execute_plan.py

# Build a single campaign by index
python execute_plan.py --campaign 0
```

All campaigns are created **PAUSED** — review in Google Ads UI before enabling.

### Expand geo targeting

`add_geo_targets.py` adds geo targets to existing campaigns without rebuilding them.

```bash
python add_geo_targets.py --dry-run   # preview
python add_geo_targets.py             # apply
```

### Other scripts

| Script | Purpose |
|---|---|
| `add_negatives.py` | Creates shared negative keyword list and attaches to campaigns |
| `add_claude_benefit_ag.py` | Adds the Claude member benefit ad group to EN_Mission_Search |
| `get_refresh_token.py` | Generates an OAuth2 refresh token |

---

## Ad Grants Compliance

Enforced automatically at the API layer (`src/utils/ad_grants_compliance.py`):

- $2.00 max CPC for Manual CPC bidding
- Search campaigns only (no Display, Video, Shopping)
- No Display Network targeting
- No single-word keywords
- Advisory checks: 5% CTR minimum, Quality Score >= 3

---

## Wix Integration

`wix/googleAdsBackend.jsw` provides a Wix backend module that calls this API from the NTARI Wix site. `wix/http-functions.js` exposes HTTP trigger endpoints.

---

## Project Reference

- **Manual:** P2-002 Implementation Manual v7.0 (internal)
- **Ad Grants policy:** [Google Ad Grants Program Policies](https://support.google.com/grants/answer/1657310)
- **Google Ads API docs:** [developers.google.com/google-ads/api](https://developers.google.com/google-ads/api/docs/start)
