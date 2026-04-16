"""
网站生成脚本：将处理后的数据构建成静态知识图谱网站
参考巴菲特项目风格，生成精美的可交互知识库（中文界面）
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
TRANSCRIPTS_DIR = BASE_DIR / "data" / "transcripts"
TRANS_DIR = BASE_DIR / "data" / "translations"
SUMMARIES_DIR = BASE_DIR / "data" / "summaries"
SITE_DIR = BASE_DIR / "site"
SITE_DIR.mkdir(parents=True, exist_ok=True)


def load_translation(slug: str) -> dict:
    """加载某个 episode 的翻译缓存，不存在则返回空字典"""
    f = TRANS_DIR / f"{slug}.json"
    if f.exists():
        try:
            return json.load(open(f, encoding="utf-8"))
        except Exception:
            pass
    return {"chapters_zh": [], "quotes_zh": [], "dialogue_zh": []}


def load_summary(slug: str) -> dict:
    """加载某个 episode 的 AI 总结，不存在或有 error 则返回空字典"""
    f = SUMMARIES_DIR / f"{slug}.json"
    if f.exists():
        try:
            data = json.load(open(f, encoding="utf-8"))
            if data.get("error"):
                return {}
            return data
        except Exception:
            pass
    return {}

# 主题颜色映射
TOPIC_COLORS = {
    "AI & Machine Learning": "#6366f1",
    "Physics & Cosmology": "#8b5cf6",
    "Mathematics": "#a855f7",
    "Biology & Evolution": "#22c55e",
    "Politics & Society": "#ef4444",
    "Technology & Programming": "#3b82f6",
    "Philosophy & Religion": "#f59e0b",
    "History & Civilization": "#d97706",
    "Space & Exploration": "#06b6d4",
    "Business & Entrepreneurship": "#10b981",
    "Psychology & Human Nature": "#ec4899",
    "Sports & Martial Arts": "#f97316",
    "Music & Arts": "#e879f9",
    "Gaming & Virtual Worlds": "#14b8a6",
}

# 主题中文名映射
TOPIC_ZH = {
    "AI & Machine Learning": "AI 与机器学习",
    "Physics & Cosmology": "物理与宇宙学",
    "Mathematics": "数学",
    "Biology & Evolution": "生物与进化",
    "Politics & Society": "政治与社会",
    "Technology & Programming": "技术与编程",
    "Philosophy & Religion": "哲学与宗教",
    "History & Civilization": "历史与文明",
    "Space & Exploration": "太空与探索",
    "Business & Entrepreneurship": "商业与创业",
    "Psychology & Human Nature": "心理与人性",
    "Sports & Martial Arts": "体育与武术",
    "Music & Arts": "音乐与艺术",
    "Gaming & Virtual Worlds": "游戏与虚拟世界",
}

DEFAULT_COLOR = "#64748b"


def get_topic_color(topic: str) -> str:
    return TOPIC_COLORS.get(topic, DEFAULT_COLOR)


def topic_zh(name: str) -> str:
    """返回主题的中文名，没有则返回原名"""
    return TOPIC_ZH.get(name, name)


def escape_html(text: str) -> str:
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def slug_to_id(slug: str) -> str:
    return re.sub(r'[^a-z0-9-]', '-', slug.lower())


def load_data():
    episodes_file = PROCESSED_DIR / "episodes.json"
    guests_file = PROCESSED_DIR / "guests.json"
    topics_file = PROCESSED_DIR / "topics.json"
    summary_file = PROCESSED_DIR / "summary.json"

    with open(episodes_file, "r", encoding="utf-8") as f:
        episodes = json.load(f)
    with open(guests_file, "r", encoding="utf-8") as f:
        guests = json.load(f)
    with open(topics_file, "r", encoding="utf-8") as f:
        topics = json.load(f)
    with open(summary_file, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # 建立 slug -> episode 映射
    ep_map = {e["slug"]: e for e in episodes}

    return episodes, guests, topics, summary, ep_map


CSS = """
:root {
  --bg: #0f0f13;
  --bg2: #16161d;
  --bg3: #1e1e2a;
  --border: #2a2a3a;
  --text: #e2e8f0;
  --text2: #94a3b8;
  --text3: #64748b;
  --accent: #6366f1;
  --accent2: #818cf8;
  --gold: #f59e0b;
  --green: #22c55e;
  --red: #ef4444;
  --radius: 12px;
  --shadow: 0 4px 24px rgba(0,0,0,0.4);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  min-height: 100vh;
}

a { color: var(--accent2); text-decoration: none; }
a:hover { color: var(--accent); text-decoration: underline; }

/* Layout */
.layout { display: flex; min-height: 100vh; }

.sidebar {
  width: 260px;
  min-width: 260px;
  background: var(--bg2);
  border-right: 1px solid var(--border);
  padding: 24px 0;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-logo {
  padding: 0 20px 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}

.sidebar-logo h1 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.3;
}

.sidebar-logo p {
  font-size: 12px;
  color: var(--text3);
  margin-top: 4px;
}

.sidebar-section {
  padding: 8px 20px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text3);
  margin-top: 12px;
}

.sidebar-link {
  display: block;
  padding: 8px 20px;
  font-size: 14px;
  color: var(--text2);
  border-left: 3px solid transparent;
  transition: all 0.15s;
}

.sidebar-link:hover, .sidebar-link.active {
  color: var(--text);
  background: var(--bg3);
  border-left-color: var(--accent);
  text-decoration: none;
}

.sidebar-link .count {
  float: right;
  font-size: 11px;
  color: var(--text3);
  background: var(--bg3);
  padding: 1px 6px;
  border-radius: 10px;
}

.main { flex: 1; overflow-x: hidden; }

