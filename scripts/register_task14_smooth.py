"""Register added smooth previews while preserving every old preview byte."""
import json
from pathlib import Path
from render_task14_hd import sha

ROOT = Path(__file__).resolve().parents[1]
media = ROOT / 'web/media'
manifest = json.loads((media / 'manifest.json').read_text())
index = json.loads((media / 'libuipc-smooth/index.json').read_text())
assert len(index['cases']) == 14 and sum(r['frames'] for r in index['cases']) == 8081
old_total = 0
for record in index['cases']:
    name = record['case']
    row = manifest['records'][f'test-initials/{name}']
    for f in row['files'].values():
        assert sha(ROOT / 'web' / f['path']) == f['sha256'], f['path']
    old_total += row['files']['video']['bytes']
    for key, filename in [('smooth_video', 'video.mp4'), ('smooth_poster', 'poster.jpg'),
                          ('smooth_contact', 'contact.jpg'), ('smooth_provenance', 'render.json'),
                          ('timesteps', 'timesteps.json')]:
        path = media / 'libuipc-smooth' / name / filename
        row['files'][key] = dict(path=str(path.relative_to(ROOT / 'web')), bytes=path.stat().st_size,
                                sha256=sha(path), source='ClothLOOP default render.py; source and renderer hashes in smooth render.json')
    assert row['files']['smooth_video']['sha256'] == record['video_sha256']
assert old_total == 46590393
assert old_total + index['video_bytes'] == index['combined_video_bytes'] < 120_000_000
(media / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(passed=True, old_video_bytes=old_total, smooth_video_bytes=index['video_bytes'],
                     combined_video_bytes=index['combined_video_bytes'])))
