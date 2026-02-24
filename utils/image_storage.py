import json
import os
from functools import lru_cache


DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_image_storage_provider() -> str:
    return os.getenv("IMAGE_STORAGE_PROVIDER", "local").strip().lower()


def is_remote_storage_enabled() -> bool:
    return get_image_storage_provider() != "local"


def is_remote_url(value: str) -> bool:
    if not value:
        return False
    return value.startswith("http://") or value.startswith("https://")


def _load_drive_credentials():
    """
    Prioriza Service Account (JSON ou FILE).
    NÃO usa GOOGLE_DRIVE_OAUTH_ACCESS_TOKEN, porque token "seco" quebra refresh e dá o erro
    que você já viu (RefreshError).
    """
    from google.oauth2 import service_account

    service_account_json = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "").strip()
    service_account_file = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "").strip()

    if service_account_json:
        try:
            info = json.loads(service_account_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON existe, mas não é JSON válido. "
                "Dica: cole o JSON inteiro em uma linha (ou use arquivo + GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE)."
            ) from exc

        return service_account.Credentials.from_service_account_info(
            info,
            scopes=DRIVE_SCOPES,
        )

    if service_account_file:
        if not os.path.exists(service_account_file):
            raise RuntimeError(
                f"GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE aponta para um arquivo que não existe: {service_account_file}"
            )
        return service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=DRIVE_SCOPES,
        )

    # Se você quiser OAuth de usuário no futuro, implemente com token.json completo.
    # Mas token "seco" via env quebra refresh. Então, intencionalmente, não suportamos aqui.
    if os.getenv("GOOGLE_DRIVE_OAUTH_ACCESS_TOKEN", "").strip():
        raise RuntimeError(
            "GOOGLE_DRIVE_OAUTH_ACCESS_TOKEN está setado, mas este projeto não suporta access token "
            "sem refresh_token (isso causa RefreshError). Use Service Account (recomendado) ou implemente OAuth completo."
        )

    raise RuntimeError(
        "Google Drive configurado, mas faltou credencial: "
        "defina GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON ou GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE."
    )


@lru_cache(maxsize=1)
def _get_drive_service():
    from googleapiclient.discovery import build

    credentials = _load_drive_credentials()
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def upload_image(file_path: str, upload_name: str) -> str:
    """
    Faz upload do arquivo para a pasta GOOGLE_DRIVE_FOLDER_ID.
    Requer que essa pasta esteja dentro de um Shared Drive (Drive compartilhado),
    e que a Service Account tenha permissão nesse Shared Drive.

    Retorna uma URL estável do Drive.
    """
    provider = get_image_storage_provider()

    if provider == "local":
        return file_path

    if provider != "google_drive":
        raise RuntimeError(f"IMAGE_STORAGE_PROVIDER inválido: {provider}")

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID não foi configurado")

    if not os.path.exists(file_path):
        raise RuntimeError(f"Arquivo não encontrado para upload: {file_path}")

    from googleapiclient.http import MediaFileUpload

    service = _get_drive_service()

    file_metadata = {
        "name": upload_name,
        "parents": [folder_id],
    }

    # Se suas imagens podem não ser PNG, você pode remover o mimetype fixo.
    media = MediaFileUpload(file_path, mimetype="image/png", resumable=False)

    # ESSENCIAL para Shared Drives:
    uploaded = (
        service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink, webContentLink",
            supportsAllDrives=True,
        )
        .execute()
    )

    file_id = uploaded["id"]

    make_public = os.getenv("GOOGLE_DRIVE_PUBLIC_PERMISSION", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    # Em Shared Drive, permission também precisa supportsAllDrives=True.
    if make_public:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            supportsAllDrives=True,
        ).execute()

    # Preferência: link de visualização, senão fallback
    url = uploaded.get("webViewLink") or uploaded.get("webContentLink")
    if url:
        return url

    # Fallback clássico (funciona):
    return f"https://drive.google.com/uc?id={file_id}"