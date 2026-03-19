import Link from "next/link";
import { Home, ListChecks, Logs, Shield, TerminalSquare, Users } from "lucide-react";

import { env } from "@/lib/env";
import { cn } from "@/lib/utils";

const sharedLinks = [
  { href: "/dashboard", label: "Overview", icon: Home },
  { href: "/dashboard/items", label: "Items", icon: ListChecks },
  { href: "/dashboard/logs", label: "My Logs", icon: Logs },
];

const adminLinks = [
  { href: "/dashboard/admin/users", label: "Users", icon: Users },
  { href: "/dashboard/admin/logs", label: "Global Logs", icon: Shield },
  { href: "/dashboard/admin/commands", label: "Commands", icon: TerminalSquare },
  { href: "/dashboard/admin/activity", label: "Activity", icon: Logs },
];

export function Sidebar({ role }: { role: "admin" | "user" }) {
  const links = role === "admin" ? [...sharedLinks, ...adminLinks] : sharedLinks;

  return (
    <aside className="w-full border-b border-border bg-card/80 p-4 lg:min-h-screen lg:w-72 lg:border-b-0 lg:border-r">
      <div className="mb-8">
        <p className="text-xs uppercase tracking-[0.3em] text-primary">Discord Bot</p>
        <h1 className="mt-2 text-2xl font-semibold text-foreground">{env.appName}</h1>
      </div>
      <nav className="grid gap-2">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted-foreground transition hover:bg-secondary hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4" />
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
