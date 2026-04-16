import requests
import re

r = requests.get("https://karpathy.ai/lexicap/", headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
print("Status:", r.status_code)
# 找所有链接
links = re.findall(r'href=["\']([^"\']+)["\']', r.text)
print("Total links:", len(links))
for l in links[:30]:
    print(" ", l)
