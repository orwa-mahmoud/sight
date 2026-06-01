# Frontend Architecture

> Source of truth is the code. If this document disagrees with the code, the
> code wins -- update the doc in the same change.

---

## 1. Stack

| Layer         | Library                           | Version |
| ------------- | --------------------------------- | ------- |
| UI framework  | React                             | 19      |
| Component lib | Mantine                           | 9       |
| Language       | TypeScript                        | 6       |
| Build tool    | Vite                              | 8       |
| Server state  | TanStack Query (React Query)      | 5       |
| Routing       | React Router                      | 7       |
| HTTP client   | Axios                             | 1       |
| Icons         | @tabler/icons-react               | 3       |
| Date handling | dayjs                             | 1       |
| Test runner   | Vitest                            | 4       |
| Test utils    | @testing-library/react            | 16      |

---

## 2. Architecture Diagram

```
                        Providers.tsx
                  ┌─────────────────────────┐
                  │  MantineProvider (theme) │
                  │    Notifications         │
                  │      QueryClientProvider │
                  │        BrowserRouter     │
                  │          AuthProvider    │
                  └────────────┬────────────┘
                               │
                          AppRoutes
                       ┌───────┴───────┐
                       │               │
                  Public           Protected
               ┌────┴────┐     ┌──────┴──────┐
            LoginPage  RegisterPage   RequireAuth
                                        │
                                  ProtectedShell
                              (Header + Sidebar)
                                        │
                         ┌──────┬───────┼───────┬──────┐
                      InboxPage  Conversations  Docs  Usage  Settings
                                   ChatTestPage
```

**Data flow:**

```
Page component
  └─ useQuery / useMutation  (TanStack Query)
       └─ feature api.ts     (typed wrapper)
            └─ api instance   (core/api/client.ts — Axios, withCredentials)
                 └─ response interceptor → on 401 calls the unauthorized handler
```

The auth JWT travels as an httpOnly cookie (set by the backend), so there is
no request interceptor injecting a token — `withCredentials: true` sends the
cookie automatically.

---

## 3. Folder Structure

```
src/
├── app/                          # Composition root
│   ├── Providers.tsx             # Nests Mantine, Notifications, QueryClient,
│   │                             #   BrowserRouter, AuthProvider
│   ├── router.tsx                # Route table (AppRoutes component)
│   └── theme.ts                  # Mantine theme: coral + slate palettes,
│                                 #   font stack, default radius, component defaults
│
├── auth/                         # Authentication (infrastructure, not a feature)
│   ├── api.ts                    # login(), register(), me() — call /api/v1/auth/*
│   ├── context.ts                # createContext<AuthContextValue>
│   ├── AuthContext.tsx            # AuthProvider — token bootstrap, login/register/logout
│   ├── useAuth.ts                # useAuth() hook (throws if outside provider)
│   ├── types.ts                  # TokenResponse, MeResponse, RegisterRequest, TenantSummary
│   ├── LoginPage.tsx             # Sign-in form
│   └── RegisterPage.tsx          # Sign-up + tenant creation form
│
├── core/
│   └── api/
│       └── client.ts             # Axios instance (withCredentials), relative
│                                 #   baseURL, response interceptor (401 →
│                                 #   unauthorized handler), setUnauthorizedHandler
│
├── features/                     # One folder per business feature
│   ├── escalations/              # Owner inbox (the differentiating page)
│   │   ├── api.ts                # listQuestions, replyToQuestion, closeQuestion
│   │   ├── types.ts              # Question, QuestionStatus
│   │   └── InboxPage.tsx         # Segmented filter, question cards, reply modal
│   │
│   ├── conversations/            # AI conversation threads + daily summary
│   │   ├── ConversationsPage.tsx # Table of threads + stat cards
│   │   └── ChatTestPage.tsx      # Live chat to test the agent pipeline
│   │
│   ├── documents/                # Knowledge base (RAG document management)
│   │   └── DocumentsPage.tsx     # Upload, list, delete documents
│   │
│   ├── llm-usage/                # Token + cost ledger
│   │   └── UsagePage.tsx         # Stat cards + cost breakdown
│   │
│   └── settings/                 # Tenant configuration
│       ├── api.ts                # getSettings, updateLLM, updateEmbedding,
│       │                         #   updateWhatsApp, updateTelegram, updateBot
│       ├── types.ts              # TenantConfigResponse
│       └── SettingsPage.tsx      # Accordion sections for LLM, embedding,
│                                 #   WhatsApp, Telegram, bot personality
│
├── shared/
│   └── components/
│       ├── AppShell.tsx          # ProtectedShell — Mantine AppShell with header,
│       │                         #   sidebar nav, user avatar, logout action
│       └── RequireAuth.tsx       # Route guard — redirects to /login when
│                                 #   unauthenticated, shows Loader while checking
│
└── test/
    ├── setup.ts                  # Vitest global setup — polyfills for
    │                             #   matchMedia, ResizeObserver, document.fonts
    └── wrapper.tsx               # TestWrapper — MantineProvider + Notifications +
                                  #   QueryClientProvider (retry: false) + MemoryRouter
```

---

