import { Anchor, Button, Card, Group, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "./useAuth";

export function RegisterPage() {
  const { t } = useTranslation();
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
      email: (v) => (/^\S+@\S+\.\S+$/.test(v) ? null : t("auth.errInvalidEmail")),
      password: (v) => (v.length >= 8 ? null : t("auth.errPasswordMin")),
      tenant_name: (v) => (v.trim().length > 0 ? null : t("auth.errRequired")),
      tenant_slug: (v) => (/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(v) && v.length >= 2 ? null : t("auth.errSlug")),
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
        message: t("auth.errRegister"),
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
              {t("auth.registerTitle")}
            </Title>
            <Text c="dimmed" size="sm">
              {t("auth.registerSubtitle")}
            </Text>
          </div>

          <form onSubmit={handleSubmit}>
            <Stack>
              <TextInput
                label={t("auth.yourName")}
                placeholder={t("auth.optional")}
                {...form.getInputProps("full_name")}
              />
              <TextInput
                label={t("auth.email")}
                placeholder={t("auth.emailPlaceholderYou")}
                {...form.getInputProps("email")}
              />
              <PasswordInput label={t("auth.password")} {...form.getInputProps("password")} />
              <TextInput
                label={t("auth.tenantName")}
                placeholder={t("auth.tenantNamePlaceholder")}
                {...form.getInputProps("tenant_name")}
              />
              <TextInput
                label={t("auth.tenantSlug")}
                placeholder={t("auth.tenantSlugPlaceholder")}
                description={t("auth.tenantSlugDesc")}
                {...form.getInputProps("tenant_slug")}
              />
              <Button type="submit" loading={submitting} fullWidth>
                {t("auth.createAccountBtn")}
              </Button>
            </Stack>
          </form>

          <Group justify="center" gap="xs">
            <Text size="sm" c="dimmed">
              {t("auth.haveAccount")}
            </Text>
            <Anchor component={Link} to="/login" size="sm">
              {t("auth.signIn")}
            </Anchor>
          </Group>
        </Stack>
      </Card>
    </Stack>
  );
}
