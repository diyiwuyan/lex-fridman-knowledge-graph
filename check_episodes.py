import json, os

slugs = ['dario-amodei', 'ilya-sutskever', 'yann-lecun-3', 'demis-hassabis-2', 'jensen-huang', 'mark-zuckerberg-3', 'jordan-peterson-2', 'elon-musk-4', 'sam-harris', 'john-carmack', 'andrew-huberman-5', 'rick-rubin', 'yuval-noah-harari', 'stephen-wolfram-3']

for slug in slugs:
    path = f'data/transcripts/{slug}.json'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        guest = data.get('guest_name', 'N/A')
        title = data.get('title', 'N/A')
        chapters = data.get('chapters', [])
        dialogue = data.get('dialogue', [])
        # Extract first 3000 chars of dialogue
        text = ' '.join([d.get('text','') for d in dialogue])[:3000]
        print(f"=== {slug} ===")
        print(f"guest={guest}, title={title}, chapters={len(chapters)}, dialogue_entries={len(dialogue)}")
        print(f"TEXT_PREVIEW: {text[:500]}")
        print()
    else:
        print(f'{slug}: FILE NOT FOUND')
