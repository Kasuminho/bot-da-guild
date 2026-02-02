const {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
} = require('discord.js');

const { TEXT } = require('../utils/i18n');
const { FIXED_ITEMS, ITEM_CHOICES } = require('../utils/fixed_items');

const lang = 'pt';

const addCommand = new SlashCommandBuilder()
  .setName('request_add')
  .setDescription('Cria ou atualiza um request de item (usar dentro da thread)')
  .addUserOption((option) =>
    option.setName('player').setDescription('Player').setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('item')
      .setDescription('Item solicitado')
      .setRequired(true)
      .addChoices(...ITEM_CHOICES),
  )
  .addIntegerOption((option) =>
    option
      .setName('quantity')
      .setDescription('Quantidade total desejada')
      .setRequired(true),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

const updateCommand = new SlashCommandBuilder()
  .setName('request_update')
  .setDescription('Registra atualização (print) do request da thread')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

const deliverCommand = new SlashCommandBuilder()
  .setName('request_deliver')
  .setDescription('Registra entrega parcial ou total do item')
  .addStringOption((option) =>
    option
      .setName('item')
      .setDescription('Item a Entregar')
      .setRequired(true)
      .addChoices(...ITEM_CHOICES),
  )
  .addIntegerOption((option) =>
    option
      .setName('quantity')
      .setDescription('Quantidade a entregar')
      .setRequired(true),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

const rankCommand = new SlashCommandBuilder()
  .setName('request_rank')
  .setDescription('Mostra o ranking atual de um item')
  .addStringOption((option) =>
    option
      .setName('item')
      .setDescription('Item')
      .setRequired(true)
      .addChoices(...ITEM_CHOICES),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

const infoCommand = new SlashCommandBuilder()
  .setName('request_info')
  .setDescription('Mostra informações do request da thread atual')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

const deleteCommand = new SlashCommandBuilder()
  .setName('request_delete')
  .setDescription('Remove este request de item')
  .addStringOption((option) =>
    option
      .setName('item')
      .setDescription('Item a remover')
      .setRequired(true)
      .addChoices(...ITEM_CHOICES),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

function formatText(template, values) {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replace(`{${key}}`, value),
    template,
  );
}

function ensureThread(interaction) {
  if (!interaction.channel || !interaction.channel.isThread()) {
    throw new Error(TEXT.thread_only[lang]);
  }
}

async function handleAdd({ interaction, db }) {
  ensureThread(interaction);

  const player = interaction.options.getUser('player', true);
  const itemKey = interaction.options.getString('item', true);
  const quantity = interaction.options.getInteger('quantity', true);

  if (quantity <= 0) {
    await interaction.reply({ content: TEXT.qty_invalid[lang], ephemeral: true });
    return;
  }

  await db.addItemRequest(
    player.id,
    player.username,
    itemKey,
    quantity,
    interaction.channel.id,
    interaction.channel.parentId,
  );

  const itemName = FIXED_ITEMS[itemKey]?.[lang] || itemKey;
  await interaction.reply({
    content: formatText(TEXT.request_created[lang], {
      player: player.toString(),
      item: itemName,
      qty: quantity,
    }),
  });
}

async function handleUpdate({ interaction, db }) {
  ensureThread(interaction);

  const ok = await db.updateItemRequestByThread(interaction.channel.id);
  if (!ok) {
    await interaction.reply({
      content: TEXT.request_not_found[lang],
      ephemeral: true,
    });
    return;
  }

  await interaction.reply({ content: TEXT.request_updated[lang] });
}

async function handleDeliver({ interaction, db }) {
  ensureThread(interaction);

  const itemKey = interaction.options.getString('item', true);
  const quantity = interaction.options.getInteger('quantity', true);

  if (quantity <= 0) {
    await interaction.reply({ content: TEXT.qty_invalid[lang], ephemeral: true });
    return;
  }

  const ok = await db.deliverItemByThread(interaction.channel.id, itemKey, quantity);
  if (!ok) {
    await interaction.reply({
      content: TEXT.request_not_found[lang],
      ephemeral: true,
    });
    return;
  }

  await interaction.reply({
    content: formatText(TEXT.deliver_ok[lang], { qty: quantity }),
  });
}

async function handleRank({ interaction, db }) {
  const itemKey = interaction.options.getString('item', true);
  const rows = await db.getDailyItemSummary();
  const filtered = rows.filter((row) => row.item_name === itemKey);

  if (filtered.length === 0) {
    await interaction.reply({ content: TEXT.rank_empty[lang], ephemeral: true });
    return;
  }

  let message = `${formatText(TEXT.rank_header[lang], {
    item: FIXED_ITEMS[itemKey]?.[lang] || itemKey,
  })}\n\n`;

  for (const row of filtered) {
    const thread = await interaction.client.channels.fetch(row.thread_id).catch(() => null);
    const link = thread?.url || '';
    message += `${formatText(TEXT.rank_line[lang], {
      remaining: row.remaining_quantity,
      link,
    })}\n`;
  }

  await interaction.reply({ content: message });
}

async function handleInfo({ interaction, db }) {
  ensureThread(interaction);

  const req = await db.getItemRequestByThread(interaction.channel.id);
  if (!req) {
    await interaction.reply({ content: TEXT.request_not_found[lang], ephemeral: true });
    return;
  }

  const daysIdle = Math.floor((Date.now() / 1000 - req.last_update) / 86400);
  const itemName = FIXED_ITEMS[req.item_name]?.[lang] || req.item_name;

  await interaction.reply({
    content: formatText(TEXT.request_info[lang], {
      player: req.player_name,
      item: itemName,
      rank: req.rank_position,
      days: daysIdle,
      link: interaction.channel.url,
    }),
  });
}

async function handleDelete({ interaction, db }) {
  ensureThread(interaction);

  const itemKey = interaction.options.getString('item', true);
  const req = await db.getRequestByThread(interaction.channel.id, itemKey);

  if (!req) {
    await interaction.reply({
      content: '❌ This thread is not linked to any request.',
      ephemeral: true,
    });
    return;
  }

  await db.deleteRequest(req.id);
  await db.reorderItemRanks(req.item_name);

  await interaction.reply({
    content: `🗑️ Request for **${req.item_name}** removed successfully.`,
  });

  await interaction.channel.send('🗑️ This request was removed from the rank.')
    .catch(() => null);
}

function registerItemRequests({ client, db, staffRoleId }) {
  client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (!interaction.member.roles.cache.has(staffRoleId)) {
      return;
    }

    try {
      if (interaction.commandName === 'request_add') {
        await handleAdd({ interaction, db });
        return;
      }

      if (interaction.commandName === 'request_update') {
        await handleUpdate({ interaction, db });
        return;
      }

      if (interaction.commandName === 'request_deliver') {
        await handleDeliver({ interaction, db });
        return;
      }

      if (interaction.commandName === 'request_rank') {
        await handleRank({ interaction, db });
        return;
      }

      if (interaction.commandName === 'request_info') {
        await handleInfo({ interaction, db });
        return;
      }

      if (interaction.commandName === 'request_delete') {
        await handleDelete({ interaction, db });
      }
    } catch (error) {
      await interaction.reply({ content: error.message, ephemeral: true });
    }
  });
}

module.exports = {
  commands: [
    addCommand,
    updateCommand,
    deliverCommand,
    rankCommand,
    infoCommand,
    deleteCommand,
  ],
  registerItemRequests,
};
