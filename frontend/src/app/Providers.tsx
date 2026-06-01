import "@mantine/core/styles.css";
import "@mantine/notifications/styles.css";

import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "@auth/AuthContext";

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

export function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MantineProvider theme={theme} defaultColorScheme="light">
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>{children}</AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}
