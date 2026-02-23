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

## Armazenamento online de imagens (Google Drive)

Para não depender de arquivos locais no container, você pode salvar imagens cadastradas diretamente no Drive.

1. Configure o provider:
   ```bash
   IMAGE_STORAGE_PROVIDER=google_drive
   ```
2. Crie uma pasta no Google Drive e configure o ID:
   ```bash
   GOOGLE_DRIVE_FOLDER_ID=seu_folder_id
   ```
3. Configure credenciais de Service Account (um dos formatos):
   - JSON inline em variável:
     ```bash
     GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON={...json...}
     ```
   - Ou caminho de arquivo no ambiente:
     ```bash
     GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE=/path/credentials.json
     ```

Quando o provider estiver como `google_drive`, o `/cadastraritem` faz upload para o Drive e salva URL pública no banco.
No fluxo `/anunciar`, quando os caminhos forem URLs, o tópico do fórum é criado com os links das imagens no conteúdo.

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
