"""Render the ramp images used by the README.

    blender -b --factory-startup --python docs/render_docs.py

Writes PNGs with a transparent background into docs/images/.
"""

import importlib
import math
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "images")

BASE = dict(ramp_name='ramp', material_name='ramp', units_enum='HAMMER',
            preset_enum='SURFSUP', collision_enum='-col', origin_enum='BOUNDS',
            width=384.0, height=544.0, tip=64.0, thickness=64.0, size=1024.0,
            style_enum='Wedge', surf_enum='Right', ramp_enum='Straight',
            turn_enum='Right', smoothness=24, angle=90.0, rise=512.0, bank=0.0,
            uv_scale=0.25, uv_texel_size=512.0)

# Three quarter views from behind the finish of the sweep, where the surfable
# face reads clearest. Left turns need the mirrored side.
VIEW = Vector((-0.7, -0.7, 0.8))
VIEW_LEFT = Vector((0.8, -0.7, 0.8))
VIEW_HERO = Vector((-0.6, -0.85, 0.4))

SHOTS = [
    ("hero", (1000, 480), VIEW_HERO, dict(ramp_enum='Straight', surf_enum='Both',
                                          size=2048.0)),
    ("shape-straight", (640, 480), VIEW, dict(ramp_enum='Straight')),
    ("shape-left", (640, 480), VIEW_LEFT, dict(ramp_enum='Left')),
    ("shape-right", (640, 480), VIEW, dict(ramp_enum='Right')),
    ("shape-up", (640, 480), VIEW, dict(ramp_enum='Up', angle=45.0)),
    ("shape-down", (640, 480), VIEW, dict(ramp_enum='Down', angle=45.0)),
    ("shape-arc", (640, 480), VIEW, dict(ramp_enum='Arc', angle=120.0)),
    ("shape-dip", (640, 480), VIEW, dict(ramp_enum='Dip', angle=120.0)),
    ("shape-spiral", (640, 480), VIEW, dict(ramp_enum='Spiral', angle=360.0,
                                            rise=1024.0, smoothness=48)),
    ("shape-scurve", (640, 480), VIEW, dict(ramp_enum='S-curve', angle=180.0,
                                            smoothness=40)),
    ("style-wedge", (640, 480), VIEW, dict(style_enum='Wedge', ramp_enum='Straight')),
    ("style-thin", (640, 480), VIEW, dict(style_enum='Thin', ramp_enum='Straight')),
    ("surf-both", (640, 480), VIEW, dict(surf_enum='Both', ramp_enum='Straight')),
]


def clear(keep):
    for obj in list(bpy.data.objects):
        if obj is not keep:
            bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)


def _fov(camera):
    """Horizontal and vertical field of view for the current resolution."""
    render = bpy.context.scene.render
    wide = camera.data.angle
    aspect = render.resolution_y / render.resolution_x
    if aspect <= 1.0:
        return wide, 2.0 * math.atan(math.tan(wide * 0.5) * aspect)
    return 2.0 * math.atan(math.tan(wide * 0.5) / aspect), wide


def _aim(camera, target, direction, distance):
    camera.location = target + direction * distance
    forward = (target - camera.location).normalized()
    camera.rotation_euler = forward.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()


def frame(obj, camera, direction, margin=1.08):
    """Aim the camera at the object and fit it to the frame.

    Fitting to the vertices rather than the bounding box keeps a shape that
    runs diagonally through its box from sitting small in the frame.
    """
    corners = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    bounds_low = Vector((min(c[i] for c in corners) for i in range(3)))
    bounds_high = Vector((max(c[i] for c in corners) for i in range(3)))
    target = (bounds_low + bounds_high) * 0.5
    direction = direction.normalized()
    distance = max((c - target).length for c in corners) * 4.0

    for _ in range(12):
        _aim(camera, target, direction, distance)
        points = [world_to_camera_view(bpy.context.scene, camera, c) for c in corners]
        low = Vector((min(p.x for p in points), min(p.y for p in points)))
        high = Vector((max(p.x for p in points), max(p.y for p in points)))

        horizontal, vertical = _fov(camera)
        matrix = camera.matrix_world
        span = Vector(((low.x + high.x) * 0.5 - 0.5, (low.y + high.y) * 0.5 - 0.5))
        target = target + (matrix.col[0].to_3d() * span.x * 2.0 * distance
                           * math.tan(horizontal * 0.5)
                           + matrix.col[1].to_3d() * span.y * 2.0 * distance
                           * math.tan(vertical * 0.5))
        distance *= max(high.x - low.x, high.y - low.y) * margin

    _aim(camera, target, direction, distance)


def setup_scene():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.compression = 100
    scene.display.render_aa = '32'

    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.studio_light = 'Default'
    shading.color_type = 'SINGLE'
    shading.single_color = (0.30, 0.45, 0.66)
    shading.show_cavity = True
    shading.cavity_type = 'BOTH'
    shading.show_shadows = True
    shading.show_object_outline = True
    shading.object_outline_color = (0.05, 0.07, 0.10)

    camera = bpy.data.objects.new("doc_camera", bpy.data.cameras.new("doc_camera"))
    camera.data.lens = 70.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    return camera


def main():
    sys.path.insert(0, os.path.dirname(ROOT))
    addon = importlib.import_module(os.path.basename(ROOT))
    addon.register()

    os.makedirs(OUT, exist_ok=True)
    camera = setup_scene()
    scene = bpy.context.scene

    for name, (width, height), direction, overrides in SHOTS:
        clear(camera)
        settings = dict(BASE)
        settings.update(overrides)
        result = bpy.ops.surge.generate_ramp(**settings)
        if result != {'FINISHED'}:
            raise RuntimeError("%s: operator returned %r" % (name, result))

        scene.render.resolution_x = width
        scene.render.resolution_y = height
        frame(bpy.context.view_layer.objects.active, camera, direction)
        scene.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("wrote %s.png" % name)

    addon.unregister()


if __name__ == "__main__":
    main()
