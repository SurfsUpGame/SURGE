"""Headless regression tests for the SURGE ramp generator."""

import math

import bmesh
import bpy

from .. import props
from ..ramp import path, profile
from ..units import HAMMER_TO_METERS, SURF_MIN_ANGLE

STYLES = ('Wedge', 'Thin')
SURFS = ('Left', 'Right', 'Both')
SHAPES = ('Straight', 'Left', 'Right', 'Up', 'Down', 'Dip', 'Arc', 'Spiral', 'S-curve')

BASE = dict(ramp_name='ramp', material_name='test', units_enum='HAMMER',
            preset_enum='CUSTOM', collision_enum='-col', origin_enum='BOUNDS',
            width=384.0, height=544.0, tip=64.0, thickness=64.0, size=1024.0,
            smoothness=8, angle=90.0, rise=512.0, bank=0.0,
            uv_scale=0.25, uv_texel_size=512.0)


def _clear():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)


def _generate(**overrides):
    _clear()
    settings = dict(BASE)
    settings.update(overrides)
    result = bpy.ops.surge.generate_ramp(**settings)
    assert result == {'FINISHED'}, "operator returned %r for %r" % (result, overrides)
    return bpy.context.view_layer.objects.active


def _check_mesh(obj, label):
    mesh = obj.data
    assert len(mesh.polygons) > 0, "%s has no faces" % label
    assert mesh.uv_layers.active is not None, "%s has no UV layer" % label

    bm = bmesh.new()
    bm.from_mesh(mesh)
    try:
        loose = [v for v in bm.verts if not v.link_faces]
        assert not loose, "%s has %d loose verts" % (label, len(loose))
        open_edges = [e for e in bm.edges if len(e.link_faces) != 2]
        assert not open_edges, "%s has %d non-manifold edges" % (label, len(open_edges))
        tiny = [f for f in bm.faces if f.calc_area() < 1e-9]
        assert not tiny, "%s has %d zero-area faces" % (label, len(tiny))
    finally:
        bm.free()


def test_every_combination_builds():
    for style in STYLES:
        for surf in SURFS:
            for shape in SHAPES:
                label = "%s/%s/%s" % (style, surf, shape)
                obj = _generate(style_enum=style, surf_enum=surf, ramp_enum=shape)
                assert obj is not None, "%s produced no object" % label
                assert obj.name == 'ramp-col', "%s named %r" % (label, obj.name)
                assert tuple(round(s, 6) for s in obj.scale) == (1.0, 1.0, 1.0), \
                    "%s has scale %r" % (label, tuple(obj.scale))
                _check_mesh(obj, label)


def test_hammer_units_scale_to_meters():
    obj = _generate(style_enum='Wedge', surf_enum='Left', ramp_enum='Straight')
    expect = (1024.0 * HAMMER_TO_METERS, 384.0 * HAMMER_TO_METERS, 544.0 * HAMMER_TO_METERS)
    for got, want, axis in zip(obj.dimensions, expect, 'XYZ'):
        assert abs(got - want) < 1e-4, "%s was %.6f, expected %.6f" % (axis, got, want)


def test_meters_units_pass_through():
    obj = _generate(style_enum='Wedge', surf_enum='Left', ramp_enum='Straight',
                    units_enum='METERS')
    for got, want, axis in zip(obj.dimensions, (1024.0, 384.0, 544.0), 'XYZ'):
        assert abs(got - want) < 1e-3, "%s was %.6f, expected %.6f" % (axis, got, want)


def test_both_sided_ramp_is_double_width():
    width = _generate(style_enum='Wedge', surf_enum='Left', ramp_enum='Straight').dimensions.y
    both = _generate(style_enum='Wedge', surf_enum='Both', ramp_enum='Straight')
    assert abs(both.dimensions.y - width * 2.0) < 1e-4, \
        "both-sided width %.6f is not double %.6f" % (both.dimensions.y, width)


def test_origin_sits_on_the_geometry():
    for origin in ('BOUNDS', 'MEDIAN'):
        obj = _generate(ramp_enum='Arc', origin_enum=origin)
        coords = [v.co for v in obj.data.vertices]
        if origin == 'BOUNDS':
            center = [(min(c[i] for c in coords) + max(c[i] for c in coords)) * 0.5 for i in range(3)]
        else:
            center = [sum(c[i] for c in coords) / len(coords) for i in range(3)]
        for value, axis in zip(center, 'XYZ'):
            assert abs(value) < 1e-5, "%s origin off by %.6f on %s" % (origin, value, axis)


