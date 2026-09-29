"""Offline source audit and registration of newly rendered Task14 previews."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--audit', type=Path, required=True)
    args = p.parse_args()
    directory = ROOT / 'web/media/libuipc'
    index = json.loads((directory / 'index.json').read_text())
    initial_index = json.loads((ROOT / 'testsets/task14_initials_20260929/index.json').read_text())
    initials = {r['case']: r for r in initial_index['cases']}
    manifest_path = ROOT / 'web/media/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    audits = []
    for case in index['cases']:
        name = case['case']
        src, dst = args.source / name, directory / name
        for file, digest in case['source_sha256'].items():
            assert sha(src / file) == digest, (name, file)
        cloth = np.load(src / 'reference/cloth.npy', mmap_mode='r')
        body = np.load(src / 'body_vertices.npy', mmap_mode='r')
        assert np.array_equal(cloth[0], np.load(ROOT / initials[name]['cloth'])['vertices'])
        assert np.array_equal(body[0], np.load(ROOT / initials[name]['body'])['vertices'])
        assert not np.array_equal(cloth[0], cloth[-1]), name
        rows = list(csv.DictReader((dst / 'iterations.csv').open()))
        logs = [json.loads(line) for line in (src / 'reference/solver_steps.jsonl').open()]
        offset = 0
        for r in rows:
            k = int(r['physical_steps'])
            group = logs[offset:offset + k]
            offset += k
            assert len(group) == k
            assert sum(s['stats']['newton_iterations'] for s in group) == int(r['nonlinear_iterations']), (name, r['frame'])
            assert sum(s['stats']['linear_solver_iterations'] for s in group) == int(r['linear_iterations'])
            assert abs(sum(s['seconds'] for s in group) - float(r['solver_seconds'])) < 1e-6
            if k:
                if 'physical_time_s' in group[-1]:
                    assert abs(group[-1]['physical_time_s'] - float(r['time_s'])) < 1e-6
                # Historical D-LAYERS labels classify actual termination, not the
                # enabled policy: an enabled semi-implicit run can reach tolerance.
                is_full = all(s['stats']['termination_criterion'] == 'native_tolerance' for s in group)
                assert (r['method'] == 'full_newton') == is_full, (name, r['frame'], r['method'], [(s['stats']['pipeline'], s['stats']['semi_implicit_enabled'], s['stats']['termination_criterion']) for s in group])
        assert offset == len(logs)
        files = {}
        for role, filename in [('video', 'video.mp4'), ('simulation_poster', 'poster.jpg'),
                               ('simulation_contact', 'contact.jpg'), ('iteration_table', 'iterations.csv'),
                               ('simulation_provenance', 'render.json')]:
            f = dst / filename
            files[role] = dict(path=str(f.relative_to(ROOT / 'web')), bytes=f.stat().st_size, sha256=sha(f),
                               source='Task14 selected exact saved source states; source hashes in render.json')
        assert files['video']['sha256'] == case['video_sha256']
        manifest['records'][f'test-initials/{name}'] = dict(note=case['geometry'], files=files)
        audits.append(dict(case=name, frames=len(rows), physical_steps=len(logs),
                           exact_public_initial_match=True, native_iteration_reaggregation=True,
                           source_hashes_verified=True, video_bytes=case['bytes']))
    assert len(audits) == 14 and sum(a['frames'] for a in audits) == 8081
    assert sum(a['video_bytes'] for a in audits) == index['video_bytes'] < 100_000_000
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(dict(passed=True, video_bytes=index['video_bytes'], cases=audits), indent=2) + '\n')
    print(f'PASS: 14 cases, 8081 frames, {index["video_bytes"]} video bytes')


if __name__ == '__main__':
    main()
