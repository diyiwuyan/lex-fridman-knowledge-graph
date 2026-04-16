"""测试 parquet 文件各种下载方式"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}

# 先查 HF API 获取 parquet 文件列表
r = requests.get(
    "https://datasets-server.huggingface.co/parquet",
    params={"dataset": "nmac/lex_fridman_podcast"},
    headers=HEADERS, timeout=15
)
print(f"parquet API status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    files = data.get("parquet_files", [])
    print(f"parquet files: {len(files)}")
    for f in files:
        print(f"  {f.get('url','')}")
        print(f"  size: {f.get('size', '?')} bytes")
else:
    print(r.text[:500])
