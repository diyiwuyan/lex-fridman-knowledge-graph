"""查看 HuggingFace 数据集结构和总量"""
import requests, json

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE = "https://datasets-server.huggingface.co"

# 总行数
r = requests.get(f"{BASE}/rows", params={
    "dataset": "nmac/lex_fridman_podcast",
    "config": "default", "split": "train",
    "offset": 0, "length": 3
}, headers=HEADERS, timeout=15)
data = r.json()
print(f"Total rows: {data['num_rows_total']:,}")
print(f"Features: {[f['name'] for f in data['features']]}")
print()
print("Sample rows:")
for row in data["rows"][:3]:
    r2 = row["row"]
    print(f"  episode_id={r2.get('episode_id')} | title={str(r2.get('title',''))[:50]}")
    print(f"  guest={r2.get('guest')} | text={str(r2.get('text',''))[:80]}")
    print(f"  start={r2.get('start_time')} end={r2.get('end_time')}")
    print()
