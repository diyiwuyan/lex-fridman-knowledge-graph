"""快速测试：只取前 500 行，看能解析出几个 episode"""
import requests, json, re, time
from pathlib import Path
from collections import defaultdict

HEADERS = {"User-Agent": "Mozilla/5.0"}
HF_API = "https://datasets-server.huggingface.co/rows"

def fetch(offset, length=100):
    r = requests.get(HF_API, params={
        "dataset": "nmac/lex_fridman_podcast",
        "config": "default", "split": "train",
        "offset": offset, "length": length,
    }, headers=HEADERS, timeout=15)
    return r.json()

episodes = defaultdict(lambda: {"title":"","guest":"","lines":0})
last_key = None

for offset in range(0, 500, 100):
    data = fetch(offset)
    for rd in data["rows"]:
        row = rd["row"]
        key = f"{row.get('title','')}|||{row.get('guest','')}"
        ep = episodes[key]
        ep["title"] = row.get("title","")
        ep["guest"] = row.get("guest","")
        ep["lines"] += 1
        last_key = key
    time.sleep(0.3)

print(f"Found {len(episodes)} episodes in first 500 rows:")
for key, ep in list(episodes.items())[:10]:
    print(f"  [{ep['lines']:3d} lines] {ep['guest'][:25]:25s} | {ep['title'][:50]}")
