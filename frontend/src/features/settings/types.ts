export interface TenantConfigResponse {
  llm_provider: string;
  llm_model: string;
  llm_api_key_masked: string;
  llm_max_tokens: number;
  llm_temperature: number;
  embedding_provider: string;
  embedding_model: string;
  embedding_api_key_masked: string;
  whatsapp_phone_number_id: string | null;
  whatsapp_access_token_masked: string | null;
  whatsapp_verify_token_masked: string | null;
  whatsapp_app_secret_masked: string | null;
  telegram_bot_token_masked: string | null;
  telegram_webhook_secret_masked: string | null;
  bot_name: string;
  bot_welcome_message: string;
  bot_language: string;
}
