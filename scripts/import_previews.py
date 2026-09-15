#!/usr/bin/env python3
"""Import existing, audited previews once. The website build never needs DATA.

Usage: python scripts/import_previews.py --source-workspace /absolute/path/to/DATA
Requires Pillow only for this optional import step. No source assets are changed.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace', type=Path, required=True)
    args = parser.parse_args()
    source = args.source_workspace.resolve()
    output = ROOT / 'web/media'
    entries = {}

    def add(key, folder, thumbnail, contact=None, video=None, note=''):
        target = output / key
        target.mkdir(parents=True, exist_ok=True)
        row = {'note': note, 'files': {}}
        for kind, name in [('thumbnail', thumbnail), ('contact', contact), ('video', video)]:
            if name is None or not (folder / name).is_file():
                if kind == 'thumbnail':
                    raise FileNotFoundError(folder / str(name))
                continue
            src = folder / name
            dest = target / (kind + ('.mp4' if kind == 'video' else '.webp'))
            if kind == 'video':
                shutil.copyfile(src, dest)
            else:
                with Image.open(src) as im:
                    im = im.convert('RGB')
                    if kind == 'thumbnail':
                        im.thumbnail((640, 480))
                    im.save(dest, 'WEBP', quality=86, method=6)
            row['files'][kind] = {
                'path': str(dest.relative_to(ROOT / 'web')),
                'sha256': sha(dest), 'bytes': dest.stat().st_size,
                'source': str(src.relative_to(source)), 'source_sha256': sha(src),
            }
        entries[key] = row

    motions = json.loads((ROOT / 'body_sequences.json').read_text())
    old_motions = json.loads((source / 'body_sequence/ours/body/manifest.json').read_text())['records']
    for motion in motions:
        dataset, name = motion['dataset'], motion['id']
        key = f'body/{dataset}/{name}'
        if dataset == 'ClothTransformer':
            folder = source / f'body_sequence/ours/body/smpl_recovery/joint_repair/motions/{name}'
            add(key, folder, 'thumbnail.jpg', 'contact.jpg', 'comparison.mp4',
                '最新关节合理性修复的对比预览；视频同时包含参考与修复结果，并非三份独立动作。')
        else:
            match = next(x for x in old_motions if x['source'] == dataset and x['name'] == name)
            folder = source / 'body_sequence/ours/body' / match['path']
            add(key, folder, 'thumbnail.png', 'contact_sheet.jpg', 'preview.mp4',
                '沿用已验证的人体预览；D-LAYERS 的 30 FPS 为播放假定。' if dataset == 'D-LAYERS' else '沿用已验证的 SMPL 人体预览。')

    old_clothes = json.loads((source / 'cloth/manifest.json').read_text())['records']
    garments = json.loads((ROOT / 'garments.json').read_text())
    for item in garments:
        dataset, identifier = item['dataset'], item['id']
        if dataset == 'ClothTransformer':
            old = next(x for x in old_clothes if x['id'] == identifier)
        else:
            old = next(x for x in old_clothes if x['source'] == dataset and identifier.removesuffix('.obj') in x['variants'])
        slug = identifier.removesuffix('.obj').replace('::', '__')
        add(f'cloth/{dataset}/{slug}', source / 'cloth' / old['path'], 'thumbnail.jpg', 'contact.jpg')

    initials = json.loads((ROOT / 'D-LAYERS/garment_body_initials.json').read_text())
    for item in initials:
        name = item['sample']
        add(f'initials/D-LAYERS/{name}', source / f'cloth/D-LAYERS/selected_38_20260915/items/{name}',
            'thumbnail.jpg', 'contact.jpg', note='人体与全部服装来自同一 sample、同一选定状态。')
    manifest = {'schema': 'ClothLOOP.web-media.v1', 'records': entries,
                'images': 'Display-only WebP derivatives. Motion videos copied byte-for-byte.',
                'source_paths': 'Provenance relative to the original DATA workspace; not build dependencies.'}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(f'Imported {len(entries)} preview sets; {sum(p.stat().st_size for p in output.rglob("*") if p.is_file()):,} bytes')


if __name__ == '__main__':
    main()
