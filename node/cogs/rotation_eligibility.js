const { SlashCommandBuilder, PermissionFlagsBits } = require('discord.js');
const { DateTime } = require('luxon');

const WINDOW_DAYS = 7;
const MIN_PERCENT = 80;
const MAX_T4_ABSENCES = 1;

const TAG_PT = 1449177142645620807;
const TAG_EN = 1449177196370460722;

const TYPE_EMOJI = {
  T3: '🟦',
  T4: '🟥',
  ABYSS: '🟪',
};

const TEXTS = {
  PT: {
    eligible: (
      '✅ **Elegível para requerimento de item**\n\n'
      + '📊 Participação: {percent}%\n'
      + '🟢 Presenças: {presences}\n'
      + '🔴 Total rotações: {total}'
    ),
    notEligible: (
      '❌ **Você não está elegível para requerimento de item**\n\n'
      + '📊 **Resumo (últimos {days} dias)**\n'
      + '- Presenças: {presences}\n'
      + '- Total rotações: {total}\n'
      + '- Participação: {percent}%\n'
      + '- Faltas em T4: {t4_absences}\n\n'
      + '📌 **Motivos:**\n{reasons}'
    ),
  },
  EN: {
    eligible: (
      '✅ **Eligible for item request**\n\n'
      + '📊 Participation: {percent}%\n'
      + '🟢 Presences: {presences}\n'
      + '🔴 Total rotations: {total}'
    ),
    notEligible: (
      '❌ **You are not eligible for item request**\n\n'
      + '📊 **Summary (last {days} days)**\n'
      + '- Presences: {presences}\n'
      + '- Total rotations: {total}\n'
      + '- Participation: {percent}%\n'
      + '- T4 absences: {t4_absences}\n\n'
      + '📌 **Reasons:**\n{reasons}'
    ),
  },
};

const verifyCommand = new SlashCommandBuilder()
  .setName('verificar_elegibilidade')
  .setDescription('Verificar elegibilidade para request')
  .addUserOption((option) =>
    option.setName('jogador').setDescription('Jogador').setRequired(true),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild);

const registerCommand = new SlashCommandBuilder()
  .setName('registrar_rotacao')
  .setDescription('Registrar participação em rotação')
  .addStringOption((option) =>
    option
      .setName('tipo')
      .setDescription('Tipo (T3, T4, ABYSS)')
      .setRequired(true),
  )
  .addIntegerOption((option) =>
    option
      .setName('dia')
      .setDescription('Dia no formato YYYYMMDD')
      .setRequired(true),
  )
  .addStringOption((option) =>
    option
      .setName('jogadores')
      .setDescription('Menções dos jogadores')
      .setRequired(true),
  )
  .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild);

function parseDay(day) {
  return DateTime.fromFormat(String(day), 'yyyyMMdd').isValid;
}

function parseMentions(raw) {
  const ids = new Set();
  const regex = /<@!?(\d+)>/g;
  let match;
  while ((match = regex.exec(raw)) !== null) {
    ids.add(match[1]);
  }
  return [...ids];
}

function formatDay(day) {
  return DateTime.fromFormat(String(day), 'yyyyMMdd').toFormat('dd/MM/yyyy');
}

function buildHistory({ history, language }) {
  const presList = [];
  const absList = [];

  for (const h of history) {
    const emoji = TYPE_EMOJI[h.type] || '⬜';
    const line = `${emoji} ${formatDay(h.day)} — ${h.type}`;
    if (h.present) {
      presList.push(line);
    } else {
      absList.push(line);
    }
  }

  if (language === 'PT') {
    return (
      '\n\n📅 **Histórico de rotações**\n\n'
      + '🟢 **Presenças:**\n'
      + (presList.length > 0 ? presList.join('\n') : '• Nenhuma')
      + '\n\n🔴 **Faltas:**\n'
      + (absList.length > 0 ? absList.join('\n') : '• Nenhuma')
    );
  }

  return (
    '\n\n📅 **Rotation history**\n\n'
    + '🟢 **Presences:**\n'
    + (presList.length > 0 ? presList.join('\n') : '• None')
    + '\n\n🔴 **Absences:**\n'
    + (absList.length > 0 ? absList.join('\n') : '• None')
  );
}

function formatTemplate(template, values) {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replace(`{${key}}`, value),
    template,
  );
}

