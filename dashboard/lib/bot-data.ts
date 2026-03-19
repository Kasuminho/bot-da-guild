import type { ItemRequestLog } from "@prisma/client";

import { prisma } from "@/lib/prisma";
import { parseJson } from "@/lib/utils";

export function discordIdToBigInt(discordId: string) {
  return BigInt(discordId);
}

export function epochToLocaleString(epoch?: number | null) {
  if (!epoch) return "—";
  return new Date(epoch * 1000).toLocaleString();
}

export async function getPlayerSnapshot(discordId: string) {
  const normalizedDiscordId = discordIdToBigInt(discordId);

  const [player, dropCount, drops, requestCount, itemRequests, dkpTransactions, auditLogs] = await Promise.all([
    prisma.player.findUnique({ where: { discordId: normalizedDiscordId } }),
    prisma.drop.count({ where: { discordId: normalizedDiscordId } }),
    prisma.drop.findMany({
      where: { discordId: normalizedDiscordId },
      orderBy: { deliveredAt: "desc" },
      take: 10,
    }),
    prisma.itemRequest.count({ where: { discordId: normalizedDiscordId } }),
    prisma.itemRequest.findMany({
      where: { discordId: normalizedDiscordId },
      orderBy: [{ itemName: "asc" }, { rankPosition: "asc" }],
      take: 10,
    }),
    prisma.dkpTransaction.findMany({
      where: { userId: normalizedDiscordId },
      orderBy: { createdAt: "desc" },
      take: 20,
    }),
    prisma.auditLog.findMany({
      where: {
        OR: [
          { actorUserId: normalizedDiscordId },
          { entityId: discordId },
        ],
      },
      orderBy: { createdAt: "desc" },
      take: 20,
    }),
  ]);

  return {
    player,
    dropCount,
    drops,
    requestCount,
    itemRequests,
    dkpTransactions,
    auditLogs,
    dkpBalance: dkpTransactions.reduce((total, row) => total + row.amount, 0),
  };
}

export async function getUserTimeline(discordId: string) {
  const normalizedDiscordId = discordIdToBigInt(discordId);
  const requests = await prisma.itemRequest.findMany({
    where: { discordId: normalizedDiscordId },
    select: { id: true, itemName: true },
  });

  const requestIds = requests.map((request) => request.id);
  const requestNameMap = new Map(requests.map((request) => [request.id, request.itemName]));

  let requestLogs: ItemRequestLog[] = [];
  if (requestIds.length > 0) {
    requestLogs = await prisma.itemRequestLog.findMany({
      where: { requestId: { in: requestIds } },
      orderBy: { createdAt: "desc" },
      take: 30,
    });
  }

  const [drops, dkpTransactions, auditLogs] = await Promise.all([
    prisma.drop.findMany({ where: { discordId: normalizedDiscordId }, orderBy: { deliveredAt: "desc" }, take: 30 }),
    prisma.dkpTransaction.findMany({ where: { userId: normalizedDiscordId }, orderBy: { createdAt: "desc" }, take: 30 }),
    prisma.auditLog.findMany({
      where: {
        OR: [
          { actorUserId: normalizedDiscordId },
          { entityId: discordId },
        ],
      },
      orderBy: { createdAt: "desc" },
      take: 30,
    }),
  ]);

  return [
    ...drops.map((drop) => ({
      id: `drop-${drop.id}`,
      source: "delivery",
      title: drop.item ?? "Item delivery",
      description: `Delivered by staff ${drop.staffId?.toString() ?? "unknown"}`,
      createdAt: drop.deliveredAt ?? 0,
      metadata: {
        threadId: drop.threadId?.toString() ?? null,
      },
    })),
    ...requestLogs.map((log) => ({
      id: `request-log-${log.id}`,
      source: "request",
      title: `${log.action} · ${requestNameMap.get(log.requestId) ?? "request"}`,
      description: log.info ?? "Request log entry",
      createdAt: log.createdAt,
      metadata: {
        threadId: log.threadId?.toString() ?? null,
      },
    })),
    ...dkpTransactions.map((transaction) => ({
      id: `dkp-${transaction.id}`,
      source: "dkp",
      title: `${transaction.amount > 0 ? "+" : ""}${transaction.amount} DKP`,
      description: transaction.reason,
      createdAt: transaction.createdAt,
      metadata: {
        createdByUserId: transaction.createdByUserId.toString(),
        eventId: transaction.eventId,
      },
    })),
    ...auditLogs.map((log) => ({
      id: `audit-${log.id}`,
      source: "audit",
      title: log.action,
      description: `${log.entityType} ${log.entityId ?? ""}`.trim(),
      createdAt: log.createdAt,
      metadata: parseJson<Record<string, unknown>>(log.detailsJson, {}),
    })),
  ].sort((left, right) => right.createdAt - left.createdAt);
}

export async function getAdminActivity() {
  const [auditLogs, drops, requestLogs, commands] = await Promise.all([
    prisma.auditLog.findMany({ orderBy: { createdAt: "desc" }, take: 12 }),
    prisma.drop.findMany({ orderBy: { deliveredAt: "desc" }, take: 12 }),
    prisma.itemRequestLog.findMany({ orderBy: { createdAt: "desc" }, take: 12 }),
    prisma.dashboardCommand.findMany({
      orderBy: { createdAt: "desc" },
      take: 12,
      include: { executor: true },
    }),
  ]);

  return [
    ...auditLogs.map((log) => ({
      id: `audit-${log.id}`,
      type: "audit",
      label: log.action,
      actor: log.actorUserId.toString(),
      createdAt: new Date(log.createdAt * 1000).toISOString(),
      status: log.entityType,
    })),
    ...drops.map((drop) => ({
      id: `drop-${drop.id}`,
      type: "delivery",
      label: drop.item ?? "Item delivered",
      actor: drop.nicknameIngame ?? drop.discordId?.toString() ?? "unknown",
      createdAt: new Date((drop.deliveredAt ?? 0) * 1000).toISOString(),
      status: "drop",
    })),
    ...requestLogs.map((log) => ({
      id: `request-log-${log.id}`,
      type: "request",
      label: log.action,
      actor: log.requestId.toString(),
      createdAt: new Date(log.createdAt * 1000).toISOString(),
      status: log.info ?? "request-log",
    })),
    ...commands.map((command) => ({
      id: `command-${command.id}`,
      type: "command",
      label: command.command,
      actor: command.executor.username,
      createdAt: command.createdAt.toISOString(),
      status: command.status,
    })),
  ].sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());
}
