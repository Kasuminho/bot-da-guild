# Migração entre PostgreSQL e SQLite

## Visão geral
O projeto agora aceita **PostgreSQL** e **SQLite**.

- Se `DATABASE_URL` apontar para `postgres://` ou `postgresql://`, o bot usa PostgreSQL.
- Se `DATABASE_URL` estiver vazio, o bot usa SQLite automaticamente em `SQLITE_PATH` (padrão: `./database.db`).
- Para períodos temporários de 60-90 dias, SQLite reduz custo e simplifica backup/restore, com a troca de menor concorrência e menos robustez para múltiplas instâncias.

## Inventário do schema legado (SQLite)
Tabelas encontradas no `db.py` original:

- `players(id, discord_id, nickname_ingame, language, channel_id)`
  - Uso implícito: `discord_id` único e coluna `timezone` usada no código (adicionada no schema novo).
- `one_time_reminders(id, tipo, nome, channel_id, timestamp, sent, warned_4h, warned_1h, warned_30m, warned_now, warned_daily_day)`
- `boss_rotations(id, rotation_type, day, created_at)`
  - `UNIQUE(rotation_type, day)`
- `boss_participation(id, rotation_id, discord_id, present)`
  - relacionamento implícito com `boss_rotations.id`
- `forum_posts(id, thread_id, close_time, closed, delivered)`
- `drops(id, discord_id, nickname_ingame, item, thread_id, staff_id, delivered_at)`
- `daily_announcements(id, text_pt, text_en, image_pt_path, image_en_path, active, created_at)`
  - código também assume `channel_id` (corrigido no schema novo)
- `player_levels(id, player_id, player_name, level, day, created_at)`
  - índice único `idx_player_day(player_id, day)`
- `parties(message_id, channel_id, creator_id, reason_pt, reason_en, start_ts, end_ts)`
- `forum_items(id, kind, category, item_pt, item_en, type_pt, type_en, image1_path, image2_path, active, created_at)`
- `item_requests(id, discord_id, player_name, item_name, total_quantity, remaining_quantity, rank_position, thread_id, thread_channel_id, created_at, last_update, warned_3d, warned_4d)`
- `item_request_logs(id, request_id, action, info, thread_id, created_at)`

## Mapeamento de tipos aplicado
- `INTEGER` (IDs Discord e chaves) -> `BIGINT`
- `TEXT` -> `TEXT`
- flags `0/1` -> `BOOLEAN`
- timestamps epoch -> `BIGINT` (mantido para compatibilidade)

## Arquivos novos
- `sql/schema.sql`: schema idempotente do PostgreSQL.
- `scripts/migrate_sqlite_to_postgres.py`: migração one-shot com validação final.

## Como migrar
1. Suba um PostgreSQL (Render, Railway, Docker etc.).
2. Defina variáveis:
   - `DATABASE_URL=postgres://...`
   - `SQLITE_PATH=./database.db` (ou caminho real do `.db`)
3. Rode migração inicial (recomendado):
   ```bash
   python scripts/migrate_sqlite_to_postgres.py --truncate-first
   ```
4. Inicie o bot normalmente:
   ```bash
   python bot.py
   ```

## Modos da migração
- `--truncate-first` (padrão recomendado): limpa tabela destino e recarrega.
- `--upsert`: usa `ON CONFLICT` em tabelas com chave conhecida.

## Checklist pós-migração
- [ ] Script finalizou sem traceback.
- [ ] Contagens SQLite/Postgres conferem no bloco `[VALIDAÇÃO]`.
- [ ] Bot inicia sem erro de schema.
- [ ] Comandos críticos (`/registrar`, reminders, forum, requests, party) funcionam.


## Volta temporária: PostgreSQL -> SQLite
1. Faça um backup do PostgreSQL atual.
2. Defina no `.env` a `DATABASE_URL` atual do Postgres.
3. Opcionalmente defina `SQLITE_PATH=./database.sqlite3`.
4. Rode a exportação:
   ```bash
   python scripts/migrate_postgres_to_sqlite.py --truncate-first
   ```
5. Para subir o bot já em SQLite, deixe `DATABASE_URL=` vazio e mantenha `SQLITE_PATH` apontando para o arquivo exportado.

## Roteiro recomendado de corte
1. Coloque o bot em manutenção curta.
2. Rode o script `migrate_postgres_to_sqlite.py --truncate-first`.
3. Valide contagens no bloco `[VALIDAÇÃO]`.
4. Troque o `.env` para `DATABASE_URL=` vazio.
5. Suba o bot e valide comandos críticos.
6. Guarde o dump/backup do Postgres por pelo menos 30 dias.
