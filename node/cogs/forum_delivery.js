const {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
  AttachmentBuilder,
} = require('discord.js');
const path = require('path');
const fs = require('fs');

const OVERRIDE_IDS = new Set([273600843251712020, 314170587968700417]);
const STAFF_CONTACT_ID = 273600843251712020;

const deliverCommand = new SlashCommandBuilder()
  .setName('entregar')
  .setDescription('Registrar entrega de item no fórum')
  .addStringOption((option) =>
    option
      .setName('jogadores')
      .setDescription('Menções dos jogadores')
      .setRequired(true),
  )
  .addStringOption((option) =>
    option.setName('item').setDescription('Item entregue').setRequired(true),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

const rejectCommand = new SlashCommandBuilder()
  .setName('recusar')
  .setDescription('Recusar uma solicitação do fórum')
  .addStringOption((option) =>
    option
      .setName('motivo')
      .setDescription('Motivo da recusa')
      .setRequired(true),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

const historyCommand = new SlashCommandBuilder()
  .setName('historico')
  .setDescription('Ver histórico de drops de um jogador')
  .addUserOption((option) =>
    option.setName('jogador').setDescription('Jogador').setRequired(true),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

async function collectAttachments({ thread, userId, limit = 60 }) {
  const attachments = [];
  const messages = await thread.messages.fetch({ limit }).catch(() => null);
  if (!messages) {
    return attachments;
  }

  for (const message of messages.values()) {
    if (message.author.id !== userId) {
      continue;
    }
    if (message.attachments.size === 0) {
      continue;
    }
    message.attachments.forEach((attachment) => attachments.push(attachment));
  }

  return attachments;
}

function parseMentionIds(input) {
  const ids = [];
  const regex = /<@!?(\d+)>/g;
  let match;
  while ((match = regex.exec(input)) !== null) {
    ids.push(match[1]);
  }
  return ids;
}

async function handleDeliver({ interaction, db, forumChannelId }) {
  await interaction.deferReply({ ephemeral: true });

  const channel = interaction.channel;
  if (!channel || channel.type !== ChannelType.PublicThread) {
    await interaction.editReply('❌ Use este comando dentro de uma thread.');
    return;
  }

  if (channel.parentId !== forumChannelId) {
    await interaction.editReply('❌ Este comando só pode ser usado em threads do fórum correto.');
    return;
  }

  const post = await db.getForumPostByThread(channel.id);
  if (!post) {
    await interaction.editReply('❌ Thread não registrada.');
    return;
  }

  const now = Math.floor(Date.now() / 1000);
  if (post.delivered) {
    await interaction.editReply('⚠️ Já finalizado.');
    return;
  }

  if (now < post.close_time && !OVERRIDE_IDS.has(interaction.user.id)) {
    await interaction.editReply(`⏰ Ainda aberto. Fecha em <t:${post.close_time}:F>`);
    return;
  }

  if (now < post.close_time && OVERRIDE_IDS.has(interaction.user.id)) {
    await channel.send('⚠️ **Entrega realizada antes do horário por override administrativo.**');
  }

  const jogadores = interaction.options.getString('jogadores', true);
  const item = interaction.options.getString('item', true);

  const playerIds = parseMentionIds(jogadores);
  const players = [];
  for (const playerId of playerIds) {
    const member = await interaction.guild.members.fetch(playerId).catch(() => null);
    if (member) {
      players.push(member);
    }
  }

  if (players.length === 0) {
    await interaction.editReply('❌ Nenhum jogador válido encontrado nas menções.');
    return;
  }

  const attachments = await collectAttachments({
    thread: channel,
    userId: interaction.user.id,
  });

  if (attachments.length === 0) {
    await interaction.editReply('❌ Envie os prints **antes** de usar o comando `/entregar`.');
    return;
  }

  const files = [];
  for (const attachment of attachments) {
    if (!attachment.url) {
      continue;
    }
    const fileName = attachment.name || path.basename(attachment.url);
    files.push(new AttachmentBuilder(attachment.url, { name: fileName }));
  }

  const mentions = players.map((player) => player.toString()).join(' ');

  await channel.send({
    content: (
      '📦 **Entrega de Item / Item Delivery**\n\n'
      + `🎯 **Jogadores / Players:** ${mentions}\n`
      + `🧾 **Item:** ${item}\n`
      + `📎 **Comprovantes:** ${files.length} arquivo(s)`
    ),
    files,
  });

  for (const player of players) {
    await db.addDrop(
      player.id,
      player.displayName,
      item,
      channel.id,
      interaction.user.id,
    );
  }

  await db.markForumPostDelivered(post.id);

  await channel.setArchived(true);
  await channel.setLocked(true);

  await interaction.editReply(`✅ Entrega registrada para ${players.length} jogador(es).`);
}

async function handleReject({ interaction, forumChannelId }) {
  await interaction.deferReply({ ephemeral: true });

  const channel = interaction.channel;
  if (!channel || channel.type !== ChannelType.PublicThread) {
    await interaction.editReply('❌ Use este comando dentro de uma thread.');
    return;
  }

  if (channel.parentId !== forumChannelId) {
    await interaction.editReply('❌ Este comando só pode ser usado em requests do fórum correto.');
    return;
  }

  const motivo = interaction.options.getString('motivo', true);

  await channel.send({
    content: (
      '❌ **Solicitação recusada pela Staff**\n\n'
      + 'Motivo:\n'
      + `> **${motivo}**\n\n`
      + `📩 Para esclarecimentos, entre em contato com <@${STAFF_CONTACT_ID}>.`
    ),
  });

  await channel.setArchived(true);
  await channel.setLocked(true);

  await interaction.editReply('✅ Solicitação recusada e thread encerrada.');
}

async function handleHistory({ interaction, db }) {
  const jogador = interaction.options.getUser('jogador', true);
  const drops = await db.getPlayerDrops(jogador.id);

  if (!drops || drops.length === 0) {
    await interaction.reply({
      content: `📦 ${jogador.toString()} ainda não recebeu nenhum item.`,
      ephemeral: true,
    });
    return;
  }

  const lines = [];
  for (const drop of drops) {
    const staff = await interaction.guild.members
      .fetch(drop.staff_id)
      .catch(() => null);
    const staffName = staff ? staff.toString() : `\`${drop.staff_id}\``;

    lines.push(
      `• **${drop.item}**\n`
      + `  ⏰ <t:${drop.delivered_at}:R>\n`
      + `  👤 Entregue por: ${staffName}`,
    );
  }

  const texto = `📜 **Histórico de Drops — ${jogador.username}**\n\n${lines.join('\n\n')}`;
  await interaction.reply({ content: texto, ephemeral: true });
}

function registerForumDelivery({ client, db, forumChannelId }) {
  client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (interaction.commandName === 'entregar') {
      await handleDeliver({ interaction, db, forumChannelId });
      return;
    }

    if (interaction.commandName === 'recusar') {
      await handleReject({ interaction, forumChannelId });
      return;
    }

    if (interaction.commandName === 'historico') {
      await handleHistory({ interaction, db });
    }
  });
}

module.exports = {
  commands: [deliverCommand, rejectCommand, historyCommand],
  registerForumDelivery,
};
