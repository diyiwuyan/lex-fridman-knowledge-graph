"""测试 HuggingFace 各种访问方式"""
import requests
import json

HEADERS = {"User-Agent": "Mozilla/5.0"}

tests = [
    # 1. datasets-server API
    "https://datasets-server.huggingface.co/rows?dataset=nmac/lex_fridman_podcast&config=default&split=train&offset=0&length=3",
    # 2. HF Hub API
    "https://huggingface.co/api/datasets/nmac/lex_fridman_podcast",
    # 3. parquet 文件直链
    "https://huggingface.co/datasets/nmac/lex_fridman_podcast/resolve/main/data/train-00000-of-00001.parquet",
    # 4. 另一个数据集
    "https://datasets-server.huggingface.co/rows?dataset=Whispering-GPT/lex-fridman-podcast&config=default&split=train&offset=0&length=3",
]

for url in tests:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        print(f"[{r.status_code}] {url[:80]}")
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"  Keys: {list(data.keys())[:5]}")
            except Exception:
                print(f"  Content-Type: {r.headers.get('Content-Type','?')}, Size: {len(r.content)} bytes")
    except Exception as e:
        print(f"[ERR] {url[:80]}")
        print(f"  {e}")
    print()
