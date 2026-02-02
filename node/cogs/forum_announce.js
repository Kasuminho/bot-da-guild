const {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ActionRowBuilder,
  StringSelectMenuBuilder,
  ButtonBuilder,
  ButtonStyle,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
  AttachmentBuilder,
  ChannelType,
} = require('discord.js');
const { DateTime } = require('luxon');

const ITEMS_PER_PAGE = 25;

const TIMEZONES = {
  'Brasil (America/Sao_Paulo)': 'America/Sao_Paulo',
  UTC: 'UTC',
};

const CRITERIA_TEXTS = {
  'skill|PvE': {
    pt: (
      '• Jogadores que utilizam esta skill\n'
      + '• Skill inferior à anunciada\n'
      + '• Participação em boss é obrigatória'
    ),
    en: (
      '• Players who use this skill\n'
      + '• Skill inferior to the announced one\n'
      + '• Boss participation is mandatory'
    ),
  },
  'skill|PvP': {
    pt: (
      '• Jogadores que utilizam esta skill\n'
      + '• Skill inferior à anunciada\n'
      + '• Level 75+ obrigatório\n'
      + '• Prioridade por nível'
    ),
    en: (
      '• Players who use this skill\n'
      + '• Skill inferior to the announced one\n'
      + '• Mandatory Level 75+\n'
      + '• Priority by level'
    ),
  },
  'equipment|PvE': {
    pt: (
      '• Jogadores que utilizam este equipamento\n'
      + '• Equipamento inferior ao anunciado\n'
      + '• Participação em boss é obrigatória'
    ),
    en: (
      '• Players who use this equipment\n'
      + '• Equipment inferior to the announced one\n'
      + '• Boss participation is mandatory'
    ),
  },
  'equipment|PvP': {
    pt: (
      '• Jogadores que utilizam este equipamento\n'
      + '• Equipamento inferior ao anunciado\n'
      + '• Level 75+ obrigatório\n'
      + '• Prioridade para quem falta ao item\n'
      + '• Enviar print dos equipamentos PvP'
    ),
    en: (
      '• Players who use this equipment\n'
      + '• Equipment inferior to the announced one\n'
      + '• Mandatory Level 75+\n'
      + '• Priority for players missing the item\n'
      + '• Send PvP equipment screenshot'
    ),
  },
};

const TYPE_SELECT_ID = 'forum-announce:type';
const ITEM_SELECT_ID = 'forum-announce:item';
const MODE_SELECT_ID = 'forum-announce:mode';
const TIMEZONE_SELECT_ID = 'forum-announce:timezone';
const PREV_BUTTON_ID = 'forum-announce:prev';
const NEXT_BUTTON_ID = 'forum-announce:next';
const DATETIME_MODAL_ID = 'forum-announce:datetime';
const DATETIME_INPUT_ID = 'forum-announce:datetime-input';

const flows = new Map();

const announceCommand = new SlashCommandBuilder()
  .setName('anunciar')
  .setDescription('Anúncio guiado')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

function buildTypeSelect() {
  return new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder()
      .setCustomId(TYPE_SELECT_ID)
      .setPlaceholder('Tipo do item')
      .addOptions(
        { label: 'Skill', value: 'skill' },
        { label: 'Equipment', value: 'equipment' },
      ),
  );
}

function buildItemSelect(items) {
  return new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder()
      .setCustomId(ITEM_SELECT_ID)
      .setPlaceholder('Selecione o item')
      .addOptions(
        items.map((item) => ({
          label: `${item.item_pt} / ${item.item_en}`,
          value: String(item.id),
        })),
      ),
  );
}

function buildPaginationControls({ canPrev, canNext }) {
  const row = new ActionRowBuilder();
  if (canPrev) {
    row.addComponents(
      new ButtonBuilder()
        .setCustomId(PREV_BUTTON_ID)
        .setLabel('⬅️ Anterior')
        .setStyle(ButtonStyle.Secondary),
    );
  }
  if (canNext) {
    row.addComponents(
      new ButtonBuilder()
        .setCustomId(NEXT_BUTTON_ID)
        .setLabel('➡️ Próximo')
        .setStyle(ButtonStyle.Secondary),
    );
  }
  return row.components.length > 0 ? row : null;
}

