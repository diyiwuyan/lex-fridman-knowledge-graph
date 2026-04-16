"""
批量翻译脚本：将 episodes 的 chapters、key_quotes、对话预览翻译成中文
- 使用 Google Translate (deep-translator) 免费翻译
- 结果缓存到 data/translations/<slug>.json，避免重复翻译
- 支持断点续传：已翻译的 slug 直接跳过
"""

import json
import time
import re
from pathlib import Path
from deep_translator import GoogleTranslator

BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TRANSCRIPTS_DIR = BASE_DIR / "data" / "transcripts"
TRANS_DIR = BASE_DIR / "data" / "translations"
TRANS_DIR.mkdir(parents=True, exist_ok=True)

translator = GoogleTranslator(source="en", target="zh-CN")

# 每次翻译后等待，避免触发限流
DELAY = 0.3  # 秒


def translate_text(text: str) -> str:
    """翻译单段文本，失败返回空字符串"""
    if not text or not text.strip():
        return ""
    try:
        # Google Translate 单次最多 5000 字符
        if len(text) > 4800:
            text = text[:4800]
        result = translator.translate(text)
        time.sleep(DELAY)
        return result or ""
    except Exception as e:
        print(f"    [WARN] translate failed: {e}")
        time.sleep(1)
        return ""


def translate_batch(texts: list[str]) -> list[str]:
    """批量翻译文本列表"""
    results = []
    for t in texts:
        results.append(translate_text(t))
    return results


def translate_episode(slug: str, ep_data: dict, transcript_data: dict) -> dict:
    """翻译一个 episode 的所有内容，返回翻译结果字典"""
    result = {
        "slug": slug,
        "chapters_zh": [],
        "quotes_zh": [],
        "dialogue_zh": [],
    }

    # 1. 翻译章节标题
    chapters = transcript_data.get("chapters", ep_data.get("chapters", []))
    if chapters:
        print(f"    翻译 {len(chapters)} 个章节标题...")
        for ch in chapters:
            title = ch.get("title", "")
            zh = translate_text(title)
            result["chapters_zh"].append(zh)

    # 2. 翻译 key_quotes
    quotes = ep_data.get("key_quotes", [])
    if quotes:
        print(f"    翻译 {len(quotes)} 条语录...")
        for q in quotes:
            text = q.get("text", "")
            zh = translate_text(text)
            result["quotes_zh"].append(zh)

    # 3. 翻译对话预览（前 20 条）
    dialogue = transcript_data.get("dialogue", [])
    preview = dialogue[:20]
    if preview:
        print(f"    翻译 {len(preview)} 条对话预览...")
        for d in preview:
            text = d.get("text", "")
            # 对话可能很长，截取前 400 字符（与网站展示一致）
            text_short = text[:400]
            zh = translate_text(text_short)
            result["dialogue_zh"].append(zh)

    return result


def main():
    # 加载 episodes 数据
    episodes = json.load(open(PROCESSED_DIR / "episodes.json", encoding="utf-8"))
    print(f"共 {len(episodes)} 个 episode 需要翻译")

    # 统计已完成
    done = sum(1 for ep in episodes if (TRANS_DIR / f"{ep['slug']}.json").exists())
    print(f"已完成: {done}，剩余: {len(episodes) - done}")
    print()

    for i, ep in enumerate(episodes, 1):
        slug = ep["slug"]
        out_file = TRANS_DIR / f"{slug}.json"

        # 跳过已翻译
        if out_file.exists():
            print(f"[{i:3d}/{len(episodes)}] SKIP {slug}")
            continue

        print(f"[{i:3d}/{len(episodes)}] 翻译 {slug}...")

        # 加载原始 transcript
        transcript_file = TRANSCRIPTS_DIR / f"{slug}.json"
        transcript_data = {}
        if transcript_file.exists():
            transcript_data = json.load(open(transcript_file, encoding="utf-8"))

        try:
            result = translate_episode(slug, ep, transcript_data)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"    [OK] 保存到 {out_file.name}")
        except Exception as e:
            print(f"    [ERROR] {slug}: {e}")
            # 保存空结果，避免重试
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump({"slug": slug, "chapters_zh": [], "quotes_zh": [], "dialogue_zh": []}, f)

    print("\n[DONE] 翻译完成！")
    done_count = sum(1 for ep in episodes if (TRANS_DIR / f"{ep['slug']}.json").exists())
    print(f"成功翻译: {done_count}/{len(episodes)}")


if __name__ == "__main__":
    main()
