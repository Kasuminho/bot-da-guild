import { getServerSession } from "next-auth";

import { StatCard } from "@/components/dashboard/stat-card";
import { StatusCard } from "@/components/dashboard/status-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { authOptions } from "@/lib/auth";
import { fetchBotStatus } from "@/lib/bot-api";
import { prisma } from "@/lib/prisma";
import { parseJson } from "@/lib/utils";

export default async function DashboardHome() {
  const session = await getServerSession(authOptions);

  if (!session?.user) {
    return null;
  }

  const [itemsCount, logsCount, latestLogs, botStatus] = await Promise.all([
    prisma.item.count({ where: { userId: session.user.id } }),
    prisma.log.count({ where: { userId: session.user.id } }),
    prisma.log.findMany({
      where: { userId: session.user.id },
      orderBy: { createdAt: "desc" },
      take: 5,
    }),
    fetchBotStatus(),
  ]);

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <StatCard label="Items sent" value={itemsCount} helper="Delivered items visible to the logged-in user." />
        <StatCard label="History logs" value={logsCount} helper="Audit entries retained for this player account." />
        <StatusCard
          status={botStatus.ok ? "online" : "offline"}
          details={botStatus.ok ? "The bot API is responding to health checks." : "The dashboard cannot reach the bot API."}
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Recent activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Action</TableHead>
                  <TableHead>Metadata</TableHead>
                  <TableHead>Created at</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {latestLogs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>{log.action}</TableCell>
                    <TableCell className="max-w-md whitespace-pre-wrap text-xs text-muted-foreground">
                      {JSON.stringify(parseJson(log.metadata, {}), null, 2)}
                    </TableCell>
                    <TableCell>{log.createdAt.toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
