# VOICEVOX音声基盤（共通土台）

やりたいことリスト6番（朝の読み上げ）と7番（空想科学読本風ショート）の共通土台。
プログラムから VOICEVOX エンジン（HTTP API）を叩いて、春日部つむぎの音声を合成する。

## 構成
- `engine/` : VOICEVOXエンジン公式Linux版（CPU、v0.26.1）。127.0.0.1:50021 でのみ待ち受ける
- `start-engine.sh` : エンジン起動
- `tts.py` : 台本テキスト（1行=1セリフ）→ 行ごとwav＋連結wav＋manifest.json（行ごとの秒数つき）。依存は標準ライブラリ＋ffmpeg
- `.venv/` : 展開用 py7zr のためだけの環境（運用には不要）

## 導入手順（実施済み 2026-11-07、再現用）
前提：Linux x86_64、`curl`、`python3`（3.10以上。tts.py が `bytes | None` 構文を使うため。`python3 -m venv` が使えることも必要）、`ffmpeg` と `ffprobe`（tts.py の時間計測は ffprobe を使う）。

```bash
cd ~/workspace/voicevox-base   # 配置先が違う場合は実際のパスに読み替える
mkdir -p download engine

# 1) エンジン本体（約1.9GB）を取得
curl -L -o download/engine.7z.001 \
  https://github.com/VOICEVOX/voicevox_engine/releases/download/0.26.1/voicevox_engine-linux-cpu-x64-0.26.1.7z.001

# 2) 展開用に py7zr を専用 venv へ入れる（運用には不要な環境）
python3 -m venv .venv
.venv/bin/pip install py7zr

# 3) 展開する（engine/linux-cpu-x64/run ができれば成功）
.venv/bin/python -c "import py7zr; py7zr.SevenZipFile('download/engine.7z.001').extractall('engine')"

# 4) 起動と疎通確認（エンジンの起動完了まで十数秒かかる。別ターミナルで起動するか、少し待ってから確認する。失敗したらもう一度 curl する）
./start-engine.sh &
sleep 15
curl http://127.0.0.1:50021/version
curl http://127.0.0.1:50021/speakers
```

## 使い方
```
./start-engine.sh &          # 別ターミナル or バックグラウンドで起動
python3 tts.py --text-file script.txt --out-dir out/sample
```
- 標準の話速は `--speed 1.2`、行間の無音は `--pause 0.05`（デフォルト値。2026-11-07に決定）
- `--engine` で接続先を変えられるが、台本テキストがそのURLへ送信される。既定の `http://127.0.0.1:50021`（自分のマシン内）以外を指定する時は送信先を必ず確認すること
- 台本の行は「表示テキスト|読みテキスト」の形で読みを併記できる（単位・英字・記号を含む行は読み併記が台本ルール）。読みが空の行（「表示|」「|」だけ）や表示が空の行（「|読み」）は、合成前に形式エラーとして行番号つきで止まる（無音や誤動作の防止）
- 既知の制限（2026-11-07、最終レビューで指摘・受け入れて完了）：形式エラーの行番号は「空行を除いた後の連番」で、台本ファイルの物理行とはずれることがある。エラーには行内容も表示されるので、直す行は内容で探すこと

## manifest.json の読み方
- `lines[].seconds`：その行の発話だけの秒数（ffprobe 実測）。行間の無音は含まれない
- `lines[].pause_after`：その行の直後に入れた無音の秒数（指定値）
- `total_seconds`：無音込みの連結後 wav 全体の秒数
- テロップの表示タイミングは「各行の seconds ＋ pause_after の累積」で作る

## 規約メモ（2026-11-07確認）
- 春日部つむぎ公式規約：合成音声は商用・非商用問わず利用可。利用時は「VOICEVOX:春日部つむぎ」のクレジット表記が必要（動画内・概要欄など任意の場所）。VOICEVOX本体の規約も併せて守る
- 禁止事項：誹謗中傷、第三者に不快感を与えるもの、権利侵害、特定の思想・団体に関係するもの、公式イラストを使った商品の販売・頒布、二次配布・自作発言 など
- 出典： https://tsumugi-official.studio.site/rule
