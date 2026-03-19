import { getServerSession } from "next-auth";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PaginationControls } from "@/components/ui/pagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { authOptions } from "@/lib/auth";
import { epochToLocaleString, getUserTimeline } from "@/lib/bot-data";

export default async function LogsPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const session = await getServerSession(authOptions);
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? "1") || 1);
  const pageSize = 10;

  if (!session?.user) {
    return null;
  }

  const timeline = await getUserTimeline(session.user.discordId);
  const rows = timeline.slice((page - 1) * pageSize, page * pageSize);
  const totalPages = Math.max(1, Math.ceil(timeline.length / pageSize));

  return (
    <Card>
      <CardHeader>
        <CardTitle>My bot activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Source</TableHead>
                <TableHead>Event</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Timestamp</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>
                    <Badge variant="secondary">{entry.source}</Badge>
                  </TableCell>
                  <TableCell>{entry.title}</TableCell>
                  <TableCell className="max-w-md whitespace-pre-wrap text-xs text-muted-foreground">
                    {JSON.stringify(entry.metadata ?? entry.description, null, 2)}
                  </TableCell>
                  <TableCell>{epochToLocaleString(entry.createdAt)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <PaginationControls page={page} totalPages={totalPages} pathname="/dashboard/logs" />
      </CardContent>
    </Card>
  );
}
