# frontdesk-frontend -- AI assistant guidelines

## STRICT RULES

- **NEVER commit without explicit user approval.**
- **NEVER push to remote** unless asked.
- **Always run before declaring a task done:**
  1. `npm run lint`
  2. `npm run typecheck`
  3. `npm test`

## Stack

React 19 + Mantine 9 + TypeScript + Vite + TanStack Query + React Router + Axios

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full architecture
document: folder structure, state management, auth flow, API client,
feature module pattern, routing, theme tokens, component patterns, testing
strategy, and conventions.

## Commands

```bash
npm run dev         # vite dev server on http://localhost:5173
npm run build       # tsc + vite build
npm run typecheck   # tsc --noEmit
npm run lint        # eslint
npm test            # vitest
```

## Backend contract

All backend calls go through `api` (the Axios instance in
`src/core/api/client.ts`). It auto-injects the Bearer token. On a 401,
the token is cleared and `RequireAuth` redirects to `/login`. Types mirror
backend snake_case JSON; no codegen.
