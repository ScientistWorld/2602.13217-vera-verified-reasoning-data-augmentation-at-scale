from __future__ import annotations

from .core import ExecutableSpec


E_GENERATOR = r"""
def generator(rng):
    pairs = [(6, 2), (10, 3), (11, 4), (13, 6), (14, 5), (17, 7), (20, 8)]
    R, r = rng.choice(pairs)
    style = rng.choice([
        "Find the product AB times AC.",
        "Compute AB * AC.",
        "Determine the value of AB·AC.",
    ])
    return {"R": R, "r": r, "style": style}
"""

E_VERIFIER = r"""
def verifier(assign):
    R = float(assign["R"])
    r = float(assign["r"])
    if R <= 0 or r <= 0 or R <= 2 * r:
        return False, None
    # Euler: OI^2 = R(R - 2r). Perpendicularity in triangle AIO gives
    # AI^2 = AO^2 - OI^2. The angle-bisector identity gives AB*AC = AI^2 + 4Rr.
    OI2 = R * (R - 2 * r)
    AI2 = R * R - OI2
    return True, AI2 + 4 * R * r
"""

H_GENERATOR = r"""
def generator(rng):
    candidates = [
        (11, 3, 45),
        (15, 5, 60),
        (22, 7, 40),
        (31, 8, 70),
        (38, 10, 75),
    ]
    R, r, theta = rng.choice(candidates)
    return {"R": R, "r": r, "theta": theta}
"""

H_VERIFIER = r"""
def verifier(assign):
    import math
    R = float(assign["R"])
    r = float(assign["r"])
    theta = float(assign["theta"])
    if R <= 0 or r <= 0 or R <= 2 * r or not (0 < theta < 180):
        return False, None
    d2 = R * (R - 2 * r)
    if d2 < 0:
        return False, None
    d = math.sqrt(d2)
    th = math.radians(theta)
    disc = R * R - (d * math.sin(th)) ** 2
    if disc < -1e-9:
        return False, None
    AI = d * math.cos(th) + math.sqrt(max(0.0, disc))
    answer = AI * AI + 4 * R * r
    return True, answer
"""

CHIP_GENERATOR = r"""
def generator(rng):
    cases = [
        (1, 2, 4, 3, "red", "purple"),
        (2, 3, 6, 6, "white", "black"),
        (3, 3, 9, 9, "green", "orange"),
        (4, 2, 8, 8, "blue", "yellow"),
        (5, 5, 25, 25, "white", "black"),
    ]
    rows, cols, color_a_count, color_b_count, color_a, color_b = rng.choice(cases)
    return {
        "rows": rows,
        "cols": cols,
        "color_a_count": color_a_count,
        "color_b_count": color_b_count,
        "color_a": color_a,
        "color_b": color_b,
    }
"""

CHIP_VERIFIER = r"""
def verifier(assign):
    rows = int(assign["rows"])
    cols = int(assign["cols"])
    cap_a = int(assign["color_a_count"])
    cap_b = int(assign["color_b_count"])
    if rows <= 0 or cols <= 0 or cap_a < 0 or cap_b < 0:
        return False, None

    total = 0
    row_masks = range(1 << rows)
    col_masks = range(1 << cols)
    for row_mask in row_masks:
        a_rows = row_mask.bit_count()
        b_rows = rows - a_rows
        for col_mask in col_masks:
            a_cols = col_mask.bit_count()
            b_cols = cols - a_cols
            row_set = (a_rows > 0, b_rows > 0)
            col_set = (a_cols > 0, b_cols > 0)
            if row_set != col_set:
                continue
            used_a = a_rows * a_cols
            used_b = b_rows * b_cols
            if used_a <= cap_a and used_b <= cap_b:
                total += 1
    return True, total
"""

POLYGON_GENERATOR = r"""
def generator(rng):
    n, target, other = rng.choice([
        (6, "blue", "red"),
        (8, "blue", "red"),
        (10, "purple", "green"),
        (12, "purple", "green"),
        (14, "violet", "amber"),
    ])
    return {"n": n, "target_color": target, "other_color": other}
"""

POLYGON_VERIFIER = r"""
def verifier(assign):
    import math
    n = int(assign["n"])
    if n < 3 or n > 20:
        return False, None
    favorable = 0
    for mask in range(1 << n):
        works = False
        for shift in range(1, n):
            shifted = ((mask << shift) | (mask >> (n - shift))) & ((1 << n) - 1)
            if mask & shifted == 0:
                works = True
                break
        favorable += int(works)
    denom = 1 << n
    g = math.gcd(favorable, denom)
    return True, favorable // g + denom // g
"""


def build_specs() -> list[ExecutableSpec]:
    e_template = (
        "In triangle ABC, let I be the incenter and O the circumcenter. "
        "Suppose IA is perpendicular to OI, the circumradius is {R}, and "
        "the inradius is {r}. {style}"
    )
    h_template = (
        "Let triangle ABC have incenter I and circumcenter O. The angle between "
        "segments IA and OI is {theta} degrees. Its circumradius is {R} and "
        "its inradius is {r}. Find the value of AB * AC."
    )
    chip_template = (
        "You have {color_a_count} indistinguishable chips of color {color_a} and "
        "{color_b_count} indistinguishable chips of color {color_b}. Some chips "
        "are placed into the unit cells of a {rows} by {cols} grid, with at most "
        "one chip per cell. All chips in any row have the same color, all chips "
        "in any column have the same color, and the placement is maximal. How "
        "many distinct placements are possible?"
    )
    polygon_template = (
        "Each vertex of a regular {n}-gon is independently colored {target_color} "
        "or {other_color} with equal probability. Let the probability that the "
        "polygon can be rotated so that every {target_color} vertex lands on a "
        "position that was originally {other_color} be m/n in lowest terms. "
        "Compute m + n."
    )
    return [
        ExecutableSpec(
            spec_id="aime2024_ii_10_vera_e",
            mode="VeRA-E",
            template=e_template,
            generator_code=E_GENERATOR,
            verifier_code=E_VERIFIER,
            base_assignment={"R": 13, "r": 6, "style": "Find the product AB times AC."},
            base_answer=468.0,
            hardness_rank=1,
        ),
        ExecutableSpec(
            spec_id="aime2024_ii_9_chip_grid_vera_e",
            mode="VeRA-E",
            template=chip_template,
            generator_code=CHIP_GENERATOR,
            verifier_code=CHIP_VERIFIER,
            base_assignment={
                "rows": 5,
                "cols": 5,
                "color_a_count": 25,
                "color_b_count": 25,
                "color_a": "white",
                "color_b": "black",
            },
            base_answer=902.0,
            hardness_rank=1,
        ),
        ExecutableSpec(
            spec_id="aime2024_i_11_polygon_rotation_vera_e",
            mode="VeRA-E",
            template=polygon_template,
            generator_code=POLYGON_GENERATOR,
            verifier_code=POLYGON_VERIFIER,
            base_assignment={"n": 8, "target_color": "blue", "other_color": "red"},
            base_answer=371.0,
            hardness_rank=1,
        ),
        ExecutableSpec(
            spec_id="aime2024_ii_10_vera_h",
            mode="VeRA-H",
            template=h_template,
            generator_code=H_GENERATOR,
            verifier_code=H_VERIFIER,
            base_assignment={"R": 38, "r": 10, "theta": 75},
            base_answer=2755.94103802,
            hardness_rank=2,
        ),
    ]
