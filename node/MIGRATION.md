# Migração: Python/SQLite -> Node/Postgres (Neon)

Este guia descreve o que precisa existir no schema Postgres para que o módulo
`node/db.js` funcione de forma equivalente ao comportamento atual do bot em
Python.

## Checklist de schema

Garanta que as seguintes tabelas/índices existam (já conforme seu schema atual):

- `players` com `discord_id` **único**.
- `one_time_reminders` com colunas de controle `sent`, `warned_1h`, `warned_30m`, `warned_now`.
- `boss_rotations` com **único** (`rotation_type`, `day`).
- `boss_participation` com **único** (`rotation_id`, `discord_id`).
- `player_levels` com **único** (`player_id`, `day`).
- `item_requests` com **único** (`discord_id`, `item_name`).

> Observação: o SQLite atual não possui `UNIQUE` em `forum_posts.thread_id`, então
> o método `addForumPost` usa `INSERT ... WHERE NOT EXISTS` para manter
> idempotência no Postgres.

## Diferença conhecida em `daily_announcements`

O schema SQLite atual contém apenas:
`id`, `text_pt`, `text_en`, `image_pt_path`, `image_en_path`, `active`, `created_at`.

Por isso, o módulo Node expõe somente:
- `addDailyAnnouncement`
- `getActiveDailyAnnouncements`
- `deactivateDailyAnnouncement`

Não há `upsert_daily_announcement` por canal, já que a coluna `channel_id`
**não existe** no schema atual.

## Próximos passos recomendados

1. Garanta que o Postgres/Neon tenha o schema acima.
2. Use o módulo `node/db.js` nas próximas migrações das cogs.
3. Migre cog por cog, validando comportamento com dados reais.
