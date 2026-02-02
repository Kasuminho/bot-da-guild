# Node.js cogs

Este diretório contém versões em Node.js dos cogs atuais.

## Reminders

- Arquivo: `reminders.js`
- Slash command: `/cadastrarlembrete`
- Fluxo: select de timezone -> modal de data/hora -> gravação no Postgres.
- Loop automático: envia avisos 1h, 30m e na hora.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { command, registerReminders } = require('./cogs/reminders');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerReminders({
    client,
    db,
    announcementsChannelId: Number(process.env.ANNOUNCEMENTS_CHANNEL_ID),
    g3xRoleId: Number(process.env.G3X_ROLE_ID),
  });
});
```

A publicação dos comandos (registrar o slash command) deve ser feita
no bootstrap do bot usando `command`.

## Players

- Arquivo: `players.js`
- Slash commands: `/cadastrarjogador`, `/associarcanal`, `/verificarinativos`
- Fluxo: cria canal do jogador, salva no Postgres e envia mensagem de onboarding.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { commands, registerPlayers } = require('./cogs/players');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerPlayers({
    client,
    db,
    categoryId: Number(process.env.CATEGORY_ID),
    staffRoleId: Number(process.env.STAFF_ROLE_ID),
  });
});
```

Os comandos de players devem ser registrados no bootstrap usando `commands`.

## Party

- Arquivo: `party.js`
- Slash commands: `/party`, `/party_delete`, `/party_clear_all`
- Fluxo: cria a party, salva no Postgres, adiciona reação ✅ e registra timezone.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { commands, registerParty } = require('./cogs/party');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerParty({ client, db });
});
```

## Party events

- Arquivo: `party_events.js`
- Eventos: reaction add/remove ✅ para atualizar o embed da party.

### Uso esperado

```js
const { Client, GatewayIntentBits, Partials } = require('discord.js');
const db = require('../db');
const { registerPartyEvents } = require('./cogs/party_events');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.GuildMessageReactions,
  ],
  partials: [Partials.Message, Partials.Reaction, Partials.Channel],
});

client.once('ready', () => {
  registerPartyEvents({ client, db });
});
```

## Scheduler

- Arquivo: `scheduler.js`
- Loop semanal: segunda-feira 12:00 UTC, envia lembrete nos canais dos jogadores.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { startWeeklyScheduler } = require('./cogs/scheduler');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  startWeeklyScheduler({ client, db });
});
```

## Forum announce

- Arquivo: `forum_announce.js`
- Slash command: `/anunciar`
- Fluxo: seleção de item -> modo -> timezone -> data/hora -> cria thread no fórum.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { command, registerForumAnnounce } = require('./cogs/forum_announce');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerForumAnnounce({
    client,
    db,
    staffChannelId: Number(process.env.STAFF_CHANNEL_ID),
    forumChannelId: Number(process.env.FORUM_CHANNEL_ID),
    forumTagId: Number(process.env.FORUM_TAG_ID),
    g3xRoleId: Number(process.env.G3X_ROLE_ID),
  });
});
```

## Forum delivery

- Arquivo: `forum_delivery.js`
- Slash commands: `/entregar`, `/recusar`, `/historico`
- Fluxo: validar thread, coletar anexos, registrar entrega e fechar thread.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { commands, registerForumDelivery } = require('./cogs/forum_delivery');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerForumDelivery({
    client,
    db,
    forumChannelId: Number(process.env.FORUM_CHANNEL_ID),
  });
});
```

## Daily announcements

- Arquivo: `daily_announcement.js`
- Slash commands: `/aviso_diario`, `/aviso_diario_desativar`
- Loop: envia avisos 12h–15h com máximo de 4 ativos.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { commands, registerDailyAnnouncement } = require('./cogs/daily_announcement');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerDailyAnnouncement({
    client,
    db,
    forceChannelId: Number(process.env.ANNOUNCEMENTS_CHANNEL_ID),
  });
});
```

## Item requests

- Arquivo: `item_requests.js`
- Slash commands: `/request_add`, `/request_update`, `/request_deliver`, `/request_rank`, `/request_info`, `/request_delete`
- Fluxo: gerencia requests de itens dentro das threads do fórum.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { commands, registerItemRequests } = require('./cogs/item_requests');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerItemRequests({
    client,
    db,
    staffRoleId: Number(process.env.STAFF_ROLE_ID),
  });
});
```

## Item requests scheduler

- Arquivo: `item_requests_scheduler.js`
- Fluxo: envia resumo do ranking e aplica regras de inatividade.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { startItemRequestScheduler } = require('./cogs/item_requests_scheduler');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  startItemRequestScheduler({
    client,
    db,
    summaryChannelId: Number(process.env.ITEM_REQUEST_SUMMARY_CHANNEL_ID),
  });
});
```

## Item requests admin

- Arquivo: `item_requests_admin.js`
- Slash command: `/request_summary`

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { command, registerItemRequestsAdmin } = require('./cogs/item_requests_admin');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerItemRequestsAdmin({
    client,
    db,
    summaryChannelId: Number(process.env.ITEM_REQUEST_SUMMARY_CHANNEL_ID),
  });
});
```

## Cadastrar item

- Arquivo: `cadastrar_item.js`
- Slash command: `/cadastraritem`
- Fluxo: salva imagens e cadastra item para o fórum.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { command, registerCadastrarItem } = require('./cogs/cadastrar_item');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerCadastrarItem({
    client,
    db,
    staffRoleId: Number(process.env.STAFF_ROLE_ID),
  });
});
```

## Player progress

- Arquivo: `player_progress.js`
- Slash commands: `/registrarlevel`, `/checarniveis`
- Fluxo: registra nível diário e verifica jogadores sem progresso.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { commands, registerPlayerProgress } = require('./cogs/player_progress');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerPlayerProgress({ client, db });
});
```

## Rotation eligibility

- Arquivo: `rotation_eligibility.js`
- Slash commands: `/verificar_elegibilidade`, `/registrar_rotacao`
- Fluxo: avalia presença e registra participações de rotação.

### Uso esperado

```js
const { Client, GatewayIntentBits } = require('discord.js');
const db = require('../db');
const { commands, registerRotationEligibility } = require('./cogs/rotation_eligibility');

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages],
});

client.once('ready', () => {
  registerRotationEligibility({ client, db });
});
```
