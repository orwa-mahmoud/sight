import {
  Accordion,
  ActionIcon,
  Alert,
  Button,
  Card,
  Center,
  CopyButton,
  Group,
  Loader,
  NumberInput,
  PasswordInput,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
  Tooltip,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconCheck, IconCopy, IconSettings } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "@auth/useAuth";

import {
  getModelCatalog,
  getSettings,
  updateBot,
  updateEmbedding,
  updateLLM,
  updateTelegram,
  updateWhatsApp,
} from "./api";

function WebhookUrlCard({
  channel,
  tenantId,
}: Readonly<{ channel: "whatsapp" | "telegram"; tenantId: string }>) {
  const { t } = useTranslation();
  const origin = globalThis.location?.origin ?? "";
  const url = `${origin}/webhooks/${tenantId}/${channel}`;
  return (
    <Card withBorder p="sm" bg="gray.0" radius="sm">
      <Group justify="space-between" wrap="nowrap" gap="xs">
        <Text size="xs" c="dimmed" style={{ wordBreak: "break-all" }}>
          {t("settings.webhookUrl")} <code>{url}</code>
        </Text>
        <CopyButton value={url}>
          {({ copied, copy }) => (
            <Tooltip label={copied ? t("settings.copied") : t("settings.copy")} withArrow>
              <ActionIcon
                variant="subtle"
                color={copied ? "teal" : "gray"}
                onClick={copy}
                aria-label={t("settings.copy")}
              >
                {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
              </ActionIcon>
            </Tooltip>
          )}
        </CopyButton>
      </Group>
    </Card>
  );
}


const BOT_LANGUAGES = [
  { value: "en", label: "English" },
  { value: "ar", label: "Arabic" },
  { value: "fr", label: "French" },
  { value: "es", label: "Spanish" },
];

function useSectionMutation<T>(fn: (p: T) => Promise<unknown>, section: string, t: TFunction) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      notifications.show({ color: "teal", message: t("settings.updated", { section }) });
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: () => {
      notifications.show({ color: "red", message: t("settings.updateError", { section }) });
    },
  });
}

