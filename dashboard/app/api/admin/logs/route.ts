import { NextRequest, NextResponse } from "next/server";

import { getPaginationParams } from "@/lib/pagination";
import { prisma } from "@/lib/prisma";
import { requireAdmin } from "@/lib/session";

export async function GET(request: NextRequest) {
  const { response } = await requireAdmin();

  if (response) {
    return response;
  }

  const { page, pageSize, skip } = getPaginationParams(request.nextUrl.searchParams);

  const [total, logs] = await Promise.all([
    prisma.log.count(),
    prisma.log.findMany({
      orderBy: { createdAt: "desc" },
      skip,
      take: pageSize,
      include: {
        user: {
          select: {
            username: true,
            discordId: true,
            role: true,
          },
        },
      },
    }),
  ]);

  return NextResponse.json({
    data: logs,
    pagination: {
      page,
      pageSize,
      total,
      totalPages: Math.max(1, Math.ceil(total / pageSize)),
    },
  });
}
