import { NextRequest, NextResponse } from "next/server";

import { findDashboardUserByDiscordId, getFallbackRole } from "@/lib/dashboard-metadata";
import { getPaginationParams } from "@/lib/pagination";
import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/session";

export async function GET(request: NextRequest) {
  const { response } = await requireAdmin();

  if (response) {
    return response;
  }

  const { page, pageSize, skip } = getPaginationParams(request.nextUrl.searchParams);
  const [total, players] = await Promise.all([
    prisma.player.count({ where: { discordId: { not: null } } }),
    prisma.player.findMany({
      where: { discordId: { not: null } },
      orderBy: { id: "desc" },
      skip,
      take: pageSize,
    }),
  ]);

  const data = await Promise.all(
    players.map(async (player) => {
      const discordId = player.discordId!;
      const [dropsCount, requestsCount, dkpCount, dashboardUser] = await Promise.all([
        prisma.drop.count({ where: { discordId } }),
        prisma.itemRequest.count({ where: { discordId } }),
        prisma.dkpTransaction.count({ where: { userId: discordId } }),
        findDashboardUserByDiscordId(discordId),
      ]);

      return {
        id: player.id,
        discordId: discordId.toString(),
        nicknameIngame: player.nicknameIngame,
        language: player.language,
        timezone: player.timezone,
        role: dashboardUser?.role ?? getFallbackRole(discordId.toString()),
        dropsCount,
        requestsCount,
        dkpCount,
      };
    }),
  );

  return NextResponse.json({
    data,
    pagination: {
      page,
      pageSize,
      total,
      totalPages: Math.max(1, Math.ceil(total / pageSize)),
    },
  });
}
