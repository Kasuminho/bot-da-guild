const {
  SlashCommandBuilder,
  PermissionFlagsBits,
  ChannelType,
} = require('discord.js');

const PLAYER_CLASSES = [
  '🏥 Divine Caster',
  '☠️ Deathbringer',
  '🧙‍♂️ Elementalist',
  '🔫 Gunslinger',
  '🏹 Night Ranger',
  '🏹 Destroyer',
  '🛡️ Vanguard',
  '⚔️ Berserker',
  '🗡️ Assassin',
];

const PLAYER_ICON = {
  '🏥 Divine Caster': '🏥',
  '☠️ Deathbringer': '☠️',
  '🧙‍♂️ Elementalist': '🧙‍♂️',
  '🔫 Gunslinger': '🔫',
  '🏹 Night Ranger': '🏹',
  '🏹 Destroyer': '🏹',
  '🛡️ Vanguard': '🛡️',
  '⚔️ Berserker': '⚔️',
  '🗡️ Assassin': '🗡️',
};

const command = new SlashCommandBuilder()
  .setName('cadastrarjogador')
  .setDescription('Cadastrar jogador e criar canal dedicado')
  .addUserOption((option) =>
    option.setName('jogador').setDescription('Jogador').setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('nick_ingame')
      .setDescription('Nickname no jogo')
      .setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('idioma')
      .setDescription('Idioma')
      .setRequired(true)
      .addChoices(
        { name: 'PT', value: 'PT' },
        { name: 'EN', value: 'EN' },
      ),
  )
  .addStringOption((option) =>
    option
      .setName('classe')
      .setDescription('Classe')
      .setRequired(true)
      .addChoices(...PLAYER_CLASSES.map((value) => ({ name: value, value }))),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels);

const associateCommand = new SlashCommandBuilder()
  .setName('associarcanal')
  .setDescription('Associar canal e idioma a um jogador')
  .addUserOption((option) =>
    option.setName('jogador').setDescription('Jogador').setRequired(true),
  )
  .addChannelOption((option) =>
    option
      .setName('canal')
      .setDescription('Canal')
      .addChannelTypes(ChannelType.GuildText)
      .setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('idioma')
      .setDescription('Idioma')
      .setRequired(true)
      .addChoices(
        { name: 'PT', value: 'PT' },
        { name: 'EN', value: 'EN' },
      ),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels);

const inactiveCommand = new SlashCommandBuilder()
  .setName('verificarinativos')
  .setDescription('Verifica jogadores inativos por 3 dias')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageChannels);

function buildPlayerMessage({ idioma, jogadorId, classe }) {
  if (idioma === 'PT') {
    return (
      `Oi, <@${jogadorId}>! Bem-vindo ao G3X! 🔥\n\n`
      + 'Como você entrou recentemente, queria explicar um procedimento que já utilizamos '
      + 'com todos os membros para ajudar no progresso dentro da guilda.\n\n'
      + 'Coletamos algumas capturas de tela da sua conta para que possamos revisar seu progresso '
      + 'e fornecer dicas personalizadas de melhoria. Isso nos ajuda a entender seus pontos fortes '
      + 'e ver onde podemos apoiar ainda mais seu crescimento.\n\n'
      + 'Quando possível, por favor, envie capturas de tela de:\n\n'
      + '• Stellas – Amplificação\n'
      + '• Equipamentos\n'
      + '• Relíquias\n'
      + '• Estigma\n'
      + '• Coleção de itens\n'
      + '• Habilidades\n'
      + '• Pedras do Paraíso\n\n'
      + 'Isso é algo que já fazemos com todos desde o início, e como você não viu o primeiro anúncio, '
      + 'estamos apenas compartilhando com você agora. 😊\n\n'
      + 'Se você tiver alguma dúvida sobre como tirar ou enviar as capturas de tela, '
      + 'fique à vontade para entrar em contato com qualquer ADM. Estamos aqui para ajudar!\n\n'
      + `🧩 **Classe:** ${classe}`
    );
  }

  return (
    `Hi, <@${jogadorId}>! Welcome to G3X! 🔥\n\n`
    + 'Since you joined recently, I wanted to explain a procedure we already use '
    + 'with all members to help with progression inside the guild.\n\n'
    + 'We collect some screenshots of your account so we can review your progression '
    + 'and provide personalized improvement tips. This helps us understand your strengths '
    + 'and see where we can support your growth even further.\n\n'
    + 'When possible, please send screenshots of:\n\n'
    + '• Stellas – Amplification\n'
    + '• Equipment\n'
    + '• Relics\n'
    + '• Stigma\n'
    + '• Item Collection\n'
    + '• Skills\n'
    + '• Heavenstones\n\n'
    + 'This is something we’ve done with everyone from the start, and since you didn’t see '
    + 'the first announcement, we’re just sharing it with you now. 😊\n\n'
    + 'If you have any questions about how to take or send the screenshots, '
    + 'feel free to contact any ADM. We’re here to help!\n\n'
    + `🧩 **Class:** ${classe}`
  );
}

