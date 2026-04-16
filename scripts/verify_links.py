import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path

# 验证首页链接
html = Path("site/index.html").read_text(encoding="utf-8")
links = re.findall(r'href="([^"]+)"', html)
print("=== 首页链接（前15个）===")
for l in links[:15]:
    print(f"  {l}")

# 验证episode页面链接
html2 = Path("site/episodes/albert-bourla.html").read_text(encoding="utf-8")
links2 = re.findall(r'href="([^"]+)"', html2)
print("\n=== albert-bourla 页面链接（前10个）===")
for l in links2[:10]:
    print(f"  {l}")

# 检查对话条数
import json
d = json.loads(Path("data/transcripts/albert-bourla.json").read_text(encoding="utf-8"))
dialogue = d.get("dialogue", [])
print(f"\nalbert-bourla 对话总条数: {len(dialogue)}")

# 检查网站里的对话是否包含全部
count = html2.count('dialogue-item')
print(f"网站页面中 dialogue-item 数量: {count}")
