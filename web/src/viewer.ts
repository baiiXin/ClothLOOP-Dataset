import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import type { Entry } from './types';

export async function mountViewer(host: HTMLElement, item: Entry, assetUrl: string): Promise<() => void> {
  const canvas = host.querySelector<HTMLCanvasElement>('canvas')!;
  const status = host.querySelector<HTMLElement>('[data-viewer-status]')!;
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, preserveDrawingBuffer: true });
  } catch {
    status.textContent = '当前浏览器无法启用 WebGL。可查看下方多视角图片或下载原始网格。';
    host.dataset.state = 'error';
    throw new Error('WebGL unavailable');
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0xf0f2ed);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x72857a, 1.4));
  const keyLight = new THREE.DirectionalLight(0xffffff, 2.0);
  keyLight.position.set(4, 6, 5);
  scene.add(keyLight);
  const fill = new THREE.DirectionalLight(0xdbe9ff, 0.6);
  fill.position.set(-4, 2, -3);
  scene.add(fill);
  const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 10000);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = false;
  controls.autoRotateSpeed = 1;
  let disposed = false;
  let frame = 0;
  const render = () => {
    if (disposed) return;
    renderer.render(scene, camera);
    canvas.dataset.rendered = 'true';
  };
  const resize = () => {
    const { width, height } = canvas.getBoundingClientRect();
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
    render();
  };
  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  controls.addEventListener('change', render);
  const clean = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frame);
    observer.disconnect();
    controls.dispose();
    scene.traverse(object => {
      if (object instanceof THREE.Mesh) {
        object.geometry.dispose();
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        materials.forEach(material => material.dispose());
      }
    });
    renderer.dispose();
    renderer.forceContextLoss();
  };
  let gltf;
  try {
    gltf = await new GLTFLoader().loadAsync(assetUrl, progress => {
      status.textContent = progress.total ? `正在加载三维网格 ${Math.round(progress.loaded / progress.total * 100)}%` : '正在加载三维网格…';
    });
  } catch (error) {
    clean();
    host.dataset.state = 'error';
    status.textContent = '三维网格加载失败。可刷新重试，或查看多视角图片。';
    throw error;
  }
  scene.add(gltf.scene);
  const bounds = new THREE.Box3().setFromObject(gltf.scene);
  const center = bounds.getCenter(new THREE.Vector3());
  const size = bounds.getSize(new THREE.Vector3());
  const extent = Math.max(size.x, size.y, size.z, 0.001);
  camera.near = extent / 1000;
  camera.far = extent * 100;
  controls.minDistance = extent * 0.1;
  controls.maxDistance = extent * 10;
  controls.target.copy(center);
  const setView = (name: string) => {
    const directions: Record<string, number[]> = { front: [0, 0, 1], back: [0, 0, -1],
      side: [1, 0, 0], top: [0, 1, 0.001], reset: [0.55, 0.22, 1] };
    const d = directions[name] || directions.reset;
    const aspect = canvas.clientWidth / Math.max(canvas.clientHeight, 1);
    const distance = extent * (aspect < 1 ? 2.3 : 1.8);
    controls.target.copy(center);
    camera.position.copy(center).add(new THREE.Vector3(...d).normalize().multiplyScalar(distance));
    controls.update();
    render();
  };
  resize();
  setView('reset');
  let meshCount = 0;
  const objects: THREE.Mesh[] = [];
  gltf.scene.traverse(obj => { if (obj instanceof THREE.Mesh) { objects.push(obj); meshCount++; } });
  const toggles = host.querySelector<HTMLElement>('[data-parts]')!;
  for (const [i, obj] of objects.entries()) {
    const label = document.createElement('label');
    label.className = 'part-toggle';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = true;
    checkbox.dataset.part = String(i);
    const span = document.createElement('span');
    span.textContent = item.parts?.[i]?.body ? '人体' : item.parts?.[i]?.name || obj.name;
    checkbox.addEventListener('change', () => { obj.visible = checkbox.checked; render(); });
    label.append(checkbox, span);
    toggles.append(label);
  }
  host.querySelectorAll<HTMLButtonElement>('[data-view]').forEach(button => {
    button.addEventListener('click', () => setView(button.dataset.view!));
  });
  const wire = host.querySelector<HTMLInputElement>('[data-wire]')!;
  wire.addEventListener('change', () => {
    objects.forEach(obj => {
      const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
      for (const material of materials) if (material instanceof THREE.MeshStandardMaterial) material.wireframe = wire.checked;
    });
    render();
  });
  const spin = host.querySelector<HTMLInputElement>('[data-spin]')!;
  let last = 0;
  const animate = (now: number) => {
    if (disposed || !spin.checked || document.hidden) return;
    controls.update(last ? Math.min((now - last) / 1000, 0.1) : 0);
    last = now;
    render();
    frame = requestAnimationFrame(animate);
  };
  const updateSpin = () => {
    cancelAnimationFrame(frame);
    controls.autoRotate = spin.checked;
    last = 0;
    if (spin.checked && !document.hidden) frame = requestAnimationFrame(animate);
  };
  spin.addEventListener('change', updateSpin);
  document.addEventListener('visibilitychange', updateSpin);
  host.dataset.state = 'ready';
  host.dataset.meshCount = String(meshCount);
  status.textContent = `${meshCount} 个部件 · 拖动旋转，滚轮缩放，右键平移`;
  return () => { document.removeEventListener('visibilitychange', updateSpin); clean(); };
}
