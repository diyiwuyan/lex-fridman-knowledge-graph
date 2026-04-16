"""
从 HuggingFace datasets-server API 下载 nmac/lex_fridman_podcast
803,239 行，按 episode (title+guest) 分组，保存为 transcript JSON

运行时间估算：803K 行 / 100 行每请求 = 8032 次请求
每次请求约 0.3s → 约 40 分钟（加上限流重试可能更长）
支持断点续传：已存在的 episode 跳过
"""

import sys
import io
# 强制 stdout 使用 UTF-8，避免 Windows GBK 编码错误
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
import time
import re
from pathlib import Path
from collections import defaultdict, OrderedDict

BASE_DIR = Path(__file__).parent.parent
TRANS_DIR = BASE_DIR / "data" / "transcripts"
TRANS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}
HF_API = "https://datasets-server.huggingface.co/rows"
DATASET = "nmac/lex_fridman_podcast"
BATCH = 100   # 每次请求行数（API 最大 100）
DELAY = 0.25  # 请求间隔（秒）
SAVE_EVERY = 50  # 每处理 N 个 episode 保存一次进度

# 进度文件
PROGRESS_FILE = BASE_DIR / "data" / "hf_download_progress.json"


def slugify(title: str, guest: str) -> str:
    """生成 slug：优先用 guest 名，fallback 用 title"""
    name = guest.strip() if guest and guest.strip() else title.strip()
    # 去掉 #xxx 前缀
    name = re.sub(r"^#\d+\s*[–—\-]\s*", "", name)
    # 取冒号前（嘉宾名部分）
    if ":" in name:
        name = name.split(":")[0]
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\s\-]", "", name)
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "unknown"


def fetch_rows(offset: int, length: int = BATCH) -> dict:
    """带重试的 API 请求"""
    for attempt in range(5):
        try:
            r = requests.get(HF_API, params={
                "dataset": DATASET,
                "config": "default",
                "split": "train",
                "offset": offset,
                "length": length,
            }, headers=HEADERS, timeout=30)

            if r.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"  [429] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue

            r.raise_for_status()
            return r.json()

        except requests.exceptions.Timeout:
            print(f"  [TIMEOUT] offset={offset}, attempt {attempt+1}/5")
            time.sleep(5)
        except Exception as e:
            print(f"  [ERR] offset={offset}: {e}, attempt {attempt+1}/5")
            time.sleep(3)

    print(f"  [FAIL] All retries failed at offset={offset}, will skip", flush=True)
    return {"rows": []}


def save_episode(ep_key: str, ep_data: dict, existing_slugs: set) -> str | None:
    """保存一个 episode，返回 slug（已存在则返回 None）"""
    title = ep_data["title"]
    guest = ep_data["guest"]
    slug = slugify(title, guest)

    # 处理重名（加数字后缀）
    base_slug = slug
    counter = 2
    while slug in existing_slugs and (TRANS_DIR / f"{slug}.json").exists():
        # 检查已有文件是否是同一个 episode
        try:
            existing = json.loads((TRANS_DIR / f"{slug}.json").read_text(encoding="utf-8"))
            if existing.get("title") == title and existing.get("guest_name") == guest:
                return None  # 完全相同，跳过
        except Exception:
            pass
        slug = f"{base_slug}-{counter}"
        counter += 1

    if slug in existing_slugs:
        return None

    dialogue = ep_data["dialogue"]
    full_text = "\n".join(d["text"] for d in dialogue)

    # 提取 episode 编号
    ep_match = re.search(r"#(\d+)", title)
    episode_num = int(ep_match.group(1)) if ep_match else None

    result = {
        "url": f"https://lexfridman.com/{slug}",
        "slug": slug,
        "title": title,
        "episode_num": episode_num,
        "guest_name": guest,
        "speakers": [guest] if guest else [],
        "chapters": [],
        "dialogue": dialogue,
        "full_text": full_text,
        "word_count": len(full_text.split()),
        "source": "huggingface_whisper",
    }

    out_file = TRANS_DIR / f"{slug}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return slug


