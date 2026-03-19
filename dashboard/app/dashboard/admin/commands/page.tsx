import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";

import { CommandForm } from "@/components/forms/command-form";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { parseJson, truncate } from "@/lib/utils";

export default async function AdminCommandsPage() {
  const session = await getServerSession(authOptions);

  if (!session?.user) {
    redirect("/login");
  }

  if (session.user.role !== "admin") {
    redirect("/dashboard");
  }

  const commands = await prisma.command.findMany({
    orderBy: { createdAt: "desc" },
    take: 20,
    include: {
      executor: { select: { username: true } },
    },
  });

  return (
    <div className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
      <Card>
        <CardHeader>
          <CardTitle>Execute bot command</CardTitle>
        </CardHeader>
        <CardContent>
          <CommandForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent command executions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Command</TableHead>
                  <TableHead>Executed by</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Result</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {commands.map((command) => (
                  <TableRow key={command.id}>
                    <TableCell>{command.command}</TableCell>
                    <TableCell>{command.executor.username}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          command.status === "success"
                            ? "success"
                            : command.status === "error"
                              ? "error"
                              : "warning"
                        }
                      >
                        {command.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-xs whitespace-pre-wrap text-xs text-muted-foreground">
                      {truncate(JSON.stringify(parseJson(command.result, {})))}
                    </TableCell>
                    <TableCell>{command.createdAt.toLocaleString()}</TableCell>
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
