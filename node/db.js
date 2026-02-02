const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
});

async function query(text, params) {
  const result = await pool.query(text, params);
  return result;
}

async function addPlayer(discordId, nickname, language, channelId) {
  await query(
    `
    INSERT INTO players (discord_id, nickname_ingame, language, channel_id)
    VALUES ($1, $2, $3, $4)
    ON CONFLICT (discord_id)
    DO UPDATE SET
      nickname_ingame = EXCLUDED.nickname_ingame,
      language = EXCLUDED.language,
      channel_id = EXCLUDED.channel_id
    `,
    [discordId, nickname, language, channelId],
  );
}

async function updateChannel(discordId, channelId) {
  await query('UPDATE players SET channel_id = $1 WHERE discord_id = $2', [
    channelId,
    discordId,
  ]);
}

async function getAllPlayers() {
  const result = await query('SELECT * FROM players', []);
  return result.rows;
}

async function getPlayerTimezone(discordId) {
  const result = await query(
    'SELECT timezone FROM players WHERE discord_id = $1',
    [discordId],
  );
  return result.rows[0]?.timezone ?? null;
}

async function updatePlayerTimezone(discordId, timezone) {
  await query('UPDATE players SET timezone = $1 WHERE discord_id = $2', [
    timezone,
    discordId,
  ]);
}

async function addReminder(tipo, nome, channelId, timestamp) {
  await query(
    `
    INSERT INTO one_time_reminders (tipo, nome, channel_id, timestamp)
    VALUES ($1, $2, $3, $4)
    `,
    [tipo, nome, channelId, timestamp],
  );
}

async function getActiveReminders() {
  const result = await query(
    `
    SELECT * FROM one_time_reminders
    WHERE sent = 0
    `,
    [],
  );
  return result.rows;
}

async function markWarned(reminderId, field) {
  const allowed = ['warned_1h', 'warned_30m', 'warned_now'];
  if (!allowed.includes(field)) {
    throw new Error(`Invalid reminder field: ${field}`);
  }
  await query(`UPDATE one_time_reminders SET ${field} = 1 WHERE id = $1`, [
    reminderId,
  ]);
}

async function markReminderSent(reminderId) {
  await query('UPDATE one_time_reminders SET sent = 1 WHERE id = $1', [
    reminderId,
  ]);
}

async function markAsSent(reminderId) {
  await markReminderSent(reminderId);
}

async function getPendingReminders(now) {
  const result = await query(
    'SELECT * FROM one_time_reminders WHERE sent = 0 AND timestamp <= $1',
    [now],
  );
  return result.rows;
}

async function upsertPlayerChannelWithLanguage(discordId, language, channelId) {
  await query(
    `
    INSERT INTO players (discord_id, nickname_ingame, language, channel_id)
    VALUES ($1, NULL, $2, $3)
    ON CONFLICT (discord_id)
    DO UPDATE SET
      channel_id = EXCLUDED.channel_id,
      language = EXCLUDED.language
    `,
    [discordId, language, channelId],
  );
}

async function addForumPost(threadId, closeTime) {
  await query(
    `
    INSERT INTO forum_posts (thread_id, close_time)
    SELECT $1, $2
    WHERE NOT EXISTS (
      SELECT 1
      FROM forum_posts
      WHERE thread_id = $1
    )
    `,
    [threadId, closeTime],
  );
}

async function getOpenForumPosts(now) {
  const result = await query(
    `
    SELECT id, thread_id
    FROM forum_posts
    WHERE closed = 0 AND close_time <= $1
    `,
    [now],
  );
  return result.rows;
}

async function markForumPostClosed(postId) {
  await query('UPDATE forum_posts SET closed = 1 WHERE id = $1', [postId]);
}

async function getForumPostByThread(threadId) {
  const result = await query(
    `
    SELECT id, close_time, closed, delivered
    FROM forum_posts
    WHERE thread_id = $1
    `,
    [threadId],
  );
  return result.rows[0] || null;
}