async function handleCadastrarJogador({ interaction, db, categoryId, staffRoleId }) {
  const jogador = interaction.options.getUser('jogador', true);
  const nickIngame = interaction.options.getString('nick_ingame', true);
  const idioma = interaction.options.getString('idioma', true);
  const classe = interaction.options.getString('classe', true);

  const guild = interaction.guild;
  if (!guild) {
    await interaction.reply({ content: '❌ Comando só funciona em servidor.', ephemeral: true });
    return;
  }

  const staffRole = guild.roles.cache.get(staffRoleId);
  if (!staffRole) {
    await interaction.reply({ content: '❌ Role de staff não encontrada.', ephemeral: true });
    return;
  }

  const overwrites = [
    {
      id: guild.roles.everyone.id,
      deny: ['ViewChannel'],
    },
    {
      id: staffRole.id,
      allow: ['ViewChannel'],
    },
    {
      id: jogador.id,
      allow: ['ViewChannel'],
    },
    {
      id: guild.members.me.id,
      allow: ['ViewChannel', 'SendMessages', 'ReadMessageHistory'],
    },
  ];

  const channelName = `${PLAYER_ICON[classe]}${nickIngame.toLowerCase()}`;
  const channel = await guild.channels.create({
    name: channelName,
    type: ChannelType.GuildText,
    parent: categoryId,
    permissionOverwrites: overwrites,
  });

  const member = await guild.members.fetch(jogador.id).catch(() => null);
  if (member) {
    await member.setNickname(nickIngame).catch(() => null);
  }

  await db.addPlayer(jogador.id, nickIngame, idioma, channel.id);

  const message = buildPlayerMessage({ idioma, jogadorId: jogador.id, classe });
  await channel.send(message);

  await interaction.reply({ content: 'Jogador cadastrado com sucesso.', ephemeral: true });
}

async function handleAssociarCanal({ interaction, db }) {
  const jogador = interaction.options.getUser('jogador', true);
  const canal = interaction.options.getChannel('canal', true);
  const idioma = interaction.options.getString('idioma', true);

  await db.upsertPlayerChannelWithLanguage(jogador.id, idioma, canal.id);

  await interaction.reply({
    content: 'Canal associado e idioma registrado com sucesso.',
    ephemeral: true,
  });
}

async function handleVerificarInativos({ interaction, db }) {
  await interaction.deferReply({ ephemeral: true });

  const limitDate = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000);
  const players = await db.getAllPlayers();

  let totalAlertas = 0;
  for (const player of players) {
    const channel = interaction.guild.channels.cache.get(player.channel_id);
    if (!channel || channel.type !== ChannelType.GuildText) {
      continue;
    }

    const member = await interaction.guild.members.fetch(player.discord_id).catch(() => null);
    if (!member) {
      continue;
    }

    const messages = await channel.messages.fetch({ limit: 50 }).catch(() => null);
    if (!messages) {
      continue;
    }

    let lastMessageAt = null;
    for (const message of messages.values()) {
      if (message.author.id === player.discord_id) {
        lastMessageAt = message.createdAt;
        break;
      }
    }

    if (!lastMessageAt || lastMessageAt < limitDate) {
      totalAlertas += 1;
      const text = player.language === 'PT'
        ? (
          `${member.toString()}\n\n`
          + '⚠️ **CADE A ATUALIZAÇÃO, MEU CONSAGRADO?**\n\n'
          + 'Já fazem **mais de 3 dias** que você não posta nada aqui.\n'
          + 'Esse canal existe **JUSTAMENTE** pra isso.\n\n'
          + 'Posta tua atualização o quanto antes pra não virar problema.\n'
          + 'Obrigado.'
        )
        : (
          `${member.toString()}\n\n`
          + '⚠️ **WHERE IS YOUR UPDATE?**\n\n'
          + 'It has been **over 3 days** without any update from you.\n'
          + 'This channel exists **exactly** for that purpose.\n\n'
          + 'Please post your update as soon as possible.\n'
          + 'Thank you.'
        );

      await channel.send(text);
    }
  }

  await interaction.editReply(
    `Verificação concluída. Alertas enviados: **${totalAlertas}**.`,
  );
}

function registerPlayers({
  client,
  db,
  categoryId,
  staffRoleId,
}) {
  client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (interaction.commandName === 'cadastrarjogador') {
      await handleCadastrarJogador({ interaction, db, categoryId, staffRoleId });
      return;
    }

    if (interaction.commandName === 'associarcanal') {
      await handleAssociarCanal({ interaction, db });
      return;
    }

    if (interaction.commandName === 'verificarinativos') {
      await handleVerificarInativos({ interaction, db });
    }
  });
}

module.exports = {
  commands: [command, associateCommand, inactiveCommand],
  registerPlayers,
};
