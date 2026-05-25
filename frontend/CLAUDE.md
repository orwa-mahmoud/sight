# Frontdesk Frontend — AI Assistant Guidelines

## STRICT RULES

- **NEVER commit without explicit user approval.**
- **NEVER push to remote** unless asked.
- **Always run before declaring a task done:**
  1. `npm run lint`
  2. `npm run typecheck`
  3. `npm test`

## Stack

React 19 + Mantine 9 + TypeScript 6 + Vite 8 + TanStack Query 5 + React Router 7 + Axios + @tabler/icons-react + Vitest

Architecture and reference docs:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) -- folder structure, state management, auth flow, API client, feature modules, routing, testing strategy.
- [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) -- color palette (coral + slate), component patterns, naming conventions, four-state rendering, mutation patterns, form patterns, icon usage, notifications, theme configuration.

## Folder Structure

```text
src/
+-- app/                    # Composition root
|   +-- Providers.tsx       # Mantine, Notifications, QueryClient, BrowserRouter, AuthProvider
|   +-- router.tsx          # Route table (AppRoutes component)
|   +-- theme.ts            # Mantine theme: coral + slate palettes, font stack, radius
|
+-- auth/                   # Authentication (infrastructure, not a feature)
|   +-- api.ts              # login(), register(), me()
|   +-- AuthContext.tsx      # AuthProvider -- token bootstrap, login/register/logout
|   +-- useAuth.ts          # useAuth() hook (throws if outside provider)
|   +-- LoginPage.tsx, RegisterPage.tsx
|
+-- core/api/client.ts      # Axios instance, token helpers, interceptors
|
+-- features/               # One folder per business feature
|   +-- escalations/        # Owner inbox (question cards, reply modal)
|   +-- conversations/      # AI conversation threads + daily summary
|   +-- documents/          # Knowledge base (RAG document management)
|   +-- llm-usage/          # Token + cost ledger
|   +-- settings/           # Tenant configuration (LLM, embedding, channels, bot)
|
+-- shared/components/      # AppShell (ProtectedShell), RequireAuth guard
+-- test/                   # setup.ts (polyfills), wrapper.tsx (TestWrapper)
```

## State Management

Two categories only. No Redux, no Zustand.

- **Server state -- TanStack Query:** Every API call uses `useQuery` or `useMutation`. QueryClient: `staleTime: 30_000`, `refetchOnWindowFocus: false`, `retry: 1`. Cache invalidation via `queryClient.invalidateQueries({ queryKey })`.
- **Auth state -- React Context:** `AuthContext` holds `user | null` + `loading`. Single source of truth for auth. Consumed via `useAuth()`.

## Auth Flow

- **Bootstrap:** AuthProvider mounts -> `getToken()` -> `authApi.me()` -> `setUser()`
- **Login:** form submit -> `authApi.login()` -> `setToken(access_token)` -> `loadCurrentUser()`
- **Logout:** `clearToken()` -> `setUser(null)` -> RequireAuth redirects to `/login`
- **401:** Axios response interceptor -> `clearToken()` -> RequireAuth redirects
- **Token:** `frontdesk_access_token` in localStorage

## API Client (`src/core/api/client.ts`)

Axios instance, `baseURL: VITE_API_URL` (default `http://localhost:8000`), timeout 30s. Request interceptor injects `Bearer <token>`. Response interceptor clears token on 401 (promise propagates to TanStack Query). Helpers: `getToken()`, `setToken(t)`, `clearToken()`.

## Feature Module Pattern

Each feature is a self-contained folder under `src/features/`:

```text
features/<name>/
+-- api.ts           # Typed API functions (calls Axios instance)
+-- types.ts         # TypeScript interfaces matching backend snake_case JSON
+-- <Name>Page.tsx   # Page component (useQuery/useMutation)
+-- *.test.tsx       # Co-located tests
```

**Rules:**
- One feature = one folder. Features own their API, types, and pages.
- No cross-feature imports. Features communicate through shared infrastructure only.
- Features with only a page (no dedicated API) inline fetch functions in the page file.

| Feature | Folder | Key pages |
| ------- | ------ | --------- |
| Escalations | `escalations/` | InboxPage |
| Conversations | `conversations/` | ConversationsPage, ChatTestPage |
| Documents | `documents/` | DocumentsPage |
| LLM Usage | `llm-usage/` | UsagePage |
| Settings | `settings/` | SettingsPage |

## Conventions

### Naming

- Page components: `PascalCase` + `Page` suffix (`InboxPage`, `SettingsPage`)
- API/Types files: `api.ts`, `types.ts` in feature folder
- Test files: same name + `.test.tsx` / `.test.ts`
- Hooks: `camelCase` with `use` prefix
- **Named exports** only (`export function X`, not `export default`)
- `Readonly<Props>` on all component function signatures

### Icons

All icons from `@tabler/icons-react`. Standard size: 18 for inline/nav, 14 for badges/labels. Stroke: 1.4-1.6.

### Brand Colors

- Primary actions (buttons, links): `coral` (Mantine primary -- `#f76b22` light, `#f87330` dark)
- Accent/nav contrast: `slate`
- Success: `teal`
- Error: `red`
- Neutral/muted: `gray`, `dimmed`

### Imports

- Relative imports within same module (`./api`, `./types`)
- Path-based imports across modules (`../../core/api/client`)
- No path aliases configured

### Four-State Rendering

Every data-driven page handles exactly: Loading (`<Loader />`), Error (`<Alert color="red">`), Empty (`<Card>` with icon + guidance), Data (actual content).

### Mutations

- Inline `onSuccess/onError` with `notifications.show()` for most pages
- Success: `color: "teal"` -- Error: `color: "red"`
- Forms use `@mantine/form` with `useForm({ initialValues, validate })`

## Commands

```bash
npm run dev         # Vite dev server on http://localhost:5173
npm run build       # tsc + Vite production build
npm run typecheck   # tsc --noEmit
npm run lint        # ESLint
npm test            # Vitest
```

## Backend Contract

- Backend (FastAPI) uses **snake_case** JSON. Frontend types mirror this exactly. No codegen.
- All endpoints under `/api/v1/`. Feature API files use the shared Axios instance.
- When backend adds or renames a field, update the corresponding `types.ts` manually.

| Frontend feature | Backend endpoints |
| ---------------- | ----------------- |
| Auth | `POST /api/v1/auth/login`, `/register`, `GET /me` |
| Escalations | `GET /api/v1/questions`, `POST .../reply`, `.../close` |
| Conversations | `GET /api/v1/conversations`, `.../daily-summary` |
| Documents | `GET/POST/DELETE /api/v1/documents` |
| LLM Usage | `GET /api/v1/llm-usage/stats` |
| Chat | `POST /api/v1/chat` |
| Settings | `GET /api/v1/settings`, `PUT .../llm`, `.../embedding`, `.../whatsapp`, `.../telegram`, `.../bot` |
