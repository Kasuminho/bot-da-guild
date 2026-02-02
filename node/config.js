const config = {
  token: process.env.DISCORD_TOKEN,
  databaseUrl: process.env.DATABASE_URL,
  logLevel: process.env.LOG_LEVEL || 'info',
  staffRoleId: Number(process.env.STAFF_ROLE_ID || 0),
  categoryId: Number(process.env.CATEGORY_ID || 0),
  announcementsChannelId: Number(process.env.ANNOUNCEMENTS_CHANNEL_ID || 0),
  guildId: Number(process.env.GUILD_ID || 0),
  forumChannelId: Number(process.env.FORUM_CHANNEL_ID || 0),
  forumTagId: Number(process.env.FORUM_TAG_ID || 0),
  g3xRoleId: Number(process.env.G3X_ROLE_ID || 0),
  staffChannelId: Number(process.env.STAFF_CHANNEL_ID || 0),
  itemRequestSummaryChannelId: Number(
    process.env.ITEM_REQUEST_SUMMARY_CHANNEL_ID || 0,
  ),
};

module.exports = {
  config,
};
