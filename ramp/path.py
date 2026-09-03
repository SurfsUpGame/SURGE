"""Sweep paths, returned as one frame matrix per profile ring.

The identity frame is the start of the ramp: forward is -X, right is +Y, up is
+Z. A frame maps a cross-section point (0, y, z) into world space.
"""

import math

from mathutils import Matrix, Vector

from ..units import BANK_EASE_FRACTION

TURN_SHAPES = {'Left', 'Right', 'Spiral', 'S-curve'}
PITCH_SHAPES = {'Up', 'Down', 'Arc', 'Dip'}
CENTERED_SHAPES = {'Arc', 'Dip'}
BANKABLE_SHAPES = TURN_SHAPES


def _turn(theta, radius, sign):
    """Yaw about the Z axis through (0, sign*radius, 0). +1 turns right."""
    offset = Matrix.Translation(Vector((0.0, sign * radius, 0.0)))
    return offset @ Matrix.Rotation(-sign * theta, 4, 'Z') @ offset.inverted()


def _pitch(theta, radius, sign):
    """Pitch about the Y axis through (0, 0, sign*radius). +1 climbs."""
    offset = Matrix.Translation(Vector((0.0, 0.0, sign * radius)))
    return offset @ Matrix.Rotation(sign * theta, 4, 'Y') @ offset.inverted()


def _smoothstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def _bank_weight(t, closed):
    """Bank strength at normalised position t, eased in and out at open ends."""
    if closed or BANK_EASE_FRACTION <= 0.0:
        return 1.0
    return min(_smoothstep(t / BANK_EASE_FRACTION),
               _smoothstep((1.0 - t) / BANK_EASE_FRACTION))


def is_closed(shape, angle, rise):
    """True when the sweep meets itself and needs no end caps."""
    if shape not in TURN_SHAPES and shape not in PITCH_SHAPES:
        return False
    if shape == 'S-curve':
        return False
    if abs(angle - 360.0) > 1e-6:
        return False
    return shape != 'Spiral' or abs(rise) < 1e-6


def _sign(turn):
    return 1.0 if turn == 'Right' else -1.0


def _frame(shape, t, angle, size, height, turn, rise):
    """Unbanked frame at normalised position t along the sweep."""
    theta = math.radians(angle) * t
    if shape == 'Straight':
        return Matrix.Translation(Vector((-size * t, 0.0, 0.0)))
    if shape in ('Left', 'Right'):
        return _turn(theta, size, _sign(shape))
    if shape == 'Spiral':
        return Matrix.Translation(Vector((0.0, 0.0, rise * t))) @ _turn(theta, size, _sign(turn))
    if shape == 'S-curve':
        sign = _sign(turn)
        half = math.radians(angle) * 0.5
        if theta <= half:
            return _turn(theta, size, sign)
        return _turn(half, size, sign) @ _turn(theta - half, size, -sign)
    if shape in ('Up', 'Dip'):
        return _pitch(theta, size + height, 1.0)
    if shape in ('Down', 'Arc'):
        return _pitch(theta, size, -1.0)
    raise ValueError("unknown ramp shape: %r" % (shape,))


def _turn_sign_at(shape, t, turn):
    if shape in ('Left', 'Right'):
        return _sign(shape)
    if shape == 'Spiral':
        return _sign(turn)
    if shape == 'S-curve':
        return _sign(turn) if t <= 0.5 else -_sign(turn)
    return 0.0


def build_frames(shape, angle, size, height, segments, turn='Right', rise=0.0, bank=0.0):
    """Return the frame matrices for one ring per step along the sweep."""
    closed = is_closed(shape, angle, rise)
    count = segments if closed else segments + 1
    step = 1.0 / segments if closed else 1.0 / max(segments, 1)

    frames = []
    for i in range(count):
        t = i * step
        matrix = _frame(shape, t, angle, size, height, turn, rise)
        if abs(bank) > 1e-6:
            roll = -_turn_sign_at(shape, t, turn) * math.radians(bank) * _bank_weight(t, closed)
            matrix = matrix @ Matrix.Rotation(roll, 4, 'X')
        frames.append(matrix)

    if shape in CENTERED_SHAPES:
        middle = _frame(shape, 0.5, angle, size, height, turn, rise).inverted()
        frames = [middle @ f for f in frames]

    return frames, closed
