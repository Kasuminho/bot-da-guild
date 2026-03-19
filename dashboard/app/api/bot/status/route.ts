import { NextResponse } from "next/server";

import { fetchBotStatus } from "@/lib/bot-api";
import { requireSession } from "@/lib/session";

export async function GET() {
  const { session, response } = await requireSession();

  if (response || !session) {
    return response;
  }

  const status = await fetchBotStatus();

  return NextResponse.json({
    status: status.ok ? "online" : "offline",
    httpStatus: status.status,
    details: status.data,
  });
}
