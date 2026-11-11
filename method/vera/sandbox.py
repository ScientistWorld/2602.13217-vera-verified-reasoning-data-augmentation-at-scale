"""Sandboxed execution of Teacher-proposed executable specifications.

Mirrors the restrictions published in briefing/evaluation.md: restricted
builtins, an import whitelist (math, random, fractions, itertools,
functools), no private attributes or frame introspection, per-call timers and
process resource limits.  The paper's Appendix B.1 sandbox is the model.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import string
import subprocess
import sys
from pathlib import Path

WORKER = Path(__file__).resolve().parent / "sandbox_worker.py"
ALLOWED_IMPORTS = {"math", "random", "fractions", "itertools", "functools"}
FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "open", "getattr", "setattr", "delattr", "globals", "locals", "vars",
    "input", "breakpoint", "memoryview", "type", "object", "super", "classmethod", "staticmethod",
    "property", "help", "dir", "id", "hash",
}
FORBIDDEN_ATTRS = {
    "gi_frame", "gi_code", "gi_yieldfrom", "gi_running", "cr_frame", "cr_code", "cr_await", "ag_frame",
    "ag_code", "f_back", "f_globals", "f_builtins", "f_locals", "f_code", "f_trace", "tb_frame", "tb_next",
    "co_code", "co_consts", "mro", "format_map", "with_traceback",
}


def hash_seed(*parts) -> int:
    """seed_val = Hash(seed_id, generator_id, sample_idx)  (paper Sec. 3.1, R5)."""
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:15], 16)


def static_problem(code: str) -> str | None:
    if len(code) > 20000:
        return "code longer than 20000 characters"
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"SyntaxError: {exc.msg} (line {exc.lineno})"
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and (node.attr.startswith("_") or node.attr in FORBIDDEN_ATTRS):
            return f"attribute '{node.attr}' is not allowed"
        if isinstance(node, ast.Name) and (node.id.startswith("__") or node.id in FORBIDDEN_NAMES):
            return f"name '{node.id}' is not allowed"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("__"):
            return "dunder function names are not allowed"
        if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.Await, ast.Global, ast.Nonlocal)):
            return f"{type(node).__name__} is not allowed"
        if isinstance(node, ast.Import) and any(a.name not in ALLOWED_IMPORTS for a in node.names):
            return "only math, random, fractions, itertools, functools may be imported"
        if isinstance(node, ast.ImportFrom) and (node.level or node.module not in ALLOWED_IMPORTS):
            return "only math, random, fractions, itertools, functools may be imported"
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and "__" in node.value:
            return "strings containing '__' are not allowed"
    return None


def template_problem(template: str, slot_names: list[str]) -> str | None:
    if not isinstance(template, str) or not template.strip():
        return "template missing"
    try:
        fields = [f for _, f, _, _ in string.Formatter().parse(template) if f is not None]
    except ValueError as exc:
        return f"template is not a valid format string ({exc})"
    missing = sorted(set(slot_names) - set(fields))
    extra = sorted(set(fields) - set(slot_names))
    if missing or extra:
        return f"template placeholders must be exactly {{{', '.join(slot_names)}}}; missing {missing}, unexpected {extra}"
    return None


def run(code: str, seed_assignment: dict, keys: list[int], probes: list[dict] | None = None,
        solve_code: str | None = None, timeout: float = 90.0) -> dict:
    req = {"code": code, "seed_assignment": seed_assignment, "keys": keys, "probes": probes or [],
           "solve_code": solve_code}
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONHASHSEED": "0"}
    try:
        proc = subprocess.run([sys.executable, "-I", "-S", str(WORKER)], input=json.dumps(req),
                              capture_output=True, text=True, timeout=timeout, cwd="/", env=env)
        return json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout: spec execution exceeded the time limit"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"sandbox failure: {type(exc).__name__}"}
