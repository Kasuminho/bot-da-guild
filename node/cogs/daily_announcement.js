const {
  SlashCommandBuilder,
  AttachmentBuilder,
  EmbedBuilder,
  ActionRowBuilder,
  StringSelectMenuBuilder,
} = require('discord.js');
const fs = require('fs');
const path = require('path');
const { mkdir } = require('fs/promises');
const translate = require('@vitalets/google-translate-api');

const IMAGE_DIR = path.join('images', 'daily');
const DAILY_SELECT_ID = 'daily:select';

const createCommand = new SlashCommandBuilder()
  .setName('aviso_diario')
  .setDescription('Cria um aviso diário (máx 4 ativos)')
  .addStringOption((option) =>
    option
      .setName('texto_pt')
      .setDescription('Texto em português')
      .setRequired(true),
  )
  .addAttachmentOption((option) =>
    option
      .setName('imagem_pt')
      .setDescription('Imagem em português')
      .setRequired(true),
  )
  .addAttachmentOption((option) =>
    option
      .setName('imagem_en')
      .setDescription('Imagem em inglês')
      .setRequired(true),
  );

const disableCommand = new SlashCommandBuilder()
  .setName('aviso_diario_desativar')
  .setDescription('Desativa um aviso diário específico');

async function downloadAttachment(attachment, targetPath) {
  const response = await fetch(attachment.url);
  if (!response.ok) {
    throw new Error(`Falha ao baixar ${attachment.url}`);
  }
  const buffer = Buffer.from(await response.arrayBuffer());
  await fs.promises.writeFile(targetPath, buffer);
}

async function handleCreate({ interaction, db }) {
  await interaction.deferReply({ ephemeral: true });

  const active = await db.getActiveDailyAnnouncements();
  if (active.length >= 4) {
    await interaction.editReply('❌ Limite de 4 avisos ativos atingido.');
    return;
  }

  const textoPt = interaction.options.getString('texto_pt', true);
  const imagemPt = interaction.options.getAttachment('imagem_pt', true);
  const imagemEn = interaction.options.getAttachment('imagem_en', true);

  if (!imagemPt.contentType?.startsWith('image') || !imagemEn.contentType?.startsWith('image')) {
    await interaction.editReply('❌ Os anexos precisam ser imagens.');
    return;
  }

  const translation = await translate(textoPt, { to: 'en' });
  const textoEn = translation.text;

  await mkdir(IMAGE_DIR, { recursive: true });
  const ts = Math.floor(Date.now() / 1000);
  const imgPtPath = path.join(IMAGE_DIR, `${ts}_pt.png`);
  const imgEnPath = path.join(IMAGE_DIR, `${ts}_en.png`);

  await downloadAttachment(imagemPt, imgPtPath);
  await downloadAttachment(imagemEn, imgEnPath);

  await db.addDailyAnnouncement(textoPt, textoEn, imgPtPath, imgEnPath);

  await interaction.editReply('✅ Aviso diário criado com sucesso.');
}

function buildDisableSelect(announcements) {
  return new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder()
      .setCustomId(DAILY_SELECT_ID)
      .setPlaceholder('Selecione o aviso para desativar')
      .addOptions(
        announcements.map((ann) => ({
          label: ann.text_pt.slice(0, 80),
          value: String(ann.id),
        })),
      ),
  );
}

async function handleDisable({ interaction, db }) {
  const announcements = await db.getActiveDailyAnnouncements();
  if (announcements.length === 0) {
    await interaction.reply({ content: '❌ Nenhum aviso ativo.', ephemeral: true });
    return;
  }

  await interaction.reply({
    content: 'Selecione o aviso que deseja desativar:',
    components: [buildDisableSelect(announcements)],
    ephemeral: true,
  });
}

function startDailyLoop({ client, db, forceChannelId }) {
  const interval = setInterval(async () => {
    const now = new Date();
    if (now.getMinutes() !== 0) {
      return;
    }

    if (now.getHours() < 12 || now.getHours() > 15) {
      return;
    }

    const index = now.getHours() - 12;
    const announcements = await db.getActiveDailyAnnouncements();
    if (index >= announcements.length) {
      return;
    }

    const channel = await client.channels.fetch(forceChannelId).catch(() => null);
    if (!channel) {
      return;
    }

    const ann = announcements[index];
    const filePt = new AttachmentBuilder(ann.image_pt_path, { name: 'pt.png' });
    const fileEn = new AttachmentBuilder(ann.image_en_path, { name: 'en.png' });

    const embedPt = new EmbedBuilder()
      .setTitle('📢 Aviso')
      .setDescription(ann.text_pt)
      .setColor(0x2ecc71)
      .setImage('attachment://pt.png');

    const embedEn = new EmbedBuilder()
      .setTitle('📢 Notice')
      .setDescription(ann.text_en)
      .setColor(0x3498db)
      .setImage('attachment://en.png');

    await channel.send({ embeds: [embedPt, embedEn], files: [filePt, fileEn] });
  }, 60 * 1000);

  return () => clearInterval(interval);
}

function registerDailyAnnouncement({ client, db, forceChannelId }) {
  startDailyLoop({ client, db, forceChannelId });

  client.on('interactionCreate', async (interaction) => {
    if (interaction.isStringSelectMenu()) {
      if (interaction.customId !== DAILY_SELECT_ID) {
        return;
      }

      const annId = Number(interaction.values[0]);
      await db.deactivateDailyAnnouncement(annId);
      await interaction.reply({
        content: '✅ Aviso desativado com sucesso.',
        ephemeral: true,
      });
      return;
    }

    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (interaction.commandName === 'aviso_diario') {
      await handleCreate({ interaction, db });
      return;
    }

    if (interaction.commandName === 'aviso_diario_desativar') {
      await handleDisable({ interaction, db });
    }
  });
}

module.exports = {
  commands: [createCommand, disableCommand],
  registerDailyAnnouncement,
};
