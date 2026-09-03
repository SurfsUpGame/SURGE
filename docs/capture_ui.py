r"""Capture the Blender screenshots used by the README.

    blender --factory-startup --no-window-focus --enable-event-simulate \
        --window-geometry 0 0 1400 880 --python docs/capture_ui.py

Opens a throwaway Blender window, generates one ramp, opens the Add New Ramp
dialog over it, and writes the whole window plus the dialog on its own into
docs/images/. The dialog is cut out by diffing the frame before and after it
opens. Exits when done.
"""

import importlib
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "images")
PLAIN = os.path.join(bpy.app.tempdir, "surge_plain.png")
DIALOG = os.path.join(bpy.app.tempdir, "surge_dialog.png")

UI_SCALE = 1.1
VIEW = Vector((-0.7, -0.7, 0.8))

SETTINGS = dict(ramp_name='ramp', material_name='ramp', units_enum='HAMMER',
                preset_enum='SURFSUP', collision_enum='-col', origin_enum='BOUNDS',
                width=384.0, height=544.0, tip=64.0, thickness=64.0, size=1024.0,
                style_enum='Wedge', surf_enum='Right', ramp_enum='Right',
                turn_enum='Right', smoothness=24, angle=90.0, bank=15.0,
                uv_scale=0.25, uv_texel_size=512.0)


def _context():
    window = bpy.context.window_manager.windows[0]
    area = next(a for a in window.screen.areas if a.type == 'VIEW_3D')
    region = next(r for r in area.regions if r.type == 'WINDOW')
    return dict(window=window, area=area, region=region)


def _pixels(path):
    image = bpy.data.images.load(path)
    width, height = image.size
    buffer = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(buffer)
    bpy.data.images.remove(image)
    return buffer.reshape(height, width, 4)


def _save(pixels, name):
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.image_settings.compression = 100
    height, width = pixels.shape[:2]
    image = bpy.data.images.new("surge_shot", width=width, height=height, alpha=True)
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = os.path.join(OUT, name)
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)


def start():
    """Reload with no splash over the window, at a screen-independent UI scale."""
    bpy.ops.wm.read_homefile(use_factory_startup=True, use_empty=True, use_splash=False)
    for _ in range(4):
        system, view = bpy.context.preferences.system, bpy.context.preferences.view
        view.ui_scale = UI_SCALE / (system.ui_scale / view.ui_scale)
    return 0.6


def build_ramp():
    override = _context()
    space = override['area'].spaces.active
    space.show_region_ui = True
    space.region_3d.view_perspective = 'ORTHO'
    space.region_3d.view_rotation = (-VIEW).to_track_quat('-Z', 'Y')
    with bpy.context.temp_override(**override):
        bpy.ops.surge.generate_ramp(**SETTINGS)
        bpy.ops.surge.increase_view()
        bpy.ops.view3d.view_selected()
    space.region_3d.view_distance *= 1.45
    return 0.6


def _move_pointer(x_fraction, y_fraction):
    override = _context()
    region = override['region']
    override['window'].event_simulate(
        'MOUSEMOVE', 'NOTHING',
        x=int(region.x + region.width * x_fraction),
        y=int(region.y + region.height * y_fraction))


def open_dialog():
    """Screenshot the window, then open the dialog left of the ramp."""
    with bpy.context.temp_override(**_context()):
        bpy.ops.screen.screenshot(filepath=PLAIN)
    _move_pointer(0.3, 0.5)
    with bpy.context.temp_override(**_context()):
        bpy.ops.surge.generate_ramp('INVOKE_DEFAULT')
    return 0.5


def hide_tooltip():
    """Park the pointer off the dialog so no tooltip covers a field."""
    _move_pointer(0.95, 0.05)
    return 1.0


def shoot():
    with bpy.context.temp_override(**_context()):
        bpy.ops.screen.screenshot(filepath=DIALOG)

    plain, dialog = _pixels(PLAIN), _pixels(DIALOG)
    if plain.shape != dialog.shape:
        raise RuntimeError("screenshots differ in size")
    # A loose threshold would take in the popup's soft shadow and the colours
    # showing through it.
    mask = np.abs(plain - dialog).max(axis=2) > 0.12
    rows, columns = np.where(mask.any(axis=1))[0], np.where(mask.any(axis=0))[0]
    if not len(rows) or not len(columns):
        raise RuntimeError("the dialog did not open")

    _save(dialog, "blender-window.png")
    _save(dialog[rows[0]:rows[-1] + 1, columns[0]:columns[-1] + 1], "blender-dialog.png")
    print("wrote blender-window.png and blender-dialog.png")
    sys.stdout.flush()
    os._exit(0)


STEPS = [start, build_ramp, open_dialog, hide_tooltip, shoot]


def step():
    """Run the next capture step, then wait out the delay it asks for."""
    if not STEPS:
        return None
    delay = STEPS.pop(0)()
    return delay if STEPS else None


def main():
    sys.path.insert(0, os.path.dirname(ROOT))
    importlib.import_module(os.path.basename(ROOT)).register()
    os.makedirs(OUT, exist_ok=True)
    bpy.app.timers.register(step, first_interval=1.0, persistent=True)


if __name__ == "__main__":
    main()
