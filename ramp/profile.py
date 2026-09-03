"""Ramp cross-sections, as closed polygons in the local YZ plane.

SURGE sweeps along -X, so the cross-section spans Y (width, +Y is right) and
Z (height, base at z = 0). All values are Hammer units; the caller scales.
"""

import math

_EPSILON = 1e-6


def _signed_area(points):
    total = 0.0
    for i, (y0, z0) in enumerate(points):
        y1, z1 = points[(i + 1) % len(points)]
        total += y0 * z1 - y1 * z0
    return total * 0.5


def _dedupe(points):
    out = []
    for p in points:
        if not out or (abs(p[0] - out[-1][0]) > _EPSILON or abs(p[1] - out[-1][1]) > _EPSILON):
            out.append(p)
    while len(out) > 1 and abs(out[0][0] - out[-1][0]) < _EPSILON and abs(out[0][1] - out[-1][1]) < _EPSILON:
        out.pop()
    return out


def _close(points):
    """Deduplicate and force counter-clockwise winding."""
    points = _dedupe(points)
    if _signed_area(points) < 0.0:
        points.reverse()
    return points


def _down_normal(p0, p1):
    """Unit normal of segment p0->p1 on the side facing away from the slope."""
    dy, dz = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dy, dz)
    if length < _EPSILON:
        raise ValueError("degenerate slope segment")
    n = (-dz / length, dy / length)
    return n if n[1] < 0.0 else (-n[0], -n[1])


def _offset_polyline(points, thickness):
    """Offset an open polyline by thickness, mitering interior corners."""
    normals = [_down_normal(points[i], points[i + 1]) for i in range(len(points) - 1)]
    offset = [(points[0][0] + normals[0][0] * thickness,
               points[0][1] + normals[0][1] * thickness)]
    for i in range(1, len(points) - 1):
        offset.append(_miter(points, normals, i, thickness))
    offset.append((points[-1][0] + normals[-1][0] * thickness,
                   points[-1][1] + normals[-1][1] * thickness))
    return offset


def _miter(points, normals, i, thickness):
    """Intersect the two offset lines meeting at points[i]."""
    a0 = (points[i - 1][0] + normals[i - 1][0] * thickness,
          points[i - 1][1] + normals[i - 1][1] * thickness)
    da = (points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
    b0 = (points[i][0] + normals[i][0] * thickness,
          points[i][1] + normals[i][1] * thickness)
    db = (points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])
    denom = da[0] * db[1] - da[1] * db[0]
    if abs(denom) < _EPSILON:
        return b0
    t = ((b0[0] - a0[0]) * db[1] - (b0[1] - a0[1]) * db[0]) / denom
    return (a0[0] + da[0] * t, a0[1] + da[1] * t)


def slope_line(surf, width, height, tip):
    """The surfable edge of the cross-section, low end first."""
    if surf == 'Both':
        return [(-width, tip), (0.0, height), (width, tip)]
    if surf == 'Left':
        return [(width * 0.5, tip), (-width * 0.5, height)]
    return [(-width * 0.5, tip), (width * 0.5, height)]


def slope_angle(width, height, tip):
    """Angle of the surfable face above horizontal, in degrees."""
    if width <= _EPSILON:
        return 90.0
    return math.degrees(math.atan2(max(height - tip, 0.0), width))


def build(style, surf, width, height, tip, thickness):
    """Return the cross-section as a counter-clockwise closed polygon."""
    if width <= _EPSILON or height <= _EPSILON:
        raise ValueError("ramp width and height must be positive")
    tip = min(max(tip, 0.0), height - _EPSILON)

    if style == 'Thin':
        line = slope_line(surf, width, height, tip)
        if thickness <= _EPSILON:
            raise ValueError("thin ramps need a positive thickness")
        return _close(line + list(reversed(_offset_polyline(line, thickness))))

    half = width if surf == 'Both' else width * 0.5
    if surf == 'Both':
        return _close([(-half, 0.0), (half, 0.0), (half, tip), (0.0, height), (-half, tip)])
    if surf == 'Left':
        return _close([(-half, 0.0), (half, 0.0), (half, tip), (-half, height)])
    return _close([(-half, 0.0), (half, 0.0), (half, height), (-half, tip)])
