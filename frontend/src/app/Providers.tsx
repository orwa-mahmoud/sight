import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "@fontsource/ibm-plex-sans-arabic/400.css";
import "@fontsource/ibm-plex-sans-arabic/500.css";
import "@fontsource/ibm-plex-sans-arabic/600.css";

import { DirectionProvider, MantineProvider, useDirection } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "@auth/AuthContext";
import i18n, { dirFor } from "@shared/i18n";
import { useLanguage } from "@shared/i18n/useLanguage";

import { theme } from "./theme";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

// Direction at first paint, before any component mounts (i18n is initialized
// synchronously, so the resolved language is already known here).
const initialDir = dirFor(i18n.resolvedLanguage ?? "en");

/**
 * Keeps <html dir/lang> and Mantine's direction in sync with the active
 * language — via `setDirection` (no subtree remount, so AuthProvider and page
 * state survive a language switch).
 */
function DirectionSync({ children }: Readonly<{ children: ReactNode }>) {
  const { language, dir } = useLanguage();
  const { setDirection } = useDirection();

  useEffect(() => {
    document.documentElement.dir = dir;
    document.documentElement.lang = language;
    setDirection(dir);
  }, [dir, language, setDirection]);

  return <>{children}</>;
}

export function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <DirectionProvider initialDirection={initialDir} detectDirection={false}>
      <MantineProvider theme={theme} defaultColorScheme="auto">
        <ModalsProvider>
          <DirectionSync>
            <Notifications position="top-right" />
            <QueryClientProvider client={queryClient}>
              <BrowserRouter>
                <AuthProvider>{children}</AuthProvider>
              </BrowserRouter>
              {import.meta.env.DEV ? <ReactQueryDevtools initialIsOpen={false} /> : null}
            </QueryClientProvider>
          </DirectionSync>
        </ModalsProvider>
      </MantineProvider>
    </DirectionProvider>
  );
}
