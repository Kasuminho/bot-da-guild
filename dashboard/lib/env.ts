const BOT_API_TIMEOUT_MS = Number(process.env.BOT_API_TIMEOUT_MS ?? 10000);
const BOT_COMMAND_ENDPOINT = (process.env.BOT_COMMAND_ENDPOINT ?? "").trim();

export const env = {
  appName: process.env.APP_NAME ?? "Bot da Guild Dashboard",
  botApiBaseUrl: process.env.BOT_API_BASE_URL ?? "http://127.0.0.1:10000",
  botApiTimeoutMs: Number.isFinite(BOT_API_TIMEOUT_MS) ? BOT_API_TIMEOUT_MS : 10000,
  botStatusEndpoint: process.env.BOT_STATUS_ENDPOINT ?? "/health",
  botCommandEndpoint: BOT_COMMAND_ENDPOINT,
  botCommandBridgeEnabled: BOT_COMMAND_ENDPOINT.length > 0,
  adminDiscordIds: (process.env.ADMIN_DISCORD_IDS ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean),
};