def main():
    # 加载进度
    start_offset = 0
    if PROGRESS_FILE.exists():
        try:
            prog = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            start_offset = prog.get("next_offset", 0)
            print(f"Resuming from offset {start_offset:,}")
        except Exception:
            pass

    # 获取总行数
    print("Fetching dataset info...")
    info = fetch_rows(0, 1)
    total_rows = info.get("num_rows_total", 803239)
    print(f"Total rows: {total_rows:,}")

    # 已有的 slug 集合
    existing_slugs = set(f.stem for f in TRANS_DIR.glob("*.json"))
    print(f"Already have: {len(existing_slugs)} transcripts")
    print(f"Starting from row {start_offset:,} / {total_rows:,}")
    print("-" * 60)

    # 当前正在积累的 episode（按 title+guest 分组）
    current_episodes: dict[str, dict] = {}
    saved_count = 0
    skipped_count = 0
    last_ep_key = None

    for offset in range(start_offset, total_rows, BATCH):
        data = fetch_rows(offset)
        rows = data.get("rows", [])
        if not rows:
            print(f"  [WARN] Empty batch at offset {offset}, skipping...", flush=True)
            time.sleep(3)
            continue

        for row_data in rows:
            row = row_data.get("row", {})
            title = row.get("title", "") or ""
            guest = row.get("guest", "") or ""
            text = row.get("text", "") or ""
            start = row.get("start")
            end = row.get("end")

            ep_key = f"{title}|||{guest}"

            # 检测 episode 切换
            if last_ep_key and ep_key != last_ep_key and last_ep_key in current_episodes:
                # 保存上一个 episode
                slug = save_episode(last_ep_key, current_episodes[last_ep_key], existing_slugs)
                if slug:
                    existing_slugs.add(slug)
                    saved_count += 1
                    ep_title = current_episodes[last_ep_key]["title"][:45]
                    ep_guest = current_episodes[last_ep_key]["guest"][:20]
                    lines = len(current_episodes[last_ep_key]["dialogue"])
                    print(f"  [SAVE] {ep_guest} - {ep_title} ({lines} lines) -> {slug}")
                else:
                    skipped_count += 1
                del current_episodes[last_ep_key]

            # 积累当前 episode
            if ep_key not in current_episodes:
                current_episodes[ep_key] = {
                    "title": title,
                    "guest": guest,
                    "dialogue": [],
                }

            if text.strip():
                # start 可能是 "00:00.000" 字符串或数字秒
                time_str = str(start) if start is not None else ""
                try:
                    si = int(float(time_str))
                    time_str = f"{si//3600:02d}:{(si%3600)//60:02d}:{si%60:02d}"
                except (ValueError, TypeError):
                    pass  # 保留原始格式
                current_episodes[ep_key]["dialogue"].append({
                    "speaker": guest or "Guest",
                    "time": time_str,
                    "text": text,
                })

            last_ep_key = ep_key

        # 进度报告
        pct = (offset + BATCH) / total_rows * 100
        total_now = len(existing_slugs)
        print(f"[{offset+BATCH:,}/{total_rows:,}] {pct:.1f}% | saved={saved_count} skip={skipped_count} total={total_now}", flush=True)

        # 保存进度
        PROGRESS_FILE.write_text(json.dumps({
            "next_offset": offset + BATCH,
            "saved": saved_count,
            "skipped": skipped_count,
        }), encoding="utf-8")

        time.sleep(DELAY)

    # 保存最后一个 episode
    if last_ep_key and last_ep_key in current_episodes:
        slug = save_episode(last_ep_key, current_episodes[last_ep_key], existing_slugs)
        if slug:
            saved_count += 1
            print(f"  [SAVE LAST] {slug}")

    print("\n" + "=" * 60)
    print(f"[DONE] Saved: {saved_count} new episodes")
    print(f"       Skipped: {skipped_count}")
    print(f"       Total transcripts: {len(list(TRANS_DIR.glob('*.json')))}")

    # 清除进度文件
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


if __name__ == "__main__":
    main()
