import { NextResponse } from "next/server";

import { requireSession } from "@/lib/session";

export async function GET() {
  const { session, response } = await requireSession();

  if (response || !session) {
    return response;
  }

  return NextResponse.json({ user: session.user });
}
