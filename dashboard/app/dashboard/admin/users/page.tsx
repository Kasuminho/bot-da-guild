import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PaginationControls } from "@/components/ui/pagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { authOptions } from "@/lib/auth";
import { findDashboardUserByDiscordId, getFallbackRole } from "@/lib/dashboard-metadata";
import { prisma } from "@/lib/prisma";

export default async function AdminUsersPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const session = await getServerSession(authOptions);
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const pageSize = 10;

  if (!session?.user) {
    redirect("/login");
  }

  if (session.user.role !== "admin") {
    redirect("/dashboard");
  }

  const [total, players] = await Promise.all([
    prisma.player.count({ where: { discordId: { not: null } } }),
    prisma.player.findMany({
      where: { discordId: { not: null } },
      orderBy: { id: "desc" },
      skip: (page - 1) * pageSize,
      take: pageSize,
    }),
  ]);

  const rows = await Promise.all(
    players.map(async (player) => {
      const discordId = player.discordId!;
      const [dropsCount, requestsCount, dkpBalance, dashboardUser] = await Promise.all([
        prisma.drop.count({ where: { discordId } }),
        prisma.itemRequest.count({ where: { discordId } }),
        prisma.dkpTransaction.aggregate({
          _sum: { amount: true },
          where: { userId: discordId },
        }),
        findDashboardUserByDiscordId(discordId),
      ]);

      return {
        id: player.id,
        discordId: discordId.toString(),
        nickname: player.nicknameIngame ?? "—",
        language: player.language ?? "—",
        timezone: player.timezone ?? "—",
        role: dashboardUser?.role ?? getFallbackRole(discordId.toString()),
        dropsCount,
        requestsCount,
        dkpBalance: dkpBalance._sum.amount ?? 0,
      };
    }),
  );

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Registered bot players</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Discord ID</TableHead>
                <TableHead>Nickname</TableHead>
                <TableHead>Language</TableHead>
                <TableHead>Timezone</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Drops</TableHead>
                <TableHead>Requests</TableHead>
                <TableHead>DKP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>{user.discordId}</TableCell>
                  <TableCell>{user.nickname}</TableCell>
                  <TableCell>{user.language}</TableCell>
                  <TableCell>{user.timezone}</TableCell>
                  <TableCell>
                    <Badge variant={user.role === "admin" ? "success" : "secondary"}>{user.role}</Badge>
                  </TableCell>
                  <TableCell>{user.dropsCount}</TableCell>
                  <TableCell>{user.requestsCount}</TableCell>
                  <TableCell>{user.dkpBalance}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <PaginationControls page={page} totalPages={totalPages} pathname="/dashboard/admin/users" />
      </CardContent>
    </Card>
  );
}
