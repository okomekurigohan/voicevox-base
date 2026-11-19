# voicevox-base

VOICEVOX エンジンをプログラムから叩くための、小さな音声合成基盤です。
台本テキスト（1行 = 1セリフ）を春日部つむぎの音声に変換し、行ごとの wav、連結した wav、そして行ごとの長さを記録した manifest.json を出力します。動画のナレーション制作など、「台本 → 音声 + テロップ表示タイミング」の流れをスクリプト化したい用途を想定しています。

エンジン本体はこのリポジトリには含まれません（公式配布物を別途取得します。下の導入手順を参照）。

## 構成

- `engine/` : VOICEVOX エンジン公式 Linux 版（CPU、v0.26.1）を展開する場所。127.0.0.1:50021 でのみ待ち受けます（リポジトリには含めません）
- `start-engine.sh` : エンジン起動スクリプト
- `tts.py` : 台本テキスト → 行ごと wav ＋ 連結 wav ＋ manifest.json（行ごとの秒数つき）。依存は Python 標準ライブラリ ＋ ffmpeg
- `sample-script.txt` / `sample-script-nopunct.txt` : 台本のサンプル

## 導入手順

前提： Linux x86_64、`curl`、Python 3.10 以上（`tts.py` が `bytes | None` 構文を使います）、`python3 -m venv`、`ffmpeg` と `ffprobe`（`tts.py` の時間計測に ffprobe を使います）。

```bash
git clone https://github.com/okomekurigohan/voicevox-base.git
cd voicevox-base
mkdir -p download engine

# 1) エンジン本体（約1.9GB）を取得
curl -L -o download/engine.7z.001 \
  https://github.com/VOICEVOX/voicevox_engine/releases/download/0.26.1/voicevox_engine-linux-cpu-x64-0.26.1.7z.001

# 2) 展開用に py7zr を専用 venv へ入れる（運用には不要な環境）
python3 -m venv .venv
.venv/bin/pip install py7zr

# 3) 展開する（engine/linux-cpu-x64/run ができれば成功）
.venv/bin/python -c "import py7zr; py7zr.SevenZipFile('download/engine.7z.001').extractall('engine')"

# 4) 起動と疎通確認（エンジンの起動完了まで十数秒かかります。別ターミナルで起動するか、少し待ってから確認してください。失敗したらもう一度 curl してください）
./start-engine.sh &
sleep 15
curl http://127.0.0.1:50021/version
curl http://127.0.0.1:50021/speakers
```

## 使い方

```
./start-engine.sh &          # 別ターミナル or バックグラウンドで起動
python3 tts.py --text-file sample-script.txt --out-dir out/sample
```

- 標準の話速は `--speed 1.2`、行間の無音は `--pause 0.05`（デフォルト値）
- `--engine` で接続先を変えられますが、台本テキストがその URL へ送信されます。既定の `http://127.0.0.1:50021`（自分のマシン内）以外を指定する時は、送信先を必ず確認してください
- 台本の行は「表示テキスト|読みテキスト」の形で読みを併記できます（単位・英字・記号を含む行は読み併記がおすすめです）。読みが空の行（「表示|」「|」だけ）や表示が空の行（「|読み」）は、合成前に形式エラーとして行番号つきで止まります（無音や誤動作の防止）
- 既知の制限：形式エラーの行番号は「空行を除いた後の連番」で、台本ファイルの物理行とはずれることがあります。エラーには行内容も表示されるので、直す行は内容で探してください

## manifest.json の読み方

- `lines[].seconds` ：その行の発話だけの秒数（ffprobe 実測）。行間の無音は含まれません
- `lines[].pause_after` ：その行の直後に入れた無音の秒数（指定値）
- `total_seconds` ：無音込みの、連結後 wav 全体の秒数
- テロップの表示タイミングは「各行の seconds ＋ pause_after の累積」で作れます

## 規約メモ

- 春日部つむぎ公式規約：合成音声は商用・非商用問わず利用可。利用時は「VOICEVOX:春日部つむぎ」のクレジット表記が必要です（動画内・概要欄など任意の場所）。VOICEVOX 本体の規約も併せて守ってください
- 禁止事項：誹謗中傷、第三者に不快感を与えるもの、権利侵害、特定の思想・団体に関係するもの、公式イラストを使った商品の販売・頒布、二次配布・自作発言 など
- 出典： https://tsumugi-official.studio.site/rule
- VOICEVOX 公式： https://voicevox.hiroshiba.jp/

## ライセンス

このリポジトリのスクリプト類は MIT ライセンスです（`LICENSE` を参照）。
VOICEVOX エンジンおよび春日部つむぎは、それぞれの公式規約に従います。