## 4. State Management

There are exactly **two** state categories. No Redux, no Zustand.

### Server state -- TanStack Query

Every API call uses `useQuery` or `useMutation` from `@tanstack/react-query`.

- **QueryClient** is created in `Providers.tsx` with `staleTime: 30_000`,
  `refetchOnWindowFocus: false`, `retry: 1`.
- Feature pages call `useQuery({ queryKey, queryFn })` directly.
- Mutations call `useMutation({ mutationFn, onSuccess, onError })`.
- Cache invalidation uses `queryClient.invalidateQueries({ queryKey })`.

### Auth state -- React Context

`AuthContext` holds the current `user` (or `null`) and `loading` flag. It is
the single source of truth for authentication state.

- Provided by `AuthProvider` at the top of the component tree.
- Consumed via `useAuth()` hook, which throws if called outside the provider.
- No global state store beyond this.

---

## 5. Auth Flow

Cookie-based. The backend sets an httpOnly `frontdesk_token` cookie on
login/register, so the SPA never reads or stores the JWT (no localStorage =
no XSS token theft). `axios` runs with `withCredentials: true`, so the cookie
is sent on every request automatically.

### Bootstrap (page load)

```
AuthProvider mounts
  └─ authApi.me()   (cookie sent automatically)
       ├─ success → setUser(response)
       └─ failure (401 = not logged in) → setUser(null)
```

### Login

```
LoginPage form submit
  └─ auth.login(email, password)
       ├─ authApi.login()  → backend sets the httpOnly cookie
       └─ loadCurrentUser() → authApi.me() → setUser()
```

### Logout

```
auth.logout()
  ├─ setUser(null) → triggers RequireAuth redirect
  └─ authApi.logout() → backend clears the cookie
```

### Token storage

The JWT lives only in the httpOnly `frontdesk_token` cookie, managed by the
backend and inaccessible to JavaScript. The SPA keeps no token in
localStorage or memory.

### 401 handling

The Axios response interceptor catches any `401` and calls the handler
registered via `setUnauthorizedHandler` (AuthProvider registers one that does
`setUser(null)`). On the next render, `RequireAuth` sees `user === null` and
redirects to `/login`.

### RequireAuth guard

```tsx
function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading)  return <Loader />;
  if (!user)    return <Navigate to="/login" />;
  return children;
}
```

It also preserves the original `location.pathname` in `state.from` for
potential post-login redirect.

---

## 6. API Client

**File:** `src/core/api/client.ts`

```ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",   // same-origin relative
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
  withCredentials: true,                          // send the auth cookie
});
```

The default base URL is empty (same-origin relative). In dev the Vite server
proxies `/api` + `/webhooks` to the backend; in Docker nginx reverse-proxies
them — so requests are same-origin everywhere and the auth cookie stays
first-party. Set `VITE_API_URL` only to point at a different origin.

### Response interceptor

