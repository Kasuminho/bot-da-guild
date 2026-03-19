import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";

import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export default async function ActivityFeedPage() {
  const session = await getServerSession(authOptions);

  if (!session?.user) {
    redirect("/login");
  }

  if (session.user.role !== "admin") {
    redirect("/dashboard");
  }

  const [logs, commands] = await Promise.all([
    prisma.log.findMany({
      orderBy: { createdAt: "desc" },
      take: 8,
      include: { user: { select: { username: true } } },
    }),
    prisma.command.findMany({
      orderBy: { createdAt: "desc" },
      take: 8,
      include: { executor: { select: { username: true } } },
    }),
  ]);

  const feed = [
    ...logs.map((log) => ({
      id: log.id,
      type: "log" as const,
      label: log.action,
      actor: log.user.username,
      createdAt: log.createdAt.toISOString(),
    })),
    ...commands.map((command) => ({
      id: command.id,
      type: "command" as const,
      label: command.command,
      actor: command.executor.username,
      createdAt: command.createdAt.toISOString(),
      status: command.status,
    })),
  ].sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime());

  return (
    <Card>
      <CardHeader>
        <CardTitle>Real-time activity feed</CardTitle>
      </CardHeader>
      <CardContent>
        <ActivityFeed initialEntries={feed.slice(0, 20)} />
      </CardContent>
    </Card>
  );
}
