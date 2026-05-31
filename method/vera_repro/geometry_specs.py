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

