#!/bin/bash
# VOICEVOXエンジンをローカルでのみ起動する（127.0.0.1:50021、外部公開なし）
# 使い方: ./start-engine.sh （フォアグラウンド起動。止める時は Ctrl+C）
set -euo pipefail
cd "$(dirname "$0")/engine/linux-cpu-x64" 2>/dev/null || {
  echo "エンジンが展開されていません。先に README の導入手順を実行してください。" >&2
  exit 1
}
exec ./run --host 127.0.0.1 --port 50021
