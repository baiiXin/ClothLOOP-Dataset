#!/usr/bin/env python3
"""Build a portable web catalogue and indexed GLB scenes from repository assets.

Only NumPy is required. Never unpickles PKLs or loads SMPL models. Original
scientific files are read-only. Generated files belong to the Pages artifact.
"""
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path
from urllib.parse import quote

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/public/generated'
COLORS = [[0.52, 0.57, 0.59, 1], [0.30, 0.55, 0.49, 1],
          [0.72, 0.47, 0.32, 1], [0.38, 0.49, 0.72, 1], [0.66, 0.48, 0.65, 1]]
REPO = 'https://github.com/baiiXin/ClothLOOP-Dataset'


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n')


def load_mesh(path):
    if path.suffix == '.npz':
        with np.load(path, allow_pickle=False) as a:
            v, f = np.asarray(a['vertices'], dtype=np.float64), np.asarray(a['faces'], dtype=np.int64)
    else:
        vertices, faces = [], []
        for line in path.read_text().splitlines():
            s = line.split()
            if s and s[0] == 'v':
                vertices.append([float(t) for t in s[1:4]])
            elif s and s[0] == 'f':
                indices = [int(t.split('/')[0]) for t in s[1:]]
                indices = [i - 1 if i > 0 else len(vertices) + i for i in indices]
                faces.extend([[indices[0], indices[i], indices[i + 1]] for i in range(1, len(indices) - 1)])
        v, f = np.asarray(vertices, dtype=np.float64), np.asarray(faces, dtype=np.int64)
    assert v.ndim == 2 and v.shape[1] == 3 and f.ndim == 2 and f.shape[1] == 3
    assert len(v) and len(f) and np.isfinite(v).all() and 0 <= f.min() <= f.max() < len(v)
    return v, f


def build_glb(key, parts, transform=None):
    binary = bytearray()
    doc = {'asset': {'version': '2.0', 'generator': 'ClothLOOP indexed display export v1'},
           'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': 'bound-scene', 'children': []}],
           'meshes': [], 'materials': [], 'buffers': [], 'bufferViews': [], 'accessors': []}
    if transform is not None:
        matrix = np.eye(4)
        matrix[:3, :3] = np.asarray(transform)
        doc['nodes'][0]['matrix'] = matrix.T.flatten().tolist()
    verification, info = [], []

    def accessor(array, component, kind, target, bounds=False):
        binary.extend(b'\x00' * (-len(binary) % 4))
        offset = len(binary)
        raw = array.tobytes()
        binary.extend(raw)
        view = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(raw), 'target': target})
        access = {'bufferView': view, 'componentType': component, 'count': len(array), 'type': kind}
        if bounds:
            access['min'], access['max'] = array.min(axis=0).tolist(), array.max(axis=0).tolist()
        idx = len(doc['accessors'])
        doc['accessors'].append(access)
        return idx, offset

    for i, (name, path, is_body) in enumerate(parts):
        v, f = load_mesh(path)
        positions = v.astype('<f4')
        normals = np.zeros_like(v)
        face_normals = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
        for j in range(3):
            np.add.at(normals, f[:, j], face_normals)
        lengths = np.linalg.norm(normals, axis=1)
        normals /= np.maximum(lengths[:, None], 1e-30)
        normals[lengths < 1e-30] = [0, 1, 0]
        index_dtype, component = ('<u2', 5123) if len(v) <= 65535 else ('<u4', 5125)
        indices = f.flatten().astype(index_dtype)
        vp, vo = accessor(positions, 5126, 'VEC3', 34962, True)
        vn, _ = accessor(normals.astype('<f4'), 5126, 'VEC3', 34962)
        fi, fo = accessor(indices, component, 'SCALAR', 34963)
        doc['materials'].append({'name': name, 'doubleSided': True, 'pbrMetallicRoughness': {
            'baseColorFactor': COLORS[0 if is_body else 1 + (i - int(parts[0][2])) % (len(COLORS) - 1)],
            'metallicFactor': 0, 'roughnessFactor': 0.78}})
        relative = str(path.relative_to(ROOT))
        source_hash = digest(path)
        doc['meshes'].append({'name': name, 'primitives': [{'attributes': {'POSITION': vp, 'NORMAL': vn},
                             'indices': fi, 'material': i, 'mode': 4}]})
        doc['nodes'].append({'name': name, 'mesh': i, 'extras': {'isBody': is_body, 'source': relative,
                                                             'sourceSha256': source_hash}})
        doc['nodes'][0]['children'].append(i + 1)
        error = float(np.abs(positions.astype(float) - v).max())
        verification.append({'source': relative, 'vertices': len(v), 'triangles': len(f),
                             'max_abs_coordinate_error': error, 'source_sha256': source_hash,
                             'position_offset': vo, 'index_offset': fo, 'index_dtype': index_dtype})
        info.append({'name': name, 'body': is_body, 'vertices': len(v), 'triangles': len(f),
                     'file': relative, 'sha256': source_hash})
    binary.extend(b'\x00' * (-len(binary) % 4))
    doc['buffers'] = [{'byteLength': len(binary)}]
    header = json.dumps(doc, separators=(',', ':'), allow_nan=False).encode()
    header += b' ' * (-len(header) % 4)
    payload = struct.pack('<III', 0x46546C67, 2, 28 + len(header) + len(binary))
    payload += struct.pack('<II', len(header), 0x4E4F534A) + header
    payload += struct.pack('<II', len(binary), 0x004E4942) + binary
    target = OUT / 'meshes' / (key + '.glb')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    # Read the serialized buffers back: face indices/order and float32 coordinates must match.
    persisted = target.read_bytes()
    assert struct.unpack_from('<III', persisted) == (0x46546C67, 2, len(persisted))
    json_len = struct.unpack_from('<I', persisted, 12)[0]
    parsed = json.loads(persisted[20:20 + json_len])
    bin_start = 28 + json_len
    assert parsed['nodes'][0].get('matrix') == doc['nodes'][0].get('matrix')
    for part, record in zip(parts, verification):
        v, f = load_mesh(part[1])
        stored_v = np.frombuffer(persisted, dtype='<f4', count=v.size,
                                 offset=bin_start + record.pop('position_offset')).reshape(v.shape)
        stored_f = np.frombuffer(persisted, dtype=record.pop('index_dtype'), count=f.size,
                                 offset=bin_start + record.pop('index_offset')).reshape(f.shape)
        assert np.array_equal(stored_v, v.astype('<f4')) and np.array_equal(stored_f, f)
        record['triangles_equal'] = True
    return {'mesh': f'generated/meshes/{key}.glb', 'parts': info,
            'vertices': sum(x['vertices'] for x in info), 'triangles': sum(x['triangles'] for x in info),
            'mesh_bytes': target.stat().st_size, 'verification': verification}


