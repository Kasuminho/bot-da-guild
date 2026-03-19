import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";

import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { authOptions } from "@/lib/auth";
import { getAdminActivity } from "@/lib/bot-data";

export default async function ActivityFeedPage() {
  const session = await getServerSession(authOptions);

  if (!session?.user) {
    redirect("/login");
  }

  if (session.user.role !== "admin") {
    redirect("/dashboard");
  }

  const feed = await getAdminActivity();

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity feed from the real bot tables</CardTitle>
      </CardHeader>
      <CardContent>
        <ActivityFeed initialEntries={feed.slice(0, 20)} />
      </CardContent>
    </Card>
  );
}
