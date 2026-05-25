import {
  Accordion,
  Alert,
  Button,
  Card,
  Center,
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
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { IconSettings } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

import {
  getSettings,
  updateBot,
  updateEmbedding,
  updateLLM,
  updateTelegram,
  updateWhatsApp,
} from "./api";

const LLM_PROVIDERS = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "azure_openai", label: "Azure OpenAI" },
  { value: "google", label: "Google" },
];

function useSectionMutation<T>(fn: (p: T) => Promise<unknown>, label: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      notifications.show({ color: "teal", message: `${label} updated.` });
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: () => {
      notifications.show({ color: "red", message: `Could not update ${label.toLowerCase()}.` });
    },
  });
}

export function SettingsPage() {
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: getSettings });

  const llmMutation = useSectionMutation(updateLLM, "LLM config");
  const embeddingMutation = useSectionMutation(updateEmbedding, "Embedding config");
  const whatsappMutation = useSectionMutation(updateWhatsApp, "WhatsApp config");
  const telegramMutation = useSectionMutation(updateTelegram, "Telegram config");
  const botMutation = useSectionMutation(updateBot, "Bot config");

  const llmForm = useForm({
    initialValues: { provider: "", model: "", api_key: "", max_tokens: 1024, temperature: 0.3 },
  });
  const embForm = useForm({ initialValues: { model: "", api_key: "", dimensions: 1536 } });
  const waForm = useForm({ initialValues: { phone_number_id: "", access_token: "", verify_token: "" } });
  const tgForm = useForm({ initialValues: { bot_token: "", webhook_secret: "" } });
  const botForm = useForm({ initialValues: { name: "", welcome_message: "", language: "" } });

  const settingsData = settingsQuery.data;
  useEffect(() => {
    if (!settingsData) return;
    llmForm.setValues({
      provider: settingsData.llm_provider,
      model: settingsData.llm_model,
      max_tokens: settingsData.llm_max_tokens,
      temperature: settingsData.llm_temperature,
    });
    embForm.setValues({
      model: settingsData.embedding_model,
      dimensions: settingsData.embedding_dimensions,
    });
    waForm.setValues({
      phone_number_id: settingsData.whatsapp_phone_number_id ?? "",
    });
    botForm.setValues({
      name: settingsData.bot_name,
      welcome_message: settingsData.bot_welcome_message,
      language: settingsData.bot_language,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settingsData]);

  if (settingsQuery.isLoading) {
    return (
      <Center py="xl">
        <Loader />
      </Center>
    );
  }
  if (settingsQuery.isError) {
    return <Alert color="red">Could not load settings.</Alert>;
  }

  const config = settingsQuery.data ?? {
    llm_provider: "", llm_model: "", llm_api_key_masked: "", llm_max_tokens: 1024,
    llm_temperature: 0.3, embedding_provider: "", embedding_model: "",
    embedding_api_key_masked: "", embedding_dimensions: 1536,
    whatsapp_phone_number_id: null, whatsapp_access_token_masked: null,
    whatsapp_verify_token_masked: null, telegram_bot_token_masked: null,
    telegram_webhook_secret_masked: null, bot_name: "", bot_welcome_message: "", bot_language: "",
  };

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={2}>Settings</Title>
          <Text c="dimmed" size="sm">
            Configure your LLM provider, channel tokens, and bot personality.
          </Text>
        </div>
        <IconSettings size={24} stroke={1.4} />
      </Group>

      <Accordion variant="separated" radius="md" defaultValue="llm">
        {/* ── LLM ─────────────────────────────────────────────── */}
        <Accordion.Item value="llm">
          <Accordion.Control>LLM Configuration</Accordion.Control>
          <Accordion.Panel>
            <form
              onSubmit={llmForm.onSubmit((v) => {
                llmMutation.mutate({
                  ...(v.provider ? { provider: v.provider } : {}),
                  ...(v.model ? { model: v.model } : {}),
                  ...(v.api_key ? { api_key: v.api_key } : {}),
                  ...(v.max_tokens ? { max_tokens: v.max_tokens } : {}),
                  ...(v.temperature === undefined ? {} : { temperature: v.temperature }),
                });
              })}
            >
              <Stack>
                <Select
                  label="Provider"
                  data={LLM_PROVIDERS}
                  placeholder={config.llm_provider}
                  {...llmForm.getInputProps("provider")}
                />
                <TextInput
                  label="Model"
                  placeholder={config.llm_model}
                  {...llmForm.getInputProps("model")}
                />
                <PasswordInput
                  label="API Key"
                  placeholder="Enter new key"
                  description={config.llm_api_key_masked ? `Current: ${config.llm_api_key_masked}` : "Not set"}
                  {...llmForm.getInputProps("api_key")}
                />
                <Group grow>
                  <NumberInput
                    label="Max tokens"
                    min={1}
                    max={128000}
                    placeholder={String(config.llm_max_tokens)}
                    {...llmForm.getInputProps("max_tokens")}
                  />
                  <NumberInput
                    label="Temperature"
                    min={0}
                    max={2}
                    step={0.1}
                    decimalScale={1}
                    placeholder={String(config.llm_temperature)}
                    {...llmForm.getInputProps("temperature")}
                  />
                </Group>
                <Button type="submit" loading={llmMutation.isPending}>
                  Save LLM config
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>

        {/* ── Embedding ───────────────────────────────────────── */}
        <Accordion.Item value="embedding">
          <Accordion.Control>Embedding Configuration</Accordion.Control>
          <Accordion.Panel>
            <form
              onSubmit={embForm.onSubmit((v) => {
                embeddingMutation.mutate({
                  ...(v.model ? { model: v.model } : {}),
                  ...(v.api_key ? { api_key: v.api_key } : {}),
                  ...(v.dimensions ? { dimensions: v.dimensions } : {}),
                });
              })}
            >
              <Stack>
                <TextInput
                  label="Model"
                  placeholder={config.embedding_model}
                  {...embForm.getInputProps("model")}
                />
                <PasswordInput
                  label="API Key (leave blank to use LLM key)"
                  description={
                    config.embedding_api_key_masked
                      ? `Current: ${config.embedding_api_key_masked}`
                      : "Using LLM key"
                  }
                  {...embForm.getInputProps("api_key")}
                />
                <NumberInput
                  label="Dimensions"
                  min={256}
                  max={4096}
                  placeholder={String(config.embedding_dimensions)}
                  {...embForm.getInputProps("dimensions")}
                />
                <Button type="submit" loading={embeddingMutation.isPending}>
                  Save embedding config
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>

        {/* ── WhatsApp ────────────────────────────────────────── */}
        <Accordion.Item value="whatsapp">
          <Accordion.Control>WhatsApp Cloud API</Accordion.Control>
          <Accordion.Panel>
            <form
              onSubmit={waForm.onSubmit((v) => {
                whatsappMutation.mutate({
                  ...(v.phone_number_id ? { phone_number_id: v.phone_number_id } : {}),
                  ...(v.access_token ? { access_token: v.access_token } : {}),
                  ...(v.verify_token ? { verify_token: v.verify_token } : {}),
                });
              })}
            >
              <Stack>
                <TextInput
                  label="Phone Number ID"
                  placeholder={config.whatsapp_phone_number_id || "Not set"}
                  {...waForm.getInputProps("phone_number_id")}
                />
                <PasswordInput
                  label="Access Token"
                  description={
                    config.whatsapp_access_token_masked
                      ? `Current: ${config.whatsapp_access_token_masked}`
                      : "Not set"
                  }
                  {...waForm.getInputProps("access_token")}
                />
                <PasswordInput
                  label="Verify Token"
                  description={
                    config.whatsapp_verify_token_masked
                      ? `Current: ${config.whatsapp_verify_token_masked}`
                      : "Not set"
                  }
                  {...waForm.getInputProps("verify_token")}
                />
                <Card withBorder p="sm" bg="gray.0" radius="sm">
                  <Text size="xs" c="dimmed">
                    Webhook URL: <code>https://your-domain/webhooks/&#123;tenant_id&#125;/whatsapp</code>
                  </Text>
                </Card>
                <Button type="submit" loading={whatsappMutation.isPending}>
                  Save WhatsApp config
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>

        {/* ── Telegram ────────────────────────────────────────── */}
        <Accordion.Item value="telegram">
          <Accordion.Control>Telegram Bot</Accordion.Control>
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
                  label="Bot Token"
                  description={
                    config.telegram_bot_token_masked
                      ? `Current: ${config.telegram_bot_token_masked}`
                      : "Not set — get one from @BotFather"
                  }
                  {...tgForm.getInputProps("bot_token")}
                />
                <PasswordInput
                  label="Webhook Secret"
                  description={
                    config.telegram_webhook_secret_masked
                      ? `Current: ${config.telegram_webhook_secret_masked}`
                      : "Not set"
                  }
                  {...tgForm.getInputProps("webhook_secret")}
                />
                <Card withBorder p="sm" bg="gray.0" radius="sm">
                  <Text size="xs" c="dimmed">
                    Webhook URL: <code>https://your-domain/webhooks/&#123;tenant_id&#125;/telegram</code>
                  </Text>
                </Card>
                <Button type="submit" loading={telegramMutation.isPending}>
                  Save Telegram config
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>

        {/* ── Bot Personality ──────────────────────────────────── */}
        <Accordion.Item value="bot">
          <Accordion.Control>Bot Personality</Accordion.Control>
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
                  label="Bot Name"
                  placeholder={config.bot_name}
                  {...botForm.getInputProps("name")}
                />
                <Textarea
                  label="Welcome Message"
                  placeholder={config.bot_welcome_message}
                  autosize
                  minRows={2}
                  {...botForm.getInputProps("welcome_message")}
                />
                <Select
                  label="Language"
                  data={[
                    { value: "en", label: "English" },
                    { value: "ar", label: "Arabic" },
                    { value: "fr", label: "French" },
                    { value: "es", label: "Spanish" },
                  ]}
                  placeholder={config.bot_language}
                  {...botForm.getInputProps("language")}
                />
                <Button type="submit" loading={botMutation.isPending}>
                  Save bot config
                </Button>
              </Stack>
            </form>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>
    </Stack>
  );
}