def test_origin_lands_on_the_cursor():
    bpy.context.scene.cursor.location = (3.0, -4.0, 5.0)
    try:
        obj = _generate(ramp_enum='Straight')
        for got, want, axis in zip(obj.location, (3.0, -4.0, 5.0), 'XYZ'):
            assert abs(got - want) < 1e-6, "%s at %.6f, expected %.6f" % (axis, got, want)
    finally:
        bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)


def test_collision_suffixes():
    for suffix, expected in (('-col', 'ramp-col'), ('-colonly', 'ramp-colonly'),
                             ('-convcol', 'ramp-convcol'), ('NONE', 'ramp')):
        obj = _generate(collision_enum=suffix)
        assert obj.name == expected, "suffix %r gave %r" % (suffix, obj.name)


def test_full_turn_closes_without_caps():
    segments = 8
    for surf in SURFS:
        obj = _generate(surf_enum=surf, ramp_enum='Right', angle=360.0,
                        smoothness=segments, size=4096.0)
        points = len(profile.build('Wedge', surf, 384.0, 544.0, 64.0, 64.0))
        assert len(obj.data.vertices) == segments * points, \
            "%s loop has %d verts, expected %d" % (surf, len(obj.data.vertices), segments * points)
        assert len(obj.data.polygons) == segments * points, \
            "%s loop has %d faces, expected %d" % (surf, len(obj.data.polygons), segments * points)


def test_slope_angle_drives_height():
    obj = _generate(style_enum='Wedge', surf_enum='Left', ramp_enum='Straight',
                    use_slope_angle=True, slope_angle=45.0, tip=0.0)
    assert abs(obj.dimensions.z - obj.dimensions.y) < 1e-4, \
        "45 degree face gave height %.6f against width %.6f" % (obj.dimensions.z, obj.dimensions.y)


def test_spiral_climbs_by_its_rise():
    flat = _generate(ramp_enum='Spiral', rise=0.0, angle=180.0, size=2048.0).dimensions.z
    climbed = _generate(ramp_enum='Spiral', rise=1024.0, angle=180.0, size=2048.0).dimensions.z
    gain = (climbed - flat) / HAMMER_TO_METERS
    assert abs(gain - 1024.0) < 1.0, "spiral gained %.2f units, expected 1024" % gain


def test_s_curve_ends_heading_forward():
    frames, closed = path.build_frames('S-curve', 90.0, 1024.0, 544.0, 8, turn='Right')
    assert not closed
    heading = frames[-1].to_3x3() @ __import__('mathutils').Vector((1.0, 0.0, 0.0))
    assert abs(heading.x - 1.0) < 1e-6, "S-curve ends turned by %r" % (heading,)


def test_bank_rolls_the_cross_section():
    level, _ = path.build_frames('Right', 90.0, 1024.0, 544.0, 8, bank=0.0)
    tilted, _ = path.build_frames('Right', 90.0, 1024.0, 544.0, 8, bank=30.0)
    mid = len(level) // 2
    up = __import__('mathutils').Vector((0.0, 0.0, 1.0))
    angle = (level[mid].to_3x3() @ up).angle(tilted[mid].to_3x3() @ up)
    assert abs(math.degrees(angle) - 30.0) < 0.5, \
        "bank rolled %.2f degrees, expected 30" % math.degrees(angle)


def test_surfsup_preset_matches_the_game_profile():
    section = profile.build('Wedge', 'Left', 384.0, 544.0, 64.0, 64.0)
    assert sorted(section) == sorted([(-192.0, 0.0), (192.0, 0.0), (192.0, 64.0), (-192.0, 544.0)])
    assert abs(profile.slope_angle(384.0, 544.0, 64.0) - 51.34) < 0.01


def test_shallow_face_is_flagged_unsurfable():
    assert profile.slope_angle(384.0, 384.0, 0.0) == 45.0
    assert profile.slope_angle(384.0, 384.0, 0.0) < SURF_MIN_ANGLE
    assert profile.slope_angle(384.0, 544.0, 64.0) > SURF_MIN_ANGLE