async function markForumPostDelivered(postId) {
  await query('UPDATE forum_posts SET delivered = 1 WHERE id = $1', [postId]);
}

async function addDrop(discordId, nickname, item, threadId, staffId) {
  await query(
    `
    INSERT INTO drops (
      discord_id,
      nickname_ingame,
      item,
      thread_id,
      staff_id,
      delivered_at
    ) VALUES ($1, $2, $3, $4, $5, $6)
    `,
    [discordId, nickname, item, threadId, staffId, Math.floor(Date.now() / 1000)],
  );
}

async function getLastDrop(discordId) {
  const result = await query(
    `
    SELECT delivered_at
    FROM drops
    WHERE discord_id = $1
    ORDER BY delivered_at DESC
    LIMIT 1
    `,
    [discordId],
  );
  return result.rows[0]?.delivered_at ?? null;
}

async function addDailyAnnouncement(textPt, textEn, imgPt, imgEn) {
  await query(
    `
    INSERT INTO daily_announcements
    (text_pt, text_en, image_pt_path, image_en_path, created_at)
    VALUES ($1, $2, $3, $4, $5)
    `,
    [textPt, textEn, imgPt, imgEn, Math.floor(Date.now() / 1000)],
  );
}

async function getActiveDailyAnnouncements() {
  const result = await query(
    `
    SELECT id, text_pt, text_en, image_pt_path, image_en_path
    FROM daily_announcements
    WHERE active = 1
    ORDER BY created_at ASC
    LIMIT 4
    `,
    [],
  );
  return result.rows;
}

async function deactivateDailyAnnouncement(announcementId) {
  await query('UPDATE daily_announcements SET active = 0 WHERE id = $1', [
    announcementId,
  ]);
}

async function getFutureReminders() {
  const now = Math.floor(Date.now() / 1000);
  const result = await query(
    `
    SELECT id, tipo, nome, channel_id, timestamp
    FROM one_time_reminders
    WHERE sent = 0
      AND timestamp > $1
    ORDER BY timestamp ASC
    `,
    [now],
  );
  return result.rows;
}

async function getReminderById(reminderId) {
  const result = await query(
    `
    SELECT tipo, nome, channel_id, timestamp
    FROM one_time_reminders
    WHERE id = $1
    `,
    [reminderId],
  );
  return result.rows[0] || null;
}

async function getPlayersStuck3Days() {
  const result = await query(
    `
    SELECT player_id, player_name
    FROM player_levels
    GROUP BY player_id
    HAVING COUNT(DISTINCT level) = 1
       AND COUNT(*) >= 3
    `,
    [],
  );
  return result.rows;
}

async function addPlayerLevel(playerId, playerName, level, daysAgo = 0) {
  if (daysAgo > 3) {
    throw new Error('Máximo de 3 dias retroativos');
  }

  const day = new Date();
  day.setUTCDate(day.getUTCDate() - daysAgo);
  const dayValue = Number(
    `${day.getUTCFullYear()}${String(day.getUTCMonth() + 1).padStart(2, '0')}${String(
      day.getUTCDate(),
    ).padStart(2, '0')}`,
  );

  await query(
    `
    INSERT INTO player_levels
    (player_id, player_name, level, day, created_at)
    VALUES ($1, $2, $3, $4, $5)
    ON CONFLICT (player_id, day) DO NOTHING
    `,
    [
      playerId,
      playerName,
      level,
      dayValue,
      Math.floor(Date.now() / 1000),
    ],
  );
}

async function cleanupOldPlayers() {
  const day = new Date();
  day.setUTCDate(day.getUTCDate() - 4);
  const limitDay = Number(
    `${day.getUTCFullYear()}${String(day.getUTCMonth() + 1).padStart(2, '0')}${String(
      day.getUTCDate(),
    ).padStart(2, '0')}`,
  );

  await query(
    `
    DELETE FROM player_levels
    WHERE player_id NOT IN (
      SELECT DISTINCT player_id
      FROM player_levels
      WHERE day >= $1
    )
    `,
    [limitDay],
  );
}