On `401`: calls the handler registered via `setUnauthorizedHandler`. The
rejected promise still propagates to the calling code (TanStack Query marks
the query as errored, or the mutation's `onError` fires).

### Helpers

| Function                      | Purpose                                                    |
| ----------------------------- | ---------------------------------------------------------- |
| `setUnauthorizedHandler(fn)`  | Register the callback fired when any response returns 401  |

---

## 7. Feature Module Pattern

Each feature is a self-contained folder under `src/features/`. The
convention:

```
features/<name>/
├── api.ts           # Typed API functions (call the axios instance)
├── types.ts         # TypeScript interfaces matching backend JSON
├── <Name>Page.tsx   # Page component (renders UI, calls useQuery/useMutation)
└── *.test.tsx       # Co-located tests
```

**Key rules:**

- One feature = one folder.
- Each feature owns its API functions, types, and page components.
- Avoid cross-feature imports. Features talk to each other only through
  shared infrastructure (auth, api client, shared components).
- Features that have only a page (no dedicated API) inline their fetch
  functions in the page file (e.g., `ConversationsPage`, `DocumentsPage`,
  `UsagePage`).

### Feature inventory

| Feature          | Folder          | API file | Types file | Pages                           |
| ---------------- | --------------- | -------- | ---------- | ------------------------------- |
| Escalations      | `escalations/`  | Yes      | Yes        | InboxPage                       |
| Conversations    | `conversations/`| No (inline) | No (inline) | ConversationsPage, ChatTestPage |
| Documents        | `documents/`    | No (inline) | No (inline) | DocumentsPage                  |
| LLM Usage        | `llm-usage/`    | No (inline) | No (inline) | UsagePage                       |
| Settings         | `settings/`     | Yes      | Yes        | SettingsPage                    |

---

## 8. Routing

**File:** `src/app/router.tsx`

All routes are defined in a single `AppRoutes` component using React Router's
`<Routes>` and `<Route>`.

### Route table

| Path              | Component           | Auth | Layout          |
| ----------------- | ------------------- | ---- | --------------- |
| `/login`          | LoginPage           | No   | None            |
| `/register`       | RegisterPage        | No   | None            |
| `/`               | InboxPage           | Yes  | ProtectedShell  |
| `/conversations`  | ConversationsPage   | Yes  | ProtectedShell  |
| `/documents`      | DocumentsPage       | Yes  | ProtectedShell  |
| `/usage`          | UsagePage           | Yes  | ProtectedShell  |
| `/chat`           | ChatTestPage        | Yes  | ProtectedShell  |
| `/settings`       | SettingsPage        | Yes  | ProtectedShell  |
| `*`               | Redirect to `/`     | --   | --              |

### Protected route pattern

Every authenticated route wraps its page in `RequireAuth` + `ProtectedShell`:

```tsx
<Route
  path="/conversations"
  element={
    <RequireAuth>
      <ProtectedShell>
        <ConversationsPage />
      </ProtectedShell>
    </RequireAuth>
  }
/>
```

`RequireAuth` handles the auth check. `ProtectedShell` provides the header
and sidebar. There is no lazy loading yet -- all page imports are eager.

---

## 9. Design System

Color palette, component patterns, naming conventions, and styling reference:

- **[DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)** -- coral + slate color palettes, primary shade config, font stack, default radius, button defaults, page structure skeleton, four-state rendering pattern, mutation patterns, form patterns, naming conventions, icon usage, brand color usage, component prop conventions, notifications.

---

## 10. Testing Strategy

### Tools

| Tool                      | Purpose                              |
| ------------------------- | ------------------------------------ |
| Vitest                    | Test runner, assertions, mocking     |
| @testing-library/react    | Render components, query the DOM     |
| @testing-library/jest-dom | Custom matchers (toBeInTheDocument)  |

### Test setup

**File:** `src/test/setup.ts`

Polyfills browser APIs that Mantine and React rely on:

- `document.fonts` -- stub for font loading API.
- `globalThis.matchMedia` -- stub returning `{ matches: false }`.
- `globalThis.ResizeObserver` -- no-op mock class.

### TestWrapper

**File:** `src/test/wrapper.tsx`

Wraps components in the provider stack needed for tests:

```tsx
<MantineProvider theme={theme}>
  <Notifications />
  <QueryClientProvider client={queryClient}>  // retry: false
    <MemoryRouter>{children}</MemoryRouter>
  </QueryClientProvider>
</MantineProvider>
```

Note: `TestWrapper` does **not** include `AuthProvider`. Tests that need auth
mock the `useAuth` hook or the `AuthContext.Provider` directly.

### Mocking patterns

**Mock a feature's API module** (escalations pattern):

```tsx
vi.mock("./api", () => ({
  listQuestions: vi.fn(),
  replyToQuestion: vi.fn(),
  closeQuestion: vi.fn(),
}));

// In the test:
vi.mocked(listQuestions).mockResolvedValue([...]);
```

**Mock the Axios instance** (conversations pattern):

```tsx
vi.mock("../../core/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    defaults: { headers: {} },
  },
  setUnauthorizedHandler: vi.fn(),
}));
```

**Mock auth for components needing useAuth:**

Provide `AuthContext.Provider` with a controlled value, or `vi.mock` the
`useAuth` module.

### Test structure

Tests are **co-located** with the source files:

```
InboxPage.tsx
InboxPage.test.tsx
api.ts
api.test.ts
types.ts
types.test.ts
```

Each test file follows this structure:

```tsx
describe("ComponentName", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("renders the title", () => { ... });
  it("shows loading state", () => { ... });
  it("shows error state", async () => { ... });
  it("shows empty state", async () => { ... });
  it("renders data", async () => { ... });
  it("handles user interaction", async () => { ... });
});
```

---

## 11. Backend Contract

### JSON shape

The backend (FastAPI) serializes all responses in **snake_case**. Frontend
TypeScript interfaces mirror this exactly:

```ts
// Backend returns: { "question_text": "...", "ai_answer_attempt": "..." }
// Frontend type:
interface Question {
  question_text: string;
  ai_answer_attempt: string | null;
}
```

There is **no codegen** (no OpenAPI client generator). Types are kept in sync
by hand. When the backend adds or renames a field, the corresponding
`types.ts` in the feature folder must be updated manually.

### API prefix

All backend endpoints live under `/api/v1/`. Feature API files use
the shared Axios instance whose `baseURL` defaults to `""` (same-origin
relative); `/api` is proxied to the backend by Vite in dev and by nginx in
Docker.

### Endpoint mapping

| Frontend feature | Backend endpoints                                   |
| ---------------- | --------------------------------------------------- |
| Auth             | `POST /api/v1/auth/login`, `/register`, `GET /me`   |
| Escalations      | `GET /api/v1/questions`, `POST .../reply`, `.../close` |
| Conversations    | `GET /api/v1/conversations`, `.../daily-summary`     |
| Documents        | `GET/POST/DELETE /api/v1/documents`                  |
| LLM Usage        | `GET /api/v1/llm-usage/stats`                        |
| Chat             | `POST /api/v1/chat`                                  |
| Settings         | `GET /api/v1/settings`, `PUT .../llm`, `.../embedding`, `.../whatsapp`, `.../telegram`, `.../bot` |

---

## 12. Conventions

Naming, imports, icons, brand colors, component props, and notification patterns are documented in **[DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)**.
