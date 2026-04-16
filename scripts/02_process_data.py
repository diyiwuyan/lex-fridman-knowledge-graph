"""
数据处理脚本：从原始 transcript JSON 提取结构化知识
- 嘉宾档案（出现次数、话题、金句）
- 主题标签（AI、物理、政治、哲学等）
- 关键词频率统计
- 交叉引用关系
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
import re
from pathlib import Path
from collections import defaultdict, Counter

BASE_DIR = Path(__file__).parent.parent
TRANSCRIPTS_DIR = BASE_DIR / "data" / "transcripts"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# 主题分类关键词映射
TOPIC_KEYWORDS = {
    "AI & Machine Learning": [
        "artificial intelligence", "machine learning", "neural network", "deep learning",
        "gpt", "llm", "language model", "openai", "chatgpt", "agi", "alignment",
        "transformer", "training", "inference", "model", "ai safety", "superintelligence",
        "robot", "automation", "algorithm", "data", "compute", "gpu", "nvidia",
        "deepseek", "gemini", "claude", "anthropic", "grok", "xai"
    ],
    "Physics & Cosmology": [
        "quantum", "physics", "relativity", "black hole", "universe", "spacetime",
        "particle", "string theory", "dark matter", "dark energy", "cosmology",
        "gravity", "entropy", "thermodynamics", "wave function", "superposition",
        "multiverse", "big bang", "neutron star", "galaxy", "telescope"
    ],
    "Mathematics": [
        "mathematics", "theorem", "proof", "algebra", "calculus", "topology",
        "number theory", "prime", "infinity", "set theory", "logic", "geometry",
        "probability", "statistics", "equation", "conjecture", "axiom"
    ],
    "Biology & Evolution": [
        "evolution", "biology", "dna", "gene", "cell", "organism", "species",
        "natural selection", "mutation", "protein", "brain", "neuroscience",
        "consciousness", "life", "origin of life", "bacteria", "virus", "immune"
    ],
    "Politics & Society": [
        "politics", "democracy", "government", "election", "president", "congress",
        "war", "military", "nato", "ukraine", "russia", "china", "israel",
        "freedom", "liberty", "constitution", "law", "justice", "policy",
        "capitalism", "socialism", "communism", "economy", "trade", "tariff"
    ],
    "Technology & Programming": [
        "programming", "software", "code", "developer", "startup", "silicon valley",
        "computer", "internet", "web", "app", "platform", "open source",
        "linux", "python", "javascript", "rust", "compiler", "operating system",
        "cybersecurity", "blockchain", "crypto", "bitcoin"
    ],
    "Philosophy & Religion": [
        "philosophy", "consciousness", "free will", "meaning", "purpose", "god",
        "religion", "ethics", "morality", "truth", "reality", "existence",
        "stoicism", "buddhism", "christianity", "islam", "meditation", "soul",
        "death", "immortality", "simulation", "determinism"
    ],
    "History & Civilization": [
        "history", "civilization", "empire", "war", "ancient", "medieval",
        "roman", "greek", "egypt", "mongol", "viking", "world war",
        "revolution", "colonialism", "slavery", "holocaust", "cold war",
        "archaeology", "anthropology", "culture", "society"
    ],
    "Space & Exploration": [
        "space", "nasa", "spacex", "rocket", "mars", "moon", "satellite",
        "astronaut", "orbit", "launch", "starship", "alien", "extraterrestrial",
        "ufo", "seti", "fermi paradox", "colonization", "telescope", "neuralink"
    ],
    "Business & Entrepreneurship": [
        "startup", "entrepreneur", "business", "company", "product", "market",
        "investor", "venture capital", "ipo", "revenue", "profit", "strategy",
        "leadership", "management", "innovation", "disruption", "scale"
    ],
    "Psychology & Human Nature": [
        "psychology", "behavior", "emotion", "motivation", "happiness", "love",
        "relationship", "trauma", "therapy", "mental health", "addiction",
        "memory", "learning", "creativity", "intelligence", "personality",
        "social", "culture", "identity", "ego", "subconscious"
    ],
    "Sports & Martial Arts": [
        "mma", "ufc", "boxing", "wrestling", "jiu-jitsu", "judo", "karate",
        "fighting", "athlete", "training", "competition", "champion", "sport",
        "fitness", "strength", "endurance", "performance"
    ],
    "Music & Arts": [
        "music", "guitar", "piano", "song", "album", "artist", "band",
        "composition", "melody", "rhythm", "jazz", "rock", "classical",
        "creativity", "art", "painting", "film", "movie", "storytelling"
    ],
    "Gaming & Virtual Worlds": [
        "video game", "esports", "virtual reality", "metaverse",
        "minecraft", "fortnite", "world of warcraft", "gta", "unreal engine",
        "game design", "game developer", "game studio", "gaming industry",
        "playstation", "xbox", "nintendo", "steam", "twitch", "speedrun",
        "overwatch", "diablo", "blizzard", "rockstar games", "valve"
    ],
}


def classify_topics(text: str) -> list[str]:
    """根据文本内容分类主题"""
    text_lower = text.lower()
    topic_scores = {}
    
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(text_lower.count(kw) for kw in keywords)
        if score > 0:
            topic_scores[topic] = score
    
    # 返回得分最高的前5个主题（提高阈值减少误分类）
    sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_topics[:5] if t[1] >= 8]


# 噪声词：这些词出现在 speakers 列表里但不是真实嘉宾名
NOISE_SPEAKERS = {
    "introduction", "about lex fridman", "chapters", "sponsors",
    "outro", "intro", "advertisement", "transcript", "summary",
    "timestamps", "links", "support", "follow", "subscribe",
}


# 已知缩写词，保持全大写
KNOWN_ABBREVIATIONS = {"dhh", "rfk", "ai", "sota", "mma", "ufc", "gpt", "llm"}


def slug_to_title(slug: str) -> str:
    """将 slug 转换为可读的 episode 标题
    例如: elon-musk-4 -> Elon Musk #4
         andrew-huberman -> Andrew Huberman
         dhh-david-heinemeier-hansson -> DHH David Heinemeier Hansson
    """
    # 去掉 -transcript 后缀
    s = slug.replace("-transcript", "")

    # 检测末尾数字（表示第几次访谈），但排除年份格式（4位数字）
    m = re.match(r'^(.+?)-(\d{1,2})$', s)
    if m:
        base, num = m.group(1), m.group(2)
        words = [w.upper() if w in KNOWN_ABBREVIATIONS else w.capitalize()
                 for w in base.split("-")]
        return f"{' '.join(words)} #{num}"

    # 普通 slug 转标题（处理缩写词）
    words = [w.upper() if w in KNOWN_ABBREVIATIONS else w.capitalize()
             for w in s.split("-")]
    return " ".join(words)


def is_likely_person_name(s: str) -> bool:
    """判断字符串是否像一个人名（而非章节标题）
    人名通常包含空格（名 + 姓），章节标题多为单词。
    """
    words = s.strip().split()
    return len(words) >= 2


def extract_guest_name(slug: str, speakers: list[str]) -> str:
    """从 slug 和说话人列表推断嘉宾名

    策略（优先级从高到低）：
    1. 用 slug 中的词匹配 speakers 列表（最可靠）
    2. 从 speakers 中找符合人名特征（多词）的非 Lex 项
    3. 从 slug 直接解析
    """
    # 去掉数字后缀和 -transcript，提取 slug 的核心词
    base_slug = slug.replace("-transcript", "")
    m = re.match(r'^(.+?)-(\d+)$', base_slug)
    if m:
        base_slug = m.group(1)
    slug_words = set(base_slug.lower().split("-")) - {"and", "the", "a", "of", "in"}

    # 过滤掉噪声词和 Lex 相关项
    clean = [
        s for s in speakers
        if s
        and s.lower() not in NOISE_SPEAKERS
        and "lex" not in s.lower()
        and len(s) > 2
    ]

    # 策略1：找 speakers 中与 slug 词匹配度最高的人名
    best_match = None
    best_score = 0
    for sp in clean:
        sp_words = set(sp.lower().split())
        score = len(sp_words & slug_words)
        if score > best_score:
            best_score = score
            best_match = sp
    if best_match and best_score > 0:
        return best_match

    # 策略2：找符合人名特征的（多词，如 "Elon Musk"）
    person_names = [s for s in clean if is_likely_person_name(s)]
    if person_names:
        return person_names[0]

    # 策略3：从 slug 直接解析
    s = base_slug
    # 处理 slug 中的 "and" 连接（如 "ezra-klein-and-derek-thompson"）
    s = re.sub(r'-and-', ' & ', s)
    return " ".join(w.capitalize() for w in s.split("-"))


def extract_key_quotes(dialogue: list[dict], max_quotes: int = 10) -> list[dict]:
    """提取关键引用（较长的、有深度的对话片段）"""
    quotes = []
    
    for d in dialogue:
        text = d.get("text", "")
        speaker = d.get("speaker", "")
        
        # 过滤：长度适中、不是 Lex 的问题
        if 100 < len(text) < 800 and speaker != "Lex Fridman":
            # 简单的"深度"评分：包含关键词
            depth_words = ["because", "therefore", "however", "actually", "fundamentally",
                          "essentially", "important", "believe", "think", "understand",
                          "realize", "truth", "meaning", "purpose", "future", "human"]
            score = sum(text.lower().count(w) for w in depth_words)
            quotes.append({
                "speaker": speaker,
                "text": text,
                "time": d.get("time"),
                "score": score
            })
    
    # 按得分排序，取前 N 条
    quotes.sort(key=lambda x: x["score"], reverse=True)
    return quotes[:max_quotes]


def process_all_transcripts():
    """处理所有 transcript，生成结构化数据"""
    
    transcript_files = list(TRANSCRIPTS_DIR.glob("*.json"))
    print(f"找到 {len(transcript_files)} 个 transcript 文件")
    
    all_episodes = []
    guest_appearances = defaultdict(list)  # 嘉宾 -> [episode slugs]
    topic_episodes = defaultdict(list)     # 主题 -> [episode slugs]
    
    for f in sorted(transcript_files):
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        
        if "error" in data:
            continue
        
        slug = data.get("slug", f.stem)
        full_text = data.get("full_text", "")
        dialogue = data.get("dialogue", [])
        speakers = data.get("speakers", [])
        raw_title = data.get("title", "")
        raw_guest = data.get("guest_name", "")
        source = data.get("source", "")

        # 分类主题
        topics = classify_topics(full_text)

        # 提取嘉宾名：HF 数据直接用 guest_name 字段，否则从 speakers 推断
        if raw_guest and raw_guest.lower() not in ("lex fridman", ""):
            guest_name = raw_guest
        else:
            guest_name = extract_guest_name(slug, speakers)

        # 生成展示用 title：
        # - HF 数据：raw_title 是节目副标题（如 "Pfizer CEO"），拼成 "Albert Bourla: Pfizer CEO"
        # - 官网数据：raw_title 是 "Lex Fridman"（网页 <title>），用 slug 生成
        if source == "huggingface_whisper" and raw_title and raw_title.lower() not in ("lex fridman", ""):
            title = f"{guest_name}: {raw_title}"
        else:
            title = slug_to_title(slug)
        
        # 提取关键引用
        key_quotes = extract_key_quotes(dialogue)
        
        # 统计词频（去除停用词）
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
                     "for", "of", "with", "by", "from", "is", "are", "was", "were",
                     "be", "been", "being", "have", "has", "had", "do", "does", "did",
                     "will", "would", "could", "should", "may", "might", "shall",
                     "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
                     "us", "them", "my", "your", "his", "its", "our", "their",
                     "this", "that", "these", "those", "what", "which", "who", "how",
                     "when", "where", "why", "if", "so", "as", "not", "no", "yes",
                     "just", "like", "very", "really", "also", "even", "still",
                     "about", "up", "out", "into", "than", "then", "there", "here",
                     "all", "any", "some", "one", "two", "three", "more", "most",
                     "can", "get", "go", "know", "think", "say", "see", "come",
                     "want", "need", "make", "take", "give", "look", "use", "find",
                     "tell", "ask", "seem", "feel", "try", "leave", "call", "keep",
                     "let", "begin", "show", "hear", "play", "run", "move", "live",
                     "believe", "hold", "bring", "happen", "write", "provide", "sit",
                     "stand", "lose", "pay", "meet", "include", "continue", "set",
                     "learn", "change", "lead", "understand", "watch", "follow",
                     "stop", "create", "speak", "read", "spend", "grow", "open",
                     "walk", "win", "offer", "remember", "love", "consider", "appear",
                     "buy", "wait", "serve", "die", "send", "expect", "build", "stay",
                     "fall", "cut", "reach", "kill", "remain", "suggest", "raise",
                     "pass", "sell", "require", "report", "decide", "pull", "break",
                     "lex", "fridman", "yeah", "okay", "right", "well", "mean",
                     "kind", "sort", "thing", "things", "way", "time", "people",
                     "something", "anything", "everything", "nothing", "someone",
                     "anyone", "everyone", "lot", "bit", "much", "many", "few",
                     "little", "big", "great", "good", "bad", "new", "old", "long",
                     "different", "same", "other", "another", "every", "each",
                     "both", "either", "neither", "such", "own", "back", "after",
                     "before", "during", "through", "between", "against", "without",
                     "within", "along", "following", "across", "behind", "beyond",
                     "plus", "except", "up", "down", "off", "over", "under",
                     "again", "further", "once", "now", "then", "always", "never",
                     "often", "sometimes", "usually", "already", "still", "yet",
                     "however", "therefore", "because", "although", "though",
                     "while", "since", "until", "unless", "whether", "both",
                     "either", "neither", "not", "nor", "so", "for", "and", "but",
                     "or", "yet", "so", "actually", "basically", "literally",
                     "probably", "maybe", "perhaps", "certainly", "definitely",
                     "absolutely", "exactly", "completely", "totally", "quite",
                     "rather", "pretty", "fairly", "almost", "nearly", "enough",
                     "too", "also", "only", "even", "just", "still", "already",
                     "soon", "later", "early", "late", "first", "last", "next",
                     "second", "third", "finally", "recently", "currently",
                     "today", "yesterday", "tomorrow", "year", "years", "day",
                     "days", "week", "weeks", "month", "months", "hour", "hours",
                     "minute", "minutes", "second", "seconds", "ago", "later",
                     "point", "fact", "case", "part", "place", "world", "life",
                     "work", "system", "problem", "question", "answer", "idea",
                     "number", "level", "process", "information", "example",
                     "sense", "reason", "result", "effect", "power", "hand",
                     "mind", "body", "head", "eye", "face", "word", "line",
                     "side", "end", "start", "beginning", "middle", "top",
                     "bottom", "left", "right", "front", "back", "inside",
                     "outside", "around", "above", "below", "between", "among",
                     "across", "through", "into", "onto", "upon", "within",
                     "without", "throughout", "toward", "towards", "against",
                     "despite", "except", "including", "regarding", "concerning",
                     "according", "based", "due", "given", "per", "via", "versus",
                     "whether", "whatever", "whenever", "wherever", "whoever",
                     "whichever", "however", "whatever", "whenever", "wherever",
                     "whoever", "whichever", "however", "whatever", "whenever",
                     "i'm", "you're", "he's", "she's", "it's", "we're", "they're",
                     "i've", "you've", "we've", "they've", "i'd", "you'd", "he'd",
                     "she'd", "we'd", "they'd", "i'll", "you'll", "he'll", "she'll",
                     "we'll", "they'll", "isn't", "aren't", "wasn't", "weren't",
                     "haven't", "hasn't", "hadn't", "won't", "wouldn't", "can't",
                     "couldn't", "shouldn't", "don't", "doesn't", "didn't",
                     "that's", "there's", "here's", "what's", "who's", "how's",
                     "let's", "it'll", "that'll", "there'll", "here'll",
                     "gonna", "wanna", "gotta", "kinda", "sorta", "lotta",
                     "cause", "cuz", "cos", "tho", "thru", "thats", "youre",
                     "im", "ive", "id", "ill", "hes", "shes", "its", "were",
                     "theyre", "theyve", "theyd", "theyll", "isnt", "arent",
                     "wasnt", "werent", "havent", "hasnt", "hadnt", "wont",
                     "wouldnt", "cant", "couldnt", "shouldnt", "dont", "doesnt",
                     "didnt", "thats", "theres", "heres", "whats", "whos",
                     "hows", "lets", "itll", "thatll", "therell", "herell",
                     "ve", "re", "ll", "d", "s", "t", "m", "n"}
        
        words = re.findall(r'\b[a-z]{3,}\b', full_text.lower())
        word_freq = Counter(w for w in words if w not in stop_words)
        top_keywords = [w for w, _ in word_freq.most_common(30)]
        
        episode_data = {
            "slug": slug,
            "title": title,
            "episode_num": data.get("episode_num"),
            "guest_name": guest_name,
            "speakers": speakers,
            "topics": topics,
            "chapters": data.get("chapters", []),
            "key_quotes": key_quotes,
            "top_keywords": top_keywords,
            "word_count": data.get("word_count", 0),
            "url": data.get("url", ""),
            "transcript_url": data.get("url", ""),
        }
        
        all_episodes.append(episode_data)
        
        # 记录嘉宾出现
        guest_appearances[guest_name].append(slug)
        
        # 记录主题出现
        for topic in topics:
            topic_episodes[topic].append(slug)
        
        print(f"  [OK] {slug}: {guest_name} | {', '.join(topics[:2])}")
    
    # 保存处理后的 episode 数据
    episodes_file = PROCESSED_DIR / "episodes.json"
    with open(episodes_file, "w", encoding="utf-8") as f:
        json.dump(all_episodes, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVED] {len(all_episodes)} episodes -> {episodes_file}")
    
    # 生成嘉宾档案
    guests = {}
    for guest_name, slugs in guest_appearances.items():
        # 找到该嘉宾的所有 episode
        guest_episodes = [e for e in all_episodes if e["slug"] in slugs]
        
        # 合并所有主题
        all_topics = []
        for ep in guest_episodes:
            all_topics.extend(ep["topics"])
        topic_counter = Counter(all_topics)
        
        # 合并所有关键词
        all_keywords = []
        for ep in guest_episodes:
            all_keywords.extend(ep["top_keywords"])
        keyword_counter = Counter(all_keywords)
        
        # 收集所有金句
        all_quotes = []
        for ep in guest_episodes:
            all_quotes.extend(ep["key_quotes"])
        all_quotes.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        guests[guest_name] = {
            "name": guest_name,
            "episode_count": len(slugs),
            "episodes": slugs,
            "main_topics": [t for t, _ in topic_counter.most_common(5)],
            "top_keywords": [k for k, _ in keyword_counter.most_common(20)],
            "best_quotes": all_quotes[:5],
        }
    
    guests_file = PROCESSED_DIR / "guests.json"
    with open(guests_file, "w", encoding="utf-8") as f:
        json.dump(guests, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] {len(guests)} guests -> {guests_file}")
    
    # 生成主题档案
    topics_data = {}
    for topic, slugs in topic_episodes.items():
        topic_eps = [e for e in all_episodes if e["slug"] in slugs]
        
        # 该主题下的所有关键词
        all_keywords = []
        for ep in topic_eps:
            all_keywords.extend(ep["top_keywords"])
        keyword_counter = Counter(all_keywords)
        
        # 该主题下的所有金句
        all_quotes = []
        for ep in topic_eps:
            all_quotes.extend(ep["key_quotes"])
        all_quotes.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        topics_data[topic] = {
            "name": topic,
            "episode_count": len(slugs),
            "episodes": slugs,
            "top_keywords": [k for k, _ in keyword_counter.most_common(20)],
            "best_quotes": all_quotes[:5],
        }
    
    topics_file = PROCESSED_DIR / "topics.json"
    with open(topics_file, "w", encoding="utf-8") as f:
        json.dump(topics_data, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] {len(topics_data)} topics -> {topics_file}")
    
    # 生成统计摘要
    summary = {
        "total_episodes": len(all_episodes),
        "total_guests": len(guests),
        "total_topics": len(topics_data),
        "total_words": sum(e["word_count"] for e in all_episodes),
        "avg_words_per_episode": int(sum(e["word_count"] for e in all_episodes) / max(len(all_episodes), 1)),
        "top_guests": sorted(
            [(g, d["episode_count"]) for g, d in guests.items()],
            key=lambda x: x[1], reverse=True
        )[:20],
        "top_topics": sorted(
            [(t, d["episode_count"]) for t, d in topics_data.items()],
            key=lambda x: x[1], reverse=True
        ),
    }
    
    summary_file = PROCESSED_DIR / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n[SUMMARY]")
    print(f"   Total episodes: {summary['total_episodes']}")
    print(f"   Total guests: {summary['total_guests']}")
    print(f"   Total words: {summary['total_words']:,}")
    print(f"   Avg words/episode: {summary['avg_words_per_episode']:,}")
    
    return all_episodes, guests, topics_data


if __name__ == "__main__":
    process_all_transcripts()
