"""
批量生成每期访谈的结构化总结（中文）
- 直接调用当前 LLM（通过 catdesk CLI ask 命令）
- 结果缓存到 data/summaries/<slug>.json
- 支持断点续传
"""

import json
import sys
import io
import time
import subprocess
import re
import os
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TRANSCRIPTS_DIR = BASE_DIR / "data" / "transcripts"
SUMMARIES_DIR = BASE_DIR / "data" / "summaries"
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

# catdesk CLI 路径
CATDESK_EXE = r"D:\program\CatPaw Desk\CatPaw Desk.exe"
CATDESK_CLI = r"D:\program\CatPaw Desk\resources\cli\catpaw-cli.js"


def call_llm(prompt: str) -> str:
    """通过 catdesk CLI 调用 LLM"""
    tmp = BASE_DIR / "data" / "_tmp_prompt.txt"
    tmp.write_text(prompt, encoding="utf-8")

    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"

    try:
        result = subprocess.run(
            [CATDESK_EXE, CATDESK_CLI, "ask", "--file", str(tmp), "--no-stream"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        # fallback: 尝试不带 --no-stream
        result2 = subprocess.run(
            [CATDESK_EXE, CATDESK_CLI, "ask", "--file", str(tmp)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            env=env,
        )
        if result2.returncode == 0:
            return result2.stdout.strip()
        print(f"    [WARN] LLM stderr: {(result.stderr or result2.stderr)[:300]}")
        return ""
    except subprocess.TimeoutExpired:
        print("    [WARN] LLM timeout (120s)")
        return ""
    except Exception as e:
        print(f"    [WARN] LLM exception: {e}")
        return ""
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def get_full_text(dialogue: list) -> str:
    """把 dialogue 列表拼成纯文本"""
    lines = []
    for d in dialogue:
        speaker = d.get("speaker", "")
        text = d.get("text", "").strip()
        if text:
            lines.append(f"{speaker}: {text}" if speaker else text)
    return "\n".join(lines)


def build_prompt(guest_name: str, title: str, full_text: str, chapters: list) -> str:
    # 取前 8000 字符（约 1500 词）
    text_sample = full_text[:8000]

    chapters_str = ""
    if chapters:
        chapters_str = "\n章节目录：\n" + "\n".join(
            f"- {c.get('title', '')}" for c in chapters[:20] if c.get("title")
        )

    return f"""你是一个专业的播客内容分析师。请根据以下 Lex Fridman 播客访谈内容，生成一份结构化的中文总结。

访谈信息：
- 嘉宾：{guest_name}
- 节目标题：{title}
{chapters_str}

访谈文字稿（节选，前8000字符）：
{text_sample}

请严格按照以下 JSON 格式输出，不要有任何其他文字，不要有 markdown 代码块标记：

{{
  "title_zh": "简洁的中文标题（10-20字，概括本期核心话题）",
  "summary_zh": "2-3句话的总体概述，说明这期访谈讨论了什么、嘉宾是谁、核心价值在哪里",
  "key_points_zh": [
    "核心观点1（1-2句，具体有料）",
    "核心观点2",
    "核心观点3",
    "核心观点4",
    "核心观点5"
  ],
  "topics_zh": ["话题标签1", "话题标签2", "话题标签3"],
  "notable_quotes_zh": [
    "值得记录的金句1（翻译自原文，格式：说话人：内容）",
    "金句2",
    "金句3"
  ],
  "guest_intro_zh": "嘉宾简介：1-2句介绍嘉宾是谁、做什么的"
}}"""


def parse_json_from_response(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    text = text.strip()
    # 直接解析
    try:
        return json.loads(text)
    except Exception:
        pass
    # 提取 ```json ... ``` 块
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 提取第一个完整 { ... }
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def generate_summary(slug: str, ep: dict) -> dict:
    guest_name = ep.get("guest_name", slug)
    title = ep.get("title", slug)

    transcript_file = TRANSCRIPTS_DIR / f"{slug}.json"
    if not transcript_file.exists():
        print(f"    [SKIP] 无 transcript 文件")
        return {}

    td = json.loads(transcript_file.read_text(encoding="utf-8"))
    dialogue = td.get("dialogue", [])
    chapters = td.get("chapters", ep.get("chapters", []))

    if not dialogue:
        print(f"    [SKIP] dialogue 为空")
        return {}

    full_text = get_full_text(dialogue)
    if len(full_text) < 200:
        print(f"    [SKIP] 文本太短 ({len(full_text)} chars)")
        return {}

    prompt = build_prompt(guest_name, title, full_text, chapters)

    print(f"    调用 LLM（文本 {len(full_text)} chars）...")
    response = call_llm(prompt)

    if not response:
        return {}

    data = parse_json_from_response(response)
    if not data:
        print(f"    [WARN] JSON 解析失败，原始响应前200字: {response[:200]}")
        return {}

    data["slug"] = slug
    data["guest"] = guest_name
    data["title_en"] = title
    return data


def main():
    # 支持命令行参数：python 06_generate_summaries.py [slug1 slug2 ...]
    target_slugs = sys.argv[1:] if len(sys.argv) > 1 else None

    episodes = json.loads((PROCESSED_DIR / "episodes.json").read_text(encoding="utf-8"))

    if target_slugs:
        episodes = [ep for ep in episodes if ep["slug"] in target_slugs]
        print(f"指定模式：处理 {len(episodes)} 个 episode")
    else:
        print(f"共 {len(episodes)} 个 episode")
        done = sum(1 for ep in episodes if (SUMMARIES_DIR / f"{ep['slug']}.json").exists())
        print(f"已完成: {done}，剩余: {len(episodes) - done}\n")

    for i, ep in enumerate(episodes, 1):
        slug = ep["slug"]
        out_file = SUMMARIES_DIR / f"{slug}.json"

        if out_file.exists() and not target_slugs:
            print(f"[{i:3d}/{len(episodes)}] SKIP {slug}")
            continue

        print(f"[{i:3d}/{len(episodes)}] 生成 {slug} ({ep.get('guest_name', '')})...")

        try:
            result = generate_summary(slug, ep)
            if result:
                out_file.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"    [OK] {result.get('title_zh', '(无标题)')}")
            else:
                # 写 error 标记，避免重复尝试
                out_file.write_text(
                    json.dumps(
                        {"slug": slug, "guest": ep.get("guest_name", ""), "error": "generation_failed"},
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                print(f"    [FAIL] 生成失败，写 error 标记")
        except Exception as e:
            print(f"    [ERROR] {e}")

        time.sleep(0.3)

    print("\n[DONE]")
    done_count = sum(1 for ep in episodes if (SUMMARIES_DIR / f"{ep['slug']}.json").exists())
    print(f"完成: {done_count}/{len(episodes)}")


if __name__ == "__main__":
    main()
