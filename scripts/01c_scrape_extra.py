"""
抓取额外发现的 transcript URL（从 category 页面发现的新 URL）
"""
import requests, json, re, time
from bs4 import BeautifulSoup
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "transcripts"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

EXTRA_URLS = [
    "https://lexfridman.com/gsp-street-fight-transcript",
    "https://lexfridman.com/book-1984-george-orwell-transcript",
]


def extract_slug(url):
    return url.rstrip("/").split("/")[-1].replace("-transcript", "")


def parse_page(html, url):
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.find("h1") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""
    title = re.sub(r"^Transcript for\s+", "", title)
    title = re.sub(r"\s*\|\s*Lex Fridman.*$", "", title)
    ep_match = re.search(r"#(\d+)", title)
    episode_num = int(ep_match.group(1)) if ep_match else None
    content_el = soup.find("div", class_="entry-content") or soup.find("article")
    if not content_el:
        return {"error": "No content", "url": url}
    full_text = content_el.get_text(separator="\n", strip=True)
    chapters = []
    for line in full_text.split("\n"):
        m = re.match(r"(\d+:\d+(?::\d+)?)\s*[–—-]\s*(.+)", line.strip())
        if m:
            chapters.append({"time": m.group(1), "title": m.group(2).strip()})
    dialogue = []
    current_speaker, current_text, current_time = None, [], None
    sp_pat = re.compile(r"^(Lex Fridman|[A-Z][a-z]+(?: [A-Z][a-z]+){0,3})$")
    tm_pat = re.compile(r"^\((\d+:\d+:\d+)\)")
    for line in full_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        tm = tm_pat.match(line)
        if tm:
            if current_speaker and current_text:
                dialogue.append({"speaker": current_speaker, "time": current_time, "text": " ".join(current_text).strip()})
                current_text = []
            current_time = tm.group(1)
            rest = line[tm.end():].strip()
            if rest:
                current_text.append(rest)
        elif sp_pat.match(line) and len(line) < 50:
            if current_speaker and current_text:
                dialogue.append({"speaker": current_speaker, "time": current_time, "text": " ".join(current_text).strip()})
                current_text, current_time = [], None
            current_speaker = line
        elif current_speaker:
            current_text.append(line)
    if current_speaker and current_text:
        dialogue.append({"speaker": current_speaker, "time": current_time, "text": " ".join(current_text).strip()})
    slug = extract_slug(url)
    return {"url": url, "slug": slug, "title": title, "episode_num": episode_num,
            "speakers": list(set(d["speaker"] for d in dialogue if d["speaker"] != "Lex Fridman")),
            "chapters": chapters, "dialogue": dialogue, "full_text": full_text, "word_count": len(full_text.split())}


def main():
    for url in EXTRA_URLS:
        slug = extract_slug(url)
        out = DATA_DIR / f"{slug}.json"
        if out.exists():
            print(f"SKIP {slug}")
            continue
        print(f"FETCH {url}")
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 404:
            print(f"  404")
            continue
        data = parse_page(r.text, url)
        if "error" not in data:
            with open(out, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  OK: {data['title'][:60]} ({data['word_count']:,} words)")
        time.sleep(1)
    total = len(list(DATA_DIR.glob("*.json")))
    print(f"\nTotal transcripts: {total}")


if __name__ == "__main__":
    main()
