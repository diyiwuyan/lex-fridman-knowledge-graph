"""
从 missing_slugs.json 批量生成所有缺失 episode 的中文总结
- 读取 data/transcripts/<slug>.json 构建 prompt
- 调用 catdesk CLI ask
- 写入 data/summaries/<slug>.json
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
TRANSCRIPTS_DIR = BASE_DIR / "data" / "transcripts"
SUMMARIES_DIR = BASE_DIR / "data" / "summaries"
MISSING_FILE = BASE_DIR / "data" / "missing_slugs.json"
SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

CATDESK_EXE = r"D:\program\CatPaw Desk\CatPaw Desk.exe"
CATDESK_CLI = r"D:\program\CatPaw Desk\resources\cli\catpaw-cli.js"


def call_llm(prompt: str) -> str:
    tmp = BASE_DIR / "data" / "_tmp_prompt.txt"
    tmp.write_text(prompt, encoding="utf-8")
    env = os.environ.copy()
    env["ELECTRON_RUN_AS_NODE"] = "1"
    try:
        result = subprocess.run(
            [CATDESK_EXE, CATDESK_CLI, "ask", "--file", str(tmp), "--no-stream"],
            capture_output=True, text=True, encoding="utf-8", timeout=120, env=env,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        result2 = subprocess.run(
            [CATDESK_EXE, CATDESK_CLI, "ask", "--file", str(tmp)],
            capture_output=True, text=True, encoding="utf-8", timeout=120, env=env,
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
    lines = []
    for d in dialogue:
        speaker = d.get("speaker", "")
        text = d.get("text", "").strip()
        if text:
            lines.append(f"{speaker}: {text}" if speaker else text)
    return "\n".join(lines)


def guess_guest_name(slug: str) -> str:
    """从 slug 猜测嘉宾名字"""
    name = slug.replace("-", " ").title()
    # 去掉末尾的数字
    name = re.sub(r'\s+\d+$', '', name)
    return name


def build_prompt(guest_name: str, slug: str, full_text: str, chapters: list) -> str:
    text_sample = full_text[:8000]
    chapters_str = ""
    if chapters:
        chapters_str = "\n章节目录：\n" + "\n".join(
            f"- {c.get('title', '')}" for c in chapters[:20] if c.get("title")
        )
    return f"""你是一个专业的播客内容分析师。请根据以下 Lex Fridman 播客访谈内容，生成一份结构化的中文总结。

访谈信息：
- 嘉宾：{guest_name}
- Slug：{slug}
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
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {}


def is_valid_summary(slug: str) -> bool:
    f = SUMMARIES_DIR / f"{slug}.json"
    if not f.exists():
        return False
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return d.get("error") != "generation_failed" and bool(d.get("title_zh") or d.get("summary_zh"))
    except:
        return False


def generate_one(slug: str) -> dict:
    tf = TRANSCRIPTS_DIR / f"{slug}.json"
    if not tf.exists():
        print(f"    [SKIP] 无 transcript 文件")
        return {}

    td = json.loads(tf.read_text(encoding="utf-8"))
    dialogue = td.get("dialogue", [])
    chapters = td.get("chapters", [])

    if not dialogue:
        print(f"    [SKIP] dialogue 为空")
        return {}

    full_text = get_full_text(dialogue)
    if len(full_text) < 200:
        print(f"    [SKIP] 文本太短 ({len(full_text)} chars)")
        return {}

    # 尝试从 transcript meta 获取嘉宾名
    guest_name = td.get("guest", td.get("guest_name", guess_guest_name(slug)))
    prompt = build_prompt(guest_name, slug, full_text, chapters)

    print(f"    调用 LLM（{len(full_text)} chars）...")
    response = call_llm(prompt)
    if not response:
        return {}

    data = parse_json_from_response(response)
    if not data:
        print(f"    [WARN] JSON 解析失败，响应前200字: {response[:200]}")
        return {}

    data["slug"] = slug
    data["guest"] = guest_name
    return data


def main():
    missing_slugs = json.loads(MISSING_FILE.read_text(encoding="utf-8"))

    # 再次过滤：跳过已经有有效 summary 的
    todo = [s for s in missing_slugs if not is_valid_summary(s)]
    total = len(todo)
    print(f"待处理: {total} 个 episode\n")

    success = 0
    fail = 0

    for i, slug in enumerate(todo, 1):
        print(f"[{i:3d}/{total}] {slug}...")

        try:
            result = generate_one(slug)
            out_file = SUMMARIES_DIR / f"{slug}.json"

            if result:
                out_file.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                print(f"    [OK] {result.get('title_zh', '(无标题)')}")
                success += 1
            else:
                out_file.write_text(
                    json.dumps({"slug": slug, "error": "generation_failed"}, ensure_ascii=False),
                    encoding="utf-8",
                )
                print(f"    [FAIL] 写 error 标记")
                fail += 1
        except Exception as e:
            print(f"    [ERROR] {e}")
            fail += 1

        time.sleep(0.2)

        # 每 50 个报告一次进度
        if i % 50 == 0:
            print(f"\n--- 进度 {i}/{total}，成功 {success}，失败 {fail} ---\n")

    print(f"\n[DONE] 成功: {success}，失败: {fail}")
    valid_total = sum(1 for p in SUMMARIES_DIR.glob("*.json") if is_valid_summary(p.stem))
    print(f"data/summaries/ 总有效文件数: {valid_total}")


if __name__ == "__main__":
    main()
