import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from pathlib import Path

eps = json.loads(Path('data/processed/episodes.json').read_text(encoding='utf-8'))
print(f"总 episode 数: {len(eps)}")

# 找出 title == guest_name 的情况
bad = [e for e in eps if e.get('title','') == e.get('guest_name','') and e.get('title','')]
print(f"\ntitle==guest_name 的 episode 数量: {len(bad)}")
print("前15个:")
for e in bad[:15]:
    print(f"  {e['slug']} | title={e['title'][:40]} | source={e.get('source','?')}")

# 按 source 分组
from collections import Counter
src_counts = Counter(e.get('source','unknown') for e in eps)
print(f"\n按来源分布: {dict(src_counts)}")

# HF 来源的 episode
hf = [e for e in eps if e.get('source') == 'huggingface']
print(f"\nHF来源总数: {len(hf)}")
print("HF前10个:")
for e in hf[:10]:
    print(f"  {e['slug']} | title={e.get('title','')[:50]} | guest={e.get('guest_name','')}")

# 看看 transcripts 里的原始数据
print("\n\n--- 查看 transcripts 原始数据 ---")
transcript_dir = Path('data/transcripts')
hf_files = list(transcript_dir.glob('*.json'))[:5]
for f in hf_files:
    data = json.loads(f.read_text(encoding='utf-8'))
    print(f"\n{f.name}:")
    print(f"  title: {data.get('title','')[:60]}")
    print(f"  guest_name: {data.get('guest_name','')}")
    print(f"  episode_number: {data.get('episode_number','')}")
    print(f"  source: {data.get('source','')}")
