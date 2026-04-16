"""
Lex Fridman Podcast Transcript Scraper
抓取所有 Lex Fridman 播客的文字稿
"""

import requests
import json
import time
import os
import re
from bs4 import BeautifulSoup
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "transcripts"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 所有已知的 transcript URLs（从播客页面提取，去重）
TRANSCRIPT_URLS = [
    "https://lexfridman.com/lars-brownworth-transcript",
    "https://lexfridman.com/jensen-huang-transcript",
    "https://lexfridman.com/jeff-kaplan-transcript",
    "https://lexfridman.com/rick-beato-transcript",
    "https://lexfridman.com/peter-steinberger-transcript",
    "https://lexfridman.com/paul-rosolie-3-transcript",
    "https://lexfridman.com/irving-finkel-transcript",
    "https://lexfridman.com/dan-houser-transcript",
    "https://lexfridman.com/pavel-durov-transcript",
    "https://lexfridman.com/keyu-jin-transcript",
    "https://lexfridman.com/jack-weatherford-transcript",
    "https://lexfridman.com/demis-hassabis-2-transcript",
    "https://lexfridman.com/dhh-david-heinemeier-hansson-transcript",
    "https://lexfridman.com/terence-tao-transcript",
    "https://lexfridman.com/sundar-pichai-transcript",
    "https://lexfridman.com/james-holland-transcript",
    "https://lexfridman.com/janna-levin-transcript",
    "https://lexfridman.com/tim-sweeney-transcript",
    "https://lexfridman.com/theprimeagen-transcript",
    "https://lexfridman.com/narendra-modi-transcript",
    "https://lexfridman.com/deepseek-dylan-patel-nathan-lambert-transcript",
    "https://lexfridman.com/jennifer-burns-transcript",
    "https://lexfridman.com/volodymyr-zelenskyy-transcript",
    "https://lexfridman.com/adam-frank-transcript",
    "https://lexfridman.com/saagar-enjeti-2-transcript",
    "https://lexfridman.com/javier-milei-transcript",
    "https://lexfridman.com/bernie-sanders-transcript",
    "https://lexfridman.com/graham-hancock-transcript",
    "https://lexfridman.com/cursor-team-transcript",
    "https://lexfridman.com/ed-barnhart-transcript",
    "https://lexfridman.com/gregory-aldrete-transcript",
    "https://lexfridman.com/donald-trump-transcript",
    "https://lexfridman.com/pieter-levels-transcript",
    "https://lexfridman.com/elon-musk-and-neuralink-team-transcript",
    "https://lexfridman.com/ivanka-trump-transcript",
    "https://lexfridman.com/aravind-srinivas-transcript",
    "https://lexfridman.com/sara-walker-3-transcript",
    "https://lexfridman.com/charan-ranganath-transcript",
    "https://lexfridman.com/paul-rosolie-2-transcript",
    "https://lexfridman.com/sean-carroll-3-transcript",
    "https://lexfridman.com/andrew-callaghan-transcript",
    "https://lexfridman.com/bassem-youssef-transcript",
    "https://lexfridman.com/tulsi-gabbard-transcript",
    "https://lexfridman.com/dana-white-transcript",
    "https://lexfridman.com/annie-jacobsen-transcript",
    "https://lexfridman.com/sam-altman-2-transcript",
    "https://lexfridman.com/israel-palestine-debate-transcript",
    "https://lexfridman.com/serhii-plokhy-transcript",
    "https://lexfridman.com/tucker-carlson-transcript",
    "https://lexfridman.com/bill-ackman-transcript",
    "https://lexfridman.com/ben-shapiro-destiny-debate-transcript",
    "https://lexfridman.com/tal-wilkenfeld-transcript",
    "https://lexfridman.com/jeff-bezos-transcript",
    "https://lexfridman.com/lisa-randall-transcript",
    "https://lexfridman.com/john-mearsheimer-transcript",
    "https://lexfridman.com/elon-musk-4-transcript",
    "https://lexfridman.com/jared-kushner-transcript",
    "https://lexfridman.com/mark-zuckerberg-3-transcript",
    "https://lexfridman.com/james-sexton-transcript",
    "https://lexfridman.com/neri-oxman-transcript",
    "https://lexfridman.com/george-hotz-3-transcript",
    "https://lexfridman.com/ben-shapiro-transcript",
    "https://lexfridman.com/nick-lane-transcript",
    "https://lexfridman.com/ai-sota-2026-transcript",
    "https://lexfridman.com/joel-david-hamkins-transcript",
    "https://lexfridman.com/michael-levin-2-transcript",
    "https://lexfridman.com/david-kirtley-transcript",
    "https://lexfridman.com/julia-shaw-transcript",
    "https://lexfridman.com/norman-ohler-transcript",
    "https://lexfridman.com/dave-hone-transcript",
    "https://lexfridman.com/dave-plummer-transcript",
    "https://lexfridman.com/iran-war-debate-transcript",
    "https://lexfridman.com/oliver-anthony-transcript",
    "https://lexfridman.com/jeffrey-wasserstrom-transcript",
    "https://lexfridman.com/robert-rodriguez-transcript",
    "https://lexfridman.com/dave-smith-transcript",
    "https://lexfridman.com/douglas-murray-2-transcript",
    "https://lexfridman.com/ezra-klein-and-derek-thompson-transcript",
    "https://lexfridman.com/marc-andreessen-2-transcript",
    "https://lexfridman.com/dario-amodei-transcript",
    "https://lexfridman.com/rick-spence-transcript",
    "https://lexfridman.com/jordan-peterson-2-transcript",
    "https://lexfridman.com/vivek-ramaswamy-transcript",
    "https://lexfridman.com/vejas-liulevicius-transcript",
    "https://lexfridman.com/cenk-uygur-transcript",
    "https://lexfridman.com/craig-jones-2-transcript",
    "https://lexfridman.com/jordan-jonas-transcript",
    "https://lexfridman.com/andrew-huberman-5-transcript",
    "https://lexfridman.com/kevin-spacey-transcript",
    "https://lexfridman.com/roman-yampolskiy-transcript",
    "https://lexfridman.com/neil-adams-transcript",
    "https://lexfridman.com/edward-gibson-transcript",
    "https://lexfridman.com/mark-cuban-transcript",
    "https://lexfridman.com/kimbal-musk-transcript",
    "https://lexfridman.com/yann-lecun-3-transcript",
    "https://lexfridman.com/marc-raibert-transcript",
    "https://lexfridman.com/omar-suleiman-2-transcript",
    "https://lexfridman.com/matthew-cox-transcript",
    "https://lexfridman.com/guillaume-verdon-transcript",
    "https://lexfridman.com/teddy-atlas-transcript",
    "https://lexfridman.com/lee-cronin-3-transcript",
    "https://lexfridman.com/michael-malice-7-transcript",
    "https://lexfridman.com/greg-lukianoff-transcript",
    "https://lexfridman.com/walter-isaacson-transcript",
    "https://lexfridman.com/andrew-huberman-4-transcript",
    "https://lexfridman.com/joscha-bach-3-transcript",
    "https://lexfridman.com/mohammed-el-kurd-transcript",
    "https://lexfridman.com/yuval-noah-harari-transcript",
    "https://lexfridman.com/benjamin-netanyahu-transcript",
    "https://lexfridman.com/robert-f-kennedy-jr-transcript",
    "https://lexfridman.com/jimmy-wales-transcript",
    "https://lexfridman.com/michael-saylor-transcript",
]

