"""Operator properties for the ramp generator.

Icon-bearing enums build their items through a callback so the preview
collection can be created in register() and freed in unregister().
"""

import bpy

from . import icons
from .units import DEFAULT_UV_TEXEL_SIZE, HAMMER_TO_METERS, PRESETS

_LENGTH_PROPS = ('width', 'height', 'tip', 'thickness', 'size', 'rise', 'uv_texel_size')

# Set while a preset or a unit change is rewriting the length fields, so their
# own update callbacks do not fight back.
_rewriting = False

STYLE_ITEMS = [
    ('Wedge', "Wedge", "Solid wedge, thickest at the top of the slope", 'wedge'),
    ('Thin', "Thin", "Slab of even thickness following the slope", 'thin'),
]

SURF_ITEMS = [
    ('Left', "Left", "Strafe left to surf along it", 'left_surf'),
    ('Right', "Right", "Strafe right to surf along it", 'right_surf'),
    ('Both', "Both", "Surfable on both sides", 'both'),
]

SHAPE_ITEMS = [
    ('Straight', "Straight", "No curve", 'straight'),
    ('Left', "Left", "Turns left", 'left_ramp'),
    ('Right', "Right", "Turns right", 'right_ramp'),
    ('Up', "Up", "Curves upwards", 'up'),
    ('Down', "Down", "Curves downwards", 'down'),
    ('Dip', "Dip", "U shaped valley", 'dip'),
    ('Arc', "Arc", "N shaped arch", 'arc'),
    ('Spiral', "Spiral", "Turns while climbing or dropping", 'spiral'),
    ('S-curve', "S-curve", "Turns one way then the other", 's_curve'),
]

TURN_ITEMS = [
    ('Right', "Right", "Turn right first", 'right_ramp'),
    ('Left', "Left", "Turn left first", 'left_ramp'),
]

_enum_cache = {}


def _items(key, entries):
    """Build enum items, caching them so Blender keeps the strings alive."""
    # Numbering from zero matters: a callback enum takes no default, so Blender
    # falls back to value 0 and the first item has to claim it.
    _enum_cache[key] = [
        (ident, label, desc, icons.icon_id(icon), index)
        for index, (ident, label, desc, icon) in enumerate(entries)
    ]
    return _enum_cache[key]


def _style_items(self, context):
    return _items('style', STYLE_ITEMS)


def _surf_items(self, context):
    return _items('surf', SURF_ITEMS)


def _shape_items(self, context):
    return _items('shape', SHAPE_ITEMS)


def _turn_items(self, context):
    return _items('turn', TURN_ITEMS)


def _apply_preset(self, context):
    global _rewriting
    if _rewriting or self.preset_enum == 'CUSTOM':
        return
    factor = HAMMER_TO_METERS if self.units_enum == 'METERS' else 1.0
    width, height, tip, thickness, size = PRESETS[self.preset_enum]
    _rewriting = True
    try:
        self.width = width * factor
        self.height = height * factor
        self.tip = tip * factor
        self.thickness = thickness * factor
        self.size = size * factor
        self.uv_texel_size = DEFAULT_UV_TEXEL_SIZE * factor
    finally:
        _rewriting = False


def _convert_units(self, context):
    """Rescale every length field when the unit system changes."""
    global _rewriting
    if _rewriting:
        return
    factor = HAMMER_TO_METERS if self.units_enum == 'METERS' else 1.0 / HAMMER_TO_METERS
    _rewriting = True
    try:
        for name in _LENGTH_PROPS:
            setattr(self, name, getattr(self, name) * factor)
    finally:
        _rewriting = False


def _mark_custom(self, context):
    if not _rewriting:
        self.preset_enum = 'CUSTOM'


