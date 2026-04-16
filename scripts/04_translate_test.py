"""快速测试：只翻译前 3 个 episode"""
import json, time
from pathlib import Path
from deep_translator import GoogleTranslator

BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TRANSCRIPTS_DIR = BASE_DIR / "data" / "transcripts"
TRANS_DIR = BASE_DIR / "data" / "translations"
TRANS_DIR.mkdir(parents=True, exist_ok=True)

translator = GoogleTranslator(source="en", target="zh-CN")

def tr(text):
    if not text or not text.strip():
        return ""
    try:
        r = translator.translate(text[:4800])
        time.sleep(0.2)
        return r or ""
    except Exception as e:
        print(f"  WARN: {e}")
        return ""

episodes = json.load(open(PROCESSED_DIR / "episodes.json", encoding="utf-8"))

for ep in episodes[:3]:
    slug = ep["slug"]
    print(f"\n=== {slug} ===")
    tf = TRANSCRIPTS_DIR / f"{slug}.json"
    td = json.load(open(tf, encoding="utf-8")) if tf.exists() else {}

    chapters = td.get("chapters", [])[:5]
    print(f"Chapters ({len(chapters)}):")
    for ch in chapters:
        zh = tr(ch.get("title",""))
        print(f"  {ch.get('title','')} -> {zh}")

    quotes = ep.get("key_quotes", [])[:2]
    print(f"Quotes ({len(quotes)}):")
    for q in quotes:
        text = q.get("text","")[:200]
        zh = tr(text)
        print(f"  EN: {text[:80]}...")
        print(f"  ZH: {zh[:80]}...")

print("\nTest done!")
