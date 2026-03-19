import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PaginationControls } from "@/components/ui/pagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { authOptions } from "@/lib/auth";
import { epochToLocaleString } from "@/lib/bot-data";
import { prisma } from "@/lib/prisma";
import { parseJson } from "@/lib/utils";

export default async function AdminLogsPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
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

  const [total, logs] = await Promise.all([
    prisma.auditLog.count(),
    prisma.auditLog.findMany({
      orderBy: { createdAt: "desc" },
      skip: (page - 1) * pageSize,
      take: pageSize,
    }),
  ]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Audit logs from the bot</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Action</TableHead>
                <TableHead>Actor</TableHead>
                <TableHead>Entity</TableHead>
                <TableHead>Details</TableHead>
                <TableHead>Timestamp</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>{log.action}</TableCell>
                  <TableCell>{log.actorUserId.toString()}</TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <p>{log.entityType}</p>
                      {log.entityId ? <Badge variant="outline">{log.entityId}</Badge> : null}
                    </div>
                  </TableCell>
                  <TableCell className="max-w-md whitespace-pre-wrap text-xs text-muted-foreground">
                    {JSON.stringify(parseJson(log.detailsJson, {}), null, 2)}
                  </TableCell>
                  <TableCell>{epochToLocaleString(log.createdAt)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <PaginationControls page={page} totalPages={totalPages} pathname="/dashboard/admin/logs" />
      </CardContent>
    </Card>
  );
}