async function getPlayerDrops(playerId) {
  const result = await query(
    `
    SELECT item, delivered_at, staff_id
    FROM drops
    WHERE discord_id = $1
    ORDER BY delivered_at DESC
    LIMIT 10
    `,
    [playerId],
  );
  return result.rows;
}

async function addForumItem(
  kind,
  category,
  itemPt,
  itemEn,
  typePt,
  typeEn,
  image1Path,
  image2Path,
) {
  const result = await query(
    `
    INSERT INTO forum_items (
      kind,
      category,
      item_pt,
      item_en,
      type_pt,
      type_en,
      image1_path,
      image2_path,
      created_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    RETURNING id
    `,
    [
      kind,
      category,
      itemPt,
      itemEn,
      typePt,
      typeEn,
      image1Path,
      image2Path,
      Math.floor(Date.now() / 1000),
    ],
  );
  return result.rows[0]?.id ?? null;
}

async function getForumItem(itemId) {
  const result = await query(
    `
    SELECT
      id,
      kind,
      category,
      item_pt,
      item_en,
      type_pt,
      type_en,
      image1_path,
      image2_path
    FROM forum_items
    WHERE id = $1 AND active = 1
    `,
    [itemId],
  );
  return result.rows[0] || null;
}

async function getForumItemsByKind(kind) {
  const result = await query(
    `
    SELECT id, item_pt, item_en
    FROM forum_items
    WHERE kind = $1 AND active = 1
    ORDER BY item_pt ASC
    `,
    [kind],
  );
  return result.rows;
}

async function getAllForumItems() {
  const result = await query(
    'SELECT id, item_pt, item_en FROM forum_items ORDER BY id',
    [],
  );
  return result.rows;
}

async function getForumItemsForSelect() {
  const result = await query(
    `
    SELECT id, kind, item_pt, item_en
    FROM forum_items
    WHERE active = 1
    ORDER BY kind, item_pt ASC
    `,
    [],
  );
  return result.rows;
}

async function addRotation(rotationType, day) {
  const now = Math.floor(Date.now() / 1000);
  await query(
    `
    INSERT INTO boss_rotations (rotation_type, day, created_at)
    VALUES ($1, $2, $3)
    ON CONFLICT (rotation_type, day) DO NOTHING
    `,
    [rotationType, day, now],
  );

  const result = await query(
    `
    SELECT id
    FROM boss_rotations
    WHERE rotation_type = $1 AND day = $2
    `,
    [rotationType, day],
  );
  return result.rows[0]?.id ?? null;
}

async function getLastRotationDay() {
  const result = await query('SELECT MAX(day) AS max_day FROM boss_rotations', []);
  return result.rows[0]?.max_day ?? null;
}

async function getRotationsSince(sinceDay) {
  const result = await query(
    `
    SELECT id, day, rotation_type
    FROM boss_rotations
    WHERE day >= $1
    ORDER BY day DESC
    `,
    [sinceDay],
  );
  return result.rows;
}

async function hasParticipation(rotationId, discordId) {
  const result = await query(
    `
    SELECT 1
    FROM boss_participation
    WHERE rotation_id = $1
      AND discord_id = $2
    LIMIT 1
    `,
    [rotationId, discordId],
  );
  return result.rowCount > 0;
}

async function getOrCreateRotation(rotationType, day) {
  const now = Math.floor(Date.now() / 1000);
  await query(
    `
    INSERT INTO boss_rotations (rotation_type, day, created_at)
    VALUES ($1, $2, $3)
    ON CONFLICT (rotation_type, day) DO NOTHING
    `,
    [rotationType, day, now],
  );

  const result = await query(
    `
    SELECT id
    FROM boss_rotations
    WHERE rotation_type = $1 AND day = $2
    `,
    [rotationType, day],
  );
  return result.rows[0]?.id ?? null;
}

