"""
从 lexfridman.com/category/transcripts/ 分页抓取所有 transcript URL
这个分类页面包含所有有 transcript 的 episode
"""

import requests
import json
from bs4 import BeautifulSoup
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_transcript_links_from_page(url: str):
    """从分类页面提取 transcript 链接"""
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return [], None
    soup = BeautifulSoup(r.text, "html.parser")

    # 提取 transcript 链接
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].rstrip("/")
        if "lexfridman.com" in href and "transcript" in href and "category" not in href:
            links.append(href)
    links = list(dict.fromkeys(links))

    # 找下一页
    next_page = None
    next_link = soup.find("a", class_="next") or soup.find("a", string="Next") or soup.find("a", string="»")
    if next_link:
        next_page = next_link.get("href")
    # 也尝试找 page/N 格式
    if not next_page:
        nav = soup.find("div", class_="nav-links") or soup.find("nav", class_="navigation")
        if nav:
            for a in nav.find_all("a", href=True):
                if "page" in a["href"] or a.get_text(strip=True).isdigit():
                    # 找当前页码
                    current = nav.find("span", class_="current")
                    if current:
                        try:
                            cur_num = int(current.get_text(strip=True))
                            next_href = a.get("href", "")
                            if f"/page/{cur_num + 1}/" in next_href:
                                next_page = next_href
                                break
                        except ValueError:
                            pass

    return links, next_page


def main():
    all_links = []
    url = "https://lexfridman.com/category/transcripts/"
    page = 1

    while url:
        print(f"Page {page}: {url}")
        links, next_url = get_transcript_links_from_page(url)
        print(f"  Found {len(links)} transcript links")
        all_links.extend(links)
        url = next_url
        page += 1
        if page > 100:  # 安全上限
            break

    all_links = list(dict.fromkeys(all_links))
    print(f"\nTotal unique transcript URLs: {len(all_links)}")

    # 与已有的对比
    existing_slugs = set()
    trans_dir = BASE_DIR / "data" / "transcripts"
    for f in trans_dir.glob("*.json"):
        existing_slugs.add(f.stem)

    new_urls = [u for u in all_links
                if u.rstrip("/").split("/")[-1].replace("-transcript", "") not in existing_slugs]

    print(f"Already scraped: {len(all_links) - len(new_urls)}")
    print(f"New to scrape: {len(new_urls)}")

    # 保存
    out_file = BASE_DIR / "data" / "category_transcript_urls.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "total": len(all_links),
            "new": len(new_urls),
            "urls": all_links,
            "new_urls": new_urls,
        }, f, ensure_ascii=False, indent=2)

    print(f"Saved to {out_file}")
    print("\nAll URLs:")
    for u in all_links:
        print(f"  {u}")


if __name__ == "__main__":
    main()
