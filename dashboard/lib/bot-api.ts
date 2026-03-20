import { env } from "@/lib/env";

export async function executeBotCommand(command: string, userId: string) {
  if (!env.botCommandBridgeEnabled) {
    return {
      ok: false,
      status: 503,
      data: {
        message: "Bot command bridge disabled. Configure BOT_COMMAND_ENDPOINT to enable it.",
      },
    };
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), env.botApiTimeoutMs);

  try {
    const response = await fetch(`${env.botApiBaseUrl}${env.botCommandEndpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ command, userId }),
      signal: controller.signal,
      cache: "no-store",
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        data,
      };
    }

    return {
      ok: true,
      status: response.status,
      data,
    };
  } catch (error) {
    return {
      ok: false,
      status: 500,
      data: {
        message: error instanceof Error ? error.message : "Unknown bot API error",
      },
    };
  } finally {
    clearTimeout(timeout);
  }
}

export async function fetchBotStatus() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), env.botApiTimeoutMs);

  try {
    const response = await fetch(`${env.botApiBaseUrl}${env.botStatusEndpoint}`, {
      method: "GET",
      signal: controller.signal,
      cache: "no-store",
    });

    const data = await response.json().catch(() => ({}));

    return {
      ok: response.ok,
      status: response.status,
      data,
    };
  } catch (error) {
    return {
      ok: false,
      status: 500,
      data: {
        status: "offline",
        message: error instanceof Error ? error.message : "Unable to reach bot API",
      },
    };
  } finally {
    clearTimeout(timeout);
  }
}
