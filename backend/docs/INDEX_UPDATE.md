# インデックス更新ガイド

## 概要

掲示板に新しいレスが投稿された際に、RAGシステムのベクトルインデックスを更新する方法について説明します。

## 更新方式

### 1. 初回インデックス作成

初めてインデックスを作成する場合：

```bash
cd backend
uv run python scripts/create_index.py
```

### 2. 差分更新

既存のインデックスに新しいレスを追加する場合：

```bash
cd backend
uv run python scripts/update_index.py
```

差分更新スクリプトは以下の処理を行います：
- 最後に処理したレス番号を`index_metadata.json`から読み込み
- 新しいレスのみを取得してインデックスに追加
- スライディングウィンドウの境界部分は再構築
- 処理完了後、最終レス番号を記録

## 定期実行の設定

### 方法1: Cron（シンプル）

```bash
# crontabを編集
crontab -e

# 10分ごとに実行する例
*/10 * * * * cd /home/toof/ghq/github.com/toof-jp/bbs-rag/backend && /usr/local/bin/uv run python scripts/update_index.py >> /var/log/bbs-rag-update.log 2>&1

# 1時間ごとに実行する例
0 * * * * cd /home/toof/ghq/github.com/toof-jp/bbs-rag/backend && /usr/local/bin/uv run python scripts/update_index.py >> /var/log/bbs-rag-update.log 2>&1
```

### 方法2: Systemd Timer（推奨）

1. サービスファイルを作成：

```bash
sudo nano /etc/systemd/system/bbs-rag-update.service
```

```ini
[Unit]
Description=BBS RAG Index Update
After=network.target postgresql.service

[Service]
Type=oneshot
User=toof
WorkingDirectory=/home/toof/ghq/github.com/toof-jp/bbs-rag/backend
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/local/bin/uv run python scripts/update_index.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

2. タイマーファイルを作成：

```bash
sudo nano /etc/systemd/system/bbs-rag-update.timer
```

```ini
[Unit]
Description=Run BBS RAG Index Update every 10 minutes
Requires=bbs-rag-update.service

[Timer]
OnBootSec=5min
OnUnitActiveSec=10min
Persistent=true

[Install]
WantedBy=timers.target
```

3. タイマーを有効化：

```bash
# リロード
sudo systemctl daemon-reload

# タイマーを有効化・開始
sudo systemctl enable bbs-rag-update.timer
sudo systemctl start bbs-rag-update.timer

# 状態確認
sudo systemctl status bbs-rag-update.timer
sudo journalctl -u bbs-rag-update.service -f
```

### 方法3: Docker環境での定期実行

docker-compose.ymlに以下を追加：

```yaml
  index-updater:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./backend:/app
      - chroma_data:/app/chroma_db
      - docstore_data:/app/docstore
    command: |
      sh -c "while true; do
        echo 'Running index update...'
        uv run python scripts/update_index.py
        echo 'Sleeping for 10 minutes...'
        sleep 600
      done"
    depends_on:
      - db
    restart: unless-stopped
```

## 手動更新

新しいレスがあることが分かっている場合の手動更新：

```bash
cd backend
uv run python scripts/update_index.py
```

更新状況は以下のファイルで確認できます：
- `backend/index_metadata.json` - 最終処理レス番号と更新日時

## トラブルシューティング

### エラー: "Collection does not exist"

```bash
# インデックスを完全に再作成
cd backend
rm -rf chroma_db docstore index_metadata.json
uv run python scripts/create_index.py
```

### パフォーマンスの問題

大量の新規レスがある場合は、初回作成スクリプトの方が効率的な場合があります：

```bash
# 1万件以上の新規レスがある場合は完全再作成を推奨
cd backend
uv run python scripts/create_index.py
```

## 監視

### ログの確認

```bash
# systemdの場合
sudo journalctl -u bbs-rag-update.service -n 100

# cronの場合
tail -f /var/log/bbs-rag-update.log
```

### インデックスの状態確認

```python
# backend/scripts/check_index_status.py として保存
import json
import os
from datetime import datetime

metadata_file = "index_metadata.json"
if os.path.exists(metadata_file):
    with open(metadata_file) as f:
        data = json.load(f)
    print(f"Last processed no: {data['last_processed_no']}")
    print(f"Last update: {data['last_update']}")
    
    # 最終更新からの経過時間
    last_update = datetime.fromisoformat(data['last_update'])
    elapsed = datetime.now() - last_update
    print(f"Time since last update: {elapsed}")
else:
    print("No metadata found. Run create_index.py first.")
```

## ベストプラクティス

1. **更新頻度**: 掲示板の活発度に応じて調整
   - 活発な掲示板: 5-10分ごと
   - 通常の掲示板: 30分-1時間ごと
   - 低活動: 1日数回

2. **エラー通知**: 更新エラーを検知する仕組みを追加
   ```bash
   # メール通知の例
   */10 * * * * cd /path/to/backend && uv run python scripts/update_index.py || echo "Index update failed" | mail -s "BBS RAG Error" admin@example.com
   ```

3. **リソース管理**: 
   - 更新中はOpenAI APIのレート制限に注意
   - PostgreSQLの負荷を監視
   - ディスク容量（Chroma DB）を定期的に確認