"""Call frozen ClothLOOP render.py main with a selected-state input adapter.

Only input loading and the video pipe are adapted: normal computation, materials,
lights, camera, ground and shadow setup use the original renderer unchanged.
"""
import os
os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE', '1')
os.environ.setdefault('PYVISTA_OFF_SCREEN', 'true')
os.environ.setdefault('LP_NUM_THREADS', '4')
import argparse
import contextlib
import csv
import importlib.util
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont
from render_task14_hd import sha


def render(job):
    source, output, renderer, evidence, name = job
    src, out = Path(source) / name, Path(output) / name
    evidence = Path(evidence) / name
    out.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    if (out / 'render.json').exists():
        return json.loads((out / 'render.json').read_text())
    assert not (out / 'video.mp4').exists(), 'Preserve incomplete outputs for review'
    original = json.loads((Path(output).parent / 'libuipc' / name / 'render.json').read_text())
    geom = np.load(src / 'geometry.npz')
    body = np.load(src / 'body_vertices.npy', mmap_mode='r')
    cloth = np.load(src / 'reference/cloth.npy', mmap_mode='r')
    n, fps = original['frames'], original['fps']
    rows = list(csv.DictReader((Path(output).parent / 'libuipc' / name / 'iterations.csv').open()))
    assert len(cloth) == len(body) == len(rows) == n
    config = yaml.safe_load((src / 'source_config.yaml').read_text())
    steps = [json.loads(line) for line in (src / 'reference/solver_steps.jsonl').open()]
    timing, cursor = [], 0
    for row in rows:
        count_steps = int(row['physical_steps'])
        part = steps[cursor:cursor + count_steps]
        cursor += count_steps
        assert len(part) == count_steps
        native = all('physical_dt_s' in s for s in part)
        dts = [s['physical_dt_s'] if native else 1 / (config['fps'] * config['substeps']) for s in part]
        if dts:
            assert abs(sum(dts) - 1 / fps) < 1e-9
        timing.append(dict(frame=int(row['frame']), dt_min_s=min(dts) if dts else None,
            dt_max_s=max(dts) if dts else None, interval_s=sum(dts), physical_dt_s=dts,
            provenance='initial' if not dts else 'native_physical_dt_s' if native else 'fixed_source_config_fps_x_substeps'))
    assert cursor == len(steps)
    (out / 'timesteps.json').write_text(json.dumps(dict(units='seconds',
        source_config_sha256=sha(src / 'source_config.yaml'), frames=timing), indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('clothloop_default_render', renderer)
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    # C-IPC panel IDs exceed the upstream palette's eight entries. Reuse colors
    # cyclically without merging components or changing any face/vertex index.
    count = int(geom['component_id'].max()) + 1
    upstream.CLOTH_COMPONENT_COLORS *= (count + 7) // 8
    def load_selected(_path):
        return (np.array(cloth, dtype=np.float32), geom['triangles'].astype(np.int64),
                np.array(body, dtype=np.float32), geom['body_triangles'].astype(np.int64),
                dict(format='lco_unified_rollout_v1', simulation_fps=fps,
                     source_sequence=name, render_label='libuipc | smooth shading'), geom['component_id'])
    upstream.load_rollout = load_selected
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
    titlefont = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 30)
    samples = []
    class AnnotatedPipe:
        def __init__(self, pipe):
            self.pipe, self.frame = pipe, 0
        def write(self, data):
            i, r = self.frame, rows[self.frame]
            self.frame += 1
            im = Image.new('RGB', (1080, 1080), '#182832')
            im.paste(Image.frombytes('RGB', (1080, 880), data), (0, 200))
            draw = ImageDraw.Draw(im)
            draw.text((25, 12), f'libuipc / {name} / smooth shading', font=titlefont, fill='white')
            draw.text((25, 65), f'Frame {i:04d}/{n-1}   t={i/fps:.3f}s   {fps:g} FPS   {r["method"]}', font=font, fill='white')
            draw.text((25, 108), f'Substeps: {r["physical_steps"]}   Nonlinear: {int(r["nonlinear_iterations"]):,}   Linear: {int(r["linear_iterations"]):,}   Solve: {float(r["solver_seconds"]):.2f}s', font=font, fill='white')
            t = timing[i]
            if t['dt_min_s'] is None:
                dt_label = 'dt: -- (initial state, no physical step)'
            elif abs(t['dt_max_s'] - t['dt_min_s']) < 1e-10:
                dt_label = f'dt: {1000*t["dt_min_s"]:.6f} ms per step'
            else:
                dt_label = f'dt: {1000*t["dt_min_s"]:.6f} - {1000*t["dt_max_s"]:.6f} ms (min-max)'
            draw.text((25, 151), dt_label + f' | sum dt: {1000*t["interval_s"]:.6f} ms', font=font, fill='#b2c6ce')
            self.pipe.write(im.tobytes())
            if i in {0, n // 2, n - 1}:
                samples.append(im.resize((540, 540)))
                if i == 0:
                    im.save(out / 'poster.jpg', quality=92)
            return len(data)
        def close(self):
            self.pipe.close()
    pipes = []
    def start(output_path, width, height, rate):
        assert (width, height, rate) == (1080, 880, fps)
        proc = subprocess.Popen(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
            '-video_size', '1080x1080', '-framerate', str(rate), '-i', '-', '-an', '-c:v', 'libx264',
            '-preset', 'fast', '-crf', '20', '-maxrate', '1800k', '-bufsize', '3600k', '-threads', '2',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output_path)], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.stdin = AnnotatedPipe(proc.stdin)
        pipes.append(proc.stdin)
        return proc
    upstream.start_ffmpeg = start
    sys.argv = [str(renderer), str(src), '--output', str(out / 'video.mp4'),
                '--width', '1080', '--height', '880', '--fps', str(fps), '--body-subdiv', '0', '--azim', '72']
    print(f'START smooth {name}: {n} frames using ClothLOOP render.py', flush=True)
    with (evidence / 'render.log').open('w') as log, contextlib.redirect_stdout(log):
        upstream.main()
    assert pipes[0].frame == n
    target = out / 'video.mp4'
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=nb_frames,r_frame_rate,width,height,duration', '-of', 'json', str(target)]))['streams'][0]
    assert int(probe['nb_frames']) == n and probe['width'] == probe['height'] == 1080
    subprocess.run(['ffmpeg', '-v', 'error', '-threads', '2', '-i', str(target), '-f', 'null', '-'], check=True)
    sheet = Image.new('RGB', (1620, 540))
    for k, im in enumerate(samples):
        sheet.paste(im, (k * 540, 0))
    sheet.save(out / 'contact.jpg', quality=90)
    for path, digest in original['source_sha256'].items():
        assert sha(src / path) == digest
    record = {**original, 'bytes': target.stat().st_size, 'video_sha256': sha(target), 'ffprobe': probe,
        'renderer': 'ClothLOOP render.py main, unchanged upstream code; selected-state loader + annotation/encoding pipe adapter',
        'renderer_commit': subprocess.check_output(['git', '-C', str(Path(renderer).parent), 'rev-parse', 'HEAD'], text=True).strip(),
        'renderer_sha256': sha(Path(renderer)), 'shading': 'area-weighted vertex normals recalculated each frame, upstream smooth_shading=True',
        'geometry': 'No geometric smoothing or subdivision. Original topology; float32 display conversion and shared translation/axis transform from default renderer.',
        'display_ground': 'Default rendering-only grid/shadows; not a simulated floor/contact constraint.',
        'palette': 'Default ClothLOOP colors, repeated after eight entries for C-IPC panels; component IDs unchanged.',
        'body_subdiv': 0, 'camera_azimuth_degrees': 72, 'timestep_provenance': sorted({r['provenance'] for r in timing}),
        'timestep_definition': 'Native physical_dt_s; where absent, fixed dt from sealed config fps*substeps. Nonuniform CC01/144 timeline is precompiled collider replay, not an online time-step controller.'}
    (out / 'render.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'DONE smooth {name}: {record["bytes"]} bytes', flush=True)
    return record


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--renderer', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--case')
    p.add_argument('--workers', type=int, default=2)
    a = p.parse_args()
    index = json.loads((a.source / 'index.json').read_text())
    cases = [a.case] if a.case else sorted(r['case'] for r in index['cases'])
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        records = list(pool.map(render, [(str(a.source), str(a.output), str(a.renderer), str(a.evidence), c) for c in cases]))
    if a.case:
        return
    old = json.loads((a.output.parent / 'libuipc/index.json').read_text())
    total = sum(r['bytes'] for r in records)
    assert total + old['video_bytes'] < 120_000_000
    (a.output / 'index.json').write_text(json.dumps(dict(schema='ClothLOOP.libuipc-smooth-preview.v1',
        video_bytes=total, combined_video_bytes=total + old['video_bytes'], cases=records), indent=2) + '\n')


if __name__ == '__main__':
    main()
