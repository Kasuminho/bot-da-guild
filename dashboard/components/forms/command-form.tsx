"use client";

import { type FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type CommandFormProps = {
  enabled: boolean;
  endpoint: string;
};

export function CommandForm({ enabled, endpoint }: CommandFormProps) {
  const [command, setCommand] = useState("");
  const [userId, setUserId] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!enabled) {
      setResult(
        JSON.stringify(
          {
            error: "Command bridge disabled",
            message: "Configure BOT_COMMAND_ENDPOINT in dashboard/.env to enable HTTP command execution.",
          },
          null,
          2,
        ),
      );
      return;
    }

    setSubmitting(true);
    setResult(null);

    try {
      const response = await fetch("/api/admin/commands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, userId }),
      });

      const data = await response.json();
      setResult(JSON.stringify(data, null, 2));

      if (response.ok) {
        setCommand("");
      }
    } catch (error) {
      setResult(JSON.stringify({ error: error instanceof Error ? error.message : "Unknown error" }, null, 2));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {!enabled ? (
        <div className="rounded-lg border border-dashed border-border bg-muted/40 p-3 text-sm text-muted-foreground">
          Command bridge disabled. The dashboard still works with the real bot database. To enable remote commands, set <code>BOT_COMMAND_ENDPOINT</code> in <code>dashboard/.env</code>.
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-muted/30 p-3 text-sm text-muted-foreground">
          Sending commands to <code>{endpoint}</code>.
        </div>
      )}
      <div className="space-y-2">
        <label htmlFor="userId" className="text-sm font-medium text-foreground">
          Target Discord user ID
        </label>
        <Input id="userId" value={userId} onChange={(event) => setUserId(event.target.value)} required disabled={!enabled} />
      </div>
      <div className="space-y-2">
        <label htmlFor="command" className="text-sm font-medium text-foreground">
          Command payload
        </label>
        <Textarea id="command" value={command} onChange={(event) => setCommand(event.target.value)} required disabled={!enabled} />
      </div>
      <Button type="submit" disabled={submitting || !enabled}>
        {submitting ? "Executing…" : "Execute command"}
      </Button>
      {result ? (
        <pre className="overflow-x-auto rounded-lg border border-border bg-black/40 p-4 text-xs text-slate-200">{result}</pre>
      ) : null}
    </form>
  );
}
