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
  const search = request.nextUrl.searchParams.get("search")?.trim();

  const where = search
    ? {
        OR: [
          { username: { contains: search } },
          { discordId: { contains: search } },
        ],
      }
    : {};

  const [total, users] = await Promise.all([
    prisma.user.count({ where }),
    prisma.user.findMany({
      where,
      skip,
      take: pageSize,
      orderBy: { createdAt: "desc" },
      include: {
        _count: {
          select: { logs: true, items: true, commands: true },
        },
      },
    }),
  ]);

  return NextResponse.json({
    data: users,
    pagination: {
      page,
      pageSize,
      total,
      totalPages: Math.max(1, Math.ceil(total / pageSize)),
    },
  });
}
