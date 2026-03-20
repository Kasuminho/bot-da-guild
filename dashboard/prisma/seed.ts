import { PrismaClient, UserRole } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  const adminIds = (process.env.ADMIN_DISCORD_IDS ?? "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .map((value) => BigInt(value));

  for (const discordId of adminIds) {
    await prisma.dashboardUser.upsert({
      where: { discordId },
      update: { role: UserRole.admin },
      create: {
        discordId,
        username: `Admin ${discordId.toString().slice(-4)}`,
        role: UserRole.admin,
      },
    });
  }
}

main()
  .then(async () => {
    await prisma.$disconnect();
  })
  .catch(async (error) => {
    console.error(error);
    await prisma.$disconnect();
    process.exit(1);
  });
