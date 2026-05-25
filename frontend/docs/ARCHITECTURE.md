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
            └─ api instance   (core/api/client.ts — Axios)
                 ├─ request interceptor → injects Bearer token
                 └─ response interceptor → clears token on 401
```

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
│       └── client.ts             # Axios instance, token helpers (get/set/clear),
│                                 #   request interceptor (Bearer injection),
│                                 #   response interceptor (401 → clearToken)
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

### Bootstrap (page load)

```
AuthProvider mounts
  └─ loadCurrentUser()
       ├─ getToken() → null? → setUser(null), done
       └─ getToken() → has token
            ├─ authApi.me() → success → setUser(response)
            └─ authApi.me() → failure → clearToken(), setUser(null)
```

### Login

```
LoginPage form submit
  └─ auth.login(email, password)
       ├─ authApi.login() → TokenResponse
       ├─ setToken(access_token) → localStorage
       └─ loadCurrentUser() → authApi.me() → setUser()
```

### Logout

```
auth.logout()
  ├─ clearToken() → localStorage.removeItem
  └─ setUser(null) → triggers RequireAuth redirect
```

### Token storage

| Key                        | Storage        | Value        |
| -------------------------- | -------------- | ------------ |
| `frontdesk_access_token`   | localStorage   | JWT string   |

### 401 handling

The Axios response interceptor catches any `401` and calls `clearToken()`.
On the next React render cycle, `RequireAuth` sees `user === null` and
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
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});
```

### Request interceptor

Injects `Authorization: Bearer <token>` on every request when a token
exists in localStorage.

### Response interceptor

On `401`: calls `clearToken()`. The rejected promise propagates to the
calling code (TanStack Query marks the query as errored, or the mutation's
`onError` fires).

### Token helpers

| Function       | Purpose                                  |
| -------------- | ---------------------------------------- |
| `getToken()`   | Read from `localStorage`                 |
| `setToken(t)`  | Write to `localStorage`                  |
| `clearToken()` | Remove from `localStorage`               |

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

## 9. Theme and Design Tokens

**File:** `src/app/theme.ts`

### Colors

#### Coral (primary)

The brand color. Used for buttons, links, active states, and accent UI.

| Shade | Hex       | Usage                     |
| ----- | --------- | ------------------------- |
| 0     | `#fff3ed` | Lightest background       |
| 1     | `#ffe2d3` | Hover backgrounds         |
| 2     | `#fdc2a7` | Light borders             |
| 3     | `#fba076` | Badges, light accents     |
| 4     | `#f9844c` | Medium accent             |
| 5     | `#f87330` | Primary on dark scheme    |
| 6     | `#f76b22` | **Primary on light scheme** (buttons, CTAs) |
| 7     | `#dc5915` | Hover on primary          |
| 8     | `#c44e10` | Active/pressed            |
| 9     | `#aa4109` | Darkest emphasis          |

#### Slate (accent)

Deep blue-gray for contrast: headings, sidebar active states, nav.

| Shade | Hex       | Usage                     |
| ----- | --------- | ------------------------- |
| 0     | `#f3f5f8` | Lightest background       |
| 1     | `#e3e6eb` | Subtle highlights         |
| 2     | `#c5cbd5` | Light borders             |
| 3     | `#a4adbd` | Muted text                |
| 4     | `#88949f` | Secondary text            |
| 5     | `#717f97` | Medium accent             |
| 6     | `#67768f` | Base accent               |
| 7     | `#566480` | Hover on accent           |
| 8     | `#4d5a73` | Active/pressed            |
| 9     | `#404c66` | Darkest accent            |

### Primary shade

```ts
primaryShade: { light: 6, dark: 5 }
```

Mantine picks `coral.6` (`#f76b22`) in light mode and `coral.5` (`#f87330`)
in dark mode for all components that use the primary color.

### Default radius

```ts
defaultRadius: "md"
```

Applies to buttons, inputs, cards, and all Mantine components that accept a
`radius` prop.

### Font stack

```
-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif
```

Used for both body text and headings. Headings use `fontWeight: "600"`.

### Button defaults

All buttons render with `fw: 500` (medium weight) by default.

---

## 10. Component Patterns

### Page structure

Every page follows the same skeleton:

```tsx
export function FeaturePage() {
  const someQuery = useQuery({ queryKey: [...], queryFn: ... });

  return (
    <Stack>
      {/* Header: Title + description + actions */}
      <Group justify="space-between">
        <div>
          <Title order={2}>Page Title</Title>
          <Text c="dimmed" size="sm">Description.</Text>
        </div>
        {/* Optional action buttons */}
      </Group>

      {/* Loading state */}
      {someQuery.isLoading && <Center py="xl"><Loader /></Center>}

      {/* Error state */}
      {someQuery.isError && <Alert color="red">Could not load data.</Alert>}

      {/* Empty state */}
      {someQuery.isSuccess && someQuery.data.length === 0 && (
        <Card withBorder radius="md" p="xl">
          <Center py="xl">
            <Stack align="center" gap="xs">
              <SomeIcon size={32} stroke={1.4} />
              <Text fw={500}>Nothing here.</Text>
              <Text c="dimmed" size="sm">Guidance text.</Text>
            </Stack>
          </Center>
        </Card>
      )}

      {/* Data state */}
      {someQuery.isSuccess && someQuery.data.length > 0 && (
        /* Table or card grid */
      )}
    </Stack>
  );
}
```

### Four-state rendering

Every data-driven page handles exactly four states:

1. **Loading** -- `<Loader />` centered on the page.
2. **Error** -- `<Alert color="red">` with a user-friendly message.
3. **Empty** -- `<Card>` with an icon, bold text, and guidance.
4. **Data** -- the actual content (table, card grid, etc.).

### Mutations

Mutations use `useMutation` from TanStack Query. Two patterns:

**Inline onSuccess/onError** (most pages):

```tsx
const mutation = useMutation({
  mutationFn: apiCall,
  onSuccess: () => {
    notifications.show({ color: "teal", message: "Done." });
    queryClient.invalidateQueries({ queryKey: [...] });
  },
  onError: () => {
    notifications.show({ color: "red", message: "Failed." });
  },
});
```

**Section mutation helper** (SettingsPage):

```tsx
function useSectionMutation(fn, label) {
  return useMutation({
    mutationFn: fn,
    onSuccess: () => { notify success; invalidate; },
    onError: () => { notify error; },
  });
}
```

### Forms

All forms use `@mantine/form`:

```tsx
const form = useForm({
  initialValues: { ... },
  validate: { fieldName: (v) => condition ? null : "Error message" },
});

const handleSubmit = form.onSubmit(async (values) => { ... });
```

---

## 11. Testing Strategy

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
  getToken: () => "tok",
  setToken: vi.fn(),
  clearToken: vi.fn(),
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

## 12. Backend Contract

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
the shared Axios instance which has `baseURL` set to
`VITE_API_URL` (default `http://localhost:8000`).

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

## 13. Conventions

### Naming

| What                | Convention                          | Example                 |
| ------------------- | ----------------------------------- | ----------------------- |
| Page component      | `PascalCase` + `Page` suffix        | `InboxPage`             |
| API file            | `api.ts` in feature folder          | `escalations/api.ts`    |
| Types file          | `types.ts` in feature folder        | `escalations/types.ts`  |
| Test file           | Same name + `.test.tsx` / `.test.ts`| `InboxPage.test.tsx`    |
| Hook                | `camelCase` with `use` prefix       | `useAuth`               |
| Context             | `PascalCase` + `Context`            | `AuthContext`            |
| Exported functions  | Named exports only                  | `export function X()`   |

### Imports

- Relative imports within the same module (`./api`, `./types`).
- Path-based imports across modules (`../../core/api/client`).
- No path aliases configured in this project (vite.config.ts has no
  `resolve.alias`).

### Icons

All icons come from `@tabler/icons-react`.

- Standard size: `18` for inline / nav icons.
- Standard stroke: `1.4` to `1.6`.
- Smaller context: `14` (badges, labels).

### Brand color usage

- Primary actions (buttons, links): `coral` (the Mantine primary color).
- Accent/nav contrast: `slate`.
- Success feedback: `teal`.
- Error feedback: `red`.
- Neutral/muted: `gray`, `dimmed`.

### Component prop conventions

- `Readonly<{ children: ReactNode }>` on all wrapper components.
- `Readonly<Props>` on component function signatures.
- Mantine style props for spacing and layout (`p`, `px`, `gap`, `mt`).

### Notifications

All user-facing notifications use `@mantine/notifications`:

```tsx
notifications.show({ color: "teal", message: "Success." });
notifications.show({ color: "red", message: "Something went wrong." });
```

Notifications are positioned `top-right` (configured in `Providers.tsx`).
