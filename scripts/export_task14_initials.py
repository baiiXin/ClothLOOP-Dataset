#!/usr/bin/env python3
"""One-time exact first-frame export; not required by the portable website build."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'testsets/task14_initials_20260929'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def size_tree(root, excluded=()):
    directories, files, stack = set(), {}, [root]
    while stack:
        p = stack.pop()
        if p.name in excluded:
            continue
        st = p.stat()  # Broken links are errors, not silently omitted.
        key = (st.st_dev, st.st_ino)
        if p.is_dir():
            if key not in directories:
                directories.add(key)
                stack.extend(p.iterdir())
        elif p.is_file():
            files[key] = st.st_size
    return dict(bytes=sum(files.values()), unique_files=len(files))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--selected', type=Path, required=True)
    parser.add_argument('--audit-output', type=Path, required=True)
    args = parser.parse_args()
    source = args.selected.resolve()
    index = json.loads((source / 'index.json').read_text())
    proof = json.loads((source / 'revalidation.json').read_text())
    assert index['complete'] and index['accepted_cases'] == 14
    assert proof['passed'] and proof['index_sha256'] == digest(source / 'index.json')
    assert not (DEST / 'index.json').exists(), 'Preserve an existing publication'
    cases, comparisons = [], []
    for item in index['cases']:
        case = item['case']
        folder, out = source / case, DEST / 'cases' / case
        out.mkdir(parents=True, exist_ok=False)
        initial = np.load(folder / 'initial_state.npz', allow_pickle=False)
        garment = np.load(folder / 'geometry.npz', allow_pickle=False)
        meta = json.loads((folder / 'case.json').read_text())
        assert digest(folder / 'initial_state.npz') == meta['exported_initial_sha256']
        assert digest(folder / 'geometry.npz') == meta['geometry_sha256']
        assert digest(folder / 'source_acceptance.json') == meta['source_certificate_sha256']
        run = folder / 'reproduction/run'
        with (run / 'geometry.jsonl').open() as stream:
            geometry = json.loads(next(stream))
        x, b = initial['cloth_positions'], initial['body_positions']
        assert geometry['frame'] == 0 and geometry['cloth_cloth'] == geometry['cloth_body'] == 0
        assert hashlib.sha256(x.tobytes() + b.tobytes()).hexdigest() == geometry['geometry_sha256']
        np.savez_compressed(out / 'body.npz', vertices=b, faces=garment['body_triangles'])
        np.savez_compressed(out / 'cloth.npz', vertices=x, faces=garment['triangles'],
                            component_id=garment['component_id'], component_names=garment['component_names'])
        for filename, vertices, faces in [('body.npz', b, garment['body_triangles']),
                                           ('cloth.npz', x, garment['triangles'])]:
            actual = np.load(out / filename, allow_pickle=False)
            assert np.array_equal(actual['vertices'], vertices) and actual['vertices'].dtype == vertices.dtype
            assert np.array_equal(actual['faces'], faces) and actual['faces'].dtype == faces.dtype
        thumbnail = source.parents[1] / 'initialization_observation1' / case / 'selected_initial.jpg'
        assert thumbnail.is_file()
        shutil.copyfile(thumbnail, out / 'preview.jpg')
        group = ('ClothTransformer' if case.startswith('ct_') else 'ContourCraft' if case.startswith('cc_')
                 else 'C-IPC' if case.startswith('cipc_') else 'D-LAYERS')
        provenance = dict(case=case, state='frame0', units='metres', up_axis='Y',
            source='Task14 observation1 final selected dataset', source_frame=0,
            source_initial_sha256=meta['exported_initial_sha256'], source_geometry_sha256=meta['geometry_sha256'],
            source_acceptance_sha256=meta['source_certificate_sha256'],
            source_selection_sha256=proof['selection_sha256'], source_index_sha256=proof['index_sha256'],
            geometry_check=geometry, source_vertices_and_topology_exact=True,
            display_transform='identity; body and cloth always share coordinates',
            limitations='First frame only. Body surface includes accepted repairs where applicable. '
                        'Body self-intersections are not certified zero. No continuous-time proof. '
                        'No full trajectories, material rest mesh, initial velocity or SMPL model included.',
            components=garment['component_names'].tolist(),
            component_note='C-IPC components are sewing panels, not a garment count.')
        write(out / 'provenance.json', provenance)
        cases.append(dict(case=case, source=group, state='frame0',
            body=str((out / 'body.npz').relative_to(ROOT)), cloth=str((out / 'cloth.npz').relative_to(ROOT)),
            preview=str((out / 'preview.jpg').relative_to(ROOT)),
            provenance=str((out / 'provenance.json').relative_to(ROOT)),
            components=provenance['components']))
        comparisons.append(dict(case=case, positions_exact=True, faces_exact=True,
                                checked_geometry_hash=geometry['geometry_sha256']))
    mesh_bytes = sum((ROOT / c[k]).stat().st_size for c in cases for k in ['body', 'cloth'])
    write(DEST / 'index.json', dict(schema='ClothLOOP.task14-initials.v1', cases=cases,
        initial_mesh_bytes=mesh_bytes, scope='14 selected joint frame-zero meshes only; no motion data'))
    payload = [p for p in DEST.rglob('*') if p.is_file()]
    write(DEST / 'manifest.json', dict(files=[dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size,
        sha256=digest(p)) for p in sorted(payload)], scope='Initial meshes, previews, provenance and index'))
    report = dict(passed=True, cases=comparisons, initial_mesh_bytes=mesh_bytes,
        selected_total_following_symlinks_deduplicated=size_tree(source),
        selected_excluding_reproduction=size_tree(source, ('reproduction',)),
        size_policy='Logical file bytes, symlinks followed, files deduplicated by device/inode; no failed trials.',
        publication_payload_bytes=sum(p.stat().st_size for p in DEST.rglob('*') if p.is_file()))
    write(args.audit_output, report)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
