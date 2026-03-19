# bot-guild

Discord guild bot with legacy loot flow (default), multi-tenant SaaS foundations, and optional DKP mode.

## Architecture inventory
- Config: `config.py` and environment variables.
- DB access: centralized in `db.py` + schema in `sql/schema.sql`.
- Commands/cogs: `cogs/*.py`, loaded in `bot.py`.
- Legacy loot flow: existing item request and forum delivery cogs.

## Refactor seams introduced
- Service layer + repositories (`services/`, `repositories/`).
- Config accessor (`GuildConfigService`).
- Command routing by mode (`LootEngineRouter` + `LegacyEngine`/`DKPEngine`).


## Legacy vs DKP (important)
- **Legacy (default):** existing cogs `forum_announce`, `forum_delivery`, `item_requests`.
- **DKP (optional):** new DKP commands/ledger subsystem.
- Changing `/loot mode_set` updates per-guild config only. It does **not** rewrite legacy cogs behavior automatically.
- Use `/loot mode_view` to confirm the guild mode.

## Quick start (local)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

### SQLite temporário (mais barato)
- Se `DATABASE_URL` estiver vazio, o bot sobe com SQLite automaticamente.
- O arquivo padrão passa a ser `./database.db`, mas você pode apontar outro caminho via `SQLITE_PATH`.
- Para uma VPS/EC2 simples, faça backup copiando o arquivo `.db` antes de cada deploy.

```bash
cp database.db backups/database-$(date +%F).db
```

## SaaS + multi-tenant migration
Set `DEFAULT_GUILD_ID` for safe backfill of historical rows:
```bash
export DEFAULT_GUILD_ID=123456789012345678
python scripts/migrate_to_multi_tenant.py
```

## SaaS admin commands
- `/saas plan_view`
- `/saas plan_set <free|pro|elite>`
- `/saas subscription_set_status <active|trialing|canceled|past_due|free>`
- `/saas subscription_set_expiry <ISO datetime>`

## DKP commands (feature-gated)
Admin/officer:
- `/dkp add`
- `/dkp remove`
- `/dkp decay`
- `/dkp reset confirm:true`
- `/dkp config_set`
- `/loot mode_set <legacy|dkp>`

Players:
- `/dkp balance`
- `/dkp top`
- `/dkp history`

## Deploy on AWS EC2 (Docker Compose)
1. Install Docker + Docker Compose plugin on EC2.
2. Clone repository and enter directory.
3. Create `.env` from `.env.example` and set secrets.
4. If using SQLite, leave `DATABASE_URL=` empty and keep `SQLITE_PATH=./database.db`.
5. Run:
```bash
docker compose up -d --build bot
```

If you still want PostgreSQL locally, start the profile explicitly:
```bash
docker compose --profile postgres up -d --build
```
6. Follow logs:
```bash
docker compose logs -f bot
```
7. Update deployment:
```bash
git pull
docker compose up -d --build bot
```

### Backup PostgreSQL
```bash
docker compose exec postgres pg_dump -U bot botguild > backup.sql
```

### Backup SQLite
```bash
cp database.db backup-$(date +%F).db
```

## Verification checklist
- [ ] Legacy commands still work with loot mode = `legacy`.
- [ ] Data from guild A never appears in guild B (DKP balance/top/history).
- [ ] `/saas plan_set` toggles features.
- [ ] Feature-gated commands deny correctly on free plan.
- [ ] `/loot mode_set dkp` enables DKP behavior only for that guild.
- [ ] `/dkp add`, `/dkp remove`, `/dkp balance`, `/dkp top`, `/dkp history` work.
- [ ] `/dkp decay` writes negative ledger transactions.
- [ ] `/dkp reset confirm:true` writes reset transactions and zeroes balances.


## Web dashboard
A full Next.js dashboard is available in `dashboard/` for Discord OAuth2 authentication, role-based access control, command execution, and bot monitoring. See `dashboard/README.md` for setup, Prisma schema, Discord OAuth configuration, and bot API integration details.