export function SettingsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const tenantId = user?.tenant.id ?? "{tenant_id}";
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: getSettings });
  const catalogQuery = useQuery({ queryKey: ["model-catalog"], queryFn: getModelCatalog });

  const llmMutation = useSectionMutation(updateLLM, t("settings.llmName"), t);
  const embeddingMutation = useSectionMutation(updateEmbedding, t("settings.embeddingName"), t);
  const whatsappMutation = useSectionMutation(updateWhatsApp, t("settings.whatsappName"), t);
  const telegramMutation = useSectionMutation(updateTelegram, t("settings.telegramName"), t);
  const botMutation = useSectionMutation(updateBot, t("settings.botConfigName"), t);

  const llmForm = useForm({
    initialValues: { provider: "", model: "", api_key: "", max_tokens: 1024, temperature: 0.3, rerank_model: "" },
  });
  const embForm = useForm({ initialValues: { model: "", api_key: "" } });
  const waForm = useForm({
    initialValues: { phone_number_id: "", access_token: "", verify_token: "", app_secret: "" },
  });
  const tgForm = useForm({ initialValues: { bot_token: "", webhook_secret: "" } });
  const botForm = useForm({ initialValues: { name: "", welcome_message: "", language: "" } });

  const settingsData = settingsQuery.data;
  const initialized = useRef(false);
  useEffect(() => {
    if (!settingsData || initialized.current) return;
    initialized.current = true;
    llmForm.setValues({
      provider: settingsData.llm_provider,
      model: settingsData.llm_model,
      max_tokens: settingsData.llm_max_tokens,
      temperature: settingsData.llm_temperature,
      rerank_model: settingsData.rerank_model,
    });
    embForm.setValues({
      model: settingsData.embedding_model,
    });
    waForm.setValues({
      phone_number_id: settingsData.whatsapp_phone_number_id ?? "",
    });
    botForm.setValues({
      name: settingsData.bot_name,
      welcome_message: settingsData.bot_welcome_message,
      language: settingsData.bot_language,
    });
  }, [settingsData, llmForm, embForm, waForm, botForm]);

  if (settingsQuery.isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }
  if (settingsQuery.isError) {
    return <Alert color="red">{t("settings.loadError")}</Alert>;
  }

  const config = settingsQuery.data ?? {
    llm_provider: "",
    llm_model: "",
    llm_api_key_masked: "",
    llm_max_tokens: 1024,
    llm_temperature: 0.3,
    rerank_model: "",
    embedding_provider: "",
    embedding_model: "",
    embedding_api_key_masked: "",
    whatsapp_phone_number_id: null,
    whatsapp_access_token_masked: null,
    whatsapp_verify_token_masked: null,
    whatsapp_app_secret_masked: null,
    telegram_bot_token_masked: null,
    telegram_webhook_secret_masked: null,
    bot_name: "",
    bot_welcome_message: "",
    bot_language: "",
  };

  const current = (masked: string | null | undefined) => `${t("settings.current")} ${masked}`;

  // Provider/model options come from the backend catalog (single source of truth),
  // so the UI never hardcodes a model list. Models are filtered to the selected provider.
  const catalogProviders = catalogQuery.data?.providers ?? [];
  const providerOptions = catalogProviders.map((p) => ({ value: p.provider, label: p.label }));
  const selectedProvider = llmForm.values.provider || config.llm_provider;
  const modelOptions =
    catalogProviders
      .find((p) => p.provider === selectedProvider)
      ?.models.map((m) => ({ value: m.model, label: m.label })) ?? [];
  const embeddingModelOptions = (catalogQuery.data?.embedding_models ?? []).map((m) => ({
    value: m.model,
    label: m.label,
  }));

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>{t("settings.title")}</Title>
          <Text c="dimmed" size="sm">
            {t("settings.subtitle")}
          </Text>
        </div>
        <IconSettings size={24} stroke={1.4} />
      </Group>

      <Accordion variant="separated" radius="md" defaultValue="llm">
        {/* ── LLM ─────────────────────────────────────────────── */}
        <Accordion.Item value="llm">
          <Accordion.Control>{t("settings.llmSection")}</Accordion.Control>
          <Accordion.Panel>
            <form
              onSubmit={llmForm.onSubmit((v) => {
                llmMutation.mutate({
                  ...(v.provider ? { provider: v.provider } : {}),
                  ...(v.model ? { model: v.model } : {}),
                  ...(v.api_key ? { api_key: v.api_key } : {}),
                  ...(v.max_tokens ? { max_tokens: v.max_tokens } : {}),
                  ...(v.temperature === undefined ? {} : { temperature: v.temperature }),
                  ...(v.rerank_model ? { rerank_model: v.rerank_model } : {}),
                });
              })}
            >
              <Stack>
                <Select
                  label={t("settings.provider")}
                  data={providerOptions}
                  placeholder={config.llm_provider}
                  {...llmForm.getInputProps("provider")}
                  onChange={(val) => {
                    // Switching provider invalidates the chosen models — clear them
                    // so the user picks from the new provider's list.
                    llmForm.setFieldValue("provider", val ?? "");
                    llmForm.setFieldValue("model", "");
                    llmForm.setFieldValue("rerank_model", "");
                  }}
                />
                <Select
                  label={t("settings.model")}
                  data={modelOptions}
                  placeholder={config.llm_model}
                  searchable
                  {...llmForm.getInputProps("model")}
                />
                <TextInput
                  label={t("settings.rerankModel")}
                  description={t("settings.rerankModelHint")}
                  placeholder={config.rerank_model}
                  {...llmForm.getInputProps("rerank_model")}
                />
                <PasswordInput
                  label={t("settings.apiKey")}
                  placeholder={t("settings.enterNewKey")}
                  description={
                    config.llm_api_key_masked ? current(config.llm_api_key_masked) : t("settings.notSet")
                  }
                  {...llmForm.getInputProps("api_key")}
                />
                <Group grow>
                  <NumberInput
                    label={t("settings.maxTokens")}
                    min={1}
                    max={128000}
                    placeholder={String(config.llm_max_tokens)}
                    {...llmForm.getInputProps("max_tokens")}
                  />
                  <NumberInput
                    label={t("settings.temperature")}
                    min={0}
                    max={2}
                    step={0.1}
                    decimalScale={1}
                    placeholder={String(config.llm_temperature)}
                    {...llmForm.getInputProps("temperature")}
                  />
                </Group>
                <Button type="submit" loading={llmMutation.isPending}>
                  {t("settings.saveLlm")}
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>

        {/* ── Embedding ───────────────────────────────────────── */}
        <Accordion.Item value="embedding">
          <Accordion.Control>{t("settings.embeddingSection")}</Accordion.Control>
          <Accordion.Panel>
            <form
              onSubmit={embForm.onSubmit((v) => {
                embeddingMutation.mutate({
                  ...(v.model ? { model: v.model } : {}),
                  ...(v.api_key ? { api_key: v.api_key } : {}),
                });
              })}
            >
              <Stack>
                <Select
                  label={t("settings.model")}
                  data={embeddingModelOptions}
                  placeholder={config.embedding_model}
                  searchable
                  {...embForm.getInputProps("model")}
                />
                <PasswordInput
                  label={t("settings.embApiKey")}
                  description={
                    config.embedding_api_key_masked
                      ? current(config.embedding_api_key_masked)
                      : t("settings.usingLlmKey")
                  }
                  {...embForm.getInputProps("api_key")}
                />
                <Button type="submit" loading={embeddingMutation.isPending}>
                  {t("settings.saveEmbedding")}
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>

        {/* ── WhatsApp ────────────────────────────────────────── */}
        <Accordion.Item value="whatsapp">
          <Accordion.Control>{t("settings.whatsappSection")}</Accordion.Control>
          <Accordion.Panel>
            <form
              onSubmit={waForm.onSubmit((v) => {
                whatsappMutation.mutate({
                  ...(v.phone_number_id ? { phone_number_id: v.phone_number_id } : {}),
                  ...(v.access_token ? { access_token: v.access_token } : {}),
                  ...(v.verify_token ? { verify_token: v.verify_token } : {}),
                  ...(v.app_secret ? { app_secret: v.app_secret } : {}),
                });
              })}
            >
              <Stack>
                <TextInput
                  label={t("settings.phoneNumberId")}
                  placeholder={config.whatsapp_phone_number_id || t("settings.notSet")}
                  {...waForm.getInputProps("phone_number_id")}
                />
                <PasswordInput
                  label={t("settings.accessToken")}
                  description={
                    config.whatsapp_access_token_masked
                      ? current(config.whatsapp_access_token_masked)
                      : t("settings.notSet")
                  }
                  {...waForm.getInputProps("access_token")}
                />
                <PasswordInput
                  label={t("settings.verifyToken")}
                  description={
                    config.whatsapp_verify_token_masked
                      ? current(config.whatsapp_verify_token_masked)
                      : t("settings.notSet")
                  }
                  {...waForm.getInputProps("verify_token")}
                />
                <PasswordInput
                  label={t("settings.appSecret")}
                  description={
                    config.whatsapp_app_secret_masked
                      ? current(config.whatsapp_app_secret_masked)
                      : t("settings.appSecretNotSet")
                  }
                  {...waForm.getInputProps("app_secret")}
                />
                <WebhookUrlCard channel="whatsapp" tenantId={tenantId} />
                <Button type="submit" loading={whatsappMutation.isPending}>
                  {t("settings.saveWhatsapp")}
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>

        {/* ── Telegram ────────────────────────────────────────── */}
        <Accordion.Item value="telegram">
          <Accordion.Control>{t("settings.telegramSection")}</Accordion.Control>
          <Accordion.Panel>
            <form
              onSubmit={tgForm.onSubmit((v) => {
                telegramMutation.mutate({
                  ...(v.bot_token ? { bot_token: v.bot_token } : {}),
                  ...(v.webhook_secret ? { webhook_secret: v.webhook_secret } : {}),
                });
              })}
            >
              <Stack>
                <PasswordInput
                  label={t("settings.botToken")}
                  description={
                    config.telegram_bot_token_masked
                      ? current(config.telegram_bot_token_masked)
                      : t("settings.botTokenNotSet")
                  }
                  {...tgForm.getInputProps("bot_token")}
                />
                <PasswordInput
                  label={t("settings.webhookSecret")}
                  description={
                    config.telegram_webhook_secret_masked
                      ? current(config.telegram_webhook_secret_masked)
                      : t("settings.notSet")
                  }
                  {...tgForm.getInputProps("webhook_secret")}
                />
                <WebhookUrlCard channel="telegram" tenantId={tenantId} />
                <Button type="submit" loading={telegramMutation.isPending}>
                  {t("settings.saveTelegram")}
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>

        {/* ── Bot Personality ──────────────────────────────────── */}
        <Accordion.Item value="bot">
          <Accordion.Control>{t("settings.botSection")}</Accordion.Control>
          <Accordion.Panel>
            <form
              onSubmit={botForm.onSubmit((v) => {
                botMutation.mutate({
                  ...(v.name ? { name: v.name } : {}),
                  ...(v.welcome_message ? { welcome_message: v.welcome_message } : {}),
                  ...(v.language ? { language: v.language } : {}),
                });
              })}
            >
              <Stack>
                <TextInput
                  label={t("settings.botNameLabel")}
                  placeholder={config.bot_name}
                  {...botForm.getInputProps("name")}
                />
                <Textarea
                  label={t("settings.welcomeMessage")}
                  placeholder={config.bot_welcome_message}
                  autosize
                  minRows={2}
                  {...botForm.getInputProps("welcome_message")}
                />
                <Select
                  label={t("settings.language")}
                  data={BOT_LANGUAGES}
                  placeholder={config.bot_language}
                  {...botForm.getInputProps("language")}
                />
                <Button type="submit" loading={botMutation.isPending}>
                  {t("settings.saveBot")}
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  );
}
