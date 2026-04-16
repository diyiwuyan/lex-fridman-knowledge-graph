"""测试并发请求速度"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import requests, time
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {"User-Agent": "Mozilla/5.0"}
HF_API  = "https://datasets-server.huggingface.co/rows"

def fetch(offset):
    t0 = time.time()
    r = requests.get(HF_API, params={
        "dataset": "nmac/lex_fridman_podcast",
        "config": "default", "split": "train",
        "offset": offset, "length": 100,
    }, headers=HEADERS, timeout=20)
    elapsed = time.time() - t0
    rows = len(r.json().get("rows", []))
    return offset, rows, elapsed

# 串行测试（4 批）
print("=== 串行 4 批 ===")
t0 = time.time()
for off in [0, 100, 200, 300]:
    _, rows, elapsed = fetch(off)
    print(f"  offset={off}: {rows} rows in {elapsed:.2f}s")
serial_time = time.time() - t0
print(f"串行总耗时: {serial_time:.2f}s")

# 并发测试（8 批）
print("\n=== 并发 8 批 ===")
t0 = time.time()
with ThreadPoolExecutor(max_workers=8) as ex:
    futs = {ex.submit(fetch, off): off for off in range(0, 800, 100)}
    for fut in as_completed(futs):
        off, rows, elapsed = fut.result()
        print(f"  offset={off}: {rows} rows in {elapsed:.2f}s")
concurrent_time = time.time() - t0
print(f"并发总耗时: {concurrent_time:.2f}s")
print(f"加速比: {serial_time*2/concurrent_time:.1f}x")
