import { getServerSession } from "next-auth";
import { NextResponse } from "next/server";

import { authOptions } from "@/lib/auth";

export async function requireSession() {
  const session = await getServerSession(authOptions);

  if (!session?.user) {
    return {
      response: NextResponse.json({ error: "Unauthorized" }, { status: 401 }),
      session: null,
    };
  }

  return { session, response: null };
}

export async function requireAdmin() {
  const { session, response } = await requireSession();

  if (response || !session) {
    return { session: null, response };
  }

  if (session.user.role !== "admin") {
    return {
      session: null,
      response: NextResponse.json({ error: "Forbidden" }, { status: 403 }),
    };
  }

  return { session, response: null };
}
