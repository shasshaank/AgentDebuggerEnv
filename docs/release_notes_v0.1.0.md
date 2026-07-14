# AgentDebuggerEnv v0.1.0 — draft release notes

> **Status: draft.** These notes are ready to paste into a GitHub Release once
> `v0.1.0` is tagged. See [Publishing](#publishing) for the manual steps.

**AgentDebuggerEnv is a reinforcement-learning environment that teaches language
models to debug the way engineers do — observe, hypothesise, then fix — instead
of guessing.** An agent is shown broken Python and real test output, must state a
hypothesis before it is allowed to run a fix, and every submission executes in a
resource-limited sandbox that scores what it actually did.

This is the first public release.

## Highlights

- **The reasoning step is what pays.** A fix submitted without a hypothesis is
  not executed. The reward is dense and itemised — format, hypothesis quality,
  localization, fix correctness, similarity, efficiency, penalties — so a weak
  policy still gets a gradient to climb, but fix quality is the largest component,
  so no amount of plausible prose substitutes for passing the tests.
- **A sandbox that survives what an LLM actually writes.** Static AST analysis
  refuses `import os`, `open('/etc/passwd')`, `eval` and
  `().__class__.__subclasses__()` *before* execution; kernel rlimits and a
  process-group deadline contain what does run. Legitimate fixes needing
  `hashlib`, `threading` or `super()` are unimpeded.
- **One scoring path.** The reward a completion receives during training is
  exactly what the evaluator computes for it — both call `score_response` — so a
  training curve and an eval number mean the same thing. A test asserts it.
- **Runs offline, on CPU, in about a minute.** The core package is pure standard
  library. An oracle agent lets anyone watch a full episode — sandbox, grader and
  all — with no GPU and no API key.

## Major features

| Area | What ships |
| --- | --- |
| Sandbox | Static policy + `setrlimit` (memory, CPU, file-size) + wall-clock deadline that kills the process group |
| Environments | `TaskEnvironment` (multi-step, hypothesis-gated) and `CurriculumEnvironment` (single-turn, what GRPO trains against) |
| Tasks | Three hand-written failure modes: off-by-one, red herring, and a race condition that passes every sequential test |
| Dataset | 90 tiered bugs (40 / 30 / 20), each execution-validated by `agentdebugger validate` |
| Rewards | Dense per-turn reward over `[-0.5, 1.0]`, plus per-task episode graders |
| Curriculum | Tier 2 unlocks at step 150, tier 3 at step 350; the trainer swaps the pool at each boundary |
| Training | GRPO + LoRA on `Qwen2.5-Coder-3B-Instruct`, batch geometry scaled to the detected GPU (T4 → H100) |
| Agents | Offline `OracleAgent`; `ApiAgent` for any OpenAI-compatible endpoint |
| Serving | FastAPI `/reset`, `/step`, `/state` |
| CLI | `episode`, `evaluate`, `evaluate-curriculum`, `validate`, `tasks`, `serve`, `train` |

## Installation

Python 3.10+ on Linux or macOS. The core install pulls **no third-party
dependencies**.

```bash
git clone https://github.com/PulipatiPranav/AgentDebuggerEnv.git
cd AgentDebuggerEnv
python -m venv .venv && source .venv/bin/activate
pip install -e .

agentdebugger episode --task hard    # watch an agent debug a race condition
agentdebugger evaluate               # score the reference agent
agentdebugger validate               # check all 90 bugs are genuinely broken and fixable
```

Heavier features are opt-in extras: `.[serve]`, `.[api]`, `.[train]`, `.[dev]`.

## Results and their provenance

Reward curves from the published GRPO run are in [images/](images/), and per-bug
evaluation output for the trained adapter is in [`results/`](../results/).

**Read those numbers with the caveat recorded in the file itself**: they were
produced by an earlier evaluation harness and are kept for provenance. They are
*not* a controlled comparison — there is no matched unstructured baseline, no
reward ablation and no no-curriculum arm behind them, so they should not be cited
as evidence for the project's hypotheses. Reproduce them with:

```bash
agentdebugger evaluate-curriculum --adapter <repo> --output results/<name>.json
```

## Known limitations

- **Single-file scope.** The environment operates on isolated functions, not
  multi-file repositories. This is a training simplification and the primary
  limit on real-world transfer.
- **The sandbox is a workstation-grade defence.** It safely runs the code an LLM
  actually produces on a developer machine or CI box. It is not a substitute for
  a container or VM when running deliberately adversarial code from an untrusted
  third party.
- **The hard-task grader is empirical.** It detects the race by stress testing,
  so it can demonstrate the presence of a lost update but never prove thread
  safety in general.
- **The central claims are stated, not yet tested.** The contributions of the
  structured Observation → Hypothesis → Action format, of the reward
  decomposition, and of the curriculum have not been isolated by ablation. They
  are written as falsifiable hypotheses with a pre-registered experiment matrix
  in [docs/research_plan.md](research_plan.md); the experiments have not been run.
- **One trained model.** Only `Qwen2.5-Coder-3B-Instruct` has been trained in this
  environment. Nothing is known about how any of this scales.

## Roadmap preview

- **Run the pre-registered experiments** in [docs/research_plan.md](research_plan.md):
  the structured-vs-unstructured, reward-ablation and curriculum arms that would
  turn the three claims into results.
- **Multi-file debugging**, with a language-server view of the codebase so the
  agent can trace across call stacks and imports.
- **Adversarial bug generation**, where a second model mutates bugs against the
  current policy's weaknesses, turning a fixed curriculum into a self-sustaining
  one.
- **A PPO comparison**, to put numbers behind the memory-versus-stability
  trade-off that motivated GRPO.

Contributions are welcome — see [CONTRIBUTING.md](../CONTRIBUTING.md) and the
[good first issues](good_first_issues.md).

## Publishing

This file is the draft body. To cut the release:

```bash
git tag -a v0.1.0 -m "AgentDebuggerEnv v0.1.0"
git push origin v0.1.0
gh release create v0.1.0 --title "AgentDebuggerEnv v0.1.0" \
    --notes-file docs/release_notes_v0.1.0.md
```

## License

MIT — see [LICENSE](../LICENSE).
