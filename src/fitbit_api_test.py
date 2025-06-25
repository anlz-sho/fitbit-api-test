import requests
import json
import os
from dotenv import load_dotenv
import base64

# .env を読み込む
load_dotenv()
CLIENT_ID = os.getenv("YOUR_CLIENT_ID")
CLIENT_SECRET = os.getenv("YOUR_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("YOUR_REFRESH_TOKEN")

# トークンエンドポイント
TOKEN_URL = "https://api.fitbit.com/oauth2/token"

def get_basic_auth_header(client_id, client_secret):
    """
    Client ID と Client Secret を Base64 エンコードした認証ヘッダーを作成
    """
    auth_str = f"{client_id}:{client_secret}"
    auth_bytes = auth_str.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
    return f"Basic {auth_base64}"


def refresh_access_token():
    """
    リフレッシュトークンを使って新しいアクセストークンを取得
    """
    headers = {
        "Authorization": get_basic_auth_header(CLIENT_ID, CLIENT_SECRET),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)

    if response.status_code == 200:
        tokens = response.json()
        print("✅ 新しいトークンを取得しました:")
        print(json.dumps(tokens, indent=2))

        # 必要に応じてファイル保存など
        with open("tokens.json", "w") as f:
            json.dump(tokens, f, indent=2)

        return tokens["access_token"], tokens["refresh_token"]
    else:
        print(f"❌ エラー: {response.status_code}")
        print(response.text)
        return None, None

# 実行
access_token, new_refresh_token = refresh_access_token()

# 取得したアクセストークンでAPI呼び出し例
if access_token:
    api_url = "https://api.fitbit.com/1.2/user/-/sleep/date/2025-06-22.json"
    api_headers = {
        "Authorization": f"Bearer {access_token}"
    }
    api_response = requests.get(api_url, headers=api_headers)

    if api_response.status_code == 200:
        print("✅ API 呼び出し成功")
        print(json.dumps(api_response.json(), indent=2))
    else:
        print(f"❌ API 呼び出しエラー: {api_response.status_code}")
        print(api_response.text)