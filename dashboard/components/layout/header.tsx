"use client";

import { signOut } from "next-auth/react";

import { UserAvatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function DashboardHeader({
  name,
  image,
  role,
}: {
  name: string;
  image?: string | null;
  role: "admin" | "user";
}) {
  return (
    <header className="flex flex-col gap-4 border-b border-border bg-card/70 px-6 py-4 backdrop-blur md:flex-row md:items-center md:justify-between">
      <div>
        <p className="text-sm text-muted-foreground">Welcome back</p>
        <h2 className="text-2xl font-semibold text-foreground">{name}</h2>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant={role === "admin" ? "success" : "secondary"}>{role}</Badge>
        <UserAvatar src={image} alt={name} />
        <Button variant="outline" onClick={() => signOut({ callbackUrl: "/login" })}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
