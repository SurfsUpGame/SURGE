# SURGE

A Blender addon that generates surf ramp meshes for [SurfsUp](https://store.steampowered.com/app/2915930/SurfsUp/) and Godot.

Install it in Blender 4.2 or newer (tested on 5.2 LTS), open the `SURGE` tab in the 3D viewport sidebar, and hit **Add New Ramp**.

## What comes out

One object, named `<your name>-col`, sitting at the 3D cursor with its origin on the geometry and a scale of exactly (1, 1, 1).

Godot's scene importer reads the `-col` suffix and builds this for you at import time:

```
your_ramp        MeshInstance3D
└── StaticBody3D
    └── CollisionShape3D   ConcavePolygonShape3D (trimesh)
```

No second physics mesh, no QC file, nothing to wire up by hand.
The suffix dropdown also offers `-colonly` and `-convcol` if you want collision only or a convex hull instead.

## Scale

SurfsUp treats one Hammer unit as one inch, the same 39.37 units per metre the game hard-codes as `SOURCE_MULT`.
Type your dimensions in Hammer units (the default) and SURGE converts the mesh to metres on generate, so a ramp lands next to existing map geometry at the right size with nothing to rescale.
Switch the Units dropdown to Meters if you would rather work metric; the dimension fields convert as you switch.

The **SurfsUp** preset reproduces the profile used by the game's own maps: 384 wide, 544 tall, 64 unit tip, which is a 51.34 degree face.
The **Classic SURGE** preset restores the original 256 by 320 defaults.

## Ramp shapes

| Shape | What it sweeps |
| --- | --- |
| Straight | A plain run, no curve |
| Left, Right | A flat turn of the given angle |
| Up, Down | A climb or a drop |
| Arc, Dip | An arch or a valley, centred on its own midpoint |
| Spiral | A turn and a climb at once, set by Rise |
| S-curve | Half the angle one way, half the other |

Bank rolls the cross-section into the corner on any turning shape, eased in and out at the ends.
An angle of 360 closes the sweep into a loop with no end caps.

Wedge style gives a solid ramp; set **Tip** above zero to leave a blunt edge at the thin end instead of a knife edge.
Thin style gives a slab of even thickness following the slope.

## Surfability

The game only lets you surf a face steeper than 45.573 degrees, which is where its `ground_normal_min` of 0.7 lands.
Anything shallower is walkable floor.
SURGE shows a warning in the dialog and on generate when the dimensions you picked fall under that line.

## UVs

UVs are computed from distance along the sweep and across the profile, so they tile evenly on every shape and never stretch through a turn.
One tile spans `Texture Size * UV Scale` units, matching Source texture scale conventions: a 512 texture at scale 0.25 covers 128 units.
The dialog shows the resulting span as you change either field.

## Tests

```bash
blender -b --factory-startup --python tests/run_tests.py
```

The suite generates every style, surf direction and shape combination and checks the mesh is manifold, correctly scaled, properly named, and fully UV mapped.

## Source engine

Versions before 2.0 also emitted a `<name>_phys` mesh for Source's VPhysics, driven by a QC file with `$concave`.
That is gone.
If you need it, use the 1.x releases.
