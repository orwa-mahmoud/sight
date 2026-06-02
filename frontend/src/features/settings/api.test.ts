import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@core/api/client", () => ({
  api: { get: vi.fn(), put: vi.fn() },
}));

import { api } from "@core/api/client";
import { getSettings, updateLLM, updateEmbedding, updateWhatsApp, updateTelegram, updateBot } from "./api";

describe("settings API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("getSettings fetches /api/v1/settings", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { llm_provider: "openai" } });
    const result = await getSettings();
    expect(api.get).toHaveBeenCalledWith("/api/v1/settings");
    expect(result).toEqual({ llm_provider: "openai" });
  });

  it("updateLLM puts to /api/v1/settings/llm", async () => {
    const payload = { provider: "anthropic", model: "claude" };
    vi.mocked(api.put).mockResolvedValue({ data: { llm_provider: "anthropic" } });
    const result = await updateLLM(payload);
    expect(api.put).toHaveBeenCalledWith("/api/v1/settings/llm", payload);
    expect(result).toEqual({ llm_provider: "anthropic" });
  });

  it("updateEmbedding puts to /api/v1/settings/embedding", async () => {
    const payload = { model: "text-embedding-3-small" };
    vi.mocked(api.put).mockResolvedValue({ data: { embedding_model: "text-embedding-3-small" } });
    const result = await updateEmbedding(payload);
    expect(api.put).toHaveBeenCalledWith("/api/v1/settings/embedding", payload);
    expect(result).toEqual({ embedding_model: "text-embedding-3-small" });
  });

  it("updateWhatsApp puts to /api/v1/settings/whatsapp", async () => {
    const payload = { phone_number_id: "123" };
    vi.mocked(api.put).mockResolvedValue({ data: { whatsapp_phone_number_id: "123" } });
    const result = await updateWhatsApp(payload);
    expect(api.put).toHaveBeenCalledWith("/api/v1/settings/whatsapp", payload);
    expect(result).toEqual({ whatsapp_phone_number_id: "123" });
  });

  it("updateTelegram puts to /api/v1/settings/telegram", async () => {
    const payload = { bot_token: "tok123" };
    vi.mocked(api.put).mockResolvedValue({ data: { telegram_bot_token_masked: "tok***" } });
    const result = await updateTelegram(payload);
    expect(api.put).toHaveBeenCalledWith("/api/v1/settings/telegram", payload);
    expect(result).toEqual({ telegram_bot_token_masked: "tok***" });
  });

  it("updateBot puts to /api/v1/settings/bot", async () => {
    const payload = { name: "Bot", language: "en" };
    vi.mocked(api.put).mockResolvedValue({ data: { bot_name: "Bot" } });
    const result = await updateBot(payload);
    expect(api.put).toHaveBeenCalledWith("/api/v1/settings/bot", payload);
    expect(result).toEqual({ bot_name: "Bot" });
  });
});
