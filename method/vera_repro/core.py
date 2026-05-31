from __future__ import annotations

import hashlib
import json
import math
import multiprocessing as mp
import random
import resource
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


class RNGShim:
    """Deterministic subset of random.Random exposed to generated specs."""

    def __init__(self, seed: int):
        self.seed = int(seed)
        self._rng = random.Random(self.seed)

    def random(self) -> float:
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        return self._rng.uniform(a, b)

    def choice(self, seq):
        return self._rng.choice(seq)

    def sample(self, population, k: int):
        return self._rng.sample(population, k)

    def shuffle(self, x):
        self._rng.shuffle(x)
        return x


SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "pow": pow,
    "range": range,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def safe_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):
    if level == 0 and name == "math":
        return math
    raise ImportError(f"module {name!r} is not allowed in executable specs")


@dataclass(frozen=True)
class ExecutableSpec:
    spec_id: str
    mode: str
    template: str
    generator_code: str
    verifier_code: str
    base_assignment: dict[str, Any] | None = None
    base_answer: float | None = None
    hardness_rank: int = 0


def hash_seed(*parts: Any, base_seed: int = 0) -> int:
    key = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return (int.from_bytes(digest[:4], "big") ^ int(base_seed)) & 0x7FFFFFFF


def _worker(q: mp.Queue, code: str, fn_name: str, payload: dict[str, Any], mem_bytes: int) -> None:
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except Exception:
        pass
    try:
        builtins = dict(SAFE_BUILTINS)
        builtins["__import__"] = safe_import
        glob = {"__builtins__": builtins, "math": math}
        loc: dict[str, Any] = {}
        exec(code, glob, loc)
        fn = loc[fn_name]
        if fn_name == "generator":
            result = fn(RNGShim(int(payload["seed"])))
        else:
            result = fn(payload["assignment"])
        q.put((True, result, None))
    except Exception:
        q.put((False, None, traceback.format_exc()))


def run_sandboxed(
    code: str,
    fn_name: str,
    payload: dict[str, Any],
    timeout_sec: float = 10.0,
    mem_bytes: int = 512 * 1024 * 1024,
) -> Any:
    q: mp.Queue = mp.Queue(1)
    p = mp.Process(target=_worker, args=(q, code, fn_name, payload, mem_bytes))
    p.start()
    p.join(timeout=timeout_sec)
    if p.is_alive():
        p.terminate()
        p.join(1)
        raise TimeoutError(f"{fn_name} exceeded {timeout_sec}s")
    ok, result, err = q.get_nowait()
    if not ok:
        raise RuntimeError(err)
    return result


def render(template: str, assignment: dict[str, Any]) -> str:
    return template.format(**assignment)


def sample_instance(
    spec: ExecutableSpec,
    sample_index: int,
    base_seed: int,
    timeout_sec: float = 10.0,
) -> dict[str, Any]:
    seed = hash_seed(spec.spec_id, sample_index, base_seed=base_seed)
    start = time.time()
    assignment = run_sandboxed(spec.generator_code, "generator", {"seed": seed}, timeout_sec)
    result = run_sandboxed(spec.verifier_code, "verifier", {"assignment": assignment}, timeout_sec)
    if not isinstance(result, (tuple, list)) or len(result) != 2:
        valid, answer = True, result
    else:
        valid, answer = bool(result[0]), result[1]
    if not valid:
        raise ValueError(f"generator produced invalid assignment for {spec.spec_id}: {assignment}")
    return {
        "variant_id": f"{spec.spec_id}_s{sample_index:03d}",
        "spec_id": spec.spec_id,
        "mode": spec.mode,
        "sample_index": sample_index,
        "assignment": assignment,
        "question": render(spec.template, assignment),
        "answer": answer,
        "numeric_answer": float(answer),
        "elapsed_sec": time.time() - start,
    }


def verify_assignment(spec: ExecutableSpec, assignment: dict[str, Any], timeout_sec: float = 10.0) -> tuple[bool, Any]:
    result = run_sandboxed(spec.verifier_code, "verifier", {"assignment": assignment}, timeout_sec)
    if isinstance(result, (tuple, list)) and len(result) == 2:
        return bool(result[0]), result[1]
    return True, result


def deterministic_replay(spec: ExecutableSpec, sample_index: int, base_seed: int) -> bool:
    first = sample_instance(spec, sample_index, base_seed)
    second = sample_instance(spec, sample_index, base_seed)
    return json.dumps(first["assignment"], sort_keys=True) == json.dumps(second["assignment"], sort_keys=True) and abs(
        float(first["numeric_answer"]) - float(second["numeric_answer"])
    ) <= 1e-12


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
