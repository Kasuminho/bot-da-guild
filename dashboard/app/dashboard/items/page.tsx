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

  const discordId = BigInt(session.user.discordId);
  const [total, drops] = await Promise.all([
    prisma.drop.count({ where: { discordId } }),
    prisma.drop.findMany({
      where: { discordId },
      orderBy: { deliveredAt: "desc" },
      skip: (page - 1) * pageSize,
      take: pageSize,
    }),
  ]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Delivered items</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead>Nickname</TableHead>
                <TableHead>Thread</TableHead>
                <TableHead>Staff ID</TableHead>
                <TableHead>Delivered at</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {drops.map((drop) => (
                <TableRow key={drop.id}>
                  <TableCell>{drop.item ?? "—"}</TableCell>
                  <TableCell>{drop.nicknameIngame ?? "—"}</TableCell>
                  <TableCell>{drop.threadId?.toString() ?? "—"}</TableCell>
                  <TableCell>{drop.staffId?.toString() ?? "—"}</TableCell>
                  <TableCell>{epochToLocaleString(drop.deliveredAt)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <PaginationControls page={page} totalPages={totalPages} pathname="/dashboard/items" />
      </CardContent>
    </Card>
  );
}
