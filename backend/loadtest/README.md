# Load testing

A [k6](https://k6.io) smoke/load harness for the Frontdesk API. These scripts
exist so capacity and latency under concurrency can be measured against a
**running** deployment — they are not run by CI and need a live target.

## Prerequisites

- Install k6: `brew install k6` (macOS) or see https://k6.io/docs/get-started/installation/
- A running API (local dev server, staging, etc.).

## Run

```bash
# Smoke (1 VU, quick sanity)
k6 run loadtest/k6_smoke.js

# Load: 50 virtual users for 2 minutes against staging
BASE_URL=https://staging.example.com VUS=50 DURATION=2m k6 run loadtest/k6_smoke.js
```

Environment variables:

| Var        | Default                 | Meaning                          |
| ---------- | ----------------------- | -------------------------------- |
| `BASE_URL` | `http://localhost:8000` | API base URL                     |
| `VUS`      | `1`                     | Concurrent virtual users         |
| `DURATION` | `30s`                   | Test duration                    |

## What it exercises

`k6_smoke.js` registers one owner in `setup()`, then every VU loops
authenticated reads (`/auth/me`, `/conversations`, `/documents`,
`/invitations`) — the hot, external-dependency-free paths (registration/login
are rate-limited, so they're kept out of the per-iteration loop). Thresholds
fail the run if p95 latency or the error rate exceed the budgets at the top of
the script; tune them to your SLOs.

> Note: the chat / RAG paths are intentionally **not** load-tested here because
> they call third-party LLM + embedding APIs (cost + rate limits). Add a
> separate, carefully-scoped scenario with test credentials if you need to
> profile those.
