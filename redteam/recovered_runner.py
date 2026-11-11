"""Run the existing driver with the explicitly recovered support module."""
import runpy
import sys
from redteam import recovered_core

sys.modules["method.vera_repro.core"] = recovered_core
if "--broader-generator" in sys.argv:
    sys.argv.remove("--broader-generator")
    from method.vera_repro import geometry_specs
    # Broaden numeric support; keep templates, verifiers, gates and H-Pro intact.
    geometry_specs.E_GENERATOR = '''
def generator(rng):
    R = rng.randint(15, 90)
    r = rng.randint(2, (R - 1) // 2)
    return {"R": R, "r": r, "style": "Find the product AB times AC."}
'''
    geometry_specs.CHIP_GENERATOR = '''
def generator(rng):
    rows = rng.randint(2, 6)
    cols = rng.randint(2, 6)
    return {"rows": rows, "cols": cols,
            "color_a_count": rows * cols, "color_b_count": rows * cols,
            "color_a": "white", "color_b": "black"}
'''
    geometry_specs.POLYGON_GENERATOR = '''
def generator(rng):
    return {"n": rng.randint(6, 16), "target_color": "blue", "other_color": "red"}
'''
runpy.run_module("method.vera_repro.run_geometry_repro", run_name="__main__")
