"""Validate this additive test set without models, network, or other workspaces."""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def local(path):
    target = (ROOT / path).resolve()
    assert ROOT in target.parents, f'Path escaped dataset: {path}'
    return target


def obj(path):
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            vertices.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('f '):
            faces.append([int(x.split('/')[0]) - 1 for x in line.split()[1:]])
    return np.asarray(vertices), np.asarray(faces)


def main():
    manifest = read(ROOT / 'manifest.json')
    indexed = set()
    for record in manifest['files']:
        assert record['path'] not in indexed
        indexed.add(record['path'])
        path = local(record['path'])
        assert path.is_file() and not path.is_symlink(), path
        assert path.stat().st_size == record['bytes'] and sha(path) == record['sha256'], path
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.name != 'manifest.json'}
    assert actual == indexed, {'unindexed': sorted(actual - indexed), 'missing': sorted(indexed - actual)}
    assert not any(p.endswith(('.pkl', '.glb', '.so', '.pem')) or 'node_modules' in p for p in indexed)
    dataset = read(ROOT / 'dataset.json')
    assert len(dataset['cases']) == 14 and len(dataset['snapshots']) == 15
    assert len({s['id'] for s in dataset['snapshots']}) == 15
    assert len({c['id'] for c in dataset['cases']}) == 14
    snapshots = {s['id']: s for s in dataset['snapshots']}
    loaded, outcomes = {}, []
    smpl = native = 0
    for item in dataset['snapshots']:
        folder = local(item['directory'])
        state = read(folder / 'state.json')
        parameters = read(folder / 'body_parameters.json')
        geometry = read(folder / 'reports/geometry.json')
        containment = read(folder / 'reports/containment.json')
        quality = read(folder / 'reports/quality.json')
        render = read(folder / 'reports/render.json')
        with np.load(folder / 'firstframe.npz', allow_pickle=False) as source:
            arrays = {key: source[key] for key in source.files}
        loaded[item['id']] = arrays
        digest = sha(folder / 'firstframe.npz')
        assert digest == item['firstframe_sha256'] == state['firstframe_sha256']
        assert digest == parameters['published_firstframe_sha256'] == render['source_sha256']
        assert sha(folder / 'media/preview_front_back.png') == render['image_sha256']
        for key in ['cloth', 'body', 'rest']:
            assert np.isfinite(arrays[key]).all(), (item['id'], key)
        assert arrays['cloth'].shape == arrays['rest'].shape
        assert arrays['cloth'].shape[1] == arrays['body'].shape[1] == 3
        for key, vertices in [('triangles', 'cloth'), ('body_triangles', 'body')]:
            assert arrays[key].shape[1] == 3
            assert arrays[key].min() >= 0 and arrays[key].max() < len(arrays[vertices])
        assert len(arrays['component_id']) == len(arrays['source_vertex_id']) == len(arrays['cloth'])
        assert arrays['component_id'].min() >= 0
        assert arrays['component_id'].max() < len(arrays['component_names'])
        assert str(arrays['units']) == 'm' and str(arrays['coordinate_system']) == 'Y-up'
        geometry_digest = hashlib.sha256(np.ascontiguousarray(arrays['cloth']).tobytes()
                                         + np.ascontiguousarray(arrays['body']).tobytes()).hexdigest()
        assert geometry_digest == geometry['geometry_sha256'] == containment['geometry_sha256']
        counts = [geometry['cloth_cloth'], geometry['cloth_body'], len(containment['penetrating_vertices'])]
        assert counts == state['intersection_counts'] == item['intersection_counts']
        if item['geometry_passed']:
            assert counts == [0, 0, 0] and quality['finite'] and not quality['degenerate_faces']
            assert read(folder / 'reports/visual_review.json')['passed']
        else:
            assert item['case_id'] == 'ct_00004' and counts == [954, 1957, 424]
        assert state['geometry_passed'] == item['geometry_passed']
        if parameters['model']['family'] == 'SMPL':
            smpl += 1
            assert parameters['model']['version'] == '1.1.0'
            p = parameters['parameters']
            for field, key, shape in [('betas', 'betas', (10,)),
                                      ('pose_axis_angle_rad', 'pose', (72,)),
                                      ('translation_m', 'translation', (3,))]:
                values = np.asarray(p[field])
                assert values.shape == shape and np.array_equal(values, arrays[key]), (item['id'], field)
            assert np.array_equal(p['global_orient_axis_angle_rad'], arrays['pose'][:3])
            assert np.array_equal(p['body_pose_axis_angle_rad'], arrays['pose'][3:])
            assert p['uniform_scale'] > 0
            if 'scale' in arrays:
                assert float(arrays['scale']) == p['uniform_scale']
        else:
            native += 1
            assert parameters['model']['family'] == 'native_mesh' and parameters['parameters'] is None
            assert parameters['model']['gender'] is None and parameters['model']['betas'] is None
            assert arrays['body'].shape == (12811, 3)
            assert len(arrays['stitch_indices']) == (851 if item['case_id'] == 'cipc_dress_knife' else 791)
        for prefix, vertices, faces in [('cloth', 'cloth', 'triangles'), ('body', 'body', 'body_triangles')]:
            obj_vertices, obj_faces = obj(folder / f'{prefix}.obj')
            assert np.array_equal(obj_vertices, arrays[vertices]) and np.array_equal(obj_faces, arrays[faces])
        outcomes.append({'snapshot': item['id'], 'geometry_passed': item['geometry_passed'], 'counts': counts})
    assert smpl == 13 and native == 2
    assert sum(s['geometry_passed'] for s in dataset['snapshots']) == 14
    defaults = []
    for case in dataset['cases']:
        variants = [s for s in dataset['snapshots'] if s['case_id'] == case['id']]
        assert len(variants) == (2 if case['id'] == 'added_85_12' else 1)
        assert set(case['snapshot_ids']) == {s['id'] for s in variants}
        default = [s for s in variants if s['variant'] == case['default_variant']]
        assert len(default) == 1
        defaults.append(default[0]['geometry_passed'])
    assert sum(defaults) == 13
    shorts, skirt = loaded['added_85_12'], loaded['added_85_12_skirt']
    assert np.array_equal(shorts['body'], skirt['body'])
    assert np.array_equal(shorts['body_triangles'], skirt['body_triangles'])
    ids = shorts['source_top_jacket_vertex_ids']
    assert np.array_equal(shorts['cloth'][:len(ids)], skirt['cloth'][ids])
    assert np.array_equal(shorts['rest'][:len(ids)], skirt['rest'][ids])
    assert snapshots['ct_00018']['selected_body_policy'] == 'user_selected_smpl_v1.1'
    print(json.dumps({'passed': True, 'indexed_files': len(indexed), 'cases': 14, 'snapshots': 15,
                      'geometry_passed_snapshots': 14, 'failed_snapshots': 1, 'default_passed_cases': 13,
                      'smpl_parameter_snapshots': smpl, 'native_mesh_snapshots': native,
                      'two_85_12_variants_share_exact_body_and_upper_garments': True,
                      'scope': 'Archive consistency only; no new intersection solve or dynamics certificate.',
                      'snapshots_checked': outcomes}, indent=2))


if __name__ == '__main__':
    main()
