const { EmbedBuilder } = require('discord.js');

const MAX_REACTIONS = 4;

function buildPartyEmbed({ reasonPt, reasonEn, startTs, endTs, creatorName, members }) {
  const slots = [...members, ...Array(Math.max(0, 5 - members.length)).fill('—')];

  return new EmbedBuilder()
    .setTitle('🎉 Party')
    .setDescription(`**${reasonPt}**\n*${reasonEn}*`)
    .setColor(0x2ecc71)
    .addFields({
      name: '🕒 Disponibilidade / Availability',
      value: `<t:${startTs}:t> – <t:${endTs}:t>`,
      inline: false,
    })
    .addFields({
      name: `👥 Party (${members.length}/5)`,
      value: slots.join('\n'),
      inline: false,
    })
    .setFooter({ text: `Criador: ${creatorName}` });
}

async function updatePartyEmbed({ message, party, members }) {
  const creator = await message.guild.members.fetch(party.creator_id).catch(() => null);
  const creatorName = creator?.displayName || creator?.user?.username || 'Criador';

  const embed = buildPartyEmbed({
    reasonPt: party.reason_pt,
    reasonEn: party.reason_en,
    startTs: party.start_ts,
    endTs: party.end_ts,
    creatorName,
    members,
  });

  await message.edit({ embeds: [embed] });
}

function registerPartyEvents({ client, db }) {
  client.on('messageReactionAdd', async (reaction, user) => {
    if (user.bot) {
      return;
    }

    if (reaction.partial) {
      await reaction.fetch().catch(() => null);
    }
    if (reaction.message.partial) {
      await reaction.message.fetch().catch(() => null);
    }

    if (reaction.emoji.name !== '✅') {
      return;
    }

    const party = await db.getPartyByMessageId(reaction.message.id);
    if (!party) {
      return;
    }

    const users = await reaction.users.fetch();
    const nonBots = users.filter((u) => !u.bot);

    if (nonBots.size > MAX_REACTIONS) {
      await reaction.users.remove(user.id).catch(() => null);
      await user.send('❌ Party cheia (4/4).').catch(() => null);
      return;
    }

    const members = [
      `<@${party.creator_id}>`,
      ...nonBots.map((u) => u.toString()),
    ];

    await updatePartyEmbed({ message: reaction.message, party, members });
  });

  client.on('messageReactionRemove', async (reaction) => {
    if (reaction.partial) {
      await reaction.fetch().catch(() => null);
    }
    if (reaction.message.partial) {
      await reaction.message.fetch().catch(() => null);
    }

    if (reaction.emoji.name !== '✅') {
      return;
    }

    const party = await db.getPartyByMessageId(reaction.message.id);
    if (!party) {
      return;
    }

    const users = await reaction.users.fetch();
    const nonBots = users.filter((u) => !u.bot);

    const members = [
      `<@${party.creator_id}>`,
      ...nonBots.map((u) => u.toString()),
    ];

    await updatePartyEmbed({ message: reaction.message, party, members });
  });
}

module.exports = {
  registerPartyEvents,
};
