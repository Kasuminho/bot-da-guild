import { getServerSession } from "next-auth";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PaginationControls } from "@/components/ui/pagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { authOptions } from "@/lib/auth";
import { epochToLocaleString } from "@/lib/bot-data";
import { prisma } from "@/lib/prisma";

export default async function ItemsPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const session = await getServerSession(authOptions);
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const pageSize = 10;

  if (!session?.user) {
    return null;
  }

  const isAdmin = session.user.role === "admin";
  const where = isAdmin ? {} : { discordId: BigInt(session.user.discordId) };
  const [total, drops] = await Promise.all([
    prisma.drop.count({ where }),
    prisma.drop.findMany({
      where,
      orderBy: { deliveredAt: "desc" },
      skip: (page - 1) * pageSize,
      take: pageSize,
    }),
  ]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isAdmin ? "Delivered items across the guild" : "Delivered items"}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                {isAdmin ? <TableHead>Player</TableHead> : null}
                <TableHead>Item</TableHead>
                <TableHead>Nickname</TableHead>
                <TableHead>Thread</TableHead>
                <TableHead>Staff ID</TableHead>
                <TableHead>Delivered at</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {drops.length > 0 ? (
                drops.map((drop) => (
                  <TableRow key={drop.id}>
                    {isAdmin ? <TableCell>{drop.discordId?.toString() ?? "—"}</TableCell> : null}
                    <TableCell>{drop.item ?? "—"}</TableCell>
                    <TableCell>{drop.nicknameIngame ?? "—"}</TableCell>
                    <TableCell>{drop.threadId?.toString() ?? "—"}</TableCell>
                    <TableCell>{drop.staffId?.toString() ?? "—"}</TableCell>
                    <TableCell>{epochToLocaleString(drop.deliveredAt)}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={isAdmin ? 6 : 5} className="text-center text-muted-foreground">
                    No delivered items were found for this view yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
        <PaginationControls page={page} totalPages={totalPages} pathname="/dashboard/items" />
      </CardContent>
    </Card>
  );
}
