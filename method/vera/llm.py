"""Batched chat generation with Hugging Face transformers (Teacher model)."""
from __future__ import annotations

import copy
import time


class ChatLM:
    def __init__(self, path: str, batch_size: int = 48, max_new_tokens: int = 900):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(path)
        self.tok.padding_side = "left"
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        self.model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.bfloat16, device_map="cuda")
        self.model.eval()
        self.batch_size = batch_size
        self.max_new_tokens = max_new_tokens
        self.cache: dict[tuple, str] = {}
        self.tokens_generated = 0

    def _render(self, messages: list[dict]) -> str:
        return self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    def generate(self, convs: list[list[dict]], temperature: float = 0.0, seed: int = 0,
                 max_new_tokens: int | None = None) -> list[str]:
        torch = self.torch
        texts = [self._render(m) for m in convs]
        keys = [(t, temperature, seed if temperature > 0 else 0, max_new_tokens) for t in texts]
        todo = sorted({i for i, k in enumerate(keys) if k not in self.cache}, key=lambda i: len(texts[i]))
        uniq: dict[tuple, int] = {}
        for i in todo:
            uniq.setdefault(keys[i], i)
        order = list(uniq.values())
        start = time.time()
        bs = self.batch_size
        pos = 0
        while pos < len(order):
            batch = order[pos:pos + bs]
            enc = self.tok([texts[i] for i in batch], return_tensors="pt", padding=True).to("cuda")
            gc = copy.deepcopy(self.model.generation_config)
            gc.max_new_tokens = max_new_tokens or self.max_new_tokens
            gc.pad_token_id = self.tok.pad_token_id
            gc.repetition_penalty = 1.0
            if temperature > 0:
                torch.manual_seed(seed * 100003 + pos)
                gc.do_sample, gc.temperature, gc.top_p, gc.top_k = True, temperature, 0.95, 0
            else:
                gc.do_sample, gc.temperature, gc.top_p, gc.top_k = False, 1.0, 1.0, 50
            try:
                with torch.no_grad():
                    out = self.model.generate(**enc, generation_config=gc)
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                bs = max(1, bs // 2)
                print(f"[llm] OOM, batch size -> {bs}", flush=True)
                continue
            new = out[:, enc["input_ids"].shape[1]:]
            for row, i in zip(new, batch):
                self.tokens_generated += int((row != self.tok.pad_token_id).sum())
                self.cache[keys[i]] = self.tok.decode(row, skip_special_tokens=True)
            pos += len(batch)
            print(f"[llm] {pos}/{len(order)} prompts, {time.time() - start:.0f}s, bs={bs}", flush=True)
        return [self.cache[k] for k in keys]


class ReplayLM:
    """Cache-only stand-in for ChatLM: replays logged Teacher generations on CPU.

    Renders the Qwen2.5 chat template by hand so cache keys match ChatLM's."""

    def __init__(self):
        self.cache: dict[tuple, str] = {}
        self.tokens_generated = 0

    @staticmethod
    def _render(messages: list[dict]) -> str:
        out = "".join(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n" for m in messages)
        return out + "<|im_start|>assistant\n"

    @staticmethod
    def _loose(text: str) -> str:
        # Feedback quotes Python exception messages, which differ across Python
        # versions; match on everything except the quoted issue text.
        i, j = text.find("Issues to fix:\n"), text.find("\nPrevious output:")
        return text[:i] + text[j:] if 0 <= i < j else text

    def generate(self, convs, temperature: float = 0.0, seed: int = 0, max_new_tokens=None):
        if not hasattr(self, "_index"):
            self._index = {}
            for k, v in self.cache.items():
                self._index.setdefault((self._loose(k[0]),) + tuple(k[1:]), []).append(v)
        outs = []
        for m in convs:
            text = self._render(m)
            key = (text, temperature, seed if temperature > 0 else 0, max_new_tokens)
            if key in self.cache:
                outs.append(self.cache[key])
                continue
            hits = self._index.get((self._loose(text),) + key[1:], [])
            if len(hits) != 1:
                raise KeyError("replay cache miss; run without --replay_only on a GPU")
            outs.append(hits[0])
        return outs
