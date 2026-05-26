import {
  Anchor,
  Button,
  Card,
  Group,
  PasswordInput,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "./useAuth";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const form = useForm({
    initialValues: { email: "", password: "" },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Enter a valid email"),
      password: (v) => (v.length >= 8 ? null : "At least 8 characters"),
    },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitting(true);
    try {
      await login(values.email, values.password);
      navigate("/", { replace: true });
    } catch {
      notifications.show({ color: "red", message: "Invalid email or password." });
    } finally {
      setSubmitting(false);
    }
  });

  if (user) return <Navigate to="/" replace />;

  return (
    <Stack align="center" justify="center" mih="100vh" px="md">
      <Card shadow="md" radius="lg" p="xl" w={420} withBorder>
        <Stack>
          <div>
            <Title order={2} mb={4}>
              Sign in to <span style={{ color: "var(--mantine-color-coral-6)" }}>frontdesk</span>
            </Title>
            <Text c="dimmed" size="sm">
              Your AI front desk dashboard.
            </Text>
          </div>

          <form onSubmit={handleSubmit}>
            <Stack>
              <TextInput
                label="Email"
                placeholder="owner@example.com"
                autoComplete="email"
                {...form.getInputProps("email")}
              />
              <PasswordInput
                label="Password"
                placeholder="••••••••"
                autoComplete="current-password"
                {...form.getInputProps("password")}
              />
              <Button type="submit" loading={submitting} fullWidth>
                Sign in
              </Button>
            </Stack>
          </form>

          <Group justify="center" gap="xs">
            <Text size="sm" c="dimmed">
              New here?
            </Text>
            <Anchor component={Link} to="/register" size="sm">
              Create an account
            </Anchor>
          </Group>
        </Stack>
      </Card>
    </Stack>
  );
}
