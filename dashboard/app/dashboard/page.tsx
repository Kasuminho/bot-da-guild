import { getServerSession } from "next-auth";

import { StatCard } from "@/components/dashboard/stat-card";
import { StatusCard } from "@/components/dashboard/status-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { authOptions } from "@/lib/auth";
import { fetchBotStatus } from "@/lib/bot-api";
import { epochToLocaleString, getPlayerSnapshot } from "@/lib/bot-data";

export default async function DashboardHome() {
  const session = await getServerSession(authOptions);

  if (!session?.user) {
    return null;
  }

  const [snapshot, botStatus] = await Promise.all([
    getPlayerSnapshot(session.user.discordId),
    fetchBotStatus(),
  ]);

  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Items delivered" value={snapshot.dropCount} helper="Pulled from the bot's existing `drops` table." />
        <StatCard label="Active requests" value={snapshot.requestCount} helper="Live queue from the bot's `item_requests` table." />
        <StatCard label="DKP balance" value={snapshot.dkpBalance} helper="Calculated from real `dkp_transactions` rows." />
        <StatusCard
          status={botStatus.ok ? "online" : "offline"}
          details={botStatus.ok ? "The existing bot health endpoint is responding." : "The dashboard cannot reach the current bot health endpoint."}
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>User profile</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <p className="text-muted-foreground">Discord ID</p>
              <p>{session.user.discordId}</p>
            </div>
            <div>
              <p className="text-muted-foreground">In-game nickname</p>
              <p>{snapshot.player?.nicknameIngame ?? "Not registered in bot DB yet"}</p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <p className="text-muted-foreground">Language</p>
                <p>{snapshot.player?.language ?? "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Timezone</p>
                <p>{snapshot.player?.timezone ?? "—"}</p>
              </div>
            </div>
            <div>
              <p className="text-muted-foreground">Channel binding</p>
              <p>{snapshot.player?.channelId?.toString() ?? "No channel associated"}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent deliveries</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Item</TableHead>
                    <TableHead>Staff</TableHead>
                    <TableHead>Thread</TableHead>
                    <TableHead>Delivered at</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {snapshot.drops.map((drop) => (
                    <TableRow key={drop.id}>
                      <TableCell>{drop.item ?? "—"}</TableCell>
                      <TableCell>{drop.staffId?.toString() ?? "—"}</TableCell>
                      <TableCell>{drop.threadId?.toString() ?? "—"}</TableCell>
                      <TableCell>{epochToLocaleString(drop.deliveredAt)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Active item requests</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Item</TableHead>
                  <TableHead>Remaining</TableHead>
                  <TableHead>Rank</TableHead>
                  <TableHead>Thread</TableHead>
                  <TableHead>Last update</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {snapshot.itemRequests.map((request) => (
                  <TableRow key={request.id}>
                    <TableCell>{request.itemName}</TableCell>
                    <TableCell>{request.remainingQuantity}/{request.totalQuantity}</TableCell>
                    <TableCell>
                      <Badge variant="secondary">#{request.rankPosition}</Badge>
                    </TableCell>
                    <TableCell>{request.threadId.toString()}</TableCell>
                    <TableCell>{epochToLocaleString(request.lastUpdate)}</TableCell>
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
