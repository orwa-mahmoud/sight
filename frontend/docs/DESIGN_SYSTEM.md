# Frontdesk Design System

Component patterns, naming conventions, color palette, and styling reference for the Frontdesk owner dashboard.

> **Source of truth:** The code. If this document disagrees with the code, the code wins -- update the doc in the same change.

---

## 1. Color Palette

### Coral (Primary)

The brand color. Used for buttons, links, active states, and accent UI.

| Shade | Hex       | Usage                                       | Mantine Reference |
| ----- | --------- | ------------------------------------------- | ----------------- |
| **0** | `#fff3ed` | Lightest background                         | `coral.0`         |
| **1** | `#ffe2d3` | Hover backgrounds                           | `coral.1`         |
| **2** | `#fdc2a7` | Light borders                               | `coral.2`         |
| **3** | `#fba076` | Badges, light accents                       | `coral.3`         |
| **4** | `#f9844c` | Medium accent                               | `coral.4`         |
| **5** | `#f87330` | Primary on dark scheme                      | `coral.5`         |
| **6** | `#f76b22` | **Primary on light scheme** (buttons, CTAs) | `coral.6`         |
| **7** | `#dc5915` | Hover on primary                            | `coral.7`         |
| **8** | `#c44e10` | Active/pressed                              | `coral.8`         |
| **9** | `#aa4109` | Darkest emphasis                            | `coral.9`         |

### Slate (Accent)

Deep blue-gray for contrast: headings, sidebar active states, nav.

| Shade | Hex       | Usage               | Mantine Reference |
| ----- | --------- | ------------------- | ----------------- |
| **0** | `#f3f5f8` | Lightest background | `slate.0`         |
| **1** | `#e3e6eb` | Subtle highlights   | `slate.1`         |
| **2** | `#c5cbd5` | Light borders       | `slate.2`         |
| **3** | `#a4adbd` | Muted text          | `slate.3`         |
| **4** | `#88949f` | Secondary text      | `slate.4`         |
| **5** | `#717f97` | Medium accent       | `slate.5`         |
| **6** | `#67768f` | Base accent         | `slate.6`         |
| **7** | `#566480` | Hover on accent     | `slate.7`         |
| **8** | `#4d5a73` | Active/pressed      | `slate.8`         |
| **9** | `#404c66` | Darkest accent      | `slate.9`         |

### Primary Shade

```ts
primaryShade: { light: 6, dark: 5 }
```

Mantine picks `coral.6` (`#f76b22`) in light mode and `coral.5` (`#f87330`) in dark mode for all components that use the primary color.

### Brand Color Usage

| Use Case          | Mantine Prop / Value                       |
| ----------------- | ------------------------------------------ |
| Primary button    | `color="coral"` (default, as primaryColor) |
| Accent contrast   | `color="slate"`                            |
| Success feedback  | `color="teal"`                             |
| Error feedback    | `color="red"`                              |
| Muted text        | `c="dimmed"`                               |
| Light primary bg  | `bg="coral.0"`                             |
| Hover on primary  | `coral.7`                                  |
| Active on primary | `coral.8`                                  |

---

## 2. Theme Configuration

**Source file:** `src/app/theme.ts`

### Default Radius

```ts
defaultRadius: "md";
```

Applies to buttons, inputs, cards, and all Mantine components that accept a `radius` prop.

### Font Stack

```
-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif
```

Used for both body text and headings. Headings use `fontWeight: "600"`.

### Button Defaults

All buttons render with `fw: 500` (medium weight) by default.

---

## 3. Component Patterns

### Page Structure

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

### Four-State Rendering

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

## 4. Naming Conventions

| What               | Convention                           | Example                |
| ------------------ | ------------------------------------ | ---------------------- |
| Page component     | `PascalCase` + `Page` suffix         | `InboxPage`            |
| API file           | `api.ts` in feature folder           | `escalations/api.ts`   |
| Types file         | `types.ts` in feature folder         | `escalations/types.ts` |
| Test file          | Same name + `.test.tsx` / `.test.ts` | `InboxPage.test.tsx`   |
| Hook               | `camelCase` with `use` prefix        | `useAuth`              |
| Context            | `PascalCase` + `Context`             | `AuthContext`          |
| Exported functions | Named exports only                   | `export function X()`  |

---

## 5. Imports

- Relative imports within the same module (`./api`, `./types`).
- Path-based imports across modules (`../../core/api/client`).
- No path aliases configured in this project (vite.config.ts has no `resolve.alias`).

---

## 6. Icons

All icons come from `@tabler/icons-react`.

- Standard size: `18` for inline / nav icons.
- Standard stroke: `1.4` to `1.6`.
- Smaller context: `14` (badges, labels).

---

## 7. Component Prop Conventions

- `Readonly<{ children: ReactNode }>` on all wrapper components.
- `Readonly<Props>` on component function signatures.
- Mantine style props for spacing and layout (`p`, `px`, `gap`, `mt`).

---

## 8. Notifications

All user-facing notifications use `@mantine/notifications`:

```tsx
notifications.show({ color: "teal", message: "Success." });
notifications.show({ color: "red", message: "Something went wrong." });
```

Notifications are positioned `top-right` (configured in `Providers.tsx`).

---

## 9. Related Docs

| Doc                                  | Purpose                                               |
| ------------------------------------ | ----------------------------------------------------- |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Project structure, state management, routing, testing |