function buildModeSelect() {
  return new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder()
      .setCustomId(MODE_SELECT_ID)
      .setPlaceholder('Modo do item')
      .addOptions(
        { label: 'PvE', value: 'PvE' },
        { label: 'PvP', value: 'PvP' },
      ),
  );
}

function buildTimezoneSelect() {
  return new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder()
      .setCustomId(TIMEZONE_SELECT_ID)
      .setPlaceholder('Selecione o fuso horário')
      .addOptions(
        Object.entries(TIMEZONES).map(([label, value]) => ({ label, value })),
      ),
  );
}

function buildDatetimeModal() {
  return new ModalBuilder()
    .setCustomId(DATETIME_MODAL_ID)
    .setTitle('Finalizar anúncio')
    .addComponents(
      new ActionRowBuilder().addComponents(
        new TextInputBuilder()
          .setCustomId(DATETIME_INPUT_ID)
          .setLabel('Data e hora')
          .setPlaceholder('YYYY-MM-DD HH:MM')
          .setRequired(true)
          .setStyle(TextInputStyle.Short),
      ),
    );
}

async function renderItemsPage({ interaction, db, flow }) {
  const rawItems = await db.getForumItemsForSelect();
  const filtered = rawItems.filter((item) => item.kind === flow.itemType);
  if (filtered.length === 0) {
    await interaction.update({
      content: '❌ Nenhum item disponível.',
      components: [],
    });
    return;
  }

  const start = flow.page * ITEMS_PER_PAGE;
  const end = start + ITEMS_PER_PAGE;
  const pageItems = filtered.slice(start, end);

  const components = [buildItemSelect(pageItems)];
  const pagination = buildPaginationControls({
    canPrev: flow.page > 0,
    canNext: end < filtered.length,
  });
  if (pagination) {
    components.push(pagination);
  }

  flow.items = filtered;

  await interaction.update({
    content: 'Selecione o item:',
    components,
  });
}

async function finalizeAnnouncement({
  interaction,
  db,
  flow,
  timestamp,
  tzName,
  forumChannelId,
  forumTagId,
  g3xRoleId,
}) {
  const forum = await interaction.client.channels.fetch(forumChannelId).catch(() => null);
  if (!forum || forum.type !== ChannelType.GuildForum) {
    await interaction.editReply('❌ Fórum não encontrado.');
    return;
  }

  const item = await db.getForumItem(flow.itemId);
  if (!item) {
    await interaction.editReply('❌ Item não encontrado.');
    return;
  }

  const filePt = new AttachmentBuilder(item.image1_path);
  const fileEn = new AttachmentBuilder(item.image2_path);

  const thread = await forum.threads.create({
    name: `📢 Anúncio – ${item.item_en} / ${item.item_pt}`,
    message: {
      content: `<t:${timestamp}:F> \`${tzName}\``,
      files: [filePt, fileEn],
    },
    appliedTags: [forumTagId],
  });

  const criteria = CRITERIA_TEXTS[`${item.kind}|${flow.mode}`];

  await thread.send(
    `<@&${g3xRoleId}>\n\n`
      + '🇧🇷 **Português**\n'
      + `🟣 **Item:** ${item.item_pt}\n`
      + `📌 **Tipo:** ${item.type_pt}\n`
      + `🎯 **Categoria:** ${flow.mode}\n\n`
      + `${criteria.pt}\n\n`
      + '🇺🇸 **English**\n'
      + `🟣 **Item:** ${item.item_en}\n`
      + `📌 **Type:** ${item.type_en}\n`
      + `🎯 **Category:** ${flow.mode}\n\n`
      + `${criteria.en}\n\n`
      + `⏰ <t:${timestamp}:F>`,
  );

  await db.addForumPost(thread.id, timestamp);

  await interaction.editReply({
    content: '✅ Anúncio criado com sucesso.',
    components: [],
  });
}

