"""Run the SURGE test suite inside Blender.

    blender -b --factory-startup --python tests/run_tests.py
"""

import importlib
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    sys.path.insert(0, os.path.dirname(ROOT))
    addon = importlib.import_module(os.path.basename(ROOT))
    addon.register()
    suite = importlib.import_module(os.path.basename(ROOT) + ".tests.test_ramps")

    names = sorted(n for n in dir(suite) if n.startswith("test_"))
    failures = []
    for name in names:
        try:
            getattr(suite, name)()
        except Exception:
            failures.append((name, traceback.format_exc()))
            print("FAIL %s" % name)
        else:
            print("ok   %s" % name)

    addon.unregister()

    for name, trace in failures:
        print("\n=== %s ===\n%s" % (name, trace))
    print("\n%d passed, %d failed" % (len(names) - len(failures), len(failures)))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
