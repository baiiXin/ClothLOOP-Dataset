# Geometry-only first-frame candidate

The exported coordinates use a strictly rechecked geometry seed taken from the
last iterate of `results/transfer/cipc_dress_knife/ipc_seam_relax_v1`.
That numerical dynamics trial **failed** at its first step: 1024 Newton iterations,
5.597 mm displacement residual, 105.36 seconds for the attempted step. It did not
produce a converged time step or a completed relaxation sequence. None is claimed.

The iterate is useful only as a local geometric correction: the original body,
cloth topology, material rest, point-edge stitch indices and interpolation ratios
remain unchanged. Independent strict edge-face, containment, triangle-quality and
actual-view checks must decide this first-frame candidate; solver convergence is
not inferred from them. The complete native failure, preliminary clean candidate,
all original intersection events and subsequent geometric checks remain on disk.

Maximum cloth displacement from the native source is 5.039 mm. The finite stitch
gap is at most 3.541 mm (source maximum 0.220 mm); this local seam opening is a
disclosed limitation and the state is not certified as mechanical equilibrium.
