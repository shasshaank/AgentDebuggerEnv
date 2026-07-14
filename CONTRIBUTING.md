# Contributing

Thanks for considering a contribution. This is a research environment, so the bar
is the same one the code holds itself to: if a change alters what a reward or a
sandbox verdict *means*, it needs a test that says so.

## Setup

Python 3.10+ on Linux or macOS. The core package has no third-party dependencies.

```bash
git clone https://github.com/PulipatiPranav/AgentDebuggerEnv.git
cd AgentDebuggerEnv
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'          # editable install + pytest and ruff
```

`pip install -e .` alone gives you the environment, sandbox, tasks, rewards,
dataset and CLI. The `serve`, `api` and `train` extras are only needed if you are
touching those code paths.

## Tests and lint

Both run in CI on every push and pull request, and both must be green to merge.

```bash
pytest                    # the full suite, ~25s (includes the 90-bug sandbox check)
pytest -m "not slow"      # skip the dataset-wide check
ruff check src tests      # lint
ruff check --fix src tests
```

## Repository structure

```text
src/agentdebugger/
├── config.py     # sandbox limits and the curriculum schedule
├── protocol.py   # actions, observations, structured-response parsing
├── sandbox/      # policy (static analysis) · runner (rlimits) · cases (test runner)
├── tasks/        # the three hand-written tasks + shared test harness
├── dataset/      # the 90-bug tiered dataset, its loader and its validator
├── rewards/      # dense turn reward (training) · episode graders (tasks)
├── envs/         # TaskEnvironment (multi-step) · CurriculumEnvironment (single-turn)
├── agents/       # oracle (offline) · api (OpenAI-compatible)
├── evaluation/   # episode and curriculum evaluation, with JSON reports
├── training/     # GRPO trainer, prompts, hardware-scaled batch geometry
├── serve/        # FastAPI server for the multi-step environment
└── cli.py        # the `agentdebugger` command
```

The dependency graph points inward and is acyclic — see
[docs/architecture.md](docs/architecture.md). Keep it that way: `import
agentdebugger` must never pull in Torch or FastAPI, so the `training` and `serve`
modules import their heavy dependencies lazily, inside functions.

## Adding a debugging task

There are two places a "task" can live, and they are not interchangeable.

**A new bug in the tiered dataset** (the usual case — this is what GRPO trains
on). Append one JSON object per line to the right tier file in
`src/agentdebugger/dataset/bugs/`, matching the schema in
[`dataset/models.py`](src/agentdebugger/dataset/models.py):

```json
{"id": "t2_031", "difficulty": 2, "bug_type": "off_by_one",
 "function_name": "binary_search", "buggy_code": "def binary_search(...): ...",
 "original_code": "def binary_search(...): ...",
 "initial_error": "IndexError: list index out of range on line 5",
 "bug_location": {"function": "binary_search", "line_start": 2},
 "test_cases": [{"input": [[1, 2, 3], 2], "expected_output": 1}]}
```

`original_code` is the reference fix, `input` is splatted into the call as
positional arguments, and `bug_location` scores localization but is never shown
to the agent. Tier 1 (`difficulty: 1`) is a bug you find by reading the error;
tier 3 is one no naive test reveals. Then prove it is sound:

```bash
agentdebugger validate --tiers 2
```

That runs the reference fix and the buggy code through the sandbox and asserts
the fix passes every case and the buggy code fails at least one. A bug that does
not pass `validate` is not a bug, and CI will reject it.

**A new hand-written multi-step task** (rarer — these are the three showcase
failure modes). Add a module under `src/agentdebugger/tasks/` returning a
`Task`, register it in `tasks/__init__.py`, and add its episode grader in
`rewards/graders.py`. A task needs a grader that scores zero for submitting
nothing — including when the buggy code passes every sequential test, as in the
`hard` task.

## Pull requests

- One logical change per PR, with a description of *why*, not just *what*.
- New behaviour comes with a test. Changes to a reward component, a sandbox rule
  or the curriculum schedule need a test that pins the new meaning — several
  claims in the README and [docs/report.md](docs/report.md) are enforced by
  `tests/test_claims.py`, and if your change invalidates a claim, update both the
  claim and its test in the same PR.
- Keep `ruff check` and `pytest` green locally before pushing.
- Do not add dependencies to the core package. If a feature needs one, it belongs
  behind an extra in `pyproject.toml`.
- No benchmark numbers without a reproducible command that produced them.