def test_uvs_cover_every_loop():
    obj = _generate(ramp_enum='Right', angle=180.0, size=2048.0)
    layer = obj.data.uv_layers.active
    assert len(layer.uv) == len(obj.data.loops)
    span = max(uv.vector.x for uv in layer.uv) - min(uv.vector.x for uv in layer.uv)
    assert span > 1.0, "UVs span only %.3f tiles along the sweep" % span


def test_degenerate_input_cancels_or_still_builds():
    """Property minimums clamp most bad input; the rest has to cancel cleanly."""
    for bad in (dict(size=0.0), dict(ramp_enum='Right', angle=0.0),
                dict(width=0.0), dict(style_enum='Thin', thickness=0.0),
                dict(height=0.0), dict(tip=9999.0), dict(smoothness=3, angle=360.0)):
        _clear()
        settings = dict(BASE)
        settings.update(bad)
        try:
            result = bpy.ops.surge.generate_ramp(**settings)
        except RuntimeError:
            continue  # reporting an ERROR from a script surfaces as RuntimeError
        assert result == {'FINISHED'}, "%r returned %r" % (bad, result)
        _check_mesh(bpy.context.view_layer.objects.active, repr(bad))


class _Stub:
    """Stand-in for the operator, so the property callbacks can be tested alone."""


def _stub(**values):
    stub = _Stub()
    for key, value in values.items():
        setattr(stub, key, value)
    return stub


def test_preset_fills_the_dimension_fields():
    stub = _stub(units_enum='HAMMER', preset_enum='SURFSUP', uv_texel_size=0.0)
    props._apply_preset(stub, None)
    got = (stub.width, stub.height, stub.tip, stub.thickness, stub.size)
    assert got == (384.0, 544.0, 64.0, 64.0, 1024.0), "SurfsUp preset gave %r" % (got,)

    stub = _stub(units_enum='HAMMER', preset_enum='CLASSIC', uv_texel_size=0.0)
    props._apply_preset(stub, None)
    got = (stub.width, stub.height, stub.tip, stub.thickness, stub.size)
    assert got == (256.0, 320.0, 0.0, 32.0, 1024.0), "Classic preset gave %r" % (got,)


def test_preset_respects_the_unit_system():
    stub = _stub(units_enum='METERS', preset_enum='SURFSUP', uv_texel_size=0.0)
    props._apply_preset(stub, None)
    assert abs(stub.width - 384.0 * HAMMER_TO_METERS) < 1e-9, "metric preset gave %r" % stub.width


def test_switching_units_rescales_every_length():
    fields = dict(width=384.0, height=544.0, tip=64.0, thickness=64.0,
                  size=1024.0, rise=512.0, uv_texel_size=512.0)
    stub = _stub(units_enum='METERS', **fields)
    props._convert_units(stub, None)
    for name, hammer in fields.items():
        assert abs(getattr(stub, name) - hammer * HAMMER_TO_METERS) < 1e-9, \
            "%s converted to %r" % (name, getattr(stub, name))
    props._convert_units(_stub(units_enum='HAMMER', **{k: getattr(stub, k) for k in fields}), None)


def test_editing_a_dimension_drops_the_preset():
    stub = _stub(preset_enum='SURFSUP')
    props._mark_custom(stub, None)
    assert stub.preset_enum == 'CUSTOM'


def test_multi_turn_spiral_is_not_clamped():
    """A spiral past 360 degrees has to keep turning, not silently stop at one."""
    obj = _generate(ramp_enum='Spiral', angle=360.0, rise=0.0, size=2048.0, smoothness=32)
    one_width, one_verts = obj.dimensions.x, len(obj.data.vertices)
    obj = _generate(ramp_enum='Spiral', angle=1080.0, rise=0.0, size=2048.0, smoothness=96)
    turn_width, turn_verts = obj.dimensions.x, len(obj.data.vertices)
    assert abs(one_width - turn_width) < 1.0, \
        "three turns should trace the same circle as one, got %.2f against %.2f" % (
            turn_width, one_width)
    assert turn_verts > one_verts * 2, \
        "1080 degrees produced %d verts against %d for 360: the angle was clamped" % (
            turn_verts, one_verts)

    frames, _closed = path.build_frames('Spiral', 540.0, 1600.0, 544.0, 64, 'Right', -3200.0)
    swept = frames[-1].to_3x3() @ __import__('mathutils').Vector((-1.0, 0.0, 0.0))
    # 540 degrees leaves the exit pointing back the way it came
    assert abs(swept.x - 1.0) < 1e-6, "540 degree spiral ended heading %r" % (swept,)
