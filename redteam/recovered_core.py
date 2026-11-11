"""Audit-only recovery of missing method.vera_repro.core; not the reference.

The specification and driver sources are unchanged. Hash encoding is declared
here because the original encoding cannot be recovered from packaged code.
"""
from __future__ import annotations
import builtins
import hashlib
import json
import multiprocessing as mp
import random
import resource
import time
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ExecutableSpec:
    spec_id: str
    mode: str
    template: str
    generator_code: str
    verifier_code: str
    base_assignment: dict | None = None
    base_answer: float | None = None
    hardness_rank: int = 0

def _math_import(name, *args, **kwargs):
    if name != "math":
        raise ImportError(name)
    return builtins.__import__(name, *args, **kwargs)

def _worker(conn, code, function, argument, seed):
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        safe_names = ["abs", "all", "any", "bool", "dict", "enumerate", "float",
                      "int", "len", "list", "max", "min", "range", "round",
                      "set", "sorted", "str", "sum", "tuple", "zip"]
        safe = {k: getattr(builtins, k) for k in safe_names}
        safe["__import__"] = _math_import
        scope = {"__builtins__": safe}
        exec(compile(code, "<audit-recovered-spec>", "exec"), scope)
        value = random.Random(seed) if function == "generator" else argument
        conn.send((True, scope[function](value)))
    except BaseException as exc:
        conn.send((False, f"{type(exc).__name__}: {exc}"))
    finally:
        conn.close()

def _execute(code, function, argument=None, seed=None):
    ctx = mp.get_context("fork")
    parent, child = ctx.Pipe(duplex=False)
    process = ctx.Process(target=_worker, args=(child, code, function, argument, seed))
    process.start()
    child.close()
    if not parent.poll(10):
        process.kill()
        process.join()
        raise TimeoutError(function)
    ok, value = parent.recv()
    process.join()
    parent.close()
    if not ok:
        raise RuntimeError(value)
    return value

def verify_assignment(spec, assignment):
    return _execute(spec.verifier_code, "verifier", assignment)

def sample_instance(spec, sample_index, base_seed):
    begin = time.monotonic()
    encoded = f"{base_seed}:{spec.spec_id}:{sample_index}".encode()
    seed = int.from_bytes(hashlib.sha256(encoded).digest(), "big")
    assignment = _execute(spec.generator_code, "generator", seed=seed)
    valid, answer = verify_assignment(spec, assignment)
    if not valid or answer is None:
        raise ValueError(f"Invalid generated assignment: {spec.spec_id}")
    return {"spec_id": spec.spec_id, "mode": spec.mode,
            "variant_id": f"{spec.spec_id}_s{sample_index:03d}",
            "sample_index": sample_index, "assignment": assignment,
            "question": spec.template.format(**assignment), "answer": answer,
            "numeric_answer": float(answer), "elapsed_sec": time.monotonic() - begin}

def write_jsonl(path: Path, rows):
    with Path(path).open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
