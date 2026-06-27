# Sight — frontend

The web dashboard for [Sight](../README.md): owners manage their knowledge
base, connect channels, review the AI's conversations, and answer escalated
questions. React 19 + Mantine 9 + TypeScript + Vite, with full English/Arabic
RTL support.

## Quick start

```bash
npm install
npm run dev    # http://localhost:5173 — Vite proxies /api + /webhooks to :8000
```

You need the [backend](../backend/) running on port 8000 (or set `VITE_API_URL`).

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Vite dev server (HMR) |
| `npm run build` | Type-check + production build |
| `npm run typecheck` | `tsc -b --noEmit` |
| `npm run lint` | ESLint |
| `npm test` | Vitest (run once) |
| `npm run test:coverage` | Vitest with coverage |
| `npm run format` | Prettier write |

Run `lint`, `typecheck`, and `test` before pushing (CI gates on all three).

## Architecture

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — folder structure, state
  management, auth flow, API client, feature modules, routing, testing.
- **[docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md)** — theme, colors, component
  patterns, four-state rendering, forms, i18n.
- **[CLAUDE.md](CLAUDE.md)** — conventions in brief.

Highlights: cookie-based auth (no JWT in JS), feature-module structure, server
state via TanStack Query (no Redux), a thin DataTable facade over
`@adapttable/mantine`, and EN/AR with RTL mirroring via Mantine's
`DirectionProvider`.
