import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "../auth/LoginPage";
import { RegisterPage } from "../auth/RegisterPage";
import { ChatTestPage } from "../features/conversations/ChatTestPage";
import { ConversationsPage } from "../features/conversations/ConversationsPage";
import { DocumentsPage } from "../features/documents/DocumentsPage";
import { InboxPage } from "../features/escalations/InboxPage";
import { UsagePage } from "../features/llm-usage/UsagePage";
import { SettingsPage } from "../features/settings/SettingsPage";
import { ProtectedShell } from "../shared/components/AppShell";
import { ErrorBoundary } from "../shared/components/ErrorBoundary";
import { RequireAuth } from "../shared/components/RequireAuth";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <ProtectedShell>
              <ErrorBoundary>
                <InboxPage />
              </ErrorBoundary>
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route
        path="/conversations"
        element={
          <RequireAuth>
            <ProtectedShell>
              <ErrorBoundary>
                <ConversationsPage />
              </ErrorBoundary>
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route
        path="/documents"
        element={
          <RequireAuth>
            <ProtectedShell>
              <ErrorBoundary>
                <DocumentsPage />
              </ErrorBoundary>
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route
        path="/usage"
        element={
          <RequireAuth>
            <ProtectedShell>
              <ErrorBoundary>
                <UsagePage />
              </ErrorBoundary>
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route
        path="/chat"
        element={
          <RequireAuth>
            <ProtectedShell>
              <ErrorBoundary>
                <ChatTestPage />
              </ErrorBoundary>
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route
        path="/settings"
        element={
          <RequireAuth>
            <ProtectedShell>
              <ErrorBoundary>
                <SettingsPage />
              </ErrorBoundary>
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
