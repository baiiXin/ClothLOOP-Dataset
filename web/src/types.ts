export type Section = 'body' | 'cloth' | 'initials' | 'test-initials';
export interface DataFile { path: string; url: string; raw_url: string; sha256: string; bytes: number }
export interface Part { name: string; body: boolean; vertices: number; triangles: number; file: string; sha256: string }
export interface Collision {
  state: string; counts: Record<string, number>; clothing_related_all_zero: boolean;
  human_self_intersections: number; recomputed: boolean; source_report_sha256: string;
  mesh_order: Record<string, string>;
}
export interface Entry {
  key: string; id: string; kind: Section; source: string; url: string; name: string;
  thumbnail?: string; contact?: string; video?: string; preview_note: string;
  category: string; category_basis?: string; description?: string; categories?: string[];
  frames?: number; fps?: number; fps_status?: string; duration?: number;
  processing?: string; processing_label?: string; group?: string; split?: string;
  mesh?: string; mesh_bytes?: number; parts?: Part[]; vertices?: number; triangles?: number;
  state?: string; state_label?: string; body_bound?: boolean; garment_count?: number;
  collision?: Collision | null; metadata: unknown; model?: Record<string, unknown>;
  initial_geometry_check?: { cloth_cloth: number; cloth_body: number; frame: number };
  simulation?: { frames: number; fps: number; fps_status: string; width: number; height: number;
    bytes: number; methods: string[]; total_nonlinear_iterations: number; total_physical_steps: number;
    poster: string; iterations: string; provenance: string };
  files: DataFile[]; source_sequence?: Record<string, unknown>;
  related_url?: string;
  source_segment?: { source_sequence_id: string; start_inclusive: number; end_exclusive: number };
}
export interface Catalog {
  schema: string; commit: string; repository: string;
  summary: { motions: number; garments: number; initials: number; bound_garments: number;
    test_initials: number; test_initial_mesh_bytes: number;
    frames: number; duration: number; assumed_fps_motions: number; restpose: number; frame0: number;
    sources: string[]; missing_previews: number; missing_motion_categories: number;
    body_splits: Record<string, number> };
  body: Entry[]; cloth: Entry[]; initials: Entry[]; 'test-initials': Entry[];
}
