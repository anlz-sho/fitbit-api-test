import requests
import json
import os
import base64
from dotenv import load_dotenv
from google.cloud import bigquery
from datetime import datetime

# .env を読み込む
load_dotenv()
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

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
    """
    tokens.jsonが存在するなら、アクセストークンとリフレッシュトークンを手に入れる
    """
    if os.path.exists("tokens.json"):
        with open("tokens.json", "r") as f:
            tokens = json.load(f)
        return tokens.get("access_token"), tokens.get("refresh_token")
    return None, None

def save_tokens(tokens):
    """
    tokens.jsonを開いて、json形式で上書きする
    """
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
    """
    Fitbit APIの呼び出しを行う
    """
    api_url = "https://api.fitbit.com/1.2/user/-/sleep/date/2025-06-22/2025-06-28.json"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        print("✅ API 呼び出し成功:")
        return response.json()
    elif response.status_code == 401:
        print("🔁 トークンが期限切れ。リフレッシュします。")
        return "expired"
    else:
        print(f"❌ API 呼び出しエラー: {response.status_code}")
        print(response.text)
        return None

def write_to_bigquery(bq_table,sleep_json):
    """
    bigqueryにデータの書き込みを行う
    """
    client = bigquery.Client()
    table_id = bq_table

    # 取り出すデータ構造の簡略化（複雑なネストを回避）
    if "sleep" not in sleep_json or not sleep_json["sleep"]:
        print("❌ データがありません")
        return

    record = sleep_json["sleep"][0]
    row = {
        "sleep_log_id": record.get("logId"),
        "date": record.get("dateOfSleep"),
        "startTime": record.get("startTime"),
        "endTime": record.get("endTime"),
        "minutesAsleep": record.get("minutesAsleep"),
        "minutesAwake": record.get("minutesAwake"),
        "timeInBed": record.get("timeInBed"),
        "efficiency": record.get("efficiency"),
        "type": record.get("type"),
        "created_at": datetime.utcnow().isoformat()
    }

    job_config = bigquery.LoadJobConfig(
        autodetect=True,  # スキーマを自動判別
        write_disposition="WRITE_APPEND",  # 追記（初回は新規作成）
    )

    # リスト形式で渡す必要あり
    job = client.load_table_from_json([row], table_id, job_config=job_config)
    job.result()  # ジョブの完了を待機

    print("✅ BigQuery に書き込み完了")


# ================== 実行部分 ==================
access_token, refresh_token = load_tokens()
bq_table = "fitbit-dashboard-463713.fitbit_data.sleep_data"

# APIコール
result = call_api(access_token)

# トークン期限切れならリフレッシュして再試行
if result == "expired":
    access_token, refresh_token = refresh_access_token(refresh_token)
    if access_token:
        result = call_api(access_token)

if result and result != "expired":
    write_to_bigquery(bq_table, result)