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

## Internationalization (EN / AR / RTL)

- i18next + react-i18next; resources bundled in `src/shared/i18n/locales/{en,ar}/common.json`
  (default namespace `common`). Init is synchronous so `t()` works in app + tests.
- Use `useTranslation()` → `t("section.key")`. **Add a key to BOTH `en` and `ar`**
  when adding UI text — never hardcode user-facing strings.
- Direction: `DirectionGate` (in `app/Providers.tsx`) syncs `<html dir/lang>` and
  Mantine's `DirectionProvider` to the active language. Switcher: `LanguageSwitcher`.
- Dark mode: `ColorSchemeToggle` (Mantine color scheme; `defaultColorScheme="auto"`).
- Tests init i18n via `src/test/setup.ts` (imports `@shared/i18n`), so components
  render English by default.

## DataTable (`src/shared/components/datatable`)

Unified, mode-agnostic table. A page builds a **`TableSource`** with
`useFrontendData` (in-memory) or `useBackendData` (server-paginated infinite
query), then renders `<DataTable source columns rowKey ... />`. Features: sort,
debounced search, filter drawer + chips (generic `SelectFilter`/`TextFilter`
bound to `source.extra`), paged + infinite modes, responsive desktop/mobile,
URL-synced state, `RowAction`s (optional confirm modal), loading skeleton +
empty/error states, i18n, GSAP entrance stagger. Columns are `ColumnDef<TRow>`
(use `Cell`/`accessor`, `sortValue`, `mobileLabel`). See `DataTable.test.tsx`.

## Shared hooks / utils

- `useMutationWithNotification` — `useMutation` + success/error toasts + invalidation.
- `useDebounce`, `core/config.ts` (typed env), `utils/confirm` (Mantine modal).

## Auth Flow

Cookie-based. The backend sets an httpOnly `frontdesk_token` cookie on
login/register; the SPA never reads or stores the JWT (no localStorage = no XSS
token theft). `axios` is configured with `withCredentials: true` so the cookie
travels with every request.

- **Bootstrap:** AuthProvider mounts -> `authApi.me()` (cookie sent automatically) -> `setUser()`; a 401 just means "not logged in".
- **Login:** form submit -> `authApi.login()` (server sets cookie) -> `loadCurrentUser()`
- **Logout:** `setUser(null)` -> `authApi.logout()` (server clears cookie) -> RequireAuth redirects to `/login`
- **401:** Axios response interceptor -> registered unauthorized handler -> `setUser(null)` -> RequireAuth redirects

## API Client (`src/core/api/client.ts`)

Axios instance, `baseURL: VITE_API_URL ?? ""` (same-origin relative by default), `withCredentials: true`, timeout 30s. In dev the Vite server proxies `/api` + `/webhooks` to the backend; in Docker nginx reverse-proxies them — so requests are same-origin everywhere and the auth cookie stays first-party. Response interceptor invokes a registered handler on 401 (promise still propagates to TanStack Query). Helper: `setUnauthorizedHandler(fn)`.

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

| Feature       | Folder           | Key pages                       |
| ------------- | ---------------- | ------------------------------- |
| Escalations   | `escalations/`   | InboxPage                       |
| Conversations | `conversations/` | ConversationsPage, ChatTestPage |
| Documents     | `documents/`     | DocumentsPage                   |
| LLM Usage     | `llm-usage/`     | UsagePage                       |
| Settings      | `settings/`      | SettingsPage                    |

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

- **Relative imports within the same module** (`./api`, `./types`)
- **Alias imports across modules** — `@app/* @auth/* @core/* @features/* @shared/* @test/*`
  (e.g. `@core/api/client`, `@shared/components/AppShell`). Never `../../` across
  modules. Aliases are configured in `tsconfig.app.json` (paths) and mirrored in
  `vite.config.ts` + `vitest.config.ts` (resolve.alias) — keep all three in sync.

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

| Frontend feature | Backend endpoints                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| Auth             | `POST /api/v1/auth/login`, `/register`, `GET /me`                                                 |
| Escalations      | `GET /api/v1/questions`, `POST .../reply`, `.../close`                                            |
| Conversations    | `GET /api/v1/conversations`, `.../daily-summary`                                                  |
| Documents        | `GET/POST/DELETE /api/v1/documents`                                                               |
| LLM Usage        | `GET /api/v1/llm-usage/stats`                                                                     |
| Chat             | `POST /api/v1/chat`                                                                               |
| Settings         | `GET /api/v1/settings`, `PUT .../llm`, `.../embedding`, `.../whatsapp`, `.../telegram`, `.../bot` |