async function addParticipation(rotationId, discordId) {
  const result = await query(
    `
    INSERT INTO boss_participation (rotation_id, discord_id, present)
    VALUES ($1, $2, 1)
    ON CONFLICT (rotation_id, discord_id) DO NOTHING
    `,
    [rotationId, discordId],
  );
  return result.rowCount > 0;
}

async function getParticipationStats(discordId, startDay, endDay) {
  const totalResult = await query(
    `
    SELECT COUNT(*)::int AS total
    FROM boss_rotations
    WHERE day BETWEEN $1 AND $2
    `,
    [startDay, endDay],
  );

  const presencesResult = await query(
    `
    SELECT COUNT(*)::int AS total
    FROM boss_participation bp
    JOIN boss_rotations br ON br.id = bp.rotation_id
    WHERE bp.discord_id = $1
      AND br.day BETWEEN $2 AND $3
    `,
    [discordId, startDay, endDay],
  );

  const t4AbsencesResult = await query(
    `
    SELECT COUNT(*)::int AS total
    FROM boss_rotations br
    WHERE br.rotation_type = 'T4'
      AND br.day BETWEEN $1 AND $2
      AND br.id NOT IN (
        SELECT rotation_id
        FROM boss_participation
        WHERE discord_id = $3
      )
    `,
    [startDay, endDay, discordId],
  );

  return {
    total_rotations: totalResult.rows[0]?.total ?? 0,
    presences: presencesResult.rows[0]?.total ?? 0,
    t4_absences: t4AbsencesResult.rows[0]?.total ?? 0,
  };
}

async function getRotationHistory(discordId, startDay, endDay) {
  const result = await query(
    `
    SELECT
      br.day,
      br.rotation_type,
      CASE
        WHEN bp.id IS NOT NULL THEN 1
        ELSE 0
      END AS present
    FROM boss_rotations br
    LEFT JOIN boss_participation bp
      ON bp.rotation_id = br.id
      AND bp.discord_id = $1
    WHERE br.day BETWEEN $2 AND $3
    ORDER BY br.day ASC
    `,
    [discordId, startDay, endDay],
  );

  return result.rows.map((row) => ({
    day: row.day,
    type: row.rotation_type,
    present: Boolean(row.present),
  }));
}

async function addItemRequest(
  discordId,
  playerName,
  itemName,
  quantity,
  threadId,
  threadChannelId,
) {
  const now = Math.floor(Date.now() / 1000);
  const existing = await query(
    `
    SELECT id, total_quantity, remaining_quantity
    FROM item_requests
    WHERE discord_id = $1 AND item_name = $2
    `,
    [discordId, itemName],
  );

  if (existing.rowCount > 0) {
    const reqId = existing.rows[0].id;
    await query(
      `
      UPDATE item_requests
      SET total_quantity = $1,
          remaining_quantity = $1,
          last_update = $2
      WHERE id = $3
      `,
      [quantity, now, reqId],
    );
    return;
  }

  const lastRankResult = await query(
    `
    SELECT COALESCE(MAX(rank_position), 0) AS max_rank
    FROM item_requests
    WHERE item_name = $1
    `,
    [itemName],
  );

  const lastRank = lastRankResult.rows[0]?.max_rank ?? 0;

  await query(
    `
    INSERT INTO item_requests (
      discord_id,
      player_name,
      item_name,
      total_quantity,
      remaining_quantity,
      rank_position,
      thread_id,
      thread_channel_id,
      created_at,
      last_update
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    `,
    [
      discordId,
      playerName,
      itemName,
      quantity,
      quantity,
      lastRank + 1,
      threadId,
      threadChannelId,
      now,
      now,
    ],
  );
}

async function updateItemRequestByThread(threadId) {
  const now = Math.floor(Date.now() / 1000);
  const result = await query(
    `
    UPDATE item_requests
    SET last_update = $1,
        warned_3d = 0,
        warned_4d = 0
    WHERE thread_id = $2
    `,
    [now, threadId],
  );
  return result.rowCount > 0;
}

