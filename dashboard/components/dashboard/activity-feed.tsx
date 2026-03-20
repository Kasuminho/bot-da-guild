"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";

interface ActivityEntry {
  id: string;
  type: string;
  label: string;
  actor: string;
  status?: string;
  createdAt: string;
}

export function ActivityFeed({ initialEntries }: { initialEntries: ActivityEntry[] }) {
  const [entries, setEntries] = useState<ActivityEntry[]>(initialEntries);

  useEffect(() => {
    const timer = setInterval(async () => {
      const response = await fetch("/api/admin/activity", { cache: "no-store" });
      if (!response.ok) return;
      const payload = await response.json();
      setEntries(payload.data ?? []);
    }, 15000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="space-y-4">
      {entries.map((entry) => (
        <div key={`${entry.type}-${entry.id}`} className="flex items-start justify-between rounded-lg border border-border p-4">
          <div>
            <p className="font-medium">{entry.label}</p>
            <p className="text-sm text-muted-foreground">Actor: {entry.actor}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <Badge variant={entry.type === "command" ? "warning" : "secondary"}>
              {entry.status ? `${entry.type}:${entry.status}` : entry.type}
            </Badge>
            <p className="text-xs text-muted-foreground">{new Date(entry.createdAt).toLocaleString()}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
