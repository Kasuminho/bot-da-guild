import { CommandStatus } from "@prisma/client";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

import { executeBotCommand } from "@/lib/bot-api";
import { createPendingDashboardCommand, listDashboardCommands, updateDashboardCommandResult } from "@/lib/dashboard-metadata";
import { env } from "@/lib/env";
import { requireAdmin } from "@/lib/session";

const commandSchema = z.object({
  command: z.string().trim().min(1).max(200),
  userId: z.string().trim().regex(/^\d+$/).min(1).max(100),
});

export async function GET() {
  const { response } = await requireAdmin();

  if (response) {
    return response;
  }

  const commands = await listDashboardCommands();

  return NextResponse.json({
    bridgeEnabled: env.botCommandBridgeEnabled,
    data: commands.map((command) => ({
      ...command,
      targetUserId: command.targetUserId?.toString() ?? null,
    })),
  });
}

export async function POST(request: NextRequest) {
  const { session, response } = await requireAdmin();

  if (response || !session) {
    return response;
  }

  if (!env.botCommandBridgeEnabled) {
    return NextResponse.json(
      { error: "Bot command bridge disabled", message: "Configure BOT_COMMAND_ENDPOINT to enable this feature." },
      { status: 503 },
    );
  }

  const payload = await request.json().catch(() => null);
  const parsed = commandSchema.safeParse(payload);

  if (!parsed.success) {
    return NextResponse.json(
      { error: "Invalid payload", details: parsed.error.flatten() },
      { status: 400 },
    );
  }

  const pendingCommand = await createPendingDashboardCommand({
    executedById: session.user.id,
    targetUserId: BigInt(parsed.data.userId),
    command: parsed.data.command,
  });

  const botResponse = await executeBotCommand(parsed.data.command, parsed.data.userId);
  const status = botResponse.ok ? CommandStatus.success : CommandStatus.error;

  const updatedCommand = pendingCommand
    ? await updateDashboardCommandResult({
      id: pendingCommand.id,
      status,
      result: botResponse.data,
    })
    : null;

  return NextResponse.json(
    {
      data: updatedCommand
        ? {
          ...updatedCommand,
          targetUserId: updatedCommand.targetUserId?.toString() ?? null,
        }
        : null,
      botResponse: botResponse.data,
      warning: pendingCommand ? null : "dashboard_commands table is missing; command executed without persistence.",
    },
    { status: botResponse.ok ? 200 : 502 },
  );
}
