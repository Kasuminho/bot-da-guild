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
  const where = { userId: session.user.id };

  const [total, logs] = await Promise.all([
    prisma.log.count({ where }),
    prisma.log.findMany({
      where,
      orderBy: { createdAt: "desc" },
      skip,
      take: pageSize,
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
