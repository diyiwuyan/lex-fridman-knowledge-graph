import json

eps = json.load(open('data/processed/episodes.json', encoding='utf-8'))
print("=== Episode titles & guests ===")
for e in eps[:15]:
    print(f"  slug: {e['slug']}")
    print(f"  title: {e['title'][:70]}")
    print(f"  guest: {e['guest_name']}")
    print(f"  topics: {e['topics']}")
    print()

# 检查一个原始 transcript 文件
raw = json.load(open('data/transcripts/elon-musk-4.json', encoding='utf-8'))
print("=== Raw transcript sample (elon-musk-4) ===")
print(f"  title: {raw['title']}")
print(f"  speakers: {raw['speakers']}")
print(f"  dialogue[0]: {raw['dialogue'][0] if raw['dialogue'] else 'EMPTY'}")
print(f"  dialogue count: {len(raw['dialogue'])}")
