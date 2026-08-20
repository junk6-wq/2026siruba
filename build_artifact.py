#!/usr/bin/env python3
"""index.html の <img src="images/…"> を data URI に置き換えた単一ファイル版を出力する。

images/ を一緒に配れない場面（メール添付、CSPで外部読み込みが塞がれた環境）向け。
出力先は dist/silver-week-2026.html。

    pip install Pillow
    python3 build_artifact.py [--width 1100] [--quality 72]
"""

import argparse
import base64
import io
import pathlib
import re
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "index.html"
OUT = ROOT / "dist" / "silver-week-2026.html"


def encode(path: pathlib.Path, max_width: int, quality: int) -> str:
    """画像を必要なら縮小し、JPEG の data URI にして返す。"""
    im = Image.open(path).convert("RGB")
    if im.width > max_width:
        im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1100,
                    help="埋め込む画像の最大幅（既定 1100px）")
    ap.add_argument("--quality", type=int, default=72,
                    help="JPEG 品質（既定 72）")
    args = ap.parse_args()

    html = SRC.read_text(encoding="utf-8")
    cache: dict[str, str] = {}
    missing: list[str] = []

    def swap(m: re.Match[str]) -> str:
        rel = m.group(1)
        if rel not in cache:
            path = ROOT / rel
            if not path.exists():
                missing.append(rel)
                return m.group(0)
            cache[rel] = encode(path, args.width, args.quality)
            print(f"  埋め込み {rel:34s} {len(cache[rel]) // 1024:5d}KB")
        return f'"{cache[rel]}"'

    # HTML の src="images/…" と、方面切り替え用JS内の img: "images/…" の両方を置換する。
    # どちらも "images/ファイル名" という引用符付き文字列である点だけが共通なので、
    # 引用符ごと拾って中身だけ data URI に差し替える。
    html = re.sub(r'"(images/[^"]+)"', swap, html)

    if missing:
        print("見つからない画像:", ", ".join(sorted(set(missing))), file=sys.stderr)
        return 1

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"\n{OUT.relative_to(ROOT)} — {OUT.stat().st_size / 1_048_576:.1f}MB "
          f"（画像 {len(cache)} 点）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
