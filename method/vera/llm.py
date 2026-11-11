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
