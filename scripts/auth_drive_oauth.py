import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]  # pode trocar por drive.file se quiser

def main():
    # oauth_client.json = o JSON do OAuth Client ID (Desktop) que você baixou do Google Cloud
    flow = InstalledAppFlow.from_client_secrets_file("oauth_client.json", SCOPES)

    # Força refresh_token (offline) e força tela de consentimento
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    print("Abra esta URL no navegador e autorize:")
    print(auth_url)

    code = input("\nCole aqui o code que aparece após autorizar: ").strip()
    flow.fetch_token(code=code)

    creds = flow.credentials

    # Salva token.json COMPLETO (com refresh_token + client_id/secret/token_uri)
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }

    with open("token.json", "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)

    print("\nOK: token.json gerado com refresh_token.")
    print("refresh_token existe?", bool(token_data.get("refresh_token")))

if __name__ == "__main__":
    main()