class RampProperties:
    """Mix-in holding every property of the generate operator."""

    ramp_name: bpy.props.StringProperty(
        name="", default='ramp',
        description="Object name. The collision suffix is appended to it")
    material_name: bpy.props.StringProperty(
        name="", default='default',
        description="Material to assign, created if it does not exist yet")

    units_enum: bpy.props.EnumProperty(
        name="", update=_convert_units,
        description="Unit system the dimension fields are typed in",
        items=[
            ('HAMMER', "Hammer units", "Type Source grid values; the mesh is scaled to metres on generate"),
            ('METERS', "Meters", "Type metres directly, as Blender and Godot use them"),
        ])

    preset_enum: bpy.props.EnumProperty(
        name="", update=_apply_preset,
        description="Fill the dimensions from a known-good set",
        items=[
            ('SURFSUP', "SurfsUp", "Matches the ramps in the game's own maps: 384 wide, 544 tall, 64 tip"),
            ('CLASSIC', "Classic SURGE", "The original SURGE defaults: 256 wide, 320 tall, sharp tip"),
            ('CUSTOM', "Custom", "Dimensions set by hand"),
        ])

    collision_enum: bpy.props.EnumProperty(
        name="",
        description="Godot import suffix appended to the object name",
        items=[
            ('-col', "-col", "Visible mesh plus a trimesh StaticBody3D"),
            ('-colonly', "-colonly", "Collision only, the mesh itself is discarded"),
            ('-convcol', "-convcol", "Visible mesh plus a convex StaticBody3D"),
            ('NONE', "None", "No suffix"),
        ])

    origin_enum: bpy.props.EnumProperty(
        name="",
        description="Where the object origin ends up",
        items=[
            ('BOUNDS', "Bounds Center", "Centre of the geometry bounding box"),
            ('MEDIAN', "Median Point", "Average of the vertex positions"),
        ])

    style_enum: bpy.props.EnumProperty(name="", description="Cross-section style", items=_style_items)
    surf_enum: bpy.props.EnumProperty(name="", description="Which side is surfable", items=_surf_items)
    ramp_enum: bpy.props.EnumProperty(name="", description="Path the ramp sweeps along", items=_shape_items)
    turn_enum: bpy.props.EnumProperty(name="", description="Direction the sweep turns first", items=_turn_items)

    width: bpy.props.FloatProperty(
        name="Width:", default=384.0, min=1.0, update=_mark_custom,
        description="Horizontal run of the surfable face. Doubled for a both-sided ramp")
    height: bpy.props.FloatProperty(
        name="Height:", default=544.0, min=1.0, update=_mark_custom,
        description="Total height of the cross-section")
    tip: bpy.props.FloatProperty(
        name="Tip:", default=64.0, min=0.0, update=_mark_custom,
        description="Thickness left at the thin end of a wedge. Zero gives a knife edge")
    thickness: bpy.props.FloatProperty(
        name="Thickness:", default=64.0, min=0.01, update=_mark_custom,
        description="Slab thickness of a thin ramp")
    size: bpy.props.FloatProperty(
        name="", default=1024.0, min=0.0, update=_mark_custom,
        description="Length of a straight ramp, or the inner turn radius of a curved one")

    use_slope_angle: bpy.props.BoolProperty(
        name="Set slope by angle", default=False,
        description="Derive the height from the face angle instead of typing it")
    slope_angle: bpy.props.FloatProperty(
        name="", default=51.34, min=1.0, max=89.0,
        description="Angle of the surfable face above horizontal")

    smoothness: bpy.props.IntProperty(
        name="", default=16, min=3, max=128,
        description="Segments along the sweep. More is smoother and heavier")
    angle: bpy.props.FloatProperty(
        name="", default=90.0, min=0.0, max=1440.0,
        description="Degrees the sweep turns through. 360 closes a turn into a "
                    "loop; a spiral or S-curve can run past it for extra turns")
    rise: bpy.props.FloatProperty(
        name="", default=512.0, update=_mark_custom,
        description="Height gained over the whole spiral. Negative descends")
    bank: bpy.props.FloatProperty(
        name="", default=0.0, min=-89.0, max=89.0,
        description="Degrees the cross-section rolls into the turn")

    uv_scale: bpy.props.FloatProperty(
        name="", default=0.25, min=0.01, max=10.0, step=5,
        description="Source-style texture scale. Smaller repeats the texture more often")
    uv_texel_size: bpy.props.FloatProperty(
        name="", default=DEFAULT_UV_TEXEL_SIZE, min=1.0,
        description="Texture size in the current units. With uv_scale it sets how far one UV tile spans")
