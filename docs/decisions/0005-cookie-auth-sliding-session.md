# 0005 — httpOnly cookie auth + sliding session (no refresh-token grant yet)

**Status:** Accepted

## Context

The dashboard is a SPA. The classic SPA pattern — store a JWT in `localStorage`
and attach it via an interceptor — exposes the token to any XSS. I wanted the
token unreadable by JS, with a simple session model for v1.

## Decision

- **httpOnly cookie.** Login/register set `sight_token` as an httpOnly cookie;
  the SPA never reads or stores the JWT. Axios uses `withCredentials: true` so the
  cookie travels automatically. A `Bearer` token is still accepted for scripts and
  the test suite.
- **Same-origin everywhere.** In dev, Vite proxies `/api` + `/webhooks` to the
  backend; in Docker, nginx reverse-proxies them — so requests are first-party and
  the cookie stays first-party (no CORS surface).
- **Sliding session, not a refresh grant.** `/auth/refresh` re-issues a fresh
  access token for the already-authenticated user. `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
  is reserved for a future real refresh-token flow.

## Consequences

**Good:** no JS-readable token → XSS can't exfiltrate the session; same-origin
keeps the cookie first-party and CORS-free; the model is easy to reason about.

**Costs:** logout only clears the cookie — there's no server-side revocation, so a
stolen token is valid until expiry (tracked: short TTL + jti blocklist, or a real
refresh grant). Cookie auth makes CSRF posture matter for state-changing routes —
`SameSite` must be set and re-auth required on sensitive mutations (tracked).
