import { CommandStatus, Prisma, UserRole, type DashboardUser } from "@prisma/client";

import { env } from "@/lib/env";
import { prisma } from "@/lib/prisma";

type DashboardUserRecord = DashboardUser;
type DashboardCommandWithExecutor = Prisma.DashboardCommandGetPayload<{
  include: { executor: { select: { username: true } } };
}>;

function isMissingDashboardTableError(error: unknown) {
  return error instanceof Prisma.PrismaClientKnownRequestError
    && error.code === "P2021"
    && typeof error.meta?.table === "string"
    && ["main.dashboard_users", "main.dashboard_commands", "dashboard_users", "dashboard_commands"].includes(
      error.meta.table,
    );
}

export function getFallbackRole(discordId: string) {
  return env.adminDiscordIds.includes(discordId) ? UserRole.admin : UserRole.user;
}

export async function findDashboardUserByDiscordId(discordId: bigint) {
  try {
    return await prisma.dashboardUser.findUnique({ where: { discordId } });
  } catch (error) {
    if (isMissingDashboardTableError(error)) {
      return null;
    }

    throw error;
  }
}

export async function syncDashboardUser(discordId: string, username: string, avatar?: string | null) {
  const normalizedDiscordId = BigInt(discordId);
  const role = getFallbackRole(discordId);

  try {
    return await prisma.dashboardUser.upsert({
      where: { discordId: normalizedDiscordId },
      update: { username, avatar: avatar ?? null, role },
      create: { discordId: normalizedDiscordId, username, avatar: avatar ?? null, role },
    });
  } catch (error) {
    if (isMissingDashboardTableError(error)) {
      return {
        id: `fallback-${discordId}`,
        discordId: normalizedDiscordId,
        username,
        avatar: avatar ?? null,
        role,
        createdAt: new Date(0),
        updatedAt: new Date(0),
      } satisfies DashboardUserRecord;
    }

    throw error;
  }
}

export async function listDashboardCommands() {
  try {
    return await prisma.dashboardCommand.findMany({
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
  } catch (error) {
    if (isMissingDashboardTableError(error)) {
      return [] satisfies DashboardCommandWithExecutor[];
    }

    throw error;
  }
}

export async function createPendingDashboardCommand(input: { executedById: string; targetUserId: bigint; command: string }) {
  try {
    return await prisma.dashboardCommand.create({
      data: {
        executedById: input.executedById,
        targetUserId: input.targetUserId,
        command: input.command,
        status: CommandStatus.pending,
        result: JSON.stringify({ targetUserId: input.targetUserId.toString() }),
      },
    });
  } catch (error) {
    if (isMissingDashboardTableError(error)) {
      return null;
    }

    throw error;
  }
}

export async function updateDashboardCommandResult(input: { id: string; status: CommandStatus; result: unknown }) {
  try {
    return await prisma.dashboardCommand.update({
      where: { id: input.id },
      data: {
        status: input.status,
        result: JSON.stringify(input.result),
      },
      include: {
        executor: {
          select: { username: true },
        },
      },
    });
  } catch (error) {
    if (isMissingDashboardTableError(error)) {
      return null;
    }

    throw error;
  }
}

export async function listActivityDashboardCommands() {
  try {
    return await prisma.dashboardCommand.findMany({
      orderBy: { createdAt: "desc" },
      take: 12,
      include: { executor: true },
    });
  } catch (error) {
    if (isMissingDashboardTableError(error)) {
      return [];
    }

    throw error;
  }
}
