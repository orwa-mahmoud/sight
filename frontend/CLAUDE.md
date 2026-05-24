# frontdesk-frontend — AI assistant guidelines

## STRICT RULES

- **NEVER commit without explicit user approval.**
- **NEVER push to remote** unless asked.
- **Always run before declaring a task done:**
  1. `npm run lint`
  2. `npm run typecheck`
  3. `npm test`

## Stack

React 19 · Mantine 9 · TypeScript · Vite · TanStack Query · React Router v6 · Axios

## Layout

```text
src/
├── app/                       # composition root
│   ├── Providers.tsx          # Mantine, QueryClient, Router, Auth
│   ├── router.tsx             # route table
│   └── theme.ts               # brand palette (coral primary, slate accent)
├── auth/                      # auth feature
│   ├── AuthContext.tsx        # provider + useAuth hook
│   ├── api.ts                 # /api/v1/auth/* wrappers
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   └── types.ts
├── core/
│   └── api/
│       └── client.ts          # axios instance + token storage + 401 handling
├── features/                  # one folder per feature
│   ├── conversations/
│   ├── documents/
│   ├── escalations/           # the differentiating page (Inbox)
│   └── llm-usage/
└── shared/
    └── components/
        ├── AppShell.tsx       # header + sidebar
        └── RequireAuth.tsx    # route guard
```

## Conventions

- **One feature = one folder.** Each feature owns its `api.ts`, `types.ts`,
  and the page components. Avoid cross-feature imports.
- **State**: server state lives in TanStack Query; auth state in the
  React context. Avoid Redux / Zustand for v1.
- **Types**: match backend snake_case JSON shapes in interfaces. There is
  no codegen; keep types in sync by hand.
- **Brand color**: coral primary (`coral.6`) on light, `coral.5` on dark.
  Slate as accent for sidebar / nav active state.
- **Icons**: `@tabler/icons-react`, stroke 1.4–1.6.

## Backend contract

All backend calls go through `api` (the axios instance). It auto-injects
the bearer token. On a 401, the token is cleared — the router redirects
to `/login` on the next render via `RequireAuth`.

## Commands

```bash
npm run dev         # vite dev server on http://localhost:5173
npm run build       # tsc + vite build
npm run typecheck   # tsc --noEmit
npm run lint        # eslint
npm test            # vitest
```
