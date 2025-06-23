import requests
import json
import os
from dotenv import load_dotenv

# .env を読み込む
load_dotenv()

# アクセストークン（環境変数や .env で管理するのがおすすめですが、まずは直接書いてもOK）
ACCESS_TOKEN = os.getenv("FITBIT_ACCESS_TOKEN")

# 呼び出したいAPI URL（1.2 の詳細睡眠API例）
API_URL = "https://api.fitbit.com/1.2/user/-/sleep/date/2025-06-22.json"

# ヘッダー（トークンを渡す部分）
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

# API を呼び出す
response = requests.get(API_URL, headers=headers)

# 結果の表示
print(f"HTTPステータス: {response.status_code}")

# JSONレスポンスを整形して表示
if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=2))
else:
    print("エラーが発生しました。")
    print(response.text)
