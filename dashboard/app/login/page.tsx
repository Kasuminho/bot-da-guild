"use client";

import { signIn } from "next-auth/react";
import { Shield, TerminalSquare } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-3xl">Bot Dashboard</CardTitle>
          <CardDescription>
            Secure Discord OAuth2 access for staff and players. Admins can execute commands and review global activity.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-border p-4">
              <Shield className="mb-3 h-5 w-5 text-primary" />
              <h3 className="font-medium">Protected access</h3>
              <p className="mt-2 text-sm text-muted-foreground">Every route is protected by NextAuth sessions and role-aware APIs.</p>
            </div>
            <div className="rounded-lg border border-border p-4">
              <TerminalSquare className="mb-3 h-5 w-5 text-primary" />
              <h3 className="font-medium">Bot control</h3>
              <p className="mt-2 text-sm text-muted-foreground">Command execution is proxied server-side so the bot API is never exposed publicly.</p>
            </div>
          </div>
          <Button className="w-full" onClick={() => signIn("discord", { callbackUrl: "/dashboard" })}>
            Continue with Discord
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
