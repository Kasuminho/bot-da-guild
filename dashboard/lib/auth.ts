import { UserRole } from "@prisma/client";
import type { DefaultSession, NextAuthOptions } from "next-auth";
import type { JWT } from "next-auth/jwt";
import DiscordProvider from "next-auth/providers/discord";

import { env } from "@/lib/env";
import { prisma } from "@/lib/prisma";

declare module "next-auth" {
  interface Session {
    user: DefaultSession["user"] & {
      id: string;
      discordId: string;
      role: UserRole;
    };
  }

  interface User {
    role: UserRole;
    discordId: string;
    avatar?: string | null;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id?: string;
    discordId?: string;
    role?: UserRole;
    avatar?: string | null;
  }
}

async function syncDashboardUser(discordId: string, username: string, avatar?: string | null) {
  const normalizedDiscordId = BigInt(discordId);
  const role = env.adminDiscordIds.includes(discordId) ? UserRole.admin : UserRole.user;

  return prisma.dashboardUser.upsert({
    where: { discordId: normalizedDiscordId },
    update: { username, avatar: avatar ?? null, role },
    create: { discordId: normalizedDiscordId, username, avatar: avatar ?? null, role },
  });
}

export const authOptions: NextAuthOptions = {
  session: {
    strategy: "jwt",
  },
  providers: [
    DiscordProvider({
      clientId: process.env.DISCORD_CLIENT_ID ?? "",
      clientSecret: process.env.DISCORD_CLIENT_SECRET ?? "",
      authorization: {
        params: {
          scope: "identify guilds",
        },
      },
      profile(profile) {
        return {
          id: profile.id,
          discordId: profile.id,
          name: profile.username,
          username: profile.username,
          email: profile.email,
          image: profile.avatar,
          avatar: profile.avatar,
          role: env.adminDiscordIds.includes(profile.id) ? UserRole.admin : UserRole.user,
        };
      },
    }),
  ],
  callbacks: {
    async signIn({ user, profile }) {
      const discordId = profile && "id" in profile ? String(profile.id) : user.discordId;
      const username = profile && "username" in profile ? String(profile.username) : user.name ?? "Discord User";
      const avatar = profile && "avatar" in profile ? String(profile.avatar ?? "") || null : user.avatar ?? null;

      const dbUser = await syncDashboardUser(discordId, username, avatar);
      user.id = dbUser.id;
      user.role = dbUser.role;
      user.discordId = dbUser.discordId.toString();
      user.avatar = dbUser.avatar;
      return true;
    },
    async jwt({ token, user, profile }): Promise<JWT> {
      if (user) {
        token.id = user.id;
        token.discordId = user.discordId;
        token.role = user.role;
        token.avatar = user.avatar ?? null;
      }

      if (!token.id && profile && "id" in profile) {
        const dbUser = await syncDashboardUser(
          String(profile.id),
          String(profile.username),
          String(profile.avatar ?? "") || null,
        );
        token.id = dbUser.id;
        token.discordId = dbUser.discordId.toString();
        token.role = dbUser.role;
        token.avatar = dbUser.avatar;
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id ?? "";
        session.user.discordId = token.discordId ?? "";
        session.user.role = token.role ?? UserRole.user;
        session.user.image = token.avatar && token.discordId
          ? `https://cdn.discordapp.com/avatars/${token.discordId}/${token.avatar}.png`
          : null;
      }

      return session;
    },
  },
  pages: {
    signIn: "/login",
  },
  secret: process.env.NEXTAUTH_SECRET,
};
