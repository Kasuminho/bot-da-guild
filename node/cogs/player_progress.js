const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');

const registerLevelCommand = new SlashCommandBuilder()
  .setName('registrarlevel')
  .setDescription('Registrar level diário do jogador')
  .addUserOption((option) =>
    option.setName('jogador').setDescription('Jogador').setRequired(true),
  )
  .addIntegerOption((option) =>
    option.setName('level').setDescription('Level').setRequired(true),
  )
  .addIntegerOption((option) =>
    option
      .setName('dias_atras')
      .setDescription('Dias retroativos')
      .setRequired(false),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

const checkLevelsCommand = new SlashCommandBuilder()
  .setName('checarniveis')
  .setDescription('Ver jogadores sem progresso nos últimos 3 dias')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

async function handleRegisterLevel({ interaction, db }) {
  const jogador = interaction.options.getUser('jogador', true);
  const level = interaction.options.getInteger('level', true);
  const diasAtras = interaction.options.getInteger('dias_atras') || 0;

  if (diasAtras < 0 || diasAtras > 3) {
    await interaction.reply({
      content: '❌ Só é permitido até 3 dias retroativos.',
      ephemeral: true,
    });
    return;
  }

  try {
    await db.addPlayerLevel(jogador.id, jogador.username, level, diasAtras);
  } catch (error) {
    await interaction.reply({
      content: '⚠️ Esse jogador já tem registro nesse dia.',
      ephemeral: true,
    });
    return;
  }

  await interaction.reply({
    content: `✅ Level **${level}** registrado para ${jogador.toString()}.`,
    ephemeral: true,
  });
}

async function handleCheckLevels({ interaction, db }) {
  const stuck = await db.getPlayersStuck3Days();
  if (!stuck || stuck.length === 0) {
    await interaction.reply({ content: '🚀 Todos estão progredindo!', ephemeral: true });
    return;
  }

  const lines = stuck.map((row) => `• <@${row.player_id}> (${row.player_name})`);
  const message = `⚠️ **Jogadores sem progresso há 3 dias:**\n\n${lines.join('\n')}`;
  await interaction.reply({ content: message, ephemeral: true });
}

function startCleanupLoop({ db }) {
  const interval = setInterval(async () => {
    await db.cleanupOldPlayers();
  }, 24 * 60 * 60 * 1000);

  return () => clearInterval(interval);
}

function registerPlayerProgress({ client, db }) {
  startCleanupLoop({ db });

  client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (interaction.commandName === 'registrarlevel') {
      await handleRegisterLevel({ interaction, db });
      return;
    }

    if (interaction.commandName === 'checarniveis') {
      await handleCheckLevels({ interaction, db });
    }
  });
}

module.exports = {
  commands: [registerLevelCommand, checkLevelsCommand],
  registerPlayerProgress,
};
