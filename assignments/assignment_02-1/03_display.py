"""
Crocheted Calabi-Yau, step 3 of 3: THE VIEW - Grasshopper Python 3 component.
Turns the grown half-patch from step 2 into Rhino geometry:
    - copies it to all n^2 patches and to both sides (+b, -b) by exact 4D rotations / mirroring,
    - draws the 4D point (Re z1, Im z1, Re z2, Im z2) in 3D as
          (Re z1, Re z2, cos(alpha) * Im z1 + sin(alpha) * Im z2),
    - joins every row to the next with triangles and colours the meshes.
Changing these inputs only re-runs this step; the fabric is not grown again.

Inputs (Item Access):
    fabric     : object          output 'fabric' of step 2 (no type hint)
    alpha      : float  (45)     projection angle in degrees (rotates the 4D -> 3D view)
    scale      : float  (1.0)
    color_mode : int    (0)      0 = colour by patch, 1 = colour by generation (age)
Outputs:
    meshes     : n*n grown, coloured patch meshes (empty at generation 0)
    mould      : the Calabi-Yau the fabric grew on, same extent (for comparison)
    rows       : every stitch row as a polyline (all patches)
    seed_chain : the base chain (generation 0) as polylines
    info       : text summary
"""

import math
import colorsys
import Rhino.Geometry as rg
import System.Drawing as sd


def project(p, alpha):
    """4D -> 3D view."""
    return (p[0], p[2], math.cos(alpha) * p[1] + math.sin(alpha) * p[3])


# ---- colours ----------------------------------------------------------------------------
def patch_color(k1, k2, n):
    """Hue from k1, brightness from k2: neighbouring patches read as distinct tiles."""
    hue = (k1 / float(n)) * 0.85
    val = 0.55 + 0.45 * (k2 / float(max(n - 1, 1)))
    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, val)
    return sd.Color.FromArgb(255, int(r * 255), int(g * 255), int(b * 255))


def age_color(g, g_last):
    """Base chain warm (orange), newest row cool (blue)."""
    t = g / float(max(g_last, 1))
    r, gg, b = colorsys.hsv_to_rgb(0.08 + 0.55 * t, 0.85, 0.95 - 0.25 * t)
    return sd.Color.FromArgb(255, int(r * 255), int(gg * 255), int(b * 255))


GREY = sd.Color.FromArgb(255, 200, 200, 200)


# ---- meshes -----------------------------------------------------------------------------
def zipper(mesh, A, B):
    """Join two rows of vertex indices (different lengths allowed) with triangles."""
    p, q = len(A) - 1, len(B) - 1
    i = j = 0
    while i < p or j < q:
        if j == q or (i < p and (i + 1) / float(p) <= (j + 1) / float(q)):
            mesh.Faces.AddFace(A[i], A[i + 1], B[j])
            i += 1
        else:
            mesh.Faces.AddFace(A[i], B[j + 1], B[j])
            j += 1


def build_patch(mould, full_rows, pts, k1, k2, alpha, scale, colors):
    """full_rows: list of (generation, mirror, vertex indices) from -b to +b.
    colors(g) gives the vertex colour. Returns (mesh or None, row polylines)."""
    mesh = rg.Mesh()
    idx_rows, polylines = [], []
    for g, mirror, idx in full_rows:
        col = colors(g)
        out, pl = [], rg.Polyline()
        for v in idx:
            x, y, z = project(mould.to_patch(pts[v], k1, k2, mirror), alpha)
            pt = rg.Point3d(x * scale, y * scale, z * scale)
            out.append(mesh.Vertices.Count)
            mesh.Vertices.Add(pt)
            mesh.VertexColors.Add(col)
            pl.Add(pt)
        idx_rows.append(out)
        polylines.append(pl)
    for A, B in zip(idx_rows, idx_rows[1:]):
        zipper(mesh, A, B)
    if mesh.Faces.Count == 0:
        return None, polylines
    mesh.Normals.ComputeNormals()
    mesh.Compact()
    return mesh, polylines


alpha_rad = math.radians(alpha)
M = fabric.mould
half, P, T = fabric.rows, fabric.P, fabric.T
n, g_last = M.n, half[-1][0]

# mirror the rows to -b ("turn work"); the base chain is shared by both sides
full_rows = [(g, True, idx) for g, b, idx in reversed(half[1:])] + [(g, False, idx) for g, b, idx in half]

meshes, mould, rows, seed_chain = [], [], [], []
for k1 in range(n):
    for k2 in range(n):
        pc = patch_color(k1, k2, n)
        colors = (lambda g, pc=pc: pc) if color_mode == 0 else (lambda g: age_color(g, g_last))
        m, pls = build_patch(M, full_rows, P, k1, k2, alpha_rad, scale, colors)
        if m is not None:
            meshes.append(m)
            mm, _ = build_patch(M, full_rows, T, k1, k2, alpha_rad, scale, lambda g: GREY)
            mould.append(mm)
        rows.extend(pl.ToPolylineCurve() for pl in pls)
        seed_chain.append(pls[len(half) - 1].ToPolylineCurve())   # the b = 0 row

# ---- summary ----------------------------------------------------------------------------
patches = n * n
counts = [patches * (len(idx) - 1) * (1 if g == 0 else 2) for g, b, idx in half]
last_idx = half[-1][2]
dist4 = M.dist4
deviation = sum(dist4(P[v], T[v]) for v in last_idx) / len(last_idx)
fabric_len = sum(dist4(P[u], P[v]) for u, v in zip(last_idx, last_idx[1:]))
mould_len = sum(dist4(T[u], T[v]) for u, v in zip(last_idx, last_idx[1:]))
info = ("generations {}  (stopped by {})  b reached {:.3f}  patches {}\n"
        "stitches per row per patch: base {} -> last {} (mould needs {})\n"
        "newest row: fabric {:.2f} x longer than the mould row (ruffle factor)\n"
        "newest row: mean distance from mould {:.4f}  ({:.2f} stitch widths)\n"
        "total stitches {}").format(
    g_last, fabric.stopped_by, half[-1][1], patches,
    len(half[0][2]) - 1, len(last_idx) - 1, M.schedule[len(half) - 1][2],
    fabric_len / mould_len, deviation, deviation / M.stitch_w, sum(counts))
