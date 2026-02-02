require('dotenv').config();

const {
  Client,
  GatewayIntentBits,
  Partials,
  REST,
  Routes,
} = require('discord.js');

const db = require('./db');
const { config } = require('./config');
const { createLogger } = require('./logger');

const { command: remindersCommand, registerReminders } = require('./cogs/reminders');
const { commands: playersCommands, registerPlayers } = require('./cogs/players');
const { commands: partyCommands, registerParty } = require('./cogs/party');
const { registerPartyEvents } = require('./cogs/party_events');
const { startWeeklyScheduler } = require('./cogs/scheduler');
const { command: forumAnnounceCommand, registerForumAnnounce } = require('./cogs/forum_announce');
const { commands: forumDeliveryCommands, registerForumDelivery } = require('./cogs/forum_delivery');
const { commands: dailyCommands, registerDailyAnnouncement } = require('./cogs/daily_announcement');
const { commands: itemRequestsCommands, registerItemRequests } = require('./cogs/item_requests');
const { command: itemRequestsAdminCommand, registerItemRequestsAdmin } = require('./cogs/item_requests_admin');
const { startItemRequestScheduler } = require('./cogs/item_requests_scheduler');
const { command: cadastrarItemCommand, registerCadastrarItem } = require('./cogs/cadastrar_item');
const { commands: playerProgressCommands, registerPlayerProgress } = require('./cogs/player_progress');
const { commands: rotationCommands, registerRotationEligibility } = require('./cogs/rotation_eligibility');

const logger = createLogger(config.logLevel);

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.GuildMessageReactions,
    GatewayIntentBits.MessageContent,
  ],
  partials: [Partials.Message, Partials.Reaction, Partials.Channel],
});

const commandList = [
  remindersCommand,
  ...playersCommands,
  ...partyCommands,
  forumAnnounceCommand,
  ...forumDeliveryCommands,
  ...dailyCommands,
  ...itemRequestsCommands,
  itemRequestsAdminCommand,
  cadastrarItemCommand,
  ...playerProgressCommands,
  ...rotationCommands,
].filter(Boolean);

async function registerCommands() {
  if (!config.token || !config.guildId) {
    logger.warn('DISCORD_TOKEN ou GUILD_ID não definido; pulando registro de comandos.');
    return;
  }

  const rest = new REST({ version: '10' }).setToken(config.token);
  await rest.put(Routes.applicationGuildCommands(client.user.id, config.guildId), {
    body: commandList.map((cmd) => cmd.toJSON()),
  });
  logger.info('Slash commands registrados.');
}

client.once('ready', async () => {
  logger.info(`Bot online como ${client.user.tag}`);

  await registerCommands();

  registerReminders({
    client,
    db,
    announcementsChannelId: config.announcementsChannelId,
    g3xRoleId: config.g3xRoleId,
  });
  registerPlayers({
    client,
    db,
    categoryId: config.categoryId,
    staffRoleId: config.staffRoleId,
  });
  registerParty({ client, db });
  registerPartyEvents({ client, db });
  startWeeklyScheduler({ client, db });
  registerForumAnnounce({
    client,
    db,
    staffChannelId: config.staffChannelId,
    forumChannelId: config.forumChannelId,
    forumTagId: config.forumTagId,
    g3xRoleId: config.g3xRoleId,
  });
  registerForumDelivery({
    client,
    db,
    forumChannelId: config.forumChannelId,
  });
  registerDailyAnnouncement({
    client,
    db,
    forceChannelId: config.announcementsChannelId,
  });
  registerItemRequests({
    client,
    db,
    staffRoleId: config.staffRoleId,
  });
  registerItemRequestsAdmin({
    client,
    db,
    summaryChannelId: config.itemRequestSummaryChannelId,
  });
  startItemRequestScheduler({
    client,
    db,
    summaryChannelId: config.itemRequestSummaryChannelId,
  });
  registerCadastrarItem({
    client,
    db,
    staffRoleId: config.staffRoleId,
  });
  registerPlayerProgress({ client, db });
  registerRotationEligibility({ client, db });
});

client.on('interactionCreate', (interaction) => {
  if (interaction.isCommand()) {
    logger.info(`SLASH | /${interaction.commandName} | user=${interaction.user.id}`);
  }
});

client.on('error', (error) => {
  logger.error('Client error', error);
});

client.login(config.token);
