import { CommandStatus } from "@prisma/client";
import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

import { executeBotCommand } from "@/lib/bot-api";
import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/session";

const commandSchema = z.object({
  command: z.string().trim().min(1).max(200),
  userId: z.string().trim().min(1).max(100),
});

export async function GET() {
  const { response } = await requireAdmin();

  if (response) {
    return response;
  }

  const commands = await prisma.command.findMany({
    orderBy: { createdAt: "desc" },
    take: 20,
    include: {
      executor: {
        select: {
          username: true,
          discordId: true,
        },
      },
    },
  });

  return NextResponse.json({ data: commands });
}

export async function POST(request: NextRequest) {
  const { session, response } = await requireAdmin();

  if (response || !session) {
    return response;
  }

  const payload = await request.json().catch(() => null);
  const parsed = commandSchema.safeParse(payload);

  if (!parsed.success) {
    return NextResponse.json(
      { error: "Invalid payload", details: parsed.error.flatten() },
      { status: 400 },
    );
  }

  const pendingCommand = await prisma.command.create({
    data: {
      executedBy: session.user.id,
      command: parsed.data.command,
      status: CommandStatus.pending,
      result: JSON.stringify({ targetUserId: parsed.data.userId }),
    },
  });

  const botResponse = await executeBotCommand(parsed.data.command, parsed.data.userId);
  const status = botResponse.ok ? CommandStatus.success : CommandStatus.error;

  const updatedCommand = await prisma.command.update({
    where: { id: pendingCommand.id },
    data: {
      status,
      result: JSON.stringify(botResponse.data),
    },
  });

  await prisma.log.create({
    data: {
      userId: session.user.id,
      action: botResponse.ok ? "BOT_COMMAND_EXECUTED" : "BOT_COMMAND_FAILED",
      metadata: JSON.stringify({
        commandId: updatedCommand.id,
        command: parsed.data.command,
        targetUserId: parsed.data.userId,
        response: botResponse.data,
      }),
    },
  });

  return NextResponse.json(
    {
      data: updatedCommand,
      botResponse: botResponse.data,
    },
    { status: botResponse.ok ? 200 : 502 },
  );
}
