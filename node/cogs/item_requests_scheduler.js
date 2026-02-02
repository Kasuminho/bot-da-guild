const fs = require('fs');
const path = require('path');
const { EmbedBuilder } = require('discord.js');
const { TEXT } = require('../utils/i18n');

const lang = 'pt';
const ITEM_IMAGES_DIR = path.join('images', 'itens');

async function clearSummaryChannel(channel, botUserId) {
  const messages = await channel.messages.fetch({ limit: 100 }).catch(() => null);
  if (!messages) {
    return;
  }

  const toDelete = messages.filter((message) => message.author.id === botUserId);
  if (toDelete.size > 0) {
    await channel.bulkDelete(toDelete, true).catch(() => null);
  }
}

async function sendItemSummary({ client, db, summaryChannelId }) {
  const channel = await client.channels.fetch(summaryChannelId).catch(() => null);
  if (!channel) {
    return;
  }

  await clearSummaryChannel(channel, client.user.id);

  const rows = await db.getDailyItemSummary();
  if (!rows || rows.length === 0) {
    return;
  }

  const embeds = new Map();
  const files = new Map();

  for (const row of rows) {
    if (!embeds.has(row.item_name)) {
      const embed = new EmbedBuilder()
        .setTitle(TEXT.rank_header[lang].replace('{item}', row.item_name))
        .setColor(0x5865f2);

      const imagePath = path.join(ITEM_IMAGES_DIR, `${row.item_name}.png`);
      if (fs.existsSync(imagePath)) {
        embed.setThumbnail(`attachment://${row.item_name}.png`);
        files.set(row.item_name, imagePath);
      }

      embeds.set(row.item_name, embed);
    }

    const thread = await client.channels.fetch(row.thread_id).catch(() => null);
    const link = thread?.url || '';

    embeds.get(row.item_name).addFields({
      name: `${row.rank_position}º - ${row.player_name}`,
      value: TEXT.rank_line[lang]
        .replace('{remaining}', row.remaining_quantity)
        .replace('{link}', link),
      inline: false,
    });
  }

  for (const [itemName, embed] of embeds.entries()) {
    const filePath = files.get(itemName);
    if (filePath) {
      await channel.send({
        embeds: [embed],
        files: [{ attachment: filePath, name: `${itemName}.png` }],
      });
    } else {
      await channel.send({ embeds: [embed] });
    }
  }
}

function startItemRequestScheduler({ client, db, summaryChannelId }) {
  const hourlyInterval = setInterval(async () => {
    await sendItemSummary({ client, db, summaryChannelId });
  }, 60 * 60 * 1000);

  const dailyInterval = setInterval(async () => {
    const now = Math.floor(Date.now() / 1000);
    const requests = await db.getAllItemRequestsForCheck();

    for (const req of requests) {
      if (req.item_name === 'creature of gaiety') {
        continue;
      }
      if (req.item_name === 'elder dragon isteria') {
        continue;
      }

      const daysIdle = Math.floor((now - req.last_update) / 86400);
      const thread = await client.channels.fetch(req.thread_id).catch(() => null);
      if (!thread) {
        continue;
      }

      if (daysIdle >= 3 && !req.warned_3d) {
        await thread.send(
          TEXT.idle_3d[lang]
            .replace('{player}', req.discord_id)
            .replace('{item}', req.item_name),
        );
        await db.markRequestWarned(req.id, 'warned_3d');
        continue;
      }

      if (daysIdle >= 4 && !req.warned_4d) {
        await thread.send(
          TEXT.idle_4d[lang]
            .replace('{player}', req.discord_id)
            .replace('{item}', req.item_name),
        );
        await db.markRequestWarned(req.id, 'warned_4d');
        continue;
      }

      if (daysIdle >= 5) {
        await thread.send(
          TEXT.rank_down[lang]
            .replace('{player}', req.discord_id)
            .replace('{item}', req.item_name),
        );
        await db.dropRequestRank(req.id);
      }
    }
  }, 24 * 60 * 60 * 1000);

  return () => {
    clearInterval(hourlyInterval);
    clearInterval(dailyInterval);
  };
}

module.exports = {
  sendItemSummary,
  startItemRequestScheduler,
};
