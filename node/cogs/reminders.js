const {
  ActionRowBuilder,
  StringSelectMenuBuilder,
  ModalBuilder,
  TextInputBuilder,
  TextInputStyle,
  SlashCommandBuilder,
} = require('discord.js');
const { DateTime } = require('luxon');

const TIMEZONES = {
  '🇧🇷 Brasil (America/Sao_Paulo)': 'America/Sao_Paulo',
  '🌍 UTC': 'UTC',
};

const TIMEZONE_SELECT_ID = 'reminders:timezone-select';
const DATETIME_MODAL_ID = 'reminders:datetime-modal';
const DATETIME_INPUT_ID = 'reminders:datetime-input';

const pendingReminders = new Map();

const command = new SlashCommandBuilder()
  .setName('cadastrarlembrete')
  .setDescription('Cadastrar lembrete com avisos automáticos')
  .addStringOption((option) =>
    option.setName('tipo').setDescription('Tipo do lembrete').setRequired(true),
  )
  .addStringOption((option) =>
    option.setName('nome').setDescription('Nome do lembrete').setRequired(true),
  );

function buildTimezoneSelect() {
  return new ActionRowBuilder().addComponents(
    new StringSelectMenuBuilder()
      .setCustomId(TIMEZONE_SELECT_ID)
      .setPlaceholder('Selecione o fuso horário')
      .addOptions(
        Object.entries(TIMEZONES).map(([label, value]) => ({
          label,
          value,
        })),
      ),
  );
}

function buildDatetimeModal(tzName) {
  return new ModalBuilder()
    .setCustomId(`${DATETIME_MODAL_ID}:${tzName}`)
    .setTitle('Cadastrar lembrete')
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

async function createReminder({
  interaction,
  db,
  tipo,
  nome,
  timestamp,
  announcementsChannelId,
  g3xRoleId,
}) {
  await db.addReminder(tipo, nome, announcementsChannelId, timestamp);

  const channel = interaction.client.channels.cache.get(announcementsChannelId);
  if (channel) {
    await channel.send(
      `<@&${g3xRoleId}>\n`
        + '📢 **Novo lembrete cadastrado**\n\n'
        + `📌 ${tipo}: ${nome}\n`
        + '🌍 Timezone: No seu horário local que mostra no computador/celular\n'
        + '🌍 Timezone: On your local time where show on computer/cellphone\n'
        + `⏰ <t:${timestamp}:F>\n\n`
        + '🔔 Avisos automáticos:\n'
        + '• 1 hora antes\n'
        + '• 30 minutos antes\n'
        + '• Na hora',
    );
  }

  await interaction.reply({
    content: '✅ Lembrete cadastrado com sucesso.',
    ephemeral: true,
  });
}

function startReminderLoop({ client, db, g3xRoleId }) {
  const interval = setInterval(async () => {
    const now = Math.floor(Date.now() / 1000);
    const reminders = await db.getActiveReminders();

    for (const reminder of reminders) {
      const channel = client.channels.cache.get(reminder.channel_id);
      if (!channel) {
        continue;
      }

      if (!reminder.warned_1h && now >= reminder.timestamp - 3600) {
        await channel.send(
          `<@&${g3xRoleId}>\n`
            + `⏳ **Falta 1 hora** — ${reminder.tipo}: ${reminder.nome}\n`
            + `⏰ <t:${reminder.timestamp}:F>`,
        );
        await db.markWarned(reminder.id, 'warned_1h');
        continue;
      }

      if (!reminder.warned_30m && now >= reminder.timestamp - 1800) {
        await channel.send(
          `<@&${g3xRoleId}>\n`
            + `⏳ **Faltam 30 minutos** — ${reminder.tipo}: ${reminder.nome}\n`
            + `⏰ <t:${reminder.timestamp}:F>`,
        );
        await db.markWarned(reminder.id, 'warned_30m');
        continue;
      }

      if (!reminder.warned_now && now >= reminder.timestamp) {
        await channel.send(
          `<@&${g3xRoleId}>\n`
            + `⏰ **Agora** — ${reminder.tipo}: ${reminder.nome}\n`
            + `⏰ <t:${reminder.timestamp}:F>`,
        );
        await db.markWarned(reminder.id, 'warned_now');
        await db.markReminderSent(reminder.id);
      }
    }
  }, 60 * 1000);

  return () => clearInterval(interval);
}

function registerReminders({ client, db, announcementsChannelId, g3xRoleId }) {
  const stopLoop = startReminderLoop({ client, db, g3xRoleId });

  client.on('interactionCreate', async (interaction) => {
    if (interaction.isChatInputCommand()) {
      if (interaction.commandName !== 'cadastrarlembrete') {
        return;
      }

      const tipo = interaction.options.getString('tipo', true);
      const nome = interaction.options.getString('nome', true);
      pendingReminders.set(interaction.user.id, { tipo, nome });

      await interaction.reply({
        content: '🌍 Selecione o fuso horário do evento:',
        components: [buildTimezoneSelect()],
        ephemeral: true,
      });
      return;
    }

    if (interaction.isStringSelectMenu()) {
      if (interaction.customId !== TIMEZONE_SELECT_ID) {
        return;
      }

      const pending = pendingReminders.get(interaction.user.id);
      if (!pending) {
        await interaction.reply({
          content: '❌ Não encontrei o lembrete pendente. Tente novamente.',
          ephemeral: true,
        });
        return;
      }

      const tzName = interaction.values[0];
      const modal = buildDatetimeModal(tzName);
      await interaction.showModal(modal);
      return;
    }

    if (interaction.isModalSubmit()) {
      if (!interaction.customId.startsWith(DATETIME_MODAL_ID)) {
        return;
      }

      const [, tzName] = interaction.customId.split(':');
      const pending = pendingReminders.get(interaction.user.id);
      if (!pending) {
        await interaction.reply({
          content: '❌ Não encontrei o lembrete pendente. Tente novamente.',
          ephemeral: true,
        });
        return;
      }

      const inputValue = interaction.fields.getTextInputValue(DATETIME_INPUT_ID);
      const localDt = DateTime.fromFormat(inputValue, 'yyyy-MM-dd HH:mm', {
        zone: tzName,
      });

      if (!localDt.isValid) {
        await interaction.reply({
          content: '❌ Formato inválido. Use `YYYY-MM-DD HH:MM`',
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

      pendingReminders.delete(interaction.user.id);
      await createReminder({
        interaction,
        db,
        tipo: pending.tipo,
        nome: pending.nome,
        timestamp,
        announcementsChannelId,
        g3xRoleId,
      });
    }
  });

  return stopLoop;
}

module.exports = {
  command,
  registerReminders,
};