/* Hero */
.hero {
  background: linear-gradient(135deg, #0f0f13 0%, #1a1a2e 50%, #16213e 100%);
  padding: 60px 48px;
  border-bottom: 1px solid var(--border);
  position: relative;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(ellipse at center, rgba(99,102,241,0.08) 0%, transparent 60%);
  pointer-events: none;
}

.hero h1 {
  font-size: 42px;
  font-weight: 800;
  background: linear-gradient(135deg, #e2e8f0, #818cf8);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
  line-height: 1.2;
}

.hero p {
  font-size: 18px;
  color: var(--text2);
  max-width: 600px;
  margin-bottom: 32px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
  max-width: 700px;
}

.stat-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 20px;
  text-align: center;
}

.stat-card .num {
  font-size: 28px;
  font-weight: 700;
  color: var(--accent2);
  display: block;
}

.stat-card .label {
  font-size: 12px;
  color: var(--text3);
  margin-top: 4px;
}

/* Content area */
.content { padding: 40px 48px; max-width: 1200px; }

.section-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.section-desc {
  font-size: 14px;
  color: var(--text2);
  margin-bottom: 28px;
}

/* Cards */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 40px;
}

.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  transition: all 0.2s;
  cursor: pointer;
}

.card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
  line-height: 1.4;
}

.card-meta {
  font-size: 12px;
  color: var(--text3);
  margin-bottom: 10px;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 20px;
  font-weight: 500;
  white-space: nowrap;
}

/* Episode list */
.ep-list { margin-bottom: 40px; }

.ep-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid var(--border);
  transition: all 0.15s;
}

.ep-item:hover { background: rgba(255,255,255,0.02); }

.ep-num {
  font-size: 12px;
  color: var(--text3);
  min-width: 40px;
  padding-top: 2px;
  font-family: monospace;
}

.ep-info { flex: 1; }

.ep-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.ep-guest {
  font-size: 13px;
  color: var(--accent2);
  margin-bottom: 6px;
}

.ep-topics { display: flex; flex-wrap: wrap; gap: 4px; }

.ep-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-shrink: 0;
}

.btn {
  font-size: 12px;
  padding: 5px 12px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg3);
  color: var(--text2);
  cursor: pointer;
  transition: all 0.15s;
  text-decoration: none;
  display: inline-block;
}

.btn:hover {
  border-color: var(--accent);
  color: var(--accent2);
  text-decoration: none;
}

.btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.btn-primary:hover {
  background: var(--accent2);
  border-color: var(--accent2);
  color: white;
}

/* Guest page */
.guest-header {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 32px;
  padding: 28px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.guest-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.guest-name { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
.guest-meta { font-size: 14px; color: var(--text2); }

/* Quote */
.quote-block {
  background: var(--bg2);
  border-left: 3px solid var(--accent);
  border-radius: 0 var(--radius) var(--radius) 0;
  padding: 16px 20px;
  margin: 12px 0;
}

.quote-text {
  font-size: 14px;
  color: var(--text);
  line-height: 1.7;
  font-style: italic;
}

.quote-meta {
  font-size: 12px;
  color: var(--text3);
  margin-top: 8px;
}

/* Bilingual translation styles */
.quote-zh {
  font-size: 13px;
  color: #94a3b8;
  line-height: 1.7;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #2a2a3a;
  font-style: normal;
}

.zh-trans {
  color: #64748b;
  font-size: 0.9em;
}

.dialogue-box {
  background: #16161d;
  border: 1px solid #2a2a3a;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 32px;
}

.dialogue-item {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #1e1e2e;
}

.dialogue-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.dialogue-speaker {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 4px;
}

.dialogue-time {
  color: #475569;
  font-weight: 400;
}

.dialogue-en {
  font-size: 14px;
  color: #cbd5e1;
  line-height: 1.7;
}

.dialogue-zh {
  font-size: 13px;
  color: #64748b;
  line-height: 1.7;
  margin-top: 6px;
  padding-left: 10px;
  border-left: 2px solid #2a2a3a;
}

.trans-btn {
  float: right;
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 4px;
  border: 1px solid #2a2a3a;
  background: transparent;
  color: #475569;
  cursor: pointer;
  margin-top: 2px;
  transition: all 0.15s;
}
.trans-btn:hover { background: #1e1e2a; color: #818cf8; border-color: #818cf8; }

/* Topic page */
.topic-header {
  padding: 28px;
  border-radius: var(--radius);
  margin-bottom: 28px;
  color: white;
}

.topic-header h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; }
.topic-header p { font-size: 14px; opacity: 0.8; }

/* Search */
.search-box {
  width: 100%;
  padding: 12px 16px;
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-size: 15px;
  margin-bottom: 24px;
  outline: none;
  transition: border-color 0.15s;
}

.search-box:focus { border-color: var(--accent); }
.search-box::placeholder { color: var(--text3); }

/* Keyword cloud */
.keyword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0;
}

.keyword-tag {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  background: var(--bg3);
  border: 1px solid var(--border);
  color: var(--text2);
  cursor: pointer;
  transition: all 0.15s;
}

.keyword-tag:hover {
  border-color: var(--accent);
  color: var(--accent2);
}

/* Chapters */
.chapter-list { margin: 16px 0; }

.chapter-item {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.chapter-time {
  color: var(--accent2);
  font-family: monospace;
  min-width: 60px;
  flex-shrink: 0;
}

.chapter-title { color: var(--text2); }

/* Breadcrumb */
.breadcrumb {
  font-size: 13px;
  color: var(--text3);
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.breadcrumb a { color: var(--text3); }
.breadcrumb a:hover { color: var(--text2); }
.breadcrumb span { color: var(--text3); }

/* Responsive */
@media (max-width: 768px) {
  .sidebar { display: none; }
  .hero { padding: 32px 20px; }
  .hero h1 { font-size: 28px; }
  .content { padding: 24px 20px; }
  .card-grid { grid-template-columns: 1fr; }
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text3); }

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-in { animation: fadeIn 0.3s ease; }

/* Filter bar */
.filter-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.filter-btn {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12px;
  border: 1px solid var(--border);
  background: var(--bg2);
  color: var(--text2);
  cursor: pointer;
  transition: all 0.15s;
}

.filter-btn:hover, .filter-btn.active {
  border-color: var(--accent);
  color: var(--accent2);
  background: rgba(99,102,241,0.1);
}

/* Progress bar */
.word-bar {
  height: 3px;
  background: var(--border);
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}

.word-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--accent2));
  border-radius: 2px;
}
"""

JS = """
// Search functionality
function initSearch(inputId, listId, itemClass) {
  const input = document.getElementById(inputId);
  if (!input) return;
  
  input.addEventListener('input', function() {
    const query = this.value.toLowerCase().trim();
    const items = document.querySelectorAll('.' + itemClass);
    
    items.forEach(item => {
      const text = item.textContent.toLowerCase();
      item.style.display = (!query || text.includes(query)) ? '' : 'none';
    });
  });
}

