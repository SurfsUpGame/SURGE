"""Scale constants and size presets shared by the SURGE operators."""

# SurfsUp works in metres and treats one Hammer unit as one inch. The game
# hard-codes the reciprocal as SOURCE_MULT = 39.37 (base_surfer.gd,
# source_movement_config.gd, Scripts/BSP/*).
HAMMER_TO_METERS = 0.0254

# A face shallower than this is walkable floor, not surfable. The game derives
# it from ground_normal_min = 0.7; RampGenerator.MIN_ANGLE states it directly.
SURF_MIN_ANGLE = 45.573

# Hammer units per UV tile before uv_scale is applied.
DEFAULT_UV_TEXEL_SIZE = 512.0

# Fraction of the sweep spent easing a bank in and out at each end.
BANK_EASE_FRACTION = 0.2

# width, height, tip, thickness, size (all Hammer units).
PRESETS = {
    'SURFSUP': (384.0, 544.0, 64.0, 64.0, 1024.0),
    'CLASSIC': (256.0, 320.0, 0.0, 32.0, 1024.0),
}


def to_scene(value, units):
    """Convert a Hammer-unit length to the scene's unit system."""
    return value * HAMMER_TO_METERS if units == 'HAMMER' else value
