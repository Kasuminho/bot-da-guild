import { NextResponse } from "next/server";

import { getAdminActivity } from "@/lib/bot-data";
import { requireAdmin } from "@/lib/session";

export async function GET() {
  const { response } = await requireAdmin();

  if (response) {
    return response;
  }

  const feed = await getAdminActivity();
  return NextResponse.json({ data: feed.slice(0, 20) });
}
