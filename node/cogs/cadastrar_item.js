const {
  SlashCommandBuilder,
  PermissionFlagsBits,
} = require('discord.js');
const path = require('path');
const fs = require('fs/promises');

const ASSETS_DIR = path.join('assets', 'forum_items');

const command = new SlashCommandBuilder()
  .setName('cadastraritem')
  .setDescription('Cadastrar um novo item')
  .addStringOption((option) =>
    option
      .setName('kind')
      .setDescription('Tipo do item')
      .setRequired(true)
      .addChoices(
        { name: 'equipment', value: 'equipment' },
        { name: 'skill', value: 'skill' },
      ),
  )
  .addStringOption((option) =>
    option
      .setName('category')
      .setDescription('Categoria do item')
      .setRequired(true)
      .addChoices(
        { name: 'rare', value: 'rare' },
        { name: 'heroic', value: 'heroic' },
        { name: 'legendary', value: 'legendary' },
      ),
  )
  .addStringOption((option) =>
    option
      .setName('item_pt')
      .setDescription('Nome do item em português')
      .setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('item_en')
      .setDescription('Nome do item em inglês')
      .setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('type_pt')
      .setDescription('Tipo em português')
      .setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('type_en')
      .setDescription('Tipo em inglês')
      .setRequired(true),
  )
  .addAttachmentOption((option) =>
    option
      .setName('image1')
      .setDescription('Primeira imagem')
      .setRequired(true),
  )
  .addAttachmentOption((option) =>
    option
      .setName('image2')
      .setDescription('Segunda imagem')
      .setRequired(true),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

async function downloadAttachment(attachment, targetPath) {
  const response = await fetch(attachment.url);
  if (!response.ok) {
    throw new Error(`Falha ao baixar ${attachment.url}`);
  }
  const buffer = Buffer.from(await response.arrayBuffer());
  await fs.writeFile(targetPath, buffer);
}

async function handleRegister({ interaction, db }) {
  await interaction.deferReply({ ephemeral: true });

  const kind = interaction.options.getString('kind', true);
  const category = interaction.options.getString('category', true);
  const itemPt = interaction.options.getString('item_pt', true);
  const itemEn = interaction.options.getString('item_en', true);
  const typePt = interaction.options.getString('type_pt', true);
  const typeEn = interaction.options.getString('type_en', true);
  const image1 = interaction.options.getAttachment('image1', true);
  const image2 = interaction.options.getAttachment('image2', true);

  const timestamp = Math.floor(Date.now() / 1000);
  const itemDir = path.join(ASSETS_DIR, String(timestamp));
  await fs.mkdir(itemDir, { recursive: true });

  const path1 = path.join(itemDir, '1.png');
  const path2 = path.join(itemDir, '2.png');

  await downloadAttachment(image1, path1);
  await downloadAttachment(image2, path2);

  await db.addForumItem(
    kind,
    category,
    itemPt,
    itemEn,
    typePt,
    typeEn,
    path1,
    path2,
  );

  await interaction.editReply(
    `✅ Item \\`${itemPt} / ${itemEn}\\` cadastrado com sucesso!`,
  );
}

function registerCadastrarItem({ client, db, staffRoleId }) {
  client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (interaction.commandName !== 'cadastraritem') {
      return;
    }

    if (!interaction.member.roles.cache.has(staffRoleId)) {
      await interaction.reply({ content: 'Comando exclusivo da staff.', ephemeral: true });
      return;
    }

    try {
      await handleRegister({ interaction, db });
    } catch (error) {
      await interaction.editReply({ content: error.message, ephemeral: true });
    }
  });
}

module.exports = {
  command,
  registerCadastrarItem,
};
