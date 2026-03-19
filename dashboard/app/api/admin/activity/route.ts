import { NextResponse } from "next/server";

import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/session";

export async function GET() {
  const { response } = await requireAdmin();

  if (response) {
    return response;
  }

  const [logs, commands] = await Promise.all([
    prisma.log.findMany({
      orderBy: { createdAt: "desc" },
      take: 10,
      include: { user: { select: { username: true } } },
    }),
    prisma.command.findMany({
      orderBy: { createdAt: "desc" },
      take: 10,
      include: { executor: { select: { username: true } } },
    }),
  ]);

  const feed = [
    ...logs.map((log) => ({
      id: log.id,
      type: "log",
      label: log.action,
      actor: log.user.username,
      createdAt: log.createdAt,
    })),
    ...commands.map((command) => ({
      id: command.id,
      type: "command",
      label: command.command,
      actor: command.executor.username,
      status: command.status,
      createdAt: command.createdAt,
    })),
  ].sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());

  return NextResponse.json({ data: feed.slice(0, 20) });
}
