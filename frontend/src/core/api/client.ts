import axios, { AxiosError } from "axios";

// Default to same-origin relative requests. In dev, the Vite server proxies
// `/api` and `/webhooks` to the backend; in Docker, nginx reverse-proxies them.
// Set VITE_API_URL only when the API is served from a different origin.
const BASE_URL = import.meta.env.VITE_API_URL ?? "";

// Auth is cookie-based: the backend sets an httpOnly `frontdesk_token` cookie on
// login/register, so the SPA never reads or stores the JWT (no localStorage =
// no XSS token theft). `withCredentials` makes the browser send that cookie on
// every request automatically.
export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
  withCredentials: true,
});

// The auth layer registers a handler so an expired/invalid session (HTTP 401)
// can reset in-memory auth state; RequireAuth then redirects to /login.
let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);
