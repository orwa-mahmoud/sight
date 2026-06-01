import { Anchor, Button, Card, Group, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "./useAuth";

export function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const form = useForm({
    initialValues: {
      email: "",
      password: "",
      full_name: "",
      tenant_name: "",
      tenant_slug: "",
    },
    validate: {
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : "Enter a valid email"),
      password: (v) => (v.length >= 8 ? null : "At least 8 characters"),
      tenant_name: (v) => (v.trim().length > 0 ? null : "Required"),
      tenant_slug: (v) =>
        /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(v) && v.length >= 2
          ? null
          : "Lowercase letters, digits, and hyphens; min 2 chars",
    },
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setSubmitting(true);
    try {
      await register({
        email: values.email,
        password: values.password,
        full_name: values.full_name || undefined,
        tenant_name: values.tenant_name,
        tenant_slug: values.tenant_slug,
      });
      navigate("/", { replace: true });
    } catch {
      notifications.show({
        color: "red",
        message: "Could not create the account. Email or slug may already exist.",
      });
    } finally {
      setSubmitting(false);
    }
  });

  if (user) return <Navigate to="/" replace />;

  return (
    <Stack align="center" justify="center" mih="100vh" px="md" py="lg">
      <Card shadow="md" radius="lg" p="xl" w={460} withBorder>
        <Stack>
          <div>
            <Title order={2} mb={4}>
              Create your front desk
            </Title>
            <Text c="dimmed" size="sm">
              Sets up your tenant and owner account in one step.
            </Text>
          </div>

          <form onSubmit={handleSubmit}>
            <Stack>
              <TextInput label="Your name" placeholder="Optional" {...form.getInputProps("full_name")} />
              <TextInput label="Email" placeholder="you@example.com" {...form.getInputProps("email")} />
              <PasswordInput label="Password" {...form.getInputProps("password")} />
              <TextInput
                label="Tenant display name"
                placeholder="Acme Front Desk"
                {...form.getInputProps("tenant_name")}
              />
              <TextInput
                label="Tenant slug"
                placeholder="acme"
                description="Used as an internal identifier. Lowercase letters, digits, hyphens."
                {...form.getInputProps("tenant_slug")}
              />
              <Button type="submit" loading={submitting} fullWidth>
                Create account
              </Button>
            </Stack>
          </form>

          <Group justify="center" gap="xs">
            <Text size="sm" c="dimmed">
              Already have an account?
            </Text>
            <Anchor component={Link} to="/login" size="sm">
              Sign in
            </Anchor>
          </Group>
        </Stack>
      </Card>
    </Stack>
  );
}
