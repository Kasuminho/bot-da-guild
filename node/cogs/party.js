const {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ActionRowBuilder,
  StringSelectMenuBuilder,
  EmbedBuilder,
} = require('discord.js');
const { DateTime } = require('luxon');
const translate = require('@vitalets/google-translate-api');

const TIMEZONES = [
  { label: '🇺🇸 Baker Island', value: 'Etc/GMT+12' },
  { label: '🇺🇸 Samoa', value: 'Pacific/Pago_Pago' },
  { label: '🇺🇸 Honolulu', value: 'Pacific/Honolulu' },
  { label: '🇺🇸 Anchorage', value: 'America/Anchorage' },
  { label: '🇺🇸 Los Angeles', value: 'America/Los_Angeles' },
  { label: '🇺🇸 Denver', value: 'America/Denver' },
  { label: '🇺🇸 Chicago', value: 'America/Chicago' },
  { label: '🇺🇸 New York', value: 'America/New_York' },
  { label: '🇨🇦 Halifax', value: 'America/Halifax' },
  { label: '🇧🇷 São Paulo', value: 'America/Sao_Paulo' },
  { label: '🇧🇷 Fernando de Noronha', value: 'America/Noronha' },
  { label: '🇵🇹 Azores', value: 'Atlantic/Azores' },
  { label: '🇬🇧 London', value: 'Europe/London' },
  { label: '🇩🇪 Berlin', value: 'Europe/Berlin' },
  { label: '🇬🇷 Athens', value: 'Europe/Athens' },
  { label: '🇷🇺 Moscow', value: 'Europe/Moscow' },
  { label: '🇦🇪 Dubai', value: 'Asia/Dubai' },
  { label: '🇵🇰 Karachi', value: 'Asia/Karachi' },
  { label: '🇧🇩 Dhaka', value: 'Asia/Dhaka' },
  { label: '🇹🇭 Bangkok', value: 'Asia/Bangkok' },
  { label: '🇨🇳 Beijing', value: 'Asia/Shanghai' },
  { label: '🇯🇵 Tokyo', value: 'Asia/Tokyo' },
  { label: '🇦🇺 Sydney', value: 'Australia/Sydney' },
  { label: '🇳🇿 Auckland', value: 'Pacific/Auckland' },
];

const TIMEZONE_SELECT_ID = 'party:timezone-select';

const partyCommand = new SlashCommandBuilder()
  .setName('party')
  .setDescription('Criar uma party')
  .addStringOption((option) =>
    option
      .setName('motivo')
      .setDescription('Motivo da party')
      .setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('inicio')
      .setDescription('Início (YYYY-MM-DD HH:MM)')
      .setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('fim')
      .setDescription('Fim (HH:MM)')
      .setRequired(true),
  );

const deleteCommand = new SlashCommandBuilder()
  .setName('party_delete')
  .setDescription('Apagar sua party');

const clearCommand = new SlashCommandBuilder()
  .setName('party_clear_all')
  .setDescription('STAFF — apagar todas as partys')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

function buildTimezoneSelect() {
  return new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder()
      .setCustomId(TIMEZONE_SELECT_ID)
      .setPlaceholder('🌍 Escolha sua cidade (uma vez só)')
      .addOptions(TIMEZONES.map((tz) => ({ label: tz.label, value: tz.value }))),
  );
}

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

async function translateReason(text) {
  const [ptResult, enResult] = await Promise.all([
    translate(text, { to: 'pt' }),
    translate(text, { to: 'en' }),
  ]);

  return {
    pt: ptResult.text,
    en: enResult.text,
  };
}

async function handleParty({ interaction, db }) {
  await interaction.deferReply({ ephemeral: true });

  const motivo = interaction.options.getString('motivo', true);
  const inicio = interaction.options.getString('inicio', true);
  const fim = interaction.options.getString('fim', true);

  const tz = await db.getPlayerTimezone(interaction.user.id);
  if (!tz) {
    await interaction.editReply({
      content: 'Antes de criar uma party, escolha sua cidade:',
      components: [buildTimezoneSelect()],
    });
    return;
  }

  const start = DateTime.fromFormat(inicio, 'yyyy-MM-dd HH:mm', { zone: tz });
  const end = DateTime.fromFormat(fim, 'HH:mm', { zone: tz }).set({
    year: start.year,
    month: start.month,
    day: start.day,
  });

  if (!start.isValid || !end.isValid) {
    await interaction.editReply('❌ Formato inválido.\nUse:\n`2025-12-25 20:00` e `22:00`');
    return;
  }

  const startTs = Math.floor(start.toSeconds());
  const endTs = Math.floor(end.toSeconds());

  const reason = await translateReason(motivo);

  const members = [interaction.user.toString()];
  const embed = buildPartyEmbed({
    reasonPt: reason.pt,
    reasonEn: reason.en,
    startTs,
    endTs,
    creatorName: interaction.user.displayName || interaction.user.username,
    members,
  });

  const msg = await interaction.channel.send({ embeds: [embed] });
  await msg.react('✅');

  await db.addParty({
    messageId: msg.id,
    channelId: msg.channel.id,
    creatorId: interaction.user.id,
    reasonPt: reason.pt,
    reasonEn: reason.en,
    startTs,
    endTs,
  });

  await interaction.editReply('✅ Party criada com sucesso.');
}

async function handlePartyDelete({ interaction, db }) {
  const party = await db.getPartyByCreator(interaction.user.id);
  if (!party) {
    await interaction.reply({ content: '❌ Você não tem party ativa.', ephemeral: true });
    return;
  }

  const channel = await interaction.client.channels.fetch(party.channel_id).catch(() => null);
  if (channel) {
    const msg = await channel.messages.fetch(party.message_id).catch(() => null);
    if (msg) {
      await msg.delete().catch(() => null);
    }
  }

  await db.deletePartyByMessageId(party.message_id);
  await interaction.reply({ content: '🧹 Party apagada.', ephemeral: true });
}

async function handlePartyClearAll({ interaction, db }) {
  const parties = await db.getAllParties();

  for (const party of parties) {
    const channel = await interaction.client.channels.fetch(party.channel_id).catch(() => null);
    if (!channel) {
      continue;
    }
    const msg = await channel.messages.fetch(party.message_id).catch(() => null);
    if (msg) {
      await msg.delete().catch(() => null);
    }
  }

  await db.clearParties();
  await interaction.reply({ content: '🔥 Todas as partys foram apagadas.', ephemeral: true });
}

function registerParty({ client, db }) {
  client.on('interactionCreate', async (interaction) => {
    if (interaction.isStringSelectMenu()) {
      if (interaction.customId !== TIMEZONE_SELECT_ID) {
        return;
      }

      const tz = interaction.values[0];
      await db.updatePlayerTimezone(interaction.user.id, tz);
      await interaction.reply({
        content: '✅ Cidade salva. Nunca mais pergunto 😉',
        ephemeral: true,
      });
      return;
    }

    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (interaction.commandName === 'party') {
      await handleParty({ interaction, db });
      return;
    }

    if (interaction.commandName === 'party_delete') {
      await handlePartyDelete({ interaction, db });
      return;
    }

    if (interaction.commandName === 'party_clear_all') {
      await handlePartyClearAll({ interaction, db });
    }
  });
}

module.exports = {
  commands: [partyCommand, deleteCommand, clearCommand],
  registerParty,
};
