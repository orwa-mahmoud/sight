# End-to-end tests (Playwright)

Browser tests for the critical path. Kept separate from the Vitest unit/component
tests and out of the per-PR CI gate (they need the full stack running). Run them
locally or via the manual `e2e` GitHub workflow.

## Run locally

```bash
# one-time: install the browser binaries
npx playwright install chromium

# against the dev server (start backend on :8000 and `npm run dev` first)
npm run e2e

# against the full docker-compose stack on :3000
PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run e2e

# full login flow (needs a real account)
E2E_EMAIL=owner@example.com E2E_PASSWORD=... npm run e2e
```

`npm run e2e:ui` opens the Playwright UI runner.

## What's covered

`smoke.spec.ts` — unauthenticated redirect to `/login`, the login form renders,
login → register navigation, and (when `E2E_EMAIL`/`E2E_PASSWORD` are set) a full
login reaching the dashboard. Grow it as flows stabilize: document upload, the
chat test, and answering an escalation.