function startForumWatcher({ client, db }) {
  const interval = setInterval(async () => {
    const now = Math.floor(Date.now() / 1000);
    const expired = await db.getOpenForumPosts(now);

    for (const post of expired) {
      const thread = await client.channels.fetch(post.thread_id).catch(() => null);
      if (thread) {
        await thread.send('⏰ **Anúncio encerrado automaticamente.**');
        await thread.setLocked(true);
      }
      await db.markForumPostClosed(post.id);
    }
  }, 60 * 1000);

  return () => clearInterval(interval);
}

function registerForumAnnounce({
  client,
  db,
  staffChannelId,
  forumChannelId,
  forumTagId,
  g3xRoleId,
}) {
  startForumWatcher({ client, db });

  client.on('interactionCreate', async (interaction) => {
    if (interaction.isChatInputCommand()) {
      if (interaction.commandName !== 'anunciar') {
        return;
      }

      if (interaction.channelId !== staffChannelId) {
        await interaction.reply({
          content: 'Somente no canal da staff.',
          ephemeral: true,
        });
        return;
      }

      flows.set(interaction.user.id, {
        itemType: null,
        itemId: null,
        mode: null,
        page: 0,
        items: [],
      });

      await interaction.reply({
        content: '📢 **Fluxo de anúncio iniciado**',
        components: [buildTypeSelect()],
        ephemeral: true,
      });
      return;
    }

    if (interaction.isStringSelectMenu()) {
      const flow = flows.get(interaction.user.id);
      if (!flow) {
        return;
      }

      if (interaction.customId === TYPE_SELECT_ID) {
        flow.itemType = interaction.values[0];
        flow.page = 0;
        await renderItemsPage({ interaction, db, flow });
        return;
      }

      if (interaction.customId === ITEM_SELECT_ID) {
        flow.itemId = Number(interaction.values[0]);
        await interaction.update({
          content: 'Selecione o modo:',
          components: [buildModeSelect()],
        });
        return;
      }

      if (interaction.customId === MODE_SELECT_ID) {
        flow.mode = interaction.values[0];
        await interaction.update({
          content: '🌍 Selecione o fuso horário:',
          components: [buildTimezoneSelect()],
        });
        return;
      }

      if (interaction.customId === TIMEZONE_SELECT_ID) {
        flow.tzName = interaction.values[0];
        await interaction.showModal(buildDatetimeModal());
        return;
      }
    }

    if (interaction.isButton()) {
      const flow = flows.get(interaction.user.id);
      if (!flow) {
        return;
      }

      if (interaction.customId === PREV_BUTTON_ID) {
        flow.page = Math.max(0, flow.page - 1);
        await renderItemsPage({ interaction, db, flow });
        return;
      }

      if (interaction.customId === NEXT_BUTTON_ID) {
        flow.page += 1;
        await renderItemsPage({ interaction, db, flow });
        return;
      }
    }

    if (interaction.isModalSubmit()) {
      if (interaction.customId !== DATETIME_MODAL_ID) {
        return;
      }

      const flow = flows.get(interaction.user.id);
      if (!flow) {
        return;
      }

      const inputValue = interaction.fields.getTextInputValue(DATETIME_INPUT_ID);
      const localDt = DateTime.fromFormat(inputValue, 'yyyy-MM-dd HH:mm', {
        zone: flow.tzName || 'UTC',
      });

      if (!localDt.isValid) {
        await interaction.reply({
          content: '❌ Formato inválido. Use YYYY-MM-DD HH:MM',
          ephemeral: true,
        });
        return;
      }

      const timestamp = Math.floor(localDt.toUTC().toSeconds());
      if (timestamp <= Math.floor(Date.now() / 1000)) {
        await interaction.reply({
          content: '❌ A data precisa ser no futuro.',
          ephemeral: true,
        });
        return;
      }

      await interaction.deferReply({ ephemeral: true });
      await finalizeAnnouncement({
        interaction,
        db,
        flow,
        timestamp,
        tzName: flow.tzName,
        forumChannelId,
        forumTagId,
        g3xRoleId,
      });
      flows.delete(interaction.user.id);
    }
  });
}

module.exports = {
  command: announceCommand,
  registerForumAnnounce,
};
