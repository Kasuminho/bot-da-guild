import json
import os
from functools import lru_cache


def get_image_storage_provider() -> str:
    return os.getenv("IMAGE_STORAGE_PROVIDER", "local").strip().lower()


def is_remote_storage_enabled() -> bool:
    return get_image_storage_provider() != "local"


def is_remote_url(value: str) -> bool:
    if not value:
        return False
    return value.startswith("http://") or value.startswith("https://")


def _load_drive_credentials():
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials

    service_account_json = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON", "").strip()
    service_account_file = os.getenv("GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE", "").strip()

    oauth_access_token = os.getenv("GOOGLE_DRIVE_OAUTH_ACCESS_TOKEN", "").strip()

    if service_account_json:
        info = json.loads(service_account_json)
        return service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/drive"],
        )

    if service_account_file:
        return service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=["https://www.googleapis.com/auth/drive"],
        )

    if oauth_access_token:
        return Credentials(token=oauth_access_token)

    raise RuntimeError(
        "Google Drive configurado, mas faltou credencial: "
        "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON, GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE "
        "ou GOOGLE_DRIVE_OAUTH_ACCESS_TOKEN"
    )


@lru_cache(maxsize=1)
def _get_drive_service():
    from googleapiclient.discovery import build

    credentials = _load_drive_credentials()
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def upload_image(file_path: str, upload_name: str) -> str:
    provider = get_image_storage_provider()

    if provider == "local":
        return file_path

    if provider != "google_drive":
        raise RuntimeError(f"IMAGE_STORAGE_PROVIDER inválido: {provider}")

    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID não foi configurado")

    from googleapiclient.http import MediaFileUpload

    service = _get_drive_service()

    file_metadata = {
        "name": upload_name,
        "parents": [folder_id],
    }

    media = MediaFileUpload(file_path, mimetype="image/png", resumable=False)
    uploaded = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id")
        .execute()
    )
    file_id = uploaded["id"]

    make_public = os.getenv("GOOGLE_DRIVE_PUBLIC_PERMISSION", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if make_public:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()

    return f"https://drive.google.com/uc?id={file_id}"
