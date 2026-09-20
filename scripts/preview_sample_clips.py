#!/usr/bin/env python3
"""Optional local CPU previews; SMPL models are never copied into the repository."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

os.environ['CUDA_VISIBLE_DEVICES'] = ''
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
import pyvista as pv
from curate_splits import ROOT, load_pose, read, write, sha

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-workspace', type=Path, required=True)
    args = parser.parse_args()
    source = args.source_workspace.resolve()
    tools = source/'body_sequence/data/tools'
    sys.path.insert(0, str(tools))
    from smpl_cpu import SMPL
    model_dir = source/'body_sequence/data/smpl/models'
    media = read(ROOT/'web/media/manifest.json')
    def asset(path, source_file=None):
        record = {'path':str(path.relative_to(ROOT/'web')), 'sha256':sha(path), 'bytes':path.stat().st_size}
        if source_file:
            record.update(source=str(source_file.relative_to(source)), source_sha256=sha(source_file))
        return record
    for sid in ['00396','00756']:
        motion = read(ROOT/f'D-LAYERS/body_sequences/sample_clips/{sid}.json')
        key = f'body/D-LAYERS/{sid}'
        out = ROOT/'web/media'/key;out.mkdir(parents=True,exist_ok=True)
        raw = load_pose(ROOT/motion['file'])
        pose = np.stack(list(raw['poses'].values()));trans = np.stack(list(raw['trans'].values()))
        model_name = ('basicmodel_m_lbs_10_207_0_v1.0.0.pkl' if motion['gender']=='male'
                      else 'basicModel_f_lbs_10_207_0_v1.0.0.pkl')
        model = SMPL(model_dir/model_name)
        vertices,_ = model.forward(pose[:,3:],pose[:,:3],trans,np.zeros(10))
        # Same Z-up to Y-up rotation as initial bindings, followed by a shared
        # display-only centering of the whole motion; no alteration of PKL data.
        vertices = vertices @ np.array([[1,0,0],[0,0,-1],[0,1,0]],dtype=np.float32)
        vertices -= (vertices.min((0,1))+vertices.max((0,1)))/2
        triangles = np.column_stack([np.full(len(model.faces),3),model.faces]).ravel()
        mesh = pv.PolyData(vertices[0],triangles)
        plot = pv.Plotter(off_screen=True,window_size=(640,640));plot.set_background('#f0f2f5')
        plot.add_mesh(mesh,color='#5b8bb0',smooth_shading=True,ambient=.45,diffuse=.6)
        lo,hi = vertices.min((0,1)),vertices.max((0,1));span=max(hi-lo)
        plot.camera_position=[(span*1.6,span*.6,span*2.1),(0,0,0),(0,1,0)]
        plot.camera.parallel_projection=True;plot.camera.parallel_scale=span*.65
        plot.show(auto_close=False,interactive_update=True)
        ff=imageio_ffmpeg.get_ffmpeg_exe();video=out/'video.mp4'
        encoder=subprocess.Popen([ff,'-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','640x640','-r','30','-i','-','-an','-c:v','libx264','-crf','23','-threads','2','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],stdin=subprocess.PIPE)
        font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
        try:
            for index,v in enumerate(vertices):
                mesh.points=v;plot.reset_camera_clipping_range();plot.render()
                im=Image.fromarray(plot.screenshot(return_img=True)[...,:3]);draw=ImageDraw.Draw(im)
                draw.text((12,12),f'{sid} | CMU {motion["source_sequence_id"]} | frame {index}/{len(vertices)-1}',fill='#203249',font=font)
                draw.text((12,35),'30 FPS assumed | preview shape: zero betas',fill='#203249',font=font)
                encoder.stdin.write(im.tobytes())
                if index==len(vertices)//2:
                    im.thumbnail((640,480));im.save(out/'thumbnail.webp',quality=86)
        finally:
            encoder.stdin.close();code=encoder.wait();plot.close()
        assert code==0
        reader=imageio_ffmpeg.read_frames(str(video));next(reader);decoded=sum(1 for _ in reader)
        assert decoded==motion['frames']
        note='按原样本片段重建的人体预览；30 FPS为播放假定。性别来自样本，betas=0仅供显示，不等同于绑定初值的原人体体型。'
        media['records'][key]={'note':note,'files':{'thumbnail':asset(out/'thumbnail.webp'),'video':asset(video)},
            'generation':{'script':'scripts/preview_sample_clips.py','input_sha256':sha(ROOT/motion['file']),
                'model_sha256':sha(model_dir/model_name),'model_gender':motion['gender'],'betas':'zero; preview only',
                'decoded_frames':decoded,'fps_status':'assumed_playback','device':'CPU OSMesa'}}
        initial_key=f'initials/D-LAYERS/{sid}';out_initial=ROOT/'web/media'/initial_key;out_initial.mkdir(parents=True,exist_ok=True)
        src=source/f'cloth/D-LAYERS/processed_p0_p2_20260809/processed/samples/{sid}/frame0.png'
        with Image.open(src) as im:
            im=im.convert('RGB');im.thumbnail((640,480));im.save(out_initial/'thumbnail.webp',quality=86)
        media['records'][initial_key]={'note':'原样本frame0人体与整套服装；保留原网格和共同显示变换。',
                                     'files':{'thumbnail':asset(out_initial/'thumbnail.webp',src)}}
        write(ROOT/'web/media/manifest.json',media)
        print(f'Rendered {sid}: {decoded} frames, {video.stat().st_size} bytes',flush=True)

if __name__=='__main__':
    main()
