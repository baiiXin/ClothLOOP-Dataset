#!/usr/bin/env python3
"""Import the approved 2026-09-20 sample clips and assign body-only splits.

Optional one-time import: --source-workspace /path/to/DATA (NumPy + ipctk).
No source meshes, poses, or older dataset assets are modified.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import pickle
import shutil

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TRAIN = '''02_04 02_05 05_20 13_13 26_11 40_12 46_01 49_04 54_24 55_12
63_25 73_09 76_05 76_11 91_12 91_19 91_33 91_36 91_38 91_61 91_62
104_04 104_11 104_17 104_53 105_05 108_11 108_12 108_16 108_17 108_18
108_20 108_22 108_27 111_02 111_05 111_14 111_20 111_37 128_02 128_03
128_04 128_05 128_06 128_07 131_03 132_54 135_07 135_09 144_26 144_28 144_30'''.split()
TEST = {'ClothTransformer': ['sim_00004', 'sim_00018'],
        'ContourCraft': ['05_06', '05_08', '05_16', '01_01', '55_27', '144_02'],
        'D-LAYERS': ['00396', '00756', '06_13', '85_12']}

def read(path):
    return json.loads(path.read_text())

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class PoseReader(pickle.Unpickler):
    def find_class(self, module, name):
        allowed = {('numpy', 'ndarray'), ('numpy', 'dtype'), ('_codecs', 'encode')}
        allowed |= {(m, n) for m in ['numpy.core.multiarray', 'numpy._core.multiarray']
                    for n in ['_reconstruct', 'scalar']}
        if (module, name) not in allowed:
            raise pickle.UnpicklingError(f'Unsupported class {module}.{name}')
        return getattr(importlib.import_module(module), name)

def load_pose(path):
    with path.open('rb') as stream:
        return PoseReader(stream).load()

def import_sample(source, sid):
    import ipctk
    ipctk.set_num_threads(2)
    processed = source/'cloth/D-LAYERS/processed_p0_p2_20260809/processed'
    src = processed/'samples'/sid
    meta = read(src/'meta.json')
    source_pose = source/'body_sequence/datasets/D-LAYERS'/meta['motion_path']
    original = load_pose(source_pose)
    start, end = meta['seq_start'], meta['seq_end']
    assert end-start == meta['num_frame'] and set(original) == {'poses', 'trans'}
    clipped = {k: {i: original[k][j] for i, j in enumerate(range(start, end))} for k in original}
    pose_path = ROOT/f'D-LAYERS/body_sequences/sample_clips/{sid}.pkl'
    pose_path.parent.mkdir(parents=True, exist_ok=True)
    if start == 0 and end == len(original['poses']):
        shutil.copyfile(source_pose, pose_path)
    else:
        with pose_path.open('wb') as stream:
            pickle.dump(clipped, stream, protocol=4)
    saved = load_pose(pose_path)
    for field in ['poses', 'trans']:
        assert list(saved[field]) == list(range(end-start))
        for i, j in enumerate(range(start, end)):
            assert saved[field][i].dtype == original[field][j].dtype
            assert np.array_equal(saved[field][i], original[field][j])
    motion_id = Path(meta['motion_path']).stem.removesuffix('_poses')
    segment = {'source_sequence_id': motion_id, 'source_path': meta['motion_path'],
               'source_sha256': sha(source_pose), 'source_frames': len(original['poses']),
               'start_inclusive': start, 'end_exclusive': end, 'frame_index_base': 0,
               'output_frame_to_source': f'source_frame = output_frame + {start}',
               'arrays_equal_to_source_slice': True, 'max_parameter_error': 0.0,
               'resampled': False, 'translation_preserved': True,
               'byte_identical_to_full_source': sha(source_pose) == sha(pose_path)}
    row = {'dataset': 'D-LAYERS', 'id': sid, 'file': str(pose_path.relative_to(ROOT)),
           'frames': end-start, 'fps': 30.0, 'fps_status': 'assumed_playback',
           'duration_seconds': (end-start)/30, 'category': '来源样本动作',
           'description': f'D-LAYERS sample {sid}: CMU {motion_id}, source frames {start}–{end-1}',
           'upstream_group': 'sample_original_clip', 'source_sequence_id': motion_id,
           'source_segment': segment, 'gender': meta['gender'],
           'gender_source': 'D-LAYERS sample metadata',
           'betas_status': 'not supplied by source motion PKL; initial binding preserves exact source mesh',
           'initial_binding': f'D-LAYERS/garment_body_initials/{sid}/binding.json', 'split': 'test'}
    write(pose_path.with_suffix('.json'), row)
    dest = ROOT/f'D-LAYERS/garment_body_initials/{sid}'
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src/'meta.json', dest/'sample_meta.original.json')
    parts = []
    for i, name in enumerate(['human']+meta['garments'], 1):
        p = src/'meshes'/f'{name}_frame000.npz'
        target = dest/('human.npz' if name == 'human' else f'garments/{name}.npz')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        assert sha(p) == sha(target)
        with np.load(target, allow_pickle=False) as z:
            v, f = z['vertices'], z['faces']
            parts.append({'file': str(target.relative_to(dest)),
                          'source': str(p.relative_to(source/'cloth')), 'bytes': target.stat().st_size,
                          'sha256': sha(target), 'name': name, 'mesh_number': i,
                          'vertices': len(v), 'faces': len(f),
                          'original_bbox': [v.min(0).tolist(), v.max(0).tolist()]})
    # Independent CPU query includes clothing self-contact and all clothing/body
    # and clothing/clothing pairs. Only body self-contact is excluded.
    vertices, faces, offset, cloth_vertices = [], [], 0, 0
    for part in parts[1:]+parts[:1]:
        with np.load(dest/part['file']) as z:
            vertices.append(z['vertices']); faces.append(z['faces']+offset)
            offset += len(z['vertices'])
            if part['name'] != 'human': cloth_vertices += len(z['vertices'])
    v, f = np.vstack(vertices), np.vstack(faces)
    mesh = ipctk.CollisionMesh(v, ipctk.edges(f), f)
    mesh.can_collide = ipctk.make_static_obstacle_filter(cloth_vertices)
    intersects = bool(ipctk.has_intersections(mesh, v))
    assert not intersects, f'{sid}: source initial state intersects; do not label zero-collision'
    source_report = processed/'collision_report.json'
    counts = read(source_report)[sid]['frame0']
    assert all(value == 0 for pair, value in counts.items() if pair != '11')
    collision = {'sample': sid, 'state': 'frame0', 'mesh_order': meta['mesh_order'],
                 'counts': counts, 'clothing_related_all_zero': True,
                 'human_self_intersections': counts['11'], 'source_report_sha256': sha(source_report),
                 'recomputed': False,
                 'independent_verification': {'algorithm': 'ipctk.has_intersections', 'device': 'CPU',
                    'date': '2026-09-20', 'clothing_related_intersections_detected': intersects,
                    'scope': 'static selected meshes; body self-intersection excluded; source pair counts not recomputed'}}
    write(dest/'collision.json', collision)
    binding = {'schema': 'ClothLOOP.dlayers.bound-state.v1', 'sample': sid, 'state': 'frame0',
               'category': 'frame0无穿', 'source_coordinate_convention': 'world Z-up',
               'units': 'Original exported coordinate units, unchanged in NPZ files',
               'human': parts[0], 'garments': parts[1:], 'mesh_order': meta['mesh_order'],
               'collision': collision, 'source_sequence': {k: meta[k] for k in ['gender','motion_path','seq_start','seq_end','num_frame']},
               'body_sequence_key': f'D-LAYERS/{sid}', 'body_sequence_file': row['file'],
               'body_sequence_path_base': 'repository root',
               'display_transform': {'matrix': [[1,0,0],[0,0,1],[0,-1,0]],
                   'operation': 'output = matrix @ source; shared by all parts',
                   'coordinate_convention': 'Y-up', 'raw_npz_transformed': False},
               'scope': 'Exact exported body and clothing at sample start. Motion clip has matching source frame range; source betas are unavailable, so poses alone are not claimed to reconstruct the exact bound body.',
               'path_base': '.', 'source_reference_base': 'Original DATA/cloth; provenance only, not a runtime dependency',
               'collision_report_file': '../../collision_report.snapshot.json',
               'sample_metadata_file': 'sample_meta.original.json'}
    write(dest/'binding.json', binding)
    return row, {'sample': sid, 'state': 'frame0', 'garments': meta['garments'],
                 'binding': row['initial_binding'], 'body': f'D-LAYERS/garment_body_initials/{sid}/human.npz',
                 'clothing_related_all_zero': True, 'human_self_intersections': counts['11'],
                 'source': 'uploaded collision counts plus independent CPU static intersection check',
                 'body_sequence_key': f'D-LAYERS/{sid}'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace', type=Path, required=True)
    args = parser.parse_args()
    source = args.source_workspace.resolve()
    rows = read(ROOT/'body_sequences.json')
    initials = read(ROOT/'D-LAYERS/garment_body_initials.json')
    for sid in ['00396', '00756']:
        row, binding = import_sample(source, sid)
        rows = [x for x in rows if (x['dataset'], x['id']) != ('D-LAYERS', sid)] + [row]
        initials = [x for x in initials if x['sample'] != sid] + [binding]
    assert {x['id'] for x in rows if x.get('upstream_group') == 'vto52'} == set(TRAIN)
    for row in rows:
        row['split'] = ('train' if row['dataset'] == 'ContourCraft' and row['id'] in TRAIN
                        else 'test' if row['id'] in TEST.get(row['dataset'], []) else 'unassigned')
        row['split_status'] = 'not_in_current_selection' if row['split'] == 'unassigned' else 'user_selected'
    write(ROOT/'body_sequences.json', rows)
    write(ROOT/'D-LAYERS/garment_body_initials.json', sorted(initials, key=lambda x:x['sample']))
    splits = {'schema': 'ClothLOOP.body-splits.v1', 'selection_date': '2026-09-20',
              'scope': 'body sequences only; garments and initial states have no train/test assignment',
              'unassigned_policy': 'retained, excluded from current training and testing',
              'source_identity_policy': 'CMU sequence ID across ContourCraft and D-LAYERS; sample clips inherit source motion ID',
              'splits': {s: [{'key': f'{x["dataset"]}/{x["id"]}', 'file': x['file'],
                             'sha256': sha(ROOT/x['file'])} for x in rows if x['split'] == s]
                         for s in ['train','test','unassigned']}}
    assert {s:len(v) for s,v in splits['splits'].items()} == {'train':52,'test':12,'unassigned':27}
    write(ROOT/'splits/body_sequences.json', splits)
    for s, items in splits['splits'].items():
        (ROOT/f'splits/{s}.txt').write_text(''.join(x['file']+'\n' for x in items))
    print(json.dumps({s:len(v) for s,v in splits['splits'].items()}))

if __name__ == '__main__':
    main()
