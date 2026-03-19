import { redirect } from "next/navigation";
import { getServerSession } from "next-auth";

import { DashboardHeader } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { authOptions } from "@/lib/auth";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);

  if (!session?.user) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen lg:flex">
      <Sidebar role={session.user.role} />
      <div className="flex-1">
        <DashboardHeader name={session.user.name ?? "Discord User"} image={session.user.image} role={session.user.role} />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
