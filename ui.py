"""Sidebar panel and the generate operator's dialog layout."""

import bpy

from . import icons
from .ramp import path
from .units import SURF_MIN_ANGLE


class SURGE_PT_MainPanel(bpy.types.Panel):
    bl_label = "Surf Ramp Generator"
    bl_idname = "SURGE_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SURGE'

    def draw(self, context):
        layout = self.layout
        layout.operator("surge.generate_ramp", text="Add New Ramp",
                        icon_value=icons.icon_id("add"))
        layout.operator("surge.increase_view", text="Increase View Distance",
                        icon_value=icons.icon_id("view"))


def draw_operator(op, layout):
    """Lay out the generate operator's dialog."""
    layout.label(text="Names", icon_value=icons.icon_id("name"))
    box = layout.box()
    _labelled(box, "Ramp Name:", op, 'ramp_name')
    _labelled(box, "Material Name:", op, 'material_name')
    row = box.row()
    row.label(text="Collision Suffix:")
    row.prop(op, 'collision_enum')

    layout.label(text="Slope Dimensions", icon_value=icons.icon_id("slope_dimensions"))
    box = layout.box()
    _labelled(box, "Units:", op, 'units_enum')
    _labelled(box, "Preset:", op, 'preset_enum')

    row = box.row(align=True)
    row.prop(op, "width")
    if op.use_slope_angle:
        row.label(text="Height: %.1f" % op.effective_height())
    else:
        row.prop(op, "height")

    row = box.row()
    row.prop(op, 'use_slope_angle')
    sub = row.row()
    sub.enabled = op.use_slope_angle
    sub.prop(op, 'slope_angle')

    if op.style_enum != 'Thin':
        row = box.row()
        row.label(text="Tip:")
        row.prop(op, "tip")

    angle = op.face_angle()
    if angle < SURF_MIN_ANGLE:
        box.label(text="%.1f deg face is not surfable (needs %.2f)" % (angle, SURF_MIN_ANGLE),
                  icon='ERROR')

    layout.label(text="Ramp Properties", icon_value=icons.icon_id("ramp_properties"))
    box = layout.box()
    _labelled(box, "Ramp Style:", op, 'style_enum')
    if op.style_enum == 'Thin':
        _labelled(box, "Thickness:", op, 'thickness', icons.icon_id("thickness"))

    _labelled(box, "Surf Direction:", op, 'surf_enum')
    _labelled(box, "Ramp Direction:", op, 'ramp_enum')

    if op.ramp_enum in ('Spiral', 'S-curve'):
        _labelled(box, "Turn:", op, 'turn_enum')
    if op.ramp_enum == 'Spiral':
        _labelled(box, "Rise:", op, 'rise')

    if op.ramp_enum != 'Straight':
        _labelled(box, "Smoothness:", op, 'smoothness', icons.icon_id("smoothness"))
        _labelled(box, "Angle:", op, 'angle', icons.icon_id("angle"))
    if op.ramp_enum in path.BANKABLE_SHAPES:
        _labelled(box, "Bank:", op, 'bank')

    _labelled(box, "Size:", op, 'size', icons.icon_id("size"))
    _labelled(box, "Origin:", op, 'origin_enum')

    layout.label(text="UVs", icon_value=icons.icon_id("uv_scale"))
    box = layout.box()
    _labelled(box, "UV Scale:", op, 'uv_scale')
    _labelled(box, "Texture Size:", op, 'uv_texel_size')
    box.label(text="One tile spans %.1f units" % op.units_per_tile())


def _labelled(layout, text, op, prop, icon=0):
    row = layout.row()
    if icon:
        row.label(text=text, icon_value=icon)
    else:
        row.label(text=text)
    row.prop(op, prop)