async function runEligibilityCheck({ thread, jogador, db, language }) {
  const until = DateTime.utc();
  const since = until.minus({ days: WINDOW_DAYS });

  const stats = await db.getParticipationStats(
    jogador.id,
    since.toFormat('yyyyMMdd'),
    until.toFormat('yyyyMMdd'),
  );

  const total = stats.total_rotations;
  const presences = stats.presences;
  const t4Absences = stats.t4_absences;
  const percent = total === 0 ? 100 : Math.floor((presences / total) * 100);

  let eligible = true;
  const reasons = [];

  if (percent < MIN_PERCENT) {
    eligible = false;
    reasons.push(
      language === 'PT'
        ? `- Participação abaixo de ${MIN_PERCENT}% (${percent}%)`
        : `- Participation below ${MIN_PERCENT}% (${percent}%)`,
    );
  }

  if (t4Absences > MAX_T4_ABSENCES) {
    eligible = false;
    reasons.push(
      language === 'PT'
        ? '- Faltou 2 ou mais rotações T4'
        : '- Missed 2 or more T4 rotations',
    );
  }

  const history = await db.getRotationHistory(
    jogador.id,
    Number(since.toFormat('yyyyMMdd')),
    Number(until.toFormat('yyyyMMdd')),
  );

  const historyBlock = buildHistory({ history, language });
  const texts = TEXTS[language];

  if (eligible) {
    await thread.send(
      `${jogador.toString()}\n\n`
      + formatTemplate(texts.eligible, {
        percent,
        presences,
        total,
      })
      + historyBlock,
    );
    return;
  }

  const msg = formatTemplate(texts.notEligible, {
    days: WINDOW_DAYS,
    presences,
    total,
    percent,
    t4_absences: t4Absences,
    reasons: reasons.join('\n'),
  });

  await thread.send(`${jogador.toString()}\n\n${msg}\n\n${historyBlock}`);

  if (!thread.archived) {
    await thread.setArchived(true);
    await thread.setLocked(true);
  }
}

function startCleanupDuplicates({ db }) {
  let lastRunKey = null;

  const interval = setInterval(async () => {
    const now = DateTime.now().setZone('America/Sao_Paulo');
    if (now.hour !== 6 || now.minute !== 0) {
      return;
    }

    const runKey = now.toISODate();
    if (lastRunKey === runKey) {
      return;
    }

    lastRunKey = runKey;
    await db.cleanupBossParticipationDuplicates();
  }, 60 * 1000);

  return () => clearInterval(interval);
}

function registerRotationEligibility({ client, db }) {
  startCleanupDuplicates({ db });

  client.on('interactionCreate', async (interaction) => {
    if (!interaction.isChatInputCommand()) {
      return;
    }

    if (interaction.commandName === 'verificar_elegibilidade') {
      if (!interaction.member.permissions.has('ManageGuild')) {
        await interaction.reply({ content: 'Comando exclusivo da staff.', ephemeral: true });
        return;
      }

      if (!interaction.channel || !interaction.channel.isThread()) {
        await interaction.reply({
          content: 'Este comando deve ser usado dentro de uma thread.',
          ephemeral: true,
        });
        return;
      }

      await interaction.deferReply();
      const jogador = interaction.options.getUser('jogador', true);
      const member = await interaction.guild.members.fetch(jogador.id).catch(() => null);
      if (!member) {
        await interaction.editReply('Jogador não encontrado.');
        return;
      }

      await runEligibilityCheck({
        thread: interaction.channel,
        jogador: member,
        db,
        language: 'PT',
      });
      return;
    }

    if (interaction.commandName === 'registrar_rotacao') {
      if (!interaction.member.permissions.has('ManageGuild')) {
        await interaction.reply({ content: 'Comando exclusivo da staff.', ephemeral: true });
        return;
      }

      const tipo = interaction.options.getString('tipo', true).toUpperCase();
      if (!['T3', 'T4', 'ABYSS'].includes(tipo)) {
        await interaction.reply({ content: 'Tipo inválido.', ephemeral: true });
        return;
      }

      const dia = interaction.options.getInteger('dia', true);
      if (!parseDay(dia)) {
        await interaction.reply({ content: 'Data inválida.', ephemeral: true });
        return;
      }

      const jogadores = interaction.options.getString('jogadores', true);
      const ids = parseMentions(jogadores);
      if (ids.length === 0) {
        await interaction.reply({ content: 'Mencione ao menos um jogador.', ephemeral: true });
        return;
      }

      const rotationId = await db.getOrCreateRotation(tipo, dia);

      let added = 0;
      let ignored = 0;
      for (const discordId of ids) {
        const ok = await db.addParticipation(rotationId, discordId);
        if (ok) {
          added += 1;
        } else {
          ignored += 1;
        }
      }

      await interaction.reply({
        content:
          `✅ Rotação **${tipo}** \`${dia}\` processada\n`
          + `➕ Adicionados: **${added}**\n`
          + `⛔ Ignorados: **${ignored}**`,
        ephemeral: true,
      });
    }
  });
}

module.exports = {
  commands: [verifyCommand, registerCommand],
  registerRotationEligibility,
};
