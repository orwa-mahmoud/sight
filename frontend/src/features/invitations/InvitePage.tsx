import { Alert, Anchor, Button, Card, Center, Group, Loader, PasswordInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle, IconUsers } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useAuth } from "@auth/useAuth";

import { acceptInvitation, previewInvitation, registerViaInvitation, rejectInvitation } from "./api";

export function InvitePage() {
  const { t } = useTranslation();
  const { token = "" } = useParams();
  const navigate = useNavigate();
  const { user, refresh } = useAuth();
  const [busy, setBusy] = useState(false);

  const previewQuery = useQuery({
    queryKey: ["invite-preview", token],
    queryFn: () => previewInvitation(token),
    retry: false,
    enabled: Boolean(token),
  });

  const form = useForm({
    initialValues: { full_name: "", password: "" },
    validate: {
      password: (v) => (v.length >= 8 ? null : t("invite.passwordTooShort")),
    },
  });

  if (previewQuery.isLoading) {
    return (
      <Center mih="100vh">
        <Loader />
      </Center>
    );
  }

  const preview = previewQuery.data;
  const invalid = previewQuery.isError || !preview || !preview.valid;

  const shell = (children: React.ReactNode) => (
    <Center mih="100vh" p="md">
      <Card withBorder radius="md" p="xl" maw={440} w="100%">
        <Stack>
          <Group gap="xs">
            <IconUsers size={22} color="var(--mantine-color-coral-6)" />
            <Title order={3}>{t("invite.title")}</Title>
          </Group>
          {children}
        </Stack>
      </Card>
    </Center>
  );

  if (invalid) {
    return shell(
      <>
        <Alert variant="light" color="red" icon={<IconAlertCircle size={18} />}>
          {t("invite.invalid")}
        </Alert>
        <Anchor component={Link} to="/login">
          {t("invite.goToLogin")}
        </Anchor>
      </>,
    );
  }

  const accept = async () => {
    setBusy(true);
    try {
      await acceptInvitation(token);
      await refresh();
      notifications.show({ color: "teal", message: t("invite.accepted") });
      navigate("/");
    } catch {
      notifications.show({ color: "red", message: t("invite.actionFailed") });
    } finally {
      setBusy(false);
    }
  };

  const reject = async () => {
    setBusy(true);
    try {
      await rejectInvitation(token);
      notifications.show({ color: "gray", message: t("invite.rejected") });
      navigate("/login");
    } catch {
      notifications.show({ color: "red", message: t("invite.actionFailed") });
    } finally {
      setBusy(false);
    }
  };

  const registerAndJoin = async (values: { full_name: string; password: string }) => {
    setBusy(true);
    try {
      await registerViaInvitation(token, values.password, values.full_name || undefined);
      await refresh();
      notifications.show({ color: "teal", message: t("invite.joined") });
      navigate("/");
    } catch {
      notifications.show({ color: "red", message: t("invite.actionFailed") });
    } finally {
      setBusy(false);
    }
  };

  const intro = (
    <Text size="sm">
      {t("invite.invitedTo", { tenant: preview.tenant_name, email: preview.email })}
    </Text>
  );

  // Logged in as the invited email → accept / reject.
  if (user && user.email === preview.email) {
    return shell(
      <>
        {intro}
        <Group>
          <Button onClick={accept} loading={busy}>
            {t("invite.accept")}
          </Button>
          <Button variant="default" onClick={reject} loading={busy}>
            {t("invite.reject")}
          </Button>
        </Group>
      </>,
    );
  }

  // Logged in as a different account.
  if (user && user.email !== preview.email) {
    return shell(
      <>
        {intro}
        <Alert variant="light" color="yellow" icon={<IconAlertCircle size={18} />}>
          {t("invite.wrongAccount", { current: user.email, invited: preview.email })}
        </Alert>
        <Anchor component={Link} to="/login">
          {t("invite.switchAccount")}
        </Anchor>
      </>,
    );
  }

  // Not logged in → register through the invite.
  return shell(
    <>
      {intro}
      <Text size="sm" c="dimmed">
        {t("invite.createAccount")}
      </Text>
      <form onSubmit={form.onSubmit(registerAndJoin)}>
        <Stack>
          <TextInput label={t("invite.fullName")} {...form.getInputProps("full_name")} />
          <PasswordInput label={t("invite.password")} required {...form.getInputProps("password")} />
          <Button type="submit" loading={busy} fullWidth>
            {t("invite.joinTenant")}
          </Button>
        </Stack>
      </form>
      <Text size="xs" c="dimmed" ta="center">
        {t("invite.haveAccount")} <Anchor component={Link} to="/login">{t("invite.goToLogin")}</Anchor>
      </Text>
    </>,
  );
}