# 去重
TRANSCRIPT_URLS = list(dict.fromkeys(TRANSCRIPT_URLS))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def extract_slug(url: str) -> str:
    """从 URL 提取 slug，如 elon-musk-4"""
    return url.rstrip("/").split("/")[-1].replace("-transcript", "")


def parse_transcript_page(html: str, url: str) -> dict:
    """解析 transcript 页面，提取结构化数据"""
    soup = BeautifulSoup(html, "html.parser")
    
    # 提取标题
    title_el = soup.find("h1") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""
    # 清理标题中的 "Transcript for " 前缀
    title = re.sub(r"^Transcript for\s+", "", title)
    title = re.sub(r"\s*\|\s*Lex Fridman Podcast.*$", "", title)
    title = re.sub(r"\s*-\s*Lex Fridman$", "", title)
    
    # 提取 episode 编号
    ep_match = re.search(r"#(\d+)", title)
    episode_num = int(ep_match.group(1)) if ep_match else None
    
    # 提取正文内容
    content_el = soup.find("div", class_="entry-content") or soup.find("article")
    if not content_el:
        return {"error": "No content found", "url": url}
    
    full_text = content_el.get_text(separator="\n", strip=True)
    
    # 提取目录（章节）
    chapters = []
    toc_pattern = re.compile(r"(\d+:\d+(?::\d+)?)\s*[–—-]\s*(.+)")
    for line in full_text.split("\n"):
        m = toc_pattern.match(line.strip())
        if m:
            chapters.append({"time": m.group(1), "title": m.group(2).strip()})
    
    # 提取对话内容（格式：说话人\n(时间戳) 内容）
    dialogue = []
    lines = full_text.split("\n")
    i = 0
    current_speaker = None
    current_text = []
    current_time = None
    
    speaker_pattern = re.compile(r"^(Lex Fridman|[A-Z][a-z]+(?: [A-Z][a-z]+){0,3})$")
    time_pattern = re.compile(r"^\((\d+:\d+:\d+)\)")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检测时间戳开头的对话行
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
    
    # 提取嘉宾名（非 Lex 的说话人）
    speakers = list(set(d["speaker"] for d in dialogue if d["speaker"] != "Lex Fridman"))
    
    # 提取嘉宾名（从 slug 推断）
    slug = extract_slug(url)
    
    return {
        "url": url,
        "slug": slug,
        "title": title,
        "episode_num": episode_num,
        "speakers": speakers,
        "chapters": chapters,
        "dialogue": dialogue,
        "full_text": full_text,
        "word_count": len(full_text.split()),
    }


