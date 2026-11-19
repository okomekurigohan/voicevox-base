#!/usr/bin/env python3
"""共通TTSクライアント（VOICEVOXエンジン HTTP API）

台本テキスト（1行=1セリフ）を春日部つむぎの音声に変換する。
- 行ごとのwavと、連結した1本のwavを出力する
- 行ごとの長さ（秒）を manifest.json に出す（後の動画制作でテロップ表示時間に使う）

使い方:
  python3 tts.py --text-file script.txt --out-dir out/ [--speed 1.15] [--speaker 春日部つむぎ] [--style ノーマル]

前提: VOICEVOXエンジンが http://127.0.0.1:50021 で動いていること（start-engine.sh 参照）。
依存は標準ライブラリのみ。連結には ffmpeg を使う。
"""
import argparse
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def api(engine: str, path: str, data: bytes | None = None, params: dict | None = None,
        content_type: str | None = None) -> bytes:
    url = engine.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    if content_type:
        req.add_header("Content-Type", content_type)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def find_style_id(engine: str, speaker_name: str, style_name: str) -> int:
    speakers = json.loads(api(engine, "/speakers"))
    for sp in speakers:
        if sp["name"] == speaker_name:
            for st in sp["styles"]:
                if st["name"] == style_name:
                    return st["id"]
            raise SystemExit(f"スタイルが見つかりません: {speaker_name} / {style_name}（候補: {[s['name'] for s in sp['styles']]}）")
    raise SystemExit(f"話者が見つかりません: {speaker_name}")


def wav_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True, help="台本テキスト（1行=1セリフ、空行は無視）")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--speed", type=float, default=1.2, help="話速（speedScale）。デフォルトは1.2")
    ap.add_argument("--speaker", default="春日部つむぎ")
    ap.add_argument("--style", default="ノーマル")
    ap.add_argument("--engine", default="http://127.0.0.1:50021")
    ap.add_argument("--pause", type=float, default=0.05, help="行間の無音（秒）。デフォルトは0.05")
    args = ap.parse_args()

    lines = [ln.strip() for ln in Path(args.text_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        raise SystemExit("台本が空です")

    # 「表示テキスト|読みテキスト」形式のパースと検証は、合成前に全行まとめて行う。
    # 読み間違いを防ぐため、単位・英字・記号を含む行は読みを併記するのが台本ルール（| が無ければ表示=読み）。
    # 読みが空の行（例:「表示|」「|」だけ）をエンジンへ送ると無音や誤動作の元になるため、ここで止める。
    # 表示が空の行（例:「|読み」）も、テロップが出ない行になるため同様に止める。
    parsed: list[tuple[str, str]] = []
    errors: list[str] = []
    for n, raw in enumerate(lines, start=1):
        if "|" in raw:
            text, reading = (s.strip() for s in raw.split("|", 1))
            if not reading:
                errors.append(f"{n}行目: 読みが空です（「表示|」の形になっています）。読みを書くか、| を外してください: {raw!r}")
                continue
            if not text:
                errors.append(f"{n}行目: 表示テキストが空です: {raw!r}")
                continue
        else:
            text = reading = raw
        parsed.append((text, reading))
    if errors:
        raise SystemExit("台本の形式エラー:\n" + "\n".join(errors))

    style_id = find_style_id(args.engine, args.speaker, args.style)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    part_files: list[Path] = []
    for i, (text, reading) in enumerate(parsed):
        query = json.loads(api(args.engine, "/audio_query", data=b"", params={"text": reading, "speaker": style_id}))
        query["speedScale"] = args.speed
        wav = api(args.engine, "/synthesis", data=json.dumps(query).encode("utf-8"),
                  params={"speaker": style_id}, content_type="application/json")
        part = out_dir / f"line_{i:03d}.wav"
        part.write_bytes(wav)
        dur = wav_seconds(part)
        entry = {"index": i, "text": text, "file": part.name, "seconds": round(dur, 3)}
        if reading != text:
            entry["reading"] = reading
        manifest.append(entry)
        part_files.append(part)
        if args.pause > 0 and i < len(lines) - 1:
            silence = out_dir / f"pause_{i:03d}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-v", "quiet", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                 "-t", str(args.pause), str(silence)],
                check=True,
            )
            part_files.append(silence)
            manifest[-1]["pause_after"] = args.pause

    list_file = out_dir / "concat.txt"
    # ffmpeg concat 形式のエスケープ（パス中の ' は '\'' と書く決まり）
    # 改行（LF/CR）とバックスラッシュを含むパスは concat 形式で安全に表せないため明示的に拒否する
    def esc(path):
        s = str(path)
        if "\n" in s or "\r" in s or "\\" in s:
            raise ValueError(f"対応できない文字を含むパスです: {s!r}")
        return s.replace("'", "'\\''")
    list_file.write_text("".join(f"file '{esc(p.resolve())}'\n" for p in part_files), encoding="utf-8")
    joined = out_dir / "joined.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "quiet", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(joined)],
        check=True,
    )
    total = wav_seconds(joined)
    (out_dir / "manifest.json").write_text(
        json.dumps({"speaker": args.speaker, "style": args.style, "speed": args.speed,
                    "lines": manifest, "total_seconds": round(total, 3)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OK: {len(lines)}行, 合計 {total:.2f}秒 -> {joined}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
