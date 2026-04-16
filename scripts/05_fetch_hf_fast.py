"""
HuggingFace 多线程并发下载 - 快速版
- 8 个线程并发请求，速度提升 6-8x
- 断点续传（进度文件）
- 线程安全的文件写入
- 自动重试 + 限流处理
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
import json
import time
import re
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent
TRANS_DIR = BASE_DIR / "data" / "transcripts"
TRANS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}
HF_API  = "https://datasets-server.huggingface.co/rows"
DATASET = "nmac/lex_fridman_podcast"

TOTAL_ROWS   = 803_239
BATCH        = 100       # 每次请求行数
WORKERS      = 4         # 并发线程数（太高会触发429限流）
REQ_DELAY    = 0.2       # 每个请求提交后的间隔（秒）
PROGRESS_FILE = BASE_DIR / "data" / "hf_download_progress.json"

# 线程锁
_save_lock   = threading.Lock()
_print_lock  = threading.Lock()
_stats_lock  = threading.Lock()

# 全局统计
stats = {"saved": 0, "skipped": 0, "errors": 0}

# 已有 slug 集合（线程共享，加锁访问）
existing_slugs: set[str] = set()


def safe_print(*args, **kwargs):
    with _print_lock:
        print(*args, **kwargs, flush=True)


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


def fetch_batch(offset: int) -> list[dict]:
    """获取一批数据，带重试"""
    for attempt in range(6):
        try:
            r = requests.get(HF_API, params={
                "dataset": DATASET,
                "config": "default",
                "split": "train",
                "offset": offset,
                "length": BATCH,
            }, headers=HEADERS, timeout=20)

            if r.status_code == 429:
                wait = 15 * (attempt + 1)
                safe_print(f"  [429] offset={offset} rate-limited, wait {wait}s")
                time.sleep(wait)
                continue

            if r.status_code != 200:
                safe_print(f"  [HTTP {r.status_code}] offset={offset}")
                time.sleep(3)
                continue

            return r.json().get("rows", [])

        except requests.exceptions.Timeout:
            safe_print(f"  [TIMEOUT] offset={offset} attempt {attempt+1}")
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            safe_print(f"  [ERR] offset={offset}: {e}")
            time.sleep(3)

    return []


def process_batch(offset: int) -> dict:
    """
    获取一批数据并按 episode 分组返回。
    注意：单批 100 行可能跨越 episode 边界，
    所以这里只返回原始行，由主线程按顺序合并。
    """
    rows = fetch_batch(offset)
    return {"offset": offset, "rows": rows}


def save_episode(title: str, guest: str, dialogue: list) -> str | None:
    """线程安全地保存一个 episode"""
    slug = slugify(title, guest)
    base_slug = slug

    with _save_lock:
        # 处理重名
        counter = 2
        while slug in existing_slugs:
            out = TRANS_DIR / f"{slug}.json"
            if out.exists():
                try:
                    existing = json.loads(out.read_text(encoding="utf-8"))
                    if existing.get("title") == title and existing.get("guest_name") == guest:
                        return None  # 完全相同
                except Exception:
                    pass
            slug = f"{base_slug}-{counter}"
            counter += 1

        existing_slugs.add(slug)

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

    return slug


def main():
    global existing_slugs

    # 加载已有 slug
    existing_slugs = set(f.stem for f in TRANS_DIR.glob("*.json"))
    safe_print(f"Already have: {len(existing_slugs)} transcripts")

    # 断点续传
    start_offset = 0
    if PROGRESS_FILE.exists():
        try:
            prog = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            start_offset = prog.get("next_offset", 0)
            safe_print(f"Resuming from offset {start_offset:,} / {TOTAL_ROWS:,} "
                       f"({start_offset/TOTAL_ROWS*100:.1f}%)")
        except Exception:
            pass

    safe_print(f"Workers: {WORKERS} | Batch: {BATCH} | Start: {start_offset:,}")
    safe_print("-" * 60)

    # 生成所有待处理的 offset
    all_offsets = list(range(start_offset, TOTAL_ROWS, BATCH))
    total_batches = len(all_offsets)

    # 用于按顺序合并 episode 的缓冲
    current_ep_key  = None
    current_title   = ""
    current_guest   = ""
    current_dialogue: list[dict] = []

    saved_count   = 0
    skipped_count = 0
    done_batches  = 0
    last_save_offset = start_offset

    # 用 ThreadPoolExecutor 并发请求，但按顺序处理结果（保证 episode 边界正确）
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        # 提交前 WORKERS*4 个批次，滑动窗口
        futures = {}
        submit_idx = 0
        window = WORKERS * 4

        def submit_next():
            nonlocal submit_idx
            while submit_idx < len(all_offsets) and len(futures) < window:
                off = all_offsets[submit_idx]
                fut = executor.submit(process_batch, off)
                futures[off] = fut
                submit_idx += 1

        submit_next()

        for batch_idx, offset in enumerate(all_offsets):
            # 等待这个 offset 的结果
            if offset not in futures:
                submit_next()
            fut = futures.pop(offset, None)
            if fut is None:
                continue

            time.sleep(REQ_DELAY)  # 控制整体请求速率

            try:
                result = fut.result(timeout=60)
            except Exception as e:
                safe_print(f"  [FUTURE ERR] offset={offset}: {e}")
                submit_next()
                continue

            submit_next()

            rows = result.get("rows", [])
            done_batches += 1

            for row_data in rows:
                row   = row_data.get("row", {})
                title = row.get("title", "") or ""
                guest = row.get("guest", "") or ""
                text  = row.get("text",  "") or ""
                start = row.get("start")

                ep_key = f"{title}|||{guest}"

                # episode 切换
                if current_ep_key and ep_key != current_ep_key and current_dialogue:
                    slug = save_episode(current_title, current_guest, current_dialogue)
                    if slug:
                        saved_count += 1
                        safe_print(f"  [SAVE] {current_guest[:25]} | {current_title[:40]} "
                                   f"({len(current_dialogue)} lines) -> {slug}")
                    else:
                        skipped_count += 1
                    current_dialogue = []

                current_ep_key = ep_key
                current_title  = title
                current_guest  = guest

                if text.strip():
                    time_str = str(start) if start is not None else ""
                    try:
                        si = int(float(time_str))
                        time_str = f"{si//3600:02d}:{(si%3600)//60:02d}:{si%60:02d}"
                    except (ValueError, TypeError):
                        pass
                    current_dialogue.append({
                        "speaker": guest or "Guest",
                        "time":    time_str,
                        "text":    text,
                    })

            # 进度报告（每 50 批）
            if done_batches % 50 == 0:
                cur_offset = offset + BATCH
                pct = cur_offset / TOTAL_ROWS * 100
                total_now = len(existing_slugs)
                safe_print(f"[{cur_offset:,}/{TOTAL_ROWS:,}] {pct:.1f}% | "
                           f"saved={saved_count} skip={skipped_count} total={total_now}")

                # 保存进度
                PROGRESS_FILE.write_text(json.dumps({
                    "next_offset": cur_offset,
                    "saved":       saved_count,
                    "skipped":     skipped_count,
                }), encoding="utf-8")
                last_save_offset = cur_offset

    # 保存最后一个 episode
    if current_ep_key and current_dialogue:
        slug = save_episode(current_title, current_guest, current_dialogue)
        if slug:
            saved_count += 1
            safe_print(f"  [SAVE LAST] {slug}")

    print("\n" + "=" * 60)
    print(f"[DONE] Saved:   {saved_count} new episodes")
    print(f"       Skipped: {skipped_count}")
    print(f"       Total:   {len(list(TRANS_DIR.glob('*.json')))}")

    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


if __name__ == "__main__":
    main()
