"""Sandboxed execution of one submitted executable specification.

The code it runs is the method's own output: evaluate.py reads it from
outputs/<method>/specs.jsonl and sends it here.

Run as a separate process by eval/train/evaluate.py:
    python -I sandbox_runner.py < request.json > result.json

The request carries the generator / verifier source, the seed assignment and
the evaluation keys.  Nothing else (no references, no answers) is sent, so the
submitted code cannot see the labels it is checked against.  The code runs
with restricted builtins, whitelisted module proxies, per-call timers and
process resource limits (no file writes, bounded CPU and memory, and no new
file descriptors: every import happens before the limits are set, so even an
escaped spec cannot open a file such as the reference programs).

Replay: the generator is executed in two independent namespaces; the second
one walks the keys in reverse order, so a sample must be a function of its key
(paper R5), not of how many times the generator was called before.
"""
from __future__ import annotations

import builtins
import json
import math
import random
import signal
import sys
import types

CALL_SECONDS = 2.0
CPU_SECONDS = 60
MEM_BYTES = 1024 * 1024 * 1024


def _limits() -> None:
    import resource

    for limit, value in (
        (resource.RLIMIT_AS, MEM_BYTES),
        (resource.RLIMIT_CPU, CPU_SECONDS),
        (resource.RLIMIT_FSIZE, 0),
        # Only stdin/stdout/stderr may exist: opening any file or socket fails.
        (resource.RLIMIT_NOFILE, 3),
    ):
        try:
            resource.setrlimit(limit, (value, value))
        except (ValueError, OSError):
            pass


def _proxy(mod: types.ModuleType) -> types.SimpleNamespace:
    ns = {}
    for name in dir(mod):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name)
        if isinstance(obj, types.ModuleType):
            continue
        ns[name] = obj
    return types.SimpleNamespace(**ns)


def _modules() -> dict:
    import fractions
    import functools
    import itertools

    return {
        "math": _proxy(math),
        "random": _proxy(random),
        "fractions": _proxy(fractions),
        "itertools": _proxy(itertools),
        "functools": _proxy(functools),
    }


SAFE_BUILTINS = [
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float",
    "frozenset", "int", "isinstance", "len", "list", "map", "max", "min", "pow",
    "range", "reversed", "round", "set", "sorted", "str", "sum", "tuple", "zip",
    "ValueError", "ZeroDivisionError", "ArithmeticError", "Exception", "KeyError",
    "IndexError", "TypeError", "OverflowError", "StopIteration", "True", "False", "None",
]


class RNGShim:
    """Public subset of random.Random handed to generator(rng)."""

    def __init__(self, seed: int):
        self.__r = random.Random(seed)

    def random(self):
        return self.__r.random()

    def uniform(self, a, b):
        return self.__r.uniform(a, b)

    def randint(self, a, b):
        return self.__r.randint(a, b)

    def randrange(self, start, stop=None, step=1):
        return self.__r.randrange(start, stop, step)

    def choice(self, seq):
        return self.__r.choice(seq)

    def choices(self, population, weights=None, k=1):
        return self.__r.choices(population, weights=weights, k=k)

    def sample(self, population, k):
        return self.__r.sample(population, k)

    def shuffle(self, x):
        self.__r.shuffle(x)
        return x

    def gauss(self, mu, sigma):
        return self.__r.gauss(mu, sigma)

    def triangular(self, low=0.0, high=1.0, mode=None):
        return self.__r.triangular(low, high, mode)


class CallTimeout(Exception):
    pass


def _alarm(signum, frame):  # noqa: ARG001
    raise CallTimeout()


def _namespace(code: str, mods: dict) -> dict:
    safe = {name: getattr(builtins, name) for name in SAFE_BUILTINS if hasattr(builtins, name)}

    def _import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        root = name.split(".")[0]
        if root in mods and level == 0 and "." not in name:
            return mods[root]
        raise ImportError(f"import of {name!r} is not allowed")

    safe["__import__"] = _import
    safe["print"] = lambda *a, **k: None
    glb = {"__builtins__": safe, "__name__": "spec"}
    glb.update(mods)
    exec(compile(code, "<spec>", "exec"), glb)
    return glb


def _number(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        if abs(x) > 10**15:
            return float(x)
        return x
    if isinstance(x, float):
        return x
    try:
        import fractions

        if isinstance(x, fractions.Fraction):
            return float(x)
    except Exception:
        pass
    return None


def _clean_assign(a):
    if not isinstance(a, dict):
        return None
    out = {}
    for k, v in a.items():
        if not isinstance(k, str):
            return None
        n = _number(v)
        if n is None:
            return None
        out[k] = n
    return out


def _call(fn, *args):
    signal.setitimer(signal.ITIMER_REAL, CALL_SECONDS)
    try:
        return fn(*args), None
    except CallTimeout:
        return None, "timeout"
    except BaseException as exc:  # noqa: BLE001
        return None, type(exc).__name__
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _verdict(fn, assign):
    res, err = _call(fn, dict(assign))
    if err:
        return {"valid": False, "label": None, "error": err}
    if not (isinstance(res, (tuple, list)) and len(res) == 2):
        return {"valid": False, "label": None, "error": "bad_return"}
    valid = res[0] is True
    label = _number(res[1]) if valid else None
    if valid and label is None:
        return {"valid": True, "label": "non_numeric", "error": None}
    if isinstance(label, float) and not math.isfinite(label):
        return {"valid": True, "label": "non_finite", "error": None}
    return {"valid": valid, "label": label, "error": None}


def main() -> None:
    req = json.loads(sys.stdin.read())
    mods = _modules()  # import everything before the descriptor limit
    signal.signal(signal.SIGALRM, _alarm)
    _limits()
    out = {"ok": True, "error": None, "seed": None, "samples": []}
    code = req["generator_code"] + "\n\n" + req["verifier_code"] + "\n"
    try:
        ns_a, err = _call(_namespace, code, mods)
        ns_b, err_b = _call(_namespace, code, mods)
        if err or err_b:
            raise RuntimeError(err or err_b)
        gen_a, ver_a = ns_a.get("generator"), ns_a.get("verifier")
        gen_b = ns_b.get("generator")
        if not (callable(gen_a) and callable(ver_a) and callable(gen_b)):
            raise RuntimeError("missing generator/verifier")
    except BaseException as exc:  # noqa: BLE001
        out.update(ok=False, error=f"compile:{type(exc).__name__}")
        sys.stdout.write(json.dumps(out))
        return

    out["seed"] = _verdict(ver_a, req["seed_assignment"])
    replays = {}
    for key in reversed(req["keys"]):
        random.seed(key)
        b_raw, gb = _call(gen_b, RNGShim(key))
        replays[key] = _clean_assign(b_raw) if gb is None else None
    for key in req["keys"]:
        random.seed(key)
        a_raw, ga = _call(gen_a, RNGShim(key))
        a = _clean_assign(a_raw) if ga is None else None
        b = replays.get(key)
        sample = {"assign": a, "replay": b, "gen_error": ga or (None if a is not None else "bad_assignment")}
        if a is not None:
            sample["verdict"] = _verdict(ver_a, a)
        out["samples"].append(sample)
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
