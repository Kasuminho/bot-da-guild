import { NextRequest, NextResponse } from "next/server";

import { getPaginationParams } from "@/lib/pagination";
import { prisma } from "@/lib/prisma";
import { requireSession } from "@/lib/session";

export async function GET(request: NextRequest) {
  const { session, response } = await requireSession();

  if (response || !session) {
    return response;
  }

  const { page, pageSize, skip } = getPaginationParams(request.nextUrl.searchParams);
  const discordId = BigInt(session.user.discordId);
  const where = { discordId };

  const [total, items] = await Promise.all([
    prisma.drop.count({ where }),
    prisma.drop.findMany({
      where,
      orderBy: { deliveredAt: "desc" },
      skip,
      take: pageSize,
    }),
  ]);

  return NextResponse.json({
    data: items.map((item) => ({
      ...item,
      discordId: item.discordId?.toString() ?? null,
      threadId: item.threadId?.toString() ?? null,
      staffId: item.staffId?.toString() ?? null,
    })),
    pagination: {
      page,
      pageSize,
      total,
      totalPages: Math.max(1, Math.ceil(total / pageSize)),
    },
  });
}