async function deliverItemByThread(threadId, itemKey, quantity) {
  const now = Math.floor(Date.now() / 1000);

  const result = await query(
    `
    SELECT id, item_name, remaining_quantity, rank_position
    FROM item_requests
    WHERE thread_id = $1 AND item_name = $2
    `,
    [threadId, itemKey],
  );

  if (result.rowCount === 0) {
    return false;
  }

  const { id: requestId, item_name: itemName, remaining_quantity: remaining, rank_position: rank } = result.rows[0];
  const newRemaining = remaining - quantity;

  if (newRemaining > 0) {
    await query(
      'UPDATE item_requests SET remaining_quantity = $1 WHERE id = $2',
      [newRemaining, requestId],
    );
  } else {
    await query('DELETE FROM item_requests WHERE id = $1', [requestId]);

    await query(
      `
      UPDATE item_requests
      SET rank_position = rank_position - 1
      WHERE item_name = $1
        AND rank_position > $2
      `,
      [itemName, rank],
    );
  }

  await query(
    `
    INSERT INTO item_request_logs
    (request_id, action, info, thread_id, created_at)
    VALUES ($1, 'delivered', $2, $3, $4)
    `,
    [requestId, `qty=${quantity}`, threadId, now],
  );

  return true;
}

async function getAllItemRequestsForCheck() {
  const result = await query(
    `
    SELECT
      id,
      discord_id,
      player_name,
      item_name,
      rank_position,
      thread_id,
      thread_channel_id,
      last_update,
      warned_3d,
      warned_4d
    FROM item_requests
    ORDER BY item_name, rank_position ASC
    `,
    [],
  );
  return result.rows;
}

async function markRequestWarned(requestId, field) {
  const allowed = ['warned_3d', 'warned_4d'];
  if (!allowed.includes(field)) {
    throw new Error(`Invalid request field: ${field}`);
  }
  await query(`UPDATE item_requests SET ${field} = 1 WHERE id = $1`, [requestId]);
}

async function dropRequestRank(requestId) {
  const now = Math.floor(Date.now() / 1000);

  const result = await query(
    `
    SELECT item_name, rank_position
    FROM item_requests
    WHERE id = $1
    `,
    [requestId],
  );

  if (result.rowCount === 0) {
    return;
  }

  const { item_name: itemName, rank_position: rank } = result.rows[0];
  const belowResult = await query(
    `
    SELECT id
    FROM item_requests
    WHERE item_name = $1
      AND rank_position = $2
    `,
    [itemName, rank + 1],
  );

  if (belowResult.rowCount === 0) {
    return;
  }

  const belowId = belowResult.rows[0].id;

  await query('UPDATE item_requests SET rank_position = $1 WHERE id = $2', [
    rank,
    belowId,
  ]);
  await query(
    `
    UPDATE item_requests
    SET rank_position = $1,
        last_update = $2,
        warned_3d = 0,
        warned_4d = 0
    WHERE id = $3
    `,
    [rank + 1, now, requestId],
  );
}

async function getDailyItemSummary() {
  const result = await query(
    `
    SELECT
      item_name,
      rank_position,
      player_name,
      remaining_quantity,
      thread_id
    FROM item_requests
    ORDER BY item_name, rank_position ASC
    `,
    [],
  );
  return result.rows;
}

async function getItemRequestByThread(threadId) {
  const result = await query(
    `
    SELECT
      id,
      discord_id,
      player_name,
      item_name,
      rank_position,
      thread_id,
      last_update
    FROM item_requests
    WHERE thread_id = $1
    `,
    [threadId],
  );
  return result.rows[0] || null;
}

async function getRequestByThread(threadId, itemName) {
  const result = await query(
    `
    SELECT id, item_name, rank_position
    FROM item_requests
    WHERE thread_id = $1 AND item_name = $2
    `,
    [threadId, itemName],
  );
  return result.rows[0] || null;
}

