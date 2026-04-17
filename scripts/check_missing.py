import json, re
from pathlib import Path

BASE = Path(__file__).parent.parent
urls_file = BASE / 'data' / 'all_transcript_urls.json'
transcripts_dir = BASE / 'data' / 'transcripts'
summaries_dir = BASE / 'data' / 'summaries'

data = json.loads(urls_file.read_text(encoding='utf-8'))
urls = data['urls']

def url_to_slug(url):
    m = re.search(r'lexfridman\.com/(.+)-transcript', url)
    return m.group(1) if m else None

all_slugs = [s for s in (url_to_slug(u) for u in urls) if s]

has_transcript = {p.stem for p in transcripts_dir.glob('*.json')}
has_summary = {p.stem for p in summaries_dir.glob('*.json')}

# 缺失 = 有 transcript 但没有（或有 error 标记的）summary
def is_error(slug):
    f = summaries_dir / f'{slug}.json'
    if not f.exists():
        return False
    try:
        d = json.loads(f.read_text(encoding='utf-8'))
        return d.get('error') == 'generation_failed'
    except:
        return True

missing = sorted(s for s in all_slugs if s in has_transcript and (s not in has_summary or is_error(s)))
print(f'总 URL: {len(all_slugs)}')
print(f'有 transcript: {len(has_transcript)}')
print(f'已有 summary: {len(has_summary)}')
print(f'缺失（有transcript但无有效summary）: {len(missing)}')
print('前20:', missing[:20])

# 保存缺失列表
out = BASE / 'data' / 'missing_slugs.json'
out.write_text(json.dumps(missing, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'缺失列表已保存到 {out}')
