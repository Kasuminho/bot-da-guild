import { CommandStatus } from "@prisma/client";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

import { executeBotCommand } from "@/lib/bot-api";
import { env } from "@/lib/env";
import { prisma } from "@/lib/prisma";
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

  const commands = await prisma.dashboardCommand.findMany({
    orderBy: { createdAt: "desc" },
    take: 20,
    include: {
      executor: {
        select: {
          username: true,
        },
      },
    },
  });

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

  const pendingCommand = await prisma.dashboardCommand.create({
    data: {
      executedById: session.user.id,
      targetUserId: BigInt(parsed.data.userId),
      command: parsed.data.command,
      status: CommandStatus.pending,
      result: JSON.stringify({ targetUserId: parsed.data.userId }),
    },
  });

  const botResponse = await executeBotCommand(parsed.data.command, parsed.data.userId);
  const status = botResponse.ok ? CommandStatus.success : CommandStatus.error;

  const updatedCommand = await prisma.dashboardCommand.update({
    where: { id: pendingCommand.id },
    data: {
      status,
      result: JSON.stringify(botResponse.data),
    },
    include: {
      executor: {
        select: { username: true },
      },
    },
  });

  return NextResponse.json(
    {
      data: {
        ...updatedCommand,
        targetUserId: updatedCommand.targetUserId?.toString() ?? null,
      },
      botResponse: botResponse.data,
    },
    { status: botResponse.ok ? 200 : 502 },
  );
}
