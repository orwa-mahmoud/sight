/**
 * Typed, validated application config — the single place env is read.
 * Import `config` instead of touching `import.meta.env` throughout the app.
 */
export interface AppConfig {
  /** API base URL. Empty = same-origin (dev proxy / nginx). */
  readonly apiUrl: string;
  readonly isDev: boolean;
}

export const config: AppConfig = {
  apiUrl: import.meta.env.VITE_API_URL ?? "",
  isDev: import.meta.env.DEV,
};