def scrape_transcript(url: str) -> dict | None:
    """抓取单个 transcript 页面"""
    slug = extract_slug(url)
    output_file = DATA_DIR / f"{slug}.json"
    
    # 如果已经抓取过，跳过
    if output_file.exists():
        print(f"  [SKIP] {slug} (already exists)")
        with open(output_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    try:
        print(f"  [FETCH] {url}")
        resp = requests.get(url, headers=HEADERS, timeout=30)
        
        if resp.status_code == 404:
            print(f"  [404] {url}")
            return None
        
        resp.raise_for_status()
        
        data = parse_transcript_page(resp.text, url)
        
        if "error" not in data:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  [OK] {slug} - {data.get('title', '?')[:60]} ({data.get('word_count', 0):,} words)")
        else:
            print(f"  [ERR] {slug}: {data['error']}")
        
        return data
        
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return None


def main():
    print(f"开始抓取 {len(TRANSCRIPT_URLS)} 个 transcript 页面...")
    print(f"输出目录: {DATA_DIR}")
    print("-" * 60)
    
    results = []
    failed = []
    
    for i, url in enumerate(TRANSCRIPT_URLS, 1):
        print(f"[{i}/{len(TRANSCRIPT_URLS)}]", end=" ")
        result = scrape_transcript(url)
        
        if result and "error" not in result:
            results.append(result)
        else:
            failed.append(url)
        
        # 礼貌性延迟，避免被封
        if i % 5 == 0:
            time.sleep(2)
        else:
            time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"[OK] Success: {len(results)}")
    print(f"[FAIL] Failed: {len(failed)}")
    if failed:
        print("Failed list:")
        for url in failed:
            print(f"  - {url}")
    
    # 保存汇总索引
    index = []
    for r in results:
        index.append({
            "slug": r["slug"],
            "title": r["title"],
            "episode_num": r["episode_num"],
            "speakers": r["speakers"],
            "word_count": r["word_count"],
            "chapter_count": len(r["chapters"]),
            "url": r["url"],
        })
    
    index_file = DATA_DIR.parent / "episode_index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    
    print(f"\n[INDEX] Saved: {index_file}")
    print(f"   Total: {len(index)} episodes")


if __name__ == "__main__":
    main()
