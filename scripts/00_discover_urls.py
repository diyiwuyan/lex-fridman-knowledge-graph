"""
自动发现所有 Lex Fridman Podcast transcript URL
策略：
1. 从 /podcast/ 页面提取所有 episode 链接
2. 每个 episode 链接 + "-transcript" = transcript URL
3. 输出完整 URL 列表（抓取时遇到 404 自动跳过）
"""

import requests
import json
from bs4 import BeautifulSoup
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SKIP_URLS = {
    "https://lexfridman.com",
    "https://lexfridman.com/",
    "https://lexfridman.com/contact",
    "https://lexfridman.com/contact/",
    "https://lexfridman.com/sponsors",
    "https://lexfridman.com/sponsors/",
    "https://lexfridman.com/feed/podcast/",
    "https://lexfridman.com/podcast",
    "https://lexfridman.com/podcast/",
}

SKIP_SLUGS = {
    "contact", "sponsors", "podcast", "feed", "about", "research",
    "courses", "books", "ama", "newsletter", "youtube", "twitter",
    "instagram", "linkedin", "github", "patreon", "discord",
}


def get_episode_links_from_podcast_page():
    print("Fetching https://lexfridman.com/podcast/ ...")
    r = requests.get("https://lexfridman.com/podcast/", headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    ep_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].rstrip("/")
        if not href.startswith("https://lexfridman.com/"):
            continue
        if href in SKIP_URLS:
            continue
        if "transcript" in href:
            continue
        path = href.replace("https://lexfridman.com", "").strip("/")
        if "/" in path:
            continue
        if not path:
            continue
        if path in SKIP_SLUGS:
            continue
        ep_links.append(href)

    ep_links = list(dict.fromkeys(ep_links))
    print(f"  Found {len(ep_links)} episode links")
    return ep_links


def main():
    ep_links = get_episode_links_from_podcast_page()

    all_transcript_urls = []
    for ep_url in ep_links:
        slug = ep_url.replace("https://lexfridman.com/", "").strip("/")
        trans_url = f"https://lexfridman.com/{slug}-transcript"
        all_transcript_urls.append(trans_url)

    print(f"Constructed {len(all_transcript_urls)} transcript URLs")

    # 与已有的对比
    existing_slugs = set()
    trans_dir = BASE_DIR / "data" / "transcripts"
    for f in trans_dir.glob("*.json"):
        existing_slugs.add(f.stem)

    new_urls = []
    existing_urls = []
    for url in all_transcript_urls:
        slug = url.rstrip("/").split("/")[-1].replace("-transcript", "")
        if slug in existing_slugs:
            existing_urls.append(url)
        else:
            new_urls.append(url)

    print(f"Already scraped: {len(existing_urls)}")
    print(f"New to scrape:   {len(new_urls)}")

    all_urls_clean = [u.rstrip("/") for u in all_transcript_urls]

    out_file = BASE_DIR / "data" / "all_transcript_urls.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "total": len(all_urls_clean),
            "existing": len(existing_urls),
            "new": len(new_urls),
            "urls": all_urls_clean,
            "new_urls": [u.rstrip("/") for u in new_urls],
        }, f, ensure_ascii=False, indent=2)

    print(f"[DONE] Saved to {out_file}")
    print(f"Total transcript URLs: {len(all_urls_clean)}")
    print(f"New to scrape: {len(new_urls)}")

    # 打印前10个新URL预览
    print("\nFirst 10 new URLs:")
    for u in new_urls[:10]:
        print(f"  {u}")


if __name__ == "__main__":
    main()
