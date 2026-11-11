"""Teacher prompts, adapted from the official VeRA GSM8K teacher prompt
(method/VeRA/src/vera/prompt_templates.py::teacher_messages) to the fixed
slot schema of this benchmark (one slot per digit-written number)."""
from __future__ import annotations

SYSTEM = (
    "You are an expert at parameterizing math word problems in GSM8K. "
    "You generalize a seed problem into an executable specification -- a question template with numeric slots, "
    "a generator that samples new slot values, and a verifier that validates a slot assignment and computes its "
    "answer -- without changing the core calculation logic. "
    "Return ONE JSON OBJECT only. No code fences, no prose."
)

EXAMPLE = r'''EXAMPLE (for a different seed)
-------
question: A baker bakes 24 muffins on each tray and fills 5 trays. She sells every muffin for $3. How much money does she make?
answer: 360
slots: n0 = 24 (int), n1 = 5 (int), n2 = 3 (int)
output:
{"template": "A baker bakes {n0} muffins on each tray and fills {n1} trays. She sells every muffin for ${n2}. How much money does she make?",
 "generator": "def generator(rng):\n    n0 = rng.randint(6, 48)\n    n1 = rng.randint(2, 12)\n    n2 = rng.randint(1, 9)\n    return {'n0': n0, 'n1': n1, 'n2': n2}",
 "verifier": "def verifier(assign):\n    n0 = assign['n0']; n1 = assign['n1']; n2 = assign['n2']\n    if min(n0, n1, n2) <= 0:\n        return False, None\n    if any(int(v) != v for v in (n0, n1, n2)):\n        return False, None\n    muffins = n0 * n1\n    money = muffins * n2\n    if money < 0 or money != int(money):\n        return False, None\n    return True, int(money)"}'''


def marked_question(seed: dict) -> str:
    q = seed["question"]
    out, last = [], 0
    for s in seed["slots"]:
        out.append(q[last:s["start"]])
        out.append(f"[{s['name']}={s['text']}]")
        last = s["end"]
    out.append(q[last:])
    return "".join(out)


def seed_assignment(seed: dict) -> dict:
    return {s["name"]: s["value"] for s in seed["slots"]}


def teacher_messages(seed: dict, feedback: str | None = None, previous: str | None = None) -> list[dict]:
    slots = "\n".join(f"{s['name']} = {s['text']} ({s['kind']})" for s in seed["slots"])
    names = ", ".join("{" + s["name"] + "}" for s in seed["slots"])
    base = seed_assignment(seed)
    parts = [
        "SEED", "----",
        f"question_id: {seed['seed_id']}",
        f"question: {seed['question']}",
        f"answer: {seed['answer']}",
        f"question with slots marked: {marked_question(seed)}",
        "",
        "SLOTS (fixed names; every number written with digits in the question is a slot)",
        "-----",
        slots,
        "",
        "GOAL", "----",
        "Output a SINGLE JSON object with exactly three keys:",
        f"- \"template\": the question rewritten with the placeholders {names} (Python str.format style). "
        "Every slot must appear. You may paraphrase or change names and story, but the underlying calculation must stay "
        "identical. Do not reveal the answer.",
        "- \"generator\": Python source of `def generator(rng):` returning a dict that maps ALL slot names to new values. "
        "Use rng.randint, rng.uniform, rng.choice or rng.random. int slots must be Python ints and every value must be "
        "positive. Pick values so the problem stays sensible (divisions come out even, no quantity becomes negative).",
        "- \"verifier\": Python source of `def verifier(assign):` that reads the slot values from assign, returns "
        "(False, None) when the assignment is invalid (non-positive values, uneven divisions, negative intermediate "
        "quantities, or a final answer that is not a non-negative integer), and otherwise returns (True, answer) with "
        "the answer computed from the slot values exactly as the question requires.",
        "",
        "RULES", "-----",
        "- The verifier must compute everything from assign[...] values; never hard-code a slot's seed value.",
        f"- verifier({base}) must return (True, {seed['answer']}).",
        "- Pure Python 3; no I/O; no imports (the module `math` is already available).",
        "- Do not use names or attributes that start with an underscore.",
        "",
        EXAMPLE,
    ]
    if feedback:
        parts += [
            "", "RETRY_FEEDBACK", "--------------",
            "The previous attempt failed validation. Diagnose and fix the issues below.",
            "Issues to fix:", feedback,
        ]
        if previous:
            parts += ["Previous output:", previous[:2500]]
    parts += ["", "OUTPUT", "------", "Return ONLY the JSON object."]
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n".join(parts)}]


def solve_messages(seed: dict) -> list[dict]:
    """Independent re-derivation used by the randomized cross-check gate."""
    args = ", ".join(s["name"] for s in seed["slots"])
    parts = [
        "Solve the following math word problem for ARBITRARY values of its numbers.",
        f"question with numbers marked: {marked_question(seed)}",
        f"For the values shown the answer is {seed['answer']}.",
        "",
        f"Write a Python function `def solve({args}):` that returns the answer for any values of {args}. "
        "Compute step by step from the arguments; do not hard-code any of the marked numbers. "
        "Return only the function inside one ```python code block.",
    ]
    return [{"role": "system", "content": "You are a careful math teacher who writes short, correct Python."},
            {"role": "user", "content": "\n".join(parts)}]
