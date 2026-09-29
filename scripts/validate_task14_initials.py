"""Validate the self-contained Task14 first-frame release without external data."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'testsets/task14_initials_20260929'


def validate():
    index = json.loads((DATA / 'index.json').read_text())
    expected = {'ct_00004', 'ct_00018', 'cc_05_06', 'cc_05_08', 'cc_05_16', 'cc_01_01',
                'cc_55_27', 'cc_144_02', 'dlayers_00396', 'dlayers_00756',
                'added_06_13', 'added_85_12', 'cipc_dress_knife', 'cipc_multilayer'}
    assert len(index['cases']) == 14 and {c['case'] for c in index['cases']} == expected
    manifest = json.loads((DATA / 'manifest.json').read_text())
    for record in manifest['files']:
        p = ROOT / record['path']
        assert p.resolve().is_relative_to(DATA.resolve()) and not p.is_symlink()
        assert p.stat().st_size == record['bytes']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == record['sha256'], record['path']
    total = 0
    for case in index['cases']:
        meshes = {}
        for part in ['body', 'cloth']:
            p = ROOT / case[part]
            meshes[part] = np.load(p, allow_pickle=False)
            v, f = meshes[part]['vertices'], meshes[part]['faces']
            assert v.dtype == np.float64 and v.ndim == 2 and v.shape[1] == 3 and np.isfinite(v).all()
            assert f.ndim == 2 and f.shape[1] == 3 and np.issubdtype(f.dtype, np.integer)
            assert f.min() >= 0 and f.max() < len(v)
            total += p.stat().st_size
        meta = json.loads((ROOT / case['provenance']).read_text())
        report = meta['geometry_check']
        assert report['frame'] == 0 and report['cloth_cloth'] == report['cloth_body'] == 0
        raw = meshes['cloth']['vertices'].tobytes() + meshes['body']['vertices'].tobytes()
        assert hashlib.sha256(raw).hexdigest() == report['geometry_sha256']
        assert meta['units'] == 'metres' and meta['up_axis'] == 'Y'
        assert len(meshes['cloth']['component_id']) == len(meshes['cloth']['vertices'])
    assert total == index['initial_mesh_bytes']
    return index


if __name__ == '__main__':
    data = validate()
    print(json.dumps(dict(passed=True, cases=len(data['cases']), initial_mesh_bytes=data['initial_mesh_bytes'])))