async function deleteRequest(requestId) {
  await query('DELETE FROM item_requests WHERE id = $1', [requestId]);
}

async function reorderItemRanks(itemName) {
  const result = await query(
    `
    SELECT id
    FROM item_requests
    WHERE item_name = $1
    ORDER BY rank_position ASC
    `,
    [itemName],
  );

  let rank = 1;
  for (const row of result.rows) {
    await query('UPDATE item_requests SET rank_position = $1 WHERE id = $2', [
      rank,
      row.id,
    ]);
    rank += 1;
  }
}

async function closePool() {
  await pool.end();
}

async function addParty({
  messageId,
  channelId,
  creatorId,
  reasonPt,
  reasonEn,
  startTs,
  endTs,
}) {
  await query(
    `
    INSERT INTO parties
    (message_id, channel_id, creator_id, reason_pt, reason_en, start_ts, end_ts)
    VALUES ($1, $2, $3, $4, $5, $6, $7)
    `,
    [messageId, channelId, creatorId, reasonPt, reasonEn, startTs, endTs],
  );
}

async function getPartyByMessageId(messageId) {
  const result = await query('SELECT * FROM parties WHERE message_id = $1', [
    messageId,
  ]);
  return result.rows[0] || null;
}

async function getPartyByCreator(creatorId) {
  const result = await query('SELECT * FROM parties WHERE creator_id = $1', [
    creatorId,
  ]);
  return result.rows[0] || null;
}

async function getAllParties() {
  const result = await query('SELECT message_id, channel_id FROM parties', []);
  return result.rows;
}

async function deletePartyByMessageId(messageId) {
  await query('DELETE FROM parties WHERE message_id = $1', [messageId]);
}

async function clearParties() {
  await query('DELETE FROM parties', []);
}

async function cleanupBossParticipationDuplicates() {
  const result = await query(
    `
    WITH duplicates AS (
      SELECT id
      FROM boss_participation
      WHERE id NOT IN (
        SELECT MIN(id)
        FROM boss_participation
        GROUP BY rotation_id, discord_id
      )
    )
    DELETE FROM boss_participation
    WHERE id IN (SELECT id FROM duplicates)
    `,
    [],
  );
  return result.rowCount;
}

module.exports = {
  addPlayer,
  updateChannel,
  getAllPlayers,
  getPlayerTimezone,
  updatePlayerTimezone,
  addReminder,
  getActiveReminders,
  markWarned,
  markReminderSent,
  markAsSent,
  getPendingReminders,
  upsertPlayerChannelWithLanguage,
  addForumPost,
  getOpenForumPosts,
  markForumPostClosed,
  getForumPostByThread,
  markForumPostDelivered,
  addDrop,
  getLastDrop,
  addDailyAnnouncement,
  getActiveDailyAnnouncements,
  deactivateDailyAnnouncement,
  getFutureReminders,
  getReminderById,
  getPlayersStuck3Days,
  addPlayerLevel,
  cleanupOldPlayers,
  getPlayerDrops,
  addForumItem,
  getForumItem,
  getForumItemsByKind,
  getAllForumItems,
  getForumItemsForSelect,
  addRotation,
  getLastRotationDay,
  getRotationsSince,
  hasParticipation,
  getOrCreateRotation,
  addParticipation,
  getParticipationStats,
  getRotationHistory,
  addItemRequest,
  updateItemRequestByThread,
  deliverItemByThread,
  getAllItemRequestsForCheck,
  markRequestWarned,
  dropRequestRank,
  getDailyItemSummary,
  getItemRequestByThread,
  getRequestByThread,
  deleteRequest,
  reorderItemRanks,
  addParty,
  getPartyByMessageId,
  getPartyByCreator,
  getAllParties,
  deletePartyByMessageId,
  clearParties,
  cleanupBossParticipationDuplicates,
  closePool,
};
