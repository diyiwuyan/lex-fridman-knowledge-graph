"""
增量抓取脚本：只抓取 all_transcript_urls.json 中尚未抓取的 transcript
- 支持断点续传（已存在的 slug 自动跳过）
- 404 页面跳过并记录
- 每 5 个请求休眠 2 秒，避免被封
"""

import requests
import json
import time
import re
from bs4 import BeautifulSoup
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "transcripts"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def extract_slug(url: str) -> str:
    return url.rstrip("/").split("/")[-1].replace("-transcript", "")


def parse_transcript_page(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.find("h1") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""
    title = re.sub(r"^Transcript for\s+", "", title)
    title = re.sub(r"\s*\|\s*Lex Fridman Podcast.*$", "", title)
    title = re.sub(r"\s*-\s*Lex Fridman$", "", title)

    ep_match = re.search(r"#(\d+)", title)
    episode_num = int(ep_match.group(1)) if ep_match else None

    content_el = soup.find("div", class_="entry-content") or soup.find("article")
    if not content_el:
        return {"error": "No content found", "url": url}

    full_text = content_el.get_text(separator="\n", strip=True)

    # 章节
    chapters = []
    toc_pattern = re.compile(r"(\d+:\d+(?::\d+)?)\s*[–—-]\s*(.+)")
    for line in full_text.split("\n"):
        m = toc_pattern.match(line.strip())
        if m:
            chapters.append({"time": m.group(1), "title": m.group(2).strip()})

    # 对话
    dialogue = []
    lines = full_text.split("\n")
    current_speaker = None
    current_text = []
    current_time = None

    speaker_pattern = re.compile(r"^(Lex Fridman|[A-Z][a-z]+(?: [A-Z][a-z]+){0,3})$")
    time_pattern = re.compile(r"^\((\d+:\d+:\d+)\)")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        time_match = time_pattern.match(line)
        if time_match:
            if current_speaker and current_text:
                dialogue.append({
                    "speaker": current_speaker,
                    "time": current_time,
                    "text": " ".join(current_text).strip()
                })
                current_text = []
            current_time = time_match.group(1)
            rest = line[time_match.end():].strip()
            if rest:
                current_text.append(rest)
        elif speaker_pattern.match(line) and len(line) < 50:
            if current_speaker and current_text:
                dialogue.append({
                    "speaker": current_speaker,
                    "time": current_time,
                    "text": " ".join(current_text).strip()
                })
                current_text = []
                current_time = None
            current_speaker = line
        elif current_speaker:
            current_text.append(line)

    if current_speaker and current_text:
        dialogue.append({
            "speaker": current_speaker,
            "time": current_time,
            "text": " ".join(current_text).strip()
        })

    slug = extract_slug(url)
    return {
        "url": url,
        "slug": slug,
        "title": title,
        "episode_num": episode_num,
        "speakers": list(set(d["speaker"] for d in dialogue if d["speaker"] != "Lex Fridman")),
        "chapters": chapters,
        "dialogue": dialogue,
        "full_text": full_text,
        "word_count": len(full_text.split()),
    }


def scrape_transcript(url: str) -> dict | None:
    slug = extract_slug(url)
    output_file = DATA_DIR / f"{slug}.json"

    if output_file.exists():
        return {"slug": slug, "status": "skip"}

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 404:
            return {"slug": slug, "status": "404"}
        resp.raise_for_status()

        data = parse_transcript_page(resp.text, url)
        if "error" not in data:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return {"slug": slug, "status": "ok", "title": data.get("title", ""), "words": data.get("word_count", 0)}
        else:
            return {"slug": slug, "status": "error", "msg": data["error"]}

    except Exception as e:
        return {"slug": slug, "status": "error", "msg": str(e)}


def main():
    url_file = BASE_DIR / "data" / "all_transcript_urls.json"
    if not url_file.exists():
        print("ERROR: Run 00_discover_urls.py first!")
        return

    data = json.loads(url_file.read_text(encoding="utf-8"))
    new_urls = data.get("new_urls", [])
    print(f"New URLs to scrape: {len(new_urls)}")
    print("-" * 60)

    ok_count = 0
    skip_count = 0
    fail_count = 0
    not_found = []

    for i, url in enumerate(new_urls, 1):
        slug = extract_slug(url)
        # 再次检查（断点续传）
        if (DATA_DIR / f"{slug}.json").exists():
            skip_count += 1
            print(f"[{i:3d}/{len(new_urls)}] SKIP {slug}")
            continue

        print(f"[{i:3d}/{len(new_urls)}] FETCH {url}")
        result = scrape_transcript(url)

        if result["status"] == "ok":
            ok_count += 1
            words = result.get("words", 0)
            title = result.get("title", "")[:50]
            print(f"  [OK] {title} ({words:,} words)")
        elif result["status"] == "404":
            fail_count += 1
            not_found.append(url)
            print(f"  [404] No transcript page")
        else:
            fail_count += 1
            print(f"  [ERR] {result.get('msg', '')}")

        # 礼貌延迟
        if i % 5 == 0:
            time.sleep(2)
        else:
            time.sleep(0.8)

    print("\n" + "=" * 60)
    print(f"[OK]   Success: {ok_count}")
    print(f"[SKIP] Already existed: {skip_count}")
    print(f"[FAIL] Failed/404: {fail_count}")

    if not_found:
        print(f"\nNo transcript found for {len(not_found)} episodes:")
        for u in not_found[:20]:
            print(f"  - {u}")

    total = len(list(DATA_DIR.glob("*.json")))
    print(f"\nTotal transcripts now: {total}")


if __name__ == "__main__":
    main()
