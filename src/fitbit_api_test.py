import requests
import json
import os
from dotenv import load_dotenv
import base64

# .env を読み込む
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
#REFRESH_TOKEN = os.getenv("YOUR_REFRESH_TOKEN")

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

def load_tokens():
    if os.path.exists("tokens.json"):
        with open("tokens.json", "r") as f:
            tokens = json.load(f)
        return tokens.get("access_token"), tokens.get("refresh_token")
    return None, None

def save_tokens(tokens):
    with open("tokens.json", "w") as f:
        json.dump(tokens, f, indent=2)

def refresh_access_token(refresh_token):
    """
    リフレッシュトークンを使って新しいアクセストークンを取得
    """
    headers = {
        "Authorization": get_basic_auth_header(CLIENT_ID, CLIENT_SECRET),
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
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

def call_api(access_token):
    api_url = "https://api.fitbit.com/1.2/user/-/sleep/date/2025-06-22.json"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        print("✅ API 呼び出し成功:")
        print(json.dumps(response.json(), indent=2))
    elif response.status_code == 401:
        print("🔁 トークンが期限切れ。リフレッシュします。")
        return False
    else:
        print(f"❌ API 呼び出しエラー: {response.status_code}")
        print(response.text)
    return True

# ================== 実行部分 ==================
access_token, refresh_token = load_tokens()

# APIコール
success = call_api(access_token)

# トークン期限切れならリフレッシュして再試行
if not success:
    access_token, refresh_token = refresh_access_token(refresh_token)
    if access_token:
        call_api(access_token)