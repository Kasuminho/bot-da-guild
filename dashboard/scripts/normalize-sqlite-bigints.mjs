import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const provider = process.env.DATABASE_PROVIDER ?? "sqlite";
const databaseUrl = process.env.DATABASE_URL ?? "file:../database.db";

if (provider !== "sqlite" || !databaseUrl.startsWith("file:")) {
  process.exit(0);
}

const sqlitePath = databaseUrl.slice("file:".length);
if (!sqlitePath || sqlitePath === ":memory:") {
  process.exit(0);
}

const scriptPath = path.resolve(process.cwd(), "scripts/normalize_sqlite_bigint_columns.py");
const databasePath = path.resolve(process.cwd(), sqlitePath);

if (!fs.existsSync(databasePath)) {
  process.exit(0);
}

execFileSync("python3", [scriptPath, databasePath], {
  cwd: process.cwd(),
  stdio: "inherit",
});
