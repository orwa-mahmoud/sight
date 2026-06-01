import { Center, Loader } from "@mantine/core";
import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "@auth/LoginPage";
import { RegisterPage } from "@auth/RegisterPage";
import { ProtectedShell } from "@shared/components/AppShell";
import { ErrorBoundary } from "@shared/components/ErrorBoundary";
import { RequireAuth } from "@shared/components/RequireAuth";

// Code-split the protected feature pages — each becomes its own chunk loaded on
// first navigation, keeping the initial (login) bundle small.
const InboxPage = lazy(() => import("@features/escalations/InboxPage").then((m) => ({ default: m.InboxPage })));
const ChatTestPage = lazy(() =>
  import("@features/conversations/ChatTestPage").then((m) => ({ default: m.ChatTestPage }))
);
const ConversationsPage = lazy(() =>
  import("@features/conversations/ConversationsPage").then((m) => ({ default: m.ConversationsPage }))
);
const DocumentsPage = lazy(() =>
  import("@features/documents/DocumentsPage").then((m) => ({ default: m.DocumentsPage }))
);
const UsagePage = lazy(() => import("@features/llm-usage/UsagePage").then((m) => ({ default: m.UsagePage })));
const SettingsPage = lazy(() =>
  import("@features/settings/SettingsPage").then((m) => ({ default: m.SettingsPage }))
);

function Protected({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <RequireAuth>
      <ProtectedShell>
        <ErrorBoundary>
          <Suspense
            fallback={
              <Center h="60vh">
                <Loader />
              </Center>
            }
          >
            {children}
          </Suspense>
        </ErrorBoundary>
      </ProtectedShell>
    </RequireAuth>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <InboxPage />
          </Protected>
        }
      />
      <Route
        path="/conversations"
        element={
          <Protected>
            <ConversationsPage />
          </Protected>
        }
      />
      <Route
        path="/documents"
        element={
          <Protected>
            <DocumentsPage />
          </Protected>
        }
      />
      <Route
        path="/usage"
        element={
          <Protected>
            <UsagePage />
          </Protected>
        }
      />
      <Route
        path="/chat"
        element={
          <Protected>
            <ChatTestPage />
          </Protected>
        }
      />
      <Route
        path="/settings"
        element={
          <Protected>
            <SettingsPage />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
