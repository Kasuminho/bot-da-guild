import fs from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";

import { PrismaClient } from "@prisma/client";

declare global {
  var prisma: PrismaClient | undefined;
  var prismaSqliteBigIntNormalized: boolean | undefined;
}

function resolveSqliteDatabasePath(databaseUrl: string) {
  if (!databaseUrl.startsWith("file:")) return null;

  const sqlitePath = databaseUrl.slice("file:".length);
  if (!sqlitePath || sqlitePath === ":memory:") return null;

  return path.resolve(process.cwd(), sqlitePath);
}

function normalizeLegacySqliteBigIntColumns() {
  if (global.prismaSqliteBigIntNormalized) return;

  const databaseUrl = process.env.DATABASE_URL ?? "";
  const databasePath = resolveSqliteDatabasePath(databaseUrl);
  if (!databasePath) {
    global.prismaSqliteBigIntNormalized = true;
    return;
  }
  if (!fs.existsSync(databasePath)) {
    global.prismaSqliteBigIntNormalized = true;
    return;
  }

  const migrationScriptPath = path.resolve(process.cwd(), "scripts/normalize_sqlite_bigint_columns.py");

  execFileSync("python3", [migrationScriptPath, databasePath], {
    cwd: process.cwd(),
    stdio: "pipe",
  });

  global.prismaSqliteBigIntNormalized = true;
}

normalizeLegacySqliteBigIntColumns();

export const prisma = global.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== "production") {
  global.prisma = prisma;
}
