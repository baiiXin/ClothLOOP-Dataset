"""Offline CPU renderer of sealed selected source states; never modifies inputs.

Requires numpy, pyvista, Pillow and ffmpeg (not a website build dependency).
"""
import os
os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE', '1')
os.environ.setdefault('PYVISTA_OFF_SCREEN', 'true')
os.environ.setdefault('LP_NUM_THREADS', '4')
import argparse
import csv
import hashlib
import json
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw, ImageFont


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def render(job):
    source, output, case = map(Path, job)
    src = source / case
    out = output / case
    if (out / 'render.json').exists():
        return json.loads((out / 'render.json').read_text())
    out.mkdir(parents=True, exist_ok=True)
    meta = json.loads((src / 'case.json').read_text())
    cloth = np.load(src / 'reference/cloth.npy', mmap_mode='r')
    body = np.load(src / 'body_vertices.npy', mmap_mode='r')
    geom = np.load(src / 'geometry.npz')
    n, fps = meta['source_frames'], meta['fps']
    assert len(cloth) == len(body) == n
    raw = list(csv.DictReader((src / 'reference/iterations_per_frame.csv').open()))
    assert len(raw) == n
    rows = []
    for i, r in enumerate(raw):
        assert int(r['frame']) == i
        assert abs(float(r['time_s']) - i / fps) < 1e-6
        rows.append(dict(frame=i, time_s=float(r['time_s']),
                         physical_steps=int(r.get('substeps', r.get('physical_steps'))),
                         nonlinear_iterations=int(r.get('iterations', r.get('newton_iterations'))),
                         linear_iterations=int(r['linear_iterations']),
                         solver_seconds=float(r['seconds']),
                         method=r.get('iteration_method', r.get('iteration_methods'))))
    with (out / 'iterations.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    def mesh(v, faces):
        return pv.PolyData(v.copy(), np.c_[np.full(len(faces), 3), faces].ravel())
    plot = pv.Plotter(off_screen=True, window_size=(1080, 880))
    plot.enable_anti_aliasing('fxaa')
    plot.set_background('#edf0f4')
    bm, cm = mesh(body[0], geom['body_triangles']), mesh(cloth[0], geom['triangles'])
    palette = np.array([[40, 158, 143], [230, 173, 67], [173, 83, 99], [98, 126, 176]], np.uint8)
    cm.cell_data['color'] = palette[geom['component_id'][geom['triangles'][:, 0]] % 4]
    plot.add_mesh(bm, color='#bdb6b0', smooth_shading=False)
    plot.add_mesh(cm, scalars='color', rgb=True, smooth_shading=False)
    # Fixed camera scale across the entire motion; tracking translation only.
    span = max(1.8, max(float(np.ptp(np.concatenate([body[i], cloth[i]]), axis=0).max()) for i in range(n)))
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
    titlefont = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
    target = out / 'video.mp4'
    if target.exists():
        raise RuntimeError(f'Incomplete existing output must be reviewed: {target}')
    proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', '1080x1080', '-framerate', str(fps), '-i', '-', '-an', '-c:v', 'libx264',
        '-preset', 'fast', '-crf', '20', '-maxrate', '2300k', '-bufsize', '4600k',
        '-threads', '2', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)], stdin=subprocess.PIPE)
    samples = []
    try:
        for i, r in enumerate(rows):
            bm.points = np.asarray(body[i]).copy()
            cm.points = np.asarray(cloth[i]).copy()
            verts = np.concatenate([body[i], cloth[i]])
            center = (verts.min(0) + verts.max(0)) / 2
            plot.camera.position = center + span * np.array([.6, .2, 2.8])
            plot.camera.focal_point = center
            plot.camera.up = (0, 1, 0)
            plot.camera.parallel_projection = True
            plot.camera.parallel_scale = .59 * span
            plot.reset_camera_clipping_range()
            plot.render()
            im = Image.new('RGB', (1080, 1080), '#182832')
            im.paste(Image.fromarray(plot.screenshot(return_img=True)[:, :, :3]), (0, 200))
            draw = ImageDraw.Draw(im)
            draw.text((25, 12), f'libuipc  /  {case.name}', font=titlefont, fill='white')
            draw.text((25, 65), f'Frame {i:04d}/{n-1}   t={i/fps:.3f}s   {fps:g} FPS   {r["method"]}', font=font, fill='white')
            draw.text((25, 108), f'Substeps: {r["physical_steps"]}   Nonlinear: {r["nonlinear_iterations"]:,}   Linear: {r["linear_iterations"]:,}   Solve: {r["solver_seconds"]:.2f}s', font=font, fill='white')
            draw.text((25, 151), 'Iterations summed over this source-frame interval; frame 0 = initial.', font=font, fill='#b2c6ce')
            proc.stdin.write(im.tobytes())
            if i in {0, n // 2, n - 1}:
                samples.append(im.resize((540, 540)))
                if i == 0:
                    im.save(out / 'poster.jpg', quality=92)
            if i % 120 == 0:
                print(f'{case}: {i}/{n}', flush=True)
    finally:
        proc.stdin.close()
        rc = proc.wait()
        plot.close()
    assert rc == 0
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=nb_frames,r_frame_rate,width,height,duration', '-of', 'json', str(target)]))['streams'][0]
    assert int(probe['nb_frames']) == n
    subprocess.run(['ffmpeg', '-v', 'error', '-threads', '2', '-i', str(target), '-f', 'null', '-'], check=True)
    sheet = Image.new('RGB', (1620, 540))
    for k, im in enumerate(samples):
        sheet.paste(im, (k * 540, 0))
    sheet.save(out / 'contact.jpg', quality=90)
    record = dict(case=case.name, frames=n, fps=fps,
        fps_status='assumed_playback' if case.name.startswith('dlayers') else 'project_defined',
        width=1080, height=1080, bytes=target.stat().st_size, video_sha256=sha(target),
        methods=sorted({r['method'] for r in rows[1:]}),
        total_nonlinear_iterations=sum(r['nonlinear_iterations'] for r in rows),
        total_physical_steps=sum(r['physical_steps'] for r in rows),
        iteration_definition='Native logged counters summed over physical substeps ending in each source-frame interval. Frame0 has no solve. Mixed/semi-implicit counts are not claimed to be full Newton.',
        geometry='Exact saved source states and actual repaired collider; no smoothing, interpolation or new simulation.',
        collision_scope='All saved source states CC=CB=0; not a continuous-time formal proof; body self-intersection not certified zero.',
        source_sha256={p: sha(src / p) for p in ['case.json', 'geometry.npz', 'reference/cloth.npy', 'body_vertices.npy', 'reference/iterations_per_frame.csv', 'reference/solver_steps.jsonl']},
        source_certificate_sha256=meta['source_certificate_sha256'], ffprobe=probe)
    (out / 'render.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'DONE {case}: {record["bytes"]} bytes', flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case')
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    index = json.loads((args.source / 'index.json').read_text())
    cases = [args.case] if args.case else sorted(x['case'] for x in index['cases'])
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        records = list(pool.map(render, [(str(args.source), str(args.output), c) for c in cases]))
    if args.case:
        return
    total = sum(r['bytes'] for r in records)
    assert len(records) == 14 and sum(r['frames'] for r in records) == 8081
    assert total < 100_000_000, total
    (args.output / 'index.json').write_text(json.dumps(dict(schema='ClothLOOP.libuipc-preview.v1',
        video_bytes=total, source_index_sha256=sha(args.source / 'index.json'), cases=records), indent=2) + '\n')


if __name__ == '__main__':
    main()
