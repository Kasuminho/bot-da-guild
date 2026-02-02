const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');
const { sendItemSummary } = require('./item_requests_scheduler');

const summaryCommand = new SlashCommandBuilder()
  .setName('request_summary')
  .setDescription('Posta o ranking de requests manualmente')
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageMessages);

function registerItemRequestsAdmin({ client, db, summaryChannelId }) {
  client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (interaction.commandName !== 'request_summary') {
      return;
    }

    await interaction.deferReply({ ephemeral: true });
    await sendItemSummary({ client, db, summaryChannelId });
    await interaction.editReply('✅ Ranking postado com sucesso.');
  });
}

module.exports = {
  command: summaryCommand,
  registerItemRequestsAdmin,
};
