import requests
import json
import os
import base64
from dotenv import load_dotenv
from google.cloud import bigquery
from datetime import datetime
from dateutil import parser

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
        #print(json.dumps(tokens, indent=2))

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
    api_url = "https://api.fitbit.com/1.2/user/-/sleep/date/2025-07-02/2025-07-20.json"
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

def is_duplicate_log(client, table_id, sleep_log_id):
    """
    sleep_log_idを重複チェックする
    """
    query = f"""
    SELECT COUNT(*) as count
    FROM `{table_id}`
    WHERE sleep_log_id = @log_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("log_id", "INT64", sleep_log_id)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()
    return next(results).count > 0

def write_to_bigquery(bq_table,sleep_json):
    """
    bigqueryにデータの書き込みを行う
    """
    client = bigquery.Client()
    table_id = bq_table

    job_config = bigquery.LoadJobConfig(
        autodetect=True,  # スキーマを自動判別
        schema=[
            bigquery.SchemaField("sleep_log_id", "INTEGER"),
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("weekday", "STRING"),
            bigquery.SchemaField("startTime", "TIMESTAMP"),
            bigquery.SchemaField("endTime", "TIMESTAMP"),
            bigquery.SchemaField("minutesAsleep", "INTEGER"),
            bigquery.SchemaField("minutesAwake", "INTEGER"),
            bigquery.SchemaField("deep_minutes", "INTEGER"),
            bigquery.SchemaField("deep_sleep_ratio", "FLOAT"),
            bigquery.SchemaField("wake_count", "INTEGER"),
            bigquery.SchemaField("sleep_latency", "FLOAT"),
            bigquery.SchemaField("sleep_score", "INTEGER"),
            bigquery.SchemaField("timeInBed", "INTEGER"),
            bigquery.SchemaField("efficiency", "INTEGER"),
            bigquery.SchemaField("type", "STRING"),
            bigquery.SchemaField("is_main_sleep", "BOOLEAN"),
            bigquery.SchemaField("created_at", "TIMESTAMP"),
        ],
        write_disposition="WRITE_APPEND",  # 追記（初回は新規作成）
    )

    inserted_count = 0
    skipped_count = 0

    if "sleep" not in sleep_json or not sleep_json["sleep"]:
        print("❌ データがありません")
        return

    rows = []
    for record in sleep_json["sleep"]:
        sleep_log_id = record.get("logId")
        if not is_duplicate_log(client, table_id, sleep_log_id):

            # 入眠潜時を計算
            start_dt = parser.parse(record["startTime"])

            sleep_stage_entries = [
                e for e in record.get("levels", {}).get("data", [])
                if e["level"] in ["asleep", "light", "deep", "rem"]
            ]

            if sleep_stage_entries:
                first_stage_dt = parser.parse(sleep_stage_entries[0]["dateTime"])
                start_dt = parser.parse(record["startTime"])
                sleep_latency = (first_stage_dt - start_dt).total_seconds() / 60
            else:
                sleep_latency = None
            print(sleep_latency)

            # 深い睡眠時間と割合
            minutes_asleep = record.get("minutesAsleep", 0)
            deep_minutes = record.get("levels", {}).get("summary", {}).get("deep", {}).get("minutes", 0)
            deep_sleep_ratio = (deep_minutes / minutes_asleep * 100) if minutes_asleep else None

            # 起床回数
            wake_count = record.get("levels", {}).get("summary", {}).get("wake", {}).get("count")

            # 曜日
            date_str = record.get("dateOfSleep")  # "2025-07-02" 形式
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            weekday = date_obj.strftime("%A")  # "Monday"

            row = {
                "sleep_log_id": record.get("logId"),
                "date": record.get("dateOfSleep"),              # 睡眠記録日
                "weekday": weekday,                             # 曜日
                "startTime": record.get("startTime"),           # 睡眠の開始時刻
                "endTime": record.get("endTime"),               # 睡眠の終了時刻
                "minutesAsleep": record.get("minutesAsleep"),   # 実際に眠っていた時間
                "minutesAwake": record.get("minutesAwake"),     # ベッドにいたが寝ていなかった時間
                "deep_minutes": deep_minutes,                   # 深い睡眠の合計
                "deep_sleep_ratio": deep_sleep_ratio,           # 深い睡眠の割合
                "wake_count": wake_count,                       # 中途覚醒の回数
                "sleep_latency": sleep_latency,                 # 入床から入眠までの時間
                "sleep_score": record.get("score"),             # Fitbitの睡眠スコア
                "timeInBed": record.get("timeInBed"),           # ベッドにいた総時間
                "efficiency": record.get("efficiency"),         # 睡眠効率(minutesAsleep/timeInBed)
                "type": record.get("type"),                     # 睡眠ステージ
                "is_main_sleep": record.get("isMainSleep"),     # 本睡眠フラグ
                "created_at": datetime.now().isoformat()
            }

            print(row)

            job = client.load_table_from_json([row], table_id, job_config=job_config)
            job.result()
            inserted_count += 1
        else:
            skipped_count += 1

    print("✅ BigQuery に書き込み完了")
    print(f"✅ BigQuery 書き込み完了: 追加 {inserted_count} 件 / スキップ {skipped_count} 件")

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