import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function StatusCard({ status, details }: { status: "online" | "offline"; details: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Bot status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Badge variant={status === "online" ? "success" : "error"}>{status}</Badge>
        <p className="text-sm text-muted-foreground">{details}</p>
      </CardContent>
    </Card>
  );
}
