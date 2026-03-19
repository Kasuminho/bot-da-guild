import { NextRequest, NextResponse } from "next/server";

import { getPaginationParams } from "@/lib/pagination";
import { getUserTimeline } from "@/lib/bot-data";
import { requireSession } from "@/lib/session";

export async function GET(request: NextRequest) {
  const { session, response } = await requireSession();

  if (response || !session) {
    return response;
  }

  const { page, pageSize, skip } = getPaginationParams(request.nextUrl.searchParams);
  const timeline = await getUserTimeline(session.user.discordId);
  const data = timeline.slice(skip, skip + pageSize);

  return NextResponse.json({
    data,
    pagination: {
      page,
      pageSize,
      total: timeline.length,
      totalPages: Math.max(1, Math.ceil(timeline.length / pageSize)),
    },
  });
}
