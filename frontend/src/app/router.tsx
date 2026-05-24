import { Navigate, Route, Routes } from "react-router-dom";

import { LoginPage } from "../auth/LoginPage";
import { RegisterPage } from "../auth/RegisterPage";
import { ConversationsPage } from "../features/conversations/ConversationsPage";
import { DocumentsPage } from "../features/documents/DocumentsPage";
import { InboxPage } from "../features/escalations/InboxPage";
import { UsagePage } from "../features/llm-usage/UsagePage";
import { ProtectedShell } from "../shared/components/AppShell";
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
              <InboxPage />
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route
        path="/conversations"
        element={
          <RequireAuth>
            <ProtectedShell>
              <ConversationsPage />
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route
        path="/documents"
        element={
          <RequireAuth>
            <ProtectedShell>
              <DocumentsPage />
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route
        path="/usage"
        element={
          <RequireAuth>
            <ProtectedShell>
              <UsagePage />
            </ProtectedShell>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
