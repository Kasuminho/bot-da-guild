import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const validProviders = new Set(["sqlite", "postgresql"]);
const provider = process.env.DATABASE_PROVIDER ?? "sqlite";

if (!validProviders.has(provider)) {
  console.error(
    `Invalid DATABASE_PROVIDER="${provider}". Use one of: ${Array.from(validProviders).join(", ")}.`,
  );
  process.exit(1);
}

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const prismaDir = path.resolve(scriptDir, "../prisma");
const templatePath = path.join(prismaDir, "schema.template.prisma");
const outputPath = path.join(prismaDir, "schema.prisma");

const template = readFileSync(templatePath, "utf8");
const renderedSchema = template.replace("__DATABASE_PROVIDER__", provider);

writeFileSync(outputPath, renderedSchema);
console.log(`Prepared prisma/schema.prisma with provider "${provider}".`);
