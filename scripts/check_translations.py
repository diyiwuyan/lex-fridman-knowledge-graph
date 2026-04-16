import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path

trans_dir = Path("data/translations")
transcript_dir = Path("data/transcripts")

files = list(trans_dir.glob("*.json"))
print(f"翻译文件数: {len(files)}")

# 检查几个典型 episode 的翻译条数 vs 原始对话条数
samples = ["albert-bourla", "ben-goertzel", "elon-musk", "alex-filippenko"]
for slug in samples:
    tf = trans_dir / f"{slug}.json"
    sf = transcript_dir / f"{slug}.json"
    if tf.exists() and sf.exists():
        trans = json.loads(tf.read_text(encoding="utf-8"))
        orig = json.loads(sf.read_text(encoding="utf-8"))
        n_trans = len(trans.get("dialogue_zh", []))
        n_orig = len(orig.get("dialogue", []))
        print(f"  {slug}: 翻译 {n_trans} 条 / 原始 {n_orig} 条")
    elif sf.exists():
        orig = json.loads(sf.read_text(encoding="utf-8"))
        n_orig = len(orig.get("dialogue", []))
        print(f"  {slug}: 无翻译文件 / 原始 {n_orig} 条")

# 统计所有翻译文件的对话翻译条数分布
counts = []
for f in files:
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        n = len(data.get("dialogue_zh", []))
        counts.append((f.stem, n))
    except:
        pass

counts.sort(key=lambda x: x[1])
print(f"\n翻译条数最少的5个:")
for slug, n in counts[:5]:
    print(f"  {slug}: {n} 条")
print(f"\n翻译条数最多的5个:")
for slug, n in counts[-5:]:
    print(f"  {slug}: {n} 条")

total_trans = sum(n for _, n in counts)
print(f"\n总翻译对话条数: {total_trans:,}")
