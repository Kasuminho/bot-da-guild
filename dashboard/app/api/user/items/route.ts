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

  const [total, items] = await Promise.all([
    prisma.item.count({ where }),
    prisma.item.findMany({
      where,
      orderBy: { deliveredAt: "desc" },
      skip,
      take: pageSize,
    }),
  ]);

  return NextResponse.json({
    data: items,
    pagination: {
      page,
      pageSize,
      total,
      totalPages: Math.max(1, Math.ceil(total / pageSize)),
    },
  });
}
