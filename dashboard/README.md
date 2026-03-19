# Bot da Guild Dashboard

Dashboard Next.js para controlar e monitorar o bot usando **os dados reais que já existem no projeto**.

## O que foi corrigido
A versão anterior criava tabelas paralelas para itens, logs e usuários do dashboard. Esta versão passa a:
- reutilizar `players`, `drops`, `item_requests`, `item_request_logs`, `audit_logs`, `dkp_transactions` e `guilds` do bot existente;
- manter no dashboard apenas metadados próprios de autenticação/autorização e o histórico do bridge HTTP de comandos (`dashboard_users` e `dashboard_commands`);
- apontar o Prisma para o mesmo SQLite do bot por padrão (`file:../database.db`).

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

## Setup

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
5. Crie apenas as tabelas extras do dashboard com Prisma:
   ```bash
   npm run prisma:push
   npm run prisma:generate
   ```
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
### Status
O dashboard usa o healthcheck já existente do bot:
```http
GET /health
```

### Command bridge
Se o bot expuser o bridge abaixo, o painel usa:
```http
POST /command
Content-Type: application/json

{
  "command": "dkp add 123456789012345678 10 weekly_reward",
  "userId": "123456789012345678"
}
```

> Observação: o restante do dashboard (players, drops, item requests, logs, DKP) já lê o banco real do bot independentemente do bridge HTTP de comando existir.

## Segurança
- Todas as rotas `/dashboard` e `/api` exigem sessão.
- Endpoints administrativos validam `role === admin`.
- O navegador nunca fala direto com o bot HTTP; tudo passa pelo backend do Next.
