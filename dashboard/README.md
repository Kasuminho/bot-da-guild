# Bot da Guild Dashboard

A production-ready Next.js dashboard for operating and monitoring the Discord bot.

## Features
- Discord OAuth2 login with NextAuth.
- Role-based access control for `admin` and `user` accounts.
- SQLite database powered by Prisma.
- Admin pages for users, logs, activity, and bot command execution.
- User pages for profile data, sent items, personal logs, and bot status.
- Server-side bot API proxy so the local bot HTTP API is never exposed to browsers.
- Responsive layout with Tailwind CSS and reusable shadcn-style UI primitives.

## Project structure

```text
/dashboard
├── app/
│   ├── api/
│   │   ├── admin/
│   │   ├── auth/[...nextauth]/
│   │   ├── bot/status/
│   │   ├── logs/
│   │   ├── me/
│   │   └── user/items/
│   ├── dashboard/
│   │   ├── admin/
│   │   ├── items/
│   │   └── logs/
│   ├── login/
│   ├── globals.css
│   └── layout.tsx
├── components/
│   ├── dashboard/
│   ├── forms/
│   ├── layout/
│   └── ui/
├── lib/
├── prisma/
│   ├── schema.prisma
│   └── seed.ts
├── .env.example
└── package.json
```

## Setup

1. Install dependencies:
   ```bash
   cd dashboard
   npm install
   ```
2. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
3. Create a random NextAuth secret:
   ```bash
   openssl rand -base64 32
   ```
4. Create the SQLite database and Prisma client:
   ```bash
   npm run prisma:push
   npm run prisma:generate
   ```
5. Optionally bootstrap admins from `ADMIN_DISCORD_IDS`:
   ```bash
   npm run prisma:seed
   ```
6. Start the dashboard:
   ```bash
   npm run dev
   ```

## Discord OAuth2 setup

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a new application.
3. Go to **OAuth2 > General** and copy the **Client ID** and **Client Secret**.
4. Add the redirect URI:
   ```text
   http://localhost:3000/api/auth/callback/discord
   ```
5. Put the credentials into `.env`.
6. List admin Discord IDs in `ADMIN_DISCORD_IDS` for staff accounts.

## Bot API contract

The dashboard expects a local HTTP API:

### Execute command
```http
POST /command
Content-Type: application/json

{
  "command": "grant_loot epic-sword",
  "userId": "123456789012345678"
}
```

### Health check
```http
GET /health
```

Any non-2xx command response is stored as a failed command execution in the dashboard audit tables.

## Example local bot API implementation

```ts
import express from "express";

const app = express();
app.use(express.json());

app.get("/health", (_req, res) => {
  res.json({ status: "ok" });
});

app.post("/command", (req, res) => {
  const { command, userId } = req.body ?? {};

  if (!command || !userId) {
    return res.status(400).json({ message: "command and userId are required" });
  }

  console.log("Executing bot command", { command, userId });
  return res.json({ success: true, command, userId });
});

app.listen(8080, () => {
  console.log("Bot API listening on http://127.0.0.1:8080");
});
```

## Security notes
- All dashboard pages and API routes require an authenticated session.
- Admin APIs additionally require `role === admin`.
- Command execution only occurs server-side through `/api/admin/commands`.
- API inputs are validated with Zod before bot requests are sent.
