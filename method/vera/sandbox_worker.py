"""Subprocess worker that executes Teacher-written spec code under limits.

Request (stdin JSON):
  code             generator + verifier source (one namespace)
  solve_code       optional independent solve(...) source (cross-check gate)
  seed_assignment  canonical seed slot values
  keys             RNG seeds for generator samples (hash-seeded, paper R5)
  probes           extra assignments to run through the verifier
Response (stdout JSON): seed verdict, per-key samples, probe verdicts.
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


def _limits() -> None:
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    except Exception:
        pass


def _proxy(mod):
    return types.SimpleNamespace(**{n: getattr(mod, n) for n in dir(mod)
                                    if not n.startswith("_") and not isinstance(getattr(mod, n), types.ModuleType)})


SAFE = ["abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "frozenset",
        "int", "isinstance", "len", "list", "map", "max", "min", "pow", "range", "reversed", "round",
        "set", "sorted", "str", "sum", "tuple", "zip", "ValueError", "ZeroDivisionError",
        "ArithmeticError", "Exception", "KeyError", "IndexError", "TypeError", "OverflowError",
        "StopIteration", "True", "False", "None"]


class RNGShim:
    def __init__(self, seed):
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


def _call(fn, *args):
    signal.setitimer(signal.ITIMER_REAL, CALL_SECONDS)
    try:
        return fn(*args), None
    except CallTimeout:
        return None, "timeout"
    except BaseException as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {str(exc)[:120]}"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def _namespace(code, mods):
    safe = {n: getattr(builtins, n) for n in SAFE if hasattr(builtins, n)}

    def _imp(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name in mods and level == 0:
            return mods[name]
        raise ImportError(f"import of {name!r} is not allowed")

    safe["__import__"] = _imp
    safe["print"] = lambda *a, **k: None
    glb = {"__builtins__": safe, "__name__": "spec"}
    glb.update(mods)
    exec(compile(code, "<spec>", "exec"), glb)
    return glb


def _num(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x if abs(x) <= 10**15 else float(x)
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    try:
        import fractions

        if isinstance(x, fractions.Fraction):
            return float(x)
    except Exception:
        pass
    return None


def _assign(a):
    if not isinstance(a, dict):
        return None
    out = {}
    for k, v in a.items():
        n = _num(v)
        if not isinstance(k, str) or n is None:
            return None
        out[k] = n
    return out


def _verdict(fn, a):
    res, err = _call(fn, dict(a))
    if err:
        return {"valid": False, "label": None, "error": err}
    if not (isinstance(res, (tuple, list)) and len(res) == 2):
        return {"valid": False, "label": None, "error": "verifier must return (valid, answer)"}
    if res[0] is not True:
        return {"valid": False, "label": None, "error": None}
    lab = _num(res[1])
    if lab is None:
        return {"valid": True, "label": None, "error": "answer is not a finite number"}
    return {"valid": True, "label": lab, "error": None}


def main():
    req = json.loads(sys.stdin.read())
    _limits()
    signal.signal(signal.SIGALRM, _alarm)
    import fractions
    import functools
    import itertools

    mods = {"math": _proxy(math), "random": _proxy(random), "fractions": _proxy(fractions),
            "itertools": _proxy(itertools), "functools": _proxy(functools)}
    out = {"ok": True, "error": None, "seed": None, "samples": [], "probes": []}
    ns, err = _call(_namespace, req["code"], mods)
    if err or not callable((ns or {}).get("generator")) or not callable((ns or {}).get("verifier")):
        out.update(ok=False, error=f"compile/runtime: {err or 'generator/verifier not defined'}")
        sys.stdout.write(json.dumps(out))
        return
    gen, ver = ns["generator"], ns["verifier"]
    solve = None
    if req.get("solve_code"):
        ns2, err2 = _call(_namespace, req["solve_code"], mods)
        solve = (ns2 or {}).get("solve") if not err2 else None
        out["solve_error"] = err2 if err2 else (None if callable(solve) else "solve not defined")
    out["seed"] = _verdict(ver, req["seed_assignment"])
    names = list(req["seed_assignment"])
    for key in req.get("keys", []):
        random.seed(key)
        raw, gerr = _call(gen, RNGShim(key))
        a = _assign(raw) if gerr is None else None
        sample = {"assign": a, "gen_error": gerr or (None if a is not None else "generator must return a dict of numbers")}
        if a is not None:
            sample["verdict"] = _verdict(ver, a)
            if callable(solve) and set(a) == set(names):
                sval, serr = _call(solve, *[a[n] for n in names])
                sample["solve"] = _num(sval) if serr is None else None
        out["samples"].append(sample)
    for probe in req.get("probes", []):
        out["probes"].append(_verdict(ver, probe))
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
