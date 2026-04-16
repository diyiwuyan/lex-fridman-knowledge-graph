import json, os, sys

def extract_text(slug, max_chars=8000):
    path = f'data/transcripts/{slug}.json'
    if not os.path.exists(path):
        return None, None, None, None, None
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    guest = data.get('guest_name', '')
    title = data.get('title', '')
    chapters = data.get('chapters', [])
    dialogue = data.get('dialogue', [])
    
    # Build text with speaker labels
    lines = []
    char_count = 0
    for d in dialogue:
        speaker = d.get('speaker', '')
        text = d.get('text', '').strip()
        if text:
            line = f"{speaker}: {text}"
            lines.append(line)
            char_count += len(line)
            if char_count >= max_chars:
                break
    
    full_text = '\n'.join(lines)
    chapter_titles = [c.get('title', '') for c in chapters]
    return guest, title, chapter_titles, full_text, data

slug = sys.argv[1] if len(sys.argv) > 1 else 'dario-amodei'
guest, title, chapters, text, data = extract_text(slug)
print(f"GUEST: {guest}")
print(f"TITLE: {title}")
print(f"CHAPTERS: {chapters[:15]}")
print(f"TEXT ({len(text)} chars):")
print(text[:6000])
