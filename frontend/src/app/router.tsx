import { Center, Loader } from "@mantine/core";
import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "@auth/LoginPage";
import { RegisterPage } from "@auth/RegisterPage";
import { ProtectedShell } from "@shared/components/AppShell";
import { ErrorBoundary } from "@shared/components/ErrorBoundary";
import { RequireAuth } from "@shared/components/RequireAuth";
import { RequireOwner } from "@shared/components/RequireOwner";
import { RequirePlatformAdmin } from "@shared/components/RequirePlatformAdmin";

// Code-split the protected feature pages — each becomes its own chunk loaded on
// first navigation, keeping the initial (login) bundle small.
const InboxPage = lazy(() =>
  import("@features/escalations/InboxPage").then((m) => ({ default: m.InboxPage })),
);
const ChatTestPage = lazy(() =>
  import("@features/conversations/ChatTestPage").then((m) => ({ default: m.ChatTestPage })),
);
const ConversationsPage = lazy(() =>
  import("@features/conversations/ConversationsPage").then((m) => ({ default: m.ConversationsPage })),
);
const DocumentsPage = lazy(() =>
  import("@features/documents/DocumentsPage").then((m) => ({ default: m.DocumentsPage })),
);
const UsagePage = lazy(() => import("@features/llm-usage/UsagePage").then((m) => ({ default: m.UsagePage })));
const SettingsPage = lazy(() =>
  import("@features/settings/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);
const AdminTenantsPage = lazy(() =>
  import("@features/admin/AdminTenantsPage").then((m) => ({ default: m.AdminTenantsPage })),
);
const AdminUsersPage = lazy(() =>
  import("@features/admin/AdminUsersPage").then((m) => ({ default: m.AdminUsersPage })),
);
const TeamPage = lazy(() =>
  import("@features/invitations/TeamPage").then((m) => ({ default: m.TeamPage })),
);
const InvitePage = lazy(() =>
  import("@features/invitations/InvitePage").then((m) => ({ default: m.InvitePage })),
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

function ProtectedAdmin({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <Protected>
      <RequirePlatformAdmin>{children}</RequirePlatformAdmin>
    </Protected>
  );
}

function ProtectedOwner({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <Protected>
      <RequireOwner>{children}</RequireOwner>
    </Protected>
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
          <ProtectedOwner>
            <SettingsPage />
          </ProtectedOwner>
        }
      />
      <Route
        path="/team"
        element={
          <ProtectedOwner>
            <TeamPage />
          </ProtectedOwner>
        }
      />
      <Route
        path="/invite/:token"
        element={
          <Suspense
            fallback={
              <Center mih="100vh">
                <Loader />
              </Center>
            }
          >
            <InvitePage />
          </Suspense>
        }
      />
      <Route
        path="/admin/tenants"
        element={
          <ProtectedAdmin>
            <AdminTenantsPage />
          </ProtectedAdmin>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedAdmin>
            <AdminUsersPage />
          </ProtectedAdmin>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
