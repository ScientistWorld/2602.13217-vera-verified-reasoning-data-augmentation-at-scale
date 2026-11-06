# VeRA: Verified Reasoning Data Augmentation at Scale

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2602.13217"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2602.13217-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| | |
|---|---|
| **Paper ID** | [2602.13217](https://arxiv.org/abs/2602.13217) |
| **Domain** | Reasoning benchmark generation and evaluation |
| **TL;DR** | VeRA turns static benchmark questions into executable families |

## Summary

The paper argues that static reasoning benchmarks invite memorization and lose
discriminative power as models improve. VeRA compiles a seed problem into a
template, generator, and verifier so new variants can be sampled and labeled
deterministically. It supports equivalent rewrites for robustness diagnostics
and hardened variants for renewed difficulty. This workspace reproduces those
mechanics offline on paper-shown AIME executable families.

## Problem

Can a benchmark item be transformed into many new, valid reasoning questions
whose labels remain trustworthy without requiring per-item human annotation or
model-voting agreement?

## The paper's method

VeRA represents benchmark items as executable specifications that can generate
fresh verified variants on demand. This separates benchmark scale from the cost
of relabeling every item.

## Key results of the paper

- GSM8K verified rewrites reduce the paper's conservative both-wrong artifact
- On AIME-2024, VeRA-E lowers the 16-model mean Avg@5 from 84.46% to 70.25%,
- On AIME-2024-II, VeRA-H Pro lowers the mean Avg@5 from 84.91% to 58.57%,

## Run it

```bash
pip install sciworld
sw research 2602.13217 --mode innovate --agent claude-code
sw evaluate 2602.13217
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

