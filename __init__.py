"""SURGE: surf ramp generation for SurfsUp."""

import bpy

from . import icons
from .operators import SURGE_OT_generate_ramp, SURGE_OT_increase_view
from .ui import SURGE_PT_MainPanel

_CLASSES = (SURGE_OT_generate_ramp, SURGE_OT_increase_view, SURGE_PT_MainPanel)


def register():
    icons.load()
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
    icons.unload()
