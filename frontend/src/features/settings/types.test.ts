import { describe, it, expect } from "vitest";
import type { TenantConfigResponse } from "./types";

describe("TenantConfigResponse type", () => {
  it("has all expected fields", () => {
    const config: TenantConfigResponse = {
      llm_provider: "openai",
      llm_model: "gpt-4o-mini",
      llm_api_key_masked: "****1234",
      llm_max_tokens: 1024,
      llm_temperature: 0.3,
      embedding_provider: "openai",
      embedding_model: "text-embedding-3-large",
      embedding_api_key_masked: "",
      embedding_dimensions: 1536,
      whatsapp_phone_number_id: null,
      whatsapp_access_token_masked: null,
      whatsapp_verify_token_masked: null,
  whatsapp_app_secret_masked: null,
      telegram_bot_token_masked: null,
      telegram_webhook_secret_masked: null,
      bot_name: "FD Bot",
      bot_welcome_message: "Hello!",
      bot_language: "en",
    };
    expect(config.llm_provider).toBe("openai");
    expect(config.bot_name).toBe("FD Bot");
  });
});
