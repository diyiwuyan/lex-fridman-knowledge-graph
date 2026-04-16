"""测试 parquet 下载 - 多种方式"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests

PARQUET_URL = "https://huggingface.co/datasets/nmac/lex_fridman_podcast/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"

# 方式1: 直接下载（HEAD 检查）
r = requests.head(PARQUET_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, allow_redirects=True)
print(f"HEAD status: {r.status_code}")
print(f"Content-Length: {r.headers.get('Content-Length', '?')}")
print(f"Final URL: {r.url}")

# 方式2: 用 hf-hub CDN 镜像
CDN_URL = "https://huggingface.co/datasets/nmac/lex_fridman_podcast/resolve/main/data/train-00000-of-00001.parquet"
r2 = requests.head(CDN_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, allow_redirects=True)
print(f"\nCDN HEAD status: {r2.status_code}")

# 方式3: hf-mirror.com (中国镜像)
MIRROR_URL = "https://hf-mirror.com/datasets/nmac/lex_fridman_podcast/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
r3 = requests.head(MIRROR_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, allow_redirects=True)
print(f"\nhf-mirror HEAD status: {r3.status_code}")
print(f"Content-Length: {r3.headers.get('Content-Length', '?')}")
