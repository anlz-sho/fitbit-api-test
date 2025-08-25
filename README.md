# Fitbit Sleep Analysis

Fitbit API から取得した睡眠データを **BigQuery** に保存し、**Looker Studio** で可視化するためのスクリプトです。  
睡眠潜時（sleep_latency）や深い睡眠割合（deep_sleep_ratio）などの分析項目を追加しています。

---

## 🚀 Features
- Fitbit API から睡眠データを取得  
- BigQuery に保存（sleep_log_id による重複チェックあり）  
- 分析用のフィールドを追加  
  - `weekday`  
  - `sleep_latency`  
  - `deep_sleep_ratio`  
  - `wake_count`
- Looker Studio での可視化  

---

## 📦 Requirements
- Python 3.11  
- Google Cloud SDK & BigQuery 権限  
- Fitbit API (Client ID / Client Secret)  

---

## 🔧 Setup

1. リポジトリを clone
```bash
git clone https://github.com/anlz-sho/fitbit-api-test.git
cd fitbit-api-test
```

2. 依存ライブラリをインストール
```bash
pip install -r requirements.txt
```

3. .env ファイルを作成して、Fitbit API のクライアント情報を記載
```env
CLIENT_ID=xxxxxxxx
CLIENT_SECRET=xxxxxxxx
```

4. 初回トークンを取得して tokens.json を配置
（リフレッシュ処理で自動更新されます）

---

## 🗄️ BigQuery Schema

本スクリプトを実行する前に、BigQuery 側に以下のスキーマでテーブルを作成しておく必要があります。  

例：`fitbit-dashboard-463713.fitbit_data.sleep_data`

| カラム名         | 型        |
|------------------|-----------|
| sleep_log_id     | INTEGER   |
| date             | DATE      |
| weekday          | STRING    |
| startTime        | TIMESTAMP |
| endTime          | TIMESTAMP |
| minutesAsleep    | INTEGER   |
| minutesAwake     | INTEGER   |
| deep_minutes     | INTEGER   |
| deep_sleep_ratio | FLOAT     |
| wake_count       | INTEGER   |
| sleep_latency    | FLOAT     |
| sleep_score      | INTEGER   |
| timeInBed        | INTEGER   |
| efficiency       | INTEGER   |
| type             | STRING    |
| is_main_sleep    | BOOLEAN   |
| created_at       | TIMESTAMP |

---

## ▶️ Usage

1. Fitbit のアクセストークンを取得して `tokens.json` を用意します。  
   フォーマット例：
   ```json
   {
     "access_token": "xxxx",
     "refresh_token": "yyyy",
     "expires_in": 28800,
     "token_type": "Bearer",
     "user_id": "ABC123"
   }

2. スクリプトを実行
```bash
python src/fitbit_api_test.py
```

3. 実行結果（例）
```
✅ API 呼び出し成功:
✅ BigQuery 書き込み完了: 追加 3 件 / スキップ 1 件
```

---

## 📊 Output

BigQuery の指定テーブル（例：`fitbit-dashboard-463713.fitbit_data.sleep_data`）に  
睡眠データが保存されます。保存されるカラムは [BigQuery Schema](#-bigquery-schema) を参照してください。

---

## 📈 Visualization

保存したデータは **Looker Studio** で可視化できます。  
例：
- 曜日ごとの平均入眠時間
- 日時ごとの sleep_latency の分析

---

## 📝 Reference
- [Fitbit Web API Reference](https://dev.fitbit.com/build/reference/web-api/)  
- Qiita記事（公開後にリンク追加予定）

---

## ⚖️ License
MIT License
