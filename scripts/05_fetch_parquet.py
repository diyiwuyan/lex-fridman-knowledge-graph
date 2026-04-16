"""
直接下载 HuggingFace parquet 文件（37MB），本地处理
完全绕过 API 限流，一次性搞定
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
import json
import re
import time
from pathlib import Path

BASE_DIR  = Path(__file__).parent.parent
TRANS_DIR = BASE_DIR / "data" / "transcripts"
TRANS_DIR.mkdir(parents=True, exist_ok=True)

PARQUET_URL = "https://huggingface.co/datasets/nmac/lex_fridman_podcast/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
MIRROR_URL  = "https://hf-mirror.com/datasets/nmac/lex_fridman_podcast/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
LOCAL_FILE  = BASE_DIR / "data" / "lex_fridman.parquet"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def download_parquet():
    if LOCAL_FILE.exists():
        size = LOCAL_FILE.stat().st_size
        print(f"Parquet already downloaded: {size/1024/1024:.1f} MB")
        return True

    for url, name in [(PARQUET_URL, "HuggingFace"), (MIRROR_URL, "hf-mirror")]:
        print(f"Downloading from {name}: {url[:60]}...")
        try:
            r = requests.get(url, headers=HEADERS, timeout=120, stream=True)
            if r.status_code != 200:
                print(f"  HTTP {r.status_code}, trying next...")
                continue

            total = int(r.headers.get("Content-Length", 0))
            downloaded = 0
            with open(LOCAL_FILE, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        print(f"\r  {downloaded/1024/1024:.1f}/{total/1024/1024:.1f} MB ({pct:.0f}%)", end="", flush=True)
            print(f"\n  Downloaded: {downloaded/1024/1024:.1f} MB")
            return True
        except Exception as e:
            print(f"  Error: {e}")
            if LOCAL_FILE.exists():
                LOCAL_FILE.unlink()

    return False


def slugify(title: str, guest: str) -> str:
    name = guest.strip() if guest and guest.strip() else title.strip()
    name = re.sub(r"^#\d+\s*[–—\-]\s*", "", name)
    if ":" in name:
        name = name.split(":")[0]
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\s\-]", "", name)
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "unknown"


def process_parquet():
    import pandas as pd

    print("Loading parquet file...")
    df = pd.read_parquet(LOCAL_FILE)
    print(f"Loaded: {len(df):,} rows, columns: {list(df.columns)}")

    # 按 episode (title + guest) 分组
    print("Grouping by episode...")
    existing_slugs = set(f.stem for f in TRANS_DIR.glob("*.json"))
    print(f"Already have: {len(existing_slugs)} transcripts")

    saved = 0
    skipped = 0
    slug_set = set(existing_slugs)

    # 按顺序遍历，检测 episode 切换
    current_title  = None
    current_guest  = None
    current_rows   = []

    def flush_episode():
        nonlocal saved, skipped
        if not current_rows:
            return
        title = current_title or ""
        guest = current_guest or ""
        slug  = slugify(title, guest)

        # 处理重名
        base = slug
        counter = 2
        while slug in slug_set:
            out = TRANS_DIR / f"{slug}.json"
            if out.exists():
                try:
                    ex = json.loads(out.read_text(encoding="utf-8"))
                    if ex.get("title") == title and ex.get("guest_name") == guest:
                        skipped += 1
                        return
                except Exception:
                    pass
            slug = f"{base}-{counter}"
            counter += 1

        slug_set.add(slug)

        dialogue = []
        for row in current_rows:
            text  = str(row.get("text", "") or "").strip()
            start = row.get("start")
            if not text:
                continue
            time_str = str(start) if start is not None else ""
            try:
                si = int(float(time_str))
                time_str = f"{si//3600:02d}:{(si%3600)//60:02d}:{si%60:02d}"
            except (ValueError, TypeError):
                pass
            dialogue.append({"speaker": guest or "Guest", "time": time_str, "text": text})

        if not dialogue:
            return

        full_text = "\n".join(d["text"] for d in dialogue)
        ep_match  = re.search(r"#(\d+)", title)
        ep_num    = int(ep_match.group(1)) if ep_match else None

        result = {
            "url":         f"https://lexfridman.com/{slug}",
            "slug":        slug,
            "title":       title,
            "episode_num": ep_num,
            "guest_name":  guest,
            "speakers":    [guest] if guest else [],
            "chapters":    [],
            "dialogue":    dialogue,
            "full_text":   full_text,
            "word_count":  len(full_text.split()),
            "source":      "huggingface_whisper",
        }

        out_file = TRANS_DIR / f"{slug}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        saved += 1
        print(f"  [SAVE] {guest[:25]:25s} | {title[:40]:40s} ({len(dialogue)} lines) -> {slug}")

    total_rows = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        title = str(row.get("title", "") or "")
        guest = str(row.get("guest", "") or "")

        if title != current_title or guest != current_guest:
            flush_episode()
            current_title = title
            current_guest = guest
            current_rows  = []

        current_rows.append(row)

        if i % 50000 == 0:
            pct = i / total_rows * 100
            total_now = len(slug_set)
            print(f"[{i:,}/{total_rows:,}] {pct:.1f}% | saved={saved} skip={skipped} total={total_now}")

    flush_episode()  # 最后一个

    print("\n" + "=" * 60)
    print(f"[DONE] Saved:   {saved} new episodes")
    print(f"       Skipped: {skipped}")
    print(f"       Total:   {len(list(TRANS_DIR.glob('*.json')))}")


def main():
    t0 = time.time()

    if not download_parquet():
        print("ERROR: Failed to download parquet file")
        return

    process_parquet()

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.0f}s ({elapsed/60:.1f} min)")


if __name__ == "__main__":
    main()
