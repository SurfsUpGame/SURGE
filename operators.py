"""The SURGE operators."""

import math

import bpy
from mathutils import Matrix, Vector

from . import ui
from .props import RampProperties
from .ramp import build, path, profile
from .units import HAMMER_TO_METERS, SURF_MIN_ANGLE


class SURGE_OT_generate_ramp(RampProperties, bpy.types.Operator):
    bl_label = "Surf Ramp Generator"
    bl_idname = "surge.generate_ramp"
    bl_description = "Generate a surf ramp ready for Godot import"
    bl_options = {'REGISTER', 'UNDO'}

    def effective_tip(self):
        return 0.0 if self.style_enum == 'Thin' else self.tip

    def effective_height(self):
        """Cross-section height, derived from the slope angle when asked for."""
        if not self.use_slope_angle:
            return self.height
        return self.effective_tip() + self.width * math.tan(math.radians(self.slope_angle))

    def face_angle(self):
        return profile.slope_angle(self.width, self.effective_height(), self.effective_tip())

    def units_per_tile(self):
        return self.uv_texel_size * self.uv_scale

    def draw(self, context):
        ui.draw_operator(self, self.layout)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=340)

    def execute(self, context):
        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        height = self.effective_height()
        tip = self.effective_tip()
        curved = self.ramp_enum != 'Straight'
        if self.size <= 1e-6:
            self.report({'ERROR'}, "Size must be greater than zero")
            return {'CANCELLED'}
        if curved and self.angle <= 1e-6:
            self.report({'ERROR'}, "A curved ramp needs a non-zero angle")
            return {'CANCELLED'}

        try:
            section = profile.build(self.style_enum, self.surf_enum,
                                    self.width, height, tip, self.thickness)
            frames, closed = path.build_frames(
                self.ramp_enum, self.angle, self.size, height,
                self.smoothness if curved else 1,
                self.turn_enum, self.rise, self.bank)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}

        scale = HAMMER_TO_METERS if self.units_enum == 'HAMMER' else 1.0
        name = self.ramp_name + ('' if self.collision_enum == 'NONE' else self.collision_enum)
        mesh = build.build(section, frames, closed, self.units_per_tile(), scale, name)

        obj = bpy.data.objects.new(name, mesh)
        context.collection.objects.link(obj)
        self._set_origin(obj)
        obj.location = context.scene.cursor.location.copy()
        obj.active_material = self._material()

        for other in list(context.selected_objects):
            other.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        for message in self._warnings(section):
            self.report({'WARNING'}, message)
        return {'FINISHED'}

    def _set_origin(self, obj):
        """Move the mesh so its origin sits on the geometry."""
        coords = [v.co for v in obj.data.vertices]
        if not coords:
            return
        if self.origin_enum == 'MEDIAN':
            center = sum(coords, Vector()) / len(coords)
        else:
            low = Vector((min(c[i] for c in coords) for i in range(3)))
            high = Vector((max(c[i] for c in coords) for i in range(3)))
            center = (low + high) * 0.5
        obj.data.transform(Matrix.Translation(-center))

    def _material(self):
        existing = bpy.data.materials.get(self.material_name)
        return existing if existing else bpy.data.materials.new(name=self.material_name)

    def _warnings(self, section):
        messages = []
        angle = self.face_angle()
        if angle < SURF_MIN_ANGLE:
            messages.append(
                "Face is %.1f degrees; anything under %.2f is walkable floor, not surfable."
                % (angle, SURF_MIN_ANGLE))
        if self.ramp_enum in path.TURN_SHAPES:
            reach = max(abs(y) for y, _ in section)
            if self.size <= reach:
                messages.append(
                    "Turn radius %.1f is inside the ramp's own half-width %.1f; the inner edge folds."
                    % (self.size, reach))
        return messages


class SURGE_OT_increase_view(bpy.types.Operator):
    bl_label = "Increase View Distance"
    bl_idname = "surge.increase_view"
    bl_description = "Push the 3D view clipping range out far enough for a full-size ramp"

    @classmethod
    def poll(cls, context):
        return context.space_data is not None and context.space_data.type == 'VIEW_3D'

    def execute(self, context):
        context.space_data.clip_start = 10.0
        context.space_data.clip_end = 50000.0
        return {'FINISHED'}
