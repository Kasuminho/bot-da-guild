import { getServerSession } from "next-auth";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PaginationControls } from "@/components/ui/pagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { parseJson } from "@/lib/utils";

export default async function ItemsPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const session = await getServerSession(authOptions);
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const pageSize = 10;

  if (!session?.user) {
    return null;
  }

  const [total, items] = await Promise.all([
    prisma.item.count({ where: { userId: session.user.id } }),
    prisma.item.findMany({
      where: { userId: session.user.id },
      orderBy: { deliveredAt: "desc" },
      skip: (page - 1) * pageSize,
      take: pageSize,
    }),
  ]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Items sent</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead>Quantity</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Metadata</TableHead>
                <TableHead>Delivered</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>{item.name}</TableCell>
                  <TableCell>{item.quantity}</TableCell>
                  <TableCell>
                    <Badge variant={item.status === "sent" ? "success" : "secondary"}>{item.status}</Badge>
                  </TableCell>
                  <TableCell className="max-w-md whitespace-pre-wrap text-xs text-muted-foreground">
                    {JSON.stringify(parseJson(item.metadata, {}), null, 2)}
                  </TableCell>
                  <TableCell>{item.deliveredAt.toLocaleString()}</TableCell>
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