def main():
    manifest = read(ROOT / 'manifest.json')
    for item in manifest['files']:
        path = ROOT / item['path']
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], item['path']
    media = read(ROOT / 'web/media/manifest.json')['records']
    for row in media.values():
        for f in row['files'].values():
            path = ROOT / 'web' / f['path']
            assert path.stat().st_size == f['bytes'] and digest(path) == f['sha256'], f['path']
    # OUT is exclusively generated by this script. No scientific input is modified.
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    motions, garments, initials, checks = [], [], [], []

    def common(key, source, identifier, kind, files):
        previews = media.get(key, {})
        return {'key': key, 'source': source, 'id': identifier, 'kind': kind,
                'url': key + '/', 'name': identifier,
                'preview_note': previews.get('note', ''),
                **{k: v['path'] for k, v in previews.get('files', {}).items()},
                'files': [{'path': p, 'url': f'{REPO}/blob/{commit}/' + quote(p, safe='/'),
                           'raw_url': f'https://raw.githubusercontent.com/baiiXin/ClothLOOP-Dataset/{commit}/' + quote(p, safe='/'),
                           'sha256': digest(ROOT / p), 'bytes': (ROOT / p).stat().st_size} for p in files]}

    for x in read(ROOT / 'body_sequences.json'):
        key = f'body/{x["dataset"]}/{x["id"]}'
        row = common(key, x['dataset'], x['id'], 'body', [x['file']])
        row.update({'frames': x['frames'], 'fps': x['fps'], 'fps_status': x.get('fps_status', 'verified'),
                    'duration': x['duration_seconds'], 'category': x.get('category', '未提供'),
                    'description': x.get('description', ''), 'split': x.get('split', 'unassigned'),
                    'processing': x.get('version', 'source_parameters'),
                    'group': x.get('upstream_group', ''), 'metadata': x})
        if x['dataset'] == 'ClothTransformer':
            row['model'] = read((ROOT / x['file']).with_suffix('.json'))
            row['processing_label'] = 'SMPL 反求 · 关节修复'
            row['category_basis'] = '当前精简索引未提供动作类别'
        else:
            row['processing_label'] = '参数保留' if x['dataset'] == 'D-LAYERS' else 'PKL → NPZ 无损参数转存'
            row['category_basis'] = '沿用来源动作说明与已有分类'
        motions.append(row)

    for x in read(ROOT / 'garments.json'):
        slug = x['id'].removesuffix('.obj').replace('::', '__')
        key = f'cloth/{x["dataset"]}/{slug}'
        row = common(key, x['dataset'], x['id'].removesuffix('.obj'), 'cloth', [x['file']])
        raw_name = Path(x['id']).stem
        category = ('套装' if 'combined' in raw_name else '下装' if 'bottom' in raw_name else
                    '上装' if 'top' in raw_name else '未提供')
        row.update({'category': category, 'category_basis': '根据文件名推断；非官方服装类别' if category != '未提供' else '来源未提供类别',
                    'state': 'source_static', 'state_label': '原始静态网格' if x['dataset'] == 'ContourCraft' else '仿真初态',
                    'body_bound': False, 'collision': None, 'metadata': x})
        scene = build_glb(key, [(raw_name, ROOT / x['file'], False)])
        checks.extend(scene.pop('verification'))
        row.update(scene)
        garments.append(row)

    for x in read(ROOT / 'D-LAYERS/garment_body_initials.json'):
        binding_path = ROOT / x['binding']
        binding = read(binding_path)
        parts = [('human', binding_path.parent / binding['human']['file'], True)]
        parts += [(g['name'], binding_path.parent / g['file'], False) for g in binding['garments']]
        key = f'initials/D-LAYERS/{x["sample"]}'
        files = [str(p.relative_to(ROOT)) for _, p, _ in parts] + [x['binding']]
        row = common(key, 'D-LAYERS', x['sample'], 'initials', files)
        row.update({'category': ' + '.join(x['garments']), 'categories': x['garments'],
                    'state': x['state'], 'state_label': '静止姿态' if x['state'] == 'restpose' else '动作首帧',
                    'body_bound': True, 'garment_count': len(x['garments']), 'collision': binding['collision'],
                    'source_sequence': binding.get('source_sequence'), 'metadata': binding,
                    'coordinate_convention': binding['source_coordinate_convention']})
        assert binding['state'] == x['state'] and binding['sample'] == x['sample']
        assert binding['collision']['state'] == x['state']
        scene = build_glb(key, parts, binding['display_transform']['matrix'])
        checks.extend(scene.pop('verification'))
        row.update(scene)
        initials.append(row)

    summary = {'motions': len(motions), 'garments': len(garments), 'initials': len(initials),
               'bound_garments': sum(x['garment_count'] for x in initials),
               'frames': sum(x['frames'] for x in motions), 'duration': sum(x['duration'] for x in motions),
               'assumed_fps_motions': sum(x['fps_status'] == 'assumed_playback' for x in motions),
               'restpose': sum(x['state'] == 'restpose' for x in initials),
               'frame0': sum(x['state'] == 'frame0' for x in initials),
               'sources': sorted({x['source'] for x in motions + garments + initials}),
               'missing_previews': sum('thumbnail' not in x for x in motions + garments + initials),
               'missing_motion_categories': sum(x['category'] == '未提供' for x in motions)}
    catalog = {'schema': 'ClothLOOP.explorer.v1', 'commit': commit, 'repository': REPO, 'summary': summary,
               'body': motions, 'cloth': garments, 'initials': initials}
    write_json(OUT / 'catalog.json', catalog)
    validation = {'schema': 'ClothLOOP.web-export-validation.v1', 'passed': True,
                  'source_manifest_files_verified': len(manifest['files']), 'mesh_count': len(checks),
                  'scene_count': len(garments) + len(initials), 'no_mesh_simplification': True,
                  'export_precision': 'float32 positions/normals; lossless uint16/uint32 indices',
                  'max_abs_coordinate_error': max(x['max_abs_coordinate_error'] for x in checks),
                  'coordinate_error_units': 'Original source units; no meter assumption',
                  'shared_body_garment_transform': True, 'checks': checks}
    write_json(OUT / 'validation.json', validation)
    (OUT.parent / '.nojekyll').touch()
    print(json.dumps({'summary': summary, 'glb_bytes': sum(x['mesh_bytes'] for x in garments + initials),
                      'max_abs_coordinate_error': validation['max_abs_coordinate_error']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
