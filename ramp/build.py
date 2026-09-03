"""Sweeps a cross-section along a path into a finished ramp mesh."""

import math

import bmesh
import bpy
from mathutils import Vector

# Dihedral angle above which a swept edge stays sharp instead of shading smooth.
SHARP_ANGLE = math.radians(30.0)


def _cumulative(values):
    out = [0.0]
    for value in values:
        out.append(out[-1] + value)
    return out


def _profile_distances(points, closed_loop=True):
    lengths = []
    count = len(points)
    for i in range(count if closed_loop else count - 1):
        y0, z0 = points[i]
        y1, z1 = points[(i + 1) % count]
        lengths.append(math.hypot(y1 - y0, z1 - z0))
    return _cumulative(lengths)


def _path_distances(frames, closed):
    origins = [f.translation for f in frames]
    lengths = []
    for i in range(len(origins) - 1):
        lengths.append((origins[i + 1] - origins[i]).length)
    if closed:
        lengths.append((origins[0] - origins[-1]).length)
    return _cumulative(lengths)


def build(profile, frames, closed, units_per_tile, scale, name):
    """Return a mesh datablock holding the swept ramp.

    profile is a closed CCW polygon in the YZ plane, frames position one ring
    each, and every length is in Hammer units until scale is applied.
    """
    if len(profile) < 3:
        raise ValueError("a ramp profile needs at least three points")
    if len(frames) < 2:
        raise ValueError("a ramp needs at least two rings")

    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    rings = []
    for matrix in frames:
        rings.append([bm.verts.new(matrix @ Vector((0.0, y, z)) * scale) for y, z in profile])
    bm.verts.ensure_lookup_table()

    span = _profile_distances(profile)
    along = _path_distances(frames, closed)
    tile = units_per_tile if units_per_tile > 1e-6 else 1.0
    count = len(profile)

    ring_pairs = list(zip(range(len(rings) - 1), range(1, len(rings))))
    if closed:
        ring_pairs.append((len(rings) - 1, 0))

    for step, (a, b) in enumerate(ring_pairs):
        u0, u1 = along[step] / tile, along[step + 1] / tile
        for j in range(count):
            k = (j + 1) % count
            face = bm.faces.new((rings[a][j], rings[a][k], rings[b][k], rings[b][j]))
            v0, v1 = span[j] / tile, span[j + 1] / tile
            for loop, uv in zip(face.loops, ((u0, v0), (u0, v1), (u1, v1), (u1, v0))):
                loop[uv_layer].uv = uv

    if not closed:
        for ring in (rings[0], rings[-1]):
            cap = bm.faces.new(ring)
            for loop, (y, z) in zip(cap.loops, profile):
                loop[uv_layer].uv = (y / tile, z / tile)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for face in bm.faces:
        face.smooth = True
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            edge.smooth = edge.calc_face_angle(0.0) <= SHARP_ANGLE

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh
