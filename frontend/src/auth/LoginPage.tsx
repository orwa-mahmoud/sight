import { Anchor, Button, Card, Group, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "./useAuth";

export function LoginPage() {
  const { t } = useTranslation();
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);

  // Return to the page the user originally tried to reach (set by RequireAuth),
  // falling back to home. Guard against pointing back at /login.
  const fromState = (location.state as { from?: string } | null)?.from;
  const redirectTo = fromState && fromState !== "/login" ? fromState : "/";

  const form = useForm({
    initialValues: { email: "", password: "" },
    validate: {
      email: (v) => (/^[^@\s]+@[^@.\s]+(?:\.[^@.\s]+)+$/.test(v) ? null : t("auth.errInvalidEmail")),
      password: (v) => (v.length >= 8 ? null : t("auth.errPasswordMin")),
    },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitting(true);
    try {
      await login(values.email, values.password);
      navigate(redirectTo, { replace: true });
    } catch {
      notifications.show({ color: "red", message: t("auth.errInvalidCredentials") });
    } finally {
      setSubmitting(false);
    }
  });

  if (user) return <Navigate to={redirectTo} replace />;

  return (
    <Stack align="center" justify="center" mih="100vh" px="md">
      <Card shadow="md" radius="lg" p="xl" w={420} withBorder>
        <Stack>
          <div>
            <Title order={2} mb={4}>
              {t("auth.signInTo")} <span style={{ color: "var(--mantine-color-coral-6)" }}>Sight</span>
            </Title>
            <Text c="dimmed" size="sm">
              {t("auth.loginSubtitle")}
            </Text>
          </div>

          <form onSubmit={handleSubmit}>
            <Stack>
              <TextInput
                label={t("auth.email")}
                placeholder={t("auth.emailPlaceholderOwner")}
                autoComplete="email"
                {...form.getInputProps("email")}
              />
              <PasswordInput
                label={t("auth.password")}
                placeholder="••••••••"
                autoComplete="current-password"
                {...form.getInputProps("password")}
              />
              <Button type="submit" loading={submitting} fullWidth>
                {t("auth.signIn")}
              </Button>
            </Stack>
          </form>

          <Group justify="center" gap="xs">
            <Text size="sm" c="dimmed">
              {t("auth.newHere")}
            </Text>
            <Anchor component={Link} to="/register" size="sm">
              {t("auth.createAccount")}
            </Anchor>
          </Group>
        </Stack>
      </Card>
    </Stack>
  );
}
