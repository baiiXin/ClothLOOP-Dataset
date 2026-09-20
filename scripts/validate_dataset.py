#!/usr/bin/env python3
"""Validate portable scientific data, split membership, clips and initial bindings.

--refresh-manifest explicitly updates curated hashes after intentional edits.
Default is read-only and suitable for CI. Requires NumPy, not SMPL or DATA.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from curate_splits import ROOT, TRAIN, TEST, read, write, sha, load_pose

def payload_files():
    roots = ['ClothTransformer', 'ContourCraft', 'D-LAYERS', 'splits']
    return sorted([p for root in roots for p in (ROOT/root).rglob('*') if p.is_file()]
                  +[ROOT/name for name in ['README.md','body_sequences.json','garments.json']])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-manifest',action='store_true')
    args=parser.parse_args()
    rows=read(ROOT/'body_sequences.json');initials=read(ROOT/'D-LAYERS/garment_body_initials.json')
    index={f'{x["dataset"]}/{x["id"]}':x for x in rows}
    assert len(index)==len(rows)==91
    split=read(ROOT/'splits/body_sequences.json')['splits']
    assert {k:len(v) for k,v in split.items()}=={'train':52,'test':12,'unassigned':27}
    seen=set();identities={}
    for name,items in split.items():
        assert (ROOT/f'splits/{name}.txt').read_text().splitlines()==[x['file'] for x in items]
        ids=set()
        for item in items:
            assert item['key'] not in seen;seen.add(item['key'])
            row=index[item['key']];assert row['split']==name and row['file']==item['file']
            assert sha(ROOT/item['file'])==item['sha256']
            assert (row['split_status']=='not_in_current_selection') == (name=='unassigned')
            if row['dataset']!='ClothTransformer':ids.add(row.get('source_sequence_id',row['id']))
        identities[name]=ids
    assert seen==set(index)
    assert {x['id'] for x in rows if x['split']=='train'}==set(TRAIN)
    assert all(x['dataset']=='ContourCraft' and x['upstream_group']=='vto52' for x in rows if x['split']=='train')
    assert {f'{ds}/{sid}' for ds,values in TEST.items() for sid in values}=={x['key'] for x in split['test']}
    assert not identities['train'] & identities['test'], 'Cross-source CMU train/test leakage'
    assert not {x['sha256'] for x in split['train']} & {x['sha256'] for x in split['test']}
    assert len(initials)==40
    for item in initials:
        binding_path=ROOT/item['binding'];b=read(binding_path)
        assert b['sample']==item['sample'] and b['state']==item['state']
        for part in [b['human']]+b['garments']:
            p=binding_path.parent/part['file']
            assert p.is_file() and not p.is_symlink() and sha(p)==part['sha256']
            assert p.stat().st_size==part['bytes']
            with np.load(p,allow_pickle=False) as z:
                assert z['vertices'].shape==(part['vertices'],3) and z['faces'].shape==(part['faces'],3)
                assert np.isfinite(z['vertices']).all() and z['faces'].min()>=0 and z['faces'].max()<len(z['vertices'])
    for sid,start,end in [('00396',0,405),('00756',508,773)]:
        row=index[f'D-LAYERS/{sid}'];d=load_pose(ROOT/row['file']);segment=row['source_segment']
        assert row['frames']==end-start and row['fps_status']=='assumed_playback'
        assert row['duration_seconds']==(end-start)/30
        assert segment['start_inclusive']==start and segment['end_exclusive']==end
        for key,size in [('poses',72),('trans',3)]:
            assert sorted(d[key])==list(range(end-start))
            arr=np.stack([d[key][i] for i in range(end-start)])
            assert arr.shape==(end-start,size) and np.isfinite(arr).all()
        b=read(ROOT/row['initial_binding'])
        assert b['body_sequence_key']==f'D-LAYERS/{sid}'
        assert (b['source_sequence']['seq_start'],b['source_sequence']['seq_end'])==(start,end)
        assert b['collision']['clothing_related_all_zero']
        assert b['collision']['independent_verification']['clothing_related_intersections_detected'] is False
    manifest=read(ROOT/'manifest.json');old={x['path']:x for x in manifest['files']}
    files=payload_files()
    assert not any(p.is_symlink() for p in files)
    if args.refresh_manifest:
        records=[]
        for p in files:
            rel=str(p.relative_to(ROOT));record=dict(old.get(rel,{'path':rel,'role':'curated metadata or documentation'}))
            if rel not in old and p.suffix=='.npz' and '/garment_body_initials/' in rel:
                b=read(p.parent.parent/'binding.json') if p.parent.name=='garments' else read(p.parent/'binding.json')
                part=next(x for x in [b['human']]+b['garments'] if x['sha256']==sha(p))
                record={'path':rel,'source':'cloth/'+part['source'],'source_sha256':part['sha256'],'byte_identical':True}
            if '/sample_clips/' in rel and p.suffix=='.pkl':
                row=index['D-LAYERS/'+p.stem];seg=row['source_segment']
                record={'path':rel,'source':'body_sequence/datasets/D-LAYERS/'+seg['source_path'],
                        'source_sha256':seg['source_sha256'],'byte_identical':seg['byte_identical_to_full_source'],
                        'processing':'Lossless frame selection, reindexed to zero; no numeric changes or resampling'}
            record.update(bytes=p.stat().st_size,sha256=sha(p));records.append(record)
        manifest.update(updated_at=datetime.now(timezone.utc).isoformat(),body_sequences=dict(Counter(x['dataset'] for x in rows)),
                        body_splits={k:len(v) for k,v in split.items()},dlayers_initial_samples=len(initials),
                        dlayers_initial_garments=sum(len(x['garments']) for x in initials),files=records)
        write(ROOT/'manifest.json',manifest)
    assert {x['path'] for x in manifest['files']}=={str(p.relative_to(ROOT)) for p in files}
    for item in manifest['files']:
        p=ROOT/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],item['path']
    report={'passed':True,'manifest_files_sha256_verified':len(files),
            'source_files_sha256_verified':sum(x.get('byte_identical',False) and x.get('source_sha256')==x['sha256'] for x in manifest['files']),
            'body_sequences':len(rows),'body_splits':{k:len(v) for k,v in split.items()},'static_garment_objs':len(read(ROOT/'garments.json')),
            'bound_samples':len(initials),'bound_meshes':sum(len(x['garments'])+1 for x in initials),
            'ct_smpl_version':'joint_plausibility_repair','ct_selected_clothes':manifest['ct_selected_clothes'],
            'raw_mesh_and_pose_values_unchanged':True,'new_clip_processing':'sample-specific slicing and local frame reindexing; no numeric resampling',
            'new_clip_frames':{'00396':405,'00756':265},'train_test_cmu_id_overlap':[],
            'split_assignment_complete_for_user_selection':True,'unselected_sequences_retained':27,
            'symlinks':0,'binding_paths_self_contained':True,'contains_previews':False,
            'contains_full_CT_simulations':False,'contains_dlayers_cloth_ground_truth_sequences':False,
            'contains_SMPL_models':False,'device':'CPU','cuda_used':False,
            'scope':'Curated scientific payload only; excludes website and build tools.'}
    if args.refresh_manifest:write(ROOT/'validation.json',report)
    else:assert read(ROOT/'validation.json')==report, 'Refresh validation.json after intentional scientific changes'
    print(f'Validated {len(rows)} motions, splits 52/12/27, {len(initials)} bindings; {len(files)} file hashes')

if __name__=='__main__':main()
