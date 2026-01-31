# bot-guild

Um bot para guilda (Discord). Este repositório contém o código principal e módulos.

## Rápido começo

1. Crie um ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

2. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure variáveis de ambiente:
   - Exporte `DISCORD_TOKEN` e, se necessário, `DATABASE_URL`.
   - Ou crie um `.env` com `DISCORD_TOKEN=seu_token` (não comite `.env`).

4. Rode o bot:
   ```bash
   python bot.py
   ```

## Boas práticas
- Não comite tokens — use variáveis de ambiente.
- Logs locais não devem ficar no repo (arquivo `bot.log` está em `.gitignore`).
- Modularize comandos em `cogs/`.

## Desenvolvimento
- Formatação: Black
- Lint: Ruff
- Pre-commit hooks recomendados para aplicar automaticamente.

## Contribuição
Abra uma issue ou PR com mudanças. Use `pre-commit` para aplicar linters/formatters antes de commitar.