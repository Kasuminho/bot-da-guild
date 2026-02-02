function startWeeklyScheduler({ client, db }) {
  let lastRunKey = null;

  const interval = setInterval(async () => {
    const now = new Date();
    const utcDay = now.getUTCDay();
    const utcHour = now.getUTCHours();
    const utcMinute = now.getUTCMinutes();

    if (utcDay !== 1 || utcHour !== 12 || utcMinute !== 0) {
      return;
    }

    const runKey = `${now.getUTCFullYear()}-${now.getUTCMonth()}-${now.getUTCDate()}`;
    if (lastRunKey === runKey) {
      return;
    }

    lastRunKey = runKey;

    const players = await db.getAllPlayers();
    for (const player of players) {
      const channel = await client.channels.fetch(player.channel_id).catch(() => null);
      if (channel) {
        await channel.send('📌 Lembrete semanal: envie sua atualização.');
      }
    }
  }, 60 * 1000);

  return () => clearInterval(interval);
}

module.exports = {
  startWeeklyScheduler,
};
