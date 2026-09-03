"""Custom icon previews, loaded on register and freed on unregister."""

import os

import bpy.utils.previews

NAMES = (
    "view", "add", "name", "slope_dimensions", "ramp_properties", "wedge", "thin",
    "thickness", "left_surf", "right_surf", "both", "left_ramp", "right_ramp",
    "down", "up", "arc", "dip", "straight", "spiral", "s_curve", "smoothness",
    "angle", "size", "uv_scale",
)

_collection = None


def icon_id(name):
    """Preview icon id, or 0 when the previews are not loaded."""
    if _collection is None or name not in _collection:
        return 0
    return _collection[name].icon_id


def load():
    global _collection
    if _collection is not None:
        return
    _collection = bpy.utils.previews.new()
    directory = os.path.join(os.path.dirname(__file__), "icons")
    for name in NAMES:
        path = os.path.join(directory, name + ".png")
        if os.path.exists(path):
            _collection.load(name, path, 'IMAGE')


def unload():
    global _collection
    if _collection is None:
        return
    bpy.utils.previews.remove(_collection)
    _collection = None
