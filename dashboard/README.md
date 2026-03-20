# Bot da Guild Dashboard

Dashboard Next.js para controlar e monitorar o bot usando **os dados reais que já existem no projeto**.

## O que este dashboard faz de verdade
Esta versão foi ajustada para:
- reutilizar `players`, `drops`, `item_requests`, `item_request_logs`, `audit_logs`, `dkp_transactions` e `guilds` do bot existente;
- manter no dashboard apenas metadados próprios de autenticação/autorização e o histórico do bridge HTTP de comandos (`dashboard_users` e `dashboard_commands`);
- apontar o Prisma para o mesmo banco do bot por padrão (`file:../database.db`) e permitir trocar o driver entre SQLite e PostgreSQL via ambiente.

## O que NÃO é obrigatório
Você **não precisa** expor uma API de comando do bot para:
- ver players;
- ver drops;
- ver item requests;
- ver logs;
- ver DKP;
- usar o dashboard autenticado.

Tudo isso vem direto do banco já usado pelo bot.

A API HTTP do bot é opcional e hoje serve só para:
- healthcheck (`/health`);
- bridge de comandos remotos, se você decidir implementar/configurar isso.

## Estrutura

```text
/dashboard
├── app/
│   ├── api/
│   │   ├── admin/
│   │   ├── auth/[...nextauth]/
│   │   ├── bot/status/
│   │   ├── logs/
│   │   ├── me/
│   │   └── user/items/
│   ├── dashboard/
│   │   ├── admin/
│   │   ├── items/
│   │   └── logs/
│   └── login/
├── components/
├── lib/
└── prisma/
```

## Fontes reais de dados do bot
- `players`: cadastro do jogador, idioma, canal e timezone.
- `drops`: itens entregues ao jogador.
- `item_requests`: fila/ranking ativo de requests.
- `item_request_logs`: histórico operacional dos requests.
- `audit_logs`: trilha de auditoria administrativa/DKP/SaaS.
- `dkp_transactions`: saldo e histórico de DKP.
- `guilds`: plano e status do tenant.

## Tabelas próprias do dashboard
- `dashboard_users`: vínculo OAuth/role do painel (`admin`/`user`).
- `dashboard_commands`: histórico das execuções enviadas ao endpoint HTTP do bot.

## Setup com o banco que já existe

1. Instale dependências:
   ```bash
   cd dashboard
   npm install
   ```
2. Copie o ambiente:
   ```bash
   cp .env.example .env
   ```
3. Gere a secret do NextAuth:
   ```bash
   openssl rand -base64 32
   ```
4. Aponte o `DATABASE_URL` para o **mesmo banco do bot**.

   ### Se o bot atual usa SQLite
   Use algo como:
   ```env
   DATABASE_PROVIDER="sqlite"
   DATABASE_URL="file:../database.db"
   ```

   ### Se o bot atual usa PostgreSQL
   Use o mesmo banco do bot e ajuste o provider:
   ```env
   DATABASE_PROVIDER="postgresql"
   DATABASE_URL="postgresql://usuario:senha@host:5432/seu_banco"
   ```
5. Crie apenas as tabelas extras do dashboard com Prisma:
   ```bash
   npm run prisma:push
   npm run prisma:generate
   ```
   Esses scripts agora geram automaticamente o `prisma/schema.prisma` com base em `DATABASE_PROVIDER`, então você não precisa editar o schema manualmente ao alternar entre SQLite e PostgreSQL.
   Quando o banco for SQLite legado, o dashboard também normaliza automaticamente colunas de IDs do Discord para `BIGINT` antes de subir o app, evitando overflow do Prisma em snowflakes antigos.
6. Promova admins via `ADMIN_DISCORD_IDS`:
   ```bash
   npm run prisma:seed
   ```
7. Rode o painel:
   ```bash
   npm run dev
   ```

## OAuth do Discord
1. Crie a aplicação no Discord Developer Portal.
2. Copie `Client ID` e `Client Secret`.
3. Configure o callback:
   ```text
   http://localhost:3000/api/auth/callback/discord
   ```
4. Defina os IDs de staff em `ADMIN_DISCORD_IDS`.

## Integração com o bot atual
### Status do bot
O dashboard pode consultar o healthcheck já existente do bot:
```http
GET /health
```

Por padrão, o exemplo usa:
```env
BOT_API_BASE_URL="http://127.0.0.1:10000"
BOT_STATUS_ENDPOINT="/health"
```

### Bridge de comandos remotos
Isso é **opcional**.
Se o seu bot **não** expõe endpoint HTTP para comando, deixe isto vazio no `dashboard/.env`:
```env
BOT_COMMAND_ENDPOINT=""
```

Se algum dia você quiser ligar essa função, configure por exemplo:
```env
BOT_COMMAND_ENDPOINT="/command"
```

e faça o bot responder algo como:
```http
POST /command
Content-Type: application/json

{
  "command": "dkp add 123456789012345678 10 weekly_reward",
  "userId": "123456789012345678"
}
```

> Observação: o restante do dashboard continua lendo o banco real do bot independentemente desse bridge existir.

## Segurança
- Todas as rotas `/dashboard` e `/api` exigem sessão.
- Endpoints administrativos validam `role === admin`.
- O navegador nunca fala direto com o bot HTTP; tudo passa pelo backend do Next.