// Filter by topic
function filterByTopic(topic) {
  const btns = document.querySelectorAll('.filter-btn');
  btns.forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  
  const items = document.querySelectorAll('.ep-item, .card');
  items.forEach(item => {
    if (!topic || item.dataset.topics?.includes(topic)) {
      item.style.display = '';
    } else {
      item.style.display = 'none';
    }
  });
}

// ── 客户端实时翻译（Google Translate 免费接口）──────────────────
async function translateText(text) {
  try {
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh-CN&dt=t&q=${encodeURIComponent(text)}`;
    const res = await fetch(url);
    const data = await res.json();
    return data[0].map(s => s[0]).join('');
  } catch(e) {
    return '';
  }
}

async function translateOne(btn) {
  const item = btn.closest('.dialogue-item');
  const enEl = item.querySelector('.dialogue-en');
  let zhEl = item.querySelector('.dialogue-zh');
  if (zhEl && zhEl.textContent.trim()) { zhEl.style.display = zhEl.style.display === 'none' ? '' : 'none'; return; }
  btn.textContent = '…';
  btn.disabled = true;
  const zh = await translateText(enEl.textContent);
  if (!zhEl) { zhEl = document.createElement('div'); zhEl.className = 'dialogue-zh'; item.appendChild(zhEl); }
  zhEl.textContent = zh;
  btn.textContent = '译';
  btn.disabled = false;
}

async function translateAll() {
  // 先展开所有折叠内容
  const moreDiv = document.getElementById('dialogue-more');
  if (moreDiv) moreDiv.style.display = 'block';
  const expandBtn = document.querySelector('[onclick*="dialogue-more"]');
  if (expandBtn) expandBtn.style.display = 'none';

  const btn = document.getElementById('translate-all-btn');
  const items = document.querySelectorAll('.dialogue-item');
  btn.disabled = true;
  let done = 0;
  for (const item of items) {
    let zhEl = item.querySelector('.dialogue-zh');
    if (zhEl && zhEl.textContent.trim()) { done++; continue; }
    const enEl = item.querySelector('.dialogue-en');
    if (!enEl) continue;
    const zh = await translateText(enEl.textContent);
    if (!zhEl) { zhEl = document.createElement('div'); zhEl.className = 'dialogue-zh'; item.appendChild(zhEl); }
    zhEl.textContent = zh;
    done++;
    btn.textContent = `翻译中 ${done}/${items.length}…`;
    await new Promise(r => setTimeout(r, 80)); // 限速避免被封
  }
  btn.textContent = `✓ 全部翻译完成 (${done} 条)`;
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function() {
  initSearch('search-input', 'ep-list', 'ep-item');
  initSearch('guest-search', 'guest-grid', 'card');
  
  // Highlight current page in sidebar
  const currentPath = window.location.pathname;
  document.querySelectorAll('.sidebar-link').forEach(link => {
    if (link.getAttribute('href') === currentPath || 
        link.getAttribute('href') === currentPath.replace('/index.html', '/')) {
      link.classList.add('active');
    }
  });

  // 给每条对话加单条翻译按钮
  document.querySelectorAll('.dialogue-item').forEach(item => {
    const zhEl = item.querySelector('.dialogue-zh');
    if (zhEl && zhEl.textContent.trim()) return; // 已有翻译，不加按钮
    const btn = document.createElement('button');
    btn.textContent = '译';
    btn.className = 'trans-btn';
    btn.onclick = () => translateOne(btn);
    item.appendChild(btn);
  });
});
"""


def build_sidebar(active_page="home", depth=1):
    """depth=0 表示根目录(index.html)，depth=1 表示子目录(episodes/guests/topics)"""
    prefix = "./" if depth == 0 else "../"
    return f"""
<nav class="sidebar">
  <div class="sidebar-logo">
    <h1>Lex Fridman<br>知识图谱</h1>
    <p>434 期节目 · 全文字幕</p>
  </div>
  
  <div class="sidebar-section">导航</div>
  <a href="{prefix}index.html" class="sidebar-link {'active' if active_page == 'home' else ''}">🏠 首页</a>
  <a href="{prefix}episodes/index.html" class="sidebar-link {'active' if active_page == 'episodes' else ''}">🎙️ 全部节目</a>
  <a href="{prefix}guests/index.html" class="sidebar-link {'active' if active_page == 'guests' else ''}">👤 嘉宾</a>
  <a href="{prefix}topics/index.html" class="sidebar-link {'active' if active_page == 'topics' else ''}">🏷️ 主题</a>
  
  <div class="sidebar-section">主题分类</div>
  <a href="{prefix}topics/ai-machine-learning.html" class="sidebar-link">🤖 AI 与机器学习</a>
  <a href="{prefix}topics/physics-cosmology.html" class="sidebar-link">⚛️ 物理与宇宙学</a>
  <a href="{prefix}topics/politics-society.html" class="sidebar-link">🏛️ 政治与社会</a>
  <a href="{prefix}topics/philosophy-religion.html" class="sidebar-link">🧠 哲学与宗教</a>
  <a href="{prefix}topics/history-civilization.html" class="sidebar-link">📜 历史与文明</a>
  <a href="{prefix}topics/technology-programming.html" class="sidebar-link">💻 技术与编程</a>
  <a href="{prefix}topics/space-exploration.html" class="sidebar-link">🚀 太空与探索</a>
  <a href="{prefix}topics/biology-evolution.html" class="sidebar-link">🧬 生物与进化</a>
</nav>
"""


def build_page(title, content, active_page="home", depth=1):
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_html(title)} - Lex Fridman 知识图谱</title>
  <style>{CSS}</style>
</head>
<body>
<div class="layout">
  {build_sidebar(active_page, depth=depth)}
  <main class="main">
    {content}
  </main>
</div>
<script>{JS}</script>
</body>
</html>"""


def build_home(episodes, guests, topics, summary):
    total_words = summary.get("total_words", 0)
    total_eps = summary.get("total_episodes", 0)
    total_guests = summary.get("total_guests", 0)
    total_topics = len(topics)

    # 最新 episodes（前12个）
    recent_eps = episodes[:12]
    recent_cards = ""
    for ep in recent_eps:
        topics_html = "".join(
            f'<span class="tag" style="background:{get_topic_color(t)}22;color:{get_topic_color(t)};border:1px solid {get_topic_color(t)}44">{topic_zh(t)}</span>'
            for t in ep.get("topics", [])[:2]
        )
        recent_cards += f"""
<a href="episodes/{ep['slug']}.html" class="card" style="text-decoration:none">
  <div class="card-title">{escape_html(ep.get('title', ''))}</div>
  <div class="card-meta">嘉宾：{escape_html(ep.get('guest_name', '?'))} · {ep.get('word_count', 0):,} 词</div>
  <div class="card-tags">{topics_html}</div>
</a>"""

    # 主题卡片
    topic_cards = ""
    for topic_name, topic_data in list(topics.items())[:8]:
        color = get_topic_color(topic_name)
        count = topic_data.get("episode_count", 0)
        topic_cards += f"""
<a href="topics/{topic_name.lower().replace(' & ', '-').replace(' ', '-')}.html" class="card" style="text-decoration:none;border-left:3px solid {color}">
  <div class="card-title" style="color:{color}">{escape_html(topic_zh(topic_name))}</div>
  <div class="card-meta">{count} 期节目</div>
  <div class="keyword-cloud">
    {''.join(f'<span class="keyword-tag">{kw}</span>' for kw in topic_data.get('top_keywords', [])[:6])}
  </div>
</a>"""

    # 多次出现的嘉宾
    multi_guests = [(g, d) for g, d in guests.items() if d.get("episode_count", 0) > 1]
    multi_guests.sort(key=lambda x: x[1].get("episode_count", 0), reverse=True)
    guest_list = ""
    for gname, gdata in multi_guests[:10]:
        count = gdata.get("episode_count", 0)
        guest_list += f"""
<a href="guests/{slug_to_id(gname)}.html" class="ep-item" style="text-decoration:none">
  <div class="ep-num">×{count}</div>
  <div class="ep-info">
    <div class="ep-title">{escape_html(gname)}</div>
    <div class="ep-topics">
      {''.join(f'<span class="tag" style="background:{get_topic_color(t)}22;color:{get_topic_color(t)};border:1px solid {get_topic_color(t)}44">{topic_zh(t)}</span>' for t in gdata.get('main_topics', [])[:3])}
    </div>
  </div>
</a>"""

    content = f"""
<div class="hero fade-in">
  <h1>Lex Fridman<br>知识图谱</h1>
  <p>每一场对话、每一个思想、每一个洞见——全部可搜索、相互关联。</p>
  <div class="stats-grid">
    <div class="stat-card">
      <span class="num">{total_eps}</span>
      <div class="label">期节目</div>
    </div>
    <div class="stat-card">
      <span class="num">{total_guests}</span>
      <div class="label">位嘉宾</div>
    </div>
    <div class="stat-card">
      <span class="num">{total_topics}</span>
      <div class="label">个主题</div>
    </div>
    <div class="stat-card">
      <span class="num">{total_words // 1_000_000:.1f}M</span>
      <div class="label">词汇量</div>
    </div>
  </div>
</div>

<div class="content">
  <div class="section-title">最新节目</div>
  <div class="section-desc">Lex Fridman 播客最新对话</div>
  <div class="card-grid">{recent_cards}</div>

  <div class="section-title">按主题浏览</div>
  <div class="section-desc">按话题分类探索所有对话</div>
  <div class="card-grid">{topic_cards}</div>

  <div class="section-title">多次出现的嘉宾</div>
  <div class="section-desc">曾多次参与节目的嘉宾</div>
  <div class="ep-list">{guest_list}</div>
</div>
"""
    return build_page("首页", content, "home", depth=0)


def build_episodes_index(episodes, topics):
    # 构建过滤按钮（中文主题名）
    all_topics = sorted(set(t for ep in episodes for t in ep.get("topics", [])))
    filter_btns = '<button class="filter-btn active" onclick="filterByTopic(\'\')">全部</button>'
    for t in all_topics:
        color = get_topic_color(t)
        filter_btns += f'<button class="filter-btn" onclick="filterByTopic(\'{escape_html(t)}\')" style="border-color:{color}44">{escape_html(topic_zh(t))}</button>'

    ep_items = ""
    for i, ep in enumerate(episodes, 1):
        topics_html = "".join(
            f'<span class="tag" style="background:{get_topic_color(t)}22;color:{get_topic_color(t)};border:1px solid {get_topic_color(t)}44">{topic_zh(t)}</span>'
            for t in ep.get("topics", [])[:3]
        )
        ep_num = ep.get("episode_num") or i
        topics_str = "|".join(ep.get("topics", []))
        ep_items += f"""
<div class="ep-item" data-topics="{escape_html(topics_str)}">
  <div class="ep-num">#{ep_num}</div>
  <div class="ep-info">
    <div class="ep-title"><a href="{ep['slug']}.html">{escape_html(ep.get('title', ''))}</a></div>
    <div class="ep-guest">{escape_html(ep.get('guest_name', ''))}</div>
    <div class="ep-topics">{topics_html}</div>
  </div>
  <div class="ep-actions">
    <a href="{ep['slug']}.html" class="btn">阅读 →</a>
    <a href="{ep.get('url', '#')}" target="_blank" class="btn">原文</a>
  </div>
</div>"""

    content = f"""
<div class="hero">
  <h1>全部节目</h1>
  <p>共 {len(episodes)} 期节目，含完整文字稿</p>
</div>
<div class="content">
  <input type="text" id="search-input" class="search-box" placeholder="搜索节目、嘉宾、主题...">
  <div class="filter-bar">{filter_btns}</div>
  <div class="ep-list" id="ep-list">{ep_items}</div>
</div>
"""
    return build_page("全部节目", content, "episodes")


def build_summary_section(summary_data: dict) -> str:
    """构建 AI 总结展示区 HTML，无总结时返回空字符串"""
    if not summary_data:
        return ""

    title_zh = escape_html(summary_data.get("title_zh", ""))
    summary_zh = escape_html(summary_data.get("summary_zh", ""))
    guest_intro = escape_html(summary_data.get("guest_intro_zh", ""))
    key_points = summary_data.get("key_points_zh", [])
    topics_zh = summary_data.get("topics_zh", [])
    notable_quotes = summary_data.get("notable_quotes_zh", [])

    # 核心观点列表
    points_html = "".join(
        f'<li style="margin-bottom:8px;color:#cbd5e1;line-height:1.6">{escape_html(p)}</li>'
        for p in key_points
    )

    # 话题标签
    tags_html = "".join(
        f'<span style="background:#6366f122;color:#818cf8;border:1px solid #6366f144;border-radius:20px;padding:3px 10px;font-size:12px">{escape_html(t)}</span>'
        for t in topics_zh
    )

    # 金句
    quotes_html = "".join(
        f'<div style="border-left:3px solid #f59e0b;padding:8px 14px;margin-bottom:8px;background:#f59e0b0a;border-radius:0 6px 6px 0;color:#fcd34d;font-size:14px;line-height:1.6">{escape_html(q)}</div>'
        for q in notable_quotes
    )

    return f"""
<div style="background:linear-gradient(135deg,#1e1e2a,#16213e);border:1px solid #6366f133;border-radius:16px;padding:28px;margin-bottom:32px">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
    <span style="font-size:20px">🤖</span>
    <span style="font-size:13px;color:#6366f1;font-weight:600;text-transform:uppercase;letter-spacing:0.08em">AI 智能总结</span>
  </div>

  {f'<h2 style="font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:12px;line-height:1.4">{title_zh}</h2>' if title_zh else ''}

  {f'<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin-bottom:16px">{summary_zh}</p>' if summary_zh else ''}

  {f'<div style="margin-bottom:16px">{tags_html}</div>' if tags_html else ''}

  {f'<p style="color:#64748b;font-size:13px;margin-bottom:20px;font-style:italic">{guest_intro}</p>' if guest_intro else ''}

  {f'''<div style="margin-bottom:20px">
    <div style="font-size:14px;font-weight:600;color:#818cf8;margin-bottom:10px">📌 核心观点</div>
    <ul style="list-style:none;padding:0">{points_html}</ul>
  </div>''' if points_html else ''}

  {f'''<div>
    <div style="font-size:14px;font-weight:600;color:#f59e0b;margin-bottom:10px">✨ 金句摘录</div>
    {quotes_html}
  </div>''' if quotes_html else ''}
</div>
"""


def build_episode_page(ep, all_episodes, ep_map):
    """构建单个 episode 页面（双语：英文原文 + 中文翻译）"""
    slug = ep["slug"]

    # 加载完整 transcript 数据
    transcript_file = TRANSCRIPTS_DIR / f"{slug}.json"
    full_data = {}
    if transcript_file.exists():
        with open(transcript_file, "r", encoding="utf-8") as f:
            full_data = json.load(f)

    # 加载 AI 总结
    summary_data = load_summary(slug)

    # 加载翻译缓存
    trans = load_translation(slug)
    chapters_zh = trans.get("chapters_zh", [])
    quotes_zh   = trans.get("quotes_zh", [])
    dialogue_zh = trans.get("dialogue_zh", [])

    chapters  = full_data.get("chapters", ep.get("chapters", []))
    dialogue  = full_data.get("dialogue", [])
    key_quotes = ep.get("key_quotes", [])

    # ── 章节目录（双语）──────────────────────────────────────────
    chapters_html = ""
    if chapters:
        chapters_html = '<div class="chapter-list">'
        for idx, ch in enumerate(chapters[:20]):
            en_title = ch.get("title", "")
            zh_title = chapters_zh[idx] if idx < len(chapters_zh) else ""
            zh_part = f'<span class="zh-trans"> · {escape_html(zh_title)}</span>' if zh_title else ""
            chapters_html += f"""
<div class="chapter-item">
  <span class="chapter-time">{escape_html(ch.get('time', ''))}</span>
  <span class="chapter-title">{escape_html(en_title)}{zh_part}</span>
</div>"""
        chapters_html += "</div>"

    # ── 精彩语录（双语）──────────────────────────────────────────
    quotes_html = ""
    for idx, q in enumerate(key_quotes[:5]):
        en_text  = q.get("text", "")
        zh_text  = quotes_zh[idx] if idx < len(quotes_zh) else ""
        time_str = f"（{q.get('time', '')}）" if q.get("time") else ""
        zh_block = f'<div class="quote-zh">{escape_html(zh_text)}</div>' if zh_text else ""
        quotes_html += f"""
<div class="quote-block">
  <div class="quote-text">"{escape_html(en_text)}"</div>
  {zh_block}
  <div class="quote-meta">— {escape_html(q.get('speaker', ''))} {escape_html(time_str)}</div>
</div>"""

    # ── 主题标签（中文）──────────────────────────────────────────
    topics_html = "".join(
        f'<span class="tag" style="background:{get_topic_color(t)}22;color:{get_topic_color(t)};border:1px solid {get_topic_color(t)}44;font-size:13px;padding:4px 12px">{topic_zh(t)}</span>'
        for t in ep.get("topics", [])
    )

    # ── 关键词云 ──────────────────────────────────────────────────
    keywords_html = "".join(
        f'<span class="keyword-tag">{escape_html(kw)}</span>'
        for kw in ep.get("top_keywords", [])[:20]
    )

    # ── 相关 episodes（同主题）───────────────────────────────────
    related = []
    for other in all_episodes:
        if other["slug"] == slug:
            continue
        shared = set(ep.get("topics", [])) & set(other.get("topics", []))
        if shared:
            related.append((other, len(shared)))
    related.sort(key=lambda x: x[1], reverse=True)
    related_html = ""
    for other, _ in related[:4]:
        related_html += f"""
<a href="{other['slug']}.html" class="card" style="text-decoration:none">
  <div class="card-title">{escape_html(other.get('title', ''))}</div>
  <div class="card-meta">{escape_html(other.get('guest_name', ''))}</div>
</a>"""

    # ── 全文对话（双语，全部显示，前30条直接展示，其余折叠）──────────
    # 智能推断说话人：HF数据只有一个speaker（节目名），需要区分Lex和嘉宾
    guest_name_ep = ep.get("guest_name", "")
    def infer_speaker(idx, text, raw_speaker, guest):
        """推断真实说话人：Lex 通常提问，嘉宾回答"""
        # 如果原始 speaker 已经包含 Lex，直接用
        if "Lex" in raw_speaker:
            return "Lex Fridman", True
        # 如果原始 speaker 不是节目名（即已有真实说话人），直接用
        if raw_speaker and raw_speaker != guest and not any(c in raw_speaker for c in ["Debate", "Discussion", "Interview"]):
            return raw_speaker, False
        # HF数据：开头约前5条是Lex的介绍词
        if idx < 5:
            return "Lex Fridman", True
        # 根据文本特征推断：问句/短句倾向Lex，长段落倾向嘉宾
        text_stripped = text.strip()
        is_question = text_stripped.endswith("?") or text_stripped.lower().startswith(("what ", "how ", "why ", "do you", "can you", "tell me", "so ", "and ", "but "))
        is_short = len(text_stripped) < 80
        if is_question or (is_short and idx % 2 == 0):
            return "Lex Fridman", True
        return guest if guest else raw_speaker, False

    dialogue_html_visible = ""
    dialogue_html_hidden = ""
    for idx, d in enumerate(dialogue):
        speaker  = d.get("speaker", "")
        text     = d.get("text", "")
        time_str = d.get("time", "")
        zh_text  = dialogue_zh[idx] if idx < len(dialogue_zh) else ""
        display_speaker, is_lex = infer_speaker(idx, text, speaker, guest_name_ep)
        color    = "#94a3b8" if is_lex else "#818cf8"
        en_display = escape_html(text)
        zh_display = f'<div class="dialogue-zh">{escape_html(zh_text)}</div>' if zh_text else ""
        item_html = f"""
<div class="dialogue-item">
  <div class="dialogue-speaker" style="color:{color}">
    {escape_html(display_speaker)}{f' <span class="dialogue-time">({time_str})</span>' if time_str else ''}
  </div>
  <div class="dialogue-en">{en_display}</div>
  {zh_display}
</div>"""
        if idx < 30:
            dialogue_html_visible += item_html
        else:
            dialogue_html_hidden += item_html

    if dialogue_html_hidden:
        dialogue_html = dialogue_html_visible + f"""
<div id="dialogue-more" style="display:none">{dialogue_html_hidden}</div>
<button onclick="document.getElementById('dialogue-more').style.display='block';this.style.display='none'" class="btn btn-primary" style="margin-top:12px">展开全部 {len(dialogue)} 条对话 ↓</button>
"""
    else:
        dialogue_html = dialogue_html_visible

    content = f"""
<div class="content fade-in">
  <div class="breadcrumb">
    <a href="../index.html">首页</a> <span>›</span>
    <a href="index.html">全部节目</a> <span>›</span>
    <span>{escape_html(ep.get('title', '')[:50])}</span>
  </div>

  <h1 style="font-size:28px;font-weight:800;margin-bottom:12px;line-height:1.3">{escape_html(ep.get('title', ''))}</h1>

  <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;flex-wrap:wrap">
    <a href="../guests/{slug_to_id(ep.get('guest_name', ''))}.html" style="font-size:16px;color:#818cf8;font-weight:600">{escape_html(ep.get('guest_name', ''))}</a>
    <span style="color:#475569">·</span>
    <span style="font-size:14px;color:#64748b">{ep.get('word_count', 0):,} 词</span>
    <span style="color:#475569">·</span>
    <a href="{ep.get('url', '#')}" target="_blank" class="btn">查看原文 ↗</a>
  </div>

  <div class="card-tags" style="margin-bottom:28px">{topics_html}</div>

  {build_summary_section(summary_data)}

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:32px">
    <div>
      <div class="section-title" style="font-size:18px;margin-bottom:12px">📋 章节目录</div>
      {chapters_html if chapters_html else '<p style="color:#64748b;font-size:14px">暂无章节信息</p>'}
    </div>
    <div>
      <div class="section-title" style="font-size:18px;margin-bottom:12px">🔑 关键词</div>
      <div class="keyword-cloud">{keywords_html}</div>
    </div>
  </div>

  <div class="section-title" style="font-size:18px;margin-bottom:12px">💬 精彩语录</div>
  {quotes_html if quotes_html else '<p style="color:#64748b;font-size:14px">暂无语录</p>'}

  <div style="display:flex;align-items:center;justify-content:space-between;margin-top:32px;margin-bottom:12px">
    <div class="section-title" style="font-size:18px;margin-bottom:0">🎙️ 完整对话（{len(dialogue)} 条）</div>
    {f'<button id="translate-all-btn" onclick="translateAll()" class="btn btn-primary" style="font-size:13px;padding:6px 14px">🌐 一键翻译全文</button>' if dialogue else ''}
  </div>
  <div class="dialogue-box">
    {dialogue_html if dialogue_html else '<p style="color:#64748b;font-size:14px">加载中...</p>'}
    {f'<a href="{ep.get("url", "#")}" target="_blank" class="btn" style="margin-top:16px">查看原始文字稿 ↗</a>' if dialogue else ''}
  </div>

  <div class="section-title" style="font-size:18px;margin-bottom:12px">🔗 相关节目</div>
  <div class="card-grid">{related_html if related_html else '<p style="color:#64748b;font-size:14px">暂无相关节目</p>'}</div>
</div>
"""
    return build_page(ep.get("title", "节目"), content, "episodes")


def build_guests_index(guests, ep_map):
    guest_cards = ""
    sorted_guests = sorted(guests.items(), key=lambda x: x[1].get("episode_count", 0), reverse=True)

    for gname, gdata in sorted_guests:
        count = gdata.get("episode_count", 0)
        topics_html = "".join(
            f'<span class="tag" style="background:{get_topic_color(t)}22;color:{get_topic_color(t)};border:1px solid {get_topic_color(t)}44">{topic_zh(t)}</span>'
            for t in gdata.get("main_topics", [])[:2]
        )
        initial = gname[0].upper() if gname else "?"
        guest_cards += f"""
<a href="{slug_to_id(gname)}.html" class="card" style="text-decoration:none">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
    <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#818cf8);display:flex;align-items:center;justify-content:center;font-weight:700;color:white;flex-shrink:0">{initial}</div>
    <div>
      <div class="card-title" style="margin-bottom:2px">{escape_html(gname)}</div>
      <div class="card-meta">{count} 期节目</div>
    </div>
  </div>
  <div class="card-tags">{topics_html}</div>
</a>"""

    content = f"""
<div class="hero">
  <h1>嘉宾</h1>
  <p>共 {len(guests)} 位嘉宾参与了所有节目</p>
</div>
<div class="content">
  <input type="text" id="guest-search" class="search-box" placeholder="搜索嘉宾...">
  <div class="card-grid" id="guest-grid">{guest_cards}</div>
</div>
"""
    return build_page("嘉宾", content, "guests")


def build_guest_page(gname, gdata, ep_map, all_episodes):
    episodes_html = ""
    for slug in gdata.get("episodes", []):
        ep = ep_map.get(slug)
        if not ep:
            continue
        topics_html = "".join(
            f'<span class="tag" style="background:{get_topic_color(t)}22;color:{get_topic_color(t)};border:1px solid {get_topic_color(t)}44">{topic_zh(t)}</span>'
            for t in ep.get("topics", [])[:2]
        )
        episodes_html += f"""
<div class="ep-item">
  <div class="ep-info">
    <div class="ep-title"><a href="../episodes/{slug}.html">{escape_html(ep.get('title', ''))}</a></div>
    <div class="ep-topics" style="margin-top:6px">{topics_html}</div>
  </div>
  <div class="ep-actions">
    <a href="../episodes/{slug}.html" class="btn">阅读 →</a>
  </div>
</div>"""

    quotes_html = ""
    for q in gdata.get("best_quotes", [])[:3]:
        quotes_html += f"""
<div class="quote-block">
  <div class="quote-text">"{escape_html(q.get('text', ''))}"</div>
  <div class="quote-meta">— {escape_html(gname)}</div>
</div>"""

    topics_html = "".join(
        f'<span class="tag" style="background:{get_topic_color(t)}22;color:{get_topic_color(t)};border:1px solid {get_topic_color(t)}44;font-size:13px;padding:4px 12px">{topic_zh(t)}</span>'
        for t in gdata.get("main_topics", [])
    )

    keywords_html = "".join(
        f'<span class="keyword-tag">{escape_html(kw)}</span>'
        for kw in gdata.get("top_keywords", [])[:20]
    )

    initial = gname[0].upper() if gname else "?"
    count = gdata.get("episode_count", 0)

    content = f"""
<div class="content fade-in">
  <div class="breadcrumb">
    <a href="../index.html">首页</a> <span>›</span>
    <a href="index.html">嘉宾</a> <span>›</span>
    <span>{escape_html(gname)}</span>
  </div>

  <div class="guest-header">
    <div class="guest-avatar">{initial}</div>
    <div>
      <div class="guest-name">{escape_html(gname)}</div>
      <div class="guest-meta">共参与 {count} 期 Lex Fridman 播客</div>
      <div class="card-tags" style="margin-top:10px">{topics_html}</div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:32px">
    <div>
      <div class="section-title" style="font-size:18px;margin-bottom:12px">🎙️ 参与节目</div>
      <div class="ep-list">{episodes_html}</div>
    </div>
    <div>
      <div class="section-title" style="font-size:18px;margin-bottom:12px">🔑 关键词</div>
      <div class="keyword-cloud">{keywords_html}</div>
    </div>
  </div>

  {f'<div class="section-title" style="font-size:18px;margin-bottom:12px">💬 精彩语录</div>{quotes_html}' if quotes_html else ''}
</div>
"""
    return build_page(gname, content, "guests")


def build_topics_index(topics):
    topic_cards = ""
    for topic_name, topic_data in sorted(topics.items(), key=lambda x: x[1].get("episode_count", 0), reverse=True):
        color = get_topic_color(topic_name)
        count = topic_data.get("episode_count", 0)
        keywords = topic_data.get("top_keywords", [])[:8]
        topic_slug = topic_name.lower().replace(" & ", "-").replace(" ", "-")
        topic_cards += f"""
<a href="{topic_slug}.html" class="card" style="text-decoration:none;border-left:3px solid {color}">
  <div class="card-title" style="color:{color}">{escape_html(topic_zh(topic_name))}</div>
  <div class="card-meta">{count} 期节目</div>
  <div class="keyword-cloud" style="margin-top:8px">
    {''.join(f'<span class="keyword-tag">{kw}</span>' for kw in keywords)}
  </div>
</a>"""

    content = f"""
<div class="hero">
  <h1>主题</h1>
  <p>探索所有节目中的 {len(topics)} 个核心主题</p>
</div>
<div class="content">
  <div class="card-grid">{topic_cards}</div>
</div>
"""
    return build_page("主题", content, "topics")


def build_topic_page(topic_name, topic_data, ep_map):
    color = get_topic_color(topic_name)
    topic_slug = topic_name.lower().replace(" & ", "-").replace(" ", "-")

    episodes_html = ""
    for slug in topic_data.get("episodes", []):
        ep = ep_map.get(slug)
        if not ep:
            continue
        other_topics = "".join(
            f'<span class="tag" style="background:{get_topic_color(t)}22;color:{get_topic_color(t)};border:1px solid {get_topic_color(t)}44">{topic_zh(t)}</span>'
            for t in ep.get("topics", [])[:2] if t != topic_name
        )
        episodes_html += f"""
<div class="ep-item">
  <div class="ep-info">
    <div class="ep-title"><a href="../episodes/{slug}.html">{escape_html(ep.get('title', ''))}</a></div>
    <div class="ep-guest" style="margin-bottom:4px">{escape_html(ep.get('guest_name', ''))}</div>
    <div class="ep-topics">{other_topics}</div>
  </div>
  <div class="ep-actions">
    <a href="../episodes/{slug}.html" class="btn">阅读 →</a>
  </div>
</div>"""

    quotes_html = ""
    for q in topic_data.get("best_quotes", [])[:5]:
        quotes_html += f"""
<div class="quote-block">
  <div class="quote-text">"{escape_html(q.get('text', ''))}"</div>
  <div class="quote-meta">— {escape_html(q.get('speaker', ''))}</div>
</div>"""

    keywords_html = "".join(
        f'<span class="keyword-tag">{escape_html(kw)}</span>'
        for kw in topic_data.get("top_keywords", [])[:25]
    )

    content = f"""
<div class="content fade-in">
  <div class="breadcrumb">
    <a href="../index.html">首页</a> <span>›</span>
    <a href="index.html">主题</a> <span>›</span>
    <span>{escape_html(topic_zh(topic_name))}</span>
  </div>

  <div class="topic-header" style="background:linear-gradient(135deg,{color}22,{color}11);border:1px solid {color}44">
    <h1 style="color:{color}">{escape_html(topic_zh(topic_name))}</h1>
    <p>共 {topic_data.get('episode_count', 0)} 期节目涉及此主题</p>
  </div>

  <div style="display:grid;grid-template-columns:2fr 1fr;gap:24px">
    <div>
      <div class="section-title" style="font-size:18px;margin-bottom:12px">🎙️ 相关节目</div>
      <div class="ep-list">{episodes_html}</div>
    </div>
    <div>
      <div class="section-title" style="font-size:18px;margin-bottom:12px">🔑 关键词</div>
      <div class="keyword-cloud">{keywords_html}</div>
      
      {f'<div class="section-title" style="font-size:18px;margin-bottom:12px;margin-top:24px">💬 精彩语录</div>{quotes_html}' if quotes_html else ''}
    </div>
  </div>
</div>
"""
    return build_page(topic_zh(topic_name), content, "topics")


def build_site():
    print("[1/7] Loading data...")
    episodes, guests, topics, summary, ep_map = load_data()

    # 创建目录
    (SITE_DIR / "episodes").mkdir(exist_ok=True)
    (SITE_DIR / "guests").mkdir(exist_ok=True)
    (SITE_DIR / "topics").mkdir(exist_ok=True)

    print("[2/7] Building home page...")
    with open(SITE_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(build_home(episodes, guests, topics, summary))

    print("[3/7] Building episodes index...")
    with open(SITE_DIR / "episodes" / "index.html", "w", encoding="utf-8") as f:
        f.write(build_episodes_index(episodes, topics))

    print(f"[3/7] Building {len(episodes)} episode pages...")
    for ep in episodes:
        page_html = build_episode_page(ep, episodes, ep_map)
        with open(SITE_DIR / "episodes" / f"{ep['slug']}.html", "w", encoding="utf-8") as f:
            f.write(page_html)

    print("[4/7] Building guests index...")
    with open(SITE_DIR / "guests" / "index.html", "w", encoding="utf-8") as f:
        f.write(build_guests_index(guests, ep_map))

    print(f"[4/7] Building {len(guests)} guest pages...")
    for gname, gdata in guests.items():
        page_html = build_guest_page(gname, gdata, ep_map, episodes)
        guest_id = slug_to_id(gname)
        with open(SITE_DIR / "guests" / f"{guest_id}.html", "w", encoding="utf-8") as f:
            f.write(page_html)

    print("[5/7] Building topics index...")
    with open(SITE_DIR / "topics" / "index.html", "w", encoding="utf-8") as f:
        f.write(build_topics_index(topics))

    print(f"[5/7] Building {len(topics)} topic pages...")
    for topic_name, topic_data in topics.items():
        topic_slug = topic_name.lower().replace(" & ", "-").replace(" ", "-")
        page_html = build_topic_page(topic_name, topic_data, ep_map)
        with open(SITE_DIR / "topics" / f"{topic_slug}.html", "w", encoding="utf-8") as f:
            f.write(page_html)

    # 统计生成的文件数
    total_files = sum(1 for _ in SITE_DIR.rglob("*.html"))
    print(f"\n[DONE] Site built successfully!")
    print(f"   Total HTML files: {total_files}")
    print(f"   Output dir: {SITE_DIR}")
    print(f"\n   Open in browser: {SITE_DIR / 'index.html'}")


if __name__ == "__main__":
    build_site()
