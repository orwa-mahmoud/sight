import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";
import "@fontsource/ibm-plex-sans-arabic/400.css";
import "@fontsource/ibm-plex-sans-arabic/500.css";
import "@fontsource/ibm-plex-sans-arabic/600.css";
import "@shared/i18n";

import { DirectionProvider, MantineProvider } from "@mantine/core";
import { ModalsProvider } from "@mantine/modals";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useEffect } from "react";
import type { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "@auth/AuthContext";
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

/** Keeps <html dir/lang> and Mantine's direction in sync with the language. */
function DirectionGate({ children }: Readonly<{ children: ReactNode }>) {
  const { language, dir } = useLanguage();

  useEffect(() => {
    document.documentElement.dir = dir;
    document.documentElement.lang = language;
  }, [dir, language]);

  // Remount on direction change so every Mantine component picks up the new
  // direction (language switches are rare, so a subtree remount is fine).
  return (
    <DirectionProvider key={dir} initialDirection={dir} detectDirection={false}>
      {children}
    </DirectionProvider>
  );
}

export function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <DirectionGate>
      <MantineProvider theme={theme} defaultColorScheme="auto">
        <ModalsProvider>
          <Notifications position="top-right" />
          <QueryClientProvider client={queryClient}>
            <BrowserRouter>
              <AuthProvider>{children}</AuthProvider>
            </BrowserRouter>
            {import.meta.env.DEV ? <ReactQueryDevtools initialIsOpen={false} /> : null}
          </QueryClientProvider>
        </ModalsProvider>
      </MantineProvider>
    </DirectionGate>
  );
}
